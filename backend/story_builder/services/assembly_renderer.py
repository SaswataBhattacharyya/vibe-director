"""Render a frozen assembly manifest to a new MP4 without modifying inputs."""
from __future__ import annotations
from story_builder.services.storage_paths import generated_root

from story_builder.services.media_jobs import gpu_workload_lock

import hashlib
import json
import math
import os
import selectors
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

from story_builder.services.assembly import validate_export_settings
from story_builder.services.media_library import asset_path, list_assets


class AssemblyRenderError(RuntimeError):
    pass


def _verified_asset(root: Path, workspace_id: str, asset_id: str, expected_hash: str,
                    expected_kind: str) -> Path:
    path, _media_type, _filename = asset_path(root, workspace_id, asset_id)
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    if digest.hexdigest() != expected_hash:
        raise AssemblyRenderError(f"Source asset {asset_id} changed after the assembly was frozen.")
    offset = 0
    found = False
    while True:
        page = list_assets(root, workspace_id, kind=expected_kind, limit=100, offset=offset)
        if any(row.get("asset_id") == asset_id and row.get("sha256") == expected_hash for row in page["assets"]):
            found = True
            break
        offset += len(page["assets"])
        if offset >= page["total"] or not page["assets"]:
            break
    if not found:
        raise AssemblyRenderError(f"Source asset {asset_id} is not a {expected_kind} asset in this workspace.")
    return path


