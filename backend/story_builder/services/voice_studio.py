"""Additional speech/design/training graphs on the existing durable Comfy dispatcher."""
import hashlib, json, os, re, shutil, uuid
from pathlib import Path
from urllib.request import urlopen
from . import audio_catalog, audio_effects, image_training, media_library, video_repertoire as jobs
from .media_jobs import collect_outputs, submit_and_wait
from .storage_paths import generated_root

COMFY=Path(os.environ.get('COMFYUI_ROOT','/home/riki/web_dev/setup_comfy_and-stuff/ComfyUI'))
URL=os.environ.get('COMFYUI_URL','http://127.0.0.1:3008').rstrip('/')
SCHEMA=Path(__file__).resolve().parent.parent/'workflows/api/audio/voice_studio_schema.json'

def node(kind, **values):
    schema=json.loads(SCHEMA.read_text())[kind]
    fields={}
    for key,spec in schema['input'].get('required',{}).items():
        opts=spec[1] if len(spec)>1 and isinstance(spec[1],dict) else {}
        if 'default' in opts: fields[key]=opts['default']
        elif isinstance(spec[0],list): fields[key]=spec[0][0]
    fields.update(values)
    return {'class_type':kind,'inputs':fields}

def compile_graph(body, prefix, dataset=''):
    operation=body.get('operation'); text=str(body.get('text','')).strip(); seed=body.get('seed',1)
    if type(seed)!=int or not 0<=seed<=4294967295: raise ValueError('Seed must be a 32-bit positive integer.')
    if operation in {'speech','design'}:
        if not 1<=len(text)<=10000: raise ValueError('Enter 1–10000 characters to speak.')
        if operation=='speech':
            voice=next((v for v in audio_catalog.discover_voices() if v['id']==body.get('voice_id') and v.get('discoverable')),None)
            if not voice: raise ValueError('Choose a discoverable reference voice.')
            graph={'1':node('ChatterBoxEngineNode'),'2':node('CharacterVoicesNode',voice_name=audio_catalog.comfy_voice_key(voice)),
                '3':node('UnifiedTTSTextNode',TTS_engine=['1',0],opt_narrator=['2',0],text=text,seed=seed,enable_audio_cache=False)}
            port=0
        else:
            description=str(body.get('description','')).strip()
            if not 1<=len(description)<=4000: raise ValueError('Describe the designed voice (1–4000 characters).')
            graph={'1':node('Qwen3TTSEngineNode',model_variant='local:Qwen3-TTS-12Hz-1.7B-VoiceDesign',attn_implementation='sdpa',use_torch_compile=False),
                '3':node('UnifiedVoiceDesignerNode',TTS_engine=['1',0],reference_text=text,voice_instruction=description,seed=seed)}
            port=1
        graph['4']=node('SaveAudioAdvanced',audio=['3',port],filename_prefix=prefix,format='flac')
        return graph
    if operation!='training': raise ValueError('Unknown voice operation.')
    epochs=body.get('epochs',100);batch=body.get('batch_size',1)
    if type(epochs)!=int or not 1<=epochs<=20000 or type(batch)!=int or not 1<=batch<=16: raise ValueError('Invalid epochs or batch size.')
    name=str(body.get('name','')).strip()
    if not re.fullmatch('[A-Za-z0-9][A-Za-z0-9_-]{0,59}',name): raise ValueError('Use a model name containing letters, numbers, underscores or hyphens.')
    return {'1':node('RVCEngineNode'),
        '2':node('RVCDatasetPrepNode',TTS_engine=['1',0],model_name=name,dataset_source=dataset,training_sample_rate='40k',cpu_workers=1),
        '3':node('RVCTrainingConfigNode',epochs=epochs,batch_size=batch,learning_rate=.0001,gpu_ids='',num_workers=0,cache_data_in_gpu=False),
        '4':node('UnifiedModelTrainingNode',TTS_engine=['1',0],training_dataset=['2',0],training_config=['3',0],output_name=name,resume=False,overwrite=False),
        '5':node('PreviewAny',source=['4',0]),'6':node('PreviewAny',source=['4',1])}

