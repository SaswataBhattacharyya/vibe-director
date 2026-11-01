from __future__ import annotations

import io
import json
import base64
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from story_builder.isolated_server import create_app
from story_builder.services import audio_effects, video_repertoire, video_repertoire_worker
from story_builder.services.media_library import register_upload


class AudioEffectsAdapterTests(unittest.TestCase):
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
        self.asset = register_upload(self.data, "workspace-a", filename="source.wav",
            content=audio.getvalue(), role="project_audio")
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

    def test_capabilities_report_copied_workflow_files_without_claiming_runtime_ready(self):
        app = create_app(data_root=self.data)
        status, result = self.call(app, "GET", "/api/audio/effects/capabilities")
        self.assertEqual(status, "200 OK")
        self.assertEqual({row["id"] for row in result["operations"]}, set(audio_effects.OPERATION_WORKFLOWS) | {"simple"})
        self.assertTrue(all(row["requires_live_validation"] for row in result["operations"] if row["id"] != "simple"))
        self.assertFalse(next(row for row in result["operations"] if row["id"] == "simple")["requires_live_validation"])

    def test_job_stages_only_workspace_audio_and_keeps_private_paths_out_of_response(self):
        app = create_app(data_root=self.data)
        with patch("story_builder.isolated_server.video_repertoire.start_job",
                   side_effect=lambda kind, job_id:video_repertoire.read_job(kind, job_id)):
            status, response = self.call(app, "POST", "/api/audio/workspace-a/effects/jobs", {
                "operation":"voice_repair","asset_id":self.asset["asset_id"],"settings":{"restoration_mode":1}})
        self.assertEqual(status, "202 Accepted", response)
        self.assertNotIn("request", response)
        job = video_repertoire.read_job("audio-effects", response["job_id"])
        staged = self.data / "projects" / "workspace-a" / "media" / "generated" / job["request"]["source_relative_path"]
        self.assertTrue(staged.is_file())
        self.assertEqual(job["request"]["asset_id"], self.asset["asset_id"])
        status, missing = self.call(app, "GET", f"/api/audio/workspace-b/effects/jobs/{response['job_id']}")
        self.assertEqual(status, "404 Not Found")

    def test_rejects_unknown_operation_and_non_audio_reference(self):
        image = register_upload(self.data, "workspace-a", filename="still.png",
            content=base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jwZkAAAAASUVORK5CYII="), role="project_image")
        app = create_app(data_root=self.data)
        status, error = self.call(app, "POST", "/api/audio/workspace-a/effects/jobs", {
            "operation":"not-an-effect","asset_id":self.asset["asset_id"],"settings":{}})
        self.assertEqual(status, "400 Bad Request")
        self.assertIn("Unknown audio effect", error["error"]["message"])
        status, error = self.call(app, "POST", "/api/audio/workspace-a/effects/jobs", {
            "operation":"voice_repair","asset_id":image["asset_id"],"settings":{}})
        self.assertEqual(status, "400 Bad Request")
        self.assertIn("audio asset", error["error"]["message"])

    def test_worker_adapts_reused_effect_into_shared_audio_library(self):
        app = create_app(data_root=self.data)
        with patch("story_builder.isolated_server.video_repertoire.start_job",
                   side_effect=lambda kind, job_id:video_repertoire.read_job(kind, job_id)):
            _, response = self.call(app, "POST", "/api/audio/workspace-a/effects/jobs", {
                "operation":"voice_repair","asset_id":self.asset["asset_id"],"settings":{}})
        job = video_repertoire.read_job("audio-effects", response["job_id"])
        workspace_root = self.data / "projects" / "workspace-a" / "media" / "generated"
        def fake_run(*, project_dir, output_root, workspace_output, job, source, update, **_):
            output = project_dir / "audio" / "effects" / job["job_id"] / "fixed.wav"
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(source.read_bytes())
            export = workspace_output / "audio" / f"{job['job_id']}.flac"
            export.parent.mkdir(parents=True, exist_ok=True)
            export.write_bytes(output.read_bytes())
            job.update(status="completed", export_path=str(export), prompt_id="prompt-mock", source_info={"duration":0.1})
            update(job)
        with patch.dict("os.environ", {"VIBE_DIRECTOR_DATA_DIR":str(self.data)}), \
             patch.object(audio_effects, "run_effect_job", side_effect=fake_run), \
             patch("story_builder.services.media_library.register_generated_audio",
                   return_value={"asset_id":"pa-1234567890abcdef","kind":"audio"}) as register:
            result = video_repertoire_worker._run_audio_effect(response["job_id"], job["request"])
        self.assertEqual(result["asset"]["asset_id"], "pa-1234567890abcdef")
        self.assertEqual(result["operation"], "voice_repair")
        self.assertTrue((self.data / "audio_studio" / "voice_changes" / response["job_id"] / "audio" / f"{response['job_id']}.flac").is_file())
        self.assertFalse((workspace_root / "generated_audio").exists())
        register.assert_called_once()


if __name__ == "__main__":
    unittest.main()
