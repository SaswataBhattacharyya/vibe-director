import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class DonorVideoManifestRebaseTests(unittest.TestCase):
    def test_rebases_only_copied_manifests_with_staged_media(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            donor = base / "donor" / "video_repertoire"
            stage = base / "vibe" / "video_repertoire"
            (donor / "downloads").mkdir(parents=True)
            (stage / "downloads").mkdir(parents=True)
            (donor / "downloads" / "kept.mp4").write_bytes(b"donor")
            (stage / "downloads" / "kept.mp4").write_bytes(b"copied")
            source_manifest = donor / "manifests" / "video-one.json"
            source_manifest.parent.mkdir()
            original = {"asset_id": "video-one", "path": str(donor / "downloads" / "kept.mp4")}
            source_manifest.write_text(json.dumps(original), encoding="utf-8")
            (stage / "manifests").mkdir()
            copied = dict(original)
            (stage / "manifests" / "video-one.json").write_text(json.dumps(copied), encoding="utf-8")
            missing = {"asset_id": "video-two", "path": str(donor / "downloads" / "absent.mp4")}
            (stage / "manifests" / "video-two.json").write_text(json.dumps(missing), encoding="utf-8")
            outside = {"asset_id": "video-three", "path": str(base / "elsewhere.mp4")}
            (stage / "manifests" / "video-three.json").write_text(json.dumps(outside), encoding="utf-8")
            alternate = stage.parent / "youtube_code" / "out_videos" / "legacy.mp4"
            alternate.parent.mkdir(parents=True)
            alternate.write_bytes(b"same historical bytes")
            import hashlib
            fallback = {"asset_id": "video-four",
                "path": str(base / "donor" / "video_summariser" / "out_videos" / "legacy.mp4"),
                "sha256": hashlib.sha256(alternate.read_bytes()).hexdigest()}
            (stage / "manifests" / "video-four.json").write_text(json.dumps(fallback), encoding="utf-8")
            mismatched = {"asset_id": "video-five",
                "path": str(base / "donor" / "video_summariser" / "out_videos" / "different.mp4"),
                "sha256": hashlib.sha256(b"original bytes").hexdigest()}
            different = alternate.parent / "different.mp4"
            different.write_bytes(b"substituted bytes")
            (stage / "manifests" / "video-five.json").write_text(json.dumps(mismatched), encoding="utf-8")

            script = Path(__file__).resolve().parents[3] / "tools" / "rebase_donor_video_manifests.py"
            result = subprocess.run([sys.executable, str(script), "--stage-root", str(stage),
                "--donor-root", str(donor)], capture_output=True, text=True, check=True)

            self.assertIn("Rebased 2 copied video manifests; 2 staged media files were missing.", result.stdout)
            self.assertEqual(json.loads(source_manifest.read_text()), original)
            self.assertEqual(json.loads((stage / "manifests" / "video-one.json").read_text())["path"],
                str((stage / "downloads" / "kept.mp4").resolve()))
            self.assertEqual(json.loads((stage / "manifests" / "video-three.json").read_text())["path"], outside["path"])
            self.assertEqual(json.loads((stage / "manifests" / "video-four.json").read_text())["path"], str(alternate.resolve()))
            self.assertEqual(json.loads((stage / "manifests" / "video-five.json").read_text())["path"], mismatched["path"])

    def test_split_catalogue_and_download_roots(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            donor = base / "donor/video_repertoire"
            donor.mkdir(parents=True)
            stage = base / "local_data/library/catalog/donor-video"
            manifests = stage / "manifests"
            manifests.mkdir(parents=True)
            downloads = base / "local_data/library/downloads/youtube"
            downloads.mkdir(parents=True)
            clip = downloads / "clip.mp4"
            clip.write_bytes(b"copied video")
            manifest = manifests / "video-one.json"
            manifest.write_text(json.dumps({"path": str(donor / "downloads/clip.mp4")}))
            script = Path(__file__).resolve().parents[3] / "tools/rebase_donor_video_manifests.py"
            subprocess.run([sys.executable, str(script), "--stage-root", str(stage),
                "--donor-root", str(donor), "--downloads-root", str(downloads),
                "--youtube-root", str(base / "local_data/engines/youtube-import")], check=True, capture_output=True)
            self.assertEqual(json.loads(manifest.read_text())["path"], str(clip))


if __name__ == "__main__":
    unittest.main()
