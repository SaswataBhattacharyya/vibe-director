import hashlib
import json
import tempfile
from pathlib import Path
from unittest import TestCase

from story_builder.services.isolated_video_contract import EXPECTED_GRAPH_SHA256
from story_builder.services.production_t2v_capability import (
    feature_enabled, record_successful_t2v_smoke,
)


class T2VFeatureFlagTests(TestCase):
    def test_product_flag_enables_t2v(self):
        self.assertTrue(feature_enabled({"VIBE_DIRECTOR_ENABLE_T2V": "true"}))

    def test_product_flag_takes_precedence_over_legacy_flag(self):
        self.assertFalse(feature_enabled({
            "VIBE_DIRECTOR_ENABLE_T2V": "0",
            "STORY_BUILDER_ENABLE_H3_T2V": "1",
        }))

    def test_legacy_flag_remains_a_fallback_during_migration(self):
        self.assertTrue(feature_enabled({"STORY_BUILDER_ENABLE_H3_T2V": "1"}))

    def test_missing_flags_fail_closed(self):
        self.assertFalse(feature_enabled({}))


class T2VSmokeEvidenceTests(TestCase):
    def test_records_only_intact_video_with_audio_and_exact_graph(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            video = root / "assets" / "clip.mp4"
            video.parent.mkdir()
            video.write_bytes(b"synthetic playable video")
            output = {
                "relative_path": "assets/clip.mp4",
                "sha256": hashlib.sha256(video.read_bytes()).hexdigest(),
                "has_video": True,
                "has_audio": True,
                "probe": {"streams": [{"codec_type": "video"}, {"codec_type": "audio"}]},
            }
            manifest = root / ".smoke.json"

            self.assertTrue(record_successful_t2v_smoke(data_root=root,
                workflow_sha256=EXPECTED_GRAPH_SHA256, job_id="job_123",
                output=output, manifest_path=manifest))
            saved = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(saved["workflow_sha256"], EXPECTED_GRAPH_SHA256)
            self.assertEqual(saved["outputs"][0]["sha256"], output["sha256"])

            self.assertFalse(record_successful_t2v_smoke(data_root=root,
                workflow_sha256="0" * 64, job_id="job_124", output=output,
                manifest_path=manifest))
            self.assertFalse(record_successful_t2v_smoke(data_root=root,
                workflow_sha256=EXPECTED_GRAPH_SHA256, job_id="job_125",
                output={**output, "relative_path": "../outside.mp4"},
                manifest_path=manifest))

    def test_rejects_missing_audio_and_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            video = root / "clip.mp4"
            video.write_bytes(b"video")
            output = {"relative_path": "clip.mp4", "sha256": "0" * 64,
                "has_video": True, "has_audio": False,
                "probe": {"streams": [{"codec_type": "video"}]}}
            self.assertFalse(record_successful_t2v_smoke(data_root=root,
                workflow_sha256=EXPECTED_GRAPH_SHA256, job_id="job_126",
                output=output, manifest_path=root / ".smoke.json"))
