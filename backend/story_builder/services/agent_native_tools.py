"""Reviewed Director access to existing native job creators; no alternate worker."""
import copy
from contextlib import contextmanager
from contextvars import ContextVar

from . import ace_studio, agent_audio_effects, agent_audio_generation, agent_editor_render, audio_catalog, media_library, projects, trellis_studio, video_repertoire, voice_studio
from .production_ledger import LedgerConflict, stable_hash
from . import agent_analysis_tools, agent_workspace_tools

_CAPTURE = ContextVar('director_native_submission', default=None)
TOOLS = {'music.generate': 'ace-studio', 'voice.speak': 'voice-studio',
         'voice.design': 'voice-studio', '3d.generate': 'trellis', '3d.generate_multiview': 'trellis',
         'audio.effects': 'audio-effects', 'editor.render': 'vibe-editor', **agent_audio_generation.TOOLS, **agent_analysis_tools.TOOLS, **agent_workspace_tools.TOOLS}


def schema(tool):
    if tool in agent_workspace_tools.TOOLS:
        return agent_workspace_tools.schema(tool)
    if tool in agent_analysis_tools.TOOLS:
        return agent_analysis_tools.schema(tool)
    if tool in agent_audio_generation.TOOLS:
        return agent_audio_generation.schema(tool)
    if tool == 'editor.render':
        return {'type': 'object', 'additionalProperties': False, 'required': ['project_id', 'revision'],
            'properties': {'project_id': {'type': 'string'}, 'revision': {'type': 'integer', 'minimum': 0}}}
    if tool == 'audio.effects':
        return agent_audio_effects.schema()
    if tool == '3d.generate_multiview':
        return {'type': 'object', 'additionalProperties': False,
            'required': ['backend', 'preset', 'parameters', 'view_profile', 'views_confirmed'],
            'properties': {'backend': {'enum': ['trellis', 'pixal']},
                'preset': {'enum': ['mv512', 'mvcascade', 'mv1024', 'bounded']},
                'parameters': {'type': 'object'}, 'view_profile': {'enum': ['two', 'four']},
                'views_confirmed': {'const': True}}}
    fields = ({'session_id': {'type': 'string'}, 'revision': {'type': 'integer', 'minimum': 0}}
        if tool == 'music.generate' else
        {'text': {'type': 'string', 'minLength': 1, 'maxLength': 10000},
         'seed': {'type': 'integer', 'minimum': 0, 'maximum': 4294967295},
         **({'voice_id': {'type': 'string'}} if tool == 'voice.speak' else
            {'description': {'type': 'string', 'minLength': 1, 'maxLength': 4000}})}
        if tool.startswith('voice.') else
        {'preset': {'enum': ['bounded', 'detail']}, 'parameters': {
            'type': 'object', 'additionalProperties': False, 'properties': {
                key: {'type': 'integer' if key.endswith('steps') or key in {'seed', 'faces'} else 'number',
                      'minimum': spec[2], 'maximum': spec[3]} for key, spec in trellis_studio.PARAMS.items()}}})
    return {'type': 'object', 'additionalProperties': False, 'required': list(fields), 'properties': fields}


