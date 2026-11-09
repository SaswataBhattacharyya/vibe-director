"""Approved image/video requests use the same validated routes as manual controls.

A durable receipt is allocated before submission. Missing acknowledgements require
reconciliation; polling never repeats a generation request.
"""
import io
import json
from pathlib import Path
from urllib.parse import urlsplit, quote

from . import video_repertoire as jobs
from .production_ledger import LedgerConflict, stable_hash

KIND = 'agent-generation'
TOOLS = {'image.generate', 'video.generate'}
IMAGE_FIELDS = {'workflow_id', 'prompt', 'seed', 'width', 'height', 'steps', 'cfg'}


def context():
    """Local versioned defaults, without probing models or authorizing submission."""
    from . import isolated_video_contract as t2v, isolated_r2v_contract as r2v, isolated_fl2va_contract as fflf
    from .production_image_workflows import SPECS
    common = {'workflow_version': 2, 'duration_seconds': 5, 'aspect_ratio': '16:9',
              'resolution_preset': .98, 'steps': 4, 'seed': 1}
    return {'image_defaults': {key: value['defaults'] for key, value in SPECS.items()
                              if key in settings_schema('image.generate')['properties']['workflow_id']['enum']},
        'video_templates': [
            {**common, 'workflow_id': 'minimax_h3_t2v_local_v1', 'workflow_sha256': t2v.EXPECTED_GRAPH_SHA256, 'references': []},
            {**common, 'workflow_id': r2v.WORKFLOW_ID, 'workflow_sha256': r2v.EXPECTED_GRAPH_SHA256,
             'ref_image_size': 'match', 'images': [], 'videos': [], 'audios': []},
            {'workflow_id': fflf.WORKFLOW_ID, 'workflow_version': fflf.WORKFLOW_VERSION,
             'workflow_sha256': fflf.EXPECTED_GRAPH_SHA256, 'duration_seconds': 5,
             'aspect_ratio': '16:9', 'resolution_preset': .98, 'first_frame': {}, 'last_frame': {}}],
        'instructions': 'Templates require a user-directed prompt. Use owned attachment IDs/hashes and numbered reference labels for R2V. For FFLF, explicitly choose first_frame and last_frame image IDs/hashes; show their order for approval. Confirm creative choices; defaults are not approval. Native validation remains authoritative.'}


def catalogue():
    return [{'id': tool, 'description': 'Generate a standalone image candidate.' if tool == 'image.generate' else 'Generate one standalone video candidate from an explicit model request.',
        'effect': 'submit', 'status': 'available', 'execution_enabled': True,
        'reason': 'Exact task approval and native model readiness required. Generated candidates are not automatically accepted. Active image/video cancellation is unavailable through this adapter.',
        'accepted_media': ['image'] if tool.startswith('image') else ['image', 'video', 'audio'],
        'scope': 'frozen_native_request', 'runtime': 'existing_generation_queue', 'approval': 'exact_plan',
        'result_kind': 'native_generation_candidate', 'input_schema': {'type': 'object', 'additionalProperties': False,
            'required': ['asset_ids', 'settings'], 'properties': {'asset_ids': {'type': 'array', 'maxItems': 10, 'items': {'type': 'string'}},
                'settings': settings_schema(tool)}}} for tool in sorted(TOOLS)]


def settings_schema(tool):
    if tool == 'image.generate':
        props = {'workflow_id': {'enum': ['z_image_turbo', 'qwen_image_2512', 'qwen_image_edit_2511', 'flux_kontext_dev']},
            'prompt': {'type': 'string'}, **{k: {'type': 'integer'} for k in ('seed', 'width', 'height', 'steps')}, 'cfg': {'type': 'number'}}
        return {'type': 'object', 'additionalProperties': False, 'required': sorted(IMAGE_FIELDS), 'properties': props}
    return {'type': 'object', 'additionalProperties': False, 'required': ['request'],
            'properties': {'request': {'type': 'object', 'description': 'Complete native VideoRequest, including workflow version/hash, explicit settings and owned reference IDs/hashes. Validated by the existing video validator.'}}}


def bridge(app):
    def call(method, path, body=None):
        raw, response = json.dumps(body or {}).encode(), []
        url = urlsplit(path)
        env = {'PATH_INFO': url.path, 'QUERY_STRING': url.query, 'REQUEST_METHOD': method,
            'CONTENT_TYPE': 'application/json', 'CONTENT_LENGTH': str(len(raw)), 'wsgi.input': io.BytesIO(raw)}
        stream = app(env, lambda status, headers: response.append(status))
        try:
            value = json.loads(b''.join(stream))
        finally:
            if hasattr(stream, 'close'):
                stream.close()
        if not response or not response[0].startswith('2'):
            error = value.get('error', {})
            raise ValueError(error.get('message', 'Native tool rejected this request.') if isinstance(error, dict) else str(error))
        return value
    return call


