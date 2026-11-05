"""Workspace media catalogue adapted from Story Builder's production asset contract."""
from __future__ import annotations
from story_builder.services.storage_paths import generated_root, project_identity

from story_builder.services.storage_paths import media_root as _media_root
import copy
import hashlib
import fcntl
import functools
import json
import math
import mimetypes
import os
import re
import subprocess
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MAX_UPLOAD_BYTES = 512 * 1024 * 1024
SUFFIX_KIND = {".png":"image", ".jpg":"image", ".jpeg":"image", ".webp":"image",
               ".mp4":"video", ".mov":"video", ".mkv":"video", ".webm":"video",
               ".wav":"audio", ".mp3":"audio", ".m4a":"audio", ".ogg":"audio",
               ".flac":"audio", ".aac":"audio"}
ROLE_KINDS = {"project_image":"image", "project_video":"video", "project_audio":"audio",
              "style_reference":"any", "image_candidate":"image", "character_master":"image", "world_master":"image",
              "character_view":"image", "world_view":"image", "first_frame":"image", "last_frame":"image", "voice_master":"audio",
              "action_reference_video":"video"}
_ID = re.compile(r"^pa-[a-f0-9]{16}$")
_SEO_ID = re.compile(r"^seo-[a-f0-9]{16}$")
MAX_STYLE_REFERENCE_FRAMES = 12


def _serialized_write(function):
    """Serialize manifest read/modify/write across server workers."""
    @functools.wraps(function)
    def wrapped(root: Path, workspace_id: str, *args, **kwargs):
        project = media_root(root, workspace_id)
        lock_path = project / ".assets.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with lock_path.open("a+b") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                return function(root, workspace_id, *args, **kwargs)
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
    return wrapped


class ProductionAssetError(ValueError):
    pass


def media_root(root: Path, workspace_id: str) -> Path:
    if not isinstance(workspace_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", workspace_id):
        raise ProductionAssetError("Invalid workspace ID.")
    try:
        return _media_root(root, workspace_id)
    except ValueError as exc:
        raise ProductionAssetError(str(exc)) from exc


def _root(base: Path, workspace_id: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", workspace_id):
        raise ProductionAssetError("Invalid workspace ID.")
    base = Path(base).resolve()
    path = (base / workspace_id).resolve()
    if not path.is_relative_to(base):
        raise ProductionAssetError("Workspace path is invalid.")
    return path


def _manifest(root: Path) -> tuple[Path, dict[str, Any]]:
    path = root / "assets.json"
    if not path.exists():
        return path, {"schema_version": 1, "assets": []}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProductionAssetError("Workspace asset index is unreadable.") from exc
    if value.get("schema_version") != 1 or not isinstance(value.get("assets"), list):
        raise ProductionAssetError("Workspace asset index has an unsupported format.")
    return path, value


def _shared_records(root: Path) -> list[dict]:
    rows = []
    for folder in ("youtube_downloads", "video_repertoire", "library/tool-media"):
        path = Path(root) / folder / "catalog.json"
        if path.is_file():
            if path.is_symlink():
                raise ProductionAssetError("Shared catalogue cannot be a symlink.")
            rows.extend(json.loads(path.read_text())["assets"])
    return rows


def _owned_record(root: Path, workspace_id: str, index: dict, asset_id: str) -> dict | None:
    """Materialize an owned shared occurrence as a workspace metadata overlay."""
    record = next((row for row in index["assets"] if row.get("asset_id") == asset_id), None)
    if record is None:
        shared = next((row for row in _shared_records(root)
                       if row.get("workspace_id") == workspace_id and row.get("asset_id") == asset_id), None)
        if shared is not None:
            record = copy.deepcopy(shared)
            index["assets"].append(record)
    return record


def _publish_shared(root: Path, record: dict) -> None:
    """Catalogue owns the occurrence; workspace manifests keep legacy memberships."""
    store = (record.get("storage_location") or {}).get("store")
    folder = {"youtube": "youtube_downloads", "repertoire": "video_repertoire", "output": "library/tool-media"}.get(store)
    if not folder:
        return
    directory = Path(root) / folder
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / ".catalog.lock").open("a+b") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        path = directory / "catalog.json"
        data = json.loads(path.read_text()) if path.exists() else {"version": 1, "assets": []}
        key = (record["workspace_id"], record["asset_id"])
        data["assets"] = [row for row in data["assets"] if (row["workspace_id"], row["asset_id"]) != key]
        data["assets"].append(copy.deepcopy(record))
        _save(path, data)


def shared_run_referenced(root: Path, run_id: str) -> bool:
    # Archived memberships still resolve for frozen takes and recovery.
    rows = _shared_records(root)
    for manifest in (Path(root) / "projects").glob("*/media/assets.json"):
        rows.extend(_manifest(manifest.parent)[1]["assets"])
    return any((row.get("storage_location") or {}).get("store") == "repertoire"
        and Path(row["storage_location"]["path"]).parts[:2] == ("runs", run_id) for row in rows)


def _seo_manifest(root: Path) -> tuple[Path, dict[str, Any]]:
    path = root / "seo_styles.json"
    if not path.exists():
        return path, {"schema_version": 1, "styles": []}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProductionAssetError("Workspace SEO style index is unreadable.") from exc
    if value.get("schema_version") != 1 or not isinstance(value.get("styles"), list):
        raise ProductionAssetError("Workspace SEO style index has an unsupported format.")
    return path, value


def _save(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".assets-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except Exception:
        Path(temporary).unlink(missing_ok=True)
        raise


def _public(record: dict[str, Any], workspace_id: str, *, deduplicated: bool | None = None,
            include_semantic_vector: bool = False):
    safe = {key: value for key, value in record.items() if key not in {"relative_path", "source", "storage_location"}}
    if not include_semantic_vector and isinstance(safe.get("semantic_annotation_index"), dict):
        safe["semantic_annotation_index"] = {
            key: value for key, value in safe["semantic_annotation_index"].items() if key != "vector"
        }
    if not include_semantic_vector and isinstance(safe.get("semantic_content_index"), dict):
        safe["semantic_content_index"] = {
            key: value for key, value in safe["semantic_content_index"].items() if key != "vector"
        }
    safe["origin"] = "imported" if record.get("source") in {"project_upload", "youtube_download"} else "generated"
    safe["content_url"] = f"/api/media/{workspace_id}/assets/{record['asset_id']}/content"
    if deduplicated is not None:
        safe["deduplicated"] = deduplicated
    return safe


def public_asset_record(record: dict[str, Any], workspace_id: str) -> dict[str, Any]:
    return _public(record, workspace_id)


def _kind(filename: str, content: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    kind = SUFFIX_KIND.get(suffix)
    signatures = {".png": content.startswith(b"\x89PNG\r\n\x1a\n"),
                  ".jpg": content.startswith(b"\xff\xd8\xff"), ".jpeg": content.startswith(b"\xff\xd8\xff"),
                  ".webp": content.startswith(b"RIFF") and content[8:12] == b"WEBP",
                  ".wav": content.startswith(b"RIFF") and content[8:12] == b"WAVE",
                  ".flac": content.startswith(b"fLaC"), ".ogg": content.startswith(b"OggS"),
                  ".mp3": content.startswith(b"ID3") or (len(content) > 1 and content[0] == 255 and content[1] & 224 == 224),
                  ".mp4": len(content) >= 12 and content[4:8] == b"ftyp",
                  ".mov": len(content) >= 12 and content[4:8] == b"ftyp",
                  ".m4a": len(content) >= 12 and content[4:8] == b"ftyp",
                  ".aac": content.startswith(b"ID3") or (len(content) > 1 and content[0] == 255 and content[1] & 246 == 240), ".mkv": content.startswith(b"\x1aE\xdf\xa3"),
                  ".webm": content.startswith(b"\x1aE\xdf\xa3")}
    if kind is None or not signatures.get(suffix, False):
        raise ProductionAssetError("Unsupported media format or file signature mismatch.")
    return kind


def _probe(path: Path, kind: str) -> dict[str, Any]:
    try:
        result = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
            "format=duration:stream=codec_type,width,height", "-of", "json", str(path)],
            capture_output=True, text=True, timeout=30, check=False)
        if result.returncode:
            raise ProductionAssetError("Media could not be validated by ffprobe.")
        value = json.loads(result.stdout)
        stream_rows = [row for row in value.get("streams", []) if isinstance(row, dict)]
        streams = {row.get("codec_type") for row in stream_rows}
        expected = "video" if kind == "image" else kind
        if expected not in streams:
            raise ProductionAssetError("The file does not contain the declared media stream.")
        if kind == "image":
            video = next(row for row in stream_rows if row.get("codec_type") == "video")
            width, height = int(video.get("width") or 0), int(video.get("height") or 0)
            if width < 1 or height < 1 or width * height > 80_000_000:
                raise ProductionAssetError("Image dimensions are invalid or unsupported.")
            return {"width": width, "height": height}
        result = {"duration_seconds": float(value.get("format", {}).get("duration") or 0), "streams": sorted(streams)}
        if kind == "video":
            video = next((row for row in stream_rows if row.get("codec_type") == "video"), None)
            if not video:
                raise ProductionAssetError("Video dimensions are invalid or unsupported.")
            width, height = int(video.get("width") or 0), int(video.get("height") or 0)
            if width < 1 or height < 1 or width * height > 200_000_000:
                raise ProductionAssetError("Video dimensions are invalid or unsupported.")
            result.update(width=width, height=height)
        return result
    except ProductionAssetError:
        raise
    except Exception as exc:
        raise ProductionAssetError("Media validation is unavailable.") from exc


@_serialized_write
def register_upload(root: Path, workspace_id: str, *, filename: str, content: bytes,
                    role: str, provenance_notes: str = "",
                    metadata: dict[str, Any] | None = None, deduplicate: bool = True, storage: str = "workspace") -> dict[str, Any]:
    project = media_root(root, workspace_id)
    if role not in ROLE_KINDS or not isinstance(content, bytes) or not content or len(content) > MAX_UPLOAD_BYTES:
        raise ProductionAssetError("Invalid role, empty file, or upload exceeds 512 MiB.")
    if storage not in {"workspace", "recording"}:
        raise ProductionAssetError("Unknown upload destination.")
    name = Path(filename or "upload").name
    kind = _kind(name, content)
    if storage == "recording" and kind != "audio":
        raise ProductionAssetError("Only audio can be saved as a recording.")
    if ROLE_KINDS[role] not in {"any", kind}:
        raise ProductionAssetError("Media type does not match the selected asset role.")
    if metadata is not None:
        try:
            encoded_metadata = json.dumps(metadata, ensure_ascii=False)
        except (TypeError, ValueError) as exc:
            raise ProductionAssetError("Asset provenance metadata is invalid.") from exc
        if type(metadata) is not dict or len(encoded_metadata) > 16_000:
            raise ProductionAssetError("Asset provenance metadata is invalid or too large.")
    digest = hashlib.sha256(content).hexdigest()
    index_path, index = _manifest(project)
    found = next((row for row in index["assets"] if row["sha256"] == digest and (storage != "recording" or (row.get("storage_location") or {}).get("store") == "audio")), None) if deduplicate else None
    if found:
        changed = False
        if role not in found["roles"]:
            found["roles"].append(role)
            changed = True
        if metadata is not None:
            stored_metadata = found.get("metadata")
            if type(stored_metadata) is not dict:
                stored_metadata = found["metadata"] = {}
                changed = True
            for key, value in metadata.items():
                if key in {"story_builder_donor_sources", "continuity_sources"}:
                    current = stored_metadata.get(key)
                    sources = [source for source in current if type(source) is dict] if isinstance(current, list) else []
                    incoming = value if isinstance(value, list) else [value]
                    for source in incoming:
                        if type(source) is dict and source not in sources:
                            sources.append(source)
                            changed = True
                    if stored_metadata.get(key) != sources:
                        changed = True
                    stored_metadata[key] = sources
                else:
                    if stored_metadata.get(key) != value:
                        changed = True
                    stored_metadata[key] = value
            if len(json.dumps(stored_metadata, ensure_ascii=False)) > 64_000:
                raise ProductionAssetError("Combined asset provenance metadata is too large.")
        if changed:
            _save(index_path, index)
        return _public(found, workspace_id, deduplicated=True)
    asset_id = f"pa-{uuid.uuid4().hex[:16]}"
    media_dir = project / "imports" / {"image": "images", "audio": "audio", "video": "videos"}[kind]
    if storage == "recording":
        from .storage_paths import checked
        media_dir = checked(root, "audio_studio", "recordings")
    media_dir.mkdir(parents=True, exist_ok=True)
    target = media_dir / f"{asset_id}{Path(name).suffix.lower()}"
    fd, temp = tempfile.mkstemp(prefix=f".{asset_id}-", dir=media_dir)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, target)
    except Exception:
        Path(temp).unlink(missing_ok=True)
        raise
    try:
        probed = _probe(target, kind)
    except Exception:
        target.unlink(missing_ok=True)
        raise
    record = {"asset_id": asset_id, "workspace_id": workspace_id, "kind": kind,
              "roles": [role], "filename": name, "media_type": mimetypes.guess_type(name)[0] or "application/octet-stream",
              "sha256": digest, "size_bytes": len(content), "source": "project_upload",
              "relative_path": target.relative_to(Path(root) / "audio_studio" if storage == "recording" else project).as_posix(), "media": probed,
              **({"storage_location": {"store": "audio", "path": target.relative_to(Path(root) / "audio_studio").as_posix()}} if storage == "recording" else {}),
              "provenance_notes": provenance_notes[:2000], "metadata": metadata or {},
              "created_at": datetime.now(timezone.utc).isoformat()}
    index["assets"].append(record)
    _save(index_path, index)
    return _public(record, workspace_id, deduplicated=False)


