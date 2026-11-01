from __future__ import annotations

import io
import json
import subprocess
import tempfile
import unittest
import wave
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import patch

from story_builder.isolated_server import create_app
from story_builder.services import control_foley, media_jobs, music_sound, video_repertoire
from story_builder.services.media_library import asset_path, register_upload
from story_builder.services.video_repertoire_worker import _publish_audio_job


class MusicSoundIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.data = self.base / "data"
        self.analyzer = self.base / "donor" / "video_audio_analyzer"
        self.analyzer.mkdir(parents=True)
        self.video_file = self.base / "reference.mp4"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
            "-i", "color=c=black:s=32x32:d=0.2", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            str(self.video_file)], check=True, capture_output=True, timeout=30)
        self.video = register_upload(self.data, "workspace-a", filename="reference.mp4",
            content=self.video_file.read_bytes(), role="project_video")
        wav = io.BytesIO()
        with wave.open(wav, "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(8000)
            audio.writeframes(b"\0\0" * 800)
        self.audio_bytes = wav.getvalue()
        self.audio = register_upload(self.data, "workspace-a", filename="reference.wav",
            content=self.audio_bytes, role="project_audio")
        video_repertoire.configure_roots(self.data, self.analyzer)

    def tearDown(self):
        video_repertoire.configure_roots(Path(self.temp.name) / "reset")

    @staticmethod
    def call(app, method, path, payload=None, query=""):
        body = json.dumps(payload or {}).encode() if payload is not None else b""
        response = []
        environ = {"REQUEST_METHOD": method, "PATH_INFO": path, "QUERY_STRING": query,
            "CONTENT_TYPE": "application/json", "CONTENT_LENGTH": str(len(body)), "wsgi.input": io.BytesIO(body)}
        content = b"".join(app(environ, lambda status, headers: response.extend([status, headers])))
        return response[0], json.loads(content) if content else None

    def test_control_foley_accepts_workspace_media_and_rejects_wrong_media_kinds(self):
        app = create_app(data_root=self.data)
        path = "/api/audio/workspace-a/control-foley/jobs"
        status, guidance = self.call(app, "GET", "/api/workflow-guidance",
            query="workflow_id=control_foley_reference_video_audio_v1&model_id=control_foley")
        self.assertEqual(status, "200 OK")
        prompt_ref = {key: guidance[key] for key in ("knowledge_id", "guidance_version", "workflow_sha256")}
        payload = {"settings": {"mode": "reference_video_audio", "duration": 3},
            "references": {"video_asset_id": self.video["asset_id"], "audio_asset_id": self.audio["asset_id"]},
            "prompt_knowledge_ref": prompt_ref}
        with patch("story_builder.services.control_foley.capabilities", return_value={"status": "available"}), \
             patch("story_builder.services.video_repertoire.start_job",
                   side_effect=lambda kind, job_id: video_repertoire.read_job(kind, job_id)):
            status, job = self.call(app, "POST", path, payload)
        self.assertEqual(status, "202 Accepted", job)
        persisted = video_repertoire.read_job("control-foley", job["job_id"])
        self.assertEqual(persisted["request"]["references"], payload["references"])
        self.assertEqual(persisted["request"]["prompt_knowledge_ref"], prompt_ref)
        self.assertEqual(asset_path(self.data, "workspace-a", self.video["asset_id"])[1], "video/mp4")
        self.assertTrue(asset_path(self.data, "workspace-a", self.audio["asset_id"])[1].startswith("audio/"))

        wrong_video = {**payload, "references": {"video_asset_id": self.audio["asset_id"],
            "audio_asset_id": self.audio["asset_id"]}}
        with patch("story_builder.services.control_foley.capabilities", return_value={"status": "available"}):
            status, error = self.call(app, "POST", path, wrong_video)
        self.assertEqual(status, "400 Bad Request")
        self.assertIn("video", error["error"]["message"].lower())
        wrong_audio = {**payload, "references": {"video_asset_id": self.video["asset_id"],
            "audio_asset_id": self.video["asset_id"]}}
        with patch("story_builder.services.control_foley.capabilities", return_value={"status": "available"}):
            status, error = self.call(app, "POST", path, wrong_audio)
        self.assertEqual(status, "400 Bad Request")
        self.assertIn("audio", error["error"]["message"].lower())

        stale = {**payload, "prompt_knowledge_ref": {**prompt_ref, "guidance_version": prompt_ref["guidance_version"] + 1}}
        with patch("story_builder.services.control_foley.capabilities", return_value={"status": "available"}), \
             patch("story_builder.services.video_repertoire.start_job") as start_job:
            status, error = self.call(app, "POST", path, stale)
        self.assertEqual(status, "409 Conflict")
        self.assertIn("guidance changed", error["error"]["message"])
        start_job.assert_not_called()

    def test_music_settings_validate_without_submitting_a_workflow(self):
        job = music_sound.new_music_job({"mode": "instrumental", "tags": "warm piano", "duration": 12})
        self.assertEqual(job["settings"]["tags"], "warm piano")
        with self.assertRaisesRegex(music_sound.MusicSoundError, "tags"):
            music_sound.new_music_job({"mode": "instrumental", "tags": "  "})
        with self.assertRaisesRegex(music_sound.MusicSoundError, "lyrics"):
            music_sound.new_music_job({"mode": "song", "tags": "pop", "lyrics": ""})
        with self.assertRaisesRegex(music_sound.MusicSoundError, "4000 characters"):
            music_sound.new_music_job({"mode": "instrumental", "tags": "x" * 4001})
        with self.assertRaisesRegex(music_sound.MusicSoundError, "10000 characters"):
            music_sound.new_music_job({"mode": "song", "tags": "pop", "lyrics": "x" * 10001})

    def test_control_foley_text_limits_match_the_music_sound_form(self):
        with self.assertRaisesRegex(control_foley.ControlFoleyError, "4000 characters"):
            control_foley.new_job({"mode": "text_audio", "prompt": "x" * 4001})
        with self.assertRaisesRegex(control_foley.ControlFoleyError, "Negative prompt"):
            control_foley.new_job({"mode": "text_audio", "prompt": "wind", "negative_prompt": "x" * 4001})

    def test_legacy_ace_endpoint_requires_standalone_confirmation(self):
        app = create_app(data_root=self.data)
        with patch("story_builder.services.video_repertoire.start_job") as start_job:
            status, result = self.call(app, "POST", "/api/audio/workspace-a/music/jobs",
                {"settings": {"tags": "warm piano"}})
        self.assertEqual(status, "409 Conflict", result)
        self.assertIn("standalone", result["error"]["message"].lower())
        start_job.assert_not_called()

    def test_control_foley_stages_reference_inputs_and_compiles_copied_graph(self):
        job = control_foley.new_job({"mode": "reference_video_audio", "duration": 3})
        comfy_input = self.base / "ComfyUI" / "input"
        control_foley.stage_inputs(project_dir=self.data / "projects" / "workspace-a" / "media" / "generated",
            comfy_input_dir=comfy_input, job=job,
            video=("reference.mp4", self.video_file.read_bytes()),
            reference_audio=("reference.wav", self.audio_bytes))
        workflow = control_foley.build_workflow(job)
        self.assertEqual(workflow["2"]["inputs"]["video_path"], job["inputs"]["video"])
        generator = workflow["3"]["inputs"]
        self.assertEqual(generator["reference_audio_path"], job["inputs"]["reference_audio"])
        self.assertTrue((comfy_input / job["inputs"]["video"]).is_file())
        self.assertTrue((comfy_input / job["inputs"]["reference_audio"]).is_file())
        self.assertEqual(len(control_foley.WORKFLOWS), 3)
        self.assertTrue(all(path.is_file() for path in control_foley.WORKFLOWS.values()))

    def test_worker_reuses_control_foley_and_publishes_to_shared_audio_library(self):
        job = video_repertoire.create_job("control-foley", {"workspace_id": "workspace-a",
            "settings": {"mode": "reference_video_audio", "duration": 3},
            "references": {"video_asset_id": self.video["asset_id"], "audio_asset_id": self.audio["asset_id"]},
            "prompt_knowledge_ref": {"knowledge_id": "audio-guidance-v1", "guidance_version": 1,
                "workflow_sha256": "a" * 64}})
        comfy_root = self.base / "ComfyUI"

        def render(job, *, project_dir, output_root, comfy_url, progress):
            # The real ComfyUI runner nests submit_and_wait's lease inside the
            # worker's GPU guard. Keep this integration test on the real lock.
            with media_jobs.comfy_submission_guard():
                output = project_dir / "audio" / "test.wav"
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(self.audio_bytes)
                job.update(status="completed", prompt_id="prompt-test", export_path=str(output))
                progress(job)
            return job

        with patch.dict("os.environ", {"VIBE_DIRECTOR_DATA_DIR": str(self.data),
                "COMFYUI_ROOT": str(comfy_root),
                "VIBE_DIRECTOR_GPU_WORKLOAD_LOCK": str(self.base / "gpu-workload.lock")}), \
             patch("story_builder.services.media_jobs.wait_for_comfyui_idle"), \
             patch("story_builder.services.media_jobs.inspect_gpu_runtime", return_value={}), \
             patch("story_builder.services.media_jobs.record_gpu_telemetry"), \
             patch("story_builder.services.video_repertoire_worker.event"), \
             patch("story_builder.services.video_repertoire_worker.save_job"), \
             patch("story_builder.services.control_foley.run_job", side_effect=render):
            result = _publish_audio_job(job["job_id"], job["request"], "control-foley")

        self.assertEqual(result["asset"]["kind"], "audio")
        self.assertTrue((comfy_root / "input" / "story_builder_control_foley" / job["job_id"] / "video.mp4").is_file())
        self.assertTrue((comfy_root / "input" / "story_builder_control_foley" / job["job_id"] / "reference_audio.wav").is_file())
        self.assertEqual(result["asset"]["metadata"]["workflow_id"], "control-foley")
        self.assertEqual(result["asset"]["metadata"]["prompt_knowledge_ref"], job["request"]["prompt_knowledge_ref"])


if __name__ == "__main__":
    unittest.main()
