"""Reviewed brief preparation in an existing Editor session; never render approval."""
import copy
import math

from . import vibe_editor, video_repertoire
from .production_ledger import LedgerConflict

KIND = 'vibe-editor'
EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.mp4', '.mov', '.mkv', '.webm', '.avi',
              '.wav', '.mp3', '.flac', '.ogg', '.aac', '.m4a'}


def ranges(selection):
    return [{key: row[key] for key in ('asset_id', 'start', 'end')} for row in selection]


def check_target(project, owner, target):
    if (not isinstance(target, dict) or set(target) != {'version', 'editor_session_id', 'expected_revision', 'selected_ranges'}
            or type(target['version']) is not int or target['version'] != 1 or type(target['expected_revision']) is not int):
        raise ValueError('Supply a version 1 Editor session, revision and selected ranges.')
    selected = target['selected_ranges']
    if (target['expected_revision'] < 0 or not isinstance(selected, list) or len(selected) > 100
            or any(not isinstance(row, dict) or set(row) != {'asset_id', 'start', 'end'}
                   or not isinstance(row['asset_id'], str) or not row['asset_id']
                   or any(type(row[key]) not in (int, float) or not math.isfinite(row[key]) for key in ('start', 'end'))
                   or not 0 <= row['start'] < row['end'] for row in selected)):
        raise ValueError('Supply valid Editor asset ranges.')
    if project['workspace_id'] != owner or project['id'] != target['editor_session_id']:
        raise LedgerConflict('Editor session belongs to another project.')
    if project['revision'] != target['expected_revision'] or ranges(project['selection']) != target['selected_ranges']:
        raise LedgerConflict('Editor revision or selected ranges changed. Refresh and propose again.')


def style_snapshot(data, project):
    selected = copy.deepcopy(vibe_editor.style(data, project['style_id'])) if project.get('style_id') else {'id': None, 'version': 0, 'rules': []}
    selected['rules'] = [rule for rule in selected['rules'] if rule['confirmed']]
    selected['project_override'] = project['overrides'].get(project.get('style_id') or 'default', '')
    return selected


def context(root, owner, target):
    if not isinstance(target, dict) or not isinstance(target.get('editor_session_id'), str):
        raise ValueError('Choose a saved Editor session.')
    with vibe_editor.state(root) as data:
        project = vibe_editor.project(data, target['editor_session_id'])
        check_target(project, owner, target)
        return {'target': copy.deepcopy(target), 'style_snapshot': style_snapshot(data, project)}


def prepare(root, owner, settings):
    if not isinstance(settings, dict) or set(settings) != {'instruction', 'target'}:
        raise ValueError('Supply the Editor instruction and target.')
    if not isinstance(settings['instruction'], str) or not 1 <= len(settings['instruction'].strip()) <= 12000:
        raise ValueError('Supply an Editor instruction of at most 12000 characters.')
    return {'instruction': settings['instruction'], **context(root, owner, settings['target'])}


def validate_job(row, job):
    request, settings = job['request'], row['plan']['settings']
    target = settings['target']
    if (request.get('operation') != 'brief' or request.get('project_id') != target['editor_session_id']
            or request.get('revision') != target['expected_revision'] + 1
            or request.get('prompt') != settings['instruction'] or request.get('agent_settings') != settings
            or request.get('agent_inputs') != row['plan']['assets']
            or ranges(request.get('selection', [])) != target['selected_ranges']
            or request.get('style_snapshot') != settings['style_snapshot']):
        raise LedgerConflict('Editor job does not match the approved brief preparation.')


def submit(root, owner, plan, invocation, on_created):
    settings = plan['settings']
    result = vibe_editor.command(root, settings['target']['editor_session_id'],
        {'action': 'prepare_brief', 'text': settings['instruction'], 'revision': settings['target']['expected_revision']},
        agent_request={'workspace_id': owner, 'agent_invocation_id': invocation,
                       'agent_settings': settings, 'agent_inputs': plan['assets']}, on_created=on_created)
    return video_repertoire.read_job(KIND, result['job_id'])
