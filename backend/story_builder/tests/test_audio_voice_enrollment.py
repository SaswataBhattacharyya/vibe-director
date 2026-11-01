from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from story_builder.isolated_server import create_app
from story_builder.services import audio_catalog
from story_builder.services.media_library import list_assets, register_upload


class AudioVoiceEnrollmentTests(unittest.TestCase):
    def test_catalog_skips_voice_symlink_escaping_configured_root(self):
        with tempfile.TemporaryDirectory() as temporary, tempfile.TemporaryDirectory() as outside:
            comfy_root = Path(temporary) / "ComfyUI"
            voices_root = comfy_root / "models" / "voices"
            voices_root.mkdir(parents=True)
            outside_voice = Path(outside) / "secret.wav"
            outside_voice.write_bytes(b"not served")
            (voices_root / "alias.wav").symlink_to(outside_voice)
            with patch.dict(os.environ, {"COMFYUI_ROOT": str(comfy_root), "TTS_AUDIO_SUITE_ROOT": str(comfy_root / "suite")}):
                self.assertEqual(audio_catalog.discover_voices(), [])

    def test_comfy_voice_catalog_exposes_safe_preview_route_without_file_paths(self):
        with tempfile.TemporaryDirectory() as temporary:
            audio_path = Path(temporary) / "Narrator.wav"
            wav = io.BytesIO()
            with wave.open(wav, "wb") as audio:
                audio.setnchannels(1); audio.setsampwidth(2); audio.setframerate(8000)
                audio.writeframes(b"\0\0" * 80)
            audio_path.write_bytes(wav.getvalue())
            voice = {"id": "user:Narrator.wav", "name": "Narrator", "source": "user",
                "relative_path": "Narrator.wav", "audio_path": str(audio_path), "has_transcript": True,
                "discoverable": True, "user_managed": True}
            app = create_app(data_root=Path(temporary) / "data")
            listing = []
            environ = {"REQUEST_METHOD": "GET", "PATH_INFO": "/api/audio/voices", "QUERY_STRING": ""}
            with patch("story_builder.isolated_server.audio_catalog.discover_voices", return_value=[voice]):
                body = b"".join(app(environ, lambda status, headers: listing.extend([status, headers])))
            self.assertEqual(listing[0], "200 OK")
            public = json.loads(body)[0]
            self.assertNotIn("audio_path", public)
            self.assertNotIn("transcript_path", public)
            self.assertEqual(public["content_url"], "/api/audio/voices/content?id=user%3ANarrator.wav")
            self.assertEqual(public["size_bytes"], len(wav.getvalue()))

            response = []
            environ = {"REQUEST_METHOD": "GET", "PATH_INFO": "/api/audio/voices/content",
                "QUERY_STRING": "id=user%3ANarrator.wav"}
            with patch("story_builder.isolated_server.audio_catalog.voice_audio_path",
                       return_value=(audio_path, "Narrator")):
                content = b"".join(app(environ, lambda status, headers: response.extend([status, headers])))
            self.assertEqual(response[0], "200 OK")
            self.assertIn(("Content-Type", "audio/x-wav"), response[1])
            self.assertEqual(content, wav.getvalue())

    def test_comfy_voice_preview_rejects_unknown_catalog_id(self):
        with tempfile.TemporaryDirectory() as temporary:
            app = create_app(data_root=Path(temporary))
            response = []
            environ = {"REQUEST_METHOD": "GET", "PATH_INFO": "/api/audio/voices/content",
                "QUERY_STRING": "id=../../etc/passwd"}
            with patch("story_builder.isolated_server.audio_catalog.voice_audio_path", side_effect=FileNotFoundError):
                body = b"".join(app(environ, lambda status, headers: response.extend([status, headers])))
            self.assertEqual(response[0], "404 Not Found")
            self.assertEqual(json.loads(body)["error"]["code"], "voice_not_found")

    def test_importing_comfy_voice_copies_it_into_workspace_without_changing_original(self):
        with tempfile.TemporaryDirectory() as temporary:
            data_root = Path(temporary) / "data"
            source_path = Path(temporary) / "ComfyUI" / "models" / "voices" / "Narrator.wav"
            source_path.parent.mkdir(parents=True)
            wav = io.BytesIO()
            with wave.open(wav, "wb") as audio:
                audio.setnchannels(1); audio.setsampwidth(2); audio.setframerate(8000)
                audio.writeframes(b"\0\0" * 80)
            source_path.write_bytes(wav.getvalue())
            original = source_path.read_bytes()
            app = create_app(data_root=data_root)
            response = []
            body = json.dumps({"voice_id": "user:Narrator.wav"}).encode()
            environ = {"REQUEST_METHOD": "POST", "PATH_INFO": "/api/audio/workspace-a/voice-library/import",
                "QUERY_STRING": "", "CONTENT_TYPE": "application/json", "CONTENT_LENGTH": str(len(body)),
                "wsgi.input": io.BytesIO(body)}
            with patch("story_builder.isolated_server.audio_catalog.voice_audio_path",
                       return_value=(source_path, "Narrator")):
                content = b"".join(app(environ, lambda status, headers: response.extend([status, headers])))

            self.assertEqual(response[0], "201 Created")
            payload = json.loads(content)
            asset = payload["asset"]
            self.assertIn("voice_master", asset["roles"])
            self.assertEqual(asset["metadata"]["comfyui_voice_catalog"],
                {"catalog_id": "user:Narrator.wav", "name": "Narrator"})
            self.assertNotIn(str(source_path), json.dumps(asset))
            stored = list_assets(data_root, "workspace-a", kind="audio")["assets"]
            self.assertEqual(len(stored), 1)
            self.assertEqual(Path(source_path).read_bytes(), original)

    def test_import_rejects_unknown_comfy_voice_id(self):
        with tempfile.TemporaryDirectory() as temporary:
            app = create_app(data_root=Path(temporary))
            response = []
            body = json.dumps({"voice_id": "../../etc/passwd"}).encode()
            environ = {"REQUEST_METHOD": "POST", "PATH_INFO": "/api/audio/workspace-a/voice-library/import",
                "QUERY_STRING": "", "CONTENT_TYPE": "application/json", "CONTENT_LENGTH": str(len(body)),
                "wsgi.input": io.BytesIO(body)}
            with patch("story_builder.isolated_server.audio_catalog.voice_audio_path", side_effect=FileNotFoundError):
                content = b"".join(app(environ, lambda status, headers: response.extend([status, headers])))
            self.assertEqual(response[0], "404 Not Found")
            self.assertEqual(json.loads(content)["error"]["code"], "voice_not_found")

    def test_live_voice_refresh_calls_comfyui_catalog_and_returns_counts(self):
        with tempfile.TemporaryDirectory() as temporary:
            app = create_app(data_root=Path(temporary))
            response = []
            body = json.dumps({"expected_voice_id": None}).encode()
            environ = {"REQUEST_METHOD": "POST", "PATH_INFO": "/api/audio/voices/refresh",
                "QUERY_STRING": "", "CONTENT_TYPE": "application/json",
                "CONTENT_LENGTH": str(len(body)), "wsgi.input": io.BytesIO(body)}
            refreshed = {"refreshed": True, "live_count": 2, "catalog_count": 2,
                "discovered_voice_ids": ["user:Alice.wav"], "restart_required": False}
            with patch("story_builder.isolated_server.audio_catalog.refresh_live_voice_catalog",
                       return_value=refreshed) as refresh:
                content = b"".join(app(environ, lambda status, headers: response.extend([status, headers])))

            self.assertEqual(response[0], "200 OK")
            self.assertEqual(json.loads(content), refreshed)
            refresh.assert_called_once_with(comfy_url="http://127.0.0.1:3008", expected_voice_id=None)

    def test_enrolled_audio_stays_in_shared_library_as_voice_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            data_root = Path(temporary)
            wav = io.BytesIO()
            with wave.open(wav, "wb") as audio:
                audio.setnchannels(1)
                audio.setsampwidth(2)
                audio.setframerate(8000)
                audio.writeframes(b"\0\0" * 80)
            asset = register_upload(data_root, "workspace-a", filename="speaker.wav",
                content=wav.getvalue(), role="project_audio")
            app = create_app(data_root=data_root)
            installed = {"audio_path": "/comfy/models/voices/Speaker.wav", "restart_required": False}
            catalog_voice = {"id": "user:Speaker.wav", "name": "Speaker", "source": "user",
                "relative_path": "Speaker.wav", "audio_path": installed["audio_path"],
                "has_transcript": True, "discoverable": True, "user_managed": True}
            response = []
            body = json.dumps({"asset_id": asset["asset_id"], "name": "Speaker",
                "transcript": "A clear test sentence."}).encode()
            environ = {"REQUEST_METHOD": "POST", "PATH_INFO": "/api/audio/workspace-a/voices",
                "QUERY_STRING": "", "CONTENT_TYPE": "application/json",
                "CONTENT_LENGTH": str(len(body)), "wsgi.input": io.BytesIO(body)}
            with patch("story_builder.isolated_server.audio_catalog.install_reference_voice", return_value=installed), \
                 patch("story_builder.isolated_server.audio_catalog.discover_voices", return_value=[catalog_voice]), \
                 patch("story_builder.isolated_server.audio_catalog.refresh_live_voice_catalog",
                       return_value={"refreshed": True, "restart_required": False}):
                content = b"".join(app(environ, lambda status, headers: response.extend([status, headers])))

            self.assertEqual(response[0], "201 Created")
            payload = json.loads(content)
            self.assertIn("voice_master", payload["asset"]["roles"])
            listed = list_assets(data_root, "workspace-a", kind="audio")["assets"]
            saved = next(row for row in listed if row["asset_id"] == asset["asset_id"])
            self.assertIn("voice_master", saved["roles"])


if __name__ == "__main__":
    unittest.main()
