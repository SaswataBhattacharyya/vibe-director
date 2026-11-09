"""Native FILM/RIFE execution and verified, silent CPU exports."""
import json
import math
import os
import shutil
import subprocess
import time
import urllib.parse
import urllib.request
import uuid
import signal
from pathlib import Path

from . import media_library, projects, video_repertoire
from .gpu_watchdog import ensure_prompt_watchdog, finish_prompt_watchdog
from .production_image_worker import _request_json
from .storage_paths import generated_root

MODELS = {'rife': 'rife_v4.26.safetensors', 'film': 'film_net_fp16.safetensors'}
GRAPH_ROOT = Path(__file__).resolve().parents[1] / 'workflows/api'


def validate_settings(value):
    if not isinstance(value, dict) or set(value) != {'model', 'multiplier', 'fps', 'hold'}:
        raise ValueError('Supply model, multiplier, fps and hold.')
    if value['model'] not in MODELS or type(value['multiplier']) is not int or not 2 <= value['multiplier'] <= 16:
        raise ValueError('Choose RIFE or FILM and an integer multiplier from 2 to 16.')
    for field, low, high in [('fps', 1, 60), ('hold', 0, 10)]:
        n = value[field]
        if type(n) not in (int, float) or not math.isfinite(n) or not low <= n <= high:
            raise ValueError(f'{field} must be finite and between {low} and {high}.')
    return dict(value)


def dimensions(path):
    result = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-of', 'json', str(path)],
                            check=True, capture_output=True, text=True, timeout=30)
    stream = next((s for s in json.loads(result.stdout)['streams'] if s['codec_type'] == 'video'), None)
    if stream is None or not 1 <= stream['width'] <= 4096 or not 1 <= stream['height'] <= 4096:
        raise ValueError('Keyframe dimensions are unsupported (maximum 4096 per side).')
    return stream['width'], stream['height']


def compile_graph(names, model, multiplier, prefix):
    if not 2 <= len(names) <= 100:
        raise ValueError('Interpolation needs 2–100 ordered keys from one continuous shot.')
    graph = json.loads((GRAPH_ROOT / f'{model}_frame_interpolation.api.json').read_text())
    graph['1']['inputs']['image'], graph['2']['inputs']['image'] = names[:2]
    batch = '3'
    for i, name in enumerate(names[2:]):
        load, merge = f'key_{i}', f'batch_{i}'
        graph[load] = {'class_type': 'LoadImage', 'inputs': {'image': name}}
        graph[merge] = {'class_type': 'ImageBatch', 'inputs': {'image1': [batch, 0], 'image2': [load, 0]}}
        batch = merge
    graph['4']['inputs']['model_name'] = MODELS[model]
    graph['5']['inputs'].update(images=[batch, 0], multiplier=multiplier)
    graph['6']['inputs']['filename_prefix'] = prefix
    return graph


def capability(url=None):
    from .production_image_workflows import graph_input_errors, input_choices
    url = (url or os.environ.get('COMFYUI_URL', 'http://127.0.0.1:3008')).rstrip('/')
    try:
        info = _request_json(url + '/object_info', timeout_seconds=3)
        choices = input_choices(info['FrameInterpolationModelLoader']['input']['required']['model_name']) or []
        missing = [n for n in ['LoadImage', 'ImageBatch', 'FrameInterpolate', 'SaveImage'] if n not in info]
        models = [m for m,v in MODELS.items() if v in choices and not graph_input_errors(compile_graph(['a.png','b.png'],m,2,'check'),info)]
        return {'available': bool(models), 'models': models,
                'reason': ('Missing nodes: ' + ', '.join(missing)) if missing else
                    None if models else 'Installed interpolation schemas or model choices do not match the bundled graphs.'}
    except (KeyError, TypeError, ValueError, OSError) as exc:
        return {'available': False, 'models': [], 'reason': f'Interpolation backend unavailable: {exc}'}


def staging(root, job_id):
    from .production_image_worker import comfyui_root
    return comfyui_root() / 'input', Path(root) / 'services/frame-staging', 'frames-' + job_id


