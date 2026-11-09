"""Playable Backlot mirror with reviewed Vibe extension proposals."""
import copy
import json
import shutil
import sys
from pathlib import Path

from . import interface_sessions as sessions, media_library, production_manifest, projects, vibe_editor
from .vibe_editor_render import APP

RUNTIME = APP / 'local_data/runtimes/openmontage'


def _write(path, value):
    text = json.dumps(value, ensure_ascii=False, indent=2)
    if path.is_file() and path.read_text() == text:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(text)
    temporary.replace(path)


def sync(board, s, expected_revision=None):
    with s['operation_lock']:
        if s.get('closed'):
            raise ValueError('Backlot workspace is closed. Open it again.')
        return _sync(board, s, expected_revision)


def _sync(board, s, expected_revision):
    owner, screenplay = s['owner']
    revision = board.get(owner, screenplay)['revision'] if expected_revision is None else expected_revision
    manifest = production_manifest.export(board, owner, screenplay, revision)
    folder = s['folder'] / 'projects/production'
    staged = copy.deepcopy(manifest['artifacts'])
    for asset in staged['asset_manifest']['assets']:
        aid = asset['vibe_asset_id']
        source, _, _ = media_library.asset_path(board.root, owner, aid)
        relative = f'media/{aid}-{asset["sha256"][:12]}{source.suffix}'
        target = folder / relative
        if not target.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_suffix('.tmp')
            shutil.copyfile(source, temporary)
            if projects.digest(temporary) != asset['sha256']:
                temporary.unlink()
                raise ValueError('Media changed during Backlot synchronization.')
            temporary.replace(target)
        asset['path'] = relative
        # The mirror has no ability to call back into application tools.
        asset.pop('content_url', None)
    if board.get(owner, screenplay)['revision'] != revision:
        raise ValueError('Storyboard changed during synchronization; refresh again.')
    for name, value in staged.items():
        _write(folder / f'artifacts/{name}.json', value)
    _write(folder / 'project.json', {'title': manifest['project']['title'], 'pipeline_type': 'vibe-director',
                                   'vibe': manifest['project']})
    _write(folder / 'vibe-manifest.json', manifest)
    _write(folder / 'vibe-state.json', board.get(owner, screenplay))
    publication = publish_final(board, s, revision)
    s['revision'] = revision
    return {'revision': revision, 'write_back': False, 'reviewed_editing': True, 'final_film': publication}


def open_workspace(board, owner, screenplay, body):
    if not isinstance(body, dict) or set(body) != {'expected_revision'}:
        raise ValueError('Supply exactly expected_revision.')
    marker = RUNTIME / 'vibe-runtime.json'
    if not marker.is_file() or json.loads(marker.read_text())['revision'] != production_manifest.UPSTREAM_REVISION:
        raise ValueError('Install the pinned Backlot runtime with: conda run -n react python scripts/setup_production_interfaces.py')
    for name, digest in json.loads(marker.read_text())['sha256'].items():
        if projects.digest(RUNTIME / name) != digest:
            raise ValueError('Backlot runtime changed. Inspect the installed runtime before opening it.')
    s = sessions.create(board.root, 'backlot', (owner, screenplay))
    try:
        sync(board, s, body['expected_revision'])
        result = sessions.launch(s, [sys.executable, Path(__file__).with_name('native_backlot.py'), RUNTIME,
                                    s['folder'] / 'projects'], health='/api/health')
        return {**result, 'revision': s['revision'], 'write_back': False}
    except BaseException:
        if s['folder'].exists():
            sessions.close(s)
        raise


def operate(board, owner, screenplay, body):
    if not isinstance(body, dict) or set(body) != {'token', 'action'}:
        raise ValueError('Supply exactly token and action.')
    s = sessions.get(board.root, body['token'], 'backlot', (owner, screenplay), allow_stopped=body['action'] == 'close')
    if body['action'] == 'close':
        sessions.close(s)
        return {'closed': True}
    if body['action'] == 'proposal':
        return proposal(board, s)
    if body['action'] == 'sync':
        return sync(board, s)
    raise ValueError('Unknown Backlot action.')


