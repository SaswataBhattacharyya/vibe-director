"""Named CPU music projects. Audio rendering uses the browser's shared audio graph;
encoding runs through the existing durable media worker, never a second controller.
"""
from pathlib import Path
from contextlib import contextmanager
import fcntl
import json
import math
import os
import re
import subprocess
import uuid
import wave
import time
from . import media_library, video_repertoire as jobs


def home(root):
    path = Path(root) / 'music_jukebox'
    path.mkdir(parents=True, exist_ok=True)
    return path


def identity(value):
    if not isinstance(value, str) or not re.fullmatch(r'jukebox-[a-f0-9]{12}', value):
        raise ValueError('Invalid music project identity.')
    return value


def project_path(root, value):
    from .storage_paths import checked, project_root
    value = identity(value)
    registry = checked(root, 'library', 'jukebox-sessions.json')
    owners = json.loads(registry.read_text()) if registry.exists() else {}
    if value in owners:
        return checked(project_root(root, owners[value]), 'music', 'jukebox', value, 'project.json')
    return checked(root, 'projects', value, 'music', 'jukebox', 'project.json')


def write(path, value, overwrite=True):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with temporary.open('w') as stream:
            json.dump(value, stream, allow_nan=False)
            stream.flush(); os.fsync(stream.fileno())
        if overwrite: temporary.replace(path)
        else:
            os.link(temporary,path)
            temporary.unlink()
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def locked(root):
    with (home(root) / '.lock').open('a') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        yield


def number(value, lo, hi):
    if type(value) not in {int, float} or not math.isfinite(value) or not lo <= value <= hi:
        raise ValueError(f'Music value must be between {lo} and {hi}.')
    return value


def validate(root, project):
    if not isinstance(project,dict): raise ValueError('Expected a music project.')
    if project.get('mode') not in {'arrange','dj'}: raise ValueError('Invalid playback mode.')
    number(project.get('swing'),0,.75)
    if type(project.get('limiter')) is not bool: raise ValueError('Invalid master protection setting.')
    if project.get('version') != 1: raise ValueError('Unsupported music project version.')
    identity(project.get('id'))
    if not isinstance(project.get('name'), str) or not 1 <= len(project['name'].strip()) <= 120: raise ValueError('Name must contain 1–120 characters.')
    number(project.get('bpm'), 30, 300)
    number(project.get('bars'), 1, 128)
    if project['bars'] != int(project['bars']): raise ValueError('Bars must be whole numbers.')
    if project['bars']*240/project['bpm']>600: raise ValueError('Arrangement exceeds 10 minutes.')
    number(project.get('master'), -60, 6)
    sources = project.get('sources', [])
    if not isinstance(sources, list) or len(sources) > 32: raise ValueError('At most 32 sources per project.')
    ids = set()
    for source in sources:
        if not isinstance(source,dict): raise ValueError('Invalid source.')
        sid = source.get('id')
        if not isinstance(sid,str) or not re.fullmatch(r'[\w-]{1,80}',sid) or sid in ids: raise ValueError('Source IDs must be unique.')
        ids.add(sid)
        # Resolve actual shared asset identities; do not accept arbitrary file URLs.
        path, _, _ = media_library.asset_path(root, source.get('workspace_id',''), source.get('asset_id',''))
        with path.open('rb') as stream: signature=stream.read(16)
        if media_library._kind(path.name, signature) != 'audio': raise ValueError('Choose audio sources.')
        expected = f"/api/media/{source['workspace_id']}/assets/{source['asset_id']}/content"
        if source.get('url') != expected: raise ValueError('Invalid audio source URL.')
        number(source.get('duration'), .001, 600)
    tracks = project.get('tracks')
    if not isinstance(tracks,list) or len(tracks) > 24: raise ValueError('At most 24 tracks.')
    tids=set()
    for track in tracks:
        if not isinstance(track,dict): raise ValueError('Invalid track.')
        if not isinstance(track.get('name'),str) or len(track['name'])>120: raise ValueError('Invalid track name.')
        for flag in ['mute','solo','compress']:
            if type(track.get(flag)) is not bool: raise ValueError('Invalid track switch.')
        if not isinstance(track.get('id'),str) or track.get('id') in tids: raise ValueError('Track identities must be unique.')
        tids.add(track['id'])
        if track.get('kind') not in {'audio','synth','bass','kick','snare','hat','sample'}: raise ValueError('Unsupported instrument.')
        for key, low, high in [('gain',-60,12),('pan',-1,1),('low',-24,24),('mid',-24,24),('high',-24,24),('echo',0,.8),('fadeIn',0,60),('fadeOut',0,60),('rate',.25,4),('reverb',0,1),('pitch',-12,12)]: number(track.get(key),low,high)
        if not all(isinstance(track.get(key),list) for key in ['clips','notes','automation']): raise ValueError('Track events must be lists.')
        for point in track.get('automation',[]):
            if not isinstance(point,dict): raise ValueError('Invalid automation point.')
            number(point.get('time'),0,600);number(point.get('gain'),-60,12);number(point.get('pan'),-1,1)
        if len(track.get('automation',[]))>1000: raise ValueError('Too many automation points.')
        clips=track.get('clips',[]); notes=track.get('notes',[])
        if len(clips)>256 or len(notes)>4096: raise ValueError('Track event limit exceeded.')
        for clip in clips:
            if not isinstance(clip,dict): raise ValueError('Invalid clip.')
            if clip.get('source') not in ids: raise ValueError('Clip source missing; relink the recording.')
            source=next(s for s in sources if s['id']==clip['source'])
            number(clip.get('start'),0,source['duration']);number(clip.get('end'),clip['start']+.00001,source['duration']+.01)
            number(clip.get('at'),0,600)
            if clip['at']+(clip['end']-clip['start'])/track['rate']>600: raise ValueError('Clip exceeds 10 minutes.')
        for note in notes:
            if not isinstance(note,dict): raise ValueError('Invalid note.')
            number(note.get('beat'),0,512);number(note.get('length'),.03125,128);number(note.get('midi'),0,127);number(note.get('velocity'),0,1)
            if (note['beat']+note['length'])*60/project['bpm']>600: raise ValueError('Note exceeds 10 minutes.')
        if track.get('kind')=='sample' and track.get('sample') not in ids: raise ValueError('Choose a sampler source.')
    dj=project.get('dj',{})
    if not isinstance(dj,dict): raise ValueError('Invalid DJ performance.')
    number(dj.get('cross',0),-1,1)
    events=dj.get('events',[])
    if not isinstance(events,list): raise ValueError('DJ events must be a list.')
    if len(events)>10000: raise ValueError('DJ performance is too long.')
    for event in events:
        if not isinstance(event,dict): raise ValueError('Invalid DJ event.')
        number(event.get('time'),0,600)
        if event.get('type') not in {'cross','play','stop','gain','low','mid','high','rate'}: raise ValueError('Invalid DJ event.')
        if event['type']=='cross': number(event.get('value'),-1,1)
        else:
            if event.get('deck') not in {'A','B'}: raise ValueError('Invalid deck.')
            if event['type']=='play':
                if event.get('source') not in ids: raise ValueError('Missing deck source.')
                number(event.get('offset'),0,next(s['duration'] for s in sources if s['id']==event['source'])-.00001);number(event.get('rate'),.5,2)
                number(event.get('loop',0),0,64)
            elif event['type']!='stop': number(event.get('value'),.5 if event['type']=='rate' else -24,2 if event['type']=='rate' else 24)
    return project