def catalogue():
    descriptions = {'editor.render': 'Render only the current prepared Editor media/tool proposal. Exact task approval authorizes clearance 2 for that frozen revision; never approve it yourself.',
        'audio.foley': 'Generate Foley using mode text_audio, text_video_audio or reference_video_audio. parameters follow the installed Control-Foley settings; references are {} or video_asset_id, then optional audio_asset_id. Preserve originals.',
        'voice.timed_speech': 'Generate timed speech from SRT and named character voice assignments. parameters use the installed timed-TTS settings; no media attachments.',
        'music.generate': 'Generate the reviewed ACE music session; never train a LoRA.',
        'voice.speak': 'Speak text with an installed reference voice.',
        'voice.design': 'Generate speech with a described voice.',
        '3d.generate': 'Generate one TRELLIS model from one owned image.',
        '3d.generate_multiview': 'Generate one TRELLIS/Pixal3D model from reviewed views: two = front/back; four = front/left/back/right. Attach distinct images in that order with matching canvas dimensions.',
        'audio.effects': 'Apply an existing Audio Studio effect to one audio source. Parameters: simple(preset,strength), noise_cleanup(model,use_cache,aggressiveness), voice_repair(restoration_mode,use_cuda), voice_changer(target_voice_id,language,refinement_passes,max_chunk_duration,chunk_method), rvc(model,index_file,pitch_detection,pitch,index_ratio,consonant_protection,volume_envelope,refinement_passes,max_chunk_duration,chunk_method), emotion(transcript,iterations,emotion), style(transcript,iterations,style). Use installed voice/model IDs; ask for an exact transcript for emotion/style.'}
    descriptions.update(agent_analysis_tools.descriptions())
    descriptions.update(agent_workspace_tools.DESCRIPTIONS)
    rows = [{'id': tool, 'effect': 'submit', 'status': 'available', 'execution_enabled': True,
        'description': descriptions[tool], 'reason': 'Exact task approval required. Installed model readiness and shared GPU guards are checked by the existing native tool at execution.',
        'accepted_media': ['image', 'video', 'audio'] if tool in agent_analysis_tools.TOOLS or tool in agent_workspace_tools.TOOLS else ['image'] if tool.startswith('3d.') else ['audio', 'video'] if tool == 'audio.foley' else ['image', 'video', 'audio'] if tool == 'editor.render' else ['audio'] if tool == 'audio.effects' else [], 'scope': 'frozen_native_request',
        'runtime': kind, 'approval': 'exact_plan', 'result_kind': 'native_job_result',
        'input_schema': {'type': 'object', 'additionalProperties': False, 'required': ['asset_ids', 'settings'],
            'properties': {'asset_ids': {'type': 'array', 'items': {'type': 'string'},
                'minItems': 2 if tool == '3d.generate_multiview' else 1 if tool in {'3d.generate', 'audio.effects'} else 0,
                'maxItems': 100 if tool == 'editor.render' or tool in agent_analysis_tools.TOOLS or tool in agent_workspace_tools.TOOLS else 2 if tool == 'audio.foley' else 4 if tool == '3d.generate_multiview' else 1 if tool in {'3d.generate', 'audio.effects'} else 0,
                'uniqueItems': True},
                'settings': schema(tool)}}} for tool, kind in TOOLS.items()]
    for row in rows:
        inputs = {**agent_analysis_tools.INPUTS, **agent_workspace_tools.INPUTS}.get(row['id'])
        if inputs:
            prefix, low, high = inputs
            row['input_schema']['properties']['asset_ids'].update(minItems=low, maxItems=high)
            row['accepted_media'] = [prefix.removesuffix('/')] if prefix else ['image', 'video', 'audio'] if high else []
    return rows


