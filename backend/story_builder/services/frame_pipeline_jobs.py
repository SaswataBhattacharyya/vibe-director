"""Frozen shared Director/Editor tasks; GPU work retains existing admission guards."""
from pathlib import Path
from . import frame_pipeline, frame_interpolation, video_repertoire
from .audio_utilities import WorkerUnavailable


def submit(root, owner, plan, invocation, on_created):
    if Path(root).resolve() != video_repertoire._CONFIGURED_DATA_ROOT:
        raise ValueError('Frame job storage belongs to another data root.')
    job = video_repertoire.create_job('frame-pipeline', {'workspace_id': owner,
        'agent_invocation_id': invocation, 'operation': frame_pipeline.TOOLS[plan['tool_id']],
        'inputs': plan['assets'], 'settings': plan['settings']})
    on_created(job)
    try:
        return video_repertoire.start_job('frame-pipeline', job['job_id'])
    except Exception as exc:
        raise WorkerUnavailable(str(exc)) from exc


def run(root, job_id, request):
    owner, settings, operation = request['workspace_id'], request['settings'], request['operation']
    tool = next((t for t, op in frame_pipeline.TOOLS.items() if op == operation), None)
    if tool is None:
        raise ValueError('Unknown frame operation.')
    frame_interpolation.check_cancel(job_id)
    # Generation has its own idempotent replay check after a lost response.
    if operation != 'next':
        if frame_pipeline.prepare(root, owner, tool, settings) != request['inputs']:
            raise ValueError('Frozen frame inputs changed.')
    else:
        for source in request['inputs']:
            frame_pipeline.image(root, owner, source['asset_id'], source['sha256'])
    if operation == 'next':
        result = frame_pipeline.next_key(root, owner, settings)
        result['message'] = 'Candidate queued in the image worker. Review it before continuing the take.'
    elif operation == 'interpolate':
        result = frame_interpolation.interpolate(root, owner, job_id, request['inputs'],
            {k: settings[k] for k in ('model','multiplier','fps','hold')})
    else:
        result = frame_interpolation.export(root, owner, job_id, settings['sequence_job_id'])
    return {**result, 'sources': request['inputs']}