@_serialized_write
def delete_temporary_image_asset(root: Path, workspace_id: str, asset_id: str, *, token: str) -> dict[str, Any]:
    """Remove only an explicitly tagged transient image reference/result."""
    if not _ID.fullmatch(asset_id) or not re.fullmatch(r"[a-f0-9]{32}", token):
        raise ProductionAssetError("Invalid temporary image asset identity.")
    project = media_root(root, workspace_id)
    index_path, index = _manifest(project)
    row = next((record for record in index["assets"] if record.get("asset_id") == asset_id), None)
    metadata = (row or {}).get("metadata") or {}
    transient = metadata.get("vibe_t2i_transient")
    if not row or row.get("kind") != "image" or not isinstance(transient, dict) or transient.get("token") != token:
        raise ProductionAssetError("This image is not a matching temporary Text to Image asset.")
    path, _, _ = asset_path(Path(root), workspace_id, asset_id)
    path.unlink(missing_ok=True)
    index["assets"] = [record for record in index["assets"] if record.get("asset_id") != asset_id]
    _save(index_path, index)
    return {"deleted": True, "asset_id": asset_id}


def _pinned_style_reference_records(root: Path, selection: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Read style-reference records from the setup context pinned by a Story."""
    if selection is None:
        return []
    if (not isinstance(selection, dict)
            or type(selection.get("snapshot_id")) is not str
            or not re.fullmatch(r"[0-9a-f]{32}", selection["snapshot_id"])
            or type(selection.get("isolated_context_id")) is not str
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", selection["isolated_context_id"])
            or type(selection.get("style_version_id")) is not str
            or not selection["style_version_id"]):
        raise ProductionAssetError("The story has no valid pinned production style selection.")
    source_workspace = selection["isolated_context_id"]
    source_project = media_root(root, source_workspace)
    _, index = _manifest(source_project)
    version_id = selection["style_version_id"]
    direction = selection.get("directing_style")
    direction_id = direction.get("style_id") if isinstance(direction, dict) else None
    def belongs(record):
        if record.get("source") not in {"project_upload", "project_output", "youtube_download"} or "style_reference" not in record.get("roles", []):
            return False
        metadata = record.get("metadata")
        if not isinstance(metadata, dict):
            return False
        direction_ids = metadata.get("directing_style_ids", [])
        if direction_id and direction_id in direction_ids:
            return True
        # Preserve old references made before directing-style IDs were stored.
        # Once explicitly associated with a directing style, do not leak it
        # into other styles through its legacy production-type link.
        return not direction_ids and version_id in metadata.get("style_version_ids", [])
    return [record for record in index["assets"] if belongs(record)]


def list_assets(root: Path, workspace_id: str, *, kind: str | None = None, limit: int = 50,
                offset: int = 0, style_selection: dict[str, Any] | None = None,
                include_semantic_vectors: bool = False, include_archived: bool = False):
    project = media_root(root, workspace_id)
    if kind not in {None, "image", "video", "audio"} or not 1 <= limit <= 100 or offset < 0:
        raise ProductionAssetError("Invalid media filter or pagination.")
    from .media_discovery import discover, available
    discover(root, workspace_id, kinds={kind} if kind else None)
    _, index = _manifest(project)
    # Shared stores own migrated occurrences; workspace manifests only hold
    # memberships. Include both, with local archive/annotation overrides winning.
    owned = {row["asset_id"]: row for row in _shared_records(root)
             if row.get("workspace_id") == workspace_id}
    owned.update({row["asset_id"]: row for row in index["assets"]})
    all_local_rows = list(owned.values())
    local_rows = [row for row in all_local_rows
                  if (kind is None or row["kind"] == kind)
                  and (include_archived or (not row.get("archived_at") and available(root, row)))]
    local_by_id = {row["asset_id"]: row for row in all_local_rows}
    recommendations = []
    for record in _pinned_style_reference_records(root, style_selection):
        # Archiving a source style reference removes it from future pickers,
        # while pinned consumers may still resolve its unchanged file directly.
        if record.get("archived_at") and not include_archived:
            continue
        if kind is not None and record["kind"] != kind:
            continue
        if record["asset_id"] in local_by_id:
            local = local_by_id[record["asset_id"]]
            if (local.get("workspace_id") != record.get("workspace_id")
                    or local.get("sha256") != record.get("sha256")):
                raise ProductionAssetError("A local asset conflicts with a pinned style reference ID.")
            continue
        recommendation = _public(record, workspace_id)
        recommendation.update(recommended=True, recommendation_source="production_style",
            source_workspace_id=record["workspace_id"], source_asset_id=record["asset_id"])
        recommendations.append(recommendation)
    recommendations.sort(key=lambda row: (row.get("created_at", ""), row["asset_id"]), reverse=True)
    local_rows.sort(key=lambda row: (row.get("created_at", ""), row["asset_id"]), reverse=True)
    rows = recommendations + [_public(row, workspace_id, include_semantic_vector=include_semantic_vectors) for row in local_rows]
    return {"assets": rows[offset:offset+limit], "total": len(rows), "limit": limit, "offset": offset}


@_serialized_write
def set_asset_archived(root: Path, workspace_id: str, asset_id: str, *, archived: bool) -> dict[str, Any]:
    """Hide a workspace asset from normal pickers without deleting its source file."""
    if not _ID.fullmatch(asset_id) or type(archived) is not bool:
        raise ProductionAssetError("Asset ID or archive action is invalid.")
    project = media_root(root, workspace_id)
    index_path, index = _manifest(project)
    record = _owned_record(root, workspace_id, index, asset_id)
    if record is None:
        raise ProductionAssetError("Asset was not found in this workspace.")
    if archived:
        record["archived_at"] = datetime.now(timezone.utc).isoformat()
    else:
        record.pop("archived_at", None)
    _save(index_path, index)
    return _public(record, workspace_id)


def pinned_style_asset_path(root: Path, selection: dict[str, Any] | None,
                            asset_id: str) -> tuple[Path, str, str, dict[str, Any]]:
    """Resolve one style asset only when it belongs to the Story's pinned setup."""
    if not _ID.fullmatch(asset_id):
        raise FileNotFoundError(asset_id)
    record = next((item for item in _pinned_style_reference_records(root, selection)
                   if item.get("asset_id") == asset_id), None)
    if record is None:
        raise FileNotFoundError(asset_id)
    source_workspace = selection["isolated_context_id"]
    path, media_type, filename = asset_path(root, source_workspace, asset_id)
    if path.stat().st_size != record.get("size_bytes"):
        raise FileNotFoundError(asset_id)
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != record.get("sha256"):
        raise FileNotFoundError(asset_id)
    return path, media_type, filename, record


@_serialized_write
def assign_role(root: Path, workspace_id: str, asset_id: str, role: str) -> dict[str, Any]:
    """Mark an existing workspace asset as selected for a compatible use."""
    project = media_root(root, workspace_id)
    if role not in ROLE_KINDS or not _ID.fullmatch(asset_id):
        raise ProductionAssetError("Invalid asset ID or role.")
    index_path, index = _manifest(project)
    record = _owned_record(root, workspace_id, index, asset_id)
    if record is None:
        raise ProductionAssetError("Asset was not found in this workspace.")
    if ROLE_KINDS[role] not in {"any", record["kind"]}:
        raise ProductionAssetError("Asset type does not match the selected role.")
    if role not in record["roles"]:
        record["roles"].append(role)
    _save(index_path, index)
    return _public(record, workspace_id)


@_serialized_write
def update_annotations(root: Path, workspace_id: str, asset_id: str, *,
                       description: str, tags: list[str], audio_category: str | None = None) -> dict[str, Any]:
    """Save user-authored searchable SEO metadata without changing source media."""
    project = media_root(root, workspace_id)
    if not _ID.fullmatch(asset_id) or type(description) is not str or len(description) > 2000:
        raise ProductionAssetError("Asset ID or description is invalid.")
    if type(tags) is not list or len(tags) > 40 or any(type(tag) is not str or not tag.strip() or len(tag.strip()) > 80 for tag in tags):
        raise ProductionAssetError("Use up to 40 nonempty search tags, each at most 80 characters.")
    normalized_tags = list(dict.fromkeys(tag.strip() for tag in tags))
    if audio_category is not None and (type(audio_category) is not str or audio_category not in {"voice", "sfx", "music", "dialogue"}):
        raise ProductionAssetError("Audio category must be voice, sfx, music or dialogue.")
    index_path, index = _manifest(project)
    record = _owned_record(root, workspace_id, index, asset_id)
    if record is None:
        raise ProductionAssetError("Asset was not found in this workspace.")
    if record["kind"] == "audio":
        if audio_category is None:
            record.pop("audio_category", None)
        else:
            record["audio_category"] = audio_category
    elif audio_category is not None:
        raise ProductionAssetError("Audio categories apply only to audio assets.")
    record["description"] = description.strip()
    record["tags"] = normalized_tags
    record.pop("semantic_annotation_index", None)
    _save(index_path, index)
    return _public(record, workspace_id)


def semantic_annotation_text(record: dict[str, Any]) -> str:
    return " ".join(str(value).strip() for value in [
        record.get("filename", ""), record.get("description", ""),
        " ".join(record.get("tags", []) if isinstance(record.get("tags"), list) else []),
        record.get("audio_category", ""), " ".join(record.get("roles", []) if isinstance(record.get("roles"), list) else []),
    ] if str(value).strip())


@_serialized_write
def save_semantic_annotation_index(root: Path, workspace_id: str, asset_id: str, *,
                                   source_sha256: str, annotation_sha256: str,
                                   model: str, vector: list[float]) -> dict[str, Any]:
    """Store a real text embedding tied to the current asset and its searchable annotations."""
    if not _ID.fullmatch(asset_id) or not re.fullmatch(r"[a-f0-9]{64}", source_sha256) or not re.fullmatch(r"[a-f0-9]{64}", annotation_sha256):
        raise ProductionAssetError("Semantic index provenance is invalid.")
    if model != "facebook/pe-av-base" or type(vector) is not list or not 1 <= len(vector) <= 4096:
        raise ProductionAssetError("Semantic index model or vector is invalid.")
    if any(type(value) not in {int, float} or not math.isfinite(value) for value in vector):
        raise ProductionAssetError("Semantic index contains invalid vector values.")
    project = media_root(root, workspace_id)
    index_path, index = _manifest(project)
    record = _owned_record(root, workspace_id, index, asset_id)
    if record is None or record.get("sha256") != source_sha256:
        raise ProductionAssetError("Asset changed or is no longer available in this workspace.")
    text = semantic_annotation_text(record)
    current_annotation_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if not text or current_annotation_sha256 != annotation_sha256:
        raise ProductionAssetError("Search details changed; save them and index again.")
    record["semantic_annotation_index"] = {
        "source": "saved_filename_description_tags_roles",
        "source_sha256": source_sha256,
        "annotation_sha256": annotation_sha256,
        "model": model,
        "dimension": len(vector),
        "vector": [float(value) for value in vector],
    }
    _save(index_path, index)
    return _public(record, workspace_id)


@_serialized_write
def save_semantic_content_index(root: Path, workspace_id: str, asset_id: str, *,
                                source_sha256: str, modality: str, model: str,
                                vector: list[float]) -> dict[str, Any]:
    """Save a PE-AV content vector only against the unchanged local asset."""
    if (not _ID.fullmatch(asset_id) or not re.fullmatch(r"[a-f0-9]{64}", source_sha256)
            or modality not in {"audio", "video", "image"} or model != "facebook/pe-av-base"
            or type(vector) is not list or not 1 <= len(vector) <= 4096
            or any(type(value) not in {int, float} or not math.isfinite(value) for value in vector)):
        raise ProductionAssetError("Semantic content index provenance or vector is invalid.")
    project = media_root(root, workspace_id)
    index_path, index = _manifest(project)
    record = _owned_record(root, workspace_id, index, asset_id)
    if record is None or record.get("sha256") != source_sha256 or record.get("kind") != modality:
        raise ProductionAssetError("Asset changed or is no longer available in this workspace.")
    record["semantic_content_index"] = {
        "source": "image_visual_content" if modality == "image" else f"{modality}_content",
        "source_sha256": source_sha256,
        "model": model, "dimension": len(vector), "vector": [float(value) for value in vector],
    }
    _save(index_path, index)
    return _public(record, workspace_id)


@_serialized_write
def save_image_analysis(root: Path, workspace_id: str, asset_id: str, *,
                        job_id: str, source_sha256: str, mode: str,
                        analysis: dict[str, Any], description: str,
                        tags: list[str]) -> dict[str, Any]:
    """Persist a detailer result and its searchable summary on its source image."""
    if not _ID.fullmatch(asset_id) or type(job_id) is not str or not re.fullmatch(r"[a-f0-9-]{16,64}", job_id):
        raise ProductionAssetError("Image asset or analysis job ID is invalid.")
    if type(source_sha256) is not str or not re.fullmatch(r"[a-f0-9]{64}", source_sha256):
        raise ProductionAssetError("Image analysis source hash is invalid.")
    if mode not in {"quick", "balanced", "deep"} or type(analysis) is not dict:
        raise ProductionAssetError("Image analysis mode or result is invalid.")
    if len(json.dumps(analysis, ensure_ascii=False).encode("utf-8")) > 1024 * 1024:
        raise ProductionAssetError("Structured image analysis must be at most 1 MiB.")
    if type(description) is not str or len(description) > 2000:
        raise ProductionAssetError("Image description must be at most 2,000 characters.")
    if type(tags) is not list or len(tags) > 40 or any(type(tag) is not str or not tag.strip() or len(tag.strip()) > 80 for tag in tags):
        raise ProductionAssetError("Use up to 40 nonempty search tags, each at most 80 characters.")
    project = media_root(root, workspace_id)
    index_path, index = _manifest(project)
    record = _owned_record(root, workspace_id, index, asset_id)
    if record is None or record.get("kind") != "image":
        raise ProductionAssetError("Image asset was not found in this workspace.")
    if record.get("sha256") != source_sha256:
        raise ProductionAssetError("Image analysis belongs to a different source image revision.")
    metadata = record.setdefault("metadata", {})
    history = metadata.setdefault("image_analyses", [])
    if type(history) is not list:
        raise ProductionAssetError("Image analysis history is unreadable.")
    if any(item.get("job_id") == job_id for item in history if isinstance(item, dict)):
        return _public(record, workspace_id)
    history.append({"job_id": job_id, "source_sha256": source_sha256, "mode": mode,
                    "saved_at": datetime.now(timezone.utc).isoformat(), "analysis": analysis})
    record["description"] = description.strip()
    record["tags"] = list(dict.fromkeys(tag.strip() for tag in tags))
    record.pop("semantic_annotation_index", None)
    _save(index_path, index)
    return _public(record, workspace_id)


def list_seo_styles(root: Path, workspace_id: str) -> list[dict[str, Any]]:
    project = media_root(root, workspace_id)
    _, value = _seo_manifest(project)
    return value["styles"]


def _validated_seo_style(payload: dict[str, Any]) -> dict[str, Any]:
    if type(payload.get("name")) is not str or not payload["name"].strip() or len(payload["name"].strip()) > 80:
        raise ProductionAssetError("SEO style name must contain 1–80 characters.")
    terms = payload.get("weighted_terms")
    if type(terms) is not dict or not 1 <= len(terms) <= 40:
        raise ProductionAssetError("Add 1–40 weighted search terms.")
    weighted_terms: list[dict[str, Any]] = []
    seen: set[str] = set()
    for term, weight in terms.items():
        if type(term) is not str or not term.strip() or len(term.strip()) > 80:
            raise ProductionAssetError("Each weighted term must contain 1–80 characters.")
        normalized = term.strip().casefold()
        if normalized in seen:
            raise ProductionAssetError("Weighted search terms must be unique.")
        if type(weight) not in {int, float} or not 0.1 <= weight <= 10:
            raise ProductionAssetError("Each search weight must be from 0.1 to 10.")
        seen.add(normalized)
        weighted_terms.append({"term": term.strip(), "weight": float(weight)})
    avoid = payload.get("avoid_terms", [])
    if type(avoid) is not list or len(avoid) > 40 or any(type(term) is not str or not term.strip() or len(term.strip()) > 80 for term in avoid):
        raise ProductionAssetError("Use up to 40 nonempty excluded terms, each at most 80 characters.")
    return {"name": payload["name"].strip(), "weighted_terms": weighted_terms,
            "avoid_terms": list(dict.fromkeys(term.strip() for term in avoid))}


@_serialized_write
def create_seo_style(root: Path, workspace_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    project = media_root(root, workspace_id)
    value = _validated_seo_style(payload)
    index_path, index = _seo_manifest(project)
    record = {"style_id": f"seo-{uuid.uuid4().hex[:16]}", **value,
              "created_at": datetime.now(timezone.utc).isoformat()}
    index["styles"].append(record)
    _save(index_path, index)
    return record


@_serialized_write
def update_seo_style(root: Path, workspace_id: str, style_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    project = media_root(root, workspace_id)
    if not _SEO_ID.fullmatch(style_id):
        raise ProductionAssetError("SEO style ID is invalid.")
    value = _validated_seo_style(payload)
    index_path, index = _seo_manifest(project)
    record = next((row for row in index["styles"] if row.get("style_id") == style_id), None)
    if record is None:
        raise ProductionAssetError("SEO style was not found in this workspace.")
    record.update(value)
    _save(index_path, index)
    return record


@_serialized_write
def delete_seo_style(root: Path, workspace_id: str, style_id: str) -> bool:
    project = media_root(root, workspace_id)
    if not _SEO_ID.fullmatch(style_id):
        raise ProductionAssetError("SEO style ID is invalid.")
    index_path, index = _seo_manifest(project)
    styles = index["styles"]
    remaining = [row for row in styles if row.get("style_id") != style_id]
    if len(remaining) == len(styles):
        return False
    index["styles"] = remaining
    _save(index_path, index)
    return True


@_serialized_write
def link_style_reference(root: Path, workspace_id: str, asset_id: str, style_version_id: str | None = None,
                         *, directing_style_id: str | None = None) -> dict[str, Any]:
    """Associate a style reference with a directing style, or a legacy type version."""
    project = media_root(root, workspace_id)
    valid_legacy = type(style_version_id) is str and 1 <= len(style_version_id) <= 160
    valid_direction = type(directing_style_id) is str and bool(re.fullmatch(r"[a-z][a-z0-9_]{1,63}", directing_style_id))
    if not _ID.fullmatch(asset_id) or valid_legacy == valid_direction:
        raise ProductionAssetError("Asset ID and exactly one valid style ID are required.")
    index_path, index = _manifest(project)
    record = next((row for row in index["assets"] if row["asset_id"] == asset_id), None)
    if record is None:
        raise ProductionAssetError("Asset was not found in this style setup.")
    if "style_reference" not in record.get("roles", []):
        raise ProductionAssetError("Only assets uploaded as style references can be linked to a production style.")
    metadata = record.setdefault("metadata", {})
    if type(metadata) is not dict:
        metadata = record["metadata"] = {}
    key, selected_id = ("directing_style_ids", directing_style_id) if valid_direction else ("style_version_ids", style_version_id)
    ids = metadata.setdefault(key, [])
    if type(ids) is not list or any(type(value) is not str for value in ids):
        raise ProductionAssetError("Style reference metadata is unreadable.")
    if selected_id not in ids:
        ids.append(selected_id)
    _save(index_path, index)
    return _public(record, workspace_id)


@_serialized_write
def _add_style_frame_source(root: Path, workspace_id: str, asset_id: str, source: dict[str, Any]) -> dict[str, Any]:
    project = media_root(root, workspace_id)
    index_path, index = _manifest(project)
    record = next((row for row in index["assets"] if row["asset_id"] == asset_id), None)
    if record is None:
        raise ProductionAssetError("Extracted style frame was not found in this workspace.")
    metadata = record.setdefault("metadata", {})
    sources = metadata.setdefault("style_frame_sources", [])
    if not isinstance(sources, list):
        raise ProductionAssetError("Style frame source metadata is unreadable.")
    if source not in sources:
        sources.append(source)
    field = "directing_style_ids" if "directing_style_id" in source else "style_version_ids"
    source_field = "directing_style_id" if field == "directing_style_ids" else "style_version_id"
    versions = metadata.setdefault(field, [])
    if not isinstance(versions, list):
        raise ProductionAssetError("Style frame version metadata is unreadable.")
    if source[source_field] not in versions:
        versions.append(source[source_field])
    _save(index_path, index)
    return _public(record, workspace_id)


def validate_style_reference_frame_request(root: Path, workspace_id: str, video_asset_id: str,
        style_version_id: str | None, timestamps_seconds: Any, *, directing_style_id: str | None = None,
        ffmpeg: str = "ffmpeg") -> tuple[Path, str, dict[str, Any], str, str, list[float]]:
    """Validate a selected-frame request without starting media processing."""
    project = media_root(root, workspace_id)
    legacy = type(style_version_id) is str and bool(style_version_id)
    direction_valid = type(directing_style_id) is str and bool(re.fullmatch(r"[a-z][a-z0-9_]{1,63}", directing_style_id))
    if not _ID.fullmatch(video_asset_id) or legacy == direction_valid:
        raise ProductionAssetError("Video asset and exactly one valid style ID are required.")
    style_key = "directing_style_id" if direction_valid else "style_version_id"
    selected_style_id = directing_style_id if direction_valid else style_version_id
    if (not isinstance(timestamps_seconds, list) or len(timestamps_seconds) > MAX_STYLE_REFERENCE_FRAMES
            or any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
                or value < 0 for value in timestamps_seconds)):
        raise ProductionAssetError(f"Supply up to {MAX_STYLE_REFERENCE_FRAMES} finite, non-negative timestamps.")
    path, _, filename = asset_path(root, workspace_id, video_asset_id)
    _, index = _manifest(project)
    parent = next((row for row in index["assets"] if row["asset_id"] == video_asset_id), None)
    if not parent or parent.get("kind") != "video" or "style_reference" not in parent.get("roles", []):
        raise ProductionAssetError("Choose a video uploaded as a style reference.")
    if "duration_seconds" not in parent.get("media", {}):
        raise ProductionAssetError("Video duration is unavailable; selected frames cannot be checked.")
    duration = float(parent["media"]["duration_seconds"])
    if not math.isfinite(duration) or duration <= 0 or any(value >= duration for value in timestamps_seconds):
        raise ProductionAssetError("Every selected timestamp must be inside the video duration.")
    if any(abs(left - right) < 0.001 for index, left in enumerate(timestamps_seconds) for right in timestamps_seconds[index+1:]):
        raise ProductionAssetError("Selected frame timestamps must be distinct to the nearest millisecond.")
    return path, filename, parent, style_key, str(selected_style_id), [float(value) for value in timestamps_seconds]


def extract_style_reference_frames(root: Path, workspace_id: str, video_asset_id: str,
        style_version_id: str | None, timestamps_seconds: Any, *, directing_style_id: str | None = None,
        ffmpeg: str = "ffmpeg", progress: Any = None) -> list[dict[str, Any]]:
    """Export only user-selected timestamps from a registered style video."""
    path, filename, parent, style_key, selected_style_id, timestamps = validate_style_reference_frame_request(
        root, workspace_id, video_asset_id, style_version_id, timestamps_seconds,
        directing_style_id=directing_style_id, ffmpeg=ffmpeg)
    if not timestamps:
        return []

    exported: list[tuple[float, bytes]] = []
    deadline = time.monotonic() + 30
    with tempfile.TemporaryDirectory(prefix="vibe-style-frames-") as temporary:
        for ordinal, timestamp in enumerate(timestamps, 1):
            frame = Path(temporary) / f"frame-{ordinal:02d}.jpg"
            try:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise subprocess.TimeoutExpired(ffmpeg, 30)
                subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{float(timestamp):.6f}",
                    "-i", str(path), "-frames:v", "1", "-vf", "scale='min(1920,iw)':-2", "-q:v", "2", str(frame)],
                    check=True, capture_output=True, timeout=min(10, remaining))
                content = frame.read_bytes()
            except subprocess.TimeoutExpired as exc:
                raise ProductionAssetError("Style-frame extraction exceeded its 30-second limit; reduce the frame count and retry.") from exc
            except (OSError, subprocess.SubprocessError) as exc:
                raise ProductionAssetError("A selected video frame could not be extracted.") from exc
            if not content:
                raise ProductionAssetError("A selected video frame was empty.")
            exported.append((float(timestamp), content))
            if progress:
                progress(ordinal, len(timestamps))

    frames = []
    stem = Path(filename).stem[:80] or "style-video"
    for ordinal, (timestamp, content) in enumerate(exported, 1):
        frame = register_upload(root, workspace_id, filename=f"{stem}-style-frame-{ordinal:02d}.jpg",
            content=content, role="style_reference", provenance_notes=f"Style frame from {video_asset_id} at {timestamp:.3f}s")
        frames.append(_add_style_frame_source(root, workspace_id, frame["asset_id"], {
            "parent_video_asset_id": video_asset_id, "parent_video_sha256": parent["sha256"],
            "source_width": parent["media"].get("width"), "source_height": parent["media"].get("height"),
            "timestamp_seconds": timestamp, style_key: selected_style_id,
            "extraction": {"method": "ffmpeg-single-frame-jpeg-v1", "max_width": 1920, "quality": 2}}))
    return frames


