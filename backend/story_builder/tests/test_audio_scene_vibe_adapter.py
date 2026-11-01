from __future__ import annotations

import io
import json
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from story_builder.isolated_server import create_app
from story_builder.services import audio_scene, video_repertoire, video_repertoire_worker
from story_builder.services.media_library import register_upload


class AudioSceneAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.data = Path(self.temp.name) / "data"
        audio = io.BytesIO()
        with wave.open(audio, "wb") as writer:
            writer.setnchannels(1)
            writer.setsampwidth(2)
            writer.setframerate(8000)
            writer.writeframes(b"\0\0" * 800)
        self.source_bytes = audio.getvalue()
        self.asset = register_upload(self.data, "workspace-a", filename="source.wav",
            content=self.source_bytes, role="project_audio")
        video_repertoire.configure_roots(self.data)

    def tearDown(self):
        video_repertoire.configure_roots(Path(self.temp.name) / "reset")

    @staticmethod
    def call(app, method, path, payload=None):
        body = json.dumps(payload or {}).encode() if payload is not None else b""
        response = []
        environ = {"REQUEST_METHOD":method,"PATH_INFO":path,"QUERY_STRING":"",
            "CONTENT_TYPE":"application/json","CONTENT_LENGTH":str(len(body)),"wsgi.input":io.BytesIO(body)}
        content = b"".join(app(environ, lambda status, headers:response.extend([status,headers])))
        return response[0], json.loads(content) if content else None

    def test_edit_ranges_are_sorted_and_overlaps_rejected(self):
        edits = audio_scene.validate_edits([{"start":3,"end":4},{"start":1,"end":2}])
        self.assertEqual([item["start"] for item in edits], [1, 3])
        with self.assertRaisesRegex(audio_scene.SceneJobError, "overlap"):
            audio_scene.validate_edits([{"start":1,"end":3},{"start":2,"end":4}])

    def test_capabilities_report_only_installed_donor_scripts(self):
        scripts = Path(self.temp.name) / "suite" / "scripts"
        scripts.mkdir(parents=True)
        (scripts / "split_scene_audio.py").touch()
        with patch("story_builder.services.audio_scene.suite_root", return_value=scripts.parent):
            result = audio_scene.capabilities()
        self.assertTrue(result["checks"]["split"]["available"])
        self.assertFalse(result["checks"]["simple_stitch"]["available"])
        self.assertFalse(result["available"])

    def test_split_job_is_workspace_scoped_and_stages_only_selected_audio(self):
        app = create_app(data_root=self.data)
        with patch("story_builder.isolated_server.video_repertoire.start_job",
                   side_effect=lambda kind, job_id:video_repertoire.read_job(kind, job_id)):
            status, result = self.call(app, "POST", "/api/audio/workspace-a/scene-surgery/jobs", {
                "asset_id":self.asset["asset_id"],"edits":[{"start":0.1,"end":0.2,"text":"line"}]})
        self.assertEqual(status, "202 Accepted", result)
        job = video_repertoire.read_job("audio-scene-split", result["job_id"])
        staged = self.data / "projects" / "workspace-a" / "media" / "generated" / job["request"]["source_relative_path"]
        self.assertEqual(staged.read_bytes(), self.source_bytes)
        self.assertNotIn("request", result)
        status, hidden = self.call(app, "GET", f"/api/audio/workspace-b/scene-surgery/jobs/{result['job_id']}")
        self.assertEqual(status, "404 Not Found")

    def test_rejects_non_audio_assets_and_invalid_edits_before_queueing(self):
        app = create_app(data_root=self.data)
        with patch("story_builder.isolated_server.video_repertoire.start_job") as start:
            status, bad_edits = self.call(app, "POST", "/api/audio/workspace-a/scene-surgery/jobs", {
                "asset_id":self.asset["asset_id"],"edits":[{"start":2,"end":1}]})
            self.assertEqual(status, "400 Bad Request")
            self.assertIn("invalid range", bad_edits["error"]["message"])
            start.assert_not_called()

    def test_worker_registers_donor_split_clips_in_shared_library(self):
        app = create_app(data_root=self.data)
        with patch("story_builder.isolated_server.video_repertoire.start_job",
                   side_effect=lambda kind, job_id:video_repertoire.read_job(kind, job_id)):
            _, accepted = self.call(app, "POST", "/api/audio/workspace-a/scene-surgery/jobs", {
                "asset_id":self.asset["asset_id"],"edits":[{"start":0.1,"end":0.2}]})
        job = video_repertoire.read_job("audio-scene-split", accepted["job_id"])
        workspace = self.data / "projects" / "workspace-a" / "media" / "generated"
        clip = workspace / "audio" / "scenes" / job["job_id"] / "parts" / "clip.wav"
        clip.parent.mkdir(parents=True)
        clip.write_bytes((workspace / job["request"]["source_relative_path"]).read_bytes())

        def fake_split(*, job, project_dir, source, edits, transcript, update):
            update({"status":"completed","stage":"completed","progress":95,
                "manifest":{"clips":[{"clip_index":1,"split_file":"clip.wav","start":0.1,"end":0.2,"text":"line",
                    "relative_path":f"audio/scenes/{job['job_id']}/parts/clip.wav"}]}})

        with patch.dict("os.environ", {"VIBE_DIRECTOR_DATA_DIR":str(self.data)}), \
             patch("story_builder.services.audio_scene.run_split", side_effect=fake_split):
            result = video_repertoire_worker._run_audio_scene_split(accepted["job_id"], job["request"])
        self.assertEqual(len(result["clips"]), 1)
        self.assertEqual(result["clips"][0]["asset"]["roles"], ["project_audio"])
        self.assertEqual(result["clips"][0]["asset"]["metadata"]["source"], "audio_scene_split")
        self.assertFalse((workspace / job["request"]["source_relative_path"]).exists())

    def test_stitch_worker_publishes_result_and_keeps_split_manifest_link(self):
        app = create_app(data_root=self.data)
        with patch("story_builder.isolated_server.video_repertoire.start_job",
                   side_effect=lambda kind, job_id:video_repertoire.read_job(kind, job_id)):
            _, split_response = self.call(app, "POST", "/api/audio/workspace-a/scene-surgery/jobs", {
                "asset_id":self.asset["asset_id"],"edits":[{"start":0.1,"end":0.2}]})
        split = video_repertoire.read_job("audio-scene-split", split_response["job_id"])
        workspace = self.data / "projects" / "workspace-a" / "media" / "generated"
        clip_path = workspace / "audio" / "scenes" / split["job_id"] / "parts" / "clip.wav"
        clip_path.parent.mkdir(parents=True)
        clip_path.write_bytes(self.source_bytes)
        split["status"] = "completed"
        split["result"] = {"manifest":{"clips":[{"clip_index":1,"split_file":"clip.wav","start":0.1,"end":0.2,"text":"line"}]}}
        video_repertoire._atomic_json(video_repertoire.job_path("audio-scene-split", split["job_id"]), split)
        with patch("story_builder.isolated_server.video_repertoire.start_job",
                   side_effect=lambda kind, job_id:video_repertoire.read_job(kind, job_id)):
            status, stitch_response = self.call(app, "POST", "/api/audio/workspace-a/scene-surgery/stitch-jobs", {
                "split_job_id":split["job_id"],"mode":"timed","gaps":{"1":0.25},"replacement_asset_ids":{}})
        self.assertEqual(status, "202 Accepted", stitch_response)
        stitch = video_repertoire.read_job("audio-scene-stitch", stitch_response["job_id"])
        with patch.dict("os.environ", {"VIBE_DIRECTOR_DATA_DIR":str(self.data)}), \
             patch("story_builder.services.audio_scene.run_stitch") as run:
            def fake_stitch(*, job, project_dir, split_job, replacements, gaps, mode, update):
                output = project_dir / "audio" / "scenes" / job["job_id"] / "final.wav"
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(self.source_bytes)
                update({"status":"completed","stage":"completed","progress":95,
                    "output_path":f"audio/scenes/{job['job_id']}/final.wav","provenance":[]})
            run.side_effect = fake_stitch
            result = video_repertoire_worker._run_audio_scene_stitch(stitch["job_id"], stitch["request"])
        self.assertEqual(result["asset"]["metadata"]["split_job_id"], split["job_id"])
        self.assertEqual(result["asset"]["metadata"]["mode"], "timed")


if __name__ == "__main__":
    unittest.main()
