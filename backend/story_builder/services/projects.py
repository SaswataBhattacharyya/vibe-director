"""Folder checkpoints for one project; existing ledgers and workers remain authoritative.

Only project rows/files are exported. Models, credentials and other projects never
enter a checkpoint. Opening never replaces newer local work.
"""
from contextlib import contextmanager
from pathlib import Path
import fcntl
import hashlib
import json
import os
import re
import shutil
import sqlite3
import uuid
from .storage_paths import checked, project_root, project_folders
from .output_destinations import write, grant, TOOLS, preference

ACTIVE = {'queued', 'running', 'submitting', 'cancel_requested', 'leased', 'rendering', 'interrupted', 'recovery_required'}
DATABASES = ('services/production/ledger.sqlite3', 'services/production/image-jobs.sqlite3')
_database_paths = {}

def configure(root, ledger, images):
    _database_paths[str(Path(root).resolve())] = dict(zip(DATABASES, (Path(ledger), Path(images))))

def database_path(root, name):
    return _database_paths.get(str(Path(root).resolve()), {}).get(name, Path(root) / name)

GLOBALS = {'production_style_versions', 'directing_style_versions', 'workflow_knowledge_snapshots', 'story_imports'}


def home(root):
    path = checked(root, 'library', 'projects')
    path.mkdir(parents=True, exist_ok=True)
    return path


@contextmanager
def locked(root):
    with (home(root) / '.lock').open('a') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        yield


def read(path, default=None):
    if path.is_symlink():
        raise ValueError('Project records cannot be symlinks.')
    return json.loads(path.read_text()) if path.exists() else default


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def identity(value):
    if not isinstance(value, str) or not re.fullmatch(r'story-[a-f0-9]{12}', value):
        raise ValueError('Invalid project identity.')
    return value


def records(root):
    return read(home(root) / 'folders.json', {})


def current(root):
    active = read(home(root) / 'active.json', {})
    workspace = active.get('workspace_id', 'tool-library')
    notice = ''
    if workspace != 'tool-library':
        try:
            project_root(root, workspace)
            if not database_path(root, DATABASES[0]).exists():
                raise ValueError('Project database is unavailable.')
            with sqlite3.connect(database_path(root, DATABASES[0])) as db:
                if not db.execute('SELECT 1 FROM story_workspaces WHERE workspace_id=?', (workspace,)).fetchone():
                    raise ValueError('Project no longer exists.')
        except (ValueError, sqlite3.Error) as exc:
            workspace = 'tool-library'
            notice = str(exc) + ' Standalone tools are available; open a project folder to continue.'
    folder = records(root).get(workspace)
    if not folder and workspace != 'tool-library':
        directory = project_root(root, workspace)
        if directory.is_dir():
            folder = str(directory)
    memory = read(home(root) / f'{workspace}.json', {})
    return {'workspace_id': workspace, 'folder': folder, 'title': active.get('title', 'Standalone tools') if workspace != 'tool-library' else 'Standalone tools',
            'browser_state': memory, 'notice': notice, 'projects_folder': str(checked(root, 'projects'))}


def browser_state(value):
    if not isinstance(value, dict) or len(json.dumps(value)) > 8_000_000:
        raise ValueError('Invalid project browser state.')
    for key, item in value.items():
        if not isinstance(key, str) or not key.startswith('vibe-') or not isinstance(item, str):
            raise ValueError('Invalid project browser entry.')
        if any(word in key.lower() for word in ('token', 'secret', 'provider', 'debug', 'palette', 'navigation')):
            raise ValueError('Application settings cannot be saved in a project.')
    return value


def sql_snapshot(path, workspace):
    if not path.exists():
        return {}
    with sqlite3.connect(path) as db:
        db.row_factory = sqlite3.Row
        db.execute('BEGIN')
        tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        all_rows = {t: [dict(r) for r in db.execute(f'SELECT * FROM "{t}"')] for t in tables}
        selected = {t: [r for r in rows if r.get('workspace_id', r.get('project_id')) == workspace] for t, rows in all_rows.items()}
        # Follow child relationships and referenced immutable global definitions.
        while True:
            before = sum(map(len, selected.values()))
            text = json.dumps(selected)
            for table, rows in all_rows.items():
                foreign = list(db.execute(f'PRAGMA foreign_key_list("{table}")'))
                columns = list(db.execute(f'PRAGMA table_info("{table}")'))
                primary = [r[1] for r in columns if r[5]]
                for row in rows:
                    owner = row.get('workspace_id', row.get('project_id'))
                    if owner and owner != workspace or row in selected[table]:
                        continue
                    child = any(row.get(fk[3]) is not None and any(parent.get(fk[4]) == row.get(fk[3]) for parent in selected.get(fk[2], [])) for fk in foreign)
                    # Several claim/history tables use job_id without a declared FK.
                    job = row.get('job_id')
                    related_job = job and any(any(p.get('job_id') == job for p in parents) for parents in selected.values())
                    global_ref = table in GLOBALS and any(isinstance(row.get(k), str) and json.dumps(row[k]) in text for k in primary)
                    if child or related_job or global_ref:
                        selected[table].append(row)
            if sum(map(len, selected.values())) == before:
                break
        return {t: rows for t, rows in selected.items() if rows}


