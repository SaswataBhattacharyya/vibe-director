"""Subprocess worker for Video Repertoire download and analysis jobs."""

from __future__ import annotations
from story_builder.services.storage_paths import generated_root

import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import traceback
from contextlib import nullcontext
from pathlib import Path
from typing import Any

from story_builder.services import video_repertoire as store
from story_builder.services.media_jobs import gpu_workload_guard, gpu_workload_lock
from story_builder.services.video_summarizer_results import publish_analyzer_outputs


class _GpuMemorySampler:
    """Best-effort host GPU allocation sampler for an analysis job.

    Reports total compute-process allocations, not a falsely precise attribution
    to one container. The baseline/delta help separate resident services from
    the peak observed while this job was active.
    """

    def __init__(self, interval_seconds: float = 1.0) -> None:
        self.interval_seconds = interval_seconds
        self.samples: list[int] = []
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    @staticmethod
    def _read_compute_allocations_mib() -> int | None:
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-compute-apps=used_memory", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=3, check=False)
            if result.returncode != 0:
                return None
            values = [int(line.strip()) for line in result.stdout.splitlines() if line.strip().isdigit()]
            return sum(values)
        except (OSError, subprocess.SubprocessError, AttributeError, TypeError, ValueError):
            return None

    def _sample(self) -> None:
        while not self._stop.is_set():
            value = self._read_compute_allocations_mib()
            if value is not None:
                self.samples.append(value)
            self._stop.wait(self.interval_seconds)

    def __enter__(self) -> "_GpuMemorySampler":
        self._thread = threading.Thread(target=self._sample, name="analysis-gpu-sampler", daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *_: object) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=4)
        # Take a final sample so short jobs still have an end reading.
        value = self._read_compute_allocations_mib()
        if value is not None:
            self.samples.append(value)

    def report(self) -> dict[str, Any]:
        if not self.samples:
            return {"available": False, "reason": "nvidia-smi compute memory query unavailable"}
        baseline = self.samples[0]
        peak = max(self.samples)
        return {"available": True, "measurement": "host_compute_process_allocations",
                "sample_interval_seconds": self.interval_seconds,
                "baseline_mib": baseline, "peak_mib": peak,
                "peak_delta_mib": max(0, peak - baseline),
                "sample_count": len(self.samples),
                "note": "Includes concurrent/resident GPU processes; peak delta is an estimate, not isolated per-container VRAM."}


def save_job(kind: str, job_id: str, **changes: Any) -> dict[str, Any]:
    path = store.job_path(kind, job_id)
    job = json.loads(path.read_text(encoding="utf-8"))
    if job.get("status") in {"cancelled", "cancel_requested"}:
        return job
    job.update(changes, updated_at=store.utc_now())
    store._atomic_json(path, job)
    return job


def event(kind: str, job_id: str, stage: str, status: str, message: str, progress: int, payload: dict[str, Any] | None = None) -> None:
    path = store.job_path(kind, job_id)
    job = json.loads(path.read_text(encoding="utf-8"))
    if job.get("status") in {"cancelled", "cancel_requested"}:
        raise KeyboardInterrupt("Job cancelled")
    job.setdefault("events", []).append({"timestamp": store.utc_now(), "stage": stage, "status": status, "message": message, "payload": payload or {}})
    job["events"] = job["events"][-300:]
    job.update(stage=stage, message=message, progress=max(job.get("progress", 0), min(progress, 99)), updated_at=store.utc_now())
    store._atomic_json(path, job)


def _analyzer_visual_scenes(manifest: dict[str, Any], run_dir: Path) -> list[dict[str, Any]]:
    """Expose only run-relative frame artifacts and compact measured evidence."""
    run_id = str(manifest.get("run_id", ""))
    marker = f"/app/runs/{run_id}/"
    scenes: list[dict[str, Any]] = []
    for scene in manifest.get("scenes", []):
        scene_id = str(scene.get("scene_id", ""))
        frames: list[dict[str, Any]] = []
        for frame in scene.get("frames", []):
            container_path = str(frame.get("path", ""))
            relative = container_path.split(marker, 1)[1] if marker in container_path else ""
            candidate = (run_dir / relative).resolve() if relative else None
            try:
                if candidate is not None:
                    candidate.relative_to(run_dir.resolve())
            except ValueError:
                candidate = None
            artifact_path = relative if candidate is not None and candidate.is_file() else None
            evidence = frame.get("evidence", {}) if isinstance(frame.get("evidence"), dict) else {}
            frames.append({
                "frame_id": frame.get("frame_id"), "timestamp_sec": frame.get("timestamp_sec"),
                "artifact_path": Path(relative).as_posix() if artifact_path else None,
                "change_score": frame.get("change_score"),
                "camera_motion_score": frame.get("camera_motion_score"),
                "measurements": evidence.get("measurements", {}),
                "dominant_colors": evidence.get("dominant_colors", []),
                "subjects": evidence.get("subjects", []), "objects": evidence.get("objects", []),
                "actions_visible": evidence.get("actions_visible", []),
                "camera": evidence.get("camera", {}), "lighting": evidence.get("lighting", {}),
                "ocr": evidence.get("ocr", {}), "continuity_facts": evidence.get("continuity_facts", []),
                "uncertainties": evidence.get("uncertainties", []),
                "confidence": evidence.get("confidence", {}),
            })
        clip_relative = f"embeddings/{scene_id}.mp4" if scene_id else ""
        clip_path = (run_dir / clip_relative).resolve() if clip_relative else None
        try:
            if clip_path is not None:
                clip_path.relative_to(run_dir.resolve())
        except ValueError:
            clip_path = None
        scenes.append({
            "scene_id": scene_id, "start_time_sec": scene.get("start_time_sec"),
            "end_time_sec": scene.get("end_time_sec"), "duration_sec": scene.get("duration_sec"),
            "clip_artifact_path": clip_relative if clip_path is not None and clip_path.is_file() else None,
            "frames": frames,
        })
    return scenes


def _publication_rows(manifest: dict[str, Any], run_dir: Path) -> list[dict[str, Any]]:
    """Choose concrete, run-local clips, selected frames and collected audio."""
    run_id = str(manifest.get("run_id", ""))
    marker = f"/app/runs/{run_id}/"
    outputs: list[dict[str, Any]] = []

    def add(path_value: Any, kind: str, occurrence: str, **metadata: Any) -> None:
        raw = str(path_value or "")
        relative = raw.split(marker, 1)[1] if marker in raw else raw
        path = Path(relative)
        candidate = (run_dir / path).resolve() if relative else None
        if (candidate is None or path.is_absolute() or ".." in path.parts
                or not candidate.is_relative_to(run_dir.resolve()) or not candidate.is_file()):
            return
        occurrence_id = re.sub(r"[^A-Za-z0-9_-]", "_", occurrence)[:160].strip("_")
        if occurrence_id:
            outputs.append({"relative_path": path.as_posix(), "kind": kind,
                "occurrence_id": occurrence_id, **metadata})

    def terms(*values: Any) -> list[str]:
        result: list[str] = []
        for value in values:
            rows = value if isinstance(value, list) else [value]
            for row in rows:
                text = row if isinstance(row, str) else row.get("label") if isinstance(row, dict) else None
                if isinstance(text, str) and text.strip():
                    result.append(text.strip()[:80])
        return list(dict.fromkeys(result))[:40]

    summary = str(manifest.get("internvideo3", {}).get("full_video_summary") or manifest.get("summary") or "")
    for scene in manifest.get("scenes", []):
        scene_id = str(scene.get("scene_id", ""))
        start = scene.get("start_time_sec")
        end = scene.get("end_time_sec")
        label = str(scene.get("summary") or summary or f"Video scene {scene_id}")[:500]
        tags = terms(scene.get("subjects"), scene.get("objects"), scene.get("actions_visible"))
        cuts = scene.get("cuts", [])
        if cuts:
            for cut in cuts:
                add(cut.get("clip_path"), "video", str(cut.get("cut_id", "")),
                    description=label, tags=tags, timestamp_start_seconds=cut.get("start_time_sec"),
                    timestamp_end_seconds=cut.get("end_time_sec"), analyzer_run_id=run_id, scene_id=scene_id, analysis_summary=summary)
        elif not (start == 0 and end and abs(float(end) - float(manifest.get("source", {}).get("duration_sec", -1))) < 0.1):
            add(f"/app/runs/{run_id}/embeddings/{scene_id}.mp4", "video", f"scene_{scene_id}_clip",
                description=label, tags=tags, timestamp_start_seconds=start, timestamp_end_seconds=end,
                analyzer_run_id=run_id, scene_id=scene_id, analysis_summary=summary)
        for frame in scene.get("frames", []):
            evidence = frame.get("evidence", {}) if isinstance(frame.get("evidence"), dict) else {}
            frame_tags = terms(evidence.get("subjects"))
            add(frame.get("path"), "image", f"scene_{scene_id}_frame_{frame.get('frame_id')}",
                description=str(frame.get("summary") or label)[:500], tags=frame_tags[:40],
                timestamp_seconds=frame.get("timestamp_sec"), analyzer_run_id=run_id, scene_id=scene_id,
                frame_id=frame.get("frame_id"))

    for index, item in enumerate(manifest.get("media_collection", {}).get("assets", [])):
        relative = item.get("relative_path") or item.get("path")
        category = str(item.get("category", "")).casefold()
        audio_category = {"voice": "voice", "voices": "voice", "dialogue": "dialogue",
            "sfx": "sfx", "music": "music"}.get(category)
        raw_tags = item.get("tags", [])
        add(relative, "audio", f"audio_{item.get('asset_id') or item.get('id') or index}",
            description=str(item.get("description") or item.get("transcript") or item.get("label") or summary or "Analyzed audio clip")[:500],
            analysis_summary=summary, audio_event_id=item.get("event_id"),
            semantic_text_source="clip" if (item.get("description") or item.get("transcript") or item.get("label")) else "video_summary",
            tags=terms(raw_tags),
            audio_category=audio_category, timestamp_start_seconds=item.get("start_time_sec"),
            timestamp_end_seconds=item.get("end_time_sec"), analyzer_run_id=run_id,
            source_asset_name=item.get("source_asset_name"), isolation_status=item.get("isolation_status"),
            audio_source=item.get("source"))
    return outputs[:1000]


