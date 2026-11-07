"""Service-backed descriptions only. Discovery never authorizes execution."""
import shutil
from . import agent_transcription, audio_utilities

_CONTRACTS = {
    'audio.extract_mp3': ('Extract audio from complete audio/video sources into MP3 files.',
                         ['audio', 'video'], 'whole_source', 'ffmpeg', 'registered_audio'),
    'video.continuity_last_frame': ('Extract one video’s final frame as a continuity reference.',
                                    ['video'], 'whole_source', 'ffmpeg', 'registered_image'),
    'editor.prepare_brief': ('Prepare an edit brief for review; cannot analyze speech, approve cuts or render.',
                             ['audio', 'video', 'image'], 'saved_editor_selection', 'reasoning_provider', 'pending_editor_brief'),
    'computer.execute': ('Run an explicitly approved coding, terminal or filesystem task.',
                         [], 'explicit_access_mode', 'codex_cli', 'verified_report'),
    'audio.transcribe': ('Transcribe one complete source on CPU with timed speech and confidence evidence; review required before cuts.',
                         ['audio', 'video'], 'whole_source', 'video-audio-analyzer-peav:dev', 'timed_transcript'),
    'audio.noise_cleanup': ('Denoise audio using the installed denoiser. Requires GPU admission at execution.',
                           ['audio'], 'whole_source', 'story-audio-denoiser', 'registered_audio'),
    'audio.demucs_stems': ('Separate vocals and accompaniment from audio using Demucs on CPU.',
                         ['audio'], 'whole_source', 'story-audio-demucs', 'registered_audio'),
}


def tools() -> dict:
    ready = bool(shutil.which('ffmpeg'))
    asset_ids = {'type': 'array', 'minItems': 1, 'maxItems': 100, 'items': {'type': 'string', 'minLength': 1}}
    rows = [
        {'id': 'audio.extract_mp3', 'effect': 'submit', 'input_schema': {
            'type': 'object', 'additionalProperties': False, 'required': ['asset_ids', 'settings'],
            'properties': {'asset_ids': asset_ids, 'settings': {'type': 'object', 'additionalProperties': False,
                'properties': {'quality': {'type': 'integer', 'minimum': 0, 'maximum': 9, 'default': 2}}}}}},
        {'id': 'video.continuity_last_frame', 'effect': 'submit', 'input_schema': {
            'type': 'object', 'additionalProperties': False, 'required': ['asset_ids', 'settings'],
            'properties': {'asset_ids': {**asset_ids, 'maxItems': 1},
                'settings': {'type': 'object', 'additionalProperties': False, 'properties': {}}}}},
    ]
    for row in rows:
        row.update(status='available' if ready else 'blocked', execution_enabled=ready)
        if not ready:
            row['reason'] = 'ffmpeg is unavailable.'
    if ready:
        for row in rows:
            row['reason'] = 'Propose a task, approve its exact plan, then run it through the shared task gateway.'
    operations = {row['id']: row for row in audio_utilities.capabilities()['operations']}
    for operation, settings in (
        ('noise_cleanup', {'model': {'enum': ['master64', 'dns64'], 'default': 'master64'},
                           'dry': {'type': 'number', 'minimum': 0, 'maximum': 1, 'default': 0}}),
        ('demucs_stems', {'stems': {'enum': [2, 4, 6], 'default': 2},
                          'device': {'const': 'cpu', 'default': 'cpu'}}),
    ):
        readiness = operations.get(operation, {})
        available = readiness.get('status') == 'available'
        rows.append({'id': 'audio.' + operation, 'effect': 'submit',
            'status': 'available' if available else 'blocked', 'execution_enabled': available,
            'reason': 'Requires exact-plan approval; preserves originals.' if available else readiness.get('reason', 'Audio runtime is unavailable.'),
            'input_schema': {'type': 'object', 'additionalProperties': False, 'required': ['asset_ids', 'settings'],
                'properties': {'asset_ids': asset_ids, 'settings': {'type': 'object',
                    'additionalProperties': False, 'properties': settings}}}})
    computer = bool(shutil.which('codex'))
    editor_target = {
        'type': 'object', 'additionalProperties': False,
        'required': ['version', 'editor_session_id', 'expected_revision', 'selected_ranges'],
        'properties': {
            'version': {'const': 1}, 'editor_session_id': {'type': 'string'},
            'expected_revision': {'type': 'integer', 'minimum': 0},
            'selected_ranges': {'type': 'array', 'maxItems': 100, 'items': {
                'type': 'object', 'additionalProperties': False, 'required': ['asset_id', 'start', 'end'],
                'properties': {'asset_id': {'type': 'string'}, 'start': {'type': 'number'}, 'end': {'type': 'number'}}}},
        },
    }
    rows.append({'id': 'editor.prepare_brief', 'effect': 'submit', 'status': 'available', 'execution_enabled': True,
        'reason': 'Requires a saved Editor session and exact task approval. Prepares clearance 1; never approves or renders.',
        'input_schema': {'type': 'object', 'additionalProperties': False, 'required': ['asset_ids', 'settings'],
            'properties': {'asset_ids': {**asset_ids, 'minItems': 0}, 'settings': {
                'type': 'object', 'additionalProperties': False, 'required': ['instruction', 'target'],
                'properties': {'instruction': {'type': 'string', 'minLength': 1, 'maxLength': 12000},
                    'target': editor_target}}}}})
    rows.append({'id': 'computer.execute', 'effect': 'submit',
        'status': 'available' if computer else 'blocked', 'execution_enabled': computer,
        'reason': 'Requires an open project, explicit access mode and exact-plan approval. Terminal, coding and filesystem; interactive browser control is unavailable.' if computer else 'Codex CLI is unavailable.',
        'input_schema': {'type': 'object', 'additionalProperties': False, 'required': ['asset_ids', 'settings'],
            'properties': {'asset_ids': {'type': 'array', 'maxItems': 0}, 'settings': {
                'type': 'object', 'additionalProperties': False, 'required': ['instruction', 'access_mode', 'skill_refs'],
                'properties': {'instruction': {'type': 'string', 'minLength': 1, 'maxLength': 12000},
                    'access_mode': {'enum': ['project', 'full']},
                    'skill_refs': {'type': 'array', 'maxItems': 6, 'items': {'type': 'string'}}}}}}})
    rows.append({'id': 'audio.transcribe', 'effect': 'submit', **agent_transcription.capability(),
        'input_schema': {'type': 'object', 'additionalProperties': False,
            'required': ['asset_ids', 'settings'], 'properties': {'asset_ids': {**asset_ids, 'maxItems': 1},
                'settings': {'type': 'object', 'additionalProperties': False, 'properties': {}}}}})
    for row in rows:
        description, media, scope, runtime, result = _CONTRACTS[row['id']]
        row.update(description=description, accepted_media=media, scope=scope, runtime=runtime,
                   approval='exact_plan', result_kind=result)
    return {'tools': rows}
