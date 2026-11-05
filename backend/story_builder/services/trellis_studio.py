"""Image-to-3D adapter using the shared durable dispatcher and GPU guard."""
from __future__ import annotations
import hashlib, json, os, shutil, struct, subprocess, tempfile, time, uuid
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from . import video_repertoire as jobs
from .media_jobs import submit_and_wait

WORKFLOWS = Path(__file__).resolve().parent.parent / 'workflows/api/three_d'
PRESETS = {'bounded':'TRELLIS2_local_1024_bounded.api.json','detail':'TRELLIS2_local_1536_detail.api.json'}
PARAMS = {'structure_steps':('3','steps',1,100), 'shape_steps':('18','steps',1,100),
 'upsample_steps':('23','steps',1,100),'texture_steps':('12','steps',1,100),
 'structure_cfg':('3','cfg',0,100),'shape_cfg':('18','cfg',0,100),
 'texture_cfg':('12','cfg',0,100),'seed':('3','seed',0,4294967295),
 'faces':('186','target_face_count',1000,1000000)}

def home(root):
    return Path(root) / 'trellis.2'

def layout(root):
    for name in ('input','output','projects','runs','batches','staging'):
        (home(root)/name).mkdir(parents=True,exist_ok=True)

def write(path, value):
    jobs._atomic_json(Path(path),value)

def image_path(root, token):
    if not isinstance(token,str) or len(token)!=32 or any(c not in '0123456789abcdef' for c in token):
        raise ValueError('Invalid image identity.')
    return home(root)/'input'/f'{token}.png'

def upload(root, content):
    from PIL import Image, ImageOps
    import io
    if not content or len(content)>40*1024**2: raise ValueError('Image limit is 40 MiB.')
    image=Image.open(io.BytesIO(content))
    if image.width*image.height>40000000: raise ValueError('Image exceeds 40 megapixels.')
    image.load()
    layout(root); token=uuid.uuid4().hex
    ImageOps.exif_transpose(image).convert('RGBA').save(image_path(root,token))
    return {'id':token,'url':f'/api/trellis/input/{token}'}

def compile_graph(preset, settings, image, prefix):
    if preset not in PRESETS: raise ValueError('Unknown TRELLIS preset.')
    if not isinstance(settings,dict) or set(settings)-set(PARAMS): raise ValueError('Unsupported TRELLIS parameters.')
    graph=json.loads((WORKFLOWS/PRESETS[preset]).read_text())
    for key,value in settings.items():
        node,field,low,high=PARAMS[key]
        if type(value) not in (int,float) or not low<=value<=high or (field in {'steps','seed','target_face_count'} and type(value)!=int):
            raise ValueError(f'Invalid {key}.')
        graph[node]['inputs'][field]=value
    graph['122']['inputs']['image']=image
    graph['322']['inputs']['filename_prefix']=prefix
    return graph

def validate_glb(path):
    with Path(path).open('rb') as stream:
        header=stream.read(12)
        if len(header)!=12: raise ValueError('Truncated GLB header.')
        magic,version,length=struct.unpack('<4sII',header)
        if magic!=b'glTF' or version!=2 or length!=Path(path).stat().st_size: raise ValueError('Invalid GLB header/length.')
        chunk=stream.read(8)
        if len(chunk)!=8: raise ValueError('Truncated GLB scene.')
        size,kind=struct.unpack('<II',chunk)
        if kind!=0x4e4f534a or size>32*1024**2: raise ValueError('Invalid GLB scene.')
        data=json.loads(stream.read(size))
        if not data.get('meshes'): raise ValueError('GLB has no meshes.')
        if any('uri' in entry for group in ('buffers','images') for entry in data.get(group,[])):
            raise ValueError('GLB must embed all textures and buffers.')
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()

