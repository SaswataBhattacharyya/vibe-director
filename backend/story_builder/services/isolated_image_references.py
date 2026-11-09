"""Validate and stage frozen image references for reference-conditioned workflows."""
from __future__ import annotations

import copy
import hashlib
import re
import stat
from pathlib import Path
from typing import Any

from story_builder.services.media_library import asset_path, list_assets, pinned_style_asset_path
from story_builder.services.minimax_h3_media import (
    cleanup_owned_media, stage_image_reference,
)

_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$")


class ImageReferenceError(ValueError):
    pass


def _safe_path(path: Path) -> Path:
    absolute = Path(path).expanduser().absolute()
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current /= part
        try:
            if stat.S_ISLNK(current.lstat().st_mode):
                raise ImageReferenceError("Image reference paths cannot contain symlinks.")
        except FileNotFoundError:
            continue
    return absolute


def validate_image_references(*, media_root: Path, workspace_id: str,
                              references: Any, style_selection: dict[str, Any] | None = None,
                              required_role: str | None = None
                              ) -> list[dict[str, str]]:
    if not _ID.fullmatch(workspace_id):
        raise ImageReferenceError("Workspace ID is invalid.")
    if not isinstance(references, list) or not 1 <= len(references) <= 3:
        raise ImageReferenceError("Qwen Image Edit requires one to three image references.")
    wanted: dict[str, str] = {}
    for item in references:
        if (not isinstance(item, dict) or set(item) != {"asset_id", "sha256"}
                or not isinstance(item.get("asset_id"), str) or not _ID.fullmatch(item["asset_id"])
                or not isinstance(item.get("sha256"), str)
                or not re.fullmatch(r"[a-f0-9]{64}", item["sha256"])):
            raise ImageReferenceError("Each image reference must contain only an asset_id and SHA-256.")
        if item["asset_id"] in wanted:
            raise ImageReferenceError("Choose each reference image only once.")
        wanted[item["asset_id"]] = item["sha256"]
    available: dict[str, dict[str, Any]] = {}
    offset = 0
    while True:
        page = list_assets(Path(media_root), workspace_id, kind="image", limit=100,
            offset=offset, style_selection=style_selection)
        available.update((row["asset_id"], row) for row in page["assets"])
        offset += page["limit"]
        if offset >= page["total"] or not page["assets"]:
            break
    for asset_id, digest in wanted.items():
        record = available.get(asset_id)
        if not record or record.get("kind") != "image" or record.get("sha256") != digest:
            raise ImageReferenceError("A selected image is missing, changed, or unavailable in this workspace.")
        if required_role and required_role not in record.get("roles", []):
            raise ImageReferenceError(f"Qwen multi-angle views require an image saved as {required_role.replace('_', ' ')}.")
        try:
            if record.get("recommended"):
                source, media_type, _filename, _source_record = pinned_style_asset_path(
                    Path(media_root), style_selection, asset_id)
            else:
                source, media_type, _filename = asset_path(Path(media_root), workspace_id, asset_id)
            source = _safe_path(source)
            digest_builder = hashlib.sha256()
            with source.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest_builder.update(chunk)
            actual = digest_builder.hexdigest()
        except (OSError, ValueError) as exc:
            raise ImageReferenceError("A selected image is missing, changed, or unavailable in this workspace.") from exc
        if media_type != record.get("media_type") or actual != digest:
            raise ImageReferenceError("A selected image is missing, changed, or unavailable in this workspace.")
    return [{"asset_id": asset_id, "sha256": digest} for asset_id, digest in wanted.items()]


def prepare_image_edit_graph(*, job: dict[str, Any], media_root: Path,
                             comfy_input_root: Path, owner_root: Path,
                             style_selection: dict[str, Any] | None = None,
                             ffprobe: str = "ffprobe") -> dict[str, Any]:
    settings = job.get("settings") or {}
    references = settings.get("image_references") or []
    if not references:
        return job["graph"]
    workspace_id = job["project_id"]
    canonical = validate_image_references(media_root=media_root, workspace_id=workspace_id,
        references=references, style_selection=style_selection or settings.get("style_selection"),
        required_role=("character_master" if job.get("asset_role") == "character_view" else "world_master") if job.get("workflow_id") == "qwen_image_multi_angle_2511" else None)
    if job.get('workflow_id') == 'flux_kontext_dev' and len(canonical) != 1:
        raise ImageReferenceError('FLUX Kontext requires exactly one reference image.')
    owner_id = f"image-{job.get('job_id', '')}"
    if not _ID.fullmatch(owner_id):
        raise ImageReferenceError("Image-reference staging owner is invalid.")
    index: dict[str, dict[str, Any]] = {}
    offset = 0
    selection = style_selection or settings.get("style_selection")
    while True:
        page = list_assets(Path(media_root), workspace_id, kind="image", limit=100,
            offset=offset, style_selection=selection)
        index.update((row["asset_id"], row) for row in page["assets"])
        offset += page["limit"]
        if offset >= page["total"] or not page["assets"]:
            break
    filenames = []
    try:
        for item in canonical:
            record = index[item["asset_id"]]
            if record.get("recommended"):
                source, media_type, _filename, _source_record = pinned_style_asset_path(
                    Path(media_root), selection, item["asset_id"])
            else:
                source, media_type, _filename = asset_path(Path(media_root), workspace_id, item["asset_id"])
            source = _safe_path(source)
            if media_type != record.get("media_type"):
                raise ImageReferenceError("Image reference MIME metadata changed.")
            staged = stage_image_reference(source, asset_id=item["asset_id"], owner_id=owner_id,
                comfy_input_dir=_safe_path(Path(comfy_input_root)),
                owner_root=_safe_path(Path(owner_root)), ffprobe=ffprobe)
            if staged.source_sha256 != item["sha256"]:
                raise ImageReferenceError("Image bytes changed after request validation.")
            filenames.append(staged.filename)
    except Exception:
        cleanup_image_reference_staging(owner_id=owner_id,
            comfy_input_root=comfy_input_root, owner_root=owner_root)
        raise
    graph = copy.deepcopy(job["graph"])
    node_ids = ("1",) if job.get("workflow_id") == "flux_kontext_dev" else ("41",) if job.get("workflow_id") == "qwen_image_multi_angle_2511" else ("78", "120", "121")
    if job.get("workflow_id") == "qwen_image_multi_angle_2511" and len(filenames) != 1:
        cleanup_image_reference_staging(owner_id=owner_id,
            comfy_input_root=comfy_input_root, owner_root=owner_root)
        raise ImageReferenceError("Qwen multi-angle world views require exactly one selected base image.")
    for node_id, filename in zip(node_ids, filenames):
        node = graph.get(node_id)
        if not isinstance(node, dict) or node.get("class_type") != "LoadImage":
            raise ImageReferenceError("Image-edit graph no longer matches its input contract.")
        node["inputs"]["image"] = filename
    return graph


def cleanup_image_reference_staging(*, owner_id: str, comfy_input_root: Path,
                                    owner_root: Path):
    if not _ID.fullmatch(owner_id):
        raise ImageReferenceError("Image-reference cleanup owner is invalid.")
    return cleanup_owned_media(owner_id,
        comfy_input_dir=_safe_path(Path(comfy_input_root)),
        owner_root=_safe_path(Path(owner_root)))
