from __future__ import annotations

import io
import json
import sqlite3
import tempfile
import unittest
import warnings
from pathlib import Path

from story_builder.isolated_server import create_app
from story_builder.services.production_ledger import LedgerConflict, ProductionLedger
from story_builder.services.production_setup import ProductionSetup
from story_builder.services.production_styles import ProductionStyleService
from story_builder.services.story_authoring import StoryAuthoring


class StoryStyleLinkTests(unittest.TestCase):
    def setUp(self):
        warnings.simplefilter("ignore", ResourceWarning)
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.ledger_path = self.root / "services/production/ledger.sqlite3"
        self.ledger = ProductionLedger(self.ledger_path)
        self.styles = ProductionStyleService(self.ledger)
        self.app = create_app(data_root=self.root,
            capability_provider=lambda: self.fail("story style link probed generation capability"),
            gpu_reader=lambda: self.fail("story style link read GPU"))

    def call(self, method, path, value=None, content_type="application/json"):
        body = b"" if value is None else value if isinstance(value, bytes) else json.dumps(value).encode("utf-8")
        started = []
        request_path, _, query = path.partition("?")
        environ = {"REQUEST_METHOD": method, "PATH_INFO": request_path, "QUERY_STRING": query,
            "CONTENT_TYPE": content_type, "CONTENT_LENGTH": str(len(body)), "wsgi.input": io.BytesIO(body)}
        response = b"".join(self.app(environ, lambda status, headers: started.append(status)))
        return started[0], json.loads(response) if response.startswith(b"{") else response

    def custom(self, purpose):
        return self.styles.publish_custom_type("journal_style", {
            "story": "Protect observed facts.", "scene_direction": "Use clear pacing.",
            "image": "Use restrained composition.", "audio": "Keep speech clear.",
            "video": "Use purposeful motion.", "review": "Check evidence and continuity.",
        }, {"display_name": "Journal", "purpose": purpose,
            "behavior": ["Separate evidence from interpretation."],
            "review_priorities": ["source fidelity"]})

    def test_keyed_create_exposes_frozen_pin_across_newer_selection_and_replay(self):
        v1 = self.custom("Keep a field record.")
        first_selection = self.styles.select(isolated_context_id="setup-context-1",
            production_type="journal_style", style_version_id=v1["style_version_id"])
        key = "4d615879-04b0-4a17-946c-adcb9bec24d8"
        request = {"idempotency_key": key, "title": "Pinned story", "source_text": "Original story.",
                   "style_selection_snapshot_id": first_selection["snapshot_id"]}
        status, created = self.call("POST", "/api/story/workspaces", request)
        self.assertEqual(status, "201 Created")
        workspace_id = created["workspace"]["workspace_id"]
        self.assertEqual(created["workspace"]["style_selection"], first_selection)
        self.assertEqual(created["workspace"]["style_selection_snapshot_id"], first_selection["snapshot_id"])
        self.assertEqual(created["workspace"]["created_revision"]["metadata"]["style_selection"], first_selection)

        status, edited = self.call("POST", f"/api/story/workspaces/{workspace_id}/revisions", {
            "source_text": "Edited story.",
            "expected_current_revision_id": created["workspace"]["created_revision"]["revision_id"]})
        self.assertEqual(status, "201 Created")

        v2 = self.custom("Keep a detailed field record.")
        second_selection = self.styles.select(isolated_context_id="setup-context-1",
            production_type="journal_style", style_version_id=v2["style_version_id"])
        self.assertNotEqual(first_selection["snapshot_id"], second_selection["snapshot_id"])
        status, loaded = self.call("GET", f"/api/story/workspaces/{workspace_id}")
        self.assertEqual(status, "200 OK")
        self.assertEqual(loaded["style_selection"], first_selection)
        self.assertEqual(loaded["current_revision_id"], edited["revision_id"])
        status, listed = self.call("GET", "/api/story/workspaces")
        self.assertEqual(status, "200 OK")
        listed_workspace = next(item for item in listed["items"] if item["workspace_id"] == workspace_id)
        self.assertEqual(listed_workspace["style_selection_snapshot_id"], first_selection["snapshot_id"])
        self.assertNotIn("style_selection", listed_workspace)
        self.assertNotIn("source_text", listed_workspace)
        status, recovered = self.call("GET", f"/api/story/creations/by-idempotency/{key}")
        self.assertEqual(status, "200 OK")
        self.assertEqual(recovered["workspace"]["style_selection"], first_selection)
        status, replayed = self.call("POST", "/api/story/workspaces", request)
        self.assertEqual(status, "200 OK")
        self.assertEqual(replayed["workspace"]["style_selection"], first_selection)
        status, conflict = self.call("POST", "/api/story/workspaces", {
            **request, "style_selection_snapshot_id": second_selection["snapshot_id"]})
        self.assertEqual(status, "409 Conflict")

        status, invalid = self.call("POST", "/api/story/workspaces", {
            "title": "Unkeyed pin", "source_text": "A story.",
            "style_selection_snapshot_id": first_selection["snapshot_id"]})
        self.assertEqual(status, "422 Unprocessable Entity")

    def test_keyed_import_apply_preserves_import_lineage_and_style_on_replay(self):
        v1 = self.custom("Record observations from source material.")
        selection = self.styles.select(isolated_context_id="setup-context-2",
            production_type="journal_style", style_version_id=v1["style_version_id"])
        status, imported = self.call("POST", "/api/story/imports?filename=field-notes.txt",
                                     b"Field note source.\n", content_type="application/octet-stream")
        self.assertEqual(status, "201 Created")
        request = {"idempotency_key": "6d07cad0-e744-4555-b13e-7763200480f1",
            "title": "Imported notes", "source_text": imported["text"],
            "style_selection_snapshot_id": selection["snapshot_id"]}
        path = f"/api/story/imports/{imported['import_id']}/apply"
        status, applied = self.call("POST", path, request)
        self.assertEqual(status, "201 Created")
        metadata = applied["workspace"]["created_revision"]["metadata"]
        self.assertEqual(metadata["import_id"], imported["import_id"])
        self.assertEqual(metadata["original_sha256"], imported["source_sha256"])
        self.assertEqual(metadata["style_selection"], selection)
        status, replayed = self.call("POST", path, request)
        self.assertEqual(status, "200 OK")
        self.assertEqual(replayed["workspace"]["created_revision"]["metadata"], metadata)

    def test_workspace_selection_updates_current_pin_without_rewriting_creation_snapshot(self):
        v1 = self.custom("Keep the original direction frozen in the first screenplay.")
        initial = self.styles.select(isolated_context_id="setup-context-update",
            production_type="journal_style", style_version_id=v1["style_version_id"])
        status, created = self.call("POST", "/api/story/workspaces", {
            "idempotency_key": "3f76a483-01c9-4c12-9a9a-4fc08d539d54",
            "title": "Style update", "source_text": "A story.",
            "style_selection_snapshot_id": initial["snapshot_id"]})
        self.assertEqual(status, "201 Created")
        workspace_id = created["workspace"]["workspace_id"]
        v2 = self.custom("Use the revised direction for future screenplay drafts.")
        status, updated = self.call("POST", "/api/styles/selections", {
            "workspace_id": workspace_id, "production_type": "journal_style",
            "style_version_id": v2["style_version_id"], "directing_style_id": "cinematic"})
        self.assertEqual(status, "201 Created")
        self.assertEqual(updated["workspace_id"], workspace_id)
        status, selected = self.call("GET", f"/api/styles/selections?workspace_id={workspace_id}")
        self.assertEqual(status, "200 OK")
        self.assertEqual(selected["selections"][-1]["snapshot_id"], updated["snapshot_id"])
        status, loaded = self.call("GET", f"/api/story/workspaces/{workspace_id}")
        self.assertEqual(status, "200 OK")
        self.assertEqual(loaded["style_selection_snapshot_id"], updated["snapshot_id"])
        self.assertEqual(loaded["style_selection"], updated)
        self.assertEqual(loaded["current_revision"]["metadata"]["style_selection"], initial)

    def test_style_change_marks_old_screenplay_stale_and_removes_acceptance(self):
        v1 = self.custom("Original direction.")
        initial = self.styles.select(isolated_context_id="setup-context-stale",
            production_type="journal_style", style_version_id=v1["style_version_id"])
        status, created = self.call("POST", "/api/story/workspaces", {
            "idempotency_key": "fd590a99-2a21-44d6-8ddb-34624eb313a4",
            "title": "Stale style", "source_text": "A story.",
            "style_selection_snapshot_id": initial["snapshot_id"]})
        self.assertEqual(status, "201 Created")
        workspace_id = created["workspace"]["workspace_id"]
        source = created["workspace"]["created_revision"]
        graph_id = "graph-style-change"
        screenplay_id = "screenplay-style-change"
        with sqlite3.connect(self.ledger_path) as db:
            db.execute("PRAGMA foreign_keys=ON")
            db.execute("""INSERT INTO story_graph_snapshots
                (snapshot_id,workspace_id,source_revision_id,source_sha256,idempotency_key,request_hash,status,chunk_total,coverage_state,provider)
                VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (graph_id,workspace_id,source["revision_id"],source["source_sha256"],
                 "graph-style-change-key","request-hash","complete",1,"complete","test"))
            db.execute("""INSERT INTO story_screenplay_revisions
                (screenplay_revision_id,workspace_id,source_revision_id,graph_snapshot_id,screenplay_json,idempotency_key,style_selection_snapshot_id,accepted_at)
                VALUES(?,?,?,?,?,?,?,CURRENT_TIMESTAMP)""",
                (screenplay_id,workspace_id,source["revision_id"],graph_id,"{}",
                 "screenplay-style-change-key",initial["snapshot_id"]))
        story = StoryAuthoring(self.ledger,data_root=self.root)
        self.assertTrue(story.list_screenplay_revisions(workspace_id=workspace_id)["items"][0]["accepted"])
        revised = self.custom("Revised direction.")
        updated = self.styles.select(workspace_id=workspace_id, production_type="journal_style",
            style_version_id=revised["style_version_id"], directing_style_id="cinematic")
        item = story.list_screenplay_revisions(workspace_id=workspace_id)["items"][0]
        self.assertTrue(item["stale"])
        self.assertFalse(item["accepted"])
        status, rejection = self.call("POST",
            f"/api/story/workspaces/{workspace_id}/screenplay/revisions/{screenplay_id}/accept", {})
        self.assertEqual(status, "409 Conflict")
        self.assertIn("older production style", rejection["error"]["message"])
        self.assertFalse(story.get_screenplay_revision(workspace_id, screenplay_id)["accepted"])
        setup = ProductionSetup(self.ledger, story)
        with self.assertRaisesRegex(LedgerConflict, "current accepted screenplay"):
            setup.save(workspace_id, screenplay_id, {"mode": "assisted_manual", "automate_steps": {
                "character_images": False, "character_voice": False, "world_images": False,
                "frame_images": False, "video": False}, "video_quality": "high",
                "duration_policy": {"kind": "fixed", "seconds": 6}})
        new_screenplay_id = "screenplay-style-change-new"
        with sqlite3.connect(self.ledger_path) as db:
            db.execute("""INSERT INTO story_screenplay_revisions
                (screenplay_revision_id,workspace_id,source_revision_id,graph_snapshot_id,screenplay_json,idempotency_key,style_selection_snapshot_id)
                VALUES(?,?,?,?,?,?,?)""",
                (new_screenplay_id, workspace_id, source["revision_id"], graph_id,
                 json.dumps({"scenes": [{"scene_number": 1, "shots": [{"shot_number": 1}]}]}),
                 "screenplay-style-change-new-key", updated["snapshot_id"]))
        status, accepted = self.call("POST",
            f"/api/story/workspaces/{workspace_id}/screenplay/revisions/{new_screenplay_id}/accept", {})
        self.assertEqual(status, "200 OK")
        self.assertTrue(accepted["accepted"])

    def test_unknown_snapshot_fails_before_reserving_workspace(self):
        request = {"idempotency_key": "1f8d8525-12b5-4c5b-b975-718d70789a8a",
            "title": "Unknown style", "source_text": "A story.",
            "style_selection_snapshot_id": "f" * 32}
        status, error = self.call("POST", "/api/story/workspaces", request)
        self.assertEqual(status, "404 Not Found")
        status, workspaces = self.call("GET", "/api/story/workspaces")
        self.assertEqual(status, "200 OK")
        self.assertEqual(workspaces["total"], 0)
        status, missing_creation = self.call("GET", f"/api/story/creations/by-idempotency/{request['idempotency_key']}")
        self.assertEqual(status, "404 Not Found")


if __name__ == "__main__":
    unittest.main()
