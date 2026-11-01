from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from story_builder.services.assembly_renderer import AssemblyRenderError, render_manifest
from story_builder.services.media_library import asset_path, register_upload


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg is required")
class AssemblyRendererTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.root = self.base / "data"
        self.workspace = "render-test"

    def register_video(self, name: str, *, with_audio: bool = True,
                       size: str = "96x64", rate: int = 8):
        path = self.base / name
        audio = ["-f", "lavfi", "-i", "sine=frequency=440:duration=0.4"] if with_audio else ["-an"]
        command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
            f"testsrc2=duration=0.4:size={size}:rate={rate}", *audio, "-c:v", "libx264", "-pix_fmt", "yuv420p"]
        if with_audio:
            command += ["-c:a", "aac"]
        command.append(str(path))
        subprocess.run(command, check=True, capture_output=True, timeout=30)
        return register_upload(self.root, self.workspace, filename=name,
            content=path.read_bytes(), role="project_video")

    def register_audio(self):
        path = self.base / "music.wav"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
            "sine=frequency=220:duration=0.4", str(path)], check=True, capture_output=True, timeout=30)
        return register_upload(self.root, self.workspace, filename=path.name,
            content=path.read_bytes(), role="project_audio")

    def manifest(self, videos, *, audio_tracks=None, policy="preserve_and_mix"):
        clips = []
        for video in videos:
            clips.append({"outputs": [{"kind": "video", "asset_id": video["asset_id"],
                "sha256": video["sha256"], "duration_seconds": video["media"]["duration_seconds"],
                "has_audio": video["media"].get("has_audio") is True}]})
        return {"manifest_id": "export-test", "manifest": {"state": "ready_for_render",
            "clips": clips, "audio_tracks": audio_tracks or [], "export_settings": {
                "resolution": "720p", "frame_rate": 24, "quality": 24, "audio_policy": policy}}}

    def test_renders_ordered_clips_and_registers_optional_audio_policy_inputs(self):
        first, second = self.register_video("first.mp4"), self.register_video("second.mp4", with_audio=False)
        audio = self.register_audio()
        track = {"asset_id": audio["asset_id"], "sha256": audio["sha256"], "start_seconds": 0.1,
            "trim_start_seconds": 0.0, "trim_end_seconds": audio["media"]["duration_seconds"], "gain": 0.5}
        output = self.root / "assets" / self.workspace / "exports" / "final.mp4"
        progress = []
        result = render_manifest(self.root, self.workspace,
            self.manifest([first, second], audio_tracks=[track]), output, progress=progress.append)
        self.assertTrue(output.is_file())
        self.assertTrue(progress)
        self.assertEqual(progress[-1], 100)
        self.assertEqual(progress, sorted(progress))
        self.assertTrue(all(0 <= value <= 100 for value in progress))
        stream_types = {stream["codec_type"] for stream in result["probe"]["streams"]}
        self.assertEqual(stream_types, {"video", "audio"})
        self.assertGreater(result["size_bytes"], 0)

    def test_normalizes_mixed_source_dimensions_and_frame_rates(self):
        first = self.register_video("small-slow.mp4", size="96x64", rate=8)
        second = self.register_video("portrait-fast.mp4", with_audio=False, size="80x96", rate=12)
        output = self.root / "assets" / self.workspace / "exports" / "mixed-sources.mp4"

        result = render_manifest(self.root, self.workspace,
            self.manifest([first, second], policy="mute"), output)

        video = next(stream for stream in result["probe"]["streams"] if stream["codec_type"] == "video")
        self.assertEqual((video["width"], video["height"]), (1280, 720))
        self.assertEqual(video["r_frame_rate"], "24/1")
        self.assertEqual(video["avg_frame_rate"], "24/1")
        self.assertGreaterEqual(float(result["probe"]["format"]["duration"]), 0.75)
        self.assertLess(float(result["probe"]["format"]["duration"]), 1.0)
        self.assertFalse(any(stream["codec_type"] == "audio" for stream in result["probe"]["streams"]))

    def test_rejects_changed_source_and_path_escape_before_rendering(self):
        video = self.register_video("source.mp4")
        source, _, _ = asset_path(self.root, self.workspace, video["asset_id"])
        source.write_bytes(source.read_bytes() + b"changed")
        with self.assertRaisesRegex(AssemblyRenderError, "changed after"):
            render_manifest(self.root, self.workspace, self.manifest([video]),
                self.root / "assets" / self.workspace / "exports" / "out.mp4")

    def test_rejects_output_outside_workspace_exports(self):
        video = self.register_video("source.mp4")
        with self.assertRaisesRegex(AssemblyRenderError, "inside this workspace"):
            render_manifest(self.root, self.workspace, self.manifest([video]), self.base / "outside.mp4")

    def test_rejects_assets_root_symlink_escape(self):
        video = self.register_video("source.mp4")
        assets = self.root / "assets"
        outside = self.base / "outside-assets"
        outside.mkdir()
        assets.symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(AssemblyRenderError, "cannot contain symlinks"):
            render_manifest(self.root, self.workspace, self.manifest([video]),
                assets / self.workspace / "exports" / "out.mp4")


if __name__ == "__main__":
    unittest.main()
