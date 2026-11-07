"""Shared CPU-only studio discussion; suggestions never submit jobs."""
import json
import math
from . import reasoning_provider, trellis_studio, multiview_3d


def suggest(text, context, history, provider=None):
    if not isinstance(text, str) or not 0 < len(text) <= 8000:
        raise ValueError('Message must contain 1–8000 characters.')
    if not isinstance(context, dict) or len(json.dumps(context)) > 12000:
        raise ValueError('Supply bounded studio context.')
    settings = context.get('settings', context)
    if not isinstance(settings, dict):
        raise ValueError('Supply studio settings as an object.')
    keys = ({'seed', 'fov', 'faces'} if settings.get('backend') == 'pixal' else
            multiview_3d.REMOTE_PARAMS if settings.get('input_mode') == 'multiview' else trellis_studio.PARAMS)
    if settings.get('activity') is not None:
        keys = set()  # Audio's existing discussion has no settings Apply operation.
    schema = {'type': 'object', 'additionalProperties': False, 'required': ['reply', 'settings'], 'properties': {
        'reply': {'type': 'string'}, 'settings': {'type': 'object', 'additionalProperties': False,
            'properties': {key: {'type': 'number'} for key in keys}}}}
    result = (provider or reasoning_provider.generate_json)(
        prompt='You are the Vibe Director studio assistant. Discuss the request; never run tools or start generation. '
        'TRELLIS is image-conditioned, not text-conditioned. Suggest only explicitly requested supported settings '
        'for the selected backend and input mode, using only schema keys; otherwise settings must be empty. '
        'Attachments supply filenames only, never visual analysis. Return reply and settings. Current context: '
        + json.dumps(context) + '\nRecent conversation: ' + json.dumps(history)[-16000:] + '\nUser: ' + text,
        output_schema=schema, cpu_only=True)
    if (not isinstance(result, dict) or not isinstance(result.get('reply'), str) or not 0 < len(result['reply']) <= 16000
            or not isinstance(result.get('settings'), dict) or set(result['settings']) - set(keys)
            or any(type(value) not in (int, float) or not math.isfinite(value) for value in result['settings'].values())):
        raise ValueError('Studio returned invalid settings guidance.')
    return result


def target(owner, value):
    if (not isinstance(value, dict) or set(value) != {'version', 'workspace_id', 'name', 'context', 'history'}
            or type(value['version']) is not int or value['version'] != 1 or value['workspace_id'] != owner
            or value['name'] not in {'trellis', 'audio'} or not isinstance(value['context'], dict)
            or not isinstance(value['history'], list) or len(value['history']) > 12 or len(json.dumps(value)) > 28000):
        raise ValueError('Supply a versioned studio target owned by the current project.')
    return value
