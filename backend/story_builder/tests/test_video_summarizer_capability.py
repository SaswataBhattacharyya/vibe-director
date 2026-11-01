from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from story_builder.isolated_server import create_app
from story_builder.services.gpu_runtime import GPUAdmissionError
from story_builder.services.video_summarizer_capability import video_summarizer_capability


class VideoSummarizerCapabilityTests(unittest.TestCase):
    def test_readiness_is_read_only_and_distinguishes_missing_image_from_docker_access(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src/video_audio_analyzer").mkdir(parents=True)
            (root / "src/video_audio_analyzer/cli.py").touch()
            image_calls = []

            def runner(command, **_kwargs):
                image_calls.append(command[-1])
                if command[-1] == "video-audio-analyzer-peav:dev":
                    return SimpleNamespace(returncode=0, stdout="", stderr="")
                return SimpleNamespace(returncode=1, stdout="", stderr="No such image")

            with patch("story_builder.services.video_summarizer_capability.shutil.which", return_value="/usr/bin/docker"):
                result = video_summarizer_capability(analyzer_root=root, runner=runner)

            self.assertEqual(image_calls, ["video-audio-analyzer-peav:dev", "video-audio-analyzer-internvideo3:dev"])
            self.assertTrue(result["checked_without_starting_jobs"])
            self.assertFalse(result["can_analyze"])
            self.assertEqual(result["checks"]["container_images"]["items"]["analysis"]["state"], "ready")
            self.assertEqual(result["checks"]["container_images"]["items"]["video_summary"]["state"], "image_missing")
            self.assertEqual(result["checks"]["vibe_adapter"]["state"], "not_integrated")

    def test_analyze_is_enabled_only_when_all_dependencies_and_adapter_are_ready(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src/video_audio_analyzer").mkdir(parents=True)
            (root / "src/video_audio_analyzer/cli.py").touch()
            for relative in (
                "models/pe-av-base/config.json", "models/internvideo3-8b-instruct/model.safetensors.index.json",
                "models/panns/Cnn14_DecisionLevelMax_mAP=0.385.pth", "models/HTSAT_AudioSet_Saved_1.ckpt",
                "models/faster-whisper-large-v3/config.json", "models/spkrec-ecapa-voxceleb/config.json",
            ):
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.touch()
            ready = SimpleNamespace(returncode=0, stdout="", stderr="")
            with patch("story_builder.services.video_summarizer_capability.shutil.which", return_value="/usr/bin/docker"):
                result = video_summarizer_capability(analyzer_root=root, adapter_ready=True, runner=lambda *_a, **_k: ready)
            self.assertTrue(result["checks"]["analyzer_source"]["available"])
            self.assertTrue(result["can_analyze"])
            self.assertIn("local GPU", result["reason"])

    def test_api_exposes_capability_snapshot_without_starting_analysis(self):
        expected = {"can_analyze": False, "checked_without_starting_jobs": True, "checks": {}}
        with tempfile.TemporaryDirectory() as directory:
            app = create_app(data_root=Path(directory), video_summarizer_capability_provider=lambda: expected)
            captured = []
            environ = {"REQUEST_METHOD": "GET", "PATH_INFO": "/api/video-summariser/capabilities",
                "QUERY_STRING": "", "CONTENT_TYPE": "", "CONTENT_LENGTH": "0", "wsgi.input": io.BytesIO()}
            body = b"".join(app(environ, lambda status, headers: captured.extend([status, headers])))
            self.assertEqual(captured[0], "200 OK")
            self.assertIn(b'"can_analyze":false', body)
            self.assertIn(b'"checked_without_starting_jobs":true', body)

    def test_builtin_api_reports_adapter_integrated_even_when_launcher_readiness_is_separate(self):
        with tempfile.TemporaryDirectory() as directory:
            app = create_app(data_root=Path(directory))
            captured = []
            environ = {"REQUEST_METHOD": "GET", "PATH_INFO": "/api/video-summariser/capabilities",
                "QUERY_STRING": "", "CONTENT_TYPE": "", "CONTENT_LENGTH": "0", "wsgi.input": io.BytesIO()}
            with patch("story_builder.isolated_server.video_summarizer_capability",
                       return_value={"can_analyze": False, "checks": {"vibe_adapter": {"state": "ready"}}}) as capability:
                body = b"".join(app(environ, lambda status, headers: captured.extend([status, headers])))
            self.assertEqual(captured[0], "200 OK")
            self.assertIn(b'"state":"ready"', body)
            self.assertTrue(capability.call_args.kwargs["adapter_ready"])

    def test_capability_gpu_preflight_is_opt_in_read_only_and_reports_admission(self):
        expected = {"can_analyze": True, "checks": {}}
        with tempfile.TemporaryDirectory() as directory:
            app = create_app(data_root=Path(directory), video_summarizer_capability_provider=lambda: expected)

            def request(query):
                captured = []
                environ = {"REQUEST_METHOD": "GET", "PATH_INFO": "/api/video-summariser/capabilities",
                    "QUERY_STRING": query, "CONTENT_TYPE": "", "CONTENT_LENGTH": "0", "wsgi.input": io.BytesIO()}
                body = b"".join(app(environ, lambda status, headers: captured.extend([status, headers])))
                return captured[0], body

            host_memory = {"total_gib": 128.0, "available_gib": 101.0,
                "swap_total_gib": 16.0, "swap_free_gib": 16.0}
            with patch("story_builder.isolated_server.inspect_gpu_runtime",
                       return_value={"comfyui": {"free_gib": 22.5}, "recorded_at": "2026-10-12T12:00:00+00:00"}) as inspect, \
                 patch("story_builder.isolated_server.read_host_memory_diagnostic", return_value=host_memory):
                status, standard = request("")
                self.assertEqual(status, "200 OK")
                self.assertNotIn(b'"gpu_admission"', standard)
                inspect.assert_not_called()
                status, checked = request("check_gpu_admission=1")
                self.assertEqual(status, "200 OK")
                self.assertIn(b'"available":true', checked)
                self.assertIn(b'"free_gib":22.5', checked)
                self.assertIn(b'"available_gib":101.0', checked)
                self.assertIn(b'"required_gib":0.0', checked)
                self.assertEqual(inspect.call_count, 1)

            with patch("story_builder.isolated_server.inspect_gpu_runtime",
                       side_effect=GPUAdmissionError("GPU operating limit reached; submission withheld.")), \
                 patch("story_builder.isolated_server.read_host_memory_diagnostic", return_value=host_memory):
                status, blocked = request("check_gpu_admission=1")
                self.assertEqual(status, "200 OK")
                self.assertIn(b'"available":false', blocked)
                self.assertIn(b"operating limit reached", blocked)


if __name__ == "__main__":
    unittest.main()
