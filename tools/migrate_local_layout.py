#!/usr/bin/env python3
"""One-time, journalled local layout migration. Preview by default; no deletion of files."""
from pathlib import Path
import argparse, hashlib, json, os, shutil, sqlite3, time


def mapping(root):
    d=root/'local_data'
    pairs=[]
    def add(a,b):
        a,b=Path(a),Path(b)
        if a.exists(): pairs.append((a,b))
    for old,new in [('migration_plan','plans/migration'),('My idea','plans/archive/ideas'),('PLAN.md','plans/archive/PLAN.md'),('REUSE_AUDIT.md','plans/archive/REUSE_AUDIT.md'),('Vibe Editor','design/vibe-editor'),('images.png','design/reference/images.png'),('test-results','local_data/test-results')]:add(root/old,root/new)
    for old,new in [('storage/production','services/production'),('storage/video_repertoire','services/media'),('storage/performance','reports/performance'),('storage/debug','reports/debug'),('story_imports','services/production/story-imports'),('ace_studio','services/music'),('vibe_editor/runtime','runtimes/editor'),('vibe_editor','services/editor'),('exports','reports/batch-specifications'),('donor_migration/video_repertoire/downloads','library/downloads/youtube'),('donor_migration/video_repertoire','library/catalog/donor-video'),('donor_migration/video_audio_analyzer','engines/video-analyzer'),('donor_migration/audio','engines/audio'),('donor_migration/youtube_code','engines/youtube-import'),('donor_migration/video_summariser','library/catalog/legacy-video'),('donor_migration/TTS_skills','engines/tts-skills'),('donor_migration/input','library/import-staging'),('story_builder_resources','engines/resources')]:add(d/old,d/new)
    for parent in [d/'media-projects',d/'assets',d/'ltx_chunks',d/'t2v_originals']:
        if not parent.exists():continue
        for child in sorted(parent.iterdir()):
            if not child.is_dir() or child.is_symlink():raise ValueError(f'Unexpected entry: {child}')
            target=d/'projects'/child.name
            if parent.name=='media-projects':
                for file in (child/'production').iterdir() if (child/'production').exists() else []:add(file,target/'media'/file.name)
                add(child/'inputs/media',target/'media/imports')
                for entry in child.iterdir():
                    if entry.name not in {'production','inputs'}:add(entry,target/'media'/entry.name)
            else:add(child,target/({'assets':'media/generated','ltx_chunks':'intermediates/chunks','t2v_originals':'intermediates/originals'}[parent.name]))
    for child in sorted(d.glob('story-*')):
        if child.is_dir():add(child/'production_v2',d/'projects'/child.name/'story/production_v2')
    for child in d.iterdir():
        if child.is_file() and child.suffix in {'.json','.jsonl'} and not child.name.startswith('.'):
            add(child,d/'reports/audits'/child.name)
    return pairs


