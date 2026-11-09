"""Typed adapters to the existing Media Prep job creators, not new workers."""
import json
from . import audio_scene, media_library, video_repertoire
from .production_ledger import stable_hash

TOOLS = {'image.analyze': 'image-detailer', 'video.analyze': 'analysis',
         'media.index_content': 'semantic-index', 'audio.split_scene': 'audio-scene-split',
         'audio.stitch_scene': 'audio-scene-stitch', 'media.download_youtube': 'youtube',
         'video.extract_style_frames': 'style-frames'}


INPUTS = {'image.analyze': ('image/', 1, 1), 'video.analyze': ('video/', 1, 20),
    'media.index_content': ('', 1, 1), 'audio.split_scene': ('audio/', 1, 1),
    'audio.stitch_scene': ('audio/', 0, 100), 'media.download_youtube': ('', 0, 0),
    'video.extract_style_frames': ('video/', 1, 1)}

def schema(tool):
    fields = {
        'image.analyze': {'mode': {'enum': ['quick', 'balanced', 'deep']}},
        'video.analyze': {'parameters': {'type': 'object'}},
        'media.index_content': {},
        'audio.split_scene': {'edits': {'type': 'array', 'minItems': 1, 'maxItems': 500,
            'items': {'type': 'object', 'additionalProperties': False, 'required': ['start', 'end', 'text'],
                'properties': {'start': {'type': 'number', 'minimum': 0}, 'end': {'type': 'number', 'exclusiveMinimum': 0}, 'text': {'type': 'string'}}}},
            'transcript': {'type': 'string', 'maxLength': 500000}},
        'audio.stitch_scene': {'split_job_id': {'type': 'string'}, 'replacement_asset_ids': {'type': 'object', 'additionalProperties': {'type': 'string'}},
            'gaps': {'type': 'object', 'additionalProperties': {'type': 'number', 'minimum': 0, 'maximum': 3600}}, 'mode': {'enum': ['simple', 'timed']}},
        'media.download_youtube': {'urls': {'type': 'array', 'minItems': 1, 'maxItems': 25, 'items': {
            'type': 'object', 'additionalProperties': False, 'required': ['url'], 'properties': {
                key: {'type': 'string'} for key in ('url', 'title', 'channel', 'video_id')}}}},
        'video.extract_style_frames': {'directing_style_id': {'type': 'string'},
            'timestamps_seconds': {'type': 'array', 'minItems': 1, 'maxItems': 100, 'items': {'type': 'number', 'minimum': 0}}},
    }[tool]
    return {'type': 'object', 'additionalProperties': False, 'required': list(fields), 'properties': fields}


def prepare(root, owner, tool, settings):
    from jsonschema import validate, ValidationError
    try:
        json.dumps(settings, allow_nan=False)
        validate(settings, schema(tool))
    except (ValidationError, ValueError, TypeError) as exc:
        raise ValueError('Invalid ' + tool + ' settings: ' + str(exc)) from exc
    if tool == 'audio.split_scene':
        audio_scene.validate_edits(settings['edits'])
    if tool == 'audio.stitch_scene':
        job = video_repertoire.read_job('audio-scene-split', settings['split_job_id'])
        if job['request'].get('workspace_id') != owner or job['status'] != 'completed':
            raise ValueError('Choose a completed split job from this project.')
        return {'split_sha256': stable_hash(job['result'])}
    if tool == 'video.analyze' and settings['parameters'].get('analysis_backend', 'video_audio_analyzer') != 'video_audio_analyzer':
        raise ValueError('Choose the installed video_audio_analyzer backend.')
    if tool == 'media.download_youtube':
        from urllib.parse import urlsplit
        for item in settings['urls']:
            url = urlsplit(item['url'])
            host = (url.hostname or '').lower()
            if url.scheme not in {'http', 'https'} or url.username or url.password or not (host in {'youtube.com', 'youtu.be'} or host.endswith('.youtube.com')):
                raise ValueError('Only YouTube and youtu.be links are supported.')
    return {}


def validate_assets(root, owner, tool, settings, assets):
    prefix, low, high = INPUTS[tool]
    if not low <= len(assets) <= high:
        raise ValueError(f'{tool} requires {low}–{high} owned sources.')
    for asset in assets:
        path, mime, _ = media_library.asset_path(root, owner, asset['asset_id'])
        if not mime.startswith(prefix):
            raise ValueError(tool + ' requires ' + prefix + ' sources.')
        if tool == 'audio.split_scene':
            duration = media_library._probe(path, 'audio')['duration_seconds']
            if any(e['end'] > duration + .05 for e in settings['edits']):
                raise ValueError('Audio edit exceeds the source duration.')
    if tool == 'audio.stitch_scene' and set(settings['replacement_asset_ids'].values()) != {a['asset_id'] for a in assets}:
        raise ValueError('Attach exactly the replacement audio sources named in this stitch.')


def submit(call, owner, tool, settings, assets):
    ids = [a['asset_id'] for a in assets]
    if tool == 'image.analyze':
        path, body = f'/api/image-detailer/{owner}/jobs', {'asset_id': ids[0], 'mode': settings['mode']}
    elif tool == 'video.analyze':
        path, body = f'/api/video-summariser/{owner}/analysis/jobs', {'asset_ids': ids, 'settings': settings['parameters']}
    elif tool == 'media.index_content':
        path, body = f'/api/media/{owner}/assets/{ids[0]}/semantic-content-index', {}
    elif tool == 'audio.split_scene':
        path, body = f'/api/audio/{owner}/scene-surgery/jobs', {'asset_id': ids[0], 'edits': settings['edits'], 'transcript': settings['transcript']}
    elif tool == 'audio.stitch_scene':
        path, body = f'/api/audio/{owner}/scene-surgery/stitch-jobs', {k: v for k, v in settings.items() if k != 'snapshot'}
    elif tool == 'media.download_youtube':
        path, body = f'/api/video-summariser/{owner}/youtube/jobs', {'urls': settings['urls']}
    else:
        path, body = f'/api/media/{owner}/assets/{ids[0]}/style-frames', {k: v for k, v in settings.items() if k != 'snapshot'}
    result = call('POST', path, body)
    return video_repertoire.read_job(TOOLS[tool], result['job_id'])


def descriptions():
    return {'image.analyze': 'Analyze one image through Image Detailer; use the completed job as visual evidence.',
        'video.analyze': 'Analyze complete videos with the installed Video/Audio Analyzer, including scene/frame/audio evidence. Native readiness and GPU admission apply.',
        'media.index_content': 'Build the existing semantic content index for one owned image, audio or video.',
        'audio.split_scene': 'Split one audio source into explicit reviewed timestamp ranges; preserve the original.',
        'audio.stitch_scene': 'Stitch a completed owned scene split with optional replacement audio and gaps.',
        'media.download_youtube': 'Download selected YouTube URLs into Media Prep using its existing durable job.',
        'video.extract_style_frames': 'Extract timestamped frames for an already selected directing style.'}
