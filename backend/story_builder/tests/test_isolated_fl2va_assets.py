from __future__ import annotations

import hashlib
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from story_builder.services import media_library
from story_builder.services.isolated_fl2va_assets import (
    FL2VAStagingError, cleanup_fl2va_staging_job, stage_fl2va_frames,
)

PNG = b"\x89PNG\r\n\x1a\n" + b"fixture-image-bytes"


class IsolatedFL2VAAssetStagingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.workspace = "stage-test"
        self.input_root = self.root / "ComfyUI" / "input"
        self.input_root.mkdir(parents=True)
        with patch.object(media_library, "_probe", return_value={"width": 1, "height": 1}):
            self.first = media_library.register_upload(self.root / "library", self.workspace,
                filename="first.png", content=PNG, role="first_frame")
            self.last = media_library.register_upload(self.root / "library", self.workspace,
                filename="last.png", content=PNG + b"last", role="last_frame")
        self.first_ref = {"asset_id": self.first["asset_id"], "sha256": self.first["sha256"]}
        self.last_ref = {"asset_id": self.last["asset_id"], "sha256": self.last["sha256"]}

    def tearDown(self):
        self.temp.cleanup()

    def stage(self, job_id="job-a", *, first=None, last=None, input_root=None):
        return stage_fl2va_frames(media_root=self.root / "library", workspace_id=self.workspace,
            job_id=job_id, first_frame=first or self.first_ref, last_frame=last or self.last_ref,
            comfy_input_root=input_root or self.input_root)

    def test_unique_job_directories_and_cleanup_remove_only_owned_files(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(self.stage, job_id) for job_id in ("job-a", "job-b")]
            results = [future.result() for future in futures]
        first_files = self.input_root / results[0][0]["first_frame"]
        other_files = self.input_root / results[1][0]["first_frame"]
        self.assertNotEqual(first_files, other_files)
        self.assertEqual(first_files.read_bytes(), PNG)
        self.assertEqual(other_files.read_bytes(), PNG)
        first_dir = first_files.parent
        unrelated = first_dir.parent / "keep.txt"
        unrelated.write_text("keep")
        results[0][1]()
        results[0][1]()
        self.assertFalse(first_dir.exists())
        self.assertTrue(unrelated.exists())
        self.assertTrue(other_files.exists())
        results[1][1]()

    def test_hash_mismatch_wrong_kind_and_missing_input_root_reject(self):
        with self.assertRaisesRegex(FL2VAStagingError, "frozen request hash"):
            self.stage(first={"asset_id": self.first_ref["asset_id"], "sha256": "0" * 64})
        with patch.object(media_library, "_probe", return_value={"duration_seconds": 1, "streams": ["audio"]}):
            audio = media_library.register_upload(self.root / "library", self.workspace,
                filename="audio.wav", content=b"RIFF\x00\x00\x00\x00WAVEdata", role="project_audio")
        with self.assertRaisesRegex(FL2VAStagingError, "not a supported image"):
            self.stage(last={"asset_id": audio["asset_id"], "sha256": audio["sha256"]})
        with self.assertRaisesRegex(FL2VAStagingError, "input root is missing"):
            self.stage(input_root=self.root / "absent")

    def test_asset_and_input_symlinks_and_path_tricks_reject(self):
        source, _, _ = media_library.asset_path(self.root / "library", self.workspace, self.first_ref["asset_id"])
        source.unlink()
        outside = self.root / "outside.png"
        outside.write_bytes(PNG)
        source.symlink_to(outside)
        with self.assertRaises(FL2VAStagingError):
            self.stage()
        link_root = self.root / "comfy-link"
        link_root.symlink_to(self.input_root, target_is_directory=True)
        with self.assertRaisesRegex(FL2VAStagingError, "symlink"):
            self.stage(input_root=link_root)
        with self.assertRaisesRegex(FL2VAStagingError, "job ID"):
            self.stage("../escape")

    def test_staged_copy_hashes_match_the_frozen_records(self):
        staged, cleanup = self.stage()
        for slot, reference in (("first_frame", self.first_ref), ("last_frame", self.last_ref)):
            data = (self.input_root / staged[slot]).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), reference["sha256"])
        cleanup()

    def test_restart_cleanup_is_job_confined_and_missing_root_is_idempotent(self):
        staged, _cleanup = self.stage("restart-job")
        target = self.input_root / staged["first_frame"]
        self.assertTrue(target.is_file())
        cleanup_fl2va_staging_job(self.input_root, "restart-job")
        cleanup_fl2va_staging_job(self.input_root, "restart-job")
        self.assertFalse(target.exists())
        cleanup_fl2va_staging_job(self.root / "missing-input", "restart-job")
        keep = self.input_root / "unrelated.txt"
        keep.write_text("keep")
        cleanup_fl2va_staging_job(self.input_root, "other-job")
        self.assertTrue(keep.exists())


if __name__ == "__main__":
    unittest.main()
