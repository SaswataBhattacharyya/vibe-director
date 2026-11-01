from __future__ import annotations

import io
import json
import subprocess
import tempfile
import unittest
import warnings
import wave
from pathlib import Path
from unittest.mock import patch

from story_builder.isolated_server import create_app
from story_builder.services.media_library import (
    asset_path, assign_role, create_seo_style, delete_seo_style, extract_style_reference_frames,
    link_style_reference, list_assets, list_seo_styles,
    register_derived_media, register_generated_audio, register_generated_video, register_upload,
    save_image_analysis, set_asset_archived, update_annotations, update_seo_style,
)
from story_builder.services import video_repertoire


class MediaLibraryTests(unittest.TestCase):
    def setUp(self):
        warnings.simplefilter("ignore", ResourceWarning)
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "data"

    def png(self, rgb=(255, 0, 0)):
        import binascii
        import struct
        import zlib
        def chunk(name, data):
            body = name + data
            return struct.pack(">I", len(data)) + body + struct.pack(">I", binascii.crc32(body) & 0xffffffff)
        row = b"\0" + bytes(rgb) * 2
        return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 2, 3, 8, 2, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(row * 3))
                + chunk(b"IEND", b""))

    def mp4(self):
        path = Path(self.temporary.name) / "style.mp4"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
            "testsrc2=duration=2:size=128x72:rate=5", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)],
            check=True, capture_output=True, timeout=30)
        return path.read_bytes()

    def test_workspace_catalog_reuses_identical_bytes_and_roles(self):
        first = register_upload(self.root, "workspace-a", filename="portrait.png",
            content=self.png(), role="character_master", provenance_notes="uploaded for casting")
        duplicate = register_upload(self.root, "workspace-a", filename="same.png",
            content=self.png(), role="style_reference")
        self.assertEqual(first["asset_id"], duplicate["asset_id"])
        self.assertTrue(duplicate["deduplicated"])
        page = list_assets(self.root, "workspace-a", kind="image")
        self.assertEqual(page["total"], 1)
        self.assertEqual(set(page["assets"][0]["roles"]), {"character_master", "style_reference"})
        self.assertEqual(list_assets(self.root, "another-workspace")["total"], 0)

    def test_image_export_route_saves_asset_and_requires_matching_overwrite_confirmation(self):
        asset = register_upload(self.root, "workspace-export", filename="generated.png",
            content=self.png(), role="image_candidate")
        folder = Path(self.temporary.name) / "exports"
        folder.mkdir()
        app = create_app(data_root=self.root)

        def post(payload):
            body = json.dumps(payload).encode()
            statuses = []
            result = json.loads(b"".join(app({"REQUEST_METHOD": "POST", "PATH_INFO": "/api/images/assets/export",
                "QUERY_STRING": "", "CONTENT_TYPE": "application/json", "CONTENT_LENGTH": str(len(body)),
                "wsgi.input": io.BytesIO(body)}, lambda status, _headers: statuses.append(status))))
            return statuses[0], result

        request = {"workspace_id": "workspace-export", "asset_id": asset["asset_id"],
            "folder": str(folder), "filename": "saved.png"}
        status, result = post(request)
        self.assertEqual(status, "200 OK")
        self.assertEqual((folder / "saved.png").read_bytes(), self.png())

        status, collision = post(request)
        self.assertEqual(status, "200 OK")
        self.assertTrue(collision["collision"])
        status, replaced = post({**request, "overwrite": True,
            "existing_sha256": collision["existing_sha256"]})
        self.assertEqual(status, "200 OK")
        self.assertEqual(replaced["path"], str(folder / "saved.png"))

        status, mismatch = post({**request, "filename": "wrong.jpg"})
        self.assertEqual(status, "400 Bad Request")
        self.assertIn("PNG filename", mismatch["error"]["message"])

    def test_archive_hides_asset_without_deleting_file_and_restore_returns_it(self):
        saved = register_upload(self.root, "workspace-a", filename="portrait.png",
            content=self.png(), role="character_master")
        path, _, _ = asset_path(self.root, "workspace-a", saved["asset_id"])

        archived = set_asset_archived(self.root, "workspace-a", saved["asset_id"], archived=True)

        self.assertIn("archived_at", archived)
        self.assertEqual(list_assets(self.root, "workspace-a")["total"], 0)
        archived_page = list_assets(self.root, "workspace-a", include_archived=True)
        self.assertEqual(archived_page["assets"][0]["asset_id"], saved["asset_id"])
        self.assertTrue(path.is_file())
        self.assertEqual(asset_path(self.root, "workspace-a", saved["asset_id"])[0], path)

        restored = set_asset_archived(self.root, "workspace-a", saved["asset_id"], archived=False)
        self.assertNotIn("archived_at", restored)
        self.assertEqual(list_assets(self.root, "workspace-a")["assets"][0]["asset_id"], saved["asset_id"])

    def test_archive_route_round_trip_and_rejects_empty_asset_records(self):
        app = create_app(data_root=self.root)

        def call(method, path, body=b"{}"):
            status_headers = []
            response = b"".join(app({"REQUEST_METHOD": method, "PATH_INFO": path, "QUERY_STRING": "",
                "CONTENT_TYPE": "application/json", "CONTENT_LENGTH": str(len(body)), "wsgi.input": io.BytesIO(body)},
                lambda status, headers: status_headers.append(status)))
            return status_headers[0], response

        saved = register_upload(self.root, "workspace-a", filename="portrait.png", content=self.png(), role="project_image")
        path = f"/api/media/workspace-a/assets/{saved['asset_id']}/archive"
        status, body = call("POST", path)
        self.assertEqual(status, "200 OK")
        self.assertIn(b'"archived_at"', body)
        status, body = call("POST", path.replace("/archive", "/restore"))
        self.assertEqual(status, "200 OK")
        self.assertNotIn(b'"archived_at"', body)
        status, _ = call("POST", path, b'{"unexpected":true}')
        self.assertEqual(status, "422 Unprocessable Entity")

    def test_archived_video_content_remains_available_for_playback_after_restore(self):
        content = self.mp4()
        saved = register_upload(self.root, "workspace-a", filename="mira.mp4",
            content=content, role="project_video")
        app = create_app(data_root=self.root)

        def call(method, path, body=b""):
            status_headers = []
            response = b"".join(app({"REQUEST_METHOD": method, "PATH_INFO": path, "QUERY_STRING": "",
                "CONTENT_TYPE": "application/json", "CONTENT_LENGTH": str(len(body)), "wsgi.input": io.BytesIO(body)},
                lambda status, headers: status_headers.append((status, headers))))
            return status_headers[0][0], status_headers[0][1], response

        asset_path = f"/api/media/workspace-a/assets/{saved['asset_id']}"
        status, _, _ = call("POST", f"{asset_path}/archive", b"{}")
        self.assertEqual(status, "200 OK")
        self.assertEqual(list_assets(self.root, "workspace-a")["total"], 0)
        status, headers, archived_content = call("GET", f"{asset_path}/content")
        self.assertEqual(status, "200 OK")
        self.assertTrue(any(name.lower() == "content-type" and value.startswith("video/")
            for name, value in headers))
        self.assertEqual(archived_content, content)

        status, _, _ = call("POST", f"{asset_path}/restore", b"{}")
        self.assertEqual(status, "200 OK")
        self.assertEqual(list_assets(self.root, "workspace-a")["assets"][0]["asset_id"], saved["asset_id"])
        status, _, restored_content = call("GET", f"{asset_path}/content")
        self.assertEqual(status, "200 OK")
        self.assertEqual(restored_content, content)

    def test_assign_role_is_idempotent_and_checks_media_kind(self):
        saved = register_upload(self.root, "workspace-a", filename="portrait.png",
            content=self.png(), role="project_image")
        selected = assign_role(self.root, "workspace-a", saved["asset_id"], "character_master")
        replay = assign_role(self.root, "workspace-a", saved["asset_id"], "character_master")
        self.assertEqual(selected["roles"], ["project_image", "character_master"])
        self.assertEqual(replay["roles"], selected["roles"])
        with self.assertRaisesRegex(ValueError, "does not match"):
            assign_role(self.root, "workspace-a", saved["asset_id"], "voice_master")

    def test_upload_route_lists_and_serves_range_from_workspace_library(self):
        app = create_app(data_root=self.root)

        def call(method, path, body=b"", content_type="application/json", headers=None):
            status_headers = []
            path_only, _, query = path.partition("?")
            environ = {"REQUEST_METHOD": method, "PATH_INFO": path_only, "QUERY_STRING": query,
                "CONTENT_TYPE": content_type, "CONTENT_LENGTH": str(len(body)), "wsgi.input": io.BytesIO(body),
                **(headers or {})}
            result = b"".join(app(environ, lambda status, response_headers: status_headers.extend([status, response_headers])))
            return status_headers[0], status_headers[1], result

        body = self.png()
        status, _, result = call("POST", "/api/media/workspace-a/assets?filename=face.png&role=character_master",
            body, "application/octet-stream")
        self.assertEqual(status, "201 Created")
        asset = json.loads(result)
        self.assertTrue(asset["asset_id"].startswith("pa-"))
        status, _, result = call("GET", "/api/media/workspace-a/assets?kind=image")
        self.assertEqual(status, "200 OK")
        self.assertEqual(json.loads(result)["total"], 1)
        status, response_headers, result = call("GET", f"/api/media/workspace-a/assets/{asset['asset_id']}/content",
            headers={"HTTP_RANGE": "bytes=0-7"})
        self.assertEqual(status, "206 Partial Content")
        self.assertIn(("Content-Range", f"bytes 0-7/{len(body)}"), response_headers)
        self.assertEqual(result, body[:8])

    def test_bad_signature_and_foreign_content_are_rejected(self):
        app = create_app(data_root=self.root)
        response = []
        body = b"not png"
        environ = {"REQUEST_METHOD": "POST", "PATH_INFO": "/api/media/workspace-a/assets",
            "QUERY_STRING": "filename=bad.png&role=character_master", "CONTENT_TYPE": "application/octet-stream",
            "CONTENT_LENGTH": str(len(body)), "wsgi.input": io.BytesIO(body)}
        result = b"".join(app(environ, lambda status, headers: response.append(status)))
        self.assertEqual(response[0], "422 Unprocessable Entity")
        self.assertIn(b"signature", result)
        response.clear()
        environ = {"REQUEST_METHOD": "GET", "PATH_INFO": "/api/media/workspace-a/assets/pa-0000000000000000/content",
            "QUERY_STRING": "", "CONTENT_TYPE": "", "CONTENT_LENGTH": "0", "wsgi.input": io.BytesIO()}
        b"".join(app(environ, lambda status, headers: response.append(status)))
        self.assertEqual(response[0], "404 Not Found")

    def test_generated_video_is_indexed_without_copying_its_bytes(self):
        output = self.root / "projects" / "workspace-a" / "media" / "generated" / "take.mp4"
        output.parent.mkdir(parents=True)
        original = self.mp4()
        output.write_bytes(original)
        saved = register_generated_video(self.root, "workspace-a", "take.mp4",
            {"job_id": "job-1", "prompt": "A test shot."})
        self.assertEqual(saved["roles"], ["project_video"])
        self.assertEqual(saved["kind"], "video")
        resolved, _, _ = asset_path(self.root, "workspace-a", saved["asset_id"])
        self.assertEqual(resolved, output.resolve())
        self.assertEqual(resolved.read_bytes(), original)
        self.assertEqual(list_assets(self.root, "workspace-a", kind="video")["assets"][0]["asset_id"], saved["asset_id"])

    def test_generated_audio_derivative_uses_the_shared_catalog_and_rejects_escape(self):
        output = self.root / "projects" / "workspace-a" / "media" / "generated" / "analysis" / "dialogue.wav"
        output.parent.mkdir(parents=True)
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
            "sine=frequency=440:duration=0.1", str(output)], check=True, capture_output=True, timeout=30)
        saved = register_generated_audio(self.root, "workspace-a", "analysis/dialogue.wav",
            {"source_asset_id": "pa-0000000000000001", "start_time_seconds": 2.0})
        self.assertEqual(saved["kind"], "audio")
        self.assertEqual(saved["roles"], ["project_audio"])
        resolved, _, _ = asset_path(self.root, "workspace-a", saved["asset_id"])
        self.assertEqual(resolved, output.resolve())
        self.assertEqual(list_assets(self.root, "workspace-a", kind="audio")["assets"][0]["asset_id"], saved["asset_id"])
        with self.assertRaisesRegex(ValueError, "outside this workspace"):
            register_generated_audio(self.root, "workspace-a", "../escape.wav", {})

    def test_analyzer_derivatives_keep_occurrence_lineage_in_shared_library(self):
        with patch("story_builder.services.media_library._probe", return_value={"width": 2, "height": 3}):
            source = register_upload(self.root, "workspace-a", filename="source.png",
                content=self.png(), role="style_reference")
            output = self.root / "projects" / "workspace-a" / "media" / "generated" / "analysis" / "frame.jpg"
            output.parent.mkdir(parents=True)
            output.write_bytes(b"\xff\xd8\xffframe")
            first = register_derived_media(self.root, "workspace-a", "analysis/frame.jpg",
                source_asset_id=source["asset_id"], source_sha256=source["sha256"],
                derivation_id="job_a_attempt_1", kind="image",
                metadata={"occurrence_id": "scene-1-frame-1", "timestamp_seconds": 1.25, "artifact_type": "selected_frame"})
            second = register_derived_media(self.root, "workspace-a", "analysis/frame.jpg",
                source_asset_id=source["asset_id"], source_sha256=source["sha256"],
                derivation_id="job_a_attempt_1", kind="image",
                metadata={"occurrence_id": "scene-1-frame-2", "timestamp_seconds": 3.5, "artifact_type": "selected_frame"})
            replay = register_derived_media(self.root, "workspace-a", "analysis/frame.jpg",
                source_asset_id=source["asset_id"], source_sha256=source["sha256"],
                derivation_id="job_a_attempt_1", kind="image",
                metadata={"occurrence_id": "scene-1-frame-1", "timestamp_seconds": 1.25, "artifact_type": "selected_frame"})
        self.assertNotEqual(first["asset_id"], second["asset_id"])
        self.assertEqual(first["metadata"]["source_asset_id"], source["asset_id"])
        self.assertEqual(first["metadata"]["timestamp_seconds"], 1.25)
        self.assertEqual(second["metadata"]["timestamp_seconds"], 3.5)
        self.assertEqual(replay["asset_id"], first["asset_id"])
        self.assertTrue(replay["deduplicated"])
        self.assertEqual(list_assets(self.root, "workspace-a", kind="image")["total"], 3)

    def test_analyzer_derivative_rejects_changed_source_and_path_escape(self):
        with patch("story_builder.services.media_library._probe", return_value={"width": 2, "height": 3}):
            source = register_upload(self.root, "workspace-a", filename="source.png",
                content=self.png(), role="style_reference")
            with self.assertRaisesRegex(ValueError, "source asset is missing or changed"):
                register_derived_media(self.root, "workspace-a", "frame.jpg",
                    source_asset_id=source["asset_id"], source_sha256="0" * 64,
                    derivation_id="job_1", kind="image", metadata={})
            with self.assertRaisesRegex(ValueError, "output path is invalid"):
                register_derived_media(self.root, "workspace-a", "../escape.jpg",
                    source_asset_id=source["asset_id"], source_sha256=source["sha256"],
                    derivation_id="job_1", kind="image", metadata={})

    def test_analyzer_derivative_rejects_symlinked_assets_root(self):
        with patch("story_builder.services.media_library._probe", return_value={"width": 2, "height": 3}):
            source = register_upload(self.root, "workspace-a", filename="source.png",
                content=self.png(), role="style_reference")
            external = Path(self.temporary.name) / "external-assets"
            external.mkdir()
            self.root.mkdir(parents=True, exist_ok=True)
            (self.root / "projects" / "workspace-a" / "media" / "generated").symlink_to(external, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "cannot be symlinks"):
                register_derived_media(self.root, "workspace-a", "frame.jpg",
                    source_asset_id=source["asset_id"], source_sha256=source["sha256"],
                    derivation_id="job_1", kind="image", metadata={})

    def test_search_annotations_are_persisted_and_audio_categories_are_validated(self):
        image = register_upload(self.root, "workspace-a", filename="rain.png", content=self.png(), role="project_image")
        saved = update_annotations(self.root, "workspace-a", image["asset_id"],
            description="Rainy courtroom, blue hour", tags=["courtroom", "rain", " rain "], audio_category=None)
        self.assertEqual(saved["description"], "Rainy courtroom, blue hour")
        self.assertEqual(saved["tags"], ["courtroom", "rain"])
        with self.assertRaisesRegex(ValueError, "only to audio"):
            update_annotations(self.root, "workspace-a", image["asset_id"],
                description="", tags=[], audio_category="music")
        with self.assertRaisesRegex(ValueError, "not found"):
            update_annotations(self.root, "other-workspace", image["asset_id"],
                description="", tags=[], audio_category=None)

    def test_audio_category_can_be_cleared_to_leave_content_unclassified(self):
        audio_bytes = io.BytesIO()
        with wave.open(audio_bytes, "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(8000)
            audio.writeframes(b"\x00\x00" * 800)
        asset = register_upload(self.root, "workspace-a", filename="mixed.wav",
            content=audio_bytes.getvalue(), role="project_audio")
        classified = update_annotations(self.root, "workspace-a", asset["asset_id"],
            description="Mixed ambience", tags=[], audio_category="sfx")
        self.assertEqual(classified["audio_category"], "sfx")
        cleared = update_annotations(self.root, "workspace-a", asset["asset_id"],
            description="Mixed ambience", tags=[], audio_category=None)
        self.assertNotIn("audio_category", cleared)

    def test_structured_image_analysis_is_saved_with_source_provenance_and_search_terms(self):
        image = register_upload(self.root, "workspace-a", filename="detail.png", content=self.png(), role="project_image")
        structured = {"analysis": {"summary": "A rainy street", "subjects": ["woman"]}, "frame_card": {"camera": "wide"}}
        saved = save_image_analysis(self.root, "workspace-a", image["asset_id"],
            job_id="12345678-1234-1234-1234-123456789abc", source_sha256=image["sha256"],
            mode="balanced", analysis=structured, description="A rainy street", tags=["rain", "street"])
        row = saved["metadata"]["image_analyses"][0]
        self.assertEqual(row["analysis"], structured)
        self.assertEqual(row["source_sha256"], image["sha256"])
        self.assertEqual(saved["description"], "A rainy street")
        self.assertEqual(saved["tags"], ["rain", "street"])
        replay = save_image_analysis(self.root, "workspace-a", image["asset_id"],
            job_id="12345678-1234-1234-1234-123456789abc", source_sha256=image["sha256"],
            mode="balanced", analysis=structured, description="A rainy street", tags=["rain", "street"])
        self.assertEqual(len(replay["metadata"]["image_analyses"]), 1)
        self.assertNotIn("content", replay)
        with self.assertRaisesRegex(ValueError, "different source"):
            save_image_analysis(self.root, "workspace-a", image["asset_id"],
                job_id="12345678-1234-1234-1234-123456789abd", source_sha256="0" * 64,
                mode="balanced", analysis=structured, description="", tags=[])

    def test_style_reference_links_are_versioned_and_reject_other_roles_or_workspaces(self):
        image = register_upload(self.root, "workspace-a", filename="look.png", content=self.png(), role="style_reference")
        linked = link_style_reference(self.root, "workspace-a", image["asset_id"], "story_film-v1")
        self.assertEqual(linked["metadata"]["style_version_ids"], ["story_film-v1"])
        linked = link_style_reference(self.root, "workspace-a", image["asset_id"], "story_film-v2")
        self.assertEqual(linked["metadata"]["style_version_ids"], ["story_film-v1", "story_film-v2"])
        with self.assertRaisesRegex(ValueError, "not found"):
            link_style_reference(self.root, "workspace-b", image["asset_id"], "story_film-v1")
        project_image = register_upload(self.root, "workspace-a", filename="project.png", content=self.png((0, 0, 255)), role="project_image")
        with self.assertRaisesRegex(ValueError, "Only assets uploaded as style references"):
            link_style_reference(self.root, "workspace-a", project_image["asset_id"], "story_film-v1")

    def test_directing_style_references_do_not_leak_between_styles_and_legacy_links_survive(self):
        image = register_upload(self.root, "setup-a", filename="horror.png", content=self.png(), role="style_reference")
        link_style_reference(self.root, "setup-a", image["asset_id"], directing_style_id="horror")
        legacy_image = register_upload(self.root, "setup-a", filename="legacy.png", content=self.png((0, 255, 0)), role="style_reference")
        link_style_reference(self.root, "setup-a", legacy_image["asset_id"], "base:story_film:v1")
        horror = {"isolated_context_id": "setup-a", "snapshot_id": "a" * 32, "style_version_id": "base:story_film:v1",
            "directing_style": {"style_id": "horror"}}
        romance = {"isolated_context_id": "setup-a", "snapshot_id": "a" * 32, "style_version_id": "base:story_film:v1",
            "directing_style": {"style_id": "romance"}}
        # Setup references live in the source setup context and are recommended
        # to a story through the pinned selection without copying the bytes.
        story_row = register_upload(self.root, "workspace-a", filename="local.png", content=self.png((0,0,255)), role="project_image")
        selected_rows = list_assets(self.root, "workspace-a", style_selection=horror)
        recommendations = {item["asset_id"]: item for item in selected_rows["assets"] if item.get("recommended")}
        self.assertEqual(set(recommendations), {image["asset_id"], legacy_image["asset_id"]})
        self.assertEqual(recommendations[image["asset_id"]]["metadata"]["directing_style_ids"], ["horror"])
        romance_rows = list_assets(self.root, "workspace-a", style_selection=romance)["assets"]
        romance_recommendations = {item["asset_id"] for item in romance_rows if item.get("recommended")}
        self.assertEqual(romance_recommendations, {legacy_image["asset_id"]})
        self.assertEqual([item["asset_id"] for item in romance_rows if not item.get("recommended")], [story_row["asset_id"]])
        set_asset_archived(self.root, "setup-a", image["asset_id"], archived=True)
        archived_rows = list_assets(self.root, "workspace-a", style_selection=horror)["assets"]
        self.assertNotIn(image["asset_id"], {item["asset_id"] for item in archived_rows})
        # Existing pinned references remain resolvable from the original file.
        self.assertTrue(asset_path(self.root, "setup-a", image["asset_id"])[0].is_file())
        # Old references have no recoverable directing-style identity and use
        # the historical type-version match until the owner reassigns them.

    def test_style_reference_route_requires_saved_style_and_keeps_links_workspace_scoped(self):
        app = create_app(data_root=self.root)
        def call(method, path, payload=None, body=None, content_type="application/json"):
            data = body if body is not None else (json.dumps(payload).encode() if payload is not None else b"")
            response = []
            path_only, _, query = path.partition("?")
            environ = {"REQUEST_METHOD": method, "PATH_INFO": path_only, "QUERY_STRING": query,
                "CONTENT_TYPE": content_type, "CONTENT_LENGTH": str(len(data)), "wsgi.input": io.BytesIO(data)}
            result = b"".join(app(environ, lambda status, headers: response.extend([status, headers])))
            return response[0], json.loads(result)
        _, catalog = call("GET", "/api/styles/catalog")
        style = catalog["production_types"][0]
        direction = catalog["directing_styles"][0]
        context = "setup-style-ref-test"
        status, _ = call("POST", "/api/styles/selections", {
            "isolated_context_id": context, "production_type": style["production_type"],
            "style_version_id": style["style_version_id"], "directing_style_id": direction["style_id"]})
        self.assertEqual(status, "201 Created")
        status, uploaded = call("POST", f"/api/media/{context}/assets?filename=look.png&role=style_reference",
            body=self.png(), content_type="application/octet-stream")
        self.assertEqual(status, "201 Created")
        status, listed = call("GET", f"/api/media/{context}/assets?kind=image")
        self.assertEqual(status, "200 OK")
        self.assertEqual([row["asset_id"] for row in listed["assets"]], [uploaded["asset_id"]])
        status, linked = call("POST", f"/api/media/{context}/assets/{uploaded['asset_id']}/style-reference",
            {"directing_style_id": direction["style_id"]})
        self.assertEqual(status, "200 OK")
        self.assertEqual(linked["metadata"]["directing_style_ids"], [direction["style_id"]])
        unselected_style = catalog["directing_styles"][1]
        status, error = call("POST", f"/api/media/{context}/assets/{uploaded['asset_id']}/style-reference",
            {"directing_style_id": unselected_style["style_id"]})
        self.assertEqual(status, "422 Unprocessable Entity")
        self.assertIn("Save this directing style", error["error"]["message"])
        other = "setup-other-style-ref-test"
        status, _ = call("POST", "/api/styles/selections", {
            "isolated_context_id": other, "production_type": style["production_type"],
            "style_version_id": style["style_version_id"], "directing_style_id": direction["style_id"]})
        self.assertEqual(status, "201 Created")
        status, error = call("POST", f"/api/media/{other}/assets/{uploaded['asset_id']}/style-reference",
            {"directing_style_id": direction["style_id"]})
        self.assertEqual(status, "422 Unprocessable Entity")
        self.assertIn("Asset was not found", error["error"]["message"])
        status, uploaded_video = call("POST", f"/api/media/{context}/assets?filename=style.mp4&role=style_reference",
            body=self.mp4(), content_type="application/octet-stream")
        self.assertEqual(status, "201 Created")
        with patch("story_builder.isolated_server.video_repertoire.start_job",
                side_effect=lambda kind, job_id: video_repertoire.read_job(kind, job_id)):
            status, queued = call("POST", f"/api/media/{context}/assets/{uploaded_video['asset_id']}/style-frames",
                {"directing_style_id": direction["style_id"], "timestamps_seconds": [0.5]})
        self.assertEqual(status, "202 Accepted")
        self.assertEqual(queued["kind"], "style-frames")
        self.assertEqual(queued["request"]["timestamps_seconds"], [0.5])
        status, listed_jobs = call("GET", f"/api/media/{context}/style-frame-jobs")
        self.assertEqual(status, "200 OK")
        self.assertEqual([job["job_id"] for job in listed_jobs], [queued["job_id"]])
        status, cancelled = call("POST", f"/api/media/{context}/style-frame-jobs/{queued['job_id']}/cancel", {})
        self.assertEqual(status, "200 OK")
        self.assertEqual(cancelled["status"], "cancelled")
        status, foreign_jobs = call("GET", f"/api/media/{other}/style-frame-jobs/{queued['job_id']}")
        self.assertEqual(status, "404 Not Found")

    def test_custom_directing_style_endpoint_binds_evidence_to_setup_assets_and_pins_version(self):
        app = create_app(data_root=self.root)
        def call(method, path, payload=None, body=None, content_type="application/json"):
            data = body if body is not None else (json.dumps(payload).encode() if payload is not None else b"")
            response=[]
            path_only,_,query=path.partition("?")
            environ={"REQUEST_METHOD":method,"PATH_INFO":path_only,"QUERY_STRING":query,
                "CONTENT_TYPE":content_type,"CONTENT_LENGTH":str(len(data)),"wsgi.input":io.BytesIO(data)}
            result=b"".join(app(environ,lambda status,headers:response.extend([status,headers])))
            return response[0],json.loads(result)
        context="setup-custom-direction"
        status,asset=call("POST",f"/api/media/{context}/assets?filename=look.png&role=style_reference",
            body=self.png(),content_type="application/octet-stream")
        self.assertEqual(status,"201 Created")
        payload={"style_id":"neo_noir","display_name":"Neo-noir","guidance":"Use motivated shadows.",
            "isolated_context_id":context,"evidence":[{"asset_id":asset["asset_id"],"kind":"image",
                "sha256":asset["sha256"],"intent":"Lighting and contrast"}]}
        status,published=call("POST","/api/styles/directing-styles",payload)
        self.assertEqual(status,"201 Created")
        style_catalog=call("GET","/api/styles/catalog")[1]["directing_styles"]
        self.assertEqual(next(item for item in style_catalog if item["style_id"]=="neo_noir")["style_version_id"],published["style_version_id"])
        status,selection=call("POST","/api/styles/selections",{
            "isolated_context_id":context,"production_type":"story_film",
            "style_version_id":"base:story_film:v1","directing_style_id":"neo_noir",
            "directing_style_version_id":published["style_version_id"]})
        self.assertEqual(status,"201 Created")
        self.assertEqual(selection["directing_style"]["evidence"][0]["asset_id"],asset["asset_id"])
        bad={**payload,"style_id":"bad_reference","evidence":[{**payload["evidence"][0],"asset_id":"pa-0000000000000000"}]}
        status,error=call("POST","/api/styles/directing-styles",bad)
        self.assertEqual(status,"422 Unprocessable Entity")
        self.assertIn("belong to this setup library",error["error"]["message"])
        status,ordinary=call("POST",f"/api/media/{context}/assets?filename=ordinary.png&role=project_image",
            body=self.png()+b"ordinary",content_type="application/octet-stream")
        self.assertEqual(status,"201 Created")
        self.assertNotIn("style_reference",ordinary["roles"])
        bad_role={**payload,"style_id":"ordinary_media","evidence":[{"asset_id":ordinary["asset_id"],"kind":"image",
            "sha256":ordinary["sha256"],"intent":"Should not pass as style evidence"}]}
        status,error=call("POST","/api/styles/directing-styles",bad_role)
        self.assertEqual(status,"422 Unprocessable Entity")
        self.assertIn("uploaded as reference media",error["error"]["message"])

    def test_story_media_view_uses_only_pinned_setup_references_without_copying(self):
        app = create_app(data_root=self.root)
        def call(method, path, payload=None, body=None, content_type="application/json"):
            data = body if body is not None else (json.dumps(payload).encode() if payload is not None else b"")
            response = []
            path_only, _, query = path.partition("?")
            environ = {"REQUEST_METHOD": method, "PATH_INFO": path_only, "QUERY_STRING": query,
                "CONTENT_TYPE": content_type, "CONTENT_LENGTH": str(len(data)), "wsgi.input": io.BytesIO(data)}
            result = b"".join(app(environ, lambda status, headers: response.extend([status, headers])))
            return response[0], response[1] if len(response) > 1 else [], result

        status, _, catalog_raw = call("GET", "/api/styles/catalog")
        self.assertEqual(status, "200 OK")
        style = json.loads(catalog_raw)["production_types"][0]
        direction = json.loads(catalog_raw)["directing_styles"][0]
        contexts = ("setup-pinned-style", "setup-same-style")
        assets = []
        snapshots = []
        for index, context in enumerate(contexts):
            status, _, saved_raw = call("POST", "/api/styles/selections", {
                "isolated_context_id": context, "production_type": style["production_type"],
                "style_version_id": style["style_version_id"], "directing_style_id": direction["style_id"]})
            self.assertEqual(status, "201 Created")
            snapshots.append(json.loads(saved_raw)["snapshot_id"])
            color = (0, 0, 255) if index else (255, 0, 0)
            status, _, uploaded_raw = call("POST", f"/api/media/{context}/assets?filename=look.png&role=style_reference",
                body=self.png(color), content_type="application/octet-stream")
            self.assertEqual(status, "201 Created")
            uploaded = json.loads(uploaded_raw)
            assets.append(uploaded)
            status, _, _ = call("POST", f"/api/media/{context}/assets/{uploaded['asset_id']}/style-reference",
                {"directing_style_id": direction["style_id"]})
            self.assertEqual(status, "200 OK")

        status, _, story_raw = call("POST", "/api/story/workspaces", {
            "idempotency_key": "00000000-0000-4000-8000-000000000001", "title": "Pinned Style Story",
            "source_text": "A short test story.", "style_selection_snapshot_id": snapshots[0]})
        self.assertEqual(status, "201 Created")
        story = json.loads(story_raw)
        workspace_id = story["workspace"]["workspace_id"]
        status, _, listed_raw = call("GET", f"/api/media/{workspace_id}/assets?kind=image")
        self.assertEqual(status, "200 OK")
        listed = json.loads(listed_raw)
        self.assertEqual([row["asset_id"] for row in listed["assets"]], [assets[0]["asset_id"]])
        self.assertTrue(listed["assets"][0]["recommended"])
        self.assertEqual(listed["assets"][0]["source_workspace_id"], contexts[0])
        self.assertEqual(listed["assets"][0]["content_url"],
            f"/api/media/{workspace_id}/assets/{assets[0]['asset_id']}/content")
        status, headers, content = call("GET", listed["assets"][0]["content_url"])
        self.assertEqual(status, "200 OK")
        self.assertTrue(any(name.lower() == "content-type" and value.startswith("image/") for name, value in headers))
        self.assertEqual(content, self.png((255, 0, 0)))
        story_manifest = self.root / "projects" / workspace_id / "production" / "assets.json"
        self.assertFalse(story_manifest.exists(), "Recommendations must not create Story-owned asset aliases.")
        status, _, unpinned_raw = call("POST", "/api/story/workspaces", {
            "idempotency_key": "00000000-0000-4000-8000-000000000002", "title": "Unpinned Story",
            "source_text": "Another test story."})
        self.assertEqual(status, "201 Created")
        unpinned = json.loads(unpinned_raw)["workspace"]["workspace_id"]
        status, _, empty_raw = call("GET", f"/api/media/{unpinned}/assets")
        self.assertEqual(status, "200 OK")
        self.assertEqual(json.loads(empty_raw)["assets"], [])
        status, _, foreign_raw = call("GET", f"/api/media/{unpinned}/assets/{assets[0]['asset_id']}/content")
        self.assertEqual(status, "404 Not Found")

    def test_video_workspace_can_list_recommendations_from_saved_style_context(self):
        app = create_app(data_root=self.root)
        def call(method, path, payload=None, body=None, content_type="application/json"):
            data = body if body is not None else (json.dumps(payload).encode() if payload is not None else b"")
            response = []
            path_only, _, query = path.partition("?")
            environ = {"REQUEST_METHOD": method, "PATH_INFO": path_only, "QUERY_STRING": query,
                "CONTENT_TYPE": content_type, "CONTENT_LENGTH": str(len(data)), "wsgi.input": io.BytesIO(data)}
            result = b"".join(app(environ, lambda status, headers: response.extend([status, headers])))
            return response[0], json.loads(result)

        setup_context = "setup-12345678-1234-1234-1234-123456789abc"
        _, catalog = call("GET", "/api/styles/catalog")
        style = catalog["production_types"][0]
        direction = catalog["directing_styles"][0]
        status, _ = call("POST", "/api/styles/selections", {"isolated_context_id": setup_context,
            "production_type": style["production_type"], "style_version_id": style["style_version_id"],
            "directing_style_id": direction["style_id"]})
        self.assertEqual(status, "201 Created")
        status, uploaded = call("POST", f"/api/media/{setup_context}/assets?filename=pinned.png&role=style_reference",
            body=self.png(), content_type="application/octet-stream")
        self.assertEqual(status, "201 Created")
        status, linked = call("POST", f"/api/media/{setup_context}/assets/{uploaded['asset_id']}/style-reference",
            {"directing_style_id": direction["style_id"]})
        self.assertEqual(status, "200 OK")
        status, listing = call("GET", f"/api/media/r2v-workspace/assets?kind=image&style_context_id={setup_context}")
        self.assertEqual(status, "200 OK")
        self.assertEqual([asset["asset_id"] for asset in listing["assets"]], [uploaded["asset_id"]])
        self.assertTrue(listing["assets"][0]["recommended"])
        self.assertEqual(listing["assets"][0]["source_workspace_id"], setup_context)

    def test_style_video_exports_only_selected_timestamp_frames(self):
        video = register_upload(self.root, "workspace-a", filename="look.mp4", content=self.mp4(), role="style_reference")
        link_style_reference(self.root, "workspace-a", video["asset_id"], "story_film-v1")
        progress = []
        frames = extract_style_reference_frames(self.root, "workspace-a", video["asset_id"], "story_film-v1", [0.2, 1.2], progress=lambda done, total: progress.append((done, total)))
        self.assertEqual(len(frames), 2)
        self.assertEqual(progress, [(1, 2), (2, 2)])
        self.assertEqual([frame["metadata"]["style_frame_sources"][0]["timestamp_seconds"] for frame in frames], [0.2, 1.2])
        self.assertEqual((frames[0]["metadata"]["style_frame_sources"][0]["source_width"],
            frames[0]["metadata"]["style_frame_sources"][0]["source_height"]), (128, 72))
        self.assertEqual(frames[0]["metadata"]["style_frame_sources"][0]["extraction"],
            {"method": "ffmpeg-single-frame-jpeg-v1", "max_width": 1920, "quality": 2})
        self.assertTrue(all(frame["metadata"]["style_version_ids"] == ["story_film-v1"] for frame in frames))
        self.assertEqual(extract_style_reference_frames(self.root, "workspace-a", video["asset_id"], "story_film-v1", []), [])
        self.assertEqual(list_assets(self.root, "workspace-a", kind="image")["total"], 2)
        with self.assertRaisesRegex(ValueError, "inside the video duration"):
            extract_style_reference_frames(self.root, "workspace-a", video["asset_id"], "story_film-v1", [2.0])

    def test_annotation_route_saves_searchable_metadata(self):
        app = create_app(data_root=self.root)
        def call(method, path, body=b"", content_type="application/json"):
            headers = []
            path_only, _, query = path.partition("?")
            environ = {"REQUEST_METHOD": method, "PATH_INFO": path_only, "QUERY_STRING": query,
                "CONTENT_TYPE": content_type, "CONTENT_LENGTH": str(len(body)), "wsgi.input": io.BytesIO(body)}
            data = b"".join(app(environ, lambda status, response_headers: headers.extend([status, response_headers])))
            return headers, data
        status, data = call("POST", "/api/media/workspace-a/assets?filename=rain.png&role=project_image", self.png(), "application/octet-stream")
        self.assertEqual(status[0], "201 Created")
        asset_id = json.loads(data)["asset_id"]
        payload = json.dumps({"description":"Rainy courtroom", "tags":["courtroom", "rain"], "audio_category":None}).encode()
        status, data = call("PATCH", f"/api/media/workspace-a/assets/{asset_id}/annotations", payload)
        self.assertEqual(status[0], "200 OK")
        self.assertEqual(json.loads(data)["tags"], ["courtroom", "rain"])
        for invalid_category in ([], {}, 42, True):
            invalid_payload = json.dumps({"description":"changed", "tags":[], "audio_category":invalid_category}).encode()
            status, data = call("PATCH", f"/api/media/workspace-a/assets/{asset_id}/annotations", invalid_payload)
            self.assertEqual(status[0], "422 Unprocessable Entity")
            self.assertIn("Audio category", json.loads(data)["error"]["message"])
        self.assertEqual(list_assets(self.root, "workspace-a")["assets"][0]["description"], "Rainy courtroom")

    def test_seo_styles_are_workspace_scoped_validated_and_editable_over_api(self):
        app = create_app(data_root=self.root)
        def call(method, path, payload=None):
            body = json.dumps(payload).encode() if payload is not None else b""
            response = []
            environ = {"REQUEST_METHOD": method, "PATH_INFO": path, "QUERY_STRING": "",
                "CONTENT_TYPE": "application/json", "CONTENT_LENGTH": str(len(body)), "wsgi.input": io.BytesIO(body)}
            result = b"".join(app(environ, lambda status, headers: response.extend([status, headers])))
            return response[0], json.loads(result)

        payload = {"name": "Rain noir", "weighted_terms": {"rain": 2, "blue hour": 1.5}, "avoid_terms": ["cartoon"]}
        status, saved = call("POST", "/api/media/workspace-a/assets/seo-styles", payload)
        self.assertEqual(status, "201 Created")
        self.assertEqual(saved["weighted_terms"][0], {"term": "rain", "weight": 2.0})
        self.assertEqual(call("GET", "/api/media/workspace-a/assets/seo-styles")[1]["styles"], [saved])
        status, updated = call("PUT", f"/api/media/workspace-a/assets/seo-styles/{saved['style_id']}",
            {**payload, "name": "Rainy noir"})
        self.assertEqual((status, updated["name"]), ("200 OK", "Rainy noir"))
        self.assertEqual(call("GET", "/api/media/other-workspace/assets/seo-styles")[1]["styles"], [])
        status, error = call("POST", "/api/media/workspace-a/assets/seo-styles", {**payload, "weighted_terms": {}})
        self.assertEqual(status, "422 Unprocessable Entity")
        self.assertIn("weighted search terms", error["error"]["message"])
        status, result = call("DELETE", f"/api/media/workspace-a/assets/seo-styles/{saved['style_id']}")
        self.assertEqual((status, result["deleted"]), ("200 OK", True))
        self.assertEqual(list_seo_styles(self.root, "workspace-a"), [])


if __name__ == "__main__":
    unittest.main()
