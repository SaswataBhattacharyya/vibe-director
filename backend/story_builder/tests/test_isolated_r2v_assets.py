from __future__ import annotations

import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from story_builder.services.isolated_r2v_assets import (
    R2VStagingError, cleanup_r2v_staging_job, stage_r2v_references,
)


class IsolatedR2VAssetTests(TestCase):
    def test_staging_rejects_symlink_ancestors_before_resolution_or_cleanup(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            real = root / "real"
            real.mkdir()
            link = root / "linked"
            link.symlink_to(real, target_is_directory=True)
            with patch("story_builder.services.isolated_r2v_assets.list_assets") as listing, \
                 patch("story_builder.services.isolated_r2v_assets.stage_image_reference") as staging, \
                 patch("story_builder.services.isolated_r2v_assets.cleanup_owned_media") as cleanup:
                with self.assertRaisesRegex(R2VStagingError, "symlinks"):
                    stage_r2v_references(media_root=root, workspace_id="ws", job_id="job-1",
                        request={"images": [], "videos": [], "audios": []},
                        comfy_input_root=link / "comfy", owner_root=root / "owners")
                listing.assert_not_called()
                staging.assert_not_called()
                cleanup.assert_not_called()

    def test_stage_and_cleanup_reject_job_and_manifest_symlink_escapes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            input_root, owner_root, outside = root / "input", root / "owners", root / "outside"
            input_root.mkdir()
            owner_root.mkdir()
            outside.mkdir()
            (owner_root / "job-1").symlink_to(outside, target_is_directory=True)
            image_request = {"images": [{"asset_id": "pa-0123456789abcdef", "sha256": "a" * 64}],
                "videos": [], "audios": []}
            with patch("story_builder.services.isolated_r2v_assets.list_assets") as listing, \
                 patch("story_builder.services.isolated_r2v_assets.stage_image_reference") as staging, \
                 patch("story_builder.services.isolated_r2v_assets.cleanup_owned_media") as cleanup:
                with self.assertRaisesRegex(R2VStagingError, "symlinks"):
                    stage_r2v_references(media_root=root, workspace_id="ws", job_id="job-1",
                        request=image_request,
                        comfy_input_root=input_root, owner_root=owner_root)
                with self.assertRaisesRegex(R2VStagingError, "symlinks"):
                    cleanup_r2v_staging_job(job_id="job-1", comfy_input_root=input_root,
                        owner_root=owner_root)
                listing.assert_not_called()
                staging.assert_not_called()
                cleanup.assert_not_called()
            (owner_root / "job-1").unlink()
            job_dir = owner_root / "job-1"
            job_dir.mkdir()
            (job_dir / "owner_manifest.json").symlink_to(outside / "manifest.json")
            with patch("story_builder.services.isolated_r2v_assets.stage_image_reference") as staging, \
                 patch("story_builder.services.isolated_r2v_assets.cleanup_owned_media") as cleanup:
                with self.assertRaisesRegex(R2VStagingError, "symlinks"):
                    cleanup_r2v_staging_job(job_id="job-1", comfy_input_root=input_root,
                        owner_root=owner_root)
                staging.assert_not_called()
                cleanup.assert_not_called()

    def test_id_hash_and_kind_are_checked_before_compiler_receives_staged_names(self):
        digest = "a" * 64
        request = {"images": [{"asset_id": "pa-0123456789abcdef", "sha256": digest}],
            "videos": [], "audios": []}
        record = {"asset_id": "pa-0123456789abcdef", "kind": "image", "sha256": digest,
            "media_type": "image/png"}
        staged = SimpleNamespace(filename="staged.png", sha256="b" * 64, source_sha256=digest)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.png"
            source.write_bytes(b"image")
            with patch("story_builder.services.isolated_r2v_assets.list_assets",
                    return_value={"assets": [record], "total": 1, "limit": 100}), \
                 patch("story_builder.services.isolated_r2v_assets.asset_path",
                    return_value=(source, "image/png", "source.png")), \
                 patch("story_builder.services.isolated_r2v_assets.stage_image_reference", return_value=staged):
                result = stage_r2v_references(media_root=root, workspace_id="ws", job_id="job-1",
                    request=request, comfy_input_root=root / "comfy", owner_root=root / "owners")
            self.assertEqual(result["pa-0123456789abcdef"].comfy_filename, "staged.png")
            with patch("story_builder.services.isolated_r2v_assets.list_assets",
                    return_value={"assets": [{**record, "sha256": "c" * 64}], "total": 1, "limit": 100}), \
                 patch("story_builder.services.isolated_r2v_assets.stage_image_reference") as stage:
                with self.assertRaises(R2VStagingError):
                    stage_r2v_references(media_root=root, workspace_id="ws", job_id="job-2",
                        request=request, comfy_input_root=root / "comfy", owner_root=root / "owners")
                stage.assert_not_called()

    def test_pinned_style_recommendation_is_staged_from_its_original_context(self):
        digest = "b" * 64
        asset_id = "pa-0123456789abcdef"
        selection = {"snapshot_id": "a" * 32, "isolated_context_id": "setup-style",
            "style_version_id": "base:film:v1"}
        record = {"asset_id": asset_id, "kind": "image", "sha256": digest,
            "media_type": "image/png", "recommended": True}
        staged = SimpleNamespace(filename="style.png", sha256="c" * 64, source_sha256=digest)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "style.png"
            source.write_bytes(b"original style bytes")
            with patch("story_builder.services.isolated_r2v_assets.list_assets",
                    return_value={"assets": [record], "total": 1, "limit": 100}) as listing, \
                 patch("story_builder.services.isolated_r2v_assets.asset_path") as local_path, \
                 patch("story_builder.services.isolated_r2v_assets.pinned_style_asset_path",
                    return_value=(source, "image/png", "style.png", record)) as pinned_path, \
                 patch("story_builder.services.isolated_r2v_assets.stage_image_reference", return_value=staged):
                result = stage_r2v_references(media_root=root, workspace_id="story-0123456789ab", job_id="job-1",
                    request={"images": [{"asset_id": asset_id, "sha256": digest}], "videos": [], "audios": []},
                    comfy_input_root=root / "comfy", owner_root=root / "owners", style_selection=selection)
            self.assertEqual(result[asset_id].comfy_filename, "style.png")
            self.assertEqual(listing.call_args.kwargs["style_selection"], selection)
            self.assertTrue(listing.call_args.kwargs["include_archived"])
            pinned_path.assert_called_once_with(root, selection, asset_id)
            local_path.assert_not_called()
