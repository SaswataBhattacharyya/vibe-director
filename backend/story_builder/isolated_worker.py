"""Explicitly enabled durable consumer for isolated H3 T2V jobs.

The API server never imports or starts this process. An operator starts it in
a separate terminal with ``--enable-worker`` after choosing product paths.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import signal
import threading
import time
from contextlib import contextmanager
from pathlib import Path

from story_builder.isolated_server import _runtime_guard
from story_builder.services.gpu_runtime import read_gpu_operating_point
from story_builder.services.isolated_video_jobs import (
    IsolatedVideoJobs, build_worker, make_output_collector,
)
from story_builder.services.story_authoring import StoryAuthoring
from story_builder.services.production_job_worker import ProductionWorkerSupervisor
from story_builder.services.production_ledger import ProductionLedger
from story_builder.services.production_t2v_capability import (
    record_successful_t2v_smoke, t2v_capability,
)
from story_builder.services.production_fl2va_capability import fl2va_capability
from story_builder.services.isolated_fl2va_contract import WORKFLOW_ID as FL2VA_WORKFLOW_ID
from story_builder.services.isolated_r2v_contract import WORKFLOW_ID as R2V_WORKFLOW_ID
from story_builder.services.production_fl2va_capability import record_successful_fl2va_smoke
from story_builder.services.production_r2v_capability import r2v_capability, record_successful_r2v_smoke
from story_builder.services.production_image_workflows import comfyui_root
from story_builder.services.fully_automated_identity import (
    IdentityReviewProcessor, IdentityReviewStore,
    enqueue_completed_full_run_identity_reviews,
)
from story_builder.services.production_image_selection import ProductionImageSelection


class _CapabilityGatedWorker:
    """Preserve the source supervisor API; gate queued claims and recheck prepare."""
    def __init__(self, worker, ledger, status_writer, jobs=None,
                 fl2va_provider=None, r2v_provider=None, t2v_provider=None,
                 identity_processor=None, identity_store=None, story=None,
                 image_selections=None, data_root=None):
        self._worker = worker
        self._ledger = ledger
        self._write = status_writer
        self._jobs = jobs
        self._fl2va_provider = fl2va_provider or fl2va_capability
        self._r2v_provider = r2v_provider or r2v_capability
        self._t2v_provider = t2v_provider or t2v_capability
        self._identity_processor = identity_processor
        self._identity_store = identity_store
        self._story = story
        self._image_selections = image_selections
        self._data_root = data_root
        from story_builder.services.t2v_batches import T2VBatches
        self._t2v_batches = T2VBatches(jobs) if jobs is not None else None

    def __getattr__(self, name):
        return getattr(self._worker, name)

    def reconcile_existing_once(self):
        # Existing prompt IDs are observed/reconciled after restart. This path
        # never creates a new submission; the source worker owns no-resubmit.
        result = self._worker.reconcile_existing_once()
        self._write("running", "Reconciling previously authorized jobs.")
        return result

    def review_next_take(self):
        # Full-mode runs advance only after a durable clip has completed.
        advanced = False
        # References and crops are explicit user choices; never delay a run to derive them.
        if self._jobs is not None:
            with self._ledger._connect() as db:
                runs = db.execute("SELECT workspace_id,screenplay_revision_id FROM fully_automated_runs WHERE run_state IN ('running','waiting_for_readiness')").fetchall()
                assisted_runs = db.execute("SELECT workspace_id,screenplay_revision_id FROM assisted_video_runs WHERE run_state IN ('running','waiting_for_readiness')").fetchall()
            for run in runs:
                def readiness(workflow_id):
                    if workflow_id == FL2VA_WORKFLOW_ID:
                        capability = self._fl2va_provider()
                    elif workflow_id == R2V_WORKFLOW_ID:
                        capability = self._r2v_provider()
                    else:
                        capability = self._t2v_provider()
                    guard = _runtime_guard(read_gpu_operating_point)
                    # Owner-started Full runs verify their own first live output.
                    # Model/graph admission and the runtime guard still apply.
                    t2v_ready = capability.get("available")
                    capability_reason = capability.get("disabled_reason")
                    reason = "; ".join(filter(None, [capability_reason, guard.get("reason")]))
                    return {"available": bool(t2v_ready and guard.get("safe_to_submit")), "reason": reason}
                result = self._jobs.advance_fully_automated_run(run["workspace_id"], run["screenplay_revision_id"], readiness=readiness)
                if result.get("status") == "queued":
                    self._write("running", None)
                    advanced = True
                elif result.get("status") == "waiting_for_readiness":
                    self._write("waiting_for_readiness", result.get("reason"))
                elif result.get("status") == "paused":
                    self._write("paused", (result.get("job") or {}).get("error") or "A Fully automated run needs recovery.")
            for run in assisted_runs:
                def readiness(workflow_id):
                    if workflow_id == FL2VA_WORKFLOW_ID:
                        capability = self._fl2va_provider()
                    elif workflow_id == R2V_WORKFLOW_ID:
                        capability = self._r2v_provider()
                    elif workflow_id == "minimax_h3_t2v_local_v1":
                        capability = self._t2v_provider()
                    else:
                        capability = {"available": False, "disabled_reason": "Unsupported Assisted workflow."}
                    guard = _runtime_guard(read_gpu_operating_point)
                    ready = capability.get("automation_available", capability.get("available"))
                    reason = "; ".join(filter(None, [capability.get("automation_disabled_reason") or capability.get("disabled_reason"), guard.get("reason")]))
                    return {"available": bool(ready and guard.get("safe_to_submit")), "reason": reason}
                result = self._jobs.advance_assisted_video_run(
                    run["workspace_id"], run["screenplay_revision_id"], readiness=readiness)
                if result.get("status") == "queued":
                    self._write("running", None)
                    advanced = True
                elif result.get("status") == "waiting_for_readiness":
                    self._write("waiting_for_readiness", result.get("reason"))
                elif result.get("status") == "paused":
                    self._write("paused", result.get("reason") or "An Assisted run needs recovery.")
        if self._t2v_batches is not None:
            def batch_readiness():
                capability = self._t2v_provider()
                guard = _runtime_guard(read_gpu_operating_point)
                return {"available": bool(capability.get("available") and guard.get("safe_to_submit")),
                        "reason": "; ".join(filter(None, [capability.get("disabled_reason"), guard.get("reason")]))}
            advanced = self._t2v_batches.advance_active(batch_readiness) or advanced
        if advanced:
            return {"status": "queued"}
        # Isolated Manual review belongs to the user. Preserve the idle contract.
        return {"status": "idle"}

    def process_one(self):
        with self._ledger._connect() as db:
            queued = db.execute("SELECT j.job_id,j.request_json FROM production_takes t JOIN isolated_video_jobs j USING(job_id) WHERE t.status='queued' ORDER BY t.created_at LIMIT 1").fetchone()
        if queued:
            try:
                request = json.loads(queued["request_json"])
                workflow_id = request.get("workflow_id")
            except (TypeError, json.JSONDecodeError):
                workflow_id = None
            if workflow_id == FL2VA_WORKFLOW_ID:
                capability = self._fl2va_provider()
            elif workflow_id == R2V_WORKFLOW_ID:
                capability = self._r2v_provider()
            elif workflow_id == "minimax_h3_t2v_local_v1":
                capability = self._t2v_provider()
            else:
                capability = {"available": False, "disabled_reason": "Queued isolated workflow ID is unsupported."}
            with self._ledger._connect() as db:
                full_run_job = db.execute("SELECT 1 FROM fully_automated_run_clips WHERE job_id=? LIMIT 1",
                    (queued["job_id"],)).fetchone()
                assisted_run_job = db.execute("SELECT 1 FROM assisted_video_run_clips WHERE job_id=? LIMIT 1",
                    (queued["job_id"],)).fetchone()
            workflow_ready = capability.get("available")
            if assisted_run_job:
                workflow_ready = capability.get("automation_available", workflow_ready)
            guard = _runtime_guard(read_gpu_operating_point)
            if not workflow_ready or not guard.get("safe_to_submit"):
                capability_reason = (capability.get("automation_disabled_reason")
                    if assisted_run_job and not workflow_ready
                    else capability.get("disabled_reason"))
                reason = "; ".join(filter(None, [capability_reason, guard.get("reason")]))
                self._write("waiting_for_readiness", reason or "T2V readiness is unavailable.")
                return {"status": "idle", "waiting_for": "readiness", "reason": reason}
        self._write("running", None)
        result = self._worker.process_one()
        if result.get("status") == "needs_review" and result.get("take_id") and self._data_root is not None:
            # A successful owner-started render, including a Full run, establishes
            # evidence from the real collected output. Evidence persistence is best-effort
            # and must never change the already durable take outcome.
            try:
                with self._ledger._connect() as db:
                    row = db.execute("SELECT t.job_id,t.output_hashes_json,j.request_json FROM production_takes t JOIN isolated_video_jobs j USING(job_id) WHERE t.take_id=? LIMIT 1",
                        (result["take_id"],)).fetchone()
                    assisted = (db.execute("SELECT 1 FROM assisted_video_run_clips WHERE job_id=? LIMIT 1",
                        (row["job_id"],)).fetchone() if row else None)
                request = json.loads(row["request_json"]) if row and not assisted else {}
                outputs = json.loads(row["output_hashes_json"] or "[]") if row and not assisted else []
                if request.get("workflow_id") == "minimax_h3_t2v_local_v1":
                    for output in outputs:
                        if record_successful_t2v_smoke(data_root=Path(self._data_root),
                                workflow_sha256=request.get("workflow_sha256", ""),
                                job_id=row["job_id"], output=output):
                            break
                elif request.get("workflow_id") == FL2VA_WORKFLOW_ID:
                    for output in outputs:
                        if record_successful_fl2va_smoke(data_root=Path(self._data_root),
                                request=request, job_id=row["job_id"], output=output):
                            break
                elif request.get("workflow_id") == R2V_WORKFLOW_ID:
                    for output in outputs:
                        if record_successful_r2v_smoke(data_root=Path(self._data_root),
                                request=request, job_id=row["job_id"], output=output):
                            break
            except (OSError, TypeError, ValueError, KeyError, json.JSONDecodeError):
                pass
        if result.get("status") == "waiting_for_comfyui":
            self._write("waiting_for_comfyui", result.get("reason"))
            return {**result, "status": "idle", "waiting_for": "comfyui"}
        return result


def _status_writer(path: Path, pid: int):
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = threading.Lock()

    def write(state: str, reason: str | None = None):
        with lock:
            payload = {"enabled": True, "pid": pid, "state": state,
                       "reason": reason, "updated_unix": time.time(),
                       "supported_workflows": ["minimax_h3_t2v_local_v1", FL2VA_WORKFLOW_ID, R2V_WORKFLOW_ID]}
            temporary = path.with_suffix(".tmp")
            temporary.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
            os.replace(temporary, path)

    def touch():
        with lock:
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                payload = {"enabled": True, "pid": pid, "state": "starting",
                    "supported_workflows": ["minimax_h3_t2v_local_v1", FL2VA_WORKFLOW_ID, R2V_WORKFLOW_ID]}
            payload["updated_unix"] = time.time()
            temporary = path.with_suffix(".tmp")
            temporary.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
            os.replace(temporary, path)

    write.touch = touch
    return write


@contextmanager
def isolated_worker_lifetime_lock(db_path: Path):
    """Keep one production-video supervisor polling a durable ledger at a time."""
    canonical_db = Path(db_path).expanduser().resolve()
    key = hashlib.sha256(str(canonical_db).encode("utf-8")).hexdigest()[:24]
    lock_path = canonical_db.parent / f".{canonical_db.name}.{key}.worker.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = lock_path.open("a+")
    try:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError(f"A production-video worker already owns this ledger: {canonical_db}") from exc
        yield
    finally:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--enable-worker", action="store_true", help="explicitly enable durable ComfyUI consumption")
    args = parser.parse_args()
    enabled_env = os.environ.get("VIBE_DIRECTOR_ENABLE_WORKER", "").strip() == "1"
    if not (args.enable_worker or enabled_env):
        raise SystemExit("Worker is disabled. Pass --enable-worker or set VIBE_DIRECTOR_ENABLE_WORKER=1 explicitly.")
    data = os.environ.get("VIBE_DIRECTOR_DATA_DIR")
    if not data:
        raise SystemExit("Set VIBE_DIRECTOR_DATA_DIR to a product-owned data directory.")
    root = Path(data).expanduser().resolve()
    db_path = Path(os.environ.get("VIBE_DIRECTOR_LEDGER_PATH", root / "services/production/ledger.sqlite3")).expanduser().resolve()
    try:
        db_path.relative_to(root)
    except ValueError as exc:
        raise SystemExit("VIBE_DIRECTOR_LEDGER_PATH must remain under VIBE_DIRECTOR_DATA_DIR.") from exc
    try:
        with isolated_worker_lifetime_lock(db_path):
            _run_worker(root, db_path)
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc


def _run_worker(root: Path, db_path: Path) -> None:
    graph = Path(os.environ["VIBE_DIRECTOR_GRAPH_PATH"]).expanduser().resolve() if os.environ.get("VIBE_DIRECTOR_GRAPH_PATH") else None
    comfy_url = os.environ.get("COMFYUI_URL", "http://127.0.0.1:3008").rstrip("/")
    status_path = root / "runtime/isolated-worker-status.json"
    write_status = _status_writer(status_path, os.getpid())
    write_status("starting", None)

    ledger = ProductionLedger(db_path)
    story = StoryAuthoring(ledger, data_root=root)
    jobs = IsolatedVideoJobs(ledger, graph_path=graph, story=story, media_root=root,
        fl2va_capability_provider=lambda: fl2va_capability(comfy_url=os.environ.get("COMFYUI_URL", "http://127.0.0.1:3008")),
        r2v_capability_provider=lambda: r2v_capability(comfy_url=os.environ.get("COMFYUI_URL", "http://127.0.0.1:3008")))
    identity_store = IdentityReviewStore(db_path)
    identity_processor = IdentityReviewProcessor(identity_store, data_root=root)
    image_jobs_path = Path(os.environ.get("VIBE_DIRECTOR_IMAGE_JOBS_DB",
        root / "services/production/image-jobs.sqlite3")).expanduser().resolve()
    try:
        image_jobs_path.relative_to(root)
    except ValueError as exc:
        raise SystemExit("VIBE_DIRECTOR_IMAGE_JOBS_DB must remain under VIBE_DIRECTOR_DATA_DIR.") from exc
    image_selections = ProductionImageSelection(image_jobs_path)
    collector = make_output_collector(data_root=root, ledger=ledger, comfy_url=comfy_url)
    fl2va_provider = lambda: fl2va_capability(comfy_url=comfy_url)
    r2v_provider = lambda: r2v_capability(comfy_url=comfy_url)
    def require_ready_for_prepare():
        capability = t2v_capability()
        guard = _runtime_guard(read_gpu_operating_point)
        if not capability.get("available") or not guard.get("safe_to_submit"):
            reason = "; ".join(filter(None, [capability.get("disabled_reason"), guard.get("reason")]))
            raise RuntimeError(reason or "T2V readiness failed again during prepare.")
    def require_fl2va_ready_for_prepare(workflow_id: str):
        if workflow_id != FL2VA_WORKFLOW_ID:
            return
        capability = fl2va_provider()
        guard = _runtime_guard(read_gpu_operating_point)
        if not capability.get("available") or not guard.get("safe_to_submit"):
            reason = "; ".join(filter(None, [capability.get("disabled_reason"), guard.get("reason")]))
            raise RuntimeError(reason or "FL2VA readiness failed again before staging.")
    def require_r2v_ready_for_prepare(workflow_id: str):
        if workflow_id != R2V_WORKFLOW_ID:
            return
        capability = r2v_provider()
        guard = _runtime_guard(read_gpu_operating_point)
        if not capability.get("available") or not guard.get("safe_to_submit"):
            reason = "; ".join(filter(None, [capability.get("disabled_reason"), guard.get("reason")]))
            raise RuntimeError(reason or "R2V readiness failed again before staging.")
    def pinned_style_selection(workspace_id: str):
        if not re.fullmatch(r"story-[a-f0-9]{12}", workspace_id):
            return None
        return story.get_workspace(workspace_id, include_source=False).get("style_selection")
    worker = build_worker(ledger, comfy_url=comfy_url, collect=collector,
                          graph_path=graph, media_root=root,
                          comfy_input_root=comfyui_root() / "input",
                          r2v_owner_root=root / "runtime/r2v-media-owners",
                          prepare_guard=require_ready_for_prepare,
                          workflow_prepare_guard=lambda workflow_id: (
                              require_fl2va_ready_for_prepare(workflow_id),
                              require_r2v_ready_for_prepare(workflow_id)),
                          fl2va_capability_provider=fl2va_provider,
                          r2v_capability_provider=r2v_provider,
                          style_selection_resolver=pinned_style_selection)
    gated = _CapabilityGatedWorker(worker, ledger, write_status, jobs=jobs,
        fl2va_provider=fl2va_provider, r2v_provider=r2v_provider,
        identity_processor=identity_processor, identity_store=identity_store,
        story=story, image_selections=image_selections, data_root=root)
    supervisor = ProductionWorkerSupervisor(gated)
    stopped = False

    def stop(_signum, _frame):
        nonlocal stopped
        stopped = True
        supervisor.stop(timeout_seconds=10)

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    supervisor.start()
    write_status("running", None)
    print(f"Isolated durable worker enabled; ledger={db_path}; ComfyUI={comfy_url}", flush=True)
    try:
        while not stopped:
            write_status.touch()
            time.sleep(2)
    finally:
        supervisor.stop(timeout_seconds=10)
        write_status("stopped", None)


if __name__ == "__main__":
    main()
