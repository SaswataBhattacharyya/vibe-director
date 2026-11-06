"""Vibe adapter for Story Builder's deterministic audio utility operations."""
from __future__ import annotations
from story_builder.services.storage_paths import generated_root, checked

import os
import re
import json
import uuid
import shutil
import subprocess
import threading
import textwrap
from contextlib import nullcontext
from pathlib import Path
from typing import Any, Callable

from story_builder.services import media_library
from story_builder.services.media_jobs import gpu_workload_guard, MediaJobError

AUDIO_EXTS = {".wav", ".flac", ".mp3", ".ogg", ".m4a", ".aac"}
VIDEO_EXTS = {".mp4", ".mkv", ".webm", ".mov", ".avi"}
OPERATIONS = {"noise_cleanup", "extract_mp3", "demucs_stems"}
SETTING_KEYS = {"extract_mp3": {"quality"}, "noise_cleanup": {"model", "dry"},
    "demucs_stems": {"stems", "device"}}


class AudioUtilityError(ValueError):
    pass


def validate_settings(operation: str, settings: dict[str, Any]) -> None:
    if operation not in OPERATIONS or not isinstance(settings, dict):
        raise AudioUtilityError("Unknown operation or invalid settings.")
    if set(settings) - SETTING_KEYS[operation]:
        raise AudioUtilityError("Settings contain unsupported fields for this operation.")
    if operation == "extract_mp3":
        quality = settings.get("quality", 2)
        if type(quality) is not int or not 0 <= quality <= 9:
            raise AudioUtilityError("MP3 quality must be an integer between 0 and 9.")
    elif operation == "noise_cleanup":
        if settings.get("model", "master64") not in {"master64", "dns64"}:
            raise AudioUtilityError("Unknown denoiser model.")
        dry = settings.get("dry", 0)
        if type(dry) not in {int, float} or not 0 <= dry <= 1:
            raise AudioUtilityError("Dry mix must be between 0 and 1.")
    else:
        stems = settings.get("stems", 2)
        if type(stems) is not int or stems not in {2, 4, 6}:
            raise AudioUtilityError("Demucs stems must be 2, 4, or 6.")
        if settings.get("device", "cuda") not in {"cuda", "cpu"}:
            raise AudioUtilityError("Demucs device must be CUDA or CPU.")


def _run(command: list[str], timeout: int = 3600) -> None:
    result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout or "Audio utility failed")[-3000:])


def _stop_owned_container_process(container: str, work_root: str) -> None:
    script = textwrap.dedent("""\
        import os,signal,sys,time
        token=sys.argv[1]; own=os.getpid(); processes={}; parents={}
        def proc_stat(pid):
            tail=open(f'/proc/{pid}/stat').read().rpartition(')')[2].split()
            return tail[0],int(tail[1])
        for name in os.listdir('/proc'):
            try:
                pid=int(name)
                if pid==own: continue
                raw=open(f'/proc/{pid}/cmdline','rb').read().replace(b'\\0',b' ').decode(errors='ignore')
                parent=proc_stat(pid)[1]
                parents[pid]=parent
                if token in raw: processes[pid]=parent
            except (OSError,ValueError,IndexError): pass
        targets=set(processes)
        changed=True
        while changed:
            changed=False
            for pid,parent in parents.items():
                if parent in targets and pid not in targets: targets.add(pid); changed=True
        for pid in targets:
            try: os.kill(pid,signal.SIGTERM)
            except ProcessLookupError: pass
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            alive=[]
            for pid in targets:
                try:
                    state=proc_stat(pid)[0]
                    if state!='Z': alive.append(pid)
                except (OSError,IndexError): pass
            if not alive: break
            time.sleep(.1)
        for pid in alive:
            try: os.kill(pid,signal.SIGKILL)
            except ProcessLookupError: pass
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            alive=[]
            for pid in targets:
                try:
                    if proc_stat(pid)[0]!='Z': alive.append(pid)
                except (OSError,IndexError): pass
            if not alive: break
            time.sleep(.1)
        if alive: raise SystemExit('Could not confirm termination of the job-owned audio process.')
    """)
    result = subprocess.run(["docker", "exec", container, "python", "-c", script, work_root],
        capture_output=True, text=True, timeout=12)
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout or "Audio process termination is unconfirmed.")[-2000:])


def _container_running(name: str) -> bool:
    if not shutil.which("docker"):
        return False
    try:
        result = subprocess.run(["docker", "inspect", "-f", "{{.State.Running}}", name],
            capture_output=True, text=True, timeout=5)
        return result.returncode == 0 and result.stdout.strip() == "true"
    except (OSError, subprocess.SubprocessError):
        return False


