"""Reviewed two-clip joins, with Vibe revisions authoritative over MCP execution."""
import copy
import json
import shutil
import time
from pathlib import Path

from . import kdenlive_mcp, media_library, projects, vibe_editor, video_repertoire
from .storage_paths import checked, generated_root, project_root


def execution_folder(root, owner, session, execution):
    vibe_editor.ident(session)
    vibe_editor.ident(execution)
    return checked(project_root(root, owner), 'editor', 'editor', session, 'kdenlive', execution)


def propose(root, tasks, session, body, *, agent_request=None, on_created=None):
    if not isinstance(body, dict) or set(body) != {'revision', 'task_id'} or type(body['revision']) is not int:
        raise ValueError('Supply the current Editor revision and completed comparison task_id.')
    if not kdenlive_mcp.capability()['ready']:
        raise ValueError(kdenlive_mcp.capability()['message'])
    with vibe_editor.state(root, readonly=True) as data:
        current = copy.deepcopy(vibe_editor.project(data, session))
    evidence = tasks.overlap(current['workspace_id'], body['task_id'])
    comparison, sources = evidence['comparison'], evidence['sources']
    ranges = comparison.get('suggested_ranges')
    if comparison['status'] != 'match' or not ranges:
        raise ValueError('No unambiguous overlap was established. Set manual ranges in the visual timeline; no automatic trim was proposed.')
    if [r['asset_id'] for r in current['selection']] != [s['asset_id'] for s in sources]:
        raise ValueError('Select exactly the compared videos in order: A first, B second.')
    clips = []
    for i, (selected, retained) in enumerate(zip(current['selection'], ranges)):
        start, end = max(selected['start'], retained['start']), min(selected['end'], retained['end'])
        # Analysis compared the real A tail and real B head, not an arbitrary selection join.
        if (i == 0 and abs(selected['end']-retained['end']) > .05) or (i == 1 and selected['start'] != 0):
            raise ValueError('Comparison used the complete source boundary. Extend A selection to its end and start B at zero, then review again.')
        if end <= start:
            raise ValueError('The suggested trim removes all of the selected second clip. Extend its selected range first.')
        clips.append({**selected, 'start': start, 'end': end})
    plan = vibe_editor.validate_plan(root, current['workspace_id'], {'summary':
        f"Kdenlive join: keep A, remove the repeated first {ranges[1]['start']:.3f}s of B; retain original audio, use a hard cut. Output 1080p.",
        'backend': 'kdenlive', 'width': 1920, 'height': 1080, 'fps': 30, 'clips': clips, 'audio': None})
    join = {'plan': plan, 'evidence': evidence}
    start = None
    with vibe_editor.state(root) as data:
        p = vibe_editor.project(data, session)
        vibe_editor.busy(p)
        if p['revision'] != body['revision'] or p['revision'] != current['revision']:
            raise ValueError('Editor changed; refresh and review the comparison again.')
        from .agent_editor import style_snapshot, check_target
        style = style_snapshot(data, p)
        if agent_request:
            settings = agent_request['agent_settings']
            check_target(p, current['workspace_id'], settings['target'])
            if style != settings['style_snapshot']:
                raise ValueError('Editor style changed; prepare a new proposal.')
        p['revision'] += 1
        p.pop('pending', None)
        extra = agent_request or {}
        if not p.get('brief'):
            p['pending'] = {'kind': 'brief', 'revision': p['revision'], 'style_snapshot': style,
                'value': {'summary': plan['summary'], 'questions': [], 'preference_proposal': ''}, 'kdenlive_join': join}
            if agent_request is not None:
                start = vibe_editor._enqueue(p, 'kdenlive_brief', join=join, style_snapshot=style, **extra)
        else:
            start = vibe_editor._enqueue(p, 'kdenlive_prepare', join=join, style_snapshot=style, **extra)
        result = copy.deepcopy(p)
    if start:
        if on_created:
            on_created(start)
        video_repertoire.start_job('vibe-editor', start['job_id'])
    return result


def _current(root, request, job_id):
    with vibe_editor.state(root, readonly=True) as data:
        p = vibe_editor.project(data, request['project_id'])
        job = video_repertoire.read_job('vibe-editor', job_id)
        if p['job_id'] != job_id or p['revision'] != request['revision'] or job['status'] in {'cancelled', 'cancel_requested'}:
            raise ValueError('Editor revision changed or job stopped; result was not applied.')


def _sources(root, owner, sources):
    paths = []
    for source in sources:
        path, mime, _ = media_library.asset_path(root, owner, source['asset_id'])
        if not mime.startswith('video/') or projects.digest(path) != source['sha256']:
            raise ValueError('Reviewed source changed or is unavailable; compare the current bytes again.')
        paths.append(path)
    return paths


