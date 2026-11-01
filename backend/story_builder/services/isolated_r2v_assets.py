"""Resolve frozen workspace media IDs and stage H3 R2V inputs per job."""
from __future__ import annotations

import re
import stat
from pathlib import Path
from typing import Any, Mapping

from story_builder.services.media_library import asset_path, list_assets, pinned_style_asset_path
from story_builder.services.minimax_h3_graph_compiler import ResolvedAsset
from story_builder.services.minimax_h3_media import (
    H3MediaError, cleanup_owned_media, stage_audio_reference,
    stage_image_reference, stage_video_reference,
)

_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$")


class R2VStagingError(ValueError):
    pass


def _safe_path(path: Path, label: str) -> Path:
    """Reject symlinks in every existing component before source helpers follow paths."""
    absolute = Path(path).expanduser().absolute()
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current /= part
        try:
            if stat.S_ISLNK(current.lstat().st_mode):
                raise R2VStagingError(f"{label} cannot contain symlinks.")
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise R2VStagingError(f"{label} could not be safely checked.") from exc
    return absolute


def _check_job_paths(input_dir: Path, owner_base: Path, job_id: str) -> None:
    _safe_path(input_dir, "Comfy input root")
    _safe_path(owner_base, "R2V owner root")
    owner_dir = _safe_path(owner_base / job_id, "R2V job owner directory")
    _safe_path(owner_dir / "owner_manifest.json", "R2V owner manifest")


def stage_r2v_references(*, media_root: Path, workspace_id: str, job_id: str,
                         request: Mapping[str, Any], comfy_input_root: Path,
                         owner_root: Path, style_selection: dict[str, Any] | None = None,
                         ffmpeg: str = "ffmpeg", ffprobe: str = "ffprobe"):
    if not _ID.fullmatch(workspace_id) or not _ID.fullmatch(job_id):
        raise R2VStagingError("Workspace or job identity is invalid.")
    input_dir = _safe_path(Path(comfy_input_root), "Comfy input root")
    owner_base = _safe_path(Path(owner_root), "R2V owner root")
    _check_job_paths(input_dir, owner_base, job_id)
    plan_rows = [("image", row) for row in request["images"]]
    plan_rows += [("video", row) for row in request["videos"]]
    plan_rows += [("audio", row) for row in request["audios"]]
    resolved: dict[str, ResolvedAsset] = {}
    try:
        wanted = {row[1]["asset_id"] for row in plan_rows}
        index = {}
        offset = 0
        while wanted - index.keys():
            page = list_assets(Path(media_root), workspace_id, limit=100, offset=offset,
                style_selection=style_selection, include_archived=True)
            index.update((row["asset_id"], row) for row in page["assets"])
            offset += page["limit"]
            if offset >= page["total"] or not page["assets"]:
                break
        for kind, row in plan_rows:
            asset_id, expected_hash = row["asset_id"], row["sha256"]
            record = index.get(asset_id)
            if not record or record.get("kind") != kind or record.get("sha256") != expected_hash:
                raise R2VStagingError("Selected asset is missing, changed, or has the wrong media type.")
            if record.get("recommended"):
                source, media_type, _filename, _source_record = pinned_style_asset_path(
                    Path(media_root), style_selection, asset_id)
            else:
                source, media_type, _filename = asset_path(Path(media_root), workspace_id, asset_id)
            if media_type != record.get("media_type"):
                raise R2VStagingError("Selected asset MIME metadata changed.")
            common = {"source_path": source, "asset_id": asset_id, "owner_id": job_id,
                      "comfy_input_dir": input_dir, "owner_root": owner_base}
            if kind == "image":
                staged = stage_image_reference(**common, ffprobe=ffprobe)
                if staged.source_sha256 != expected_hash:
                    raise R2VStagingError("Image bytes changed after request validation.")
                resolved[asset_id] = ResolvedAsset(asset_id, "image", staged.filename, staged.sha256)
            elif kind == "video":
                staged = stage_video_reference(**common, start_sec=row["start_sec"],
                    end_sec=row["end_sec"], include_audio=row["include_paired_soundtrack"],
                    ffmpeg=ffmpeg, ffprobe=ffprobe)
                if staged.source_sha256 != expected_hash:
                    raise R2VStagingError("Video bytes changed after request validation.")
                resolved[asset_id] = ResolvedAsset(asset_id, "video", staged.filename,
                    staged.sha256, staged.source_start_sec, staged.source_end_sec, staged.has_audio)
            else:
                staged = stage_audio_reference(**common, ffmpeg=ffmpeg, ffprobe=ffprobe)
                if staged.source_sha256 != expected_hash:
                    raise R2VStagingError("Audio bytes changed after request validation.")
                resolved[asset_id] = ResolvedAsset(asset_id, "audio", staged.filename, staged.sha256)
    except Exception:
        try:
            cleanup_r2v_staging_job(job_id=job_id, comfy_input_root=input_dir,
                owner_root=owner_base)
        except R2VStagingError:
            pass
        raise
    return resolved


def cleanup_r2v_staging_job(*, job_id: str, comfy_input_root: Path, owner_root: Path):
    if not _ID.fullmatch(job_id):
        raise R2VStagingError("R2V job identity is invalid.")
    input_dir = _safe_path(Path(comfy_input_root), "Comfy input root")
    owner_base = _safe_path(Path(owner_root), "R2V owner root")
    _check_job_paths(input_dir, owner_base, job_id)
    return cleanup_owned_media(job_id, comfy_input_dir=input_dir, owner_root=owner_base)