def prepare(call, owner, tool, settings, assets):
    if call is None:
        raise ValueError('Native generation bridge is unavailable.')
    if not isinstance(settings, dict):
        raise ValueError('Supply typed generation settings.')
    if tool == 'image.generate':
        if set(settings) != IMAGE_FIELDS:
            raise ValueError('Image generation requires workflow_id, prompt, seed, width, height, steps and cfg.')
        if settings['workflow_id'] not in settings_schema(tool)['properties']['workflow_id']['enum']:
            raise ValueError('Choose a supported standalone image workflow.')
        refs = [{'asset_id': a['asset_id'], 'sha256': a['sha256']} for a in assets]
        body = {**settings, 'workspace_id': owner, 'control_mode': 'assisted_manual', 'initial_candidate_count': 1,
                'asset_role': 'image_candidate', 'output_prefix': 'director/image', 'source_references': refs}
        compiled = call('POST', '/api/images/validations', body)
        return {**body, 'validation_sha256': stable_hash(compiled)}
    if set(settings) != {'request'} or not isinstance(settings['request'], dict):
        raise ValueError('Supply a complete native video request.')
    normalized = call('POST', '/api/video/validations', settings)['normalized_request']
    from .isolated_fl2va_contract import WORKFLOW_ID as FFLF_ID
    if normalized['workflow_id'] not in {'minimax_h3_t2v_local_v1', 'minimax_h3_r2v_dynamic_v1', FFLF_ID}:
        raise ValueError('Choose a supported T2V, R2V or first/last-frame video workflow.')
    refs = ([normalized['first_frame'], normalized['last_frame']] if normalized['workflow_id'] == FFLF_ID
            else [r for key in ('images', 'videos', 'audios') for r in normalized.get(key, [])])
    if normalized['workflow_id'] == FFLF_ID and any(Path(a['filename']).suffix.lower() not in {'.png', '.jpg', '.jpeg', '.webp'} for a in assets):
        raise ValueError('First/last-frame endpoints must be images.')
    if {(r['asset_id'], r['sha256']) for r in refs} != {(a['asset_id'], a['sha256']) for a in assets}:
        raise ValueError('Attach exactly the owned references named in this video request.')
    return {'request': normalized}


def submit(call, owner, plan, invocation, created):
    if plan['tool_id'] == 'image.generate':
        body = {k: v for k, v in plan['settings'].items() if k != 'validation_sha256'}
        if stable_hash(call('POST', '/api/images/validations', body)) != plan['settings']['validation_sha256']:
            raise LedgerConflict('Image workflow changed since approval. Propose a new task.')
    job = jobs.create_job(KIND, {'workspace_id': owner, 'agent_invocation_id': invocation, 'agent_plan': plan})
    created(job)
    job.update(status='running', message='Submitting the approved native request.')
    jobs._atomic_json(jobs.job_path(KIND, job['job_id']), job)
    try:
        settings = plan['settings']
        if plan['tool_id'] == 'image.generate':
            body = {k: v for k, v in settings.items() if k != 'validation_sha256'}
            receipt = call('POST', '/api/images/jobs', {**body, 'idempotency_key': invocation})
            job['receipt'] = {'batch_id': receipt['batch_id']}
        else:
            receipt = call('POST', '/api/video/jobs', {**settings, 'workspace_id': owner,
                'clip_id': 'director-' + invocation, 'idempotency_key': invocation})
            job['receipt'] = {'job_id': receipt['job_id']}
    except Exception:
        job.update(status='recovery_required', message='Native submission acknowledgement missing. Reconcile this invocation before creating another task.')
        jobs._atomic_json(jobs.job_path(KIND, job['job_id']), job)
        raise
    jobs._atomic_json(jobs.job_path(KIND, job['job_id']), job)
    return job


def refresh(call, job):
    if not job.get('receipt'):
        job.update(status='recovery_required', message='Submission receipt missing; reconcile the native invocation before retrying.')
        jobs._atomic_json(jobs.job_path(KIND, job['job_id']), job)
        return job
    if job['status'] in {'completed', 'failed', 'cancelled'}:
        return job
    request, receipt = job['request'], job['receipt']
    if request['agent_plan']['tool_id'] == 'image.generate':
        value = call('GET', '/api/images/batches/' + quote(receipt['batch_id'], safe='') + '?workspace_id=' + quote(request['workspace_id'], safe=''))
        rows = value['jobs']
        states = {r['status'] for r in rows}
        terminal = {'completed', 'succeeded', 'accepted', 'ready', 'failed', 'cancelled', 'recovery_required'}
        state = ('recovery_required' if 'recovery_required' in states else 'failed' if 'failed' in states
            else 'cancelled' if 'cancelled' in states else 'completed') if rows and states <= terminal else 'running'
    else:
        value = call('GET', '/api/video/jobs/' + quote(receipt['job_id'], safe=''))
        if value.get('workspace_id') != request['workspace_id']:
            raise LedgerConflict('Video receipt belongs to another project.')
        state = value['status']
        if state in {'stale', 'interrupted'}:
            state = 'recovery_required'
        elif state not in {'completed', 'failed', 'cancelled', 'recovery_required'}:
            state = 'running'
    job.update(status=state, result=value)
    jobs._atomic_json(jobs.job_path(KIND, job['job_id']), job)
    return job


def validate(row, job):
    request = job.get('request', {})
    if (request.get('workspace_id') != row['project_id'] or request.get('agent_plan') != row['plan']
            or request.get('agent_invocation_id') != row['invocation']['invocation_id']
            or row['invocation']['job_id'] and row['invocation']['job_id'] != job['job_id']):
        raise LedgerConflict('Generation receipt does not match the frozen invocation.')