def _materialize_cut_clips(manifest: dict[str, Any], run_dir: Path, source: Path) -> None:
    """Encode sampled cut intervals serially; do not duplicate the full source."""
    duration = float(manifest.get("source", {}).get("duration_sec", 0))
    for scene in manifest.get("scenes", []):
        for cut in scene.get("cuts", []):
            start, end = float(cut["start_time_sec"]), float(cut["end_time_sec"])
            cut_id = str(cut["cut_id"])
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,160}", cut_id) or not 0 <= start < end <= duration + 0.1:
                raise ValueError("Invalid cut interval.")
            if start < 0.1 and abs(end - duration) < 0.1:
                continue
            target = run_dir / "cuts" / f"{cut_id}.mp4"
            target.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-threads", "1",
                "-ss", str(start), "-i", str(source), "-t", str(end-start), "-map", "0:v:0", "-map", "0:a?",
                "-c:v", "libx264", "-preset", "fast", "-threads", "1", "-c:a", "aac", "-movflags", "+faststart",
                str(target)], check=True, capture_output=True, timeout=600)
            cut["clip_path"] = target.relative_to(run_dir).as_posix()
            cut["media_storage"] = "cut_clip"


def run_youtube(job_id: str, request: dict[str, Any]) -> dict[str, Any]:
    urls = request.get("urls", [])
    max_height = int(request.get("max_height", 720))
    if not urls:
        raise ValueError("At least one URL is required")
    if max_height != 720:
        raise ValueError("The current downloader supports the approved 720p preset only")
    outputs = []
    published = []
    failures = []
    for index, item in enumerate(urls, start=1):
        url = item.get("url") if isinstance(item, dict) else str(item)
        event("youtube", job_id, "download", "running", f"Downloading {index} of {len(urls)}", int(5 + 85 * (index - 1) / len(urls)), {"url": url})
        try:
            path, metadata = _download_with_cli(url, store.youtube_downloads_root())
            asset = store.register_asset(
                path, source_mode=request.get("source_mode", "urls"), source_url=url,
                title=str(metadata.get("title", "")), channel=str(metadata.get("channel") or metadata.get("uploader") or ""),
                provenance_notes=str(request.get("provenance_notes", "")), metadata={"extractor": metadata.get("extractor"), "id": metadata.get("id")},
            )
            outputs.append(asset)
            workspace_id = request.get("workspace_id")
            if workspace_id:
                from story_builder.services.media_library import register_downloaded_video
                data_root = Path(os.environ.get("VIBE_DIRECTOR_DATA_DIR", store.PROJECT_ROOT)).resolve()
                published.append(register_downloaded_video(data_root, str(workspace_id), path, {
                    "source_url": url, "repertoire_asset_id": asset["asset_id"],
                    "description": str(asset.get("title") or path.stem)[:2000],
                    "tags": ["youtube", str(asset.get("channel") or "")[:80]],
                    "provenance_notes": str(request.get("provenance_notes", ""))[:2000]}))
        except Exception as exc:
            failures.append({"url": url, "error": str(exc)})
    return {"assets": outputs, "published_assets": published, "failures": failures}


def _download_with_cli(url: str, output_dir: Path) -> tuple[Path, dict[str, Any]]:
    executable = shutil.which("yt-dlp") or shutil.which("yt-dlp_linux")
    if not executable:
        raise RuntimeError("yt-dlp executable is not available")
    output_dir.mkdir(parents=True, exist_ok=True)
    metadata_run = subprocess.run([executable, "--no-playlist", "--dump-single-json", url], check=True, capture_output=True, text=True, timeout=120)
    metadata = json.loads(metadata_run.stdout)
    command = [
        executable, "--no-playlist",
        "-f", "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best[height<=720]/best",
        "--merge-output-format", "mp4", "--print", "after_move:filepath",
        "-o", str(output_dir / "%(title)s.%(ext)s"), url,
    ]
    completed = subprocess.run(command, check=True, capture_output=True, text=True, timeout=7200)
    candidates = [Path(line.strip()) for line in completed.stdout.splitlines() if line.strip()]
    path = next((item for item in reversed(candidates) if item.exists()), None)
    if path is None:
        raise FileNotFoundError("yt-dlp completed without reporting a downloaded file")
    return path, metadata


def _make_clip(source: Path, destination: Path, start: float, end: float) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    duration = max(0.05, end - start)
    copy_command = ["ffmpeg", "-y", "-ss", str(start), "-i", str(source), "-t", str(duration), "-c", "copy", str(destination)]
    result = subprocess.run(copy_command, capture_output=True)
    if result.returncode or not destination.exists() or destination.stat().st_size == 0:
        encode_command = ["ffmpeg", "-y", "-ss", str(start), "-i", str(source), "-t", str(duration), "-c:v", "libx264", "-c:a", "aac", str(destination)]
        subprocess.run(encode_command, check=True, capture_output=True)


