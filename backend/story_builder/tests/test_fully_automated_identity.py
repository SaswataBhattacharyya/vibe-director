import hashlib
import json
import sqlite3
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from story_builder.services.fully_automated_identity import (
    IdentityReviewProcessor, IdentityReviewStore, analyze_identity_frames, sample_identity_frames,
    validate_identity_observations, enqueue_completed_full_run_identity_reviews,
    _consensus_identity_candidates,
)


class FullyAutomatedIdentityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.video = self.root / "clip.mp4"
        self.video.write_bytes(b"synthetic video bytes")
        self.digest = hashlib.sha256(self.video.read_bytes()).hexdigest()

    def test_samples_are_deterministic_bounded_and_source_bound(self):
        def ffmpeg(command, **kwargs):
            Path(command[-1]).write_bytes(b"jpeg")

        with patch("story_builder.services.fully_automated_identity.subprocess.run", side_effect=ffmpeg) as run:
            frames = sample_identity_frames(self.video, self.root / "frames", expected_sha256=self.digest,
                                            duration_seconds=12, sample_count=3)
        self.assertEqual([frame["timestamp_seconds"] for frame in frames], [3, 6, 9])
        self.assertTrue(all(frame["source_sha256"] == self.digest and Path(frame["path"]).is_file() for frame in frames))
        self.assertTrue(all(frame["sample_sha256"] == hashlib.sha256(Path(frame["path"]).read_bytes()).hexdigest() for frame in frames))
        self.assertEqual(run.call_count, 3)

    def test_rejects_changed_clip_and_unbounded_sampling(self):
        self.video.write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "changed since"):
            sample_identity_frames(self.video, self.root / "frames", expected_sha256=self.digest, duration_seconds=5)
        with self.assertRaisesRegex(ValueError, "one and six"):
            sample_identity_frames(self.video, self.root / "frames", expected_sha256=hashlib.sha256(b"changed").hexdigest(),
                                   duration_seconds=5, sample_count=7)

    def test_cleans_partial_samples_on_ffmpeg_failure(self):
        calls = 0
        def ffmpeg(command, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                Path(command[-1]).write_bytes(b"jpeg")
            else:
                raise RuntimeError("decode failed")

        with patch("story_builder.services.fully_automated_identity.subprocess.run", side_effect=ffmpeg):
            with self.assertRaisesRegex(RuntimeError, "decode failed"):
                sample_identity_frames(self.video, self.root / "frames", expected_sha256=self.digest,
                                       duration_seconds=12, sample_count=2)
        self.assertEqual(list((self.root / "frames").glob("*.jpg")), [])

    def test_failed_retry_preserves_samples_from_an_earlier_attempt(self):
        frames_dir = self.root / "frames"
        frames_dir.mkdir()
        existing = frames_dir / f"{self.digest[:16]}-1-4.000.jpg"
        existing.write_bytes(b"previous successful sample")
        with patch("story_builder.services.fully_automated_identity.subprocess.run",
                   side_effect=RuntimeError("decode failed")):
            with self.assertRaisesRegex(RuntimeError, "decode failed"):
                sample_identity_frames(self.video, frames_dir, expected_sha256=self.digest,
                                       duration_seconds=12, sample_count=2)
        self.assertEqual(existing.read_bytes(), b"previous successful sample")
        self.assertEqual(list(frames_dir.glob("*.jpg")), [existing])

    @unittest.skipUnless(shutil.which("ffmpeg"), "FFmpeg is not installed")
    def test_samples_a_synthetic_clip_with_real_ffmpeg(self):
        video = self.root / "synthetic.mp4"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
                        "-i", "color=c=blue:s=320x240:d=4", "-c:v", "mpeg4", str(video)],
                       check=True, capture_output=True, timeout=30)
        digest = hashlib.sha256(video.read_bytes()).hexdigest()
        frames = sample_identity_frames(video, self.root / "real-frames", expected_sha256=digest,
                                        duration_seconds=4, sample_count=1)
        self.assertEqual(frames[0]["timestamp_seconds"], 2)
        self.assertGreater(Path(frames[0]["path"]).stat().st_size, 0)

    def test_vision_review_is_bound_to_sample_hashes_and_canonical_reference_order(self):
        frame = self.root / "sample.jpg"
        portrait = self.root / "character.png"
        frame.write_bytes(b"sample-frame")
        portrait.write_bytes(b"character-reference")
        sample = {"path": str(frame), "timestamp_seconds": 2.5,
            "source_sha256": "a" * 64, "sample_sha256": hashlib.sha256(frame.read_bytes()).hexdigest(),
            "sample_index": 1}
        calls = []

        def provider(**kwargs):
            calls.append(kwargs)
            return {"frames": [{"sample_index": 1, "timestamp_seconds": 2.5,
                "observations": [{"status": "candidate_match", "character_id": "char-1",
                    "visual_evidence": "The same distinctive scar is visible.",
                    "visible_people": 1, "face_clear": True,
                    "bbox": [0.2, 0.1, 0.8, 0.95]}]}]}

        result = analyze_identity_frames(samples=[sample], characters=[{"character_id": "char-1",
            "name": "Mira", "reference_path": str(portrait),
            "reference_sha256": hashlib.sha256(portrait.read_bytes()).hexdigest()}], generate_json=provider)
        self.assertEqual(result["frames"][0]["source_sha256"], "a" * 64)
        self.assertEqual(result["frames"][0]["sample_sha256"], sample["sample_sha256"])
        self.assertEqual([Path(value).name for value in calls[0]["image_paths"]],
            ["sample.jpg", "character.png"])
        self.assertIn("scene context and expected cast are not identity evidence", calls[0]["prompt"])

    def test_description_only_identity_review_uses_frames_without_portrait_images(self):
        frame = self.root / "sample.jpg"
        frame.write_bytes(b"sample-frame")
        sample = {"path": str(frame), "timestamp_seconds": 2.5,
            "source_sha256": "a" * 64, "sample_sha256": hashlib.sha256(frame.read_bytes()).hexdigest(),
            "sample_index": 1}
        calls = []

        def provider(**kwargs):
            calls.append(kwargs)
            return {"frames": [{"sample_index": 1, "timestamp_seconds": 2.5,
                "observations": [{"status": "ambiguous", "character_id": None,
                    "visual_evidence": "A person is visible but the outfit is not distinctive.",
                    "visible_people": 1, "face_clear": False, "bbox": None}]}]}

        result = analyze_identity_frames(samples=[sample], characters=[{"character_id": "char-1",
            "name": "Mira", "visual_description": "She has a silver streak through her black hair."}],
            generate_json=provider)
        self.assertEqual(calls[0]["image_paths"], [str(frame)])
        self.assertIn("generic, hidden, or not distinguishable, return ambiguous", calls[0]["prompt"])
        self.assertEqual(result["frames"][0]["observations"][0]["status"], "ambiguous")

    def test_vision_review_rejects_unknown_ids_changed_frames_and_ambiguous_assignment(self):
        frame = self.root / "sample.jpg"
        portrait = self.root / "character.png"
        frame.write_bytes(b"sample-frame")
        portrait.write_bytes(b"character-reference")
        sample = {"path": str(frame), "timestamp_seconds": 1.0,
            "source_sha256": "b" * 64, "sample_sha256": hashlib.sha256(frame.read_bytes()).hexdigest(),
            "sample_index": 1}
        unknown = {"frames": [{"sample_index": 1, "timestamp_seconds": 1.0,
            "observations": [{"status": "candidate_match", "character_id": "invented",
                "visual_evidence": "A face is visible.", "visible_people": 1,
                "face_clear": True, "bbox": [0.2, 0.1, 0.8, 0.95]}]}]}
        with self.assertRaisesRegex(ValueError, "canonical character ID"):
            validate_identity_observations(unknown, samples=[sample], canonical_character_ids={"char-1"})
        ambiguous_assignment = {"frames": [{"sample_index": 1, "timestamp_seconds": 1.0,
            "observations": [{"status": "ambiguous", "character_id": "char-1",
                "visual_evidence": "A person is partly obscured.", "visible_people": 1,
                "face_clear": False, "bbox": None}]}]}
        with self.assertRaisesRegex(ValueError, "cannot assign"):
            validate_identity_observations(ambiguous_assignment, samples=[sample], canonical_character_ids={"char-1"})
        two_ids_one_person = {"frames": [{"sample_index": 1, "timestamp_seconds": 1.0,
            "observations": [
                {"status": "candidate_match", "character_id": "char-1",
                    "visual_evidence": "Distinctive coat.", "visible_people": 1,
                    "face_clear": True, "bbox": [0.2, 0.1, 0.8, 0.95]},
                {"status": "candidate_match", "character_id": "char-2",
                    "visual_evidence": "Same distinctive coat.", "visible_people": 1,
                    "face_clear": True, "bbox": [0.2, 0.1, 0.8, 0.95]},
            ]}]}
        with self.assertRaisesRegex(ValueError, "at most one character crop"):
            validate_identity_observations(two_ids_one_person, samples=[sample],
                canonical_character_ids={"char-1", "char-2"})
        frame.write_bytes(b"changed-frame")
        with self.assertRaisesRegex(ValueError, "changed after extraction"):
            analyze_identity_frames(samples=[sample], characters=[{"character_id": "char-1",
                "name": "Mira", "reference_path": str(portrait),
                "reference_sha256": hashlib.sha256(portrait.read_bytes()).hexdigest()}],
                generate_json=lambda **_: {})

    def test_vision_results_keep_one_row_per_frame_with_zero_or_multiple_observations(self):
        samples = [
            {"path": "unused-1.jpg", "timestamp_seconds": 1.0, "source_sha256": "c" * 64,
             "sample_sha256": "d" * 64, "sample_index": 1},
            {"path": "unused-2.jpg", "timestamp_seconds": 2.0, "source_sha256": "c" * 64,
             "sample_sha256": "e" * 64, "sample_index": 2},
        ]
        result = {"frames": [
            {"sample_index": 1, "timestamp_seconds": 1.0, "observations": []},
            {"sample_index": 2, "timestamp_seconds": 2.0, "observations": [
                {"status": "not_visible", "character_id": None,
                 "visual_evidence": "No person is clearly visible.", "visible_people": 0,
                 "face_clear": False, "bbox": None},
                {"status": "ambiguous", "character_id": None,
                 "visual_evidence": "A person is visible but obscured.", "visible_people": 1,
                 "face_clear": False, "bbox": None},
            ]},
        ]}
        normalized = validate_identity_observations(result, samples=samples,
            canonical_character_ids={"char-1"})["frames"]
        self.assertEqual([frame["sample_index"] for frame in normalized], [1, 2])
        self.assertEqual([len(frame["observations"]) for frame in normalized], [0, 2])

    def test_identity_crop_requires_recurrence_across_distinct_frames(self):
        observation = {"status": "candidate_match", "character_id": "char-1",
            "bbox": [0.2, 0.1, 0.8, 0.95], "visual_evidence": "Red coat and short hair."}
        one_frame = [{"sample_index": 1, "timestamp_seconds": 1.0,
            "sample_sha256": "a" * 64, "observations": [observation]}]
        self.assertEqual(_consensus_identity_candidates(one_frame), {})
        repeated = [*one_frame, {"sample_index": 2, "timestamp_seconds": 2.0,
            "sample_sha256": "b" * 64, "observations": [observation]}]
        selected = _consensus_identity_candidates(repeated)
        self.assertEqual(set(selected), {"char-1"})
        self.assertEqual(selected["char-1"]["frame"]["sample_index"], 1)
        self.assertEqual(selected["char-1"]["sample_indexes"], {1, 2})
        self.assertEqual([row["sample_index"] for row in selected["char-1"]["supporting_frames"]], [1, 2])

    def test_processor_records_every_frame_that_supported_a_character_crop(self):
        portrait = self.root / "portrait.png"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
            "-f", "lavfi", "-i", "color=c=blue:s=200x200", "-frames:v", "1", str(portrait)],
            check=True, capture_output=True, timeout=30)
        portrait_hash = hashlib.sha256(portrait.read_bytes()).hexdigest()
        samples = []
        for index, color in enumerate(("red", "green", "blue"), start=1):
            frame_path = self.root / f"frame-{index}.jpg"
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
                "-f", "lavfi", "-i", f"color=c={color}:s=200x200", "-frames:v", "1", str(frame_path)],
                check=True, capture_output=True, timeout=30)
            samples.append({"path": str(frame_path), "timestamp_seconds": float(index),
                "source_sha256": self.digest, "sample_sha256": hashlib.sha256(frame_path.read_bytes()).hexdigest(),
                "sample_index": index})
        store = IdentityReviewStore(self.root / "ledger.sqlite3")
        queued = store.enqueue(workspace_id="story-1", screenplay_revision_id="revision-1",
            scene_number=1, source_job_id="job-1", source_asset_id="pa-0123456789abcdef",
            source_sha256=self.digest, duration_seconds=8,
            characters=[{"character_id": "char-1", "name": "Mira",
                "reference_path": str(portrait), "reference_sha256": portrait_hash}])
        processor = IdentityReviewProcessor(store, data_root=self.root,
            source_resolver=lambda _workspace, _asset: self.video)
        observations = [{"status": "candidate_match", "character_id": "char-1",
            "visual_evidence": "Red coat and short hair.", "visible_people": 1,
            "face_clear": True, "bbox": [0.2, 0.1, 0.8, 0.95]}]
        result_payload = {"frames": [{"sample_index": row["sample_index"],
            "timestamp_seconds": row["timestamp_seconds"], "observations": observations,
            "source_sha256": self.digest, "sample_sha256": row["sample_sha256"]} for row in samples]}
        registered = []
        def register(_root, _workspace, **values):
            registered.append(values)
            return {"asset_id": "pa-1123456789abcdef", "sha256": hashlib.sha256(values["content"]).hexdigest()}
        with patch("story_builder.services.fully_automated_identity.sample_identity_frames", return_value=samples), \
             patch("story_builder.services.fully_automated_identity.analyze_identity_frames", return_value=result_payload), \
             patch("story_builder.services.media_library.register_upload", side_effect=register):
            result = processor.process_one()
        self.assertEqual(result["status"], "completed")
        reference = result["review"]["result"]["derived_references"][0]
        self.assertEqual(reference["character_id"], "char-1")
        self.assertEqual(reference["frame_kind"], "last")
        self.assertEqual(reference["sample_sha256"], samples[-1]["sample_sha256"])
        self.assertEqual([row["sample_index"] for row in reference["supporting_frames"]], [1, 2, 3])
        crop_path = self.root / "registered-character-crop.jpg"
        crop_path.write_bytes(registered[0]["content"])
        dimensions = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height", "-of", "csv=s=x:p=0", str(crop_path)],
            check=True, capture_output=True, text=True, timeout=30).stdout.strip()
        crop_width, crop_height = (int(value) for value in dimensions.split("x", 1))
        self.assertGreaterEqual(crop_width, 96)
        self.assertGreaterEqual(crop_height, 96)
        self.assertLess(crop_width, 200)
        self.assertLess(crop_height, 200)
        provenance = json.loads(registered[0]["provenance_notes"])
        self.assertEqual([row["sample_index"] for row in provenance["supporting_frames"]], [1, 2, 3])

    def test_durable_review_claim_retries_and_persists_completion(self):
        portrait = self.root / "character.png"
        portrait.write_bytes(b"portrait")
        portrait_hash = hashlib.sha256(portrait.read_bytes()).hexdigest()
        store = IdentityReviewStore(self.root / "ledger.sqlite3")
        queued = store.enqueue(workspace_id="story-1", screenplay_revision_id="revision-1",
            scene_number=1, source_job_id="job-1", source_asset_id="pa-0123456789abcdef",
            source_sha256="a" * 64, duration_seconds=8,
            characters=[{"character_id":"char-1", "name":"Mira",
                "reference_path":str(portrait), "reference_sha256":portrait_hash}])
        replay = store.enqueue(workspace_id="story-1", screenplay_revision_id="revision-1",
            scene_number=1, source_job_id="job-1", source_asset_id="pa-0123456789abcdef",
            source_sha256="a" * 64, duration_seconds=8,
            characters=[{"character_id":"char-1", "name":"Mira",
                "reference_path":str(portrait), "reference_sha256":portrait_hash}])
        self.assertEqual(queued["review_id"], replay["review_id"])
        with self.assertRaisesRegex(ValueError, "already frozen"):
            store.enqueue(workspace_id="story-1", screenplay_revision_id="revision-1",
                scene_number=1, source_job_id="job-1", source_asset_id="pa-0123456789abcdef",
                source_sha256="a" * 64, duration_seconds=8,
                characters=[{"character_id":"char-1", "name":"Mira revised",
                    "reference_path":str(portrait), "reference_sha256":portrait_hash}])
        first = store.claim_next(lease_seconds=30)
        self.assertEqual(first["attempt_count"], 1)
        failed = store.fail(first["review_id"], first["owner_token"], "provider timeout")
        self.assertEqual(failed["state"], "queued")
        second = store.claim_next(lease_seconds=30)
        self.assertEqual(second["attempt_count"], 2)
        completed = store.complete(second["review_id"], second["owner_token"], {"frames": []})
        self.assertEqual(completed["state"], "complete")
        self.assertEqual(completed["result"], {"frames": []})
        self.assertEqual(store.get(completed["review_id"])["result"], {"frames": []})
        self.assertIsNone(store.claim_next())

    def test_expired_lease_can_be_reclaimed_and_old_owner_cannot_complete(self):
        portrait = self.root / "character.png"
        portrait.write_bytes(b"portrait")
        store = IdentityReviewStore(self.root / "ledger.sqlite3")
        store.enqueue(workspace_id="story-1", screenplay_revision_id="revision-1",
            scene_number=1, source_job_id="job-1", source_asset_id="pa-0123456789abcdef",
            source_sha256="a" * 64, duration_seconds=8,
            characters=[{"character_id":"char-1", "name":"Mira",
                "reference_path":str(portrait), "reference_sha256":hashlib.sha256(b"portrait").hexdigest()}])
        old = store.claim_next(lease_seconds=30)
        with store._connect() as db:
            db.execute("UPDATE fully_automated_identity_reviews SET lease_until='2000-01-01T00:00:00+00:00' WHERE review_id=?", (old["review_id"],))
        new = store.claim_next(lease_seconds=30)
        self.assertEqual(new["attempt_count"], 2)
        with self.assertRaisesRegex(ValueError, "lease expired or was replaced"):
            store.complete(old["review_id"], old["owner_token"], {"frames": []})

    def test_processor_resolves_source_by_asset_id_and_persists_validated_result(self):
        video = self.root / "runtime-video.mp4"
        video.write_bytes(b"registered video bytes")
        portrait = self.root / "portrait.png"
        portrait.write_bytes(b"portrait")
        video_hash = hashlib.sha256(video.read_bytes()).hexdigest()
        store = IdentityReviewStore(self.root / "ledger.sqlite3")
        queued = store.enqueue(workspace_id="story-1", screenplay_revision_id="revision-1",
            scene_number=1, source_job_id="job-1", source_asset_id="pa-0123456789abcdef",
            source_sha256=video_hash, duration_seconds=8,
            characters=[{"character_id": "char-1", "name": "Mira",
                "reference_path": str(portrait), "reference_sha256": hashlib.sha256(b"portrait").hexdigest()}])
        sample_file = self.root / "frame.jpg"
        sample_file.write_bytes(b"sample")
        sample = {"path": str(sample_file), "timestamp_seconds": 2.0,
            "source_sha256": video_hash, "sample_sha256": hashlib.sha256(b"sample").hexdigest(),
            "sample_index": 1}
        processor = IdentityReviewProcessor(store, data_root=self.root,
            source_resolver=lambda workspace, asset: video)
        with patch("story_builder.services.fully_automated_identity.sample_identity_frames", return_value=[sample]) as sample_frames, \
             patch("story_builder.services.fully_automated_identity.analyze_identity_frames",
                   return_value={"frames": [{"sample_index": 1, "timestamp_seconds": 2.0,
                       "observations": [], "source_sha256": video_hash,
                       "sample_sha256": sample["sample_sha256"]}]}) as analyze:
            result = processor.process_one()
        self.assertEqual(result["status"], "completed")
        self.assertEqual(store.get(queued["review_id"])["state"], "complete")
        sample_frames.assert_called_once()
        analyze.assert_called_once()

    def test_processor_rejects_character_reference_outside_product_root(self):
        other = self.root.parent / "outside-character.png"
        other.write_bytes(b"external portrait")
        self.addCleanup(other.unlink, missing_ok=True)
        store = IdentityReviewStore(self.root / "ledger.sqlite3")
        store.enqueue(workspace_id="story-1", screenplay_revision_id="revision-1",
            scene_number=1, source_job_id="job-1", source_asset_id="pa-0123456789abcdef",
            source_sha256=self.digest, duration_seconds=8,
            characters=[{"character_id": "char-1", "name": "Mira",
                "reference_path": str(other), "reference_sha256": hashlib.sha256(other.read_bytes()).hexdigest()}])
        processor = IdentityReviewProcessor(store, data_root=self.root,
            source_resolver=lambda _workspace, _asset: self.video)
        result = processor.process_one()
        self.assertEqual(result["status"], "queued")
        self.assertEqual(result["review"]["error_message"], "Identity review failed (ValueError).")

    def test_completed_full_clip_enqueues_only_targeted_selected_character_once(self):
        portrait = self.root / "portrait.png"
        portrait.write_bytes(b"portrait")
        video_hash = "b" * 64
        manifest = {"clip_plan": {"clips": [{"clip_id": "clip-1",
            "target_character_ids": ["character-1"],
            "evidence_record_ids": ["event-1"]}]}}
        db_path = self.root / "ledger.sqlite3"
        with sqlite3.connect(db_path) as db:
            db.executescript("""CREATE TABLE fully_automated_runs (
                workspace_id TEXT, screenplay_revision_id TEXT, run_state TEXT, manifest_json TEXT);
                CREATE TABLE story_screenplay_revisions (
                workspace_id TEXT, screenplay_revision_id TEXT, graph_snapshot_id TEXT, source_revision_id TEXT, screenplay_json TEXT);
                CREATE TABLE isolated_video_jobs (job_id TEXT, workspace_id TEXT, source_lineage_json TEXT);
                CREATE TABLE production_takes (job_id TEXT, status TEXT);""")
            db.execute("INSERT INTO fully_automated_runs VALUES(?,?,?,?)",
                ("story-1", "revision-1", "running", json.dumps(manifest)))
            db.execute("INSERT INTO story_screenplay_revisions VALUES(?,?,?,?,?)",
                ("story-1", "revision-1", "graph-1", "source-1", "{}"))

        class Jobs:
            ledger = IdentityReviewStore(db_path)
            def get_fully_automated_first_clip(self, *_args):
                return {"clips": [{"clip_id": "clip-1", "scene_number": 1,
                    "duration_seconds": 8, "job": {"job_id": "job-1", "status": "needs_review",
                    "outputs": [{"kind": "video", "has_video": True,
                        "shared_asset_id": "pa-0123456789abcdef", "sha256": video_hash}]}}]}
        class Story:
            def get_story_graph(self, **_kwargs):
                return {"status": "complete", "source_revision_id": "source-1", "records": [
                    {"record_id": "character-1", "kind": "entity", "type": "character", "name": "Mira"},
                    {"record_id": "event-1", "kind": "event", "type": "event", "name": "enters"}]}
        class Selections:
            def get(self, **_kwargs):
                return {"asset_id": "pa-1123456789abcdef"}
        store = IdentityReviewStore(db_path)
        with patch("story_builder.services.media_library.asset_path",
                return_value=(portrait, "image/png", "portrait.png")):
            first = enqueue_completed_full_run_identity_reviews(jobs=Jobs(), story=Story(),
                selections=Selections(), store=store, data_root=self.root)
            second = enqueue_completed_full_run_identity_reviews(jobs=Jobs(), story=Story(),
                selections=Selections(), store=store, data_root=self.root)
        self.assertEqual((first, second), (1, 0))
        with store._connect() as db:
            row = db.execute("SELECT state,input_json FROM fully_automated_identity_reviews").fetchone()
        self.assertEqual(row["state"], "queued")
        self.assertEqual(json.loads(row["input_json"])["characters"][0]["character_id"], "character-1")

    def test_completed_full_clip_uses_graph_description_when_no_portrait_is_selected(self):
        video_hash = "c" * 64
        manifest = {"clip_plan": {"clips": [{"clip_id": "clip-1",
            "target_character_ids": ["character-1"], "evidence_record_ids": ["event-1"]}]}}
        db_path = self.root / "description-ledger.sqlite3"
        with sqlite3.connect(db_path) as db:
            db.executescript("""CREATE TABLE fully_automated_runs (
                workspace_id TEXT, screenplay_revision_id TEXT, run_state TEXT, manifest_json TEXT);
                CREATE TABLE story_screenplay_revisions (
                workspace_id TEXT, screenplay_revision_id TEXT, graph_snapshot_id TEXT, source_revision_id TEXT, screenplay_json TEXT);
                CREATE TABLE isolated_video_jobs (job_id TEXT, workspace_id TEXT, source_lineage_json TEXT);
                CREATE TABLE production_takes (job_id TEXT, status TEXT);""")
            db.execute("INSERT INTO fully_automated_runs VALUES(?,?,?,?)",
                ("story-1", "revision-1", "running", json.dumps(manifest)))
            db.execute("INSERT INTO story_screenplay_revisions VALUES(?,?,?,?,?)",
                ("story-1", "revision-1", "graph-1", "source-1", "{}"))

        class Jobs:
            ledger = IdentityReviewStore(db_path)
            def get_fully_automated_first_clip(self, *_args):
                return {"clips": [{"clip_id": "clip-1", "scene_number": 1,
                    "duration_seconds": 8, "job": {"job_id": "job-1", "status": "accepted",
                    "outputs": [{"kind": "video", "has_video": True,
                        "shared_asset_id": "pa-0123456789abcdef", "sha256": video_hash}]}}]}
        class Story:
            def get_story_graph(self, **_kwargs):
                return {"status": "complete", "source_revision_id": "source-1", "records": [
                    {"record_id": "character-1", "kind": "entity", "type": "character", "name": "Mira",
                     "detail": "She has a silver streak through her black hair."}]}
        class Selections:
            def get(self, **_kwargs):
                return None
        store = IdentityReviewStore(db_path)
        queued = enqueue_completed_full_run_identity_reviews(jobs=Jobs(), story=Story(),
            selections=Selections(), store=store, data_root=self.root)
        self.assertEqual(queued, 1)
        with store._connect() as db:
            row = db.execute("SELECT input_json FROM fully_automated_identity_reviews").fetchone()
        self.assertEqual(json.loads(row["input_json"])["characters"], [{"character_id": "character-1",
            "name": "Mira", "visual_description": "She has a silver streak through her black hair."}])


if __name__ == "__main__":
    unittest.main()
