#!/usr/bin/env python3
"""Offline, journaled storage migration. Dry-run by default; never prunes models.

Stop Vibe Director API/workers before --apply or --rollback. The journal stores
small metadata snapshots and original workspace publication files for rollback.
Large training directories are renamed on the same filesystem, never copied.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from story_builder.services.storage_paths import relocated_path, relocate_record_paths


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    with temp.open('w') as stream:
        json.dump(data, stream, indent=2)
        stream.flush(); os.fsync(stream.fileno())
    temp.replace(path)


def inventory(root):
    moves = []
    pairs = [('library/downloads/youtube', 'youtube_downloads/files'),
             ('engines/youtube-import/out_videos', 'youtube_downloads/files/legacy_import'),
             ('services/media/analyses/video_audio_analyzer', 'video_repertoire/runs'),
             ('library/catalog/donor-video', 'video_repertoire/legacy/donor-video'),
             ('library/catalog/legacy-video/out_videos', 'video_repertoire/legacy/out_videos')]
    for name in ('uploads','clips','manifests','indexes','audio','temp'):
        pairs.append(('services/media/'+name, 'video_repertoire/'+name))
    # Remaining analyses include job results and indexes, not the already moved runs.
    analyses = root/'services/media/analyses'
    for p in sorted(analyses.iterdir()) if analyses.exists() else []:
        if p.name != 'video_audio_analyzer':
            pairs.append((str(p.relative_to(root)), 'video_repertoire/analyses/'+p.name))
    for name in ('state.json','datasets','runs'):
        pairs.append(('services/music/'+name,'ace_step/'+name))
    jukebox = root/'music_jukebox/projects'
    for p in sorted(jukebox.iterdir()) if jukebox.exists() else []:
        pairs.append((str(p.relative_to(root)), 'projects/'+p.name+'/music/jukebox'))
    pending = list(pairs)
    while pending:
        old, new = pending.pop(0)
        source,target=root/old,root/new
        if not source.exists(): continue
        if source.is_symlink() or any(p.is_symlink() for p in source.parents if p != root.parent):
            raise ValueError('Unsafe migration source: '+str(source))
        if target.exists():
            if source.is_dir() and target.is_dir() and not target.is_symlink():
                pending[0:0] = [(str(p.relative_to(root)), str((target/p.name).relative_to(root))) for p in sorted(source.iterdir())]
                continue
            raise ValueError('Destination collision: '+str(target))
        parent=target.parent
        while not parent.exists(): parent=parent.parent
        if source.stat().st_dev != parent.stat().st_dev:
            raise ValueError('Cross-filesystem move requires a separate verified copy: '+old)
        moves.append({'old':old,'new':new})
    # Resolve every published occurrence before changing anything.
    runs=root/'services/media/analyses/video_audio_analyzer'
    if not runs.exists(): runs=root/'video_repertoire/runs'
    publications=[];catalogs={'youtube':[],'repertoire':[]};manifest_updates=[]
    for manifest in sorted((root/'projects').glob('*/media/assets.json')):
        data=json.loads(manifest.read_text())
        for row in data['assets']:
            if row.get('source') == 'youtube_download':
                path=root/'library/downloads/youtube'/row['relative_path']
                if not path.exists(): path=root/'youtube_downloads/files'/row['relative_path']
                if not path.is_file() or digest(path) != row['sha256']: raise ValueError('Download missing/changed: '+str(path))
                catalogs['youtube'].append(row)
            metadata=row.get('metadata') or {}
            if row.get('source') != 'project_output' or not metadata.get('analyzer_run_id') or row.get('storage_location'): continue
            output=manifest.parent/'generated'/row['relative_path']
            if not output.is_file() or digest(output) != row['sha256']:
                raise ValueError('Publication missing/changed: '+str(output))
            run=runs/metadata['analyzer_run_id']
            relative=metadata.get('analyzer_relative_path')
            candidate=run/relative if relative else None
            if candidate is None or not candidate.is_file() or digest(candidate) != row['sha256']:
                matches=[]
                for p in run.rglob('*'):
                    if p.is_file() and not p.is_symlink() and p.stat().st_size==output.stat().st_size and digest(p)==row['sha256']: matches.append(p)
                if not matches: raise ValueError('Cannot resolve legacy occurrence: '+row['asset_id'])
                candidate=sorted(matches)[0]
            if not candidate.resolve().is_relative_to(run.resolve()) or any(p.is_symlink() for p in [candidate,*candidate.parents]):
                raise ValueError('Unsafe run artifact')
            location={'store':'repertoire','path':(Path('runs')/metadata['analyzer_run_id']/candidate.relative_to(run)).as_posix()}
            publications.append({'manifest':str(manifest.relative_to(root)),'asset_id':row['asset_id'],
                'old':str(output.relative_to(root)),'location':location,'sha256':row['sha256']})
        # Already migrated rows remain part of the canonical catalogue.
        catalogs['repertoire'].extend(r for r in data['assets'] if (r.get('storage_location') or {}).get('store')=='repertoire')
    donor_root=root/'library/catalog/donor-video'
    for manifest in sorted((donor_root/'manifests').glob('video-*.json')):
        data=json.loads(manifest.read_text())
        raw=Path(str(data.get('path','')))
        resolved=raw.resolve(strict=False)
        mappings=((root/'library/downloads/youtube',root/'youtube_downloads/files'),
                  (root/'engines/youtube-import/out_videos',root/'youtube_downloads/files/legacy_import'))
        mapping=next(((old,new,resolved.relative_to(old)) for old,new in mappings
                      if resolved.is_relative_to(old)),None)
        if mapping is None: continue
        old_root,new_root,relative=mapping
        source=old_root/relative
        canonical=new_root/relative
        # The downloads directory is part of this same journaled move. Confirm
        # the exact bytes now, before recording a path rewrite.
        if not source.is_file() or (data.get('sha256') and digest(source)!=data['sha256']):
            raise ValueError('Donor manifest download missing/changed: '+str(manifest))
        manifest_updates.append({'manifest':str(manifest.relative_to(root)),
            'path':str(canonical),'sha256':data.get('sha256','')})
    job_updates=[]
    for job in sorted((root/'services/media/jobs').glob('*/*/job.json')):
        before=json.loads(job.read_text())
        after=relocate_record_paths(root,before)
        if after != before:
            job_updates.append({'path':str(job.relative_to(root)),'data':after})
    # ACE request files are used to inspect/recover runs. Keep logs and source
    # scripts byte-for-byte; migrate only structured path-valued fields.
    ace_request_updates=[]
    for run in sorted((root/'services/music/runs').glob('*')):
        if not run.is_dir() or run.is_symlink(): continue
        for name in ('request.json','training_request.json','song_input_params.json'):
            path=run/name
            if not path.is_file() or path.is_symlink(): continue
            before=json.loads(path.read_text())
            after=relocate_record_paths(root,before)
            if after != before:
                ace_request_updates.append({'path':str(path.relative_to(root)),'data':after})
    return {'version':1,'moves':moves,'publications':publications,'catalogs':catalogs,
        'manifest_updates':manifest_updates,'job_updates':job_updates,
        'ace_request_updates':ace_request_updates}


def assert_idle(root):
    active={'queued','running','submitting','cancel_requested'}
    for path in (root/'services/media/jobs').glob('*/*/job.json'):
        if json.loads(path.read_text()).get('status') in active: raise ValueError('Active media job: '+str(path))
    import sqlite3
    for db in (root/'services/production').glob('*.sqlite3'):
        with sqlite3.connect(db.as_uri()+'?mode=ro',uri=True) as c:
            for (table,) in c.execute("SELECT name FROM sqlite_master WHERE type='table'"):
                if not table.replace('_','').isalnum(): continue
                cols={r[1] for r in c.execute('PRAGMA table_info("'+table+'")')}
                if 'status' in cols and c.execute('SELECT 1 FROM "'+table+'" WHERE status IN (?,?,?,?) LIMIT 1',tuple(active)).fetchone():
                    raise ValueError('Active production job in '+db.name+':'+table)
    # Refuse a live writer, including workers whose status record is stale.
    for proc in Path('/proc').glob('[0-9]*'):
        try: cmd=(proc/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
        except OSError: continue
        if any(x in cmd for x in ('-m story_builder.isolated_server','-m story_builder.isolated_worker','-m story_builder.services.video_repertoire_worker','-m story_builder.isolated_image_worker')):
            raise ValueError('Stop the API/workers before migration (PID '+proc.name+').')


def apply(root, report, journal):
    assert_idle(root)
    if journal.exists(): raise ValueError('Journal exists; use a new journal or rollback it.')
    journal.mkdir(parents=True)
    write(journal/'plan.json', report)
    state={'moves':[],'metadata':[],'publications':[],'created':[],'complete':False}
    def save(): write(journal/'journal.json',state)
    def backup(relative):
        if relative in state['metadata']: return
        src=root/relative;target=journal/'metadata'/relative
        if src.exists():
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,target)
            state['metadata'].append(relative)
        else: state['created'].append(relative)
        save()
    save()
    for move in report['moves']:
        target=root/move['new'];target.parent.mkdir(parents=True,exist_ok=True)
        # Write intent before rename, so rollback also handles an interrupted rename.
        state['moves'].append(move);save()
        (root/move['old']).rename(target)
    grouped={}
    for row in report['publications']: grouped.setdefault(row['manifest'],[]).append(row)
    catalogue=report['catalogs']['repertoire'][:]
    for relative, rows in grouped.items():
        backup(relative)
        path=root/relative;data=json.loads(path.read_text())
        by_id={r['asset_id']:r for r in rows}
        for row in data['assets']:
            if row['asset_id'] not in by_id: continue
            change=by_id[row['asset_id']];canonical=root/'video_repertoire'/change['location']['path']
            if digest(canonical)!=change['sha256']: raise ValueError('Canonical artifact changed during migration')
            row['storage_location']=change['location']
            row['metadata']['analyzer_relative_path']=Path(change['location']['path']).relative_to('runs/'+row['metadata']['analyzer_run_id']).as_posix()
            catalogue.append(row)
        write(path,data)
        for change in rows:
            old=root/change['old'];dest=journal/'publications'/change['old']
            dest.parent.mkdir(parents=True,exist_ok=True)
            state['publications'].append(change['old']);save();old.rename(dest)
    for relative,rows in [('youtube_downloads/catalog.json',report['catalogs']['youtube']),('video_repertoire/catalog.json',catalogue)]:
        backup(relative);write(root/relative,{'version':1,'assets':rows})
    for change in report.get('manifest_updates',[]):
        relative=change['manifest']
        migrated=relocated_path(root,root/relative)
        target_relative=str(migrated.relative_to(root))
        backup(target_relative)
        path=root/target_relative
        data=json.loads(path.read_text())
        canonical=Path(change['path'])
        if not canonical.is_absolute() or not canonical.is_relative_to(root):
            raise ValueError('Unsafe donor manifest destination: '+str(canonical))
        media=canonical
        if not media.is_file() or (change.get('sha256') and digest(media)!=change['sha256']):
            raise ValueError('Donor manifest target missing/changed: '+str(media))
        data['path']=str(media)
        write(path,data)
    for group in ('job_updates','ace_request_updates'):
        for change in report.get(group,[]):
            path=relocated_path(root,root/change['path'])
            relative=str(path.relative_to(root))
            backup(relative)
            write(path,change['data'])
    # Convert global registries to project documents using the same tested runtime adapter.
    from story_builder.services.storage_paths import load_project_documents, save_project_documents
    for relative,tool in [('ace_step/state.json','ace'),('services/editor/state.json','editor')]:
        path=root/relative
        if not path.is_file(): continue
        backup(relative);data=relocate_record_paths(root,load_project_documents(root,json.loads(path.read_text())))
        def project_write(path,value):
            backup(str(path.relative_to(root)));write(path,value)
        registry=save_project_documents(root,data,tool,project_write);write(path,registry)
    state['complete']=True;save()


def rollback(root,journal):
    assert_idle(root)
    state=json.loads((journal/'journal.json').read_text())
    for relative in reversed(state['metadata']):
        shutil.copy2(journal/'metadata'/relative,root/relative)
    for relative in reversed(state['created']): (root/relative).unlink(missing_ok=True)
    for relative in reversed(state['publications']):
        src=journal/'publications'/relative;dest=root/relative
        if src.exists():
            if dest.exists(): raise ValueError('Rollback collision: '+str(dest))
            dest.parent.mkdir(parents=True,exist_ok=True);src.rename(dest)
    for move in reversed(state['moves']):
        src=root/move['new'];dest=root/move['old']
        if src.exists():
            if dest.exists(): raise ValueError('Rollback collision: '+str(dest))
            dest.parent.mkdir(parents=True,exist_ok=True);src.rename(dest)
    state['rolled_back']=True;write(journal/'journal.json',state)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True);p.add_argument('--journal',type=Path)
    action=p.add_mutually_exclusive_group();action.add_argument('--apply',action='store_true');action.add_argument('--rollback',action='store_true')
    args=p.parse_args();root=args.root.resolve()
    if args.rollback:
        if not args.journal: p.error('--rollback requires --journal')
        rollback(root,args.journal.resolve());return
    report=inventory(root)
    journal=args.journal or root/'reports/storage-migration'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    if args.apply: apply(root,report,journal.resolve())
    else: write(journal/'dry-run.json',report)
    print(json.dumps({'apply':args.apply,'journal':str(journal),'moves':len(report['moves']),
        'publications':len(report['publications']),'downloads':len(report['catalogs']['youtube']),
        'job_updates':len(report.get('job_updates',[])),
        'ace_request_updates':len(report.get('ace_request_updates',[]))}))

if __name__=='__main__': main()
