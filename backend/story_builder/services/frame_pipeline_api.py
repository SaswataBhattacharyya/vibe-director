"""Project-scoped review API shared by Director and Editor."""
import re
import json
from urllib.parse import parse_qs
from . import agent_graph, frame_pipeline as frames, frame_interpolation, video_repertoire, projects
from .storage_paths import generated_root


def handle(root, environ, start_response, read_json, respond, *, tasks):
    endpoint_match = re.fullmatch(r'/api/frame-pipeline/([\w-]+)/takes/([\w-]+)/endpoints', environ['PATH_INFO'])
    if endpoint_match and environ.get('REQUEST_METHOD','GET') == 'GET':
        owner, take_id = endpoint_match.groups()
        revision = int(parse_qs(environ.get('QUERY_STRING','')).get('revision',['0'])[0])
        return respond(start_response,'200 OK',frames.endpoints(root, owner, take_id, revision))
    job_match = re.fullmatch(r'/api/frame-pipeline/([\w-]+)/jobs/([\w-]+)/(reconcile|lossless)', environ['PATH_INFO'])
    if job_match:
        owner, job_id, action = job_match.groups()
        agent_graph.resolve_workspace(root, owner)
        job = video_repertoire.read_job('frame-pipeline', job_id)
        if job['request'].get('workspace_id') != owner:
            raise ValueError('Frame job belongs to another project.')
        folder = generated_root(root, owner) / 'frame-pipeline' / job_id
        if action == 'reconcile' and environ.get('REQUEST_METHOD') == 'POST':
            if environ.get('CONTENT_TYPE','').split(';')[0] != 'application/json' or read_json(environ) != {}:
                raise ValueError('Reconciliation needs an empty JSON object.')
            # Requeue this exact durable job. Its saved prompt journal forbids POST resubmission.
            with projects.locked(root):
                job = video_repertoire.read_job('frame-pipeline', job_id)
                if job['status'] not in {'recovery_required','interrupted'} or job['request']['operation'] != 'interpolate' or not (folder/'interpolation.json').is_file():
                    raise ValueError('Only an uncertain interpolation with a saved prompt can be reconciled.')
                job['status'] = 'interrupted'
                video_repertoire._atomic_json(video_repertoire.job_path('frame-pipeline',job_id), job)
                result = video_repertoire.start_job('frame-pipeline',job_id)
            return respond(start_response,'200 OK',result)
        if action == 'lossless' and environ.get('REQUEST_METHOD','GET') == 'GET':
            if job['status'] != 'completed' or job['request'].get('operation') != 'export':
                raise ValueError('Export is not completed.')
            target = folder/'lossless.mkv'
            record = json.loads((folder/'export.json').read_text())
            if target.is_symlink() or projects.digest(target) != record['lossless_sha256']:
                raise ValueError('Lossless export is missing or changed.')
            start_response('200 OK',[('Content-Type','video/x-matroska'),('Content-Length',str(target.stat().st_size)),
                ('Content-Disposition','attachment; filename="lossless.mkv"')])
            def chunks():
                with target.open('rb') as stream:
                    while block := stream.read(1024*1024):
                        yield block
            return chunks()
        raise ValueError('Unsupported frame job action.')
    match = re.fullmatch(r'/api/frame-pipeline/([\w-]+)(?:/(takes|propose)(?:/([\w-]+))?)?', environ['PATH_INFO'])
    if not match:
        return respond(start_response, '404 Not Found', {'error':{'message':'Unknown frame resource.'}})
    owner, operation, take_id = match.groups()
    agent_graph.resolve_workspace(root, owner)
    method = environ.get('REQUEST_METHOD', 'GET')
    if method == 'GET' and not operation:
        takes = [frames.get(root, owner, row['take_id']) for row in frames.list_takes(root, owner)]
        result = {'workspace_id':owner, 'takes':takes, 'interpolation':frame_interpolation.capability()}
    elif method == 'POST':
        if environ.get('CONTENT_TYPE','').split(';')[0] != 'application/json':
            raise ValueError('Use application/json.')
        body = read_json(environ)
        if operation == 'takes' and not take_id and set(body) in ({'asset_id'},{'asset_id','normalize'}):
            result = frames.create(root, owner, body['asset_id'], normalize=body.get('normalize',False))
        elif operation == 'takes' and take_id:
            result = frames.change(root, owner, take_id, body)
        elif operation == 'propose' and not take_id and set(body) == {'tool_id','settings'}:
            sources = frames.prepare(root, owner, body['tool_id'], body['settings'])
            result = tasks.propose(owner, {**body, 'asset_ids':[s['asset_id'] for s in sources]})
        else:
            raise ValueError('Unsupported frame action.')
    else:
        raise ValueError('Unsupported frame method.')
    return respond(start_response, '200 OK', result)
