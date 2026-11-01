from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

from story_builder.isolated_server import create_app
from story_builder.services.media_library import register_upload
from story_builder.services import video_repertoire
from story_builder.services.video_repertoire_worker import run_image_detailer
from story_builder.services.video_repertoire_worker import run_timed_tts
from story_builder.services.gpu_runtime import GPUAdmissionError


class ImageDetailerIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "data"
        video_repertoire.configure_roots(self.root, analyzer_root=Path(self.temporary.name) / "analyzer")

    @staticmethod
    def png() -> bytes:
        import binascii
        import struct
        import zlib
        def chunk(name, data):
            body = name + data
            return struct.pack(">I", len(data)) + body + struct.pack(">I", binascii.crc32(body) & 0xffffffff)
        row = b"\0" + b"\xff\0\0" * 2
        return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 2, 3, 8, 2, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(row * 3)) + chunk(b"IEND", b""))

    @staticmethod
    def wav() -> bytes:
        import wave
        output = io.BytesIO()
        with wave.open(output, "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(8000)
            audio.writeframes(b"\0\0" * 800)
        return output.getvalue()

    def call(self, app, method, path, payload=None):
        body = json.dumps(payload or {}).encode() if payload is not None else b""
        captured = []
        environ = {"REQUEST_METHOD": method, "PATH_INFO": path, "QUERY_STRING": "",
            "CONTENT_TYPE": "application/json", "CONTENT_LENGTH": str(len(body)), "wsgi.input": io.BytesIO(body)}
        response = b"".join(app(environ, lambda status, headers: captured.extend([status, headers])))
        return captured[0], json.loads(response) if response else None

    def test_api_creates_workspace_scoped_image_detailer_job_from_catalog_image(self):
        asset = register_upload(self.root, "workspace-a", filename="portrait.png", content=self.png(), role="project_image")
        app = create_app(data_root=self.root)
        with patch("story_builder.isolated_server.inspect_gpu_runtime", return_value={"recorded_at":"now"}), \
             patch("story_builder.isolated_server.video_repertoire.start_job", side_effect=lambda kind, job_id: video_repertoire.read_job(kind, job_id)):
            status, job = self.call(app, "POST", "/api/image-detailer/workspace-a/jobs",
                {"asset_id": asset["asset_id"], "mode": "quick"})
        self.assertEqual(status, "202 Accepted")
        self.assertEqual(job["request"]["asset_id"], asset["asset_id"])
        self.assertEqual(job["request"]["sha256"], asset["sha256"])
        status, rows = self.call(app, "GET", "/api/image-detailer/workspace-a/jobs")
        self.assertEqual(status, "200 OK")
        self.assertEqual([row["job_id"] for row in rows], [job["job_id"]])
        status, hidden = self.call(app, "GET", f"/api/image-detailer/workspace-b/jobs/{job['job_id']}")
        self.assertEqual(status, "404 Not Found")
        self.assertEqual(hidden["error"]["code"], "not_found")

    def test_worker_reuses_donor_analyzer_and_keeps_result_bound_to_image_hash(self):
        asset = register_upload(self.root, "workspace-a", filename="portrait.png", content=self.png(), role="project_image")
        job = video_repertoire.create_job("image-detailer", {"workspace_id":"workspace-a", "asset_id":asset["asset_id"], "sha256":asset["sha256"], "mode":"balanced"})
        fake = ModuleType("story_builder.services.image_detailer")
        fake.analyze_image = lambda path, mode: {"mode":mode,"analysis":{"summary":"A red portrait"},"frame_card":{"summary":"A red portrait"}}
        with patch.dict("sys.modules", {"story_builder.services.image_detailer":fake}), \
             patch("story_builder.services.video_repertoire_worker.event") as event:
            result = run_image_detailer(job["job_id"], job["request"])
        self.assertEqual(result["analysis"]["analysis"]["summary"], "A red portrait")
        self.assertEqual(result["sha256"], asset["sha256"])
        self.assertEqual(event.call_count, 3)
        with self.assertRaisesRegex(ValueError, "changed"):
            run_image_detailer(job["job_id"], {**job["request"], "sha256":"0" * 64})

    def test_invalid_mode_and_non_image_are_rejected_before_job_admission(self):
        image = register_upload(self.root, "workspace-a", filename="portrait.png", content=self.png(), role="project_image")
        audio = register_upload(self.root, "workspace-a", filename="sample.wav", content=self.wav(), role="project_audio")
        app = create_app(data_root=self.root)
        status, invalid = self.call(app, "POST", "/api/image-detailer/workspace-a/jobs", {"asset_id":image["asset_id"],"mode":"invalid"})
        self.assertEqual(status, "400 Bad Request")
        self.assertIn("mode", invalid["error"]["message"])
        status, wrong_kind = self.call(app, "POST", "/api/image-detailer/workspace-a/jobs", {"asset_id":audio["asset_id"]})
        self.assertEqual(status, "404 Not Found")
        self.assertEqual(wrong_kind["error"]["code"], "asset_not_found")

    def test_gpu_admission_blocks_new_image_job_before_durable_creation(self):
        image = register_upload(self.root, "workspace-a", filename="portrait.png", content=self.png(), role="project_image")
        app = create_app(data_root=self.root)
        with patch("story_builder.isolated_server.inspect_gpu_runtime", side_effect=GPUAdmissionError("Only 1.7 GiB free; 20 GiB is required.")), \
             patch("story_builder.isolated_server.video_repertoire.create_job") as create_job:
            status, response = self.call(app, "POST", "/api/image-detailer/workspace-a/jobs", {"asset_id":image["asset_id"]})
        self.assertEqual(status, "409 Conflict")
        self.assertEqual(response["error"]["code"], "gpu_not_ready")
        self.assertIn("1.7 GiB free", response["error"]["message"])
        create_job.assert_not_called()

    def test_gpu_admission_blocks_image_job_retry_before_worker_start(self):
        job = {"job_id":"12345678-1234-1234-1234-123456789abc", "request":{"workspace_id":"workspace-a"}, "status":"failed"}
        app = create_app(data_root=self.root)
        with patch("story_builder.isolated_server.video_repertoire.read_job", return_value=job), \
             patch("story_builder.isolated_server.inspect_gpu_runtime", side_effect=GPUAdmissionError("GPU admission unavailable.")), \
             patch("story_builder.isolated_server.video_repertoire.start_job") as start_job:
            status, response = self.call(app, "POST", f"/api/image-detailer/workspace-a/jobs/{job['job_id']}/retry")
        self.assertEqual(status, "409 Conflict")
        self.assertEqual(response["error"]["code"], "gpu_not_ready")
        start_job.assert_not_called()

    def test_api_saves_structured_analysis_only_to_its_workspace_source_image(self):
        image = register_upload(self.root, "workspace-a", filename="portrait.png", content=self.png(), role="project_image")
        app = create_app(data_root=self.root)
        analysis = {"subjects":["person"],"frame_card":{"summary":"Portrait"}}
        job = {"job_id":"12345678-1234-1234-1234-123456789abc", "status":"completed",
            "request":{"workspace_id":"workspace-a","asset_id":image["asset_id"]},
            "result":{"asset_id":image["asset_id"],"sha256":image["sha256"],"analysis":analysis}}
        with patch("story_builder.isolated_server.video_repertoire.read_job", return_value=job):
            status, saved = self.call(app, "POST", f"/api/media/workspace-a/assets/{image['asset_id']}/analysis", {
                "job_id":job["job_id"], "source_sha256":image["sha256"],
                "mode":"balanced", "analysis":analysis, "description":"Portrait", "tags":["person"]})
        self.assertEqual(status, "200 OK")
        self.assertEqual(saved["metadata"]["image_analyses"][0]["analysis"]["subjects"], ["person"])
        self.assertEqual(saved["description"], "Portrait")
        with patch("story_builder.isolated_server.video_repertoire.read_job", return_value=job):
            status, hidden = self.call(app, "POST", f"/api/media/workspace-b/assets/{image['asset_id']}/analysis", {
                "job_id":job["job_id"], "source_sha256":image["sha256"],
                "mode":"balanced", "analysis":analysis, "description":"", "tags":[]})
        self.assertEqual(status, "422 Unprocessable Entity")
        self.assertIn("workspace", hidden["error"]["message"])

    def test_voice_enrollment_copies_only_selected_workspace_audio_and_transcript(self):
        asset = register_upload(self.root, "workspace-a", filename="dialogue.wav", content=self.wav(), role="project_audio")
        comfy_root = Path(self.temporary.name) / "ComfyUI"
        app = create_app(data_root=self.root)
        with patch("story_builder.isolated_server.audio_catalog.comfyui_root", return_value=comfy_root), \
             patch("story_builder.isolated_server.audio_catalog.refresh_live_voice_catalog", return_value={
                 "refreshed": True, "live_count": 1, "restart_required": False}):
            status, result = self.call(app, "POST", "/api/audio/workspace-a/voices", {
                "asset_id": asset["asset_id"], "name": "Arjun reference", "transcript": "Exact spoken words."})
            self.assertEqual(status, "201 Created")
            self.assertTrue(result["voice"]["discoverable"])
            self.assertNotIn("audio_path", result["voice"])
            audio_file = comfy_root / "models" / "voices" / "Arjun reference.wav"
            transcript_file = comfy_root / "models" / "voices" / "Arjun reference.reference.txt"
            self.assertEqual(audio_file.read_bytes(), self.wav())
            self.assertEqual(transcript_file.read_text().strip(), "Exact spoken words.")
            status, conflict = self.call(app, "POST", "/api/audio/workspace-a/voices", {
                "asset_id": asset["asset_id"], "name": "Arjun reference", "transcript": "Exact spoken words."})
            self.assertEqual(status, "409 Conflict")
            self.assertEqual(conflict["error"]["code"], "voice_name_conflict")
            status, voices = self.call(app, "GET", "/api/audio/voices")
            self.assertEqual(status, "200 OK")
            self.assertEqual([voice["name"] for voice in voices], ["Arjun reference"])

    def test_timed_tts_api_validates_voice_map_and_hides_srt_from_public_job(self):
        voices = [{"id":"voice-arjun", "name":"Arjun", "source":"user", "relative_path":"Arjun.wav",
            "discoverable":True, "has_transcript":True, "user_managed":True}]
        app = create_app(data_root=self.root)
        _, workspace = self.call(app, "POST", "/api/story/workspaces", {"title":"Timed dialogue", "source_text":"A story."})
        workspace_id = workspace["workspace_id"]
        payload = {"srt_content":"1\n00:00:00,000 --> 00:00:02,000\n[Arjun] Wait here. [pause:1s]",
            "characters":[{"name":"Arjun", "reference_voice_id":"voice-arjun", "language":"en"}],
            "settings":{"language":"English", "timing_mode":"smart_natural"}}
        with patch("story_builder.isolated_server.audio_catalog.discover_voices", return_value=voices), \
             patch("story_builder.isolated_server.audio_tts.validate_live_nodes"), \
             patch("story_builder.isolated_server.video_repertoire.start_job", side_effect=lambda kind, job_id: video_repertoire.read_job(kind, job_id)):
            status, result = self.call(app, "POST", f"/api/audio/{workspace_id}/timed-tts/jobs", payload)
            self.assertEqual(status, "202 Accepted", result)
            self.assertNotIn("request", result)
            self.assertNotIn("srt_content", json.dumps(result))
            status, rows = self.call(app, "GET", f"/api/audio/{workspace_id}/timed-tts/jobs")
            self.assertEqual(status, "200 OK")
            self.assertEqual([row["job_id"] for row in rows], [result["job_id"]])
            status, hidden = self.call(app, "GET", f"/api/audio/workspace-other/timed-tts/jobs/{result['job_id']}")
            self.assertEqual(status, "404 Not Found")
            with patch("story_builder.isolated_server.audio_tts.validate_live_nodes", side_effect=RuntimeError("Missing ChatterBox node")), \
                 patch("story_builder.isolated_server.video_repertoire.start_job") as start:
                status, unavailable = self.call(app, "POST", f"/api/audio/{workspace_id}/timed-tts/jobs", payload)
            self.assertEqual(status, "503 Service Unavailable")
            self.assertEqual(unavailable["error"]["code"], "timed_tts_unavailable")
            start.assert_not_called()
            status, invalid = self.call(app, "POST", f"/api/audio/{workspace_id}/timed-tts/jobs", {
                **payload, "characters":[{"name":"Arjun", "reference_voice_id":"missing", "language":"en"}]})
            self.assertEqual(status, "400 Bad Request")
            self.assertIn("voice", invalid["error"]["message"].lower())

    def test_timed_tts_worker_publishes_completed_audio_to_shared_library(self):
        job = video_repertoire.create_job("timed-tts", {"workspace_id":"workspace-a", "srt_content":
            "1\n00:00:00,000 --> 00:00:02,000\n[Arjun] Wait.", "characters":[{"name":"Arjun",
            "reference_voice_id":"voice-arjun", "language":"en"}], "settings":{"language":"English"}})
        voices = [{"id":"voice-arjun", "name":"Arjun", "source":"user", "relative_path":"Arjun.wav", "discoverable":True}]
        def complete(**kwargs):
            kwargs["job"]["status"] = "completed"
            kwargs["job"]["reports"] = {"timing_report.txt":"ok"}
        expected = {"asset_id":"pa-timed", "kind":"audio", "content_url":"/api/media/workspace-a/assets/pa-timed/content"}
        with patch("story_builder.services.audio_catalog.discover_voices", return_value=voices), \
             patch("story_builder.services.audio_tts.run_timed_job", side_effect=complete), \
             patch("story_builder.services.media_library.register_generated_audio", return_value=expected) as register:
            result = run_timed_tts(job["job_id"], job["request"])
        self.assertEqual(result["asset"], expected)
        self.assertEqual(result["reports"], {"timing_report.txt":"ok"})
        register.assert_called_once_with(self.root, "workspace-a", f"audio/{job['job_id']}.flac", {
            "source":"timed_tts", "job_id":job["job_id"], "workflow":"chatterbox_timed_multichar",
            "speakers":["arjun"], "timing_mode":"smart_natural"})

    def test_audio_reconstruct_reuses_workspace_audio_and_publishes_accepted_take(self):
        asset = register_upload(self.root, "workspace-a", filename="recorded.wav", content=self.wav(), role="project_audio")
        app = create_app(data_root=self.root)
        base = "/api/audio/workspace-a/reconstruct"
        status, _ = self.call(app, "POST", f"{base}/calibration", {
            "character_name":"Arjun", "sentence":"Testing one two.", "settings":{"model":"reference"}})
        self.assertEqual(status, "200 OK")
        status, part = self.call(app, "POST", f"{base}/parts", {
            "part_id":"scene1_line1", "character_name":"Arjun", "sequence":1,
            "expected_text":"Wait here."})
        self.assertEqual(status, "201 Created")
        status, take = self.call(app, "POST", f"{base}/parts/{part['part_id']}/takes", {
            "asset_id":asset["asset_id"], "transcript":"Wait here."})
        self.assertEqual(status, "201 Created")
        self.assertEqual(take["transcript"], "Wait here.")
        status, accepted = self.call(app, "POST", f"{base}/parts/{part['part_id']}/accept/{take['take_id']}", {})
        self.assertEqual(status, "200 OK")
        self.assertEqual(accepted["asset"]["kind"], "audio")
        self.assertIn("audio_reconstruct", accepted["asset"]["metadata"]["source"])
        status, rows = self.call(app, "GET", "/api/media/workspace-a/assets")
        self.assertEqual(status, "200 OK")
        self.assertEqual({row["asset_id"] for row in rows["assets"] if row["kind"] == "audio"}, {asset["asset_id"], accepted["asset"]["asset_id"]})

    def test_audio_reconstruct_rejects_non_audio_and_unsafe_character_names(self):
        image = register_upload(self.root, "workspace-a", filename="portrait.png", content=self.png(), role="project_image")
        app = create_app(data_root=self.root)
        base = "/api/audio/workspace-a/reconstruct"
        status, unsafe = self.call(app, "POST", f"{base}/calibration", {
            "character_name":"../escape", "sentence":"Testing.", "settings":{}})
        self.assertEqual(status, "400 Bad Request")
        self.assertIn("Character name", unsafe["error"]["message"])
        status, _ = self.call(app, "POST", f"{base}/calibration", {
            "character_name":"Arjun", "sentence":"Testing.", "settings":{}})
        self.assertEqual(status, "200 OK")
        status, part = self.call(app, "POST", f"{base}/parts", {
            "part_id":"line_1", "character_name":"Arjun", "sequence":1, "expected_text":"Hello."})
        self.assertEqual(status, "201 Created")
        status, error = self.call(app, "POST", f"{base}/parts/{part['part_id']}/takes", {
            "asset_id":image["asset_id"], "transcript":"Hello."})
        self.assertEqual(status, "400 Bad Request")
        self.assertIn("not audio", error["error"]["message"])


if __name__ == "__main__":
    unittest.main()
