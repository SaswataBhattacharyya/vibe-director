from __future__ import annotations

import io
import json
import base64
import shutil
import tempfile
import unittest
import wave
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from story_builder.isolated_server import create_app
from story_builder.services import audio_utilities, video_repertoire
from story_builder.services.media_jobs import MediaJobError
from story_builder.services.media_library import list_assets, register_upload


class AudioUtilitiesIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.data = Path(self.temp.name) / "data"
        wav = io.BytesIO()
        with wave.open(wav, "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(8000)
            audio.writeframes(b"\0\0" * 800)
        self.asset = register_upload(self.data, "workspace-a", filename="voice.wav",
            content=wav.getvalue(), role="project_audio")
        video_repertoire.configure_roots(self.data)

    def tearDown(self):
        video_repertoire.configure_roots(Path(self.temp.name) / "reset")

    @staticmethod
    def call(app, method, path, payload=None):
        body = json.dumps(payload or {}).encode() if payload is not None else b""
        response = []
        environ = {"REQUEST_METHOD": method, "PATH_INFO": path, "QUERY_STRING": "",
            "CONTENT_TYPE": "application/json", "CONTENT_LENGTH": str(len(body)), "wsgi.input": io.BytesIO(body)}
        content = b"".join(app(environ, lambda status, headers: response.extend([status, headers])))
        return response[0], json.loads(content) if content else None

    def test_capabilities_route_and_job_use_shared_workspace_asset(self):
        app = create_app(data_root=self.data)
        caps = {"operations": [{"id": "extract_mp3", "status": "available", "runtime": "ffmpeg"}]}
        with patch.object(audio_utilities, "capabilities", return_value=caps):
            status, payload = self.call(app, "GET", "/api/audio/utilities/capabilities")
        self.assertEqual(status, "200 OK")
        self.assertEqual(payload, caps)

        with patch.object(audio_utilities, "capabilities", return_value=caps), \
             patch("story_builder.isolated_server.video_repertoire.start_job",
                   side_effect=lambda kind, job_id: video_repertoire.read_job(kind, job_id)):
            status, job = self.call(app, "POST", "/api/audio/workspace-a/utilities/jobs", {
                "operation": "extract_mp3", "asset_ids": [self.asset["asset_id"]], "settings": {"quality": 3}})
        self.assertEqual(status, "202 Accepted", job)
        persisted = video_repertoire.read_job("audio-utilities", job["job_id"])
        self.assertEqual(persisted["request"]["workspace_id"], "workspace-a")
        self.assertEqual(persisted["request"]["inputs"][0]["asset_id"], self.asset["asset_id"])
        self.assertEqual(persisted["request"]["settings"]["quality"], 3)

        status, _ = self.call(app, "GET", f"/api/audio/other-workspace/utilities/jobs/{job['job_id']}")
        self.assertEqual(status, "404 Not Found")

    def test_shared_asset_staging_rejects_video_for_audio_only_operation(self):
        image = register_upload(self.data, "workspace-a", filename="wrong.png",
            content=base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jwZkAAAAASUVORK5CYII="),
            role="project_image")
        with self.assertRaisesRegex(audio_utilities.AudioUtilityError, "not supported"):
            audio_utilities.stage_assets(self.data, "workspace-a", "stage-test", [image["asset_id"]], "demucs_stems")

    @unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg is required for this CPU-only integration check")
    def test_mp3_extraction_publishes_derivative_in_shared_library(self):
        staged = audio_utilities.stage_assets(self.data, "workspace-a", "stage-mp3",
            [self.asset["asset_id"]], "extract_mp3")
        job = {"job_id": "audio-utilities-test", "request": {"workspace_id": "workspace-a",
            "operation": "extract_mp3", "settings": {"quality": 4}, "inputs": staged,
            "staging_id": "stage-mp3"}}
        with patch.object(audio_utilities, "gpu_workload_guard",
                          side_effect=AssertionError("CPU-only MP3 extraction must not claim the GPU slot")):
            outputs = audio_utilities.run_job(job, data_root=self.data, progress=lambda _event: None)
        self.assertEqual(len(outputs), 1)
        self.assertEqual(outputs[0]["kind"], "audio")
        self.assertIn("project_audio", outputs[0]["roles"])
        listed = list_assets(self.data, "workspace-a", kind="audio")["assets"]
        self.assertIn(outputs[0]["asset_id"], {row["asset_id"] for row in listed})

    def test_multi_file_gpu_utility_holds_one_slot_for_the_entire_job(self):
        source, _media_type, _filename = audio_utilities.media_library.asset_path(
            self.data, "workspace-a", self.asset["asset_id"])
        second = register_upload(self.data, "workspace-a", filename="music.wav",
            content=Path(source).read_bytes()[:-2] + b"\x01\x00", role="project_audio")
        staged = audio_utilities.stage_assets(self.data, "workspace-a", "stage-stems",
            [self.asset["asset_id"], second["asset_id"]], "demucs_stems")
        job = {"job_id": "multi-file-stems", "request": {"workspace_id": "workspace-a",
            "operation": "demucs_stems", "settings": {"device": "cuda", "stems": 2},
            "inputs": staged, "staging_id": "stage-stems"}}
        events = {"entered": 0, "active": 0, "max_active": 0, "outputs": 0}

        @contextmanager
        def fake_gpu_slot(**_kwargs):
            events["entered"] += 1
            events["active"] += 1
            events["max_active"] = max(events["max_active"], events["active"])
            try:
                yield
            finally:
                events["active"] -= 1

        def fake_run(command, *_args, **_kwargs):
            if command[:2] == ["docker", "cp"] and "output/." in command[2]:
                destination = Path(command[3])
                destination.mkdir(parents=True, exist_ok=True)
                events["outputs"] += 1
                (destination / "vocals.wav").write_bytes(Path(source).read_bytes()[:-2] + bytes([events["outputs"], 0]))

        with patch.object(audio_utilities, "gpu_workload_guard", side_effect=fake_gpu_slot), \
             patch.object(audio_utilities, "_run", side_effect=fake_run):
            outputs = audio_utilities.run_job(job, data_root=self.data, progress=lambda _event: None)

        self.assertEqual(len(outputs), 2)
        self.assertEqual(events, {"entered": 1, "active": 0, "max_active": 1, "outputs": 2})

    def test_gpu_safety_trip_does_not_publish_completed_audio_utility_output(self):
        staged = audio_utilities.stage_assets(self.data, "workspace-a", "stage-trip",
            [self.asset["asset_id"]], "demucs_stems")
        job = {"job_id": "safety-trip-stems", "request": {"workspace_id": "workspace-a",
            "operation": "demucs_stems", "settings": {"device": "cuda", "stems": 2},
            "inputs": staged, "staging_id": "stage-trip"}}

        cancellations = []
        trip = {}
        @contextmanager
        def tripped_guard(*, on_safety_trip, **_kwargs):
            trip["callback"] = on_safety_trip
            yield

        def fake_run(command, *_args, **_kwargs):
            if command[:2] == ["docker", "exec"] and command[3] == "mkdir":
                trip["callback"]("injected safety trip")
            if command[:2] == ["docker", "cp"] and "output/." in command[2]:
                destination = Path(command[3])
                destination.mkdir(parents=True, exist_ok=True)
                (destination / "vocals.wav").write_bytes(b"mock audio output")

        with patch.object(audio_utilities, "gpu_workload_guard", side_effect=tripped_guard), \
             patch.object(audio_utilities, "_run", side_effect=fake_run), \
             patch.object(audio_utilities, "_stop_owned_container_process",
                          side_effect=lambda container, work_root: cancellations.append((container, work_root))):
            with self.assertRaisesRegex(MediaJobError, "GPU safety trip stopped"):
                audio_utilities.run_job(job, data_root=self.data, progress=lambda _event: None)

        self.assertEqual(cancellations, [("story-audio-demucs", "/tmp/vibe-audio-safety-trip-stems-1")])
        listed = list_assets(self.data, "workspace-a", kind="audio")["assets"]
        self.assertEqual({row["asset_id"] for row in listed}, {self.asset["asset_id"]})

    def test_audio_safety_stop_targets_only_the_unique_container_work_root(self):
        with patch.object(audio_utilities.subprocess, "run", return_value=unittest.mock.Mock(returncode=0)) as run:
            audio_utilities._stop_owned_container_process("story-audio-demucs", "/tmp/vibe-audio-job-1")
        command = run.call_args.args[0]
        self.assertEqual(command[:4], ["docker", "exec", "story-audio-demucs", "python"])
        self.assertEqual(command[-1], "/tmp/vibe-audio-job-1")
        compile(command[5], "audio-safety-stop", "exec")


if __name__ == "__main__":
    unittest.main()
