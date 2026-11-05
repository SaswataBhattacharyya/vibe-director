"""Explicit local studio actions; no generic command execution surface."""
import json, re
from urllib.parse import parse_qs
from pathlib import Path
from . import trellis_studio as trellis, image_training, video_repertoire as jobs, voice_studio, studio_checkpoints

def handle(root,environ,start_response,read_json,respond):
    method=environ.get('REQUEST_METHOD','GET');path=environ.get('PATH_INFO','')
    if path=='/api/trellis/upload' and method=='POST':
        size=int(environ.get('CONTENT_LENGTH') or 0)
        if not 0<size<=40*1024**2: raise ValueError('Image limit is 40 MiB.')
        return respond(start_response,'200 OK',trellis.upload(root,environ['wsgi.input'].read(size)))
    body=read_json(environ) if method=='POST' else {}
    result=None
    if path=='/api/studio-tools/output-folder' and method=='POST':
        from . import output_destinations
        result=output_destinations.grant(root,body.get('path'))
    elif path=='/api/studio-tools/output-destination' and method=='POST':
        from . import output_destinations
        result=output_destinations.preference(root,body.get('tool'),body.get('workspace_id') or 'tool-library',body.get('choice'),allow_unavailable=body.get('choice') is None)
    elif path=='/api/studio-tools/output-relink' and method=='POST':
        from . import output_destinations
        result=output_destinations.locate_saved_folder(root,body.get('tool'),body.get('workspace_id') or 'tool-library',body.get('grant'))
    elif path=='/api/studio-tools/checkpoints' and method=='GET': result={'checkpoints':studio_checkpoints.catalog(root)}
    elif path=='/api/studio-tools/checkpoints/delete' and method=='POST': result=studio_checkpoints.delete(root,body)
    elif path=='/api/studio-tools/voice/capabilities' and method=='GET': result=voice_studio.capabilities()
    elif path=='/api/studio-tools/voice/jobs' and method=='GET': result={'jobs':jobs.list_jobs('voice-studio')[:30]}
    elif path=='/api/studio-tools/voice/jobs' and method=='POST': result=voice_studio.create(root,body)
    elif match:=re.fullmatch(r'/api/studio-tools/voice/jobs/(voice-studio-[a-f0-9]{12})(?:/(cancel|resume))?',path):
        identity,action=match.groups()
        if method=='POST' and action=='cancel': result=jobs.cancel_job('voice-studio',identity)
        elif method=='POST' and action=='resume':
            job=jobs.read_job('voice-studio',identity)
            if job['status'] not in {'recovery_required','interrupted'}: raise ValueError('Only an interrupted or uncertain job can be reconciled.')
            job['status']='interrupted';jobs._atomic_json(jobs.job_path('voice-studio',identity),job)
            result=jobs.start_job('voice-studio',identity)
        elif method=='GET' and not action: result=voice_studio.progress(identity)
        else: raise ValueError('Unsupported voice action.')
    elif path=='/api/studio-tools/training' and method=='GET': result=image_training.health()
    elif path=='/api/studio-tools/training/launch' and method=='POST': result=image_training.launch(root)
    elif path=='/api/studio-tools/loras' and method=='GET': result={'loras':image_training.catalog()}
    elif path=='/api/studio-tools/loras/checkpoints' and method=='GET': result={'checkpoints':image_training.checkpoints()}
    elif path=='/api/studio-tools/loras/publish' and method=='POST': result=image_training.publish(body)
    elif path=='/api/trellis/service' and method=='POST':
        from . import multiview_3d
        result=multiview_3d.ensure_ready(root)
    elif path=='/api/trellis/state' and method=='GET':
        from . import multiview_3d
        backend=parse_qs(environ.get('QUERY_STRING','')).get('backend',['trellis'])[0]
        if backend not in {'trellis','pixal'}:raise ValueError('Invalid backend.')
        workspace=parse_qs(environ.get('QUERY_STRING','')).get('workspace_id',[None])[0]
        result={'input':str(trellis.home(root)/'input'),'output':str(trellis.output_folder(root,None,backend)),
                'service':multiview_3d.health(),
                'jobs':[j for j in jobs.list_jobs('trellis') if j.get('request',{}).get('backend','trellis')==backend and (not workspace or j.get('request',{}).get('workspace_id','tool-library')==workspace)][:30]}

    elif path=='/api/trellis/output-folder' and method=='POST':
        result=trellis.grant_folder(root,body['path']) if body.get('path') else trellis.choose_folder(root)
    elif path=='/api/trellis/jobs' and method=='POST': result=trellis.create(root,body)
    elif match:=re.fullmatch(r'/api/trellis/input/([a-f0-9]{32})',path):
        if method!='GET': raise ValueError('Use GET.')
        data=trellis.image_path(root,match[1]).read_bytes()
        start_response('200 OK',[('Content-Type','image/png'),('Content-Length',str(len(data)))]);return [data]
    elif match:=re.fullmatch(r'/api/trellis/jobs/(trellis-[a-f0-9]{12})(?:/(cancel|resume|recover|blender|model|folder)(?:/(\d+))?)?',path):
        job_id,action,index=match.groups()
        if not action and method=='GET':
            result=jobs.read_job('trellis',job_id)
            manifest=trellis.home(root)/'batches'/f'{job_id}.json'
            result['items']=json.loads(manifest.read_text())['items']
        elif method=='POST' and action=='cancel':
            job=jobs.read_job('trellis',job_id)
            if job['request'].get('input_mode')=='multiview' and job['request'].get('backend')=='trellis' and job['status']=='running':
                job.update(stop_after_current=True,message='Will stop after the current object; remote rendering continues.')
                jobs._atomic_json(jobs.job_path('trellis',job_id),job);result=job
            else:result=jobs.cancel_job('trellis',job_id)
        elif method=='POST' and action=='recover':
            from . import multiview_3d
            result=multiview_3d.reconcile(root,job_id,body.get('request_id'),body.get('index',1))
        elif method=='POST' and action=='resume':
            job=jobs.read_job('trellis',job_id)
            if job['request'].get('input_mode')=='multiview' and job['request'].get('backend')=='trellis':
                from . import multiview_3d
                multiview_3d.reconcile(root,job_id)
            if job['status']=='recovery_required':job['status']='interrupted'
            job.pop('stop_after_current',None)
            jobs._atomic_json(jobs.job_path('trellis',job_id),job)
            result=jobs.start_job('trellis',job_id)
        elif method=='POST' and action=='blender': result=trellis.open_blender(root,job_id,int(index or 1))
        elif method=='POST' and action=='folder':
            import subprocess
            folder=trellis.result_path(root,job_id,int(index or 1)).parent
            subprocess.Popen(['xdg-open',str(folder)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            result={'opened':True}
        elif method=='GET' and action=='model':
            file=trellis.result_path(root,job_id,int(index or 1));size=file.stat().st_size
            start_response('200 OK',[('Content-Type','model/gltf-binary'),('Content-Length',str(size)),('Content-Disposition',f'inline; filename="{file.name}"')])
            def stream():
                with file.open('rb') as source:
                    while chunk:=source.read(1024*1024): yield chunk
            return stream()
        else: raise ValueError('Unsupported 3D action.')
    elif path=='/api/studio-tools/chat' and method=='POST':
        from .reasoning_provider import generate_json
        from . import multiview_3d
        context=body.get('context',{})
        keys={'seed','fov','faces'} if context.get('backend')=='pixal' else multiview_3d.REMOTE_PARAMS if context.get('input_mode')=='multiview' else trellis.PARAMS
        schema={'type':'object','properties':{'reply':{'type':'string'},'settings':{'type':'object','additionalProperties':False,'properties':{k:{'type':'number'} for k in keys}}},'required':['reply','settings'],'additionalProperties':False}
        text=str(body.get('text',''))
        if not 0<len(text)<=8000: raise ValueError('Message must contain 1–8000 characters.')
        result=generate_json(prompt='You are the Vibe Director studio assistant. Discuss the request; never run tools or start generation. TRELLIS is image-conditioned, not text-conditioned. Suggest only explicitly requested supported settings for the selected backend and input mode, using only schema keys; otherwise settings must be empty. Return reply and settings. Current context: '+json.dumps(body.get('context',{}))[:12000]+'\nRecent conversation: '+json.dumps(body.get('history',[]))[-16000:]+'\nUser: '+text,output_schema=schema,cpu_only=True)
    else:
        return respond(start_response,'404 Not Found',{'error':{'message':'Studio action not found.'}})
    return respond(start_response,'200 OK',result)
