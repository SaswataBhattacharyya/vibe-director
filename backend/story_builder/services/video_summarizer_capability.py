"""Read-only readiness snapshot for the adapted Video Summariser integration."""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable


def _image_status(image: str, runner: Callable[..., Any]) -> dict[str, Any]:
    docker = shutil.which("docker")
    if not docker:
        return {"available": False, "state": "docker_missing", "reason": "Docker is not installed."}
    try:
        result = runner([docker, "image", "inspect", image], capture_output=True,
                        text=True, timeout=3, check=False)
    except subprocess.TimeoutExpired:
        return {"available": False, "state": "docker_timeout", "reason": "Docker did not answer the image check."}
    except OSError as exc:
        if exc.errno in {13, 1}:
            return {"available": False, "state": "docker_permission", "reason": "This service account cannot inspect Docker images."}
        return {"available": False, "state": "docker_error", "reason": "Docker image readiness could not be checked."}
    if result.returncode == 0:
        return {"available": True, "state": "ready", "reason": None}
    detail = f"{result.stderr or ''} {result.stdout or ''}".lower()
    if "permission denied" in detail or "access denied" in detail:
        return {"available": False, "state": "docker_permission", "reason": "This service account cannot inspect Docker images."}
    if "cannot connect" in detail or "daemon" in detail and "running" in detail:
        return {"available": False, "state": "docker_stopped", "reason": "The Docker daemon is not reachable."}
    return {"available": False, "state": "image_missing", "reason": f"Required analyzer image is not built: {image}."}


def video_summarizer_capability(*, analyzer_root: str | Path | None = None,
                                adapter_ready: bool = False,
                                runner: Callable[..., Any] = subprocess.run) -> dict[str, Any]:
    """Report analyzer dependencies without starting containers, models, or GPU work."""
    default_root = Path(__file__).resolve().parents[3] / "local_data" / "engines" / "video-analyzer"
    root = Path(analyzer_root or os.environ.get("VIBE_DIRECTOR_VIDEO_ANALYZER_ROOT",
        default_root)).expanduser().resolve()
    launcher_root = Path(__file__).resolve().parent.parent / "scripts" / "video_audio_analyzer"
    source_ready = all(path.is_file() for path in (
        launcher_root / "run_peav_worker.sh",
        launcher_root / "run_internvideo3_stage.sh",
        root / "src/video_audio_analyzer/cli.py",
    ))
    model_checks = {
        "PE-AV": root / "models/pe-av-base/config.json",
        "InternVideo3": root / "models/internvideo3-8b-instruct/model.safetensors.index.json",
        "PANNs": root / "models/panns/Cnn14_DecisionLevelMax_mAP=0.385.pth",
        "HTS-AT": root / "models/HTSAT_AudioSet_Saved_1.ckpt",
        "Whisper": root / "models/faster-whisper-large-v3/config.json",
        "Speaker embeddings": root / "models/spkrec-ecapa-voxceleb/config.json",
    }
    models = {name: path.is_file() for name, path in model_checks.items()}
    images = {
        "analysis": _image_status("video-audio-analyzer-peav:dev", runner),
        "video_summary": _image_status("video-audio-analyzer-internvideo3:dev", runner),
    }
    checks = {
        "analyzer_source": {"available": source_ready, "state": "ready" if source_ready else "missing",
            "reason": None if source_ready else "Analyzer source or entry point is missing."},
        "models": {"available": all(models.values()), "state": "ready" if all(models.values()) else "incomplete",
            "items": models},
        "container_images": {"available": all(item["available"] for item in images.values()),
            "state": "ready" if all(item["available"] for item in images.values()) else "incomplete", "items": images},
        "vibe_adapter": {"available": adapter_ready,
            "state": "ready" if adapter_ready else "not_integrated",
            "reason": None if adapter_ready else "Video Summariser jobs and result records are not yet connected to Vibe's shared asset library."},
    }
    available = all(item["available"] for item in checks.values())
    return {"tool": "video_summariser", "available": available, "checks": checks,
        "can_analyze": available,
        "reason": ("Analyzer and Vibe adapter are ready. Starting analysis will use the local GPU." if available
            else "Analysis is unavailable until the analyzer source, models, container images and Vibe adapter are ready."),
        "checked_without_starting_jobs": True}