def assert_idle(root, workspace):
    for database in DATABASES:
        for table, rows in sql_snapshot(database_path(root, database), workspace).items():
            if any(row.get('status', row.get('state', row.get('run_state'))) in ACTIVE for row in rows):
                raise ValueError('This project has an active job. Wait or cancel it before saving or changing projects.')
    for path in (Path(root) / 'services/media/jobs').glob('*/*/job.json'):
        value = read(path, {})
        if value.get('request', {}).get('workspace_id', 'tool-library') == workspace and value.get('status') in ACTIVE:
            raise ValueError('This project has an active media job. Wait or cancel it before saving or changing projects.')


def folder_path(value):
    path = Path(str(value)).expanduser()
    if not path.is_absolute() or not path.is_dir():
        raise ValueError('Choose an existing absolute project folder.')
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('Project folders cannot use symlinks.')
    return path.resolve()


def existing_project(root, folder):
    """Recognize only an exact local folder owned by a live ledger identity."""
    if folder.parent != (Path(root).resolve() / 'projects'):
        return None
    path = database_path(root, DATABASES[0])
    if not path.exists():
        return None
    with sqlite3.connect(path) as db:
        rows = db.execute('SELECT workspace_id,title FROM story_workspaces').fetchall()
    for workspace, title in rows:
        try:
            directory = project_root(root, identity(workspace))
        except ValueError:
            continue  # Deleted projects must never be reopened from their old directory.
        if directory != folder:
            continue
        marker = read(folder / 'media/workspace.json', {})
        if marker.get('workspace_id', workspace) != workspace:
            raise ValueError('Project folder ownership does not match its saved identity.')
        return {'workspace_id': workspace, 'title': title}
    return None


