import tempfile
import unittest
import sqlite3
from pathlib import Path
from unittest.mock import patch

from story_builder.services.character_voice_bindings import CharacterVoiceBindings
from story_builder.services.production_ledger import LedgerConflict, ProductionLedger
from story_builder.services.production_setup import ProductionSetup


class Story:
    def get_screenplay_revision(self, workspace_id, screenplay_revision_id):
        return {"accepted": True, "graph_snapshot_id": "graph-1"}

    def get_story_graph(self, *, workspace_id, snapshot_id):
        return {"snapshot_id": snapshot_id, "status": "complete", "records": [
            {"record_id": "character-a", "kind": "entity", "type": "character", "name": "Asha", "detail": "Asha description."},
            {"record_id": "character-b", "kind": "entity", "type": "character", "name": "Ravi", "detail": ""},
            {"record_id": "event-a", "kind": "event", "type": "character", "name": "Not a person", "detail": ""},
        ]}


class CharacterVoiceBindingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.ledger = ProductionLedger(self.root / "ledger.sqlite3")
        self.story = Story()
        self.setup = ProductionSetup(self.ledger, self.story)
        self.store = CharacterVoiceBindings(self.ledger, self.root, self.story, self.setup)
        self.save_setup()

    def save_setup(self, *, mode="assisted_manual", character_voice=False):
        import json
        setup = {"mode": mode, "automate_steps": {"character_images": False, "character_voice": character_voice,
            "world_images": False, "frame_images": False, "video": False}, "video_quality": "standard",
            "duration_policy": {"kind": "fixed", "seconds": 5}}
        with self.ledger._connect() as db:
            db.execute("INSERT OR REPLACE INTO story_production_setups(workspace_id,screenplay_revision_id,setup_json) VALUES(?,?,?)",
                ("workspace-a", "screenplay-a", json.dumps(setup, sort_keys=True, separators=(",", ":"))))

    def tearDown(self):
        self.temp.cleanup()

    @patch("story_builder.services.character_voice_bindings.list_assets")
    def test_one_workspace_voice_can_be_reused_and_cleared(self, list_assets):
        list_assets.return_value = {"assets": [{"asset_id": "pa-aaaaaaaaaaaaaaaa", "roles": ["voice_master"]}], "total": 1}
        self.store.set("workspace-a", "screenplay-a", "character-a", "pa-aaaaaaaaaaaaaaaa")
        result = self.store.set("workspace-a", "screenplay-a", "character-b", "pa-aaaaaaaaaaaaaaaa")
        self.assertEqual({row["character_id"] for row in result["bindings"]}, {"character-a", "character-b"})
        result = self.store.set("workspace-a", "screenplay-a", "character-a", None)
        self.assertEqual([(row["character_id"], row["voice_asset_id"]) for row in result["bindings"]],
            [("character-b", "pa-aaaaaaaaaaaaaaaa")])

    @patch("story_builder.services.character_voice_bindings.list_assets")
    def test_rejects_non_voice_asset_and_noncanonical_character(self, list_assets):
        list_assets.return_value = {"assets": [{"asset_id": "pa-bbbbbbbbbbbbbbbb", "roles": ["project_audio"]}], "total": 1}
        with self.assertRaisesRegex(ValueError, "marked as a voice reference"):
            self.store.set("workspace-a", "screenplay-a", "character-a", "pa-bbbbbbbbbbbbbbbb")
        with self.assertRaisesRegex(LedgerConflict, "current accepted graph"):
            self.store.set("workspace-a", "screenplay-a", "event-a", None)

    def test_rejects_unaccepted_screenplay(self):
        self.store.story.get_screenplay_revision = lambda *_: {"accepted": False}
        with self.assertRaisesRegex(LedgerConflict, "current accepted screenplay"):
            self.store.get("workspace-a", "screenplay-old")

    @patch("story_builder.services.character_voice_bindings.list_assets")
    def test_manual_binding_requires_unchecked_assisted_setup(self, list_assets):
        list_assets.return_value = {"assets": [{"asset_id": "pa-eeeeeeeeeeeeeeee", "roles": ["voice_master"]}], "total": 1}
        self.save_setup(character_voice=True)
        with self.assertRaisesRegex(LedgerConflict, "configured for automation"):
            self.store.set("workspace-a", "screenplay-a", "character-a", "pa-eeeeeeeeeeeeeeee")
        with self.assertRaisesRegex(LedgerConflict, "configured for automation"):
            self.store.set("workspace-a", "screenplay-a", "character-a", None)
        self.save_setup(mode="fully_automated", character_voice=False)
        with self.assertRaisesRegex(LedgerConflict, "Fully automated"):
            self.store.set("workspace-a", "screenplay-a", "character-a", "pa-eeeeeeeeeeeeeeee")
        self.save_setup(mode="assisted_manual", character_voice=False)
        result = self.store.set("workspace-a", "screenplay-a", "character-a", "pa-eeeeeeeeeeeeeeee")
        self.assertEqual(result["bindings"][0]["voice_asset_id"], "pa-eeeeeeeeeeeeeeee")

    @patch("story_builder.services.character_voice_bindings.list_assets")
    def test_automatic_matching_assigns_only_unique_explicit_matches_and_pauses_for_choice(self, list_assets):
        self.save_setup(character_voice=True)
        list_assets.return_value = {"assets": [
            {"asset_id": "pa-1111111111111111", "roles": ["voice_master"], "filename": "Asha voice.wav", "tags": [], "audio_category": "voice"},
            {"asset_id": "pa-2222222222222222", "roles": ["voice_master"], "filename": "Ravi warm.wav", "tags": ["Ravi"], "audio_category": "voice"},
            {"asset_id": "pa-3333333333333333", "roles": ["voice_master"], "filename": "Ravi take two.wav", "tags": [], "audio_category": "voice"},
        ], "total": 3}
        with patch.object(self.setup, "_accepted_revision", return_value={}):
            state = self.store.run_automatic("workspace-a", "screenplay-a")
        decisions = {item["character_id"]: item for item in state["automation_result"]}
        self.assertEqual(decisions["character-a"]["status"], "matched")
        self.assertEqual(decisions["character-a"]["voice_asset_id"], "pa-1111111111111111")
        self.assertEqual(decisions["character-b"]["status"], "ambiguous")
        self.assertIsNone(decisions["character-b"]["voice_asset_id"])
        resolved = self.store.set("workspace-a", "screenplay-a", "character-b", "pa-2222222222222222")
        self.assertEqual(next(item for item in resolved["automation_decisions"] if item["character_id"] == "character-b")["status"], "resolved_manually")
        with patch.object(self.setup, "_accepted_revision", return_value={}):
            again = self.store.run_automatic("workspace-a", "screenplay-a")
        self.assertEqual(next(item for item in again["automation_decisions"] if item["character_id"] == "character-b")["status"], "resolved_manually")

    @patch("story_builder.services.character_voice_bindings.list_assets")
    def test_automatic_bindings_can_be_changed_cleared_and_stay_cleared(self, list_assets):
        self.save_setup(character_voice=True)
        list_assets.return_value = {"assets": [
            {"asset_id": "pa-1111111111111111", "roles": ["voice_master"], "filename": "Asha voice.wav"},
            {"asset_id": "pa-2222222222222222", "roles": ["voice_master"], "filename": "Other.wav"},
        ], "total": 2}
        with patch.object(self.setup, "_accepted_revision", return_value={}):
            self.store.run_automatic("workspace-a", "screenplay-a")
        self.store.set("workspace-a", "screenplay-a", "character-a", "pa-2222222222222222")
        self.store.set("workspace-a", "screenplay-a", "character-a", None)
        with patch.object(self.setup, "_accepted_revision", return_value={}):
            state = self.store.run_automatic("workspace-a", "screenplay-a")
        self.assertFalse(any(row["character_id"] == "character-a" for row in state["bindings"]))
        state = self.store.set("workspace-a", "screenplay-a", "character-a", "pa-1111111111111111")
        self.assertEqual(state["bindings"][0]["voice_asset_id"], "pa-1111111111111111")

    @patch("story_builder.services.character_voice_bindings.list_assets")
    def test_auto_voice_assignment_requires_checked_assisted_step(self, list_assets):
        self.save_setup(character_voice=False)
        with self.assertRaisesRegex(LedgerConflict, "Enable Character-to-audio selection"):
            self.store.run_automatic("workspace-a", "screenplay-a")

    @patch("story_builder.services.character_voice_bindings.list_assets")
    def test_automatic_matching_does_not_assign_voices_to_non_speaking_characters(self, list_assets):
        self.save_setup(character_voice=True)
        self.store.story.get_screenplay_revision = lambda *_: {"accepted": True, "graph_snapshot_id": "graph-1",
            "screenplay": {"scenes": [{"shots": [{"dialogue": "Asha: Stay behind me."}]}]}}
        list_assets.return_value = {"assets": [
            {"asset_id": "pa-1111111111111111", "roles": ["voice_master"], "filename": "Asha.wav", "tags": [], "audio_category": "voice"},
            {"asset_id": "pa-2222222222222222", "roles": ["voice_master"], "filename": "Ravi.wav", "tags": [], "audio_category": "voice"},
        ], "total": 2}
        with patch.object(self.setup, "_accepted_revision", return_value={}):
            result = self.store.run_automatic("workspace-a", "screenplay-a")
        by_character = {item["character_id"]: item for item in result["automation_result"]}
        self.assertEqual(by_character["character-a"]["status"], "matched")
        self.assertEqual(by_character["character-b"]["status"], "not_speaking")

    def test_readable_state_distinguishes_speakers_narrator_and_non_speakers(self):
        self.story.get_screenplay_revision = lambda *_: {"accepted": True, "graph_snapshot_id": "graph-1",
            "screenplay": {"scenes": [{"shots": [{"dialogue": "Asha: Stay behind me.\nNarrator (V.O.): The door opens."}]}]}}
        original_graph = self.story.get_story_graph
        def graph_with_narrator(*, workspace_id, snapshot_id):
            graph = original_graph(workspace_id=workspace_id, snapshot_id=snapshot_id)
            graph["records"].append({"record_id": "character-narrator", "kind": "entity", "type": "character",
                "name": "Narrator", "detail": ""})
            return graph
        self.story.get_story_graph = graph_with_narrator

        statuses = {row["character_id"]: row["status"]
            for row in self.store.get("workspace-a", "screenplay-a")["speech_statuses"]}
        self.assertEqual(statuses, {"character-a": "speaking", "character-b": "not_speaking",
            "character-narrator": "narrator"})

    def test_readable_state_marks_unmapped_speaker_labels_as_unknown(self):
        self.story.get_screenplay_revision = lambda *_: {"accepted": True, "graph_snapshot_id": "graph-1",
            "screenplay": {"scenes": [{"shots": [{"dialogue": "UNKNOWN: Who's there?"}]}]}}
        statuses = self.store.get("workspace-a", "screenplay-a")["speech_statuses"]
        self.assertEqual({row["status"] for row in statuses}, {"unknown"})

    def test_manual_binding_rejects_when_no_saved_setup_exists(self):
        with self.ledger._connect() as db:
            db.execute("DELETE FROM story_production_setups WHERE workspace_id=? AND screenplay_revision_id=?", ("workspace-a", "screenplay-a"))
        with self.assertRaisesRegex(LedgerConflict, "Save Automation & Parameters"):
            self.store.set("workspace-a", "screenplay-a", "character-a", None)

    @patch("story_builder.services.character_voice_bindings.list_assets")
    def test_readable_binding_state_does_not_require_manual_setup(self, list_assets):
        list_assets.return_value = {"assets": [{"asset_id": "pa-ffffffffffffffff", "roles": ["voice_master"]}], "total": 1}
        self.store.set("workspace-a", "screenplay-a", "character-a", "pa-ffffffffffffffff")
        with self.ledger._connect() as db:
            db.execute("DELETE FROM story_production_setups WHERE workspace_id=? AND screenplay_revision_id=?", ("workspace-a", "screenplay-a"))
        self.assertEqual(self.store.get("workspace-a", "screenplay-a")["bindings"][0]["voice_asset_id"], "pa-ffffffffffffffff")

    @patch("story_builder.services.character_voice_bindings.list_assets")
    def test_voice_validation_pages_past_first_hundred_assets(self, list_assets):
        list_assets.side_effect = [
            {"assets": [{"asset_id": f"pa-{index:016x}", "roles": ["project_audio"]} for index in range(100)], "total": 101},
            {"assets": [{"asset_id": "pa-cccccccccccccccc", "roles": ["voice_master"]}], "total": 101},
        ]
        self.store.set("workspace-a", "screenplay-a", "character-a", "pa-cccccccccccccccc")
        self.assertEqual(list_assets.call_args_list[1].kwargs["offset"], 100)

    @patch("story_builder.services.character_voice_bindings.list_assets")
    def test_superseded_screenplay_during_media_validation_does_not_commit_binding(self, list_assets):
        def media_lookup(*args, **kwargs):
            self.store.story.get_screenplay_revision = lambda *_: {"accepted": False}
            return {"assets": [{"asset_id": "pa-dddddddddddddddd", "roles": ["voice_master"]}], "total": 1}
        list_assets.side_effect = media_lookup
        with self.assertRaisesRegex(LedgerConflict, "current accepted screenplay"):
            self.store.set("workspace-a", "screenplay-a", "character-a", "pa-dddddddddddddddd")
        with sqlite3.connect(self.ledger.path) as db:
            count = db.execute("SELECT COUNT(*) FROM story_character_voice_bindings").fetchone()[0]
        self.assertEqual(count, 0)


if __name__ == "__main__":
    unittest.main()