def prepare(root, job_id, request, progress):
    _current(root, request, job_id)
    join = request['join']
    owner, session = request['workspace_id'], request['project_id']
    sources = join['evidence']['sources']
    paths = _sources(root, owner, sources)
    folder = execution_folder(root, owner, session, job_id)
    folder.mkdir(parents=True, exist_ok=False)
    plan = vibe_editor.validate_plan(root, owner, join['plan'])
    staged = []
    for i, (path, source) in enumerate(zip(paths, sources)):
        target = folder / f'source-{i}{path.suffix.lower()}'
        shutil.copyfile(path, target)
        if projects.digest(target) != source['sha256']:
            raise ValueError('Source changed while preparing Kdenlive; discard this proposal.')
        staged.append({**source, 'path': target.name})
    frozen = {**plan, 'sources': staged, 'workspace_id': owner, 'editor_project_id': session,
              'editor_revision': request['revision']}
    vibe_editor.write(folder / 'request.json', frozen)
    result = kdenlive_mcp.run(folder, 'prepare', progress)
    preview = Path(result['outputPath']).resolve()
    if not preview.is_relative_to(folder.resolve()) or not preview.is_file():
        raise ValueError('MCP returned an invalid preview artifact.')
    relative = f'vibe_editor/{session}/{job_id}-join-preview.mp4'
    destination = generated_root(root, owner) / relative
    with vibe_editor.state(root) as data:
        p = vibe_editor.project(data, session)
        if p['job_id'] != job_id or p['revision'] != request['revision'] or video_repertoire.read_job('vibe-editor', job_id)['status'] in {'cancelled', 'cancel_requested'}:
            raise ValueError('Editor changed or stopped; preview was not published.')
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open('xb') as output, preview.open('rb') as source:
            shutil.copyfileobj(source, output)
        asset = media_library.register_generated_video(root, owner, relative,
            {'editor_project_id': session, 'editor_revision': request['revision'], 'purpose': 'kdenlive_join_preview'})
        p['pending'] = {'kind': 'plan', 'revision': p['revision'],
            'value': {**plan, 'kdenlive_execution': job_id}, 'style_snapshot': request['style_snapshot'],
            'evidence': {'backend': 'kdenlive', 'comparison': join['evidence']}}
        p['join_preview'] = {'asset': asset, 'execution_id': job_id, 'revision': p['revision']}
        vibe_editor.message(p, 'assistant', 'Kdenlive join preview is ready. Inspect the boundary and audio before approving this exact cut for final rendering.')
    return {'pending_clearance': 'plan', 'revision': request['revision'], 'preview': asset}


def render(root, job_id, request, progress):
    _current(root, request, job_id)
    owner, session = request['workspace_id'], request['project_id']
    plan = vibe_editor.validate_plan(root, owner, request['plan'])
    execution = plan.get('kdenlive_execution')
    if not execution:
        raise ValueError('Prepare and review a Kdenlive join preview first.')
    folder = execution_folder(root, owner, session, execution)
    frozen = json.loads((folder / 'request.json').read_text())
    if frozen['workspace_id'] != owner or frozen['editor_project_id'] != session:
        raise ValueError('Kdenlive execution belongs to another session.')
    _sources(root, owner, frozen['sources'])
    comparable = ('backend', 'width', 'height', 'fps', 'clips', 'audio')
    if any(plan[key] != frozen[key] for key in comparable):
        raise ValueError('The timeline differs from its Kdenlive preview. Prepare and review a new join.')
    for source in frozen['sources']:
        if projects.digest(folder / source['path']) != source['sha256']:
            raise ValueError('Kdenlive staged source changed; prepare a new join.')
    result = kdenlive_mcp.run(folder, 'render', progress)
    editable = Path(result['editable']['path']).resolve()
    if not editable.is_relative_to(folder.resolve()) or not editable.is_file():
        raise ValueError('MCP returned an invalid editable project artifact.')
    final = Path(result['outputPath']).resolve()
    if not final.is_relative_to(folder.resolve()):
        raise ValueError('MCP final artifact escaped its execution folder.')
    probe = media_library._probe(final, 'video')
    duration = sum(round((clip['end']-clip['start'])*plan['fps'])/plan['fps'] for clip in plan['clips'])
    if abs(probe['duration_seconds']-duration) > 2/plan['fps'] or (probe['width'], probe['height']) != (plan['width'], plan['height']):
        raise ValueError('Kdenlive output does not match the approved duration/dimensions.')
    needs_audio = any('audio' in media_library._probe(path, 'video')['streams'] for path in _sources(root, owner, frozen['sources']))
    if needs_audio and 'audio' not in probe['streams']:
        raise ValueError('Kdenlive output lost source audio; publication refused.')
    while True:
        _current(root, request, job_id)
        with vibe_editor.state(root, readonly=True) as data:
            paused = vibe_editor.project(data, session).get('pause_requested', False)
        if not paused:
            break
        progress('paused', 'Render completed. Waiting for Resume before publishing.', 95)
        time.sleep(.5)
    with vibe_editor.state(root) as data:
        p = vibe_editor.project(data, session)
        if p['job_id'] != job_id or p['revision'] != request['revision'] or video_repertoire.read_job('vibe-editor', job_id)['status'] in {'cancelled', 'cancel_requested'}:
            raise ValueError('Stopped or changed revision; final output was not published.')
        if p.get('pause_requested'):
            raise ValueError('Publication paused at the final boundary. Resume and retry the saved render.')
        relative = f'vibe_editor/{session}/{job_id}.mp4'
        destination = generated_root(root, owner) / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open('xb') as output, final.open('rb') as source:
            shutil.copyfileobj(source, output)
        asset = media_library.register_generated_video(root, owner, relative,
            {'editor_project_id': session, 'editor_revision': request['revision'], 'editor_job_id': job_id, 'backend': 'kdenlive'})
        output = {'asset': asset, 'duration_seconds': duration, 'backend': 'kdenlive',
                  'editable_project': result['editable']['path'], 'execution_id': execution,
                  'verification': result['verification']}
        p['output'] = output
        return output
