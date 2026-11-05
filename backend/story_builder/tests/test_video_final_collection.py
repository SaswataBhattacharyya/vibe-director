"""Real CPU media checks for chunk collection through final-only publication."""
import copy
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from story_builder.services import media_jobs, media_library, output_destinations
from story_builder.services.isolated_video_jobs import IsolatedVideoJobs, make_output_collector
from story_builder.services.ltx_chunks import plan_chunks
from story_builder.services.production_ledger import ProductionLedger
from story_builder.services.storage_paths import intermediate_root
from story_builder.services.t2v_pipeline import digest, probe
from story_builder.tests.test_isolated_video_jobs import request


class VideoOutputSelectionTests(unittest.TestCase):
    def test_output_only_filters_all_history_media_groups_without_changing_default(self):
        history = {"outputs": {"loader": {
            group: [{"filename": kind + ".mp4", "type": kind} for kind in ("input", "temp", "output")]
            + [{"filename": "legacy.mp4"}]
            for group in ("images", "gifs", "videos", "audio", "audios")}}}
        original = copy.deepcopy(history)
        with tempfile.TemporaryDirectory() as tmp, patch.object(media_jobs, "_download_output",
                side_effect=lambda url, dest, filename: dest / filename) as download:
            media_jobs.collect_outputs(history, destination_dir=Path(tmp), comfy_url="http://unused", output_only=True)
            self.assertEqual(download.call_count, 10)
            self.assertTrue(all(call.args[2] in {"output.mp4", "legacy.mp4"} for call in download.call_args_list))
            download.reset_mock()
            media_jobs.collect_outputs(history, destination_dir=Path(tmp), comfy_url="http://unused")
            self.assertEqual(download.call_count, 20)
        self.assertEqual(history, original)


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg required")
class VideoFinalCollectionTests(unittest.TestCase):
    def video(self, path, *, size, frames, color="red", audio=False):
        cmd = ["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "lavfi", "-i",
               f"color=c={color}:s={size}:r=24"]
        if audio:
            cmd += ["-f", "lavfi", "-i", "sine=frequency=440:sample_rate=32000", "-c:a", "aac"]
        cmd += ["-frames:v", str(frames), "-c:v", "libx264", "-threads", "2", "-pix_fmt", "yuv420p", str(path)]
        subprocess.run(cmd, capture_output=True, timeout=30, check=True)

    def test_three_chunks_publish_only_stitched_final_with_original_audio(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "data"
            root.mkdir()
            chosen = base / "output"
            chosen.mkdir()
            choice = {"mode": "folder", **output_destinations.grant(root, str(chosen))}
            output_destinations.preference(root, "video-generation", "tool-library", choice)
            ledger = ProductionLedger(root / "ledger.sqlite3")
            jobs = IsolatedVideoJobs(ledger, media_root=root)
            job = jobs.create_job(workspace_id="tool-library", clip_id="clip", idempotency_key="test",
                                  request=request(workflow_version=2, steps=4, resolution_preset=0.4))
            take = jobs._take_and_meta(job["job_id"])[0]
            original = intermediate_root(root, "tool-library", "originals") / job["job_id"] / "original.mp4"
            original.parent.mkdir(parents=True)
            self.video(original, size="160x96", frames=158, audio=True)
            plan = plan_chunks(original, 158)
            self.assertEqual(len(plan), 3)
            take["pipeline"] = dict(stage="ltx_refinement", original=dict(relative_path=original.relative_to(root).as_posix(),
                sha256=digest(original)), ltx_chunks=plan, ltx_chunk_outputs=[], ltx_chunk_index=0)
            collect = make_output_collector(data_root=root, ledger=ledger, comfy_url="http://unused")
            input_preview = base / "input.mp4"
            self.video(input_preview, size="160x96", frames=65)
            for index, window in enumerate(plan):
                enhanced = base / f"enhanced{index}.mp4"
                self.video(enhanced, size="864x480", frames=window["padded_frames"], color=("red", "green", "blue")[index])
                history = {"outputs": {
                    "5022": {"images": [{"filename": "input.mp4", "type": "input"}]},
                    "5014": {"images": [{"filename": enhanced.name, "type": "output"}]}}}
                def download(url, dest, filename):
                    self.assertNotIn("type=input", url)
                    shutil.copy2(base / filename, dest / filename)
                    return dest / filename
                with patch.object(media_jobs, "_download_output", side_effect=download):
                    outputs = collect(take, history)
                self.assertEqual(len(outputs), 1)
                if index < len(plan) - 1:
                    self.assertTrue(outputs[0]["pipeline_chunk"])
                    self.assertEqual(list(chosen.iterdir()), [])
                    with ledger._connect() as db:
                        self.assertEqual(db.execute("SELECT COUNT(*) FROM isolated_video_assets").fetchone()[0], 0)
                    take["pipeline"]["ltx_chunk_outputs"].append(outputs[0])
                    take["pipeline"]["ltx_chunk_index"] += 1
            final = outputs[0]
            self.assertNotIn("pipeline_chunk", final)
            path, _, _ = media_library.asset_path(root, "tool-library", final["shared_asset_id"])
            self.assertTrue(path.is_relative_to(chosen))
            self.assertEqual(list(chosen.rglob("*.mp4")), [path])
            result = probe(path)
            video = next(s for s in result["streams"] if s["codec_type"] == "video")
            audio = next(s for s in result["streams"] if s["codec_type"] == "audio")
            self.assertEqual((video["width"], video["height"], int(video["nb_read_frames"])), (864, 480, 144))
            self.assertEqual(audio["sample_rate"], "32000")
            self.assertAlmostEqual(float(video["duration"]), 6)
            self.assertAlmostEqual(final["duration_seconds"], 6, delta=1 / 24)
            self.assertTrue(original.is_file())
            self.assertEqual(len(media_library.list_assets(root, "tool-library", kind="video")["assets"]), 1)
