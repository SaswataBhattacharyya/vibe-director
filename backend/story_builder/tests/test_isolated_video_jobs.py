from __future__ import annotations

import tempfile
import unittest
import urllib.error
import warnings
import io
import json
import hashlib
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from unittest.mock import patch

from story_builder.services.isolated_video_contract import EXPECTED_GRAPH_SHA256
from story_builder.services.isolated_video_jobs import (
    IsolatedJobConflict, IsolatedVideoJobs, StoryHandoffRejected, build_worker, prepare_isolated_take, story_clip_id,
)
from story_builder.services.production_job_worker import ProductionJobWorker, PreparedTake
from story_builder.services.production_ledger import LedgerNotFound, ProductionLedger
from story_builder.isolated_server import create_app

ROOT = Path(__file__).resolve().parents[1]
GRAPH = ROOT / "workflows/api/minimax_h3_t2v_api.json"


def request(**changes):
    payload = {"workflow_id": "minimax_h3_t2v_local_v1", "workflow_version": 1,
        "workflow_sha256": EXPECTED_GRAPH_SHA256, "prompt": "A quiet street at dusk.",
        "duration_seconds": 6, "aspect_ratio": "16:9", "resolution_preset": 0.98,
        "steps": 20, "seed": 1, "references": []}
    payload.update(changes)
    return payload


