"""Owned, approved CPU comparison jobs; original media stays untouched."""
from pathlib import Path
from . import media_library, projects, video_overlap, video_repertoire
from .audio_utilities import WorkerUnavailable

KIND = 'video-overlap'


def submit(root, owner, assets, settings, invocation, on_created):
    if Path(root).resolve() != video_repertoire._CONFIGURED_DATA_ROOT:
        raise ValueError('Overlap job storage is configured for another data root.')
    job = video_repertoire.create_job(KIND, {'workspace_id': owner, 'agent_invocation_id': invocation,
        'operation': 'compare_overlap', 'inputs': assets, 'settings': settings})
    on_created(job)
    try:
        return video_repertoire.start_job(KIND, job['job_id'])
    except Exception as exc:
        raise WorkerUnavailable(str(exc)) from exc


def run(root, request):
    if request.get('operation') != 'compare_overlap' or len(request.get('inputs', [])) != 2:
        raise ValueError('Overlap comparison requires two ordered videos.')
    settings = video_overlap.settings(request['settings'])
    owner, paths = request['workspace_id'], []
    for source in request['inputs']:
        path, mime, _ = media_library.asset_path(root, owner, source['asset_id'])
        if not mime.startswith('video/') or projects.digest(path) != source['sha256']:
            raise ValueError('Approved comparison source changed or is unavailable.')
        paths.append(path)
    comparison = video_overlap.compare(*paths, settings)
    for source, path in zip(request['inputs'], paths):
        if projects.digest(path) != source['sha256']:
            raise ValueError('Comparison source changed during analysis; result discarded.')
    return {'workspace_id': owner, 'comparison': comparison, 'sources': request['inputs']}
