"""Immutable brief/media shot outlines, separate from screenplay acceptance/history."""
import json
import uuid
from contextlib import closing

from . import agent_graph, media_library, projects
from .production_ledger import LedgerConflict, LedgerNotFound, stable_hash


def setup(ledger):
    with closing(ledger._connect()) as db:
        db.execute('''CREATE TABLE IF NOT EXISTS story_board_sources (
            workspace_id TEXT NOT NULL, source_id TEXT NOT NULL, request_hash TEXT NOT NULL,
            envelope_json TEXT NOT NULL, PRIMARY KEY(workspace_id, source_id))''')
        db.commit()


def get(board, owner, source):
    agent_graph.resolve_workspace(board.root, owner)
    with closing(board.ledger._connect()) as db:
        row = db.execute('SELECT envelope_json FROM story_board_sources WHERE workspace_id=? AND source_id=?',
                         (owner, source)).fetchone()
    if row is None:
        raise LedgerNotFound('Storyboard outline not found in this project.')
    return json.loads(row[0])


def list_sources(board, owner):
    agent_graph.resolve_workspace(board.root, owner)
    with closing(board.ledger._connect()) as db:
        rows = db.execute('SELECT source_id,envelope_json FROM story_board_sources WHERE workspace_id=? ORDER BY rowid DESC LIMIT 100', (owner,)).fetchall()
    return {'sources': [{'source_id': r[0], 'title': json.loads(r[1])['screenplay']['title']} for r in rows]}


def create(board, owner, body):
    if not isinstance(body, dict) or set(body) != {'request_id', 'title', 'brief', 'asset_ids'}:
        raise ValueError('Supply request_id, title, brief and ordered asset_ids.')
    try:
        request = str(uuid.UUID(body['request_id']))
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError('Supply a UUID request identity.') from exc
    if (not isinstance(body['title'], str) or not 1 <= len(body['title'].strip()) <= 200
            or not isinstance(body['brief'], str) or len(body['brief']) > 16000):
        raise ValueError('Use a title (1–200 characters) and a brief of at most 16000 characters.')
    ids = body['asset_ids']
    if not isinstance(ids, list) or len(ids) > 100 or any(not isinstance(a, str) for a in ids) or len(set(ids)) != len(ids):
        raise ValueError('Choose up to 100 distinct project images/videos in shot order.')
    lines = [line.strip() for line in body['brief'].splitlines() if line.strip()]
    count = max(len(lines), len(ids))
    if any(len(line) > 6000 for line in lines):
        raise ValueError('Keep each shot outline below 6001 characters.')
    if not 1 <= count <= 100:
        raise ValueError('Write one shot per line or choose media (at most 100 shots).')
    source = 'board-' + request
    with projects.locked(board.root):
        agent_graph.resolve_workspace(board.root, owner)
        digest = stable_hash(body)
        with closing(board.ledger._connect()) as db:
            prior = db.execute('SELECT request_hash FROM story_board_sources WHERE workspace_id=? AND source_id=?', (owner, source)).fetchone()
        if prior:
            if prior[0] != digest:
                raise LedgerConflict('This storyboard request identity belongs to different content.')
            state = board.get(owner, source)
            if not state['revision']:
                state = board.save(owner, source, {'expected_revision': 0, 'body': state['body']})
            return {'source': get(board, owner, source), 'board': state}
        assets = board.assets(owner)
        for aid in ids:
            record = assets.get(aid)
            if not record or record['kind'] not in {'image', 'video'} or record.get('archived_at'):
                raise ValueError('Select current project images or videos.')
            path, _, _ = media_library.asset_path(board.root, owner, aid)
            if projects.digest(path) != record['sha256']:
                raise LedgerConflict('Source media changed. Re-register it before starting this board.')
        shots = []
        for index in range(count):
            asset = assets[ids[index]] if index < len(ids) else None
            duration = 2 if asset and asset['kind'] == 'image' else 6
            if asset and asset['kind'] == 'video':
                path, _, _ = media_library.asset_path(board.root, owner, asset['asset_id'])
                duration = min(6, media_library._probe(path, 'video')['duration_seconds'])
            shots.append({'shot_number': index + 1, 'presentation': asset['kind'] if asset else 'video',
                'planned_duration_seconds': duration,
                'action': lines[index] if index < len(lines) else asset['filename'], 'dialogue': '',
                'direction': {k: '' for k in ('camera', 'lighting', 'mood', 'sfx', 'music')}, 'evidence': []})
        envelope = {'workspace_id': owner, 'screenplay_revision_id': source, 'source_kind': 'brief_media',
            'accepted': False, 'source_assets': [{'asset_id': aid, 'sha256': assets[aid]['sha256']} for aid in ids],
            'screenplay': {'title': body['title'].strip(), 'coverage_note': 'Owner-authored shot outline; no screenplay acceptance.',
                'scenes': [{'scene_number': 1, 'slugline': body['title'].strip(), 'summary': body['brief'], 'shots': shots}]}}
        with closing(board.ledger._connect()) as db:
            db.execute('INSERT INTO story_board_sources VALUES (?,?,?,?)', (owner, source, digest, json.dumps(envelope)))
            db.commit()
        state = board.get(owner, source)
        for index, aid in enumerate(ids, 1):
            shot, asset = state['body']['shots'][f'1.{index}'], assets[aid]
            shot.update(media_asset_id=aid, route='existing')
            if asset['kind'] == 'image':
                shot['image_asset_id'] = aid
        saved = board.save(owner, source, {'expected_revision': 0, 'body': state['body']})
        return {'source': envelope, 'board': saved}
