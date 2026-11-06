"""Service-backed descriptions only. Discovery never authorizes execution."""
import shutil


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
    return {'tools': rows}
