from __future__ import annotations

import io
import hashlib
import json
import subprocess
import tempfile
import unittest
import wave
from contextlib import contextmanager, nullcontext
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

from story_builder.isolated_server import create_app
from story_builder.services.media_library import (asset_path, list_assets, register_upload, save_semantic_annotation_index,
    semantic_annotation_text, update_annotations)
from story_builder.services import video_repertoire
from story_builder.services import media_semantic_search
from story_builder.services import sam_audio_vibe
from story_builder.services.media_jobs import MediaJobError
from story_builder.services.gpu_runtime import GPUAdmissionError


class VideoRepertoireVibeAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.data = self.base / "data"
        self.analyzer = self.base / "donor" / "video_audio_analyzer"
        self.analyzer.mkdir(parents=True)
        self.source_file = self.base / "sample.mp4"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
            "-i", "color=c=black:s=32x32:d=0.2", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            str(self.source_file)], check=True, capture_output=True, timeout=30)
        self.source = register_upload(self.data, "workspace-a", filename="sample.mp4",
            content=self.source_file.read_bytes(), role="project_video")
        video_repertoire.configure_roots(self.data, self.analyzer)

    def tearDown(self):
        video_repertoire.configure_roots(Path(self.temp.name) / "reset")

    def request(self, app, method, path, payload=None, query_string=""):
        response = []
        body = json.dumps(payload).encode() if payload is not None else b""
        environ = {"REQUEST_METHOD": method, "PATH_INFO": path, "QUERY_STRING": query_string,
            "CONTENT_TYPE": "application/json" if payload is not None else "",
            "CONTENT_LENGTH": str(len(body)), "wsgi.input": io.BytesIO(body)}
        content = b"".join(app(environ, lambda status, headers: response.extend([status, headers])))
        return response[0], json.loads(content) if content else None

    def test_delete_analysis_preserves_source_and_rejects_active_or_other_workspace(self):
        app = create_app(data_root=self.data)
        job = video_repertoire.create_job("analysis", {"workspace_id":"workspace-a", "asset_ids":[], "source_asset_ids":[self.source["asset_id"]]})
        job_id = job["job_id"]
        path = f"/api/video-summariser/workspace-a/analysis/jobs/{job_id}"
        self.assertEqual(self.request(app,"DELETE",path)[0],"409 Conflict")
        self.assertEqual(self.request(app,"DELETE",path.replace("workspace-a","workspace-b"))[0],"404 Not Found")
        run_id = "owned-run"
        run_dir = video_repertoire.analyzer_runs_root()/run_id
        run_dir.mkdir(parents=True); (run_dir/"manifest.json").write_text("{}")
        (run_dir/"job_owner.json").write_text(json.dumps({"job_id":job_id}))
        output = self.data/"projects"/"workspace-a"/"media"/"generated"/"analysis"/f"{job_id}_{run_id}"
        output.mkdir(parents=True); (output/"unregistered.wav").write_bytes(b"partial")
        job.update(status="completed",result={"audio_analysis":[{"run_id":run_id}]})
        video_repertoire._atomic_json(video_repertoire.job_path("analysis",job_id),job)
        self.assertEqual(self.request(app,"DELETE",path)[0],"200 OK")
        self.assertFalse(run_dir.exists()); self.assertFalse(output.exists())
        self.assertTrue(asset_path(self.data,"workspace-a",self.source["asset_id"])[0].is_file())
        self.assertEqual(self.request(app,"GET",path)[0],"404 Not Found")

    def staged_donor_video(self, asset_id="video-a1b2c3d4e5f6"):
        root = self.base / "staged-video-repertoire"
        media = root / "youtube_code" / "out_videos" / "donor.mp4"
        manifests = root / "manifests"
        media.parent.mkdir(parents=True, exist_ok=True)
        manifests.mkdir(parents=True, exist_ok=True)
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
            "-i", "color=c=blue:s=32x32:d=0.3", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            str(media)], check=True, capture_output=True, timeout=30)
        manifest = {"asset_id": asset_id, "path": str(media), "filename": media.name,
            "title": "Donor clip", "channel": "Test channel", "created_at": "2026-10-11T00:00:00Z",
            "sha256": video_repertoire.sha256_file(media), "source_mode": "youtube",
            "source_url": "https://youtube.com/watch?v=example"}
        (manifests / f"{asset_id}.json").write_text(json.dumps(manifest), encoding="utf-8")
        return root, media, asset_id

    def upload_test_image(self):
        image_path = self.base / "sample.png"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i",
            str(self.source_file), "-frames:v", "1", str(image_path)],
            check=True, capture_output=True, timeout=30)
        return register_upload(self.data, "workspace-a", filename=image_path.name,
            content=image_path.read_bytes(), role="project_image")

    def test_analysis_job_cleanup_stops_vibe_and_legacy_labeled_containers(self):
        vibe_id, legacy_id = "a" * 12, "b" * 12
        stop_called = False

        def docker_run(command, **_kwargs):
            nonlocal stop_called
            if command[1] == "stop":
                stop_called = True
                self.assertEqual(set(command[4:]), {vibe_id, legacy_id})
                return subprocess.CompletedProcess(command, 0, stdout=f"{vibe_id}\n{legacy_id}\n", stderr="")
            label = command[-1].removeprefix("label=")
            if stop_called:
                return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
            container_id = vibe_id if label.startswith("vibe-director.analysis-job=") else legacy_id
            return subprocess.CompletedProcess(command, 0, stdout=f"{container_id}\n", stderr="")

        with patch.object(video_repertoire.shutil, "which", return_value="/usr/bin/docker"), \
                patch.object(video_repertoire.subprocess, "run", side_effect=docker_run):
            stopped = video_repertoire._stop_analysis_job_containers("analysis-123")

        self.assertEqual(set(stopped), {vibe_id, legacy_id})

    def test_staged_donor_videos_list_and_import_into_workspace_library(self):
        donor_root, donor_file, donor_id = self.staged_donor_video()
        app = create_app(data_root=self.data)
        with patch.object(video_repertoire, "STAGED_DONOR_REPERTOIRE_ROOT", donor_root):
            status, rows = self.request(app, "GET", "/api/video-summariser/workspace-a/library/donor")
            self.assertEqual(status, "200 OK")
            self.assertEqual([row["asset_id"] for row in rows], [donor_id])
            self.assertTrue(rows[0]["importable"])
            response = []
            preview_env = {"REQUEST_METHOD":"GET", "PATH_INFO":f"/api/video-summariser/workspace-a/library/donor/{donor_id}/content",
                "QUERY_STRING":"", "CONTENT_LENGTH":"0", "HTTP_RANGE":"bytes=0-127", "wsgi.input":io.BytesIO(b"")}
            preview = b"".join(app(preview_env, lambda status, headers: response.extend([status, headers])))
            self.assertEqual(response[0], "206 Partial Content")
            self.assertIn(("Accept-Ranges", "bytes"), response[1])
            self.assertEqual(preview, donor_file.read_bytes()[:128])
            status, result = self.request(app, "POST", "/api/video-summariser/workspace-a/library/donor/import",
                {"asset_ids": [donor_id]})
            imported_id = result["assets"][0]["asset_id"]
            update_annotations(self.data, "workspace-a", imported_id,
                description="Owner edited description", tags=["owner-tag"])
            status_again, repeated = self.request(app, "POST", "/api/video-summariser/workspace-a/library/donor/import",
                {"asset_ids": [donor_id]})
        self.assertEqual(status, "200 OK")
        self.assertEqual(status_again, "200 OK")
        self.assertEqual(len(result["assets"]), 1)
        self.assertEqual(repeated["assets"][0]["asset_id"], result["assets"][0]["asset_id"])
        self.assertFalse(result["assets"][0]["deduplicated"])
        self.assertTrue(repeated["assets"][0]["deduplicated"])
        self.assertEqual(repeated["assets"][0]["description"], "Owner edited description")
        imported = result["assets"][0]
        self.assertEqual(imported["kind"], "video")
        self.assertIn(donor_id, imported["provenance_notes"])
        self.assertEqual(imported["description"], "Donor clip · Test channel")
        self.assertIn("donor-video", imported["tags"])
        self.assertIn("source-youtube", imported["tags"])
        imported_path, _, _ = asset_path(self.data, "workspace-a", imported["asset_id"])
        self.assertTrue(imported_path.is_file())
        self.assertTrue(donor_file.is_file())
        self.assertEqual(list_assets(self.data, "workspace-a", kind="video")["total"], 2)

    def test_staged_donor_listing_marks_videos_over_library_limit(self):
        donor_root, _donor_file, _donor_id = self.staged_donor_video()
        app = create_app(data_root=self.data)
        with patch.object(video_repertoire, "STAGED_DONOR_REPERTOIRE_ROOT", donor_root), \
                patch("story_builder.services.media_library.MAX_UPLOAD_BYTES", 1):
            status, rows = self.request(app, "GET", "/api/video-summariser/workspace-a/library/donor")
        self.assertEqual(status, "200 OK")
        self.assertEqual(len(rows), 1)
        self.assertFalse(rows[0]["importable"])

    def test_duplicate_donor_videos_keep_all_source_lineage(self):
        donor_root, _donor_file, first_id = self.staged_donor_video()
        first_manifest = json.loads((donor_root / "manifests" / f"{first_id}.json").read_text(encoding="utf-8"))
        second_id = "video-012345abcdef"
        second_manifest = {**first_manifest, "asset_id": second_id, "title": "Second donor record"}
        (donor_root / "manifests" / f"{second_id}.json").write_text(json.dumps(second_manifest), encoding="utf-8")
        app = create_app(data_root=self.data)
        with patch.object(video_repertoire, "STAGED_DONOR_REPERTOIRE_ROOT", donor_root):
            status, result = self.request(app, "POST", "/api/video-summariser/workspace-a/library/donor/import",
                {"asset_ids": [first_id]})
            self.assertEqual(status, "200 OK")
            first_asset = result["assets"][0]
            update_annotations(self.data, "workspace-a", first_asset["asset_id"],
                description="Owner notes", tags=["owner-tag"])
            status, duplicate = self.request(app, "POST", "/api/video-summariser/workspace-a/library/donor/import",
                {"asset_ids": [second_id]})
            self.assertEqual(status, "200 OK")
            self.assertEqual(first_asset["asset_id"], duplicate["assets"][0]["asset_id"])
            asset = duplicate["assets"][0]
            self.assertIn("Donor clip", asset["description"])
            self.assertIn("Second donor record", asset["description"])
            self.assertIn("Owner notes", asset["description"])
            self.assertIn("owner-tag", asset["tags"])
            sources = asset["metadata"]["story_builder_donor_sources"]
            self.assertEqual({source["asset_id"] for source in sources}, {first_id, second_id})
            _status, repeated = self.request(app, "POST", "/api/video-summariser/workspace-a/library/donor/import",
                {"asset_ids": [first_id, second_id]})
        self.assertEqual(len(repeated["assets"][0]["metadata"]["story_builder_donor_sources"]), 2)

    def test_staged_donor_import_rejects_path_escape_and_unknown_id(self):
        donor_root, _donor_file, donor_id = self.staged_donor_video()
        manifest_path = donor_root / "manifests" / f"{donor_id}.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["path"] = str(self.source_file)
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        app = create_app(data_root=self.data)
        with patch.object(video_repertoire, "STAGED_DONOR_REPERTOIRE_ROOT", donor_root):
            status, escaped = self.request(app, "POST", "/api/video-summariser/workspace-a/library/donor/import",
                {"asset_ids": [donor_id]})
            self.assertEqual(status, "400 Bad Request")
            status, unknown = self.request(app, "POST", "/api/video-summariser/workspace-a/library/donor/import",
                {"asset_ids": ["video-000000000000"]})
        self.assertEqual(status, "404 Not Found")
        self.assertEqual(unknown["error"]["code"], "donor_asset_not_found")

    def test_staged_donor_listing_and_import_skip_non_object_manifests(self):
        donor_root, _donor_file, _donor_id = self.staged_donor_video()
        (donor_root / "manifests" / "video-000000000000.json").write_text("[]", encoding="utf-8")
        app = create_app(data_root=self.data)
        with patch.object(video_repertoire, "STAGED_DONOR_REPERTOIRE_ROOT", donor_root):
            status, rows = self.request(app, "GET", "/api/video-summariser/workspace-a/library/donor")
            self.assertEqual(status, "200 OK")
            self.assertEqual(len(rows), 1)
            status, result = self.request(app, "POST", "/api/video-summariser/workspace-a/library/donor/import",
                {"asset_ids": ["video-000000000000"]})
        self.assertEqual(status, "404 Not Found")
        self.assertEqual(result["error"]["code"], "donor_asset_not_found")

    def test_donor_analysis_exposes_summary_and_explicitly_imports_lineaged_audio(self):
        donor_root, _video_file, video_id = self.staged_donor_video()
        video_manifest_path = donor_root / "manifests" / f"{video_id}.json"
        video_manifest = json.loads(video_manifest_path.read_text(encoding="utf-8"))
        video_manifest["analysis_ids"] = ["analysis-test-01"]
        video_manifest_path.write_text(json.dumps(video_manifest), encoding="utf-8")
        run_id = "run-test-01"
        run_manifest_dir = donor_root / "manifests" / "analyzer-runs"
        run_manifest_dir.mkdir(parents=True)
        run_root = donor_root / "analyses" / "video_audio_analyzer" / run_id
        clip_path = run_root / "audio" / "collected" / "sfx" / "clip.wav"
        clip_path.parent.mkdir(parents=True)
        with wave.open(str(clip_path), "wb") as output:
            output.setnchannels(1); output.setsampwidth(2); output.setframerate(16000)
            output.writeframes(b"\0\0" * 800)
        voice_path = run_root / "audio" / "collected" / "voices" / "voice.wav"
        voice_path.parent.mkdir(parents=True)
        with wave.open(str(voice_path), "wb") as output:
            output.setnchannels(1); output.setsampwidth(2); output.setframerate(16000)
            output.writeframes(b"\1\0" * 800)
        (run_root / "internvideo3_summary.json").write_text(json.dumps({
            "status": "completed", "model": "summary-model", "revision": "abc123",
            "full_video_summary": "Courtroom scene with a tense argument."}), encoding="utf-8")
        (run_manifest_dir / f"{run_id}.json").write_text(json.dumps({
            "run_id": run_id, "job_id": "analysis-test-01", "project_id": video_id,
            "source_run": f"analyses/video_audio_analyzer/{run_id}", "collected_assets": [{
                "asset_id": "sfx_test_clip_01", "category": "sfx", "label": "Gavel strike",
                "source_run": run_id, "persisted_in_run": True,
                "path": f"analyses/video_audio_analyzer/{run_id}/audio/collected/sfx/clip.wav",
                "start_time_sec": 3.25, "end_time_sec": 4.0,
            }, {
                "asset_id": "voice_test_clip_02", "category": "voices", "label": "Witness line",
                "source_run": run_id, "persisted_in_run": True,
                "path": f"analyses/video_audio_analyzer/{run_id}/audio/collected/voices/voice.wav",
                "start_time_sec": 1.0, "end_time_sec": 1.75,
            }]}), encoding="utf-8")
        app = create_app(data_root=self.data)
        with patch.object(video_repertoire, "STAGED_DONOR_REPERTOIRE_ROOT", donor_root):
            status, info = self.request(app, "GET", f"/api/video-summariser/workspace-a/library/donor/{video_id}/analysis")
            self.assertEqual(status, "200 OK")
            self.assertEqual(info["analysis"]["summary"], "Courtroom scene with a tense argument.")
            self.assertEqual(len(info["audio_assets"]), 2)
            self.assertEqual(next(item for item in info["audio_assets"] if item["asset_id"] == "voice_test_clip_02")["category"], "voice")
            status, video_result = self.request(app, "POST", "/api/video-summariser/workspace-a/library/donor/import",
                {"asset_ids": [video_id]})
            video_asset = video_result["assets"][0]
            self.assertIn("Courtroom scene with a tense argument.", video_asset["description"])
            donor_video = video_asset["metadata"]["story_builder_donor_sources"][0]
            self.assertEqual(donor_video["asset_id"], video_id)
            self.assertEqual(donor_video["analysis"]["analysis_id"], "analysis-test-01")
            self.assertEqual(donor_video["analysis"]["run_id"], run_id)
            self.assertEqual(donor_video["analysis"]["model"], "summary-model")
            self.assertEqual(donor_video["analysis"]["revision"], "abc123")
            status, audio_result = self.request(app, "POST",
                f"/api/video-summariser/workspace-a/library/donor/{video_id}/analysis/import",
                {"asset_ids": ["sfx_test_clip_01"]})
            audio_asset = audio_result["assets"][0]
            donor_audio = audio_asset["metadata"]["story_builder_donor_sources"][0]
            self.assertEqual(donor_audio["video_asset_id"], video_id)
            self.assertEqual(donor_audio["analysis_id"], "analysis-test-01")
            self.assertEqual(donor_audio["run_id"], run_id)
            self.assertEqual(donor_audio["start_time_sec"], 3.25)
            self.assertEqual(donor_audio["end_time_sec"], 4.0)
            self.assertEqual(donor_audio["sha256"], video_repertoire.sha256_file(clip_path))
            existing_voice = register_upload(self.data, "workspace-a", filename="voice.wav",
                content=voice_path.read_bytes(), role="project_audio")
            existing_voice = update_annotations(self.data, "workspace-a", existing_voice["asset_id"],
                description="Director's voice note", tags=["keep-this"])
            status, voice_result = self.request(app, "POST",
                f"/api/video-summariser/workspace-a/library/donor/{video_id}/analysis/import",
                {"asset_ids": ["voice_test_clip_02"]})
            self.assertEqual(status, "200 OK")
            voice_asset = voice_result["assets"][0]
            self.assertEqual(voice_asset["audio_category"], "voice")
            self.assertTrue(voice_asset["deduplicated"])
            self.assertEqual(voice_asset["description"], "Director's voice note")
            self.assertEqual(voice_asset["tags"], ["keep-this"])
            self.assertNotIn("voice_master", voice_asset["roles"])
            enroll_body = json.dumps({"asset_id": voice_asset["asset_id"], "name": "Witness voice",
                "transcript": "I saw the lights turn on."}).encode()
            environ = {"REQUEST_METHOD": "POST", "PATH_INFO": "/api/audio/workspace-a/voices",
                "QUERY_STRING": "", "CONTENT_TYPE": "application/json",
                "CONTENT_LENGTH": str(len(enroll_body)), "wsgi.input": io.BytesIO(enroll_body)}
            response = []
            with patch("story_builder.isolated_server.audio_catalog.install_reference_voice",
                       return_value={"audio_path": "/comfy/voices/Witness.wav", "restart_required": False}), \
                 patch("story_builder.isolated_server.audio_catalog.discover_voices", return_value=[]), \
                 patch("story_builder.isolated_server.audio_catalog.refresh_live_voice_catalog",
                       return_value={"refreshed": True, "restart_required": False}):
                content = b"".join(app(environ, lambda status, headers: response.extend([status, headers])))
            self.assertEqual(response[0], "201 Created")
            self.assertIn("voice_master", json.loads(content)["asset"]["roles"])
            update_annotations(self.data, "workspace-a", audio_asset["asset_id"],
                description="Owner's edit", tags=["custom"])
            _status, repeated = self.request(app, "POST",
                f"/api/video-summariser/workspace-a/library/donor/{video_id}/analysis/import",
                {"asset_ids": ["sfx_test_clip_01"]})
        self.assertEqual(status, "200 OK")
        self.assertEqual(audio_asset["kind"], "audio")
        self.assertEqual(audio_asset["audio_category"], "sfx")
        self.assertIn(video_id, audio_asset["provenance_notes"])
        self.assertIn("3.25–4.0 seconds", audio_asset["provenance_notes"])
        self.assertEqual(repeated["assets"][0]["description"], "Owner's edit")
        self.assertEqual(repeated["assets"][0]["metadata"]["story_builder_donor_sources"], [donor_audio])

    def test_stages_selected_workspace_video_without_moving_source(self):
        original, _, _ = asset_path(self.data, "workspace-a", self.source["asset_id"])
        [staged] = video_repertoire.stage_workspace_video_assets(self.data, "workspace-a", [self.source["asset_id"]])
        stage_path = Path(staged["path"]).resolve()
        self.assertTrue(stage_path.is_relative_to((self.data / "video_repertoire").resolve()))
        self.assertEqual(original.read_bytes(), self.source_file.read_bytes())
        self.assertEqual(staged["metadata"]["source_asset_id"], self.source["asset_id"])
        self.assertEqual(staged["metadata"]["workspace_id"], "workspace-a")
        self.assertEqual(video_repertoire.get_asset(staged["asset_id"])["sha256"], self.source["sha256"])

    def test_default_analyzer_root_uses_vibe_local_migration_copy(self):
        video_repertoire.configure_roots(self.data)
        expected = Path(__file__).resolve().parents[3] / "local_data" / "engines" / "video-analyzer"
        self.assertEqual(video_repertoire.ANALYZER_ROOT, expected.resolve())
        self.assertNotIn("/home/riki/web_dev/story_builder", str(video_repertoire.ANALYZER_ROOT))

    def test_analyzer_capabilities_check_configured_local_model_root(self):
        for relative in (
            "models/internvideo3-8b-instruct/config.json",
            "models/internvideo3-8b-instruct/model.safetensors.index.json",
            "models/pe-av-base/config.json",
            "models/pe-av-base/model.safetensors",
        ):
            target = self.analyzer / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.touch()
        with patch.object(video_repertoire, "urlopen", side_effect=URLError("offline")),              patch.object(video_repertoire.shutil, "which", return_value=None):
            result = video_repertoire.capabilities("http://ollama.invalid")
        self.assertTrue(result["video_audio_analyzer_models_ready"])
        self.assertFalse(result["video_audio_analyzer_ready"])

    def test_analysis_api_creates_workspace_scoped_durable_job_without_starting_process(self):
        app = create_app(data_root=self.data, video_summarizer_capability_provider=lambda: {"can_analyze": True})
        with patch("story_builder.isolated_server.inspect_gpu_runtime", return_value={"recorded_at":"now"}), \
             patch("story_builder.services.video_repertoire.start_job", side_effect=lambda kind, job_id:
                   video_repertoire.read_job(kind, job_id)):
            status, job = self.request(app, "POST", "/api/video-summariser/workspace-a/analysis/jobs",
                {"asset_ids": [self.source["asset_id"]], "settings": {}})
        self.assertEqual(status, "202 Accepted")
        self.assertEqual(job["request"]["workspace_id"], "workspace-a")
        self.assertEqual(job["status"], "queued")
        status, listed = self.request(app, "GET", "/api/video-summariser/workspace-a/analysis/jobs")
        self.assertEqual(status, "200 OK")
        self.assertEqual([item["job_id"] for item in listed], [job["job_id"]])
        status, found = self.request(app, "GET", f"/api/video-summariser/workspace-a/analysis/jobs/{job['job_id']}")
        self.assertEqual(status, "200 OK")
        self.assertEqual(found["job_id"], job["job_id"])
        status, hidden = self.request(app, "GET", f"/api/video-summariser/workspace-b/analysis/jobs/{job['job_id']}")
        self.assertEqual(status, "404 Not Found")
        self.assertEqual(hidden["error"]["code"], "not_found")

    def test_analysis_api_rejects_non_video_or_foreign_assets(self):
        app = create_app(data_root=self.data, video_summarizer_capability_provider=lambda: {"can_analyze": True})
        status, result = self.request(app, "POST", "/api/video-summariser/workspace-b/analysis/jobs",
            {"asset_ids": [self.source["asset_id"]]})
        self.assertEqual(status, "404 Not Found")
        self.assertEqual(result["error"]["code"], "asset_not_found")

    def test_analysis_api_does_not_queue_when_readiness_fails(self):
        app = create_app(data_root=self.data, video_summarizer_capability_provider=lambda: {
            "can_analyze": False, "reason": "Docker image is missing."})
        with patch("story_builder.services.video_repertoire.create_job") as create_job:
            status, result = self.request(app, "POST", "/api/video-summariser/workspace-a/analysis/jobs",
                {"asset_ids": [self.source["asset_id"]]})
        self.assertEqual(status, "409 Conflict")
        self.assertEqual(result["error"]["code"], "analyzer_not_ready")
        create_job.assert_not_called()

    def test_analysis_api_does_not_stage_or_queue_when_gpu_admission_fails(self):
        app = create_app(data_root=self.data, video_summarizer_capability_provider=lambda: {"can_analyze": True})
        with patch("story_builder.isolated_server.inspect_gpu_runtime", side_effect=GPUAdmissionError("Only 1.7 GiB free; 20 GiB is required.")), \
             patch("story_builder.services.video_repertoire.stage_workspace_video_assets") as stage_assets, \
             patch("story_builder.services.video_repertoire.create_job") as create_job:
            status, result = self.request(app, "POST", "/api/video-summariser/workspace-a/analysis/jobs",
                {"asset_ids": [self.source["asset_id"]], "settings": {}})
        self.assertEqual(status, "409 Conflict")
        self.assertEqual(result["error"]["code"], "gpu_not_ready")
        self.assertIn("20 GiB is required", result["error"]["message"])
        stage_assets.assert_not_called()
        create_job.assert_not_called()

    def test_sam_isolation_api_uses_workspace_scoped_analyzed_event(self):
        app = create_app(data_root=self.data)
        expected = {"status": "preview_ready", "temporary_id": "sam-" + "a" * 32,
            "audio_url": "/api/video-summariser/workspace-a/sam/previews/sam-" + "a" * 32 + "/audio"}
        with patch.object(sam_audio_vibe, "isolate_event", return_value=expected) as isolate:
            status, result = self.request(app, "POST",
                "/api/video-summariser/workspace-a/analysis/runs/0123456789abcdef/events/event-1/isolate",
                {"prompt": "distant crowd cheering"})
        self.assertEqual(status, "200 OK")
        self.assertEqual(result, expected)
        isolate.assert_called_once_with(self.data.resolve(), "workspace-a", "0123456789abcdef",
            "event-1", "distant crowd cheering")

    def test_sam_isolation_withholds_sidecar_call_when_gpu_admission_fails(self):
        app = create_app(data_root=self.data)
        with patch.object(sam_audio_vibe, "isolate_event",
                   side_effect=MediaJobError("Insufficient free GPU memory.")) as isolate:
            status, result = self.request(app, "POST",
                "/api/video-summariser/workspace-a/analysis/runs/0123456789abcdef/events/event-1/isolate",
                {"prompt": "distant crowd cheering"})
        self.assertEqual(status, "503 Service Unavailable")
        self.assertEqual(result["error"]["code"], "gpu_admission_failed")
        self.assertIn("Insufficient free GPU memory", result["error"]["message"])
        isolate.assert_called_once_with(self.data.resolve(), "workspace-a", "0123456789abcdef",
            "event-1", "distant crowd cheering")

    def test_sam_safety_trip_does_not_publish_preview_metadata(self):
        temporary_id = "sam-" + "a" * 32
        source_audio = self.base / "analysis.wav"
        source_audio.write_bytes(b"source")
        owner = {"source_asset_id": "source-asset", "source_sha256": "sha",
            "video_asset_id": "video-asset", "audio_path": source_audio}
        class FakeAdapter:
            def isolate(self, *, temp_root, **_kwargs):
                temp_root.mkdir(parents=True, exist_ok=True)
                (temp_root / f"{temporary_id}.wav").write_bytes(b"wav-bytes")
                return {"status": "preview_ready", "temporary_id": temporary_id}
        @contextmanager
        def safety_trip(**_kwargs):
            yield
            raise MediaJobError("thermal cutoff")
        with patch.object(sam_audio_vibe, "_owned_run", return_value=(self.base,
                {"audio_events": [{"event_id": "event-1", "start_time_sec": 1, "end_time_sec": 2}]}, owner)), \
             patch.object(sam_audio_vibe, "_adapter", return_value=FakeAdapter()), \
             patch("story_builder.services.media_jobs.gpu_workload_guard", side_effect=safety_trip):
            with self.assertRaisesRegex(MediaJobError, "thermal cutoff"):
                sam_audio_vibe.isolate_event(self.data, "workspace-a", "0123456789abcdef",
                    "event-1", "distant crowd")
        wav, info = sam_audio_vibe._paths(self.data, "workspace-a", temporary_id)
        self.assertTrue(wav.is_file())
        self.assertFalse(info.exists())

    def test_sam_capability_api_reports_readiness_without_exposing_worker_details(self):
        app = create_app(data_root=self.data)
        status_payload = {"status": "gated_or_unavailable", "model": "facebook/sam-audio-large-tv",
            "checkpoint_present": False, "authentication_configured": True,
            "worker_configured": True, "worker": {"url": "http://private-worker", "token": "secret"}}
        with patch.object(sam_audio_vibe, "readiness", return_value=status_payload) as readiness:
            status, result = self.request(app, "GET", "/api/video-summariser/sam/capabilities")
        self.assertEqual(status, "200 OK")
        self.assertFalse(result["available"])
        self.assertEqual(result["status"], "gated_or_unavailable")
        self.assertNotIn("worker", result)
        self.assertNotIn("url", json.dumps(result))
        self.assertNotIn("secret", json.dumps(result))
        readiness.assert_called_once_with()

    def test_sam_isolation_api_hides_events_outside_workspace(self):
        app = create_app(data_root=self.data)
        with patch.object(sam_audio_vibe, "isolate_event", side_effect=FileNotFoundError):
            status, result = self.request(app, "POST",
                "/api/video-summariser/workspace-b/analysis/runs/0123456789abcdef/events/event-1/isolate",
                {"prompt": "crowd"})
        self.assertEqual(status, "404 Not Found")
        self.assertEqual(result["error"]["code"], "analysis_event_not_found")

    def test_sam_save_api_requires_explicit_workspace_preview_save_without_model_review(self):
        app = create_app(data_root=self.data, reasoning_json_provider=lambda **_kwargs: self.fail("must not call a model"))
        expected = {"status": "saved", "asset": {"asset_id": "audio-a1b2"}}
        with patch.object(sam_audio_vibe, "save_preview", return_value=expected) as save:
            status, result = self.request(app, "POST",
                "/api/video-summariser/workspace-a/sam/previews/sam-" + "a" * 32 + "/save", {})
        self.assertEqual(status, "200 OK")
        self.assertEqual(result, expected)
        save.assert_called_once_with(self.data.resolve(), "workspace-a", "sam-" + "a" * 32)

    def test_sam_preview_stream_is_workspace_scoped_and_wav_typed(self):
        app = create_app(data_root=self.data)
        preview = self.base / "temporary.wav"
        preview.write_bytes(b"RIFF" + b"\x00" * 40)
        captured = {}
        def serve(_environ, start_response, path, *, media_type=None, filename=None):
            captured.update(path=path, media_type=media_type)
            start_response("200 OK", [("Content-Type", media_type or "application/octet-stream")])
            return [b"audio"]
        with patch.object(sam_audio_vibe, "preview_path", return_value=preview) as resolve, \
             patch("story_builder.isolated_server._serve_asset", side_effect=serve):
            response = []
            body = b"".join(app({"REQUEST_METHOD": "GET", "PATH_INFO":
                "/api/video-summariser/workspace-a/sam/previews/sam-" + "a" * 32 + "/audio",
                "QUERY_STRING": "", "CONTENT_LENGTH": "0", "wsgi.input": io.BytesIO(b"")},
                lambda status, headers: response.extend([status, headers])))
        self.assertEqual(response[0], "200 OK")
        self.assertEqual(body, b"audio")
        self.assertEqual(captured, {"path": preview, "media_type": "audio/wav"})
        resolve.assert_called_once_with(self.data.resolve(), "workspace-a", "sam-" + "a" * 32)

    def test_sam_preview_path_rejects_workspace_path_traversal(self):
        with self.assertRaises(sam_audio_vibe.SamAudioError):
            sam_audio_vibe._paths(self.data, "../outside", "sam-" + "a" * 32)

    def test_sam_preview_path_rejects_workspace_symlink_outside_data_root(self):
        outside = self.base / "outside-temp"
        outside.mkdir()
        link = self.data / "video_repertoire" / "temp" / "sam_audio" / "workspace-a"
        link.parent.mkdir(parents=True)
        link.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(sam_audio_vibe.SamAudioError):
            sam_audio_vibe._paths(self.data, "workspace-a", "sam-" + "a" * 32)

    def test_sam_save_retry_returns_the_same_library_asset_after_preview_is_removed(self):
        temporary_id = "sam-" + "b" * 32
        wav, info = sam_audio_vibe._paths(self.data, "workspace-a", temporary_id)
        wav.parent.mkdir(parents=True)
        with wave.open(str(wav), "wb") as output:
            output.setnchannels(1); output.setsampwidth(2); output.setframerate(16000)
            output.writeframes(b"\x00\x00" * 1600)
        info.write_text(json.dumps({"expires_epoch": 4102444800, "prompt": "rain", "model": "sam-audio",
            "provenance": {"event_label": "rain", "source_asset_id": self.source["asset_id"]}}), encoding="utf-8")

        first = sam_audio_vibe.save_preview(self.data, "workspace-a", temporary_id)
        second = sam_audio_vibe.save_preview(self.data, "workspace-a", temporary_id)

        self.assertEqual(first["status"], "saved")
        self.assertEqual(second["status"], "saved")
        self.assertTrue(second["idempotent"])
        self.assertEqual(second["asset"]["asset_id"], first["asset"]["asset_id"])
        self.assertEqual(list_assets(self.data, "workspace-a", kind="audio")["total"], 1)
        self.assertEqual(len((self.data / "video_repertoire/indexes/sam_audio_reviews/workspace-a.jsonl").read_text().splitlines()), 1)

    def test_analysis_retry_restarts_workspace_job_only_when_ready(self):
        app = create_app(data_root=self.data, video_summarizer_capability_provider=lambda: {"can_analyze": True})
        job = {"job_id": "job-a", "request": {"workspace_id": "workspace-a"}, "status": "failed"}
        with patch("story_builder.isolated_server.inspect_gpu_runtime", return_value={"recorded_at":"now"}), \
             patch("story_builder.services.video_repertoire.read_job", return_value=job), \
             patch("story_builder.services.video_repertoire.start_job", return_value={**job, "status": "queued"}) as start_job:
            status, result = self.request(app, "POST", "/api/video-summariser/workspace-a/analysis/jobs/job-a/retry", {})
        self.assertEqual(status, "202 Accepted")
        self.assertEqual(result["status"], "queued")
        start_job.assert_called_once_with("analysis", "job-a")

    def test_analysis_retry_hides_foreign_job_and_respects_readiness(self):
        job = {"job_id": "job-a", "request": {"workspace_id": "workspace-a"}, "status": "failed"}
        app = create_app(data_root=self.data, video_summarizer_capability_provider=lambda: {"can_analyze": True})
        with patch("story_builder.services.video_repertoire.read_job", return_value=job), \
             patch("story_builder.services.video_repertoire.start_job") as start_job:
            status, hidden = self.request(app, "POST", "/api/video-summariser/workspace-b/analysis/jobs/job-a/retry", {})
        self.assertEqual(status, "404 Not Found")
        self.assertEqual(hidden["error"]["code"], "not_found")
        start_job.assert_not_called()

        app = create_app(data_root=self.data, video_summarizer_capability_provider=lambda: {
            "can_analyze": False, "reason": "Analyzer unavailable."})
        with patch("story_builder.services.video_repertoire.read_job", return_value=job), \
             patch("story_builder.services.video_repertoire.start_job") as start_job:
            status, blocked = self.request(app, "POST", "/api/video-summariser/workspace-a/analysis/jobs/job-a/retry", {})
        self.assertEqual(status, "409 Conflict")
        self.assertEqual(blocked["error"]["code"], "analyzer_not_ready")
        start_job.assert_not_called()

    def test_analysis_retry_does_not_start_worker_when_gpu_admission_fails(self):
        job = {"job_id": "job-a", "request": {"workspace_id": "workspace-a"}, "status": "failed"}
        app = create_app(data_root=self.data, video_summarizer_capability_provider=lambda: {"can_analyze": True})
        with patch("story_builder.services.video_repertoire.read_job", return_value=job), \
             patch("story_builder.isolated_server.inspect_gpu_runtime", side_effect=GPUAdmissionError("GPU admission unavailable.")), \
             patch("story_builder.services.video_repertoire.start_job") as start_job:
            status, blocked = self.request(app, "POST", "/api/video-summariser/workspace-a/analysis/jobs/job-a/retry", {})
        self.assertEqual(status, "409 Conflict")
        self.assertEqual(blocked["error"]["code"], "gpu_not_ready")
        start_job.assert_not_called()

    def test_semantic_search_uses_only_workspace_runs_and_maps_published_asset(self):
        run_root = video_repertoire.analyzer_runs_root() / "run-a"
        index = run_root / "index"
        index.mkdir(parents=True)
        (run_root / "manifest.json").write_text(json.dumps({"embeddings": {"pe_av": {"status": "completed"}}}))
        (index / "index_manifest.json").write_text(json.dumps({"record_schema_version": 2,
            "model": {"backend": "pe_av"}, "vector_fields": {"pe_av_vector": 2}}))
        matching_asset = {"asset_id": "pa-frame", "kind": "image", "metadata": {
            "analyzer_run_id": "run-a", "frame_id": "frame-1"}}
        jobs = [
            {"status": "completed", "request": {"workspace_id": "workspace-a"},
             "result": {"audio_analysis": [{"run_id": "run-a"}]}},
            {"status": "completed", "request": {"workspace_id": "workspace-b"},
             "result": {"audio_analysis": [{"run_id": "run-b"}]}},
        ]
        fake_retrieval = type("Retrieval", (), {
            "_load_records": staticmethod(lambda _index: [{"record_id": "deleted-frame", "kind": "frame",
                "index_embedding_backend": "pe_av", "pe_av_vector": [0.1, 0.2]}, {"record_id": "frame-1", "kind": "frame",
                "index_embedding_backend": "pe_av", "pe_av_vector": [0.1, 0.2]}]),
            "search_records": staticmethod(lambda records, *_args, **_kwargs: {
                "results": [{**records[0], "score": 0.9}], "query_backend": "pe_av"}),
        })
        with patch.object(media_semantic_search, "_retrieval_module", return_value=fake_retrieval), \
             patch.object(video_repertoire, "list_jobs", return_value=jobs), \
             patch.object(media_semantic_search, "list_assets", return_value={"assets": [matching_asset], "total": 1}):
            result = media_semantic_search.search_workspace(self.data, "workspace-a", "rainy street", kind="image")
        self.assertEqual([row["asset"]["asset_id"] for row in result["results"]], ["pa-frame"])
        self.assertEqual(result["results"][0]["run_id"], "run-a")

    def test_analysis_rejects_completed_sources_and_derived_clips_before_runtime(self):
        app=create_app(data_root=self.data,video_summarizer_capability_provider=lambda:{"can_analyze":True})
        path="/api/video-summariser/workspace-a/analysis/jobs"
        completed={"status":"completed","request":{"workspace_id":"workspace-a","source_asset_ids":[self.source["asset_id"]]}}
        with patch.object(video_repertoire,"list_jobs",return_value=[completed]), patch.object(video_repertoire,"start_job") as start:
            status,result=self.request(app,"POST",path,{"asset_ids":[self.source["asset_id"]]})
            self.assertEqual(status,"409 Conflict");self.assertEqual(result["error"]["code"],"already_analyzed");start.assert_not_called()
        derived={**self.source,"metadata":{"analyzer_run_id":"run-a"}}
        with patch("story_builder.isolated_server.list_media_assets",return_value={"assets":[derived],"total":1}), patch.object(video_repertoire,"start_job") as start:
            status,result=self.request(app,"POST",path,{"asset_ids":[derived["asset_id"]]})
            self.assertEqual(status,"404 Not Found");start.assert_not_called()
        self.assertNotEqual(self.request(app,"DELETE",f"/api/media/workspace-a/assets/{self.source['asset_id']}")[0],"200 OK")
        self.assertTrue(asset_path(self.data,"workspace-a",self.source["asset_id"])[0].is_file())

    def test_semantic_search_rejects_bad_request(self):
        with self.assertRaises(ValueError):
            media_semantic_search.search_workspace(self.data, "workspace-a", "  ", kind="video")

    def test_semantic_audio_search_skips_malformed_persisted_timestamps(self):
        run_root = video_repertoire.analyzer_runs_root() / "run-audio"
        index = run_root / "index"
        index.mkdir(parents=True)
        (run_root / "manifest.json").write_text(json.dumps({"embeddings": {"pe_av": {"status": "completed"}}}))
        (index / "index_manifest.json").write_text(json.dumps({"record_schema_version": 2,
            "model": {"backend": "pe_av"}, "vector_fields": {"pe_av_vector": 2}}))
        malformed_asset = {"asset_id": "pa-audio", "kind": "audio", "metadata": {
            "analyzer_run_id": "run-audio", "timestamp_start_seconds": "bad", "timestamp_end_seconds": 9}}
        jobs = [{"status": "completed", "request": {"workspace_id": "workspace-a"},
            "result": {"audio_analysis": [{"run_id": "run-audio"}]}}]
        fake_retrieval = type("Retrieval", (), {
            "_load_records": staticmethod(lambda _index: [{"record_id": "event-1", "kind": "audio_event",
                "index_embedding_backend": "pe_av", "pe_av_vector": [0.1, 0.2],
                "start_time_sec": 2, "end_time_sec": 4}]),
            "search_records": staticmethod(lambda *_args, **_kwargs: {
                "results": [], "query_backend": "pe_av"}),
        })
        with patch.object(media_semantic_search, "_retrieval_module", return_value=fake_retrieval), \
             patch.object(video_repertoire, "list_jobs", return_value=jobs), \
             patch.object(media_semantic_search, "list_assets", return_value={"assets": [malformed_asset], "total": 1}):
            result = media_semantic_search.search_workspace(self.data, "workspace-a", "speech", kind="audio")
        self.assertEqual(result["results"], [])
        self.assertIn("No matching", result["reason"])

    def test_annotation_index_rejects_non_object_worker_responses(self):
        for payload in ([], None):
            with self.subTest(payload=payload), patch.dict("os.environ", {
                    "VIDEO_AUDIO_ANALYZER_PE_AV_WORKER_URL": "http://worker"}), patch(
                    "story_builder.services.media_semantic_search.urllib.request.urlopen",
                    return_value=io.BytesIO(json.dumps(payload).encode())):
                with self.assertRaisesRegex(RuntimeError, "invalid text embedding"):
                    media_semantic_search.index_workspace_asset(self.data, "workspace-a", self.source["asset_id"])

    def test_saved_annotation_index_uses_real_worker_embedding_and_stales_on_edit(self):
        asset = update_annotations(self.data, "workspace-a", self.source["asset_id"],
            description="Rainy street at night", tags=["neon", "cinema"])
        vector = [0.25, -0.5, 0.75]
        response = io.BytesIO(json.dumps({"model":"facebook/pe-av-base", "dimension":3,
            "embedding":vector}).encode())
        with patch.dict("os.environ", {"VIDEO_AUDIO_ANALYZER_PE_AV_WORKER_URL":"http://worker"}), \
             patch("story_builder.services.media_semantic_search.urllib.request.urlopen", return_value=response) as request:
            indexed = media_semantic_search.index_workspace_asset(self.data, "workspace-a", asset["asset_id"])
        self.assertEqual(indexed["semantic_annotation_index"]["source"], "saved_filename_description_tags_roles")
        self.assertNotIn("vector", indexed["semantic_annotation_index"])
        manifest = json.loads((self.data / "projects" / "workspace-a" / "media" / "assets.json").read_text())
        stored = next(row for row in manifest["assets"] if row["asset_id"] == asset["asset_id"])
        self.assertEqual(stored["semantic_annotation_index"]["vector"], vector)
        public_asset = next(row for row in list_assets(self.data, "workspace-a")["assets"]
            if row["asset_id"] == asset["asset_id"])
        internal_asset = next(row for row in list_assets(self.data, "workspace-a", include_semantic_vectors=True)["assets"]
            if row["asset_id"] == asset["asset_id"])
        self.assertNotIn("vector", public_asset["semantic_annotation_index"])
        self.assertEqual(internal_asset["semantic_annotation_index"]["vector"], vector)
        request.assert_called_once()
        update_annotations(self.data, "workspace-a", asset["asset_id"], description="Different text",
            tags=["neon", "cinema"])
        current = next(row for row in list_assets(self.data, "workspace-a")["assets"] if row["asset_id"] == asset["asset_id"])
        self.assertNotIn("semantic_annotation_index", current)

    def test_semantic_search_includes_only_current_saved_annotation_embeddings(self):
        asset = update_annotations(self.data, "workspace-a", self.source["asset_id"],
            description="A rainy neon street", tags=["night scene"])
        text = semantic_annotation_text(asset)
        indexed = save_semantic_annotation_index(self.data, "workspace-a", asset["asset_id"],
            source_sha256=asset["sha256"], annotation_sha256=hashlib.sha256(text.encode()).hexdigest(),
            model="facebook/pe-av-base", vector=[0.2, 0.8])
        fake_retrieval = type("Retrieval", (), {
            "_load_records": staticmethod(lambda _index: []),
            "search_records": staticmethod(lambda records, *_args, **_kwargs: {
                "results": [{**records[0], "score": 0.91}], "query_backend": "pe_av"}),
        })
        with patch.dict("os.environ", {"VIDEO_AUDIO_ANALYZER_PE_AV_WORKER_URL":"http://worker"}), \
             patch.object(media_semantic_search, "_retrieval_module", return_value=fake_retrieval), \
             patch.object(video_repertoire, "list_jobs", return_value=[]):
            result = media_semantic_search.search_workspace(self.data, "workspace-a", "wet city at night", kind="video")
        self.assertEqual(result["results"][0]["asset"]["asset_id"], indexed["asset_id"])
        self.assertEqual(result["results"][0]["semantic_source"], "saved_annotations")
        self.assertNotIn("vector", result["results"][0]["asset"]["semantic_annotation_index"])
        self.assertEqual(result["annotation_index_count"], 1)

    def test_semantic_content_index_job_embeds_and_persists_video_vector(self):
        (self.analyzer / "models" / "pe-av-base").mkdir(parents=True)
        (self.analyzer / "models" / "pe-av-base" / "config.json").write_text("{}")
        (self.analyzer / "models" / "pe-av-base" / "model.safetensors").write_bytes(b"checkpoint")
        (self.analyzer / "src" / "video_audio_analyzer").mkdir(parents=True)
        (self.analyzer / "src" / "video_audio_analyzer" / "peav_adapter.py").write_text("# installed")
        vector = [0.125, -0.5, 0.75]
        completed = subprocess.CompletedProcess([], 0,
            stdout=json.dumps({"model":"facebook/pe-av-base", "embedding":vector}), stderr="")
        request = {"workspace_id":"workspace-a", "asset_id":self.source["asset_id"],
            "modality":"video", "sha256":self.source["sha256"]}
        job = video_repertoire.create_job("semantic-index", request)
        with patch("story_builder.services.video_repertoire_worker.gpu_workload_guard", return_value=nullcontext()), \
             patch("story_builder.services.video_repertoire_worker.subprocess.run", return_value=completed) as run:
            from story_builder.services.video_repertoire_worker import run_semantic_index
            result = run_semantic_index(job["job_id"], request)
        self.assertEqual(result["dimension"], 3)
        command = run.call_args.args[0]
        self.assertIn("--network", command)
        self.assertEqual(command[command.index("--network") + 1], "none")
        mounts = [command[i + 1] for i, value in enumerate(command[:-1]) if value == "-v"]
        indexed_path, _, _ = asset_path(self.data, "workspace-a", self.source["asset_id"])
        self.assertTrue(any(item.startswith(str(indexed_path) + ":") and item.endswith(":ro") for item in mounts))
        manifest = json.loads((self.data / "projects" / "workspace-a" / "media" / "assets.json").read_text())
        stored = next(row for row in manifest["assets"] if row["asset_id"] == self.source["asset_id"])
        self.assertEqual(stored["semantic_content_index"]["vector"], vector)
        public_asset = next(row for row in list_assets(self.data, "workspace-a")["assets"] if row["asset_id"] == self.source["asset_id"])
        self.assertNotIn("vector", public_asset["semantic_content_index"])

    def test_semantic_content_index_job_route_is_workspace_scoped_and_durable(self):
        app = create_app(data_root=self.data)
        with patch("story_builder.isolated_server.inspect_gpu_runtime", return_value={"recorded_at":"now"}), \
             patch.object(video_repertoire, "start_job", side_effect=lambda kind, job_id: video_repertoire.read_job(kind, job_id)) as start:
            status, job = self.request(app, "POST",
                f"/api/media/workspace-a/assets/{self.source['asset_id']}/semantic-content-index", {})
        self.assertEqual(status, "202 Accepted")
        self.assertEqual(job["kind"], "semantic-index")
        self.assertEqual(job["request"]["modality"], "video")
        start.assert_called_once_with("semantic-index", job["job_id"])
        status, hidden = self.request(app, "GET", f"/api/media/workspace-b/semantic-index-jobs/{job['job_id']}")
        self.assertEqual(status, "404 Not Found")
        status, stored = self.request(app, "GET", f"/api/media/workspace-a/semantic-index-jobs/{job['job_id']}")
        self.assertEqual(status, "200 OK")
        self.assertEqual(stored["job_id"], job["job_id"])

    def test_semantic_content_index_accepts_image_and_queues_visual_job(self):
        image = self.upload_test_image()
        app = create_app(data_root=self.data)
        with patch("story_builder.isolated_server.inspect_gpu_runtime", return_value={"recorded_at":"now"}), \
             patch.object(video_repertoire, "start_job", side_effect=lambda kind, job_id: video_repertoire.read_job(kind, job_id)) as start:
            status, job = self.request(app, "POST",
                f"/api/media/workspace-a/assets/{image['asset_id']}/semantic-content-index", {})
        self.assertEqual(status, "202 Accepted")
        self.assertEqual(job["request"]["modality"], "image")
        start.assert_called_once_with("semantic-index", job["job_id"])

    def test_semantic_content_index_does_not_create_or_start_job_when_gpu_admission_fails(self):
        app = create_app(data_root=self.data)
        with patch("story_builder.isolated_server.inspect_gpu_runtime",
                   side_effect=GPUAdmissionError("Only 1.7 GiB free; 20 GiB is required.")), \
             patch.object(video_repertoire, "create_job") as create_job, \
             patch.object(video_repertoire, "start_job") as start_job:
            status, result = self.request(app, "POST",
                f"/api/media/workspace-a/assets/{self.source['asset_id']}/semantic-content-index", {})
        self.assertEqual(status, "409 Conflict")
        self.assertEqual(result["error"]["code"], "gpu_not_ready")
        self.assertIn("20 GiB is required", result["error"]["message"])
        create_job.assert_not_called()
        start_job.assert_not_called()

    def test_semantic_index_retry_does_not_start_worker_when_gpu_admission_fails(self):
        app = create_app(data_root=self.data)
        job = {"job_id":"job-123", "request":{"workspace_id":"workspace-a"}, "status":"failed"}
        with patch.object(video_repertoire, "read_job", return_value=job), \
             patch("story_builder.isolated_server.inspect_gpu_runtime",
                   side_effect=GPUAdmissionError("Only 1.7 GiB free; 20 GiB is required.")), \
             patch.object(video_repertoire, "start_job") as start_job:
            status, result = self.request(app, "POST",
                "/api/media/workspace-a/semantic-index-jobs/job-123/retry", {})
        self.assertEqual(status, "409 Conflict")
        self.assertEqual(result["error"]["code"], "gpu_not_ready")
        start_job.assert_not_called()

    def test_image_visual_index_uses_temporary_video_and_preserves_source(self):
        image = self.upload_test_image()
        (self.analyzer / "models" / "pe-av-base").mkdir(parents=True)
        (self.analyzer / "models" / "pe-av-base" / "config.json").write_text("{}")
        (self.analyzer / "models" / "pe-av-base" / "model.safetensors").write_bytes(b"checkpoint")
        (self.analyzer / "src" / "video_audio_analyzer").mkdir(parents=True)
        (self.analyzer / "src" / "video_audio_analyzer" / "peav_adapter.py").write_text("# installed")
        request = {"workspace_id":"workspace-a", "asset_id":image["asset_id"],
            "modality":"image", "sha256":image["sha256"]}
        job = video_repertoire.create_job("semantic-index", request)
        vector = [0.2, 0.4, 0.8]
        calls = []
        def fake_run(command, **_kwargs):
            calls.append(command)
            if command[0] == "ffmpeg":
                Path(command[-1]).write_bytes(b"temporary mp4")
                return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
            return subprocess.CompletedProcess(command, 0,
                stdout=json.dumps({"model":"facebook/pe-av-base", "embedding":vector}), stderr="")
        original_path, _, _ = asset_path(self.data, "workspace-a", image["asset_id"])
        original_bytes = original_path.read_bytes()
        with patch("story_builder.services.video_repertoire_worker.gpu_workload_guard", return_value=nullcontext()), \
             patch("story_builder.services.video_repertoire_worker.subprocess.run", side_effect=fake_run):
            from story_builder.services.video_repertoire_worker import run_semantic_index
            result = run_semantic_index(job["job_id"], request)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][calls[0].index("-frames:v") + 1], "16")
        docker = calls[1]
        self.assertEqual(docker[-2], "video")
        mounts = [docker[i + 1] for i, value in enumerate(docker[:-1]) if value == "-v"]
        self.assertTrue(any(":/input/asset.mp4:ro" in item for item in mounts))
        self.assertFalse(any(item.startswith(str(original_path) + ":") for item in mounts))
        self.assertEqual(original_path.read_bytes(), original_bytes)
        self.assertEqual(result["asset"]["semantic_content_index"]["source"], "image_visual_content")
        self.assertFalse(Path(calls[0][-1]).exists(), "temporary still-image clip must be removed")

    def test_semantic_search_uses_current_image_visual_vector(self):
        from story_builder.services.media_library import save_semantic_content_index
        image = self.upload_test_image()
        indexed = save_semantic_content_index(self.data, "workspace-a", image["asset_id"],
            source_sha256=image["sha256"], modality="image", model="facebook/pe-av-base", vector=[0.2, 0.8])
        fake_retrieval = type("Retrieval", (), {
            "_load_records": staticmethod(lambda _index: []),
            "search_records": staticmethod(lambda records, *_args, **_kwargs: {
                "results": [{**records[0], "score": 0.91}], "query_backend": "pe_av"}),
        })
        with patch.dict("os.environ", {"VIDEO_AUDIO_ANALYZER_PE_AV_WORKER_URL":"http://worker"}), \
             patch.object(media_semantic_search, "_retrieval_module", return_value=fake_retrieval), \
             patch.object(video_repertoire, "list_jobs", return_value=[]):
            result = media_semantic_search.search_workspace(self.data, "workspace-a", "red jacket", kind="image")
        self.assertEqual(result["results"][0]["asset"]["asset_id"], indexed["asset_id"])
        self.assertEqual(result["results"][0]["semantic_source"], "image_visual_content")

    def test_semantic_search_uses_current_raw_media_content_vector(self):
        from story_builder.services.media_library import save_semantic_content_index
        indexed = save_semantic_content_index(self.data, "workspace-a", self.source["asset_id"],
            source_sha256=self.source["sha256"], modality="video", model="facebook/pe-av-base", vector=[0.2, 0.8])
        fake_retrieval = type("Retrieval", (), {
            "_load_records": staticmethod(lambda _index: []),
            "search_records": staticmethod(lambda records, *_args, **_kwargs: {
                "results": [{**records[0], "score": 0.91}], "query_backend": "pe_av"}),
        })
        with patch.dict("os.environ", {"VIDEO_AUDIO_ANALYZER_PE_AV_WORKER_URL":"http://worker"}), \
             patch.object(media_semantic_search, "_retrieval_module", return_value=fake_retrieval), \
             patch.object(video_repertoire, "list_jobs", return_value=[]):
            result = media_semantic_search.search_workspace(self.data, "workspace-a", "rainy street", kind="video")
        self.assertEqual(result["results"][0]["asset"]["asset_id"], indexed["asset_id"])
        self.assertEqual(result["results"][0]["semantic_source"], "media_content")
        self.assertNotIn("vector", result["results"][0]["asset"]["semantic_content_index"])

    def test_semantic_index_route_is_explicit_and_gpu_guarded(self):
        app = create_app(data_root=self.data)
        indexed = {**self.source, "semantic_annotation_index":{"model":"facebook/pe-av-base"}}
        with patch("story_builder.isolated_server.gpu_workload_guard", return_value=nullcontext()) as guard, \
             patch("story_builder.isolated_server.index_media_asset_annotations", return_value=indexed) as index:
            status, result = self.request(app, "POST",
                f"/api/media/workspace-a/assets/{self.source['asset_id']}/semantic-index", {})
        self.assertEqual(status, "200 OK")
        self.assertTrue(result["indexed"])
        self.assertIn("not embedded", result["source"])
        guard.assert_called_once()
        index.assert_called_once_with(self.data.resolve(), "workspace-a", self.source["asset_id"])

    def test_semantic_search_route_uses_gpu_guard_and_workspace(self):
        app = create_app(data_root=self.data)
        expected = {"results": [], "query_backend": "pe_av", "reason": None}
        with patch("story_builder.isolated_server.gpu_workload_guard", return_value=nullcontext()) as guard, \
             patch("story_builder.isolated_server.search_media_semantically", return_value=expected) as search:
            status, result = self.request(app, "GET", "/api/media/workspace-a/assets/search",
                query_string="q=rainy+street&kind=image&limit=10")
        self.assertEqual(status, "200 OK")
        self.assertEqual(result, expected)
        guard.assert_called_once()
        search.assert_called_once_with(self.data.resolve(), "workspace-a", "rainy street",
            kind="image", limit=10, offset=0)

    def test_youtube_search_is_workspace_scoped_and_rejects_non_youtube_urls(self):
        app = create_app(data_root=self.data)
        with patch("story_builder.services.video_repertoire.resolve_youtube_sources", return_value={
                "source_mode": "search", "query": "courtroom", "candidates": [{
                    "url": "https://www.youtube.com/watch?v=abc", "video_id": "abc", "title": "Trial", "channel": "News"}]}):
            status, result = self.request(app, "POST", "/api/video-summariser/workspace-a/youtube/sources",
                {"mode": "search", "query": "courtroom", "count": 2})
        self.assertEqual(status, "200 OK")
        self.assertEqual(result["candidates"][0]["video_id"], "abc")
        with patch("story_builder.services.video_repertoire.resolve_youtube_sources", return_value={
                "source_mode": "paste", "query": "", "candidates": [{"url": "https://example.com/video.mp4"}]}):
            status, result = self.request(app, "POST", "/api/video-summariser/workspace-a/youtube/sources",
                {"mode": "paste", "urls_text": "https://example.com/video.mp4"})
        self.assertEqual(status, "400 Bad Request")

    def test_youtube_download_jobs_are_workspace_scoped_and_queue_without_network(self):
        app = create_app(data_root=self.data)
        url = "https://www.youtube.com/watch?v=abc"
        with patch("story_builder.services.video_repertoire.start_job", side_effect=lambda kind, job_id:
                   video_repertoire.read_job(kind, job_id)):
            status, job = self.request(app, "POST", "/api/video-summariser/workspace-a/youtube/jobs",
                {"urls": [{"url": url, "video_id": "abc", "title": "Trial", "channel": "News"}], "source_mode": "search"})
        self.assertEqual(status, "202 Accepted")
        self.assertEqual(job["request"]["workspace_id"], "workspace-a")
        status, listed = self.request(app, "GET", "/api/video-summariser/workspace-a/youtube/jobs")
        self.assertEqual(status, "200 OK")
        self.assertEqual([item["job_id"] for item in listed], [job["job_id"]])
        status, found = self.request(app, "GET", f"/api/video-summariser/workspace-a/youtube/jobs/{job['job_id']}")
        self.assertEqual(status, "200 OK")
        self.assertEqual(found["job_id"], job["job_id"])
        status, hidden = self.request(app, "GET", f"/api/video-summariser/workspace-b/youtube/jobs/{job['job_id']}")
        self.assertEqual(status, "404 Not Found")
        status, bad = self.request(app, "POST", "/api/video-summariser/workspace-a/youtube/jobs",
            {"urls": [{"url": "http://127.0.0.1:8080/admin"}]})
        self.assertEqual(status, "400 Bad Request")

    def test_youtube_worker_publishes_download_to_shared_workspace_library(self):
        from story_builder.services import video_repertoire_worker as worker
        source = self.data / "youtube_downloads" / "files" / "download.mp4"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes(self.source_file.read_bytes())
        job = video_repertoire.create_job("youtube", {"workspace_id": "workspace-a"})
        with patch.dict("os.environ", {"VIBE_DIRECTOR_DATA_DIR": str(self.data)}), \
             patch.object(worker, "_download_with_cli", return_value=(source, {"title": "Trial", "channel": "News", "id": "abc"})):
            result = worker.run_youtube(job["job_id"], {"workspace_id": "workspace-a",
                "urls": [{"url": "https://www.youtube.com/watch?v=abc"}], "source_mode": "paste"})
        self.assertEqual(len(result["published_assets"]), 1)
        self.assertEqual(result["published_assets"][0]["workspace_id"], "workspace-a")
        self.assertEqual(result["published_assets"][0]["metadata"]["source_url"], "https://www.youtube.com/watch?v=abc")


if __name__ == "__main__":
    unittest.main()