def save(root, body, creating=False):
    with locked(root):
        p=body.get('project')
        if not isinstance(p,dict): raise ValueError('Expected a music project.')
        if creating:
            p={**p,'id':'jukebox-'+uuid.uuid4().hex[:12],'revision':0}
            p['workspace_id']=p.get('workspace_id') or p['id']
            from .storage_paths import checked, project_root
            project_root(root, p['workspace_id'])
            registry=checked(root,'library','jukebox-sessions.json')
            owners=json.loads(registry.read_text()) if registry.exists() else {}
            owners[p['id']]=p['workspace_id']
            # Validate before publishing a locator for the new session.
            validate(root,p)
            write(registry,owners)
        path=project_path(root,p['id'])
        current=json.loads(path.read_text()) if path.exists() else None
        if not creating and (current is None or current['revision'] != body.get('revision')): raise ValueError('Project changed in another tab. Reopen before saving.')
        if current and p.get('workspace_id')!=current['workspace_id']: raise ValueError('Project workspace cannot change.')
        validate(root,p)
        if current:
            checkpoint=path.parent/'checkpoints'/f"{current['revision']:06}.json"
            write(checkpoint,current)
            for old in sorted(checkpoint.parent.glob('*.json'))[:-30]: old.unlink()
        p={**p,'revision':(current['revision']+1 if current else 1)}
        write(path,p)
        return p


def export_path(root, job_id):
    """Keep frozen export metadata; verified project copies recover missing originals."""
    record=json.loads((home(root)/'exports'/f'{job_id}.json').read_text())
    from .storage_paths import relocated_path
    path=relocated_path(root,Path(record['path']))
    if path.is_file() and not any(p.is_symlink() for p in (path,*path.parents)):
        return path
    copy=home(root)/'saved-exports'/job_id/record['name']
    if copy.is_file() and not any(p.is_symlink() for p in (copy,*copy.parents)):
        return copy
    raise ValueError('Locate the saved music export before opening it.')


def snapshot(root, workspace=None):
    result=[]; legacy=[]
    for path in [*(Path(root)/'projects').glob('*/music/jukebox/project.json'), *(Path(root)/'projects').glob('*/music/jukebox/*/project.json')]:
        try:
            p=json.loads(path.read_text())
            if workspace and p.get('workspace_id') != workspace:
                if p.get('workspace_id') == p.get('id'):
                    legacy.append({'id':p['id'],'name':p['name'],'revision':p['revision']})
                continue
            result.append({'id':p['id'],'name':p['name'],'revision':p['revision']})
        except (ValueError,KeyError): continue
    return {'projects':result,'legacy_projects':legacy,'output':str(home(root)/'output')}