def asset_path(root: Path, workspace_id: str, asset_id: str) -> tuple[Path, str, str]:
    try:
        return _original_asset_path(root, workspace_id, asset_id)
    except (FileNotFoundError, ValueError):
        base = media_root(root, workspace_id)
        index = base / 'checkpoint-assets.json'
        if not index.is_file() or index.is_symlink():
            raise
        entry = json.loads(index.read_text()).get(asset_id)
        if not entry:
            raise
        relative = Path(entry.get('path', ''))
        if relative.is_absolute() or '..' in relative.parts or relative.parts[:1] != ('checkpoint-media',):
            raise ValueError('Invalid checkpoint media location.')
        path = base / relative
        if any(p.is_symlink() for p in (path, *path.parents)) or not path.is_file():
            raise FileNotFoundError('Checkpoint media is unavailable.')
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError('Checkpoint media has changed.')
        _, manifest = _manifest(base)
        record = next((r for r in manifest['assets'] if r['asset_id'] == asset_id), None)
        if not record or record['sha256'] != entry['sha256']:
            raise ValueError('Checkpoint media identity mismatch.')
        return path, record['media_type'], record['filename']


def _original_asset_path(root: Path, workspace_id: str, asset_id: str) -> tuple[Path, str, str]:
    project = media_root(root, workspace_id)
    if not _ID.fullmatch(asset_id):
        raise FileNotFoundError(asset_id)
    _, index = _manifest(project)
    record = next((row for row in index["assets"] if row["asset_id"] == asset_id), None)
    if record is None:
        record = next((row for row in _shared_records(root) if row["workspace_id"] == workspace_id and row["asset_id"] == asset_id), None)
    if not record or record.get("source") not in {"project_upload", "project_output", "youtube_download"}:
        raise FileNotFoundError(asset_id)
    if record.get("storage_location"):
        from .storage_paths import shared_file
        path = shared_file(root, record["storage_location"])
        return path, record["media_type"], record["filename"]
    relative = Path(record["relative_path"])
    if relative.is_absolute() or ".." in relative.parts:
        raise FileNotFoundError(asset_id)
    if record["source"] == "youtube_download":
        base = _youtube_download_base(root)
    elif record["source"] == "project_output":
        candidate_base = generated_root(Path(root).resolve(), workspace_id)
        if candidate_base.parent.is_symlink() or candidate_base.is_symlink():
            raise FileNotFoundError(asset_id)
        base = candidate_base.resolve()
    else:
        if relative.parts[:1] != ("imports",):
            raise FileNotFoundError(asset_id)
        candidate_base = project / "imports"
        if candidate_base.parent.is_symlink() or candidate_base.is_symlink():
            raise FileNotFoundError(asset_id)
        base = candidate_base.resolve()
        relative = Path(*relative.parts[1:])
    path = (base / relative).resolve()
    cursor = base
    for part in relative.parts:
        cursor /= part
        if cursor.is_symlink():
            raise FileNotFoundError(asset_id)
    if not path.is_relative_to(base) or not path.is_file():
        raise FileNotFoundError(asset_id)
    return path, record["media_type"], record["filename"]