def stage(root, job_id, paths, sources):
    from .minimax_h3_media import stage_image_reference
    input_dir, owner_root, owner = staging(root, job_id)
    names = []
    try:
        for path, source in zip(paths, sources):
            record = stage_image_reference(path, asset_id=source['asset_id'], owner_id=owner,
                comfy_input_dir=input_dir, owner_root=owner_root)
            if record.source_sha256 != source['sha256']:
                raise ValueError('Keyframe changed while staging.')
            names.append(record.filename)
    except Exception:
        # No prompt has been submitted yet; partial staging is safe to remove.
        cleanup_staging(root, job_id)
        raise
    return names


def cleanup_staging(root, job_id):
    from .minimax_h3_media import cleanup_owned_media
    input_dir, owner_root, owner = staging(root, job_id)
    return cleanup_owned_media(owner, comfy_input_dir=input_dir, owner_root=owner_root)


def check_cancel(job_id):
    job = video_repertoire.read_job('frame-pipeline', job_id)
    if job['status'] in {'cancelled', 'cancel_requested'}:
        raise KeyboardInterrupt('Frame pipeline job cancelled.')


def interpolate(root, owner, job_id, sources, settings):
    from .frame_pipeline import image
    from .media_jobs import gpu_workload_guard
    from .gpu_runtime import interrupt_if_owned_prompt
    settings = validate_settings(settings)
    out = generated_root(root, owner) / 'frame-pipeline' / job_id
    out.mkdir(parents=True, exist_ok=True)
    journal = out / 'interpolation.json'
    url = os.environ.get('COMFYUI_URL', 'http://127.0.0.1:3008').rstrip('/')
    paths = [media_library.asset_path(root, owner, s['asset_id'])[0] for s in sources]
    sizes = [dimensions(p) for p in paths]
    if len(set(sizes)) != 1:
        raise ValueError('Keyframes have different decoded dimensions.')
    if not 2 <= len(paths) <= 100:
        raise ValueError('Interpolation requires 2–100 keys.')
    count = (len(paths)-1)*settings['multiplier']+1
    budget = count*sizes[0][0]*sizes[0][1]*4
    if count > 500 or budget > 2*1024**3 or shutil.disk_usage(out).free < budget*2 + 128*1024**2:
        raise ValueError('Sequence exceeds the frame/storage budget. Split the take or use a smaller multiplier.')
    for s in sources:
        image(root, owner, s['asset_id'], s['sha256'])
    config = {'sources': sources, 'settings': settings}
    if journal.exists():
        state = json.loads(journal.read_text())
        if state['config'] != config:
            raise ValueError('Frozen interpolation settings changed.')
        # No resubmission of a pending/uncertain prompt. Recovery reads history only.
        prompt_id = state['prompt_id']
    else:
        available = capability(url)
        if settings['model'] not in available['models']:
            raise ValueError(available['reason'] or 'Selected interpolation model is unavailable.')
        prompt_id = str(uuid.uuid4())
        with gpu_workload_guard(comfy_url=url, timeout_seconds=60):
            check_cancel(job_id)
            names = stage(root, job_id, paths, sources)
            graph = compile_graph(names, settings['model'], settings['multiplier'], f'vibe/{owner}/{job_id}/frame')
            state = {'config': config, 'prompt_id': prompt_id, 'graph': graph, 'state': 'submitting'}
            video_repertoire._atomic_json(journal, state)
            ensure_prompt_watchdog(comfy_url=url, prompt_id=prompt_id).check()
            try:
                response = _request_json(url + '/prompt', method='POST', payload={'prompt': graph, 'prompt_id': prompt_id, 'client_id': job_id}, timeout_seconds=60)
                if response.get('node_errors') or response.get('prompt_id') != prompt_id:
                    raise ValueError('ComfyUI rejected or changed the submitted prompt: ' + str(response))
                history = wait(url, prompt_id, job_id)
            except KeyboardInterrupt:
                interrupt_if_owned_prompt(comfy_url=url, prompt_id=prompt_id, request_json=_request_json)
                raise
            except (OSError, ValueError, TimeoutError) as exc:
                return {'workspace_id': owner, 'job_status': 'recovery_required', 'error': str(exc)}
    if 'history' not in locals():
        history = _request_json(url + '/history/' + prompt_id, timeout_seconds=20).get(prompt_id)
        if not history:
            return {'workspace_id': owner, 'job_status': 'recovery_required', 'error': 'Prompt outcome remains uncertain. Inspect its queue/history; no replacement was submitted.'}
    if history.get('status', {}).get('status_str') == 'error':
        finish_prompt_watchdog(comfy_url=url, prompt_id=prompt_id)
        cleanup_staging(root, job_id)
        raise ValueError('Interpolation execution failed: ' + str(history.get('status')))
    if history.get('status', {}).get('completed') is not True:
        return {'workspace_id': owner, 'job_status': 'recovery_required', 'error': 'Interpolation is not terminal yet.'}
    finish_prompt_watchdog(comfy_url=url, prompt_id=prompt_id)
    cleanup_staging(root, job_id)
    images = history.get('outputs', {}).get('6', {}).get('images', [])
    if len(images) != count:
        raise ValueError(f'Expected {count} interpolation frames; received {len(images)}.')
    sequence = out / 'sequence'
    sequence.mkdir(exist_ok=True)
    frames = []
    for i, record in enumerate(images):
        check_cancel(job_id)
        if record.get('type') != 'output':
            raise ValueError('Only saved output images can be published.')
        query = urllib.parse.urlencode({k: record[k] for k in ('filename', 'subfolder', 'type')})
        target = sequence / f'frame_{i:04d}.png'
        with urllib.request.urlopen(url + '/view?' + query, timeout=60) as response:
            data = response.read(32*1024**2+1)
        if len(data) > 32*1024**2 or not data.startswith(b'\x89PNG\r\n\x1a\n'):
            raise ValueError('Interpolation output is not a supported PNG.')
        temp = target.with_suffix('.part')
        temp.write_bytes(data)
        temp.replace(target)
        if dimensions(target) != sizes[0]:
            raise ValueError('Interpolation output dimensions changed.')
        frames.append({'path': target.name, 'sha256': projects.digest(target)})
    # Compare decoded pixels; PNG metadata/compression may differ from source files.
    for i,path in enumerate(paths):
        before, after = pixels(path), pixels(sequence / frames[i*settings['multiplier']]['path'])
        # Native FrameInterpolate copies endpoints through intermediate_dtype (fp16 optional).
        # One 8-bit level allows its float/SaveImage roundtrip, never a visual edit.
        if len(before) != len(after) or any(abs(a-b)>1 for a,b in zip(before,after)):
            raise ValueError('Interpolation did not preserve an original keyframe.')
    for s in sources:
        image(root, owner, s['asset_id'], s['sha256'])
    manifest = {'sources': sources, 'settings': settings, 'frames': frames, 'prompt_id': prompt_id,
                'dimensions': sizes[0], 'history': history}
    video_repertoire._atomic_json(out / 'sequence.json', manifest)
    return {'workspace_id': owner, 'sequence_job_id': job_id, 'frame_count': count,
            'duration_seconds': count/settings['fps'] + 2*round(settings['hold']*settings['fps'])/settings['fps']}