def proposal(board, s):
    """Import typed native edits as a draft; never save/approve or submit a job."""
    owner, source = s['owner']
    with s['operation_lock']:
        path = s['folder'] / 'projects/production/vibe-proposal.json'
        if not path.is_file() or path.stat().st_size > 128 * 1024:
            raise ValueError('Send an edit proposal from the Backlot Vibe extension first.')
        value = json.loads(path.read_text())
        state = board.get(owner, source)
        if type(value.get('base_revision')) is not int or value['base_revision'] != state['revision']:
            raise ValueError('Storyboard changed since these Backlot edits. Reopen the extension and review the current board.')
        changes = value.get('changes')
        if not isinstance(changes, list) or not 1 <= len(changes) <= 100:
            raise ValueError('Supply 1–100 shot changes.')
        draft, seen = copy.deepcopy(state['body']), set()
        for change in changes:
            if not isinstance(change, dict) or set(change) != {'shot_key', 'values'}:
                raise ValueError('Invalid Backlot shot change.')
            key, values = change['shot_key'], change['values']
            if not isinstance(key, str) or key not in draft['shots'] or key in seen:
                raise ValueError('Unknown or duplicate shot identity.')
            seen.add(key)
            if not isinstance(values, dict) or not values or set(values) - {'prompt', 'video_prompt', 'duration', 'notes'}:
                raise ValueError('Backlot extension edits support shot prompts, duration and notes; media/job identities are preserved.')
            draft['shots'][key].update(values)
        draft = board.validate(owner, source, draft)
        # Production manifest rechecks owned asset hashes before importing edits.
        production_manifest.export(board, owner, source, state['revision'])
        return {'body': draft, 'base_revision': state['revision'],
                'explanation': 'Backlot Vibe extension proposal. Review these shot changes, use as a draft, then save in Vibe. No generation has started.'}


def publish_final(board, session, revision):
    """Mirror only a verified output from this saved board's Editor session."""
    owner, source = session['owner']
    with vibe_editor.state(board.root, readonly=True) as data:
        candidates = [p for p in data['projects'] if p['workspace_id'] == owner
            and p.get('storyboard_source', {}).get('source_id') == source and p.get('output')]
        editor = max(candidates, key=lambda p: p['storyboard_source']['revision'], default=None)
        output = copy.deepcopy((editor or {}).get('output'))
    if not output or not output.get('asset'):
        return None
    editor_id = editor['id']
    source_revision = editor['storyboard_source']['revision']
    if source_revision > revision:
        raise ValueError('Film belongs to a newer storyboard revision. Refresh Backlot.')
    aid = output['asset']['asset_id']
    asset = board.assets(owner).get(aid)
    if not asset or asset['kind'] != 'video' or asset.get('archived_at'):
        raise ValueError('The saved film output is unavailable in this project.')
    metadata = asset.get('metadata', {})
    if (asset['sha256'] != output['asset'].get('sha256')
            or metadata.get('editor_project_id') != editor_id):
        raise ValueError('The film output does not match its verified Editor provenance.')
    path, _, _ = media_library.asset_path(board.root, owner, aid)
    if projects.digest(path) != asset['sha256']:
        raise ValueError('The saved film changed. Review its current bytes before publishing.')
    folder = session['folder'] / 'projects/production'
    target = folder / 'renders' / f'{aid}-{asset["sha256"][:12]}{path.suffix}'
    if not target.is_file():
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix('.tmp')
        try:
            shutil.copyfile(path, temporary)
            if projects.digest(temporary) != asset['sha256']:
                raise ValueError('Film changed during Backlot publication.')
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
    value = {'asset_id': aid, 'sha256': asset['sha256'], 'editor_session_id': editor_id,
             'storyboard_revision': source_revision, 'current_storyboard_revision': revision, 'path': target.relative_to(folder).as_posix()}
    _write(folder / 'vibe-final-film.json', value)
    return value