def owned_files(root, workspace, memory=None):
    directory = project_root(root, workspace)
    sources = {}
    # A compatibility save may live in this folder; never snapshot old checkpoints.
    for base, dirs, names in os.walk(directory, followlinks=False):
        dirs[:] = [name for name in dirs if name not in {'project-data', 'checkpoint-media'}]
        for name in names:
            if name not in {'vibe-project.json', 'checkpoint-assets.json'}:
                path = Path(base) / name
                sources[path] = Path('content') / path.relative_to(directory)
    for document in (directory / 'music/jukebox').glob('*/project.json'):
        if any(item.get('workspace_id') != workspace for item in read(document).get('sources', [])):
            raise ValueError('Copy this music session into the current project before saving its folder; it still references another project’s recordings.')
    from . import trellis_studio
    input_ids = set()
    drafts = json.dumps(memory or {})
    for token in re.findall(r'[a-f0-9]{32}', drafts):
        candidate = trellis_studio.image_path(root, token)
        if candidate.is_file():
            input_ids.add(token)
    for path in (Path(root) / 'services/media/jobs').glob('*/*/job.json'):
        value = read(path, {})
        if value.get('request', {}).get('workspace_id') != workspace:
            continue
        for child in path.parent.rglob('*'):
            if child.is_file():
                sources[child] = Path('runtime') / child.relative_to(root)
        if value.get('kind') == 'trellis' or path.parent.parent.name == 'trellis':
            batch = trellis_studio.home(root) / 'batches' / (value['job_id'] + '.json')
            if batch.exists():
                sources[batch] = Path('runtime') / batch.relative_to(root)
                for item in read(batch).get('items', []):
                    if item.get('status') == 'completed':
                        result = trellis_studio.result_path(root, value['job_id'], item['index'])
                        sources[result] = Path('runtime/trellis.2/saved-results') / value['job_id'] / result.name
            for item in value.get('request', {}).get('items', []):
                input_ids.add(item['id'])
                input_ids.update(item.get('views', {}).values())
        if path.parent.parent.name == 'music-jukebox':
            export = Path(root) / 'music_jukebox/exports' / (value['job_id'] + '.json')
            if export.exists():
                sources[export] = Path('runtime') / export.relative_to(root)
                from . import music_jukebox
                audio = music_jukebox.export_path(root, value['job_id'])
                sources[audio] = Path('runtime/music_jukebox/saved-exports') / value['job_id'] / audio.name
    for token in input_ids:
        path = trellis_studio.image_path(root, token)
        if not path.is_file():
            raise ValueError('A saved 3D input is missing. Locate it before saving the project.')
        sources[path] = Path('runtime') / path.relative_to(root)
    ledger = sql_snapshot(database_path(root, DATABASES[0]), workspace)
    for item in ledger.get('story_imports', []):
        for field in ('relative_path', 'preview_path'):
            relative = Path(item[field])
            if relative.is_absolute() or '..' in relative.parts:
                raise ValueError('Invalid story import location.')
            path = Path(root) / 'services/production/story-imports' / relative
            sources[path] = Path('runtime') / path.relative_to(root)
    for document in (directory / 'music/ace').glob('*/project.json'):
        value = read(document)
        for adapter in value.get('adapters', []):
            if not adapter.get('path'):
                continue
            from .storage_paths import relocated_path
            base = relocated_path(root, Path(adapter['path']))
            if not base.is_relative_to(Path(root) / 'ace_step/runs') or not base.is_dir():
                raise ValueError('Locate the trained ACE adapter before saving the project.')
            for path in base.rglob('*'):
                if path.is_file():
                    sources[path] = Path('runtime') / path.relative_to(root)
        dataset = (value.get('dataset') or {}).get('path')
        if dataset:
            from .storage_paths import relocated_path
            base = relocated_path(root, Path(dataset))
            if not base.is_relative_to(Path(root) / 'ace_step/datasets') or not base.is_dir():
                raise ValueError('Locate the ACE training dataset before saving the project.')
            for path in base.rglob('*'):
                if path.is_file():
                    sources[path] = Path('runtime') / path.relative_to(root)
    for job_path in (Path(root) / 'services/media/jobs').glob('*/*/job.json'):
        value = read(job_path, {})
        if value.get('request', {}).get('workspace_id') != workspace:
            continue
        for analysis in (value.get('result') or {}).get('audio_analysis') or []:
            run_id = analysis.get('run_id')
            if not isinstance(run_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,160}', run_id):
                continue
            from .output_destinations import resolve_run_path
            canonical = Path(root) / 'video_repertoire/runs' / run_id
            actual = resolve_run_path(root, canonical)
            if not actual.is_dir():
                raise ValueError('Locate analysis output before saving the project.')
            for path in actual.rglob('*'):
                if path.is_file():
                    sources[path] = Path('runtime/video_repertoire/runs') / run_id / path.relative_to(actual)
    for path, relative in sources.items():
        if any(p.is_symlink() for p in (path, *path.parents)):
            raise ValueError('Project files cannot use symlinks.')
        yield path, relative


def valid_runtime(relative):
    parts = relative.parts
    return (parts[:3] == ('services', 'media', 'jobs') or
            parts[:3] == ('services', 'production', 'story-imports') or
            parts[:2] == ('music_jukebox', 'saved-exports') or parts[:2] == ('trellis.2', 'saved-results') or parts[:2] == ('video_repertoire', 'runs') or parts[:2] in {('ace_step', 'datasets'), ('ace_step', 'runs')} or
            len(parts) == 3 and parts[:2] in {('trellis.2', 'input'), ('trellis.2', 'batches'), ('music_jukebox', 'exports')})


def session_grants(root, workspace, folder, memory):
    # Export only folder grants actually mentioned by this project's sessions/jobs.
    texts = json.dumps(memory)
    for path in (Path(root) / 'library/output_destinations/preferences').glob(f'*--{workspace}.json'):
        texts += path.read_text()
    directory = project_root(root, workspace)
    for path in directory.rglob('*.json'):
        texts += path.read_text()
    for path in (Path(root) / 'services/media/jobs').glob('*/*/job.json'):
        value = read(path, {})
        if value.get('request', {}).get('workspace_id') == workspace:
            texts += json.dumps(value)
    result = {}
    domains = ('library/output_destinations/grants', 'trellis.2/projects', 'music_jukebox/folders')
    for domain in domains:
        for path in (Path(root) / domain).glob('*.json'):
            token = path.stem.removeprefix('folder-')
            if not re.fullmatch('[a-f0-9]{32}', token) or token not in texts:
                continue
            value = read(path)
            location = Path(value['path'])
            result[path.relative_to(root).as_posix()] = {'path': str(location), 'relative': location.relative_to(folder).as_posix() if location.is_relative_to(folder) else None}
    return result