def _run_direct_analyzer(job_id: str, assets: list[dict[str, Any]], settings: dict[str, Any], job_dir: Path) -> dict[str, Any]:
    """Run the isolated clip-first analyzer as the primary website analysis path."""
    analyzer_root = store.ANALYZER_ROOT
    launcher = store.PROJECT_ROOT / "scripts" / "video_audio_analyzer" / "run_peav_worker.sh"
    if not launcher.is_file():
        raise FileNotFoundError(f"Direct video/audio analyzer launcher is missing: {launcher}")
    audio_settings = settings.get("audio_analyzer", {}) if isinstance(settings.get("audio_analyzer", {}), dict) else {}
    audio_enabled = bool(settings.get("audio_analyzer_enabled", True))
    fps = float(audio_settings.get("extract_fps", settings.get("extract_fps", 2.0)))
    args_by_setting = (
        ("detect_speech", "--detect-speech"), ("detect_music", "--detect-music"),
        ("detect_sfx", "--detect-sfx"), ("create_audio_embeddings", "--create-audio-embeddings"),
        ("create_av_embeddings", "--create-av-embeddings"), ("diarize_speakers", "--diarize-speakers"),
        ("extract_source_audio", "--extract-source-audio"), ("extract_preview_mp3", "--extract-mp3"),
    )
    videos: list[dict[str, Any]] = []
    audio_runs: list[dict[str, Any]] = []
    published_assets: list[dict[str, Any]] = []
    for index, asset in enumerate(assets, start=1):
        source = store.safe_path(Path(asset["path"]), store.REPERTOIRE_ROOT, store.LEGACY_VIDEO_ROOT, store.youtube_downloads_root())
        event("analysis", job_id, "video_audio_analyzer", "running",
            f"Analyzing video {index} of {len(assets)} with direct-video InternVideo3; audio stages are independently configurable.",
            12 + int(80 * (index - 1) / max(1, len(assets))), {"asset_id": asset["asset_id"], "title": asset.get("title", source.name)})
        args = ["bash", str(launcher), str(source), "--extract-fps", str(fps),
            "--run-demucs", str(audio_settings.get("run_demucs", "AUTO") if audio_enabled else "off"),
            "--frame-change-threshold", str(audio_settings.get("frame_change_threshold", 0.08)),
            "--analyze-frame-evidence",
            "--project-id", str(audio_settings.get("project_id") or asset["asset_id"])]
        args.extend(["--cut-boundary-threshold", str(settings.get("cut_boundary_threshold", 0.18)),
            "--min-cut-seconds", str(settings.get("min_cut_seconds", 0.5))])
        args.append("--extract-cut-clips" if settings.get("extract_cut_clips", True) else "--no-extract-cut-clips")
        for key, flag in args_by_setting:
            enabled = audio_enabled and bool(audio_settings.get(key, True))
            args.append(flag if enabled else "--no-" + flag[2:])
        args.append("--adaptive-sampling" if audio_settings.get("adaptive_sampling", True) else "--no-adaptive-sampling")
        args.append("--preserve-scene-anchors" if audio_settings.get("preserve_scene_anchors", True) else "--no-preserve-scene-anchors")
        if audio_settings.get("keep_intermediate_samples", False):
            args.append("--keep-intermediate-samples")
        for key, flag in (("collect_voice_examples", "--collect-voice-examples"),
            ("collect_music_clips", "--collect-music-clips"), ("collect_sfx_clips", "--collect-sfx-clips")):
            if audio_enabled and audio_settings.get(key, False):
                args.append(flag)
        environment = os.environ.copy()
        environment["VIDEO_AUDIO_ANALYZER_PROJECT_ID"] = str(audio_settings.get("project_id") or asset["asset_id"])
        environment["VIDEO_AUDIO_ANALYZER_JOB_ID"] = job_id
        log_path = job_dir / f"direct-analyzer-{asset['asset_id']}.log"
        with log_path.open("ab") as log_handle:
            completed = subprocess.run(args, cwd=str(store.PROJECT_ROOT), env=environment,
                stdout=log_handle, stderr=subprocess.STDOUT, timeout=24 * 3600, check=False)
        digest = store.sha256_file(source)[:16]
        runs_root = store.analyzer_runs_root()
        candidates = list((runs_root / digest).glob("manifest.json")) if (runs_root / digest).is_dir() else []
        candidates += list(runs_root.glob(f"{digest}-rerun-*/manifest.json"))
        manifest_path = max(candidates, key=lambda path: path.stat().st_mtime) if candidates else None
        if completed.returncode != 0 or manifest_path is None:
            tail = log_path.read_text(encoding="utf-8", errors="replace")[-5000:]
            raise RuntimeError(f"Direct analyzer failed for {source.name} (exit {completed.returncode}); "
                f"manifest={'missing' if manifest_path is None else manifest_path}; log tail:\n{tail}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if str(analyzer_root / "src") not in sys.path:
            sys.path.insert(0, str(analyzer_root / "src"))
        from video_audio_analyzer.codex_director_review import apply_director_overlay
        manifest = apply_director_overlay(manifest, store.REPERTOIRE_ROOT / "indexes" / "director_reviews")
        run_id = str(manifest["run_id"])
        run_dir = store.analyzer_runs_root() / run_id
        _materialize_cut_clips(manifest, run_dir, source)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        from video_audio_analyzer.repertoire import promote_run
        promotion = promote_run(run_dir, store.REPERTOIRE_ROOT,
            str(audio_settings.get("project_id") or asset["asset_id"]), include_standard_media=False, job_id=job_id)
        source_identity = asset.get("metadata", {}) if isinstance(asset.get("metadata"), dict) else {}
        workspace_id = source_identity.get("workspace_id")
        source_asset_id = source_identity.get("source_asset_id")
        source_sha256 = source_identity.get("source_sha256")
        if workspace_id and source_asset_id and source_sha256:
            published_assets.extend(publish_analyzer_outputs(store._CONFIGURED_DATA_ROOT, workspace_id,
                source_asset_id=source_asset_id, source_sha256=source_sha256,
                derivation_id=f"{job_id}_{run_id}", run_dir=run_dir,
                outputs=_publication_rows(manifest, run_dir)))
        analyzer_scenes = _analyzer_visual_scenes(manifest, run_dir)
        direct_scenes = []
        for scene in manifest.get("scenes", []):
            start = float(scene.get("start_time_sec", 0.0) or 0.0)
            end = float(scene.get("end_time_sec", start) or start)
            scene_id = str(scene.get("scene_id", ""))
            relative_clip = f"runs/{run_id}/embeddings/{scene_id}.mp4"
            transcript_segments = [item for item in manifest.get("transcript", {}).get("segments", [])
                if float(item.get("start_time_sec", 0) or 0) < end and float(item.get("end_time_sec", 0) or 0) > start]
            timed_events = [item for item in manifest.get("audio_events", [])
                if float(item.get("start_time_sec", 0) or 0) < end and float(item.get("end_time_sec", 0) or 0) > start]
            transcript_text = " ".join(str(item.get("text", "")).strip() for item in transcript_segments if item.get("text"))
            direct_scenes.append({"scene_id": scene_id, "start_time_sec": start, "end_time_sec": end,
                "start_time_hms": _format_hms(start), "end_time_hms": _format_hms(end),
                "summary": str(scene.get("summary") or ""), "transcript": transcript_text,
                "transcript_segments": transcript_segments, "audio_events": timed_events,
                "cuts": scene.get("cuts", []),
                "clip_path": relative_clip if (run_dir / "embeddings" / f"{scene_id}.mp4").is_file() else None,
                "keyframes": [], "deltas": []})
        summary_text = str(manifest.get("internvideo3", {}).get("full_video_summary") or manifest.get("summary") or "")
        videos.append({"asset_id": asset["asset_id"], "title": asset.get("title") or source.name,
            "summary": {"detailed_video_summary": summary_text, "brief_video_summary": summary_text},
            "scenes": direct_scenes, "summary_model": manifest.get("internvideo3", {}).get("model"),
            "run_id": run_id})
        collection = manifest.get("media_collection", {})
        for collected in collection.get("assets", []):
            stored = str(collected.get("path", "")).replace("\\", "/")
            marker = f"runs/{run_id}/"
            collected["relative_path"] = stored.split(marker, 1)[1] if marker in stored else ""
            collected.pop("path", None)
        audio_runs.append({"asset_id": asset["asset_id"], "status": "completed", "run_id": run_id,
            "summary": summary_text, "summary_model": manifest.get("internvideo3", {}).get("model"),
            "statuses": manifest.get("statuses", {}), "scenes": analyzer_scenes,
            "audio": {"source_audio": "audio/source_audio.mka" if manifest.get("audio", {}).get("source_audio") else None,
                "preview_mp3": "audio/preview.mp3" if manifest.get("audio", {}).get("preview_mp3") else None,
                "analysis_wav": "audio/analysis.wav" if manifest.get("audio", {}).get("analysis_wav") else None},
            "audio_events": manifest.get("audio_events", []), "transcript": manifest.get("transcript", {}),
            "diarization": manifest.get("diarization", {}), "voices": manifest.get("voices", {}), "demucs": manifest.get("demucs", {}),
            "music_features": manifest.get("music_features", {}), "media_collection": collection, "promotion": promotion})
        if job_id not in asset.setdefault("analysis_ids", []):
            asset["analysis_ids"].append(job_id)
            store._atomic_json(store.asset_manifest_path(asset["asset_id"]), asset)
        event("analysis", job_id, "video_audio_analyzer", "completed",
            f"Direct-video summary and {sum(1 for scene in manifest.get('scenes', []) for cut in scene.get('cuts', []) if cut.get('clip_path'))} cut clip(s) are ready.",
            12 + int(80 * index / max(1, len(assets))), {"asset_id": asset["asset_id"], "run_id": run_id,
                "audio_events": len(manifest.get("audio_events", [])), "summary_model": manifest.get("internvideo3", {}).get("model")})
    return {"videos": videos, "audio_analysis": audio_runs, "published_assets": published_assets,
        "errors": [], "skipped_videos": [],
        "primary_backend": "video_audio_analyzer", "summary_model": "InternVideo3"}


def _format_hms(seconds: float) -> str:
    total = max(0, int(seconds))
    return f"{total // 3600:02d}:{(total % 3600) // 60:02d}:{total % 60:02d}"


def _frame_card(frame: Any) -> dict[str, Any]:
    """Compact director-facing frame metadata; verbose analysis remains in artifacts."""
    signals = getattr(frame, "support_signals", {}) or {}
    detections = getattr(frame, "object_detections", []) or []
    return {
        "frame_id": frame.frame_id,
        "timestamp_sec": frame.timestamp_sec,
        "summary": (frame.concise_summary or frame.detailed_description or "")[:500],
        "subjects": [item.label for item in detections],
        "objects": [item.to_dict() for item in detections],
        "action_state": (frame.concise_summary or ""),
        "composition": "",
        "camera": "",
        "lighting": "",
        "palette": frame.dominant_colors,
        "text": frame.ocr_text,
        "reference_uses": ["composition", "subject appearance", "lighting"],
        "replaceable_parts": ["subjects", "background", "style"],
        "confidence": 0.75 if frame.detailed_description else 0.0,
        "uncertainties": frame.warnings,
        "evidence": {"florence_caption": frame.florence_caption, "support_signals": signals},
    }


def run_analysis(job_id: str, request: dict[str, Any]) -> dict[str, Any]:
    settings = request.get("settings", {})
    backend = str(settings.get("analysis_backend") or os.environ.get("VIDEO_REPERTOIRE_ANALYSIS_BACKEND", "video_audio_analyzer"))
    if backend == "video_audio_analyzer":
        assets = [store.get_asset(asset_id) for asset_id in request.get("asset_ids", [])]
        if not assets:
            raise ValueError("Select at least one video asset")
        job_dir = store.job_path("analysis", job_id).parent
        job_dir.mkdir(parents=True, exist_ok=True)
        # Direct analyzer stages launch their own CUDA containers, outside
        # ComfyUI. Share the same cross-process admission lock as every
        # Vibe Director ComfyUI render so an analysis cannot overlap a video,
        # image, or audio generation job and consume the GB10 unified-memory
        # pool at the same time. This is backend-side queueing: no second
        # prompt is placed in ComfyUI's queue while another Vibe Director GPU
        # job owns the lease.
        event("analysis", job_id, "gpu_admission", "waiting",
            "Waiting for the shared GPU slot; analyzer stages will run one at a time.", 10)
        with gpu_workload_guard(comfy_url=os.environ.get("COMFYUI_URL", "http://127.0.0.1:3008"),
                on_safety_trip=lambda _reason: store._stop_analysis_job_containers(job_id)):
            with _GpuMemorySampler() as gpu_sampler:
                result = _run_direct_analyzer(job_id, assets, settings, job_dir)
        result["gpu_usage"] = gpu_sampler.report()
        return result
    if backend != "legacy":
        raise ValueError(f"Unsupported video analysis backend: {backend}")
    from video_scene_summarizer.config.settings import load_settings
    from video_scene_summarizer.graph.workflow import run_analysis_stage

    assets = [store.get_asset(asset_id) for asset_id in request.get("asset_ids", [])]
    if not assets:
        raise ValueError("Select at least one video asset")
    job_dir = store.job_path("analysis", job_id).parent
    input_dir = job_dir / "inputs"
    input_dir.mkdir(parents=True, exist_ok=True)
    filename_to_asset: dict[str, dict[str, Any]] = {}
    for asset in assets:
        source = store.safe_path(Path(asset["path"]), store.REPERTOIRE_ROOT, store.LEGACY_VIDEO_ROOT, store.youtube_downloads_root())
        target = input_dir / f"{asset['asset_id']}_{source.name}"
        if not target.exists():
            try:
                target.symlink_to(source)
            except OSError:
                shutil.copy2(source, target)
        filename_to_asset[target.stem] = asset
    output_root = store.REPERTOIRE_ROOT / "analyses" / job_id
    config = load_settings(store.VIDEO_SUMMARISER_ROOT)
    stage_progress = {"model_setup": 8, "audio_extraction": 16, "transcription": 28, "scene_detection": 40, "scene_preview": 48, "keyframe_analysis": 62, "frame_delta": 70, "scene_analysis": 78, "cross_scene_analysis": 84, "video_summary": 90, "report_writing": 94}

    def callback(item: dict[str, Any]) -> None:
        stage = str(item.get("stage", "analysis"))
        event("analysis", job_id, stage, str(item.get("status", "running")), str(item.get("message", stage)), stage_progress.get(stage, 50), item.get("payload") if isinstance(item.get("payload"), dict) else {})

    with gpu_workload_guard(comfy_url=os.environ.get("COMFYUI_URL", "http://127.0.0.1:3008")):
        result = run_analysis_stage(
            config=config, input_dir=input_dir, output_root=output_root, keep_downloaded_videos=True,
            use_transcript_fusion=bool(settings.get("transcript_fusion", True)), reuse_cache=bool(settings.get("reuse_cache", True)),
            skip_existing=bool(settings.get("skip_existing", False)), use_frame_shaving=bool(settings.get("frame_shaving", False)),
            extract_fps=float(settings.get("extract_fps", config.extract_fps or config.analysis_fps)),
            use_scene_compaction=bool(settings.get("scene_compaction", False)), delete_frame_images=bool(settings.get("delete_frames", False)),
            event_callback=callback,
        )
    videos = []
    visual_detailer_enabled = bool(settings.get("visual_detailer", False))
    for record in result.get("processed_videos", []):
        record_name = Path(record.video_path).name if record.video_path else ""
        matching = next((asset for asset in assets if record_name.startswith(f"{asset['asset_id']}_")), None)
        if matching is None and len(assets) == 1:
            matching = assets[0]
        source = Path(matching["path"]) if matching else Path(record.video_path)
        scenes = []
        for scene in record.metadata.get("_scenes", []):
            clip = store.REPERTOIRE_ROOT / "clips" / (matching["asset_id"] if matching else record.sanitized_name) / f"{job_id}_{scene.scene_id}.mp4"
            try:
                _make_clip(source, clip, scene.start_time_sec, scene.end_time_sec)
                clip_path = str(clip.relative_to(store.REPERTOIRE_ROOT))
            except Exception:
                clip_path = ""
            scene_payload = {
                "scene_id": scene.scene_id, "scene_number": scene.scene_number, "start_time_sec": scene.start_time_sec,
                "end_time_sec": scene.end_time_sec, "start_time_hms": scene.start_time_hms, "end_time_hms": scene.end_time_hms,
                "summary": scene.scene_compiled_text or scene.scene_story_text, "transcript": scene.transcript_text,
                "keywords": scene.keywords, "confidence_notes": scene.confidence_notes, "clip_path": clip_path,
                "action_segment": {"start_time_sec": scene.start_time_sec, "end_time_sec": scene.end_time_sec, "clip_path": clip_path, "label": scene.scene_id},
                "keyframes": [{"frame_id": frame.frame_id, "timestamp_sec": frame.timestamp_sec, "description": frame.detailed_description,
                               "summary": frame.concise_summary, "frame_card": _frame_card(frame), "path": _relative_artifact(Path(frame.frame_path))} for frame in scene.keyframe_analyses],
                "deltas": [delta.to_dict() for delta in scene.frame_deltas],
            }
            if visual_detailer_enabled:
                evidence: list[dict[str, Any]] = []
                for frame in scene.keyframe_analyses:
                    try:
                        from story_builder.services.image_detailer import analyze_image
                        frame_result = analyze_image(Path(frame.frame_path), mode="quick")
                        evidence.append({"frame_id": frame.frame_id, "timestamp_sec": frame.timestamp_sec, "frame_card": frame_result.get("frame_card"), "specialist_evidence": frame_result.get("specialist_evidence", {}), "analysis": frame_result.get("analysis", {})})
                    except Exception as exc:
                        evidence.append({"frame_id": frame.frame_id, "timestamp_sec": frame.timestamp_sec, "error": str(exc)})
                evidence_path = output_root / "visual_evidence" / f"{scene.scene_id}.json"
                evidence_path.parent.mkdir(parents=True, exist_ok=True)
                evidence_path.write_text(json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8")
                scene_payload["visual_evidence_path"] = str(evidence_path.relative_to(store.REPERTOIRE_ROOT))
                scene_payload["visual_evidence"] = evidence
            scenes.append(scene_payload)
        summary = record.metadata.get("_final_summary")
        videos.append({
            "asset_id": matching.get("asset_id") if matching else None, "title": record.title,
            "summary": summary.to_dict() if summary else None, "scenes": scenes,
        })
        if matching:
            matching.setdefault("analysis_ids", [])
            if job_id not in matching["analysis_ids"]:
                matching["analysis_ids"].append(job_id)
                store._atomic_json(store.asset_manifest_path(matching["asset_id"]), matching)
    audio_runs: list[dict[str, Any]] = []
    audio_settings = settings.get("audio_analyzer", {}) if isinstance(settings.get("audio_analyzer", {}), dict) else {}
    if settings.get("audio_analyzer_enabled", False):
        analyzer_root = store.ANALYZER_ROOT
        script = store.PROJECT_ROOT / "scripts" / "video_audio_analyzer" / "run_peav_worker.sh"
        if not script.is_file():
            audio_runs.append({"status": "unavailable", "reason": f"Analyzer launcher is missing: {script}"})
        else:
            for index, asset in enumerate(assets, start=1):
                source = store.safe_path(Path(asset["path"]), store.REPERTOIRE_ROOT, store.LEGACY_VIDEO_ROOT, store.youtube_downloads_root())
                event("analysis", job_id, "audio_video_analyzer", "running",
                    f"Running upgraded audio/semantic analysis for video {index} of {len(assets)}.", 94,
                    {"asset_id": asset["asset_id"], "title": asset.get("title", source.name)})
                args = ["bash", str(script), str(source), "--extract-fps", str(audio_settings.get("extract_fps", settings.get("extract_fps", 4))),
                    "--run-demucs", str(audio_settings.get("run_demucs", "AUTO")),
                    "--frame-change-threshold", str(audio_settings.get("frame_change_threshold", 0.08)),
                    "--cut-boundary-threshold", str(settings.get("cut_boundary_threshold", 0.18)),
                    "--min-cut-seconds", str(settings.get("min_cut_seconds", 0.5)),
                    "--project-id", str(audio_settings.get("project_id") or asset["asset_id"])]
                args.append("--extract-cut-clips" if settings.get("extract_cut_clips", True) else "--no-extract-cut-clips")
                args.append("--adaptive-sampling" if audio_settings.get("adaptive_sampling", True) else "--no-adaptive-sampling")
                args.append("--preserve-scene-anchors" if audio_settings.get("preserve_scene_anchors", True) else "--no-preserve-scene-anchors")
                if audio_settings.get("keep_intermediate_samples", False):
                    args.append("--keep-intermediate-samples")
                for key, flag in (("detect_speech", "--detect-speech"), ("detect_music", "--detect-music"),
                    ("detect_sfx", "--detect-sfx"), ("create_audio_embeddings", "--create-audio-embeddings"),
                    ("create_av_embeddings", "--create-av-embeddings"), ("diarize_speakers", "--diarize-speakers"),
                    ("extract_source_audio", "--extract-source-audio"), ("extract_preview_mp3", "--extract-mp3")):
                    args.append(flag if audio_settings.get(key, True) else "--no-" + flag[2:])
                for key, flag in (("collect_voice_examples", "--collect-voice-examples"),
                    ("collect_music_clips", "--collect-music-clips"), ("collect_sfx_clips", "--collect-sfx-clips")):
                    if audio_settings.get(key, False):
                        args.append(flag)
                log_path = job_dir / f"audio-analyzer-{asset['asset_id']}.log"
                environment = os.environ.copy()
                environment["VIDEO_AUDIO_ANALYZER_PROJECT_ID"] = str(audio_settings.get("project_id") or asset["asset_id"])
                environment["VIDEO_AUDIO_ANALYZER_JOB_ID"] = job_id
                # Use the maintained Vibe launcher with the configured model/source
                # root; it mounts the already-validated source file read-only.
                environment["VIBE_DIRECTOR_VIDEO_ANALYZER_ROOT"] = str(analyzer_root)
                environment["VIDEO_REPERTOIRE_ROOT"] = str(store.REPERTOIRE_ROOT)
                completed = None
                try:
                    with log_path.open("ab") as log_handle:
                        with gpu_workload_guard(comfy_url=os.environ.get("COMFYUI_URL", "http://127.0.0.1:3008"),
                                on_safety_trip=lambda _reason: store._stop_analysis_job_containers(job_id)):
                            completed = subprocess.run(args, cwd=str(store.PROJECT_ROOT.parent), env=environment,
                                stdout=log_handle, stderr=subprocess.STDOUT, timeout=24 * 3600, check=False)
                    digest = store.sha256_file(source)[:16]
                    run_root = store.analyzer_runs_root()
                    manifests = list((run_root / digest).glob("manifest.json")) if (run_root / digest).is_dir() else []
                    manifests += sorted(run_root.glob(f"{digest}-rerun-*/manifest.json"), key=lambda item: item.stat().st_mtime, reverse=True)
                    manifest_path = max(manifests, key=lambda item: item.stat().st_mtime) if manifests else None
                    if completed.returncode != 0 or manifest_path is None:
                        tail = log_path.read_text(encoding="utf-8", errors="replace")[-3000:]
                        audio_runs.append({"asset_id": asset["asset_id"], "status": "failed",
                            "reason": f"Analyzer exited {completed.returncode}; manifest was not produced." if not manifest_path else f"Analyzer exited {completed.returncode}.",
                            "log_tail": tail})
                        continue
                    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                    if str(analyzer_root / "src") not in sys.path:
                        sys.path.insert(0, str(analyzer_root / "src"))
                    from video_audio_analyzer.codex_director_review import apply_director_overlay
                    manifest = apply_director_overlay(manifest, store.REPERTOIRE_ROOT / "indexes" / "director_reviews")
                    run_dir = store.analyzer_runs_root() / str(manifest["run_id"])
                    if not run_dir.is_dir():
                        raise FileNotFoundError(f"Analyzer manifest points to a missing run directory: {run_dir}")
                    analyzer_scenes = _analyzer_visual_scenes(manifest, run_dir)
                    if str(analyzer_root / "src") not in sys.path:
                        sys.path.insert(0, str(analyzer_root / "src"))
                    from video_audio_analyzer.repertoire import promote_run
                    promotion = promote_run(run_dir, store.REPERTOIRE_ROOT,
                        str(audio_settings.get("project_id") or asset["asset_id"]), include_standard_media=False,
                        job_id=job_id)
                    collection = manifest.get("media_collection", {})
                    for collected_asset in collection.get("assets", []):
                        stored = str(collected_asset.get("path", "")).replace("\\", "/")
                        marker = f"runs/{manifest['run_id']}/"
                        collected_asset["relative_path"] = stored.split(marker, 1)[1] if marker in stored else ""
                        collected_asset.pop("path", None)
                    audio_runs.append({"asset_id": asset["asset_id"], "status": "completed", "run_id": manifest["run_id"],
                        "summary": manifest.get("summary"), "statuses": manifest.get("statuses", {}),
                        "scenes": analyzer_scenes,
                        "audio": {"source_audio": "audio/source_audio.mka" if manifest.get("audio", {}).get("source_audio") else None,
                            "preview_mp3": "audio/preview.mp3" if manifest.get("audio", {}).get("preview_mp3") else None,
                            "analysis_wav": "audio/analysis.wav" if manifest.get("audio", {}).get("analysis_wav") else None},
                        "audio_events": manifest.get("audio_events", []), "transcript": manifest.get("transcript", {}),
                        "diarization": manifest.get("diarization", {}), "voices": manifest.get("voices", {}),
                        "music_features": manifest.get("music_features", {}),
                        "media_collection": collection, "promotion": promotion})
                    event("analysis", job_id, "audio_video_analyzer", "completed",
                        f"Upgraded analyzer finished: {len(manifest.get('audio_events', []))} timestamped audio event(s).", 97,
                        {"asset_id": asset["asset_id"], "run_id": manifest["run_id"], "stages": manifest.get("statuses", {})})
                except Exception as exc:
                    audio_runs.append({"asset_id": asset["asset_id"], "status": "failed", "reason": str(exc),
                        "log_path": str(log_path)})
    return {"videos": videos, "audio_analysis": audio_runs, "errors": result.get("errors", []), "skipped_videos": [str(item) for item in result.get("skipped_videos", [])]}


def run_image_detailer(job_id: str, request: dict[str, Any]) -> dict[str, Any]:
    """Analyze one already-indexed Vibe image; keep source bytes in the library."""
    from story_builder.services.media_library import asset_path

    workspace_id = str(request.get("workspace_id", ""))
    asset_id = str(request.get("asset_id", ""))
    mode = str(request.get("mode", "balanced"))
    if mode not in {"quick", "balanced", "deep"}:
        raise ValueError("Image analysis mode must be quick, balanced or deep.")
    source, media_type, filename = asset_path(store._CONFIGURED_DATA_ROOT, workspace_id, asset_id)
    if not media_type.startswith("image/"):
        raise ValueError("The selected shared-library asset is not an image.")
    digest = store.sha256_file(source)
    if digest != request.get("sha256"):
        raise ValueError("The image changed after this analysis job was created; refresh the library and retry.")
    event("image-detailer", job_id, "validating", "running", "Checking the selected image and its library identity.", 10,
        {"workspace_id": workspace_id, "asset_id": asset_id})
    event("image-detailer", job_id, "analyzing", "running", "Running the image analyzer.", 35,
        {"mode": mode, "filename": filename})
    from story_builder.services.image_detailer import analyze_image
    result = analyze_image(source, mode=mode)
    event("image-detailer", job_id, "saving", "running", "Saving analysis with this image's durable job record.", 90)
    return {"workspace_id": workspace_id, "asset_id": asset_id, "filename": filename,
        "sha256": digest, "mode": mode, "analysis": result}


def run_style_frames(job_id: str, request: dict[str, Any]) -> dict[str, Any]:
    from story_builder.services.media_library import extract_style_reference_frames
    workspace_id = str(request.get("workspace_id", ""))
    asset_id = str(request.get("asset_id", ""))
    def report(done: int, total: int) -> None:
        event("style-frames", job_id, "extracting", "running",
            f"Extracted frame {done} of {total}.", int(done * 90 / total), {"completed_frames": done, "total_frames": total})
    frames = extract_style_reference_frames(store._CONFIGURED_DATA_ROOT, workspace_id, asset_id,
        None, request.get("timestamps_seconds"), directing_style_id=str(request.get("directing_style_id", "")),
        progress=report)
    return {"workspace_id": workspace_id, "asset_id": asset_id, "frames": frames}


def run_semantic_index(job_id: str, request: dict[str, Any]) -> dict[str, Any]:
    """Embed one validated library asset in the isolated PE-AV runtime."""
    import math
    import tempfile
    from story_builder.services.media_library import asset_path, save_semantic_content_index

    workspace_id, asset_id = str(request.get("workspace_id", "")), str(request.get("asset_id", ""))
    source, media_type, filename = asset_path(store._CONFIGURED_DATA_ROOT, workspace_id, asset_id)
    modality = "video" if media_type.startswith("video/") else "audio" if media_type.startswith("audio/") else "image" if media_type.startswith("image/") else ""
    if modality not in {"audio", "video", "image"} or modality != request.get("modality"):
        raise ValueError("Semantic content indexing supports image, audio and video library assets.")
    digest = store.sha256_file(source)
    if digest != request.get("sha256"):
        raise ValueError("The asset changed after indexing was queued; refresh the library and retry.")
    model_dir = store.ANALYZER_ROOT / "models" / "pe-av-base"
    source_root = store.ANALYZER_ROOT / "src"
    if not (model_dir / "config.json").is_file() or not (model_dir / "model.safetensors").is_file():
        raise RuntimeError("The PE-AV checkpoint is not installed in the configured analyzer models directory.")
    if not (source_root / "video_audio_analyzer" / "peav_adapter.py").is_file():
        raise RuntimeError("The copied PE-AV adapter is unavailable.")
    suffix = Path(filename).suffix.lower()
    if not re.fullmatch(r"\.[a-z0-9]{1,8}", suffix):
        suffix = ".media"
    temporary_media = tempfile.TemporaryDirectory(prefix="vibe-image-semantic-") if modality == "image" else None
    indexed_source = source
    if modality == "image":
        # PE-AV has a video visual encoder but no still-image input. Repeat the
        # same still into a short silent clip to reuse its visual projection.
        indexed_source = Path(temporary_media.name) / "image.mp4"
        try:
            frame = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-loop", "1", "-framerate", "16", "-i", str(source), "-frames:v", "16",
                "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(indexed_source)],
                capture_output=True, text=True, timeout=60, check=False)
        except Exception:
            temporary_media.cleanup()
            raise
        if frame.returncode != 0 or not indexed_source.is_file():
            temporary_media.cleanup()
            raise RuntimeError((frame.stderr or "Could not prepare the still image for PE-AV visual indexing.")[-2000:])
    container_media = f"/input/asset{'.mp4' if modality == 'image' else suffix}"
    code = (
        "import json,sys; from video_audio_analyzer.peav_adapter import PEAVAdapter; "
        "m,p=sys.argv[1:]; r=PEAVAdapter('/models/pe-av-base').embed(**{m:p}); "
        "k={'audio':'audio_embeds','video':'video_embeds','image':'video_embeds'}[m]; "
        "v=(r.get(k) or [None])[0]; "
        "print(json.dumps({'model':'facebook/pe-av-base','embedding':v})) if v else sys.exit(7)"
    )
    command = ["docker", "run", "--rm", "--gpus", "all", "--network", "none",
        "--label", f"vibe-director.semantic-index-job={job_id}",
        "--user", f"{os.getuid()}:{os.getgid()}", "--entrypoint", "python",
        "-e", "PYTHONPATH=/app/src", "-v", f"{model_dir}:/models/pe-av-base:ro",
        "-v", f"{source_root}:/app/src:ro", "-v", f"{indexed_source}:{container_media}:ro",
        os.environ.get("VIDEO_AUDIO_ANALYZER_PE_AV_IMAGE", "video-audio-analyzer-peav:dev"),
        "-c", code, "video" if modality == "image" else modality, container_media]
    event("semantic-index", job_id, "embedding", "running", "Embedding this library asset with the isolated PE-AV model.", 20,
        {"workspace_id": workspace_id, "asset_id": asset_id, "modality": modality})
    try:
        with gpu_workload_guard(comfy_url=os.environ.get("COMFYUI_URL", "http://127.0.0.1:3008"), timeout_seconds=180,
                on_safety_trip=lambda _reason: store._stop_semantic_index_job_containers(job_id)):
            completed = subprocess.run(command, capture_output=True, text=True,
                timeout=max(60, int(os.environ.get("VIBE_PEAV_CONTENT_INDEX_TIMEOUT", "1800"))), check=False)
    finally:
        if temporary_media is not None:
            temporary_media.cleanup()
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "PE-AV worker failed.")[-2000:]
        raise RuntimeError(detail)
    try:
        payload = json.loads(completed.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError) as exc:
        raise RuntimeError("PE-AV worker did not return a valid embedding response.") from exc
    vector = payload.get("embedding") if isinstance(payload, dict) else None
    if (not isinstance(payload, dict) or payload.get("model") != "facebook/pe-av-base" or type(vector) is not list or not vector
            or any(type(value) not in {int, float} or not math.isfinite(value) for value in vector)):
        raise RuntimeError("PE-AV worker returned an invalid embedding.")
    if store.sha256_file(source) != digest:
        raise RuntimeError("The source asset changed during indexing; its embedding was discarded.")
    saved = save_semantic_content_index(store._CONFIGURED_DATA_ROOT, workspace_id, asset_id,
        source_sha256=digest, modality=modality, model=payload["model"], vector=vector)
    return {"workspace_id": workspace_id, "asset_id": asset_id, "filename": filename,
        "sha256": digest, "modality": modality, "model": payload["model"],
        "dimension": len(vector), "asset": saved}


