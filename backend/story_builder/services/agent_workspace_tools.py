"""Bounded CPU workspace operations using existing media and Editor services."""
import json
import subprocess
from jsonschema import validate, ValidationError
from . import editor_layers, frame_pipeline, media_library, projects, video_repertoire, vibe_editor
from .production_ledger import stable_hash
from .storage_paths import generated_root

KIND = 'agent-workspace'
DESCRIPTIONS = {
    'media.list': 'List owned project media with pagination. Use returned IDs for subsequent tools.',
    'media.inspect': 'Read owned media metadata and probe duration, dimensions, streams and frame rate on CPU.',
    'video.sample_frames': 'Extract up to six explicitly timestamped video frames on CPU as owned images for attachment and visual inspection.',
    'editor.create_session': 'Create a new empty saved Editor session owned by this project. Does not approve a brief or render.',
    'editor.select_media': 'Set ordered, source-relative media ranges on an existing Editor session at its exact revision. Preserves originals and invalidates stale pending plans; never renders.',
    'editor.prepare_timeline': 'Prepare explicit cuts, clip order, captions, effects, speed, transitions, layers and soundtrack using the existing typed Editor plan. Requires saved selections and an approved brief; never renders.',
    'frame.create_take': 'Create a candidate keyframe take from one owned image. Owner frame review is still required.',
}
TOOLS = dict.fromkeys(DESCRIPTIONS, KIND)
INPUTS = {'media.list': ('', 0, 0), 'media.inspect': ('', 1, 100), 'video.sample_frames': ('video/', 1, 1),
          'frame.create_take': ('image/', 1, 1), 'editor.prepare_timeline': ('', 1, 100),
          'editor.create_session': ('', 0, 0), 'editor.select_media': ('', 1, 100)}


def schema(tool):
    fields = {
        'media.list': {'kind': {'enum': ['all', 'image', 'video', 'audio']}, 'offset': {'type': 'integer', 'minimum': 0}, 'limit': {'type': 'integer', 'minimum': 1, 'maximum': 100}},
        'media.inspect': {},
        'video.sample_frames': {'timestamps_seconds': {'type': 'array', 'minItems': 1, 'maxItems': 6, 'uniqueItems': True, 'items': {'type': 'number', 'minimum': 0}}},
        'editor.create_session': {'name': {'type': 'string', 'minLength': 1, 'maxLength': 100}},
        'editor.select_media': {'project_id': {'type': 'string'}, 'revision': {'type': 'integer', 'minimum': 0},
            'selection': {'type': 'array', 'minItems': 1, 'maxItems': 100, 'items': {'type': 'object', 'additionalProperties': False,
                'required': ['asset_id', 'start', 'end'], 'properties': {'asset_id': {'type': 'string'},
                    'start': {'type': 'number', 'minimum': 0}, 'end': {'type': 'number', 'exclusiveMinimum': 0}}}}},
        'editor.prepare_timeline': {'project_id': {'type': 'string'}, 'revision': {'type': 'integer', 'minimum': 0}, 'plan': {'type': 'object', 'description': 'Existing Editor plan: clips [{asset_id,start,end,caption?,fit?,effect?,speed?,transition?}], audio optional {asset_id,start,end}, layers optional; width,height,fps and backend hyperframes or kdenlive. Times are source-relative seconds.'}},
        'frame.create_take': {'normalize': {'type': 'boolean'}},
    }[tool]
    return {'type': 'object', 'additionalProperties': False, 'required': list(fields), 'properties': fields}


def prepare(root, owner, tool, settings):
    try:
        json.dumps(settings, allow_nan=False)
        validate(settings, schema(tool))
    except (ValueError, TypeError, ValidationError) as exc:
        raise ValueError('Invalid ' + tool + ' settings: ' + str(exc)) from exc
    if tool in {'editor.prepare_timeline', 'editor.select_media'}:
        with vibe_editor.state(root, readonly=True) as data:
            p = vibe_editor.project(data, settings['project_id'])
            vibe_editor.busy(p)
            if p['workspace_id'] != owner or p['revision'] != settings['revision']:
                raise ValueError('Editor ownership or revision changed. Refresh before preparing cuts.')
            if tool == 'editor.select_media':
                return {'selection': vibe_editor.validate_selection(root, owner, settings['selection']), 'session_sha256': stable_hash(p)}
            if not p.get('brief'):
                raise ValueError('Review and approve the Editor creative brief first.')
            plan = vibe_editor.selected_plan(root, p, settings['plan'])
            return {'plan': plan, 'session_sha256': stable_hash(p)}
    return {}


