from __future__ import annotations

import io
import json
import tempfile
import unittest
import warnings
from pathlib import Path

from story_builder.isolated_server import create_app


class ProductionStyleApiTests(unittest.TestCase):
    def setUp(self):
        warnings.simplefilter("ignore", ResourceWarning)
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.app = create_app(data_root=self.root,
            capability_provider=lambda: self.fail("style route probed generation capability"),
            gpu_reader=lambda: self.fail("style route read GPU"))

    def call(self, method, path, payload=None):
        body = b"" if payload is None else json.dumps(payload).encode("utf-8")
        started = []
        request_path, _, query = path.partition("?")
        environ = {"REQUEST_METHOD": method, "PATH_INFO": request_path, "QUERY_STRING": query,
            "CONTENT_TYPE": "application/json" if body else "", "CONTENT_LENGTH": str(len(body)),
            "wsgi.input": io.BytesIO(body)}
        response = b"".join(self.app(environ, lambda status, headers: started.append(status)))
        return started[0], json.loads(response) if response else None

    @staticmethod
    def custom_payload(production_type="field_journal", purpose="Document field observations clearly."):
        return {"production_type": production_type,
            "narrative_guidance": {
                "story": "Protect author intent and causal continuity.",
                "scene_direction": "Use clear blocking and motivated camera choices.",
                "image": "Use a restrained palette and readable composition.",
                "audio": "Keep dialogue clear and music subordinate.",
                "video": "Use purposeful camera movement and coherent pacing.",
                "review": "Check continuity, clarity, and factual support.",
            },
            "director_profile": {"display_name": "Field Journal", "purpose": purpose,
                "behavior": ["Keep observations distinct from interpretation."],
                "review_priorities": ["source fidelity", "readability"]}}

    def test_catalog_read_returns_six_types_without_generation_probe(self):
        status, catalog = self.call("GET", "/api/styles/catalog")
        self.assertEqual(status, "200 OK")
        self.assertEqual(len(catalog["production_types"]), 6)
        self.assertTrue(all(item["narrative_hash"] and item["director_profile_hash"]
                            for item in catalog["production_types"]))

    def test_custom_type_validation_is_422(self):
        status, error = self.call("POST", "/api/styles/types", self.custom_payload())
        self.assertEqual(status, "201 Created")
        bad = self.custom_payload("incomplete_type")
        bad["narrative_guidance"].pop("review")
        status, error = self.call("POST", "/api/styles/types", bad)
        self.assertEqual(status, "422 Unprocessable Entity")
        self.assertEqual(error["error"]["code"], "invalid_style_request")

    def test_publish_select_reload_and_append_only_history(self):
        status, v1 = self.call("POST", "/api/styles/types", self.custom_payload())
        self.assertEqual(status, "201 Created")
        _, workspace = self.call("POST", "/api/story/workspaces", {"title": "Style test", "source_text": "A short story."})
        body = {"workspace_id": workspace["workspace_id"], "production_type": "field_journal",
                "style_version_id": v1["style_version_id"]}
        status, first = self.call("POST", "/api/styles/selections", body)
        self.assertEqual(status, "201 Created")
        self.assertEqual(first["narrative_hash"], v1["narrative_hash"])
        self.assertEqual(first["director_profile_hash"], v1["director_profile_hash"])
        status, loaded = self.call("GET", f"/api/styles/selections/{first['snapshot_id']}")
        self.assertEqual(status, "200 OK")
        self.assertEqual(loaded, first)
        status, listed = self.call("GET", f"/api/styles/selections?workspace_id={workspace['workspace_id']}")
        self.assertEqual(status, "200 OK")
        self.assertEqual(listed["selections"], [first])

        status, v2 = self.call("POST", "/api/styles/types", self.custom_payload(purpose="Document field observations for later review."))
        self.assertEqual(status, "201 Created")
        self.assertEqual(v2["style_version"], 2)
        body["style_version_id"] = v2["style_version_id"]
        status, second = self.call("POST", "/api/styles/selections", body)
        self.assertEqual(status, "201 Created")
        _, reloaded_first = self.call("GET", f"/api/styles/selections/{first['snapshot_id']}")
        _, history = self.call("GET", f"/api/styles/selections?workspace_id={workspace['workspace_id']}")
        self.assertEqual(reloaded_first, first)
        self.assertEqual([item["snapshot_id"] for item in history["selections"]],
                         [first["snapshot_id"], second["snapshot_id"]])

    def test_isolated_selection_and_unknown_workspace(self):
        status, selection = self.call("POST", "/api/styles/selections", {
            "isolated_context_id": "draft-session-1", "production_type": "story_film"})
        self.assertEqual(status, "201 Created")
        status, listed = self.call("GET", "/api/styles/selections?isolated_context_id=draft-session-1")
        self.assertEqual(status, "200 OK")
        self.assertEqual(listed["selections"], [selection])
        status, error = self.call("POST", "/api/styles/selections", {
            "workspace_id": "story-000000000000", "production_type": "story_film"})
        self.assertEqual(status, "404 Not Found")
        status, error = self.call("GET", f"/api/styles/selections/{'f' * 32}")
        self.assertEqual(status, "404 Not Found")

    def test_invalid_selection_shapes_return_422(self):
        invalid_payloads = [
            {"workspace_id": [], "production_type": "story_film"},
            {"isolated_context_id": [], "production_type": "story_film"},
            {"isolated_context_id": "draft-1", "production_type": []},
            {"isolated_context_id": "draft-1", "production_type": "story_film", "style_version_id": []},
            {"workspace_id": "", "isolated_context_id": "draft-1", "production_type": "story_film"},
        ]
        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                status, body = self.call("POST", "/api/styles/selections", payload)
                self.assertEqual(status, "422 Unprocessable Entity")
                self.assertEqual(body["error"]["code"], "invalid_style_request")


if __name__ == "__main__":
    unittest.main()
