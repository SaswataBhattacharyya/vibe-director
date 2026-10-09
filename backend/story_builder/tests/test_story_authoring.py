from __future__ import annotations

import tempfile
import unittest
import warnings
import uuid
from pathlib import Path
from unittest.mock import patch

from story_builder.services.production_ledger import LedgerConflict, ProductionLedger
from story_builder.services.story_authoring import StoryAuthoring


class StoryAuthoringTests(unittest.TestCase):
    def setUp(self):
        warnings.simplefilter("ignore", ResourceWarning)
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        root = Path(self.temporary.name)
        self.ledger_path = root / "data/ledger.sqlite3"
        self.data_root = root / "data"
        self.ledger = ProductionLedger(self.ledger_path)
        self.authoring = StoryAuthoring(self.ledger, data_root=self.data_root, chunk_chars=128)

    def test_unicode_source_chunks_round_trip_and_restart(self):
        source = ("😀🌒 — long story line.\n\n" * 60) + "ending Ω"
        workspace = self.authoring.create_workspace(title="Long story", source_text=source)
        revision_id = workspace["current_revision"]["revision_id"]
        self.assertEqual(workspace["current_revision"]["source_text"], source)
        chunks = workspace["current_revision"]["source_chunks"]
        self.assertGreater(len(chunks), 1)
        self.assertEqual("".join(row["text"] for row in chunks), source)
        self.assertEqual(chunks[0]["start"], 0)
        self.assertEqual(chunks[-1]["end"], len(source))
        self.assertTrue(all(left["end"] == right["start"] for left, right in zip(chunks, chunks[1:])))

        restarted = StoryAuthoring(ProductionLedger(self.ledger_path), data_root=self.data_root, chunk_chars=128)
        loaded = restarted.get_workspace(workspace["workspace_id"])
        self.assertEqual(loaded["current_revision_id"], revision_id)
        self.assertEqual(loaded["current_revision"]["source_text"], source)
        page = restarted.list_revisions(workspace["workspace_id"], limit=1)
        self.assertEqual(page["total"], 1)
        self.assertEqual(page["items"][0]["revision_id"], revision_id)

    def test_selected_unicode_edit_preserves_outside_text_and_restore_is_new_child(self):
        source = "Before 😀. The old phrase stays. After Ω."
        workspace = self.authoring.create_workspace(title="Edit", source_text=source)
        base_id = workspace["current_revision"]["revision_id"]
        selected = "old phrase"
        start = source.index(selected)
        proposal = self.authoring.propose_selected_edit(workspace_id=workspace["workspace_id"],
            base_revision_id=base_id, start_codepoint=start, end_codepoint=start + len(selected),
            expected_text=selected, replacement="new phrase", instruction="Clarify the wording.")
        edited = self.authoring.accept_selected_edit(workspace_id=workspace["workspace_id"],
            proposal_id=proposal["proposal_id"], expected_current_revision_id=base_id)
        expected = source[:start] + "new phrase" + source[start + len(selected):]
        self.assertEqual(edited["source_text"], expected)
        self.assertEqual(edited["source_text"][:start], source[:start])
        self.assertEqual(edited["source_text"][start + len("new phrase"):], source[start + len(selected):])
        self.assertEqual(self.authoring.get_edit_proposal(workspace_id=workspace["workspace_id"],
            proposal_id=proposal["proposal_id"])["status"], "accepted")

        restored = self.authoring.restore_revision(workspace_id=workspace["workspace_id"],
            revision_id=base_id, expected_current_revision_id=edited["revision_id"])
        self.assertEqual(restored["source_text"], source)
        self.assertNotEqual(restored["revision_id"], base_id)
        self.assertEqual(restored["parent_revision_id"], edited["revision_id"])
        self.assertEqual(self.authoring.get_workspace(workspace["workspace_id"])["current_revision_id"],
                         restored["revision_id"])

    def test_stale_proposal_and_optimistic_concurrent_revision_conflict(self):
        workspace = self.authoring.create_workspace(title="Concurrency", source_text="One. Two.")
        base_id = workspace["current_revision"]["revision_id"]
        first = self.authoring.propose_selected_edit(workspace_id=workspace["workspace_id"],
            base_revision_id=base_id, start_codepoint=0, end_codepoint=3,
            expected_text="One", replacement="First")
        second = self.authoring.propose_selected_edit(workspace_id=workspace["workspace_id"],
            base_revision_id=base_id, start_codepoint=5, end_codepoint=8,
            expected_text="Two", replacement="Second")
        accepted = self.authoring.accept_selected_edit(workspace_id=workspace["workspace_id"],
            proposal_id=first["proposal_id"], expected_current_revision_id=base_id)
        with self.assertRaises(LedgerConflict):
            self.authoring.accept_selected_edit(workspace_id=workspace["workspace_id"],
                proposal_id=second["proposal_id"], expected_current_revision_id=base_id)
        with self.assertRaises(LedgerConflict):
            self.authoring.write_revision(workspace_id=workspace["workspace_id"],
                source_text="stale writer", expected_current_revision_id=base_id)
        self.assertEqual(self.authoring.get_workspace(workspace["workspace_id"])["current_revision_id"],
                         accepted["revision_id"])

    def test_invalid_workspace_offsets_and_quote_mismatch_are_rejected(self):
        with self.assertRaises(ValueError):
            self.authoring.get_workspace("../outside")
        workspace = self.authoring.create_workspace(title="Bounds", source_text="A story.")
        revision_id = workspace["current_revision"]["revision_id"]
        for start, end in ((True, 1), (-1, 1), (0, 100)):
            with self.assertRaises(ValueError):
                self.authoring.propose_selected_edit(workspace_id=workspace["workspace_id"],
                    base_revision_id=revision_id, start_codepoint=start, end_codepoint=end,
                    expected_text="", replacement="x")
        with self.assertRaises(LedgerConflict):
            self.authoring.propose_selected_edit(workspace_id=workspace["workspace_id"],
                base_revision_id=revision_id, start_codepoint=0, end_codepoint=1,
                expected_text="Z", replacement="x")

    def test_revision_listing_uses_monotonic_sequence_not_timestamp_or_random_id(self):
        workspace = self.authoring.create_workspace(title="Order", source_text="revision 1")
        current = workspace["current_revision"]["revision_id"]
        ids = [current]
        for number in range(2, 5):
            revision = self.authoring.write_revision(workspace_id=workspace["workspace_id"],
                source_text=f"revision {number}", expected_current_revision_id=current)
            current = revision["revision_id"]
            ids.append(current)
        with self.ledger._connect() as db:
            db.execute("UPDATE story_revision_index SET created_at='2026-10-08T00:00:00+00:00' WHERE workspace_id=?",
                       (workspace["workspace_id"],))
        page = self.authoring.list_revisions(workspace["workspace_id"], limit=4)
        self.assertEqual([row["revision_id"] for row in page["items"]], list(reversed(ids)))
        self.assertEqual([row["revision_number"] for row in page["items"]], [4, 3, 2, 1])

    def test_revision_id_collision_never_overwrites_existing_immutable_file(self):
        workspace = self.authoring.create_workspace(title="Collision", source_text="keep original")
        original = workspace["current_revision"]
        original_path = self.data_root / workspace["workspace_id"] / "production_v2" / "runs" / workspace["authoring_uuid"] / "story" / "revisions" / f"{original['revision_id']}.json"
        original_bytes = original_path.read_bytes()
        colliding = uuid.UUID(hex=original["revision_id"].removeprefix("story-canon-") + "0" * 20)
        replacement_id = uuid.UUID("abcdef12-3456-7890-abcd-ef1234567890")
        with patch("story_builder.services.story_authoring.uuid.uuid4", side_effect=[colliding, replacement_id]):
            revised = self.authoring.write_revision(workspace_id=workspace["workspace_id"],
                source_text="second source", expected_current_revision_id=original["revision_id"])
        self.assertNotEqual(revised["revision_id"], original["revision_id"])
        self.assertEqual(original_path.read_bytes(), original_bytes)
        self.assertEqual(self.authoring.get_revision(workspace["workspace_id"], original["revision_id"])["source_text"],
                         "keep original")

    def test_incomplete_workspace_is_listed_and_can_be_initialized_after_restart(self):
        workspace_id = "story-aaaaaaaaaaaa"
        authoring_uuid = str(uuid.uuid4())
        with self.ledger._connect() as db:
            db.execute("INSERT INTO story_workspaces(workspace_id,title,authoring_uuid) VALUES(?,?,?)",
                       (workspace_id, "Interrupted create", authoring_uuid))
        restarted = StoryAuthoring(ProductionLedger(self.ledger_path), data_root=self.data_root, chunk_chars=128)
        incomplete = restarted.get_workspace(workspace_id)
        self.assertFalse(incomplete["initialized"])
        self.assertEqual(incomplete["status"], "initializing")
        listed = restarted.list_workspaces()
        self.assertEqual(listed["total"], 1)
        self.assertFalse(listed["items"][0]["initialized"])
        initialized = restarted.initialize_workspace(workspace_id=workspace_id, source_text="recovered source")
        self.assertEqual(restarted.get_workspace(workspace_id)["current_revision"]["revision_id"],
                         initialized["revision_id"])
        with self.assertRaises(LedgerConflict):
            restarted.initialize_workspace(workspace_id=workspace_id, source_text="second initialization")


if __name__ == "__main__":
    unittest.main()