def live_ready(graph):
    with urlopen(URL+'/object_info',timeout=15) as response: schema=json.load(response)
    for entry in graph.values():
        kind=entry['class_type']
        if kind not in schema: raise ValueError('ComfyUI node missing: '+kind)
        fields={**schema[kind]['input'].get('required',{}),**schema[kind]['input'].get('optional',{})}
        for key,value in entry['inputs'].items():
            if key not in fields: raise ValueError(f'Installed {kind} no longer accepts {key}.')
            allowed=fields[key][0]
            if isinstance(allowed,list) and isinstance(value,str) and value not in allowed:
                raise ValueError(f'{kind}: {key} value is unavailable. Refresh models before starting.')

def training_artifacts(history):
    values=history.get('outputs',{}).get('5',{}).get('text',[])
    artifacts=None
    for value in values:
        try:
            candidate=json.loads(value) if isinstance(value,str) else value
            if isinstance(candidate,dict) and candidate.get('engine_type')=='rvc': artifacts=candidate;break
        except (ValueError,TypeError): continue
    if not artifacts or not artifacts.get('model_path'): raise ValueError('Training finished without identified RVC artifacts.')
    paths=[]; root=(COMFY/'models/TTS/RVC').resolve()
    for key in ('model_path','index_path'):
        raw=artifacts.get(key)
        if not raw: continue
        path=Path(raw)
        # The installed container reports its mounted Comfy model root.
        if not path.is_file():
            parts=path.parts
            if 'models' in parts: path=COMFY/Path(*parts[parts.index('models'):])
        path=path.resolve()
        if not path.is_relative_to(root) or path.suffix not in {'.pth','.index'} or not path.is_file():
            raise ValueError('Returned RVC artifact is missing or outside its model catalog.')
        paths.append(str(path))
    return {'artifacts':json.dumps(artifacts,indent=2),'artifact_paths':paths,
            'artifact_hashes':{path:_digest(Path(path)) for path in paths}}

def progress(identity):
    job=jobs.read_job('voice-studio',identity)
    if job['request']['operation']=='training' and job['status']=='running':
        try:
            with urlopen(URL+'/api/tts-audio-suite/training-progress',timeout=3) as response: nodes=json.load(response).get('nodes',{})
            # Node IDs alone are reused across graphs. Match this job's unique dataset path as well.
            matches=[entry for entry in nodes.values() if identity in json.dumps(entry)]
            if matches: job['training_progress']=matches[-1]
        except (OSError,ValueError): pass
    return job

def capabilities():
    result={'speech':False,'design':False,'training':False,'errors':{}}
    try:
        with urlopen(URL+'/object_info',timeout=5) as response: schema=json.load(response)
    except (OSError,ValueError) as exc:
        result['errors']={key:str(exc) for key in ('speech','design','training')};return result
    for operation in ('speech','design','training'):
        try:
            # No voice lookup needed to inspect class readiness.
            classes={'speech':['ChatterBoxEngineNode','CharacterVoicesNode','UnifiedTTSTextNode','SaveAudioAdvanced'],
                'design':['Qwen3TTSEngineNode','UnifiedVoiceDesignerNode','SaveAudioAdvanced'],
                'training':['RVCEngineNode','RVCDatasetPrepNode','RVCTrainingConfigNode','UnifiedModelTrainingNode','PreviewAny']}[operation]
            if any(c not in schema for c in classes): raise ValueError('Required ComfyUI nodes are missing.')
            if operation=='design' and not any((COMFY/'models/TTS').rglob('*VoiceDesign*/config.json')): raise ValueError('Local Qwen3 VoiceDesign weights not found. No automatic download will start.')
            result[operation]=True
        except (OSError,ValueError) as exc: result['errors'][operation]=str(exc)
    return result

def create(root,body):
    workspace=str(body.get('workspace_id','')); media_library.media_root(root,workspace)
    operation=body.get('operation')
    if operation=='training':
        if body.get('confirmed') is not True: raise ValueError('Review and confirm the training dataset and settings first.')
        ids=body.get('asset_ids',[])
        if not isinstance(ids,list) or not 1<=len(ids)<=500 or len(set(ids))!=len(ids): raise ValueError('Choose 1–500 distinct audio clips for training.')
        for identity in ids:
            _,kind,_=media_library.asset_path(root,workspace,identity)
            if not kind.startswith('audio/'): raise ValueError('Training inputs must be audio.')
    graph=compile_graph(body,'vibe_voice/validation','validation')
    live_ready(graph);image_training.ensure_idle()
    # Freeze only supported request fields; never accept arbitrary executable graphs.
    request={k:body[k] for k in ('workspace_id','operation','text','seed','voice_id','description','name','epochs','batch_size','asset_ids') if k in body}
    if operation=='training':
        request['inputs']=[{'id':identity,'sha256':_digest(media_library.asset_path(root,workspace,identity)[0])} for identity in body['asset_ids']]
    job=jobs.create_job('voice-studio',request)
    return jobs.start_job('voice-studio',job['job_id'])

