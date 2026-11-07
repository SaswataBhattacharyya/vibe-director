"""CPU-only, offline timed speech evidence through the installed analyzer image."""
import json
import math
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from . import media_library, projects, video_repertoire
from .audio_utilities import UtilityUnavailable, WorkerUnavailable
from .video_summarizer_capability import _image_status

KIND = 'agent-transcription'
IMAGE = 'video-audio-analyzer-peav:dev'
LABEL = 'vibe-director.transcription-job'


def model_path():
    return Path(video_repertoire.ANALYZER_ROOT) / 'models/faster-whisper-large-v3'


def capability():
    reason = None
    if not all(shutil.which(tool) for tool in ('ffmpeg', 'ffprobe')):
        reason = 'FFmpeg and FFprobe are required for complete-source speech analysis.'
    elif not all((model_path() / name).is_file() for name in ('config.json', 'model.bin', 'tokenizer.json')):
        reason = 'Prepared faster-whisper-large-v3 model files are missing from the configured Video Analyzer.'
    else:
        reason = _image_status(IMAGE, subprocess.run)['reason']
    return {'status': 'blocked' if reason else 'available', 'execution_enabled': not bool(reason),
            'reason': reason or 'Offline CPU transcription of one complete source. Exact-plan approval required; no automatic cuts.'}


def submit(root, owner, assets, invocation, on_created):
    ready = capability()
    if not ready['execution_enabled']:
        raise UtilityUnavailable(ready['reason'])
    if Path(root).resolve() != video_repertoire._CONFIGURED_DATA_ROOT:
        raise ValueError('Transcription job storage is configured for a different data root.')
    job = video_repertoire.create_job(KIND, {'workspace_id': owner, 'agent_invocation_id': invocation,
        'operation': 'transcribe', 'settings': {}, 'inputs': assets})
    on_created(job)
    try:
        return video_repertoire.start_job(KIND, job['job_id'])
    except Exception as exc:
        raise WorkerUnavailable(str(exc)) from exc


# Static host-owned worker; there are no model-authored commands or remote downloads.
WORKER = '''import json
from faster_whisper import WhisperModel
model=WhisperModel('/models',device='cpu',compute_type='int8',cpu_threads=4,local_files_only=True)
segments,info=model.transcribe('/input/source.wav',word_timestamps=True,vad_filter=True)
rows=[]
for segment in segments:
 rows.append({'start':segment.start,'end':segment.end,'text':segment.text,
  'avg_logprob':segment.avg_logprob,'no_speech_prob':segment.no_speech_prob,
  'words':[{'start':w.start,'end':w.end,'text':w.word,'probability':w.probability} for w in (segment.words or [])]})
print(json.dumps({'language':info.language,'language_probability':info.language_probability,'segments':rows}))
'''


def validate(result, source):
    """Reject fabricated, mismatched or malformed timing evidence before displaying it."""
    if (not isinstance(result, dict) or result.get('asset_id') != source['asset_id']
            or result.get('sha256') != source['sha256'] or result.get('scope') != 'whole_source'
            or result.get('device') != 'cpu' or result.get('model') != 'faster-whisper-large-v3'):
        raise ValueError('Transcript does not match the approved complete source.')
    duration = result.get('duration_seconds')
    if type(duration) not in (int, float) or not math.isfinite(duration) or duration <= 0:
        raise ValueError('Transcript source duration is invalid.')
    if (not isinstance(result.get('language'), str) or type(result.get('language_probability')) not in (int, float)
            or not 0 <= result['language_probability'] <= 1):
        raise ValueError('Transcript language confidence is invalid.')
    segments = result.get('segments')
    if not isinstance(segments, list) or len(segments) > 20000:
        raise ValueError('Transcript segments are invalid or exceed the review limit.')
    previous = 0
    for row in segments:
        if not isinstance(row, dict) or not isinstance(row.get('text'), str) or len(row['text']) > 12000:
            raise ValueError('Transcript text is invalid.')
        words = row.get('words')
        if not isinstance(words, list) or len(words) > 12000:
            raise ValueError('Transcript words are invalid.')
        for item in [row, *words]:
            if (not isinstance(item, dict) or any(type(item.get(k)) not in (int, float)
                    or not math.isfinite(item[k]) for k in ('start', 'end'))
                    or not 0 <= item['start'] <= item['end'] <= duration + .1):
                raise ValueError('Transcript timestamps are outside the complete source.')
        if any(not isinstance(w.get('text'), str) or not row['start'] <= w['start'] <= w['end'] <= row['end'] for w in words):
            raise ValueError('Transcript words do not match their segment.')
        if row['start'] < previous:
            raise ValueError('Transcript segments are out of source order.')
        previous = row['start']
        for key in ('avg_logprob', 'no_speech_prob'):
            if type(row.get(key)) not in (int, float) or not math.isfinite(row[key]):
                raise ValueError('Transcript confidence evidence is missing.')
        if not 0 <= row['no_speech_prob'] <= 1 or any(
                type(w.get('probability')) not in (int, float) or not 0 <= w['probability'] <= 1 for w in row.get('words', [])):
            raise ValueError('Transcript probabilities are invalid.')
    return result