def wait(url, prompt_id, job_id):
    deadline = time.monotonic()+3600
    while time.monotonic() < deadline:
        check_cancel(job_id)
        ensure_prompt_watchdog(comfy_url=url, prompt_id=prompt_id).check()
        history = _request_json(url + '/history/' + prompt_id, timeout_seconds=20).get(prompt_id)
        if history and (history.get('status', {}).get('completed') or history.get('status', {}).get('status_str') == 'error'):
            return history
        time.sleep(2)
    raise TimeoutError('Interpolation timed out; reconcile the saved prompt before resuming.')


def pixels(path):
    return subprocess.run(['ffmpeg', '-v', 'error', '-nostdin', '-i', str(path), '-frames:v', '1',
        '-pix_fmt', 'rgb24', '-f', 'rawvideo', 'pipe:1'], check=True, capture_output=True, timeout=30).stdout


def export(root, owner, job_id, sequence_job_id):
    from . import frame_pipeline
    source_job = video_repertoire.read_job('frame-pipeline', sequence_job_id)
    if source_job['status'] != 'completed' or source_job['request']['workspace_id'] != owner or source_job['request']['operation'] != 'interpolate':
        raise ValueError('Choose a completed interpolation job from this project.')
    source = generated_root(root, owner) / 'frame-pipeline' / sequence_job_id
    manifest = json.loads((source / 'sequence.json').read_text())
    settings = validate_settings(manifest['settings'])
    request = source_job['request']
    if manifest['sources'] != request['inputs'] or settings != {k: request['settings'][k] for k in ('model','multiplier','fps','hold')}:
        raise ValueError('Sequence manifest differs from its frozen interpolation request.')
    frames = manifest['frames']
    if len(frames) != (len(manifest['sources'])-1)*settings['multiplier']+1:
        raise ValueError('Sequence manifest has the wrong frame count.')
    for s in manifest['sources']:
        frame_pipeline.image(root, owner, s['asset_id'], s['sha256'])
    for i,frame in enumerate(frames):
        path = source / 'sequence' / f'frame_{i:04d}.png'
        if frame['path'] != path.name or projects.digest(path) != frame['sha256']:
            raise ValueError('Approved interpolation sequence changed; export refused.')
    out = generated_root(root, owner) / 'frame-pipeline' / job_id
    out.mkdir(parents=True, exist_ok=True)
    hold = round(settings['hold']*settings['fps'])
    expected = len(frames)+2*hold
    width, height = manifest['dimensions']
    if width%2 or height%2:
        raise ValueError('MP4 export requires even image dimensions; normalize explicitly.')
    check_cancel(job_id)
    for name, codecs in [('preview.mp4', ['-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart']),
                         ('lossless.mkv', ['-c:v','ffv1','-level','3','-pix_fmt','gbrp'])]:
        target = out / name
        partial = out / ('encoding-' + name)
        try:
            run_cpu(['ffmpeg','-v','error','-nostdin','-y','-framerate',str(settings['fps']),
                '-i',str(source/'sequence/frame_%04d.png'),'-vf',f'tpad=start_mode=clone:start={hold}:stop_mode=clone:stop={hold}',
                '-an',*codecs,str(partial)], job_id)
            check_cancel(job_id)
            probe = json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-show_streams','-show_format','-of','json',str(partial)],timeout=30))
            streams = probe['streams']
            video = next(s for s in streams if s['codec_type']=='video')
            duration = float(probe['format']['duration'])
            if len(streams)!=1 or int(video['nb_read_frames'])!=expected or (video['width'],video['height'])!=(width,height) or video['codec_name'] != ('h264' if name.endswith('mp4') else 'ffv1') or not math.isfinite(duration) or abs(duration-expected/settings['fps'])>1/settings['fps']:
                raise ValueError('Export verification failed: frame count, dimensions or silent stream contract.')
            run_cpu(['ffmpeg','-v','error','-nostdin','-i',str(partial),'-f','null','-'], job_id)
            partial.replace(target)
        finally:
            partial.unlink(missing_ok=True)
    check_cancel(job_id)
    for original in manifest['sources']:
        frame_pipeline.image(root, owner, original['asset_id'], original['sha256'])
    metadata = {'frame_pipeline': {'sequence_job_id': sequence_job_id, 'sources': manifest['sources'], 'settings':settings}}
    asset = media_library.register_generated_video(root,owner,f'frame-pipeline/{job_id}/preview.mp4',metadata)
    video_repertoire._atomic_json(out/'export.json', {'asset_id':asset['asset_id'],'preview_sha256':projects.digest(out/'preview.mp4'),
        'lossless_sha256':projects.digest(out/'lossless.mkv'),'frame_count':expected,'ffprobe':probe})
    return {'workspace_id': owner, 'assets':[media_library.public_asset_record(asset,owner)],
            'sequence_job_id':sequence_job_id, 'frame_count':expected}


def run_cpu(command, job_id):
    """Cancellation terminates only this export's process group and reaps it."""
    process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, start_new_session=True)
    try:
        deadline = time.monotonic()+300
        while True:
            check_cancel(job_id)
            try:
                _, error = process.communicate(timeout=.5)
                if process.returncode:
                    raise ValueError('FFmpeg export failed: ' + error.decode(errors='replace')[-2000:])
                return
            except subprocess.TimeoutExpired:
                if time.monotonic()>deadline:
                    raise TimeoutError('FFmpeg export timed out.')
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
        if process.stderr:
            process.stderr.close()
