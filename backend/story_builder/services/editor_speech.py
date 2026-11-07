"""Reviewed transcript segments to retained source ranges. Never starts a render."""
import copy

from . import agent_editor, vibe_editor


def evidence(root, tasks, project_id):
    with vibe_editor.state(root) as data:
        project = copy.deepcopy(vibe_editor.project(data, project_id))
    owner = project['workspace_id']
    ids = list(dict.fromkeys(row['asset_id'] for row in project['selection']))
    assets = tasks._assets(owner, ids, extensions=agent_editor.EXTENSIONS) if ids else []
    found = tasks.speech_evidence(owner, assets)
    return {'revision': project['revision'], 'sources': [tasks.transcript(owner, row['task_id']) for row in found]}


def retained_ranges(selection, asset_id, cuts):
    """Subtract a sorted union of cuts, retaining order and every unaffected interval."""
    merged = []
    for start, end in sorted(cuts):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    clips = []
    for row in selection:
        if row['asset_id'] != asset_id:
            clips.append(copy.deepcopy(row))
            continue
        position = row['start']
        for start, end in merged:
            if end <= position or start >= row['end']:
                continue
            if position < start:
                clips.append({**row, 'start': position, 'end': start})
            position = max(position, min(end, row['end']))
        if position < row['end']:
            clips.append({**row, 'start': position})
    return clips


def propose(root, tasks, project_id, body):
    if not isinstance(body, dict) or set(body) != {'revision', 'task_id', 'segment_indices'}:
        raise ValueError('Supply the reviewed revision, speech task and segment indices.')
    indices = body['segment_indices']
    if (not isinstance(indices, list) or not 1 <= len(indices) <= 100
            or any(type(i) is not int or i < 0 for i in indices) or len(set(indices)) != len(indices)):
        raise ValueError('Choose 1–100 distinct transcript segments after reviewing playback.')
    with vibe_editor.state(root) as data:
        p = copy.deepcopy(vibe_editor.project(data, project_id))
    if type(body['revision']) is not int or body['revision'] != p['revision']:
        raise ValueError('Editor revision changed. Refresh and review the cuts again.')
    source = tasks.transcript(p['workspace_id'], body['task_id'])
    if not any(r['asset_id'] == source['asset_id'] for r in p['selection']):
        raise ValueError('The analyzed source is not selected in this Editor session.')
    # Preserve the current proposal (or last approved timeline), including filters,
    # framing, captions and dimensions. Retiming/transitions need a separate mapper.
    plans = [r['value'] for r in p['revisions'] if r['kind'] == 'plan']
    if p.get('pending', {}).get('kind') == 'plan':
        plans.append(p['pending']['value'])
    base = plans[-1] if plans else {'width': 1280, 'height': 720, 'fps': 24,
                                   'clips': p['selection'], 'audio': None}
    if base.get('audio') or any(r['mime'].startswith('audio/') for r in base['clips']):
        raise ValueError('Reviewed speech cuts cannot realign a replacement soundtrack. Edit that timeline directly.')
    if any(r.get('speed', {'start': 1, 'end': 1}) != {'start': 1, 'end': 1}
           or r.get('transition', {}).get('kind', 'cut') != 'cut' for r in base['clips']):
        raise ValueError('Reviewed speech cuts require normal-speed clips and hard cuts. Edit retimed clips or transitions directly.')
    segments = source['transcript']['segments']
    if any(i >= len(segments) for i in indices):
        raise ValueError('A reviewed transcript segment no longer exists.')
    cuts = [(segments[i]['start'], segments[i]['end']) for i in sorted(indices)]
    if any(not any(r['asset_id'] == source['asset_id'] and r['start'] <= start < end <= r['end']
                   for r in base['clips']) for start, end in cuts):
        raise ValueError('A cut lies outside the current timeline ranges. Select the complete source or the required range first.')
    clips = retained_ranges(base['clips'], source['asset_id'], cuts)
    if not clips:
        raise ValueError('These cuts remove the entire edit. Keep at least one clip.')
    provenance = {key: source[key] for key in ('task_id', 'job_id', 'asset_id', 'sha256')}
    provenance['removed_segments'] = [{'index': i, **{key: segments[i][key] for key in ('start', 'end', 'text')}} for i in sorted(indices)]
    plan = {**base, 'summary': 'Reviewed speech cuts; preserve all other selected footage and original audio.',
            'clips': clips, 'audio': None}
    return vibe_editor.propose_plan(root, project_id, {'revision': body['revision'], 'plan': plan}, evidence=provenance)
