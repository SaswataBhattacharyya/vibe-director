"""Jukebox HTTP seam. No inference or GPU work occurs during editing/export."""
import json
import re
from . import music_jukebox as music, video_repertoire as jobs


def handle(root,environ,start_response,read_json,respond):
    method=environ.get('REQUEST_METHOD','GET').upper();path=environ.get('PATH_INFO','')
    if match:=re.fullmatch(r'/api/jukebox/projects/(jukebox-[a-f0-9]{12})/render',path):
        if method!='POST' or environ.get('CONTENT_TYPE','').split(';')[0]!='audio/wav': raise ValueError('Use a WAV upload.')
        return respond(start_response,'200 OK',music.stage_export(root,match[1],environ))
    if method not in {'GET','POST'}: return respond(start_response,'405 Method Not Allowed',{'error':{'message':'Unsupported music method.'}})
    if method=='POST' and environ.get('CONTENT_TYPE','').split(';')[0]!='application/json': raise ValueError('Use application/json.')
    body=read_json(environ) if method=='POST' else {}
    if path=='/api/jukebox/state' and method=='GET': result=music.snapshot(root)
    elif path=='/api/jukebox/folder' and method=='POST': result=music.folder(root,body)
    elif path=='/api/jukebox/projects' and method=='POST': result=music.save(root,body,True)
    elif match:=re.fullmatch(r'/api/jukebox/projects/(jukebox-[a-f0-9]{12})/jobs',path):
        if method!='GET': raise ValueError('Use GET.')
        result={'jobs':[j for j in jobs.list_jobs('music-jukebox') if j.get('request',{}).get('project_id')==match[1]]}
    elif match:=re.fullmatch(r'/api/jukebox/projects/(jukebox-[a-f0-9]{12})(?:/(save|export|copy))?',path):
        pid,action=match.groups()
        if method=='GET' and not action: result=json.loads(music.project_path(root,pid).read_text())
        elif method=='POST' and action=='save':
            if body.get('project',{}).get('id')!=pid: raise ValueError('Project identity mismatch.')
            result=music.save(root,body)
        elif method=='POST' and action=='copy':
            p=json.loads(music.project_path(root,pid).read_text());folder=music.granted(root,body.get('folder'))
            target=folder/f'{pid}.json'
            if target.is_symlink(): raise ValueError('Project output cannot be a symbolic link.')
            if target.exists() and not body.get('overwrite'): raise ValueError('Project file exists. Confirm overwrite.')
            music.write(target,p,overwrite=bool(body.get('overwrite')));result={'path':str(target)}
        elif method=='POST' and action=='export':
            music.claim_export(root,pid,body)
            job=jobs.create_job('music-jukebox',{**body,'project_id':pid});result=jobs.start_job('music-jukebox',job['job_id'])
        else: raise ValueError('Unsupported music operation.')
    elif match:=re.fullmatch(r'/api/jukebox/jobs/(music-jukebox-[a-f0-9]{12})(?:/(cancel))?',path):
        jid,action=match.groups()
        if method=='POST' and action=='cancel': result=jobs.cancel_job('music-jukebox',jid)
        elif method=='GET' and not action: result=jobs.read_job('music-jukebox',jid)
        else: raise ValueError('Unsupported job operation.')
    elif match:=re.fullmatch(r'/api/jukebox/exports/(music-jukebox-[a-f0-9]{12})',path):
        if method!='GET': raise ValueError('Use GET.')
        from pathlib import Path
        record=json.loads((music.home(root)/'exports'/f'{match[1]}.json').read_text());file=Path(record['path'])
        start_response('200 OK',[('Content-Type',{'wav':'audio/wav','flac':'audio/flac','mp3':'audio/mpeg'}[file.suffix[1:]]),('Content-Length',str(file.stat().st_size))])
        def stream():
            with file.open('rb') as source:
                while chunk:=source.read(1024*1024): yield chunk
        return stream()
    elif path=='/api/jukebox/chat' and method=='POST':
        from .reasoning_provider import generate_json
        text=body.get('text','')
        if not isinstance(text,str) or not 1<=len(text)<=8000: raise ValueError('Message must contain 1–8000 characters.')
        schema={'type':'object','properties':{'reply':{'type':'string'},'action':{'type':'string','enum':['none','tempo','gain','house_beat','crossfade']},'value':{'type':'number'},'track':{'type':'string'}},'required':['reply','action','value','track'],'additionalProperties':False}
        result=generate_json(prompt='You are the Music Jukebox director. Explain musical terms simply. Never run tools. Propose only supported changes, or action none and explain manual steps. Actions: tempo value 30–300 BPM; gain track ID and value -60..12 dB; house_beat value BPM makes kick/snare/hat patterns; crossfade value duration seconds creates a saved DJ A to B crossfader automation only (requires deck performances already captured). No file deletion, generation or training. User will review brief then exact changes before apply. Current project: '+json.dumps(body.get('context',{}))[:24000]+'\nUser: '+text,output_schema=schema,cpu_only=True)
    else: return respond(start_response,'404 Not Found',{'error':{'message':'Music endpoint not found.'}})
    return respond(start_response,'200 OK',result)
