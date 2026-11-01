"""Workspace-scoped SAM Audio preview and explicit save adapter for Vibe."""
from __future__ import annotations
from story_builder.services.storage_paths import generated_root

import json
import math
import os
import re
import shutil
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import media_library, video_repertoire

RUN_ID = re.compile(r"[a-f0-9]{16}(?:-rerun-[a-f0-9]{8})?")
TEMP_ID = re.compile(r"sam-[a-f0-9]{32}")
PROMPT_VERSION = "sam-isolation-value-review-v1"


class SamAudioError(ValueError):
    pass


def _adapter():
    source = str(video_repertoire.ANALYZER_ROOT / "src")
    import sys
    if source not in sys.path:
        sys.path.insert(0, source)
    from video_audio_analyzer import sam_audio_adapter
    return sam_audio_adapter


def readiness() -> dict[str, Any]:
    """Read SAM worker/checkpoint health without submitting inference."""
    return _adapter().readiness()


def _paths(root: Path, workspace_id: str, temporary_id: str) -> tuple[Path, Path]:
    if (not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", workspace_id)
            or not TEMP_ID.fullmatch(temporary_id)):
        raise SamAudioError("Invalid temporary preview ID.")
    data_root = Path(root).resolve()
    base = (data_root / "video_repertoire" / "temp" / "sam_audio" / workspace_id).resolve()
    if not base.is_relative_to(data_root):
        raise SamAudioError("Temporary preview directory must remain inside the Vibe data root.")
    wav, info = base / f"{temporary_id}.wav", base / f"{temporary_id}.json"
    if wav.parent != base or info.parent != base:
        raise SamAudioError("Invalid temporary preview path.")
    return wav, info


