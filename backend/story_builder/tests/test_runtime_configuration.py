import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from story_builder.services import gpu_runtime, media_jobs, production_image_worker
from story_builder.services.production_ledger import ProductionLedger


class RuntimeConfigurationTests(unittest.TestCase):
    def test_safety_trip_reason_survives_owned_process_exit_error(self):
        cancelled = threading.Event()
        with tempfile.TemporaryDirectory() as temporary, patch.dict(os.environ, {
            "VIBE_DIRECTOR_GPU_WORKLOAD_LOCK": str(Path(temporary) / "app-gpu.lock"),
        }, clear=True), patch.object(media_jobs, "wait_for_comfyui_idle"), \
                patch.object(media_jobs, "record_gpu_telemetry"), \
                patch.object(media_jobs, "inspect_gpu_runtime", side_effect=RuntimeError("NV_ERR_NO_MEMORY")):
            with self.assertRaisesRegex(media_jobs.MediaJobError, "NV_ERR_NO_MEMORY") as failure:
                with media_jobs.gpu_workload_guard(comfy_url="http://unused",
                        on_safety_trip=lambda reason: cancelled.set(), monitor_interval_seconds=0.01):
                    self.assertTrue(cancelled.wait(1))
                    raise RuntimeError("Direct analyzer failed (exit 137)")
            self.assertIn("exit 137", str(failure.exception.__cause__))

    def test_body_error_without_safety_trip_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary, patch.dict(os.environ, {
            "VIBE_DIRECTOR_GPU_WORKLOAD_LOCK": str(Path(temporary) / "app-gpu.lock"),
        }, clear=True), patch.object(media_jobs, "wait_for_comfyui_idle"):
            with self.assertRaisesRegex(ValueError, "invalid input"):
                with media_jobs.gpu_workload_guard(comfy_url="http://unused"):
                    raise ValueError("invalid input")

    def test_gpu_safety_trip_cancels_owned_work_before_body_returns(self):
        cancelled = threading.Event()
        body_running = threading.Event()
        with tempfile.TemporaryDirectory() as temporary, patch.dict(os.environ, {
            "VIBE_DIRECTOR_GPU_WORKLOAD_LOCK": str(Path(temporary) / "app-gpu.lock"),
        }, clear=True), patch.object(media_jobs, "wait_for_comfyui_idle"), \
                patch.object(media_jobs, "inspect_gpu_runtime", side_effect=RuntimeError("thermal cutoff")):
            with self.assertRaisesRegex(media_jobs.MediaJobError, "thermal cutoff"):
                with media_jobs.gpu_workload_guard(comfy_url="http://unused",
                        on_safety_trip=lambda _reason: (body_running.is_set(), cancelled.set()),
                        monitor_interval_seconds=0.01):
                    body_running.set()
                    deadline = time.monotonic() + 1
                    while not cancelled.is_set() and time.monotonic() < deadline:
                        time.sleep(0.01)
                    self.assertTrue(body_running.is_set())
                    self.assertTrue(cancelled.is_set())

    def test_unconfirmed_safety_trip_holds_future_admission_until_operator_recovers(self):
        with tempfile.TemporaryDirectory() as temporary, patch.dict(os.environ, {
            "VIBE_DIRECTOR_GPU_WORKLOAD_LOCK": str(Path(temporary) / "app-gpu.lock"),
            "VIBE_DIRECTOR_GPU_SAFETY_HOLD_PATH": str(Path(temporary) / "gpu-safety-hold.json"),
        }, clear=True), patch.object(media_jobs, "wait_for_comfyui_idle"), \
                patch.object(media_jobs, "inspect_gpu_runtime", side_effect=RuntimeError("thermal cutoff")):
            with self.assertRaisesRegex(media_jobs.MediaJobError, "thermal cutoff"):
                with media_jobs.gpu_workload_guard(comfy_url="http://unused", monitor_interval_seconds=0.01):
                    time.sleep(0.04)
            hold = media_jobs.get_gpu_safety_hold()
            self.assertTrue(hold["termination_unknown"])
            self.assertIn("No adapter cancellation handler", hold["reason"])
            with self.assertRaisesRegex(media_jobs.MediaJobError, "admission is held"):
                with media_jobs.gpu_workload_lock():
                    self.fail("safety hold allowed another workload")
            self.assertEqual(media_jobs.clear_gpu_safety_hold(verified_idle=True), {"cleared": True})
            self.assertFalse(media_jobs.get_gpu_safety_hold()["termination_unknown"])

    def test_unknown_termination_hold_cannot_be_cleared_without_idle_confirmation(self):
        with tempfile.TemporaryDirectory() as temporary, patch.dict(os.environ, {
            "VIBE_DIRECTOR_GPU_WORKLOAD_LOCK": str(Path(temporary) / "app-gpu.lock"),
            "VIBE_DIRECTOR_GPU_SAFETY_HOLD_PATH": str(Path(temporary) / "gpu-safety-hold.json"),
        }, clear=True):
            with self.assertRaisesRegex(ValueError, "Confirm that"):
                media_jobs.clear_gpu_safety_hold(verified_idle=False)

    def test_vibe_ledger_path_takes_precedence_with_legacy_fallback(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            vibe_path = root / "vibe.sqlite3"
            legacy_path = root / "legacy.sqlite3"
            with patch.dict(os.environ, {
                "VIBE_DIRECTOR_LEDGER_PATH": str(vibe_path),
                "STORY_BUILDER_PRODUCTION_LEDGER_PATH": str(legacy_path),
            }, clear=True):
                ledger = ProductionLedger()
            self.assertEqual(ledger.path, vibe_path.resolve())
            self.assertTrue(vibe_path.exists())
            self.assertFalse(legacy_path.exists())

            with patch.dict(os.environ, {
                "STORY_BUILDER_PRODUCTION_LEDGER_PATH": str(legacy_path),
            }, clear=True):
                legacy_ledger = ProductionLedger()
            self.assertEqual(legacy_ledger.path, legacy_path.resolve())

    def test_comfy_container_prefers_vibe_setting_and_keeps_legacy_fallback(self):
        with patch.dict(os.environ, {
            "VIBE_DIRECTOR_COMFYUI_CONTAINER": "vibe-comfy",
            "STORY_BUILDER_COMFYUI_CONTAINER": "legacy-comfy",
        }, clear=True):
            self.assertEqual(gpu_runtime.comfy_container_name(), "vibe-comfy")
        with patch.dict(os.environ, {"STORY_BUILDER_COMFYUI_CONTAINER": "legacy-comfy"}, clear=True):
            self.assertEqual(gpu_runtime.comfy_container_name(), "legacy-comfy")

    def test_gpu_telemetry_path_prefers_vibe_setting_and_keeps_legacy_fallback(self):
        self.assertEqual(gpu_runtime._telemetry_path({
            "VIBE_DIRECTOR_GPU_TELEMETRY_PATH": "/tmp/vibe.jsonl",
            "STORY_BUILDER_GPU_TELEMETRY_PATH": "/tmp/legacy.jsonl",
        }), Path("/tmp/vibe.jsonl"))
        self.assertEqual(gpu_runtime._telemetry_path({
            "STORY_BUILDER_GPU_TELEMETRY_PATH": "/tmp/legacy.jsonl",
        }), Path("/tmp/legacy.jsonl"))

    def test_all_gpu_workloads_share_one_vibe_director_lock(self):
        with tempfile.TemporaryDirectory() as temporary:
            lock_path = Path(temporary) / "app-gpu.lock"
            entered = threading.Event()
            acquired = threading.Event()

            def second_workload():
                entered.set()
                with media_jobs.comfy_submission_guard():
                    acquired.set()

            with patch.dict(os.environ, {
                "VIBE_DIRECTOR_GPU_WORKLOAD_LOCK": str(lock_path),
                "STORY_BUILDER_COMFY_SUBMISSION_LOCK": str(Path(temporary) / "legacy.lock"),
            }, clear=True):
                with media_jobs.gpu_workload_lock():
                    worker = threading.Thread(target=second_workload)
                    worker.start()
                    self.assertTrue(entered.wait(1))
                    self.assertFalse(acquired.wait(0.1))
                self.assertTrue(acquired.wait(1))
                worker.join(timeout=1)

            self.assertTrue(lock_path.is_file())
            self.assertFalse((Path(temporary) / "legacy.lock").exists())

    def test_gpu_workload_guard_can_nest_comfy_submission_lease(self):
        with tempfile.TemporaryDirectory() as temporary, patch.dict(os.environ, {
            "VIBE_DIRECTOR_GPU_WORKLOAD_LOCK": str(Path(temporary) / "app-gpu.lock"),
        }, clear=True):
            with media_jobs.gpu_workload_lock():
                with media_jobs.comfy_submission_guard():
                    with media_jobs.gpu_workload_lock():
                        self.assertEqual(media_jobs._GPU_WORKLOAD_LOCK_STATE.depth, 3)
                self.assertEqual(media_jobs._GPU_WORKLOAD_LOCK_STATE.depth, 1)
            self.assertEqual(media_jobs._GPU_WORKLOAD_LOCK_STATE.depth, 0)

    def test_gpu_workload_lock_serializes_separate_backend_processes(self):
        with tempfile.TemporaryDirectory() as temporary:
            lock_path = Path(temporary) / "app-gpu.lock"
            child_code = "from story_builder.services.media_jobs import gpu_workload_lock\n" \
                "with gpu_workload_lock():\n    print('acquired', flush=True)\n"
            with patch.dict(os.environ, {
                "VIBE_DIRECTOR_GPU_WORKLOAD_LOCK": str(lock_path),
                "PYTHONPATH": str(Path(__file__).resolve().parents[2]),
            }):
                with media_jobs.gpu_workload_lock():
                    child = subprocess.Popen([sys.executable, "-c", child_code],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    time.sleep(0.1)
                    self.assertIsNone(child.poll(), "second backend passed the shared GPU gate")
                stdout, stderr = child.communicate(timeout=3)

            self.assertEqual(child.returncode, 0, stderr)
            self.assertEqual(stdout.strip(), "acquired")

    def test_gpu_admission_uses_resolved_comfy_container(self):
        with patch.dict(os.environ, {
            "VIBE_DIRECTOR_COMFYUI_CONTAINER": "vibe-comfy",
            "STORY_BUILDER_COMFYUI_CONTAINER": "legacy-comfy",
        }, clear=True), patch.object(gpu_runtime, "_run",
                return_value="PID COMMAND\n123 python main.py --port 3008") as run:
            processes = gpu_runtime._comfy_processes("http://127.0.0.1:3008")
        self.assertIn(123, processes)
        self.assertEqual(run.call_args.args[0][2], "vibe-comfy")

    def test_duplicate_output_cleanup_uses_vibe_container_and_output_root(self):
        with tempfile.TemporaryDirectory() as temporary:
            host_root = Path(temporary) / "host"
            source = host_root / "nested" / "image.png"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"image")
            commands = []

            def fake_run(command, **_kwargs):
                commands.append(command)
                if "rm" in command:
                    source.unlink()
                return subprocess.CompletedProcess(command, 0, "", "")

            with patch.dict(os.environ, {
                "VIBE_DIRECTOR_COMFYUI_CONTAINER": "vibe-comfy",
                "STORY_BUILDER_COMFYUI_CONTAINER": "legacy-comfy",
                "VIBE_DIRECTOR_COMFYUI_CONTAINER_OUTPUT": "/vibe/output",
                "STORY_BUILDER_COMFYUI_CONTAINER_OUTPUT": "/legacy/output",
            }, clear=True), patch.object(production_image_worker.shutil, "which", return_value="docker"), \
                    patch.object(production_image_worker.subprocess, "run", side_effect=fake_run):
                removed = production_image_worker.ProductionImageWorker._remove_owned_comfy_output_as_container_root(
                    source, host_root)

            self.assertTrue(removed)
            self.assertEqual(commands[0][4], "vibe-comfy")
            self.assertEqual(commands[0][-1], "/vibe/output/nested/image.png")


if __name__ == "__main__":
    unittest.main()