@_serialized_write
def register_generated_image(root: Path, workspace_id: str, relative_path: str,
                             metadata: dict[str, Any]) -> dict[str, Any]:
    """Index an existing product-owned generated image; never move its bytes."""
    project = media_root(root, workspace_id)
    output_dir = (generated_root(Path(root).resolve(), workspace_id)).resolve()
    output = (output_dir / relative_path).resolve()
    if not output.is_relative_to(output_dir) or not output.is_file():
        raise ProductionAssetError("Generated image output is missing or outside this workspace.")
    probed = _probe(output, "image")
    digest_obj = hashlib.sha256()
    with output.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest_obj.update(chunk)
    digest = digest_obj.hexdigest()
    index_path, index = _manifest(project)
    record = {"asset_id": f"pa-{uuid.uuid4().hex[:16]}", "workspace_id": workspace_id,
        "kind": "image", "roles": ["image_candidate"], "filename": output.name,
        "media_type": mimetypes.guess_type(output.name)[0] or "image/png", "sha256": digest,
        "size_bytes": output.stat().st_size, "source": "project_output", "relative_path": relative_path,
        "media": probed, "metadata": metadata,
        "created_at": datetime.now(timezone.utc).isoformat()}
    index["assets"].append(record)
    _save(index_path, index)
    return _public(record, workspace_id, deduplicated=False)


