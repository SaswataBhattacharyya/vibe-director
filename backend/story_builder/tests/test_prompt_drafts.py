import sqlite3
import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from story_builder.services.production_ledger import LedgerConflict, ProductionLedger
from story_builder.services.production_setup import ProductionSetup
from story_builder.services.prompt_drafts import PromptDrafts
from story_builder.services.workflow_knowledge import WorkflowKnowledge
from story_builder.services.workflow_knowledge_catalog import seed_minimax_h3_workflow_knowledge
from story_builder.services.isolated_video_contract import T2V_WORKFLOW_ID
from story_builder.services.isolated_r2v_contract import WORKFLOW_ID as R2V_WORKFLOW_ID


class Story:
    @staticmethod
    def _screenplay_is_currently_accepted(db, row):
        current = db.execute("SELECT current_revision_id FROM story_workspaces WHERE workspace_id=?", (row["workspace_id"],)).fetchone()
        latest = db.execute("SELECT screenplay_revision_id FROM story_screenplay_revisions WHERE workspace_id=? AND source_revision_id=? ORDER BY rowid DESC LIMIT 1",
            (row["workspace_id"], row["source_revision_id"])).fetchone()
        return bool(row["accepted_at"] and current and current["current_revision_id"] == row["source_revision_id"]
            and latest and latest["screenplay_revision_id"] == row["screenplay_revision_id"])


class PromptDraftTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "ledger.sqlite3"
        self.ledger = ProductionLedger(self.path)
        with sqlite3.connect(self.path) as db:
            db.executescript("""
                CREATE TABLE story_workspaces(workspace_id TEXT PRIMARY KEY,current_revision_id TEXT);
                CREATE TABLE story_screenplay_revisions(screenplay_revision_id TEXT PRIMARY KEY,workspace_id TEXT,source_revision_id TEXT,accepted_at TEXT,screenplay_json TEXT,style_selection_snapshot_id TEXT);
                INSERT INTO story_workspaces VALUES('ws-a','source-a');
            """)
            screenplay = {"title": "Test", "logline": "A complete story context.", "characters": [],
                "scenes": [{"scene_number": 1, "slugline": "INT. ROOM - NIGHT", "summary": "A quiet confrontation.",
                    "shots": [{"shot_number": 1, "action": "A door opens.", "dialogue": "Who is there?",
                        "direction": {"camera": "slow push", "lighting": "blue practicals", "mood": "uneasy", "sfx": "door latch", "music": "low strings"}}]}]}
            db.execute("INSERT INTO story_screenplay_revisions VALUES(?,?,?,?,?,?)",
                ("sp-a", "ws-a", "source-a", "2026-10-10", json.dumps(screenplay), "style-a"))
        self.story = Story()
        self.setup = ProductionSetup(self.ledger, self.story)
        self.knowledge = WorkflowKnowledge(self.ledger)
        seed_minimax_h3_workflow_knowledge(self.knowledge)
        self.styles = type("Styles", (), {"get_selection": lambda _, snapshot: {
            "snapshot_id": snapshot, "production_type": "Drama", "style_version_id": "drama-v2",
            "directing_style": {"style_id": "horror", "version": 1,
                "guidance": "Use controlled darkness and restrained reveals.", "style_hash": "a" * 64},
            "narrative_hash": "b" * 64, "director_profile_hash": "c" * 64,
            "narrative_guidance": {"video": "Hold a restrained static camera; use monochrome lighting."},
            "director_profile": {"camera": "locked-off"}}})()
        self.drafts = PromptDrafts(self.ledger, self.story, self.knowledge, self.styles)
        self.setup_value = {"mode": "assisted_manual", "automate_steps": {
            "character_images": False, "character_voice": False, "world_images": False,
            "frame_images": False, "video": False}, "video_quality": "high",
            "duration_policy": {"kind": "fixed", "seconds": 6}}
        self.setup.save("ws-a", "sp-a", self.setup_value)

    def tearDown(self):
        self.temp.cleanup()

    def test_frozen_run_parameters_survive_changes_to_current_setup(self):
        changed = {**self.setup_value, "video_quality": "standard",
            "duration_policy": {"kind": "fixed", "seconds": 10}}
        self.setup.save("ws-a", "sp-a", changed)
        with patch("story_builder.services.reasoning_provider.generate_json",
                   return_value={"prompt": "A door opens."}) as model:
            self.drafts.prepare("ws-a", "sp-a", "1.1", T2V_WORKFLOW_ID,
                setup_snapshot=self.setup_value)
        prompt = model.call_args.kwargs["prompt"]
        self.assertIn('"video_quality": "high"', prompt)
        self.assertIn('"seconds": 6', prompt)
        self.assertIn('"style_id": "horror"', prompt)
        self.assertIn("Use controlled darkness and restrained reveals.", prompt)
        self.assertNotIn('"video_quality": "standard"', prompt)
        self.assertNotIn('"seconds": 10', prompt)

    def test_prompt_drafts_persist_with_setup_and_screenplay_identity(self):
        value = {"1.1": {"workflow_id": T2V_WORKFLOW_ID, "prompt": "Scene action and holistic direction."}}
        saved = self.drafts.save("ws-a", "sp-a", self.setup_value, value)
        restored = self.drafts.get("ws-a", "sp-a")
        self.assertEqual(saved["drafts"], value)
        self.assertEqual(restored["drafts"], value)
        self.assertTrue(restored["setup_matches_current"])
        self.assertEqual(restored["setup_hash"], saved["setup_hash"])

    def test_reached_shot_can_be_saved_incrementally_and_merges_existing_prompts(self):
        initial = {"1.1": {"workflow_id": T2V_WORKFLOW_ID, "prompt": "First shot."}}
        self.drafts.save("ws-a", "sp-a", self.setup_value, initial)
        with sqlite3.connect(self.path) as db:
            screenplay = json.loads(db.execute("SELECT screenplay_json FROM story_screenplay_revisions WHERE screenplay_revision_id='sp-a'").fetchone()[0])
            screenplay["scenes"][0]["shots"].append({"shot_number": 2, "action": "A light switches on.", "direction": {}})
            db.execute("UPDATE story_screenplay_revisions SET screenplay_json=? WHERE screenplay_revision_id='sp-a'", (json.dumps(screenplay),))
        saved = self.drafts.save_shot("ws-a", "sp-a", self.setup_value, "1.2",
            {"workflow_id": T2V_WORKFLOW_ID, "prompt": "Second shot."})
        self.assertEqual(saved["drafts"], {**initial, "1.2": {"workflow_id": T2V_WORKFLOW_ID, "prompt": "Second shot."}})

    def test_rejects_missing_setup_stale_screenplay_and_changed_setup(self):
        value = {"1.1": {"workflow_id": T2V_WORKFLOW_ID, "prompt": "Prompt."}}
        other = {**self.setup_value, "video_quality": "standard"}
        with self.assertRaisesRegex(LedgerConflict, "setup changed"):
            self.drafts.save("ws-a", "sp-a", other, value)
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE story_workspaces SET current_revision_id='source-b'")
        with self.assertRaisesRegex(LedgerConflict, "current accepted screenplay"):
            self.drafts.save("ws-a", "sp-a", self.setup_value, value)

    def test_rejects_unsafe_shot_key_workflow_and_prompt_limit(self):
        base = {"workflow_id": T2V_WORKFLOW_ID, "prompt": "ok"}
        for key, draft in [("../1", base), ("1.1", {**base, "workflow_id": "unknown"}), ("1.1", {**base, "prompt": "x" * 7000})]:
            with self.subTest(key=key, prompt_length=len(draft["prompt"])):
                with self.assertRaises(ValueError):
                    self.drafts.save("ws-a", "sp-a", self.setup_value, {key: draft})

    def test_requires_exact_scene_shot_set(self):
        with self.assertRaisesRegex(ValueError, "match every scene and shot"):
            self.drafts.save("ws-a", "sp-a", self.setup_value, {"99.99": {"workflow_id": T2V_WORKFLOW_ID, "prompt": "ok"}})
        with self.assertRaisesRegex(ValueError, "every scene.shot"):
            self.drafts.save("ws-a", "sp-a", self.setup_value, {})

    def test_assisted_automated_video_requires_run_workflow_for_every_shot_prompt(self):
        steps = {**self.setup_value["automate_steps"], "video": True}
        setup_value = {**self.setup_value, "automate_steps": steps,
            "video_workflow_id": R2V_WORKFLOW_ID}
        self.setup.save("ws-a", "sp-a", setup_value)
        with self.assertRaisesRegex(ValueError, "single workflow selected"):
            self.drafts.save("ws-a", "sp-a", setup_value,
                {"1.1": {"workflow_id": T2V_WORKFLOW_ID, "prompt": "Wrong route."}})
        saved = self.drafts.save("ws-a", "sp-a", setup_value,
            {"1.1": {"workflow_id": R2V_WORKFLOW_ID, "prompt": "Use the selected references."}})
        self.assertEqual(saved["drafts"]["1.1"]["workflow_id"], R2V_WORKFLOW_ID)

    def test_prepare_uses_exact_workflow_guidance_and_returns_provenance(self):
        from story_builder.services.isolated_fl2va_contract import WORKFLOW_ID as FL2VA
        with patch("story_builder.services.reasoning_provider.generate_json", return_value={"prompt": "One continuous shot moves from the first frame to the last."}) as model:
            result = self.drafts.prepare("ws-a", "sp-a", "1.1", FL2VA)
        self.assertEqual(result["workflow_id"], FL2VA)
        self.assertEqual(result["knowledge_ref"]["guidance_version"], 1)
        self.assertEqual(result["style_ref"], {"snapshot_id": "style-a", "style_version_id": "drama-v2",
            "narrative_hash": "b" * 64, "director_profile_hash": "c" * 64,
            "directing_style_hash": "a" * 64})
        self.assertEqual(result["prompt"], "One continuous shot moves from the first frame to the last.")
        prompt = model.call_args.kwargs["prompt"]
        self.assertIn("frame_interpolation", prompt)
        self.assertIn("A quiet confrontation", prompt)
        self.assertIn("low strings", prompt)
        self.assertIn("Hold a restrained static camera", prompt)
        self.assertIn('"video_quality": "high"', prompt)
        self.assertIn('"seconds": 6', prompt)
        saved = self.drafts.save("ws-a", "sp-a", self.setup_value, {"1.1": {
            "workflow_id": FL2VA, "prompt": result["prompt"], "knowledge_ref": result["knowledge_ref"],
            "style_ref": result["style_ref"]}})
        self.assertEqual(saved["drafts"]["1.1"]["knowledge_ref"], result["knowledge_ref"])
        self.assertEqual(saved["drafts"]["1.1"]["style_ref"], result["style_ref"])

    def test_rejects_malformed_or_changed_pinned_style_provenance(self):
        with patch("story_builder.services.reasoning_provider.generate_json", return_value={"prompt": "A restrained shot."}):
            prepared = self.drafts.prepare("ws-a", "sp-a", "1.1", T2V_WORKFLOW_ID)
        changed = {**prepared["style_ref"], "narrative_hash": "d" * 64}
        with self.assertRaisesRegex(LedgerConflict, "creative style changed"):
            self.drafts.save("ws-a", "sp-a", self.setup_value, {"1.1": {
                "workflow_id": T2V_WORKFLOW_ID, "prompt": prepared["prompt"], "style_ref": changed}})
        malformed = {**prepared["style_ref"], "directing_style_hash": "bad"}
        with self.assertRaisesRegex(ValueError, "malformed creative style provenance"):
            self.drafts.save("ws-a", "sp-a", self.setup_value, {"1.1": {
                "workflow_id": T2V_WORKFLOW_ID, "prompt": prepared["prompt"], "style_ref": malformed}})


if __name__ == "__main__":
    unittest.main()
