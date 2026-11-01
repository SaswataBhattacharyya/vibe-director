from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import io

from story_builder.services import media_library
from story_builder.services.isolated_fl2va_contract import (
    EXPECTED_GRAPH_SHA256, FL2VA_GRAPH_PATH, WORKFLOW_ID, WORKFLOW_VERSION,
)
from story_builder.services.isolated_video_jobs import (
    IsolatedJobConflict, IsolatedVideoJobs, prepare_isolated_take,
)
from story_builder.services.isolated_video_contract import EXPECTED_GRAPH_SHA256 as T2V_GRAPH_SHA256
from story_builder.services.production_ledger import ProductionLedger
from story_builder.isolated_server import create_app

PNG = b"\x89PNG\r\n\x1a\nfixture-png"
READY = {"available": True, "workflow_id": WORKFLOW_ID}


def fl_request(first, last, **changes):
    result = {"workflow_id": WORKFLOW_ID, "workflow_version": WORKFLOW_VERSION,
        "workflow_sha256": EXPECTED_GRAPH_SHA256, "prompt": "A slow dolly through rain.",
        "duration_seconds": 5, "aspect_ratio": "16:9", "resolution_preset": 0.98,
        "first_frame": first, "last_frame": last}
    result.update(changes)
    return result


class IsolatedFL2VAJobTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.workspace = "fl-workspace"
        self.media_root = self.root / "media"
        self.input_root = self.root / "ComfyUI/input"
        self.input_root.mkdir(parents=True)
        self.ledger = ProductionLedger(self.root / "ledger.sqlite3")
        self.capability = lambda: READY
        with patch.object(media_library, "_probe", return_value={"width": 1, "height": 1}):
            self.first = media_library.register_upload(self.media_root, self.workspace,
                filename="first.png", role="first_frame", content=PNG)
            self.last = media_library.register_upload(self.media_root, self.workspace,
                filename="last.png", role="last_frame", content=PNG + b"last")
        self.first_ref = {"asset_id": self.first["asset_id"], "sha256": self.first["sha256"]}
        self.last_ref = {"asset_id": self.last["asset_id"], "sha256": self.last["sha256"]}
        self.jobs = IsolatedVideoJobs(self.ledger,
            fl2va_capability_provider=self.capability)

    def create(self, key="fl-job", **changes):
        return self.jobs.create_job(workspace_id=self.workspace, clip_id="clip-1",
            idempotency_key=key, request=fl_request(self.first_ref, self.last_ref, **changes))

    def test_selected_fl2va_compiles_and_durable_replay_hashes_exact_snapshot(self):
        validation = self.jobs.validate(fl_request(self.first_ref, self.last_ref))
        self.assertEqual(validation["normalized_request"]["workflow_id"], WORKFLOW_ID)
        self.assertTrue(validation["compiled_preview"]["preview_only"])
        first = self.create()
        replay = IsolatedVideoJobs(ProductionLedger(self.root / "ledger.sqlite3"),
            fl2va_capability_provider=self.capability).create_job(
                workspace_id=self.workspace, clip_id="clip-1", idempotency_key="fl-job",
                request=fl_request(self.first_ref, self.last_ref))
        self.assertEqual(first["job_id"], replay["job_id"])
        self.assertEqual(first["request_hash"], replay["request_hash"])
        with self.assertRaises(IsolatedJobConflict):
            self.create(prompt="Changed prompt.")

    def test_capability_missing_keeps_fl2va_out_of_durable_queue(self):
        jobs = IsolatedVideoJobs(self.ledger,
            fl2va_capability_provider=lambda: {"available": False, "disabled_reason": "smoke missing"})
        with self.assertRaisesRegex(ValueError, "smoke missing"):
            jobs.create_job(workspace_id=self.workspace, clip_id="clip-1", idempotency_key="blocked",
                request=fl_request(self.first_ref, self.last_ref))
        self.assertEqual(self.ledger.list_runs(project_id=self.workspace), [])

    def test_mixed_workflows_share_workspace_run_in_either_order(self):
        t2v = {"workflow_id": "minimax_h3_t2v_local_v1", "workflow_version": 1,
            "workflow_sha256": T2V_GRAPH_SHA256, "prompt": "A quiet street at dusk.",
            "duration_seconds": 6, "aspect_ratio": "16:9", "resolution_preset": 0.98,
            "steps": 20, "seed": 1, "references": []}
        for order in (("t2v", "fl2va"), ("fl2va", "t2v")):
            with self.subTest(order=order):
                workspace = "mixed-" + order[0]
                jobs = IsolatedVideoJobs(self.ledger, fl2va_capability_provider=self.capability)
                created = {}
                for workflow in order:
                    created[workflow] = jobs.create_job(workspace_id=workspace,
                        clip_id=workflow, idempotency_key=workflow,
                        request=t2v if workflow == "t2v" else fl_request(self.first_ref, self.last_ref))
                t2v_take = jobs._take_and_meta(created["t2v"]["job_id"])[0]
                fl2va_take = jobs._take_and_meta(created["fl2va"]["job_id"])[0]
                self.assertEqual(t2v_take["run_id"], fl2va_take["run_id"])
                self.assertEqual(jobs.get_job(created["t2v"]["job_id"])["request"]["workflow_id"],
                    "minimax_h3_t2v_local_v1")
                self.assertEqual(jobs.get_job(created["fl2va"]["job_id"])["request"]["workflow_id"],
                    WORKFLOW_ID)

    def test_prepare_stages_ordered_frozen_images_and_returns_cleanup(self):
        job = self.create()
        take = self.jobs._take_and_meta(job["job_id"])[0]
        prepared = prepare_isolated_take(take, media_root=self.media_root,
            comfy_input_root=self.input_root, fl2va_capability_provider=self.capability)
        loaders = sorted(((int(key), node) for key, node in prepared.graph.items()
            if node.get("class_type") == "LoadImage"), key=lambda pair: pair[0])
        self.assertEqual(len(loaders), 2)
        first_path = self.input_root / loaders[0][1]["inputs"]["image"]
        last_path = self.input_root / loaders[1][1]["inputs"]["image"]
        self.assertEqual(hashlib.sha256(first_path.read_bytes()).hexdigest(), self.first["sha256"])
        self.assertEqual(hashlib.sha256(last_path.read_bytes()).hexdigest(), self.last["sha256"])
        self.assertTrue(str(next(n["inputs"]["filename_prefix"] for n in prepared.graph.values()
            if n.get("class_type") == "SaveVideo")).startswith("isolated/fl-workspace/clip-1/"))
        prepared.cleanup()
        self.assertFalse(first_path.exists())
        self.assertFalse(last_path.exists())