def _youtube_download_base(root: Path) -> Path:
    from .storage_paths import shared_downloads_root
    return shared_downloads_root(root)


@_serialized_write
def register_downloaded_video(root: Path, workspace_id: str, path: Path,
                              metadata: dict[str, Any]) -> dict[str, Any]:
    """Link a canonical download into a workspace without copying its bytes."""
    base = _youtube_download_base(root)
    output = Path(path).resolve()
    if not output.is_relative_to(base) or not output.is_file():
        raise ProductionAssetError("Downloaded video is outside the shared download store.")
    relative = output.relative_to(base)
    cursor = base
    for part in relative.parts:
        cursor /= part
        if cursor.is_symlink():
            raise ProductionAssetError("Downloaded video cannot be a symlink.")
    digest_obj = hashlib.sha256()
    with output.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest_obj.update(chunk)
    digest = digest_obj.hexdigest()
    index_path, index = _manifest(media_root(root, workspace_id))
    found = next((row for row in index["assets"] if row.get("kind") == "video" and row.get("sha256") == digest), None)
    if found:
        found.update(source="youtube_download", relative_path=relative.as_posix(), filename=output.name)
        found.setdefault("metadata", {}).update(metadata)
        found["storage_location"] = {"store": "youtube", "path": relative.as_posix()}
        _save(index_path, index)
        _publish_shared(root, found)
        return _public(found, workspace_id, deduplicated=True)
    record = {"asset_id": f"pa-{uuid.uuid4().hex[:16]}", "workspace_id": workspace_id,
        "kind": "video", "roles": ["project_video"], "filename": output.name,
        "media_type": mimetypes.guess_type(output.name)[0] or "video/mp4", "sha256": digest,
        "size_bytes": output.stat().st_size, "source": "youtube_download",
        "relative_path": relative.as_posix(), "media": _probe(output, "video"),
        "metadata": metadata, "created_at": datetime.now(timezone.utc).isoformat()}
    record["storage_location"] = {"store": "youtube", "path": relative.as_posix()}
    index["assets"].append(record)
    _save(index_path, index)
    _publish_shared(root, record)
    return _public(record, workspace_id, deduplicated=False)


@_serialized_write
def register_generated_video(root: Path, workspace_id: str, relative_path: str,
                             metadata: dict[str, Any]) -> dict[str, Any]:
    """Index an existing owned video output; no bytes are copied or deleted."""
    project = media_root(root, workspace_id)
    output_dir = (generated_root(Path(root).resolve(), workspace_id)).resolve()
    output = (output_dir / relative_path).resolve()
    if not output.is_relative_to(output_dir) or not output.is_file():
        raise ProductionAssetError("Generated video output is missing.")
    # Keep generated outputs in the same media schema as uploads. The renderer's
    # FFprobe report is useful provenance, but it is not the library's normalized
    # shape and omits fields (notably duration_seconds) used by later pickers.
    probed = _probe(output, "video")
    digest_obj = hashlib.sha256()
    with output.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest_obj.update(chunk)
    digest = digest_obj.hexdigest()
    index_path, index = _manifest(project)
    if metadata.get("batch_filename"):
        for row in index["assets"]:
            if row.get("source") == "project_output" and row.get("relative_path") == relative_path and row.get("sha256") != digest:
                row["relative_path"] = f"overwritten/{row['asset_id']}.mp4"
                row["archived_at"] = datetime.now(timezone.utc).isoformat()
        _save(index_path, index)
    found = next((row for row in index["assets"] if row.get("sha256") == digest and row.get("source") == "project_output"
                  and (not metadata.get("batch_filename") or row.get("relative_path") == relative_path)), None)
    if found:
        if "project_video" not in found["roles"]:
            found["roles"].append("project_video")
            _save(index_path, index)
        return _public(found, workspace_id, deduplicated=True)
    record = {"asset_id": f"pa-{uuid.uuid4().hex[:16]}", "workspace_id": workspace_id,
        "kind": "video", "roles": ["project_video"], "filename": output.name,
        "media_type": mimetypes.guess_type(output.name)[0] or "video/mp4", "sha256": digest,
        "size_bytes": output.stat().st_size, "source": "project_output", "relative_path": relative_path,
        "media": probed, "metadata": metadata,
        "created_at": datetime.now(timezone.utc).isoformat()}
    index["assets"].append(record)
    _save(index_path, index)
    return _public(record, workspace_id, deduplicated=False)