class IsolatedVideoJobTests(unittest.TestCase):
    def setUp(self):
        warnings.simplefilter("ignore", ResourceWarning)
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.db_path = Path(self.temporary.name) / "product.sqlite3"
        self.ledger = ProductionLedger(self.db_path)
        self.jobs = IsolatedVideoJobs(self.ledger, graph_path=GRAPH)
        self._story_job_fixture = None
        # Routing tests use explicit CPU-frame doubles; extraction has its own real FFmpeg tests.
        frame_patch = patch("story_builder.services.isolated_video_jobs.last_frame", side_effect=lambda root, workspace, output, **kw: {
            "asset_id":"pa-aaaaaaaaaaaaaaaa", "sha256":output["sha256"], "role":"continuity", "intent":"Preserve the world; advance only the new shot."})
        frame_patch.start()
        self.addCleanup(frame_patch.stop)

    def test_owner_pause_blocks_claim_and_resume_retains_same_job(self):
        jobs = self.fully_automated_jobs()
        started = jobs.start_fully_automated_first_clip("workspace-a", "screenplay-a")
        paused = jobs.control_fully_automated_run("workspace-a", "screenplay-a", "pause")
        self.assertEqual(paused["run_state"], "owner_paused")
        self.assertIsNone(jobs.ledger.claim_next_queued_take(lease_owner="test"))
        jobs._set_full_run_state("workspace-a", "screenplay-a", "running", None)
        self.assertEqual(jobs.get_fully_automated_first_clip("workspace-a", "screenplay-a")["run_state"], "owner_paused")
        resumed = jobs.control_fully_automated_run("workspace-a", "screenplay-a", "resume")
        self.assertEqual(resumed["job"]["job_id"], started["job"]["job_id"])
        self.assertIsNotNone(jobs.ledger.claim_next_queued_take(lease_owner="test"))

    def test_owner_stop_cancels_queued_clip_and_cannot_be_overwritten(self):
        jobs = self.fully_automated_jobs()
        started = jobs.start_fully_automated_first_clip("workspace-a", "screenplay-a")
        stopped = jobs.control_fully_automated_run("workspace-a", "screenplay-a", "stop")
        self.assertEqual(stopped["run_state"], "stopped")
        self.assertEqual(jobs.get_job(started["job"]["job_id"])["status"], "cancelled")
        jobs._set_full_run_state("workspace-a", "screenplay-a", "completed", None)
        self.assertEqual(jobs.control_fully_automated_run("workspace-a", "screenplay-a", "stop")["run_state"], "stopped")
        self.assertIsNone(jobs.ledger.claim_next_queued_take(lease_owner="test"))
        with self.assertRaises(IsolatedJobConflict):
            jobs.control_fully_automated_run("workspace-a", "screenplay-a", "resume")

    def test_production_video_worker_ledger_is_single_owner(self):
        from story_builder.isolated_worker import isolated_worker_lifetime_lock

        with isolated_worker_lifetime_lock(self.db_path):
            with self.assertRaisesRegex(RuntimeError, "already owns this ledger"):
                with isolated_worker_lifetime_lock(self.db_path):
                    self.fail("a second production-video worker acquired the same ledger")

    def create(self, *, key="key-1", payload=None, **extra):
        return self.jobs.create_job(workspace_id="workspace-a", clip_id="clip-1",
            idempotency_key=key, request=payload or request(), **extra)

    def test_ledger_connection_context_closes_handle(self):
        with self.ledger._connect() as db:
            db.execute("SELECT 1")
        with self.assertRaises(sqlite3.ProgrammingError):
            db.execute("SELECT 1")

    def test_list_jobs_is_workspace_scoped_and_bounded(self):
        first = self.create(key="list-a")
        second = self.jobs.create_job(workspace_id="workspace-b", clip_id="clip-b",
            idempotency_key="list-b", request=request())
        self.jobs.create_job(workspace_id="workspace-b", clip_id="clip-c",
            idempotency_key="list-c", request=request())
        self.assertEqual([row["job_id"] for row in self.jobs.list_jobs(workspace_id="workspace-a")],
            [first["job_id"]])
        self.assertIn(second["job_id"], [row["job_id"] for row in self.jobs.list_jobs(workspace_id="workspace-b")])
        self.assertEqual(len(self.jobs.list_jobs(workspace_id="workspace-b", limit=1)), 1)
        ordered = self.jobs.list_jobs(workspace_id="workspace-b", limit=1)
        page_two = self.jobs.list_jobs(workspace_id="workspace-b", limit=1, offset=1)
        self.assertEqual(len(page_two), 1)
        self.assertNotEqual(ordered[0]["job_id"], page_two[0]["job_id"])

    def test_full_run_clip_number_schema_migration_preserves_legacy_rows_and_is_idempotent(self):
        legacy_path = Path(self.temporary.name) / "legacy.sqlite3"
        legacy_ledger = ProductionLedger(legacy_path)
        with legacy_ledger._connect() as db:
            db.executescript("""
                CREATE TABLE fully_automated_run_clips (
                    workspace_id TEXT NOT NULL, screenplay_revision_id TEXT NOT NULL,
                    scene_number INTEGER NOT NULL, shot_number INTEGER NOT NULL,
                    job_id TEXT NOT NULL UNIQUE, predecessor_job_id TEXT,
                    clip_state TEXT NOT NULL DEFAULT 'queued', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY(workspace_id, screenplay_revision_id, scene_number, shot_number)
                );
                CREATE TABLE fully_automated_run_attempts (
                    job_id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL, screenplay_revision_id TEXT NOT NULL,
                    scene_number INTEGER NOT NULL, shot_number INTEGER NOT NULL, attempt_number INTEGER NOT NULL,
                    predecessor_job_id TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(workspace_id, screenplay_revision_id, scene_number, shot_number, attempt_number)
                );
                INSERT INTO fully_automated_run_clips VALUES
                    ('workspace-a','revision-a',2,3,'legacy-job','prior-job','failed','2026-01-02T03:04:05Z');
                INSERT INTO fully_automated_run_attempts VALUES
                    ('legacy-job','workspace-a','revision-a',2,3,2,'prior-job','2026-01-02T03:04:05Z');
            """)

        migrated = IsolatedVideoJobs(legacy_ledger, graph_path=GRAPH)
        with legacy_ledger._connect() as db:
            clip = dict(db.execute("SELECT * FROM fully_automated_run_clips").fetchone())
            attempt = dict(db.execute("SELECT * FROM fully_automated_run_attempts").fetchone())
        self.assertEqual(clip, {"workspace_id":"workspace-a", "screenplay_revision_id":"revision-a",
            "scene_number":2, "shot_number":3, "clip_number":1, "job_id":"legacy-job",
            "predecessor_job_id":"prior-job", "clip_state":"failed", "created_at":"2026-01-02T03:04:05Z"})
        self.assertEqual(attempt, {"job_id":"legacy-job", "workspace_id":"workspace-a",
            "screenplay_revision_id":"revision-a", "scene_number":2, "shot_number":3,
            "clip_number":1, "attempt_number":2, "predecessor_job_id":"prior-job",
            "created_at":"2026-01-02T03:04:05Z"})

        # A second open is a no-op, and the expanded key permits another planned clip for the shot.
        IsolatedVideoJobs(legacy_ledger, graph_path=GRAPH)
        with legacy_ledger._connect() as db:
            db.execute("INSERT INTO fully_automated_run_clips(workspace_id,screenplay_revision_id,scene_number,shot_number,clip_number,job_id) VALUES('workspace-a','revision-a',2,3,2,'second-clip')")
            db.execute("INSERT INTO fully_automated_run_attempts(job_id,workspace_id,screenplay_revision_id,scene_number,shot_number,clip_number,attempt_number) VALUES('second-attempt','workspace-a','revision-a',2,3,2,1)")
            self.assertEqual(db.execute("SELECT COUNT(*) FROM fully_automated_run_clips").fetchone()[0], 2)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM fully_automated_run_attempts").fetchone()[0], 2)

    def test_concurrent_full_run_migration_does_not_reset_new_clip_numbers(self):
        path = Path(self.temporary.name) / "concurrent-legacy.sqlite3"
        ledger = ProductionLedger(path)
        with ledger._connect() as db:
            db.executescript("""
                CREATE TABLE fully_automated_run_clips (
                    workspace_id TEXT NOT NULL, screenplay_revision_id TEXT NOT NULL,
                    scene_number INTEGER NOT NULL, shot_number INTEGER NOT NULL,
                    job_id TEXT NOT NULL UNIQUE, predecessor_job_id TEXT,
                    clip_state TEXT NOT NULL DEFAULT 'queued', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY(workspace_id, screenplay_revision_id, scene_number, shot_number)
                );
                CREATE TABLE fully_automated_run_attempts (
                    job_id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL, screenplay_revision_id TEXT NOT NULL,
                    scene_number INTEGER NOT NULL, shot_number INTEGER NOT NULL, attempt_number INTEGER NOT NULL,
                    predecessor_job_id TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(workspace_id, screenplay_revision_id, scene_number, shot_number, attempt_number)
                );
                INSERT INTO fully_automated_run_clips
                    (workspace_id,screenplay_revision_id,scene_number,shot_number,job_id)
                    VALUES('workspace-a','revision-a',1,1,'first-clip');
            """)

        both_observed_legacy = threading.Barrier(2)
        winner_committed = threading.Event()

        class MigrationConnection:
            def __init__(self, connection, role):
                self.connection = connection
                self.role = role
                self.inserted_second_clip = False

            def execute(self, sql, parameters=()):
                if sql == "BEGIN IMMEDIATE":
                    both_observed_legacy.wait(timeout=5)
                    if self.role == "loser":
                        winner_committed.wait(timeout=5)
                    return self.connection.execute(sql, parameters)
                return self.connection.execute(sql, parameters)

            def commit(self):
                self.connection.commit()
                if self.role == "winner" and not self.inserted_second_clip:
                    self.inserted_second_clip = True
                    with sqlite3.connect(path) as db:
                        db.execute("INSERT INTO fully_automated_run_clips(workspace_id,screenplay_revision_id,scene_number,shot_number,clip_number,job_id) VALUES('workspace-a','revision-a',1,1,2,'second-clip')")
                    winner_committed.set()

            def rollback(self):
                self.connection.rollback()

        def migrate(role):
            raw = sqlite3.connect(path, timeout=5, isolation_level=None)
            raw.row_factory = sqlite3.Row
            IsolatedVideoJobs._migrate_full_run_clip_numbers(MigrationConnection(raw, role))
            raw.close()

        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(migrate, ("winner", "loser")))
        with ledger._connect() as db:
            rows = [tuple(row) for row in db.execute("SELECT job_id,clip_number FROM fully_automated_run_clips ORDER BY clip_number")]
        self.assertEqual(rows, [("first-clip", 1), ("second-clip", 2)])

    def test_full_style_video_route_numbers_refs_and_reserves_continuity_slot(self):
        setup = {"video_quality": "high", "duration_policy": {"kind": "fixed", "seconds": 6},
            "style_video_references": [
                {"asset_id": "pa-0123456789abcdef", "sha256": "a" * 64, "intent": "Match its cool palette."},
                {"asset_id": "pa-fedcba9876543210", "sha256": "b" * 64, "intent": "Use its camera movement."}]}
        first = self.jobs._full_r2v_request(setup=setup, prompt="A quiet street.")
        later = self.jobs._full_r2v_request(setup=setup, prompt="A person enters.",
            continuity={"asset_id": "video_previous", "sha256": "c" * 64})
        self.assertEqual(first["videos"], [])
        self.assertEqual(later["videos"], [])
        self.assertEqual(later["images"][0]["role"], "continuity")
        self.assertIn("<Picture 1>", later["prompt"])
        self.assertNotIn("<Video", later["prompt"])

    def test_full_identity_refs_use_latest_prior_cited_crops_in_screenplay_order(self):
        from story_builder.services.fully_automated_identity import IdentityReviewStore

        self.jobs.media_root = Path(self.temporary.name)
        IdentityReviewStore(self.db_path)
        with self.ledger._connect() as db:
            db.executemany("INSERT INTO fully_automated_run_clips(workspace_id,screenplay_revision_id,scene_number,shot_number,clip_number,job_id) VALUES(?,?,?,?,?,?)", [
                ("workspace-a", "revision-a", 1, 1, 1, "earlier-1"),
                ("workspace-a", "revision-a", 1, 2, 1, "earlier-2"),
                ("workspace-a", "revision-a", 2, 1, 1, "future"),
            ])
        asset_files = {}
        for asset_id, byte in (("crop-old", b"old"), ("crop-new", b"new"), ("crop-b", b"b"), ("crop-future", b"future")):
            path = Path(self.temporary.name) / f"{asset_id}.png"
            path.write_bytes(byte)
            asset_files[asset_id] = (path, "image/png", path.name)
        reviews = [
            ("earlier-1", [{"character_id": "char-a", "name": "A"}], ["crop-old"]),
            ("earlier-2", [{"character_id": "char-a", "name": "A"}, {"character_id": "char-b", "name": "B"}], ["crop-new", "crop-b"]),
            ("future", [{"character_id": "char-a", "name": "A"}], ["crop-future"]),
        ]
        crop_character = {"crop-old": "char-a", "crop-new": "char-a",
            "crop-b": "char-b", "crop-future": "char-a"}
        with self.ledger._connect() as db:
            for job_id, characters, asset_ids in reviews:
                refs = [{"frame_kind": "last", "character_id": crop_character[asset_id],
                    "asset_id": asset_id,
                    "sha256": hashlib.sha256(asset_files[asset_id][0].read_bytes()).hexdigest()}
                    for asset_id in asset_ids]
                db.execute("INSERT INTO fully_automated_identity_reviews(review_id,workspace_id,screenplay_revision_id,scene_number,source_job_id,source_asset_id,source_sha256,input_json,state,result_json,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                    (f"review-{job_id}", "workspace-a", "revision-a", 1, job_id, "source", "e" * 64,
                     json.dumps({"characters": characters}), "complete", json.dumps({"derived_references": refs}), "now"))
        def resolve_asset(_root, _workspace, asset_id):
            return asset_files[asset_id]
        plan = [{"scene_number": 1, "shot_number": 1, "clip_number": 1},
            {"scene_number": 1, "shot_number": 2, "clip_number": 1},
            {"scene_number": 2, "shot_number": 1, "clip_number": 1}]
        # Cast targets and story evidence intentionally use unrelated IDs.
        clip = {"target_character_ids": ["char-b", "char-a"],
            "evidence_record_ids": ["event-17", "fact-29"]}
        with self.ledger._connect() as db, patch("story_builder.services.media_library.asset_path", side_effect=resolve_asset):
            refs = self.jobs._full_identity_images(db, "workspace-a", "revision-a", plan, 2, clip)
        self.assertEqual([row["asset_id"] for row in refs], ["crop-b", "crop-new"])

    def story_jobs(self):
        class Story:
            @staticmethod
            def _screenplay_is_currently_accepted(db, row):
                current = db.execute("SELECT current_revision_id FROM story_workspaces WHERE workspace_id=?", (row["workspace_id"],)).fetchone()
                latest = db.execute("SELECT screenplay_revision_id FROM story_screenplay_revisions WHERE workspace_id=? AND source_revision_id=? ORDER BY rowid DESC LIMIT 1", (row["workspace_id"], row["source_revision_id"])).fetchone()
                return bool(row["accepted_at"] and current and current["current_revision_id"] == row["source_revision_id"]
                    and latest and latest["screenplay_revision_id"] == row["screenplay_revision_id"])
        with sqlite3.connect(self.db_path) as db:
            db.executescript("""
                CREATE TABLE story_workspaces(workspace_id TEXT PRIMARY KEY,current_revision_id TEXT);
                CREATE TABLE story_screenplay_revisions(screenplay_revision_id TEXT PRIMARY KEY,workspace_id TEXT,source_revision_id TEXT,accepted_at TEXT,screenplay_json TEXT);
                CREATE TABLE story_production_setups(workspace_id TEXT,screenplay_revision_id TEXT,setup_json TEXT,updated_at TEXT DEFAULT CURRENT_TIMESTAMP,PRIMARY KEY(workspace_id,screenplay_revision_id));
                CREATE TABLE story_prompt_drafts(workspace_id TEXT,screenplay_revision_id TEXT,setup_hash TEXT,drafts_json TEXT,updated_at TEXT DEFAULT CURRENT_TIMESTAMP,PRIMARY KEY(workspace_id,screenplay_revision_id));
                INSERT INTO story_workspaces VALUES('workspace-a','source-a');
                INSERT INTO story_screenplay_revisions VALUES('screenplay-a','workspace-a','source-a','accepted','{"scenes":[{"scene_number":1,"shots":[{"shot_number":1,"evidence_record_ids":["e-1"]}]}]}');
            """)
        setup = {"mode":"assisted_manual","automate_steps":{"character_images":False,"character_voice":False,"world_images":False,"frame_images":False,"video":False},"video_quality":"high","duration_policy":{"kind":"fixed","seconds":6}}
        setup_json = json.dumps(setup, sort_keys=True, separators=(",", ":"))
        setup_hash = hashlib.sha256(setup_json.encode()).hexdigest()
        draft = {"workflow_id": request()["workflow_id"], "prompt":"A screenplay shot prompt."}
        with sqlite3.connect(self.db_path) as db:
            db.execute("INSERT INTO story_production_setups(workspace_id,screenplay_revision_id,setup_json) VALUES(?,?,?)", ("workspace-a", "screenplay-a", setup_json))
            db.execute("INSERT INTO story_prompt_drafts(workspace_id,screenplay_revision_id,setup_hash,drafts_json) VALUES(?,?,?,?)", ("workspace-a", "screenplay-a", setup_hash, json.dumps({"1.1":draft}, sort_keys=True, separators=(",", ":"))))
        return IsolatedVideoJobs(self.ledger, graph_path=GRAPH, story=Story), {
            "screenplay_revision_id":"screenplay-a", "setup_hash":setup_hash,
            "scene_number":1, "shot_number":1,
            "source_prompt_sha256":hashlib.sha256(draft["prompt"].encode()).hexdigest(),
        }

    def fully_automated_jobs(self, *, duration_policy=None, workflow=None,
                             style_video_references=None):
        if self._story_job_fixture is None:
            self._story_job_fixture = self.story_jobs()[0]
        jobs = self._story_job_fixture
        setup = {"mode":"fully_automated","automate_steps":{"character_images":False,"character_voice":False,"world_images":False,"frame_images":False,"video":False},"video_quality":"standard","duration_policy":duration_policy or {"kind":"fixed","seconds":7}}
        if style_video_references is not None:
            setup["style_video_references"] = style_video_references
        setup_json = json.dumps(setup, sort_keys=True, separators=(",", ":"))
        setup_hash = hashlib.sha256(setup_json.encode()).hexdigest()
        with sqlite3.connect(self.db_path) as db:
            db.execute("UPDATE story_production_setups SET setup_json=? WHERE workspace_id='workspace-a'", (setup_json,))
            drafts = {"1.1":{"workflow_id":workflow or request()["workflow_id"],"prompt":"Saved first scene prompt."}}
            db.execute("UPDATE story_prompt_drafts SET setup_hash=?,drafts_json=? WHERE workspace_id='workspace-a'",
                (setup_hash, json.dumps(drafts, sort_keys=True, separators=(",", ":"))))
        def plan_one_clip_per_shot(*, prompt, temperature):
            payload = json.loads(prompt.split("INPUT JSON:\n", 1)[1])
            rows = []
            for shot in payload["scene"]["shots"]:
                spans = []
                for field in ("action", "dialogue"):
                    text = shot.get(field, "")
                    if text:
                        spans.append({"field": field, "start": 0, "end": len(text)})
                draft = payload["saved_workflow_prompts"][f"{payload['scene']['scene_number']}.{shot['shot_number']}"]
                rows.append({"scene_number": payload["scene"]["scene_number"],
                    "shot_number": shot["shot_number"],
                    "duration_seconds": payload["duration_bounds_seconds"]["minimum"],
                    "duration_reason": "One short test clip covers the shot.",
                    "prompt": draft["prompt"], "source_spans": spans})
            return {"clips": rows}
        jobs.full_clip_plan_provider = plan_one_clip_per_shot
        return jobs

    def test_assisted_plan_splits_shot_before_clip_keyed_reference_mapping(self):
        jobs, _ = self.story_jobs()
        jobs.media_root = Path(self.temporary.name)
        setup = {"mode":"assisted_manual","automate_steps":{"character_images":False,
            "character_voice":False,"world_images":False,"frame_images":False,"video":True},
            "video_quality":"high","duration_policy":{"kind":"fixed","seconds":6},
            "video_workflow_id":"minimax_h3_r2v_dynamic_v1"}
        setup_json = json.dumps(setup, sort_keys=True, separators=(",", ":"))
        setup_hash = hashlib.sha256(setup_json.encode()).hexdigest()
        screenplay = {"scenes":[{"scene_number":1,"shots":[{"shot_number":1,
            "action":"Guard enters room","dialogue":"Stop there","evidence_record_ids":["e-1"]}]}]}
        with sqlite3.connect(self.db_path) as db:
            db.execute("UPDATE story_screenplay_revisions SET screenplay_json=? WHERE screenplay_revision_id='screenplay-a'", (json.dumps(screenplay),))
            db.execute("UPDATE story_production_setups SET setup_json=? WHERE workspace_id='workspace-a'", (setup_json,))
            db.execute("UPDATE story_prompt_drafts SET setup_hash=?,drafts_json=? WHERE workspace_id='workspace-a'",
                (setup_hash, json.dumps({"1.1":{"workflow_id":"minimax_h3_r2v_dynamic_v1","prompt":"Guard enters. Stop there."}})))

        def split_shot(*, prompt, temperature):
            return {"clips":[
                {"scene_number":1,"shot_number":1,"duration_seconds":6,"duration_reason":"Entry action.",
                 "prompt":"Guard enters.","source_spans":[{"field":"action","start":0,"end":6}]},
                {"scene_number":1,"shot_number":1,"duration_seconds":6,"duration_reason":"Dialogue beat.",
                 "prompt":"Stop there.","source_spans":[{"field":"action","start":6,"end":17},{"field":"dialogue","start":0,"end":10}]},
            ]}
        jobs.full_clip_plan_provider = split_shot
        plan = jobs.prepare_assisted_video_clip_plan("workspace-a", "screenplay-a")
        self.assertEqual([clip["clip_number"] for clip in plan["clips"]], [1, 2])
        self.assertNotEqual(plan["clips"][0]["clip_id"], plan["clips"][1]["clip_id"])
        self.assertEqual(jobs.get_assisted_video_clip_plan("workspace-a", "screenplay-a")["clips"], plan["clips"])
        with self.assertRaisesRegex(ValueError, "Map every planned clip exactly once"):
            jobs.save_assisted_video_clip_references("workspace-a", "screenplay-a", [
                {"clip_id": "shot-1.1", "references": []}])

    def test_assisted_clip_prompt_edit_is_saved_only_to_current_unfrozen_plan(self):
        jobs, _ = self.story_jobs()
        with jobs.ledger._connect() as db:
            source = {"screenplay": json.loads(db.execute("SELECT screenplay_json FROM story_screenplay_revisions WHERE screenplay_revision_id='screenplay-a'").fetchone()[0]),
                "setup": json.loads(db.execute("SELECT setup_json FROM story_production_setups WHERE workspace_id='workspace-a'").fetchone()[0]),
                "drafts": json.loads(db.execute("SELECT drafts_json FROM story_prompt_drafts WHERE workspace_id='workspace-a'").fetchone()[0])}
        input_hash = hashlib.sha256(json.dumps(source, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
        clip = {"clip_id":"assistclip-0001", "scene_number":1, "shot_number":1, "clip_number":1,
            "workflow_id":"minimax_h3_t2v_local_v1", "duration_seconds":6, "duration_reason":"fixed",
            "prompt":"Original clip prompt.", "source_spans":[]}
        with jobs.ledger._connect() as db:
            db.execute("INSERT INTO assisted_video_clip_plans(workspace_id,screenplay_revision_id,input_hash,plan_json) VALUES(?,?,?,?)",
                ("workspace-a", "screenplay-a", input_hash, json.dumps([clip])))

        saved = jobs.save_assisted_video_clip_prompt("workspace-a", "screenplay-a", clip["clip_id"],
            expected_prompt=clip["prompt"], prompt="Director-edited clip prompt.")
        self.assertEqual(saved["clips"][0]["prompt"], "Director-edited clip prompt.")
        with self.assertRaisesRegex(IsolatedJobConflict, "changed elsewhere"):
            jobs.save_assisted_video_clip_prompt("workspace-a", "screenplay-a", clip["clip_id"],
                expected_prompt=clip["prompt"], prompt="Stale edit.")
        with self.assertRaisesRegex(ValueError, "1–6,999"):
            jobs.save_assisted_video_clip_prompt("workspace-a", "screenplay-a", clip["clip_id"],
                expected_prompt="Director-edited clip prompt.", prompt="x" * 7000)
        with jobs.ledger._connect() as db:
            db.execute("INSERT INTO assisted_video_runs(workspace_id,screenplay_revision_id,manifest_json,run_state) VALUES(?,?,?,'running')",
                ("workspace-a", "screenplay-a", "{}"))
        with self.assertRaisesRegex(IsolatedJobConflict, "frozen"):
            jobs.save_assisted_video_clip_prompt("workspace-a", "screenplay-a", clip["clip_id"],
                expected_prompt="Director-edited clip prompt.", prompt="Too late.")

    def test_assisted_run_admits_frozen_clip_to_shared_queue_with_selected_references(self):
        jobs, _ = self.story_jobs()
        jobs.r2v_capability_provider = lambda: {"available": True}
        workflow = "minimax_h3_r2v_dynamic_v1"
        style_reference = {"asset_id":"pa-1123456789abcdef", "sha256":"f"*64,
            "intent":"Borrow the cool palette from this film."}
        setup = {"mode":"assisted_manual","automate_steps":{"character_images":False,
            "character_voice":False,"world_images":False,"frame_images":False,"video":True},
            "video_quality":"standard","duration_policy":{"kind":"fixed","seconds":6},
            "video_workflow_id":workflow,"style_video_references":[style_reference]}
        setup_json = json.dumps(setup, sort_keys=True, separators=(",", ":"))
        setup_hash = hashlib.sha256(setup_json.encode()).hexdigest()
        knowledge_ref = {"knowledge_id":"minimax-h3-r2v", "guidance_version":2,
            "workflow_sha256":"a" * 64}
        drafts = {"1.1":{"workflow_id":workflow,"prompt":"The guard crosses the room.",
            "knowledge_ref":knowledge_ref}}
        draft_json = json.dumps(drafts, sort_keys=True, separators=(",", ":"))
        screenplay = {"scenes":[{"scene_number":1,"shots":[{"shot_number":1,
            "evidence_record_ids":["e-1"]}]}]}
        with sqlite3.connect(self.db_path) as db:
            db.execute("UPDATE story_screenplay_revisions SET screenplay_json=? WHERE screenplay_revision_id='screenplay-a'",
                (json.dumps(screenplay),))
            db.execute("UPDATE story_production_setups SET setup_json=? WHERE workspace_id='workspace-a'",
                (setup_json,))
            db.execute("UPDATE story_prompt_drafts SET setup_hash=?,drafts_json=? WHERE workspace_id='workspace-a'",
                (setup_hash, draft_json))
        input_hash = hashlib.sha256(json.dumps({"screenplay":screenplay,"setup":setup,
            "drafts":drafts}, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
        clip = {"clip_id":"assistclip-0001","scene_number":1,"shot_number":1,"clip_number":1,
            "workflow_id":workflow,"duration_seconds":6,"duration_reason":"One action beat.",
            "prompt":"The guard crosses the room.","source_spans":[]}
        reference = {"kind":"image","asset_id":"pa-0123456789abcdef","sha256":"b" * 64,
            "role":"character","intent":"Keep the guard's uniform and face consistent."}
        with sqlite3.connect(self.db_path) as db:
            db.execute("INSERT INTO assisted_video_clip_plans(workspace_id,screenplay_revision_id,input_hash,plan_json) VALUES(?,?,?,?)",
                ("workspace-a","screenplay-a",input_hash,json.dumps([clip],sort_keys=True,separators=(",", ":"))))
            db.execute("INSERT INTO assisted_video_clip_references(workspace_id,screenplay_revision_id,clip_id,references_json) VALUES(?,?,?,?)",
                ("workspace-a","screenplay-a",clip["clip_id"],json.dumps([reference],sort_keys=True,separators=(",", ":"))))

        original_connect = jobs.ledger._connect
        connect_count = 0
        def edit_plan_before_freeze():
            nonlocal connect_count
            connect_count += 1
            if connect_count == 4:
                with original_connect() as db:
                    row = db.execute("SELECT plan_json FROM assisted_video_clip_plans WHERE workspace_id=? AND screenplay_revision_id=?",
                        ("workspace-a", "screenplay-a")).fetchone()
                    clips = json.loads(row["plan_json"])
                    clips[0]["prompt"] = "Concurrent edit that must not be lost."
                    db.execute("UPDATE assisted_video_clip_plans SET plan_json=? WHERE workspace_id=? AND screenplay_revision_id=?",
                        (json.dumps(clips), "workspace-a", "screenplay-a"))
            return original_connect()
        with patch.object(jobs.ledger, "_connect", side_effect=edit_plan_before_freeze):
            with self.assertRaisesRegex(IsolatedJobConflict, "changed while the run was starting"):
                jobs.start_assisted_video_run("workspace-a", "screenplay-a", readiness={"available":True})
        with jobs.ledger._connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM assisted_video_runs").fetchone()[0], 0)
            db.execute("UPDATE assisted_video_clip_plans SET plan_json=? WHERE workspace_id=? AND screenplay_revision_id=?",
                (json.dumps([clip], sort_keys=True, separators=(",", ":")), "workspace-a", "screenplay-a"))

        started = jobs.start_assisted_video_run("workspace-a","screenplay-a",
            readiness={"available":True})

        self.assertEqual(started["status"], "queued", started)
        self.assertEqual(started["job"]["status"], "queued")
        self.assertEqual(started["job"]["clip_id"], clip["clip_id"])
        self.assertEqual(started["job"]["request"]["images"], [
            {"asset_id":reference["asset_id"],"sha256":reference["sha256"],
             "role":reference["role"],"intent":reference["intent"]}])
        self.assertEqual(started["job"]["request"]["videos"], [])
        self.assertIn("<Picture 1> character:", started["job"]["request"]["prompt"])
        self.assertNotIn("<Video", started["job"]["request"]["prompt"])
        self.assertEqual(started["job"]["source_lineage"]["knowledge_ref"], knowledge_ref)
        state = jobs.get_assisted_video_run("workspace-a","screenplay-a")
        self.assertEqual((state["run_state"],state["planned_count"],len(state["clips"])),
            ("running",1,1))
        with jobs.ledger._connect() as db:
            binding = db.execute("SELECT clip_id,job_id,predecessor_job_id FROM assisted_video_run_clips").fetchone()
        self.assertEqual(tuple(binding), (clip["clip_id"],started["job"]["job_id"],None))

        # Failure pauses the run. Retry must re-use the frozen request and atomically
        # replace only the latest failed binding; repeating the request is idempotent.
        with jobs.ledger._connect() as db:
            db.execute("UPDATE production_takes SET status='failed' WHERE job_id=?",
                (started["job"]["job_id"],))
        paused = jobs.advance_assisted_video_run("workspace-a", "screenplay-a",
            readiness={"available": True})
        self.assertEqual(paused["status"], "paused")
        retried = jobs.retry_assisted_video_clip("workspace-a", "screenplay-a", clip["clip_id"],
            readiness={"available": True})
        self.assertEqual(retried["status"], "queued")
        self.assertNotEqual(retried["job"]["job_id"], started["job"]["job_id"])
        self.assertEqual(retried["job"]["request"], started["job"]["request"])
        self.assertIsNone(retried["job"]["retake_of_job_id"])
        self.assertEqual(retried["run"]["run_state"], "running")
        with jobs.ledger._connect() as db:
            binding = db.execute("SELECT clip_id,job_id,predecessor_job_id FROM assisted_video_run_clips").fetchone()
        self.assertEqual(tuple(binding), (clip["clip_id"], retried["job"]["job_id"], None))
        replay = jobs.retry_assisted_video_clip("workspace-a", "screenplay-a", clip["clip_id"],
            readiness={"available": True})
        self.assertEqual(replay["job"]["job_id"], retried["job"]["job_id"])

    def test_assisted_run_recovers_using_manifest_order_when_sqlite_rows_return_reordered(self):
        jobs, _ = self.story_jobs()
        planned = [
            {"clip_id": "clip-z-first", "clip_number": 1},
            {"clip_id": "clip-a-second", "clip_number": 2},
        ]
        first = jobs.create_job(workspace_id="workspace-a", clip_id=planned[0]["clip_id"],
            idempotency_key="recovery-first", request=request())
        second = jobs.create_job(workspace_id="workspace-a", clip_id=planned[1]["clip_id"],
            idempotency_key="recovery-second", request=request())
        with jobs.ledger._connect() as db:
            db.execute("INSERT INTO assisted_video_runs(workspace_id,screenplay_revision_id,manifest_json,run_state) VALUES(?,?,?,'running')",
                ("workspace-a", "screenplay-a", json.dumps({"clips": planned})))
            # Insert in manifest order; the table's composite primary key is
            # ordered by clip_id and may return the rows in the opposite order.
            db.execute("INSERT INTO assisted_video_run_clips(workspace_id,screenplay_revision_id,clip_id,job_id,clip_state) VALUES(?,?,?,?, 'needs_review')",
                ("workspace-a", "screenplay-a", planned[0]["clip_id"], first["job_id"]))
            db.execute("INSERT INTO assisted_video_run_clips(workspace_id,screenplay_revision_id,clip_id,job_id,predecessor_job_id,clip_state) VALUES(?,?,?,?,?, 'needs_review')",
                ("workspace-a", "screenplay-a", planned[1]["clip_id"], second["job_id"], first["job_id"]))
            db.execute("UPDATE production_takes SET status='needs_review' WHERE job_id IN (?,?)",
                (first["job_id"], second["job_id"]))
            returned_order = [row[0] for row in db.execute(
                "SELECT clip_id FROM assisted_video_run_clips WHERE workspace_id=? AND screenplay_revision_id=?",
                ("workspace-a", "screenplay-a")).fetchall()]
        self.assertEqual(returned_order, ["clip-a-second", "clip-z-first"])

        recovered = jobs.advance_assisted_video_run("workspace-a", "screenplay-a",
            readiness={"available": True})

        self.assertEqual(recovered["status"], "completed", recovered)
        self.assertEqual(recovered["job"]["job_id"], second["job_id"])

    def test_assisted_admission_rejects_changed_prompt_after_run_freeze(self):
        jobs, _ = self.story_jobs()
        jobs.r2v_capability_provider = lambda: {"available": True}
        workflow = "minimax_h3_r2v_dynamic_v1"
        setup = {"mode":"assisted_manual","automate_steps":{"character_images":False,
            "character_voice":False,"world_images":False,"frame_images":False,"video":True},
            "video_quality":"standard","duration_policy":{"kind":"fixed","seconds":6},
            "video_workflow_id":workflow}
        setup_json = json.dumps(setup, sort_keys=True, separators=(",", ":"))
        setup_hash = hashlib.sha256(setup_json.encode()).hexdigest()
        drafts = {"1.1":{"workflow_id":workflow,"prompt":"Frozen prompt."}}
        with sqlite3.connect(self.db_path) as db:
            screenplay = json.loads(db.execute("SELECT screenplay_json FROM story_screenplay_revisions WHERE screenplay_revision_id='screenplay-a'").fetchone()[0])
            db.execute("UPDATE story_production_setups SET setup_json=? WHERE workspace_id='workspace-a'", (setup_json,))
            db.execute("UPDATE story_prompt_drafts SET setup_hash=?,drafts_json=? WHERE workspace_id='workspace-a'",
                (setup_hash,json.dumps(drafts,sort_keys=True,separators=(",", ":"))))
        input_hash = hashlib.sha256(json.dumps({"screenplay":screenplay,"setup":setup,
            "drafts":drafts},sort_keys=True,ensure_ascii=False,separators=(",", ":")).encode()).hexdigest()
        clips = [{"clip_id":f"assistclip-000{number}","scene_number":1,"shot_number":1,"clip_number":number,
            "workflow_id":workflow,"duration_seconds":6,"duration_reason":"One action beat.",
            "prompt":"Frozen prompt.","source_spans":[]} for number in (1, 2)]
        references = [{"kind":"image","asset_id":f"pa-1123456789abcdef","sha256":"c"*64,
            "role":"character","intent":"Keep this character."}]
        with sqlite3.connect(self.db_path) as db:
            db.execute("INSERT INTO assisted_video_clip_plans(workspace_id,screenplay_revision_id,input_hash,plan_json) VALUES(?,?,?,?)",
                ("workspace-a","screenplay-a",input_hash,json.dumps(clips,sort_keys=True,separators=(",", ":"))))
            db.executemany("INSERT INTO assisted_video_clip_references(workspace_id,screenplay_revision_id,clip_id,references_json) VALUES(?,?,?,?)",
                [("workspace-a","screenplay-a",clip["clip_id"],json.dumps(references,sort_keys=True,separators=(",", ":"))) for clip in clips])
        started = jobs.start_assisted_video_run("workspace-a","screenplay-a",readiness={"available":True})
        self.assertEqual(started["status"], "queued")
        with sqlite3.connect(self.db_path) as db:
            db.execute("UPDATE story_prompt_drafts SET drafts_json=? WHERE workspace_id='workspace-a'",
                (json.dumps({"1.1":{"workflow_id":workflow,"prompt":"Changed after queue."}}),))
            db.execute("UPDATE production_takes SET status='needs_review' WHERE job_id=?", (started["job"]["job_id"],))
        advanced = jobs.advance_assisted_video_run("workspace-a", "screenplay-a", readiness={"available":True})
        self.assertEqual(advanced["status"], "paused")
        self.assertIn("changed before Assisted job admission", advanced["reason"])
        with jobs.ledger._connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM assisted_video_run_clips").fetchone()[0], 1)
        with jobs.ledger._connect() as db:
            manifest = json.loads(db.execute("SELECT manifest_json FROM assisted_video_runs WHERE workspace_id='workspace-a'").fetchone()[0])
            self.assertEqual([clip["prompt"] for clip in manifest["clips"]], ["Frozen prompt.", "Frozen prompt."])

    def test_assisted_r2v_adds_previous_clip_only_when_director_enabled_it(self):
        jobs, _ = self.story_jobs()
        workflow = "minimax_h3_r2v_dynamic_v1"
        previous = {"clip_id":"clip-previous","scene_number":1,"clip_number":1}
        manifest = {"setup":{"video_quality":"standard"},"clips":[previous, {
            "clip_id":"clip-current","scene_number":1,"clip_number":2}]}
        clip = {"workflow_id":workflow,"duration_seconds":6,"prompt":"Continue the movement.",
            "clip_id":"clip-current","scene_number":1,
            "references":[{"kind":"image","asset_id":"pa-2123456789abcdef","sha256":"d"*64,
                "role":"character","intent":"Keep the same character."}],
            "continue_previous_clip":True}
        predecessor = {"workspace_id":"workspace-a","status":"needs_review","clip_id":"clip-previous","outputs":[
            {"kind":"video","has_video":True,"shared_asset_id":"pa-3123456789abcdef","sha256":"e"*64}]}

        request = jobs._assisted_request(manifest, clip, predecessor)

        self.assertEqual(request["videos"], [])
        self.assertEqual(request["images"][-1]["role"], "continuity")
        self.assertIn("<Picture 2>", request["prompt"])
        without_continuity = jobs._assisted_request(manifest, {**clip,"continue_previous_clip":False}, predecessor)
        self.assertEqual(without_continuity["videos"], [])
        with self.assertRaisesRegex(StoryHandoffRejected, "previous clip is not ready"):
            jobs._assisted_request(manifest, clip, {**predecessor,"clip_id":"unrelated-clip"})

    def test_assisted_r2v_inherits_selected_run_style_video_once_before_clip_references(self):
        jobs, _ = self.story_jobs()
        style = {"asset_id":"pa-1123456789abcdef", "sha256":"f"*64,
            "intent":"Borrow the muted palette and slow camera movement."}
        manifest = {"setup":{"mode":"assisted_manual", "automate_steps":{"video":True},
            "video_quality":"standard", "style_video_references":[style]}, "clips":[]}
        clip = {"workflow_id":"minimax_h3_r2v_dynamic_v1", "duration_seconds":6,
            "prompt":"A quiet arrival.", "clip_id":"clip-current", "scene_number":1,
            "references":[{"kind":"image", "asset_id":"pa-2123456789abcdef", "sha256":"d"*64,
                "role":"character", "intent":"Keep the same character."}], "continue_previous_clip":False}

        request = jobs._assisted_request(manifest, clip)

        self.assertEqual(request["videos"], [])
        self.assertNotIn("<Video", request["prompt"])
        paired_clip = {**clip, "references": clip["references"] + [{"kind":"video",
            "asset_id":"pa-3123456789abcdef", "sha256":"e"*64, "role":"clip_context",
            "intent":"Use its river movement.", "start_sec":None, "end_sec":None,
            "include_paired_soundtrack":True, "audio_intent":"Keep the river ambience."},
            {"kind":"audio", "asset_id":"pa-4123456789abcdef", "sha256":"c"*64,
                "role":"voice", "intent":"Use this voice.", "speaker_ids":["character-mira"]}]}
        paired_request = jobs._assisted_request(manifest, paired_clip)
        self.assertEqual([video["asset_id"] for video in paired_request["videos"]],
            ["pa-3123456789abcdef"])
        self.assertIn("<Audio 1> is the soundtrack of <Video 1>", paired_request["prompt"])
        self.assertIn("<Audio 2> is the voice reference for Subject (character-mira).", paired_request["prompt"])
        duplicate = {**clip, "references": clip["references"] + [{"kind":"video", "asset_id":style["asset_id"],
            "sha256":style["sha256"], "role":"style", "intent":style["intent"], "start_sec":None,
            "end_sec":None, "include_paired_soundtrack":False, "audio_intent":""}]}
        self.assertEqual(jobs._assisted_request(manifest, duplicate)["videos"][0]["asset_id"], style["asset_id"])
        fflf = {**clip, "workflow_id":"minimax_h3_fl2va_first_last_v1"}
        with self.assertRaisesRegex(StoryHandoffRejected, "mapped first and last frame"):
            jobs._assisted_request(manifest, fflf)

    def test_fully_automated_first_clip_is_durable_and_idempotent(self):
        jobs = self.fully_automated_jobs()
        knowledge_ref = {"knowledge_id":"minimax-h3-t2v", "guidance_version":3,
            "workflow_sha256":"a" * 64}
        with sqlite3.connect(self.db_path) as db:
            db.execute("UPDATE story_prompt_drafts SET drafts_json=? WHERE workspace_id='workspace-a'",
                (json.dumps({"1.1":{"workflow_id":request()["workflow_id"],
                    "prompt":"Saved first scene prompt.", "knowledge_ref":knowledge_ref}}),))
        started = jobs.start_fully_automated_first_clip("workspace-a", "screenplay-a")
        self.assertEqual(started["run_state"], "first_clip_queued")
        self.assertEqual(started["job"]["status"], "queued")
        self.assertEqual(started["job"]["request"]["duration_seconds"], 7)
        self.assertEqual(started["job"]["request"]["resolution_preset"], 0.4)
        self.assertEqual(started["job"]["source_lineage"]["scene_number"], 1)
        self.assertEqual(started["job"]["source_lineage"]["knowledge_ref"], knowledge_ref)
        with sqlite3.connect(self.db_path) as db:
            changed_setup = {"mode":"fully_automated","automate_steps":{"character_images":False,"character_voice":False,"world_images":False,"frame_images":False,"video":False},"video_quality":"high","duration_policy":{"kind":"fixed","seconds":9}}
            changed_json = json.dumps(changed_setup, sort_keys=True, separators=(",", ":"))
            db.execute("UPDATE story_production_setups SET setup_json=? WHERE workspace_id='workspace-a'", (changed_json,))
            db.execute("UPDATE story_prompt_drafts SET setup_hash=?,drafts_json=? WHERE workspace_id='workspace-a'",
                (hashlib.sha256(changed_json.encode()).hexdigest(), json.dumps({"1.1":{"workflow_id":request()["workflow_id"],"prompt":"Edited prompt after queue."}}, separators=(",", ":"))))
        replay = jobs.start_fully_automated_first_clip("workspace-a", "screenplay-a")
        recovered = jobs.get_fully_automated_first_clip("workspace-a", "screenplay-a")
        self.assertEqual(replay["job"]["job_id"], started["job"]["job_id"])
        self.assertEqual(recovered["job"]["job_id"], started["job"]["job_id"])
        self.assertEqual(recovered["idempotency_key"], started["job"]["idempotency_key"])
        by_key = jobs.get_by_idempotency_key(workspace_id="workspace-a", idempotency_key=recovered["idempotency_key"])
        self.assertEqual(by_key["job_id"], started["job"]["job_id"])
        self.assertEqual(recovered["job"]["request"]["prompt"], "Saved first scene prompt.")
        self.assertEqual(recovered["job"]["request"]["duration_seconds"], 7)
        with jobs.ledger._connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM production_takes WHERE project_id='workspace-a'").fetchone()[0], 1)

    def test_full_run_status_exposes_safe_identity_review_without_private_paths(self):
        jobs = self.fully_automated_jobs()
        started = jobs.start_fully_automated_first_clip("workspace-a", "screenplay-a")
        job_id = started["job"]["job_id"]
        with jobs.ledger._connect() as db:
            db.execute("""CREATE TABLE fully_automated_identity_reviews (
                review_id TEXT PRIMARY KEY, workspace_id TEXT, screenplay_revision_id TEXT,
                scene_number INTEGER, source_job_id TEXT, source_asset_id TEXT, source_sha256 TEXT,
                input_json TEXT, state TEXT, attempt_count INTEGER, owner_token TEXT, lease_until TEXT,
                result_json TEXT, error_message TEXT, updated_at TEXT)""")
            db.execute("""INSERT INTO fully_automated_identity_reviews
                (review_id,workspace_id,screenplay_revision_id,scene_number,source_job_id,
                 source_asset_id,source_sha256,input_json,state,result_json,updated_at)
                VALUES('review-1','workspace-a','screenplay-a',1,?,'asset-1',? ,?,'complete',?,'now')""",
                (job_id, "a" * 64, json.dumps({"characters":[{"character_id":"char-1",
                    "name":"Mira","reference_path":"/private/data/portrait.png"}]}),
                 json.dumps({"frames":[{"sample_index":1,"timestamp_seconds":2.5,
                    "observations":[{"status":"candidate_match","character_id":"char-1",
                        "visual_evidence":"Red jacket visible"}]}]})))

        clip = jobs.get_fully_automated_first_clip("workspace-a", "screenplay-a")["clips"][0]
        self.assertEqual(clip["identity_review"]["state"], "complete")
        self.assertEqual(clip["identity_review"]["frames"][0]["observations"][0]["character_name"], "Mira")
        self.assertNotIn("reference_path", json.dumps(clip["identity_review"]))

    def test_fully_automated_start_prepares_and_saves_missing_first_prompt(self):
        jobs = self.fully_automated_jobs()
        with sqlite3.connect(self.db_path) as db:
            db.execute("UPDATE story_prompt_drafts SET drafts_json='{}' WHERE workspace_id='workspace-a'")

        class PromptPreparer:
            def __init__(self):
                self.prepared = []
                self.saved = []
            def prepare(self, workspace, revision, shot_key, workflow_id, *, setup_snapshot=None):
                self.prepared.append((workspace, revision, shot_key, workflow_id))
                return {"workflow_id": workflow_id, "prompt": "Prepared only when the owner starts the Full run."}
            def save_shot(self, workspace, revision, setup, shot_key, draft):
                self.saved.append((workspace, revision, shot_key))
                with jobs.ledger._connect() as db:
                    row = db.execute("SELECT drafts_json FROM story_prompt_drafts WHERE workspace_id=? AND screenplay_revision_id=?",
                        (workspace, revision)).fetchone()
                    drafts = json.loads(row["drafts_json"])
                    drafts[shot_key] = draft
                    db.execute("UPDATE story_prompt_drafts SET drafts_json=? WHERE workspace_id=? AND screenplay_revision_id=?",
                        (json.dumps(drafts, sort_keys=True), workspace, revision))

        preparer = PromptPreparer()
        jobs.prompt_drafts = preparer
        started = jobs.start_fully_automated_first_clip("workspace-a", "screenplay-a")

        self.assertEqual(started["run_state"], "first_clip_queued")
        self.assertEqual(started["job"]["request"]["prompt"], "Prepared only when the owner starts the Full run.")
        self.assertEqual(preparer.prepared, [("workspace-a", "screenplay-a", "1.1", request()["workflow_id"])])
        self.assertEqual(preparer.saved, [("workspace-a", "screenplay-a", "1.1")])
        with sqlite3.connect(self.db_path) as db:
            saved = json.loads(db.execute("SELECT drafts_json FROM story_prompt_drafts WHERE workspace_id='workspace-a'").fetchone()[0])
        self.assertEqual(saved["1.1"]["prompt"], "Prepared only when the owner starts the Full run.")

    def test_global_style_analysis_does_not_attach_video_or_force_r2v(self):
        jobs = self.fully_automated_jobs()
        jobs.r2v_capability_provider = lambda: {"available": True}
        setup = {"mode": "fully_automated", "automate_steps": {"character_images": False,
            "character_voice": False, "world_images": False, "frame_images": False, "video": False},
            "video_quality": "standard", "duration_policy": {"kind": "fixed", "seconds": 7},
            "style_video_references": [{"asset_id": "pa-0123456789abcdef", "sha256": "a" * 64,
                "intent": "Match its cool palette."}]}
        encoded = json.dumps(setup, sort_keys=True, separators=(",", ":"))
        setup_hash = hashlib.sha256(encoded.encode()).hexdigest()
        with sqlite3.connect(self.db_path) as db:
            db.execute("UPDATE story_production_setups SET setup_json=? WHERE workspace_id='workspace-a'", (encoded,))
            db.execute("UPDATE story_prompt_drafts SET setup_hash=?,drafts_json=? WHERE workspace_id='workspace-a'",
                (setup_hash, json.dumps({"1.1": {"workflow_id": request()["workflow_id"],
                    "prompt": "Opening shot with cool palette."}})))

        started = jobs.start_fully_automated_first_clip("workspace-a", "screenplay-a")

        self.assertEqual(started["job"]["request"]["workflow_id"], request()["workflow_id"])
        self.assertEqual(started["job"]["request"].get("videos", []), [])
        self.assertNotIn("<Video", started["job"]["request"]["prompt"])

    def test_fully_automated_run_retains_style_and_scene_continuity_references(self):
        style_reference = {"asset_id": "pa-0123456789abcdef", "sha256": "a" * 64,
            "intent": "Keep the cool palette throughout the story."}
        jobs = self.fully_automated_jobs(
            style_video_references=[style_reference])
        jobs.r2v_capability_provider = lambda: {"available": True}
        screenplay = {"scenes": [
            {"scene_number": 1, "slugline": "INT. ROOM", "summary": "A room.", "shots": [{"shot_number": 1, "evidence_record_ids": ["e-1-1"]}, {"shot_number": 2, "evidence_record_ids": ["e-1-2"]}]},
            {"scene_number": 2, "slugline": "EXT. STREET", "summary": "A street.", "shots": [{"shot_number": 1, "evidence_record_ids": ["e-2-1"]}]},
        ]}
        drafts = {
            "1.1": {"workflow_id": request()["workflow_id"], "prompt": "Opening shot.",
                "knowledge_ref": {"knowledge_id":"minimax-h3-r2v", "guidance_version":2, "workflow_sha256":"b" * 64}},
            "1.2": {"workflow_id": "minimax_h3_r2v_dynamic_v1", "prompt": "Continue the action.",
                "knowledge_ref": {"knowledge_id":"minimax-h3-r2v", "guidance_version":2, "workflow_sha256":"b" * 64}},
            "2.1": {"workflow_id": request()["workflow_id"], "prompt": "Begin the next scene.",
                "knowledge_ref": {"knowledge_id":"minimax-h3-r2v", "guidance_version":2, "workflow_sha256":"b" * 64}},
        }
        with sqlite3.connect(self.db_path) as db:
            db.execute("UPDATE story_screenplay_revisions SET screenplay_json=? WHERE screenplay_revision_id='screenplay-a'",
                (json.dumps(screenplay),))
            db.execute("UPDATE story_prompt_drafts SET drafts_json=? WHERE workspace_id='workspace-a'",
                (json.dumps(drafts),))
        first = jobs.start_fully_automated_first_clip("workspace-a", "screenplay-a")
        self.assertEqual(jobs.get_fully_automated_first_clip("workspace-a", "screenplay-a")["planned_count"], 2)
        changed_setup = {"mode":"fully_automated","automate_steps":{"character_images":False,"character_voice":False,"world_images":False,"frame_images":False,"video":False},"video_quality":"high","duration_policy":{"kind":"fixed","seconds":9}}
        with sqlite3.connect(self.db_path) as db:
            db.execute("UPDATE story_production_setups SET setup_json=? WHERE workspace_id='workspace-a'", (json.dumps(changed_setup),))
            db.execute("UPDATE story_prompt_drafts SET drafts_json=? WHERE workspace_id='workspace-a'",
                (json.dumps({key: {**draft, "prompt": "Edited after run start."} for key, draft in drafts.items()}),))

        def complete(job):
            output = {"asset_id": f"asset_{job['job_id'][:20]}", "shared_asset_id": "video_" + hashlib.sha256(job["job_id"].encode()).hexdigest()[:32],
                "kind": "video", "sha256": hashlib.sha256((job["job_id"] + "output").encode()).hexdigest(), "has_video": True}
            with sqlite3.connect(self.db_path) as db:
                db.execute("UPDATE production_takes SET status='needs_review',output_hashes_json=? WHERE job_id=?",
                    (json.dumps([output]), job["job_id"]))
            return output

        complete(first["job"])
        waiting = jobs.advance_fully_automated_run("workspace-a", "screenplay-a", readiness=lambda _: {"available": False, "reason": "R2V model unavailable."})
        self.assertEqual(waiting["status"], "waiting_for_readiness")
        self.assertEqual(len(jobs.get_fully_automated_first_clip("workspace-a", "screenplay-a")["clips"]), 1)
        second = jobs.advance_fully_automated_run("workspace-a", "screenplay-a", readiness=lambda _: {"available": True})
        self.assertEqual(second["status"], "queued")
        self.assertEqual(second["job"]["request"]["workflow_id"], "minimax_h3_r2v_dynamic_v1")
        self.assertEqual(second["job"]["request"]["videos"], [])
        self.assertEqual(second["job"]["request"]["images"][-1]["role"], "continuity")
        self.assertIn("<Picture 1>", second["job"]["request"]["prompt"])
        self.assertEqual(second["job"]["source_lineage"]["scene_number"], 1)
        self.assertEqual(second["job"]["source_lineage"]["knowledge_ref"], drafts["1.2"]["knowledge_ref"])
        self.assertIn("Continue the action.", second["job"]["request"]["prompt"])
        self.assertNotIn("Edited after run start.", second["job"]["request"]["prompt"])
        self.assertEqual(second["job"]["request"]["duration_seconds"], 7)
        complete(second["job"])
        self.assertEqual(jobs.get_fully_automated_first_clip("workspace-a", "screenplay-a")["planned_count"], 2)
        third = jobs.advance_fully_automated_run("workspace-a", "screenplay-a", readiness=lambda _: {"available": True})
        self.assertEqual(third["status"], "queued")
        self.assertEqual(third["job"]["request"]["workflow_id"], request()["workflow_id"])
        self.assertEqual(third["job"]["request"].get("videos", []), [])
        self.assertEqual(third["job"]["source_lineage"]["scene_number"], 2)
        complete(third["job"])
        final = jobs.advance_fully_automated_run("workspace-a", "screenplay-a", readiness=lambda _: {"available": True})
        self.assertEqual(final["status"], "completed")
        state = jobs.get_fully_automated_first_clip("workspace-a", "screenplay-a")
        self.assertEqual(state["run_state"], "completed")
        self.assertEqual(state["completed_count"], 3)
        self.assertEqual(len(state["clips"]), 3)
        self.assertEqual(jobs.advance_fully_automated_run("workspace-a", "screenplay-a")["status"], "completed")

    def test_fully_automated_prepares_later_scene_prompt_only_when_scene_is_reached(self):
        jobs = self.fully_automated_jobs()
        screenplay = {"scenes": [
            {"scene_number": 1, "shots": [{"shot_number": 1, "action": "Begins.", "dialogue": "", "evidence_record_ids": ["e-1"]}]},
            {"scene_number": 2, "shots": [{"shot_number": 1, "action": "Continues.", "dialogue": "", "evidence_record_ids": ["e-2"]}]},
        ]}
        with sqlite3.connect(self.db_path) as db:
            db.execute("UPDATE story_screenplay_revisions SET screenplay_json=? WHERE screenplay_revision_id='screenplay-a'", (json.dumps(screenplay),))

        class PromptPreparer:
            def __init__(self):
                self.calls = []
            def prepare(self, workspace, revision, shot_key, workflow_id, *, setup_snapshot=None):
                self.calls.append((shot_key, workflow_id))
                self.setup_snapshot = setup_snapshot
                return {"workflow_id": workflow_id, "prompt": f"Prepared scene shot {shot_key}."}

        preparer = PromptPreparer()
        jobs.prompt_drafts = preparer
        first = jobs.start_fully_automated_first_clip("workspace-a", "screenplay-a")
        self.assertEqual(preparer.calls, [])
        self.assertEqual(jobs.get_fully_automated_first_clip("workspace-a", "screenplay-a")["planned_count"], 1)
        output = {"asset_id": "first", "shared_asset_id": "shared-first", "kind": "video",
            "sha256": hashlib.sha256(b"first").hexdigest(), "has_video": True}
        with sqlite3.connect(self.db_path) as db:
            db.execute("UPDATE production_takes SET status='needs_review',output_hashes_json=? WHERE job_id=?",
                (json.dumps([output]), first["job"]["job_id"]))
        next_clip = jobs.advance_fully_automated_run("workspace-a", "screenplay-a",
            readiness=lambda _: {"available": True})
        self.assertEqual(next_clip["status"], "queued")
        self.assertEqual(preparer.calls, [("2.1", request()["workflow_id"])])
        self.assertEqual(preparer.setup_snapshot["video_quality"], "standard")
        state = jobs.get_fully_automated_first_clip("workspace-a", "screenplay-a")
        self.assertEqual(state["planned_count"], 2)
        with jobs.ledger._connect() as db:
            run = db.execute("SELECT manifest_json FROM fully_automated_runs WHERE workspace_id='workspace-a'").fetchone()
        manifest = json.loads(run["manifest_json"])
        self.assertEqual(manifest["drafts"]["2.1"]["prompt"], "Prepared scene shot 2.1.")

    def test_fully_automated_paused_scene_planning_can_resume_without_rerendering_completed_clip(self):
        jobs = self.fully_automated_jobs()
        screenplay = {"scenes": [
            {"scene_number": 1, "shots": [{"shot_number": 1, "action": "Begins.", "dialogue": "", "evidence_record_ids": ["e-1"]}]},
            {"scene_number": 2, "shots": [{"shot_number": 1, "action": "Continues.", "dialogue": "", "evidence_record_ids": ["e-2"]}]},
        ]}
        with sqlite3.connect(self.db_path) as db:
            db.execute("UPDATE story_screenplay_revisions SET screenplay_json=? WHERE screenplay_revision_id='screenplay-a'", (json.dumps(screenplay),))

        class PromptPreparer:
            failed = False
            def prepare(self, workspace, revision, shot_key, workflow_id, *, setup_snapshot=None):
                if shot_key == "2.1" and not self.failed:
                    self.failed = True
                    raise ValueError("Temporary next-scene planning failure.")
                return {"workflow_id": workflow_id, "prompt": f"Prepared {shot_key}."}

        jobs.prompt_drafts = PromptPreparer()
        first = jobs.start_fully_automated_first_clip("workspace-a", "screenplay-a")
        output = {"asset_id": "first", "shared_asset_id": "shared-first", "kind": "video",
            "sha256": hashlib.sha256(b"first").hexdigest(), "has_video": True}
        with sqlite3.connect(self.db_path) as db:
            db.execute("UPDATE production_takes SET status='needs_review',output_hashes_json=? WHERE job_id=?",
                (json.dumps([output]), first["job"]["job_id"]))

        failed = jobs.advance_fully_automated_run("workspace-a", "screenplay-a",
            readiness=lambda _: {"available": True})
        paused = jobs.get_fully_automated_first_clip("workspace-a", "screenplay-a")
        self.assertEqual(failed["status"], "paused")
        self.assertTrue(paused["resume_available"])
        self.assertEqual(paused["clips"][0]["job"]["job_id"], first["job"]["job_id"])

        resumed = jobs.resume_fully_automated_planning("workspace-a", "screenplay-a")
        self.assertEqual(resumed["run_state"], "first_clip_queued")
        next_clip = jobs.advance_fully_automated_run("workspace-a", "screenplay-a",
            readiness=lambda _: {"available": True})

        self.assertEqual(next_clip["status"], "queued")
        state = jobs.get_fully_automated_first_clip("workspace-a", "screenplay-a")
        self.assertEqual(len(state["clips"]), 2)
        self.assertEqual(state["clips"][0]["job"]["job_id"], first["job"]["job_id"])
        self.assertEqual(state["clips"][1]["job"]["request"]["prompt"], "Prepared 2.1.")
        with jobs.ledger._connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM production_takes WHERE project_id='workspace-a'").fetchone()[0], 2)

    def test_fully_automated_planning_resume_rejects_failed_clip(self):
        jobs = self.fully_automated_jobs()
        first = jobs.start_fully_automated_first_clip("workspace-a", "screenplay-a")
        with jobs.ledger._connect() as db:
            db.execute("UPDATE fully_automated_runs SET run_state='paused' WHERE workspace_id='workspace-a'")
        with self.assertRaises(IsolatedJobConflict):
            jobs.resume_fully_automated_planning("workspace-a", "screenplay-a")

    def test_fully_automated_preserves_style_provenance_from_fresh_prompt(self):
        jobs = self.fully_automated_jobs()
        style_ref = {"snapshot_id": "style-snapshot-a", "style_version_id": "style-v2",
            "narrative_hash": "b" * 64, "director_profile_hash": "c" * 64,
            "directing_style_hash": "d" * 64}
        with sqlite3.connect(self.db_path) as db:
            db.execute("UPDATE story_prompt_drafts SET drafts_json='{}' WHERE workspace_id='workspace-a'")

        class PromptPreparer:
            def prepare(self, workspace, revision, shot_key, workflow_id, **kwargs):
                return {"workflow_id": workflow_id, "prompt": "Prepared from the selected style.",
                    "style_ref": style_ref}

            def save_shot(self, workspace, revision, setup, shot_key, draft):
                with jobs.ledger._connect() as db:
                    row = db.execute("SELECT drafts_json FROM story_prompt_drafts WHERE workspace_id=? AND screenplay_revision_id=?",
                        (workspace, revision)).fetchone()
                    drafts = json.loads(row["drafts_json"])
                    drafts[shot_key] = draft
                    db.execute("UPDATE story_prompt_drafts SET drafts_json=? WHERE workspace_id=? AND screenplay_revision_id=?",
                        (json.dumps(drafts, sort_keys=True), workspace, revision))

        jobs.prompt_drafts = PromptPreparer()
        started = jobs.start_fully_automated_first_clip("workspace-a", "screenplay-a")
        self.assertEqual(started["job"]["source_lineage"]["style_ref"], style_ref)
        with sqlite3.connect(self.db_path) as db:
            saved = json.loads(db.execute("SELECT drafts_json FROM story_prompt_drafts WHERE workspace_id='workspace-a'").fetchone()[0])
            run = json.loads(db.execute("SELECT manifest_json FROM fully_automated_runs WHERE workspace_id='workspace-a'").fetchone()[0])
        self.assertEqual(saved["1.1"]["style_ref"], style_ref)
        self.assertEqual(run["drafts"]["1.1"]["style_ref"], style_ref)

    def test_full_run_waits_for_same_job_during_submission_recovery(self):
        jobs = self.fully_automated_jobs()
        started = jobs.start_fully_automated_first_clip("workspace-a", "screenplay-a")
        job_id = started["job"]["job_id"]
        for status in ("recovery_required", "running"):
            with jobs.ledger._connect() as db:
                db.execute("UPDATE production_takes SET status=? WHERE job_id=?", (status, job_id))
            result = jobs.advance_fully_automated_run("workspace-a", "screenplay-a", readiness=lambda _: {"available": True})
            self.assertEqual(result["status"], "waiting")
            self.assertEqual(result["job"]["job_id"], job_id)
            with jobs.ledger._connect() as db:
                self.assertEqual(db.execute("SELECT run_state FROM fully_automated_runs WHERE workspace_id='workspace-a'").fetchone()[0], "running")
                self.assertEqual(db.execute("SELECT COUNT(*) FROM production_takes WHERE project_id='workspace-a'").fetchone()[0], 1)

    def test_fully_automated_run_pauses_after_failed_clip_without_successor(self):
        jobs = self.fully_automated_jobs()
        jobs.r2v_capability_provider = lambda: {"available": True}
        screenplay = {"scenes": [{"scene_number": 1, "slugline": "INT. ROOM", "summary": "A room.", "shots": [{"shot_number": 1, "evidence_record_ids": ["e-1-1"]}, {"shot_number": 2, "evidence_record_ids": ["e-1-2"]}]}]}
        with sqlite3.connect(self.db_path) as db:
            db.execute("UPDATE story_screenplay_revisions SET screenplay_json=? WHERE screenplay_revision_id='screenplay-a'", (json.dumps(screenplay),))
            db.execute("UPDATE story_prompt_drafts SET drafts_json=? WHERE workspace_id='workspace-a'", (json.dumps({
                "1.1": {"workflow_id": request()["workflow_id"], "prompt": "Opening shot."},
                "1.2": {"workflow_id": "minimax_h3_r2v_dynamic_v1", "prompt": "Continue the action."}}),))
        started = jobs.start_fully_automated_first_clip("workspace-a", "screenplay-a")
        with jobs.ledger._connect() as db:
            db.execute("UPDATE production_takes SET status='failed',error_json=? WHERE job_id=?",
                       (json.dumps({"message": "worker failure"}), started["job"]["job_id"]))

        result = jobs.advance_fully_automated_run("workspace-a", "screenplay-a", readiness=lambda _: {"available": True})

        self.assertEqual(result["status"], "paused")
        self.assertEqual(result["job"]["error"]["message"], "worker failure")
        with jobs.ledger._connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM production_takes WHERE project_id='workspace-a'").fetchone()[0], 1)
            self.assertEqual(db.execute("SELECT run_state FROM fully_automated_runs WHERE workspace_id='workspace-a'").fetchone()[0], "paused")
        original_lookup = jobs.get_by_idempotency_key
        lookup_barrier = Barrier(2)
        def concurrent_lookup(*, workspace_id, idempotency_key):
            try:
                return original_lookup(workspace_id=workspace_id, idempotency_key=idempotency_key)
            except Exception as exc:
                if idempotency_key.startswith("fullretry-") and isinstance(exc, LedgerNotFound):
                    lookup_barrier.wait(timeout=5)
                raise
        jobs.get_by_idempotency_key = concurrent_lookup
        with ThreadPoolExecutor(max_workers=2) as executor:
            retry_calls = [executor.submit(jobs.retry_fully_automated_shot, "workspace-a", "screenplay-a", 1, 1,
                readiness=lambda workflow: {"available": True}) for _ in range(2)]
            retried, replay = [future.result(timeout=10) for future in retry_calls]
        del jobs.get_by_idempotency_key
        recovered = jobs.retry_fully_automated_shot("workspace-a", "screenplay-a", 1, 1,
            readiness=lambda workflow: (_ for _ in ()).throw(AssertionError("recovery must precede readiness checks")))
        self.assertEqual(recovered["job"]["job_id"], retried["job"]["job_id"])
        self.assertEqual(retried["job"]["job_id"], replay["job"]["job_id"])
        self.assertEqual(retried["job"]["job_id"], retried["run"]["clips"][0]["job"]["job_id"])
        history = retried["run"]["clips"][0]["attempts"]
        self.assertEqual([(attempt["attempt_number"], attempt["job"]["status"]) for attempt in history], [(1, "failed"), (2, "queued")])
        self.assertEqual(history[0]["job"]["job_id"], started["job"]["job_id"])
        with jobs.ledger._connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM production_takes WHERE project_id='workspace-a'").fetchone()[0], 2)

        retry_output = {"asset_id": "retry-output", "shared_asset_id": "retry-video", "kind": "video",
            "sha256": hashlib.sha256(b"retry-output").hexdigest(), "has_video": True}
        with jobs.ledger._connect() as db:
            db.execute("UPDATE production_takes SET status='needs_review',output_hashes_json=? WHERE job_id=?",
                (json.dumps([retry_output]), retried["job"]["job_id"]))
        successor = jobs.advance_fully_automated_run("workspace-a", "screenplay-a", readiness=lambda _: {"available": True})
        self.assertEqual(successor["status"], "queued")
        self.assertEqual(successor["job"]["request"]["images"][0]["asset_id"], "pa-aaaaaaaaaaaaaaaa")
        self.assertEqual(successor["job"]["request"]["videos"], [])
        self.assertEqual(successor["job"]["request"]["images"][-1]["sha256"], retry_output["sha256"])
        self.assertEqual(len(jobs.get_fully_automated_first_clip("workspace-a", "screenplay-a")["clips"]), 2)

    def test_full_retry_keeps_frozen_r2v_request_when_new_identity_review_arrives(self):
        from story_builder.services.fully_automated_identity import IdentityReviewStore

        jobs = self.fully_automated_jobs()
        jobs.r2v_capability_provider = lambda: {"available": True}
        jobs.media_root = Path(self.temporary.name)
        screenplay = {"scenes": [{"scene_number": 1, "shots": [
            {"shot_number": 1, "action": "The guard enters.", "dialogue": "", "evidence_record_ids": ["e-1"]},
            {"shot_number": 2, "action": "He turns toward the door.", "dialogue": "", "evidence_record_ids": ["e-2"],
                "character_record_ids": ["char-guard"]},
        ]}]}
        with sqlite3.connect(self.db_path) as db:
            db.execute("UPDATE story_screenplay_revisions SET screenplay_json=? WHERE screenplay_revision_id='screenplay-a'",
                (json.dumps(screenplay),))
            db.execute("UPDATE story_prompt_drafts SET drafts_json=? WHERE workspace_id='workspace-a'", (json.dumps({
                "1.1": {"workflow_id": request()["workflow_id"], "prompt": "The guard enters."},
                "1.2": {"workflow_id": "minimax_h3_r2v_dynamic_v1", "prompt": "He turns toward the door."},
            }),))

        first = jobs.start_fully_automated_first_clip("workspace-a", "screenplay-a")
        first_output = {"asset_id": "first", "shared_asset_id": "video-first", "kind": "video",
            "sha256": hashlib.sha256(b"first-video").hexdigest(), "has_video": True}
        with sqlite3.connect(self.db_path) as db:
            db.execute("UPDATE production_takes SET status='needs_review',output_hashes_json=? WHERE job_id=?",
                (json.dumps([first_output]), first["job"]["job_id"]))
        second = jobs.advance_fully_automated_run("workspace-a", "screenplay-a",
            readiness=lambda _: {"available": True})
        self.assertEqual(second["job"]["request"]["workflow_id"], "minimax_h3_r2v_dynamic_v1")
        with sqlite3.connect(self.db_path) as db:
            db.execute("UPDATE production_takes SET status='failed',error_json=? WHERE job_id=?",
                (json.dumps({"message": "worker failure"}), second["job"]["job_id"]))
        paused = jobs.advance_fully_automated_run("workspace-a", "screenplay-a",
            readiness=lambda _: {"available": True})
        self.assertEqual(paused["status"], "paused")

        IdentityReviewStore(self.db_path)
        crop = Path(self.temporary.name) / "guard.png"
        crop.write_bytes(b"new identity crop")
        crop_digest = hashlib.sha256(crop.read_bytes()).hexdigest()
        with jobs.ledger._connect() as db:
            db.execute("INSERT INTO fully_automated_identity_reviews(review_id,workspace_id,screenplay_revision_id,scene_number,source_job_id,source_asset_id,source_sha256,input_json,state,result_json,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                ("review-first", "workspace-a", "screenplay-a", 1, first["job"]["job_id"],
                 "source-video", "a" * 64, json.dumps({"characters": [{"character_id": "char-guard", "name": "Guard"}]}),
                 "complete", json.dumps({"derived_references": [{"character_id": "char-guard", "asset_id": "guard-crop",
                     "sha256": crop_digest}]}), "now"))
        with patch("story_builder.services.media_library.asset_path",
                   return_value=(crop, "image/png", crop.name)):
            retried = jobs.retry_fully_automated_shot("workspace-a", "screenplay-a", 1, 2,
                readiness=lambda _: {"available": True})

        self.assertEqual(retried["job"]["request"], second["job"]["request"])
        self.assertEqual(retried["job"]["request"]["images"][-1]["role"], "continuity")
        self.assertEqual(len(retried["job"]["request"]["images"]), 1)

    def test_fully_automated_duration_plan_splits_shot_and_freezes_clip_order(self):
        jobs = self.fully_automated_jobs(duration_policy={"kind": "director_selected", "min_seconds": 5, "max_seconds": 10})
        jobs.r2v_capability_provider = lambda: {"available": True}
        screenplay = {"scenes": [
            {"scene_number": 1, "shots": [
                {"shot_number": 1, "action": "Enters room. Sits down.", "dialogue": "", "evidence_record_ids": ["e-1"]},
                {"shot_number": 2, "action": "Opens the door.", "dialogue": "", "evidence_record_ids": ["e-2"]}]},
            {"scene_number": 2, "shots": [
                {"shot_number": 1, "action": "Walks outside.", "dialogue": "", "evidence_record_ids": ["e-3"]}]}]}
        drafts = {"1.1": {"workflow_id": request()["workflow_id"], "prompt": "Guard enters and sits."},
            "1.2": {"workflow_id": "minimax_h3_r2v_dynamic_v1", "prompt": "Door opens."},
            "2.1": {"workflow_id": request()["workflow_id"], "prompt": "Outside."}}
        with sqlite3.connect(self.db_path) as db:
            db.execute("UPDATE story_screenplay_revisions SET screenplay_json=? WHERE screenplay_revision_id='screenplay-a'", (json.dumps(screenplay),))
            db.execute("UPDATE story_prompt_drafts SET drafts_json=? WHERE workspace_id='workspace-a'", (json.dumps(drafts),))

        def split_first_action(*, prompt, temperature):
            payload = json.loads(prompt.split("INPUT JSON:\n", 1)[1])
            scene = payload["scene"]
            rows = []
            for shot in scene["shots"]:
                key = f"{scene['scene_number']}.{shot['shot_number']}"
                source = shot["action"]
                spans = []
                prompt_text = payload["saved_workflow_prompts"][key]["prompt"]
                if scene["scene_number"] == 1 and shot["shot_number"] == 1:
                    split = source.index(" Sits")
                    segments = [(0, split, "Guard enters the room."), (split, len(source), "Guard sits down.")]
                else:
                    segments = [(0, len(source), prompt_text)]
                for start, end, clip_prompt in segments:
                    rows.append({"scene_number": scene["scene_number"], "shot_number": shot["shot_number"],
                        "duration_seconds": 5 + len(rows), "duration_reason": "Keep the action readable.",
                        "prompt": clip_prompt, "source_spans": [{"field": "action", "start": start, "end": end}]})
            return {"clips": rows}
        jobs.full_clip_plan_provider = split_first_action
        frozen_plan = jobs._fully_automated_first_clip_input("workspace-a", "screenplay-a")["run_manifest"]["clip_plan"]["clips"]
        started = jobs.start_fully_automated_first_clip("workspace-a", "screenplay-a")
        self.assertEqual(started["job"]["request"]["workflow_id"], request()["workflow_id"])
        self.assertEqual(started["job"]["request"]["duration_seconds"], 5)
        self.assertEqual(started["clip_id"], frozen_plan[0]["clip_id"])

        output = {"asset_id": "first", "shared_asset_id": "shared-first", "kind": "video",
            "sha256": hashlib.sha256(b"first").hexdigest(), "has_video": True}
        with sqlite3.connect(self.db_path) as db:
            db.execute("UPDATE production_takes SET status='needs_review',output_hashes_json=? WHERE job_id=?",
                (json.dumps([output]), started["job"]["job_id"]))
        self.assertEqual(jobs.get_fully_automated_first_clip("workspace-a", "screenplay-a")["planned_count"], 3)
        next_clip = jobs.advance_fully_automated_run("workspace-a", "screenplay-a",
            readiness=lambda workflow: {"available": True})
        self.assertEqual(next_clip["status"], "queued")
        self.assertEqual(next_clip["job"]["clip_id"], frozen_plan[1]["clip_id"])
        self.assertEqual(next_clip["job"]["request"]["workflow_id"], "minimax_h3_r2v_dynamic_v1")
        self.assertEqual(next_clip["job"]["request"]["duration_seconds"], 6)
        self.assertEqual(next_clip["job"]["request"]["images"][0]["asset_id"], "pa-aaaaaaaaaaaaaaaa")
        state = jobs.get_fully_automated_first_clip("workspace-a", "screenplay-a")
        self.assertEqual(state["planned_count"], 3)
        self.assertEqual([(row["scene_number"], row["shot_number"], row["clip_number"]) for row in state["clips"]], [(1, 1, 1), (1, 1, 2)])

    def test_fully_automated_first_clip_rejects_stale_or_unsupported_inputs_before_queue(self):
        jobs = self.fully_automated_jobs(duration_policy={"kind":"director_selected","min_seconds":5,"max_seconds":10})
        planned = jobs._fully_automated_first_clip_input("workspace-a", "screenplay-a")
        self.assertGreaterEqual(planned["request"]["duration_seconds"], 5)
        self.assertLessEqual(planned["request"]["duration_seconds"], 10)
        self.assertEqual(len(planned["run_manifest"]["clip_plan"]["clips"]), 1)
        with jobs.ledger._connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM production_takes WHERE project_id='workspace-a'").fetchone()[0], 0)
        jobs = self.fully_automated_jobs(workflow="minimax_h3_r2v_dynamic_v1")
        with self.assertRaisesRegex(IsolatedJobConflict, "must use minimax_h3_t2v_local_v1"):
            jobs.start_fully_automated_first_clip("workspace-a", "screenplay-a")
        with jobs.ledger._connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM production_takes WHERE project_id='workspace-a'").fetchone()[0], 0)
        jobs = self.fully_automated_jobs()
        with sqlite3.connect(self.db_path) as db:
            db.execute("UPDATE story_workspaces SET current_revision_id='source-b' WHERE workspace_id='workspace-a'")
        with self.assertRaisesRegex(IsolatedJobConflict, "current accepted screenplay"):
            jobs.start_fully_automated_first_clip("workspace-a", "screenplay-a")

    def test_full_run_status_read_does_not_request_an_ephemeral_clip_plan(self):
        jobs = self.fully_automated_jobs()
        jobs.full_clip_plan_provider = lambda **_: (_ for _ in ()).throw(AssertionError("status reads must not call the model"))
        state = jobs.get_fully_automated_first_clip("workspace-a", "screenplay-a")
        self.assertEqual(state["run_state"], "not_started")
        self.assertIsNone(state["planned_count"])

    def test_fully_automated_preflights_every_shot_route_and_final_r2v_prompt_budget(self):
        jobs = self.fully_automated_jobs()
        screenplay = {"scenes": [{"scene_number": 1, "shots": [{"shot_number": 1, "evidence_record_ids": ["e-1-1"]}, {"shot_number": 2, "evidence_record_ids": ["e-1-2"]}]}]}
        with sqlite3.connect(self.db_path) as db:
            db.execute("UPDATE story_screenplay_revisions SET screenplay_json=? WHERE screenplay_revision_id='screenplay-a'", (json.dumps(screenplay),))
            db.execute("UPDATE story_prompt_drafts SET drafts_json=? WHERE workspace_id='workspace-a'", (json.dumps({
                "1.1": {"workflow_id": request()["workflow_id"], "prompt": "First prompt."},
                "1.2": {"workflow_id": "minimax_h3_t2v_local_v1", "prompt": "Wrong route."}},),))
        with self.assertRaisesRegex(IsolatedJobConflict, "must use minimax_h3_r2v_dynamic_v1"):
            jobs.start_fully_automated_first_clip("workspace-a", "screenplay-a")
        with sqlite3.connect(self.db_path) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM production_takes WHERE project_id='workspace-a'").fetchone()[0], 0)

        prefix = "<Video 1> Continue the immediately preceding clip as the visual continuity reference.\n\n"
        overlong = "x" * (7000 - len(prefix))
        with sqlite3.connect(self.db_path) as db:
            db.execute("UPDATE story_prompt_drafts SET drafts_json=? WHERE workspace_id='workspace-a'", (json.dumps({
                "1.1": {"workflow_id": request()["workflow_id"], "prompt": "First prompt."},
                "1.2": {"workflow_id": "minimax_h3_r2v_dynamic_v1", "prompt": overlong}},),))
        with self.assertRaisesRegex(ValueError, "6,999-character limit"):
            jobs.start_fully_automated_first_clip("workspace-a", "screenplay-a")
        with sqlite3.connect(self.db_path) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM production_takes WHERE project_id='workspace-a'").fetchone()[0], 0)

    def test_fully_automated_admission_rechecks_full_frozen_snapshot_in_queue_transaction(self):
        jobs = self.fully_automated_jobs()
        derive = jobs._fully_automated_first_clip_input

        def derive_then_change_later_prompt(workspace_id, revision_id):
            snapshot = derive(workspace_id, revision_id)
            with sqlite3.connect(self.db_path) as db:
                db.execute("UPDATE story_prompt_drafts SET drafts_json=? WHERE workspace_id='workspace-a'",
                    (json.dumps({"1.1": {"workflow_id": request()["workflow_id"], "prompt": "Changed during admission."}}),))
            return snapshot

        jobs._fully_automated_first_clip_input = derive_then_change_later_prompt
        with self.assertRaisesRegex(IsolatedJobConflict, "changed during Full-run admission"):
            jobs.start_fully_automated_first_clip("workspace-a", "screenplay-a")
        with sqlite3.connect(self.db_path) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM production_takes WHERE project_id='workspace-a'").fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM fully_automated_runs WHERE workspace_id='workspace-a'").fetchone()[0], 0)
        with jobs.ledger._connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM production_takes WHERE project_id='workspace-a'").fetchone()[0], 0)

    def test_release_unsubmitted_attempt_fences_late_submission_and_keeps_new_draft_usable(self):
        from story_builder.services.minimax_h3_t2v import T2V_GRAPH_PATH
        self.jobs.graph_path = T2V_GRAPH_PATH
        self.assertEqual(self.jobs.release_attempt(workspace_id="workspace-a", idempotency_key="old"), {"released":True})
        self.assertEqual(self.jobs.release_attempt(workspace_id="workspace-a", idempotency_key="old"), {"released":True})
        with self.assertRaises(StoryHandoffRejected):
            self.create(key="old", payload=request(workflow_version=2, steps=4), _manual_submission=True)
        self.assertEqual(self.jobs.list_jobs(workspace_id="workspace-a"), [])
        created = self.create(key="new", payload=request(workflow_version=2, steps=4), _manual_submission=True)
        restored = self.jobs.release_attempt(workspace_id="workspace-a", idempotency_key="new")
        self.assertFalse(restored["released"])
        self.assertEqual(restored["job"]["job_id"], created["job_id"])
        self.assertEqual(len(self.jobs.list_jobs(workspace_id="workspace-a")), 1)

    def test_release_attempt_racing_admission_never_loses_or_duplicates_job(self):
        from story_builder.services.minimax_h3_t2v import T2V_GRAPH_PATH
        self.jobs.graph_path = T2V_GRAPH_PATH
        gate = Barrier(2)
        def submit():
            gate.wait()
            try: return self.create(key="race-release", payload=request(workflow_version=2, steps=4), _manual_submission=True)
            except StoryHandoffRejected: return None
        def release():
            gate.wait()
            return self.jobs.release_attempt(workspace_id="workspace-a", idempotency_key="race-release")
        with ThreadPoolExecutor(2) as pool:
            a, b = pool.submit(submit), pool.submit(release)
            job, result = a.result(), b.result()
        saved = self.jobs.list_jobs(workspace_id="workspace-a")
        if result["released"]:
            self.assertIsNone(job)
            self.assertEqual(saved, [])
        else:
            self.assertEqual(result["job"]["job_id"], job["job_id"])
            self.assertEqual(len(saved), 1)

    def test_manual_submission_treats_screenplay_metadata_as_advisory(self):
        jobs, lineage = self.story_jobs()
        from story_builder.services.minimax_h3_t2v import T2V_GRAPH_PATH
        jobs.graph_path = T2V_GRAPH_PATH
        clip = story_clip_id("workspace-a", "screenplay-a", 1, 1)
        payload = request(workflow_version=2, steps=4, prompt="My own final prompt.", duration_seconds=9)
        for number, metadata in enumerate((lineage, {**lineage, "setup_hash": "0" * 64},
                {**lineage, "workflow_id": "stale-extra-field"}, {"scene_number": 1})):
            with self.subTest(metadata=metadata):
                job = jobs.create_job(workspace_id="workspace-a", clip_id=clip,
                    idempotency_key=f"manual-{number}", request=payload,
                    source_lineage=metadata, _manual_submission=True)
                self.assertEqual(job["request"]["prompt"], payload["prompt"])
                self.assertEqual(job["request"]["duration_seconds"], 9)
                replay = jobs.create_job(workspace_id="workspace-a", clip_id=clip,
                    idempotency_key=f"manual-{number}", request=payload,
                    source_lineage={"outdated": True}, _manual_submission=True)
                self.assertEqual(replay["job_id"], job["job_id"])
                self.assertEqual(replay["source_lineage"], job["source_lineage"])
        with self.assertRaises(StoryHandoffRejected):
            jobs.create_job(workspace_id="workspace-a", clip_id=clip, idempotency_key="strict-stale",
                request=payload, source_lineage={**lineage, "setup_hash": "0" * 64})
        with self.assertRaisesRegex(IsolatedJobConflict, "[Ii]dempotency"):
            jobs.create_job(workspace_id="workspace-a", clip_id=clip, idempotency_key="manual-0",
                request={**payload, "prompt": "A different render."}, _manual_submission=True)
        with self.assertRaisesRegex(ValueError, "frozen automated run"):
            jobs.create_job(workspace_id="workspace-a", clip_id=clip, idempotency_key="bad-mode",
                request=payload, _manual_submission=True, _full_run_continuation=True)

    def test_manual_retake_inherits_original_provenance_without_browser_lineage(self):
        jobs, lineage = self.story_jobs()
        from story_builder.services.minimax_h3_t2v import T2V_GRAPH_PATH
        jobs.graph_path = T2V_GRAPH_PATH
        clip = story_clip_id("workspace-a", "screenplay-a", 1, 1)
        payload = request(workflow_version=2, steps=4)
        original = jobs.create_job(workspace_id="workspace-a", clip_id=clip,
            idempotency_key="original-linked", request=payload, source_lineage=lineage)
        self.assertEqual(original["source_lineage"]["shot_number"], 1)
        take = jobs._take_and_meta(original["job_id"])[0]
        for status in ("submitting", "collecting", "needs_review"):
            self.ledger.transition_take(project_id="workspace-a", take_id=take["take_id"], status=status)
        for number, metadata in enumerate((None, {"broken": "browser metadata"})):
            retake = jobs.create_job(workspace_id="workspace-a", clip_id=clip,
                idempotency_key=f"manual-retake-{number}", request={**payload, "prompt": "My retake."},
                retake_of_job_id=original["job_id"], keep_original=True,
                source_lineage=metadata, _manual_submission=True)
            self.assertEqual(retake["source_lineage"], original["source_lineage"])
            self.assertEqual(retake["request"]["prompt"], "My retake.")
        self.assertEqual(jobs.get_job(original["job_id"])["status"], "needs_review")

    def test_manual_r2v_admits_custom_image_audio_prompt_without_saved_shot(self):
        from story_builder.tests.test_isolated_r2v_contract import request as r2v_request
        jobs = IsolatedVideoJobs(self.ledger, r2v_capability_provider=lambda: {"available": True})
        payload = r2v_request(workflow_version=2, steps=4,
            prompt="Animate <Picture 1> with sound from <Audio 1>.",
            audios=[{"asset_id": "pa-1111111111111111", "sha256": "b" * 64,
                     "role": "sound", "intent": "Use the soundtrack.", "speaker_ids": []}])
        job = jobs.create_job(workspace_id="workspace-a", clip_id="manual-r2v", idempotency_key="manual-r2v",
            request=payload, source_lineage={"workflow_id": "stale", "scene_number": 1}, _manual_submission=True)
        self.assertEqual(job["request"]["prompt"], payload["prompt"])
        self.assertEqual(len(job["request"]["images"]), 1)
        self.assertEqual(len(job["request"]["audios"]), 1)
        self.assertIsNone(job["source_lineage"])

    def test_manual_http_submission_accepts_unprepared_shot_and_reports_definitive_rejection(self):
        from story_builder.services.minimax_h3_t2v import T2V_GRAPH_PATH
        app = create_app(data_root=Path(self.temporary.name) / "manual-http", graph_path=T2V_GRAPH_PATH,
            capability_provider=lambda: {"available": True},
            worker_status_provider=lambda: {"enabled": True, "running": True, "available": True},
            gpu_reader=lambda: {"temperature_c": 40., "graphics_clock_mhz": 1200.})
        def call(payload, path="/api/video/jobs"):
            body = json.dumps(payload).encode()
            environ = {"REQUEST_METHOD": "POST", "PATH_INFO": path, "QUERY_STRING": "",
                "CONTENT_TYPE": "application/json", "CONTENT_LENGTH": str(len(body)), "wsgi.input": io.BytesIO(body)}
            statuses = []
            result = json.loads(b"".join(app(environ, lambda status, headers: statuses.append(status))))
            return statuses[0], result
        payload = {"workspace_id": "ws", "clip_id": "clip", "idempotency_key": "manual-http",
            "request": request(workflow_version=2, steps=4), "source_lineage": {"broken": True}}
        status, job = call(payload)
        self.assertEqual(status, "202 Accepted", job)
        self.assertIsNone(job["source_lineage"])
        status, rejected = call({**payload, "idempotency_key": "invalid", "request": {**payload["request"], "prompt": ""}})
        self.assertEqual(status, "422 Unprocessable Entity", rejected)
        self.assertEqual(rejected["admission_state"], "not_created")
        status, conflict = call({**payload, "request": {**payload["request"], "prompt": "Changed request."}})
        self.assertEqual(status, "409 Conflict", conflict)
        self.assertNotIn("admission_state", conflict)

        status, recovered = call({"workspace_id":"ws", "idempotency_key":"manual-http"}, "/api/video/attempts/release")
        self.assertEqual(status, "200 OK")
        self.assertEqual(recovered["job"]["job_id"], job["job_id"])
        self.assertFalse(recovered["released"])
        status, released = call({"workspace_id":"ws", "idempotency_key":"not-admitted"}, "/api/video/attempts/release")
        self.assertEqual(status, "200 OK")
        self.assertTrue(released["released"])

    def test_story_lineage_persists_replays_and_retakes_without_changing_request(self):
        jobs, lineage = self.story_jobs()
        clip = story_clip_id("workspace-a", "screenplay-a", 1, 1)
        job = jobs.create_job(workspace_id="workspace-a", clip_id=clip, idempotency_key="story-1",
            request=request(), source_lineage=lineage)
        self.assertNotIn("source_lineage", job["request"])
        self.assertEqual(job["source_lineage"]["scene_number"], 1)
        self.assertEqual(job["source_lineage"]["shot_number"], 1)
        self.assertEqual(job["source_lineage"]["workflow_id"], request()["workflow_id"])
        self.assertEqual(job["source_lineage"]["source_prompt_sha256"], lineage["source_prompt_sha256"])
        replay = jobs.create_job(workspace_id="workspace-a", clip_id=clip, idempotency_key="story-1",
            request=request(), source_lineage=lineage)
        self.assertEqual(replay["job_id"], job["job_id"])
        self.assertEqual(replay["source_lineage"], job["source_lineage"])
        take = jobs._take_and_meta(job["job_id"])[0]
        self.ledger.transition_take(project_id="workspace-a", take_id=take["take_id"], status="submitting")
        self.ledger.transition_take(project_id="workspace-a", take_id=take["take_id"], status="collecting")
        self.ledger.transition_take(project_id="workspace-a", take_id=take["take_id"], status="needs_review")
        draft = jobs.retake_draft(job["job_id"], keep_original=True)
        self.assertEqual(draft["source_lineage"], job["source_lineage"])
        retake = jobs.create_retake(job["job_id"], idempotency_key="story-retake", keep_original=True,
            overrides={"prompt":"Retake prompt."})
        self.assertEqual(retake["source_lineage"], job["source_lineage"])

    def test_story_lineage_freezes_and_validates_prompt_knowledge_provenance(self):
        jobs, lineage = self.story_jobs()
        knowledge_ref = {"knowledge_id": "minimax-h3-t2v", "guidance_version": 3,
            "workflow_sha256": "a" * 64}
        style_ref = {"snapshot_id": "style-snapshot-a", "style_version_id": "style-v2",
            "narrative_hash": "b" * 64, "director_profile_hash": "c" * 64,
            "directing_style_hash": "d" * 64}
        lineage["knowledge_ref"] = knowledge_ref
        lineage["style_ref"] = style_ref
        with sqlite3.connect(self.db_path) as db:
            row = db.execute("SELECT drafts_json FROM story_prompt_drafts WHERE workspace_id='workspace-a'").fetchone()
            drafts = json.loads(row[0])
            drafts["1.1"]["knowledge_ref"] = knowledge_ref
            drafts["1.1"]["style_ref"] = style_ref
            db.execute("UPDATE story_prompt_drafts SET drafts_json=? WHERE workspace_id='workspace-a'",
                (json.dumps(drafts, sort_keys=True, separators=(",", ":")),))

        clip = story_clip_id("workspace-a", "screenplay-a", 1, 1)
        job = jobs.create_job(workspace_id="workspace-a", clip_id=clip, idempotency_key="story-knowledge",
            request=request(), source_lineage=lineage)
        self.assertEqual(job["source_lineage"]["knowledge_ref"], knowledge_ref)
        self.assertEqual(job["source_lineage"]["style_ref"], style_ref)
        replay = jobs.create_job(workspace_id="workspace-a", clip_id=clip, idempotency_key="story-knowledge",
            request=request(), source_lineage=lineage)
        self.assertEqual(replay["source_lineage"], job["source_lineage"])

        changed = {**lineage, "knowledge_ref": {**knowledge_ref, "workflow_sha256": "b" * 64}}
        with self.assertRaisesRegex(StoryHandoffRejected, "guidance provenance changed"):
            jobs.create_job(workspace_id="workspace-a", clip_id=clip, idempotency_key="story-knowledge-changed",
                request=request(), source_lineage=changed)
        changed_style = {**lineage, "style_ref": {**style_ref, "narrative_hash": "e" * 64}}
        with self.assertRaisesRegex(StoryHandoffRejected, "creative style provenance changed"):
            jobs.create_job(workspace_id="workspace-a", clip_id=clip, idempotency_key="story-style-changed",
                request=request(), source_lineage=changed_style)

    def test_story_lineage_rejects_stale_setup_or_wrong_clip_and_isolated_jobs_stay_unlinked(self):
        jobs, lineage = self.story_jobs()
        clip = story_clip_id("workspace-a", "screenplay-a", 1, 1)
        with self.assertRaisesRegex(IsolatedJobConflict, "clip identity"):
            jobs.create_job(workspace_id="workspace-a", clip_id="wrong-clip", idempotency_key="bad-clip",
                request=request(), source_lineage=lineage)
        changed = dict(lineage, setup_hash="0" * 64)
        with self.assertRaisesRegex(IsolatedJobConflict, "setup changed"):
            jobs.create_job(workspace_id="workspace-a", clip_id=clip, idempotency_key="stale-setup",
                request=request(), source_lineage=changed)
        isolated = self.create(key="unlinked")
        self.assertIsNone(isolated["source_lineage"])

    def test_story_handoff_rejects_manual_video_when_video_stage_is_automated(self):
        jobs, lineage = self.story_jobs()
        setup = {"mode":"assisted_manual", "automate_steps":{"character_images":False,
            "character_voice":False,"world_images":False,"frame_images":False,"video":True},
            "video_quality":"high", "duration_policy":{"kind":"fixed","seconds":6},
            "video_workflow_id":"minimax_h3_r2v_dynamic_v1"}
        setup_json = json.dumps(setup, sort_keys=True, separators=(",", ":"))
        setup_hash = hashlib.sha256(setup_json.encode()).hexdigest()
        with sqlite3.connect(self.db_path) as db:
            db.execute("UPDATE story_production_setups SET setup_json=? WHERE workspace_id='workspace-a'", (setup_json,))
            db.execute("UPDATE story_prompt_drafts SET setup_hash=? WHERE workspace_id='workspace-a'", (setup_hash,))
        lineage["setup_hash"] = setup_hash
        with self.assertRaisesRegex(IsolatedJobConflict, "automates video generation"):
            jobs.create_job(workspace_id="workspace-a", clip_id=story_clip_id("workspace-a", "screenplay-a", 1, 1),
                idempotency_key="manual-bypass", request=request(), source_lineage=lineage)
        with sqlite3.connect(self.db_path) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM production_takes WHERE project_id='workspace-a'").fetchone()[0], 0)

    def test_story_lineage_rejects_prompt_changed_after_video_handoff(self):
        jobs, lineage = self.story_jobs()
        clip = story_clip_id("workspace-a", "screenplay-a", 1, 1)
        with sqlite3.connect(self.db_path) as db:
            saved = json.loads(db.execute("SELECT drafts_json FROM story_prompt_drafts WHERE workspace_id='workspace-a'").fetchone()[0])
            saved["1.1"]["prompt"] = "Edited in Prompt Preparation after the handoff."
            db.execute("UPDATE story_prompt_drafts SET drafts_json=? WHERE workspace_id='workspace-a'", (json.dumps(saved),))
        with self.assertRaisesRegex(IsolatedJobConflict, "prompt changed after opening"):
            jobs.create_job(workspace_id="workspace-a", clip_id=clip, idempotency_key="stale-prompt-handoff",
                request=request(prompt="Final editable Video prompt."), source_lineage=lineage)

    def test_story_retake_inherits_frozen_lineage_after_story_setup_and_prompt_change(self):
        jobs, lineage = self.story_jobs()
        clip = story_clip_id("workspace-a", "screenplay-a", 1, 1)
        original = jobs.create_job(workspace_id="workspace-a", clip_id=clip, idempotency_key="lineage-original",
            request=request(), source_lineage=lineage)
        take = jobs._take_and_meta(original["job_id"])[0]
        self.ledger.transition_take(project_id="workspace-a", take_id=take["take_id"], status="submitting")
        self.ledger.transition_take(project_id="workspace-a", take_id=take["take_id"], status="collecting")
        self.ledger.transition_take(project_id="workspace-a", take_id=take["take_id"], status="needs_review")
        with sqlite3.connect(self.db_path) as db:
            db.execute("UPDATE story_workspaces SET current_revision_id='source-b' WHERE workspace_id='workspace-a'")
            changed_setup = {"mode":"fully_automated","changed":True}
            changed_setup_json = json.dumps(changed_setup, sort_keys=True, separators=(",", ":"))
            db.execute("UPDATE story_production_setups SET setup_json=? WHERE workspace_id='workspace-a'", (changed_setup_json,))
            changed_hash = hashlib.sha256(changed_setup_json.encode()).hexdigest()
            changed_drafts = {"1.1":{"workflow_id":request()["workflow_id"],"prompt":"New current prompt."}}
            db.execute("UPDATE story_prompt_drafts SET setup_hash=?,drafts_json=? WHERE workspace_id='workspace-a'",
                (changed_hash, json.dumps(changed_drafts)))
        retake = jobs.create_job(workspace_id="workspace-a", clip_id=clip, idempotency_key="lineage-retake-api",
            request=request(prompt="Edited retake prompt."), retake_of_job_id=original["job_id"],
            keep_original=True, source_lineage=lineage)
        self.assertEqual(retake["source_lineage"], original["source_lineage"])
        self.assertEqual(retake["request"]["prompt"], "Edited retake prompt.")
        with self.assertRaisesRegex(IsolatedJobConflict, "frozen story lineage"):
            jobs.create_job(workspace_id="workspace-a", clip_id=clip, idempotency_key="lineage-retake-drop",
                request=request(), retake_of_job_id=original["job_id"], keep_original=True)
        replacement = dict(lineage, source_prompt_sha256="0" * 64)
        with self.assertRaisesRegex(IsolatedJobConflict, "frozen story lineage"):
            jobs.create_job(workspace_id="workspace-a", clip_id=clip, idempotency_key="lineage-retake-replace",
                request=request(), retake_of_job_id=original["job_id"], keep_original=True,
                source_lineage=replacement)

    def test_isolated_supervisor_idle_contract_without_director(self):
        from unittest.mock import Mock
        from story_builder.isolated_worker import _CapabilityGatedWorker
        source = Mock()
        source.process_one.return_value = {"status": "idle"}
        gated = _CapabilityGatedWorker(source, self.ledger, Mock())
        self.assertEqual(gated.review_next_take(), {"status": "idle"})
        source.review_next_take.assert_not_called()
        self.assertEqual(gated.process_one()["status"], "idle")
        source.process_one.return_value = {"status": "waiting_for_comfyui", "reason": "busy"}
        self.assertEqual(gated.process_one()["waiting_for"], "comfyui")
        self.create()
        with patch("story_builder.isolated_worker.t2v_capability", return_value={"available": False}), patch("story_builder.isolated_worker._runtime_guard", return_value={"safe_to_submit": False}):
            self.assertEqual(gated.process_one()["status"], "idle")
        self.assertEqual(source.process_one.call_count, 2)

    def test_full_worker_does_not_advance_while_identity_review_is_processing(self):
        from unittest.mock import Mock
        from story_builder.isolated_worker import _CapabilityGatedWorker

        jobs = Mock()
        processor = Mock()
        processor.process_one.return_value = {"status": "completed", "review": {"review_id": "review-a"}}
        gated = _CapabilityGatedWorker(Mock(), Mock(), Mock(), jobs=jobs,
            identity_processor=processor, identity_store=object(), story=object(),
            image_selections=object(), data_root=self.temporary.name)

        with patch("story_builder.isolated_worker.enqueue_completed_full_run_identity_reviews",
                   return_value=1) as enqueue:
            result = gated.review_next_take()

        self.assertEqual(result, {"status": "identity_review",
            "review": {"status": "completed", "review": {"review_id": "review-a"}}})
        enqueue.assert_called_once()
        processor.process_one.assert_called_once()
        jobs.advance_fully_automated_run.assert_not_called()

    def test_idempotent_create_survives_service_restart_and_conflicts_on_changed_input(self):
        first = self.create()
        after_restart = IsolatedVideoJobs(ProductionLedger(self.db_path), graph_path=GRAPH).create_job(
            workspace_id="workspace-a", clip_id="clip-1", idempotency_key="key-1", request=request())
        self.assertEqual(first["job_id"], after_restart["job_id"])
        self.assertEqual(first["request_hash"], after_restart["request_hash"])
        with self.assertRaises(IsolatedJobConflict):
            self.create(payload=request(prompt="Changed text."))

    def test_concurrent_duplicate_requests_create_one_job(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: self.create(key="same-key"), range(2)))
        self.assertEqual(results[0]["job_id"], results[1]["job_id"])
        self.assertEqual(len(self.jobs.events(results[0]["job_id"])), 1)

    def test_snapshot_and_retake_draft_preserve_full_request_without_queueing(self):
        saved = request(prompt="  exact authored prompt  ")
        original = self.create(payload=saved)
        self.assertEqual(original["request"], saved)
        row = self.jobs._take_and_meta(original["job_id"])[0]
        self.ledger.transition_take(project_id="workspace-a", take_id=row["take_id"], status="submitting")
        self.ledger.transition_take(project_id="workspace-a", take_id=row["take_id"], status="collecting")
        self.ledger.transition_take(project_id="workspace-a", take_id=row["take_id"], status="needs_review")
        draft = self.jobs.retake_draft(original["job_id"], keep_original=False)
        self.assertFalse(draft["submission_created"])
        self.assertEqual(draft["request"], saved)
        self.assertEqual(draft["candidate_disposition"], "discard_requested")
        self.assertEqual(draft["asset_cleanup"], "none")
        with self.ledger._connect() as db:
            decision = db.execute("SELECT disposition FROM isolated_video_retake_decisions WHERE source_job_id=?",
                (original["job_id"],)).fetchone()
        self.assertEqual(decision["disposition"], "discard_requested")
        self.assertEqual(self.jobs.get_job(original["job_id"])["candidate_disposition"], "discard_requested")
        self.assertEqual(self.jobs.list_jobs(workspace_id="workspace-a")[0]["candidate_disposition"], "discard_requested")
        self.assertEqual(self.jobs.get_by_idempotency_key(workspace_id="workspace-a",
            idempotency_key=original["idempotency_key"])["candidate_disposition"], "discard_requested")
        # Reopening the dialog can change the explicit choice; the durable row
        # reflects the latest user action without creating a generation job.
        kept_draft = self.jobs.retake_draft(original["job_id"], keep_original=True)
        self.assertEqual(kept_draft["candidate_disposition"], "keep")
        with self.ledger._connect() as db:
            decision = db.execute("SELECT disposition FROM isolated_video_retake_decisions WHERE source_job_id=?",
                (original["job_id"],)).fetchone()
            take_count = db.execute("SELECT COUNT(*) FROM production_takes WHERE project_id='workspace-a'").fetchone()[0]
        self.assertEqual(decision["disposition"], "keep")
        self.assertEqual(self.jobs.get_job(original["job_id"])["candidate_disposition"], "keep")
        self.assertEqual(take_count, 1)
        retake = self.jobs.create_retake(original["job_id"], idempotency_key="retake-1",
            keep_original=False, overrides={"prompt": "Edited prompt."})
        self.assertEqual(retake["retake_of_job_id"], original["job_id"])
        self.assertFalse(retake["keep_original"])
        self.assertEqual(retake["request"]["seed"], saved["seed"])
        self.assertEqual(retake["request"]["prompt"], "Edited prompt.")
        self.assertEqual(retake["status"], "queued")
        with self.assertRaises(IsolatedJobConflict):
            self.jobs.create_retake(original["job_id"], idempotency_key="retake-1",
                keep_original=True, overrides={"prompt": "Edited prompt."})

    def _reviewable_job_with_output(self, *, media_root, key="discard-output"):
        from story_builder.services.media_library import list_assets, register_generated_video

        job = self.create(key=key)
        take = self.jobs._take_and_meta(job["job_id"])[0]
        for status in ("submitting", "collecting", "needs_review"):
            self.ledger.transition_take(project_id="workspace-a", take_id=take["take_id"], status=status)
        output_dir = media_root / "projects" / "workspace-a" / "media" / "generated"
        output_dir.mkdir(parents=True, exist_ok=True)
        output = output_dir / f"{key}.mp4"
        output.write_bytes(b"generated video bytes for " + key.encode())
        with patch("story_builder.services.media_library._probe", return_value={
                "duration_seconds": 2.0, "width": 128, "height": 72, "has_video": True, "has_audio": True}):
            shared = register_generated_video(media_root, "workspace-a", output.name,
                {"job_id": job["job_id"], "kind": "video", "duration_seconds": 2.0})
        digest = shared["sha256"]
        asset_id = f"video_{digest[:32]}"
        metadata = {"shared_asset_id": shared["asset_id"], "sha256": digest,
            "relative_path": f"assets/workspace-a/{output.name}"}
        with self.ledger._connect() as db:
            db.execute("INSERT INTO isolated_video_assets(asset_id,job_id,workspace_id,sha256,metadata_json) VALUES(?,?,?,?,?)",
                (asset_id, job["job_id"], "workspace-a", digest, json.dumps(metadata)))
            db.execute("INSERT INTO isolated_video_asset_refs(asset_id,job_id) VALUES(?,?)",
                (asset_id, job["job_id"]))
        jobs = IsolatedVideoJobs(self.ledger, graph_path=GRAPH, media_root=media_root)
        return jobs, job, take, shared, output, list_assets

    def test_discard_archives_unshared_output_recoverably(self):
        from story_builder.services.media_library import asset_path

        media_root = Path(self.temporary.name) / "media"
        jobs, job, _take, shared, output, list_assets = self._reviewable_job_with_output(media_root=media_root)

        result = jobs.retake_draft(job["job_id"], keep_original=False)

        self.assertEqual(result["asset_cleanup"], "archived_recoverable")
        self.assertEqual(list_assets(media_root, "workspace-a", kind="video")["total"], 0)
        archived = list_assets(media_root, "workspace-a", kind="video", include_archived=True)
        self.assertEqual(archived["assets"][0]["asset_id"], shared["asset_id"])
        self.assertTrue(output.is_file())
        self.assertEqual(asset_path(media_root, "workspace-a", shared["asset_id"])[0], output)

    def test_discard_keeps_output_visible_when_another_job_references_it(self):
        media_root = Path(self.temporary.name) / "media"
        jobs, job, _take, shared, _output, list_assets = self._reviewable_job_with_output(
            media_root=media_root, key="shared-output")
        other_job = self.create(key="other-output-reference")
        with self.ledger._connect() as db:
            db.execute("INSERT INTO isolated_video_asset_refs(asset_id,job_id) SELECT asset_id,? FROM isolated_video_assets WHERE job_id=?",
                (other_job["job_id"], job["job_id"]))

        result = jobs.retake_draft(job["job_id"], keep_original=False)

        self.assertEqual(result["asset_cleanup"], "retained_shared")
        assets = list_assets(media_root, "workspace-a", kind="video")["assets"]
        self.assertEqual([asset["asset_id"] for asset in assets], [shared["asset_id"]])

    def test_changing_discard_choice_back_to_keep_restores_output(self):
        media_root = Path(self.temporary.name) / "media"
        jobs, job, _take, shared, _output, list_assets = self._reviewable_job_with_output(
            media_root=media_root, key="choice-reversal")

        discarded = jobs.retake_draft(job["job_id"], keep_original=False)
        kept = jobs.retake_draft(job["job_id"], keep_original=True)

        self.assertEqual(discarded["asset_cleanup"], "archived_recoverable")
        self.assertEqual(kept["asset_cleanup"], "restored")
        self.assertEqual(list_assets(media_root, "workspace-a", kind="video")["assets"][0]["asset_id"],
            shared["asset_id"])

    def test_unknown_submission_cannot_be_turned_into_manual_retake(self):
        job = self.create()
        take = self.jobs._take_and_meta(job["job_id"])[0]
        self.ledger.transition_take(project_id="workspace-a", take_id=take["take_id"], status="submitting")
        self.ledger.transition_take(project_id="workspace-a", take_id=take["take_id"],
            status="recovery_required", payload={"code": "unknown_post"})
        with self.assertRaises(IsolatedJobConflict):
            self.jobs.create_retake(job["job_id"], idempotency_key="unsafe-retake", keep_original=True)
        with self.assertRaises(IsolatedJobConflict):
            self.jobs.retake_draft(job["job_id"], keep_original=True)

    def test_idempotency_get_never_repairs_missing_metadata(self):
        job = self.create()
        with self.ledger._connect() as db:
            db.execute("DELETE FROM isolated_video_jobs WHERE job_id=?", (job["job_id"],))
        with self.assertRaises(IsolatedJobConflict):
            self.jobs.get_by_idempotency_key(workspace_id="workspace-a", idempotency_key="key-1")
        with self.ledger._connect() as db:
            count = db.execute("SELECT COUNT(*) FROM isolated_video_jobs WHERE job_id=?", (job["job_id"],)).fetchone()[0]
        self.assertEqual(count, 0)

    def test_facade_metadata_and_queued_row_share_one_ledger_transaction(self):
        run = self.ledger.create_run(project_id="workspace-a", idempotency_key="isolated-workspace:workspace-a",
            config={"control_mode": "manual", "entry": "isolated"})
        with self.assertRaisesRegex(RuntimeError, "rollback marker"):
            self.ledger.queue_take(project_id="workspace-a", run_id=run["run_id"], shot_id="c1",
                take_id="atomic-take", idempotency_key="isolated:atomic", input_snapshot=request(),
                on_create=lambda db, row: (_ for _ in ()).throw(RuntimeError("rollback marker")))
        takes = self.ledger.get_run(project_id="workspace-a", run_id=run["run_id"])["takes"]
        self.assertFalse(any(item["take_id"] == "atomic-take" for item in takes))

    def test_prepare_uses_frozen_request_and_rewrites_output_prefix(self):
        job = self.create()
        take = self.jobs._take_and_meta(job["job_id"])[0]
        prepared = prepare_isolated_take(take, graph_path=GRAPH)
        save_nodes = [n for n in prepared.graph.values() if n.get("class_type") == "SaveVideo"]
        self.assertEqual(len(save_nodes), 1)
        self.assertIn("isolated/workspace-a/clip-1/", save_nodes[0]["inputs"]["filename_prefix"])
        self.assertNotIn("isolated_preview", save_nodes[0]["inputs"]["filename_prefix"])

    def test_worker_stop_during_preparation_never_submits(self):
        job = self.create()
        calls = []
        def prepare(take):
            self.ledger.transition_take(project_id=take["project_id"], take_id=take["take_id"],
                status="cancel_requested", payload={"reason": "owner_stopped_run"})
            return PreparedTake(graph={"fixture": {}}, cleanup=lambda: calls.append("cleaned"))
        def request_json(url, **kwargs):
            calls.append(kwargs.get("method", "GET"))
            return {"queue_running": [], "queue_pending": []}
        worker = ProductionJobWorker(self.ledger, comfy_url="http://fixture.invalid",
            prepare=prepare, collect=lambda *args: [], cleanup=lambda *args: None,
            request_json=request_json, release_idle=lambda **kwargs: {"released": False})
        result = worker.process_one()
        self.assertEqual(result["status"], "cancelled")
        self.assertEqual(self.jobs.get_job(job["job_id"])["status"], "cancelled")
        self.assertNotIn("POST", calls)
        self.assertIn("cleaned", calls)

    def test_worker_stop_waits_for_exact_prompt_to_leave_queue(self):
        job = self.create()
        take = self.ledger.claim_next_queued_take(lease_owner="test", lease_seconds=300)
        self.ledger.transition_take(project_id=take["project_id"], take_id=take["take_id"],
            status="cancel_requested", payload={})
        queue = {"queue_running": [[0, "owned-prompt"]], "queue_pending": []}
        worker = ProductionJobWorker(self.ledger, comfy_url="http://fixture.invalid",
            prepare=lambda *args: None, collect=lambda *args: [], cleanup=lambda *args: None,
            request_json=lambda *args, **kwargs: queue)
        with patch("story_builder.services.production_job_worker.interrupt_if_owned_prompt"):
            self.assertFalse(worker._finish_owner_cancellation(take, None,
                submitted=True, prompt_id="owned-prompt"))
            self.assertEqual(self.jobs.get_job(job["job_id"])["status"], "cancel_requested")
            queue["queue_running"] = []
            self.assertTrue(worker._finish_owner_cancellation(take, None,
                submitted=True, prompt_id="owned-prompt"))
        self.assertEqual(self.jobs.get_job(job["job_id"])["status"], "cancelled")

    def test_worker_unknown_submit_is_durable_recovery_and_not_retried(self):
        job = self.create()
        endpoints = []
        def request_json(url, *, method="GET", payload=None, timeout_seconds=30):
            endpoints.append((url, method))
            if method == "POST":
                raise urllib.error.URLError("simulated connection loss after request write")
            return {"queue_running": [], "queue_pending": []}
        class Watchdog:
            def check(self):
                return None
        worker = ProductionJobWorker(self.ledger, comfy_url="http://fixture.invalid",
            prepare=lambda take: PreparedTake(graph={"fixture": {}}, cleanup=lambda: None),
            collect=lambda take, history: [], cleanup=lambda take: None,
            request_json=request_json,
            gpu_inspector=lambda **kwargs: {"gpu": {"name": "test"}, "recorded_at": "test"},
            operating_point_reader=lambda: {"temperature_c": 40.0, "graphics_clock_mhz": 1200.0},
            release_idle=lambda **kwargs: {"released": False})
        with patch("story_builder.services.production_job_worker.record_gpu_telemetry"), \
             patch("story_builder.services.production_job_worker.ensure_prompt_watchdog", return_value=Watchdog()), \
             patch("story_builder.services.production_job_worker.finish_prompt_watchdog"):
            result = worker.process_one()
            self.assertEqual(result["status"], "recovery_required")
            worker.reconcile_existing_once()
        record = self.jobs.get_job(job["job_id"])
        self.assertEqual(record["status"], "recovery_required")
        self.assertTrue(record["engine_prompt_id"])
        self.assertEqual([method for _, method in endpoints].count("POST"), 1)
        self.assertTrue(any("/history/" in url for url, _ in endpoints))
        self.assertTrue(all("/queue" in url or "/prompt" in url or "/history/" in url for url, _ in endpoints))

    def test_local_http_adapter_is_read_only_on_reconnect_and_never_starts_worker(self):
        app = create_app(data_root=Path(self.temporary.name) / "data", graph_path=GRAPH,
            capability_provider=lambda: {"available": True, "workflow_id": "fixture"},
            worker_status_provider=lambda: {"enabled": True, "running": True, "available": True},
            gpu_reader=lambda: {"temperature_c": 40.0, "graphics_clock_mhz": 1200.0})
        def call(method, path, payload=None, content_type="application/json"):
            body = b"" if payload is None else json.dumps(payload).encode()
            environ = {"REQUEST_METHOD": method, "PATH_INFO": path.split("?", 1)[0],
                "QUERY_STRING": path.split("?", 1)[1] if "?" in path else "",
                "CONTENT_TYPE": content_type, "CONTENT_LENGTH": str(len(body)), "wsgi.input": io.BytesIO(body)}
            started = []
            response = b"".join(app(environ, lambda status, headers: started.append((status, headers))))
            return started[0][0], json.loads(response) if response else None
        status, created = call("POST", "/api/video/jobs", {"workspace_id": "ws", "clip_id": "c1",
            "idempotency_key": "lost-response", "request": request()})
        self.assertEqual(status, "202 Accepted")
        status, listed = call("GET", "/api/video/jobs?workspace_id=ws")
        self.assertEqual(status, "200 OK")
        self.assertEqual([item["job_id"] for item in listed["jobs"]], [created["job_id"]])
        status, missing_workspace = call("GET", "/api/video/jobs")
        self.assertEqual(status, "400 Bad Request")
        status, recovered = call("GET", "/api/video/jobs/by-idempotency/lost-response?workspace_id=ws")
        self.assertEqual(status, "200 OK")
        self.assertEqual(created["job_id"], recovered["job_id"])
        self.assertEqual(recovered["status"], "queued")
        self.assertIn("dispatch", call("GET", "/api/video/capabilities")[1])
        status, mismatch = call("POST", "/api/video/jobs", {"workspace_id": "ws", "clip_id": "c1",
            "idempotency_key": "lost-response", "request": request(prompt="different")})
        self.assertEqual(status, "409 Conflict")
        status, rejected = call("POST", "/api/video/validations", {"request": request()}, "text/plain")
        self.assertEqual(status, "415 Unsupported Media Type")

    def test_http_create_fails_closed_when_live_runtime_guard_is_unsafe(self):
        data = Path(self.temporary.name) / "unsafe-data"
        app = create_app(data_root=data, graph_path=GRAPH,
            capability_provider=lambda: {"available": True},
            gpu_reader=lambda: {"temperature_c": 48.0, "graphics_clock_mhz": 2431.0})
        payload = {"workspace_id": "ws", "clip_id": "c1", "idempotency_key": "blocked",
            "request": request()}
        body = json.dumps(payload).encode()
        environ = {"REQUEST_METHOD": "POST", "PATH_INFO": "/api/video/jobs", "QUERY_STRING": "",
            "CONTENT_TYPE": "application/json", "CONTENT_LENGTH": str(len(body)), "wsgi.input": io.BytesIO(body)}
        started = []
        result = json.loads(b"".join(app(environ, lambda status, headers: started.append(status))))
        self.assertEqual(started[0], "503 Service Unavailable")
        self.assertEqual(result["error"]["code"], "runtime_not_ready")
        self.assertFalse(result["capability"]["available"])
        ledger = ProductionLedger(data / "services/production/ledger.sqlite3")
        self.assertEqual(ledger.list_runs(project_id="ws"), [])

    def test_automated_first_clip_route_fails_closed_before_story_lookup_when_t2v_unavailable(self):
        data = Path(self.temporary.name) / "first-clip-unavailable"
        app = create_app(data_root=data, graph_path=GRAPH,
            capability_provider=lambda: {"available": False, "disabled_reason": "T2V model is not installed."},
            worker_status_provider=lambda: {"enabled": True, "running": True, "available": True},
            gpu_reader=lambda: {"temperature_c": 40.0, "graphics_clock_mhz": 1200.0})
        payload = {"screenplay_revision_id": "screenplay-a"}
        body = json.dumps(payload).encode()
        environ = {"REQUEST_METHOD": "POST", "PATH_INFO": "/api/story/workspaces/workspace-a/automated-first-clip",
            "QUERY_STRING": "", "CONTENT_TYPE": "application/json", "CONTENT_LENGTH": str(len(body)), "wsgi.input": io.BytesIO(body)}
        started = []
        result = json.loads(b"".join(app(environ, lambda status, headers: started.append(status))))
        self.assertEqual(started[0], "503 Service Unavailable")
        self.assertEqual(result["error"]["code"], "runtime_not_ready")
        ledger = ProductionLedger(data / "services/production/ledger.sqlite3")
        with ledger._connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM production_takes").fetchone()[0], 0)

    def test_automated_first_clip_route_recovers_existing_binding_when_t2v_is_unavailable(self):
        data = Path(self.temporary.name) / "first-clip-recovery"
        frozen = {"run_state": "first_clip_queued", "workspace_id": "workspace-a",
            "screenplay_revision_id": "screenplay-a", "job": {"job_id": "already-queued"}}
        class BoundJobs:
            def __init__(self, *args, **kwargs):
                pass
            @staticmethod
            def recover_fully_automated_first_clip(workspace_id, revision_id):
                return frozen if (workspace_id, revision_id) == ("workspace-a", "screenplay-a") else None
            @staticmethod
            def start_fully_automated_first_clip(*args):
                raise AssertionError("bound recovery must not start a new admission")
        with patch("story_builder.isolated_server.IsolatedVideoJobs", BoundJobs):
            app = create_app(data_root=data, graph_path=GRAPH,
                capability_provider=lambda: {"available": False, "disabled_reason": "GPU guard is offline."})
        payload = {"screenplay_revision_id": "screenplay-a"}
        body = json.dumps(payload).encode()
        environ = {"REQUEST_METHOD": "POST", "PATH_INFO": "/api/story/workspaces/workspace-a/automated-first-clip",
            "QUERY_STRING": "", "CONTENT_TYPE": "application/json", "CONTENT_LENGTH": str(len(body)), "wsgi.input": io.BytesIO(body)}
        started = []
        result = json.loads(b"".join(app(environ, lambda status, headers: started.append(status))))
        self.assertEqual(started[0], "200 OK")
        self.assertEqual(result, frozen)

    def test_automated_run_retry_route_checks_selected_workflow_and_dispatches_shot(self):
        data = Path(self.temporary.name) / "full-run-retry-route"
        job = {"job_id": "failed-shot", "status": "failed", "request": {"workflow_id": "minimax_h3_t2v_local_v1"}}
        frozen = {"run_state": "paused", "workspace_id": "workspace-a", "screenplay_revision_id": "screenplay-a",
            "clips": [{"scene_number": 1, "shot_number": 1, "job": job}]}
        received = []
        class BoundJobs:
            def __init__(self, *args, **kwargs):
                pass
            @staticmethod
            def get_fully_automated_first_clip(workspace_id, revision_id):
                return frozen
            @staticmethod
            def retry_fully_automated_shot(workspace_id, revision_id, scene, shot, *, clip_number=1, readiness):
                received.append((workspace_id, revision_id, scene, shot, clip_number, readiness("minimax_h3_t2v_local_v1")["available"]))
                return {"status": "queued", "job": {"job_id": "retry-shot"}, "run": {"run_state": "first_clip_queued"}}
        with patch("story_builder.isolated_server.IsolatedVideoJobs", BoundJobs):
            app = create_app(data_root=data, graph_path=GRAPH,
                capability_provider=lambda: {"available": True},
                worker_status_provider=lambda: {"enabled": True, "running": True, "available": True},
                gpu_reader=lambda: {"temperature_c": 40.0, "graphics_clock_mhz": 1200.0})
        payload = {"screenplay_revision_id": "screenplay-a", "scene_number": 1, "shot_number": 1}
        body = json.dumps(payload).encode()
        environ = {"REQUEST_METHOD": "POST", "PATH_INFO": "/api/story/workspaces/workspace-a/automated-run-retry",
            "QUERY_STRING": "", "CONTENT_TYPE": "application/json", "CONTENT_LENGTH": str(len(body)), "wsgi.input": io.BytesIO(body)}
        started = []
        result = json.loads(b"".join(app(environ, lambda status, headers: started.append(status))))
        self.assertEqual(started[0], "202 Accepted")
        self.assertEqual(result["job"]["job_id"], "retry-shot")
        self.assertEqual(received, [("workspace-a", "screenplay-a", 1, 1, 1, True)])

    def test_assisted_run_retry_route_checks_the_bound_clip_workflow(self):
        data = Path(self.temporary.name) / "assisted-run-retry-route"
        failed = {"job_id":"failed-clip", "status":"failed",
            "request":{"workflow_id":"minimax_h3_r2v_dynamic_v1"}}
        frozen = {"run_state":"paused", "workspace_id":"workspace-a",
            "screenplay_revision_id":"screenplay-a", "clips":[{"clip_id":"clip-a",
                "scene_number":1,"shot_number":1,"clip_number":1,"job":failed}]}
        received = []
        class BoundJobs:
            def __init__(self, *args, **kwargs):
                pass
            @staticmethod
            def get_assisted_video_run(workspace_id, revision_id):
                return frozen
            @staticmethod
            def retry_assisted_video_clip(workspace_id, revision_id, clip_id, *, readiness):
                received.append((workspace_id, revision_id, clip_id,
                    readiness("minimax_h3_r2v_dynamic_v1")["available"]))
                return {"status":"queued", "job":{"job_id":"retried-clip"},
                    "run":{"run_state":"running"}}
        with patch("story_builder.isolated_server.IsolatedVideoJobs", BoundJobs):
            app = create_app(data_root=data, graph_path=GRAPH,
                capability_provider=lambda: {"available": True},
                r2v_capability_provider=lambda: {"available": True},
                worker_status_provider=lambda: {"enabled": True,"running": True,"available": True,
                    "supported_workflows":["minimax_h3_r2v_dynamic_v1"]},
                gpu_reader=lambda: {"temperature_c":40.0,"graphics_clock_mhz":1200.0})
        payload = {"screenplay_revision_id":"screenplay-a", "clip_id":"clip-a"}
        body = json.dumps(payload).encode()
        environ = {"REQUEST_METHOD":"POST", "PATH_INFO":"/api/story/workspaces/workspace-a/assisted-video-run-retry",
            "QUERY_STRING":"", "CONTENT_TYPE":"application/json", "CONTENT_LENGTH":str(len(body)), "wsgi.input":io.BytesIO(body)}
        started = []
        result = json.loads(b"".join(app(environ, lambda status, headers: started.append(status))))
        self.assertEqual(started[0], "202 Accepted")
        self.assertEqual(result["job"]["job_id"], "retried-clip")
        self.assertEqual(received, [("workspace-a","screenplay-a","clip-a",True)])

    def test_http_create_blocked_when_no_explicit_worker_consumer(self):
        data = Path(self.temporary.name) / "no-worker-data"
        app = create_app(data_root=data, graph_path=GRAPH,
            capability_provider=lambda: {"available": True},
            gpu_reader=lambda: {"temperature_c": 40.0, "graphics_clock_mhz": 1200.0})
        payload = {"workspace_id": "ws", "clip_id": "c1", "idempotency_key": "no-consumer",
            "request": request()}
        body = json.dumps(payload).encode()
        environ = {"REQUEST_METHOD": "POST", "PATH_INFO": "/api/video/jobs", "QUERY_STRING": "",
            "CONTENT_TYPE": "application/json", "CONTENT_LENGTH": str(len(body)), "wsgi.input": io.BytesIO(body)}
        started = []
        result = json.loads(b"".join(app(environ, lambda status, headers: started.append(status))))
        self.assertEqual(started[0], "503 Service Unavailable")
        self.assertFalse(result["capability"]["dispatch"]["available"])
        ledger = ProductionLedger(data / "services/production/ledger.sqlite3")
        self.assertEqual(ledger.list_runs(project_id="ws"), [])


if __name__ == "__main__":
    unittest.main()
