"""Reviewed frame takes, backed by existing image jobs and project checkpoints."""
import copy
import json
import uuid

from . import agent_graph, media_library, projects
from .production_image_jobs import ProductionImageJobStore
from .production_image_workflows import compile_image_candidates
from .production_ledger import LedgerConflict, LedgerNotFound

TOOLS = {'image.generate_next_keyframe': 'next', 'video.interpolate_keyframes': 'interpolate',
         'video.export_frame_sequence': 'export'}


def store(root):
    result = ProductionImageJobStore(projects.database_path(root, projects.DATABASES[1]))
    with result._connect() as db:
        db.execute('CREATE TABLE IF NOT EXISTS frame_pipeline_takes '
                   '(project_id TEXT NOT NULL,take_id TEXT NOT NULL,revision INTEGER NOT NULL,'
                   'document_json TEXT NOT NULL,PRIMARY KEY(project_id,take_id))')
    return result


def image(root, owner, asset_id, sha256=None):
    from .frame_interpolation import dimensions
    path, mime, name = media_library.asset_path(root, owner, asset_id)
    digest = projects.digest(path)
    if not mime.startswith('image/') or sha256 is not None and digest != sha256:
        raise LedgerConflict('Keyframe is missing or changed; select and review it again.')
    width, height = dimensions(path)
    return {'asset_id': asset_id, 'sha256': digest, 'filename': name,
            'width': width, 'height': height}


def list_takes(root, owner):
    agent_graph.resolve_workspace(root, owner)
    with store(root)._connect() as db:
        return [json.loads(r[0]) for r in db.execute(
            'SELECT document_json FROM frame_pipeline_takes WHERE project_id=? ORDER BY rowid DESC', (owner,))]


def get(root, owner, take_id):
    agent_graph.resolve_workspace(root, owner)
    with store(root)._connect() as db:
        row = db.execute('SELECT document_json FROM frame_pipeline_takes WHERE project_id=? AND take_id=?',
                         (owner, take_id)).fetchone()
    if row is None:
        raise LedgerNotFound('Frame take not found in this project.')
    take = json.loads(row[0])
    for key in take['keys']:
        if key.get('job_id'):
            job = store(root).get_job(project_id=owner, job_id=key['job_id'])
            key['job_status'] = job['status']
            key['error'] = job.get('error')
            if job.get('output_asset_id'):
                key['image'] = image(root, owner, job['output_asset_id'], (key.get('image') or {}).get('sha256'))
    return take


def save(root, take, expected=None):
    # This table is included by the existing project snapshot's project_id filter.
    with store(root)._connect() as db:
        if expected is None:
            db.execute('INSERT INTO frame_pipeline_takes VALUES (?,?,?,?)',
                       (take['project_id'], take['take_id'], take['revision'], json.dumps(take)))
        else:
            changed = db.execute('UPDATE frame_pipeline_takes SET revision=?,document_json=? '
                'WHERE project_id=? AND take_id=? AND revision=?', (take['revision'], json.dumps(take),
                    take['project_id'], take['take_id'], expected)).rowcount
            if changed != 1:
                raise LedgerConflict('Frame take changed. Reload before continuing.')
    return take


def create(root, owner, asset_id, *, parent=None, normalize=False):
    agent_graph.resolve_workspace(root, owner)
    source = image(root, owner, asset_id)
    if type(normalize) is not bool:
        raise ValueError('Canvas normalization must be true or false.')
    if normalize:
        from .frame_canvas import normalize as normalize_canvas
        source = image(root, owner, normalize_canvas(root, owner, source))
    take = {'project_id': owner, 'take_id': 'take-' + uuid.uuid4().hex, 'revision': 1,
            'parent': parent, 'keys': [{'key_id': 'key-' + uuid.uuid4().hex,
                'image': source, 'review': 'candidate', 'previous_key_id': None}], 'events': []}
    return save(root, take)


def endpoints(root, owner, take_id, revision):
    take = get(root, owner, take_id)
    expected(take, revision)
    keys = approved(root, owner, take, minimum=2)
    return {'take_id': take_id, 'revision': revision, 'first_frame': keys[0]['image'],
            'last_frame': keys[-1]['image']}


def expected(take, revision):
    if type(revision) is not int or revision != take['revision']:
        raise LedgerConflict('Frame take changed. Reload before continuing.')


def approved(root, owner, take, *, minimum=1):
    keys = [k for k in take['keys'] if k['review'] != 'rejected']
    if len(keys) < minimum or any(k['review'] != 'approved' or not k.get('image') for k in keys):
        raise ValueError('Review and approve every active keyframe before continuing.')
    for key in keys:
        image(root, owner, key['image']['asset_id'], key['image']['sha256'])
    return keys