def validate_folder(root, value, workspace=None):
    folder = folder_path(value)
    if workspace and (existing_project(root, folder) or {}).get('workspace_id') == workspace:
        return folder
    source_repo = Path(__file__).resolve().parents[3]
    runtime = Path(root).resolve()
    if any(folder.is_relative_to(base) or base.is_relative_to(folder) for base in (source_repo, runtime)):
        raise ValueError('Choose a project folder outside source code and application runtime data.')
    return folder


def output_defaults(root, workspace, folder):
    output = folder_path(folder) / 'outputs'
    output.mkdir(exist_ok=True)
    from .output_destinations import preference_path
    for tool in TOOLS:
        if not preference_path(root, tool, workspace).exists():
            category = 'videos' if tool in {'video-generation', 'assembly-export'} else 'images' if tool == 'image-generation' else 'analyses' if tool == 'analysis' else 'audio'
            directory = output / category
            directory.mkdir(exist_ok=True)
            selected = grant(root, str(directory))
            preference(root, tool, workspace, {'mode': 'folder', 'grant': selected['grant']})
    for category in ('models', 'edits'):
        (output / category).mkdir(exist_ok=True)


def save(root, workspace, folder, memory):
    identity(workspace)
    assert_idle(root, workspace)
    folder = validate_folder(root, folder, workspace)
    manifest_path = folder / 'vibe-project.json'
    previous = read(manifest_path, {})
    if previous and previous.get('workspace_id') != workspace:
        raise ValueError('This folder belongs to another project. Choose an empty project folder.')
    output_defaults(root, workspace, folder)
    checkpoint = uuid.uuid4().hex
    destination = checked(folder, 'project-data', checkpoint)
    destination.mkdir(parents=True)
    published = False
    try:
        databases = {db: sql_snapshot(database_path(root, db), workspace) for db in DATABASES}
        sources = []
        files = []
        for source, relative in owned_files(root, workspace, memory):
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            checksum = digest(target)
            sources.append((source, checksum))
            files.append({'path': relative.as_posix(), 'sha256': checksum})
        # Materialize registered media without changing its identity or frozen metadata.
        # The checkpoint copy is used only if its original registered location is absent.
        from .media_library import asset_path
        asset_manifest = read(project_root(root, workspace) / 'media/assets.json', {})
        portable = {}
        for asset in asset_manifest.get('assets', []):
            source, _, _ = asset_path(root, workspace, asset['asset_id'])
            relative = Path('content/media/checkpoint-media') / asset['asset_id']
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            checksum = digest(target)
            if checksum != asset['sha256']:
                raise ValueError('Registered media changed; restore it before saving the project.')
            files.append({'path': relative.as_posix(), 'sha256': checksum})
            portable[asset['asset_id']] = {'path': 'checkpoint-media/' + asset['asset_id'], 'sha256': checksum}
        index = destination / 'content/media/checkpoint-assets.json'
        write(index, portable)
        files = [entry for entry in files if entry['path'] != 'content/media/checkpoint-assets.json']
        files.append({'path': 'content/media/checkpoint-assets.json', 'sha256': digest(index)})
        preferences = {}
        for path in (Path(root) / 'library/output_destinations/preferences').glob(f'*--{workspace}.json'):
            choice = read(path)
            if choice.get('mode') == 'folder':
                from .output_destinations import granted
                selected = granted(root, choice['grant'])
                preferences[path.name] = {'choice': choice, 'path': str(selected), 'relative': selected.relative_to(folder).as_posix() if selected.is_relative_to(folder) else None}
        style_ids = {read(p).get('style_id') for p in (project_root(root, workspace) / 'editor/editor').glob('*/project.json')}
        styles = [item for item in read(Path(root) / 'services/editor/state.json', {}).get('styles', []) if item['id'] in style_ids]
        snapshot = {'editor_styles': styles, 'version': 1, 'workspace_id': workspace, 'databases': databases,
                    'browser_state': browser_state(memory), 'files': files, 'folder_grants': session_grants(root, workspace, folder, memory), 'source_root': str(Path(root).resolve()), 'preferences': preferences}
        assert_idle(root, workspace)
        if {str(path) for path, _ in owned_files(root, workspace, memory)} != {str(path) for path, _ in sources} or databases != {db: sql_snapshot(database_path(root, db), workspace) for db in DATABASES} or any(digest(source) != checksum for source, checksum in sources):
            raise ValueError('Project changed while saving. Save again after the current edit finishes.')
        write(destination / 'state.json', snapshot)
        title = workspace
        rows = snapshot['databases'][DATABASES[0]].get('story_workspaces', [])
        if rows:
            title = rows[0]['title']
        write(manifest_path, {'format': 'vibe-director-project', 'version': 1, 'workspace_id': workspace, 'title': title, 'checkpoint': checkpoint,
                              'state_path': f'project-data/{checkpoint}/state.json',
                              'content_path': f'project-data/{checkpoint}/content',
                              'runtime_path': f'project-data/{checkpoint}/runtime',
                              'state_sha256': digest(destination / 'state.json')})
        published = True
        folders = records(root)
        folders[workspace] = str(folder)
        write(home(root) / 'folders.json', folders)
        write(home(root) / f'{workspace}.json', memory)
        return {'workspace_id': workspace, 'folder': str(folder), 'title': title, 'browser_state': memory}
    except Exception:
        if not published:
            shutil.rmtree(destination)
        raise


