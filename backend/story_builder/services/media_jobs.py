"""Generic media job persistence and ComfyUI execution helpers."""

from __future__ import annotations

import json
import logging
import shutil
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import os
import tempfile
import threading
from datetime import datetime, timezone
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable

from story_builder.services.gpu_runtime import (
    DEFAULT_TELEMETRY_PATH, GPUAdmissionError, inspect_gpu_runtime, record_gpu_telemetry,
)


from story_builder.services.gpu_watchdog import ensure_prompt_watchdog, finish_prompt_watchdog


class ComfyMemoryReleasePending(RuntimeError):
    """No GPU submission occurred; keep the durable job queued for handoff."""


class MediaJobError(RuntimeError):
    """Raised when a media job cannot be prepared or executed."""

    def __init__(self, message: str, *, prompt_id: str | None = None,
                 remote_state_unknown: bool = False):
        super().__init__(message)
        self.prompt_id = prompt_id
        self.remote_state_unknown = remote_state_unknown


_GPU_WORKLOAD_LOCK_STATE = threading.local()
LOGGER = logging.getLogger(__name__)


def _workload_lock_path() -> Path:
    return Path(os.environ.get("VIBE_DIRECTOR_GPU_WORKLOAD_LOCK") or
                os.environ.get("STORY_BUILDER_COMFY_SUBMISSION_LOCK") or
                (Path(tempfile.gettempdir()) / "story-builder-comfy-submission.lock"))


def _workload_policy_path() -> Path:
    return Path(os.environ.get("VIBE_DIRECTOR_WORKLOAD_POLICY_PATH") or
                (Path(__file__).resolve().parents[3] / "local_data" / "storage" / "workload-policy.json"))


def _gpu_safety_hold_path() -> Path:
    return Path(os.environ.get("VIBE_DIRECTOR_GPU_SAFETY_HOLD_PATH") or
                (Path(__file__).resolve().parents[3] / "local_data" / "storage" / "gpu-safety-hold.json"))


def get_gpu_safety_hold() -> dict[str, Any]:
    """Return the durable admission hold left by an unconfirmed safety stop."""
    target = _gpu_safety_hold_path()
    try:
        value = json.loads(target.read_text(encoding="utf-8"))
        if isinstance(value, dict) and value.get("termination_unknown") is True:
            return value
        return {"termination_unknown": True, "reason": "Safety hold record is malformed; admission is held."}
    except FileNotFoundError:
        return {"termination_unknown": False}
    except (OSError, ValueError, AttributeError) as exc:
        return {"termination_unknown": True,
            "reason": f"Safety hold record cannot be read; admission is held ({type(exc).__name__})."}


def _set_gpu_safety_hold(reason: str, workload_id: str) -> None:
    target = _gpu_safety_hold_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + "." + uuid.uuid4().hex + ".tmp")
    value = {"termination_unknown": True, "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "workload_id": workload_id, "reason": reason}
    try:
        with temporary.open("w", encoding="utf-8") as stream:
            json.dump(value, stream)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)


def clear_gpu_safety_hold(*, verified_idle: bool) -> dict[str, bool]:
    """Clear an unknown-termination hold only after an explicit idle check."""
    import fcntl
    if verified_idle is not True:
        raise ValueError("Confirm that the affected workload and shared model services are idle.")
    lock_path = _workload_lock_path()
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise MediaJobError("Wait for active Vibe Director workloads to finish before clearing the safety hold.") from exc
        _gpu_safety_hold_path().unlink(missing_ok=True)
    return {"cleared": True}


def get_workload_policy() -> dict[str, bool]:
    try:
        value = json.loads(_workload_policy_path().read_text())
        return {"allow_simultaneous_runs": value.get("allow_simultaneous_runs") is True}
    except (OSError, ValueError, AttributeError):
        return {"allow_simultaneous_runs": False}


