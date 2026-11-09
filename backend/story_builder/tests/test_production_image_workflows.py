from __future__ import annotations

import io
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from story_builder.isolated_server import _image_lineage, _require_manual_image_stage, create_app
from story_builder.services.production_image_workflows import (
    ImageWorkflowError, SPECS, _read_smoke, compile_image_candidates, generation_policy,
    record_successful_image_smoke,
    image_workflow_catalog,
)
from story_builder.services.production_image_jobs import ProductionImageJobStore
from story_builder.services.production_image_selection import ProductionImageSelection
from story_builder.services.production_ledger import LedgerConflict
from story_builder.services.production_image_worker import ProductionImageWorker
from story_builder.isolated_image_worker import (
    _accepted_world_view_labels, _advance_checked_image_stage, _director_acceptor, _director_review,
    _enqueue_selected_world_views, _unresolved_assisted_voice_ids, image_worker_lifetime_lock,
)


class ProductionImageWorkflowTests(unittest.TestCase):
    def test_opted_in_voice_gate_waits_only_for_unresolved_speaking_characters(self):
        state = {"bindings": [{"character_id": "bound"}], "speech_statuses": [
            {"character_id": "bound", "status": "speaking"},
            {"character_id": "quiet", "status": "not_speaking"},
            {"character_id": "needs-choice", "status": "narrator"},
            {"character_id": "unknown-speaker", "status": "unknown"}]}
        self.assertEqual(_unresolved_assisted_voice_ids(state), ["needs-choice", "unknown-speaker"])
        self.assertEqual(_unresolved_assisted_voice_ids({"bindings": [], "speech_statuses": [
            {"character_id": "quiet", "status": "not_speaking"}]}), [])

    def test_world_direction_completion_requires_review_or_manual_selection_and_unique_labels(self):
        jobs = Mock()
        jobs.get_director_review.side_effect = [
            {"resolution_status": "pending"}, {"resolution_status": "accepted"}]
        views = [{"label": "Front"}, {"label": "Front"}, {"label": "Right"}]
        rows = [
            ("job-auto-pending", "pa-1", 1, "world_view", {"director_review_required": True,
                "lineage": {"target_record_id": "location-a", "base_asset_id": "base-1", "base_asset_sha256": "a"*64}, "world_views": views}, "completed"),
            ("job-auto-accepted", "pa-2", 2, "world_view", {"director_review_required": True,
                "lineage": {"target_record_id": "location-a", "base_asset_id": "base-1", "base_asset_sha256": "a"*64}, "world_views": views}, "completed"),
            ("job-manual-unselected", "pa-3", 3, "world_view", {"lineage": {"target_record_id": "location-a",
                "base_asset_id": "base-1", "base_asset_sha256": "a"*64}, "world_views": views}, "completed"),
        ]
        accepted = _accepted_world_view_labels(workspace="ws", target="location-a", base_asset_id="base-1",
            base_asset_sha256="a"*64, stage_rows=rows,
            assets_by_id={"pa-2": {"roles": []}, "pa-3": {"roles": ["image_candidate"]}}, jobs=jobs)
        self.assertEqual(accepted, {"front"})

    def test_assisted_supervisor_waits_at_unchecked_manual_stage_until_selected_or_skipped(self):
        with tempfile.TemporaryDirectory() as temporary:
            db_path = Path(temporary) / "state.sqlite3"
            setup = {"mode": "assisted_manual", "automate_steps": {
                "character_images": True, "character_voice": False, "world_images": False,
                "frame_images": False, "video": False}}
            setup_hash = hashlib.sha256(json.dumps(setup, sort_keys=True,
                separators=(",", ":")).encode()).hexdigest()
            with sqlite3.connect(db_path) as db:
                db.executescript("""
                    CREATE TABLE story_production_setups(workspace_id TEXT,screenplay_revision_id TEXT,setup_json TEXT,updated_at TEXT);
                    CREATE TABLE production_runs(project_id TEXT,config_json TEXT,created_at TEXT);
                    CREATE TABLE production_image_jobs(project_id TEXT,job_id TEXT,output_asset_id TEXT,candidate_index INTEGER,asset_role TEXT,settings_json TEXT,status TEXT,created_at TEXT);
                """)
                db.execute("INSERT INTO story_production_setups VALUES(?,?,?,?)", (
                    "ws", "sp", json.dumps(setup), "2026-10-13"))
                db.execute("INSERT INTO production_image_jobs VALUES(?,?,?,?,?,?,?,?)", (
                    "ws", "job-char", "pa-1", 1, "character_master", json.dumps({
                        "stage": "character_images", "setup_sha256": setup_hash,
                        "lineage": {"screenplay_revision_id": "sp"}}), "completed", "2026-10-13"))
            def connect():
                db = sqlite3.connect(db_path)
                db.row_factory = sqlite3.Row
                return db
            ledger = Mock()
            ledger._connect.side_effect = connect
            story = Mock()
            story.ledger = ledger
            story.get_screenplay_revision.return_value = {"accepted": True, "graph_snapshot_id": "graph",
                "screenplay": {"scenes": []}}
            story.get_story_graph.return_value = {"records": [{"kind": "entity", "type": "location",
                "record_id": "loc-1"}]}
            jobs = Mock()
            jobs._connect.side_effect = connect
            selections = Mock()
            selections.get.return_value = None
            with patch("story_builder.isolated_image_worker.ProductionSetup.list_assisted_stage_skips",
                    return_value={"skipped": []}):
                result = _advance_checked_image_stage(root=Path(temporary), ledger=ledger,
                    story=story, selections=selections, image_jobs=jobs)
            self.assertEqual(result["status"], "waiting_for_manual")
            self.assertEqual(result["step"], "world_images")

    def test_accepted_checked_character_runs_voice_matching_without_characters_page(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            setup = {"mode": "assisted_manual",
                "automate_steps": {"character_images": True, "character_voice": True,
                    "world_images": False, "frame_images": False, "video": False},
                "image_stage_settings": {"character_images": {"workflow_id": "z_image_turbo",
                    "width": 1024, "height": 1024, "steps": 8, "cfg": 1.0}}}
            setup_hash = hashlib.sha256(json.dumps(setup, sort_keys=True,
                separators=(",", ":")).encode()).hexdigest()
            story = Mock()
            story.get_screenplay_revision.return_value = {"accepted": True,
                "source_revision_id": "source-a", "graph_snapshot_id": "graph-a",
                "style_selection_snapshot_id": "style-a"}
            selections = Mock()
            selections.get.return_value = None
            setup_service = Mock()
            setup_service.get.return_value = {"setup": setup}
            character_voices = Mock()
            accept = _director_acceptor(root=root, story=story, selections=selections,
                setup_service=setup_service, image_jobs=Mock(), character_voices=character_voices)
            job = {"project_id": "workspace-a", "job_id": "job-character",
                "run_id": "run-a", "asset_role": "character_master",
                "output_asset_id": "pa-2222222222222222", "settings": {
                    "stage": "character_images", "setup_sha256": setup_hash,
                    "workflow_id": "z_image_turbo", "width": 1024, "height": 1024,
                    "steps": 8, "cfg": 1.0,
                    "lineage": {"screenplay_revision_id": "revision-a",
                        "source_revision_id": "source-a", "graph_snapshot_id": "graph-a",
                        "style_selection_snapshot_id": "style-a", "target_type": "character",
                        "target_record_id": "character-a"}}}
            with patch("story_builder.isolated_image_worker.assign_media_role",
                    return_value={"asset_id": job["output_asset_id"], "roles": ["character_master"]}):
                accept(job)
            selections.select.assert_called_once()
            self.assertEqual(selections.select.call_args.kwargs["asset_id"], job["output_asset_id"])
            character_voices.run_automatic.assert_called_once_with("workspace-a", "revision-a")

    def test_accepted_direction_view_is_retained_as_world_view_asset(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            base_file = root / "base.png"
            base_file.write_bytes(b"verified-world-master")
            setup = {"mode": "assisted_manual", "automate_steps": {"world_images": True},
                "image_stage_settings": {"world_images": {"world_view_count": 4}}}
            setup_hash = hashlib.sha256(json.dumps(setup, sort_keys=True,
                separators=(",", ":")).encode()).hexdigest()
            story = Mock()
            story.get_screenplay_revision.return_value = {"accepted": True,
                "source_revision_id": "source-a", "graph_snapshot_id": "graph-a",
                "style_selection_snapshot_id": "style-a"}
            selections = Mock()
            selections.get.return_value = {"asset_id": "pa-1111111111111111"}
            setup_service = Mock()
            setup_service.get.return_value = {"setup": setup}
            accept = _director_acceptor(root=root, story=story, selections=selections,
                setup_service=setup_service, image_jobs=Mock())
            job = {"project_id": "workspace-a", "job_id": "job-view", "asset_role": "world_view",
                "output_asset_id": "pa-2222222222222222", "settings": {
                    "stage": "world_images", "setup_sha256": setup_hash,
                    "automated_world_views": True,
                    "image_references": [{"asset_id": "pa-1111111111111111",
                        "sha256": hashlib.sha256(base_file.read_bytes()).hexdigest()}],
                    "world_views": [{"label": item} for item in ("Front", "Right", "Back", "Left")],
                    "lineage": {"screenplay_revision_id": "revision-a", "source_revision_id": "source-a",
                        "graph_snapshot_id": "graph-a", "style_selection_snapshot_id": "style-a",
                        "target_type": "location", "target_record_id": "location-a",
                        "base_asset_id": "pa-1111111111111111",
                        "base_asset_sha256": hashlib.sha256(base_file.read_bytes()).hexdigest()}}}
            with patch("story_builder.isolated_image_worker.asset_path",
                    return_value=(base_file, "image/png", "master.png")), \
                 patch("story_builder.isolated_image_worker.assign_media_role",
                    return_value={"asset_id": job["output_asset_id"], "roles": ["world_view"]}) as assign:
                result = accept(job)
            self.assertTrue(result["world_view"])
            assign.assert_called_once_with(root, "workspace-a", job["output_asset_id"], "world_view")
            selections.select.assert_not_called()

    def test_accepted_world_master_durably_enqueues_direction_views(self):
        image_jobs = Mock()
        selections = Mock()
        selections.get.return_value = {"asset_id": "pa-0123456789abcdef"}
        story = Mock()
        story.get_screenplay_revision.return_value = {
            "screenplay_revision_id": "revision-a", "source_revision_id": "source-a",
            "graph_snapshot_id": "graph-a", "style_selection_snapshot_id": "style-a",
        }
        target = {"record_id": "location-a", "kind": "entity", "type": "location",
            "name": "Harbor", "detail": "Stone harbor in a coastal town."}
        story.get_story_graph.return_value = {"records": [target]}
        job = {"project_id": "workspace-a", "output_asset_id": "pa-0123456789abcdef",
            "run_id": "run-a"}
        lineage = {"screenplay_revision_id": "revision-a", "target_record_id": "location-a",
            "style_selection": {"production_type": "Film", "directing_style": {"display_name": "Natural"}}}
        setup = {"mode": "assisted_manual", "automate_steps": {"world_images": True},
            "image_stage_settings": {"world_images": {"world_view_count": 4}}}
        with patch("story_builder.isolated_image_worker.list_assets", return_value={"assets": [
                {"asset_id": "pa-0123456789abcdef", "roles": ["world_master"], "sha256": "a" * 64}],
                "limit": 100, "total": 1}):
            _enqueue_selected_world_views(root=Path("/tmp"), image_jobs=image_jobs,
                story=story, selections=selections, setup_service=Mock(), job=job,
                lineage=lineage, setup=setup)
        image_jobs.enqueue_batches.assert_called_once()
        batch = image_jobs.enqueue_batches.call_args.args[0][0]
        self.assertEqual(batch["asset_role"], "world_view")
        self.assertEqual(batch["run_id"], "run-a")
        self.assertEqual(len(batch["candidates"]), 4)
        self.assertEqual(batch["settings"]["image_references"][0]["asset_id"], "pa-0123456789abcdef")

    def test_image_smoke_requires_matching_workflow_version_and_graph_hash(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workflow_id = "z_image_turbo"
            graph_hash = "a" * 64
            smoke_root = root / "smokes"
            smoke_root.mkdir()
            record = {"workflow_id": workflow_id, "workflow_version": "1",
                "workflow_sha256": graph_hash, "status": "passed"}
            smoke_path = smoke_root / f"{workflow_id}.json"
            smoke_path.write_text(json.dumps(record), encoding="utf-8")
            self.assertIsNotNone(_read_smoke(smoke_root, workflow_id, "1", graph_hash))
            self.assertIsNone(_read_smoke(smoke_root, workflow_id, "2", graph_hash))
            self.assertIsNone(_read_smoke(smoke_root, workflow_id, "1", "b" * 64))

    def test_bundled_image_graphs_match_adapter_node_and_default_contracts(self):
        graph_root = Path(__file__).resolve().parents[1] / "workflows" / "api"
        sampler_nodes = {
            "flux_kontext_dev": "11", "qwen_image_2512": "230", "z_image_turbo": "44",
            "qwen_image_edit_2511": "3", "qwen_image_multi_angle_2511": "65",
        }
        latent_nodes = {
            "qwen_image_2512": "232", "z_image_turbo": "41",
            "qwen_image_multi_angle_2511": "66",
        }
        for workflow_id, spec in SPECS.items():
            with self.subTest(workflow=workflow_id):
                graph = json.loads((graph_root / spec["graph"]).read_text(encoding="utf-8"))
                classes = {node.get("class_type") for node in graph.values()
                    if isinstance(node, dict)}
                missing = set(spec["required_nodes"]) - classes
                # The multi-angle adapter replaces its PreviewImage output with
                # SaveImage while compiling a candidate graph.
                expected_dynamic_nodes = {"SaveImage"} if workflow_id == "qwen_image_multi_angle_2511" else set()
                self.assertEqual(missing, expected_dynamic_nodes)
                sampler = graph[sampler_nodes[workflow_id]]["inputs"]
                defaults = spec["defaults"]
                self.assertEqual(sampler["steps"], defaults["steps"])
                self.assertEqual(sampler["cfg"], defaults["cfg"])
                if workflow_id == "flux_kontext_dev":
                    self.assertEqual(graph["5"]["class_type"], "FluxKontextImageScale")
                elif workflow_id == "qwen_image_edit_2511":
                    self.assertEqual(graph["93"]["class_type"], "ImageScaleToTotalPixels")
                    self.assertEqual(graph["89"]["class_type"], "LoraLoaderModelOnly")
                else:
                    latent = graph[latent_nodes[workflow_id]]
                    self.assertEqual(latent["class_type"], "EmptySD3LatentImage")
                    self.assertEqual(latent["inputs"]["width"], defaults["width"])
                    self.assertEqual(latent["inputs"]["height"], defaults["height"])

    def test_director_image_review_passes_candidate_bytes_to_codex_and_binds_decision_hash(self):
        with tempfile.TemporaryDirectory() as temporary:
            image = Path(temporary) / "candidate.png"
            image.write_bytes(b"test-image-bytes")
            decision = {"schema_version": 1, "action": "accept", "reason": "Matches Mira.",
                "prompt_delta": "", "criteria": ["identity matches"], "confidence": 0.9}
            with patch("story_builder.isolated_image_worker.generate_json", return_value=decision) as provider:
                result = _director_review({"settings": {"lineage": {"target_type": "character",
                    "target_name": "Mira"}}, "asset_role": "character_master",
                    "prompt": "Mira portrait"}, image)
            provider.assert_called_once()
            self.assertEqual(provider.call_args.kwargs["image_paths"], [image])
            self.assertEqual(result["action"], "accept")
            self.assertEqual(result["image_sha256"], hashlib.sha256(b"test-image-bytes").hexdigest())

    def test_director_image_review_rejects_malformed_provider_decision(self):
        with tempfile.TemporaryDirectory() as temporary:
            image = Path(temporary) / "candidate.png"
            image.write_bytes(b"test-image-bytes")
            with patch("story_builder.isolated_image_worker.generate_json", return_value={"action": "maybe"}):
                with self.assertRaisesRegex(ValueError, "invalid visual review"):
                    _director_review({"settings": {"lineage": {"target_type": "location"}},
                        "asset_role": "world_master", "prompt": "Old station"}, image)

    def test_changed_image_bytes_block_review_without_starving_next_target(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store = ProductionImageJobStore(root / "image-jobs.sqlite3")
            compiled = compile_image_candidates(workflow_id="z_image_turbo", prompt="Mira portrait.",
                control_mode="assisted_manual", seed=8, output_prefix="workspace-1/character_master")
            batch = store.enqueue_batch(project_id="workspace-1", run_id="run-1",
                idempotency_key="review-bytes", workflow_id=compiled["workflow_id"],
                workflow_version=compiled["workflow_version"], asset_role="character_master",
                prompt=compiled["prompt"], settings={"director_review_required": True},
                candidates=compiled["candidates"][:1])
            job = store.next_queued()
            prompt_id = store.reserve_prompt_id(job["job_id"])
            store.transition(job["job_id"], "running", prompt_id=prompt_id)
            store.transition(job["job_id"], "completed", output_asset_id="pa-0123456789abcdef")
            store.record_director_review(project_id="workspace-1", run_id="run-1", job_id=job["job_id"],
                asset_id="pa-0123456789abcdef", decision={"schema_version": 1, "action": "accept",
                    "reason": "ok", "prompt_delta": "", "criteria": [], "confidence": 1,
                    "image_sha256": "0" * 64})
            image = root / "changed.png"
            image.write_bytes(b"new bytes")
            worker = ProductionImageWorker(store, comfy_url="http://127.0.0.1:9",
                output_root=root / "assets", register_output=lambda **_: {},
                resolve_candidate=lambda *_: image, review_candidate=lambda *_: {},
                accept_candidate=lambda _: self.fail("Changed bytes must not be selected."))
            result = worker.review_next_candidate()
            self.assertEqual(result["status"], "held")
            self.assertEqual(store.get_director_review(project_id="workspace-1", job_id=job["job_id"])["resolution_status"], "blocked")
            self.assertEqual(store.unresolved_director_reviews(), [])

    def test_stale_pending_review_cannot_enqueue_retake_after_setup_changes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store = ProductionImageJobStore(root / "image-jobs.sqlite3")
            compiled = compile_image_candidates(workflow_id="z_image_turbo", prompt="Mira portrait.",
                control_mode="assisted_manual", seed=8, output_prefix="workspace-1/character_master")
            batch = store.enqueue_batch(project_id="workspace-1", run_id="run-1",
                idempotency_key="stale-pending-review", workflow_id=compiled["workflow_id"],
                workflow_version=compiled["workflow_version"], asset_role="character_master",
                prompt=compiled["prompt"], settings={"director_review_required": True},
                candidates=compiled["candidates"][:1])
            job = store.next_queued()
            prompt_id = store.reserve_prompt_id(job["job_id"])
            store.transition(job["job_id"], "running", prompt_id=prompt_id)
            store.transition(job["job_id"], "completed", output_asset_id="pa-0123456789abcdef")
            store.record_director_review(project_id="workspace-1", run_id="run-1", job_id=job["job_id"],
                asset_id="pa-0123456789abcdef", decision={"schema_version": 1, "action": "retake",
                    "reason": "wrong coat", "prompt_delta": "red coat", "criteria": [], "confidence": 1})
            worker = ProductionImageWorker(store, comfy_url="http://127.0.0.1:9",
                output_root=root / "assets", register_output=lambda **_: {},
                resolve_candidate=lambda *_: Path(temporary) / "unused.png",
                review_candidate=lambda *_: self.fail("Saved decisions do not need a new provider call."),
                accept_candidate=lambda _: self.fail("Stale review must not select a candidate."),
                validate_candidate=lambda _job: "The saved setup changed.",
                enqueue_retake=lambda *_: self.fail("Stale review must not enqueue another render."))
            result = worker.review_next_candidate()
            self.assertEqual(result["status"], "blocked")
            saved = store.get_director_review(project_id="workspace-1", job_id=job["job_id"])
            self.assertEqual(saved["resolution_status"], "blocked")
            self.assertEqual(saved["error"]["code"], "automated_image_inputs_stale")

    def test_reviewed_candidate_with_existing_master_is_resolved_as_alternate(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store = ProductionImageJobStore(root / "image-jobs.sqlite3")
            compiled = compile_image_candidates(workflow_id="z_image_turbo", prompt="Mira portrait.",
                control_mode="assisted_manual", seed=8, output_prefix="workspace-1/character_master")
            store.enqueue_batch(project_id="workspace-1", run_id="run-1",
                idempotency_key="review-alternate", workflow_id=compiled["workflow_id"],
                workflow_version=compiled["workflow_version"], asset_role="character_master",
                prompt=compiled["prompt"], settings={"director_review_required": True},
                candidates=compiled["candidates"][:1])
            job = store.next_queued()
            prompt_id = store.reserve_prompt_id(job["job_id"])
            store.transition(job["job_id"], "running", prompt_id=prompt_id)
            store.transition(job["job_id"], "completed", output_asset_id="pa-0123456789abcdef")
            image = root / "candidate.png"
            image.write_bytes(b"reviewed bytes")
            store.record_director_review(project_id="workspace-1", run_id="run-1", job_id=job["job_id"],
                asset_id="pa-0123456789abcdef", decision={"schema_version": 1, "action": "accept",
                    "reason": "ok", "prompt_delta": "", "criteria": [], "confidence": 1,
                    "image_sha256": hashlib.sha256(image.read_bytes()).hexdigest()})
            worker = ProductionImageWorker(store, comfy_url="http://127.0.0.1:9",
                output_root=root / "assets", register_output=lambda **_: {},
                resolve_candidate=lambda *_: image, review_candidate=lambda *_: {},
                accept_candidate=lambda _: {"alternate": True})
            result = worker.review_next_candidate()
            self.assertEqual(result["status"], "alternate")
            self.assertEqual(store.get_director_review(project_id="workspace-1", job_id=job["job_id"])["resolution_status"], "rejected")
            self.assertEqual(store.unresolved_director_reviews(), [])

    def test_story_image_stage_requires_unchecked_assisted_manual_step(self):
        def state(mode="assisted_manual", enabled=False, world_enabled=False, frame_enabled=False):
            return {"setup": {"mode": mode, "automate_steps": {
                "character_images": enabled, "world_images": world_enabled,
                "character_voice": False, "frame_images": frame_enabled, "video": False}}}
        _require_manual_image_stage(state(), "character_master")
        _require_manual_image_stage(state(), "world_master")
        with self.assertRaisesRegex(LedgerConflict, "use its automated image stage"):
            _require_manual_image_stage(state(enabled=True), "character_master")
        with self.assertRaisesRegex(LedgerConflict, "selected for automation"):
            _require_manual_image_stage(state(world_enabled=True), "world_master")
        _require_manual_image_stage(state(), "first_frame")
        _require_manual_image_stage(state(), "last_frame")
        with self.assertRaisesRegex(LedgerConflict, "selected for automation"):
            _require_manual_image_stage(state(frame_enabled=True), "last_frame")
        with self.assertRaisesRegex(LedgerConflict, "skipped in Fully automated"):
            _require_manual_image_stage(state(mode="fully_automated"), "character_master")
        with self.assertRaisesRegex(LedgerConflict, "Save Automation"):
            _require_manual_image_stage({"setup": None}, "character_master")

    def test_story_image_submission_rejects_manual_click_for_automated_step_before_enqueue(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "data"
            app = create_app(data_root=root)
            payload = {"workflow_id": "z_image_turbo", "prompt": "Mira portrait",
                "control_mode": "assisted_manual", "seed": 42, "output_prefix": "workspace-1/character_master",
                "workspace_id": "workspace-1", "idempotency_key": "story-image-test",
                "asset_role": "character_master", "screenplay_revision_id": "screenplay-1",
                "target_record_id": "character-mira"}
            body = json.dumps(payload).encode()
            response = []
            environ = {"REQUEST_METHOD": "POST", "PATH_INFO": "/api/images/jobs", "QUERY_STRING": "",
                "CONTENT_TYPE": "application/json", "CONTENT_LENGTH": str(len(body)), "wsgi.input": io.BytesIO(body)}
            setup = {"workspace_id": "workspace-1", "screenplay_revision_id": "screenplay-1", "setup": {
                "mode": "assisted_manual", "automate_steps": {"character_images": True,
                    "character_voice": False, "world_images": False, "frame_images": False, "video": False}}}
            with patch("story_builder.isolated_server._image_lineage", return_value={
                    "screenplay_revision_id": "screenplay-1", "target_type": "character",
                    "target_record_id": "character-mira"}), \
                 patch("story_builder.services.production_setup.ProductionSetup.get", return_value=setup):
                result = b"".join(app(environ, lambda status, headers: response.append(status)))
            self.assertEqual(response[0], "409 Conflict")
            self.assertIn("selected for automation", json.loads(result)["error"]["message"])
            self.assertIsNone(ProductionImageJobStore(root / "services/production/image-jobs.sqlite3").find_idempotent_batch(
                project_id="workspace-1", idempotency_key="story-image-test"))

    def test_story_frame_submission_rejects_automated_stage_before_enqueue(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "data"
            app = create_app(data_root=root)
            payload = {"workflow_id": "z_image_turbo", "prompt": "Platform at dusk",
                "control_mode": "assisted_manual", "seed": 42, "output_prefix": "workspace-1/first_frame",
                "workspace_id": "workspace-1", "idempotency_key": "story-frame-test",
                "asset_role": "first_frame", "screenplay_revision_id": "screenplay-1",
                "scene_number": 1, "shot_number": 1, "clip_id": "story-clip"}
            body = json.dumps(payload).encode()
            response = []
            environ = {"REQUEST_METHOD": "POST", "PATH_INFO": "/api/images/jobs", "QUERY_STRING": "",
                "CONTENT_TYPE": "application/json", "CONTENT_LENGTH": str(len(body)), "wsgi.input": io.BytesIO(body)}
            setup = {"workspace_id": "workspace-1", "screenplay_revision_id": "screenplay-1", "setup": {
                "mode": "assisted_manual", "automate_steps": {"character_images": False,
                    "character_voice": False, "world_images": False, "frame_images": True, "video": False}}}
            with patch("story_builder.isolated_server._image_lineage", return_value={
                    "screenplay_revision_id": "screenplay-1", "target_type": "clip", "clip_id": "story-clip",
                    "scene_number": 1, "shot_number": 1}), \
                 patch("story_builder.services.production_setup.ProductionSetup.get", return_value=setup):
                result = b"".join(app(environ, lambda status, headers: response.append(status)))
            self.assertEqual(response[0], "409 Conflict")
            self.assertIn("selected for automation", json.loads(result)["error"]["message"])
            self.assertIsNone(ProductionImageJobStore(root / "services/production/image-jobs.sqlite3").find_idempotent_batch(
                project_id="workspace-1", idempotency_key="story-frame-test"))

    def test_story_frame_submission_rejects_a_skipped_shot_before_enqueue(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "data"
            app = create_app(data_root=root)
            payload = {"workflow_id": "z_image_turbo", "prompt": "Platform at dusk",
                "control_mode": "assisted_manual", "seed": 42, "output_prefix": "workspace-1/first_frame",
                "workspace_id": "workspace-1", "idempotency_key": "skipped-frame-test",
                "asset_role": "first_frame", "screenplay_revision_id": "screenplay-1",
                "scene_number": 1, "shot_number": 1, "clip_id": "story-clip"}
            body = json.dumps(payload).encode()
            response = []
            environ = {"REQUEST_METHOD": "POST", "PATH_INFO": "/api/images/jobs", "QUERY_STRING": "",
                "CONTENT_TYPE": "application/json", "CONTENT_LENGTH": str(len(body)), "wsgi.input": io.BytesIO(body)}
            setup = {"workspace_id": "workspace-1", "screenplay_revision_id": "screenplay-1", "setup": {
                "mode": "assisted_manual", "automate_steps": {"character_images": False,
                    "character_voice": False, "world_images": False, "frame_images": False, "video": False}}}
            with patch("story_builder.isolated_server._image_lineage", return_value={
                    "screenplay_revision_id": "screenplay-1", "target_type": "clip", "clip_id": "story-clip",
                    "scene_number": 1, "shot_number": 1}), \
                 patch("story_builder.services.production_setup.ProductionSetup.get", return_value=setup), \
                 patch("story_builder.services.production_setup.ProductionSetup.list_assisted_stage_skips", return_value={"skipped": []}), \
                 patch("story_builder.services.production_setup.ProductionSetup.frame_preparation_is_skipped", return_value=True):
                result = b"".join(app(environ, lambda status, headers: response.append(status)))
            self.assertEqual(response[0], "409 Conflict")
            self.assertIn("Frame preparation is skipped", json.loads(result)["error"]["message"])
            self.assertIsNone(ProductionImageJobStore(root / "services/production/image-jobs.sqlite3").find_idempotent_batch(
                project_id="workspace-1", idempotency_key="skipped-frame-test"))

    def test_image_lineage_requires_current_accepted_character_in_screenplay_graph(self):
        class Story:
            def get_screenplay_revision(self, workspace_id, screenplay_id):
                return {"accepted": True, "source_revision_id": "rev-1", "graph_snapshot_id": "graph-1"}
            def get_story_graph(self, *, workspace_id, snapshot_id):
                return {"status": "complete", "records": [
                    {"record_id": "char-1", "kind": "entity", "type": "character", "name": "Mira"},
                    {"record_id": "event-1", "kind": "event", "type": "event", "name": "Arrives"}]}
        lineage = _image_lineage(Story(), "workspace-1", {
            "screenplay_revision_id": "sp-1", "target_record_id": "char-1", "asset_role": "character_master"})
        self.assertEqual(lineage, {"screenplay_revision_id": "sp-1", "source_revision_id": "rev-1",
            "graph_snapshot_id": "graph-1", "target_type": "character",
            "target_record_id": "char-1", "target_name": "Mira"})
        with self.assertRaisesRegex(LedgerConflict, "not a character"):
            _image_lineage(Story(), "workspace-1", {
                "screenplay_revision_id": "sp-1", "target_record_id": "event-1", "asset_role": "character_master"})

    def test_world_master_lineage_requires_canonical_location_entity(self):
        class Story:
            def get_screenplay_revision(self, workspace_id, screenplay_id):
                return {"accepted": True, "source_revision_id": "rev-1", "graph_snapshot_id": "graph-1"}
            def get_story_graph(self, *, workspace_id, snapshot_id):
                return {"status": "complete", "records": [
                    {"record_id": "place-1", "kind": "entity", "type": "location", "name": "Old station"},
                    {"record_id": "org-1", "kind": "entity", "type": "organization", "name": "Railway"}]}
        payload = {"screenplay_revision_id": "sp-1", "target_record_id": "place-1", "asset_role": "world_master"}
        lineage = _image_lineage(Story(), "workspace-1", payload)
        self.assertEqual(lineage["target_type"], "location")
        self.assertEqual(lineage["target_name"], "Old station")
        with self.assertRaisesRegex(LedgerConflict, "not a location"):
            _image_lineage(Story(), "workspace-1", {**payload, "target_record_id": "org-1"})
        with self.assertRaisesRegex(LedgerConflict, "not a location"):
            _image_lineage(Story(), "workspace-1", {**payload, "target_record_id": "legacy-free-text"})

    def test_frame_image_lineage_uses_existing_revision_scoped_clip_identity(self):
        from story_builder.services.isolated_video_jobs import story_clip_id

        class Story:
            def get_screenplay_revision(self, workspace_id, screenplay_id):
                return {"accepted": True, "source_revision_id": "source-1", "graph_snapshot_id": "graph-1",
                    "screenplay": {"scenes": [{"scene_number": 1, "shots": [{"shot_number": 1}, {"shot_number": 2}]}]}}

        clip = story_clip_id("workspace-1", "sp-1", 1, 2)
        payload = {"screenplay_revision_id": "sp-1", "scene_number": 1, "shot_number": 2,
            "clip_id": clip, "asset_role": "first_frame"}
        lineage = _image_lineage(Story(), "workspace-1", payload)
        self.assertEqual(lineage, {"screenplay_revision_id": "sp-1", "source_revision_id": "source-1",
            "graph_snapshot_id": "graph-1", "target_type": "clip", "scene_number": 1,
            "shot_number": 2, "clip_id": clip})
        with self.assertRaisesRegex(LedgerConflict, "not a shot"):
            _image_lineage(Story(), "workspace-1", {**payload, "shot_number": 3,
                "clip_id": story_clip_id("workspace-1", "sp-1", 1, 3)})
        with self.assertRaisesRegex(LedgerConflict, "not a shot"):
            _image_lineage(Story(), "workspace-1", {**payload, "clip_id": "story-forged"})

    def test_compiles_four_assisted_manual_candidates_from_bundled_workflows(self):
        for workflow_id, prompt_node, sampler_node in (
            ("qwen_image_2512", "227", "230"),
            ("z_image_turbo", "45", "44"),
        ):
            result = compile_image_candidates(workflow_id=workflow_id,
                prompt="Rain on an empty stage.", control_mode="assisted_manual",
                seed=41, output_prefix="story/character")
            self.assertEqual(result["initial_candidate_count"], 4)
            self.assertEqual([item["seed"] for item in result["candidates"]], [41, 42, 43, 44])
            self.assertEqual(result["candidates"][0]["graph"][prompt_node]["inputs"]["text"],
                "Rain on an empty stage.")
            self.assertEqual(result["candidates"][0]["graph"][sampler_node]["inputs"]["seed"], 41)

    def test_owner_candidate_counts_compile_and_persist_with_seed_bounds(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = ProductionImageJobStore(Path(temporary) / "jobs.sqlite3")
            for count in (1, 4, 8):
                result = compile_image_candidates(workflow_id="z_image_turbo", prompt="Portrait",
                    control_mode="assisted_manual", seed=42, output_prefix="characters",
                    initial_candidate_count=count)
                self.assertEqual([item["seed"] for item in result["candidates"]], list(range(42, 42+count)))
                batch = store.enqueue_batch(project_id="workspace-1", run_id=f"run-{count}",
                    idempotency_key=f"count-{count}", workflow_id=result["workflow_id"],
                    workflow_version=result["workflow_version"], asset_role="character_master",
                    prompt=result["prompt"], settings=result["settings"], candidates=result["candidates"])
                self.assertEqual(len(batch["jobs"]), count)
            for count, seed in ((9, 42), (8, 4294967295)):
                with self.assertRaises(ImageWorkflowError):
                    compile_image_candidates(workflow_id="z_image_turbo", prompt="Portrait",
                        control_mode="assisted_manual", seed=seed, output_prefix="characters",
                        initial_candidate_count=count)

    def test_multi_angle_world_compiles_separately_labelled_four_or_eight_views(self):
        for count, labels in ((2, ["Left", "Right"]), (3, ["Left", "Right", "Back"]), (4, ["Front", "Right", "Back", "Left"]),
                              (8, ["Front", "Front-right", "Right", "Back-right",
                                   "Back", "Back-left", "Left", "Front-left"])):
            result = compile_image_candidates(workflow_id="qwen_image_multi_angle_2511",
                prompt="An old railway station.", control_mode="assisted_manual", seed=20,
                output_prefix="world/views", source_images=["base.png"], world_view_count=count)
            self.assertEqual(result["initial_candidate_count"], count)
            self.assertEqual([item["world_view"]["label"] for item in result["candidates"]], labels)
            for item, label in zip(result["candidates"], labels):
                graph = item["graph"]
                self.assertEqual(set(graph["41"]["inputs"]), {"image"})
                self.assertEqual(graph["68"]["inputs"]["image1"], ["41", 0])
                self.assertTrue(result["settings"]["multi_angle_batch"])
                self.assertEqual(graph, result["candidates"][0]["graph"])
                self.assertEqual(item["seed"], 20)
                self.assertEqual(graph["68"]["inputs"]["prompt"], ["112", 0])
                self.assertEqual(graph["112"]["inputs"]["prompt2"], "An old railway station.")
                cameras = [graph[str(108+i) if i < 4 else str(200+i)]["inputs"] for i in range(count)]
                self.assertEqual([camera["horizontal_angle"] for camera in cameras],
                    [view["azimuth"] for view in result["settings"]["world_views"]])
                self.assertTrue(all(camera["vertical_angle"] == 0 and camera["zoom"] == 1 for camera in cameras))
                final_list = "90" if count <= 4 else "208"
                self.assertEqual(graph["112"]["inputs"]["prompt1"], [final_list, 1])
                if count < 4:
                    self.assertEqual(graph["90"]["inputs"][f"prompt_{count+1}"], "")
                    self.assertNotIn(str(108+count), graph)
                if count == 8:
                    self.assertEqual(graph["208"]["inputs"]["optional_prompt_list"], ["90", 0])
                self.assertEqual(graph["116"]["class_type"], "SaveImage")
                self.assertTrue(graph["116"]["inputs"]["filename_prefix"].endswith("/directional-views"))
        with self.assertRaises(ImageWorkflowError):
            compile_image_candidates(workflow_id="qwen_image_multi_angle_2511",
                prompt="Station", control_mode="assisted_manual", seed=1,
                output_prefix="world/views", source_images=["base.png", "extra.png"])
        with self.assertRaises(ImageWorkflowError):
            compile_image_candidates(workflow_id="qwen_image_multi_angle_2511",
                prompt="Station", control_mode="assisted_manual", seed=1,
                output_prefix="world/views", source_images=["base.png"], world_view_count=6)

    def test_character_views_receive_opposite_explicit_facing_instructions(self):
        for count in (2, 3, 4, 8):
            result = compile_image_candidates(workflow_id="qwen_image_multi_angle_2511",
                prompt="Preserve identity and clothing.", control_mode="assisted_manual", seed=42,
                output_prefix="characters/views", source_images=["master.png"],
                world_view_count=count, asset_role="character_view")
            graph = result["candidates"][0]["graph"]
            instructions = {item["world_view"]["label"]: item["direction_instruction"] for item in result["candidates"]}
            self.assertIn("RIGHT edge", instructions["Left"])
            self.assertIn("LEFT edge", instructions["Right"])
            for i, item in enumerate(result["candidates"]):
                concat = graph[str(300+i)]["inputs"]
                camera_id = str(108+i) if i < 4 else str(200+i)
                self.assertEqual(concat["prompt1"], [camera_id, 0])
                self.assertEqual(concat["prompt2"], item["direction_instruction"])
                list_id, slot = ("90", i+1) if i < 4 else ("208", i-3)
                self.assertEqual(graph[list_id]["inputs"][f"prompt_{slot}"], [str(300+i), 0])

    def test_multi_angle_rejects_shared_fixed_view_instruction(self):
        with self.assertRaisesRegex(ImageWorkflowError, "fixed camera view"):
            compile_image_candidates(workflow_id="qwen_image_multi_angle_2511",
                prompt="Edit the supplied character into a side view.",
                control_mode="assisted_manual", seed=42, output_prefix="views",
                source_images=["master.png"], world_view_count=2)

    def test_image_job_store_allows_eight_candidates_and_rejects_nine(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = ProductionImageJobStore(Path(temporary) / "jobs.sqlite3")
            compiled = compile_image_candidates(workflow_id="qwen_image_multi_angle_2511",
                prompt="Station", control_mode="assisted_manual", seed=1,
                output_prefix="world/views", source_images=["base.png"], world_view_count=8)
            result = store.enqueue_batch(project_id="workspace-1", run_id="run-1",
                idempotency_key="eight-views", workflow_id=compiled["workflow_id"],
                workflow_version=compiled["workflow_version"], asset_role="world_view",
                prompt=compiled["prompt"], settings=compiled["settings"],
                candidates=compiled["candidates"])
            self.assertEqual(len(result["jobs"]), 8)
            with self.assertRaisesRegex(ValueError, "1–8 candidates"):
                store.enqueue_batch(project_id="workspace-1", run_id="run-1",
                    idempotency_key="wrong-workflow-cap", workflow_id="z_image_turbo",
                    workflow_version="1", asset_role="world_master", prompt="Station",
                    settings={}, candidates=compiled["candidates"] + [compiled["candidates"][0]])

    def test_image_job_store_persists_prompt_workflow_knowledge_reference(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = ProductionImageJobStore(Path(temporary) / "jobs.sqlite3")
            compiled = compile_image_candidates(workflow_id="z_image_turbo", prompt="Mira portrait",
                control_mode="assisted_manual", seed=12, output_prefix="workspace-1/character")
            reference = {"knowledge_id": "knowledge-1", "guidance_version": 3,
                "workflow_sha256": "a" * 64}
            compiled["settings"]["prompt_knowledge_ref"] = reference
            result = store.enqueue_batch(project_id="workspace-1", run_id="run-1",
                idempotency_key="image-prompt-provenance", workflow_id=compiled["workflow_id"],
                workflow_version=compiled["workflow_version"], asset_role="character_master",
                prompt=compiled["prompt"], settings=compiled["settings"],
                candidates=compiled["candidates"][:1])
            persisted = store.list_batch(project_id="workspace-1", batch_id=result["batch_id"])
            self.assertEqual(persisted["jobs"][0]["settings"]["prompt_knowledge_ref"], reference)

    def test_image_prompt_product_limit_counts_unicode_codepoints(self):
        accepted = "a" * 6998 + "🎬"
        result = compile_image_candidates(workflow_id="z_image_turbo", prompt=accepted,
            control_mode="assisted_manual", seed=1, output_prefix="story/frame")
        self.assertEqual(len(result["prompt"]), 6999)
        with self.assertRaisesRegex(ImageWorkflowError, "1–6,999 Unicode code points"):
            compile_image_candidates(workflow_id="z_image_turbo", prompt=accepted + "x",
                control_mode="assisted_manual", seed=1, output_prefix="story/frame")

    def test_only_exact_retry_path_can_compile_previously_accepted_legacy_prompt(self):
        legacy_prompt = "a" * 7000
        with self.assertRaises(ImageWorkflowError):
            compile_image_candidates(workflow_id="z_image_turbo", prompt=legacy_prompt,
                control_mode="assisted_manual", seed=1, output_prefix="story/frame")
        result = compile_image_candidates(workflow_id="z_image_turbo", prompt=legacy_prompt,
            control_mode="assisted_manual", seed=1, output_prefix="story/frame",
            allow_legacy_prompt_limit=True)
        self.assertEqual(result["prompt"], legacy_prompt)
        with self.assertRaises(ImageWorkflowError):
            compile_image_candidates(workflow_id="z_image_turbo", prompt="a" * 20001,
                control_mode="assisted_manual", seed=1, output_prefix="story/frame",
                allow_legacy_prompt_limit=True)

    def test_fully_automated_skips_image_generation_and_references(self):
        self.assertEqual(image_workflow_catalog(object_info={})["generation_policy"]["fully_automated"],
            {"image_generation": "skipped"})
        with self.assertRaises(ImageWorkflowError):
            generation_policy("fully_automated")

    def test_edit_workflow_requires_one_to_three_staged_images(self):
        with self.assertRaises(ImageWorkflowError):
            compile_image_candidates(workflow_id="qwen_image_edit_2511", prompt="Edit image",
                control_mode="assisted_manual", seed=1, output_prefix="edit/one")
        result = compile_image_candidates(workflow_id="qwen_image_edit_2511", prompt="Change the coat.",
            control_mode="assisted_manual", seed=1, output_prefix="edit/one", source_images=["in.png"])
        graph = result["candidates"][0]["graph"]
        self.assertEqual(graph["78"]["inputs"]["image"], "in.png")
        self.assertNotIn("120", graph)
        self.assertNotIn("121", graph)

    def test_image_batch_is_durable_and_idempotent(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "image-jobs.sqlite3"
            compiled = compile_image_candidates(workflow_id="z_image_turbo", prompt="A lighthouse.",
                control_mode="assisted_manual", seed=71, output_prefix="story/world")
            request = {"project_id": "workspace-1", "run_id": "run-1",
                "idempotency_key": "world-master-1", "workflow_id": compiled["workflow_id"],
                "workflow_version": compiled["workflow_version"], "asset_role": "world_master",
                "prompt": compiled["prompt"], "settings": compiled["settings"],
                "candidates": compiled["candidates"]}
            first = ProductionImageJobStore(path).enqueue_batch(**request)
            replay = ProductionImageJobStore(path).enqueue_batch(**request)
            self.assertFalse(first["reused"])
            self.assertTrue(replay["reused"])
            self.assertEqual([job["status"] for job in replay["jobs"]], ["queued"] * 4)
            with self.assertRaises(LedgerConflict):
                ProductionImageJobStore(path).enqueue_batch(**{**request, "prompt": "different"})
            durable = ProductionImageJobStore(path).list_batch(project_id="workspace-1", batch_id=first["batch_id"])
            self.assertEqual(len(durable["jobs"]), 4)
            self.assertEqual(durable["jobs"][0]["prompt"], "A lighthouse.")

    def test_restart_requeues_only_candidates_claimed_before_remote_submit(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = ProductionImageJobStore(Path(temporary) / "jobs.sqlite3")
            compiled = compile_image_candidates(workflow_id="z_image_turbo", prompt="A lighthouse.",
                control_mode="assisted_manual", seed=71, output_prefix="story/world")
            batch = store.enqueue_batch(project_id="workspace-1", run_id="run-1",
                idempotency_key="restart-test", workflow_id=compiled["workflow_id"],
                workflow_version=compiled["workflow_version"], asset_role="world_master",
                prompt=compiled["prompt"], settings=compiled["settings"], candidates=compiled["candidates"])
            store.next_queued()
            recovered = store.reconcile_after_restart()
            self.assertEqual(recovered, {"requeued_unsubmitted": 1, "held_for_reconciliation": 0})
            self.assertEqual([job["status"] for job in store.list_batch(
                project_id="workspace-1", batch_id=batch["batch_id"])["jobs"]], ["queued"] * 4)

    def test_image_job_store_rejects_path_segments(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = ProductionImageJobStore(Path(temporary) / "jobs.sqlite3")
            compiled = compile_image_candidates(workflow_id="z_image_turbo", prompt="A lighthouse.",
                control_mode="assisted_manual", seed=71, output_prefix="story/world")
            with self.assertRaisesRegex(ValueError, "safe path-free"):
                store.enqueue_batch(project_id="../../escaped", run_id="run-1",
                    idempotency_key="unsafe", workflow_id=compiled["workflow_id"],
                    workflow_version=compiled["workflow_version"], asset_role="world_master",
                    prompt=compiled["prompt"], settings=compiled["settings"], candidates=compiled["candidates"])

    def test_worker_checks_project_path_before_collecting_outputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            worker = ProductionImageWorker(ProductionImageJobStore(Path(temporary) / "jobs.sqlite3"),
                comfy_url="http://127.0.0.1:3008", output_root=Path(temporary) / "assets",
                register_output=lambda **_kwargs: {})
            with self.assertRaisesRegex(ValueError, "safe path-free"):
                worker._collect_completed({"project_id": "../../escaped"}, "prompt", {})

    def test_worker_rejects_project_output_symlink_escape_before_collecting(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            assets = root / "assets"
            outside = root / "outside"
            assets.mkdir()
            outside.mkdir()
            (assets / "workspace-1").symlink_to(outside, target_is_directory=True)
            worker = ProductionImageWorker(ProductionImageJobStore(root / "jobs.sqlite3"),
                comfy_url="http://127.0.0.1:3008", output_root=assets,
                register_output=lambda **_kwargs: {})
            with patch("story_builder.services.production_image_worker.collect_outputs") as collect:
                with self.assertRaisesRegex(ValueError, "escaped the project output root"):
                    worker._collect_completed({"project_id": "workspace-1", "job_id": "job-1"},
                        "prompt", {})
                collect.assert_not_called()

    def test_smoke_evidence_storage_failure_does_not_reverse_completed_image_job(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output_root = root / "assets"
            image_dir = output_root / "workspace-1" / "production" / "image_jobs" / "job-1"
            image_dir.mkdir(parents=True)
            (image_dir / "candidate.png").write_bytes(b"rendered image")
            store = Mock()
            worker = ProductionImageWorker(store, comfy_url="http://127.0.0.1:3008",
                output_root=output_root, register_output=lambda **_kwargs: {"asset_id": "asset-1"})
            worker.release_idle = lambda **_kwargs: None
            job = {"project_id": "workspace-1", "job_id": "job-1", "batch_id": "batch-1",
                "run_id": "run-1", "workflow_id": "z_image_turbo", "workflow_version": "1",
                "asset_role": "character_candidate", "prompt": "A person.", "seed": 42,
                "candidate_index": 1, "graph": {},
                "settings": {"workflow_template_sha256": "a" * 64}}
            with patch("story_builder.services.production_image_worker.collect_outputs",
                       return_value=[{"kind": "image", "relative_path": "candidate.png"}]), \
                 patch("story_builder.services.production_image_worker.record_successful_image_smoke",
                       side_effect=OSError("smoke storage unavailable")):
                result = worker._collect_completed(job, "prompt-1", {})

            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["asset_id"], "asset-1")

    def test_workflow_capability_fails_closed_without_smoke_and_live_nodes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for spec in SPECS.values():
                for folder, filename in spec["models"].values():
                    model = root / "ComfyUI" / "models" / folder / filename
                    model.parent.mkdir(parents=True, exist_ok=True)
                    model.touch()
            catalog = image_workflow_catalog(comfy_root=root / "ComfyUI",
                workflow_root=Path(__file__).resolve().parents[1] / "workflows" / "api",
                smoke_root=root / "smokes", object_info={})
        self.assertTrue(all(not row["available"] for row in catalog["workflows"]))

    def test_manual_readiness_precedes_smoke_and_successful_run_unlocks_automation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for spec in SPECS.values():
                for folder, filename in spec["models"].values():
                    model = root / "ComfyUI" / "models" / folder / filename
                    model.parent.mkdir(parents=True, exist_ok=True)
                    model.touch()
            graph_root = Path(__file__).resolve().parents[1] / "workflows" / "api"
            live_nodes = {node: {} for spec in SPECS.values() for node in spec["required_nodes"]}
            kontext = json.loads((graph_root / SPECS['flux_kontext_dev']['graph']).read_text())
            for node in kontext.values():
                live_nodes[node['class_type']] = {'input': {'required': {
                    field: [[value]] if isinstance(value,str) else ['ANY']
                    for field,value in node['inputs'].items()}}}
            catalog = image_workflow_catalog(comfy_root=root / "ComfyUI",
                workflow_root=graph_root, smoke_root=root / "smokes", object_info=live_nodes)
            self.assertTrue(all(row["available"] for row in catalog["workflows"]))
            self.assertTrue(all(not row["automation_available"] for row in catalog["workflows"]))
            row = next(item for item in catalog["workflows"] if item["workflow_id"] == "z_image_turbo")
            self.assertTrue(record_successful_image_smoke(smoke_root=root / "smokes",
                workflow_id=row["workflow_id"], workflow_version=row["version"],
                workflow_sha256=row["workflow_sha256"], output_sha256="a" * 64,
                job_id="vibe-job-1"))
            catalog = image_workflow_catalog(comfy_root=root / "ComfyUI",
                workflow_root=graph_root, smoke_root=root / "smokes", object_info=live_nodes)
            row = next(item for item in catalog["workflows"] if item["workflow_id"] == "z_image_turbo")
            self.assertTrue(row["available"])
            self.assertTrue(row["automation_available"])
            self.assertEqual(row["live_smoke"]["evidence"]["job_id"], "vibe-job-1")

    def test_validation_route_returns_compiled_candidate_graph(self):
        with tempfile.TemporaryDirectory() as temporary:
            app = create_app(data_root=Path(temporary) / "data")
            payload = {"workflow_id": "z_image_turbo", "prompt": "A red kite above a city.",
                "control_mode": "assisted_manual", "seed": 8, "output_prefix": "isolated/image"}
            body = json.dumps(payload).encode()
            response = []
            environ = {"REQUEST_METHOD": "POST", "PATH_INFO": "/api/images/validations",
                "QUERY_STRING": "", "CONTENT_TYPE": "application/json",
                "CONTENT_LENGTH": str(len(body)), "wsgi.input": io.BytesIO(body)}
            result = b"".join(app(environ, lambda status, headers: response.append(status)))
        self.assertEqual(response[0], "200 OK")
        compiled = json.loads(result)
        self.assertEqual(compiled["initial_candidate_count"], 4)
        self.assertEqual(compiled["candidates"][0]["graph"]["45"]["inputs"]["text"], payload["prompt"])

    def test_edit_submission_rejects_client_supplied_comfy_filenames(self):
        with tempfile.TemporaryDirectory() as temporary:
            app = create_app(data_root=Path(temporary) / "data")
            payload = {"workflow_id": "qwen_image_edit_2511", "prompt": "Change the coat.",
                "control_mode": "assisted_manual", "seed": 8, "output_prefix": "isolated/image",
                "source_images": ["reference.png"], "workspace_id": "workspace-1",
                "idempotency_key": "request-1"}
            body = json.dumps(payload).encode()
            response = []
            environ = {"REQUEST_METHOD": "POST", "PATH_INFO": "/api/images/jobs",
                "QUERY_STRING": "", "CONTENT_TYPE": "application/json",
                "CONTENT_LENGTH": str(len(body)), "wsgi.input": io.BytesIO(body)}
            result = b"".join(app(environ, lambda status, headers: response.append(status)))
        self.assertEqual(response[0], "400 Bad Request")
        self.assertIn("asset IDs", json.loads(result)["error"]["message"])

    def test_edit_validation_compiles_workspace_asset_ids_as_safe_placeholders(self):
        reference = {"asset_id": "image_0123456789abcdef", "sha256": "a" * 64}
        with tempfile.TemporaryDirectory() as temporary, patch(
                "story_builder.isolated_server.validate_image_references", return_value=[reference]) as validate:
            app = create_app(data_root=Path(temporary) / "data")
            payload = {"workflow_id": "qwen_image_edit_2511", "prompt": "Keep the face; change the coat.",
                "control_mode": "assisted_manual", "seed": 8, "output_prefix": "isolated/image",
                "workspace_id": "workspace-1", "source_references": [reference]}
            body = json.dumps(payload).encode()
            response = []
            environ = {"REQUEST_METHOD": "POST", "PATH_INFO": "/api/images/validations",
                "QUERY_STRING": "", "CONTENT_TYPE": "application/json",
                "CONTENT_LENGTH": str(len(body)), "wsgi.input": io.BytesIO(body)}
            result = b"".join(app(environ, lambda status, headers: response.append(status)))
        self.assertEqual(response[0], "200 OK")
        compiled = json.loads(result)
        self.assertEqual(compiled["source_references"], [reference])
        self.assertEqual(compiled["candidates"][0]["graph"]["78"]["inputs"]["image"], "ref-1.png")
        validate.assert_called_once()

    def test_edit_retry_replays_frozen_references_when_live_assets_are_unavailable(self):
        reference = {"asset_id": "image_0123456789abcdef", "sha256": "a" * 64}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "data"
            compiled = compile_image_candidates(workflow_id="qwen_image_edit_2511",
                prompt="Keep the person; change the coat.", control_mode="assisted_manual", seed=8,
                output_prefix="workspace-1/character_master", source_images=["ref-1.png"])
            compiled["settings"]["image_references"] = [reference]
            compiled["settings"]["style_selection"] = {"snapshot_id": "style-old"}
            store = ProductionImageJobStore(root / "services/production/image-jobs.sqlite3")
            store.enqueue_batch(project_id="workspace-1", run_id="run-existing",
                idempotency_key="edit-retry", workflow_id=compiled["workflow_id"],
                workflow_version=compiled["workflow_version"], asset_role="character_master",
                prompt=compiled["prompt"], settings=compiled["settings"], candidates=compiled["candidates"])
            app = create_app(data_root=root, worker_status_provider=lambda: {"available": False})
            payload = {"workflow_id": "qwen_image_edit_2511", "prompt": "Keep the person; change the coat.",
                "control_mode": "assisted_manual", "seed": 8, "output_prefix": "workspace-1/character_master",
                "workspace_id": "workspace-1", "idempotency_key": "edit-retry",
                "asset_role": "character_master", "source_references": [reference]}
            body = json.dumps(payload).encode()
            response = []
            environ = {"REQUEST_METHOD": "POST", "PATH_INFO": "/api/images/jobs", "QUERY_STRING": "",
                "CONTENT_TYPE": "application/json", "CONTENT_LENGTH": str(len(body)), "wsgi.input": io.BytesIO(body)}
            with patch("story_builder.isolated_server.validate_image_references",
                       side_effect=AssertionError("replay must not require live asset resolution")):
                result = b"".join(app(environ, lambda status, headers: response.append(status)))
        self.assertEqual(response[0], "200 OK")
        replay = json.loads(result)
        self.assertTrue(replay["reused"])
        self.assertEqual(replay["jobs"][0]["settings"]["image_references"], [reference])

    def test_image_jobs_reject_path_traversal_and_replay_saved_batch_before_readiness(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "data"
            custom_db = root / "custom/alternate-image-jobs.sqlite3"
            store = ProductionImageJobStore(custom_db)
            compiled = compile_image_candidates(workflow_id="z_image_turbo", prompt="A lighthouse.",
                control_mode="assisted_manual", seed=8, output_prefix="workspace-1/world_master")
            store.enqueue_batch(project_id="workspace-1", run_id="run-existing",
                idempotency_key="retry-key", workflow_id=compiled["workflow_id"],
                workflow_version=compiled["workflow_version"], asset_role="world_master",
                prompt=compiled["prompt"], settings=compiled["settings"], candidates=compiled["candidates"])
            with patch.dict(os.environ, {"VIBE_DIRECTOR_IMAGE_JOBS_DB": str(custom_db)}):
                app = create_app(data_root=root, worker_status_provider=lambda: {"available": False})
            def call(payload):
                body = json.dumps(payload).encode()
                response = []
                environ = {"REQUEST_METHOD": "POST", "PATH_INFO": "/api/images/jobs",
                    "QUERY_STRING": "", "CONTENT_TYPE": "application/json",
                    "CONTENT_LENGTH": str(len(body)), "wsgi.input": io.BytesIO(body)}
                result = b"".join(app(environ, lambda status, headers: response.append(status)))
                return response[0], json.loads(result)
            unsafe_status, _ = call({"workflow_id": "z_image_turbo", "prompt": "x",
                "control_mode": "assisted_manual", "seed": 1, "output_prefix": "x",
                "workspace_id": "../../escaped", "idempotency_key": "unsafe"})
            replay_status, replay = call({"workflow_id": "z_image_turbo", "prompt": "A lighthouse.",
                "control_mode": "assisted_manual", "seed": 8, "output_prefix": "workspace-1/world_master",
                "workspace_id": "workspace-1", "idempotency_key": "retry-key", "asset_role": "world_master"})
        self.assertEqual(unsafe_status, "400 Bad Request")
        self.assertEqual(replay_status, "200 OK")
        self.assertTrue(replay["reused"])

    def test_character_image_retry_uses_frozen_lineage_after_screenplay_changes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "data"
            db = root / "services/production/image-jobs.sqlite3"
            store = ProductionImageJobStore(db)
            lineage = {"screenplay_revision_id": "screenplay-old", "source_revision_id": "source-old",
                "graph_snapshot_id": "graph-old", "target_type": "character",
                "target_record_id": "character-mira", "target_name": "Mira"}
            compiled = compile_image_candidates(workflow_id="z_image_turbo", prompt="Mira portrait",
                control_mode="assisted_manual", seed=42, output_prefix="workspace-1/character_master")
            compiled["settings"]["lineage"] = lineage
            store.enqueue_batch(project_id="workspace-1", run_id="run-existing",
                idempotency_key="character-retry", workflow_id=compiled["workflow_id"],
                workflow_version=compiled["workflow_version"], asset_role="character_master",
                prompt=compiled["prompt"], settings=compiled["settings"], candidates=compiled["candidates"])
            app = create_app(data_root=root, worker_status_provider=lambda: {"available": False})
            payload = {"workflow_id": "z_image_turbo", "prompt": "Mira portrait",
                "control_mode": "assisted_manual", "seed": 42, "output_prefix": "workspace-1/character_master",
                "workspace_id": "workspace-1", "idempotency_key": "character-retry",
                "asset_role": "character_master", "screenplay_revision_id": "screenplay-old",
                "target_record_id": "character-mira"}
            body = json.dumps(payload).encode()
            response = []
            environ = {"REQUEST_METHOD": "POST", "PATH_INFO": "/api/images/jobs", "QUERY_STRING": "",
                "CONTENT_TYPE": "application/json", "CONTENT_LENGTH": str(len(body)), "wsgi.input": io.BytesIO(body)}
            with patch("story_builder.isolated_server._image_lineage", side_effect=AssertionError("must replay frozen lineage")):
                result = b"".join(app(environ, lambda status, headers: response.append(status)))
        self.assertEqual(response[0], "200 OK")
        self.assertTrue(json.loads(result)["reused"])

    def test_world_image_retry_replays_frozen_location_lineage(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "data"
            db = root / "services/production/image-jobs.sqlite3"
            store = ProductionImageJobStore(db)
            lineage = {"screenplay_revision_id": "screenplay-old", "source_revision_id": "source-old",
                "graph_snapshot_id": "graph-old", "target_type": "location",
                "target_record_id": "location-station", "target_name": "Old station"}
            compiled = compile_image_candidates(workflow_id="z_image_turbo", prompt="Old station at dusk",
                control_mode="assisted_manual", seed=42, output_prefix="workspace-1/world_master")
            compiled["settings"]["lineage"] = lineage
            store.enqueue_batch(project_id="workspace-1", run_id="run-existing",
                idempotency_key="world-retry", workflow_id=compiled["workflow_id"],
                workflow_version=compiled["workflow_version"], asset_role="world_master",
                prompt=compiled["prompt"], settings=compiled["settings"], candidates=compiled["candidates"])
            app = create_app(data_root=root, worker_status_provider=lambda: {"available": False})
            payload = {"workflow_id": "z_image_turbo", "prompt": "Old station at dusk",
                "control_mode": "assisted_manual", "seed": 42, "output_prefix": "workspace-1/world_master",
                "workspace_id": "workspace-1", "idempotency_key": "world-retry", "asset_role": "world_master",
                "screenplay_revision_id": "screenplay-old", "target_record_id": "location-station"}
            body = json.dumps(payload).encode()
            response = []
            environ = {"REQUEST_METHOD": "POST", "PATH_INFO": "/api/images/jobs", "QUERY_STRING": "",
                "CONTENT_TYPE": "application/json", "CONTENT_LENGTH": str(len(body)), "wsgi.input": io.BytesIO(body)}
            with patch("story_builder.isolated_server._image_lineage", side_effect=AssertionError("must replay frozen lineage")):
                result = b"".join(app(environ, lambda status, headers: response.append(status)))
        self.assertEqual(response[0], "200 OK")
        self.assertTrue(json.loads(result)["reused"])

    def test_image_jobs_db_override_must_remain_inside_product_data_root(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "data"
            outside = Path(temporary) / "outside.sqlite3"
            with patch.dict(os.environ, {"VIBE_DIRECTOR_IMAGE_JOBS_DB": str(outside)}):
                with self.assertRaisesRegex(ValueError, "must remain under VIBE_DIRECTOR_DATA_DIR"):
                    create_app(data_root=root)

    def test_second_worker_process_cannot_acquire_same_database_lock(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            db = root / "services/production/image-jobs.sqlite3"
            marker = root / "worker-holds-lock"
            script = ("import sys,time\n"
                "from pathlib import Path\n"
                "from story_builder.isolated_image_worker import image_worker_lifetime_lock\n"
                "with image_worker_lifetime_lock(Path(sys.argv[1])):\n"
                " Path(sys.argv[2]).write_text('locked')\n"
                " time.sleep(30)\n")
            worker = subprocess.Popen([sys.executable, "-c", script, str(db), str(marker)],
                cwd=Path(__file__).resolve().parents[2], stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL)
            try:
                deadline = time.monotonic() + 5
                while not marker.exists() and worker.poll() is None and time.monotonic() < deadline:
                    time.sleep(0.02)
                self.assertTrue(marker.exists(), "first worker process did not acquire its lock")
                with self.assertRaisesRegex(RuntimeError, "already owns this job database"):
                    with image_worker_lifetime_lock(db):
                        self.fail("second process acquired the live worker lock")
            finally:
                worker.terminate()
                worker.wait(timeout=5)

    def test_completed_candidate_can_be_selected_only_in_its_workspace(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "data"
            store = ProductionImageJobStore(root / "services/production/image-jobs.sqlite3")
            compiled = compile_image_candidates(workflow_id="z_image_turbo", prompt="Portrait.",
                control_mode="assisted_manual", seed=8, output_prefix="workspace-1/character_master")
            batch = store.enqueue_batch(project_id="workspace-1", run_id="run-1",
                idempotency_key="candidate-select", workflow_id=compiled["workflow_id"],
                workflow_version=compiled["workflow_version"], asset_role="character_master",
                prompt=compiled["prompt"], settings=compiled["settings"], candidates=compiled["candidates"][:1])
            job = store.next_queued()
            prompt_id = store.reserve_prompt_id(job["job_id"])
            store.transition(job["job_id"], "running", prompt_id=prompt_id)
            store.transition(job["job_id"], "completed", output_asset_id="pa-0123456789abcdef")
            app = create_app(data_root=root)
            payload = {"workspace_id": "workspace-1", "asset_role": "character_master"}
            def call(workspace):
                body = json.dumps({**payload, "workspace_id": workspace}).encode()
                response = []
                environ = {"REQUEST_METHOD": "POST", "PATH_INFO": f"/api/images/jobs/{job['job_id']}/accept",
                    "QUERY_STRING": "", "CONTENT_TYPE": "application/json",
                    "CONTENT_LENGTH": str(len(body)), "wsgi.input": io.BytesIO(body)}
                result = b"".join(app(environ, lambda status, headers: response.append(status)))
                return response[0], json.loads(result)
            with patch("story_builder.isolated_server.assign_media_role",
                       return_value={"asset_id": "pa-0123456789abcdef", "roles": ["image_candidate", "character_master"]}):
                wrong_status, _ = call("workspace-2")
                accepted_status, accepted = call("workspace-1")
        self.assertEqual(wrong_status, "404 Not Found")
        self.assertEqual(accepted_status, "200 OK")
        self.assertTrue(accepted["selected"])

    def test_skipped_frame_candidate_cannot_be_selected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "data"
            store = ProductionImageJobStore(root / "services/production/image-jobs.sqlite3")
            compiled = compile_image_candidates(workflow_id="z_image_turbo", prompt="Station platform.",
                control_mode="assisted_manual", seed=8, output_prefix="workspace-1/first_frame")
            lineage = {"screenplay_revision_id": "screenplay-1", "source_revision_id": "source-1",
                "graph_snapshot_id": "graph-1", "target_type": "clip", "scene_number": 1,
                "shot_number": 2, "clip_id": "story-clip"}
            store.enqueue_batch(project_id="workspace-1", run_id="run-1",
                idempotency_key="skipped-frame-select", workflow_id=compiled["workflow_id"],
                workflow_version=compiled["workflow_version"], asset_role="first_frame",
                prompt=compiled["prompt"], settings={**compiled["settings"], "lineage": lineage},
                candidates=compiled["candidates"][:1])
            job = store.next_queued()
            prompt_id = store.reserve_prompt_id(job["job_id"])
            store.transition(job["job_id"], "running", prompt_id=prompt_id)
            store.transition(job["job_id"], "completed", output_asset_id="pa-0123456789abcdef")
            app = create_app(data_root=root)
            payload = {"workspace_id": "workspace-1", "asset_role": "first_frame",
                "screenplay_revision_id": "screenplay-1", "scene_number": 1, "shot_number": 2,
                "clip_id": "story-clip"}
            body = json.dumps(payload).encode()
            response = []
            environ = {"REQUEST_METHOD": "POST", "PATH_INFO": f"/api/images/jobs/{job['job_id']}/accept",
                "QUERY_STRING": "", "CONTENT_TYPE": "application/json", "CONTENT_LENGTH": str(len(body)),
                "wsgi.input": io.BytesIO(body)}
            with patch("story_builder.isolated_server._image_lineage", return_value=lineage), \
                 patch("story_builder.services.production_setup.ProductionSetup.get", return_value={"setup": {
                    "mode": "assisted_manual", "automate_steps": {"character_images": False,
                    "world_images": False, "frame_images": False}}}), \
                 patch("story_builder.services.production_setup.ProductionSetup.frame_preparation_is_skipped", return_value=True), \
                 patch("story_builder.isolated_server.assign_media_role") as assign:
                result = b"".join(app(environ, lambda status, headers: response.append(status)))
            self.assertEqual(response[0], "409 Conflict")
            self.assertIn("clear the skip", json.loads(result)["error"]["message"])
            assign.assert_not_called()

    def test_character_candidate_must_be_selected_for_its_original_screenplay_target(self, role="character_master"):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "data"
            store = ProductionImageJobStore(root / "services/production/image-jobs.sqlite3")
            compiled = compile_image_candidates(workflow_id="z_image_turbo", prompt="Mira portrait.",
                control_mode="assisted_manual", seed=8, output_prefix="workspace-1/character_master")
            lineage = {"screenplay_revision_id": "screenplay-1", "source_revision_id": "source-1",
                "graph_snapshot_id": "graph-1", "target_type": "character",
                "target_record_id": "mira-id", "target_name": "Mira"}
            batch = store.enqueue_batch(project_id="workspace-1", run_id="run-1",
                idempotency_key="character-candidate", workflow_id=compiled["workflow_id"],
                workflow_version=compiled["workflow_version"], asset_role=role,
                prompt=compiled["prompt"], settings={**compiled["settings"], "lineage": lineage},
                candidates=compiled["candidates"][:1])
            job = store.next_queued()
            prompt_id = store.reserve_prompt_id(job["job_id"])
            store.transition(job["job_id"], "running", prompt_id=prompt_id)
            store.transition(job["job_id"], "completed", output_asset_id="pa-0123456789abcdef")
            selections = ProductionImageSelection(root / "services/production/image-jobs.sqlite3")
            selections.select(project_id="workspace-1", screenplay_revision_id="screenplay-1",
                target_type="character", target_record_id="mira-id", asset_id="prior-master",
                job_id="prior-job", authority="user")
            app = create_app(data_root=root)
            def call(target_id):
                body = json.dumps({"workspace_id": "workspace-1", "asset_role": role,
                    "screenplay_revision_id": "screenplay-1", "target_record_id": target_id}).encode()
                response = []
                environ = {"REQUEST_METHOD": "POST", "PATH_INFO": f"/api/images/jobs/{job['job_id']}/accept",
                    "QUERY_STRING": "", "CONTENT_TYPE": "application/json", "CONTENT_LENGTH": str(len(body)),
                    "wsgi.input": io.BytesIO(body)}
                result = b"".join(app(environ, lambda status, headers: response.append(status)))
                return response[0], json.loads(result)
            with patch("story_builder.isolated_server._image_lineage",
                side_effect=lambda story, workspace, payload: {**lineage, "target_record_id": payload["target_record_id"]}), \
                 patch("story_builder.services.production_setup.ProductionSetup.get", return_value={"setup": {
                    "mode": "assisted_manual", "automate_steps": {"character_images": False,
                    "world_images": False, "frame_images": False}}}), \
                 patch("story_builder.isolated_server.assign_media_role",
                    return_value={"asset_id": "pa-0123456789abcdef", "roles": ["image_candidate", "character_master"]}):
                wrong_status, _ = call("arjun-id")
                correct_status, correct = call("mira-id")
                master = selections.get(project_id="workspace-1", screenplay_revision_id="screenplay-1",
                    target_type="character", target_record_id="mira-id")
                self.assertEqual(master["asset_id"], "prior-master" if role == "character_view" else "pa-0123456789abcdef")
        self.assertEqual(wrong_status, "409 Conflict")
        self.assertEqual(correct_status, "200 OK")
        self.assertTrue(correct["selected"])

    def test_character_view_acceptance_keeps_original_master(self):
        self.test_character_candidate_must_be_selected_for_its_original_screenplay_target(role="character_view")

    def test_world_candidate_selection_keeps_its_original_location_target(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "data"
            store = ProductionImageJobStore(root / "services/production/image-jobs.sqlite3")
            compiled = compile_image_candidates(workflow_id="z_image_turbo", prompt="Old station.",
                control_mode="assisted_manual", seed=8, output_prefix="workspace-1/world_master")
            lineage = {"screenplay_revision_id": "screenplay-1", "source_revision_id": "source-1",
                "graph_snapshot_id": "graph-1", "target_type": "location",
                "target_record_id": "station-id", "target_name": "Old station"}
            batch = store.enqueue_batch(project_id="workspace-1", run_id="run-1",
                idempotency_key="world-candidate", workflow_id=compiled["workflow_id"],
                workflow_version=compiled["workflow_version"], asset_role="world_master",
                prompt=compiled["prompt"], settings={**compiled["settings"], "lineage": lineage},
                candidates=compiled["candidates"][:1])
            job = store.next_queued()
            prompt_id = store.reserve_prompt_id(job["job_id"])
            store.transition(job["job_id"], "running", prompt_id=prompt_id)
            store.transition(job["job_id"], "completed", output_asset_id="pa-0123456789abcdef")
            app = create_app(data_root=root)
            def call(target_id):
                body = json.dumps({"workspace_id": "workspace-1", "asset_role": "world_master",
                    "screenplay_revision_id": "screenplay-1", "target_record_id": target_id}).encode()
                response = []
                environ = {"REQUEST_METHOD": "POST", "PATH_INFO": f"/api/images/jobs/{job['job_id']}/accept",
                    "QUERY_STRING": "", "CONTENT_TYPE": "application/json", "CONTENT_LENGTH": str(len(body)),
                    "wsgi.input": io.BytesIO(body)}
                result = b"".join(app(environ, lambda status, headers: response.append(status)))
                return response[0], json.loads(result)
            with patch("story_builder.isolated_server._image_lineage",
                side_effect=lambda story, workspace, payload: {**lineage, "target_record_id": payload["target_record_id"]}), \
                 patch("story_builder.services.production_setup.ProductionSetup.get", return_value={"setup": {
                    "mode": "assisted_manual", "automate_steps": {"character_images": False,
                    "world_images": False, "frame_images": False}}}), \
                 patch("story_builder.isolated_server.assign_media_role",
                    return_value={"asset_id": "pa-0123456789abcdef", "roles": ["image_candidate", "world_master"]}):
                wrong_status, _ = call("other-location")
                accepted_status, accepted = call("station-id")
        self.assertEqual(wrong_status, "409 Conflict")
        self.assertEqual(accepted_status, "200 OK")
        self.assertTrue(accepted["selected"])

    def test_old_manual_candidate_cannot_be_selected_after_stage_is_checked(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "data"
            store = ProductionImageJobStore(root / "services/production/image-jobs.sqlite3")
            compiled = compile_image_candidates(workflow_id="z_image_turbo", prompt="Mira portrait.",
                control_mode="assisted_manual", seed=8, output_prefix="workspace-1/character_master")
            lineage = {"screenplay_revision_id": "screenplay-1", "source_revision_id": "source-1",
                "graph_snapshot_id": "graph-1", "target_type": "character",
                "target_record_id": "mira-id", "target_name": "Mira"}
            store.enqueue_batch(project_id="workspace-1", run_id="run-1",
                idempotency_key="old-manual-candidate", workflow_id=compiled["workflow_id"],
                workflow_version=compiled["workflow_version"], asset_role="character_master",
                prompt=compiled["prompt"], settings={**compiled["settings"], "lineage": lineage},
                candidates=compiled["candidates"][:1])
            job = store.next_queued()
            prompt_id = store.reserve_prompt_id(job["job_id"])
            store.transition(job["job_id"], "running", prompt_id=prompt_id)
            store.transition(job["job_id"], "completed", output_asset_id="pa-0123456789abcdef")
            app = create_app(data_root=root)
            payload = {"workspace_id": "workspace-1", "asset_role": "character_master",
                "screenplay_revision_id": "screenplay-1", "target_record_id": "mira-id"}
            body = json.dumps(payload).encode()
            response = []
            environ = {"REQUEST_METHOD": "POST", "PATH_INFO": f"/api/images/jobs/{job['job_id']}/accept",
                "QUERY_STRING": "", "CONTENT_TYPE": "application/json", "CONTENT_LENGTH": str(len(body)),
                "wsgi.input": io.BytesIO(body)}
            setup = {"setup": {"mode": "assisted_manual", "automate_steps": {
                "character_images": True, "world_images": False, "frame_images": False}}}
            with patch("story_builder.isolated_server._image_lineage", return_value=lineage), \
                 patch("story_builder.services.production_setup.ProductionSetup.get", return_value=setup), \
                 patch("story_builder.isolated_server.assign_media_role") as assign:
                result = b"".join(app(environ, lambda status, headers: response.append(status)))
            self.assertEqual(response[0], "409 Conflict")
            self.assertIn("selected for automation", json.loads(result)["error"]["message"])
            assign.assert_not_called()
            self.assertIsNone(ProductionImageSelection(root / "services/production/image-jobs.sqlite3").get(
                project_id="workspace-1", screenplay_revision_id="screenplay-1",
                target_type="character", target_record_id="mira-id"))


if __name__ == "__main__":
    unittest.main()
