from __future__ import annotations

import hashlib
import io
import json
import tempfile
import threading
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from story_builder.isolated_server import create_app
from story_builder.services.production_ledger import LedgerConflict, ProductionLedger
from story_builder.services.production_styles import ProductionStyleService
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
            if "GRAPH RECORDS (JSON):\n" in prompt:
                records = json.loads(prompt.split("GRAPH RECORDS (JSON):\n", 1)[1])
                cited = [r["record_id"] for r in records if r["kind"] in {"event", "fact"}]
                return {"model": "fake-model", "scenes": ([{"slugline": "INT. ROOM - DAY", "summary": "Mira keeps the key.", "shots": [{"action": "Mira keeps the key.", "dialogue": "", "camera": "", "lighting": "", "mood": "", "sfx": "", "music": "", "evidence_record_ids": cited}]}] if cited else [])}
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

    def test_pinned_production_style_guides_screenplay_and_is_preserved_in_lineage(self):
        styles = ProductionStyleService(self.ledger)
        selection = styles.select(isolated_context_id="pre-story-style", production_type="informative")
        created, _ = self.story.create_or_resume_workspace(
            idempotency_key=str(uuid.uuid4()), action="create", title="Styled story",
            source_text="Mira keeps the key.", style_selection_snapshot_id=selection["snapshot_id"],
            style_selection_resolver=styles.get_selection)
        workspace_id = created["workspace"]["workspace_id"]
        revision_id = created["workspace"]["created_revision"]["revision_id"]

        def graph_provider(*, prompt):
            chunk = json.loads(prompt.split("CHUNK TEXT (JSON):\n", 1)[1])
            quote = "Mira keeps the key."
            start = chunk.index(quote)
            return {"records": [{"kind": "event", "type": "action", "name": quote,
                "detail": "Mira retains the key.", "start": start, "end": start + len(quote),
                "quote": quote, "status": "source_supported"}]}

        graph = self.story.build_story_graph(workspace_id=workspace_id, source_revision_id=revision_id,
            idempotency_key=str(uuid.uuid4()), provider_call=graph_provider)
        prompts = []

        def screenplay_provider(*, prompt):
            prompts.append(prompt)
            records = json.loads(prompt.split("GRAPH RECORDS (JSON):\n", 1)[1])
            record_id = records[0]["record_id"]
            return {"scenes": [{"slugline": "INT. ROOM - DAY", "summary": "Mira keeps the key.",
                "shots": [{"action": "Mira keeps the key.", "dialogue": "", "camera": "", "lighting": "",
                    "mood": "", "sfx": "", "music": "", "evidence_record_ids": [record_id]}]}]}

        draft = self.story.draft_screenplay(workspace_id=workspace_id, source_revision_id=revision_id,
            graph_snapshot_id=graph["snapshot_id"], idempotency_key=str(uuid.uuid4()),
            provider_call=screenplay_provider)
        self.assertEqual(draft["style_selection_snapshot_id"], selection["snapshot_id"])
        self.assertIn('"production_type": "informative"', prompts[0])
        self.assertIn("explanatory framing", prompts[0])
        self.assertIn("Define terms, mark uncertainty", prompts[0])
        edited = json.loads(json.dumps(draft["screenplay"]))
        edited["scenes"][0]["shots"][0]["camera"] = "A steady close shot."
        child = self.story.edit_screenplay(workspace_id=workspace_id,
            screenplay_revision_id=draft["screenplay_revision_id"], idempotency_key=str(uuid.uuid4()),
            screenplay=edited)
        self.assertEqual(child["style_selection_snapshot_id"], selection["snapshot_id"])

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

    def test_screenplay_draft_edit_and_reload_keep_source_and_graph_lineage(self):
        graph_path = f"/api/story/workspaces/{self.workspace}/graph"
        _, graph = self.call("POST", graph_path, {"source_revision_id": self.revision, "idempotency_key": str(uuid.uuid4())})
        screenplay_path = f"/api/story/workspaces/{self.workspace}/screenplay"
        draft_key = str(uuid.uuid4())
        status, draft = self.call("POST", screenplay_path, {"source_revision_id": self.revision,
            "graph_snapshot_id": graph["snapshot_id"], "idempotency_key": draft_key})
        self.assertEqual(status, "201 Created")
        self.assertEqual(draft["source_revision_id"], self.revision)
        self.assertEqual(draft["graph_snapshot_id"], graph["snapshot_id"])
        self.assertIsNone(draft["style_selection_snapshot_id"])
        revision = self.story.get_revision(self.workspace, self.revision)
        legacy_request = {"workspace_id": self.workspace, "source_revision_id": self.revision,
            "source_sha256": revision["source_sha256"], "graph_snapshot_id": graph["snapshot_id"],
            "chunk_ids": [chunk["chunk_id"] for chunk in revision["source_chunks"]]}
        expected_hash = hashlib.sha256(self.story._canonical_json(legacy_request).encode()).hexdigest()
        with self.ledger._connect() as db:
            stored_hash = db.execute("SELECT request_hash FROM story_screenplay_tasks WHERE idempotency_key=?", (draft_key,)).fetchone()["request_hash"]
        self.assertEqual(stored_hash, expected_hash)
        screenplay_prompt = next(prompt for prompt, _provider, _temperature in self.calls if "GRAPH RECORDS (JSON):\n" in prompt)
        self.assertNotIn("Pinned production guidance", screenplay_prompt)
        self.assertGreaterEqual(len(draft["screenplay"]["scenes"]), 1)
        altered = json.loads(json.dumps(draft["screenplay"]))
        altered["scenes"][0]["shots"][0]["action"] = "Payload collision."
        with self.assertRaises(LedgerConflict):
            self.story._save_screenplay(workspace_id=self.workspace, source_revision_id=self.revision,
                graph_snapshot_id=graph["snapshot_id"], screenplay=altered, idempotency_key=draft_key)
        first_shot = draft["screenplay"]["scenes"][0]["shots"][0]
        self.assertEqual(first_shot["action"], "Mira keeps the key.")
        self.assertEqual(first_shot["evidence"][0]["source_revision_id"], self.revision)
        self.assertEqual(draft["task_status"], "complete")
        self.assertEqual(draft["chunk_complete"], draft["chunk_total"])
        self.assertEqual(draft["coverage_state"], "all_source_chunks_planned_semantic_coverage_unverified")
        edited = json.loads(json.dumps(draft["screenplay"]))
        edited["scenes"][0]["shots"][0]["action"] = ""
        edited["scenes"][0]["shots"][0]["dialogue"] = "Mira: I have it."
        edit_key = str(uuid.uuid4())
        edit_status, saved = self.call("PATCH", f"{screenplay_path}/revisions/{draft['screenplay_revision_id']}",
            {"idempotency_key": edit_key, "screenplay": edited})
        self.assertEqual(edit_status, "201 Created")
        self.assertEqual(saved["parent_screenplay_revision_id"], draft["screenplay_revision_id"])
        self.assertEqual(saved["screenplay"]["scenes"][0]["shots"][0]["action"], "")
        self.assertEqual(saved["screenplay"]["scenes"][0]["shots"][0]["dialogue"], "Mira: I have it.")
        replay_status, replayed_edit = self.call("PATCH", f"{screenplay_path}/revisions/{draft['screenplay_revision_id']}",
            {"idempotency_key": edit_key, "screenplay": edited})
        self.assertEqual(replay_status, "201 Created")
        self.assertEqual(replayed_edit["screenplay_revision_id"], saved["screenplay_revision_id"])
        _, loaded = self.call("GET", f"{screenplay_path}?revision_id={self.revision}")
        self.assertEqual(loaded["screenplay_revision_id"], saved["screenplay_revision_id"])
        self.assertEqual(loaded["screenplay"]["scenes"][0]["shots"][0]["evidence"], first_shot["evidence"])
        accept_path = f"{screenplay_path}/revisions/{saved['screenplay_revision_id']}/accept"
        accept_status, accepted = self.call("POST", accept_path, {})
        self.assertEqual(accept_status, "200 OK")
        self.assertTrue(accepted["accepted"])
        self.assertTrue(accepted["accepted_at"])
        _, replayed_acceptance = self.call("POST", accept_path, {})
        self.assertTrue(replayed_acceptance["accepted"])
        post_accept_edit = json.loads(json.dumps(saved["screenplay"]))
        post_accept_edit["scenes"][0]["shots"][0]["dialogue"] = "Mira: I found it."
        _, child = self.call("PATCH", f"{screenplay_path}/revisions/{saved['screenplay_revision_id']}",
            {"idempotency_key": str(uuid.uuid4()), "screenplay": post_accept_edit})
        self.assertFalse(child["accepted"])
        _, after_edit_history = self.call("GET", f"{screenplay_path}/revisions?limit=10&offset=0")
        self.assertFalse(next(item for item in after_edit_history["items"] if item["screenplay_revision_id"] == saved["screenplay_revision_id"])["accepted"])
        self.assertFalse(next(item for item in after_edit_history["items"] if item["screenplay_revision_id"] == child["screenplay_revision_id"])["accepted"])
        stale = json.loads(json.dumps(draft["screenplay"]))
        stale["scenes"][0]["shots"][0]["action"] = "A stale sibling edit."
        stale_status, stale_result = self.call("PATCH", f"{screenplay_path}/revisions/{draft['screenplay_revision_id']}",
            {"idempotency_key": str(uuid.uuid4()), "screenplay": stale})
        self.assertEqual(stale_status, "409 Conflict")
        self.assertIn("stale", stale_result["error"]["message"].lower())
        self.story.write_revision(workspace_id=self.workspace, source_text="Mira keeps the key, then hides it.",
            expected_current_revision_id=self.revision)
        _, history = self.call("GET", f"{screenplay_path}/revisions?limit=10&offset=0")
        self.assertGreaterEqual(history["total"], 2)
        old = next(item for item in history["items"] if item["screenplay_revision_id"] == saved["screenplay_revision_id"])
        self.assertTrue(old["stale"])
        self.assertFalse(old["accepted"])
        stale_accept_status, stale_accept = self.call("POST", f"{screenplay_path}/revisions/{child['screenplay_revision_id']}/accept", {})
        self.assertEqual(stale_accept_status, "409 Conflict")
        self.assertIn("older story revision", stale_accept["error"]["message"])
        _, historical = self.call("GET", f"{screenplay_path}/revisions/{saved['screenplay_revision_id']}")
        self.assertEqual(historical["source_revision_id"], self.revision)
        stale_edit = json.loads(json.dumps(historical["screenplay"]))
        stale_edit["scenes"][0]["shots"][0]["action"] = "Do not save against old canon."
        status, result = self.call("PATCH", f"{screenplay_path}/revisions/{saved['screenplay_revision_id']}",
            {"idempotency_key": str(uuid.uuid4()), "screenplay": stale_edit})
        self.assertEqual(status, "409 Conflict")
        self.assertIn("older story revision", result["error"]["message"])

    def test_screenplay_invalid_evidence_rejected_then_same_key_recovers_failed_chunk_only(self):
        _, graph = self.call("POST", f"/api/story/workspaces/{self.workspace}/graph", {
            "source_revision_id": self.revision, "idempotency_key": str(uuid.uuid4())})
        path = f"/api/story/workspaces/{self.workspace}/screenplay"
        key = str(uuid.uuid4()); calls = []
        def provider(*, prompt, provider, temperature):
            calls.append(prompt)
            records = json.loads(prompt.split("GRAPH RECORDS (JSON):\n", 1)[1])
            cited = [r["record_id"] for r in records if r["kind"] in {"event", "fact"}]
            if len(calls) == 2:
                self.assertIn("PREVIOUS CHUNK CONTINUITY (JSON)", prompt)
                return {"scenes": [{"slugline": "INT. ROOM", "summary": "Mira", "shots": [{"action": "Mira", "evidence_record_ids": ["foreign-record"]}]}]}
            return {"scenes": ([{"slugline": "INT. ROOM", "summary": "Mira", "shots": [{"action": "Mira keeps the key.", "dialogue": "", "camera": "", "lighting": "", "mood": "", "sfx": "", "music": "", "evidence_record_ids": cited}]}] if cited else [])}
        app = create_app(data_root=self.root, reasoning_json_provider=provider, capability_provider=lambda: {}, gpu_reader=lambda: {})
        payload = {"source_revision_id": self.revision, "graph_snapshot_id": graph["snapshot_id"], "idempotency_key": key}
        status, partial = self.call_with_app(app, "POST", path, payload)
        self.assertEqual(status, "202 Accepted")
        self.assertEqual(partial["task_status"], "partial")
        self.assertEqual(sum(c["state"] == "complete" for c in partial["chunks"]), 1)
        before = len(calls)
        restarted_app = create_app(data_root=self.root, reasoning_json_provider=provider,
            capability_provider=lambda: {}, gpu_reader=lambda: {})
        status, final = self.call_with_app(restarted_app, "POST", path, payload)
        self.assertEqual(status, "201 Created")
        self.assertEqual(final["task_status"], "complete")
        self.assertEqual(len(calls), before + partial["chunk_total"] - 1)
        replay_app = create_app(data_root=self.root, reasoning_json_provider=provider,
            capability_provider=lambda: {}, gpu_reader=lambda: {})
        status, replay = self.call_with_app(replay_app, "POST", path, payload)
        self.assertEqual(status, "201 Created")
        self.assertEqual(replay["screenplay_revision_id"], final["screenplay_revision_id"])
        self.assertEqual(len(calls), before + partial["chunk_total"] - 1)

    def test_screenplay_uncertain_chunk_blocks_later_chunks_on_replay(self):
        _, graph = self.call("POST", f"/api/story/workspaces/{self.workspace}/graph", {
            "source_revision_id": self.revision, "idempotency_key": str(uuid.uuid4())})
        path = f"/api/story/workspaces/{self.workspace}/screenplay"
        calls = []
        def unavailable(*, prompt, provider, temperature):
            calls.append(prompt)
            raise RuntimeError("provider response status is unknown")
        app = create_app(data_root=self.root, reasoning_json_provider=unavailable,
            capability_provider=lambda: {}, gpu_reader=lambda: {})
        payload = {"source_revision_id": self.revision, "graph_snapshot_id": graph["snapshot_id"],
            "idempotency_key": str(uuid.uuid4())}
        status, partial = self.call_with_app(app, "POST", path, payload)
        self.assertEqual(status, "202 Accepted")
        self.assertEqual(partial["chunks"][0]["state"], "uncertain")
        self.assertTrue(all(chunk["state"] == "pending" for chunk in partial["chunks"][1:]))
        self.assertEqual(len(calls), 1)
        replay_status, replay = self.call_with_app(app, "POST", path, payload)
        self.assertEqual(replay_status, "202 Accepted")
        self.assertEqual(replay["chunks"][0]["state"], "uncertain")
        self.assertTrue(all(chunk["state"] == "pending" for chunk in replay["chunks"][1:]))
        self.assertEqual(len(calls), 1)

    def test_concurrent_screenplay_siblings_allow_only_one_child(self):
        _, graph = self.call("POST", f"/api/story/workspaces/{self.workspace}/graph", {
            "source_revision_id": self.revision, "idempotency_key": str(uuid.uuid4())})
        path = f"/api/story/workspaces/{self.workspace}/screenplay"
        _, draft = self.call("POST", path, {"source_revision_id": self.revision,
            "graph_snapshot_id": graph["snapshot_id"], "idempotency_key": str(uuid.uuid4())})
        parent_id = draft["screenplay_revision_id"]
        original_save = self.story._save_screenplay
        barrier = threading.Barrier(2)
        def synchronized_save(**kwargs):
            barrier.wait(timeout=5)
            return original_save(**kwargs)
        self.story._save_screenplay = synchronized_save
        def save(action):
            screenplay = json.loads(json.dumps(draft["screenplay"]))
            screenplay["scenes"][0]["shots"][0]["action"] = action
            return self.call("PATCH", f"{path}/revisions/{parent_id}", {
                "idempotency_key": str(uuid.uuid4()), "screenplay": screenplay})
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(save, ("First sibling.", "Second sibling.")))
        self.story._save_screenplay = original_save
        self.assertEqual(sorted(status for status, _ in results), ["201 Created", "409 Conflict"])
        _, latest = self.call("GET", f"{path}?revision_id={self.revision}")
        self.assertEqual(latest["parent_screenplay_revision_id"], parent_id)

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
