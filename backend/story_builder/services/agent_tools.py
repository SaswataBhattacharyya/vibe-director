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
