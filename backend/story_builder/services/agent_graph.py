"""Bounded, non-mutating projections of existing project records."""
import hashlib
import json
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from . import projects
from .storage_paths import project_root, media_root

LIMIT = 100


def read_json(root, path, default=None):
    root, path = Path(root).resolve(), Path(path)
    if not path.is_relative_to(root) or any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('Unsafe context source.')
    if not path.exists():
        return default
    if not path.is_file():
        raise ValueError('Context source must be a regular file.')
    with path.open('rb') as stream:
        content = stream.read(4_000_001)
    if len(content) > 4_000_000:
        raise ValueError('Context source exceeds its read budget.')
    return json.loads(content)


@contextmanager
def database(root):
    path = projects.database_path(root, projects.DATABASES[0])
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('Unsafe project database.')
    db = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)
    try:
        db.row_factory = sqlite3.Row
        yield db
    finally:
        db.close()


def resolve_workspace(root: Path, workspace: str) -> dict:
    if not isinstance(workspace, str) or not re.fullmatch(r'(?:tool-library|story-[a-f0-9]{12})', workspace):
        raise ValueError('Invalid agent workspace.')
    active = read_json(root, Path(root) / 'library/projects/active.json', {})
    if active.get('workspace_id', 'tool-library') != workspace:
        raise ValueError('Agent workspace must match the open project.')
    if workspace == 'tool-library':
        return {'workspace_id': workspace, 'title': 'Standalone tools', 'current_revision_id': None}
    project_root(root, workspace)  # Retired projects and unsafe folders are rejected.
    with database(root) as db:
        row = db.execute('SELECT workspace_id,title,current_revision_id FROM story_workspaces WHERE workspace_id=?', (workspace,)).fetchone()
    if row is None:
        raise ValueError('Agent project is unavailable.')
    return dict(row)


def context(root: Path, owner: dict) -> dict:
    workspace = owner['workspace_id']
    nodes, relations, truncated = [], [], []
    seen = set()
    def add(kind, source_id, provenance, *, revision=None, sha256=None, label=None):
        ident = f'{kind}:{source_id}'
        if ident in seen:
            return
        seen.add(ident)
        nodes.append({'id': ident, 'kind': kind, 'source_id': source_id, 'owner': workspace,
            'revision': revision, 'sha256': sha256, 'provenance': provenance, 'label': label or source_id})
        if kind != 'workspace':
            relations.append({'from': f'workspace:{workspace}', 'to': ident, 'kind': 'contains'})
    add('workspace', workspace, 'project registry', label=owner['title'])
    if owner.get('current_revision_id'):
        with database(root) as db:
            row = db.execute('SELECT revision_id,revision_number,source_sha256 FROM story_revision_index WHERE workspace_id=? AND revision_id=?',
                (workspace, owner['current_revision_id'])).fetchone()
        if row:
            add('story_revision', row['revision_id'], 'story_revision_index', revision=row['revision_number'], sha256=row['source_sha256'])
    manifest = read_json(root, media_root(root, workspace) / 'assets.json', {'assets': []})
    assets = [a for a in manifest['assets'] if a.get('workspace_id') == workspace and not a.get('archived_at')]
    for row in assets[:LIMIT]:
        add('asset', row['asset_id'], 'registered media manifest', sha256=row.get('sha256'), label=row.get('filename'))
    if len(assets) > LIMIT:
        truncated.append('assets')
    state = read_json(root, Path(root) / 'services/editor/state.json', {})
    sessions = list(state.get('projects', []))
    for relative in state.get('project_files', [])[:LIMIT]:
        path = Path(relative)
        if path.is_absolute() or '..' in path.parts or path.parts[:1] != ('projects',):
            raise ValueError('Unsafe Editor registry entry.')
        # Do not read another project's document just to filter its contents.
        base = project_root(root, workspace)
        candidate = Path(root) / path
        if candidate.is_relative_to(base / 'editor'):
            sessions.append(read_json(root, candidate, {}))
    owned = [p for p in sessions if p.get('workspace_id') == workspace]
    for row in owned[:LIMIT]:
        digest = hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()
        add('editor_session', row['id'], 'Editor project document', revision=row.get('revision'), sha256=digest)
    if len(owned) > LIMIT or len(state.get('project_files', [])) > LIMIT:
        truncated.append('editor_sessions')
    # Read only jobs explicitly referenced by owned Editor sessions. No worker recovery polling.
    from .video_repertoire import JOB_KINDS
    for row in owned[:LIMIT]:
        job_id = row.get('job_id')
        if not isinstance(job_id, str) or not re.fullmatch(r'[a-z0-9-]{1,100}', job_id):
            continue
        kind = next((k for k in JOB_KINDS if job_id.startswith(k + '-')), None)
        if not kind:
            continue
        job = read_json(root, Path(root) / 'services/media/jobs' / kind / job_id / 'job.json', {})
        if job.get('request', {}).get('workspace_id') == workspace and job.get('job_id') == job_id:
            add('job', job_id, 'durable media job', revision=job.get('updated_at'), label=job.get('status'))
            relations.append({'from': f"editor_session:{row['id']}", 'to': f'job:{job_id}', 'kind': 'references'})
    return {'workspace_id': workspace, 'nodes': nodes, 'relations': relations, 'truncated': truncated}