def activate(root, workspace, title, memory):
    write(home(root) / 'active.json', {'workspace_id': workspace, 'title': title})
    write(home(root) / f'{workspace}.json', memory)
    return current(root)


def open_project(root, folder):
    folder = folder_path(folder)
    existing = existing_project(root, folder)
    folder = validate_folder(root, folder, existing['workspace_id'] if existing else None)
    manifest = read(folder / 'vibe-project.json', {})
    if existing and not manifest:
        workspace = existing['workspace_id']
        assert_idle(root, workspace)
        return activate(root, workspace, existing['title'], read(home(root) / f'{workspace}.json', {}))
    if existing and manifest.get('workspace_id') != existing['workspace_id']:
        raise ValueError('Project checkpoint ownership does not match this folder.')
    if manifest.get('format') != 'vibe-director-project' or manifest.get('version') != 1:
        raise ValueError('This folder does not contain a supported vibe-project.json.')
    workspace = identity(manifest.get('workspace_id'))
    project_root(root, workspace)  # Deleted projects require explicit recovery, never silent resurrection.
    checkpoint = manifest.get('checkpoint', '')
    if not re.fullmatch('[a-f0-9]{32}', checkpoint):
        raise ValueError('Invalid project checkpoint.')
    base = checked(folder, 'project-data', checkpoint)
    state_path = base / 'state.json'
    if state_path.is_symlink() or digest(state_path) != manifest.get('state_sha256'):
        raise ValueError('Project checkpoint has changed or is incomplete.')
    snapshot = read(state_path)
    if snapshot.get('version') != 1 or snapshot.get('workspace_id') != workspace:
        raise ValueError('Project checkpoint identity does not match.')
    memory = browser_state(snapshot.get('browser_state', {}))
    # Existing local data wins: never roll back work performed since Save project.
    registered = records(root).get(workspace)
    if registered and Path(registered).resolve() == folder:
        return activate(root, workspace, manifest['title'], read(home(root) / f'{workspace}.json', memory))
    if registered and not Path(registered).exists():
        # A moved folder keeps the newer application state, just like reopening
        # its old location. Only this project's internal destinations move.
        with sqlite3.connect(database_path(root, DATABASES[0])) as db:
            local = db.execute('SELECT 1 FROM story_workspaces WHERE workspace_id=?', (workspace,)).fetchone()
        if local:
            latest = read(home(root) / f'{workspace}.json', memory)
            for name, item in session_grants(root, workspace, Path(registered), latest).items():
                if item.get('relative') is not None:
                    target = folder / item['relative']
                    if any(p.is_symlink() for p in (target, *target.parents)):
                        raise ValueError('Moved output folder cannot use symlinks.')
                    target.mkdir(parents=True, exist_ok=True)
                    write(Path(root) / name, {'path': str(target)})
            folders = records(root)
            folders[workspace] = str(folder)
            write(home(root) / 'folders.json', folders)
            return activate(root, workspace, manifest['title'], latest)
    pending = []
    for item in snapshot.get('files', []):
        relative = Path(item['path'])
        if relative.is_absolute() or '..' in relative.parts or relative.parts[:1] not in {('content',), ('runtime',)}:
            raise ValueError('Invalid project file location.')
        source = base / relative
        if any(p.is_symlink() for p in (source, *source.parents)) or digest(source) != item['sha256']:
            raise ValueError('Project content is missing or has changed.')
        target = project_root(root, workspace) / Path(*relative.parts[1:]) if relative.parts[0] == 'content' else Path(root) / Path(*relative.parts[1:])
        if relative.parts[0] == 'runtime' and not valid_runtime(Path(*relative.parts[1:])):
            raise ValueError('Invalid project runtime file.')
        if relative.parts[:4] == ('runtime', 'services', 'media', 'jobs') and relative.name == 'job.json':
            job = read(source)
            if job.get('request', {}).get('workspace_id') != workspace or job.get('status') in ACTIVE:
                raise ValueError('Saved project jobs must be settled and belong to this project.')
        if any(p.is_symlink() for p in (target, *target.parents)):
            raise ValueError('Local project storage cannot use symlinks.')
        if target.exists() and (target.is_symlink() or digest(target) != item['sha256']):
            raise ValueError('Newer local project content exists. Save it before opening this checkpoint.')
        pending.append((source, target))
    editor_state_path = Path(root) / 'services/editor/state.json'
    existing_styles = read(editor_state_path, {}).get('styles', [])
    for style in snapshot.get('editor_styles', []):
        if any(item['id'] == style['id'] and item != style for item in existing_styles):
            raise ValueError('A newer shared Editor style exists. It was not overwritten.')
    restored_grants = []
    for name, item in snapshot.get('folder_grants', {}).items():
        relative = Path(name)
        allowed = {'library/output_destinations/grants', 'trellis.2/projects', 'music_jukebox/folders'}
        if relative.parent.as_posix() not in allowed or not re.fullmatch(r'(folder-)?[a-f0-9]{32}\.json', relative.name):
            raise ValueError('Invalid session folder grant.')
        sub = item.get('relative')
        if sub is None:
            continue  # External destinations require an explicit Choose/Locate action.
        sub = Path(sub)
        if sub.is_absolute() or '..' in sub.parts:
            raise ValueError('Invalid session output path.')
        target = folder / sub
        if any(p.is_symlink() for p in (target, *target.parents)):
            raise ValueError('Invalid session output folder.')
        restored_grants.append((Path(root) / relative, target))
    for name, item in snapshot.get('preferences', {}).items():
        if not re.fullmatch(r'[a-z-]+--' + re.escape(workspace) + r'\.json', name) or name.split('--')[0] not in TOOLS:
            raise ValueError('Invalid output preference.')
        if not isinstance(item.get('choice'), dict) or not re.fullmatch('[a-f0-9]{32}', item['choice'].get('grant', '')):
            raise ValueError('Invalid output grant.')
        sub = item.get('relative')
        if sub is not None:
            relative = Path(sub)
            if relative.is_absolute() or '..' in relative.parts:
                raise ValueError('Invalid project output path.')
            target = folder / relative
            if any(p.is_symlink() for p in (target, *target.parents)):
                raise ValueError('Output folder cannot use symlinks.')
        elif not isinstance(item.get('path'), str) or not Path(item['path']).is_absolute():
            raise ValueError('Invalid external output path.')
    for source, target in pending:
        if target.name == 'project.json' and target.parent.parent.name == 'jukebox':
            value = read(source)
            if value.get('workspace_id') != workspace or not re.fullmatch(r'jukebox-[a-f0-9]{12}', value.get('id', '')):
                raise ValueError('Music session ownership mismatch.')
    previous_root = snapshot.get('source_root')
    if previous_root and (not isinstance(previous_root, str) or not Path(previous_root).is_absolute() or len(Path(previous_root).parts) < 3):
        raise ValueError('Invalid project runtime location.')
    databases = snapshot.get('databases', {})
    if set(databases) - set(DATABASES):
        raise ValueError('Unsupported project database.')
    created_files = []
    with sqlite3.connect(database_path(root, DATABASES[0])) as db:
        for index, name in enumerate(DATABASES[1:], 1):
            if databases.get(name):
                db.execute(f'ATTACH DATABASE ? AS db{index}', (str(database_path(root, name)),))
        try:
            db.execute('BEGIN IMMEDIATE')
            for index, name in enumerate(DATABASES):
                tables = databases.get(name, {})
                if not tables:
                    continue
                alias = 'main' if index == 0 else f'db{index}'
                known = {r[0] for r in db.execute(f"SELECT name FROM {alias}.sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
                for table, rows in tables.items():
                    if table not in known:
                        raise ValueError('Project requires a newer application schema.')
                    schema = list(db.execute(f'PRAGMA {alias}.table_info("{table}")'))
                    columns = [r[1] for r in schema]
                    keys = [r[1] for r in schema if r[5]]
                    if not keys:
                        raise ValueError('Project table has no stable identity.')
                    for row in rows:
                        if set(row) != set(columns) or row.get('workspace_id', row.get('project_id', workspace)) != workspace:
                            raise ValueError('Project database ownership or schema mismatch.')
                        if row.get('status', row.get('state', row.get('run_state'))) in ACTIVE:
                            raise ValueError('Saved project jobs must be settled before importing.')
                        where = ' AND '.join(f'"{key}"=?' for key in keys)
                        existing = db.execute(f'SELECT * FROM {alias}."{table}" WHERE {where}', [row[k] for k in keys]).fetchone() if keys else None
                        if existing and list(existing) != [row[k] for k in columns]:
                            raise ValueError('Newer local project records exist. No records were overwritten.')
                        if not existing:
                            names = ','.join(f'"{c}"' for c in columns)
                            db.execute(f'INSERT INTO {alias}."{table}" ({names}) VALUES ({",".join("?" for _ in columns)})', [row[c] for c in columns])
            for source, target in pending:
                target.parent.mkdir(parents=True, exist_ok=True)
                if not target.exists():
                    # Copy to a temporary sibling first; a failed copy never leaves a partial file.
                    from .output_destinations import copy_verified
                    copy_verified(source, target)
                    created_files.append(target)
            db.commit()
        except Exception:
            db.rollback()
            for target in created_files:
                target.unlink(missing_ok=True)
            raise
    for record, target in restored_grants:
        target.mkdir(parents=True, exist_ok=True)
        write(record, {'path': str(target)})
    jukebox_registry = checked(root, 'library', 'jukebox-sessions.json')
    owners = read(jukebox_registry, {})
    for document in (project_root(root, workspace) / 'music/jukebox').glob('*/project.json'):
        value = read(document)
        if value.get('workspace_id') != workspace:
            raise ValueError('Music session ownership mismatch.')
        owners[value['id']] = workspace
    if owners:
        write(jukebox_registry, owners)
    # Service registries contain only locators; rebuild entries for imported sessions.
    from . import vibe_editor, ace_studio
    with vibe_editor.state(root) as editor_state:
        for style in snapshot.get('editor_styles', []):
            if not any(item['id'] == style['id'] for item in editor_state['styles']):
                editor_state['styles'].append(style)
    with ace_studio.state(root):
        pass
    for tool, location, prefix in (('editor', 'services/editor/state.json', 'editor/editor'), ('ace', 'ace_step/state.json', 'music/ace')):
        registry_path = Path(root) / location
        registry = read(registry_path, {})
        paths = [p.relative_to(root).as_posix() for p in (project_root(root, workspace) / prefix).glob('*/project.json')]
        if paths:
            registry.setdefault('project_files', []).extend(p for p in paths if p not in registry.get('project_files', []))
            write(registry_path, registry)
    for name, item in snapshot.get('preferences', {}).items():
        if not re.fullmatch(r'[a-z-]+--' + re.escape(workspace) + r'\.json', name):
            raise ValueError('Invalid output preference.')
        token = item['choice'].get('grant', '')
        if not re.fullmatch('[a-f0-9]{32}', token):
            raise ValueError('Invalid output grant.')
        relative = item.get('relative')
        if relative is not None:
            sub = Path(relative)
            if sub.is_absolute() or '..' in sub.parts:
                raise ValueError('Invalid project output path.')
            target = folder / sub
        else:
            target = Path(item['path'])
        # A saved manifest is not a new external folder grant. Only regrant paths
        # inside the explicitly opened project; external dependencies need Locate.
        if relative is not None:
            if any(p.is_symlink() for p in (target, *target.parents)):
                raise ValueError('Output folder cannot use symlinks.')
            target.mkdir(parents=True, exist_ok=True)
            write(checked(root, 'library', 'output_destinations', 'grants') / f'{token}.json', {'path': str(target)})
        pref = checked(root, 'library', 'output_destinations', 'preferences') / name
        if not pref.exists():
            write(pref, item['choice'])
    relocations = read(home(root) / 'runtime-locations.json', {})
    previous_root = snapshot.get('source_root')
    if previous_root and previous_root != str(Path(root).resolve()):
        relocations[previous_root] = str(Path(root).resolve())
        write(home(root) / 'runtime-locations.json', relocations)
    folders = records(root)
    folders[workspace] = str(folder)
    write(home(root) / 'folders.json', folders)
    return activate(root, workspace, manifest['title'], memory)


def handle(root, story, environ, start_response, read_json, respond):
    method, path = environ.get('REQUEST_METHOD'), environ.get('PATH_INFO')
    with locked(root):
        if method == 'GET' and path == '/api/projects/current':
            return respond(start_response, '200 OK', current(root))
        if method != 'POST':
            return respond(start_response, '405 Method Not Allowed', {'error': {'message': 'Use POST for project operations.'}})
        body = read_json(environ)
        if path == '/api/projects/choose-folder':
            selected = grant(root, body.get('path'))
            return respond(start_response, '200 OK', selected)
        if path == '/api/projects/memory':
            workspace = body.get('workspace_id')
            checked(root, 'projects', workspace)
            write(home(root) / f'{workspace}.json', browser_state(body.get('browser_state', {})))
            return respond(start_response, '200 OK', {'saved': True})
        active = current(root)
        assert_idle(root, active['workspace_id'])
        if path == '/api/projects/save':
            result = save(root, identity(body.get('workspace_id')), body.get('folder') or records(root).get(body.get('workspace_id')), body.get('browser_state', {}))
        elif path == '/api/projects/open':
            result = open_project(root, body.get('folder'))
        elif path == '/api/projects/new':
            title = str(body.get('title', '')).strip()
            if not title or len(title) > 120:
                raise ValueError('Enter a project name (1–120 characters).')
            # New UI chooses a parent; retain the exact-folder contract for older callers.
            create_child = 'parent_folder' in body
            workspace = 'story-' + uuid.uuid4().hex[:12]
            folder_registry = None
            if create_child:
                default_parent = checked(root, 'projects')
                default_parent.mkdir(parents=True, exist_ok=True)
                parent = folder_path(body.get('parent_folder') or default_parent)
                if parent != default_parent.resolve():
                    parent = validate_folder(root, parent)
                name = re.sub(r'[^A-Za-z0-9 _.-]+', '-', title).strip(' .-')[:100].rstrip(' .') or 'Project'
                folder = parent / name
                if folder.exists() or folder.is_symlink():
                    raise ValueError('A folder with this project name already exists. Use Open project or choose another name.')
                if parent == default_parent.resolve():
                    folder_registry = project_folders(root)
                    if name in folder_registry.values():
                        raise ValueError('This project folder name is already registered. Choose another name.')
                folder.mkdir()
            else:
                folder = validate_folder(root, body.get('folder'))
            if (folder / 'vibe-project.json').exists():
                raise ValueError('This folder already contains a project. Use Open project.')
            with sqlite3.connect(database_path(root, DATABASES[0])) as db:
                db.execute('INSERT INTO story_workspaces(workspace_id,title,authoring_uuid) VALUES(?,?,?)', (workspace, title, str(uuid.uuid4())))
            try:
                if folder_registry is not None:
                    write(checked(root, 'library') / 'project-folders.json', {**folder_registry, workspace: folder.name})
                result = save(root, workspace, folder, {})
            except Exception:
                with sqlite3.connect(database_path(root, DATABASES[0])) as db:
                    db.execute('DELETE FROM story_workspaces WHERE workspace_id=?', (workspace,))
                if folder_registry is not None:
                    write(checked(root, 'library') / 'project-folders.json', folder_registry)
                if create_child:
                    try:
                        folder.rmdir()  # Only remove our newly created directory if still empty.
                    except OSError:
                        pass
                raise
            result = activate(root, workspace, title, {})
        elif path == '/api/projects/select':
            workspace = body.get('workspace_id')
            if workspace == 'tool-library':
                result = activate(root, workspace, 'Standalone tools', read(home(root) / 'tool-library.json', {}))
            else:
                assert_idle(root, workspace)
                item = story.get_workspace(identity(workspace))
                project_root(root, workspace)
                result = activate(root, workspace, item['title'], read(home(root) / f'{workspace}.json', {}))
        else:
            raise ValueError('Unknown project operation.')
        # Frozen destinations on existing jobs are never rewritten.
        if result.get('folder'):
            output_defaults(root, result['workspace_id'], result['folder'])
        return respond(start_response, '200 OK', result)