def run_timed_tts(job_id: str, request: dict[str, Any]) -> dict[str, Any]:
    """Run Story Builder's timed TTS workflow and publish its audio to Vibe."""
    from story_builder.services import audio_catalog, audio_tts
    from story_builder.services.media_library import register_generated_audio

    workspace_id = str(request.get("workspace_id", ""))
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", workspace_id):
        raise ValueError("Invalid workspace ID for timed dialogue audio.")
    srt_content = request.get("srt_content")
    characters = request.get("characters")
    settings = request.get("settings", {})
    if not isinstance(srt_content, str) or len(srt_content) > 500_000:
        raise ValueError("Timed dialogue SRT must be text of at most 500,000 characters.")
    if not isinstance(characters, list) or not isinstance(settings, dict):
        raise ValueError("Timed dialogue requires a character voice map and settings object.")

    rewritten, resolved = audio_tts.prepare_srt(srt_content, characters, audio_catalog.discover_voices())
    job = audio_tts.new_job(settings, resolved, srt_content, rewritten)
    job["job_id"] = job_id
    workflow = audio_tts.build_workflow(rewritten_srt=rewritten, narrator=resolved["narrator"],
        settings=settings, filename_prefix=f"vibe_director/{workspace_id}/{job_id}")
    job_root = store.job_path("timed-tts", job_id).parent

    def update(changes: dict[str, Any]) -> None:
        status = changes.get("status", "running")
        stage = {"running": "rendering", "submitting": "submitting", "completed": "publishing",
            "failed": "failed", "recovery_required": "recovery"}.get(status, "rendering")
        progress = {"running": 12, "submitting": 20, "completed": 90,
            "failed": 99, "recovery_required": 99}.get(status, 30)
        event("timed-tts", job_id, stage, status, str(changes.get("error") or f"Timed dialogue audio: {stage}."), progress)
        safe_changes = {key: value for key, value in changes.items() if key not in {"original_srt", "rewritten_srt"}}
        save_job("timed-tts", job_id, **safe_changes)

    audio_tts.run_timed_job(project_id=workspace_id, project_dir=job_root,
        output_root=store._CONFIGURED_DATA_ROOT / "projects", workspace_output=generated_root(store._CONFIGURED_DATA_ROOT, workspace_id), job=job, workflow=workflow,
        comfy_url=os.environ.get("COMFYUI_URL", "http://127.0.0.1:3008"), update=update)
    if job.get("status") == "recovery_required":
        return {"job_status": "recovery_required", "prompt_id": job.get("prompt_id"),
            "error": job.get("error"), "workspace_id": workspace_id}
    if job.get("status") != "completed":
        raise RuntimeError(str(job.get("error") or "Timed dialogue audio failed."))
    relative_path = f"audio/{job_id}.flac"
    asset = register_generated_audio(store._CONFIGURED_DATA_ROOT, workspace_id, relative_path,
        {"source": "timed_tts", "job_id": job_id, "workflow": "chatterbox_timed_multichar",
         "speakers": resolved.get("used_characters", []), "timing_mode": settings.get("timing_mode", "smart_natural")})
    return {"workspace_id": workspace_id, "asset": asset,
        "reports": job.get("reports", {}), "prompt_id": job.get("prompt_id")}