def run(root, job_id, request):
    if request.get('operation') != 'transcribe' or request.get('settings') != {} or len(request['inputs']) != 1:
        raise ValueError('Transcription requires one approved complete source and empty settings.')
    ready = capability()
    if not ready['execution_enabled']:
        raise UtilityUnavailable(ready['reason'])
    source = request['inputs'][0]
    path, mime, _ = media_library.asset_path(root, request['workspace_id'], source['asset_id'])
    if not mime.startswith(('audio/', 'video/')) or projects.digest(path) != source['sha256']:
        raise ValueError('Approved speech source changed or is unavailable.')
    # An immutable private copy avoids a live file changing while the analyzer reads it.
    with tempfile.TemporaryDirectory(prefix='vibe-speech-') as folder:
        staged = Path(folder) / ('original' + path.suffix)
        shutil.copyfile(path, staged)
        if projects.digest(staged) != source['sha256']:
            raise ValueError('Speech source changed during staging.')
        subprocess.run(['ffmpeg', '-v', 'error', '-nostdin', '-i', str(staged), '-vn', '-ac', '1', '-ar', '16000',
                        str(Path(folder) / 'source.wav')], check=True, capture_output=True, timeout=3600)
        duration = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'default=nw=1:nk=1', str(Path(folder) / 'source.wav')], check=True,
            capture_output=True, text=True, timeout=30).stdout)
        try:
            process = subprocess.run(['docker', 'run', '--rm', '--network', 'none', '--read-only',
                '--cpus', '4', '--memory', '12g', '--pids-limit', '256', '--cap-drop', 'ALL',
                '--security-opt', 'no-new-privileges',
                '--label', f'{LABEL}={job_id}', '--user', f'{os.getuid()}:{os.getgid()}',
                '--tmpfs', '/tmp:rw,nosuid,size=512m', '-e', 'HOME=/tmp', '-e', 'HF_HUB_OFFLINE=1',
                '--mount', f'type=bind,src={Path(folder).resolve()},dst=/input,readonly',
                '--mount', f'type=bind,src={model_path().resolve()},dst=/models,readonly',
                '--entrypoint', 'python', IMAGE, '-c', WORKER], capture_output=True, text=True, timeout=7200)
            if process.returncode:
                raise RuntimeError('CPU speech analyzer failed: ' + process.stderr[-2000:])
            if len(process.stdout) > 20_000_000:
                raise ValueError('Transcript exceeds the supported evidence size.')
            result = json.loads(process.stdout)
        finally:
            video_repertoire._stop_job_containers(job_id, LABEL)
    result.update(asset_id=source['asset_id'], sha256=source['sha256'], scope='whole_source',
                  device='cpu', model='faster-whisper-large-v3', duration_seconds=duration)
    return {'workspace_id': request['workspace_id'], 'transcript': validate(result, source)}


def report(result, source):
    transcript = validate(result, source)
    rows = transcript['segments']
    text = '\n'.join(f"{s['start']:.3f}–{s['end']:.3f}s: {s['text'].strip()} "
        f"[log probability {s['avg_logprob']:.3f}; no-speech probability {s['no_speech_prob']:.3f}]" for s in rows)
    return (f"Complete source analyzed on CPU ({transcript['duration_seconds']:.3f}s). Source-relative timestamps; "
            'ASR confidence is evidence, not a determination that speech is gibberish. Review against playback. '
            'No cuts or render have been approved.\n' + (text[:58000] or 'No speech segments detected.')
            + ('\nReview truncated; the complete transcript remains in the durable job result.' if len(text) > 58000 else ''))
