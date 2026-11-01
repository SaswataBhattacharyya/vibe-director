import unittest
from pathlib import Path
from unittest.mock import patch
from story_builder.tests import test_media_library as fixtures
from story_builder.services.media_library import (browse_catalogue, reuse_catalogue_asset,
    register_upload, asset_path, set_asset_archived, update_annotations, ProductionAssetError)

class CatalogueTests(unittest.TestCase):
    setUp = fixtures.MediaLibraryTests.setUp
    png = fixtures.MediaLibraryTests.png
    # Reuse fixture helpers, not the unrelated inherited test suite.
    def test_cross_workspace_filters_and_independent_copy(self):
        source = register_upload(self.root, "source", filename="portrait.png", content=self.png(), role="character_master")
        page = browse_catalogue(self.root, "target", kinds="image", query="portrait", limit=1)
        self.assertEqual(page["total"], 1)
        self.assertEqual(page["assets"][0]["workspace_id"], "source")
        self.assertNotIn("relative_path", page["assets"][0])
        self.assertEqual(browse_catalogue(self.root, "target", kinds="audio")["total"], 0)
        self.assertEqual(browse_catalogue(self.root, "target", source="current")["total"], 0)
        copied = reuse_catalogue_asset(self.root, "target", source_workspace_id="source", asset_id=source["asset_id"])
        self.assertNotEqual(copied["asset_id"], source["asset_id"])
        a, _, _ = asset_path(self.root, "source", source["asset_id"])
        b, _, _ = asset_path(self.root, "target", copied["asset_id"])
        self.assertNotEqual(a, b)
        self.assertEqual(a.read_bytes(), b.read_bytes())
        a.unlink()
        self.assertTrue(b.exists())

    def test_archive_tamper_traversal_and_target_dedup(self):
        source = register_upload(self.root, "source", filename="portrait.png", content=self.png(), role="character_master")
        target = register_upload(self.root, "target", filename="own.png", content=self.png(), role="world_master")
        copied = reuse_catalogue_asset(self.root, "target", source_workspace_id="source", asset_id=source["asset_id"])
        self.assertEqual(copied["asset_id"], target["asset_id"])
        self.assertEqual(copied["roles"], ["world_master"])
        with self.assertRaises(ProductionAssetError):
            browse_catalogue(self.root, "../escape")
        with self.assertRaises(ProductionAssetError):
            browse_catalogue(self.root, "target", limit=101)
        source_path, _, _ = asset_path(self.root, "source", source["asset_id"])
        source_path.write_bytes(b"changed")
        with self.assertRaises(ProductionAssetError):
            reuse_catalogue_asset(self.root, "other", source_workspace_id="source", asset_id=source["asset_id"])
        set_asset_archived(self.root, "source", source["asset_id"], archived=True)
        self.assertEqual(browse_catalogue(self.root, "other", owner="source")["total"], 0)
        with self.assertRaises(ProductionAssetError):
            reuse_catalogue_asset(self.root, "other", source_workspace_id="source", asset_id=source["asset_id"])

    def test_style_reuse_preserves_origin_and_deduplicates_provenance(self):
        source = register_upload(self.root, "source", filename="style.png", content=self.png(), role="style_reference")
        self.assertEqual(browse_catalogue(self.root, "target", source="style")["total"], 1)
        with self.assertRaises(ProductionAssetError):
            reuse_catalogue_asset(self.root, "target", source_workspace_id="source", asset_id=source["asset_id"], role="project_audio")
        first = reuse_catalogue_asset(self.root, "target", source_workspace_id="source", asset_id=source["asset_id"], role="style_reference")
        second = reuse_catalogue_asset(self.root, "target", source_workspace_id="source", asset_id=source["asset_id"], role="style_reference")
        self.assertEqual(first["asset_id"], second["asset_id"])
        self.assertIn("style_reference", second["roles"])
        self.assertEqual(len(second["metadata"]["library_sources"]), 1)
        self.assertEqual(second["metadata"]["library_sources"][0]["workspace_id"], "source")

    def test_ace_filter_archive_keeps_saved_audio_playable(self):
        import io, wave
        from story_builder.services.media_library import register_generated_audio
        from story_builder.services.storage_paths import generated_root
        payload = io.BytesIO()
        with wave.open(payload, "wb") as wav:
            wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(8000)
            wav.writeframes(b"\0\0" * 800)
        output = generated_root(self.root, "music") / "ace.wav"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(payload.getvalue())
        ace = register_generated_audio(self.root, "music", "ace.wav", {"source":"ace_step_standalone"})
        register_upload(self.root, "music", filename="other.png", content=self.png(), role="character_master")
        result = browse_catalogue(self.root, "target", source="ace_generated", kinds="audio")
        self.assertEqual([a["asset_id"] for a in result["assets"]], [ace["asset_id"]])
        self.assertEqual(browse_catalogue(self.root, "target", source="generated")["total"], 1)
        self.assertEqual(browse_catalogue(self.root, "target", source="ace_generated", kinds="image")["total"], 0)
        set_asset_archived(self.root, "music", ace["asset_id"], archived=True)
        self.assertEqual(browse_catalogue(self.root, "target", source="ace_generated")["total"], 0)
        path, _, _ = asset_path(self.root, "music", ace["asset_id"])
        self.assertEqual(path.read_bytes(), payload.getvalue())
        set_asset_archived(self.root, "music", ace["asset_id"], archived=False)
        self.assertEqual(browse_catalogue(self.root, "target", source="ace_generated")["total"], 1)

    def test_named_workspace_global_source_and_folder_navigation(self):
        from story_builder.services.media_library import name_media_workspace
        register_upload(self.root, "elsewhere", filename="portrait.png", content=self.png(), role="character_master")
        name_media_workspace(self.root, "elsewhere", "Summer film")
        result = browse_catalogue(self.root, "target", source="imported", owner="target")
        self.assertEqual(result["total"], 1)  # Global sources ignore stale workspace filters.
        self.assertEqual(result["workspace_names"]["elsewhere"], "Summer film")
        folder = result["assets"][0]["source_folder"]
        self.assertEqual(browse_catalogue(self.root, "target", source="imported", folder=folder)["total"], 1)
        self.assertEqual(browse_catalogue(self.root, "target", source="imported", folder="not-here")["total"], 0)
        for invalid in ("", "  ", "x" * 121, "bad\nname"):
            with self.assertRaises(ProductionAssetError):
                name_media_workspace(self.root, "target", invalid)
        with self.assertRaises(ProductionAssetError):
            browse_catalogue(self.root, "target", folder="../outside")

    def test_download_refresh_indexes_without_copy_or_resurrection(self):
        from story_builder.services.media_library import reconcile_download_catalogue
        base = self.root / "youtube_downloads/files"
        source = base / "channel/movie.mp4"
        source.parent.mkdir(parents=True)
        source.write_bytes(b"video fixture")
        before = source.stat()
        with patch("story_builder.services.media_library._probe", return_value={"duration_seconds": 1}):
            first = reconcile_download_catalogue(self.root)
            self.assertEqual(first, {"added": 1, "errors": []})
            self.assertEqual(reconcile_download_catalogue(self.root)["added"], 0)
            result = browse_catalogue(self.root, "target", source="downloaded", owner="target")
            self.assertEqual(result["total"], 1)
            self.assertIn("channel", result["folders"])
            row = result["assets"][0]
            set_asset_archived(self.root, row["workspace_id"], row["asset_id"], archived=True)
            self.assertEqual(reconcile_download_catalogue(self.root)["added"], 0)
        self.assertEqual(browse_catalogue(self.root, "target", source="downloaded")["total"], 0)  # Owner archive hides the catalogue entry; refresh must not resurrect it.
        self.assertEqual(source.stat().st_ino, before.st_ino)
        self.assertEqual(source.read_bytes(), b"video fixture")
        self.assertEqual(list(self.root.rglob("*.mp4")), [source])