def _publish_audio_job(job_id: str, request: dict[str, Any], kind: str) -> dict[str, Any]:
    """Run a reused ComfyUI audio workflow and publish its output to Vibe."""
    from story_builder.services import media_library
    from story_builder.services import music_sound, control_foley

    workspace_id = str(request.get("workspace_id", ""))
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", workspace_id):
        raise ValueError("Invalid workspace ID for audio generation.")
    data_root = Path(os.environ.get("VIBE_DIRECTOR_DATA_DIR", store.PROJECT_ROOT)).resolve()
    workspace_root = generated_root(data_root, workspace_id)
    job_dir = store.job_path(kind, job_id).parent
    job_dir.mkdir(parents=True, exist_ok=True)
    output_root = data_root / "projects"
    comfy_url = os.environ.get("COMFYUI_URL", "http://127.0.0.1:3008")
    settings = request.get("settings")
    if not isinstance(settings, dict):
        raise ValueError("Audio generation settings are required.")
    if kind == "ace-music":
        job = music_sound.new_music_job(settings)
        runner = music_sound.run_music_job
        metadata_source = "ace_step_music"
    else:
        job = control_foley.new_job(settings)
        runner = control_foley.run_job
        metadata_source = "control_foley"
        refs = request.get("references", {})
        if not isinstance(refs, dict):
            raise ValueError("Control-Foley references must be an object.")
        def read_asset(asset_id: str, expected_kind: str) -> tuple[str, bytes] | None:
            if not asset_id:
                return None
            source_path, media_type, filename = media_library.asset_path(data_root, workspace_id, asset_id)
            if not media_type.startswith(f"{expected_kind}/"):
                raise ValueError(f"Selected {expected_kind} reference is not a {expected_kind} asset.")
            path = Path(source_path).resolve()
            if not path.is_file():
                raise ValueError("Selected media reference is missing from the workspace library.")
            return filename, path.read_bytes()
        video = read_asset(str(refs.get("video_asset_id") or ""), "video")
        reference_audio = read_asset(str(refs.get("audio_asset_id") or ""), "audio")
        comfy_root = Path(os.environ.get("COMFYUI_ROOT", "/home/riki/web_dev/setup_comfy_and-stuff/ComfyUI")).expanduser().resolve()
        # Use the durable ledger ID for staged inputs and ComfyUI output names.
        job["job_id"] = job_id
        control_foley.stage_inputs(project_dir=workspace_root, comfy_input_dir=comfy_root / "input",
            job=job, video=video, reference_audio=reference_audio)

    job["job_id"] = job_id
    def update(current: dict[str, Any]) -> None:
        status = current.get("status", "running")
        stage = {"running":"rendering", "completed":"publishing", "failed":"failed", "recovery_required":"recovery"}.get(status, "rendering")
        event(kind, job_id, stage, status, str(current.get("error") or f"Audio generation: {stage}."),
            {"running":20,"completed":90,"failed":99,"recovery_required":99}.get(status,35))
        save_job(kind, job_id, status=status, stage=stage,
            message=str(current.get("error") or f"Audio generation: {stage}."),
            progress={"running":20,"completed":90,"failed":99,"recovery_required":99}.get(status,35),
            result={"prompt_id": current.get("prompt_id"), "error": current.get("error")})

    event(kind, job_id, "gpu_admission", "waiting", "Waiting for the shared GPU slot.", 5)
    with gpu_workload_guard(comfy_url=comfy_url):
        runner(job, project_dir=workspace_root, output_root=output_root, workspace_output=workspace_root, comfy_url=comfy_url, progress=update)
    if job.get("status") == "recovery_required":
        return {"job_status":"recovery_required", "prompt_id":job.get("prompt_id"), "error":job.get("error")}
    if job.get("status") != "completed":
        raise RuntimeError(str(job.get("error") or "Audio generation failed."))
    source = Path(job["export_path"]).resolve()
    if not source.is_file():
        raise RuntimeError("Audio workflow completed without an output file.")
    generated_dir = workspace_root / "generated_audio"
    generated_dir.mkdir(parents=True, exist_ok=True)
    target = generated_dir / f"{job_id}{source.suffix.lower()}"
    shutil.copy2(source, target)
    metadata = {"source": metadata_source, "job_id": job_id, "settings": settings,
        "references": request.get("references", {}), "workflow_id": kind,
        "prompt_knowledge_ref": request.get("prompt_knowledge_ref")}
    asset = media_library.register_generated_audio(data_root, workspace_id,
        f"generated_audio/{target.name}", metadata)
    return {"workspace_id":workspace_id, "asset":asset,
        "prompt_id":job.get("prompt_id"), "settings":settings}


