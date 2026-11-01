"""Resolve and stage frozen FL2VA frame assets; this module never submits jobs."""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import stat
from pathlib import Path
from typing import Any, Mapping

from story_builder.services.media_library import asset_path

_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$")
_HEX = re.compile(r"^[a-f0-9]{64}$")
_IMAGE_FORMATS = {
    ".png": ("image/png", lambda b: b.startswith(b"\x89PNG\r\n\x1a\n")),
    ".jpg": ("image/jpeg", lambda b: b.startswith(b"\xff\xd8\xff")),
    ".jpeg": ("image/jpeg", lambda b: b.startswith(b"\xff\xd8\xff")),
    ".webp": ("image/webp", lambda b: b.startswith(b"RIFF") and b[8:12] == b"WEBP"),
}


class FL2VAStagingError(ValueError):
    """An asset cannot be safely staged for the requested frame slot."""


def _validate_reference(reference: Any, slot: str) -> dict[str, str]:
    if not isinstance(reference, Mapping) or set(reference) != {"asset_id", "sha256"}:
        raise FL2VAStagingError(f"{slot} requires a frozen asset ID and SHA-256.")
    asset_id, digest = reference["asset_id"], reference["sha256"]
    if type(asset_id) is not str or not _SAFE_ID.fullmatch(asset_id):
        raise FL2VAStagingError(f"{slot} contains an invalid asset ID.")
    if type(digest) is not str or not _HEX.fullmatch(digest):
        raise FL2VAStagingError(f"{slot} contains an invalid SHA-256.")
    return {"asset_id": asset_id, "sha256": digest}


def _checked_input_root(value: Path) -> Path:
    configured = Path(value).expanduser().absolute()
    if not configured.is_dir():
        raise FL2VAStagingError("Configured ComfyUI input root is missing or not a directory.")
    cursor = Path(configured.anchor)
    for part in configured.parts[1:]:
        cursor /= part
        if cursor.is_symlink():
            raise FL2VAStagingError("ComfyUI input root cannot contain symlink components.")
    resolved = configured.resolve(strict=True)
    if resolved != configured:
        raise FL2VAStagingError("ComfyUI input root must resolve to its configured directory.")
    return resolved


def _copy_verified(source: Path, destination: Path, *, media_type: str,
                   expected_hash: str, suffix: str) -> None:
    format_spec = _IMAGE_FORMATS.get(suffix.lower())
    if format_spec is None or media_type != format_spec[0]:
        raise FL2VAStagingError("Frame asset is not a supported image type.")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        source_fd = os.open(source, flags)
    except OSError as exc:
        raise FL2VAStagingError("Frame asset is missing or is a symlink.") from exc
    digest = hashlib.sha256()
    header = bytearray()
    try:
        with os.fdopen(source_fd, "rb") as reader, destination.open("xb") as writer:
            info = os.fstat(reader.fileno())
            if not stat.S_ISREG(info.st_mode):
                raise FL2VAStagingError("Frame asset must be a regular file.")
            while chunk := reader.read(1024 * 1024):
                if len(header) < 16:
                    header.extend(chunk[:16 - len(header)])
                digest.update(chunk)
                writer.write(chunk)
            writer.flush()
            os.fsync(writer.fileno())
        if not format_spec[1](bytes(header)):
            raise FL2VAStagingError("Frame bytes do not match their declared image format.")
        if digest.hexdigest() != expected_hash:
            raise FL2VAStagingError("Frame bytes no longer match the frozen request hash.")
    except Exception:
        destination.unlink(missing_ok=True)
        raise


def stage_fl2va_frames(*, media_root: Path, workspace_id: str, job_id: str,
                       first_frame: Mapping[str, str], last_frame: Mapping[str, str],
                       comfy_input_root: Path) -> tuple[dict[str, str], Any]:
    """Stage first/last bytes in an isolated Comfy input directory.

    Returns frame slot → Comfy-relative basename plus an idempotent cleanup
    closure. The caller owns the staged inputs until cleanup is invoked.
    """
    if type(workspace_id) is not str or not _SAFE_ID.fullmatch(workspace_id):
        raise FL2VAStagingError("Invalid workspace ID.")
    if type(job_id) is not str or not _SAFE_ID.fullmatch(job_id):
        raise FL2VAStagingError("Invalid job ID.")
    refs = {"first_frame": _validate_reference(first_frame, "first_frame"),
            "last_frame": _validate_reference(last_frame, "last_frame")}
    input_root = _checked_input_root(Path(comfy_input_root))
    owner_root = input_root / "vibe-director-fl2va"
    if owner_root.is_symlink():
        raise FL2VAStagingError("FL2VA staging root cannot be a symlink.")
    owner_root.mkdir(mode=0o700, exist_ok=True)
    if not owner_root.resolve(strict=True).is_relative_to(input_root):
        raise FL2VAStagingError("FL2VA staging root escaped ComfyUI input.")
    job_dir = owner_root / job_id
    job_dir.mkdir(mode=0o700)
    if not job_dir.resolve(strict=True).is_relative_to(owner_root.resolve(strict=True)):
        shutil.rmtree(job_dir, ignore_errors=True)
        raise FL2VAStagingError("Job staging directory escaped its owner root.")

    staged: dict[str, str] = {}
    try:
        for slot, reference in refs.items():
            try:
                source, media_type, filename = asset_path(Path(media_root), workspace_id, reference["asset_id"])
            except (OSError, ValueError) as exc:
                raise FL2VAStagingError(f"{slot} asset is missing, invalid, or escapes its workspace.") from exc
            suffix = Path(filename).suffix.lower()
            output_name = f"{slot}{suffix}"
            _copy_verified(source, job_dir / output_name, media_type=media_type,
                           expected_hash=reference["sha256"], suffix=suffix)
            staged[slot] = (Path("vibe-director-fl2va") / job_id / output_name).as_posix()
    except Exception:
        shutil.rmtree(job_dir, ignore_errors=True)
        raise

    return staged, lambda: cleanup_fl2va_staging_job(input_root, job_id)


def cleanup_fl2va_staging_job(comfy_input_root: Path, job_id: str) -> None:
    """Remove only one job-owned staging directory; safe to call after restart."""
    if type(job_id) is not str or not _SAFE_ID.fullmatch(job_id):
        raise FL2VAStagingError("Invalid job ID for staging cleanup.")
    configured = Path(comfy_input_root).expanduser().absolute()
    if not configured.is_dir():
        return
    try:
        input_root = _checked_input_root(configured)
    except FL2VAStagingError:
        return
    owner_root = input_root / "vibe-director-fl2va"
    if owner_root.is_symlink() or not owner_root.is_dir():
        return
    job_dir = owner_root / job_id
    if not job_dir.exists() or job_dir.is_symlink():
        return
    try:
        if job_dir.resolve(strict=True).is_relative_to(owner_root.resolve(strict=True)):
            shutil.rmtree(job_dir)
    except FileNotFoundError:
        return
