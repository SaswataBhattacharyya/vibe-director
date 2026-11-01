"""Native multi-angle execution regressions. No ComfyUI/provider/GPU calls."""
import tempfile
import unittest
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import Mock, patch

from story_builder.services.production_image_jobs import ProductionImageJobStore
from story_builder.services.production_image_worker import ProductionImageWorker
from story_builder.services.production_image_workflows import compile_image_candidates

MODULE = "story_builder.services.production_image_worker."

class MultiAngleExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = ProductionImageJobStore(self.root / "jobs.sqlite3")
        compiled = compile_image_candidates(workflow_id="qwen_image_multi_angle_2511",
            prompt="Preserve the reference identity and clothing against white.",
            control_mode="assisted_manual", seed=20, output_prefix="workspace/views",
            source_images=["master.png"], world_view_count=4)
        self.batch = self.store.enqueue_batch(project_id="workspace", run_id="run-1",
            idempotency_key="views", workflow_id=compiled["workflow_id"],
            workflow_version=compiled["workflow_version"], asset_role="character_view",
            prompt=compiled["prompt"], settings=compiled["settings"], candidates=compiled["candidates"])
        self.registered = []
        self.history = {"status": {"completed": True}, "outputs": {
            "108": {"images": [{"filename": "camera-ui.png"}]},
            "116": {"images": [{"filename": f"view-{i}.png"} for i in range(4)]}}}
        def register(**kwargs):
            self.registered.append(kwargs)
            return {"asset_id": "asset-" + str(kwargs["metadata"]["production_image_job"]["candidate_index"])}
        self.worker = ProductionImageWorker(self.store, comfy_url="http://mock.invalid",
            output_root=self.root / "assets", register_output=register, release_idle=Mock())
        self.worker._cleanup_owned_comfy_outputs = Mock()

    def rows(self):
        return self.store.list_batch(project_id="workspace", batch_id=self.batch["batch_id"])["jobs"]

    def start(self):
        job = self.store.next_queued()
        prompt = self.store.reserve_prompt_id(job["job_id"])
        self.store.transition(job["job_id"], "running")
        return job, prompt

    def collect(self, history, *, destination_dir, **kwargs):
        self.assertEqual(set(history["outputs"]), {"116"})
        destination_dir.mkdir(parents=True, exist_ok=True)
        result = []
        for i in range(len(history["outputs"]["116"]["images"])):
            name = f"copy-{len(self.registered)}-{i}.png"
            (destination_dir / name).write_bytes(b"mock image")
            result.append({"kind": "image", "relative_path": name})
        return result

    def test_claim_and_reservation_cover_group_and_busy_returns_group_to_queue(self):
        job = self.store.next_queued()
        self.assertEqual({r["status"] for r in self.rows()}, {"preparing"})
        self.assertIsNone(self.store.next_queued())
        self.store.transition(job["job_id"], "queued")
        self.assertEqual({r["status"] for r in self.rows()}, {"queued"})
        job, prompt = self.start()
        self.assertEqual({r["status"] for r in self.rows()}, {"running"})
        self.assertEqual([r["prompt_id"] for r in self.rows()], [prompt, None, None, None])
        self.store.transition(job["job_id"], "failed")
        self.assertEqual({r["status"] for r in self.rows()}, {"failed"})

    def test_one_submission_saves_every_view_in_order_and_ignores_camera_previews(self):
        posts = []
        def request(url, **kwargs):
            self.assertTrue(url.endswith("/prompt"))
            posts.append(kwargs["payload"])
            return {"prompt_id": kwargs["payload"]["prompt_id"]}
        self.worker.request_json = request
        self.worker.gpu_inspector = Mock(return_value={})
        self.worker._comfy_busy_reason = Mock(return_value=None)
        self.worker._wait_history = Mock(return_value=self.history)
        with patch(MODULE + "comfy_submission_guard", return_value=nullcontext()), \
             patch(MODULE + "ensure_prompt_watchdog"), \
             patch(MODULE + "record_gpu_telemetry"), \
             patch(MODULE + "collect_outputs", side_effect=self.collect):
            result = self.worker.process_one.__wrapped__(self.worker)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(len(posts), 1)
        self.assertEqual([r["output_asset_id"] for r in self.rows()], [f"asset-{i}" for i in range(1,5)])
        saved = sorted(self.registered, key=lambda r: r["metadata"]["production_image_job"]["candidate_index"])
        self.assertEqual([r["metadata"]["production_image_job"]["world_view"]["label"] for r in saved],
            ["Front", "Right", "Back", "Left"])
        self.assertEqual([Path(r["relative_path"]).name.split("-")[-1] for r in saved],
            ["0.png", "1.png", "2.png", "3.png"])
        self.assertIsNone(self.store.next_queued())

    def test_two_three_and_eight_views_are_saved_under_individual_assets(self):
        for count in (2, 3, 8):
            self.registered.clear()
            compiled = compile_image_candidates(workflow_id="qwen_image_multi_angle_2511",
                prompt="Preserve the empty environment.", control_mode="assisted_manual", seed=30,
                output_prefix="workspace/eight", source_images=["world.png"], world_view_count=count)
            other = ProductionImageJobStore(self.root / f"views-{count}.sqlite3")
            batch = other.enqueue_batch(project_id="workspace", run_id="run-8", idempotency_key="eight",
                workflow_id=compiled["workflow_id"], workflow_version=compiled["workflow_version"],
                asset_role="world_view", prompt=compiled["prompt"], settings=compiled["settings"],
                candidates=compiled["candidates"])
            self.store = other
            self.batch = batch
            self.worker.store = other
            self.history["outputs"]["116"]["images"] = [{"filename": f"view-{i}.png"} for i in range(count)]
            job, prompt = self.start()
            with patch(MODULE + "collect_outputs", side_effect=self.collect):
                self.worker._collect_completed(job, prompt, self.history)
            self.assertEqual([r["output_asset_id"] for r in self.rows()], [f"asset-{i}" for i in range(1,count+1)])
            self.assertEqual(len(self.registered), count)

    def test_missing_output_does_not_publish_mislabelled_views(self):
        job, prompt = self.start()
        self.history["outputs"]["116"]["images"].pop()
        with patch(MODULE + "collect_outputs") as collect:
            with self.assertRaisesRegex(RuntimeError, "exactly 4"):
                self.worker._collect_completed(job, prompt, self.history)
        collect.assert_not_called()
        self.assertEqual(self.registered, [])

    def test_partial_save_and_restart_reconcile_only_original_prompt(self):
        job, prompt = self.start()
        original = self.worker.register_output
        def fail_third(**kwargs):
            if len(self.registered) == 2:
                raise OSError("mock disk unavailable")
            return original(**kwargs)
        self.worker.register_output = fail_third
        with patch(MODULE + "collect_outputs", side_effect=self.collect):
            with self.assertRaises(OSError):
                self.worker._collect_completed(job, prompt, self.history)
        self.store.reconcile_after_restart()
        self.assertEqual(len(self.store.recovery_jobs()), 1)
        self.assertIsNone(self.store.next_queued())
        self.worker.register_output = original
        self.worker.request_json = Mock(side_effect=lambda url, **kw:
            {prompt: self.history} if "/history/" in url else {"queue_running": [], "queue_pending": []})
        with patch(MODULE + "comfy_submission_guard", return_value=nullcontext()), \
             patch(MODULE + "collect_outputs", side_effect=self.collect):
            self.worker.reconcile_recovery_once()
        self.assertEqual({r["status"] for r in self.rows()}, {"completed"})
        self.assertEqual(len(self.registered), 4)
        self.assertTrue(all(call.kwargs.get("method", "GET") == "GET" for call in self.worker.request_json.call_args_list))

    def test_failed_download_does_not_shift_direction_labels(self):
        job, prompt = self.start()
        with patch(MODULE + "collect_outputs", return_value=[{"kind":"image","relative_path":f"{i}.png"} for i in range(3)]):
            with self.assertRaisesRegex(RuntimeError, "every verified"):
                self.worker._collect_completed(job, prompt, self.history)
        self.assertEqual(self.registered, [])