def change(root, owner, take_id, payload):
    with projects.locked(root):
        take = get(root, owner, take_id)
        revision = payload.get('revision')
        expected(take, revision)
        operation = payload.get('operation')
        if operation == 'review':
            if set(payload) != {'operation', 'revision', 'key_id', 'decision'} or payload['decision'] not in {'approved', 'rejected'}:
                raise ValueError('Review needs key_id and approved/rejected decision.')
            key = next((k for k in take['keys'] if k['key_id'] == payload['key_id']), None)
            if key is None or key['review'] != 'candidate' or (not key.get('image') and not (payload['decision'] == 'rejected' and key.get('job_status') in {'failed', 'cancelled'})):
                raise ValueError('Choose a completed, unreviewed candidate.')
            if payload['decision'] == 'approved':
                image(root, owner, key['image']['asset_id'], key['image']['sha256'])
                earlier = [k for k in take['keys'][:take['keys'].index(key)] if k['review'] != 'rejected']
                if earlier and (key['image']['width'], key['image']['height']) != (earlier[0]['image']['width'], earlier[0]['image']['height']):
                    raise ValueError('Dimensions differ from the approved starting canvas. Normalize the image explicitly and import it as a replacement.')
            key['review'] = payload['decision']
        elif operation == 'append':
            if set(payload) != {'operation', 'revision', 'asset_id'}:
                raise ValueError('Append needs a registered image asset_id.')
            keys = approved(root, owner, take, minimum=0)
            take['keys'].append({'key_id': 'key-' + uuid.uuid4().hex,
                'previous_key_id': keys[-1]['key_id'] if keys else None, 'review': 'candidate',
                'image': image(root, owner, payload['asset_id'])})
        elif operation == 'branch':
            if set(payload) != {'operation', 'revision', 'key_id'}:
                raise ValueError('Branch needs an approved key_id.')
            index = next((i for i,k in enumerate(take['keys']) if k['key_id'] == payload['key_id'] and k['review'] == 'approved'), None)
            if index is None:
                raise ValueError('Branch from an approved keyframe.')
            branch = copy.deepcopy(take)
            branch.update(take_id='take-' + uuid.uuid4().hex, revision=1,
                          parent={'take_id': take_id, 'key_id': payload['key_id']}, events=[])
            branch['keys'] = branch['keys'][:index+1]
            return save(root, branch)
        else:
            raise ValueError('Unknown frame review action.')
        take['events'].append({**payload})
        take['revision'] += 1
        return save(root, take, revision)


def prepare(root, owner, tool, settings):
    if tool not in TOOLS or not isinstance(settings, dict):
        raise ValueError('Unsupported frame-pipeline tool.')
    operation = TOOLS[tool]
    required = {'take_id', 'revision'} | ({'prompt', 'seed'} if operation == 'next' else {'model', 'multiplier', 'fps', 'hold'} if operation == 'interpolate' else {'sequence_job_id'})
    if set(settings) != required:
        raise ValueError('Required frame settings: ' + ', '.join(sorted(required)))
    take = get(root, owner, settings['take_id'])
    expected(take, settings['revision'])
    keys = approved(root, owner, take, minimum=1 if operation == 'next' else 2)
    if operation == 'next' and len(take['keys']) >= 100:
        raise ValueError('Use a new take after 100 candidates.')
    if operation == 'next':
        if type(settings['seed']) is not int:
            raise ValueError('Seed must be an integer.')
        compile_image_candidates(workflow_id='flux_kontext_dev', prompt=settings['prompt'], seed=settings['seed'],
            output_prefix='frame-pipeline/check', control_mode='assisted_manual', source_images=['reference.png'], initial_candidate_count=1)
    elif operation == 'interpolate':
        from .frame_interpolation import validate_settings
        validate_settings({k: settings[k] for k in ('model', 'multiplier', 'fps', 'hold')})
        if len({(k['image']['width'], k['image']['height']) for k in keys}) != 1:
            raise ValueError('All interpolation keys must have identical dimensions.')
    elif operation == 'export':
        from . import video_repertoire
        job = video_repertoire.read_job('frame-pipeline', settings['sequence_job_id'])
        request = job['request']
        if job['status'] != 'completed' or request.get('workspace_id') != owner or request.get('operation') != 'interpolate' or request['inputs'] != [k['image'] for k in keys] or request['settings']['take_id'] != take['take_id'] or request['settings']['revision'] != take['revision']:
            raise LedgerConflict('Choose a completed interpolation for this exact reviewed take revision.')
    return [k['image'] for k in (keys[-1:] if operation == 'next' else keys)]


def next_key(root, owner, settings):
    with projects.locked(root):
        take = get(root, owner, settings['take_id'])
        # Replay after a crash or lost worker response returns the exact queued key.
        old = next((k for k in take['keys'] if k.get('request') == settings), None)
        if old:
            return {'workspace_id': owner, 'take_id': take['take_id'], 'key_id': old['key_id'], 'image_job_id': old['job_id']}
        sources = prepare(root, owner, 'image.generate_next_keyframe', settings)
        compiled = compile_image_candidates(workflow_id='flux_kontext_dev', prompt=settings['prompt'], seed=settings['seed'],
            output_prefix=f"frame-pipeline/{take['take_id']}/{take['revision']}", control_mode='assisted_manual',
            source_images=['reference.png'], initial_candidate_count=1)
        compiled['settings']['image_references'] = [{'asset_id': sources[0]['asset_id'], 'sha256': sources[0]['sha256']}]
        batch = {**compiled, 'project_id': owner, 'run_id': 'frame-' + take['take_id'],
                 'idempotency_key': f"{take['take_id']}-{take['revision']}", 'asset_role': 'image_candidate'}
        result = store(root).enqueue_batches([batch])[0]
        key = {'key_id': 'key-' + uuid.uuid4().hex, 'review': 'candidate',
            'previous_key_id': next(k['key_id'] for k in reversed(take['keys']) if k['review'] == 'approved'),
            'job_id': result['jobs'][0]['job_id'], 'batch_id': result['batch_id'], 'request': settings}
        take['keys'].append(key)
        take['revision'] += 1
        save(root, take, settings['revision'])
        return {'workspace_id': owner, 'take_id': take['take_id'], 'key_id': key['key_id'], 'image_job_id': key['job_id']}
