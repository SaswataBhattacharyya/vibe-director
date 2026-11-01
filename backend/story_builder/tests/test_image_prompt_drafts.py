from __future__ import annotations

import io
import json
import tempfile
import unittest
import sqlite3
from unittest.mock import patch
from pathlib import Path

from story_builder.isolated_server import create_app
from story_builder.services.image_prompt_drafts import prepare_image_prompt
from story_builder.services.production_ledger import LedgerConflict


class FakeKnowledge:
    def __init__(self, status="matched"):
        self.status = status

    def get(self, workflow_id, *, model_id):
        return {
            "workflow_id": workflow_id, "model_id": model_id,
            "retrieval_status": self.status, "knowledge_id": "knowledge-1",
            "guidance_version": 3, "workflow_sha256": "a" * 64,
            "sources": [{"source_id": "graph", "uri": "workflows/image.json",
                         "version": "b" * 64, "section": "prompt input"}],
            "nodes": [{"kind": "prompt_contract", "text": "Keep the subject centered.",
                       "source_ids": ["graph"]}],
        }


class ImagePromptDraftTests(unittest.TestCase):
    def test_multi_angle_director_brief_delegates_angles_to_native_camera_nodes(self):
        calls = []
        prepare_image_prompt(workflow_knowledge=FakeKnowledge(),
            workflow_id="qwen_image_multi_angle_2511", asset_role="character_view",
            prompt_seed="Create a side view", world_view_count=4,
            provider_call=lambda **kwargs: (calls.append(kwargs["prompt"]) or {"prompt": "Preserve identity and clothing."}))
        self.assertIn("Do not specify side, front, back", calls[0])
        self.assertIn("Rewrite conflicting angle instructions", calls[0])

    def test_draft_uses_exact_workflow_guidance_and_returns_provenance(self):
        calls = []

        def provider_call(*, temperature, prompt):
            calls.append((temperature, prompt))
            return {"prompt": "A centered portrait of Mira."}

        result = prepare_image_prompt(workflow_knowledge=FakeKnowledge(), workflow_id="z_image_turbo",
            asset_role="character_master", prompt_seed="Mira portrait", story_context={"title": "Trial"},
            provider_call=provider_call)
        self.assertEqual(result["prompt"], "A centered portrait of Mira.")
        self.assertEqual(result["knowledge_ref"], {"knowledge_id": "knowledge-1",
            "guidance_version": 3, "workflow_sha256": "a" * 64})
        self.assertIn("Keep the subject centered.", calls[0][1])
        self.assertIn('"title": "Trial"', calls[0][1])
        self.assertIn("do not put workflow settings or metadata in the image prompt", calls[0][1])
        self.assertEqual(calls[0][0], 0)

    def test_asset_briefs_separate_characters_from_worlds(self):
        for role, expected in (("character_master", "plain white studio background"),
                ("world_master", "No people or characters"),
                ("character_view", "plain white background"),
                ("world_view", "no people or characters")):
            calls = []
            prepare_image_prompt(workflow_knowledge=FakeKnowledge(), workflow_id="z_image_turbo",
                asset_role=role, prompt_seed="Saved facts", provider_call=lambda **kw:
                    (calls.append(kw["prompt"]) or {"prompt": "An editable draft"}))
            self.assertIn(expected, calls[0])
            self.assertIn("ASSET BRIEF (required)", calls[0])

    def test_character_prompts_translate_story_roles_into_positive_human_appearance(self):
        for workflow in ("z_image_turbo", "qwen_image_edit_2511", "qwen_image_multi_angle_2511"):
            for role in ("character_master", "character_view"):
                calls = []
                prepared = "A man in a plain work shirt and trousers, standing with relaxed empty hands against a plain white background."
                result = prepare_image_prompt(workflow_knowledge=FakeKnowledge(), workflow_id=workflow,
                    asset_role=role, prompt_seed="Ivo, a bicycle mechanic, no props",
                    target_context={"name": "Ivo", "detail": "Bicycle mechanic carrying a dynamo"},
                    provider_call=lambda **kw: (calls.append(kw["prompt"]) or {"prompt": prepared}))
                self.assertIn("omit the occupation/job title itself", calls[0])
                self.assertIn("Use positive visual descriptions only", calls[0])
                self.assertIn("rewrite them rather than repeating their story-role wording", calls[0])
                self.assertEqual(result["prompt"], prepared)
                self.assertNotIn("bicycle", result["prompt"])

    def test_draft_receives_pinned_directing_style(self):
        calls = []
        def provider_call(*, temperature, prompt):
            calls.append(prompt)
            return {"prompt": "A restrained, shadow-heavy portrait."}
        selection = {"directing_style": {"style_id": "horror", "version": 2,
            "guidance": "Use motivated shadows, restrained color, and held compositions."}}
        prepare_image_prompt(workflow_knowledge=FakeKnowledge(), workflow_id="z_image_turbo",
            asset_role="character_master", prompt_seed="A portrait", style_context=selection,
            provider_call=provider_call)
        self.assertIn('"style_id": "horror"', calls[0])
        self.assertIn("motivated shadows", calls[0])

    def test_multi_angle_uses_qwen_edit_knowledge_identity(self):
        class CaptureKnowledge(FakeKnowledge):
            def get(self, workflow_id, *, model_id):
                self.requested = (workflow_id, model_id)
                return super().get(workflow_id, model_id=model_id)

        knowledge = CaptureKnowledge()
        prepare_image_prompt(workflow_knowledge=knowledge, workflow_id="qwen_image_multi_angle_2511",
            asset_role="world_view", prompt_seed="Four sides", world_view_count=4,
            provider_call=lambda **_: {"prompt": "Four directional views of the same world."})
        self.assertEqual(knowledge.requested, ("qwen_image_multi_angle_2511", "qwen_image_edit_2511"))

    def test_multi_angle_corrects_fixed_direction_before_returning_draft(self):
        calls = []
        def provider(**kwargs):
            calls.append(kwargs)
            return {"prompt": "Edit into a side view." if len(calls) == 1 else "Preserve the same person and clothing against a white background."}
        for count in (2, 3):
            calls.clear()
            result = prepare_image_prompt(workflow_knowledge=FakeKnowledge(),
                workflow_id="qwen_image_multi_angle_2511", asset_role="character_view",
                prompt_seed="side view", world_view_count=count, provider_call=provider)
            self.assertEqual(len(calls), 2)
            self.assertNotIn("side view", result["prompt"])
        with self.assertRaisesRegex(ValueError, "fixed camera view"):
            prepare_image_prompt(workflow_knowledge=FakeKnowledge(),
                workflow_id="qwen_image_multi_angle_2511", asset_role="character_view",
                prompt_seed="", world_view_count=2,
                provider_call=lambda **_: {"prompt": "Edit into a side view."})

    def test_unmatched_guidance_does_not_call_provider(self):
        def provider_call(**_):
            self.fail("Provider must not run without exact workflow guidance")

        with self.assertRaisesRegex(LedgerConflict, "No curated guidance"):
            prepare_image_prompt(workflow_knowledge=FakeKnowledge("not_curated"),
                workflow_id="z_image_turbo", asset_role="character_master", prompt_seed="Mira",
                provider_call=provider_call)

    def test_input_and_output_prompt_limits_are_enforced(self):
        with self.assertRaisesRegex(ValueError, "under 7,000"):
            prepare_image_prompt(workflow_knowledge=FakeKnowledge(), workflow_id="z_image_turbo",
                asset_role="character_master", prompt_seed="x" * 7000,
                provider_call=lambda **_: self.fail("Invalid input must not call provider"))
        with self.assertRaisesRegex(ValueError, "under the 7,000-character limit"):
            prepare_image_prompt(workflow_knowledge=FakeKnowledge(), workflow_id="z_image_turbo",
                asset_role="character_master", prompt_seed="Mira",
                provider_call=lambda **_: {"prompt": "x" * 7000})

    def test_stale_guidance_is_explicitly_rejected_without_creating_jobs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "data"
            app = create_app(data_root=root,
                gpu_reader=lambda: self.fail("Rejected prompt must not query GPU"),
                worker_status_provider=lambda: self.fail("Rejected prompt must not query worker"))
            payload = {"workspace_id": "standalone-1", "workflow_id": "z_image_turbo",
                "asset_role": "character_master", "prompt": "A portrait", "seed": 42,
                "control_mode": "assisted_manual", "output_prefix": "standalone-1/portrait",
                "idempotency_key": "stale-prompt", "prompt_knowledge_ref": {
                    "knowledge_id": "outdated", "guidance_version": 1, "workflow_sha256": "a" * 64}}
            body = json.dumps(payload).encode()
            for _ in range(2):
                statuses = []
                result = json.loads(b"".join(app({"REQUEST_METHOD": "POST", "PATH_INFO": "/api/images/jobs",
                    "QUERY_STRING": "", "CONTENT_TYPE": "application/json", "CONTENT_LENGTH": str(len(body)),
                    "wsgi.input": io.BytesIO(body)}, lambda status, headers: statuses.append(status))))
                self.assertEqual(statuses, ["409 Conflict"])
                self.assertEqual(result["admission_state"], "not_created")
                self.assertEqual(result["error"]["code"], "image_prompt_guidance_changed")
            with sqlite3.connect(root / "services/production/image-jobs.sqlite3") as db:
                self.assertEqual(db.execute("SELECT COUNT(*) FROM production_image_jobs").fetchone()[0], 0)
            with patch("story_builder.isolated_server.image_workflow_catalog", return_value={
                    "workflows": [{"workflow_id": "z_image_turbo"}]}):
                result = json.loads(b"".join(app({"REQUEST_METHOD": "GET", "PATH_INFO": "/api/images/workflows",
                    "QUERY_STRING": ""}, lambda *_: None)))
            self.assertTrue(result["workflows"][0]["prompt_knowledge_ref"]["knowledge_id"])

    def test_prepare_route_calls_mock_provider_without_gpu_or_comfy_submission(self):
        calls = []

        def provider(**kwargs):
            calls.append(kwargs)
            return {"prompt": "A carefully framed standalone image."}

        with tempfile.TemporaryDirectory() as temporary:
            app = create_app(data_root=Path(temporary) / "data", reasoning_json_provider=provider,
                gpu_reader=lambda: self.fail("Prompt drafting must not query or submit to the GPU"),
                worker_status_provider=lambda: self.fail("Prompt drafting must not query ComfyUI"))
            payload = {"workspace_id": "standalone-1", "workflow_id": "z_image_turbo",
                "asset_role": "character_master", "prompt": "A portrait"}
            body = json.dumps(payload).encode()
            environ = {"REQUEST_METHOD": "POST", "PATH_INFO": "/api/images/prompts/prepare",
                "QUERY_STRING": "", "CONTENT_TYPE": "application/json", "CONTENT_LENGTH": str(len(body)),
                "wsgi.input": io.BytesIO(body)}
            response = []
            result = b"".join(app(environ, lambda status, headers: response.append(status)))
        self.assertEqual(response[0], "200 OK")
        data = json.loads(result)
        self.assertEqual(data["prompt"], "A carefully framed standalone image.")
        self.assertEqual(data["knowledge_ref"]["guidance_version"], 1)
        self.assertTrue(data["sources"])
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["provider"], "codex")


if __name__ == "__main__":
    unittest.main()
