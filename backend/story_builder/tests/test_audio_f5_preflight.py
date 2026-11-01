from __future__ import annotations

import os
import io
import subprocess
import tempfile
import unittest
import json
import wave
from pathlib import Path
from unittest.mock import patch

from story_builder.isolated_server import create_app
from story_builder.services import audio_catalog
from story_builder.services import video_repertoire
from story_builder.services.media_library import register_upload


class F5DatasetPreparationPreflightTests(unittest.TestCase):
    @staticmethod
    def _call(app, method, path, payload=None):
        import io as io_module
        body = json.dumps(payload).encode() if payload is not None else b""
        response = []
        environ = {"REQUEST_METHOD": method, "PATH_INFO": path, "QUERY_STRING": "",
            "CONTENT_TYPE": "application/json", "CONTENT_LENGTH": str(len(body)), "wsgi.input": io_module.BytesIO(body)}
        content = b"".join(app(environ, lambda status, headers: response.extend([status, headers])))
        return response[0], json.loads(content) if content else None

    def test_ready_means_dataset_preparation_prerequisites_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "ComfyUI"
            suite = root / "custom_nodes" / "TTS-Audio-Suite"
            engine = suite / "engines" / "f5_tts"
            (engine / "model").mkdir(parents=True)
            (engine / "model" / "utils.py").write_text("", encoding="utf-8")
            (engine / "data" / "Emilia_ZH_EN_pinyin").mkdir(parents=True)
            (engine / "data" / "Emilia_ZH_EN_pinyin" / "vocab.txt").write_text("token\n", encoding="utf-8")
            checkpoint = root / "models" / "TTS" / "F5-TTS" / "F5TTS_v1_Base"
            checkpoint.mkdir(parents=True)
            (checkpoint / "model_1250000.safetensors").write_bytes(b"fixture")
            with patch.dict(os.environ, {"COMFYUI_ROOT": str(root), "TTS_AUDIO_SUITE_ROOT": str(suite),
                                         "AUDIO_TOOLS_PYTHON": os.sys.executable}), \
                 patch("story_builder.services.audio_catalog.shutil.which", return_value="/usr/bin/ffprobe"), \
                 patch("story_builder.services.audio_catalog.subprocess.run",
                       return_value=subprocess.CompletedProcess([], 0,
                           stdout='{"soundfile": true, "datasets": true}', stderr="")):
                result = audio_catalog.f5_dataset_preparation_preflight()
            self.assertTrue(result["preparation_ready"])
            self.assertFalse(result["training_enabled"])

    def test_missing_preparation_runtime_is_reported_without_enabling_training(self):
        with tempfile.TemporaryDirectory() as temporary:
            with patch.dict(os.environ, {"COMFYUI_ROOT": temporary,
                                         "TTS_AUDIO_SUITE_ROOT": str(Path(temporary) / "missing-suite"),
                                         "AUDIO_TOOLS_PYTHON": str(Path(temporary) / "missing-python")}), \
                 patch("story_builder.services.audio_catalog.shutil.which", return_value=None):
                result = audio_catalog.f5_dataset_preparation_preflight()
            self.assertFalse(result["preparation_ready"])
            self.assertFalse(result["training_enabled"])
            self.assertIn("python_dependencies", {row["name"] for row in result["checks"]})

    def test_workspace_independent_preflight_route_reports_readiness(self):
        with tempfile.TemporaryDirectory() as temporary:
            app = create_app(data_root=Path(temporary))
            response = []
            with patch("story_builder.isolated_server.audio_catalog.f5_dataset_preparation_preflight",
                       return_value={"preparation_ready": False, "training_enabled": False,
                                     "checks": [], "message": "requirements missing"}):
                body = b"".join(app({"REQUEST_METHOD": "GET", "PATH_INFO": "/api/audio/finetune/f5/preflight",
                                     "QUERY_STRING": ""},
                                    lambda status, headers: response.extend([status, headers])))
            self.assertEqual(response[0], "200 OK")
            self.assertIn(b"requirements missing", body)

    def test_preparation_job_uses_only_workspace_audio_and_is_workspace_scoped(self):
        with tempfile.TemporaryDirectory() as temporary:
            data = Path(temporary) / "data"
            wav = io.BytesIO()
            with wave.open(wav, "wb") as audio:
                audio.setnchannels(1); audio.setsampwidth(2); audio.setframerate(8000); audio.writeframes(b"\x00\x00" * 8)
            asset = register_upload(data, "workspace-a", filename="line.wav", content=wav.getvalue(), role="project_audio")
            comfy = Path(temporary) / "ComfyUI"
            checkpoint = comfy / "models" / "TTS" / "F5-TTS" / "F5TTS_v1_Base" / "model_1250000.safetensors"
            checkpoint.parent.mkdir(parents=True); checkpoint.touch()
            video_repertoire.configure_roots(data)
            self.addCleanup(lambda: video_repertoire.configure_roots(Path(temporary) / "reset"))
            app = create_app(data_root=data)
            request = {"dataset_name": "voice-test", "base_model": "F5TTS_v1_Base",
                "samples": [{"asset_id": asset["asset_id"], "text": "A sample line."}]}
            with patch("story_builder.isolated_server.audio_catalog.f5_dataset_preparation_preflight",
                       return_value={"preparation_ready": True, "message": "ready"}), \
                 patch("story_builder.isolated_server.audio_catalog.comfyui_root", return_value=comfy), \
                 patch("story_builder.isolated_server.video_repertoire.start_job",
                       side_effect=lambda kind, job_id: video_repertoire.read_job(kind, job_id)):
                status, accepted = self._call(app, "POST", "/api/audio/workspace-a/finetune/f5/jobs", request)
            self.assertEqual(status, "202 Accepted", accepted)
            saved = video_repertoire.read_job("f5-prepare", accepted["job_id"])
            self.assertEqual(saved["request"]["samples"][0]["filename"], "line.wav")
            status, _ = self._call(app, "GET", f"/api/audio/workspace-b/finetune/f5/jobs/{accepted['job_id']}")
            self.assertEqual(status, "404 Not Found")

    def test_preparation_rejects_foreign_workspace_asset_without_starting_worker(self):
        with tempfile.TemporaryDirectory() as temporary:
            data = Path(temporary) / "data"
            wav = io.BytesIO()
            with wave.open(wav, "wb") as audio:
                audio.setnchannels(1); audio.setsampwidth(2); audio.setframerate(8000); audio.writeframes(b"\x00\x00" * 8)
            foreign = register_upload(data, "workspace-b", filename="other.wav", content=wav.getvalue(), role="project_audio")
            comfy = Path(temporary) / "ComfyUI"
            checkpoint = comfy / "models" / "TTS" / "F5-TTS" / "F5TTS_v1_Base" / "model_1250000.safetensors"
            checkpoint.parent.mkdir(parents=True); checkpoint.touch()
            video_repertoire.configure_roots(data)
            self.addCleanup(lambda: video_repertoire.configure_roots(Path(temporary) / "reset"))
            app = create_app(data_root=data)
            with patch("story_builder.isolated_server.audio_catalog.f5_dataset_preparation_preflight",
                       return_value={"preparation_ready": True, "message": "ready"}), \
                 patch("story_builder.isolated_server.audio_catalog.comfyui_root", return_value=comfy), \
                 patch("story_builder.isolated_server.video_repertoire.start_job") as start:
                status, body = self._call(app, "POST", "/api/audio/workspace-a/finetune/f5/jobs", {
                    "dataset_name": "foreign-test", "base_model": "F5TTS_v1_Base",
                    "samples": [{"asset_id": foreign["asset_id"], "text": "Transcript"}]})
            self.assertEqual(status, "404 Not Found")
            self.assertIn("not found in this workspace", body["error"]["message"])
            start.assert_not_called()

    def test_f5_metadata_escapes_pipe_in_transcript(self):
        from story_builder.services.audio_finetune import build_metadata, read_metadata
        rows = [{"filename": "line.wav", "text": "left | right"}]
        self.assertEqual(read_metadata(build_metadata(rows))[0]["text"], "left | right")


if __name__ == "__main__":
    unittest.main()