def output_folder(root, grant, backend="trellis"):
    if not grant: return (Path(root)/"pixal3d" if backend=="pixal" else home(root))/"output"
    if not isinstance(grant,str) or not grant.isalnum(): raise ValueError('Invalid folder grant.')
    record=json.loads((home(root)/'projects'/f'folder-{grant}.json').read_text())
    path=Path(record['path'])
    if not path.is_dir() or path.resolve()!=path: raise ValueError('Output folder changed; choose it again.')
    return path

def choose_folder(root):
    layout(root)
    result=subprocess.run(['zenity','--file-selection','--directory','--title=Choose 3D output folder'],capture_output=True,text=True,timeout=120)
    if result.returncode: raise ValueError('Folder selection cancelled or unavailable. Enter an existing absolute output path instead.')
    return grant_folder(root,result.stdout.strip())

def grant_folder(root, value):
    path=Path(str(value)).expanduser()
    if not path.is_absolute() or not path.is_dir(): raise ValueError('Choose an existing absolute output folder.')
    layout(root); token=uuid.uuid4().hex
    write(home(root)/'projects'/f'folder-{token}.json',{'path':str(path.resolve())})
    return {'grant':token,'path':str(path.resolve())}

def create(root, body):
    layout(root)
    workspace=body.get('workspace_id') or 'tool-library'
    from .storage_paths import project_root
    project_root(root,workspace)
    if body.get('mode','single') not in {'single','batch'}: raise ValueError('Invalid 3D mode.')
    items=body.get('items'); preset=body.get('preset','bounded'); settings=body.get('settings',{})
    if not isinstance(items,list) or not 1<=len(items)<=500 or (body.get('mode','single')=='single' and len(items)!=1): raise ValueError('Select 1–500 images.')
    from . import multiview_3d as multi
    backend=body.get('backend','trellis'); input_mode=body.get('input_mode','single')
    if backend not in {'trellis','pixal'} or input_mode not in {'single','multiview'}: raise ValueError('Invalid 3D backend/input mode.')
    if backend=='pixal' and input_mode!='multiview':raise ValueError('Pixal3D requires multiple labelled views.')
    profile=body.get('view_profile','two')
    if profile not in multi.VIEWS:raise ValueError('Choose two or four views.')
    if input_mode=='multiview' and body.get('views_confirmed') is not True:raise ValueError('Review and confirm the view assignments first.')
    frozen=[]
    if any(not isinstance(item,dict) for item in items): raise ValueError('Invalid image selection.')
    if any(not isinstance(item.get('id'),str) for item in items): raise ValueError('Invalid image identity.')
    if len({item.get('id') for item in items})!=len(items): raise ValueError('Choose distinct images.')
    for index,item in enumerate(items):
        path=image_path(root,item.get('id'))
        if not path.is_file(): raise ValueError('Input image is missing.')
        row={'id':item['id'],'name':str(item.get('name','Image'))[:200],'status':'queued','index':index+1}
        if input_mode=='multiview':
            views=item.get('views')
            if not isinstance(views,dict) or set(views)!=set(multi.VIEWS[profile]) or len(set(views.values()))!=len(views):raise ValueError('Every view needs a distinct, labelled image.')
            for token in views.values():
                if not image_path(root,token).is_file():raise ValueError('Missing view image.')
            row['views']=views
            row['hashes']={v:hashlib.sha256(image_path(root,t).read_bytes()).hexdigest() for v,t in views.items()}
            # Validate matching canvases without modifying any input.
            from PIL import Image
            sizes=[]
            for token in views.values():
                with Image.open(image_path(root,token)) as im:sizes.append(im.size)
            if len(set(sizes))!=1:raise ValueError('Views must have matching canvas dimensions; pad/align them first.')
        frozen.append(row)
    if input_mode=='single':compile_graph(preset,settings,'validation.png','validation')
    elif backend=='pixal':multi.pixal_graph(profile,settings,{v:'validation.png' for v in multi.VIEWS[profile]},'validation')
    else:multi.remote_settings(preset,settings)
    output_folder(root,body.get('output_grant'),backend)
    job=jobs.create_job('trellis',{'workspace_id':workspace,'preset':preset,'settings':settings,'items':frozen,'output_grant':body.get('output_grant'),'mode':body.get('mode','single'),'backend':backend,'input_mode':input_mode,'view_profile':profile})
    write(home(root)/'batches'/f"{job['job_id']}.json",{'items':frozen})
    return jobs.start_job('trellis',job['job_id'])