def validate_assets(root, owner, tool, settings, assets):
    _, low, high = INPUTS[tool]
    if not low <= len(assets) <= high:
        raise ValueError(f'{tool} requires {low}–{high} owned sources.')
    if tool == 'editor.prepare_timeline':
        expected = list(dict.fromkeys(r['asset_id'] for r in editor_layers.media_ranges(settings['snapshot']['plan'])))
        if expected != [a['asset_id'] for a in assets]:
            raise ValueError('Attach all timeline media in plan order, including soundtrack and media layers.')
    if tool == 'editor.select_media' and list(dict.fromkeys(s['asset_id'] for s in settings['selection'])) != [a['asset_id'] for a in assets]:
        raise ValueError('Attach exactly the selected sources in selection order.')
    for asset in assets:
        path, mime, _ = media_library.asset_path(root, owner, asset['asset_id'])
        if tool == 'frame.create_take' and not mime.startswith('image/'):
            raise ValueError('A keyframe take requires one image.')
        if tool == 'video.sample_frames':
            if not mime.startswith('video/'):
                raise ValueError('Frame sampling requires one video.')
            duration = media_library._probe(path, 'video')['duration_seconds']
            if any(t >= duration for t in settings['timestamps_seconds']):
                raise ValueError(f'Frame times must be before the video end ({duration:g} seconds).')


def submit(root, owner, tool, settings, assets):
    job = video_repertoire.create_job(KIND, {'workspace_id': owner, 'tool_id': tool, 'settings': settings, 'inputs': assets})
    return video_repertoire.start_job(KIND, job['job_id'])


def run(root, job_id, request):
    owner, tool, settings, assets = (request[k] for k in ('workspace_id', 'tool_id', 'settings', 'inputs'))
    original = {k: v for k, v in settings.items() if k != 'snapshot'}
    if prepare(root, owner, tool, original) != settings['snapshot']:
        raise ValueError('Workspace context changed since approval. Prepare a new task.')
    validate_assets(root, owner, tool, settings, assets)
    paths = []
    for asset in assets:
        path, mime, _ = media_library.asset_path(root, owner, asset['asset_id'])
        if projects.digest(path) != asset['sha256']:
            raise ValueError('Approved media changed.')
        paths.append((path, mime))
    if tool == 'media.list':
        result = media_library.list_assets(root, owner, kind=None if settings['kind'] == 'all' else settings['kind'], offset=settings['offset'], limit=settings['limit'])
    elif tool == 'media.inspect':
        result = {'sources': [{**a, 'mime': mime, 'metadata': media_library._probe(path, mime.split('/')[0])} for a, (path, mime) in zip(assets, paths)]}
    elif tool == 'frame.create_take':
        result = frame_pipeline.create(root, owner, assets[0]['asset_id'], normalize=settings['normalize'])
    elif tool == 'editor.create_session':
        p = vibe_editor.add_project(root, {'workspace_id': owner, 'name': settings['name']})
        result = {'project_id': p['id'], 'name': p['name'], 'revision': p['revision']}
    elif tool == 'editor.select_media':
        p = vibe_editor.update_project(root, settings['project_id'], {'selection': settings['selection']}, expected_revision=settings['revision'])
        result = {'project_id': p['id'], 'revision': p['revision'], 'selection': p['selection']}
    elif tool == 'editor.prepare_timeline':
        p = vibe_editor.propose_plan(root, settings['project_id'], {'revision': settings['revision'], 'plan': settings['snapshot']['plan']})
        result = {'project_id': p['id'], 'revision': p['revision'], 'pending_clearance': 'plan', 'plan': p['pending']['value']}
    elif tool == 'video.sample_frames':
        result = sample_frames(root, owner, job_id, assets[0], paths[0][0], settings['timestamps_seconds'])
    else:
        raise ValueError('Unknown workspace tool.')
    return {'workspace_id': owner, 'result': result}


def sample_frames(root, owner, job_id, asset, path, timestamps):
    # Generated outputs are deliberate persistent results; only transient files are
    # removed here. A failed extraction never touches the user's source.
    destination = generated_root(root, owner) / 'director-frames' / job_id
    destination.mkdir(parents=True, exist_ok=True)
    frames = []
    for index, seconds in enumerate(timestamps):
        output = destination / f'frame-{index}.png'
        temporary = output.with_suffix('.tmp.png')
        try:
            subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-ss', str(seconds), '-i', str(path),
                '-frames:v', '1', '-vf', 'scale=min(1280\\,iw):-2', '-threads', '1', '-y', str(temporary)],
                check=True, capture_output=True, timeout=60)
            temporary.replace(output)
            record = media_library.register_derived_media(root, owner, output.relative_to(generated_root(root, owner)).as_posix(),
                source_asset_id=asset['asset_id'], source_sha256=asset['sha256'], derivation_id=job_id,
                kind='image', metadata={'timestamp_seconds': seconds, 'occurrence_id': f'{job_id}-{index}', 'description': f'Video sample at {seconds:g} seconds'})
            frames.append({'timestamp_seconds': seconds, 'asset': record})
        finally:
            temporary.unlink(missing_ok=True)
    return {'frames': frames}
