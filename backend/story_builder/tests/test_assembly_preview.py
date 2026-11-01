import unittest
import tempfile
import hashlib
import json
from pathlib import Path

from story_builder.services.assembly import (AssemblyExportJobs, AssemblySelections, build_assembly_preview,
    build_assembly_snapshot, build_export_manifest, validate_export_settings,
    validate_assembly_audio_tracks, validate_assembly_selection)
from story_builder.services.production_ledger import ProductionLedger


class AssemblyPreviewTests(unittest.TestCase):
    def test_export_settings_are_explicit_and_bounded(self):
        settings = {"resolution":"1080p", "frame_rate":24, "quality":22,
            "audio_policy":"preserve_and_mix"}
        self.assertEqual(validate_export_settings(settings), {"container":"mp4",
            "video_codec":"libx264", "audio_codec":"aac", **settings})
        for changed in ({**settings, "resolution":"source"},
                        {**settings, "frame_rate":25},
                        {**settings, "quality":17},
                        {**settings, "audio_policy":"guess"}):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                validate_export_settings(changed)
        with self.assertRaises(ValueError):
            validate_export_settings({**settings, "resolution": []})

    def test_export_manifest_pins_snapshot_and_explicit_settings(self):
        snapshot = {"snapshot_id":"assembly-a", "snapshot_sha256":"b" * 64,
            "screenplay_revision_id":"rev", "snapshot":{"state":"awaiting_export_settings",
                "clips":[{"job_id":"take"}], "audio_tracks":[]}}
        settings = validate_export_settings({"resolution":"720p", "frame_rate":30,
            "quality":24, "audio_policy":"mute"})
        manifest = build_export_manifest(snapshot, settings)
        self.assertEqual(manifest["state"], "ready_for_render")
        self.assertEqual(manifest["snapshot_sha256"], "b" * 64)
        self.assertEqual(manifest["export_settings"]["resolution"], "720p")
        with self.assertRaisesRegex(ValueError, "frozen assembly snapshot"):
            build_export_manifest({**snapshot, "snapshot":{"state":"ready_for_render"}}, settings)

    def test_uses_screenplay_order_and_only_accepted_playable_takes(self):
        screenplay = {"scenes": [{"scene_number": 2, "shots": [{"shot_number": 1}]},
            {"scene_number": 1, "shots": [{"shot_number": 1}]}]}
        jobs = [
            {"job_id": "accepted", "clip_id": "clip-a", "status": "accepted",
             "request": {"workflow_id": "minimax_h3_t2v_local_v1", "prompt": "A wide shot"},
             "request_hash": hashlib.sha256(json.dumps({"workflow_id": "minimax_h3_t2v_local_v1", "prompt": "A wide shot"}, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest(),
             "source_lineage": {"screenplay_revision_id": "rev", "scene_number": 2, "shot_number": 1},
             "outputs": [{"kind": "video", "playback_url": "/video/a"}]},
            {"job_id": "review", "clip_id": "clip-a", "status": "needs_review",
             "source_lineage": {"screenplay_revision_id": "rev", "scene_number": 2, "shot_number": 1},
             "outputs": [{"kind": "video", "playback_url": "/video/b"}]},
            {"job_id": "discarded-accepted", "clip_id": "clip-a", "status": "accepted",
             "candidate_disposition": "discard_requested",
             "source_lineage": {"screenplay_revision_id": "rev", "scene_number": 2, "shot_number": 1},
             "outputs": [{"kind": "video", "playback_url": "/video/discarded"}]},
            {"job_id": "audio-only", "clip_id": "clip-c", "status": "accepted",
             "source_lineage": {"screenplay_revision_id": "other-rev", "scene_number": 1, "shot_number": 1},
             "outputs": [{"kind": "audio", "playback_url": "/audio/c"}]},
        ]
        result = build_assembly_preview(screenplay, jobs, screenplay_revision_id="rev")
        self.assertEqual([(clip["scene_number"], clip["shot_number"]) for clip in result["clips"]], [(2, 1), (1, 1)])
        self.assertEqual([take["job_id"] for take in result["clips"][0]["accepted_takes"]], ["accepted"])
        self.assertEqual(result["clips"][0]["accepted_takes"][0]["request"]["workflow_id"], "minimax_h3_t2v_local_v1")
        self.assertEqual([take["job_id"] for take in result["clips"][0]["review_takes"]], ["review"])
        self.assertTrue(result["clips"][1]["missing_accepted_take"])
        self.assertEqual(result["missing_clip_count"], 1)

    def test_full_run_keeps_distinct_dynamic_clip_order_and_marks_partial_run(self):
        clips = [{"clip_id": "clip-2", "scene_number": 1, "shot_number": 1, "clip_number": 2},
                 {"clip_id": "clip-1", "scene_number": 1, "shot_number": 1, "clip_number": 1}]
        jobs = [{"job_id": "job-1", "clip_id": "clip-1", "status": "accepted",
            "outputs": [{"kind": "video", "playback_url": "/video/1"}]}]
        result = build_assembly_preview({"scenes": []}, jobs,
            screenplay_revision_id="rev", full_run={"run_state": "running", "planned_count": 3, "clips": clips})
        self.assertEqual([item["clip_number"] for item in result["clips"]], [2, 1])
        self.assertEqual(result["planned_source"], "full_run")
        self.assertTrue(result["planning_incomplete"])
        self.assertEqual(result["missing_clip_count"], 1)

    def test_selection_accepts_only_accepted_takes_for_current_clip_keys(self):
        preview = {"clips": [
            {"clip_id": "clip-a", "accepted_takes": [{"job_id": "take-a"}]},
            {"scene_number": 2, "shot_number": 1, "clip_number": 1,
             "accepted_takes": [{"job_id": "take-b"}]},
        ]}
        self.assertEqual(validate_assembly_selection(preview, {"clip-a": "take-a"}), {"clip-a": "take-a"})
        with self.assertRaisesRegex(ValueError, "accepted video take"):
            validate_assembly_selection(preview, {"clip-a": "take-b"})
        with self.assertRaisesRegex(ValueError, "not part"):
            validate_assembly_selection(preview, {"deleted-clip": "take-a"})

    def test_selection_store_survives_reopen(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = ProductionLedger(Path(directory) / "ledger.sqlite3")
            first = AssemblySelections(ledger)
            first.save("workspace", "revision", {"clip-a": "take-a"})
            reopened = AssemblySelections(ledger)
            saved = reopened.get("workspace", "revision")
            self.assertEqual(saved["selections"], {"clip-a": "take-a"})
            self.assertEqual(saved["workspace_id"], "workspace")

    def test_audio_tracks_validate_identity_timing_trim_and_gain(self):
        asset = {"asset_id": "audio-a", "kind": "audio", "sha256": "a" * 64,
            "media": {"duration_seconds": 12.0}}
        track = {"asset_id": "audio-a", "sha256": "a" * 64, "start_seconds": 1,
            "trim_start_seconds": 2, "trim_end_seconds": 8, "gain": 0.8}
        self.assertEqual(validate_assembly_audio_tracks({"audio-a": asset}, [track])[0]["trim_end_seconds"], 8.0)
        with self.assertRaisesRegex(ValueError, "file changed"):
            validate_assembly_audio_tracks({"audio-a": asset}, [{**track, "sha256": "b" * 64}])
        with self.assertRaisesRegex(ValueError, "outside the supported range"):
            validate_assembly_audio_tracks({"audio-a": asset}, [{**track, "trim_end_seconds": 13}])
        with self.assertRaisesRegex(ValueError, "only once"):
            validate_assembly_audio_tracks({"audio-a": asset}, [track, track])
        with self.assertRaisesRegex(ValueError, "verified file duration"):
            validate_assembly_audio_tracks({"audio-a": {**asset, "media": {}}}, [track])

    def test_audio_track_store_survives_reopen(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = ProductionLedger(Path(directory) / "ledger.sqlite3")
            first = AssemblySelections(ledger)
            track = {"asset_id": "audio-a", "sha256": "a" * 64,
                "start_seconds": 0.0, "trim_start_seconds": 0.0, "trim_end_seconds": 4.0, "gain": 1.0}
            first.save_audio("workspace", "revision", [track])
            self.assertEqual(AssemblySelections(ledger).get_audio("workspace", "revision")["audio_tracks"], [track])

    def test_snapshot_freezes_complete_accepted_outputs_and_audio_without_export_settings(self):
        digest = "a" * 64
        request = {"workflow_id":"minimax_h3_r2v_local_v1", "workflow_sha256":"c" * 64,
            "prompt":"Continue the previous shot", "duration_seconds":6}
        request_hash = hashlib.sha256(json.dumps(request, sort_keys=True,
            separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
        lineage = {"screenplay_revision_id":"revision", "scene_number":1, "shot_number":1,
            "source_prompt_sha256":"d" * 64, "setup_hash":"e" * 64}
        preview = {"screenplay_revision_id":"revision", "planning_incomplete":False, "clips":[
            {"clip_id":"clip-a", "scene_number":1, "shot_number":1, "clip_number":1,
             "accepted_takes":[{"job_id":"take-a", "request_hash":request_hash, "request":request,
                "source_lineage":lineage, "created_at":"2026-10-11T00:00:00Z", "outputs":[{"asset_id":"asset-a", "shared_asset_id":"pa-asset",
                "sha256":digest, "kind":"video", "duration_seconds":6.0, "has_audio":True, "has_video":True}]}]}]}
        audio = [{"asset_id":"audio-a", "sha256":"b" * 64, "start_seconds":0.0,
            "trim_start_seconds":1.0, "trim_end_seconds":4.0, "gain":0.8}]
        snapshot = build_assembly_snapshot(preview, {"clip-a":"take-a"}, audio,
            screenplay={"source_revision_id":"source", "style_selection_snapshot_id":"style-v2"},
            setup={"mode":"assisted_manual"})
        self.assertEqual(snapshot["state"], "awaiting_export_settings")
        self.assertIsNone(snapshot["export_settings"])
        self.assertEqual(snapshot["clips"][0]["outputs"][0]["sha256"], digest)
        self.assertEqual(snapshot["clips"][0]["request_hash"], request_hash)
        self.assertEqual(snapshot["clips"][0]["request"], request)
        self.assertEqual(snapshot["clips"][0]["source_lineage"], lineage)
        self.assertEqual(snapshot["clips"][0]["take_created_at"], "2026-10-11T00:00:00Z")
        self.assertEqual(snapshot["audio_tracks"], audio)
        with self.assertRaisesRegex(ValueError, "every planned clip"):
            build_assembly_snapshot(preview, {}, audio, screenplay={}, setup={})
        with self.assertRaisesRegex(ValueError, "must start before the assembled video ends"):
            build_assembly_snapshot(preview, {"clip-a":"take-a"},
                [{**audio[0], "start_seconds":6.0}], screenplay={}, setup={})

    def test_snapshot_rejects_request_hash_mismatch(self):
        preview = {"planning_incomplete":False, "clips":[{"clip_id":"clip-a", "accepted_takes":[
            {"job_id":"take-a", "request":{"prompt":"tampered"}, "request_hash":"0" * 64,
             "outputs":[{"kind":"video", "asset_id":"asset-a", "sha256":"a" * 64,
                "duration_seconds":1.0}]}]}]}
        with self.assertRaisesRegex(ValueError, "does not match its request hash"):
            build_assembly_snapshot(preview, {"clip-a":"take-a"}, [], screenplay={}, setup={})

    def test_snapshot_store_is_immutable_and_idempotent_for_same_content(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = ProductionLedger(Path(directory) / "ledger.sqlite3")
            store = AssemblySelections(ledger)
            snapshot = {"state":"awaiting_export_settings", "clips":[], "audio_tracks":[]}
            first = store.save_snapshot("workspace", "revision", snapshot)
            repeated = AssemblySelections(ledger).save_snapshot("workspace", "revision", snapshot)
            changed = store.save_snapshot("workspace", "revision", {**snapshot, "clips":[{"job_id":"take"}]})
            self.assertEqual(first["snapshot_id"], repeated["snapshot_id"])
            self.assertNotEqual(first["snapshot_id"], changed["snapshot_id"])
            self.assertEqual(len(store.list_snapshots("workspace", "revision")), 2)

    def test_identical_snapshots_are_isolated_by_workspace_and_revision(self):
        with tempfile.TemporaryDirectory() as directory:
            store = AssemblySelections(ProductionLedger(Path(directory) / "ledger.sqlite3"))
            snapshot = {"state":"awaiting_export_settings", "clips":[], "audio_tracks":[]}
            first = store.save_snapshot("workspace-a", "revision", snapshot)
            other_workspace = store.save_snapshot("workspace-b", "revision", snapshot)
            other_revision = store.save_snapshot("workspace-a", "revision-2", snapshot)
            self.assertEqual(first["snapshot_sha256"], other_workspace["snapshot_sha256"])
            self.assertNotEqual(first["snapshot_id"], other_workspace["snapshot_id"])
            self.assertNotEqual(first["snapshot_id"], other_revision["snapshot_id"])
            self.assertEqual(store.get_snapshot("workspace-a", "revision", first["snapshot_id"])["workspace_id"], "workspace-a")
            self.assertIsNone(store.get_snapshot("workspace-b", "revision", first["snapshot_id"]))

    def test_export_manifest_store_is_content_addressed_and_workspace_scoped(self):
        with tempfile.TemporaryDirectory() as directory:
            store = AssemblySelections(ProductionLedger(Path(directory) / "ledger.sqlite3"))
            manifest = {"state":"ready_for_render", "export_settings":{"resolution":"1080p"}}
            saved = store.save_export_manifest("workspace", "revision", manifest)
            repeated = AssemblySelections(store.ledger).save_export_manifest("workspace", "revision", manifest)
            self.assertEqual(saved["manifest_id"], repeated["manifest_id"])
            self.assertEqual(store.list_export_manifests("workspace", "revision")[0]["manifest"], manifest)

    def test_identical_export_manifests_are_isolated_by_workspace_and_revision(self):
        with tempfile.TemporaryDirectory() as directory:
            store = AssemblySelections(ProductionLedger(Path(directory) / "ledger.sqlite3"))
            manifest = {"state":"ready_for_render", "export_settings":{"resolution":"1080p"}}
            first = store.save_export_manifest("workspace-a", "revision", manifest)
            other_workspace = store.save_export_manifest("workspace-b", "revision", manifest)
            other_revision = store.save_export_manifest("workspace-a", "revision-2", manifest)
            self.assertEqual(first["manifest_sha256"], other_workspace["manifest_sha256"])
            self.assertNotEqual(first["manifest_id"], other_workspace["manifest_id"])
            self.assertNotEqual(first["manifest_id"], other_revision["manifest_id"])
            self.assertEqual(store.list_export_manifests("workspace-b", "revision")[0]["workspace_id"], "workspace-b")

    def test_export_jobs_are_durable_idempotent_and_recover_after_worker_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = ProductionLedger(Path(directory) / "ledger.sqlite3")
            selections = AssemblySelections(ledger)
            manifest = selections.save_export_manifest("workspace", "revision", {"state":"ready_for_render"})
            jobs = AssemblyExportJobs(ledger)
            queued = jobs.enqueue("workspace", "revision", manifest)
            self.assertEqual(jobs.enqueue("workspace", "revision", manifest)["job_id"], queued["job_id"])
            claimed = jobs.claim_next()
            self.assertEqual(claimed["state"], "rendering")
            jobs.update_progress(queued["job_id"], 42)
            jobs.update_progress(queued["job_id"], 18)
            self.assertEqual(jobs.get("workspace", "revision", queued["job_id"])["progress_percent"], 42)
            reopened = AssemblyExportJobs(ProductionLedger(Path(directory) / "ledger.sqlite3"))
            self.assertEqual(reopened.recover_running(), 1)
            recovered = reopened.claim_next()
            self.assertEqual(recovered["job_id"], queued["job_id"])
            self.assertEqual(recovered["progress_percent"], 0)
            reopened.update_progress(queued["job_id"], 140)
            self.assertEqual(reopened.get("workspace", "revision", queued["job_id"])["progress_percent"], 99)
            reopened.fail(queued["job_id"], "ffmpeg error")
            self.assertEqual(reopened.get("workspace", "revision", queued["job_id"])["state"], "failed")
            retried = reopened.retry("workspace", "revision", queued["job_id"])
            self.assertEqual(retried["state"], "queued")
            self.assertEqual(retried["progress_percent"], 0)


if __name__ == "__main__":
    unittest.main()