@_serialized_write
def register_generated_audio(root: Path, workspace_id: str, relative_path: str,
                             metadata: dict[str, Any], *, storage_location: dict | None = None) -> dict[str, Any]:
    """Index an owned audio derivative in the shared workspace repertoire."""
    project = media_root(root, workspace_id)
    output_dir = (generated_root(Path(root).resolve(), workspace_id)).resolve()
    if storage_location is not None:
        from .storage_paths import shared_file
        output = shared_file(root, storage_location)
    else:
        output = (output_dir / relative_path).resolve()
    if (storage_location is None and not output.is_relative_to(output_dir)) or not output.is_file():
        raise ProductionAssetError("Generated audio output is missing or outside this workspace.")
    with output.open("rb") as stream:
        signature = stream.read(16)
    media_type = _kind(output.name, signature)
    if media_type != "audio":
        raise ProductionAssetError("Generated audio output is not a supported audio file.")
    probed = _probe(output, "audio")
    digest_obj = hashlib.sha256()
    with output.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest_obj.update(chunk)
    digest = digest_obj.hexdigest()
    index_path, index = _manifest(project)
    found = next((row for row in index["assets"] if row.get("sha256") == digest
        and row.get("source") == "project_output"), None)
    if found:
        if "project_audio" not in found["roles"]:
            found["roles"].append("project_audio")
            _save(index_path, index)
        return _public(found, workspace_id, deduplicated=True)
    record = {"asset_id": f"pa-{uuid.uuid4().hex[:16]}", "workspace_id": workspace_id,
        "kind": "audio", "roles": ["project_audio"], "filename": output.name,
        "media_type": mimetypes.guess_type(output.name)[0] or "application/octet-stream",
        "sha256": digest, "size_bytes": output.stat().st_size, "source": "project_output",
        "relative_path": relative_path, "media": probed, "metadata": metadata,
        **({"storage_location": storage_location} if storage_location else {}),
        "created_at": datetime.now(timezone.utc).isoformat()}
    index["assets"].append(record)
    _save(index_path, index)
    return _public(record, workspace_id, deduplicated=False)