def result_path(root, job_id, index):
    job=jobs.read_job('trellis',job_id)
    manifest=json.loads((home(root)/'batches'/f'{job_id}.json').read_text())
    row=next((r for r in manifest['items'] if r['index']==int(index) and r['status']=='completed'),None)
    if not row: raise ValueError('No validated result for this item.')
    try:
        path=output_folder(root,job['request'].get('output_grant'),job['request'].get('backend','trellis'))/job_id/f'{int(index):04d}.glb'
    except (ValueError, FileNotFoundError):
        path=home(root)/'saved-results'/job_id/f'{int(index):04d}.glb'
    if not path.exists():
        path=home(root)/'saved-results'/job_id/f'{int(index):04d}.glb'
    if validate_glb(path)!=row['sha256']: raise ValueError('Result changed on disk.')
    return path

def validate_graph(graph, info):
    """Flatten selected Comfy dynamic-combo inputs before validating the saved graph."""
    for node in graph.values():
        kind=node['class_type']
        if kind not in info: raise ValueError('Missing ComfyUI node: '+kind)
        schema=info[kind].get('input',{})
        fields={**schema.get('required',{}),**schema.get('optional',{})}
        for key,spec in list(fields.items()):
            if spec[0]=='COMFY_DYNAMICCOMBO_V3':
                options=spec[1].get('options',[])
                selected=next((row for row in options if row['key']==node['inputs'].get(key)),None)
                if not selected: raise ValueError(f'Invalid {kind}.{key} selection.')
                for group in ('required','optional'):
                    fields.update({key+'.'+name:value for name,value in selected.get('inputs',{}).get(group,{}).items()})
        for key,value in node['inputs'].items():
            if key not in fields: raise ValueError(f'Installed {kind} no longer accepts {key}.')
            spec=fields[key];choices=spec[0]
            if kind=='LoadImage' and key=='image': continue  # staged after preflight
            if isinstance(choices,list) and isinstance(value,str) and value not in choices:
                raise ValueError(f'Unavailable {kind}.{key}: {value}')
            bounds=spec[1] if len(spec)>1 and isinstance(spec[1],dict) else {}
            if type(value) in (int,float):
                if ('min' in bounds and value<bounds['min']) or ('max' in bounds and value>bounds['max']):
                    raise ValueError(f'{kind}.{key} exceeds the installed node limits.')

