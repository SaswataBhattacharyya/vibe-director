"""Exercise the maintained launcher without Docker, providers or GPU work."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class VideoAnalyzerLauncherTests(unittest.TestCase):
    def test_uploaded_video_outside_model_staging_is_mounted_read_only(self):
        launcher = Path(__file__).resolve().parents[1] / "scripts/video_audio_analyzer/run_peav_worker.sh"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            analyzer = root / "model staging/video_audio_analyzer"
            analyzer.mkdir(parents=True)
            video = root / "uploaded media/clip with spaces.mp4"
            video.parent.mkdir()
            video.write_bytes(b"test input")
            binary = root / "bin"
            binary.mkdir()
            capture = root / "docker-args.json"
            docker = binary / "docker"
            docker.write_text("#!/usr/bin/env python3\nimport json, os, sys\nfrom pathlib import Path\nPath(os.environ['CAPTURE']).write_text(json.dumps(sys.argv[1:]))\n")
            docker.chmod(0o755)
            curl = binary / "curl"
            curl.write_text("#!/bin/sh\nexit 1\n")
            curl.chmod(0o755)
            repertoire = root / "vibe data/repertoire"
            environment = dict(os.environ, PATH=str(binary) + os.pathsep + os.environ["PATH"],
                CAPTURE=str(capture), VIBE_DIRECTOR_VIDEO_ANALYZER_ROOT=str(analyzer),
                VIDEO_REPERTOIRE_ROOT=str(repertoire), VIDEO_AUDIO_ANALYZER_INTERNVIDEO3_ENABLED="0",
                VIDEO_AUDIO_ANALYZER_CODEX_DIRECTOR="0")
            subprocess.run(["bash", str(launcher), str(video), "--no-detect-speech"],
                env=environment, check=True, capture_output=True, timeout=10)
            args = json.loads(capture.read_text())
            self.assertIn(str(video) + ":/app/input/clip with spaces.mp4:ro", args)
            self.assertIn(str(analyzer / "models") + ":/models:ro", args)
            self.assertIn(str(repertoire / "runs") + ":/app/runs", args)
            self.assertIn("vibe-director.analysis-job=manual-", next(value for value in args if value.startswith("vibe-director.analysis-job=")))
            self.assertEqual(args[args.index("--video") + 1], "/app/input/clip with spaces.mp4")
            self.assertIn("--no-detect-speech", args)
            self.assertEqual(video.read_bytes(), b"test input")

    def test_internvideo3_preflight_uses_vibe_job_label_without_docker(self):
        launcher = Path(__file__).resolve().parents[1] / "scripts/video_audio_analyzer/run_internvideo3_stage.sh"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            analyzer = root / "analyzer"
            model = analyzer / "models/internvideo3-8b-instruct"
            model.mkdir(parents=True)
            (model / "model.safetensors.index.json").write_text("{}")
            data = root / "vibe data"
            run = data / "video_repertoire/runs/run-a"
            run.mkdir(parents=True)
            manifest = run / "manifest.json"
            manifest.write_text("{}")
            video = root / "input.mp4"
            video.write_bytes(b"test input")
            binary = root / "bin"
            binary.mkdir()
            capture = root / "docker-args.json"
            docker = binary / "docker"
            docker.write_text(
                "#!/usr/bin/env python3\n"
                "import json, os, sys\n"
                "from pathlib import Path\n"
                "if sys.argv[1:3] == ['image', 'inspect']: sys.exit(0)\n"
                "Path(os.environ['CAPTURE']).write_text(json.dumps(sys.argv[1:]))\n"
            )
            docker.chmod(0o755)
            environment = dict(os.environ, PATH=str(binary) + os.pathsep + os.environ["PATH"],
                CAPTURE=str(capture), VIBE_DIRECTOR_VIDEO_ANALYZER_ROOT=str(analyzer),
                VIBE_DIRECTOR_DATA_DIR=str(data), VIDEO_AUDIO_ANALYZER_JOB_ID="analysis-456")
            subprocess.run(["bash", str(launcher), str(video), str(manifest), "--preflight"],
                env=environment, check=True, capture_output=True, timeout=10)
            args = json.loads(capture.read_text())
            self.assertIn("vibe-director.analysis-job=analysis-456", args)
            self.assertIn("--preflight-only", args)


if __name__ == "__main__":
    unittest.main()
