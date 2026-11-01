from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
import os
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from story_builder.assembly_export_worker import process_one
from story_builder.services.assembly import AssemblyExportJobs, AssemblySelections
from story_builder.services.media_library import asset_path, list_assets, register_upload
from story_builder.services.production_ledger import ProductionLedger
from story_builder.services.storage_paths import generated_root


class AssemblyExportWorkerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "data"
        workload_env = patch.dict(os.environ, {
            "VIBE_DIRECTOR_GPU_WORKLOAD_LOCK": str(self.root / "runtime/workload.lock"),
            "VIBE_DIRECTOR_WORKLOAD_POLICY_PATH": str(self.root / "runtime/workload-policy.json")})
        workload_env.start()
        self.addCleanup(workload_env.stop)
        ledger = ProductionLedger(self.root / "services/production/ledger.sqlite3")
        self.selections = AssemblySelections(ledger)
        self.jobs = AssemblyExportJobs(ledger)

    def enqueue(self):
        manifest = self.selections.save_export_manifest("workspace-a", "revision-a", {
            "state": "ready_for_render", "clips": [{"outputs": [{"kind": "video"}]}],
            "audio_tracks": [], "export_settings": {"resolution": "720p"}})
        return self.jobs.enqueue("workspace-a", "revision-a", manifest)

    def test_processes_and_publishes_a_valid_frozen_manifest(self):
        queued = self.enqueue()
        order = []
        active = False
        @contextmanager
        def workload_slot():
            nonlocal active
            order.append("slot")
            active = True
            try:
                yield
            finally:
                active = False
        def render(*args, **kwargs):
            order.append("render")
            self.assertTrue(active, "FFmpeg must hold the shared workload slot")
            return {"probe": {"format": {"duration": "1.0"}}}
        claim_next = self.jobs.claim_next
        def claim():
            order.append("claim")
            return claim_next()
        with patch("story_builder.assembly_export_worker.render_manifest",
                   side_effect=render) as render_manifest, \
             patch("story_builder.assembly_export_worker.register_generated_video",
                   return_value={"asset_id": "pa-export-1"}) as register, \
             patch("story_builder.assembly_export_worker.gpu_workload_lock", side_effect=workload_slot), \
             patch.object(self.jobs, "claim_next", side_effect=claim):
            self.assertTrue(process_one(self.root, self.jobs, self.selections))
            render_manifest.assert_called_once()
            self.assertEqual(render_manifest.call_args.args[0:2], (self.root, "workspace-a"))
            self.assertEqual(render_manifest.call_args.args[2]["manifest_id"], queued["manifest_id"])
            output = render_manifest.call_args.args[3]
            self.assertEqual(output, generated_root(self.root, "workspace-a") / "exports" / f"{queued['job_id']}.mp4")
            self.assertEqual(order, ["slot", "claim", "render"])
            register.assert_called_once_with(self.root, "workspace-a", f"exports/{queued['job_id']}.mp4", {
                "assembly_job_id": queued["job_id"], "manifest_id": queued["manifest_id"],
                "manifest_sha256": queued["manifest_sha256"], "probe": {"format": {"duration": "1.0"}}})

        finished = self.jobs.get("workspace-a", "revision-a", queued["job_id"])
        self.assertEqual(finished["state"], "completed")
        self.assertEqual(finished["output_asset_id"], "pa-export-1")
        self.assertIsNone(finished["error"])
        self.assertFalse(process_one(self.root, self.jobs, self.selections))

    def test_manifest_hash_mismatch_fails_without_rendering(self):
        queued = self.enqueue()
        with self.selections.ledger._connect() as db:
            db.execute("UPDATE story_assembly_export_manifests SET manifest_json=? WHERE manifest_id=?",
                (json.dumps({"tampered": True}), queued["manifest_id"]))
        with patch("story_builder.assembly_export_worker.render_manifest") as render:
            self.assertTrue(process_one(self.root, self.jobs, self.selections))
            render.assert_not_called()
        failed = self.jobs.get("workspace-a", "revision-a", queued["job_id"])
        self.assertEqual(failed["state"], "failed")
        self.assertIn("content does not match", failed["error"])

    def test_save_retry_uses_completed_asset_without_rendering_again(self):
        queued = self.enqueue()
        with self.jobs.ledger._connect() as db:
            db.execute("UPDATE story_assembly_export_jobs SET output_destination_json=? WHERE job_id=?",
                       (json.dumps({"mode":"folder","grant":"test"}), queued["job_id"]))
        with patch("story_builder.assembly_export_worker.render_manifest", return_value={"probe":{}}) as render, \
             patch("story_builder.assembly_export_worker.register_generated_video", return_value={"asset_id":"kept-result"}), \
             patch("story_builder.services.media_library.relocate_output", side_effect=ValueError("Folder unavailable")):
            self.assertTrue(process_one(self.root, self.jobs, self.selections))
            render.assert_called_once()
        failed = self.jobs.get("workspace-a", "revision-a", queued["job_id"])
        self.assertEqual(failed["state"], "failed")
        self.jobs.retry("workspace-a", "revision-a", queued["job_id"])
        with patch("story_builder.assembly_export_worker.render_manifest") as render, \
             patch("story_builder.services.media_library.relocate_output") as save:
            self.assertTrue(process_one(self.root, self.jobs, self.selections))
            render.assert_not_called()
            self.assertEqual(save.call_args.args[2], "kept-result")
        self.assertEqual(self.jobs.get("workspace-a", "revision-a", queued["job_id"])["state"], "completed")

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg is required")
    def test_real_cpu_export_worker_registers_playable_shared_library_output(self):
        workspace = "workspace-a"
        source = Path(self.temporary.name) / "source.mp4"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
            "-i", "testsrc2=duration=0.4:size=96x64:rate=8", "-an", "-c:v", "libx264",
            "-pix_fmt", "yuv420p", str(source)], check=True, capture_output=True, timeout=30)
        asset = register_upload(self.root, workspace, filename=source.name,
            content=source.read_bytes(), role="project_video")
        frozen = self.selections.save_export_manifest(workspace, "revision-a", {
            "state": "ready_for_render", "clips": [{"outputs": [{"kind": "video",
                "asset_id": asset["asset_id"], "sha256": asset["sha256"],
                "duration_seconds": asset["media"]["duration_seconds"], "has_audio": False}]}],
            "audio_tracks": [], "export_settings": {"resolution": "720p", "frame_rate": 24,
                "quality": 24, "audio_policy": "mute"}})
        queued = self.jobs.enqueue(workspace, "revision-a", frozen)

        self.assertTrue(process_one(self.root, self.jobs, self.selections))
        finished = self.jobs.get(workspace, "revision-a", queued["job_id"])
        self.assertEqual(finished["state"], "completed")
        self.assertEqual(finished["progress_percent"], 100)
        outputs = list_assets(self.root, workspace, kind="video")["assets"]
        exported = next(item for item in outputs if item["asset_id"] == finished["output_asset_id"])
        self.assertIn("project_video", exported["roles"])
        self.assertGreater(exported["media"]["duration_seconds"], 0)
        output_path, media_type, filename = asset_path(self.root, workspace, exported["asset_id"])
        self.assertEqual(media_type, "video/mp4")
        self.assertEqual(filename, f"{queued['job_id']}.mp4")
        self.assertTrue(output_path.is_file())
        self.assertEqual(exported["metadata"]["manifest_sha256"], queued["manifest_sha256"])


if __name__ == "__main__":
    unittest.main()