def capabilities() -> dict[str, Any]:
    ffmpeg = bool(shutil.which("ffmpeg"))
    denoiser = _container_running("story-audio-denoiser")
    demucs = _container_running("story-audio-demucs")
    return {"operations": [
        {"id": "noise_cleanup", "status": "available" if denoiser else "blocked", "runtime": "story-audio-denoiser", "reason": None if denoiser else "Audio denoiser runtime is not running."},
        {"id": "extract_mp3", "status": "available" if ffmpeg else "blocked", "runtime": "ffmpeg", "reason": None if ffmpeg else "ffmpeg is unavailable."},
        {"id": "demucs_stems", "status": "available" if demucs else "blocked", "runtime": "story-audio-demucs", "reason": None if demucs else "Demucs runtime is not running."},
    ]}


def stage_assets(data_root: Path, workspace_id: str, job_id: str, asset_ids: list[str], operation: str) -> list[dict[str, str]]:
    if operation not in OPERATIONS or not isinstance(asset_ids, list) or not 1 <= len(asset_ids) <= 100:
        raise AudioUtilityError("Select between one and 100 assets for a supported operation.")
    if any(not isinstance(asset_id, str) or not asset_id for asset_id in asset_ids):
        raise AudioUtilityError("Asset IDs must be non-empty strings.")
    allowed = AUDIO_EXTS | VIDEO_EXTS if operation == "extract_mp3" else AUDIO_EXTS
    root = Path(data_root).resolve()
    workspace_root = (generated_root(root, workspace_id)).resolve()
    destination = checked(workspace_root, "utility_inputs", job_id)
    destination.mkdir(parents=True, exist_ok=False)
    try:
        staged = []
        for index, asset_id in enumerate(dict.fromkeys(asset_ids), 1):
            source, media_type, filename = media_library.asset_path(root, workspace_id, asset_id)
            if Path(filename).suffix.lower() not in allowed:
                raise AudioUtilityError(f"{filename} is not supported for {operation}.")
            source = Path(source).resolve()
            if not source.is_file():
                raise AudioUtilityError("A selected shared-library asset is missing.")
            target = destination / f"{index:03d}{Path(filename).suffix.lower()}"
            shutil.copy2(source, target)
            staged.append({"asset_id": asset_id, "filename": Path(filename).name,
                "relative_path": target.relative_to(root).as_posix(), "media_type": media_type})
        return staged
    except BaseException:
        shutil.rmtree(destination, ignore_errors=True)
        raise


class UtilityUnavailable(RuntimeError):
    pass


class WorkerUnavailable(RuntimeError):
    pass


def submit(root: Path, workspace_id: str, payload: dict, *, invocation_id: str | None = None,
           on_created: Callable[[dict], None] | None = None,
           expected_hashes: dict[str, str] | None = None) -> dict:
    """Shared manual/agent seam; a persisted job owns its inputs even if dispatch fails."""
    from . import video_repertoire
    root = Path(root).resolve()
    if root != video_repertoire._CONFIGURED_DATA_ROOT:
        raise AudioUtilityError("Audio job storage is configured for a different data root.")
    if set(payload) != {"operation", "asset_ids", "settings"} or not isinstance(payload.get("settings"), dict):
        raise AudioUtilityError("Supply operation, shared-library asset_ids and settings.")
    operation = payload["operation"]
    selected = next((row for row in capabilities()["operations"] if row["id"] == operation), None)
    if selected is None:
        raise AudioUtilityError("Unknown audio utility operation.")
    if selected["status"] != "available":
        raise UtilityUnavailable(selected.get("reason") or "Audio utility is unavailable.")
    validate_settings(operation, payload["settings"])
    if invocation_id is not None and not re.fullmatch(r'call-[0-9a-f]{32}', invocation_id):
        raise AudioUtilityError('Invalid invocation identity.')
    staging_id = "stage-" + (invocation_id or uuid.uuid4().hex)
    staged = stage_assets(root, workspace_id, staging_id, payload["asset_ids"], operation)
    request = {"workspace_id": workspace_id, "operation": operation,
        "settings": payload["settings"], "inputs": staged, "staging_id": staging_id}
    if invocation_id is not None:
        request["agent_invocation_id"] = invocation_id
    try:
        if expected_hashes is not None:
            from .projects import digest
            if any(digest(root / item['relative_path']) != expected_hashes.get(item['asset_id']) for item in staged):
                raise AudioUtilityError('Staged media changed after approval.')
            for item in staged:
                item['sha256'] = expected_hashes[item['asset_id']]
        job = video_repertoire.create_job("audio-utilities", request)
    except Exception:
        # Creation can acknowledge failure after publication. Inspect raw records without recovery writes.
        try:
            persisted = any(json.loads(path.read_text()).get("request", {}).get("staging_id") == staging_id
                for path in (root / "services/media/jobs/audio-utilities").glob("*/job.json"))
        except (OSError, ValueError, AttributeError, TypeError):
            persisted = True  # Uncertain ownership must retain recoverable inputs.
        if not persisted:
            shutil.rmtree(generated_root(root, workspace_id) / "utility_inputs" / staging_id, ignore_errors=True)
        raise
    if on_created is not None:
        on_created(job)  # Save agent/job identity before dispatch; failures retain the durable job.
    try:
        return video_repertoire.start_job("audio-utilities", job["job_id"])
    except Exception as exc:
        raise WorkerUnavailable(str(exc)) from exc