def set_workload_policy(allow_simultaneous_runs: bool) -> dict[str, bool]:
    """Persist the policy only while all shared/exclusive workload leases are idle."""
    import fcntl
    if type(allow_simultaneous_runs) is not bool:
        raise ValueError("allow_simultaneous_runs must be a boolean.")
    lock_path = _workload_lock_path()
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise MediaJobError("Wait for active workloads to finish before changing simultaneous runs.") from exc
        policy = {"allow_simultaneous_runs": allow_simultaneous_runs}
        target = _workload_policy_path()
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(target.name + "." + uuid.uuid4().hex + ".tmp")
        try:
            with temporary.open("w") as stream:
                json.dump(policy, stream)
                stream.flush()
                os.fsync(stream.fileno())
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
        return policy


@contextmanager
def gpu_workload_lock():
    """One blocking lease for heavy CPU/GPU work; shared only after explicit opt-in."""
    import fcntl
    depth = getattr(_GPU_WORKLOAD_LOCK_STATE, "depth", 0)
    if depth:
        _GPU_WORKLOAD_LOCK_STATE.depth = depth + 1
        try:
            yield
        finally:
            _GPU_WORKLOAD_LOCK_STATE.depth -= 1
        return
    lock_path = _workload_lock_path()
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+") as handle:
        while True:
            hold = get_gpu_safety_hold()
            if hold.get("termination_unknown"):
                raise MediaJobError("GPU admission is held because a previous workload may still be running: " +
                    str(hold.get("reason") or "termination is unknown"))
            parallel = get_workload_policy()["allow_simultaneous_runs"]
            fcntl.flock(handle.fileno(), fcntl.LOCK_SH if parallel else fcntl.LOCK_EX)
            hold = get_gpu_safety_hold()
            if hold.get("termination_unknown"):
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
                raise MediaJobError("GPU admission is held because a previous workload may still be running: " +
                    str(hold.get("reason") or "termination is unknown"))
            if parallel == get_workload_policy()["allow_simultaneous_runs"]:
                break
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        _GPU_WORKLOAD_LOCK_STATE.depth = 1
        try:
            yield
        finally:
            _GPU_WORKLOAD_LOCK_STATE.depth = 0
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


@contextmanager
def comfy_submission_guard():
    """Backward-compatible alias for the application-wide GPU workload lease."""
    with gpu_workload_lock():
        yield


def wait_for_comfyui_idle(*, comfy_url: str, timeout_seconds: int,
                          poll_interval_seconds: float = 2.0,
                          workload_id: str | None = None,
                          telemetry_path: str | Path | None = None,
                          workload_started_at: str | None = None) -> None:
    """Wait inside the backend dispatcher until ComfyUI has no running/pending prompts."""
    deadline = time.monotonic() + max(0, timeout_seconds)
    last_busy: tuple[int, int] | None = None
    while True:
        try:
            with urllib.request.urlopen(f"{comfy_url.rstrip('/')}/queue", timeout=10) as response:
                queue = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise MediaJobError(f"Cannot verify ComfyUI queue before submit: {type(exc).__name__}: {exc}") from exc
        running, pending = queue.get("queue_running"), queue.get("queue_pending")
        if not isinstance(running, list) or not isinstance(pending, list):
            raise MediaJobError("ComfyUI returned an invalid /queue response; submission was withheld")
        if (not running and not pending) or get_workload_policy()["allow_simultaneous_runs"]:
            try:
                sample = inspect_gpu_runtime(comfy_url=comfy_url, workload_started_at=workload_started_at)
            except GPUAdmissionError as exc:
                raise MediaJobError(f"GPU admission failed closed: {exc}") from exc
            record_gpu_telemetry(telemetry_path, sample, workload_id=workload_id, phase="admission")
            return
        last_busy = (len(running), len(pending))
        if time.monotonic() >= deadline:
            raise MediaJobError(f"Timed out waiting for ComfyUI queue to become idle; running={last_busy[0]} pending={last_busy[1]}")
        time.sleep(max(0.05, poll_interval_seconds))