def migrate(root, apply=False):
    root=root.resolve();d=root/'local_data'; report=d/'reports/layout-migration-20261027';report.mkdir(parents=True,exist_ok=True)
    if (report/'completed.json').exists():raise ValueError('Already applied; inspect completed.json or use --rollback.')
    pairs=mapping(root)
    for a,b in pairs:
        if a.is_symlink() or b.exists() or b.is_symlink():raise ValueError(f'Unsafe or occupied destination: {a} -> {b}')
        if a.stat().st_dev!=d.stat().st_dev:raise ValueError('This migration supports same-filesystem renames only.')
    def mapped(value):
        if not isinstance(value,str):return value
        for a,b in sorted(pairs,key=lambda p:-len(str(p[0]))):
            old=str(a)
            if value==old or value.startswith(old+'/'):return str(b)+value[len(old):]
        for a,b in sorted(pairs,key=lambda p:-len(str(p[0]))):
            if not a.is_relative_to(d) or not b.is_relative_to(d):continue
            old=a.relative_to(d).as_posix()
            if value==old or value.startswith(old+'/'):return b.relative_to(d).as_posix()+value[len(old):]
        # Workspace upload manifests store a path relative to their media directory.
        if value.startswith('inputs/media/'):return 'imports/'+value[len('inputs/media/'):]
        return value
    def transform(value):
        if isinstance(value,dict):return {k:transform(v) for k,v in value.items()}
        if isinstance(value,list):return [transform(v) for v in value]
        return mapped(value)
    # Record inode/size instead of reading tens of GB of unchanged model weights.
    entries=[]
    for a,b in pairs:
        files=[a] if a.is_file() else [p for p in a.rglob('*') if p.is_file() and not p.is_symlink()]
        entries.append({'source':str(a),'destination':str(b),'files':len(files),'bytes':sum(p.stat().st_size for p in files)})
    links=[]
    donor=Path('/home/riki/web_dev/story_builder')
    if donor.exists():
        for base,dirs,files in os.walk(donor,followlinks=False):
            dirs[:]=[name for name in dirs if name not in {'.git','.venv','node_modules','__pycache__'}]
            for name in files+dirs:
                p=Path(base)/name
                if p.is_symlink():
                    old=os.readlink(p);new=mapped(old)
                    if old!=new:links.append({'path':str(p),'before':old,'after':new})
    preview={'created_at':time.time(),'moves':entries,'donor_links':links,'exceptions':['local_data/ace_step/runtime: fixed-prefix Python environment','graphify-out: configured code graph','music/editor registry-owned working files retain their adapter subdirectories','generated asset subfolders retain workflow-specific names and stable relative paths']}
    (report/'preview.json').write_text(json.dumps(preview,indent=2))
    if not apply:return preview
    if (report/'completed.json').exists():raise ValueError('Already applied; inspect completed.json.')
    # Confirm all durable queues are idle before stopping writers or moving anything.
    active=[]
    for p in (d/'storage/production').glob('*.sqlite3'):
        with sqlite3.connect(p) as db:
            for (table,) in db.execute("SELECT name FROM sqlite_master WHERE type='table'"):
                if 'status' not in [r[1] for r in db.execute(f'PRAGMA table_info("{table}")')]:continue
                count=db.execute(f"SELECT count(*) FROM \"{table}\" WHERE status IN ('queued','running','cancel_requested','submitted','rendering')").fetchone()[0]
                if count:active.append(f'{table}: {count}')
    for p in [*(d/'storage/video_repertoire/jobs').rglob('job.json'),d/'ace_studio/state.json',d/'vibe_editor/state.json']:
        if not p.exists():continue
        val=json.loads(p.read_text())
        def check(x):
            if isinstance(x,dict):
                if x.get('status') in {'queued','running','cancel_requested','rendering','submitted'}:active.append(str(p))
                for v in x.values():check(v)
            elif isinstance(x,list):
                for v in x:check(v)
        if p.name == 'job.json':
            if val.get('status') in {'queued','running','cancel_requested','rendering','submitted'}:active.append(str(p))
        else:
            check(val)
    if active:raise ValueError('Active jobs: '+', '.join(active))
    # Caller must stop Vibe writers; a second process scan prevents accidental live moves.
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():continue
        try:
            args=(proc/'cmdline').read_bytes().split(b'\0')
            if len(args)<3 or args[1]!=b'-m' or args[2] not in [b'story_builder.'+name for name in [b'isolated_server',b'isolated_worker',b'isolated_image_worker',b'assembly_export_worker',b'video_repertoire_worker']]:continue
            env=dict(item.split(b'=',1) for item in (proc/'environ').read_bytes().split(b'\0') if b'=' in item)
            if env.get(b'VIBE_DIRECTOR_DATA_DIR')==str(d).encode():raise ValueError('Stop Vibe API/workers first.')
        except (OSError,ProcessLookupError):continue
    backup=report/'data-before';backup.mkdir(exist_ok=True)
    dbs=list((d/'storage/production').glob('*.sqlite3'))
    for p in dbs:
        destination=backup/p.relative_to(d);destination.parent.mkdir(parents=True,exist_ok=True)
        with sqlite3.connect(p) as source,sqlite3.connect(destination) as target:source.backup(target)
    # Only active saved records are rewritten. Engine code, prompts, snapshots and weights are not walked.
    json_files=[]
    for folder in ['media-projects','storage/video_repertoire','ace_studio','vibe_editor','story-f4e3e594089b','donor_migration/video_repertoire/manifests']:
        start=d/folder
        if start.exists():json_files.extend(p for p in start.rglob('*.json') if 'node_modules' not in p.parts and 'runtime' not in p.parts)
    (report/'started.json').write_text(json.dumps({'moves':entries,'links':links},indent=2))
    # Frozen generation snapshots are immutable: never silently invalidate their hashes.
    for p in dbs:
        with sqlite3.connect(p) as db:
            for (table,) in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"):
                columns=[r[1] for r in db.execute(f'PRAGMA table_info("{table}")')]
                if 'input_snapshot_json' in columns:
                    for (value,) in db.execute(f'SELECT input_snapshot_json FROM "{table}"'):
                        if value and transform(json.loads(value)) != json.loads(value):
                            raise ValueError(f'Frozen input path requires explicit recovery adaptation: {p.name}/{table}')
    rewrites=[]
    for p in json_files:
        original=json.loads(p.read_text());updated=transform(original)
        if updated!=original:
            b=backup/p.relative_to(d);b.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,b)
            p.write_text(json.dumps(updated,ensure_ascii=False,indent=2));rewrites.append(str(p))
    # Persisted JSON columns and absolute path columns; arbitrary text is not substring-replaced.
    for p in dbs:
        with sqlite3.connect(p) as db:
            for (table,) in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"):
                columns=[r[1] for r in db.execute(f'PRAGMA table_info("{table}")')]
                for row in db.execute(f'SELECT rowid,* FROM "{table}"').fetchall():
                    updates={}
                    for key,value in zip(columns,row[1:]):
                        if key == 'input_snapshot_json' or not isinstance(value,str):continue
                        replacement=mapped(value)
                        if replacement==value and value[:1] in {'{','['}:
                            try:
                                parsed=json.loads(value);converted=transform(parsed)
                                if parsed!=converted:replacement=json.dumps(converted,ensure_ascii=False)
                            except json.JSONDecodeError:pass
                        if replacement!=value:updates[key]=replacement
                    if updates:
                        assignments=','.join(f'"{c}"=?' for c in updates)
                        db.execute(f'UPDATE "{table}" SET {assignments} WHERE rowid=?',[*updates.values(),row[0]])
            db.commit();assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    journal=[]
    for a,b in pairs:
        # A child move may have made a parent empty; retain it too for a clean reversible mapping.
        before=a.stat(); b.parent.mkdir(parents=True,exist_ok=True);a.rename(b)
        assert b.stat().st_ino==before.st_ino
        journal.append({'source':str(a),'destination':str(b),'inode':before.st_ino})
        (report/'moves.json').write_text(json.dumps(journal,indent=2))
    for item in links:
        p=Path(item['path'])
        if os.readlink(p)!=item['before']:raise ValueError(f'Compatibility link changed: {p}')
        p.unlink();p.symlink_to(item['after'])
        if not p.exists():raise ValueError(f'Broken relocated donor compatibility link: {p}')
    # Remove only empty retired directories, never bytes.
    for base in [d/'media-projects',d/'assets',d/'storage',d/'donor_migration',d/'ltx_chunks',d/'t2v_originals',d/'story-f4e3e594089b']:
        if base.exists():
            for current,dirs,files in os.walk(base,topdown=False):
                try:Path(current).rmdir()
                except OSError:pass
    result={**preview,'applied_at':time.time(),'rewritten_json':rewrites,'sqlite_backups':[str(p) for p in backup.rglob('*.sqlite3')],'moves_verified':len(journal)}
    (report/'completed.json').write_text(json.dumps(result,indent=2));return result