def prepare(root, owner, tool, settings, *, call=None):
    if tool in agent_workspace_tools.TOOLS:
        return {**copy.deepcopy(settings), 'snapshot': agent_workspace_tools.prepare(root, owner, tool, settings)}
    if tool in agent_analysis_tools.TOOLS:
        snapshot = agent_analysis_tools.prepare(root, owner, tool, settings)
        return {**copy.deepcopy(settings), 'snapshot': snapshot}
    fields = schema(tool)['properties']
    if not isinstance(settings, dict) or set(settings) != set(fields):
        raise ValueError('Supply exactly the native tool settings: ' + ', '.join(fields))
    for key, spec in fields.items():
        value = settings[key]
        kind = spec.get('type')
        if (kind == 'string' and (not isinstance(value, str) or not spec.get('minLength', 1) <= len(value) <= spec.get('maxLength', 200))
                or kind == 'integer' and (type(value) is not int or not spec.get('minimum', 0) <= value <= spec.get('maximum', 2**53))
                or kind == 'object' and not isinstance(value, dict)
                or kind == 'array' and (not isinstance(value, list) or not spec.get('minItems', 0) <= len(value) <= spec.get('maxItems', 200))
                or 'const' in spec and value is not spec['const']
                or 'enum' in spec and value not in spec['enum']):
            raise ValueError('Invalid native setting: ' + key)
    settings = copy.deepcopy(settings)
    if tool in agent_audio_generation.TOOLS:
        settings['snapshot'] = agent_audio_generation.prepare(tool, settings, call)
    elif tool == 'editor.render':
        settings['snapshot'] = agent_editor_render.prepare(root, owner, settings)
    elif tool == 'audio.effects':
        settings['snapshot'] = agent_audio_effects.prepare(settings)
    elif tool == 'music.generate':
        with ace_studio.state(root) as data:
            p = ace_studio.project(data, settings['session_id'])
            ace_studio.unlocked(p)
            if p['workspace_id'] != owner or p['revision'] != settings['revision']:
                raise LedgerConflict('Music session ownership or revision changed. Reload it.')
            if p['intent'] != 'generate' or p['questions'] or p.get('confirmed_revision') == p['revision']:
                raise ValueError('Review the music draft and answer its questions before proposing generation.')
            settings['snapshot'] = {k: copy.deepcopy(p[k]) for k in ('settings', 'intent', 'questions')}
            if p['settings'].get('task', 'text') != 'text':
                path, _, _ = ace_studio.reference(root, p)
                settings['snapshot']['reference_sha256'] = projects.digest(path)
    elif tool.startswith('voice.'):
        voice_studio.compile_graph({'operation': 'speech' if tool == 'voice.speak' else 'design', **settings}, 'validation')
        if tool == 'voice.speak':
            path, _ = audio_catalog.voice_audio_path(settings['voice_id'])
            transcript = audio_catalog._reference_transcript(path)
            if transcript is None:
                raise ValueError('Selected voice transcript is unavailable.')
            settings['snapshot'] = {'audio_sha256': projects.digest(path), 'transcript_sha256': projects.digest(transcript)}
    elif tool == '3d.generate_multiview':
        from . import multiview_3d as multi
        if settings['backend'] == 'pixal':
            if settings['preset'] != 'bounded':
                raise ValueError('Pixal3D uses the bounded preset.')
            compiled = multi.pixal_graph(settings['view_profile'], settings['parameters'],
                {v: 'validation.png' for v in multi.VIEWS[settings['view_profile']]}, 'validation')
        else:
            compiled = multi.remote_settings(settings['preset'], settings['parameters'])
        settings['snapshot'] = {'compiled_sha256': stable_hash(compiled)}
    else:
        trellis_studio.compile_graph(settings['preset'], settings['parameters'], 'validation.png', 'validation')
    return settings


def check(root, owner, tool, settings, *, call=None):
    original = {k: v for k, v in settings.items() if k != 'snapshot'}
    if prepare(root, owner, tool, original, call=call) != settings:
        raise LedgerConflict('Native tool settings changed. Review a new proposal.')


def validate_images(root, owner, tool, settings, assets):
    """Validate before staging or allocating a job; never change a source image."""
    from PIL import Image, ImageOps
    from .multiview_3d import VIEWS
    count = len(VIEWS[settings['view_profile']]) if tool == '3d.generate_multiview' else 1
    if len(assets) != count or len({a['asset_id'] for a in assets}) != count:
        raise ValueError(f'Select {count} distinct owned images in the documented view order.')
    sizes = []
    for asset in assets:
        path, _, _ = media_library.asset_path(root, owner, asset['asset_id'])
        if path.stat().st_size > 40 * 1024**2:
            raise ValueError('3D input images must be 40 MiB or smaller.')
        with Image.open(path) as image:
            if image.width * image.height > 40000000:
                raise ValueError('3D input images must be 40 megapixels or smaller.')
            sizes.append(ImageOps.exif_transpose(image).size)
    if len(set(sizes)) != 1:
        raise ValueError('Views must have matching canvas dimensions; pad/align them first.')


@contextmanager
def capture(owner, plan, invocation, created):
    token = _CAPTURE.set((owner, plan, invocation, created))
    try:
        yield
    finally:
        _CAPTURE.reset(token)


