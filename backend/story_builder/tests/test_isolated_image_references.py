from __future__ import annotations

import tempfile
import hashlib
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from story_builder.services.isolated_image_references import (
    ImageReferenceError, prepare_image_edit_graph, validate_image_references,
)
from story_builder.services.production_image_workflows import compile_image_candidates


class IsolatedImageReferenceTests(unittest.TestCase):
    def test_reference_validation_requires_unique_id_and_matching_workspace_hash(self):
        content = b"same image"
        ref = {"asset_id": "image-1", "sha256": hashlib.sha256(content).hexdigest()}
        record = {**ref, "kind": "image", "media_type": "image/png"}
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "image.png"
            source.write_bytes(content)
            with patch("story_builder.services.isolated_image_references.list_assets", return_value={
                    "assets": [record], "total": 1, "limit": 100}), \
                 patch("story_builder.services.isolated_image_references.asset_path",
                    return_value=(source, "image/png", "image.png")):
                self.assertEqual(validate_image_references(media_root=Path("/tmp"),
                    workspace_id="workspace-1", references=[ref]), [ref])
                with self.assertRaisesRegex(ImageReferenceError, "only once"):
                    validate_image_references(media_root=Path("/tmp"), workspace_id="workspace-1",
                        references=[ref, ref])
                with self.assertRaisesRegex(ImageReferenceError, "missing, changed"):
                    validate_image_references(media_root=Path("/tmp"), workspace_id="workspace-1",
                        references=[{**ref, "sha256": "b" * 64}])

    def test_reference_validation_rejects_changed_image_bytes(self):
        ref = {"asset_id": "image-1", "sha256": "a" * 64}
        record = {**ref, "kind": "image", "media_type": "image/png"}
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "image.png"
            source.write_bytes(b"changed image bytes")
            with patch("story_builder.services.isolated_image_references.list_assets", return_value={
                    "assets": [record], "total": 1, "limit": 100}), \
                 patch("story_builder.services.isolated_image_references.asset_path",
                    return_value=(source, "image/png", "image.png")):
                with self.assertRaisesRegex(ImageReferenceError, "missing, changed"):
                    validate_image_references(media_root=Path("/tmp"), workspace_id="workspace-1",
                        references=[ref])

    def test_worker_stages_frozen_refs_and_patches_only_qwen_image_edit_inputs(self):
        ref = {"asset_id": "image-1", "sha256": hashlib.sha256(b"same image").hexdigest()}
        record = {**ref, "kind": "image", "media_type": "image/png"}
        compiled = compile_image_candidates(workflow_id="qwen_image_edit_2511", prompt="Edit",
            control_mode="assisted_manual", seed=1, output_prefix="edit/run", source_images=["ref-1.png"])
        job = {"project_id": "workspace-1", "job_id": "01234567-89ab-cdef-0123-456789abcdef",
            "graph": compiled["candidates"][0]["graph"],
            "settings": {"image_references": [ref]}}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.png"
            source.write_bytes(b"same image")
            staged = SimpleNamespace(filename="safe-staged.png", source_sha256=ref["sha256"])
            with patch("story_builder.services.isolated_image_references.list_assets", return_value={
                    "assets": [record], "total": 1, "limit": 100}), \
                 patch("story_builder.services.isolated_image_references.asset_path",
                    return_value=(source, "image/png", "source.png")), \
                 patch("story_builder.services.isolated_image_references.stage_image_reference",
                    return_value=staged) as stage:
                graph = prepare_image_edit_graph(job=job, media_root=root,
                    comfy_input_root=root / "comfy-input", owner_root=root / "owners")
        self.assertEqual(graph["78"]["inputs"]["image"], "safe-staged.png")
        self.assertEqual(job["graph"]["78"]["inputs"]["image"], "ref-1.png")
        self.assertEqual(stage.call_args.kwargs["asset_id"], ref["asset_id"])
        self.assertEqual(stage.call_args.kwargs["owner_id"], f"image-{job['job_id']}")

    def test_worker_stages_one_world_base_into_multi_angle_loader(self, role="world_master"):
        content = b"world base"
        ref = {"asset_id": "image-world", "sha256": hashlib.sha256(content).hexdigest()}
        record = {**ref, "kind": "image", "roles": [role], "media_type": "image/png"}
        compiled = compile_image_candidates(workflow_id="qwen_image_multi_angle_2511",
            prompt="A station", control_mode="assisted_manual", seed=1,
            output_prefix="world/views", source_images=["base.png"])
        job = {"project_id": "workspace-1", "job_id": "01234567-89ab-cdef-0123-456789abcdef",
            "asset_role": "character_view" if role == "character_master" else "world_view",
            "workflow_id": "qwen_image_multi_angle_2511", "graph": compiled["candidates"][0]["graph"],
            "settings": {"image_references": [ref]}}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.png"
            source.write_bytes(content)
            staged = SimpleNamespace(filename="safe-world.png", source_sha256=ref["sha256"])
            with patch("story_builder.services.isolated_image_references.list_assets", return_value={
                    "assets": [record], "total": 1, "limit": 100}), \
                 patch("story_builder.services.isolated_image_references.asset_path",
                    return_value=(source, "image/png", "source.png")), \
                 patch("story_builder.services.isolated_image_references.stage_image_reference",
                    return_value=staged):
                graph = prepare_image_edit_graph(job=job, media_root=root,
                    comfy_input_root=root / "comfy-input", owner_root=root / "owners")
        self.assertEqual(graph["41"]["inputs"]["image"], "safe-world.png")
        self.assertEqual(job["graph"]["41"]["inputs"]["image"],
            compiled["candidates"][0]["graph"]["41"]["inputs"]["image"])

    def test_worker_stages_character_master_for_character_side_views(self):
        self.test_worker_stages_one_world_base_into_multi_angle_loader(role="character_master")

    def test_multi_angle_reference_must_be_a_saved_world_master(self):
        content = b"portrait, not a location"
        ref = {"asset_id": "image-world", "sha256": hashlib.sha256(content).hexdigest()}
        record = {**ref, "kind": "image", "roles": ["character_master"], "media_type": "image/png"}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.png"
            source.write_bytes(content)
            with patch("story_builder.services.isolated_image_references.list_assets", return_value={
                    "assets": [record], "total": 1, "limit": 100}), \
                 patch("story_builder.services.isolated_image_references.asset_path",
                    return_value=(source, "image/png", "source.png")):
                with self.assertRaisesRegex(ImageReferenceError, "saved as world master"):
                    validate_image_references(media_root=root, workspace_id="workspace-1",
                        references=[ref], required_role="world_master")
