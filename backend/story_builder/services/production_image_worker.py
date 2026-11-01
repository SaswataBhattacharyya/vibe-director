"""Serialized ComfyUI worker for durable production image candidates."""
from __future__ import annotations

import json
import hashlib
import logging
import os
import shutil
import subprocess
import threading
import time
import uuid
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from story_builder.services.media_jobs import (
    collect_outputs, comfy_submission_guard, release_comfyui_models_if_idle,
    get_workload_policy, gpu_workload_lock,
)
from story_builder.services.gpu_runtime import (
    DEFAULT_TELEMETRY_PATH, GPU_RENDER_CLOCK_CEILING_MHZ, GPU_RENDER_TEMP_CUTOFF,
    GPUAdmissionError, comfy_container_name, inspect_gpu_runtime, interrupt_if_owned_prompt,
    read_gpu_operating_point, record_gpu_telemetry,
)
from story_builder.services.production_image_jobs import ProductionImageJobStore, _project_id
from story_builder.services.production_image_workflows import SMOKE_ROOT, record_successful_image_smoke

from story_builder.services.gpu_watchdog import ensure_prompt_watchdog, finish_prompt_watchdog

LOGGER = logging.getLogger(__name__)


def comfyui_root() -> Path:
    default = "/home/riki/web_dev/setup_comfy_and-stuff/ComfyUI"
    return Path(os.environ.get("COMFYUI_ROOT", default)).expanduser().resolve()


def _request_json(url: str, *, method: str = "GET", payload: dict[str, Any] | None = None,
                  timeout_seconds: int = 30) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, method=method,
        headers={"Content-Type": "application/json"} if data is not None else {})
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        return json.loads(response.read().decode("utf-8"))