def _run_audio_utilities(job_id: str, request: dict[str, Any]) -> dict[str, Any]:
    from story_builder.services import audio_utilities
    workspace_id = str(request.get("workspace_id", ""))
    def update(changes: dict[str, Any]) -> None:
        status = changes.get("status", "running")
        stage = str(changes.get("stage", "processing"))
        message = str(changes.get("message", "Processing audio."))
        event("audio-utilities", job_id, stage, status, message, int(changes.get("progress", 10)))
        save_job("audio-utilities", job_id, status=status, stage=stage,
            message=message, progress=int(changes.get("progress", 10)))
    root = Path(os.environ.get("VIBE_DIRECTOR_DATA_DIR", store.PROJECT_ROOT)).resolve()
    assets = audio_utilities.run_job({"job_id": job_id, "request": request}, data_root=root, progress=update)
    return {"workspace_id": workspace_id, "assets": assets}


def _run_audio_effect(job_id: str, request: dict[str, Any]) -> dict[str, Any]:
    from story_builder.services import audio_effects, media_library
    workspace_id = str(request.get("workspace_id", ""))
    root = Path(os.environ.get("VIBE_DIRECTOR_DATA_DIR", store.PROJECT_ROOT)).resolve()
    workspace_root = generated_root(root, workspace_id)
    source = (workspace_root / str(request.get("source_relative_path", ""))).resolve()
    if not source.is_relative_to(workspace_root.resolve()) or not source.is_file():
        raise ValueError("Audio effect input is missing from this workspace.")
    effect_job = audio_effects.new_effect_job(str(request.get("operation", "")),
        request.get("settings", {}), source)
    effect_job["job_id"] = job_id
    def update(changes: dict[str, Any]) -> None:
        status = str(changes.get("status", "running"))
        stage = {"preparing":"preparing", "submitting":"submitting", "running":"rendering",
            "completed":"publishing", "failed":"failed", "recovery_required":"recovery"}.get(status, "rendering")
        progress = {"preparing":10, "submitting":20, "running":35, "completed":90,
            "failed":99, "recovery_required":99}.get(status, 25)
        message = str(changes.get("error") or f"Audio effect: {stage}.")
        event("audio-effects", job_id, stage, status, message, progress)
        save_job("audio-effects", job_id, status=status, stage=stage, message=message,
            progress=progress, result={"prompt_id":changes.get("prompt_id"),"error":changes.get("error")})
    event("audio-effects", job_id, "gpu_admission", "waiting", "Waiting for the shared GPU slot.", 5)
    comfy_root = Path(os.environ.get("COMFYUI_ROOT", "/home/riki/web_dev/setup_comfy_and-stuff/ComfyUI")).expanduser().resolve()
    try:
        audio_effects.run_effect_job(project_id=workspace_id, project_dir=workspace_root,
            output_root=root / "projects", workspace_output=root / "audio_studio/voice_changes" / job_id, comfy_input_dir=comfy_root / "input",
            comfy_url=os.environ.get("COMFYUI_URL", "http://127.0.0.1:3008"),
            job=effect_job, source=source, update=update)
    finally:
        if effect_job.get("status") != "recovery_required":
            source.unlink(missing_ok=True)
    if effect_job.get("status") == "recovery_required":
        return {"job_status":"recovery_required", "error":effect_job.get("error"), "prompt_id":effect_job.get("prompt_id")}
    if effect_job.get("status") != "completed":
        raise RuntimeError(str(effect_job.get("error") or "Audio effect failed."))
    output = Path(effect_job["export_path"])
    relative = output.relative_to(root / "audio_studio").as_posix()
    asset = media_library.register_generated_audio(root, workspace_id,
        relative, {"source":"audio_effect", "operation":request["operation"],
            "job_id":job_id, "source_asset_id":request["asset_id"], "settings":request["settings"],
            "source_info":effect_job.get("source_info"), "workflow_id":request["operation"]},
        storage_location={"store":"audio", "path":relative})
    return {"workspace_id":workspace_id, "asset":asset, "prompt_id":effect_job.get("prompt_id"),
        "operation":request["operation"], "source_info":effect_job.get("source_info")}


