"""Catalogue-driven chat dispatch. Models propose; the task ledger authorizes."""
import json
from jsonschema import validate, ValidationError


def propose(tasks, owner, catalogue, call):
    if not isinstance(call, dict) or set(call) != {'tool_id', 'asset_ids', 'settings'}:
        raise ValueError('Supply tool_id, asset_ids and settings for the proposed tool.')
    tool = next((t for t in catalogue if t['id'] == call['tool_id']), None)
    if tool is None:
        raise ValueError('That operation is not in the live application tool catalogue.')
    if not tool['execution_enabled']:
        raise ValueError(tool.get('reason', 'This tool is unavailable.'))
    try:
        json.dumps(call, allow_nan=False)
        validate({k: call[k] for k in ('asset_ids', 'settings')}, tool['input_schema'])
    except (ValidationError, TypeError, ValueError) as exc:
        raise ValueError('Invalid ' + tool['id'] + ' request: ' + str(exc)) from exc
    return tasks.propose(owner, call)


def context(tasks, owner, source_ids):
    """Bound completed evidence; resolve sampled images again before vision input."""
    from . import media_library, vibe_editor
    results, frames = [], []
    for row in tasks.list(owner)['tasks'][:12]:
        if row['status'] != 'completed':
            continue
        completed = tasks.poll(owner, row['task_id'])
        results.append({'task_id': row['task_id'], 'tool_id': row['plan']['tool_id'],
                        'report': (completed.get('report') or '')[:10000]})
        if (not frames and row['plan']['tool_id'] == 'video.sample_frames'
                and source_ids and {a['asset_id'] for a in row['plan']['assets']} <= set(source_ids)):
            frames = completed.get('outputs', [])[:6]
    with vibe_editor.state(tasks.root, readonly=True) as data:
        sessions = [{k: p[k] for k in ('id', 'name', 'revision', 'selection')} for p in data['projects']
                    if p['workspace_id'] == owner][-20:]
    paths = [media_library.asset_path(tasks.root, owner, a['asset_id'])[0] for a in frames]
    return {'tool_results': results, 'editor_sessions': sessions}, frames, paths