def run_job(root, job_id, request, progress):
    from .image_training import ensure_idle
    ensure_idle()
    from . import multiview_3d as multi
    backend=request.get('backend','trellis'); remote=request.get('input_mode')=='multiview' and backend=='trellis'
    layout(root); manifest_path=home(root)/'batches'/f'{job_id}.json'
    state=json.loads(manifest_path.read_text()); url=os.environ.get('COMFYUI_URL','http://127.0.0.1:3008').rstrip('/')
    if not remote:
        multi.release_service_if_idle()
        with urlopen(url+'/object_info',timeout=30) as response: info=json.load(response)
    for row in state['items']:
        if jobs.read_job('trellis',job_id).get('stop_after_current'):
            return {**state,'job_status':'cancelled'}
        if jobs.read_job('trellis',job_id)['status'] in {'cancelled','cancel_requested'}: raise KeyboardInterrupt()
        if row['status']=='completed':
            result_path(root,job_id,row['index']); continue
        run=home(root)/'runs'/job_id/str(row['index']); run.mkdir(parents=True,exist_ok=True)
        if row.get('views'):
            for view,token in row['views'].items():
                if hashlib.sha256(image_path(root,token).read_bytes()).hexdigest()!=row['hashes'][view]:raise ValueError('Input view changed; select it again.')
        if remote:
            row.setdefault('started_at',time.time());row['status']='running';write(manifest_path,state)
            progress('rendering',f"Refining object {row['index']}/{len(state['items'])}; TRELLIS multi-view",int((row['index']-1)/len(state['items'])*100))
            try: temporary=multi.remote_render(root,job_id,row,request,run,progress)
            except Exception as exc:
                row['status']='recovery_required';write(manifest_path,state)
                return {'job_status':'recovery_required','error':str(exc),'items':state['items']}
            _publish(root,job_id,row,request,temporary,run,state,manifest_path)
            continue
        if backend=='pixal':
            prepared=multi.prepare_views(root,row['views'],run)
            images={v:f"vibe_trellis/{job_id}/{row['index']}-{v}.png" for v in prepared}
            graph=multi.pixal_graph(request['view_profile'],request['settings'],images,f"3d/vibe/{job_id}/{row['index']}")
        else:graph=compile_graph(request['preset'],request['settings'],f"vibe_trellis/{job_id}/{row['index']}.png",f"3d/vibe/{job_id}/{row['index']}")
        validate_graph(graph,info)
        prompt=row.get('prompt_id')
        if row['status']=='failed':
            row.pop('prompt_id',None); prompt=None
        if prompt:
            try:
                with urlopen(url+'/history/'+prompt,timeout=30) as response: saved=json.load(response)
            except (OSError,ValueError):
                return {'job_status':'recovery_required','error':'Could not reconcile the owned prompt; no duplicate was submitted.','items':state['items']}
            history=saved.get(prompt)
            if not history:
                return {'job_status':'recovery_required','error':'An owned prompt has no history yet. Resume after ComfyUI settles; no duplicate was submitted.','items':state['items']}
        else:
            # Shared input mount; use the same runtime as existing image/audio adapters.
            comfy=Path(os.environ.get('COMFYUI_ROOT','/home/riki/web_dev/setup_comfy_and-stuff/ComfyUI'))
            staged=comfy/'input/vibe_trellis'/f"{job_id}/{row['index']}.png"; staged.parent.mkdir(parents=True,exist_ok=True)
            import shutil
            if backend=='pixal':
                for view,path in prepared.items():shutil.copyfile(path,staged.with_name(f"{row['index']}-{view}.png"))
            else:shutil.copyfile(image_path(root,row['id']),staged)
            prompt=str(uuid.uuid4()); row.update(status='running',prompt_id=prompt,started_at=time.time()); write(manifest_path,state)
            write(run/'workflow.json',graph)
            progress('rendering',f"Generating {row['index']}/{len(state['items'])}: {row['name']}",int((row['index']-1)/len(state['items'])*100))
            try:
                _,history=submit_and_wait(graph,comfy_url=url,timeout_seconds=14400,prompt_id=prompt,workload_id=job_id)
            except Exception as exc:
                row['status']='recovery_required' if getattr(exc,'remote_state_unknown',False) else 'failed'; write(manifest_path,state)
                if row['status']=='failed': raise
                return {'job_status':'recovery_required','error':str(exc),'items':state['items']}
        if history.get('status',{}).get('status_str')=='error':
            row['status']='failed';write(manifest_path,state)
            raise ValueError('Owned TRELLIS prompt failed in ComfyUI. Inspect the job before retrying.')
        if not history.get('status',{}).get('completed'):
            return {'job_status':'recovery_required','error':'Owned TRELLIS prompt is not completed; no duplicate submitted.','items':state['items']}
        descriptors=history.get('outputs',{}).get('372' if backend=='pixal' else '322',{}).get('3d',[])
        if not descriptors:
            row['status']='failed'; write(manifest_path,state)
            raise ValueError('TRELLIS finished without a saved GLB. Retry failed starts a new owned job for this item.')
        desc=descriptors[0]
        if Path(desc.get('filename','')).suffix.lower()!='.glb' or desc.get('type')!='output': raise ValueError('Unexpected 3D descriptor.')
        query=urlencode({k:desc.get(k,'') for k in ('filename','subfolder','type')})
        folder=output_folder(root,request.get('output_grant'),request.get('backend','trellis'))/job_id; folder.mkdir(parents=True,exist_ok=True)
        target=folder/f"{row['index']:04d}.glb"; temporary=run/'collecting.glb'
        with urlopen(url+'/view?'+query,timeout=180) as response,temporary.open('wb') as stream:
            import shutil
            shutil.copyfileobj(response,stream)
        _publish(root,job_id,row,request,temporary,run,state,manifest_path)
        digest=row['sha256'];target=Path(row['path'])
        comfy=Path(os.environ.get('COMFYUI_ROOT','/home/riki/web_dev/setup_comfy_and-stuff/ComfyUI'))
        (comfy/'input/vibe_trellis'/job_id/f"{row['index']}.png").unlink(missing_ok=True)
        if backend=='pixal':
            for view in multi.VIEWS[request['view_profile']]:
                (comfy/'input/vibe_trellis'/job_id/f"{row['index']}-{view}.png").unlink(missing_ok=True)
        # Remove only this owned, hash-identical Comfy staging result.
        owned=(comfy/'output/3d/vibe'/job_id).resolve()
        source=(comfy/'output'/desc.get('subfolder','')/desc['filename']).resolve()
        try:
            if source.is_relative_to(owned) and source!=target.resolve() and source.is_file() and validate_glb(source)==digest:
                source.unlink()
        except (OSError,ValueError) as exc:
            row['cleanup_warning']=str(exc);write(manifest_path,state)
        progress('validated',f"Validated {row['index']}/{len(state['items'])}",int(row['index']/len(state['items'])*100))
    return state

