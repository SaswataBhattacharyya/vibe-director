from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from story_builder.services.media_library import asset_path, list_assets, register_upload
from story_builder.services.video_summarizer_results import publish_analyzer_outputs
from story_builder.services.video_repertoire_worker import _publication_rows


class VideoSummarizerResultTests(unittest.TestCase):
    def test_projection_selects_only_existing_run_local_clips_frames_and_audio(self):
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory) / "run-a"
            for relative in ("embeddings/scene-1.mp4", "frames/frame-1.jpg", "audio/voice.wav"):
                path = run_dir / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"x")
            manifest = {"run_id": "run-a", "summary": "A person enters a rainy room.",
                "scenes": [{"scene_id": "scene-1", "start_time_sec": 1, "end_time_sec": 3,
                    "summary": "Person enters", "subjects": ["person"], "frames": [
                        {"frame_id": "f1", "path": "/app/runs/run-a/frames/frame-1.jpg", "timestamp_sec": 2,
                         "evidence": {"subjects": ["person"]}},
                        {"frame_id": "f2", "path": "/etc/passwd", "timestamp_sec": 2.5}]}],
                "media_collection": {"assets": [{"asset_id": "voice-a", "relative_path": "audio/voice.wav",
                    "category": "voice", "description": "Speaker sample", "tags": ["dialogue"]},
                    {"asset_id": "bad", "relative_path": "../../outside.wav", "category": "music"}]}}
            rows = _publication_rows(manifest, run_dir)
            self.assertEqual([row["kind"] for row in rows], ["video", "image", "audio"])
            self.assertEqual(rows[1]["relative_path"], "frames/frame-1.jpg")
            self.assertEqual(rows[1]["timestamp_seconds"], 2)
            self.assertEqual(rows[2]["audio_category"], "voice")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "data"
        self.run = self.root / "video_repertoire/runs/run"
        self.run.mkdir(parents=True)

    @staticmethod
    def png():
        import binascii
        import struct
        import zlib
        def chunk(name, data):
            body = name + data
            return struct.pack(">I", len(data)) + body + struct.pack(">I", binascii.crc32(body) & 0xffffffff)
        row = b"\0" + bytes((255, 0, 0)) * 2
        return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 2, 3, 8, 2, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(row * 3)) + chunk(b"IEND", b""))

    def test_publishes_timestamped_image_occurrence_and_replay_is_idempotent(self):
        source = register_upload(self.root, "workspace-a", filename="source.mp4",
            content=self.mp4_bytes(), role="project_video")
        frame = self.run / "frames" / "frame.jpg"
        frame.parent.mkdir()
        frame.write_bytes(b"\xff\xd8\xffsample-frame")
        outputs = [{"relative_path": "frames/frame.jpg", "kind": "image",
            "occurrence_id": "scene_001_frame_003", "timestamp_seconds": 4.25,
            "description": "Courtroom wide shot", "tags": ["courtroom", "wide"]}]
        with patch("story_builder.services.media_library._probe", return_value={"width": 2, "height": 3}):
            first = publish_analyzer_outputs(self.root, "workspace-a", source_asset_id=source["asset_id"],
                source_sha256=source["sha256"], derivation_id="analysis_job_1", run_dir=self.run, outputs=outputs)
            replay = publish_analyzer_outputs(self.root, "workspace-a", source_asset_id=source["asset_id"],
                source_sha256=source["sha256"], derivation_id="analysis_job_1", run_dir=self.run, outputs=outputs)
        self.assertEqual(first[0]["asset_id"], replay[0]["asset_id"])
        self.assertFalse(first[0]["deduplicated"])
        self.assertTrue(replay[0]["deduplicated"])
        self.assertEqual(first[0]["metadata"]["timestamp_seconds"], 4.25)
        self.assertEqual(first[0]["description"], "Courtroom wide shot")
        self.assertEqual(first[0]["tags"], ["courtroom", "wide"])
        copied, _, _ = asset_path(self.root, "workspace-a", first[0]["asset_id"])
        self.assertEqual(copied.read_bytes(), frame.read_bytes())
        self.assertEqual(list_assets(self.root, "workspace-a", kind="image")["total"], 1)

    def test_rejects_paths_that_escape_or_symlink_out_of_analyzer_run(self):
        source = register_upload(self.root, "workspace-a", filename="source.mp4",
            content=self.mp4_bytes(), role="project_video")
        outside = Path(self.temp.name) / "outside.jpg"
        outside.write_bytes(b"\xff\xd8\xffoutside")
        (self.run / "linked.jpg").symlink_to(outside)
        common = {"source_asset_id": source["asset_id"], "source_sha256": source["sha256"],
            "derivation_id": "analysis_job_1", "run_dir": self.run}
        with self.assertRaisesRegex(ValueError, "must remain inside its run"):
            publish_analyzer_outputs(self.root, "workspace-a", outputs=[{"relative_path": "../outside.jpg",
                "kind": "image", "occurrence_id": "frame_1"}], **common)
        with self.assertRaisesRegex(ValueError, "missing or outside its run"):
            publish_analyzer_outputs(self.root, "workspace-a", outputs=[{"relative_path": "linked.jpg",
                "kind": "image", "occurrence_id": "frame_1"}], **common)

    def test_rejects_invalid_workspace_and_unrecognized_media_suffix(self):
        source = register_upload(self.root, "workspace-a", filename="source.mp4",
            content=self.mp4_bytes(), role="project_video")
        (self.run / "frame.bin").write_bytes(b"data")
        common = {"source_asset_id": source["asset_id"], "source_sha256": source["sha256"],
            "derivation_id": "analysis_job_1", "run_dir": self.run}
        with self.assertRaisesRegex(ValueError, "workspace ID is invalid"):
            publish_analyzer_outputs(self.root, "../outside", outputs=[], **common)
        with self.assertRaisesRegex(ValueError, "missing or outside its run"):
            publish_analyzer_outputs(self.root, "workspace-a", outputs=[{"relative_path": "frame.bin",
                "kind": "image", "occurrence_id": "frame_1"}], **common)

    def mp4_bytes(self):
        path = Path(self.temp.name) / "source.mp4"
        import subprocess
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
            "color=c=black:s=32x32:d=0.1", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)],
            check=True, capture_output=True, timeout=30)
        return path.read_bytes()


if __name__ == "__main__":
    unittest.main()