class FL2VACapabilityGateTests(unittest.TestCase):
    def test_all_readiness_gates_are_required_and_smoke_is_hash_and_stream_verified(self):
        from story_builder.services.production_fl2va_capability import fl2va_capability

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            models = root / "models"
            files = [models / "diffusion_models/minimax_h3_fl2va_pruned_int8_convrot.safetensors",
                models / "vae/minimax_h3_video_vae_fp16.safetensors",
                models / "vae/minimax_h3_audio_vae_fp32.safetensors",
                models / "text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors"]
            for path in files:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"fixture")
            graph = json.loads(FL2VA_GRAPH_PATH.read_text())
            info = {node["class_type"]: {} for node in graph.values()
                if isinstance(node, dict) and node.get("class_type")}
            output_dir = root / "smoke"
            output_dir.mkdir()
            output = output_dir / "result.mp4"
            output.write_bytes(b"smoke-output")
            smoke = output_dir / "manifest.json"
            manifest = {"status": "completed", "has_video": True, "has_audio": True,
                "workflow_id": WORKFLOW_ID, "workflow_version": WORKFLOW_VERSION,
                "workflow_sha256": EXPECTED_GRAPH_SHA256,
                "input_roles": ["first_frame", "last_frame"],
                "outputs": [{"kind": "video", "relative_path": "result.mp4",
                    "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
                    "probe": {"streams": [{"codec_type": "video"}, {"codec_type": "audio"}]}}]}
            with patch.dict("os.environ", {"VIBE_DIRECTOR_ENABLE_FL2VA": "1"}, clear=False):
                t2v_smoke = dict(manifest, workflow_id="minimax_h3_t2v_local_v1",
                    workflow_sha256=T2V_GRAPH_SHA256, input_roles=[])
                smoke.write_text(json.dumps(t2v_smoke))
                rejected_t2v = fl2va_capability(root=root, smoke_path=smoke, object_info=info)
                self.assertFalse(rejected_t2v["available"])
                self.assertIn("smoke", rejected_t2v["disabled_reason"])
                smoke.write_text(json.dumps(manifest))
                good = fl2va_capability(root=root, smoke_path=smoke, object_info=info)
                self.assertTrue(good["available"], good["disabled_reason"])
                no_audio_vae = files[2]
                no_audio_vae.unlink()
                self.assertFalse(fl2va_capability(root=root, smoke_path=smoke, object_info=info)["available"])
                no_audio_vae.write_bytes(b"fixture")
                self.assertFalse(fl2va_capability(root=root, smoke_path=smoke,
                    object_info={})["available"])
                smoke.write_text(json.dumps({"status": "completed", "has_video": True,
                    "has_audio": True, "outputs": []}))
                self.assertFalse(fl2va_capability(root=root, smoke_path=smoke,
                    object_info=info)["available"])
            with patch.dict("os.environ", {"VIBE_DIRECTOR_ENABLE_FL2VA": "0"}, clear=False):
                self.assertFalse(fl2va_capability(root=root, smoke_path=smoke,
                    object_info=info)["available"])

    def test_api_admission_uses_selected_fl2va_capability_and_gpu_guard(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            app = create_app(data_root=root,
                fl2va_capability_provider=lambda: {"available": False, "disabled_reason": "smoke absent"},
                worker_status_provider=lambda: {"enabled": True, "running": True, "available": True},
                gpu_reader=lambda: {"temperature_c": 40.0, "graphics_clock_mhz": 1200.0})
            request = fl_request({"asset_id": "asset-a", "sha256": "a" * 64},
                {"asset_id": "asset-b", "sha256": "b" * 64})
            body = json.dumps({"workspace_id": "ws", "clip_id": "clip", "idempotency_key": "blocked",
                "request": request}).encode()
            environ = {"REQUEST_METHOD": "POST", "PATH_INFO": "/api/video/jobs", "QUERY_STRING": "",
                "CONTENT_TYPE": "application/json", "CONTENT_LENGTH": str(len(body)), "wsgi.input": io.BytesIO(body)}
            statuses = []
            response = json.loads(b"".join(app(environ, lambda status, headers: statuses.append(status))))
            self.assertEqual(statuses[0], "503 Service Unavailable")
            self.assertIn("smoke absent", response["capability"]["disabled_reason"])
            self.assertEqual(ProductionLedger(root / "services/production/ledger.sqlite3").list_runs(project_id="ws"), [])

    def test_api_rejects_foreign_fl2va_frame_assets_before_queueing(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with patch.object(media_library, "_probe", return_value={"width": 1, "height": 1}):
                foreign_first = media_library.register_upload(root, "other-workspace",
                    filename="first.png", role="first_frame", content=PNG)
                foreign_last = media_library.register_upload(root, "other-workspace",
                    filename="last.png", role="last_frame", content=PNG + b"last")
            request = fl_request(
                {"asset_id": foreign_first["asset_id"], "sha256": foreign_first["sha256"]},
                {"asset_id": foreign_last["asset_id"], "sha256": foreign_last["sha256"]})
            app = create_app(data_root=root, fl2va_capability_provider=lambda: READY,
                worker_status_provider=lambda: {"enabled": True, "running": True, "available": True,
                    "supported_workflows": [WORKFLOW_ID]},
                gpu_reader=lambda: {"temperature_c": 40.0, "graphics_clock_mhz": 1200.0})
            body = json.dumps({"workspace_id": "fl-workspace", "clip_id": "clip-foreign",
                "idempotency_key": "foreign-frames", "request": request}).encode()
            statuses = []
            environ = {"REQUEST_METHOD": "POST", "PATH_INFO": "/api/video/jobs", "QUERY_STRING": "",
                "CONTENT_TYPE": "application/json", "CONTENT_LENGTH": str(len(body)), "wsgi.input": io.BytesIO(body)}
            response = json.loads(b"".join(app(environ, lambda status, headers: statuses.append(status))))
            ledger = ProductionLedger(root / "services/production/ledger.sqlite3")
            with ledger._connect() as db:
                jobs = db.execute("SELECT job_id FROM production_takes WHERE project_id=?",
                    ("fl-workspace",)).fetchall()
        self.assertEqual(statuses[0], "422 Unprocessable Entity")
        self.assertIn("not available to this workspace", response["error"]["message"])
        self.assertEqual(jobs, [])

    def test_api_accepts_archived_frames_for_an_existing_fl2va_draft(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            workspace = "saved-fl2va-workspace"
            with patch.object(media_library, "_probe", return_value={"width": 1, "height": 1}):
                first = media_library.register_upload(root, workspace,
                    filename="first.png", role="first_frame", content=PNG)
                last = media_library.register_upload(root, workspace,
                    filename="last.png", role="last_frame", content=PNG + b"last")
            app = create_app(data_root=root, fl2va_capability_provider=lambda: READY,
                worker_status_provider=lambda: {"enabled": True, "running": True, "available": True,
                    "supported_workflows": [WORKFLOW_ID]},
                gpu_reader=lambda: {"temperature_c": 40.0, "graphics_clock_mhz": 1200.0})

            def call(method, path, payload=None):
                data = json.dumps(payload).encode() if payload is not None else b""
                statuses = []
                response = b"".join(app({"REQUEST_METHOD": method, "PATH_INFO": path,
                    "QUERY_STRING": "", "CONTENT_TYPE": "application/json",
                    "CONTENT_LENGTH": str(len(data)), "wsgi.input": io.BytesIO(data)},
                    lambda status, _headers: statuses.append(status)))
                return statuses[0], json.loads(response)

            for asset in (first, last):
                status, archived = call("POST",
                    f"/api/media/{workspace}/assets/{asset['asset_id']}/archive", {})
                self.assertEqual(status, "200 OK", archived)
            status, accepted = call("POST", "/api/video/jobs", {
                "workspace_id": workspace, "clip_id": "saved-clip",
                "idempotency_key": "archived-fl2va-frames",
                "request": fl_request(
                    {"asset_id": first["asset_id"], "sha256": first["sha256"]},
                    {"asset_id": last["asset_id"], "sha256": last["sha256"]})})
            self.assertEqual(status, "202 Accepted", accepted)

    def test_api_requires_fl2va_worker_dispatch_and_safe_gpu(self):
        for worker_status, gpu_status, expected in (
            ({"enabled": True, "running": True, "available": True},
             {"temperature_c": 40.0, "graphics_clock_mhz": 1200.0}, "worker does not report FL2VA"),
            ({"enabled": True, "running": True, "available": True,
             "supported_workflows": [WORKFLOW_ID]},
             {"temperature_c": 90.0, "graphics_clock_mhz": 1200.0}, "GPU"),
        ):
            with self.subTest(expected=expected), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                app = create_app(data_root=root,
                    fl2va_capability_provider=lambda: READY,
                    worker_status_provider=lambda: worker_status,
                    gpu_reader=lambda: gpu_status)
                request = fl_request({"asset_id": "asset-a", "sha256": "a" * 64},
                    {"asset_id": "asset-b", "sha256": "b" * 64})
                body = json.dumps({"workspace_id": "ws", "clip_id": "clip",
                    "idempotency_key": "blocked", "request": request}).encode()
                environ = {"REQUEST_METHOD": "POST", "PATH_INFO": "/api/video/jobs",
                    "QUERY_STRING": "", "CONTENT_TYPE": "application/json",
                    "CONTENT_LENGTH": str(len(body)), "wsgi.input": io.BytesIO(body)}
                statuses = []
                response = json.loads(b"".join(app(environ,
                    lambda status, headers: statuses.append(status))))
                self.assertEqual(statuses[0], "503 Service Unavailable")
                self.assertIn(expected.lower(), response["capability"]["disabled_reason"].lower())
                self.assertEqual(ProductionLedger(root / "services/production/ledger.sqlite3")
                    .list_runs(project_id="ws"), [])

    def test_worker_uses_workflow_capability_and_runtime_guard_before_claim(self):
        from unittest.mock import Mock
        from story_builder.isolated_worker import _CapabilityGatedWorker

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ledger = ProductionLedger(root / "ledger.sqlite3")
            with patch.object(media_library, "_probe", return_value={"width": 1, "height": 1}):
                a = media_library.register_upload(root / "media", "ws", filename="a.png",
                    role="first_frame", content=PNG)
                b = media_library.register_upload(root / "media", "ws", filename="b.png",
                    role="last_frame", content=PNG + b"b")
            jobs = IsolatedVideoJobs(ledger, fl2va_capability_provider=lambda: READY)
            jobs.create_job(workspace_id="ws", clip_id="clip", idempotency_key="queued",
                request=fl_request({"asset_id": a["asset_id"], "sha256": a["sha256"]},
                    {"asset_id": b["asset_id"], "sha256": b["sha256"]}))
            source, status_writer = Mock(), Mock()
            blocked = _CapabilityGatedWorker(source, ledger, status_writer,
                fl2va_provider=lambda: {"available": False, "disabled_reason": "node missing"})
            with patch("story_builder.isolated_worker._runtime_guard", return_value={"safe_to_submit": True}):
                blocked.process_one()
            source.process_one.assert_not_called()

            blocked_gpu = _CapabilityGatedWorker(source, ledger, status_writer,
                fl2va_provider=lambda: READY)
            with patch("story_builder.isolated_worker._runtime_guard", return_value={"safe_to_submit": False, "reason": "hot"}):
                blocked_gpu.process_one()
            source.process_one.assert_not_called()


if __name__ == "__main__":
    unittest.main()