def _run_audio_scene_split(job_id: str, request: dict[str, Any]) -> dict[str, Any]:
    from story_builder.services import audio_scene, media_library
    workspace_id = str(request.get("workspace_id", ""))
    root = Path(os.environ.get("VIBE_DIRECTOR_DATA_DIR", store.PROJECT_ROOT)).resolve()
    workspace_root = generated_root(root, workspace_id)
    source = audio_scene.safe_project_path(workspace_root, str(request.get("source_relative_path", "")))
    job = {"job_id": job_id}

    def update(changes: dict[str, Any]) -> None:
        status = str(changes.get("status", "running"))
        stage = str(changes.get("stage", "splitting"))
        progress = int(changes.get("progress", 25))
        message = str(changes.get("error") or ("Split audio into editable scene clips." if status == "running" else "Audio split completed."))
        event("audio-scene-split", job_id, stage, status, message, progress)
        current = store.read_job("audio-scene-split", job_id)
        result = dict(current.get("result") or {})
        result.update({key: changes[key] for key in ("manifest", "manifest_path", "enriched_path") if key in changes})
        save_job("audio-scene-split", job_id, status=status, stage=stage, message=message,
            progress=progress, error=changes.get("error"), result=result or None)

    audio_scene.run_split(job=job, project_dir=workspace_root, source=source,
        edits=request["edits"], transcript=request.get("transcript"), update=update)
    current = store.read_job("audio-scene-split", job_id)
    if current.get("status") != "completed":
        raise RuntimeError(str(current.get("error") or "Audio scene split failed."))
    published = []
    for clip in (current.get("result") or {}).get("manifest", {}).get("clips", []):
        relative = str(clip.get("relative_path", ""))
        asset = media_library.register_generated_audio(root, workspace_id, relative, {
            "source": "audio_scene_split", "job_id": job_id,
            "source_asset_id": request["asset_id"], "clip_index": clip.get("clip_index"),
            "start": clip.get("start"), "end": clip.get("end"), "transcript": clip.get("text", "")})
        published.append({"clip_index": clip.get("clip_index"), "asset": asset})
    staged_source = request.get("source_relative_path")
    if staged_source:
        audio_scene.safe_project_path(workspace_root, str(staged_source)).unlink(missing_ok=True)
    return {"workspace_id": workspace_id, "source_asset_id": request["asset_id"],
        "manifest": (current.get("result") or {}).get("manifest"), "clips": published}


