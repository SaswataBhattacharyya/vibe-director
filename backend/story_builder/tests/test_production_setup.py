import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from story_builder.services.production_ledger import LedgerConflict, ProductionLedger
from story_builder.services.production_setup import ProductionSetup


class Story:
    @staticmethod
    def _screenplay_is_currently_accepted(db, row):
        current = db.execute("SELECT current_revision_id FROM story_workspaces WHERE workspace_id=?", (row["workspace_id"],)).fetchone()
        latest = db.execute("SELECT screenplay_revision_id FROM story_screenplay_revisions WHERE workspace_id=? AND source_revision_id=? ORDER BY rowid DESC LIMIT 1",
            (row["workspace_id"], row["source_revision_id"])).fetchone()
        return bool(row["accepted_at"] and current and current["current_revision_id"] == row["source_revision_id"]
            and latest and latest["screenplay_revision_id"] == row["screenplay_revision_id"])


class ProductionSetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "ledger.sqlite3"
        self.ledger = ProductionLedger(self.path)
        with sqlite3.connect(self.path) as db:
            db.executescript("""
                CREATE TABLE story_workspaces(workspace_id TEXT PRIMARY KEY,current_revision_id TEXT);
                CREATE TABLE story_screenplay_revisions(screenplay_revision_id TEXT PRIMARY KEY,workspace_id TEXT,source_revision_id TEXT,accepted_at TEXT,screenplay_json TEXT);
                INSERT INTO story_workspaces VALUES('ws-a','source-a');
            """)
            db.execute("INSERT INTO story_screenplay_revisions VALUES(?,?,?,?,?)", (
                "sp-a", "ws-a", "source-a", "2026-10-10",
                json.dumps({"scenes": [{"scene_number": 1, "shots": [{"shot_number": 1}, {"shot_number": 2}]}]})))
        self.store = ProductionSetup(self.ledger, Story())

    def tearDown(self):
        self.temp.cleanup()

    def setup_value(self, **change):
        value = {"mode": "assisted_manual", "automate_steps": {
            "character_images": False, "character_voice": False, "world_images": False,
            "frame_images": False, "video": False}, "video_quality": "high",
            "duration_policy": {"kind": "fixed", "seconds": 6}}
        return {**value, **change}

    def test_setup_persists_for_exact_accepted_revision(self):
        value = self.setup_value(mode="fully_automated", video_quality="standard",
            duration_policy={"kind": "director_selected", "min_seconds": 5, "max_seconds": 10})
        saved = self.store.save("ws-a", "sp-a", value)
        self.assertEqual(saved["setup"], value)
        self.assertEqual(self.store.get("ws-a", "sp-a")["setup"], value)

    def test_none_some_all_checkbox_semantics_are_preserved(self):
        steps = self.setup_value()["automate_steps"]
        self.assertFalse(any(steps.values()))
        steps["character_images"] = steps["video"] = True
        self.assertEqual(sum(steps.values()), 2)
        self.assertEqual(sum({**steps, "world_images": True, "character_voice": True, "frame_images": True}.values()), 5)
        settings = {"character_images": {"workflow_id": "z_image_turbo", "width": 1280,
            "height": 720, "steps": 8, "cfg": 1}}
        saved = self.store.save("ws-a", "sp-a", self.setup_value(automate_steps=steps,
            image_stage_settings=settings, video_workflow_id="minimax_h3_r2v_dynamic_v1"))
        self.assertEqual(saved["setup"]["automate_steps"], steps)

    def test_invalid_values_and_superseded_screenplay_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "5–10"):
            self.store.save("ws-a", "sp-a", self.setup_value(duration_policy={"kind": "fixed", "seconds": 11}))
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE story_workspaces SET current_revision_id='source-b' WHERE workspace_id='ws-a'")
        with self.assertRaisesRegex(LedgerConflict, "current accepted screenplay"):
            self.store.save("ws-a", "sp-a", self.setup_value())

    def test_automated_image_stages_require_supported_confirmed_parameters(self):
        steps = {**self.setup_value()["automate_steps"], "character_images": True}
        steps["video"] = True
        value = self.setup_value(automate_steps=steps, video_workflow_id="minimax_h3_r2v_dynamic_v1")
        with self.assertRaisesRegex(ValueError, "Confirm image workflow"):
            self.store.save("ws-a", "sp-a", value)
        value["image_stage_settings"] = {"character_images": {
            "workflow_id": "z_image_turbo", "width": 1280, "height": 720, "steps": 8, "cfg": 1.0}}
        value["video_workflow_id"] = "minimax_h3_r2v_dynamic_v1"
        self.assertEqual(self.store.save("ws-a", "sp-a", value)["setup"]["image_stage_settings"], value["image_stage_settings"])
        self.assertEqual(self.store.get("ws-a", "sp-a")["setup"]["video_workflow_id"], value["video_workflow_id"])
        for bad in (
            {"workflow_id": "qwen_image_edit_2511", "width": 1024, "height": 1024, "steps": 4, "cfg": 1},
            {"workflow_id": "z_image_turbo", "width": 1279, "height": 720, "steps": 8, "cfg": 1},
            {"workflow_id": "z_image_turbo", "width": 1280, "height": 720, "steps": 20, "cfg": 1},
        ):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                ProductionSetup.validate({**value, "image_stage_settings": {"character_images": bad}}, require_image_settings=True)
        with self.assertRaisesRegex(ValueError, "only be provided"):
            ProductionSetup.validate({**self.setup_value(), "image_stage_settings": value["image_stage_settings"]}, require_image_settings=True)

    def test_manual_image_stage_removes_only_its_automatic_settings(self):
        steps = {**self.setup_value()["automate_steps"],
            "character_images": True, "world_images": True, "frame_images": True}
        setting = {"workflow_id": "z_image_turbo", "width": 1280,
            "height": 720, "steps": 8, "cfg": 1}
        settings = {step: dict(setting) for step in
            ("character_images", "world_images", "frame_images")}
        settings["world_images"]["world_view_count"] = 4
        for manual_step in settings:
            with self.subTest(manual_step=manual_step):
                manual_steps = {**steps, manual_step: False}
                with self.assertRaisesRegex(ValueError, "only be provided"):
                    ProductionSetup.validate(self.setup_value(automate_steps=manual_steps,
                        image_stage_settings=settings), require_image_settings=True)
                remaining = {step: value for step, value in settings.items() if step != manual_step}
                saved = self.store.save("ws-a", "sp-a", self.setup_value(
                    automate_steps=manual_steps, image_stage_settings=remaining))
                self.assertEqual(saved["setup"]["image_stage_settings"], remaining)
                self.assertEqual(saved["setup"]["automate_steps"], manual_steps)
        saved = self.store.save("ws-a", "sp-a", self.setup_value(image_stage_settings={}))
        self.assertFalse(saved["setup"].get("image_stage_settings"))

    def test_qwen_edit_is_allowed_for_frame_stage_only(self):
        steps = {**self.setup_value()["automate_steps"], "frame_images": True}
        setting = {"workflow_id": "qwen_image_edit_2511", "width": 1024,
            "height": 1024, "steps": 4, "cfg": 1.0}
        saved = self.store.save("ws-a", "sp-a", self.setup_value(
            automate_steps=steps, image_stage_settings={"frame_images": setting}))
        self.assertEqual(saved["setup"]["image_stage_settings"]["frame_images"], setting)
        for step in ("character_images", "world_images"):
            with self.subTest(step=step), self.assertRaisesRegex(ValueError, "text-to-image workflow"):
                ProductionSetup.validate({**self.setup_value(),
                    "automate_steps": {**self.setup_value()["automate_steps"], step: True},
                    "image_stage_settings": {step: setting}}, require_image_settings=True)

    def test_world_view_count_is_world_only_and_defaults_to_four(self):
        steps = {**self.setup_value()["automate_steps"], "world_images": True}
        world_setting = {"workflow_id": "z_image_turbo", "width": 1280,
            "height": 720, "steps": 8, "cfg": 1.0}
        base = self.setup_value(automate_steps=steps, image_stage_settings={"world_images": world_setting})
        normalized = ProductionSetup.validate(base, require_image_settings=True)
        self.assertEqual(normalized["image_stage_settings"]["world_images"]["world_view_count"], 4)
        for count in (2, 3, 4, 8):
            with self.subTest(count=count):
                saved = self.store.save("ws-a", "sp-a", self.setup_value(automate_steps=steps,
                    image_stage_settings={"world_images": {**world_setting, "world_view_count": count}}))
                self.assertEqual(saved["setup"]["image_stage_settings"]["world_images"]["world_view_count"], count)
        for count in (True, 6, "8"):
            with self.subTest(invalid_count=count), self.assertRaisesRegex(ValueError, "exactly two, three, four or eight"):
                ProductionSetup.validate(self.setup_value(automate_steps=steps,
                    image_stage_settings={"world_images": {**world_setting, "world_view_count": count}}),
                    require_image_settings=True)
        character_steps = {**self.setup_value()["automate_steps"], "character_images": True}
        with self.assertRaisesRegex(ValueError, "needs a workflow"):
            ProductionSetup.validate(self.setup_value(automate_steps=character_steps,
                image_stage_settings={"character_images": {**world_setting, "world_view_count": 8}}),
                require_image_settings=True)

    def test_style_video_setup_freezes_unique_ids_and_intents(self):
        refs = [{"asset_id": "pa-0123456789abcdef", "sha256": "a" * 64, "intent": "Use this as a color reference."}]
        steps = {**self.setup_value()["automate_steps"], "video": True}
        setup = ProductionSetup.validate(self.setup_value(automate_steps=steps,
            video_workflow_id="minimax_h3_r2v_dynamic_v1", style_video_references=refs))
        self.assertEqual(setup["style_video_references"], refs)
        with self.assertRaisesRegex(ValueError, "only once"):
            ProductionSetup.validate(self.setup_value(automate_steps=steps,
                video_workflow_id="minimax_h3_r2v_dynamic_v1", style_video_references=refs * 2))
        with self.assertRaisesRegex(ValueError, "at most two"):
            ProductionSetup.validate(self.setup_value(automate_steps=steps,
                video_workflow_id="minimax_h3_r2v_dynamic_v1", style_video_references=refs * 3))
        with self.assertRaisesRegex(ValueError, "require Reference to video"):
            ProductionSetup.validate(self.setup_value(automate_steps=steps,
                video_workflow_id="minimax_h3_fl2va_first_last_v1", style_video_references=refs))
        # The selection may be retained while video automation is off, but it
        # cannot be used by the run until Assisted automatic video is enabled.
        self.assertEqual(ProductionSetup.validate(self.setup_value(style_video_references=refs))["style_video_references"], refs)

    def test_assisted_automated_video_requires_one_supported_run_workflow(self):
        steps = {**self.setup_value()["automate_steps"], "video": True}
        with self.assertRaisesRegex(ValueError, "one video workflow"):
            self.store.save("ws-a", "sp-a", self.setup_value(automate_steps=steps))
        for workflow_id in ("minimax_h3_fl2va_first_last_v1", "minimax_h3_r2v_dynamic_v1"):
            value = self.setup_value(automate_steps=steps, video_workflow_id=workflow_id)
            self.assertEqual(self.store.save("ws-a", "sp-a", value)["setup"]["video_workflow_id"], workflow_id)
        with self.assertRaisesRegex(ValueError, "only when Assisted manual Video Generation is checked"):
            ProductionSetup.validate(self.setup_value(video_workflow_id="minimax_h3_r2v_dynamic_v1"))
        bad = self.setup_value(automate_steps=steps, video_workflow_id="minimax_h3_t2v_local_v1")
        with self.assertRaisesRegex(ValueError, "Choose FFLF or R2V"):
            ProductionSetup.validate(bad)

    def test_frame_skip_is_durable_scoped_to_existing_accepted_shots_and_reversible(self):
        saved = self.store.set_frame_preparation_skip("ws-a", "sp-a", 1, 2, True)
        self.assertEqual(saved["skipped"], [{"scene_number": 1, "shot_number": 2}])
        self.assertEqual(self.store.list_frame_preparation_skips("ws-a", "sp-a")["skipped"], saved["skipped"])
        self.assertTrue(self.store.frame_preparation_is_skipped("ws-a", "sp-a", 1, 2))
        self.store.set_frame_preparation_skip("ws-a", "sp-a", 1, 2, False)
        self.assertFalse(self.store.frame_preparation_is_skipped("ws-a", "sp-a", 1, 2))
        self.assertEqual(self.store.list_frame_preparation_skips("ws-a", "sp-a")["skipped"], [])

    def test_frame_skip_rejects_forged_shot_and_non_boolean(self):
        with self.assertRaisesRegex(LedgerConflict, "shot in the accepted screenplay"):
            self.store.set_frame_preparation_skip("ws-a", "sp-a", 2, 1, True)
        with self.assertRaisesRegex(ValueError, "boolean"):
            self.store.set_frame_preparation_skip("ws-a", "sp-a", 1, 1, 1)

    def test_assisted_optional_image_stage_skip_is_explicit_durable_and_only_for_unchecked_steps(self):
        self.store.save("ws-a", "sp-a", self.setup_value())
        saved = self.store.set_assisted_stage_skip("ws-a", "sp-a", "world_images", True)
        self.assertEqual(saved["skipped"], ["world_images"])
        self.assertEqual(self.store.list_assisted_stage_skips("ws-a", "sp-a")["skipped"], ["world_images"])
        self.store.set_assisted_stage_skip("ws-a", "sp-a", "world_images", False)
        self.assertEqual(self.store.list_assisted_stage_skips("ws-a", "sp-a")["skipped"], [])
        setup = self.setup_value(automate_steps={**self.setup_value()["automate_steps"], "world_images": True},
            image_stage_settings={"world_images": {"workflow_id": "z_image_turbo", "width": 1280,
                "height": 720, "steps": 8, "cfg": 1.0}})
        self.store.save("ws-a", "sp-a", setup)
        with self.assertRaisesRegex(LedgerConflict, "Only an unchecked optional image stage"):
            self.store.set_assisted_stage_skip("ws-a", "sp-a", "world_images", True)


if __name__ == "__main__":
    unittest.main()
