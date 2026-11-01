"""Small adapters for the prepared Pixal graphs and isolated TRELLIS service."""
import fcntl, json, os, subprocess, time
from pathlib import Path
from urllib.request import urlopen
from . import trellis_studio as studio

SETUP = Path(os.environ.get('VIBE_COMFY_SETUP','/home/riki/web_dev/setup_comfy_and-stuff'))
URL = 'http://127.0.0.1:52070'
FILES = studio.WORKFLOWS/'multiview'
VIEWS = {'two':('front','back'), 'four':('front','left','back','right')}
REMOTE_PARAMS = {
 'seed':(0,4294967295,int),'ss_guidance_strength':(0,20,float),'ss_sampling_steps':(1,100,int),
 'slat_guidance_strength':(0,20,float),'slat_sampling_steps':(1,100,int),
 'blend_temperature':(.1,10,float),'texture_size':(512,2048,int),'decimation_target':(1000,1000000,int),
}

def health():
    try:
        with urlopen(URL+'/health',timeout=3) as r: result=json.load(r)
        return {**result,'ready':result.get('status')=='ok'}
    except (OSError,ValueError): return {'ready':False,'gpu_busy':False}

def ensure_ready(root):
    folder=studio.home(root)/'runs';folder.mkdir(parents=True,exist_ok=True)
    with (folder/'service.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if health()['ready']: return health()
        subprocess.run(['bash',str(SETUP/'env_setup/trellis2_multiview/scripts/service.sh'),'start'],cwd=SETUP,check=True,capture_output=True,text=True,timeout=120)
        end=time.monotonic()+90
        while time.monotonic()<end:
            state=health()
            if state['ready']: return state
            time.sleep(2)
        raise ValueError('TRELLIS service did not become ready. Retry connection; no render was submitted.')

def release_service_if_idle():
    state=health()
    if not state['ready']: return
    if state.get('gpu_busy'): raise ValueError('TRELLIS multi-view is still processing. Wait before changing backends.')
    if state.get('model_loaded') or state.get('cuda_initialized'):
        subprocess.run(['bash',str(SETUP/'env_setup/trellis2_multiview/scripts/service.sh'),'stop'],cwd=SETUP,check=True,capture_output=True,text=True,timeout=90)
        if health()['ready']: raise ValueError('TRELLIS memory release could not be confirmed.')

def remote_settings(preset, values):
    names={'mv512':'front_back_512.json','mvcascade':'front_back_1024.json','mv1024':'front_back_1024_direct.json'}
    if preset not in names: raise ValueError('Unknown multi-view preset.')
    result=json.loads((FILES/'trellis2_multiview/config'/names[preset]).read_text())
    if not isinstance(values,dict) or set(values)-set(REMOTE_PARAMS): raise ValueError('Unsupported multi-view parameter.')
    for key,value in values.items():
        low,high,kind=REMOTE_PARAMS[key]
        if type(value) not in (int,float) or not low<=value<=high or (kind is int and type(value) is not int): raise ValueError('Invalid '+key)
        result[key]=value
    if result['texture_size'] not in (512,1024,2048): raise ValueError('Texture size must be 512, 1024 or 2048.')
    return result

def pixal_graph(profile, settings, images, prefix):
    name='front_back' if profile=='two' else 'four_views' if profile=='four' else None
    if not name: raise ValueError('Choose two or four labelled views.')
    graph=json.loads((FILES/'pixal3d_multiview'/f'Pixal3D_MV_{name}_bounded.api.json').read_text())
    if not isinstance(settings,dict) or set(settings)-{'seed','fov','faces'}: raise ValueError('Unsupported Pixal parameter.')
    bounds={'seed':(0,4294967295),'fov':(10,60),'faces':(1000,1000000)}
    for key,value in settings.items():
        low,high=bounds[key]
        if type(value) not in (int,float) or not low<=value<=high or (key!='fov' and type(value) is not int): raise ValueError('Invalid '+key)
        if key=='seed':
            for node in ('3','12','18','23'):graph[node]['inputs']['seed']=value
        else:
            node,field=('324','fov') if key=='fov' else ('186','target_face_count')
            graph[node]['inputs'][field]=value
    for index,view in enumerate(VIEWS[profile]):graph[str(400+index)]['inputs']['image']=images[view]
    graph['372']['inputs']['filename_prefix']=prefix
    return graph

def prepare_views(root, views, run):
    """Keep relative canvas scale: common square padding, never per-subject auto crop."""
    from PIL import Image
    paths={name:studio.image_path(root,token) for name,token in views.items()}
    sizes=[]
    for path in paths.values():
        with Image.open(path) as im:sizes.append(im.size)
    if len(set(sizes))!=1: raise ValueError('Views must have matching canvas dimensions. Pad/align the images before submitting.')
    size=max(sizes[0]);result={}
    for view,path in paths.items():
        with Image.open(path) as im:
            im=im.convert('RGBA');canvas=Image.new('RGBA',(size,size),(0,0,0,255))
            canvas.alpha_composite(im,((size-im.width)//2,(size-im.height)//2))
            target=run/f'{view}.png';canvas.convert('RGB').save(target);result[view]=target
    return result

def remote_render(root, job_id, row, request, run, progress):
    """Persist submission intent before POST. An uncertain POST is never repeated."""
    import requests
    from . import media_jobs
    from contextlib import ExitStack
    marker=run/'remote-request.json';receipt=run/'remote-response.json'
    if not receipt.exists() and marker.exists():
        raise ValueError('TRELLIS submission is uncertain. It will not be sent again. Wait for the service to finish, then recover using its request ID.')
    if not receipt.exists():
        ensure_ready(root)
        with media_jobs.gpu_workload_guard(comfy_url=os.environ.get('COMFYUI_URL','http://127.0.0.1:3008')):
            state=health()
            if state.get('gpu_busy'):raise ValueError('TRELLIS service is busy; no request submitted.')
            released=media_jobs.release_comfyui_models_if_idle(comfy_url=os.environ.get('COMFYUI_URL','http://127.0.0.1:3008'),wait_for_memory_release=True)
            if released.get('status')!='memory_release_observed':raise ValueError('Comfy model release is not confirmed: '+str(released))
            views=prepare_views(root,row['views'],run)
            studio.write(marker,{'job_id':job_id,'item':row['index'],'state':'submission_started','settings':remote_settings(request['preset'],request['settings'])})
            # A durable hold survives worker death; clear only this exact hold after verified idle.
            owner=f'trellis-multiview:{job_id}:{row["index"]}'
            media_jobs._set_gpu_safety_hold('TRELLIS multi-view request may be running; reconcile before another workload.',owner)
            try:
                with ExitStack() as stack:
                    files={v:(p.name,stack.enter_context(p.open('rb')),'image/png') for v,p in views.items()}
                    response=requests.post(URL+'/generate-multiview',files=files,data=remote_settings(request['preset'],request['settings']),timeout=(10,14400))
                    response.raise_for_status();data=response.json()
                studio.write(receipt,data)
            except BaseException:
                # Timeout is not cancellation. The durable hold deliberately remains.
                raise
    ensure_ready(root)
    data=json.loads(receipt.read_text());identity=data.get('request_id','')
    import uuid
    if str(uuid.UUID(identity))!=identity: raise ValueError('Invalid service request identity.')
    expected=f'/download/{identity}/output.glb'
    if data.get('glb_url')!=expected: raise ValueError('Unexpected service GLB URL.')
    target=run/'collecting.glb'
    with urlopen(URL+expected,timeout=180) as response,target.open('wb') as stream:
        import shutil
        shutil.copyfileobj(response,stream)
    studio.validate_glb(target)
    release_service_if_idle()
    owner=f'trellis-multiview:{job_id}:{row["index"]}'
    if media_jobs.get_gpu_safety_hold().get('workload_id')==owner:
        media_jobs._gpu_safety_hold_path().unlink(missing_ok=True)
    return target

def reconcile(root, job_id, request_id=None, index=1):
    """Explicit recovery; no generation request is sent from this operation."""
    import uuid
    from . import media_jobs
    job=studio.jobs.read_job('trellis',job_id)
    if job['status'] not in {'recovery_required','interrupted','failed','cancelled'}:raise ValueError('This job does not need recovery.')
    if job['request'].get('backend')!='trellis' or job['request'].get('input_mode')!='multiview':raise ValueError('Not a TRELLIS multi-view job.')
    if type(index) is not int or not 1<=index<=len(job['request']['items']):raise ValueError('Invalid object number.')
    run=studio.home(root)/'runs'/job_id/str(index);receipt=run/'remote-response.json'
    if request_id and not (run/'remote-request.json').exists():raise ValueError('This object has no submitted request to recover.')
    ensure_ready(root)
    state=health()
    if not state.get('ready') or state.get('gpu_busy'):raise ValueError('Wait until TRELLIS is reachable and idle before reconciling.')
    if request_id:
        identity=str(uuid.UUID(str(request_id)))
        target=run/'recovery.glb'
        with urlopen(URL+f'/download/{identity}/output.glb',timeout=180) as source,target.open('wb') as stream:
            import shutil
            shutil.copyfileobj(source,stream)
        studio.validate_glb(target)
        studio.write(receipt,{'request_id':identity,'glb_url':f'/download/{identity}/output.glb','manually_recovered':True})
    uncertain=list((studio.home(root)/'runs'/job_id).glob('*/remote-request.json'))
    if any(not p.with_name('remote-response.json').exists() for p in uncertain):
        raise ValueError('The reply was lost. Recover the completed result with its request ID from the TRELLIS service log; no generation will be repeated.')
    release_service_if_idle()
    hold=media_jobs.get_gpu_safety_hold()
    if hold.get('termination_unknown'):
        if not str(hold.get('workload_id','')).startswith(f'trellis-multiview:{job_id}:'):raise ValueError('Another workload owns the GPU safety hold.')
        media_jobs.clear_gpu_safety_hold(verified_idle=True)
    return {'reconciled':True}
