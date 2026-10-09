from __future__ import annotations

import io
import json
import tempfile
import unittest
import uuid
from pathlib import Path

from story_builder.isolated_server import create_app
from story_builder.services.production_ledger import ProductionLedger
from story_builder.services.story_authoring import StoryAuthoring


class StoryGraphTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "data"
        self.ledger = ProductionLedger(self.root / "storage/production/ledger.sqlite3")
        self.story = StoryAuthoring(self.ledger, data_root=self.root)
        source = "Mira keeps the key. " * 400
        created = self.story.create_workspace(title="Graph source", source_text=source)
        self.workspace = created["workspace_id"]
        self.revision = created["current_revision"]["revision_id"]
        self.source = source
        self.calls = []

        def fake_provider(*, prompt, provider, temperature):
            self.calls.append((prompt, provider, temperature))
            chunk = json.loads(prompt.split("CHUNK TEXT (JSON):\n", 1)[1])
            quote = "Mira keeps the key."
            start = chunk.index(quote)
            end = start + len(quote)
            return {"model": "fake-model", "records": [
                {"kind": "entity", "type": "character", "name": "Mira", "detail": "", "start": start, "end": end, "quote": quote, "status": "source_supported", "confidence": 0.99},
                {"kind": "entity", "type": "object", "name": "key", "detail": "", "start": start, "end": end, "quote": quote, "status": "source_supported", "confidence": 0.99},
                {"kind": "fact", "type": "possession", "name": "Mira keeps the key", "detail": "Mira possesses the key.", "start": start, "end": end, "quote": quote, "status": "source_supported", "confidence": 0.95},
                {"kind": "event", "type": "action", "name": "Mira keeps the key", "detail": "", "start": start, "end": end, "quote": quote, "status": "source_supported"},
                {"kind": "time", "type": "sequence", "name": "Mira keeps the key", "detail": "Ordering is unknown.", "start": start, "end": end, "quote": quote, "status": "unresolved"},
                {"kind": "relation", "type": "story_relation", "name": "Mira → key", "detail": "", "subject": "Mira", "predicate": "keeps", "object": "key", "start": start, "end": end, "quote": quote, "status": "source_supported"},
            ]}

        self.app = create_app(data_root=self.root, reasoning_json_provider=fake_provider,
            capability_provider=lambda: {}, gpu_reader=lambda: {})

    def call(self, method, path, payload=None):
        result_status = []
        raw = json.dumps(payload or {}).encode()
        environ = {"REQUEST_METHOD": method, "PATH_INFO": path.partition("?")[0],
            "QUERY_STRING": path.partition("?")[2], "CONTENT_TYPE": "application/json",
            "CONTENT_LENGTH": str(len(raw)), "wsgi.input": io.BytesIO(raw)}
        result = b"".join(self.app(environ, lambda status, headers: result_status.append(status)))
        return result_status[0], json.loads(result)

    def test_all_chunks_have_exact_durable_evidence_and_review_survives_reload(self):
        key = str(uuid.uuid4())
        path = f"/api/story/workspaces/{self.workspace}/graph"
        status, graph = self.call("POST", path, {"source_revision_id": self.revision, "idempotency_key": key})
        self.assertEqual(status, "200 OK")
        self.assertGreater(graph["chunk_total"], 1)
        self.assertEqual(graph["chunk_complete"], graph["chunk_total"])
        self.assertFalse(graph["semantic_coverage_claim"])
        self.assertEqual(graph["contradiction_state"], "not_assessed")
        self.assertEqual({call[1:] for call in self.calls}, {("codex", 0)})
        self.assertEqual(graph["source_sha256"], self.story.get_revision(self.workspace, self.revision)["source_sha256"])
        fact = next(record for record in graph["records"] if record["kind"] == "fact")
        self.assertEqual(len(fact["evidence"]), graph["chunk_total"])
        for evidence in fact["evidence"]:
            self.assertEqual(self.source[evidence["start_codepoint"]:evidence["end_codepoint"]], evidence["quote"])
            self.assertEqual(evidence["source_revision_id"], self.revision)
        call_count = len(self.calls)
        replay_status, replay = self.call("POST", path, {"source_revision_id": self.revision, "idempotency_key": key})
        self.assertEqual(replay_status, "200 OK")
        self.assertEqual(replay["snapshot_id"], graph["snapshot_id"])
        self.assertEqual(len(self.calls), call_count)
        update_status, saved = self.call("PATCH", f"{path}/records/{fact['record_id']}", {
            "name": "Mira holds the key", "detail": "Writer reviewed this claim.", "status": "user_authored"})
        self.assertEqual(update_status, "200 OK")
        self.assertEqual(saved["status"], "user_authored")
        restarted = StoryAuthoring(ProductionLedger(self.root / "storage/production/ledger.sqlite3"), data_root=self.root)
        loaded = restarted.get_story_graph(workspace_id=self.workspace, snapshot_id=graph["snapshot_id"])
        reviewed = next(record for record in loaded["records"] if record["record_id"] == fact["record_id"])
        self.assertEqual(reviewed["name"], "Mira holds the key")
        self.assertTrue(reviewed["user_modified"])
        self.assertEqual(reviewed["evidence"], fact["evidence"])

    def test_explicit_retry_retries_only_failed_chunks(self):
        calls = []
        def provider(*, prompt, provider, temperature):
            calls.append(prompt)
            if len(calls) == 1:
                return {"records": [{"kind": "fact", "type": "claim", "name": "unsupported span",
                    "detail": "", "start": 0, "end": 4, "quote": "WRONG", "status": "source_supported"}]}
            chunk = json.loads(prompt.split("CHUNK TEXT (JSON):\n", 1)[1])
            quote = "Mira keeps the key."
            start = chunk.index(quote)
            return {"records": [{"kind": "fact", "type": "claim", "name": "Mira keeps the key",
                "detail": "", "start": start, "end": start + len(quote), "quote": quote,
                "status": "source_supported"}]}
        app = create_app(data_root=self.root, reasoning_json_provider=provider,
            capability_provider=lambda: {}, gpu_reader=lambda: {})
        key = str(uuid.uuid4())
        path = f"/api/story/workspaces/{self.workspace}/graph"
        payload = {"source_revision_id": self.revision, "idempotency_key": key}
        first_status, graph = self.call_with_app(app, "POST", path, payload)
        self.assertEqual(first_status, "202 Accepted")
        self.assertEqual(graph["status"], "partial")
        self.assertEqual(graph["chunk_complete"], graph["chunk_total"] - 1)
        count = len(calls)
        second_status, replay = self.call_with_app(app, "POST", path, payload)
        self.assertEqual(second_status, "200 OK")
        self.assertEqual(replay["snapshot_id"], graph["snapshot_id"])
        self.assertEqual(replay["chunk_complete"], replay["chunk_total"])
        self.assertEqual(len(calls), count + 1)

    def test_duplicate_post_does_not_steal_live_chunk_claim(self):
        key = str(uuid.uuid4())
        path = f"/api/story/workspaces/{self.workspace}/graph"
        payload = {"source_revision_id": self.revision, "idempotency_key": key}
        nested = []
        entered = False

        def provider(*, prompt, provider, temperature):
            nonlocal entered
            if not entered:
                entered = True
                nested.append(self.call("POST", path, payload))
            chunk = json.loads(prompt.split("CHUNK TEXT (JSON):\n", 1)[1])
            quote = "Mira keeps the key."
            start = chunk.index(quote)
            return {"records": [{"kind": "fact", "type": "claim", "name": "Mira keeps the key",
                "detail": "", "start": start, "end": start + len(quote), "quote": quote,
                "status": "source_supported"}]}

        app = create_app(data_root=self.root, reasoning_json_provider=provider,
            capability_provider=lambda: {}, gpu_reader=lambda: {})
        outer = self.call_with_app(app, "POST", path, payload)
        self.assertEqual(nested[0][0], "202 Accepted")
        self.assertEqual(nested[0][1]["status"], "processing")
        self.assertEqual(outer[0], "200 OK")
        self.assertEqual(outer[1]["status"], "complete")

    def test_uncertain_provider_failure_is_not_retried_with_same_key(self):
        calls = []
        def unavailable(*, prompt, provider, temperature):
            calls.append(prompt)
            raise RuntimeError("provider response status is unknown")
        app = create_app(data_root=self.root, reasoning_json_provider=unavailable,
            capability_provider=lambda: {}, gpu_reader=lambda: {})
        path = f"/api/story/workspaces/{self.workspace}/graph"
        payload = {"source_revision_id": self.revision, "idempotency_key": str(uuid.uuid4())}
        first = self.call_with_app(app, "POST", path, payload)
        self.assertEqual(first[0], "202 Accepted")
        self.assertTrue(all(chunk["state"] == "uncertain" for chunk in first[1]["chunks"]))
        self.call_with_app(app, "POST", path, payload)
        self.assertEqual(len(calls), first[1]["chunk_total"])

    @staticmethod
    def call_with_app(app, method, path, payload=None):
        result_status = []
        raw = json.dumps(payload or {}).encode()
        environ = {"REQUEST_METHOD": method, "PATH_INFO": path.partition("?")[0],
            "QUERY_STRING": path.partition("?")[2], "CONTENT_TYPE": "application/json",
            "CONTENT_LENGTH": str(len(raw)), "wsgi.input": io.BytesIO(raw)}
        result = b"".join(app(environ, lambda status, headers: result_status.append(status)))
        return result_status[0], json.loads(result)


if __name__ == "__main__":
    unittest.main()