def _publish(root,job_id,row,request,temporary,run,state,manifest_path):
    folder=output_folder(root,request.get('output_grant'),request.get('backend','trellis'))/job_id;folder.mkdir(parents=True,exist_ok=True)
    target=folder/f"{row['index']:04d}.glb"
    digest=validate_glb(temporary)
    import shutil
    pending=None
    try:
        with tempfile.NamedTemporaryFile(dir=folder,delete=False) as stream:
            pending=Path(stream.name)
            with temporary.open('rb') as source: shutil.copyfileobj(source,stream)
        os.replace(pending,target); temporary.unlink()
    finally:
        if pending: pending.unlink(missing_ok=True)
    row.update(status='completed',sha256=digest,path=str(target),elapsed_seconds=round(time.time()-row.get('started_at',time.time()),2));write(manifest_path,state)

def open_blender(root,job_id,index):
    job=jobs.read_job('trellis',job_id)
    if job['request'].get('mode','single')!='single' or len(job['request']['items'])!=1: raise ValueError('Open with Blender is Single-only.')
    path=result_path(root,job_id,index); script=home(root)/'runs'/job_id/'open_blender.py'
    script.write_text('import bpy\nbpy.ops.object.select_all(action="SELECT")\nbpy.ops.object.delete(use_global=False)\nbpy.ops.import_scene.gltf(filepath='+repr(str(path))+')\n')
    executable = os.environ.get('BLENDER_EXECUTABLE') or shutil.which('blender')
    if not executable:
        candidates = sorted((Path.home()/'Applications').glob('Blender-*.AppImage'),
                            key=lambda p: p.stat().st_mtime, reverse=True)
        executable = next((str(p) for p in candidates if os.access(p, os.X_OK)), None)
    if not executable:
        raise ValueError('Blender was not found. Install Blender or set BLENDER_EXECUTABLE to its executable path.')
    env = os.environ.copy()
    if executable.endswith('.AppImage'):
        env['APPIMAGE_EXTRACT_AND_RUN'] = '1'
    log = script.with_suffix('.log')
    with log.open('ab') as output:
        process = subprocess.Popen([executable,'--python',str(script)],env=env,
                                   stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
    try:
        code = process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        return {'opened':True,'pid':process.pid}
    raise ValueError(f'Blender exited during startup (code {code}). See {log}')