def _run_audio_scene_stitch(job_id: str, request: dict[str, Any]) -> dict[str, Any]:
    from story_builder.services import audio_scene, media_library
    workspace_id = str(request.get("workspace_id", ""))
    root = Path(os.environ.get("VIBE_DIRECTOR_DATA_DIR", store.PROJECT_ROOT)).resolve()
    workspace_root = generated_root(root, workspace_id)
    split_job = store.read_job("audio-scene-split", str(request["split_job_id"]))
    split_result = split_job.get("result") or {}
    split_record = {"job_id":split_job["job_id"], "manifest":split_result.get("manifest")}
    replacements = {int(index):audio_scene.safe_project_path(workspace_root, relative)
        for index, relative in request.get("replacement_paths", {}).items()}

    def update(changes: dict[str, Any]) -> None:
        status = str(changes.get("status", "running"))
        stage = str(changes.get("stage", "stitching"))
        progress = int(changes.get("progress", 25))
        message = str(changes.get("error") or "Stitching scene clips.")
        event("audio-scene-stitch", job_id, stage, status, message, progress)
        current = store.read_job("audio-scene-stitch", job_id)
        detail = dict(current.get("result") or {})
        detail.update({key:changes[key] for key in ("output_path", "provenance") if key in changes})
        save_job("audio-scene-stitch", job_id, status=status, stage=stage, message=message,
            progress=progress, error=changes.get("error"), result=detail or None)

    audio_scene.run_stitch(job={"job_id":job_id}, project_dir=workspace_root, split_job=split_record,
        replacements=replacements, gaps=request.get("gaps", {}), mode=request["mode"], update=update)
    current = store.read_job("audio-scene-stitch", job_id)
    if current.get("status") != "completed":
        raise RuntimeError(str(current.get("error") or "Audio scene stitch failed."))
    relative = str((current.get("result") or {})["output_path"])
    asset = media_library.register_generated_audio(root, workspace_id, relative,
        {"source":"audio_scene_stitch", "job_id":job_id, "split_job_id":request["split_job_id"],
         "mode":request["mode"], "provenance":(current.get("result") or {}).get("provenance", [])})
    for staged_relative in request.get("replacement_paths", {}).values():
        audio_scene.safe_project_path(workspace_root, str(staged_relative)).unlink(missing_ok=True)
    return {"workspace_id":workspace_id, "split_job_id":request["split_job_id"],
        "output_path":relative, "asset":asset, "provenance":(current.get("result") or {}).get("provenance", [])}


def _run_f5_prepare(job_id: str, request: dict[str, Any]) -> dict[str, Any]:
    from story_builder.services import audio_finetune, media_library

    data_root = Path(os.environ.get("VIBE_DIRECTOR_DATA_DIR", store.PROJECT_ROOT)).resolve()
    workspace_id = str(request["workspace_id"])
    workspace_root = generated_root(data_root, workspace_id)
    uploads = []
    for sample in request["samples"]:
        path, media_type, filename = media_library.asset_path(data_root, workspace_id, sample["asset_id"])
        if not media_type.startswith("audio/") or filename != sample["filename"]:
            raise ValueError("A selected source is no longer a matching workspace audio asset.")
        uploads.append((filename, path.read_bytes()))
    manifest = audio_finetune.stage_dataset(project_dir=workspace_root,
        dataset_name=request["dataset_name"], model=request["base_model"],
        metadata=audio_finetune.build_metadata(request["samples"]), uploads=uploads)

    def update(changes: dict[str, Any]) -> None:
        status = str(changes.get("status", "running"))
        stage = str(changes.get("stage", status))
        progress = int(changes.get("progress", 30 if status == "running" else 100))
        message = str(changes.get("error") or ("Preparing F5 dataset artifacts." if status == "running" else "F5 dataset preparation finished."))
        event("f5-prepare", job_id, stage, status, message, progress)
        result = {key: changes[key] for key in ("artifacts", "command_preview", "command_blockers") if key in changes}
        result["manifest"] = {key: manifest[key] for key in ("dataset_name", "base_model", "sample_count", "total_duration", "sample_rates", "samples")}
        save_job("f5-prepare", job_id, status=status, stage=stage, message=message,
            progress=progress, error=changes.get("error"), result=result,
            completed_at=changes.get("completed_at"))

    preparation_job = {"dataset_name": request["dataset_name"], "base_model": request["base_model"]}
    audio_finetune.prepare_dataset(project_dir=workspace_root, job=preparation_job, update=update)
    current = store.read_job("f5-prepare", job_id)
    if current.get("status") != "completed":
        raise RuntimeError(str(current.get("error") or "F5 dataset preparation failed."))
    return {"workspace_id": workspace_id, "dataset_name": request["dataset_name"],
        "manifest": current.get("result", {}).get("manifest"),
        "artifacts": current.get("result", {}).get("artifacts"),
        "command_preview": current.get("result", {}).get("command_preview"),
        "command_blockers": current.get("result", {}).get("command_blockers", []),
        "training_enabled": False}


def _relative_artifact(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(store.REPERTOIRE_ROOT.resolve()))
    except ValueError:
        return ""


def publish_completed_result(kind, job_id, job, result):
    from .output_destinations import finalize
    save_job(kind, job_id, stage="publishing", message="Saving completed output.",
             result=result, publication_pending=True)
    result = finalize(store._CONFIGURED_DATA_ROOT, job, result)
    save_job(kind, job_id, status="completed", stage="completed", message="Job completed.",
             progress=100, result=result, error=None, publication_pending=False)


def main() -> int:
    if len(sys.argv) != 3:
        return 2
    kind, job_id = sys.argv[1:]
    def cancel_worker(_signum: int, _frame: Any) -> None:
        raise KeyboardInterrupt("Job cancelled")
    signal.signal(signal.SIGTERM, cancel_worker)
    try:
        job = store.read_job(kind, job_id)
        if job.get("status") in {"cancelled", "cancel_requested"}:
            return 130
        if job.get("publication_pending") and isinstance(job.get("result"), dict):
            # Retry only the saved publication; never repeat completed GPU/provider work.
            publish_completed_result(kind, job_id, job, job["result"])
            return 0
        save_job(kind, job_id, stage="waiting", message="Waiting for a workload slot.")
        with (nullcontext() if kind in {"ace-studio", "music-jukebox", "continuity-frame", "agent-computer", "agent-transcription"} else gpu_workload_lock()):
            current = store.read_job(kind, job_id)
            if current.get("status") in {"cancelled", "cancel_requested"}:
                return 130
            started = save_job(kind, job_id, status="running", stage="running", message="Worker is running.")
            if started.get("status") in {"cancelled", "cancel_requested"}:
                return 130
            if kind == 'music-jukebox':
                from .music_jukebox import encode
                result = encode(store._CONFIGURED_DATA_ROOT,job_id,job['request'])
            elif kind == 'voice-studio':
                from .voice_studio import run
                result = run(store._CONFIGURED_DATA_ROOT,job_id,job['request'],lambda stage,message,progress:event(kind,job_id,stage,'running',message,progress))
            elif kind == 'trellis':
                from .trellis_studio import run_job
                result = run_job(store._CONFIGURED_DATA_ROOT, job_id, job['request'],
                    lambda stage,message,progress: event(kind,job_id,stage,'running',message,progress))
            elif kind == "ace-studio":
                from .ace_studio import run_job
                result = run_job(Path(os.environ.get("VIBE_DIRECTOR_DATA_DIR", store.PROJECT_ROOT)).resolve(), job_id, job["request"],
                    lambda stage, message, progress: event(kind, job_id, stage, "running", message, progress))
            elif kind == "vibe-editor":
                from .vibe_editor import run_job
                result = run_job(Path(os.environ.get("VIBE_DIRECTOR_DATA_DIR", store.PROJECT_ROOT)).resolve(), job_id, job["request"],
                    lambda stage, message, progress: event(kind, job_id, stage, "running", message, progress))
            elif kind == "youtube":
                result = run_youtube(job_id, job["request"])
            elif kind == "analysis":
                result = run_analysis(job_id, job["request"])
            elif kind == "semantic-index":
                result = run_semantic_index(job_id, job["request"])
            elif kind == "image-detailer":
                result = run_image_detailer(job_id, job["request"])
            elif kind == "style-frames":
                result = run_style_frames(job_id, job["request"])
            elif kind == "timed-tts":
                result = run_timed_tts(job_id, job["request"])
            elif kind in {"ace-music", "control-foley"}:
                result = _publish_audio_job(job_id, job["request"], kind)
            elif kind == "agent-computer":
                from .agent_computer import run
                result = run(store._CONFIGURED_DATA_ROOT, job_id, job["request"])
            elif kind == "agent-transcription":
                from .agent_transcription import run
                result = run(store._CONFIGURED_DATA_ROOT, job_id, job['request'])
            elif kind == "continuity-frame":
                from .agent_continuity import run
                result = run(store._CONFIGURED_DATA_ROOT, job["request"])
            elif kind == "audio-utilities":
                result = _run_audio_utilities(job_id, job["request"])
            elif kind == "audio-effects":
                result = _run_audio_effect(job_id, job["request"])
            elif kind == "audio-scene-split":
                result = _run_audio_scene_split(job_id, job["request"])
            elif kind == "audio-scene-stitch":
                result = _run_audio_scene_stitch(job_id, job["request"])
            elif kind == "f5-prepare":
                result = _run_f5_prepare(job_id, job["request"])
            else:
                raise ValueError(f"Unsupported video repertoire job kind: {kind}")
        if result.get("job_status") == "cancelled":
            save_job(kind,job_id,status="cancelled",stage="cancelled",message="Stopped after the current object.",result=result)
            return 0
        if result.get("job_status") == "recovery_required":
            save_job(kind, job_id, status="recovery_required", stage="recovery",
                message="The rendering backend may still be processing this request. Reconcile it before retrying.",
                result=result, error=result.get("error"))
            return 0
        publish_completed_result(kind, job_id, job, result)
        return 0
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        save_job(kind, job_id, status="failed", stage="failed", message=str(exc), error=f"{exc}\n{traceback.format_exc()}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
