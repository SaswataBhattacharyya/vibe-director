from __future__ import annotations

import io
import json
import tempfile
import unittest
import warnings
from pathlib import Path

from story_builder.isolated_server import create_app
from story_builder.services.production_ledger import ProductionLedger
from story_builder.services.production_styles import ProductionStyleService


class StoryStyleLinkTests(unittest.TestCase):
    def setUp(self):
        warnings.simplefilter("ignore", ResourceWarning)
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.ledger_path = self.root / "storage/production/ledger.sqlite3"
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