def run_job(job: dict[str, Any], *, data_root: Path, progress: Callable[[dict[str, Any]], None]) -> list[dict[str, Any]]:
    root = Path(data_root).resolve()
    request = job["request"]
    workspace_id = request["workspace_id"]
    operation = request["operation"]
    settings = request["settings"]
    validate_settings(operation, settings)
    workspace_root = (generated_root(root, workspace_id)).resolve()
    folder = workspace_root / "utility_inputs" / request["staging_id"]
    output = root / "audio_studio/output" / job["job_id"]
    output.mkdir(parents=True, exist_ok=True)
    completed_outputs = []
    inputs = request["inputs"]
    uses_gpu = operation == "noise_cleanup" or (
        operation == "demucs_stems" and settings.get("device", "cuda") == "cuda")
    safety_tripped = threading.Event()
    active = {}
    def stop_owned_workload(_reason: str) -> None:
        safety_tripped.set()
        if active:
            _stop_owned_container_process(active["container"], active["work_root"])
    gpu_slot = (gpu_workload_guard(comfy_url=os.environ.get("COMFYUI_URL", "http://127.0.0.1:3008"),
        on_safety_trip=stop_owned_workload) if uses_gpu else nullcontext())
    # Keep a multi-file GPU utility job in one admission window. Releasing the
    # lease between inputs would let another generator start before this job
    # had finished, contrary to Vibe Director's one-workload-at-a-time rule.
    with gpu_slot:
        for index, item in enumerate(inputs, 1):
            source = (root / item["relative_path"]).resolve()
            if not source.is_file() or not source.is_relative_to(folder.resolve()):
                raise AudioUtilityError("Staged input is missing or outside this job.")
            if request.get('agent_invocation_id') or item.get('sha256'):
                from .projects import digest
                if digest(source) != item.get('sha256'):
                    raise AudioUtilityError('Staged input no longer matches the approved media.')
            progress({"status": "running", "stage": "processing", "progress": round((index - 1) / len(inputs) * 90), "message": f"Processing {index} of {len(inputs)}."})
            target_dir = output / f"{index:03d}-{source.stem}"
            target_dir.mkdir(parents=True, exist_ok=True)
            if operation == "extract_mp3":
                target = target_dir / f"{source.stem}.mp3"
                quality = settings.get("quality", 2)
                _run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(source), "-vn", "-codec:a", "libmp3lame", "-q:a", str(quality), str(target)])
                results = [target]
            else:
                container = "story-audio-denoiser" if operation == "noise_cleanup" else "story-audio-demucs"
                container_root = f"/tmp/vibe-audio-{job['job_id']}-{index}"
                active.update(container=container, work_root=container_root)
                def run_owned(command):
                    if safety_tripped.is_set():
                        raise MediaJobError("GPU safety trip stopped this audio utility job before publication.")
                    _run(command)
                run_owned(["docker", "exec", container, "mkdir", "-p", f"{container_root}/input", f"{container_root}/output"])
                run_owned(["docker", "cp", str(source), f"{container}:{container_root}/input/source{source.suffix}"])
                if operation == "noise_cleanup":
                    model = settings.get("model", "master64")
                    dry = float(settings.get("dry", 0))
                    run_owned(["docker", "exec", container, "python", "-c", "import denoiser_runtime_compat, runpy; runpy.run_module('denoiser.enhance', run_name='__main__')", "--master64" if model == "master64" else "--dns64", "--dry", str(dry), "--num_workers", "1", "--noisy_dir", f"{container_root}/input", "--out_dir", f"{container_root}/output"])
                else:
                    stems = settings.get("stems", 2)
                    device = settings.get("device", "cuda")
                    model = "htdemucs_6s" if stems == 6 else "htdemucs"
                    command = ["docker", "exec", container, "demucs", "-n", model, "-o", f"{container_root}/output", "--device", device]
                    if stems == 2:
                        command += ["--two-stems", "vocals"]
                    run_owned(command + [f"{container_root}/input/source{source.suffix}"])
                run_owned(["docker", "cp", f"{container}:{container_root}/output/.", str(target_dir)])
                results = [path for path in target_dir.rglob("*") if path.is_file() and path.suffix.lower() in AUDIO_EXTS]
                if not results:
                    raise RuntimeError("Audio container completed without an audio output.")
                active.clear()
            for result in results:
                relative = result.relative_to(root / "audio_studio").as_posix()
                completed_outputs.append((relative, item["asset_id"]))
    # The guard can report a safety trip only after the owned command exits.
    # Publish after it succeeds so an unconfirmed workload never becomes a library asset.
    return [media_library.register_generated_audio(root, workspace_id, relative, {
        "source": "audio_utility", "job_id": job["job_id"], "operation": operation,
        "source_asset_id": source_asset_id, "settings": settings}, storage_location={"store": "audio", "path": relative})
        for relative, source_asset_id in completed_outputs]