def _digest(path):
    with path.open('rb') as stream: return hashlib.file_digest(stream,'sha256').hexdigest()

def run(root,identity,request,update):
    image_training.ensure_idle()
    folder=jobs.job_path('voice-studio',identity).parent; workspace=request['workspace_id']
    stage=COMFY/'input/vibe_voice'/identity
    uncertain=False
    try:
        if request['operation']=='training':
            stage.mkdir(parents=True,exist_ok=True)
            for i,row in enumerate(request['inputs']):
                source,kind,_=media_library.asset_path(root,workspace,row['id'])
                if not kind.startswith('audio/') or _digest(source)!=row['sha256']: raise ValueError('A training source changed; prepare a new reviewed request.')
                shutil.copy2(source,stage/f'{i:04d}{source.suffix}')
        frozen=dict(request)
        if request['operation']=='training': frozen['name']=request['name'][:35]+'_'+identity
        graph=compile_graph(frozen,f'vibe_voice/{identity}',f'vibe_voice/{identity}')
        live_ready(graph);jobs._atomic_json(folder/'workflow.json',graph)
        submitted=folder/'submission.json'
        if submitted.is_file():
            prompt=json.loads(submitted.read_text())['prompt_id']
            try:
                with urlopen(URL+'/history/'+prompt,timeout=30) as response: history=json.load(response).get(prompt)
            except (OSError,ValueError):
                uncertain=True
                return {'job_status':'recovery_required','prompt_id':prompt,'error':'Could not reconcile the owned ComfyUI prompt. Retry reconciliation when ComfyUI is available.'}
            if not history:
                uncertain=True
                return {'job_status':'recovery_required','prompt_id':prompt,'error':'Waiting for the owned prompt history; no duplicate was submitted.'}
            if history.get('status',{}).get('status_str')=='error': raise ValueError('The owned ComfyUI prompt failed. Inspect its saved history before starting a new job.')
            if not history.get('status',{}).get('completed'):
                uncertain=True
                return {'job_status':'recovery_required','prompt_id':prompt,'error':'Owned prompt has not completed; no duplicate was submitted.'}
        else:
            prompt=str(uuid.uuid4());jobs._atomic_json(submitted,{'prompt_id':prompt})
            update('rendering','Training voice model.' if request['operation']=='training' else 'Generating speech.',15)
            try:
                prompt,history=submit_and_wait(graph,comfy_url=URL,prompt_id=prompt,timeout_seconds=86400 if request['operation']=='training' else 3600,workload_id=identity)
            except Exception as exc:
                if getattr(exc,'remote_state_unknown',False):
                    uncertain=True
                    return {'job_status':'recovery_required','prompt_id':prompt,'error':str(exc)}
                raise
        jobs._atomic_json(folder/'history.json',history)
        if request['operation']=='training':
            # Suite exports trained weights directly into its actual RVC loader catalog.
            # Persist the returned artifacts rather than guessing checkpoint filenames.
            return {'prompt_id':prompt,**training_artifacts(history),'training_node_id':'4'}
        output=root/'audio_studio/output'/identity
        files=collect_outputs(history,destination_dir=output,comfy_url=URL)
        audio=next((output/row['filename'] for row in files if row['kind']=='audio'),None)
        if not audio: raise ValueError('No generated speech audio returned.')
        audio_effects.validate_duration('speech',audio)
        asset=media_library.register_generated_audio(root,workspace,audio.relative_to(root/'audio_studio').as_posix(),{'source':'voice_studio','job_id':identity,'operation':request['operation'],'transcript':request['text']},storage_location={'store':'audio','path':audio.relative_to(root/'audio_studio').as_posix()})
        return {'prompt_id':prompt,'asset':asset,'transcript':request['text']}
    finally:
        if not uncertain and stage.exists(): shutil.rmtree(stage)