@contextmanager
def gpu_workload_guard(*, comfy_url: str, timeout_seconds: int = 24 * 3600,
                       on_safety_trip: Callable[[str], None] | None = None,
                       monitor_interval_seconds: float = 10):
    """Admit one Vibe Director GPU workload after visible ComfyUI work is idle.

    All Vibe Director generation and analysis workers must share the same
    process-wide lease for their full GPU work duration. This cannot lock out
    external applications or direct manual ComfyUI clients.
    """
    with gpu_workload_lock():
        started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        stopped = threading.Event()
        monitor_failure: list[str] = []
        workload_id = f"pid:{os.getpid()}"
        telemetry_path = DEFAULT_TELEMETRY_PATH
        wait_for_comfyui_idle(comfy_url=comfy_url, timeout_seconds=timeout_seconds,
                              workload_id=workload_id, telemetry_path=telemetry_path,
                              workload_started_at=started_at)

        def monitor() -> None:
            while not stopped.wait(monitor_interval_seconds):
                try:
                    sample = inspect_gpu_runtime(comfy_url=comfy_url, workload_started_at=started_at, check_queue=False)
                    record_gpu_telemetry(telemetry_path, sample, workload_id=workload_id, phase="app_gpu_workload")
                except Exception as exc:
                    message = f"{type(exc).__name__}: {exc}"
                    monitor_failure.append(message)
                    record_gpu_telemetry(telemetry_path, {"recorded_at": datetime.now(timezone.utc).isoformat(),
                        "monitor_error": message}, workload_id=workload_id, phase="monitor_error")
                    if on_safety_trip is not None:
                        try:
                            # The adapter owns this callback and must synchronously
                            # stop and verify only its own process/container before
                            # the shared lease can be released.
                            on_safety_trip(message)
                        except Exception as cancel_error:
                            unknown = (f"Owned-workload cancellation could not be confirmed: "
                                f"{type(cancel_error).__name__}: {cancel_error}")
                            monitor_failure.append(unknown)
                            _set_gpu_safety_hold(unknown, workload_id)
                    else:
                        unknown = "No adapter cancellation handler was registered; workload termination is unknown."
                        monitor_failure.append(unknown)
                        _set_gpu_safety_hold(unknown, workload_id)
                    stopped.set()

        monitor_thread = threading.Thread(target=monitor, name="story-builder-gpu-monitor", daemon=True)
        monitor_thread.start()
        try:
            yield
        except BaseException as exc:
            stopped.set()
            # Cancellation owns the lease until its termination verification
            # returns (or records a durable unknown-termination hold). A timed
            # join could release admission while that callback is still active.
            monitor_thread.join()
            if monitor_failure and isinstance(exc, Exception):
                raise MediaJobError(f"GPU state changed during the workload: {monitor_failure[0]}") from exc
            raise
        stopped.set()
        monitor_thread.join()
        if monitor_failure:
            raise MediaJobError(f"GPU state changed during the workload: {monitor_failure[0]}")


