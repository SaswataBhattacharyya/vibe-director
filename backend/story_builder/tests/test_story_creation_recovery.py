from __future__ import annotations

import io
import json
import tempfile
import unittest
import warnings
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from story_builder.isolated_server import create_app
from story_builder.services.production_ledger import LedgerConflict, LedgerNotFound, ProductionLedger
from story_builder.services.story_authoring import StoryAuthoring


KEY = "f2a3e2e8-4859-469f-84cc-41e7d2c42b90"
IMPORT_ID = "import-" + "a" * 32


class StoryCreationRecoveryTests(unittest.TestCase):
    def setUp(self):
        warnings.simplefilter("ignore", ResourceWarning)
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "data"
        self.db_path = self.root / "storage/production/ledger.sqlite3"
        self.data_root = self.root
        self.authoring = StoryAuthoring(ProductionLedger(self.db_path), data_root=self.data_root)

    def create(self, key=KEY, *, title="One", source="Exact story Ω.", action="create"):
        return self.authoring.create_or_resume_workspace(idempotency_key=key, action=action,
            title=title, source_text=source)

    def test_lost_response_restart_lookup_and_frozen_initial_revision(self):
        first, created = self.create()
        self.assertTrue(created)
        self.assertEqual(first["status"], "ready")
        workspace_id = first["workspace"]["workspace_id"]
        initial_id = first["workspace"]["created_revision"]["revision_id"]

        restarted = StoryAuthoring(ProductionLedger(self.db_path), data_root=self.data_root)
        replay, created_again = restarted.create_or_resume_workspace(idempotency_key=KEY,
            action="create", title="One", source_text="Exact story Ω.")
        self.assertFalse(created_again)
        self.assertEqual(replay["workspace"]["workspace_id"], workspace_id)
        self.assertEqual(replay["workspace"]["created_revision"]["revision_id"], initial_id)
        with restarted.ledger._connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM story_workspaces").fetchone()[0], 1)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM story_creation_requests").fetchone()[0], 1)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM story_revision_index").fetchone()[0], 1)

        created_revision = first["workspace"]["created_revision"]
        later = restarted.write_revision(workspace_id=workspace_id, source_text="Later edit.",
            expected_current_revision_id=created_revision["revision_id"])
        lookup = restarted.get_creation_by_key(KEY)
        self.assertEqual(lookup["workspace"]["created_revision"]["revision_id"], initial_id)
        self.assertEqual(lookup["workspace"]["current_revision_id"], later["revision_id"])
        with self.assertRaises(LedgerConflict):
            restarted.create_or_resume_workspace(idempotency_key=KEY, action="create",
                title="One", source_text="Changed story.")
        with self.assertRaises(LedgerConflict):
            restarted.create_or_resume_workspace(idempotency_key=KEY, action="apply",
                title="One", source_text="Exact story Ω.", import_id=IMPORT_ID)

    def test_apply_freezes_import_lineage_and_replay_does_not_reresolve_it(self):
        evidence = {"kind": "source_import", "import_id": IMPORT_ID,
                    "original_sha256": "a" * 64, "extracted_text_sha256": "b" * 64}
        calls = []
        first, created = self.authoring.create_or_resume_workspace(idempotency_key=KEY,
            action="apply", title="From import", source_text="Reviewed text.", import_id=IMPORT_ID,
            source_metadata_factory=lambda: calls.append("resolved") or evidence)
        self.assertTrue(created)
        self.assertEqual(calls, ["resolved"])
        replay, created_again = self.authoring.create_or_resume_workspace(idempotency_key=KEY,
            action="apply", title="From import", source_text="Reviewed text.", import_id=IMPORT_ID,
            source_metadata_factory=lambda: self.fail("replay re-resolved source metadata"))
        self.assertFalse(created_again)
        self.assertEqual(replay["request_hash"], first["request_hash"])
        self.assertEqual(replay["workspace"]["created_revision"]["metadata"], evidence)

    def test_concurrent_identical_creates_share_one_workspace_and_initial_revision(self):
        def call():
            return self.authoring.create_or_resume_workspace(idempotency_key=KEY,
                action="create", title="Concurrent", source_text="One exact source.")[0]

        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _index: call(), range(8)))
        workspace_ids = {result["workspace"]["workspace_id"] for result in results}
        revision_ids = {result["workspace"]["created_revision"]["revision_id"] for result in results}
        self.assertEqual(len(workspace_ids), 1)
        self.assertEqual(len(revision_ids), 1)
        with self.authoring.ledger._connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM story_workspaces").fetchone()[0], 1)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM story_revision_index").fetchone()[0], 1)

    def test_interrupted_initialization_is_read_only_visible_then_explicitly_resumed(self):
        with patch.object(StoryAuthoring, "write_revision", side_effect=RuntimeError("simulated interruption")):
            with self.assertRaises(RuntimeError):
                self.create()
        pending = self.authoring.get_creation_by_key(KEY)
        self.assertEqual(pending["status"], "initializing")
        self.assertIsNone(pending["workspace"]["current_revision_id"])
        with self.assertRaises(LedgerNotFound):
            self.authoring.get_creation_by_key("e7a4cb2e-8f1f-4cdf-9a6f-94ce4138d4dd")
        resumed, created = self.create()
        self.assertFalse(created)
        self.assertEqual(resumed["status"], "ready")
        self.assertEqual(resumed["workspace"]["workspace_id"], pending["workspace"]["workspace_id"])

    def test_http_idempotency_lookup_and_explicit_retry_statuses(self):
        app = create_app(data_root=self.root,
            graph_path=Path(__file__).resolve().parents[1] / "workflows/api/minimax_h3_t2v_api.json",
            capability_provider=lambda: self.fail("story creation probed video readiness"),
            gpu_reader=lambda: self.fail("story creation read GPU"))

        def call(method, path, payload=None):
            body = b"" if payload is None else json.dumps(payload).encode()
            started = []
            environ = {"REQUEST_METHOD": method, "PATH_INFO": path, "QUERY_STRING": "",
                "CONTENT_TYPE": "application/json", "CONTENT_LENGTH": str(len(body)), "wsgi.input": io.BytesIO(body)}
            response = b"".join(app(environ, lambda status, headers: started.append(status)))
            return started[0], json.loads(response)

        body = {"idempotency_key": KEY, "title": "HTTP", "source_text": "Once."}
        status, first = call("POST", "/api/story/workspaces", body)
        self.assertEqual(status, "201 Created")
        status, replay = call("POST", "/api/story/workspaces", body)
        self.assertEqual(status, "200 OK")
        status, found = call("GET", f"/api/story/creations/by-idempotency/{KEY}")
        self.assertEqual(status, "200 OK")
        self.assertEqual(first["workspace"]["workspace_id"], replay["workspace"]["workspace_id"])
        self.assertEqual(first["workspace"]["workspace_id"], found["workspace"]["workspace_id"])
        status, absent = call("GET", "/api/story/creations/by-idempotency/e7a4cb2e-8f1f-4cdf-9a6f-94ce4138d4dd")
        self.assertEqual(status, "404 Not Found")

        upload = b"Import input."
        started = []
        environ = {"REQUEST_METHOD": "POST", "PATH_INFO": "/api/story/imports", "QUERY_STRING": "filename=source.txt",
            "CONTENT_TYPE": "application/octet-stream", "CONTENT_LENGTH": str(len(upload)), "wsgi.input": io.BytesIO(upload)}
        preview = json.loads(b"".join(app(environ, lambda status, headers: started.append(status))))
        self.assertEqual(started[0], "201 Created")
        apply_key = "8e2c41a1-8ae3-494e-b0d3-eafab25a6f81"
        apply_path = f"/api/story/imports/{preview['import_id']}/apply"
        apply_body = {"idempotency_key": apply_key, "title": "Applied", "source_text": preview["text"]}
        status, applied = call("POST", apply_path, apply_body)
        self.assertEqual(status, "201 Created")
        status, applied_replay = call("POST", apply_path, apply_body)
        self.assertEqual(status, "200 OK")
        self.assertEqual(applied["workspace"]["workspace_id"], applied_replay["workspace"]["workspace_id"])
        status, mismatch = call("POST", apply_path, {**apply_body, "source_text": "changed"})
        self.assertEqual(status, "409 Conflict")


if __name__ == "__main__":
    unittest.main()
