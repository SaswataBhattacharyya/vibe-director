"""Discover media in authorized source folders without moving the user's files."""
from pathlib import Path
import hashlib
import mimetypes
import os
import uuid
from functools import lru_cache
from datetime import datetime, timezone


@lru_cache(maxsize=1024)
def _file_digest(path, signature):
    # Reuse hashes only while inode, size and nanosecond timestamps match.
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def _signature(path):
    stat = path.stat()
    return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)


def project_locations(root, workspace):
    from .storage_paths import project_root
    from .projects import records, folder_path
    canonical = project_root(root, workspace)
    locations = [(canonical, {"store": "project", "workspace_id": workspace})]
    saved = records(root).get(workspace)
    if saved:
        try:
            folder = folder_path(saved)
            if folder != canonical.resolve():
                locations.append((folder, {"store": "project", "workspace_id": workspace, "saved": True}))
        except (ValueError, OSError):
            pass  # A disconnected project folder must not break other sources.
    return locations


def discover(root, workspace, *, shared=False, kinds=None):
    return _discover_locked(root, workspace, shared=shared, kinds=kinds)


# Use the same manifest lock as uploads, annotations, archiving and deletion.
from .media_library import _serialized_write


@_serialized_write
def _discover_locked(root, workspace, *, shared=False, kinds=None):
    from . import media_library as library
    from .storage_paths import shared_downloads_root, repertoire_root
    locations = ([(library.media_root(root, workspace), {"store": "tool"})]
                 if workspace == "tool-library" else project_locations(root, workspace))
    if shared:
        locations += [(shared_downloads_root(root), {"store": "youtube"}),
                      (repertoire_root(root), {"store": "repertoire"})]
    index_path, index = library._manifest(library.media_root(root, workspace))
    known = {}
    records = {row['asset_id']: row for row in library._shared_records(root)}
    records.update({row['asset_id']: row for row in index['assets']})
    for record in records.values():
        try:
            path, _, _ = library.asset_path(root, record.get('workspace_id', workspace), record['asset_id'])
            known.setdefault(path.resolve(), []).append(record)
        except (ValueError, OSError):
            pass
    errors, added = [], 0
    for base, location in locations:
        if not base.is_dir() or any(p.is_symlink() for p in (base, *base.parents)):
            continue
        for directory, children, files in os.walk(base, followlinks=False):
            # Checkpoint copies and job intermediates are not additional source assets.
            children[:] = sorted(name for name in children if not name.startswith('.')
                and name not in {'project-data', 'checkpoint-media', 'intermediates'}
                and not (Path(directory) / name).is_symlink())
            for name in sorted(files):
                path = Path(directory) / name
                kind = library.SUFFIX_KIND.get(path.suffix.lower())
                if not kind or (kinds and kind not in kinds) or name.startswith('.') or path.is_symlink():
                    continue
                previous = known.get(path.resolve(), [])
                if any(row.get('archived_at') for row in previous):
                    continue  # Never resurrect archived paths by rediscovery.
                try:
                    before = _signature(path)
                    digest = _file_digest(path, before)
                    if any(row['sha256'] == digest for row in previous):
                        continue
                    media = library._probe(path, kind)
                    after = path.stat()
                    if before != _signature(path):
                        continue  # Still being written; discover it on the next browse.
                    relative = path.relative_to(base).as_posix()
                    record = {'asset_id': 'pa-' + uuid.uuid4().hex[:16], 'workspace_id': workspace,
                        'kind': kind, 'roles': ['project_' + kind], 'filename': name,
                        'media_type': mimetypes.guess_type(name)[0] or 'application/octet-stream',
                        'sha256': digest, 'size_bytes': after.st_size, 'media': media,
                        'source': 'project_upload', 'relative_path': relative,
                        'storage_location': {**location, 'path': relative},
                        'created_at': datetime.fromtimestamp(after.st_mtime, timezone.utc).isoformat(),
                        'description': '', 'tags': [], 'provenance_notes': 'Discovered in source folder; original file retained.',
                        'metadata': {'folder_discovery': True,
                            **({'replaces_asset_ids': [row['asset_id'] for row in previous]} if previous else {})}}
                    index['assets'].append(record)
                    known.setdefault(path.resolve(), []).append(record)
                    added += 1
                except (ValueError, OSError) as exc:
                    errors.append({'filename': name, 'message': str(exc)})
    if added:
        library._save(index_path, index)
    return {'added': added, 'errors': errors}


def available(root, record):
    from .media_library import asset_path
    try:
        path, _, _ = asset_path(root, record['workspace_id'], record['asset_id'])
        before = _signature(path)
        return _file_digest(path, before) == record['sha256'] and before == _signature(path)
    except (ValueError, OSError):
        return False