class ProductionImageWorker:
    """Process one queued candidate at a time; uncertain POSTs are never retried."""

    def __init__(self, store: ProductionImageJobStore, *, comfy_url: str,
                 output_root: Path, register_output: Callable[..., dict[str, Any]],
                 comfy_output_root: Path | None = None,
                 workspace_output: Callable[[str], Path] | None = None,
                 request_json: Callable[..., dict[str, Any]] = _request_json,
                 release_idle: Callable[..., dict[str, Any]] = release_comfyui_models_if_idle,
                 gpu_inspector: Callable[..., dict[str, Any]] | None = None,
                 operating_point_reader: Callable[[], dict[str, float]] | None = None,
                 cleanup_staging: Callable[[str], Any] | None = None,
                 prepare_graph: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
                 resolve_candidate: Callable[[str, str], Path] | None = None,
                 review_candidate: Callable[[dict[str, Any], Path], dict[str, Any]] | None = None,
                 director_provider_preflight: Callable[[str], dict[str, Any]] | None = None,
                 accept_candidate: Callable[[dict[str, Any]], Any] | None = None,
                 validate_candidate: Callable[[dict[str, Any]], str | None] | None = None,
                 enqueue_retake: Callable[[dict[str, Any], dict[str, Any], int], str] | None = None,
                 sleep: Callable[[float], None] = time.sleep,
                 poll_interval: float = 2.0, timeout_seconds: int = 3600):
        self.store = store
        self.comfy_url = comfy_url.rstrip("/")
        self.output_root = Path(output_root).resolve()
        self.workspace_output = workspace_output
        self.comfy_output_root = Path(comfy_output_root or (comfyui_root() / "output")).resolve()
        self.register_output = register_output
        self.request_json = request_json
        self.release_idle = release_idle
        self.gpu_inspector = gpu_inspector or inspect_gpu_runtime
        self.operating_point_reader = operating_point_reader or read_gpu_operating_point
        self.cleanup_staging = cleanup_staging
        self.prepare_graph = prepare_graph
        self.resolve_candidate = resolve_candidate
        self.review_candidate = review_candidate
        self.director_provider_preflight = director_provider_preflight
        self.accept_candidate = accept_candidate
        self.validate_candidate = validate_candidate
        self.enqueue_retake = enqueue_retake
        self.sleep = sleep
        self.poll_interval = max(0.05, poll_interval)
        self.timeout_seconds = max(5, timeout_seconds)

    @gpu_workload_lock()
    def process_one(self) -> dict[str, Any]:
        job = self.store.next_queued()
        if job is None:
            return {"status": "idle"}
        LOGGER.info("Production image candidate claimed job=%s project=%s workflow=%s candidate=%s",
            job["job_id"], job["project_id"], job["workflow_id"], job["candidate_index"])
        prompt_id: str | None = None
        workload_started_at: str | None = None
        try:
            settings = job.get("settings") or {}
            if (settings.get("director_review_required") or settings.get("automated_world_views")) and self.validate_candidate is not None:
                stale_reason = self.validate_candidate(job)
                if stale_reason:
                    self.store.transition(job["job_id"], "failed", error={
                        "code": "automated_image_inputs_stale", "message": stale_reason})
                    return {"status": "failed", "job_id": job["job_id"], "reason": stale_reason}
            if settings.get("director_review_required"):
                provider = str(settings.get("director_provider") or "").strip()
                if not provider or self.director_provider_preflight is None:
                    message = "Full-mode image generation is blocked because its saved Director provider is unavailable for preflight."
                    self.store.transition(job["job_id"], "failed", error={
                        "code": "director_provider_unavailable", "message": message})
                    return {"status": "failed", "job_id": job["job_id"], "reason": message}
                try:
                    self.director_provider_preflight(provider)
                except Exception as exc:
                    message = f"Saved Director provider preflight failed: {type(exc).__name__}: {exc}"[:1200]
                    self.store.transition(job["job_id"], "failed", error={
                        "code": "director_provider_unavailable", "message": message,
                        "provider": provider})
                    LOGGER.warning("Blocking Full-mode image before GPU submission job=%s provider=%s error=%s",
                                   job["job_id"], provider, message)
                    return {"status": "failed", "job_id": job["job_id"], "reason": message}
            busy_reason = self._comfy_busy_reason()
            if busy_reason:
                self.store.transition(job["job_id"], "queued", error={"code": "comfyui_busy", "message": busy_reason})
                return {"status": "waiting_for_comfyui", "job_id": job["job_id"], "reason": busy_reason}
            # Keep the global admission lock through terminal polling. This
            # prevents concurrent Story Builder jobs from filling ComfyUI's queue.
            with comfy_submission_guard():
                busy_reason = self._comfy_busy_reason()
                if busy_reason:
                    self.store.transition(job["job_id"], "queued", error={"code": "comfyui_busy", "message": busy_reason})
                    return {"status": "waiting_for_comfyui", "job_id": job["job_id"], "reason": busy_reason}
                try:
                    workload_started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
                    sample = self.gpu_inspector(comfy_url=self.comfy_url,
                                                workload_started_at=workload_started_at)
                except GPUAdmissionError as exc:
                    self.store.transition(job["job_id"], "queued", error={"code": "gpu_admission_failed", "message": str(exc)})
                    return {"status": "waiting_for_gpu", "job_id": job["job_id"], "reason": str(exc)}
                record_gpu_telemetry(DEFAULT_TELEMETRY_PATH, sample, workload_id=job["job_id"], phase="admission")
                from .image_training import ensure_idle, selection
                try:
                    ensure_idle()
                    selection(job.get("settings", {}).get("zimage_lora"))
                except ValueError as exc:
                    self.store.transition(job["job_id"], "failed", error={"code":"training_or_lora_conflict", "message":str(exc)})
                    return {"status":"failed", "job_id":job["job_id"], "reason":str(exc)}
                graph = self.prepare_graph(job) if self.prepare_graph else job["graph"]
                prompt_id = self.store.reserve_prompt_id(job["job_id"])
                try:
                    ensure_prompt_watchdog(comfy_url=self.comfy_url, prompt_id=prompt_id).check()
                except GPUAdmissionError:
                    finish_prompt_watchdog(comfy_url=self.comfy_url, prompt_id=prompt_id)
                    raise
                try:
                    response = self.request_json(f"{self.comfy_url}/prompt", method="POST",
                        payload={"prompt": graph, "prompt_id": prompt_id}, timeout_seconds=60)
                except urllib.error.HTTPError as exc:
                    finish_prompt_watchdog(comfy_url=self.comfy_url, prompt_id=prompt_id)
                    detail = exc.read().decode("utf-8", errors="replace")[-2000:]
                    self.store.transition(job["job_id"], "failed", error={
                        "code": "comfy_submission_rejected", "http_status": exc.code, "message": detail})
                    return {"status": "failed", "job_id": job["job_id"]}
                except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
                    self.store.transition(job["job_id"], "recovery_required", error={
                        "code": "comfy_submit_outcome_unknown", "message": f"{type(exc).__name__}: {exc}"})
                    return {"status": "recovery_required", "job_id": job["job_id"], "prompt_id": prompt_id}
                if response.get("prompt_id") != prompt_id:
                    self.store.transition(job["job_id"], "recovery_required", error={
                        "code": "comfy_prompt_id_mismatch", "message": "ComfyUI returned a different prompt ID."})
                    return {"status": "recovery_required", "job_id": job["job_id"], "prompt_id": prompt_id}
                self.store.transition(job["job_id"], "running")
                history = self._wait_history(job["job_id"], prompt_id,
                                             workload_started_at=workload_started_at)
                if history is None:
                    return {"status": "recovery_required", "job_id": job["job_id"], "prompt_id": prompt_id}
                state = history.get("status", {})
                if state.get("status_str") == "error":
                    self.store.transition(job["job_id"], "failed", error={
                        "code": "comfy_render_failed", "messages": state.get("messages", [])})
                    self.release_idle(comfy_url=self.comfy_url)
                    return {"status": "failed", "job_id": job["job_id"]}
                return self._collect_completed(job, prompt_id, history)
        except Exception as exc:
            LOGGER.exception("Production image candidate worker error job=%s", job["job_id"])
            status = "failed" if prompt_id is None else "recovery_required"
            try:
                self.store.transition(job["job_id"], status, error={"code": "image_worker_error", "message": f"{type(exc).__name__}: {exc}"})
            except Exception:
                LOGGER.exception("Unable to persist production image candidate failure job=%s", job["job_id"])
            return {"status": status, "job_id": job["job_id"], "prompt_id": prompt_id}
        finally:
            self._cleanup_staging_if_batch_settled(job)

    def reconcile_recovery_once(self, *, limit: int = 20) -> dict[str, int]:
        """Reconcile only saved prompt IDs; never resubmit a recovery job."""
        jobs = self.store.recovery_jobs(limit=limit)
        observed = 0
        for job in jobs:
            prompt_id = str(job["prompt_id"])
            ensure_prompt_watchdog(comfy_url=self.comfy_url, prompt_id=prompt_id)
            try:
                history = self.request_json(f"{self.comfy_url}/history/{prompt_id}", timeout_seconds=20)
                queue = self.request_json(f"{self.comfy_url}/queue", timeout_seconds=10)
            except Exception as exc:
                LOGGER.warning("Image recovery check unavailable job=%s prompt=%s error=%s",
                               job["job_id"], prompt_id, exc)
                continue
            state = history.get(prompt_id) if isinstance(history, dict) else None
            if not state:
                entries = list(queue.get("queue_running", [])) + list(queue.get("queue_pending", []))
                is_queued = any((row.get("prompt_id") if isinstance(row, dict) else
                                 row[1] if isinstance(row, (tuple, list)) and len(row) > 1 else None) == prompt_id
                                for row in entries)
                if not is_queued:
                    LOGGER.warning("Saved image prompt is absent from ComfyUI history and queue; held for manual reconciliation job=%s prompt=%s",
                                   job["job_id"], prompt_id)
                continue
            status = state.get("status", {}) if isinstance(state, dict) else {}
            if status.get("status_str") == "error":
                self.store.transition(job["job_id"], "failed", error={
                    "code": "comfy_render_failed", "messages": status.get("messages", []),
                    "prompt_id": prompt_id})
                self._cleanup_staging_if_batch_settled(job)
                self.release_idle(comfy_url=self.comfy_url)
                observed += 1
                continue
            if not status.get("completed"):
                continue
            try:
                with comfy_submission_guard():
                    self.store.transition(job["job_id"], "running")
                    result = self._collect_completed(job, prompt_id, state)
                observed += 1
                LOGGER.info("Recovered completed image prompt job=%s prompt=%s status=%s",
                            job["job_id"], prompt_id, result["status"])
            except Exception as exc:
                LOGGER.exception("Image prompt recovery failed job=%s prompt=%s", job["job_id"], prompt_id)
                try:
                    self.store.transition(job["job_id"], "recovery_required", error={
                        "code": "image_recovery_incomplete", "message": str(exc)[:1000],
                        "prompt_id": prompt_id})
                except Exception:
                    LOGGER.exception("Could not preserve image recovery state job=%s", job["job_id"])
                observed += 1
        return {"observed": observed, "checked": len(jobs)}

    def review_next_candidate(self) -> dict[str, Any]:
        """Run one durable Full-mode visual review and replay any pending decision safely."""
        if not all((self.resolve_candidate, self.review_candidate, self.accept_candidate)):
            return {"status": "reviewer_unavailable"}
        reviews = self.store.unresolved_director_reviews(limit=1)
        if reviews:
            review = reviews[0]
            job = self.store.get_job(project_id=review["project_id"], job_id=review["job_id"])
            return self._resolve_director_decision(job, review["decision"])
        owner_token = str(uuid.uuid4())
        job = self.store.claim_next_director_review(owner_token=owner_token)
        if not job:
            return {"status": "idle"}
        if job.get("review_attempts_exhausted"):
            decision = {"schema_version": 1, "action": "blocked",
                "reason": "Director image review exceeded its bounded restart retry count.",
                "prompt_delta": "", "criteria": [], "confidence": 0.0}
            review = self.store.record_director_review(project_id=job["project_id"], run_id=job["run_id"],
                job_id=job["job_id"], asset_id=job["output_asset_id"], decision=decision)
            self.store.resolve_director_review(job_id=job["job_id"], resolution_status="blocked",
                error={"code": "director_image_review_attempts_exhausted", "message": decision["reason"]})
            return {"status": "blocked", "job_id": job["job_id"], "review": review}
        try:
            image_path = self.resolve_candidate(job["project_id"], job["output_asset_id"])
            if self.validate_candidate is not None:
                stale_reason = self.validate_candidate(job)
                if stale_reason:
                    decision = {"schema_version": 1, "action": "blocked", "reason": stale_reason,
                        "prompt_delta": "", "criteria": [], "confidence": 0.0}
                    review = self.store.record_director_review(project_id=job["project_id"],
                        run_id=job["run_id"], job_id=job["job_id"], asset_id=job["output_asset_id"],
                        decision=decision, owner_token=owner_token)
                    self.store.resolve_director_review(job_id=job["job_id"], resolution_status="blocked",
                        error={"code": "automated_image_inputs_stale", "message": stale_reason})
                    self.store.release_director_review_claim(job_id=job["job_id"], owner_token=owner_token)
                    return {"status": "blocked", "job_id": job["job_id"], "review": review}
            decision = self.review_candidate(job, image_path)
            if not isinstance(decision, dict) or decision.get("action") not in {"accept", "retake", "blocked"}:
                raise ValueError("Director returned no valid candidate action.")
            review = self.store.record_director_review(project_id=job["project_id"], run_id=job["run_id"],
                job_id=job["job_id"], asset_id=job["output_asset_id"], decision=decision,
                owner_token=owner_token)
        except Exception as exc:
            LOGGER.exception("Director image review failed job=%s", job["job_id"])
            decision = {"schema_version": 1, "action": "blocked",
                "reason": f"Director image review is unavailable: {type(exc).__name__}: {exc}"[:1200],
                "prompt_delta": "", "criteria": [], "confidence": 0.0}
            review = self.store.record_director_review(project_id=job["project_id"], run_id=job["run_id"],
                job_id=job["job_id"], asset_id=job["output_asset_id"], decision=decision,
                owner_token=owner_token)
            self.store.resolve_director_review(job_id=job["job_id"], resolution_status="blocked",
                error={"code": "director_image_review_failed", "message": decision["reason"]})
            self.store.release_director_review_claim(job_id=job["job_id"], owner_token=owner_token)
            return {"status": "blocked", "job_id": job["job_id"], "review": review}
        self.store.release_director_review_claim(job_id=job["job_id"], owner_token=owner_token)
        return self._resolve_director_decision(job, decision)

    def reassess_existing_candidate(self, *, project_id: str, job_id: str,
                                    correction_reason: str) -> dict[str, Any]:
        """Re-review the exact saved bytes once; this path can never enqueue a retake."""
        if not all((self.resolve_candidate, self.review_candidate, self.accept_candidate)):
            return {"status": "reviewer_unavailable", "job_id": job_id}
        owner_token = str(uuid.uuid4())
        if not self.store.claim_director_reassessment(project_id=project_id, job_id=job_id,
                                                       owner_token=owner_token):
            return {"status": "review_in_progress", "job_id": job_id}
        try:
            job = self.store.get_job(project_id=project_id, job_id=job_id)
            current = self.store.get_director_review(project_id=project_id, job_id=job_id)
            if not job or not current:
                return {"status": "not_found", "job_id": job_id}
            # A saved reassessment is replayed without running another inference.
            if current.get("superseded_review"):
                decision = current["decision"]
                held = self._verify_reviewed_candidate(job, decision)
                if held:
                    return held
                if current["resolution_status"] == "accepted":
                    return {"status": "accepted", "job_id": job_id, "asset_id": job["output_asset_id"]}
                return self._resolve_director_decision(job, decision)
            original = current
            if original.get("resolution_status") not in {"rejected", "blocked"}:
                return {"status": "not_reassessable", "job_id": job_id}
            image_path = Path(self.resolve_candidate(project_id, job["output_asset_id"])).resolve()
            expected_hash = original["decision"].get("image_sha256")
            if (not image_path.is_file() or not isinstance(expected_hash, str)
                    or hashlib.sha256(image_path.read_bytes()).hexdigest() != expected_hash):
                return {"status": "held", "job_id": job_id,
                        "reason": "The original candidate bytes cannot be verified against its saved review."}
            decision = self.review_candidate(job, image_path)
            # Reassessment may only add a second opinion that accepts the same bytes.
            if not isinstance(decision, dict) or decision.get("action") != "accept":
                return {"status": "held", "job_id": job_id,
                        "reason": "The reassessment did not produce a valid acceptance; original review remains authoritative."}
            if hashlib.sha256(image_path.read_bytes()).hexdigest() != expected_hash:
                return {"status": "held", "job_id": job_id,
                        "reason": "Candidate bytes changed during reassessment."}
            source_hash = hashlib.sha256(json.dumps(original["decision"], sort_keys=True).encode()).hexdigest()
            saved = self.store.record_director_reassessment(project_id=project_id, run_id=job["run_id"],
                job_id=job_id, asset_id=job["output_asset_id"], source_decision_hash=source_hash,
                correction_reason=correction_reason, decision=decision, owner_token=owner_token)
            # If acceptance side effects fail, the immutable pending row is replayed by the ordinary reviewer.
            self.accept_candidate(job)
            self.store.resolve_director_review(job_id=job_id, resolution_status="accepted")
            return {"status": "accepted", "job_id": job_id, "asset_id": job["output_asset_id"],
                    "reassessment": saved}
        finally:
            self.store.release_director_review_claim(job_id=job_id, owner_token=owner_token)

    def _verify_reviewed_candidate(self, job: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any] | None:
        """Recovery must accept the bytes reviewed, not a changed file at the same path."""
        expected_hash = decision.get("image_sha256")
        if expected_hash is None:
            return None  # Older decisions did not record byte provenance.
        try:
            image_path = Path(self.resolve_candidate(job["project_id"], job["output_asset_id"]))
            if (isinstance(expected_hash, str) and image_path.is_file()
                    and hashlib.sha256(image_path.read_bytes()).hexdigest() == expected_hash):
                return None
        except OSError:
            pass
        return {"status": "held", "job_id": job["job_id"],
                "reason": "Candidate bytes do not match the saved Director review."}

    def _resolve_director_decision(self, job: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
        if (job.get("settings", {}).get("director_review_required")
                and self.validate_candidate is not None):
            stale_reason = self.validate_candidate(job)
            if stale_reason:
                self.store.resolve_director_review(job_id=job["job_id"], resolution_status="blocked",
                    error={"code": "automated_image_inputs_stale", "message": stale_reason})
                return {"status": "blocked", "job_id": job["job_id"], "reason": stale_reason}
        action = decision.get("action")
        if action == "accept":
            held = self._verify_reviewed_candidate(job, decision)
            if held:
                self.store.resolve_director_review(job_id=job["job_id"], resolution_status="blocked",
                    error={"code": "director_reviewed_bytes_changed", "message": held["reason"]})
                return held
            try:
                accepted = self.accept_candidate(job)
            except Exception as exc:
                message = f"Reviewed candidate could not be selected safely: {type(exc).__name__}: {exc}"[:1200]
                self.store.resolve_director_review(job_id=job["job_id"], resolution_status="blocked",
                    error={"code": "director_image_acceptance_failed", "message": message})
                return {"status": "blocked", "job_id": job["job_id"], "reason": message}
            if isinstance(accepted, dict) and accepted.get("alternate") is True:
                self.store.resolve_director_review(job_id=job["job_id"], resolution_status="rejected",
                    error={"code": "director_master_already_selected",
                           "message": "The current master was kept; this reviewed candidate remains an alternate."})
                return {"status": "alternate", "job_id": job["job_id"],
                        "asset_id": job["output_asset_id"]}
            self.store.resolve_director_review(job_id=job["job_id"], resolution_status="accepted")
            return {"status": "accepted", "job_id": job["job_id"], "asset_id": job["output_asset_id"]}
        if action == "retake":
            used = int(job.get("settings", {}).get("retake_index", 0))
            budget = int(job.get("settings", {}).get("full_retake_budget", 0))
            if used >= budget:
                self.store.resolve_director_review(job_id=job["job_id"], resolution_status="rejected",
                    error={"code": "director_retake_budget_exhausted", "message": "The Director's bounded retake budget is exhausted."})
                return {"status": "rejected", "job_id": job["job_id"], "asset_id": job["output_asset_id"]}
            if self.enqueue_retake is None:
                self.store.resolve_director_review(job_id=job["job_id"], resolution_status="blocked",
                    error={"code": "director_retake_dispatcher_unavailable", "message": "Bounded image retake dispatcher is unavailable."})
                return {"status": "blocked", "job_id": job["job_id"], "reason": "Bounded image retake dispatcher is unavailable."}
            batch_id = self.enqueue_retake(job, decision, used + 1)
            self.store.resolve_director_review(job_id=job["job_id"], resolution_status="retake_queued",
                retake_batch_id=batch_id)
            return {"status": "retake_queued", "job_id": job["job_id"], "batch_id": batch_id}
        self.store.resolve_director_review(job_id=job["job_id"], resolution_status="blocked",
            error={"code": "director_image_review_blocked", "message": str(decision.get("reason") or "Visual review was inconclusive.")[:1200]})
        return {"status": "blocked", "job_id": job["job_id"]}

    def _collect_completed(self, job: dict[str, Any], prompt_id: str,
                           history: dict[str, Any]) -> dict[str, Any]:
        project_id = _project_id(job.get("project_id"))
        project_output = (self.workspace_output(project_id) if self.workspace_output else self.output_root / project_id).resolve()
        destination = (project_output / "production" / "image_jobs" / job["job_id"]).resolve()
        if not project_output.is_relative_to(self.output_root) or not destination.is_relative_to(project_output):
            raise ValueError("Resolved image candidate output path escaped the project output root.")
        grouped = (job.get("settings") or {}).get("multi_angle_batch") is True
        output_history = history
        members = [job]
        if grouped:
            members = self.store.list_batch(project_id=project_id, batch_id=job["batch_id"])["jobs"]
            expected = len(job["settings"]["world_views"])
            outputs = history.get("outputs", {}).get("116", {})
            if len(members) != expected or len(outputs.get("images", [])) != expected:
                raise RuntimeError(f"Directional workflow must return exactly {expected} saved views; outputs remain held for recovery.")
            # Camera nodes can return UI previews. Only collect the final SaveImage.
            output_history = {**history, "outputs": {"116": outputs}}
        items = collect_outputs(output_history, destination_dir=destination, comfy_url=self.comfy_url)
        images = [item for item in items if item.get("kind") == "image"]
        if not images or (grouped and len(images) != len(members)):
            raise RuntimeError("ComfyUI completed but did not return every verified image output.")
        # Finish the leader last: restart reconciliation always retains its remote
        # prompt until every view has a durable asset, without a second submission.
        ordered = list(zip(members, images)) if grouped else [(job, images[0])]
        if grouped:
            ordered = ordered[1:] + ordered[:1]
        assets = {}
        for member, image in ordered:
            if member.get("status") == "completed":
                duplicate = (destination / image["relative_path"]).resolve()
                if duplicate.is_relative_to(destination):
                    duplicate.unlink(missing_ok=True)
                assets[member["job_id"]] = member["output_asset_id"]
                continue
            assets[member["job_id"]] = self._register_completed_image(
                member, prompt_id, image, project_output, destination, job["job_id"])
        self._cleanup_staging_if_batch_settled(job)
        self._cleanup_owned_comfy_outputs(job["graph"], history)
        self.release_idle(comfy_url=self.comfy_url)
        return {"status": "completed", "job_id": job["job_id"], "asset_id": assets[job["job_id"]]}

    def _register_completed_image(self, job: dict[str, Any], prompt_id: str,
                                  image: dict[str, Any], project_output: Path,
                                  destination: Path, output_job_id: str) -> str:
        relative_path = (Path("production") / "image_jobs" / output_job_id / image["relative_path"]).as_posix()
        metadata = {"production_image_job": {
            "job_id": job["job_id"], "batch_id": job["batch_id"], "run_id": job["run_id"],
            "workflow_id": job["workflow_id"], "workflow_version": job["workflow_version"],
            "prompt": job["prompt"], "seed": job["seed"], "settings": job["settings"],
            "candidate_index": job["candidate_index"], "comfy_prompt_id": prompt_id,
            "status": "completed", "accepted": False, "intended_role": job["asset_role"]}}
        transient_token = (job.get("settings") or {}).get("vibe_t2i_transient_token")
        if isinstance(transient_token, str):
            metadata["vibe_t2i_transient"] = {"token": transient_token}
        if job.get("workflow_id") == "qwen_image_multi_angle_2511":
            views = (job.get("settings") or {}).get("world_views")
            index = job["candidate_index"] - 1
            if not isinstance(views, list) or index >= len(views) or not isinstance(views[index], dict):
                raise RuntimeError("Qwen multi-angle candidate is missing its saved view label.")
            view = views[index]
            if type(view.get("label")) is not str or type(view.get("azimuth")) is not int:
                raise RuntimeError("Qwen multi-angle candidate has invalid saved view metadata.")
            metadata["production_image_job"]["world_view"] = view
            subject = "Character" if job.get("asset_role") == "character_view" else "World"
            metadata["description"] = f"{subject} reference · {view['label']} view"
            metadata["tags"] = [subject.lower(), "directional view", view["label"].lower()]
        asset = self.register_output(project_id=job["project_id"], relative_path=relative_path,
            role="image_candidate", metadata=metadata)
        if asset.get("deduplicated") and asset.get("relative_path") and asset["relative_path"] != relative_path:
            duplicate = (project_output / relative_path).resolve()
            if duplicate.is_relative_to(destination):
                duplicate.unlink(missing_ok=True)
        self.store.transition(job["job_id"], "completed", output_asset_id=asset["asset_id"])
        template_sha = (job.get("settings") or {}).get("workflow_template_sha256")
        if isinstance(template_sha, str):
            image_path = (destination / image["relative_path"]).resolve()
            if image_path.is_relative_to(destination) and image_path.is_file():
                try:
                    output_sha = hashlib.sha256(image_path.read_bytes()).hexdigest()
                    recorded = record_successful_image_smoke(smoke_root=SMOKE_ROOT,
                        workflow_id=job["workflow_id"], workflow_version=job["workflow_version"],
                        workflow_sha256=template_sha, output_sha256=output_sha,
                        job_id=job["job_id"])
                    if not recorded:
                        LOGGER.warning("Image completed without workflow-smoke evidence job=%s workflow=%s",
                            job["job_id"], job["workflow_id"])
                except OSError as exc:
                    # The render and asset are already durably completed. Smoke
                    # evidence is a convenience gate for later Assisted runs;
                    # its storage must never reverse or obscure that success.
                    LOGGER.warning("Could not persist image workflow-smoke evidence job=%s workflow=%s error=%s",
                        job["job_id"], job["workflow_id"], exc)
        return asset["asset_id"]

    def _cleanup_staging_if_batch_settled(self, job: dict[str, Any]) -> None:
        settings = job.get("settings") or {}
        if settings.get("image_references"):
            owner_id = f"image-{job['job_id']}"
            try:
                current = self.store.get_job(project_id=job["project_id"], job_id=job["job_id"])
            except Exception:
                return
            if not current or current.get("status") not in {"completed", "failed", "cancelled"}:
                return
            if self.cleanup_staging is not None:
                try:
                    self.cleanup_staging(owner_id)
                except Exception:
                    LOGGER.warning("Could not clean image reference staging owner=%s job=%s",
                        owner_id, job["job_id"], exc_info=True)
            return
        owner_id = settings.get("staging_owner_id")
        if not owner_id or self.cleanup_staging is None:
            return
        if not self.store.batch_is_settled(project_id=job["project_id"], batch_id=job["batch_id"]):
            return
        try:
            self.cleanup_staging(str(owner_id))
        except Exception:
            LOGGER.warning("Could not clean settled image batch staging owner=%s batch=%s",
                           owner_id, job["batch_id"], exc_info=True)

    def _comfy_busy_reason(self) -> str | None:
        try:
            queue = self.request_json(f"{self.comfy_url}/queue", timeout_seconds=10)
        except Exception as exc:
            return f"Cannot verify ComfyUI queue; keeping this image candidate backend-queued ({type(exc).__name__}: {exc})."
        running, pending = queue.get("queue_running"), queue.get("queue_pending")
        if not isinstance(running, list) or not isinstance(pending, list):
            return "ComfyUI returned an invalid queue response; keeping this image candidate backend-queued."
        if (running or pending) and not get_workload_policy()["allow_simultaneous_runs"]:
            return f"ComfyUI is busy (running={len(running)}, pending={len(pending)}); candidate remains in the Vibe Director queue."
        return None

    def _cleanup_owned_comfy_outputs(self, graph: dict[str, Any], history: dict[str, Any]) -> None:
        """Remove only exact Comfy output files matching this job's saved prefix.

        The canonical copied output has already been registered by asset ID;
        this prevents a second retained copy in ComfyUI/output. Unknown paths
        and any non-output type are deliberately left untouched.
        """
        prefixes = {str(node.get("inputs", {}).get("filename_prefix", ""))
                    for node in graph.values() if node.get("class_type") == "SaveImage"}
        prefixes.discard("")
        root = self.comfy_output_root.resolve()
        for node_output in history.get("outputs", {}).values():
            rows = list(node_output.get("images", [])) + list(node_output.get("gifs", [])) + list(node_output.get("videos", [])) + list(node_output.get("audio", [])) + list(node_output.get("audios", []))
            for item in rows:
                if item.get("type", "output") != "output":
                    continue
                filename = str(item.get("filename", ""))
                subfolder = str(item.get("subfolder", ""))
                if not filename or Path(filename).name != filename:
                    continue
                if subfolder and any(part in {"", ".", ".."} for part in subfolder.split("/")):
                    continue
                relative = (Path(subfolder) / filename).as_posix() if subfolder else filename
                owned = False
                for prefix in prefixes:
                    prefix_path = Path(prefix)
                    if Path(subfolder) == prefix_path.parent and filename.startswith(prefix_path.name):
                        owned = True
                        break
                if not owned:
                    continue
                source = (root / relative).resolve()
                if not source.is_relative_to(root) or not source.is_file():
                    continue
                try:
                    source.unlink()
                except PermissionError:
                    if not self._remove_owned_comfy_output_as_container_root(source, root):
                        LOGGER.warning("Could not remove owned duplicate Comfy output %s; preserving it", source, exc_info=True)
                except OSError:
                    LOGGER.warning("Could not remove owned duplicate Comfy output %s; preserving it", source, exc_info=True)

    @staticmethod
    def _remove_owned_comfy_output_as_container_root(source: Path, output_root: Path) -> bool:
        """Retry unlink through Docker only for a path already proven job-owned.

        ComfyUI commonly creates output files as root/nobody inside its
        container, leaving the host user unable to unlink the
        duplicate. The caller has already matched the saved filename prefix
        and constrained `source` beneath the canonical Comfy output root.
        """
        docker = shutil.which("docker")
        container = comfy_container_name()
        try:
            relative = source.resolve().relative_to(output_root.resolve())
        except (OSError, ValueError):
            return False
        inner_root = Path(os.environ.get("VIBE_DIRECTOR_COMFYUI_CONTAINER_OUTPUT")
            or os.environ.get("STORY_BUILDER_COMFYUI_CONTAINER_OUTPUT", "/workspace/ComfyUI/output"))
        inner_path = (inner_root / relative).as_posix()
        if (not docker or not inner_root.is_absolute() or ".." in inner_root.parts
                or not inner_path.startswith(inner_root.as_posix().rstrip("/") + "/")):
            return False
        try:
            removed = subprocess.run([docker, "exec", "--user", "0", container,
                "rm", "-f", "--", inner_path], capture_output=True, text=True,
                timeout=15, check=False)
            if removed.returncode != 0:
                return False
            verified = subprocess.run([docker, "exec", "--user", "0", container,
                "test", "!", "-e", inner_path], capture_output=True, text=True,
                timeout=10, check=False)
            return verified.returncode == 0 and not source.exists()
        except (OSError, subprocess.SubprocessError):
            return False

    def _wait_history(self, job_id: str, prompt_id: str, *,
                      workload_started_at: str | None = None) -> dict[str, Any] | None:
        watchdog = ensure_prompt_watchdog(comfy_url=self.comfy_url, prompt_id=prompt_id)
        deadline = time.monotonic() + self.timeout_seconds
        errors = 0
        next_telemetry = 0.0
        next_limit_check = 0.0
        while time.monotonic() < deadline:
            if time.monotonic() >= next_limit_check:
                try:
                    watchdog.check()
                    point = self.operating_point_reader()
                except GPUAdmissionError as exc:
                    self.store.transition(job_id, "recovery_required", error={
                        "code": "gpu_limit_monitor_failed", "message": str(exc), "prompt_id": prompt_id})
                    return None
                record_gpu_telemetry(DEFAULT_TELEMETRY_PATH,
                    {"recorded_at": datetime.now(timezone.utc).isoformat(), "gpu": point,
                     "temperature_cutoff_c": GPU_RENDER_TEMP_CUTOFF,
                     "graphics_clock_ceiling_mhz": GPU_RENDER_CLOCK_CEILING_MHZ},
                    workload_id=job_id, phase="gpu_limit_watch")
                violation = (point["temperature_c"] >= GPU_RENDER_TEMP_CUTOFF or
                             point["graphics_clock_mhz"] > GPU_RENDER_CLOCK_CEILING_MHZ)
                if violation:
                    interrupted, detail = interrupt_if_owned_prompt(comfy_url=self.comfy_url,
                        prompt_id=prompt_id, request_json=self.request_json)
                    error = {"code": "gpu_render_limit_reached", "temperature_c": point["temperature_c"],
                        "graphics_clock_mhz": point["graphics_clock_mhz"], "interrupt_requested": interrupted,
                        "message": detail, "prompt_id": prompt_id}
                    self.store.transition(job_id, "recovery_required", error=error)
                    LOGGER.error("GPU render guard reached limit job=%s prompt=%s details=%s", job_id, prompt_id, error)
                    return None
                next_limit_check = time.monotonic() + 1.0
            if time.monotonic() >= next_telemetry:
                try:
                    sample = self.gpu_inspector(comfy_url=self.comfy_url, expected_prompt_id=prompt_id,
                                                workload_started_at=workload_started_at)
                except GPUAdmissionError as exc:
                    self.store.transition(job_id, "recovery_required", error={"code": "gpu_monitor_failed", "message": str(exc)})
                    return None
                record_gpu_telemetry(DEFAULT_TELEMETRY_PATH, sample, workload_id=job_id, phase="render")
                next_telemetry = time.monotonic() + 10
            try:
                history = self.request_json(f"{self.comfy_url}/history/{prompt_id}", timeout_seconds=30)
                errors = 0
                prompt = history.get(prompt_id)
                if prompt:
                    status = prompt.get("status", {})
                    if status.get("status_str") == "error" or status.get("completed"):
                        return prompt
            except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
                errors += 1
                if errors == 1 or errors % 10 == 0:
                    LOGGER.warning("Image history temporarily unavailable job=%s prompt=%s failures=%s error=%s",
                        job_id, prompt_id, errors, exc)
            self.sleep(self.poll_interval)
        self.store.transition(job_id, "recovery_required", error={
            "code": "image_render_timeout", "message": "Render exceeded its wait deadline; reconcile this exact prompt before retrying."})
        return None


class ProductionImageWorkerSupervisor:
    """Small idle-safe consumer; no ComfyUI calls are made without queued image work."""

    def __init__(self, worker: ProductionImageWorker, *, idle_sleep_seconds: float = 2.0,
                 advance_assisted_stages: Callable[[], Any] | None = None):
        self.worker = worker
        self.idle_sleep_seconds = max(0.25, idle_sleep_seconds)
        self.advance_assisted_stages = advance_assisted_stages
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> bool:
        if self._thread and self._thread.is_alive():
            return False
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="production-image-worker", daemon=True)
        self._thread.start()
        return True

    def stop(self, timeout_seconds: float = 2.0) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=max(0.0, timeout_seconds))

    def _run(self) -> None:
        LOGGER.info("Production image worker started; ComfyUI is contacted only for queued image jobs")
        while not self._stop.is_set():
            try:
                recovery = self.worker.reconcile_recovery_once()
                result = self.worker.process_one()
                review_result = self.worker.review_next_candidate()
                status = result.get("status")
                if status == "idle" and self.advance_assisted_stages is not None:
                    self.advance_assisted_stages()
                if status in {"idle", "waiting_for_comfyui", "waiting_for_gpu", "recovery_required"} and review_result.get("status") in {"idle", "reviewer_unavailable", "accepted", "blocked", "rejected", "retake_queued"}:
                    delay = self.idle_sleep_seconds if not recovery.get("observed") else 0.05
                    self._stop.wait(delay)
            except Exception:
                LOGGER.exception("Production image worker iteration failed; retrying after bounded idle")
                self._stop.wait(self.idle_sleep_seconds)
        LOGGER.info("Production image worker stopped")
