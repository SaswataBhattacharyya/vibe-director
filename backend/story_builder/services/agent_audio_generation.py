"""Freeze Foley/timed-speech inputs; submission stays in the existing job routes."""
from . import audio_catalog, audio_tts, control_foley, media_library, projects
from .production_ledger import stable_hash

TOOLS = {'audio.foley': 'control-foley', 'voice.timed_speech': 'timed-tts'}


def schema(tool):
    fields = ({'parameters': {'type': 'object'}, 'references': {'type': 'object'}}
              if tool == 'audio.foley' else
              {'srt_content': {'type': 'string', 'minLength': 1, 'maxLength': 500000},
               'characters': {'type': 'array', 'minItems': 1, 'maxItems': 200, 'items': {'type': 'object'}},
               'parameters': {'type': 'object'}})
    return {'type': 'object', 'additionalProperties': False, 'required': list(fields), 'properties': fields}


def prepare(tool, settings, call):
    if tool == 'audio.foley':
        parameters = settings['parameters']
        allowed = {'mode', 'prompt', 'negative_prompt', 'duration', 'seed', 'steps', 'guidance', 'fps', 'device', 'precision'}
        if set(parameters) - allowed:
            raise ValueError('Unknown Foley parameter.')
        job = control_foley.new_job(parameters)
        mode = job['settings']['mode']
        required = [] if mode == 'text_audio' else ['video_asset_id'] if mode == 'text_video_audio' else ['video_asset_id', 'audio_asset_id']
        if set(settings['references']) != set(required) or any(type(settings['references'][k]) is not str for k in required):
            raise ValueError('Foley references must match its mode: ' + ', '.join(required))
        job.update(job_id='validation', inputs={'video': 'validation.mp4', 'reference_audio': 'validation.wav'})
        if call is None:
            raise ValueError('Foley workflow guidance bridge is unavailable.')
        workflow = f'control_foley_{mode}_v1'
        guidance = call('GET', f'/api/workflow-guidance?workflow_id={workflow}&model_id=control_foley')
        if guidance.get('retrieval_status') != 'matched':
            raise ValueError('Foley workflow guidance is unavailable; review the installed workflow first.')
        return {'compiled_sha256': stable_hash(control_foley.build_workflow(job)),
                'prompt_knowledge_ref': {k: guidance[k] for k in ('knowledge_id', 'guidance_version', 'workflow_sha256')}}
    characters = settings['characters']
    if not 1 <= len(characters) <= 200 or any(not isinstance(c, dict) or set(c) - {'name', 'reference_voice_id', 'language'}
            or any(type(c.get(k)) is not str or not c[k].strip() for k in ('name', 'reference_voice_id')) for c in characters):
        raise ValueError('Assign each named character an installed reference_voice_id and optional language.')
    if len({c['name'].strip().casefold() for c in characters}) != len(characters):
        raise ValueError('Character names must be distinct.')
    allowed = {'timing_mode', 'language', 'seed', 'exaggeration', 'temperature', 'cfg_weight', 'fade',
               'max_stretch_ratio', 'min_stretch_ratio', 'timing_tolerance', 'batch_size', 'enable_audio_cache'}
    if set(settings['parameters']) - allowed:
        raise ValueError('Unknown timed-speech parameter.')
    rewritten, resolved = audio_tts.prepare_srt(settings['srt_content'], characters, audio_catalog.discover_voices())
    graph = audio_tts.build_workflow(rewritten_srt=rewritten, narrator=resolved['narrator'], settings=settings['parameters'], filename_prefix='validation')
    hashes = {}
    for character in characters:
        source, _ = audio_catalog.voice_audio_path(character['reference_voice_id'])
        hashes[character['reference_voice_id']] = projects.digest(source)
    return {'compiled_sha256': stable_hash(graph), 'voice_sha256': hashes}


def validate_assets(root, owner, tool, settings, assets):
    refs = {k: settings['references'][k] for k in ('video_asset_id', 'audio_asset_id') if k in settings.get('references', {})}
    if [a['asset_id'] for a in assets] != list(refs.values()):
        raise ValueError('Attach Foley references in video, then audio order; timed speech uses no attachments.')
    for key, asset in zip(refs, assets):
        _, mime, _ = media_library.asset_path(root, owner, asset['asset_id'])
        if not mime.startswith('video/' if key == 'video_asset_id' else 'audio/'):
            raise ValueError('Foley reference media type does not match ' + key)


def submit(call, owner, tool, settings):
    if call is None:
        raise ValueError('Audio job bridge is unavailable.')
    if tool == 'audio.foley':
        return call('POST', f'/api/audio/{owner}/control-foley/jobs', {
            'settings': settings['parameters'], 'references': settings['references'],
            'prompt_knowledge_ref': settings['snapshot']['prompt_knowledge_ref']})
    return call('POST', f'/api/audio/{owner}/timed-tts/jobs', {
        'srt_content': settings['srt_content'], 'characters': settings['characters'], 'settings': settings['parameters']})