def release_comfyui_models_if_idle(*, comfy_url: str, timeout_seconds: int = 10,
                                   poll_interval_seconds: float = 0.5,
                                   wait_for_memory_release: bool = False,
                                   keep_waiting: Callable[[], bool] | None = None) -> dict[str, Any]:
    """Ask ComfyUI to unload VRAM models only when its shared queue is idle.

    This is best-effort housekeeping: it must never turn a successful render
    into a failed job, and it must not disrupt a queued/running workflow owned
    by another Story Builder page or a direct ComfyUI user.
    Pipeline handoffs may additionally require two idle, low-allocation samples.
    This observes the Torch allocator, not proof that every dynamic/CPU allocation
    was evicted. ComfyUI's /free response only acknowledges asynchronous flags.
    """
    try:
        with urllib.request.urlopen(f"{comfy_url.rstrip('/')}/queue", timeout=timeout_seconds) as response:
            queue = json.loads(response.read().decode("utf-8"))
        if not all(isinstance(queue.get(key), list) for key in ("queue_running", "queue_pending")):
            raise ValueError("Invalid ComfyUI queue observation")
        running = queue["queue_running"]
        pending = queue["queue_pending"]
        if running or pending:
            return {"status": "deferred", "reason": "comfyui_queue_not_empty",
                    "running": len(running), "pending": len(pending)}
        request = urllib.request.Request(
            f"{comfy_url.rstrip('/')}/free",
            data=json.dumps({"unload_models": True, "free_memory": True}).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            response.read()
        if wait_for_memory_release:
            started = time.monotonic()
            deadline = started + 30
            idle_samples = 0
            observation = {}
            # The initial observation window is 30s. A supervised handoff can
            # keep polling every 10s thereafter; elapsed time never grants
            # permission to load a model. The caller maintains its claim lease.
            while True:
                if keep_waiting is not None and not keep_waiting():
                    return {"status": "cancelled", "unload_request_accepted": True,
                            "memory_release_observed": False, "elapsed_seconds": time.monotonic() - started}
                elapsed = time.monotonic() - started
                if time.monotonic() >= deadline and keep_waiting is None:
                    return {"status": "unverified", "unload_request_accepted": True,
                            "reason": "Idle Torch allocator was not observed within 30 seconds",
                            "elapsed_seconds": elapsed, **observation}
                time.sleep(10.0 if elapsed >= 30 else max(0.1, poll_interval_seconds))
                try:
                    with urllib.request.urlopen(f"{comfy_url.rstrip('/')}/queue", timeout=timeout_seconds) as response:
                        observed_queue = json.loads(response.read().decode("utf-8"))
                    if not all(isinstance(observed_queue.get(key), list) for key in ("queue_running", "queue_pending")):
                        raise ValueError("Invalid ComfyUI queue observation")
                    if observed_queue["queue_running"] or observed_queue["queue_pending"]:
                        return {"status": "deferred", "reason": "comfyui_queue_changed_during_release"}
                    with urllib.request.urlopen(f"{comfy_url.rstrip('/')}/system_stats", timeout=timeout_seconds) as response:
                        observed_stats = json.loads(response.read().decode("utf-8"))
                    device = observed_stats["devices"][0]
                    reserved = int(device["torch_vram_total"])
                    unused = int(device["torch_vram_free"])
                    if not 0 <= unused <= reserved:
                        raise ValueError("Invalid ComfyUI allocator counters")
                    active = reserved - unused
                    observation = {"torch_reserved_bytes": reserved, "torch_active_bytes": active,
                                   "vram_free_bytes": device.get("vram_free"),
                                   "host_memory": observed_stats.get("system", {})}
                    idle_samples = idle_samples + 1 if reserved <= 256 * 1024**2 and active <= 64 * 1024**2 else 0
                except Exception as exc:
                    idle_samples = 0
                    observation = {"reason": f"Memory observation failed: {type(exc).__name__}: {exc}"}
                if idle_samples >= 2:
                    result = {"status": "memory_release_observed", "unload_request_accepted": True,
                              "memory_release_observed": True, "elapsed_seconds": time.monotonic() - started,
                              **observation}
                    LOGGER.info("ComfyUI pipeline memory handoff: %s", result)
                    try:
                        record_gpu_telemetry(DEFAULT_TELEMETRY_PATH, result,
                                             workload_id=None, phase="pipeline_memory_handoff")
                    except OSError:
                        LOGGER.warning("Could not record ComfyUI memory handoff", exc_info=True)
                    return result
                if elapsed >= 30:
                    LOGGER.warning("Waiting for ComfyUI unload; checking again in 10s: elapsed=%.1fs %s",
                                   time.monotonic() - started, observation)
        # Acknowledgement does not prove eviction or model fit. Preserve only
        # observed memory as diagnostic evidence; do not recreate a VRAM floor.
        try:
            with urllib.request.urlopen(f"{comfy_url.rstrip('/')}/system_stats", timeout=timeout_seconds) as response:
                stats = json.loads(response.read().decode("utf-8"))
            devices = stats.get("devices")
            free_bytes = int(devices[0]["vram_free"])
            return {"status": "unload_requested", "unload_request_accepted": True,
                    "vram_free_bytes": free_bytes}
        except Exception as exc:
            return {"status": "unverified", "unload_request_accepted": True,
                    "reason": f"Memory observation failed: {type(exc).__name__}: {exc}"}
    except Exception as exc:  # cleanup failure must not mask the workflow result
        return {"status": "unavailable", "reason": f"{type(exc).__name__}: {exc}"}


def apply_media_inputs(workflow: dict[str, Any], payload: dict[str, Any], filename_prefix: str) -> dict[str, Any]:
    prompt = payload.get("prompt", "")
    negative_prompt = payload.get("negative_prompt", "")
    images = payload.get("images", []) or []
    number_overrides = {key: payload.get(key) for key in ("width", "height", "steps", "cfg", "seed", "length", "frame_rate")}

    image_index = 0
    for node in workflow.values():
        class_type = node.get("class_type", "")
        inputs = node.setdefault("inputs", {})
        if class_type == "LoadImage" and image_index < len(images):
            inputs["image"] = images[image_index]
            image_index += 1
        if class_type in {"CLIPTextEncode", "TextEncodeQwenImageEditPlus"}:
            if "prompt" in inputs:
                default_prompt = str(inputs.get("prompt", ""))
                inputs["prompt"] = negative_prompt if _looks_negative(default_prompt) and negative_prompt else prompt
            if "text" in inputs:
                default_text = str(inputs.get("text", ""))
                if _looks_negative(default_text):
                    if negative_prompt:
                        inputs["text"] = negative_prompt
                else:
                    inputs["text"] = prompt
        for key, value in number_overrides.items():
            if value is not None and key in inputs:
                inputs[key] = value
        if class_type in {"SaveImage", "SaveVideo"} and "filename_prefix" in inputs:
            inputs["filename_prefix"] = filename_prefix
    return workflow


def _looks_negative(value: str) -> bool:
    lowered = value.lower()
    return any(token in lowered for token in ("low quality", "deformed", "ugly", "bad "))


def submit_and_wait(workflow: dict[str, Any], *, comfy_url: str, timeout_seconds: int = 600,
                    prompt_id: str | None = None, telemetry_path: str | Path | None = None,
                    workload_id: str | None = None) -> tuple[str, dict[str, Any]]:
    # Keep the shared lock through completion, not just POST: otherwise a
    # second website operation could be added to ComfyUI's own pending queue.
    telemetry_path = telemetry_path or DEFAULT_TELEMETRY_PATH
    workload_id = workload_id or f"pid:{os.getpid()}:comfy_render"
    with comfy_submission_guard():
        workload_started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        wait_for_comfyui_idle(comfy_url=comfy_url, timeout_seconds=timeout_seconds,
                              workload_id=workload_id, telemetry_path=telemetry_path,
                              workload_started_at=workload_started_at)
        requested_prompt_id = prompt_id
        try:
            watchdog = ensure_prompt_watchdog(comfy_url=comfy_url, prompt_id=prompt_id) if prompt_id else None
            if watchdog:
                watchdog.check()
        except GPUAdmissionError as exc:
            if prompt_id:
                finish_prompt_watchdog(comfy_url=comfy_url, prompt_id=prompt_id)
            raise MediaJobError(f"GPU watchdog admission failed before POST: {exc}") from exc
        payload: dict[str, Any] = {"prompt": workflow}
        if requested_prompt_id is not None:
            payload["prompt_id"] = requested_prompt_id
        request = urllib.request.Request(
            f"{comfy_url}/prompt",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if requested_prompt_id:
                finish_prompt_watchdog(comfy_url=comfy_url, prompt_id=requested_prompt_id)
            try:
                detail = exc.read().decode("utf-8", errors="replace")
            except Exception:
                detail = str(exc)
            raise MediaJobError(f"ComfyUI rejected the workflow (HTTP {exc.code}): {detail[:2000]}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise MediaJobError(
                "ComfyUI submission outcome is unknown after the request was sent; "
                "do not blindly resubmit. Check the ComfyUI queue/history first.",
                prompt_id=requested_prompt_id, remote_state_unknown=True) from exc
        except json.JSONDecodeError as exc:
            raise MediaJobError(
                "ComfyUI returned an unreadable submission response; the render may still be queued. "
                "Check the ComfyUI queue/history before retrying.",
                prompt_id=requested_prompt_id, remote_state_unknown=True) from exc
        prompt_id = data.get("prompt_id")
        if not prompt_id or (requested_prompt_id is not None and prompt_id != requested_prompt_id):
            raise MediaJobError(
                f"ComfyUI returned an unexpected prompt_id {prompt_id!r}; "
                "reconcile queue/history before retrying.",
                prompt_id=requested_prompt_id, remote_state_unknown=True)

        watchdog = watchdog or ensure_prompt_watchdog(comfy_url=comfy_url, prompt_id=prompt_id)
        history_url = f"{comfy_url}/history/{prompt_id}"
        deadline = time.time() + timeout_seconds
        consecutive_poll_errors = 0
        next_telemetry = time.monotonic()
        while time.time() < deadline:
            try:
                watchdog.check()
            except GPUAdmissionError as exc:
                raise MediaJobError(str(exc), prompt_id=str(prompt_id), remote_state_unknown=True) from exc
            if time.monotonic() >= next_telemetry:
                try:
                    sample = inspect_gpu_runtime(comfy_url=comfy_url, expected_prompt_id=str(prompt_id),
                                                 workload_started_at=workload_started_at)
                except GPUAdmissionError as exc:
                    raise MediaJobError(
                        f"GPU runtime monitoring failed; remote render may still be active: {exc}",
                        prompt_id=str(prompt_id), remote_state_unknown=True) from exc
                record_gpu_telemetry(telemetry_path, sample, workload_id=workload_id, phase="render")
                next_telemetry = time.monotonic() + 10
            try:
                with urllib.request.urlopen(history_url, timeout=30) as response:
                    history = json.loads(response.read().decode("utf-8"))
            except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
                # A transient health/API miss does not mean a costly model
                # render stopped. Keep its prompt ID and continue polling up
                # to the job deadline; never submit a replacement here.
                consecutive_poll_errors += 1
                if consecutive_poll_errors == 1 or consecutive_poll_errors % 10 == 0:
                    LOGGER.warning("Comfy history polling temporarily unavailable prompt_id=%s "
                                   "consecutive_errors=%d error=%s: %s",
                                   prompt_id, consecutive_poll_errors, type(exc).__name__, exc)
                time.sleep(2)
                continue
            if consecutive_poll_errors:
                LOGGER.info("Comfy history polling recovered prompt_id=%s after transient_errors=%d",
                            prompt_id, consecutive_poll_errors)
                consecutive_poll_errors = 0
            prompt_state = history.get(prompt_id)
            if prompt_state:
                status = prompt_state.get("status", {})
                if status.get("status_str") == "error":
                    raise MediaJobError(f"ComfyUI prompt failed: {status.get('messages', [])}",
                                        prompt_id=str(prompt_id))
                if status.get("completed"):
                    release_comfyui_models_if_idle(comfy_url=comfy_url)
                    try:
                        sample = inspect_gpu_runtime(comfy_url=comfy_url, workload_started_at=workload_started_at)
                    except GPUAdmissionError as exc:
                        LOGGER.warning("GPU post-release verification unavailable prompt_id=%s error=%s",
                                       prompt_id, exc)
                        record_gpu_telemetry(telemetry_path,
                            {"recorded_at": datetime.now(timezone.utc).isoformat(),
                             "post_release_verification_error": str(exc)},
                            workload_id=workload_id, phase="after_model_release_unverified")
                    else:
                        record_gpu_telemetry(telemetry_path, sample, workload_id=workload_id,
                                             phase="after_model_release")
                    return str(prompt_id), prompt_state
            time.sleep(2)
        raise MediaJobError(
            f"Timed out waiting for ComfyUI prompt {prompt_id}; remote state is unknown. "
            "Reconcile this exact prompt before retrying.",
            prompt_id=str(prompt_id), remote_state_unknown=True)


def collect_outputs(history: dict[str, Any], *, destination_dir: Path, comfy_url: str,
                    output_only: bool = False) -> list[dict[str, Any]]:
    destination_dir.mkdir(parents=True, exist_ok=True)
    collected: list[dict[str, Any]] = []
    for node_output in history.get("outputs", {}).values():
        for image in node_output.get("images", []):
            if output_only and image.get("type", "output") != "output":
                continue
            copied = _copy_image_output(image, destination_dir, comfy_url)
            if copied is not None:
                kind = "video" if copied.suffix.lower() in {".mp4", ".webm", ".mov", ".mkv", ".avi", ".gif"} else "image"
                collected.append({"kind": kind, "relative_path": copied.name, "filename": copied.name})
        for video in node_output.get("gifs", []) + node_output.get("videos", []):
            if output_only and video.get("type", "output") != "output":
                continue
            copied = _copy_binary_output(video, destination_dir, comfy_url)
            if copied is not None:
                collected.append({"kind": "video", "relative_path": copied.name, "filename": copied.name})
        audio_items = node_output.get("audio", []) + node_output.get("audios", [])
        for audio in audio_items:
            if output_only and audio.get("type", "output") != "output":
                continue
            copied = _copy_binary_output(audio, destination_dir, comfy_url)
            if copied is not None:
                collected.append({"kind": "audio", "relative_path": copied.name, "filename": copied.name})
    return collected


def _copy_image_output(image: dict[str, Any], destination_dir: Path, comfy_url: str) -> Path | None:
    params = urllib.parse.urlencode(
        {"filename": image.get("filename", ""), "subfolder": image.get("subfolder", ""), "type": image.get("type", "output")}
    )
    view_url = f"{comfy_url}/view?{params}"
    return _download_output(view_url, destination_dir, image.get("filename", "output.png"))


def _copy_binary_output(data: dict[str, Any], destination_dir: Path, comfy_url: str) -> Path | None:
    params = urllib.parse.urlencode(
        {"filename": data.get("filename", ""), "subfolder": data.get("subfolder", ""), "type": data.get("type", "output")}
    )
    view_url = f"{comfy_url}/view?{params}"
    return _download_output(view_url, destination_dir, data.get("filename", "output.bin"))


def _download_output(url: str, destination_dir: Path, filename: str) -> Path | None:
    safe_name = f"{uuid.uuid4().hex}_{Path(filename).name}"
    path = destination_dir / safe_name
    try:
        with urllib.request.urlopen(url, timeout=120) as response:
            path.write_bytes(response.read())
    except urllib.error.URLError:
        return None
    return path


def save_uploaded_asset(upload_path: Path, destination_dir: Path) -> Path:
    destination_dir.mkdir(parents=True, exist_ok=True)
    target = destination_dir / f"{uuid.uuid4().hex}_{upload_path.name}"
    shutil.copy2(upload_path, target)
    return target
