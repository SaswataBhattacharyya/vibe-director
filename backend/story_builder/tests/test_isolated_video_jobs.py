from __future__ import annotations

import tempfile
import unittest
import urllib.error
import warnings
import io
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from story_builder.services.isolated_video_contract import EXPECTED_GRAPH_SHA256
from story_builder.services.isolated_video_jobs import (
    IsolatedJobConflict, IsolatedVideoJobs, build_worker, prepare_isolated_take,
)
from story_builder.services.production_job_worker import ProductionJobWorker, PreparedTake
from story_builder.services.production_ledger import ProductionLedger
from story_builder.isolated_server import create_app

ROOT = Path(__file__).resolve().parents[1]
GRAPH = ROOT / "workflows/api/minimax_h3_t2v_api.json"


def request(**changes):
    payload = {"workflow_id": "minimax_h3_t2v_local_v1", "workflow_version": 1,
        "workflow_sha256": EXPECTED_GRAPH_SHA256, "prompt": "A quiet street at dusk.",
        "duration_seconds": 6, "aspect_ratio": "16:9", "resolution_preset": 0.98,
        "steps": 20, "seed": 1, "references": []}
    payload.update(changes)
    return payload


class IsolatedVideoJobTests(unittest.TestCase):
    def setUp(self):
        warnings.simplefilter("ignore", ResourceWarning)
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.db_path = Path(self.temporary.name) / "product.sqlite3"
        self.ledger = ProductionLedger(self.db_path)
        self.jobs = IsolatedVideoJobs(self.ledger, graph_path=GRAPH)

    def create(self, *, key="key-1", payload=None, **extra):
        return self.jobs.create_job(workspace_id="workspace-a", clip_id="clip-1",
            idempotency_key=key, request=payload or request(), **extra)

    def test_isolated_supervisor_idle_contract_without_director(self):
        from unittest.mock import Mock
        from story_builder.isolated_worker import _CapabilityGatedWorker
        source = Mock()
        source.process_one.return_value = {"status": "idle"}
        gated = _CapabilityGatedWorker(source, self.ledger, Mock())
        self.assertEqual(gated.review_next_take(), {"status": "idle"})
        source.review_next_take.assert_not_called()
        self.assertEqual(gated.process_one()["status"], "idle")
        source.process_one.return_value = {"status": "waiting_for_comfyui", "reason": "busy"}
        self.assertEqual(gated.process_one()["waiting_for"], "comfyui")
        self.create()
        with patch("story_builder.isolated_worker.t2v_capability", return_value={"available": False}), patch("story_builder.isolated_worker._runtime_guard", return_value={"safe_to_submit": False}):
            self.assertEqual(gated.process_one()["status"], "idle")
        self.assertEqual(source.process_one.call_count, 2)

    def test_idempotent_create_survives_service_restart_and_conflicts_on_changed_input(self):
        first = self.create()
        after_restart = IsolatedVideoJobs(ProductionLedger(self.db_path), graph_path=GRAPH).create_job(
            workspace_id="workspace-a", clip_id="clip-1", idempotency_key="key-1", request=request())
        self.assertEqual(first["job_id"], after_restart["job_id"])
        self.assertEqual(first["request_hash"], after_restart["request_hash"])
        with self.assertRaises(IsolatedJobConflict):
            self.create(payload=request(prompt="Changed text."))

    def test_concurrent_duplicate_requests_create_one_job(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: self.create(key="same-key"), range(2)))
        self.assertEqual(results[0]["job_id"], results[1]["job_id"])
        self.assertEqual(len(self.jobs.events(results[0]["job_id"])), 1)

    def test_snapshot_and_retake_draft_preserve_full_request_without_queueing(self):
        saved = request(prompt="  exact authored prompt  ")
        original = self.create(payload=saved)
        self.assertEqual(original["request"], saved)
        row = self.jobs._take_and_meta(original["job_id"])[0]
        self.ledger.transition_take(project_id="workspace-a", take_id=row["take_id"], status="submitting")
        self.ledger.transition_take(project_id="workspace-a", take_id=row["take_id"], status="collecting")
        self.ledger.transition_take(project_id="workspace-a", take_id=row["take_id"], status="needs_review")
        draft = self.jobs.retake_draft(original["job_id"], keep_original=False)
        self.assertFalse(draft["submission_created"])
        self.assertEqual(draft["request"], saved)
        retake = self.jobs.create_retake(original["job_id"], idempotency_key="retake-1",
            keep_original=False, overrides={"prompt": "Edited prompt."})
        self.assertEqual(retake["retake_of_job_id"], original["job_id"])
        self.assertFalse(retake["keep_original"])
        self.assertEqual(retake["request"]["seed"], saved["seed"])
        self.assertEqual(retake["request"]["prompt"], "Edited prompt.")
        self.assertEqual(retake["status"], "queued")
        with self.assertRaises(IsolatedJobConflict):
            self.jobs.create_retake(original["job_id"], idempotency_key="retake-1",
                keep_original=True, overrides={"prompt": "Edited prompt."})

    def test_unknown_submission_cannot_be_turned_into_manual_retake(self):
        job = self.create()
        take = self.jobs._take_and_meta(job["job_id"])[0]
        self.ledger.transition_take(project_id="workspace-a", take_id=take["take_id"], status="submitting")
        self.ledger.transition_take(project_id="workspace-a", take_id=take["take_id"],
            status="recovery_required", payload={"code": "unknown_post"})
        with self.assertRaises(IsolatedJobConflict):
            self.jobs.create_retake(job["job_id"], idempotency_key="unsafe-retake", keep_original=True)
        with self.assertRaises(IsolatedJobConflict):
            self.jobs.retake_draft(job["job_id"], keep_original=True)

    def test_idempotency_get_never_repairs_missing_metadata(self):
        job = self.create()
        with self.ledger._connect() as db:
            db.execute("DELETE FROM isolated_video_jobs WHERE job_id=?", (job["job_id"],))
        with self.assertRaises(IsolatedJobConflict):
            self.jobs.get_by_idempotency_key(workspace_id="workspace-a", idempotency_key="key-1")
        with self.ledger._connect() as db:
            count = db.execute("SELECT COUNT(*) FROM isolated_video_jobs WHERE job_id=?", (job["job_id"],)).fetchone()[0]
        self.assertEqual(count, 0)

    def test_facade_metadata_and_queued_row_share_one_ledger_transaction(self):
        run = self.ledger.create_run(project_id="workspace-a", idempotency_key="isolated-workspace:workspace-a",
            config={"control_mode": "manual", "entry": "isolated"})
        with self.assertRaisesRegex(RuntimeError, "rollback marker"):
            self.ledger.queue_take(project_id="workspace-a", run_id=run["run_id"], shot_id="c1",
                take_id="atomic-take", idempotency_key="isolated:atomic", input_snapshot=request(),
                on_create=lambda db, row: (_ for _ in ()).throw(RuntimeError("rollback marker")))
        takes = self.ledger.get_run(project_id="workspace-a", run_id=run["run_id"])["takes"]
        self.assertFalse(any(item["take_id"] == "atomic-take" for item in takes))

    def test_prepare_uses_frozen_request_and_rewrites_output_prefix(self):
        job = self.create()
        take = self.jobs._take_and_meta(job["job_id"])[0]
        prepared = prepare_isolated_take(take, graph_path=GRAPH)
        save_nodes = [n for n in prepared.graph.values() if n.get("class_type") == "SaveVideo"]
        self.assertEqual(len(save_nodes), 1)
        self.assertIn("isolated/workspace-a/clip-1/", save_nodes[0]["inputs"]["filename_prefix"])
        self.assertNotIn("isolated_preview", save_nodes[0]["inputs"]["filename_prefix"])

    def test_worker_unknown_submit_is_durable_recovery_and_not_retried(self):
        job = self.create()
        endpoints = []
        def request_json(url, *, method="GET", payload=None, timeout_seconds=30):
            endpoints.append((url, method))
            if method == "POST":
                raise urllib.error.URLError("simulated connection loss after request write")
            return {"queue_running": [], "queue_pending": []}
        class Watchdog:
            def check(self):
                return None
        worker = ProductionJobWorker(self.ledger, comfy_url="http://fixture.invalid",
            prepare=lambda take: PreparedTake(graph={"fixture": {}}, cleanup=lambda: None),
            collect=lambda take, history: [], cleanup=lambda take: None,
            request_json=request_json,
            gpu_inspector=lambda **kwargs: {"gpu": {"name": "test"}, "recorded_at": "test"},
            operating_point_reader=lambda: {"temperature_c": 40.0, "graphics_clock_mhz": 1200.0},
            release_idle=lambda **kwargs: {"released": False})
        with patch("story_builder.services.production_job_worker.record_gpu_telemetry"), \
             patch("story_builder.services.production_job_worker.ensure_prompt_watchdog", return_value=Watchdog()), \
             patch("story_builder.services.production_job_worker.finish_prompt_watchdog"):
            result = worker.process_one()
            self.assertEqual(result["status"], "recovery_required")
            worker.reconcile_existing_once()
        record = self.jobs.get_job(job["job_id"])
        self.assertEqual(record["status"], "recovery_required")
        self.assertTrue(record["engine_prompt_id"])
        self.assertEqual([method for _, method in endpoints].count("POST"), 1)
        self.assertTrue(any("/history/" in url for url, _ in endpoints))
        self.assertTrue(all("/queue" in url or "/prompt" in url or "/history/" in url for url, _ in endpoints))

    def test_local_http_adapter_is_read_only_on_reconnect_and_never_starts_worker(self):
        app = create_app(data_root=Path(self.temporary.name) / "data", graph_path=GRAPH,
            capability_provider=lambda: {"available": True, "workflow_id": "fixture"},
            worker_status_provider=lambda: {"enabled": True, "running": True, "available": True},
            gpu_reader=lambda: {"temperature_c": 40.0, "graphics_clock_mhz": 1200.0})
        def call(method, path, payload=None, content_type="application/json"):
            body = b"" if payload is None else json.dumps(payload).encode()
            environ = {"REQUEST_METHOD": method, "PATH_INFO": path.split("?", 1)[0],
                "QUERY_STRING": path.split("?", 1)[1] if "?" in path else "",
                "CONTENT_TYPE": content_type, "CONTENT_LENGTH": str(len(body)), "wsgi.input": io.BytesIO(body)}
            started = []
            response = b"".join(app(environ, lambda status, headers: started.append((status, headers))))
            return started[0][0], json.loads(response) if response else None
        status, created = call("POST", "/api/video/jobs", {"workspace_id": "ws", "clip_id": "c1",
            "idempotency_key": "lost-response", "request": request()})
        self.assertEqual(status, "202 Accepted")
        status, recovered = call("GET", "/api/video/jobs/by-idempotency/lost-response?workspace_id=ws")
        self.assertEqual(status, "200 OK")
        self.assertEqual(created["job_id"], recovered["job_id"])
        self.assertEqual(recovered["status"], "queued")
        self.assertIn("dispatch", call("GET", "/api/video/capabilities")[1])
        status, mismatch = call("POST", "/api/video/jobs", {"workspace_id": "ws", "clip_id": "c1",
            "idempotency_key": "lost-response", "request": request(prompt="different")})
        self.assertEqual(status, "409 Conflict")
        status, rejected = call("POST", "/api/video/validations", {"request": request()}, "text/plain")
        self.assertEqual(status, "415 Unsupported Media Type")

    def test_http_create_fails_closed_when_live_runtime_guard_is_unsafe(self):
        data = Path(self.temporary.name) / "unsafe-data"
        app = create_app(data_root=data, graph_path=GRAPH,
            capability_provider=lambda: {"available": True},
            gpu_reader=lambda: {"temperature_c": 48.0, "graphics_clock_mhz": 2431.0})
        payload = {"workspace_id": "ws", "clip_id": "c1", "idempotency_key": "blocked",
            "request": request()}
        body = json.dumps(payload).encode()
        environ = {"REQUEST_METHOD": "POST", "PATH_INFO": "/api/video/jobs", "QUERY_STRING": "",
            "CONTENT_TYPE": "application/json", "CONTENT_LENGTH": str(len(body)), "wsgi.input": io.BytesIO(body)}
        started = []
        result = json.loads(b"".join(app(environ, lambda status, headers: started.append(status))))
        self.assertEqual(started[0], "503 Service Unavailable")
        self.assertEqual(result["error"]["code"], "runtime_not_ready")
        self.assertFalse(result["capability"]["available"])
        ledger = ProductionLedger(data / "storage/production/ledger.sqlite3")
        self.assertEqual(ledger.list_runs(project_id="ws"), [])

    def test_http_create_blocked_when_no_explicit_worker_consumer(self):
        data = Path(self.temporary.name) / "no-worker-data"
        app = create_app(data_root=data, graph_path=GRAPH,
            capability_provider=lambda: {"available": True},
            gpu_reader=lambda: {"temperature_c": 40.0, "graphics_clock_mhz": 1200.0})
        payload = {"workspace_id": "ws", "clip_id": "c1", "idempotency_key": "no-consumer",
            "request": request()}
        body = json.dumps(payload).encode()
        environ = {"REQUEST_METHOD": "POST", "PATH_INFO": "/api/video/jobs", "QUERY_STRING": "",
            "CONTENT_TYPE": "application/json", "CONTENT_LENGTH": str(len(body)), "wsgi.input": io.BytesIO(body)}
        started = []
        result = json.loads(b"".join(app(environ, lambda status, headers: started.append(status))))
        self.assertEqual(started[0], "503 Service Unavailable")
        self.assertFalse(result["capability"]["dispatch"]["available"])
        ledger = ProductionLedger(data / "storage/production/ledger.sqlite3")
        self.assertEqual(ledger.list_runs(project_id="ws"), [])


if __name__ == "__main__":
    unittest.main()