def folder(root, body):
    value=body.get('path')
    if not value:
        proc=subprocess.run(['zenity','--file-selection','--directory','--title=Choose music folder'],capture_output=True,text=True,timeout=120)
        if proc.returncode: raise ValueError('Folder selection cancelled. You can enter an existing absolute path.')
        value=proc.stdout.strip()
    path=Path(value).expanduser()
    if not path.is_absolute() or not path.is_dir(): raise ValueError('Choose an existing absolute folder.')
    token=uuid.uuid4().hex;write(home(root)/'folders'/f'{token}.json',{'path':str(path.resolve())})
    return {'path':str(path.resolve()),'grant':token}


def granted(root, token):
    if not isinstance(token,str) or not re.fullmatch(r'[a-f0-9]{32}',token): raise ValueError('Choose the folder again.')
    path=Path(json.loads((home(root)/'folders'/f'{token}.json').read_text())['path'])
    if not path.is_dir() or path.resolve()!=path: raise ValueError('Folder moved; choose it again.')
    return path


def stage_export(root, project_id, environ):
    p=json.loads(project_path(root,project_id).read_text())
    size=int(environ.get('CONTENT_LENGTH') or 0)
    if not 44<=size<=120*1024*1024: raise ValueError('Export must be a WAV up to 120 MiB (10 minute stereo limit).')
    data=environ['wsgi.input'].read(size)
    if len(data)!=size: raise ValueError('Incomplete audio upload.')
    token=uuid.uuid4().hex;path=home(root)/'cache'/'renders'/f'{token}.wav';path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(data)
    try:
        with wave.open(str(path)) as audio:
            if audio.getsampwidth()!=2 or audio.getnchannels()!=2 or audio.getframerate()!=44100 or not 1<=audio.getnframes()<=44100*600: raise ValueError('Expected bounded stereo 44.1 kHz WAV.')
    except Exception:
        path.unlink(missing_ok=True);raise
    write(path.with_suffix('.json'),{'project_id':project_id,'revision':p['revision'],'claimed':False})
    for old in path.parent.glob('*'):
        if old.is_file() and old.stat().st_mtime<time.time()-86400: old.unlink(missing_ok=True)
    return {'token':token,'revision':p['revision']}


def encode(root, job_id, request):
    token=request['token']
    if not re.fullmatch(r'[a-f0-9]{32}',token): raise ValueError('Invalid export token.')
    source=home(root)/'cache'/'renders'/f'{token}.wav'
    identity(request['project_id'])
    fmt=request.get('format','wav')
    if fmt not in {'wav','mp3','flac'}: raise ValueError('Choose WAV, MP3 or FLAC.')
    name=request.get('name','')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9 _.-]{0,100}',name) or name in {'.','..'}: raise ValueError('Use a simple output filename.')
    dest=granted(root,request['folder']) if request.get('folder') else home(root)/'output'/request['project_id']
    dest.mkdir(parents=True,exist_ok=True)
    target=dest/f'{name}.{fmt}'
    if target.is_symlink(): raise ValueError('Output cannot be a symbolic link.')
    if target.exists() and not request.get('overwrite'): raise ValueError('Output exists. Confirm overwrite or choose another name.')
    temporary=dest/f'.{job_id}.{fmt}'
    try:
        codecs={'wav':['-c:a','pcm_s16le'],'flac':['-c:a','flac'],'mp3':['-c:a','libmp3lame','-b:a','320k']}
        subprocess.run(['ffmpeg','-v','error','-nostdin','-y','-i',str(source),*codecs[fmt],str(temporary)],check=True,capture_output=True,timeout=180)
        probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(temporary)],timeout=20))
        if not probe.get('streams') or float(probe['format']['duration'])<=0: raise ValueError('Encoded output did not validate.')
        if jobs.read_job('music-jukebox',job_id)['status'] in {'cancelled','cancel_requested'}: raise ValueError('Export cancelled.')
        if request.get('overwrite'): temporary.replace(target)
        else:
            os.link(temporary,target);temporary.unlink() # atomic no-clobber, even concurrent exports
        record={'path':str(target),'name':target.name,'duration':float(probe['format']['duration']),'project_id':request['project_id']}
        write(home(root)/'exports'/f'{job_id}.json',record)
        return {**record,'url':f'/api/jukebox/exports/{job_id}'}
    finally:
        temporary.unlink(missing_ok=True);source.unlink(missing_ok=True);source.with_suffix('.json').unlink(missing_ok=True)


def claim_export(root, project_id, body):
    token=body.get('token','')
    if not isinstance(token,str) or not re.fullmatch(r'[a-f0-9]{32}',token): raise ValueError('Render audio before exporting.')
    with locked(root):
        path=home(root)/'cache'/'renders'/f'{token}.json'
        metadata=json.loads(path.read_text())
        if metadata['project_id']!=project_id or metadata['claimed']: raise ValueError('Render belongs to another export; render again.')
        if not path.with_suffix('.wav').is_file(): raise ValueError('Rendered audio is missing.')
        metadata['claimed']=True;write(path,metadata)
    return metadata
