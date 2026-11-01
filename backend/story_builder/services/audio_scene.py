"""Project-scoped wrappers for the existing TTS-Audio-Suite scene tools."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

DEFAULT_SUITE = Path("/home/riki/web_dev/setup_comfy_and-stuff/ComfyUI/custom_nodes/TTS-Audio-Suite")
AUDIO_SUFFIXES = {".wav", ".flac", ".mp3", ".ogg", ".m4a", ".aac"}
MAX_EDITS = 500


class SceneJobError(ValueError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def suite_root() -> Path:
    return Path(os.environ.get("TTS_AUDIO_SUITE_ROOT", str(DEFAULT_SUITE))).expanduser().resolve()


def tools_python() -> str:
    return os.environ.get("AUDIO_TOOLS_PYTHON", sys.executable)


def capabilities() -> dict[str, Any]:
    scripts = {
        "split": "split_scene_audio.py",
        "simple_stitch": "concat_scene_audio.py",
        "timed_stitch": "timed_concat_scene_audio.py",
    }
    root = suite_root() / "scripts"
    checks = {key: {"path": str(root / name), "available": (root / name).is_file()} for key, name in scripts.items()}
    return {"available": all(check["available"] for check in checks.values()), "checks": checks}


def validate_edits(raw: Any) -> list[dict[str, Any]]:
    edits = raw.get("edits") if isinstance(raw, dict) else raw
    if not isinstance(edits, list) or not edits:
        raise SceneJobError("At least one edit range is required")
    if len(edits) > MAX_EDITS:
        raise SceneJobError(f"At most {MAX_EDITS} edit ranges are allowed")
    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(edits, 1):
        if not isinstance(item, dict):
            raise SceneJobError(f"Edit {index} must be an object")
        try:
            start, end = float(item["start"]), float(item["end"])
        except (KeyError, TypeError, ValueError) as exc:
            raise SceneJobError(f"Edit {index} needs numeric start and end") from exc
        if start < 0 or end <= start:
            raise SceneJobError(f"Edit {index} has an invalid range: {start} -> {end}")
        clean = {**item, "start": start, "end": end, "text": str(item.get("text", "")).strip()}
        clean.pop("file_name", None)
        normalized.append(clean)
    normalized.sort(key=lambda item: item["start"])
    for previous, current in zip(normalized, normalized[1:]):
        if current["start"] < previous["end"]:
            raise SceneJobError("Edit ranges overlap")
    return normalized


def safe_project_path(project_dir: Path, relative_path: str) -> Path:
    candidate = (project_dir / relative_path).resolve()
    root = project_dir.resolve()
    if candidate != root and root not in candidate.parents:
        raise SceneJobError("Project path escapes the project directory")
    if not candidate.is_file():
        raise SceneJobError("Project audio file was not found")
    if candidate.suffix.lower() not in AUDIO_SUFFIXES:
        raise SceneJobError("Unsupported audio file type")
    return candidate


def _tool_result(command: list[str]) -> dict[str, Any]:
    completed = subprocess.run(command, cwd=suite_root(), capture_output=True, text=True, timeout=3600)
    if completed.returncode:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or "Audio tool failed")
    decoder = json.JSONDecoder()
    for offset, character in enumerate(completed.stdout):
        if character != "{":
            continue
        try:
            value, end = decoder.raw_decode(completed.stdout[offset:])
            if not completed.stdout[offset + end:].strip() and isinstance(value, dict):
                return value
        except json.JSONDecodeError:
            continue
    raise RuntimeError("Audio tool did not return a JSON result")


def run_split(*, job: dict[str, Any], project_dir: Path, source: Path, edits: list[dict[str, Any]], transcript: str | None, update: Callable[[dict[str, Any]], None]) -> None:
    root = project_dir / "audio" / "scenes" / job["job_id"]
    original_dir, parts_dir = root / "original", root / "parts"
    original_dir.mkdir(parents=True, exist_ok=True)
    parts_dir.mkdir(parents=True, exist_ok=True)
    source_copy = original_dir / f"source{source.suffix.lower()}"
    edits_path, transcript_path = root / "edits.json", root / "transcript.txt"
    try:
        shutil.copy2(source, source_copy)
        edits_path.write_text(json.dumps({"edits": edits}, indent=2) + "\n", encoding="utf-8")
        if transcript is not None:
            transcript_path.write_text(transcript, encoding="utf-8")
        update({"status": "running", "stage": "splitting", "progress": 20, "started_at": utc_now()})
        command = [tools_python(), str(suite_root() / "scripts" / "split_scene_audio.py"), "--audio", str(source_copy), "--instructions", str(edits_path), "--output-dir", str(parts_dir)]
        if transcript is not None:
            command += ["--transcript", str(transcript_path)]
        result = _tool_result(command)
        manifest = json.loads(Path(result["scene_manifest_path"]).read_text(encoding="utf-8"))
        for clip in manifest["clips"]:
            clip["relative_path"] = str(Path("audio") / "scenes" / job["job_id"] / "parts" / clip["split_file"])
        update({"status": "completed", "stage": "completed", "progress": 95, "completed_at": utc_now(), "result": result, "manifest": manifest,
            "manifest_path": str(Path("audio") / "scenes" / job["job_id"] / "parts" / Path(result["scene_manifest_path"]).name),
            "enriched_path": str(Path("audio") / "scenes" / job["job_id"] / "parts" / Path(result["enriched_json_path"]).name)})
    except Exception as exc:
        update({"status": "failed", "stage": "failed", "completed_at": utc_now(), "error": str(exc)})


def run_stitch(*, job: dict[str, Any], project_dir: Path, split_job: dict[str, Any], replacements: dict[int, Path], gaps: dict[int, float], mode: str, update: Callable[[dict[str, Any]], None]) -> None:
    split_root = project_dir / "audio" / "scenes" / split_job["job_id"]
    root = project_dir / "audio" / "scenes" / job["job_id"]
    stage, replacement_dir = root / "stage", root / "replacements"
    stage.mkdir(parents=True, exist_ok=True)
    replacement_dir.mkdir(parents=True, exist_ok=True)
    try:
        update({"status": "running", "stage": "stitching", "progress": 20, "started_at": utc_now()})
        items, provenance = [], []
        clips = split_job.get("manifest", {}).get("clips", [])
        for clip in clips:
            index, name = int(clip["clip_index"]), str(clip["split_file"])
            original = safe_project_path(project_dir, str(Path("audio") / "scenes" / split_job["job_id"] / "parts" / name))
            selected = original
            if index in replacements:
                replacement = replacements[index]
                if not replacement.is_file() or replacement.suffix.lower() not in AUDIO_SUFFIXES:
                    raise SceneJobError(f"Replacement for clip {index} is not a supported audio file")
                saved = replacement_dir / f"clip_{index:04d}{replacement.suffix.lower()}"
                shutil.copy2(replacement, saved)
                selected, staged_name = saved, f"edited_{name}"
            else:
                staged_name = name
            shutil.copy2(selected, stage / staged_name)
            gap = float(gaps.get(index, 0.0))
            if gap < 0 or gap > 3600:
                raise SceneJobError(f"Gap after clip {index} must be between 0 and 3600 seconds")
            items.append({"file": staged_name, "gap_after_seconds": gap})
            provenance.append({"clip_index": index, "selected": "replacement" if index in replacements else "original", "file": staged_name})
        output = root / "final.wav"
        if mode == "timed":
            manifest_path = root / "timed_manifest.json"
            manifest_path.write_text(json.dumps({"version": 1, "items": items}, indent=2) + "\n", encoding="utf-8")
            command = [tools_python(), str(suite_root() / "scripts" / "timed_concat_scene_audio.py"), "--clips-dir", str(stage), "--manifest", str(manifest_path), "--output", str(output)]
        elif mode == "simple":
            command = [tools_python(), str(suite_root() / "scripts" / "concat_scene_audio.py"), "--clips-dir", str(stage), "--output", str(output)]
        else:
            raise SceneJobError("Stitch mode must be simple or timed")
        result = _tool_result(command)
        relative = str(Path("audio") / "scenes" / job["job_id"] / "final.wav")
        update({"status": "completed", "stage": "completed", "progress": 95, "completed_at": utc_now(),
            "result": result, "provenance": provenance, "output_path": relative})
    except Exception as exc:
        update({"status": "failed", "stage": "failed", "completed_at": utc_now(), "error": str(exc)})
