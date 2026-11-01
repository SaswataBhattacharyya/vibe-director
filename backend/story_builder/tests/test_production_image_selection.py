from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from story_builder.services.production_image_jobs import LedgerConflict
from story_builder.services.production_image_selection import ProductionImageSelection


class ProductionImageSelectionTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.path = Path(self.tempdir.name) / "jobs.sqlite3"
        self.store = ProductionImageSelection(self.path)
        self.target = dict(project_id="story-123", screenplay_revision_id="screenplay-1",
            target_type="character", target_record_id="entity-1")

    def test_selection_is_idempotent_and_user_replacement_keeps_history(self):
        first = self.store.select(**self.target, asset_id="pa-0000000000000001", job_id="job-1",
            authority="user", decision={"kind": "explicit_candidate_selection"})
        replay = self.store.select(**self.target, asset_id="pa-0000000000000001", job_id="job-1",
            authority="user", decision={"kind": "explicit_candidate_selection"})
        self.assertFalse(first["replayed"])
        self.assertTrue(replay["replayed"])

        replacement = self.store.select(**self.target, asset_id="pa-0000000000000002", job_id="job-2",
            authority="user", decision={"kind": "explicit_candidate_selection"})
        self.assertEqual(replacement["asset_id"], "pa-0000000000000002")
        self.assertEqual(replacement["authority"], "user")
        with sqlite3.connect(self.path) as db:
            rows = db.execute("SELECT prior_asset_id,asset_id FROM production_image_selection_history ORDER BY event_id").fetchall()
        self.assertEqual(rows, [(None, "pa-0000000000000001"),
                                ("pa-0000000000000001", "pa-0000000000000002")])

    def test_director_cannot_replace_existing_target_master(self):
        self.store.select(**self.target, asset_id="pa-0000000000000001", job_id="job-1",
            authority="director", decision={"action": "accept"})
        with self.assertRaisesRegex(LedgerConflict, "already exists"):
            self.store.select(**self.target, asset_id="pa-0000000000000002", job_id="job-2",
                authority="director", decision={"action": "accept"})
        self.assertEqual(self.store.get(**self.target)["asset_id"], "pa-0000000000000001")


if __name__ == "__main__":
    unittest.main()