@_serialized_write
def register_derived_media(root: Path, workspace_id: str, relative_path: str, *,
                           source_asset_id: str, source_sha256: str, derivation_id: str,
                           kind: str, metadata: dict[str, Any], storage_location: dict | None = None) -> dict[str, Any]:
    """Publish one analyzer-produced occurrence into the shared media library.

    Unlike generated-media helpers, this deliberately does not deduplicate by
    file hash: two identical frames at different source timestamps are distinct
    searchable occurrences and must retain their own lineage.
    """
    if (type(kind) is not str or kind not in {"image", "video", "audio"} or not _ID.fullmatch(source_asset_id)
            or type(source_sha256) is not str or not re.fullmatch(r"[a-f0-9]{64}", source_sha256)
            or type(derivation_id) is not str or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", derivation_id)
            or type(relative_path) is not str or not isinstance(metadata, dict)
            or {"derivation_id", "source_asset_id", "source_sha256"} & set(metadata)):
        raise ProductionAssetError("Derived media identity or metadata is invalid.")
    try:
        encoded_metadata = json.dumps(metadata, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ProductionAssetError("Derived media metadata must be valid JSON.") from exc
    if len(encoded_metadata.encode("utf-8")) > 256 * 1024:
        raise ProductionAssetError("Derived media metadata exceeds 256 KiB.")
    description = metadata.get("description", "")
    tags = metadata.get("tags", [])
    audio_category = metadata.get("audio_category")
    if type(description) is not str or len(description) > 2000:
        raise ProductionAssetError("Derived media description must be at most 2,000 characters.")
    if (type(tags) is not list or len(tags) > 40
            or any(type(tag) is not str or not tag.strip() or len(tag.strip()) > 80 for tag in tags)):
        raise ProductionAssetError("Derived media tags must contain up to 40 short, nonempty terms.")
    if (kind == "audio" and audio_category is not None
            and (type(audio_category) is not str or audio_category not in {"voice", "sfx", "music", "dialogue"})):
        raise ProductionAssetError("Derived audio category must be voice, sfx, music or dialogue.")
    if kind != "audio" and audio_category is not None:
        raise ProductionAssetError("Audio category applies only to derived audio assets.")

    project = media_root(root, workspace_id)
    index_path, index = _manifest(project)
    source = _owned_record(root, workspace_id, index, source_asset_id)
    if source is None or source.get("sha256") != source_sha256:
        raise ProductionAssetError("The source asset is missing or changed since analysis started.")

    output_base = generated_root(root, workspace_id).parent
    if output_base.is_symlink():
        raise ProductionAssetError("Derived media output root cannot be a symlink.")
    output_dir = generated_root(root, workspace_id)
    if storage_location is not None:
        from .storage_paths import shared_file, repertoire_root
        if storage_location.get("store") != "repertoire":
            raise ProductionAssetError("Derived outputs must use the repertoire store.")
        shared_file(root, storage_location)
        output_dir = repertoire_root(root)
        relative_path = storage_location["path"]
    relative = Path(relative_path)
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        raise ProductionAssetError("Derived media output path is invalid.")
    candidate = output_dir / relative
    output = candidate.resolve()
    cursor = output_dir
    symlinked = output_dir.is_symlink()
    for part in relative.parts:
        cursor /= part
        symlinked = symlinked or cursor.is_symlink()
    if not output.is_relative_to(output_dir.resolve()) or not output.is_file() or symlinked:
        raise ProductionAssetError("Derived media output is missing or outside this workspace.")
    with output.open("rb") as stream:
        signature = stream.read(32)
    if _kind(output.name, signature) != kind:
        raise ProductionAssetError("Derived media file type does not match its declared kind.")
    probed = _probe(output, kind)
    digest_obj = hashlib.sha256()
    with output.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest_obj.update(chunk)
    digest = digest_obj.hexdigest()
    occurrence_id = metadata.get("occurrence_id")
    if occurrence_id is not None:
        if type(occurrence_id) is not str or not re.fullmatch(r"[A-Za-z0-9_-]{1,160}", occurrence_id):
            raise ProductionAssetError("Derived media occurrence ID is invalid.")
        existing = next((row for row in index["assets"]
            if row.get("metadata", {}).get("derivation_id") == derivation_id
            and row.get("metadata", {}).get("occurrence_id") == occurrence_id), None)
        if existing is not None:
            if existing.get("sha256") != digest or existing.get("relative_path") != output.relative_to(output_dir.resolve()).as_posix():
                raise ProductionAssetError("This derived media occurrence was already published with different content.")
            return _public(existing, workspace_id, deduplicated=True)
    role = {"image": "project_image", "video": "project_video", "audio": "project_audio"}[kind]
    record = {"asset_id": f"pa-{uuid.uuid4().hex[:16]}", "workspace_id": workspace_id,
        "kind": kind, "roles": [role], "filename": output.name,
        "media_type": mimetypes.guess_type(output.name)[0] or "application/octet-stream",
        "sha256": digest, "size_bytes": output.stat().st_size,
        "source": "project_output", "relative_path": output.relative_to(output_dir.resolve()).as_posix(),
        **({"storage_location": storage_location} if storage_location else {}),
        "media": probed, "description": description.strip(),
        "tags": list(dict.fromkeys(tag.strip() for tag in tags)),
        **({"audio_category": audio_category} if audio_category is not None else {}),
        "metadata": {"derivation_id": derivation_id,
            "source_asset_id": source_asset_id, "source_sha256": source_sha256, **metadata},
        "created_at": datetime.now(timezone.utc).isoformat()}
    index["assets"].append(record)
    _save(index_path, index)
    _publish_shared(root, record)
    return _public(record, workspace_id, deduplicated=False)


@_serialized_write
def delete_analysis_assets(root: Path, workspace_id: str, job_id: str, run_ids: set[str]) -> int:
    """Remove only catalogued outputs whose analysis ownership is proven."""
    if not re.fullmatch(r"analysis-[A-Za-z0-9_-]+", job_id):
        raise ProductionAssetError("Invalid analysis ID.")
    project = media_root(root, workspace_id)
    index_path, index = _manifest(project)
    output_dir = generated_root(Path(root).resolve(), workspace_id)
    if output_dir.parent.is_symlink():
        raise ProductionAssetError("Unsafe shared asset root.")
    derivations = {f"{job_id}_{run_id}" for run_id in run_ids}
    removed, retained = [], []
    for row in index["assets"]:
        metadata = row.get("metadata") or {}
        owned = metadata.get("derivation_id") in derivations or (metadata.get("sam_audio") or {}).get("run_id") in run_ids
        if row.get("source") != "project_output" or not owned:
            retained.append(row)
            continue
        if row.get("storage_location"):
            retained.append(row)
            continue
        relative = Path(row.get("relative_path", ""))
        if relative.is_absolute() or not relative.parts or ".." in relative.parts:
            raise ProductionAssetError("Unsafe analysis output path; nothing was removed.")
        cursor = output_dir
        if cursor.is_symlink():
            raise ProductionAssetError("Unsafe analysis output directory.")
        for part in relative.parts:
            cursor /= part
            if cursor.is_symlink():
                raise ProductionAssetError("Unsafe analysis output symlink.")
        if not cursor.resolve().is_relative_to(output_dir.resolve()):
            raise ProductionAssetError("Analysis output escaped its workspace.")
        removed.append(cursor)
    for path in removed:
        path.unlink(missing_ok=True)
    index["assets"] = retained
    _save(index_path, index)
    return len(removed)


@_serialized_write
def delete_extracted_asset(root: Path, workspace_id: str, asset_id: str) -> dict[str, Any]:
    """Delete one analyzer output, never an uploaded/downloaded source."""
    if not _ID.fullmatch(asset_id):
        raise ProductionAssetError("Invalid asset ID.")
    project = media_root(root, workspace_id)
    index_path, index = _manifest(project)
    row = _owned_record(root, workspace_id, index, asset_id)
    metadata = (row or {}).get("metadata") or {}
    if (not row or row.get("source") != "project_output" or row.get("kind") not in {"video", "audio", "image"}
            or not (metadata.get("analyzer_run_id") or (metadata.get("sam_audio") or {}).get("run_id"))):
        raise ProductionAssetError("Only extracted video/audio/image assets can be deleted here.")
    path, _, _ = asset_path(Path(root), workspace_id, asset_id)
    private_path = None
    run_id = metadata.get("analyzer_run_id")
    if isinstance(run_id, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,128}", run_id):
        from .storage_paths import repertoire_root
        run_dir = repertoire_root(root) / "runs" / run_id
        manifest_path = run_dir / "manifest.json"
        if manifest_path.is_file() and not any(parent.is_symlink() for parent in [manifest_path, *manifest_path.parents]):
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if manifest.get("run_id") == run_id:
                from story_builder.services.video_repertoire_worker import _publication_rows
                output = next((item for item in _publication_rows(manifest, run_dir)
                    if item.get("occurrence_id") == metadata.get("occurrence_id") and item.get("kind") == row.get("kind")), None)
                if output:
                    candidate = run_dir / output["relative_path"]
                    if candidate.resolve().is_relative_to(run_dir.resolve()) and not any(parent.is_symlink() for parent in [candidate,*candidate.parents]):
                        private_path = candidate
    preview = deletion_preview(root, workspace_id, asset_id)
    result = delete_media_file.__wrapped__(root, workspace_id, asset_id, preview["sha256"])
    if private_path and private_path != path:
        private_path.unlink(missing_ok=True)
    return result


def catalogue_source(record: dict[str, Any]) -> str:
    metadata = record.get("metadata") or {}
    if record.get("source") == "youtube_download" or (record.get("storage_location") or {}).get("store") == "youtube":
        return "downloaded"
    if (record.get("storage_location") or {}).get("store") == "repertoire":
        return "extracted" if metadata.get("analyzer_run_id") or metadata.get("style_frame_sources") else "repertoire"
    if metadata.get("analyzer_run_id") or metadata.get("style_frame_sources"):
        return "extracted"
    if metadata.get("story_builder_donor_sources"):
        return "repertoire"
    return "imported" if record.get("source") == "project_upload" else "generated"


@_serialized_write
def name_media_workspace(root: Path, workspace_id: str, name: str) -> dict[str, str]:
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 120 or any(ord(c) < 32 for c in name):
        raise ProductionAssetError("Enter a workspace name between 1 and 120 characters.")
    path = media_root(root, workspace_id) / "workspace.json"
    _save(path, {"name": name.strip()})
    return {"workspace_id": workspace_id, "name": name.strip()}


def catalogue_workspace_names(root: Path) -> dict[str, str]:
    names = {}
    base = root / "projects"
    names["tool-library"] = "Shared media"
    for project in sorted(base.iterdir()) if base.exists() else []:
        if project.is_symlink() or not project.is_dir():
            continue
        try:
            path = media_root(root, project_identity(root, project.name)) / "workspace.json"
            if path.exists():
                saved = json.loads(path.read_text())
                name = saved.get("name") if isinstance(saved, dict) else None
                if isinstance(name, str) and name.strip():
                    names[project_identity(root, project.name)] = name.strip()
        except (OSError, ValueError):
            continue
    return names


def reconcile_download_catalogue(root: Path) -> dict[str, Any]:
    """Index only the canonical download store; retain original bytes and paths."""
    base = _youtube_download_base(root)
    workspace = "tool-library"
    known = {r.get("relative_path") for r in _shared_records(root) if r.get("source") == "youtube_download"}
    projects = root / "projects"
    for project in projects.iterdir() if projects.exists() else []:
        if project.is_symlink() or not project.is_dir():
            continue
        try:
            _, index = _manifest(media_root(root, project_identity(root, project.name)))
            known.update(r.get("relative_path") for r in index["assets"] if r.get("source") == "youtube_download")
        except ProductionAssetError:
            continue
    added, errors = 0, []
    for path in sorted(base.rglob("*")) if base.exists() else []:
        if any(part.is_symlink() for part in [path, *path.parents]) or not path.is_file() or SUFFIX_KIND.get(path.suffix.lower()) != "video":
            continue
        relative = path.relative_to(base).as_posix()
        if relative in known:  # Keep archives archived; refresh must not resurrect deleted items.
            continue
        try:
            register_downloaded_video(root, workspace, path, {"description": path.stem, "tags": ["youtube"]})
            added += 1
        except (OSError, ValueError) as exc:
            errors.append({"filename": path.name, "message": str(exc)})
    return {"added": added, "errors": errors}


def browse_catalogue(root: Path, workspace_id: str, *, kinds: str = "image,video,audio",
                     source: str = "all", owner: str = "", query: str = "",
                     offset: int = 0, limit: int = 24, order: str = "newest", folder: str = "") -> dict[str, Any]:
    """Discover supported files in source folders, retaining registered identities and roles."""
    if workspace_id:
        media_root(root, workspace_id)
    allowed = set(kinds.split(","))
    if not allowed or allowed - {"image", "video", "audio"}:
        raise ProductionAssetError("Choose supported media kinds.")
    if source not in {"all", "projects", "current", "downloaded", "extracted", "repertoire", "imported", "generated", "style", "ace_generated"}:
        raise ProductionAssetError("Unknown media source.")
    if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 100 or order not in {"newest", "oldest"} or len(query) > 500:
        raise ProductionAssetError("Invalid catalogue paging, ordering or search.")
    if folder and (folder.startswith("/") or ".." in folder.split("/") or len(folder) > 1000):
        raise ProductionAssetError("Invalid source folder.")
    if owner and source in {"all", "projects", "current"}:
        media_root(root, owner)
    from .media_discovery import discover, available
    # Category filters retain metadata semantics; broad folder scopes discover files.
    if source in {"all", "projects", "current", "downloaded", "repertoire"}:
        if source in {"all", "downloaded", "repertoire"} and not owner:
            discover(root, "tool-library", shared=True, kinds=allowed)
        if source in {"all", "projects", "current"}:
            selected = owner or (workspace_id if source == "current" else "")
            if selected:
                discover(root, selected, kinds=allowed)
            else:
                for directory in sorted((root / "projects").iterdir()) if (root / "projects").exists() else []:
                    if directory.is_dir() and not directory.is_symlink():
                        try:
                            discover(root, project_identity(root, directory.name), kinds=allowed)
                        except ProductionAssetError:
                            continue
    rows, owners, folders = [], [], set()
    base = root / "projects"
    records_by_owner = {}
    for record in _shared_records(root):
        records_by_owner.setdefault(record["workspace_id"], {})[record["asset_id"]] = record
    for record in _manifest(media_root(root, "tool-library"))[1]["assets"]:
        records_by_owner.setdefault("tool-library", {})[record["asset_id"]] = record
    for project in sorted(base.iterdir()) if base.exists() else []:
        if project.is_dir() and not project.is_symlink():
            for record in _manifest(media_root(root, project_identity(root, project.name)))[1]["assets"]:
                # Project archives/notes apply only in project scope, not to the shared original.
                bucket = records_by_owner.setdefault(project_identity(root, project.name), {})
                if record["asset_id"] not in bucket or source == "current" or owner:
                    bucket[record["asset_id"]] = record
    for project_name, records in sorted(records_by_owner.items()):
        project = base / project_name
        if project.is_symlink():
            continue
        try:
            project_media = media_root(root, project_identity(root, project.name))
            index = {"assets": list(records.values())}
        except ProductionAssetError:
            continue
        owners.append(project.name)
        if (source == "current" and project.name != workspace_id) or (owner and source in {"all", "projects", "current"} and project.name != owner):
            continue
        if source == "projects" and project.name == "tool-library":
            continue
        for record in index["assets"]:
            if source != "current" and not owner and record.get("storage_location") and (record.get("metadata") or {}).get("library_sources"):
                continue
            if record.get("archived_at") or record.get("kind") not in allowed or not available(root, record):
                continue
            category = catalogue_source(record)
            if source == "style" and "style_reference" not in record.get("roles", []):
                continue
            if source == "ace_generated" and (record.get("kind") != "audio" or (record.get("metadata") or {}).get("source") != "ace_step_standalone"):
                continue
            if source not in {"all", "projects", "current", "style", "ace_generated", category} and not (source == "repertoire" and category == "extracted"):
                continue
            text = " ".join([str(record.get("filename", "")), str(record.get("description", "")), *map(str, record.get("tags") or [])]).casefold()
            if query.strip().casefold() not in text:
                continue
            relative = Path(record.get("relative_path") or record.get("filename") or "")
            asset_folder = relative.parent.as_posix()
            if asset_folder == ".":
                asset_folder = ""
            prefix = folder + "/" if folder else ""
            if asset_folder.startswith(prefix) and asset_folder != folder:
                child = asset_folder[len(prefix):].split("/")[0]
                folders.add(prefix + child)
            if folder and asset_folder != folder and not asset_folder.startswith(prefix):
                continue
            row = _public(record, project.name)
            row["source_folder"] = asset_folder
            row["catalogue_source"] = category
            rows.append(row)
    rows.sort(key=lambda row: (row.get("created_at", ""), row["workspace_id"], row["asset_id"]), reverse=order == "newest")
    return {"assets": rows[offset:offset + limit], "total": len(rows), "offset": offset,
            "limit": limit, "workspaces": owners, "workspace_names": catalogue_workspace_names(root), "folders": sorted(folders)}


def reuse_catalogue_asset(root: Path, workspace_id: str, *, source_workspace_id: str, asset_id: str, role: str | None = None, mode: str = "reference") -> dict[str, Any]:
    """Link shared media by default; copying remains an explicit choice."""
    if mode not in {"reference", "copy"}:
        raise ProductionAssetError("Choose reference or copy.")
    project = media_root(root, source_workspace_id)
    _, index = _manifest(project)
    record = next((item for item in index["assets"] if item.get("asset_id") == asset_id and not item.get("archived_at")), None)
    if not record:
        record = next((row for row in _shared_records(root) if row["workspace_id"] == source_workspace_id and row["asset_id"] == asset_id and not row.get("archived_at")), None)
    if not record:
        raise ProductionAssetError("This source asset is unavailable or archived.")
    if role is not None and (role not in ROLE_KINDS or ROLE_KINDS[role] not in {"any", record["kind"]}):
        raise ProductionAssetError("Media type does not match the selected asset role.")
    media_root(root, workspace_id)
    if source_workspace_id == workspace_id:
        return assign_role(root, workspace_id, asset_id, role) if role else _public(record, workspace_id)
    path, _, filename = asset_path(root, source_workspace_id, asset_id)
    location = record.get("storage_location")
    if not location and record.get("source") == "youtube_download":
        location = {"store": "youtube", "path": record["relative_path"]}
    if mode == "reference" and location:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest() != record.get("sha256"):
            raise ProductionAssetError("Source content changed; refresh its registration before reuse.")
        return _link_shared_asset(root, workspace_id, source_workspace_id, record, location, role)
    if path.stat().st_size > MAX_UPLOAD_BYTES:
        raise ProductionAssetError("This source exceeds the 512 MiB import limit.")
    with path.open("rb") as stream:
        content = stream.read(MAX_UPLOAD_BYTES + 1)
    if hashlib.sha256(content).hexdigest() != record.get("sha256"):
        raise ProductionAssetError("Source content changed; refresh its registration before reuse.")
    # Preserve existing target annotations/roles on hash deduplication.
    _, target_index = _manifest(media_root(root, workspace_id))
    existing = next((item for item in target_index["assets"] if item.get("sha256") == record["sha256"]), None)
    if existing:
        if existing.get("archived_at"):
            raise ProductionAssetError("This file is archived in the target workspace. Restore it first.")
        if role:
            assign_role(root, workspace_id, existing["asset_id"], role)
        return _record_reuse(root, workspace_id, existing["asset_id"], source_workspace_id, record)
    return register_upload(root, workspace_id, filename=filename, content=content,
        role=role or "project_" + record["kind"],
        provenance_notes=f"Copied from workspace {source_workspace_id}, asset {asset_id}.",
        metadata={"library_sources": [{"workspace_id": source_workspace_id,
            "asset_id": asset_id, "sha256": record["sha256"], "source": catalogue_source(record),
            "filename": record.get("filename"), "created_at": record.get("created_at"),
            "roles": record.get("roles", []), "metadata": record.get("metadata", {}),
            "description": record.get("description", ""), "tags": record.get("tags", [])}]})


@_serialized_write
def _record_reuse(root: Path, workspace_id: str, asset_id: str, source_workspace_id: str, source: dict[str, Any]) -> dict[str, Any]:
    """Record a deduplicated reuse under its own lock; preserve target annotations."""
    index_path, index = _manifest(media_root(root, workspace_id))
    record = next(row for row in index["assets"] if row["asset_id"] == asset_id)
    sources = record.setdefault("metadata", {}).setdefault("library_sources", [])
    if not any(row.get("workspace_id") == source_workspace_id and row.get("asset_id") == source["asset_id"] for row in sources):
        sources.append({"workspace_id": source_workspace_id, "asset_id": source["asset_id"], "sha256": source["sha256"],
            "source": catalogue_source(source), "filename": source.get("filename"), "roles": source.get("roles", [])})
        _save(index_path, index)
    return _public(record, workspace_id, deduplicated=True)


@_serialized_write
def _link_shared_asset(root, workspace_id, source_workspace_id, source, location, role):
    index_path, index = _manifest(media_root(root, workspace_id))
    record = next((r for r in index["assets"] if r.get("storage_location") == location
                   and r.get("sha256") == source["sha256"] and not r.get("archived_at")), None)
    if record is None:
        record = copy.deepcopy(source)
        record.update(asset_id=f"pa-{uuid.uuid4().hex[:16]}", workspace_id=workspace_id,
                      storage_location=location, source="project_output",
                      created_at=datetime.now(timezone.utc).isoformat())
        record.pop("archived_at", None)
        record["roles"] = [role or "project_" + record["kind"]]
        record.setdefault("metadata", {})["library_sources"] = [{"workspace_id": source_workspace_id,
            "asset_id": source["asset_id"], "sha256": source["sha256"], "source": catalogue_source(source)}]
        index["assets"].append(record)
    elif role and role not in record["roles"]:
        record["roles"].append(role)
    _save(index_path, index)
    return _public(record, workspace_id)


@_serialized_write
def relocate_output(root, workspace_id, asset_id, choice, job_id):
    """Publish a final derivative once, then remove its verified staging file."""
    from . import output_destinations as destinations
    index_path, index = _manifest(media_root(root, workspace_id))
    record = next((r for r in index['assets'] if r['asset_id'] == asset_id), None)
    if not record: raise FileNotFoundError(asset_id)
    source, _, _ = asset_path(root, workspace_id, asset_id)
    metadata = record.get('metadata') or {}
    if record.get('source') != 'project_output' and not (job_id == 'recordings' and (record.get('storage_location') or {}).get('store') == 'audio'):
        return _public(record, workspace_id)
    # A deduplicated earlier output is already authoritative and may have users.
    owner_job = metadata.get('job_id') or (metadata.get('production_image_job') or {}).get('job_id') or metadata.get('assembly_job_id')
    if owner_job and owner_job != job_id: return _public(record, workspace_id)
    base = destinations.target_root(root, choice)
    if source.is_relative_to(base):
        public = _public(record, workspace_id);public['saved_path'] = str(source)
        return public
    filename = metadata.get('batch_filename') or (asset_id + source.suffix.lower())
    if Path(filename).name != filename: raise ValueError('Invalid output filename.')
    target = base / job_id / filename
    relative = target.relative_to(base).as_posix()
    token = choice.get('grant') or destinations.grant(root, str(base))['grant']
    if destinations.digest(source) != record.get("sha256"):
        raise ProductionAssetError("Output content changed; staging retained for recovery.")
    destinations.copy_verified(source, target)
    previous = record.get('storage_location')
    record['storage_location'] = {'store': 'output', 'grant': token, 'path': relative}
    record['saved_path'] = str(target)
    _save(index_path, index)
    _publish_shared(root, record)
    # Preserve shared source locations if another membership still references them.
    referenced = False
    if previous:
        for manifest in (Path(root) / 'projects').glob('*/media/assets.json'):
            if manifest == index_path: continue
            if any(r.get('storage_location') == previous for r in _manifest(manifest.parent)[1]['assets']):
                referenced = True; break
    if not referenced: source.unlink(missing_ok=True)
    return _public(record, workspace_id)


def deletion_preview(root: Path, workspace_id: str, asset_id: str) -> dict[str, Any]:
    """Resolve a catalogue identity, and report saved uses before permanent deletion."""
    path, _, _ = asset_path(root, workspace_id, asset_id)
    references = []
    # Operational saved documents only: reports/backups and historical job logs are not live selections.
    documents = list((Path(root) / "projects").rglob("*.json"))
    documents += [Path(root) / "ace_step/state.json", Path(root) / "services/editor/state.json",
                  Path(root) / "music_jukebox/state.json"]
    for document in sorted(set(documents)):
        if not document.is_file():
            continue
        if document.name in {"assets.json", "workspace.json"} or document.is_symlink():
            continue
        relative = document.relative_to(root).as_posix()
        if any(part in {"generated", "imports", "runs", "jobs"} for part in document.relative_to(root).parts):
            continue
        try:
            if asset_id in document.read_text(encoding="utf-8"):
                references.append(relative)
        except (OSError, UnicodeError):
            raise ProductionAssetError(f"Cannot check saved references in {relative}.")
    # Another membership, or a derived asset, must not be left pointing at deleted bytes.
    manifests = list((Path(root) / "projects").glob("*/media/assets.json"))
    manifests += list((Path(root) / "library").glob("*/assets.json"))
    rows = list(_shared_records(root))
    for document in manifests:
        owner = (project_identity(root, document.parent.parent.name)
                 if document.parent.name == "media" else
                 "tool-library" if document.parent.name == "tool-media" else document.parent.name)
        rows.extend({**row, "workspace_id": row.get("workspace_id") or owner}
                    for row in _manifest(document.parent)[1]["assets"])
    for other in rows:
        if other.get("workspace_id") == workspace_id and other.get("asset_id") == asset_id:
            continue
        if asset_id in json.dumps(other):
            references.append(f"Media {other.get('asset_id')} in {other.get('workspace_id')}")
        try:
            other_path, _, _ = asset_path(root, other.get("workspace_id", ""), other.get("asset_id", ""))
        except (ProductionAssetError, FileNotFoundError):
            continue
        if other_path == path:
            references.append(f"Shared file used by {other.get('asset_id')} in {other.get('workspace_id')}")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"asset_id": asset_id, "path": str(path), "sha256": digest.hexdigest(),
            "references": sorted(set(references)), "can_delete": not references}


