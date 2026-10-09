from __future__ import annotations

import io
import json
import sqlite3
import tempfile
import unittest
import uuid
import warnings
from pathlib import Path

from story_builder.isolated_server import create_app
from story_builder.services.production_ledger import ProductionLedger
from story_builder.services.story_authoring import StoryAuthoring


class StorySelectedEditApiTests(unittest.TestCase):
    def setUp(self):
        warnings.simplefilter("ignore", ResourceWarning)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "data"
        self.ledger = ProductionLedger(self.root / "storage/production/ledger.sqlite3")
        self.story = StoryAuthoring(self.ledger, data_root=self.root)
        created = self.story.create_workspace(title="Unicode", source_text="Before 😀. The old phrase. After Ω.")
        self.workspace = created["workspace_id"]
        self.revision = created["current_revision"]["revision_id"]
        self.calls = []

        def fake_provider(*, prompt, provider, temperature):
            self.calls.append((prompt, provider, temperature))
            return {"replacement": "the new phrase", "explanation": "Clarified."}

        self.app = create_app(data_root=self.root, capability_provider=lambda: self.fail("must not probe video"),
            gpu_reader=lambda: self.fail("must not read GPU"), reasoning_json_provider=fake_provider)

    def call(self, method, path, payload=None):
        started = []
        body = json.dumps(payload or {}).encode()
        environ = {"REQUEST_METHOD": method, "PATH_INFO": path.partition("?")[0],
            "QUERY_STRING": path.partition("?")[2], "CONTENT_TYPE": "application/json",
            "CONTENT_LENGTH": str(len(body)), "wsgi.input": io.BytesIO(body)}
        result = b"".join(self.app(environ, lambda status, headers: started.append(status)))
        return started[0], json.loads(result)

    def request(self, key=None):
        source = self.story.get_revision(self.workspace, self.revision)["source_text"]
        quote = "old phrase"
        start = source.index(quote)
        return {"idempotency_key": key or str(uuid.uuid4()), "base_revision_id": self.revision,
            "start_codepoint": start, "end_codepoint": start + len(quote),
            "expected_text": quote, "instruction": "Make the wording more specific."}

    def test_unicode_selected_context_durable_key_accept_and_reload(self):
        payload = self.request()
        status, proposal = self.call("POST", f"/api/story/workspaces/{self.workspace}/edit-proposals", payload)
        self.assertEqual(status, "201 Created")
        self.assertEqual(proposal["status"], "pending")
        self.assertEqual(proposal["provider"], "codex")
        self.assertEqual(proposal["expected_text"], "old phrase")
        prompt, provider, temperature = self.calls[0]
        self.assertIn("SELECTED PASSAGE:\nold phrase", prompt)
        self.assertNotIn("Before 😀", prompt)
        self.assertEqual((provider, temperature), ("codex", 0))

        status, replay = self.call("POST", f"/api/story/workspaces/{self.workspace}/edit-proposals", payload)
        self.assertEqual(status, "201 Created")
        self.assertEqual(replay["proposal_id"], proposal["proposal_id"])
        self.assertEqual(len(self.calls), 1)
        status, recovered = self.call("GET", f"/api/story/edit-requests/by-key/{payload['idempotency_key']}")
        self.assertEqual(status, "200 OK")
        self.assertEqual(recovered["proposal"]["proposal_id"], proposal["proposal_id"])

        status, accepted = self.call("POST", f"/api/story/workspaces/{self.workspace}/edit-proposals/accept", {
            "proposal_id": proposal["proposal_id"], "expected_current_revision_id": self.revision})
        self.assertEqual(status, "201 Created")
        self.assertEqual(accepted["source_text"], "Before 😀. The the new phrase. After Ω.")
        restarted = StoryAuthoring(ProductionLedger(self.root / "storage/production/ledger.sqlite3"), data_root=self.root)
        self.assertEqual(restarted.get_workspace(self.workspace)["current_revision"]["source_text"], accepted["source_text"])

    def test_ambiguous_provider_failure_never_repeats_paid_call(self):
        calls = []
        def fails(*, prompt, provider, temperature):
            calls.append(prompt)
            raise TimeoutError("provider response lost")
        self.app = create_app(data_root=self.root, reasoning_json_provider=fails,
            capability_provider=lambda: {}, gpu_reader=lambda: {})
        payload = self.request()
        path = f"/api/story/workspaces/{self.workspace}/edit-proposals"
        status, _ = self.call("POST", path, payload)
        self.assertEqual(status, "500 Internal Server Error")
        status, recovered = self.call("GET", f"/api/story/edit-requests/by-key/{payload['idempotency_key']}")
        self.assertEqual(status, "200 OK")
        self.assertEqual(recovered["status"], "failed")
        status, _ = self.call("POST", path, payload)
        self.assertEqual(status, "409 Conflict")
        self.assertEqual(len(calls), 1)

    def test_proposal_and_recovery_pointer_commit_together(self):
        payload = self.request()
        key = payload["idempotency_key"]
        with self.ledger._connect() as db:
            db.execute("CREATE TRIGGER reject_edit_completion BEFORE UPDATE OF status ON story_ai_edit_requests WHEN NEW.status='complete' BEGIN SELECT RAISE(ABORT,'simulated completion failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.story.propose_ai_selected_edit(workspace_id=self.workspace,
                base_revision_id=payload["base_revision_id"],
                start_codepoint=payload["start_codepoint"], end_codepoint=payload["end_codepoint"],
                expected_text=payload["expected_text"], instruction=payload["instruction"],
                idempotency_key=key,
                provider_call=lambda **kwargs: {"replacement": "the new phrase", "provider": "codex", "model": "fake"})
        with self.ledger._connect() as db:
            proposal_count = db.execute("SELECT COUNT(*) FROM story_edit_proposals WHERE workspace_id=?", (self.workspace,)).fetchone()[0]
            request = db.execute("SELECT status,proposal_id FROM story_ai_edit_requests WHERE idempotency_key=?", (key,)).fetchone()
        self.assertEqual(proposal_count, 0)
        self.assertEqual((request["status"], request["proposal_id"]), ("failed", None))


if __name__ == "__main__":
    unittest.main()
