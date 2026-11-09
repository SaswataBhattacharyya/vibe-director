"""Explicit project notes with immutable revisions and optimistic concurrency."""
from . import agent_graph, projects
from .production_ledger import LedgerConflict, _now


def read(root, ledger, owner):
    agent_graph.resolve_workspace(root, owner)
    return read_saved(ledger, owner)


def read_saved(ledger, owner):
    """Read exact-owner notes after the calling surface validates its own context."""
    with ledger._connect() as db:
        row = db.execute('SELECT revision,content FROM agent_knowledge WHERE project_id=? ORDER BY revision DESC LIMIT 1', (owner,)).fetchone()
    return {'workspace_id': owner, 'revision': row['revision'] if row else 0, 'content': row['content'] if row else ''}


def save(root, ledger, owner, payload):
    if (not isinstance(payload, dict) or set(payload) != {'revision', 'content'}
            or type(payload['revision']) is not int or not isinstance(payload['content'], str)
            or len(payload['content']) > 16000):
        raise ValueError('Supply current revision and up to 16000 characters of project knowledge.')
    with projects.locked(root), ledger._connect() as db:
        agent_graph.resolve_workspace(root, owner)
        db.execute('BEGIN IMMEDIATE')
        revision = db.execute('SELECT COALESCE(MAX(revision),0) FROM agent_knowledge WHERE project_id=?', (owner,)).fetchone()[0]
        if payload['revision'] != revision:
            raise LedgerConflict('Project knowledge changed. Reload the latest notes before saving.')
        db.execute('INSERT INTO agent_knowledge VALUES (?,?,?,?)', (owner, revision + 1, payload['content'], _now()))
        db.commit()
    return read(root, ledger, owner)