@gpu_workload_lock()
def render_manifest(root: Path, workspace_id: str, manifest_record: dict[str, Any],
                    output_path: Path, *, progress: Callable[[int], None] | None = None,
                    run: Callable[..., Any] = subprocess.run,
                    popen: Callable[..., Any] = subprocess.Popen) -> dict[str, Any]:
    """Normalize/concatenate frozen clips and explicitly selected audio tracks.

    Source files are resolved inside the workspace and re-hashed immediately
    before use. Rendering writes a temporary sibling and atomically replaces
    only the requested new output path after FFmpeg succeeds.
    """
    manifest = manifest_record.get("manifest")
    if (not isinstance(manifest, dict) or manifest.get("state") != "ready_for_render"
            or not isinstance(manifest.get("clips"), list) or not manifest["clips"]):
        raise AssemblyRenderError("A complete ready_for_render manifest is required.")
    try:
        settings = validate_export_settings(manifest.get("export_settings"))
    except ValueError as exc:
        raise AssemblyRenderError(f"Export settings are invalid: {exc}") from exc
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        raise AssemblyRenderError("FFmpeg and ffprobe must be installed to render an assembly.")
    dimensions = {"720p": (1280, 720), "1080p": (1920, 1080), "1440p": (2560, 1440)}
    resolution = settings.get("resolution")
    fps, crf = settings.get("frame_rate"), settings.get("quality")
    if resolution not in dimensions or type(fps) is not int or type(crf) is not int:
        raise AssemblyRenderError("The manifest has unsupported render settings.")
    policy = settings.get("audio_policy")
    if policy not in {"preserve_and_mix", "selected_tracks_only", "mute"}:
        raise AssemblyRenderError("The manifest has an unsupported audio policy.")

    clips: list[dict[str, Any]] = manifest["clips"]
    sources: list[Path] = []
    durations: list[float] = []
    clip_audio: list[bool] = []
    for clip in clips:
        outputs = clip.get("outputs") if isinstance(clip, dict) else None
        output = next((item for item in outputs or [] if isinstance(item, dict)
                       and item.get("kind") == "video"), None)
        if output is None:
            raise AssemblyRenderError("Every frozen clip must contain a video output.")
        asset_id = output.get("shared_asset_id") or output.get("asset_id")
        digest, duration = output.get("sha256"), output.get("duration_seconds")
        if (not isinstance(asset_id, str) or not isinstance(digest, str) or len(digest) != 64
                or type(duration) not in (int, float) or not math.isfinite(duration) or duration <= 0):
            raise AssemblyRenderError("A frozen clip has invalid asset identity or duration.")
        sources.append(_verified_asset(root, workspace_id, asset_id, digest, "video"))
        durations.append(float(duration))
        clip_audio.append(output.get("has_audio") is True)

    tracks = manifest.get("audio_tracks", [])
    if not isinstance(tracks, list) or len(tracks) > 20:
        raise AssemblyRenderError("The manifest has an invalid audio-track list.")
    audio_inputs: list[tuple[Path, dict[str, Any]]] = []
    if policy != "mute":
        if policy == "preserve_and_mix":
            audio_inputs.extend((path, {"clip_index": index}) for index, (path, has_audio) in
                enumerate(zip(sources, clip_audio)) if has_audio)
        for track in tracks:
            if not isinstance(track, dict):
                raise AssemblyRenderError("An optional audio track is malformed.")
            path = _verified_asset(root, workspace_id, track.get("asset_id", ""),
                track.get("sha256", ""), "audio")
            try:
                start = float(track["start_seconds"])
                trim_start, trim_end = float(track["trim_start_seconds"]), float(track["trim_end_seconds"])
                gain = float(track["gain"])
            except (KeyError, TypeError, ValueError) as exc:
                raise AssemblyRenderError("An optional audio track has invalid timing or gain.") from exc
            if (not all(math.isfinite(value) for value in (start, trim_start, trim_end, gain))
                    or start < 0 or trim_start < 0 or trim_end <= trim_start or gain < 0 or gain > 2):
                raise AssemblyRenderError("An optional audio track has invalid timing or gain.")
            audio_inputs.append((path, {"start_seconds": start, "trim_start_seconds": trim_start,
                "trim_end_seconds": trim_end, "gain": gain}))

    width, height = dimensions[resolution]
    total_duration = sum(durations)
    input_args = []
    for path in sources:
        input_args.extend(["-i", str(path)])
    for path, track in audio_inputs:
        if "clip_index" not in track:
            input_args.extend(["-i", str(path)])

    filters = []
    video_labels = []
    for index in range(len(sources)):
        label = f"v{index}"
        filters.append(f"[{index}:v:0]scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,fps={fps},setsar=1,format=yuv420p,"
            f"setpts=PTS-STARTPTS[{label}]")
        video_labels.append(f"[{label}]")
    filters.append("".join(video_labels) + f"concat=n={len(sources)}:v=1:a=0[outv]")
    audio_labels = []
    audio_input_index = len(sources)
    for _path, track in audio_inputs:
        label = f"a{len(audio_labels)}"
        if "clip_index" in track:
            index = track["clip_index"]
            delay_ms = round(sum(durations[:index]) * 1000)
            filters.append(f"[{index}:a:0]aresample=48000,aformat=channel_layouts=stereo,"
                f"atrim=duration={durations[index]:.6f},asetpts=PTS-STARTPTS,"
                f"adelay={delay_ms}|{delay_ms}[{label}]")
        else:
            delay_ms = round(track["start_seconds"] * 1000)
            filters.append(f"[{audio_input_index}:a:0]atrim=start={track['trim_start_seconds']:.6f}:"
                f"end={track['trim_end_seconds']:.6f},asetpts=PTS-STARTPTS,"
                f"aresample=48000,aformat=channel_layouts=stereo,volume={track['gain']:.6f},"
                f"adelay={delay_ms}|{delay_ms}[{label}]")
            audio_input_index += 1
        audio_labels.append(f"[{label}]")
    if audio_labels:
        filters.append("".join(audio_labels) + f"amix=inputs={len(audio_labels)}:duration=longest:dropout_transition=0,"
            f"atrim=duration={total_duration:.6f},alimiter=limit=0.95[aout]")

    workspace_assets = generated_root(Path(root).resolve(), workspace_id)
    output_root = workspace_assets / "exports"
    candidate = Path(output_path).absolute()
    try:
        candidate.relative_to(output_root)
    except ValueError as exc:
        raise AssemblyRenderError("The export output path must stay inside this workspace's exports folder.") from exc
    for parent in (candidate, *candidate.parents):
        if parent.is_symlink():
            raise AssemblyRenderError("The workspace export path cannot contain symlinks.")
        if parent == workspace_assets.parent:
            break
    output_root = output_root.resolve()
    output_path = candidate.resolve()
    if not output_path.is_relative_to(output_root) or output_path.suffix.lower() != ".mp4":
        raise AssemblyRenderError("The export output path must stay inside this workspace's exports folder.")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_name(f".{output_path.stem}.rendering.mp4")
    temporary.unlink(missing_ok=True)
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostats", "-progress", "pipe:1", "-y", *input_args,
        "-filter_complex", ";".join(filters), "-map", "[outv]"]
    if audio_labels:
        command.extend(["-map", "[aout]", "-c:a", "aac", "-b:a", "192k"])
    else:
        command.append("-an")
    command.extend(["-c:v", "libx264", "-preset", "medium", "-crf", str(crf),
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(temporary)])
    try:
        last_progress = -1
        with tempfile.TemporaryFile(mode="w+t") as stderr_file:
            process = popen(command, stdout=subprocess.PIPE, stderr=stderr_file,
                bufsize=0)
            assert process.stdout is not None
            deadline = time.monotonic() + 6 * 60 * 60
            pending = b""
            selector = selectors.DefaultSelector()
            selector.register(process.stdout, selectors.EVENT_READ)
            try:
                while selector.get_map():
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        process.kill()
                        raise AssemblyRenderError("FFmpeg render exceeded the six-hour time limit.")
                    events = selector.select(min(1.0, remaining))
                    if not events and process.poll() is not None:
                        # Drain EOF so the final progress block is parsed before exit.
                        chunk = os.read(process.stdout.fileno(), 8192)
                        if not chunk:
                            selector.unregister(process.stdout)
                            break
                    else:
                        chunk = os.read(process.stdout.fileno(), 8192) if events else b""
                        if events and not chunk:
                            selector.unregister(process.stdout)
                            break
                    pending += chunk
                    while b"\n" in pending:
                        raw_line, pending = pending.split(b"\n", 1)
                        key, separator, value = raw_line.decode("utf-8", "replace").strip().partition("=")
                        if not separator or key != "out_time_us" or progress is None:
                            continue
                        try:
                            elapsed = max(0, int(value)) / 1_000_000
                        except ValueError:
                            continue
                        current = max(0, min(99, int(elapsed / total_duration * 100)))
                        if current > last_progress:
                            last_progress = current
                            progress(current)
                if pending and progress is not None:
                    key, separator, value = pending.decode("utf-8", "replace").strip().partition("=")
                    if separator and key == "out_time_us":
                        try:
                            current = max(0, min(99, int(max(0, int(value)) / 1_000_000 / total_duration * 100)))
                        except ValueError:
                            current = last_progress
                        if current > last_progress:
                            progress(current)
                return_code = process.wait(timeout=max(0.1, deadline - time.monotonic()))
            finally:
                selector.close()
                process.stdout.close()
                if process.poll() is None:
                    process.kill()
                    process.wait()
            stderr_file.seek(0)
            stderr_text = stderr_file.read()
        if return_code != 0:
            raise AssemblyRenderError((stderr_text or "FFmpeg render failed.")[-2000:])
        if not temporary.is_file() or temporary.stat().st_size == 0:
            raise AssemblyRenderError("FFmpeg did not produce a playable output file.")
        probe_result = run(["ffprobe", "-v", "error", "-show_format", "-show_streams",
            "-of", "json", str(temporary)], capture_output=True, text=True, timeout=60, check=False)
        if probe_result.returncode != 0:
            raise AssemblyRenderError("The rendered output could not be verified by ffprobe.")
        probe = json.loads(probe_result.stdout)
        if not any(stream.get("codec_type") == "video" for stream in probe.get("streams", [])):
            raise AssemblyRenderError("The output has no video stream.")
        temporary.replace(output_path)
        if progress:
            progress(100)
        return {"path": str(output_path), "probe": probe,
            "size_bytes": output_path.stat().st_size, "manifest_id": manifest_record.get("manifest_id")}
    finally:
        temporary.unlink(missing_ok=True)
