"""Manage only identified trained artifacts, never datasets or shared base weights."""
import hashlib, json, shutil, sqlite3
from pathlib import Path
from urllib.request import urlopen
from . import ace_studio, image_training, video_repertoire as jobs

ACTIVE={'queued','running','cancel_requested','recovery_required'}

def fingerprint(path):
    files=sorted(path.rglob('*')) if path.is_dir() else [path]
    digest=hashlib.sha256();size=0
    for file in files:
        if file.is_symlink(): raise ValueError('Symbolic links are not deletable checkpoints.')
        if not file.is_file(): continue
        digest.update(str(file.relative_to(path) if path.is_dir() else file.name).encode())
        with file.open('rb') as stream:
            while data:=stream.read(1024*1024): digest.update(data);size+=len(data)
    return digest.hexdigest(),size

def catalog(root):
    root=Path(root).resolve();entries=[]
    def add(path,kind,name,**extra):
        path=Path(path)
        if not path.exists() or path.is_symlink(): return
        try: digest,size=fingerprint(path)
        except (ValueError,OSError): return
        entries.append({'id':hashlib.sha256(str(root/'services/music/runs'/path.relative_to(root/'ace_step/runs') if path.is_relative_to(root/'ace_step/runs') else path.resolve()).encode()).hexdigest(),'path':str(path.resolve()),'kind':kind,'name':name,'sha256':digest,'bytes':size,**extra})
    for row in image_training.catalog():
        add(image_training.LORAS/row['id'],'Published Z-Image LoRA',row.get('name',row['id']),sidecar=str((image_training.LORAS/row['id']).with_suffix('.json')))
    for row in image_training.checkpoints():
        add(row['checkpoint'],'Toolkit trained checkpoint',row['name'])
    run_root=root/'ace_step/runs'
    for path in run_root.glob('ace-studio-*/training/lightning_logs/*/checkpoints/*_lora'):
        if path.resolve().is_relative_to(run_root) and (path/'adapter_config.json').is_file(): add(path,'ACE-Step trained LoRA',path.name)
    from .voice_studio import COMFY
    rvc=(COMFY/'models/TTS/RVC').resolve()
    for job in jobs.list_jobs('voice-studio'):
        for raw in (job.get('result') or {}).get('artifact_paths',[]):
            path=Path(raw)
            if path.resolve().is_relative_to(rvc) and path.suffix in {'.pth','.index'}: add(path,'RVC trained artifact',path.name)
    return list({row['id']:row for row in entries}.values())

def assert_idle(root):
    image_training.ensure_idle()
    for kind in jobs.JOB_KINDS:
        if any(job['status'] in ACTIVE for job in jobs.list_jobs(kind)): raise ValueError('Finish or resolve active jobs before deleting trained checkpoints.')
    database=Path(root)/'services/production/image-jobs.sqlite3'
    if database.is_file():
        with sqlite3.connect(database.as_uri()+'?mode=ro',uri=True) as connection:
            if connection.execute("SELECT COUNT(*) FROM production_image_jobs WHERE status IN ('queued','running','submitting','recovery_required')").fetchone()[0]: raise ValueError('An image job may still reference this checkpoint.')
    from .voice_studio import URL
    with urlopen(URL+'/queue',timeout=5) as response: queue=json.load(response)
    if queue.get('queue_running') or queue.get('queue_pending'): raise ValueError('Wait until ComfyUI is idle before deleting checkpoints.')

def delete(root,body):
    if body.get('confirmed') is not True: raise ValueError('Permanent deletion needs explicit confirmation.')
    from .media_jobs import gpu_workload_lock
    with gpu_workload_lock():
        assert_idle(root)
        row=next((r for r in catalog(root) if r['id']==body.get('id') and r['sha256']==body.get('sha256')),None)
        if row is None: raise ValueError('Checkpoint changed or is no longer owned; refresh the list.')
        path=Path(row['path'])
        # Remove references while holding the ACE state lock, preserving datasets and base links.
        with ace_studio.state(root) as data:
            for project in data['projects']:
                removed={a['id'] for a in project.get('adapters',[]) if a.get('path')==str(path)}
                project['adapters']=[a for a in project.get('adapters',[]) if a['id'] not in removed]
                if project.get('settings',{}).get('adapter_id') in removed: project['settings']['adapter_id']=''
            if path.is_dir(): shutil.rmtree(path)
            else: path.unlink()
            if row.get('sidecar'): Path(row['sidecar']).unlink(missing_ok=True)
        audit=Path(root)/'services/trained-artifacts-deleted.json'
        records=json.loads(audit.read_text()) if audit.is_file() else []
        records.append({**row,'deleted':True,'deleted_at':jobs.utc_now()})
        jobs._atomic_json(audit,records)
        for job in jobs.list_jobs('voice-studio'):
            result=job.get('result') or {}
            if str(path) in result.get('artifact_paths',[]):
                result.setdefault('deleted_artifact_paths',[]).append(str(path))
                jobs._atomic_json(jobs.job_path('voice-studio',job['job_id']),{**job,'result':result})
    return {'deleted':row['path'],'checkpoints':catalog(root)}