@_serialized_write
def delete_media_file(root: Path, workspace_id: str, asset_id: str, sha256: str) -> dict[str, Any]:
    preview = deletion_preview(root, workspace_id, asset_id)
    if not preview["can_delete"]:
        raise ProductionAssetError("File is still used by: " + "; ".join(preview["references"]))
    if sha256 != preview["sha256"]:
        raise ProductionAssetError("File changed since confirmation. Refresh and review it again.")
    path, _, _ = asset_path(root, workspace_id, asset_id)
    index_path, index = _manifest(media_root(root, workspace_id))
    # Remove only this identity, never a containing folder or its source video.
    path.unlink()
    index["assets"] = [row for row in index["assets"] if row.get("asset_id") != asset_id]
    _save(index_path, index)
    for folder in ("youtube_downloads", "video_repertoire", "library/tool-media"):
        catalogue = Path(root) / folder / "catalog.json"
        if not catalogue.is_file():
            continue
        with (catalogue.parent / ".catalog.lock").open("a+b") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            data = json.loads(catalogue.read_text())
            data["assets"] = [row for row in data["assets"] if not
                              (row.get("workspace_id") == workspace_id and row.get("asset_id") == asset_id)]
            _save(catalogue, data)
    return {"deleted": True, "asset_id": asset_id, "path": str(path)}