def _owned_run(root: Path, workspace_id: str, run_id: str) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    if not RUN_ID.fullmatch(run_id):
        raise SamAudioError("Invalid analyzer run ID.")
    matched = None
    for job in video_repertoire.list_jobs("analysis"):
        request = job.get("request") or {}
        if request.get("workspace_id") != workspace_id or job.get("status") != "completed":
            continue
        for row in ((job.get("result") or {}).get("audio_analysis") or []):
            if row.get("run_id") == run_id:
                matched = (request, row)
                break
        if matched:
            break
    if not matched:
        raise FileNotFoundError("Analyzer run was not found in this workspace.")
    run_dir = video_repertoire.safe_path(video_repertoire.analyzer_runs_root() / run_id, video_repertoire.analyzer_runs_root())
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError("Analyzer run manifest is missing.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    staged_id = matched[1].get("asset_id")
    staged = video_repertoire.get_asset(staged_id) if isinstance(staged_id, str) else None
    metadata = (staged or {}).get("metadata") or {}
    source_id = metadata.get("source_asset_id")
    source_sha = metadata.get("source_sha256")
    if (metadata.get("workspace_id") != workspace_id or source_id not in matched[0].get("source_asset_ids", [])
            or not isinstance(source_sha, str)):
        raise FileNotFoundError("Analyzer run source is no longer available in this workspace.")
    source, _media_type, _filename = media_library.asset_path(root, workspace_id, source_id)
    if video_repertoire.sha256_file(source) != source_sha:
        raise FileNotFoundError("Source video changed since analysis.")
    audio_path = run_dir / "audio" / "analysis.wav"
    if not audio_path.is_file():
        raise FileNotFoundError("Run analysis audio is missing.")
    return run_dir, manifest, {"source_asset_id": source_id, "source_sha256": source_sha,
        "audio_path": audio_path, "video_asset_id": staged_id}


def isolate_event(root: Path, workspace_id: str, run_id: str, event_id: str, prompt: str) -> dict[str, Any]:
    run_dir, manifest, owner = _owned_run(root, workspace_id, run_id)
    if type(event_id) is not str or not re.fullmatch(r"[A-Za-z0-9_-]{1,120}", event_id):
        raise SamAudioError("Invalid audio event ID.")
    event = next((row for row in manifest.get("audio_events", []) if row.get("event_id") == event_id), None)
    if not event:
        raise FileNotFoundError("Audio event was not found in this run.")
    if type(prompt) is not str or not prompt.strip() or len(prompt.strip()) > 500:
        raise SamAudioError("Enter a short sound description (1–500 characters).")
    start = float(event.get("start_time_sec", 0))
    end = float(event.get("end_time_sec", 0))
    if not math.isfinite(start) or not math.isfinite(end) or start < 0 or end <= start:
        raise SamAudioError("The selected event has an invalid time range.")
    temp_root = _paths(root, workspace_id, "sam-" + "0" * 32)[0].parent
    from .media_jobs import gpu_workload_guard
    # Keep preview publication outside the guard: a safety trip must raise before
    # an unconfirmed sidecar result can be registered as a usable preview.
    with gpu_workload_guard(comfy_url=os.environ.get("COMFYUI_URL", "http://127.0.0.1:3008")):
        result = _adapter().isolate(audio_path=owner["audio_path"], prompt=prompt.strip(), start_sec=start,
            end_sec=end, temp_root=temp_root, provenance={"workspace_id": workspace_id, "run_id": run_id,
                "source_asset_id": owner["source_asset_id"], "source_sha256": owner["source_sha256"],
                "video_asset_id": owner["video_asset_id"], "event_id": event_id,
                "event_type": event.get("event_type"), "event_label": event.get("label"),
                "event_confidence": event.get("confidence"), "detector": event.get("detector"),
                "start_time_sec": start, "end_time_sec": end})
    if result.get("status") != "preview_ready":
        return {key: value for key, value in result.items() if key != "temporary_path"}
    temporary_id = result.get("temporary_id")
    wav, info = _paths(root, workspace_id, str(temporary_id))
    if not wav.is_file():
        raise SamAudioError("SAM Audio preview was not created.")
    ttl_hours = max(1, int(os.environ.get("VIDEO_AUDIO_ANALYZER_SAM_TEMP_TTL_HOURS", "24")))
    metadata = {**result, "expires_epoch": wav.stat().st_mtime + ttl_hours * 3600}
    metadata.pop("temporary_path", None)
    info.write_text(json.dumps(metadata, ensure_ascii=False), encoding="utf-8")
    return {key: value for key, value in metadata.items() if key != "expires_epoch"} | {
        "audio_url": f"/api/video-summariser/{workspace_id}/sam/previews/{temporary_id}/audio"}


def preview_path(root: Path, workspace_id: str, temporary_id: str) -> Path:
    wav, info = _paths(root, workspace_id, temporary_id)
    if not wav.is_file() or not info.is_file():
        raise FileNotFoundError("Temporary SAM preview was not found.")
    metadata = json.loads(info.read_text(encoding="utf-8"))
    if float(metadata.get("expires_epoch", 0)) <= time.time():
        wav.unlink(missing_ok=True); info.unlink(missing_ok=True)
        raise FileNotFoundError("Temporary SAM preview has expired.")
    return wav


def _append_audit(root: Path, workspace_id: str, record: dict[str, Any]) -> None:
    audit = Path(root).resolve() / "video_repertoire" / "indexes" / "sam_audio_reviews" / f"{workspace_id}.jsonl"
    audit.parent.mkdir(parents=True, exist_ok=True)
    with audit.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")


def _saved_preview_asset(root: Path, workspace_id: str, temporary_id: str) -> dict[str, Any] | None:
    offset = 0
    while True:
        page = media_library.list_assets(root, workspace_id, kind="audio", limit=100, offset=offset)
        for asset in page["assets"]:
            sam = (asset.get("metadata") or {}).get("sam_audio") or {}
            if asset.get("workspace_id") == workspace_id and sam.get("temporary_id") == temporary_id:
                return asset
        offset += page["limit"]
        if offset >= page["total"]:
            return None


def save_preview(root: Path, workspace_id: str, temporary_id: str) -> dict[str, Any]:
    _paths(root, workspace_id, temporary_id)
    existing = _saved_preview_asset(root, workspace_id, temporary_id)
    if existing:
        return {"status": "saved", "asset": existing, "idempotent": True}
    wav = preview_path(root, workspace_id, temporary_id)
    _wav, info_path = _paths(root, workspace_id, temporary_id)
    metadata = json.loads(info_path.read_text(encoding="utf-8"))
    audit = {"temporary_id": temporary_id, "decision": "save_to_repertoire", "reviewer": "director",
        "review_method": "played_preview_and_explicit_save", "provenance": metadata.get("provenance", {}),
        "reviewed_at": datetime.now(timezone.utc).isoformat()}
    provenance = metadata.get("provenance", {})
    relative = Path("derived") / "sam-audio" / f"{temporary_id}.wav"
    output_root = generated_root(root, workspace_id).parent
    output_workspace = generated_root(root, workspace_id)
    if output_root.is_symlink() or output_workspace.is_symlink():
        raise SamAudioError("The shared library output path is not safe.")
    destination = output_workspace / relative
    if not destination.resolve().is_relative_to(output_workspace.resolve()):
        raise SamAudioError("The shared library output path is not safe.")
    if destination.exists():
        raise SamAudioError("This preview has already been saved.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(wav, destination)
    try:
        asset = media_library.register_generated_audio(root, workspace_id, relative.as_posix(), {
        "description": str(metadata.get("prompt", "Isolated sound"))[:2000],
        "tags": ["isolated sound", str(provenance.get("event_label") or "audio event")[:80]],
        "audio_category": "sfx", "sam_audio": {**provenance, "temporary_id": temporary_id,
            "model": metadata.get("model"),
            "prompt": metadata.get("prompt"), "director_review": audit}})
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    _append_audit(root, workspace_id, audit)
    wav.unlink(missing_ok=True); info_path.unlink(missing_ok=True)
    return {"status": "saved", "asset": asset, "director_review": audit}


def discard_preview(root: Path, workspace_id: str, temporary_id: str) -> dict[str, Any]:
    wav, info = _paths(root, workspace_id, temporary_id)
    removed = wav.exists() or info.exists()
    wav.unlink(missing_ok=True); info.unlink(missing_ok=True)
    return {"status": "discarded", "removed": removed}
