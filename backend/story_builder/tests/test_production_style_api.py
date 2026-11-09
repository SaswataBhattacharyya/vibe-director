from __future__ import annotations

import io
import hashlib
import json
import tempfile
import unittest
import warnings
from pathlib import Path
from unittest.mock import patch

from story_builder.isolated_server import create_app
from story_builder.services.media_library import register_upload, asset_path


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

    def call_raw(self, method, path, filename, body):
        started = []
        request_path, _, query = path.partition("?")
        environ = {"REQUEST_METHOD": method, "PATH_INFO": request_path, "QUERY_STRING": query,
            "CONTENT_TYPE": "application/octet-stream", "CONTENT_LENGTH": str(len(body)),
            "HTTP_X_FILE_NAME": filename, "wsgi.input": io.BytesIO(body)}
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

    def test_style_source_upload_is_context_scoped_and_returns_cited_evidence(self):
        status, source = self.call_raw("POST", "/api/styles/sources?isolated_context_id=setup-test",
            "rules.txt", b"Use quiet dialogue.\n\nPrefer motivated camera movement.\n")
        self.assertEqual(status, "201 Created")
        self.assertEqual(source["evidence_blocks"][0]["locator"], "line:1-1")
        status, listed = self.call("GET", "/api/styles/sources?isolated_context_id=setup-test")
        self.assertEqual(status, "200 OK")
        self.assertEqual(listed["sources"][0]["source_id"], source["source_id"])
        status, loaded = self.call("GET", f"/api/styles/sources/{source['source_id']}?isolated_context_id=setup-test")
        self.assertEqual(status, "200 OK")
        self.assertEqual(loaded["evidence_blocks"], source["evidence_blocks"])
        status, other = self.call("GET", "/api/styles/sources?isolated_context_id=another-setup")
        self.assertEqual(status, "200 OK")
        self.assertEqual(other["sources"], [])

    def test_style_source_rejects_bad_format_and_context_traversal(self):
        status, error = self.call_raw("POST", "/api/styles/sources?isolated_context_id=setup-test",
            "clip.mp4", b"video")
        self.assertEqual(status, "422 Unprocessable Entity")
        self.assertEqual(error["error"]["code"], "unsupported_style_source")
        status, error = self.call("GET", "/api/styles/sources?isolated_context_id=../outside")
        self.assertEqual(status, "422 Unprocessable Entity")
        status, error = self.call_raw("POST", "/api/styles/sources?isolated_context_id=setup-test",
            "../rules.txt", b"Some rules.")
        self.assertEqual(status, "422 Unprocessable Entity")
        self.assertEqual(error["error"]["code"], "invalid_style_source_filename")

    def test_style_document_proposal_is_cited_unpublished_and_publish_rechecks_source(self):
        content = b"Use quiet dialogue.\n"
        source_id = f"style-source-{hashlib.sha256(content).hexdigest()[:16]}"
        status, uploaded = self.call_raw("POST", "/api/styles/sources?isolated_context_id=setup-test", "rules.txt", content)
        self.assertEqual(status, "201 Created")
        proposal = {"display_name": "Quiet Film", "guidance": "Use quiet dialogue.", "evidence": [{
            "source_id": source_id, "locator": "line:1-1", "quote": "Use quiet dialogue.",
            "intent": "Keep dialogue restrained."}]}
        self.app = create_app(data_root=self.root,
            capability_provider=lambda: self.fail("style route probed generation capability"),
            gpu_reader=lambda: self.fail("style route read GPU"),
            reasoning_json_provider=lambda **_kwargs: proposal)
        status, drafted = self.call("POST", "/api/styles/sources/analyze", {
            "isolated_context_id": "setup-test", "source_ids": [uploaded["source_id"]],
            "user_intent": "Use its dialogue style."})
        self.assertEqual(status, "200 OK")
        self.assertFalse(drafted["persisted"])
        self.assertFalse(drafted["published"])
        self.assertEqual(drafted["evidence"][0]["source_sha256"], uploaded["sha256"])

        evidence = drafted["evidence"]
        evidence[0]["quote"] = "A quote that was not uploaded."
        status, error = self.call("POST", "/api/styles/directing-styles", {
            "isolated_context_id": "setup-test", "style_id": "quiet_film", "display_name": "Quiet Film",
            "guidance": "Use quiet dialogue.", "evidence": evidence})
        self.assertEqual(status, "422 Unprocessable Entity")
        evidence[0]["quote"] = "Use quiet dialogue."
        status, published = self.call("POST", "/api/styles/directing-styles", {
            "isolated_context_id": "setup-test", "style_id": "quiet_film", "display_name": "Quiet Film",
            "guidance": "Use quiet dialogue.", "evidence": evidence})
        self.assertEqual(status, "201 Created")
        self.assertEqual(published["evidence"][0]["source_id"], source_id)

    def test_image_style_proposal_attaches_only_selected_setup_images_and_is_unpublished(self):
        png = b"\x89PNG\r\n\x1a\n" + b"test-image-bytes"
        with patch("story_builder.services.media_library._probe", return_value={"width": 1, "height": 1}):
            image = register_upload(self.root, "setup-test", filename="reference.png", content=png,
                role="style_reference", provenance_notes="test fixture")
            unrelated = register_upload(self.root, "other-setup", filename="other.png", content=png + b"2",
                role="style_reference", provenance_notes="test fixture")
        received = {}
        result = {"display_name": "Low-key Cinema", "guidance": "Use subdued color and motivated light.",
            "evidence": [{"asset_id": image["asset_id"], "intent": "Use the subdued palette."}]}
        self.app = create_app(data_root=self.root,
            capability_provider=lambda: self.fail("style route probed generation capability"),
            gpu_reader=lambda: self.fail("style route read GPU"),
            reasoning_json_provider=lambda **kwargs: (received.update(kwargs) or result))
        status, drafted = self.call("POST", "/api/styles/media/analyze", {
            "isolated_context_id": "setup-test", "asset_ids": [image["asset_id"]],
            "user_intent": "Focus on lighting."})
        self.assertEqual(status, "200 OK")
        self.assertEqual(drafted["status"], "proposal")
        self.assertFalse(drafted["persisted"])
        self.assertFalse(drafted["published"])
        self.assertEqual(drafted["evidence"], [{"kind": "image", "asset_id": image["asset_id"],
            "sha256": image["sha256"], "intent": "Use the subdued palette."}])
        self.assertEqual([Path(path) for path in received["image_paths"]], [asset_path(self.root, "setup-test", image["asset_id"])[0]])

        status, error = self.call("POST", "/api/styles/media/analyze", {
            "isolated_context_id": "setup-test", "asset_ids": [unrelated["asset_id"]]})
        self.assertEqual(status, "422 Unprocessable Entity")
        self.assertEqual(error["error"]["code"], "invalid_style_images")

    def test_style_proposal_accepts_selected_reference_beyond_first_asset_page(self):
        png = b"\x89PNG\r\n\x1a\n" + b"style-reference-"
        with patch("story_builder.services.media_library._probe", return_value={"width": 1, "height": 1}):
            for index in range(101):
                image = register_upload(self.root, "setup-test", filename=f"reference-{index:03}.png",
                    content=png + str(index).encode(), role="style_reference")
        selected = image
        proposal = {"display_name": "Late Reference", "guidance": "Use its composition.",
            "evidence": [{"asset_id": selected["asset_id"], "intent": "Use this composition."}]}
        self.app = create_app(data_root=self.root,
            capability_provider=lambda: self.fail("style route probed generation capability"),
            gpu_reader=lambda: self.fail("style route read GPU"),
            reasoning_json_provider=lambda **_kwargs: proposal)

        status, drafted = self.call("POST", "/api/styles/media/analyze", {
            "isolated_context_id": "setup-test", "asset_ids": [selected["asset_id"]]})

        self.assertEqual(status, "200 OK")
        self.assertEqual(drafted["evidence"][0]["asset_id"], selected["asset_id"])

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
