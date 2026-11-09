"""Freeze existing Audio Studio effects without loading models or starting jobs."""
from . import audio_catalog, audio_effects, media_library, projects
from .production_ledger import stable_hash

FIELDS = {
    'simple': {'preset', 'strength'},
    'noise_cleanup': {'model', 'use_cache', 'aggressiveness'},
    'voice_repair': {'restoration_mode', 'use_cuda'},
    'voice_changer': {'target_voice_id', 'language', 'refinement_passes', 'max_chunk_duration', 'chunk_method'},
    'rvc': {'model', 'index_file', 'pitch_detection', 'pitch', 'index_ratio', 'consonant_protection',
            'volume_envelope', 'refinement_passes', 'max_chunk_duration', 'chunk_method'},
    'emotion': {'transcript', 'iterations', 'emotion'},
    'style': {'transcript', 'iterations', 'style'},
}


def schema():
    return {'type': 'object', 'additionalProperties': False, 'required': ['operation', 'parameters'],
        'properties': {'operation': {'enum': list(FIELDS)}, 'parameters': {'type': 'object'}}}


def prepare(settings):
    operation, parameters = settings['operation'], settings['parameters']
    if set(parameters) - FIELDS[operation]:
        raise ValueError('Unsupported audio effect settings: ' + ', '.join(sorted(set(parameters) - FIELDS[operation])))
    if any(type(value) not in (str, int, float, bool) for value in parameters.values()):
        raise ValueError('Audio effect settings must be text, numbers or booleans.')
    if operation == 'simple':
        compiled = audio_effects.simple_filter(parameters)
    else:
        compiled = audio_effects.build_workflow(operation=operation, settings=parameters,
            comfy_input_name='validation.wav', filename_prefix='validation')
    snapshot = {'compiled_sha256': stable_hash(compiled)}
    if operation == 'voice_changer':
        path, _ = audio_catalog.voice_audio_path(parameters.get('target_voice_id', ''))
        snapshot['voice_sha256'] = projects.digest(path)
    if operation == 'rvc':
        model = next(row for row in audio_effects.discover_rvc_models()
                     if row['id'] == parameters.get('model', 'Sayano.pth'))
        snapshot['model_sha256'] = projects.digest(model['path'])
        index = next((r for r in model['indexes'] if r['id'] == parameters.get('index_file')), None)
        if index:
            snapshot['index_sha256'] = projects.digest(index['path'])
    return snapshot


def validate_source(root, owner, settings, assets):
    if len(assets) != 1:
        raise ValueError('Select one owned audio source for Audio Studio effects.')
    path, mime, _ = media_library.asset_path(root, owner, assets[0]['asset_id'])
    if not mime.startswith('audio/') or path.suffix.lower() not in audio_effects.AUDIO_SUFFIXES:
        raise ValueError('Audio Studio effects require a supported audio source; extract video audio first.')
    if path.stat().st_size > 250 * 1024**2:
        raise ValueError('Audio effects are limited to 250 MiB per source.')
    audio_effects.validate_duration(settings['operation'], path)
