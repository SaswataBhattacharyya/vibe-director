"""Durable CPU last-frame adapter; reuse the manual continuity implementation."""
from pathlib import Path

from . import media_library, projects, video_continuity, video_repertoire
from .storage_paths import media_root
from .audio_utilities import UtilityUnavailable, WorkerUnavailable

KIND = 'continuity-frame'


def submit(root, owner, assets, invocation, on_created):
    import shutil
    if not shutil.which('ffmpeg'):
        raise UtilityUnavailable('FFmpeg is required for continuity extraction.')
    if Path(root).resolve() != video_repertoire._CONFIGURED_DATA_ROOT:
        raise ValueError('Continuity job storage is configured for a different data root.')
    job = video_repertoire.create_job(KIND, {'workspace_id': owner,
        'agent_invocation_id': invocation, 'operation': 'last_frame', 'settings': {}, 'inputs': assets})
    on_created(job)
    try:
        return video_repertoire.start_job(KIND, job['job_id'])
    except Exception as exc:
        raise WorkerUnavailable(str(exc)) from exc


def run(root, request):
    owner = request['workspace_id']
    if request.get('operation') != 'last_frame' or request.get('settings') != {} or len(request['inputs']) != 1:
        raise ValueError('Invalid frozen continuity request.')
    source = request['inputs'][0]
    path, media_type, _ = media_library.asset_path(root, owner, source['asset_id'])
    if not media_type.startswith('video/') or projects.digest(path) != source['sha256']:
        raise ValueError('Approved continuity video changed or is unavailable.')
    frame = video_continuity.last_frame(root, owner,
        {'shared_asset_id': source['asset_id'], 'sha256': source['sha256']})
    # Return the actual owned catalogue record, never an invented content URL.
    _, index = media_library._manifest(media_root(root, owner))
    asset = media_library._owned_record(root, owner, index, frame['asset_id'])
    if asset is None:
        raise ValueError('Continuity output is not registered.')
    return {'workspace_id': owner, 'assets': [media_library.public_asset_record(asset, owner)]}
