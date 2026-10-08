"""Explicitly enabled durable consumer for isolated H3 T2V jobs.

The API server never imports or starts this process. An operator starts it in
a separate terminal with ``--enable-worker`` after choosing product paths.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import threading
import time
from pathlib import Path

from story_builder.isolated_server import _runtime_guard
from story_builder.services.gpu_runtime import read_gpu_operating_point
from story_builder.services.isolated_video_jobs import (
    IsolatedVideoJobs, build_worker, make_output_collector,
)
from story_builder.services.production_job_worker import ProductionWorkerSupervisor
from story_builder.services.production_ledger import ProductionLedger
from story_builder.services.production_t2v_capability import t2v_capability


class _CapabilityGatedWorker:
    """Preserve the source supervisor API; gate queued claims and recheck prepare."""
    def __init__(self, worker, ledger, status_writer):
        self._worker = worker
        self._ledger = ledger
        self._write = status_writer

    def __getattr__(self, name):
        return getattr(self._worker, name)

    def reconcile_existing_once(self):
        # Existing prompt IDs are observed/reconciled after restart. This path
        # never creates a new submission; the source worker owns no-resubmit.
        result = self._worker.reconcile_existing_once()
        self._write("running", "Reconciling previously authorized jobs.")
        return result

    def review_next_take(self):
        # Isolated Manual review belongs to the user. The source worker returns
        # reviewer_unavailable without a Director, which would bypass the
        # supervisor idle sleep and spin; preserve its idle contract here.
        return {"status": "idle"}

    def process_one(self):
        with self._ledger._connect() as db:
            queued = db.execute("SELECT 1 FROM production_takes WHERE status='queued' LIMIT 1").fetchone()
        if queued:
            capability = t2v_capability()
            guard = _runtime_guard(read_gpu_operating_point)
            if not capability.get("available") or not guard.get("safe_to_submit"):
                reason = "; ".join(filter(None, [capability.get("disabled_reason"), guard.get("reason")]))
                self._write("waiting_for_readiness", reason or "T2V readiness is unavailable.")
                return {"status": "idle", "waiting_for": "readiness", "reason": reason}
        self._write("running", None)
        result = self._worker.process_one()
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
                       "reason": reason, "updated_unix": time.time()}
            temporary = path.with_suffix(".tmp")
            temporary.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
            os.replace(temporary, path)

    def touch():
        with lock:
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                payload = {"enabled": True, "pid": pid, "state": "starting"}
            payload["updated_unix"] = time.time()
            temporary = path.with_suffix(".tmp")
            temporary.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
            os.replace(temporary, path)

    write.touch = touch
    return write


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
    db_path = Path(os.environ.get("VIBE_DIRECTOR_LEDGER_PATH", root / "storage/production/ledger.sqlite3")).expanduser().resolve()
    try:
        db_path.relative_to(root)
    except ValueError as exc:
        raise SystemExit("VIBE_DIRECTOR_LEDGER_PATH must remain under VIBE_DIRECTOR_DATA_DIR.") from exc
    graph = Path(os.environ["VIBE_DIRECTOR_GRAPH_PATH"]).expanduser().resolve() if os.environ.get("VIBE_DIRECTOR_GRAPH_PATH") else None
    comfy_url = os.environ.get("COMFYUI_URL", "http://127.0.0.1:3008").rstrip("/")
    status_path = root / "runtime/isolated-worker-status.json"
    write_status = _status_writer(status_path, os.getpid())
    write_status("starting", None)

    ledger = ProductionLedger(db_path)
    IsolatedVideoJobs(ledger, graph_path=graph)  # ensures metadata tables exist
    collector = make_output_collector(data_root=root, ledger=ledger, comfy_url=comfy_url)
    def require_ready_for_prepare():
        capability = t2v_capability()
        guard = _runtime_guard(read_gpu_operating_point)
        if not capability.get("available") or not guard.get("safe_to_submit"):
            reason = "; ".join(filter(None, [capability.get("disabled_reason"), guard.get("reason")]))
            raise RuntimeError(reason or "T2V readiness failed again during prepare.")
    worker = build_worker(ledger, comfy_url=comfy_url, collect=collector,
                          graph_path=graph, prepare_guard=require_ready_for_prepare)
    gated = _CapabilityGatedWorker(worker, ledger, write_status)
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
