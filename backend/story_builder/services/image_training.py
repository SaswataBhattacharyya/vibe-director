"""Fixed existing Toolkit launcher and provenance-checked Turbo LoRA catalog."""
import fcntl, hashlib, json, os, shutil, sqlite3, subprocess, time, uuid
from pathlib import Path
from urllib.request import urlopen
SETUP=Path(os.environ.get('VIBE_COMFY_SETUP','/home/riki/web_dev/setup_comfy_and-stuff'))
URL='http://127.0.0.1:8675'
LORAS=SETUP/'ComfyUI/models/loras'
OUTPUT=SETUP/'env_setup/zimage_training/output'

def health():
    try:
        with urlopen(URL+'/api/queue',timeout=3) as r: queues=json.load(r)['queues']
        with urlopen(URL+'/api/jobs',timeout=3) as r: jobs=json.load(r)['jobs']
        return {'ready':True,'url':URL,'queues':queues,'active':any(q.get('is_running') for q in queues) or any(str(j.get('status','')).lower() in {'running','training','queued'} for j in jobs)}
    except (OSError,ValueError,KeyError): return {'ready':False,'url':URL,'active':False}

def ensure_idle():
    state=health()
    if state['active']:
        raise ValueError('AI Toolkit has an active training queue. Stop its queue before starting a ComfyUI workload.')
    # Also inspect stopped-service state: launching the UI must not revive a queue.
    database=SETUP/'env_setup/zimage_training/ai-toolkit/aitk_db.db'
    if database.is_file() and not state['ready']:
        try:
            with sqlite3.connect(database.as_uri()+'?mode=ro',uri=True,timeout=3) as connection:
                active=connection.execute('SELECT COUNT(*) FROM Queue WHERE is_running = 1').fetchone()[0]
            if active: raise ValueError('AI Toolkit saved an active queue. Open its existing container manually and stop the queue before using the automatic launcher.')
        except sqlite3.Error as exc:
            raise ValueError('Could not verify that the saved AI Toolkit queues are stopped.') from exc


def launch(root):
    folder=Path(root)/'services/image_training';folder.mkdir(parents=True,exist_ok=True)
    with (folder/'launch.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if health()['ready']: return health()
        ensure_idle()
        # No build, installation, queue/start API or preset mutations.
        subprocess.run(['docker','compose','-f','docker-compose.yml','-f','docker-compose.training.yml','--profile','training','up','-d','--no-build','zimage-training'],cwd=SETUP,check=True,capture_output=True,text=True,timeout=120)
        end=time.monotonic()+90
        while time.monotonic()<end:
            state=health()
            if state['ready']: return state
            time.sleep(2)
        raise ValueError('AI Toolkit did not become ready. Check the existing zimage-training container log and Retry.')

def checked(path, metadata):
    if path.suffix!='.safetensors' or not path.is_file(): raise ValueError('Choose a safetensors checkpoint.')
    if metadata.get('base_model_variant')!='z-image-turbo' or metadata.get('training_type') not in {'character','world'}:
        raise ValueError('Verified z-image-turbo character/world provenance is required; unknown or Base LoRAs cannot be used.')
    with path.open('rb') as stream:
        size=int.from_bytes(stream.read(8),'little')
        if not 0<size<16*1024**2: raise ValueError('Invalid safetensors header.')
        header=json.loads(stream.read(size))
    if not any('lora_' in key.lower() for key in header): raise ValueError('No LoRA tensors found.')
    with path.open('rb') as stream: digest=hashlib.file_digest(stream,'sha256').hexdigest()
    if digest!=metadata.get('sha256'): raise ValueError('Checkpoint hash differs from its provenance.')
    return digest

def catalog():
    rows=[]
    for sidecar in (LORAS/'zimage').glob('*.json'):
        try:
            metadata=json.loads(sidecar.read_text()); path=(LORAS/metadata['checkpoint_path']).resolve()
            if not path.is_relative_to((LORAS/'zimage').resolve()): continue
            checked(path,metadata);rows.append({**metadata,'id':path.relative_to(LORAS).as_posix()})
        except (OSError,ValueError,KeyError): continue
    return rows

def selection(value):
    if not value: return None
    row=next((r for r in catalog() if r['id']==value.get('id') and r['sha256']==value.get('sha256')),None)
    if row is None: raise ValueError('LoRA missing, incompatible or changed; refresh the catalog.')
    strength=value.get('strength',1)
    if type(strength) not in (int,float) or not -2<=strength<=2: raise ValueError('LoRA strength must be -2 to 2.')
    return {'id':row['id'],'sha256':row['sha256'],'strength':strength,'trigger_word':row.get('trigger_word','')}

def checkpoints():
    """Read existing Toolkit job configurations; never create or queue jobs."""
    database=SETUP/'env_setup/zimage_training/ai-toolkit/aitk_db.db'
    if not database.is_file(): return []
    with sqlite3.connect(database.as_uri()+'?mode=ro',uri=True,timeout=3) as connection:
        saved=connection.execute('SELECT id,name,status,job_config FROM Job').fetchall()
    rows=[]
    for identity,name,status,raw in saved:
        try:
            config=json.loads(raw); process=config['config']['process'][0]
            category=config.get('meta',{}).get('training_type')
            if process.get('model',{}).get('arch')!='zimage:turbo' or process.get('network',{}).get('type')!='lora' or category not in {'character','world'}: continue
            if status.lower() in {'running','training','queued'}: continue
            folder=(OUTPUT/config['config']['name']).resolve()
            if not folder.is_relative_to(OUTPUT.resolve()): continue
            for path in folder.rglob('*.safetensors'):
                if not path.resolve().is_relative_to(folder): continue
                metadata={'base_model_variant':'z-image-turbo','training_type':category,'name':name,
                    'trigger_word':process.get('trigger_word',''),'toolkit_job_id':identity,
                    'config_sha256':hashlib.sha256(raw.encode()).hexdigest(),'original_path':str(path.resolve())}
                with path.open('rb') as stream: metadata['sha256']=hashlib.file_digest(stream,'sha256').hexdigest()
                checked(path,metadata)
                rows.append({**metadata,'checkpoint':str(path.resolve()),'bytes':path.stat().st_size})
        except (ValueError,KeyError,TypeError,OSError): continue
    return rows

# Publication is explicit and based on an installed trainer's real saved job.
def publish(body):
    ensure_idle()
    metadata=next((row for row in checkpoints() if row['checkpoint']==body.get('checkpoint') and row['sha256']==body.get('sha256')),None)
    if metadata is None: raise ValueError('Choose an unchanged checkpoint from the refreshed Toolkit list.')
    source=Path(metadata['checkpoint']);digest=checked(source,metadata)
    destination=LORAS/'zimage'/f'{digest}.safetensors';destination.parent.mkdir(parents=True,exist_ok=True)
    temporary=destination.with_name('.'+uuid.uuid4().hex+'.safetensors')
    try:
        with temporary.open('xb') as stream,source.open('rb') as incoming: shutil.copyfileobj(incoming,stream)
        checked(temporary,metadata);os.replace(temporary,destination)
    finally: temporary.unlink(missing_ok=True)
    metadata.update(checkpoint_path=destination.relative_to(LORAS).as_posix())
    from .video_repertoire import _atomic_json
    _atomic_json(destination.with_suffix('.json'),metadata)
    return {'loras':catalog()}