def correlate(kind, request):
    active = _CAPTURE.get()
    if not active:
        return request
    owner, plan, invocation, _ = active
    if kind != TOOLS[plan['tool_id']] or request.get('workspace_id') != owner:
        raise LedgerConflict('Native job does not belong to the approved operation/project.')
    return {**request, 'agent_invocation_id': invocation,
            'agent_plan': copy.deepcopy(plan)}


def created(job):
    active = _CAPTURE.get()
    if active:
        active[3](job)  # Durable mapping precedes native dispatch.


def submit(root, owner, plan, invocation, on_created, *, call=None):
    tool, settings = plan['tool_id'], plan['settings']
    with capture(owner, plan, invocation, on_created):
        if tool in agent_workspace_tools.TOOLS:
            return agent_workspace_tools.submit(root, owner, tool, settings, plan['assets'])
        if tool in agent_analysis_tools.TOOLS:
            if call is None:
                raise ValueError('Media Prep bridge is unavailable.')
            agent_analysis_tools.validate_assets(root, owner, tool, settings, plan['assets'])
            return agent_analysis_tools.submit(call, owner, tool, settings, plan['assets'])
        if tool in agent_audio_generation.TOOLS:
            agent_audio_generation.validate_assets(root, owner, tool, settings, plan['assets'])
            result = agent_audio_generation.submit(call, owner, tool, settings)
            return video_repertoire.read_job(TOOLS[tool], result['job_id'])
        if tool == 'editor.render':
            result = agent_editor_render.submit(root, settings)
            return video_repertoire.read_job('vibe-editor', result['job_id'])
        if tool == 'audio.effects':
            if call is None:
                raise ValueError('Audio Studio bridge is unavailable.')
            agent_audio_effects.validate_source(root, owner, settings, plan['assets'])
            result = call('POST', f'/api/audio/{owner}/effects/jobs', {
                'operation': settings['operation'], 'settings': settings['parameters'],
                'asset_id': plan['assets'][0]['asset_id']})
            return video_repertoire.read_job('audio-effects', result['job_id'])
        if tool == 'music.generate':
            p = ace_studio.command(root, settings['session_id'], {'action': 'confirm', 'revision': settings['revision']})
            return video_repertoire.read_job('ace-studio', p['job_id'])
        if tool.startswith('voice.'):
            return voice_studio.create(root, {'workspace_id': owner,
                'operation': 'speech' if tool == 'voice.speak' else 'design',
                **{k: v for k, v in settings.items() if k != 'snapshot'}})
        validate_images(root, owner, tool, settings, plan['assets'])
        staged = []
        try:
            for asset in plan['assets']:
                path, _, _ = media_library.asset_path(root, owner, asset['asset_id'])
                staged.append(trellis_studio.upload(root, path.read_bytes())['id'])
            extra = {}
            item = {'id': staged[0], 'name': plan['assets'][0]['filename']}
            if tool == '3d.generate_multiview':
                from .multiview_3d import VIEWS
                item['views'] = dict(zip(VIEWS[settings['view_profile']], staged))
                extra = {k: settings[k] for k in ('backend', 'view_profile', 'views_confirmed')}
                extra['input_mode'] = 'multiview'
            return trellis_studio.create(root, {'workspace_id': owner, 'mode': 'single', **extra,
                'preset': settings['preset'], 'settings': settings['parameters'],
                'items': [item]})
        except Exception:
            # Only our newly created staging image is eligible for removal, and only
            # before a durable job claims it. Never remove registered project media.
            if not any(j.get('request', {}).get('agent_invocation_id') == invocation
                       for j in video_repertoire.list_jobs('trellis')):
                for token in staged:
                    trellis_studio.image_path(root, token).unlink(missing_ok=True)
            raise


def validate_job(row, job):
    request = job.get('request', {})
    if (job.get('kind') != TOOLS[row['plan']['tool_id']] or request.get('workspace_id') != row['project_id']
            or request.get('agent_invocation_id') != row['invocation']['invocation_id']
            or request.get('agent_plan') != row['plan']
            or row['invocation']['job_id'] and job['job_id'] != row['invocation']['job_id']):
        raise LedgerConflict('Native job does not match its frozen Director invocation.')