def rollback(root):
    root=root.resolve();d=root/'local_data';report=d/'reports/layout-migration-20261027'
    if (report/'rolled-back.json').exists():raise ValueError('Already rolled back.')
    started=json.loads((report/'started.json').read_text())
    moves=json.loads((report/'moves.json').read_text()) if (report/'moves.json').exists() else []
    # Run only with Vibe writers stopped, just as for apply.
    for proc in Path('/proc').iterdir():
        try:
            args=(proc/'cmdline').read_bytes().split(b'\0')
            if len(args)>2 and args[1]==b'-m' and args[2].startswith(b'story_builder.'):
                env=(proc/'environ').read_bytes().split(b'\0')
                if ('VIBE_DIRECTOR_DATA_DIR='+str(d)).encode() in env:raise ValueError('Stop Vibe API/workers before rollback.')
        except (OSError,ProcessLookupError):pass
    for item in reversed(moves):
        a,b=Path(item['source']),Path(item['destination'])
        # Forward moves can leave empty ancestors of separately relocated children.
        # Remove empty directories only; never remove files added after migration.
        if a.is_dir() and not a.is_symlink():
            for directory in sorted((p for p in a.rglob('*') if p.is_dir() and not p.is_symlink()), key=lambda p:len(p.parts), reverse=True):
                try:directory.rmdir()
                except OSError:pass
            try:a.rmdir()
            except OSError:pass
        if a.exists() or a.is_symlink():raise ValueError(f'Rollback destination occupied: {a}')
        if b.stat().st_ino!=item['inode']:raise ValueError(f'Relocated entry changed: {b}')
        a.parent.mkdir(parents=True,exist_ok=True);b.rename(a)
    for item in started['links']:
        p=Path(item['path'])
        if p.is_symlink() and os.readlink(p)==item['after']:
            p.unlink();p.symlink_to(item['before'])
    for p in (report/'data-before').rglob('*'):
        if p.is_file():
            target=d/p.relative_to(report/'data-before');target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(p,target)
    (report/'rolled-back.json').write_text(json.dumps({'rolled_back_at':time.time(),'moves':len(moves)}))
    return {'moves':moves}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);mode=parser.add_mutually_exclusive_group();mode.add_argument('--apply',action='store_true');mode.add_argument('--rollback',action='store_true');args=parser.parse_args()
    result=rollback(args.root) if args.rollback else migrate(args.root,args.apply);print(json.dumps({'moves':len(result['moves']),'files':sum(x.get('files',0) for x in result['moves']),'bytes':sum(x.get('bytes',0) for x in result['moves']),'applied':args.apply,'report':str(args.root/'local_data/reports/layout-migration-20261027')},indent=2))
