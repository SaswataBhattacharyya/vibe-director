from __future__ import annotations

import io
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from story_builder.isolated_server import create_app
from story_builder.assembly_export_worker import process_one
from story_builder.services.assembly import AssemblyExportJobs, AssemblySelections
from story_builder.services.media_library import asset_path, list_assets, register_upload
from story_builder.services.production_ledger import ProductionLedger


class AssemblyExportApiTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "data"
        self.ledger_path = self.root / "services/production/ledger.sqlite3"

    @staticmethod
    def call(app, method, path, payload=None):
        body = json.dumps(payload).encode() if payload is not None else b""
        captured = []
        path_info, _, query = path.partition("?")
        environ = {"REQUEST_METHOD": method, "PATH_INFO": path_info, "QUERY_STRING": query,
            "CONTENT_TYPE": "application/json", "CONTENT_LENGTH": str(len(body)), "wsgi.input": io.BytesIO(body)}
        response = b"".join(app(environ, lambda status, headers: captured.extend([status, headers])))
        return captured[0], json.loads(response) if response else None

    def test_export_api_queues_lists_and_retries_workspace_scoped_job(self):
        ledger = ProductionLedger(self.ledger_path)
        store = AssemblySelections(ledger)
        manifest = store.save_export_manifest("workspace-a", "revision-a", {
            "state": "ready_for_render", "clips": [], "audio_tracks": [], "export_settings": {}})
        app = create_app(data_root=self.root)
        accepted_revision = {"accepted": True, "screenplay": {"scenes": []}}
        setup = {"setup": {"mode": "assisted_manual", "automate_steps": {"video": False}}}
        with patch("story_builder.isolated_server.StoryAuthoring.get_screenplay_revision",
                   return_value=accepted_revision), \
             patch("story_builder.isolated_server.ProductionSetup.get", return_value=setup):
            status, queued = self.call(app, "POST", "/api/story/workspaces/workspace-a/assembly-export-jobs",
                {"screenplay_revision_id": "revision-a", "manifest_id": manifest["manifest_id"]})
            self.assertEqual(status, "202 Accepted")
            self.assertEqual(queued["state"], "queued")
            status, listing = self.call(app, "GET", "/api/story/workspaces/workspace-a/assembly-export-jobs?screenplay_revision_id=revision-a")
            self.assertEqual(status, "200 OK")
            self.assertEqual([job["job_id"] for job in listing["jobs"]], [queued["job_id"]])

            jobs = AssemblyExportJobs(ledger)
            jobs.claim_next()
            jobs.fail(queued["job_id"], "synthetic failure")
            status, retried = self.call(app, "POST",
                f"/api/story/workspaces/workspace-a/assembly-export-jobs/{queued['job_id']}/retry",
                {"screenplay_revision_id": "revision-a"})
            self.assertEqual(status, "202 Accepted")
            self.assertEqual(retried["state"], "queued")

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg is required")
    def test_accepted_take_flows_through_export_api_and_real_worker_to_playable_library_asset(self):
        workspace, revision = "workspace-a", "revision-a"
        source = Path(self.temporary.name) / "accepted-take.mp4"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
            "-i", "testsrc2=duration=0.4:size=96x64:rate=8", "-an", "-c:v", "libx264",
            "-pix_fmt", "yuv420p", str(source)], check=True, capture_output=True, timeout=30)
        source_asset = register_upload(self.root, workspace, filename=source.name,
            content=source.read_bytes(), role="project_video")
        request = {"workflow_id": "minimax_h3_t2v_local_v1", "prompt": "Synthetic accepted take"}
        import hashlib
        request_hash = hashlib.sha256(json.dumps(request, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False).encode()).hexdigest()
        accepted_take = {"job_id": "take-a", "clip_id": "1.1.1", "status": "accepted",
            "request": request, "request_hash": request_hash,
            "source_lineage": {"screenplay_revision_id": revision, "scene_number": 1, "shot_number": 1},
            "outputs": [{"kind": "video", "asset_id": source_asset["asset_id"],
                "shared_asset_id": source_asset["asset_id"], "sha256": source_asset["sha256"],
                "duration_seconds": source_asset["media"]["duration_seconds"], "has_audio": False,
                "has_video": True, "playback_url": f"/api/video/assets/{source_asset['asset_id']}"}]}
        app = create_app(data_root=self.root)
        accepted_revision = {"accepted": True, "source_revision_id": "source-a",
            "style_selection_snapshot_id": None,
            "screenplay": {"scenes": [{"scene_number": 1, "shots": [{"shot_number": 1}]}]}}
        setup = {"setup": {"mode": "assisted_manual", "automate_steps": {"video": False}}}
        with patch("story_builder.isolated_server.StoryAuthoring.get_screenplay_revision",
                   return_value=accepted_revision), \
             patch("story_builder.isolated_server.ProductionSetup.get", return_value=setup), \
             patch("story_builder.services.isolated_video_jobs.IsolatedVideoJobs.list_jobs",
                   return_value=[accepted_take]):
            status, preview = self.call(app, "GET",
                f"/api/story/workspaces/{workspace}/assembly-preview?screenplay_revision_id={revision}")
            self.assertEqual(status, "200 OK")
            self.assertEqual(preview["missing_clip_count"], 0)
            self.assertEqual(preview["clips"][0]["accepted_takes"][0]["job_id"], "take-a")

            status, selected = self.call(app, "PUT", f"/api/story/workspaces/{workspace}/assembly-selection",
                {"screenplay_revision_id": revision, "selections": {"1.1.1": "take-a"}})
            self.assertEqual(status, "200 OK")
            self.assertEqual(selected["selections"], {"1.1.1": "take-a"})

            status, frozen = self.call(app, "POST", f"/api/story/workspaces/{workspace}/assembly-snapshots",
                {"screenplay_revision_id": revision, "selections": {"1.1.1": "take-a"}})
            self.assertEqual(status, "201 Created", frozen)
            self.assertEqual(frozen["snapshot"]["clips"][0]["outputs"][0]["asset_id"], source_asset["asset_id"])

            status, manifest = self.call(app, "POST", f"/api/story/workspaces/{workspace}/assembly-exports",
                {"screenplay_revision_id": revision, "snapshot_id": frozen["snapshot_id"],
                 "settings": {"resolution": "720p", "frame_rate": 24, "quality": 24,
                    "audio_policy": "mute"}})
            self.assertEqual(status, "201 Created")
            self.assertEqual(manifest["manifest"]["state"], "ready_for_render")

            status, queued = self.call(app, "POST", f"/api/story/workspaces/{workspace}/assembly-export-jobs",
                {"screenplay_revision_id": revision, "manifest_id": manifest["manifest_id"]})
            self.assertEqual(status, "202 Accepted")
            self.assertEqual(queued["state"], "queued")

        store = AssemblyExportJobs(ProductionLedger(self.ledger_path))
        selections = AssemblySelections(ProductionLedger(self.ledger_path))
        self.assertTrue(process_one(self.root, store, selections))
        finished = store.get(workspace, revision, queued["job_id"])
        self.assertEqual(finished["state"], "completed")
        assets = list_assets(self.root, workspace, kind="video")["assets"]
        exported = next(asset for asset in assets if asset["asset_id"] == finished["output_asset_id"])
        path, media_type, filename = asset_path(self.root, workspace, exported["asset_id"])
        self.assertTrue(path.is_file())
        self.assertEqual(media_type, "video/mp4")
        self.assertEqual(filename, f"{queued['job_id']}.mp4")
        self.assertGreater(exported["media"]["duration_seconds"], 0)
        self.assertIn("video", exported["media"]["streams"])
        self.assertEqual(exported["metadata"]["manifest_sha256"], manifest["manifest_sha256"])
        captured = []
        environ = {"REQUEST_METHOD": "GET", "PATH_INFO": f"/api/media/{workspace}/assets/{exported['asset_id']}/content",
            "QUERY_STRING": "", "CONTENT_LENGTH": "0", "wsgi.input": io.BytesIO(b"")}
        playback = b"".join(app(environ, lambda status, headers: captured.extend([status, headers])))
        self.assertEqual(captured[0], "200 OK")
        response_headers = dict(captured[1])
        self.assertEqual(response_headers.get("Content-Type"), "video/mp4")
        self.assertGreater(len(playback), 0)


if __name__ == "__main__":
    unittest.main()
