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


    def test_recursive_unregistered_project_files_and_role_filters(self):
        from story_builder.services.media_library import list_assets
        from story_builder.services.storage_paths import project_root
        folder = project_root(self.root, "external") / "user files/nested"
        folder.mkdir(parents=True)
        image = folder / "outside.PNG"
        image.write_bytes(self.png())
        (folder / "voice.mp3").write_bytes(b"audio fixture")
        (folder / "clip.mp4").write_bytes(b"video fixture")
        (folder / "notes.txt").write_text("not media")
        (folder / "escape.png").symlink_to(image)
        with patch("story_builder.services.media_library._probe", return_value={"duration_seconds": 1}):
            images = browse_catalogue(self.root, "external", source="current", kinds="image")
            self.assertEqual([a["filename"] for a in images["assets"]], ["outside.PNG"])
            row = images["assets"][0]
            self.assertEqual(row["roles"], ["project_image"])
            self.assertEqual(asset_path(self.root, "external", row["asset_id"])[0], image)
            self.assertEqual(browse_catalogue(self.root, "external", source="current", kinds="audio")["total"], 1)
            self.assertEqual(browse_catalogue(self.root, "external", source="current", kinds="video")["total"], 1)
            self.assertEqual(browse_catalogue(self.root, "other", owner="external", kinds="image")["total"], 1)
            self.assertEqual(browse_catalogue(self.root, "other", source="current")["total"], 0)
            self.assertEqual(browse_catalogue(self.root, "other", source="style")["total"], 0)
            self.assertEqual(list_assets(self.root, "external", kind="image")["assets"][0]["asset_id"], row["asset_id"])
            linked = reuse_catalogue_asset(self.root, "other", source_workspace_id="external", asset_id=row["asset_id"])
            self.assertEqual(asset_path(self.root, "other", linked["asset_id"])[0], image)
            set_asset_archived(self.root, "external", row["asset_id"], archived=True)
            self.assertEqual(browse_catalogue(self.root, "external", source="current", kinds="image")["total"], 0)
            image.unlink()
            self.assertEqual(list_assets(self.root, "other", kind="image")["total"], 0)

    def test_unregistered_shared_media_all_types_preserves_existing_identity(self):
        existing = register_upload(self.root, "owner", filename="known.png", content=self.png(), role="character_master")
        for directory in ("youtube_downloads/files/sub", "video_repertoire/unanalysed"):
            folder = self.root / directory
            folder.mkdir(parents=True)
            for name in ("photo.webp", "sound.flac", "movie.mov"):
                (folder / name).write_bytes(b"media fixture")
        with patch("story_builder.services.media_library._probe", return_value={}):
            for kind in ("image", "audio", "video"):
                self.assertEqual(browse_catalogue(self.root, "owner", source="downloaded", kinds=kind)["total"], 1)
                self.assertEqual(browse_catalogue(self.root, "owner", source="repertoire", kinds=kind)["total"], 1)
            first = browse_catalogue(self.root, "owner", kinds="image")
            self.assertEqual(first["total"], 3)
            self.assertEqual(browse_catalogue(self.root, "owner", source="projects", kinds="image")["total"], 1)
            again = browse_catalogue(self.root, "owner", kinds="image")
            self.assertEqual([a["asset_id"] for a in first["assets"]], [a["asset_id"] for a in again["assets"]])
            self.assertIn(existing["asset_id"], [a["asset_id"] for a in again["assets"]])

    def test_managed_staging_exclusion_is_precise_in_all_project_locations(self):
        import json
        from story_builder.services.storage_paths import project_root, media_root, generated_root
        from story_builder.services.projects import home
        for workspace in ("story-aaaaaaaaaaaa", "tool-library"):
            base = media_root(self.root, workspace) if workspace == "tool-library" else project_root(self.root, workspace)
            staging = generated_root(self.root, workspace) / "utility_inputs/stage-test"
            staging.mkdir(parents=True)
            (staging / "private.png").write_bytes(self.png())
            legitimate = base / "user files/utility_inputs"
            legitimate.mkdir(parents=True)
            original = legitimate / "original.png"
            original.write_bytes(self.png())
            with patch("story_builder.services.media_library._probe", return_value={}):
                rows = browse_catalogue(self.root, workspace, source="current", kinds="image")["assets"]
            self.assertEqual([r["filename"] for r in rows], ["original.png"])
            self.assertEqual(original.read_bytes(), self.png())
        saved = Path(self.temporary.name) / "saved staging project"
        (saved / "media/generated/utility_inputs/stage-test").mkdir(parents=True)
        (saved / "media/generated/utility_inputs/stage-test/private.png").write_bytes(self.png())
        (saved / "published.png").write_bytes(self.png())
        (home(self.root) / "folders.json").write_text(json.dumps({"story-aaaaaaaaaaaa": str(saved)}))
        with patch("story_builder.services.media_library._probe", return_value={}):
            rows = browse_catalogue(self.root, "story-aaaaaaaaaaaa", source="current", kinds="image")["assets"]
        self.assertEqual({r["filename"] for r in rows}, {"original.png", "published.png"})

    def test_saved_external_folder_is_discovered_and_traversal_rejected(self):
        import json
        from story_builder.services.projects import home
        from story_builder.services.storage_paths import shared_file
        folder = Path(self.temporary.name) / "saved project"
        folder.mkdir()
        image = folder / "pasted.png"
        image.write_bytes(self.png())
        (home(self.root) / "folders.json").write_text(json.dumps({"saved": str(folder)}))
        with patch("story_builder.services.media_library._probe", return_value={}):
            row = browse_catalogue(self.root, "saved", source="current", kinds="image")["assets"][0]
        self.assertEqual(asset_path(self.root, "saved", row["asset_id"])[0], image)
        for path in ("../outside.png", str(image)):
            with self.assertRaises(ValueError):
                shared_file(self.root, {"store": "project", "workspace_id": "saved", "saved": True, "path": path})
        image.write_bytes(b"changed")
        with self.assertRaises(ProductionAssetError):
            reuse_catalogue_asset(self.root, "other", source_workspace_id="saved", asset_id=row["asset_id"])


    def test_real_image_discovery_and_checkpoint_copies_are_not_sources(self):
        from story_builder.services.storage_paths import project_root
        folder = project_root(self.root, "real")
        folder.mkdir(parents=True)
        (folder / "new.png").write_bytes(self.png())
        backup = folder / "project-data/revision/content"
        backup.mkdir(parents=True)
        (backup / "old.png").write_bytes(self.png())
        row = browse_catalogue(self.root, "real", source="current", kinds="image")["assets"][0]
        self.assertEqual(row["filename"], "new.png")
        self.assertEqual(row["media"], {"width": 2, "height": 3})
        self.assertEqual(browse_catalogue(self.root, "real", source="current")["total"], 1)

    def test_replaced_file_gets_new_identity_without_rewriting_saved_reference(self):
        import hashlib
        from story_builder.services.media_library import list_assets, register_generated_image
        from story_builder.services.storage_paths import generated_root
        folder = generated_root(self.root, "replace")
        folder.mkdir(parents=True, exist_ok=True)
        image = folder / "lastframe.png"
        image.write_bytes(self.png())
        registered = register_generated_image(self.root, "replace", "lastframe.png", {})
        first = list_assets(self.root, "replace", kind="image")["assets"][0]
        self.assertEqual(first["asset_id"], registered["asset_id"])
        # A valid replacement at the same path, with unchanged dimensions/length.
        image.write_bytes(self.png((0, 255, 0)))
        second = list_assets(self.root, "replace", kind="image")["assets"]
        self.assertEqual(len(second), 1)
        self.assertNotEqual(second[0]["asset_id"], first["asset_id"])
        self.assertEqual(second[0]["sha256"], hashlib.sha256(image.read_bytes()).hexdigest())
        self.assertEqual(list_assets(self.root, "replace", kind="image")["assets"], second)
        self.assertEqual(browse_catalogue(self.root, "replace", source="current", kinds="image")["total"], 1)
        historical = {row["asset_id"]: row for row in list_assets(self.root, "replace", include_archived=True)["assets"]}
        self.assertEqual(historical[first["asset_id"]]["sha256"], first["sha256"])
        self.assertEqual(len(historical), 2)
        set_asset_archived(self.root, "replace", second[0]["asset_id"], archived=True)
        image.write_bytes(self.png((0, 0, 255)))
        self.assertEqual(list_assets(self.root, "replace")["total"], 0)
        self.assertEqual(list_assets(self.root, "replace", include_archived=True)["total"], 2)
