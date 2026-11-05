from __future__ import annotations

import hashlib
import json
import io
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from story_builder.services.isolated_r2v_contract import (
    EXPECTED_GRAPH_SHA256, GRAPH_PATH, WORKFLOW_ID, R2VContractError,
    compile_preview, normalize_request, plan_from_request,
)
from story_builder.services.isolated_video_jobs import IsolatedVideoJobs
from story_builder.services.isolated_r2v_assets import R2VStagingError
from story_builder.services.production_ledger import ProductionLedger, stable_hash
from story_builder.services.production_r2v_capability import r2v_capability, record_successful_r2v_smoke
from story_builder.services.minimax_h3_graph_compiler import GraphPlanError, ResolvedAsset, compile_r2v_graph, validate_comfy_capabilities
from story_builder.services.isolated_video_jobs import prepare_isolated_take
from story_builder.isolated_server import create_app

READY = {"available": True, "workflow_id": WORKFLOW_ID}


def request(**changes):
    row = {"workflow_id": WORKFLOW_ID, "workflow_version": 1,
        "workflow_sha256": EXPECTED_GRAPH_SHA256,
        "prompt": "Use <Picture 1> as the character identity reference.",
        "duration_seconds": 5, "aspect_ratio": "16:9", "resolution_preset": 0.98,
        "steps": 20, "seed": 1, "ref_image_size": "match",
        "images": [{"asset_id": "pa-0123456789abcdef", "sha256": "a" * 64,
            "role": "character_identity", "intent": "Match the lead character."}],
        "videos": [], "audios": []}
    row.update(changes)
    return row


class R2VSocketCapabilityTests(TestCase):
    def nodes(self):
        nodes = {name: {} for name in ("MiniMaxH3ReferenceToVideo", "LoadImage", "LoadAudio", "VHS_LoadVideo", "CreateVideo", "SaveVideo")}
        nodes["MiniMaxH3ReferenceToVideo"] = {"input": {
            "required": {key: [] for key in ("clip", "prompt", "width", "height", "length", "ref_image_size")},
            "optional": {key: [] for key in ("vae", "audio_vae", "ref_images", "ref_videos", "ref_video_audios", "ref_audios")}}}
        nodes["VHS_LoadVideo"] = {"input": {"required": {key: [] for key in
            ("video", "force_rate", "custom_width", "custom_height", "frame_load_cap", "skip_first_frames", "select_every_nth")}}}
        return nodes

    def test_installed_optional_vae_sockets_are_supported(self):
        self.assertEqual(validate_comfy_capabilities(self.nodes())["status"], "ready")

    def test_legacy_required_vae_sockets_remain_supported(self):
        nodes = self.nodes(); inputs = nodes["MiniMaxH3ReferenceToVideo"]["input"]
        for key in ("vae", "audio_vae"):
            inputs["required"][key] = inputs["optional"].pop(key)
        self.assertEqual(validate_comfy_capabilities(nodes)["status"], "ready")

    def test_missing_workflow_sockets_are_rejected_with_names(self):
        for key in ("clip", "prompt", "width", "height", "length", "ref_image_size", "vae", "audio_vae"):
            with self.subTest(socket=key):
                nodes = self.nodes(); inputs = nodes["MiniMaxH3ReferenceToVideo"]["input"]
                for group in ("required", "optional"):
                    inputs[group].pop(key, None)
                with self.assertRaisesRegex(GraphPlanError, "lacks workflow inputs: " + key):
                    validate_comfy_capabilities(nodes)

    def test_reference_groups_and_video_loader_still_required(self):
        for key in ("ref_images", "ref_videos", "ref_video_audios", "ref_audios"):
            with self.subTest(group=key):
                nodes = self.nodes(); del nodes["MiniMaxH3ReferenceToVideo"]["input"]["optional"][key]
                with self.assertRaisesRegex(GraphPlanError, "autogrow reference input"):
                    validate_comfy_capabilities(nodes)
        nodes = self.nodes(); del nodes["VHS_LoadVideo"]["input"]["required"]["video"]
        with self.assertRaisesRegex(GraphPlanError, "loader lacks required inputs"):
            validate_comfy_capabilities(nodes)


class IsolatedR2VContractTests(TestCase):
    def test_story_r2v_admission_accepts_only_its_pinned_style_media(self):
        import binascii
        import struct
        import zlib
        from story_builder.services.media_library import link_style_reference

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            app = create_app(data_root=root,
                r2v_capability_provider=lambda: {"workflow_id": WORKFLOW_ID, "available": True},
                worker_status_provider=lambda: {"enabled": True, "running": True,
                    "available": True, "supported_workflows": [WORKFLOW_ID]},
                gpu_reader=lambda: {"temperature_c": 40.0, "graphics_clock_mhz": 1200.0})

            def call(method, path, payload=None, body=None, content_type="application/json"):
                data = body if body is not None else (json.dumps(payload).encode() if payload is not None else b"")
                status = []
                path_only, _, query = path.partition("?")
                response = b"".join(app({"REQUEST_METHOD": method, "PATH_INFO": path_only,
                    "QUERY_STRING": query, "CONTENT_TYPE": content_type,
                    "CONTENT_LENGTH": str(len(data)), "wsgi.input": io.BytesIO(data)},
                    lambda code, _headers: status.append(code)))
                return status[0], json.loads(response)

            def png():
                def chunk(name, data):
                    body = name + data
                    return (struct.pack(">I", len(data)) + body
                        + struct.pack(">I", binascii.crc32(body) & 0xffffffff))
                row = b"\0\xff\x00\x00\xff\x00\xff\x00"
                return (b"\x89PNG\r\n\x1a\n"
                    + chunk(b"IHDR", struct.pack(">IIBBBBB", 2, 1, 8, 2, 0, 0, 0))
                    + chunk(b"IDAT", zlib.compress(row)) + chunk(b"IEND", b""))

            _, catalog = call("GET", "/api/styles/catalog")
            style = catalog["production_types"][0]
            direction = catalog["directing_styles"][0]
            setup_id = "setup-r2v-style"
            status, saved = call("POST", "/api/styles/selections", {
                "isolated_context_id": setup_id, "production_type": style["production_type"],
                "style_version_id": style["style_version_id"],
                "directing_style_id": direction["style_id"]})
            self.assertEqual(status, "201 Created")
            status, image = call("POST", f"/api/media/{setup_id}/assets?filename=style.png&role=style_reference",
                body=png(), content_type="application/octet-stream")
            self.assertEqual(status, "201 Created")
            status, _ = call("POST", f"/api/media/{setup_id}/assets/{image['asset_id']}/style-reference",
                {"directing_style_id": direction["style_id"]})
            self.assertEqual(status, "200 OK", _)
            status, created = call("POST", "/api/story/workspaces", {
                "idempotency_key": "00000000-0000-4000-8000-000000000021",
                "title": "Pinned style", "source_text": "A story.",
                "style_selection_snapshot_id": saved["snapshot_id"]})
            self.assertEqual(status, "201 Created")
            story_id = created["workspace"]["workspace_id"]
            style_request = request(prompt="Use <Picture 1> as the visual style reference.",
                images=[{"asset_id": image["asset_id"], "sha256": image["sha256"],
                    "role": "visual_style", "intent": "Match the production style."}])
            status, accepted = call("POST", "/api/video/jobs", {"workspace_id": story_id,
                "clip_id": "scene-1-shot-1", "idempotency_key": "style-reference-r2v",
                "request": style_request})
            self.assertEqual(status, "202 Accepted", accepted)

            status, _archived = call("POST",
                f"/api/media/{setup_id}/assets/{image['asset_id']}/archive", {})
            self.assertEqual(status, "200 OK", _archived)
            status, accepted_archived_reference = call("POST", "/api/video/jobs", {
                "workspace_id": story_id, "clip_id": "scene-1-shot-2",
                "idempotency_key": "archived-style-reference-r2v", "request": style_request})
            self.assertEqual(status, "202 Accepted", accepted_archived_reference)

            status, unpinned = call("POST", "/api/story/workspaces", {
                "idempotency_key": "00000000-0000-4000-8000-000000000022",
                "title": "Unpinned", "source_text": "Another story."})
            self.assertEqual(status, "201 Created")
            status, rejected = call("POST", "/api/video/jobs", {
                "workspace_id": unpinned["workspace"]["workspace_id"],
                "clip_id": "scene-1-shot-1", "idempotency_key": "unavailable-style-r2v",
                "request": style_request})
            self.assertEqual(status, "422 Unprocessable Entity")
            self.assertIn("not available", rejected["error"]["message"])

    def test_pinned_graph_and_typed_preview_compile_reference_tag_and_alignment(self):
        raw = GRAPH_PATH.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), EXPECTED_GRAPH_SHA256)
        preview = compile_preview(request())
        self.assertTrue(preview["preview_only"])
        self.assertFalse(preview["submission_performed"])
        self.assertEqual(preview["reference_map"]["pictures"][0]["tag"], "<Picture 1>")
        self.assertEqual(preview["compiled"]["frame_count"], 124)
        graph = preview["graph"]
        self.assertEqual(graph["136"]["inputs"]["ref_images.ref_image_0"][0], "137")
        self.assertEqual(graph["137"]["inputs"]["image"], "preview-pa-0123456789abcdef.png")

    def test_one_voice_asset_can_be_explicitly_shared_by_multiple_characters(self):
        payload = request(
            prompt="Use <Picture 1> for Mira and <Audio 1> as the shared voice for Mira (character-mira) and Sol (character-sol).",
            audios=[{"asset_id": "voice-0123456789abcdef", "sha256": "b" * 64,
                "role": "character_voice", "intent": "Shared voice reference.",
                "speaker_ids": ["character-mira", "character-sol"]}],
        )
        preview = compile_preview(payload)
        self.assertEqual(preview["reference_map"]["speaker_audio_tags"], {
            "character-mira": "<Audio 1>", "character-sol": "<Audio 1>"})
        self.assertEqual(len([node for node in preview["graph"].values()
            if node.get("class_type") == "LoadAudio"]), 1)
        self.assertEqual(preview["request"]["audios"][0]["speaker_ids"],
            ["character-mira", "character-sol"])

    def test_assisted_shared_voice_intent_punctuation_does_not_break_bindings(self):
        speakers = [f"character-{index}-" + "x" * 60 for index in range(12)]
        clip = {"workflow_id": WORKFLOW_ID, "duration_seconds": 6,
            "prompt": "Two characters exchange a greeting.", "references": [{
                "kind": "audio", "asset_id": "voice-0123456789abcdef", "sha256": "b" * 64,
                "role": "voice", "intent": "Use this voice. Preserve the dialogue.\nKeep its tone.",
                "speaker_ids": speakers}]}
        payload = IsolatedVideoJobs._assisted_request(None,
            {"setup": {"video_quality": "standard"}}, clip)
        preview = compile_preview(payload)
        self.assertEqual(preview["reference_map"]["speaker_audio_tags"],
            {speaker: "<Audio 1>" for speaker in speakers})
        self.assertEqual(len([node for node in preview["graph"].values()
            if node.get("class_type") == "LoadAudio"]), 1)

        # Selection validation compiles placeholder bindings before prompt authoring.
        plan = plan_from_request(normalize_request(payload), "preview", "preview", "preview")
        compiled = compile_r2v_graph(plan, {"voice-0123456789abcdef": ResolvedAsset(
            "voice-0123456789abcdef", "audio", "voice.wav", "b" * 64)}, reference_map_only=True)
        self.assertEqual(compiled.reference_map.speaker_audio_tags,
            {speaker: "<Audio 1>" for speaker in speakers})

    def test_assisted_paired_soundtrack_precedes_standalone_voice_tags(self):
        clip = {"workflow_id": WORKFLOW_ID, "duration_seconds": 6,
            "prompt": "A character speaks beside the river.", "references": [{
                "kind": "video", "asset_id": "video-0123456789abcdef", "sha256": "c" * 64,
                "role": "style", "intent": "Match the lighting.", "start_sec": None,
                "end_sec": None, "include_paired_soundtrack": True,
                "audio_intent": "Use the river ambience."}, {
                "kind": "audio", "asset_id": "voice-0123456789abcdef", "sha256": "b" * 64,
                "role": "voice", "intent": "Use this voice.", "speaker_ids": ["character-mira"]}]}
        payload = IsolatedVideoJobs._assisted_request(None,
            {"setup": {"video_quality": "standard"}}, clip)
        preview = compile_preview(payload)
        self.assertIn("<Audio 1> is the soundtrack of <Video 1>", payload["prompt"])
        self.assertEqual(preview["reference_map"]["speaker_audio_tags"],
            {"character-mira": "<Audio 2>"})

    def test_client_paths_unknown_hash_and_tag_mismatch_rejected(self):
        for bad in (
            request(images=[{"asset_id": "../../etc/passwd", "sha256": "a" * 64,
                "role": "x", "intent": "y"}]),
            request(workflow_sha256="0" * 64),
        ):
            with self.assertRaises(R2VContractError):
                normalize_request(bad)
        with self.assertRaises(R2VContractError):
            compile_preview(request(prompt="No reference tag."))

    def test_limits_and_zero_reference_route(self):
        with self.assertRaises(R2VContractError) as error:
            normalize_request(request(prompt="x" * 7000))
        self.assertEqual(error.exception.code, "prompt_too_long")
        with self.assertRaises(R2VContractError) as error:
            compile_preview(request(images=[]))
        self.assertEqual(error.exception.code, "zero_reference_route")

    def test_job_replay_persists_canonical_request_hash_and_r2v_gate_is_independent(self):
        with tempfile.TemporaryDirectory() as temporary:
            ledger = ProductionLedger(Path(temporary) / "ledger.sqlite3")
            unavailable = IsolatedVideoJobs(ledger, r2v_capability_provider=lambda: {"available": False, "disabled_reason": "R2V smoke missing"})
            with self.assertRaisesRegex(ValueError, "R2V smoke missing"):
                unavailable.create_job(workspace_id="ws", clip_id="c1", idempotency_key="blocked", request=request())
            jobs = IsolatedVideoJobs(ledger, r2v_capability_provider=lambda: READY)
            first = jobs.create_job(workspace_id="ws", clip_id="c1", idempotency_key="r2v-one", request=request())
            second = IsolatedVideoJobs(ProductionLedger(Path(temporary) / "ledger.sqlite3"),
                r2v_capability_provider=lambda: READY).create_job(
                    workspace_id="ws", clip_id="c1", idempotency_key="r2v-one", request=request())
            self.assertEqual(first["job_id"], second["job_id"])
            self.assertEqual(first["request_hash"], second["request_hash"])
            self.assertEqual(first["request"]["workflow_id"], WORKFLOW_ID)

    def test_manual_bootstrap_preserves_assisted_admission_gate(self):
        from unittest.mock import Mock
        from story_builder.isolated_worker import _CapabilityGatedWorker

        with tempfile.TemporaryDirectory() as temporary:
            ledger = ProductionLedger(Path(temporary) / "ledger.sqlite3")
            capability = {"available": True, "automation_available": False,
                "automation_disabled_reason": "R2V verified output required"}
            jobs = IsolatedVideoJobs(ledger, r2v_capability_provider=lambda: capability)
            for binding in ({"_assisted_run_clip": ("clip",)},):
                with self.assertRaisesRegex(ValueError, "verified output required"):
                    jobs.create_job(workspace_id="ws", clip_id="c1", idempotency_key="auto",
                        request=request(), **binding)
            job = jobs.create_job(workspace_id="ws", clip_id="c1", idempotency_key="manual",
                request=request())
            source = Mock()
            take = jobs._take_and_meta(job["job_id"])[0]
            source.process_one.return_value = {"status": "needs_review", "take_id": take["take_id"]}
            gated = _CapabilityGatedWorker(source, ledger, Mock(),
                r2v_provider=lambda: capability, data_root=temporary)
            with ledger._connect() as db:
                db.execute("UPDATE production_takes SET output_hashes_json=? WHERE take_id=?",
                    (json.dumps([{"mock": True}]), take["take_id"]))
            with patch("story_builder.isolated_worker._runtime_guard", return_value={"safe_to_submit": True}), patch(
                    "story_builder.isolated_worker.record_successful_r2v_smoke", return_value=True) as record:
                self.assertEqual(gated.process_one()["status"], "needs_review")
            source.process_one.assert_called_once()
            self.assertEqual(record.call_args.kwargs["job_id"], job["job_id"])
            self.assertEqual(record.call_args.kwargs["request"]["workflow_id"], WORKFLOW_ID)

    def test_create_job_rejects_empty_or_tag_mismatched_r2v_before_persisting(self):
        with tempfile.TemporaryDirectory() as temporary:
            ledger = ProductionLedger(Path(temporary) / "ledger.sqlite3")
            jobs = IsolatedVideoJobs(ledger, r2v_capability_provider=lambda: READY)
            for bad_request in (request(images=[]), request(prompt="A shot without its required reference tag.")):
                with self.subTest(request=bad_request):
                    with self.assertRaises(ValueError):
                        jobs.create_job(workspace_id="ws", clip_id="clip",
                            idempotency_key="invalid-" + str(len(bad_request["images"])),
                            request=bad_request)
            self.assertEqual(ledger.list_runs(project_id="ws"), [])

    def test_api_status_and_admission_use_r2v_readiness(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            app = create_app(data_root=root,
                r2v_capability_provider=lambda: {"workflow_id": WORKFLOW_ID,
                    "available": False, "disabled_reason": "R2V smoke is missing"},
                worker_status_provider=lambda: {"enabled": True, "running": True,
                    "available": True, "supported_workflows": [WORKFLOW_ID]},
                gpu_reader=lambda: {"temperature_c": 40.0, "graphics_clock_mhz": 1200.0})
            status = []
            body = b"".join(app({"REQUEST_METHOD": "GET", "PATH_INFO": "/api/video/capabilities",
                "QUERY_STRING": f"workflow_id={WORKFLOW_ID}"},
                lambda code, _headers: status.append(code)))
            self.assertEqual(status[0], "200 OK")
            self.assertIn("R2V smoke is missing", json.loads(body)["disabled_reason"])
            payload = json.dumps({"workspace_id": "ws", "clip_id": "clip",
                "idempotency_key": "blocked-r2v", "request": request()}).encode()
            status.clear()
            body = b"".join(app({"REQUEST_METHOD": "POST", "PATH_INFO": "/api/video/jobs",
                "QUERY_STRING": "", "CONTENT_TYPE": "application/json",
                "CONTENT_LENGTH": str(len(payload)), "wsgi.input": io.BytesIO(payload)},
                lambda code, _headers: status.append(code)))
            self.assertEqual(status[0], "503 Service Unavailable")
            self.assertIn("R2V smoke is missing", json.loads(body)["capability"]["disabled_reason"])
            self.assertEqual(ProductionLedger(root / "services/production/ledger.sqlite3")
                .list_runs(project_id="ws"), [])

    def test_worker_prepare_rechecks_r2v_readiness_before_staging_and_compiles_staged_assets(self):
        import story_builder.services.isolated_video_jobs as jobs_module

        frozen = normalize_request(request())
        take = {"input_snapshot": frozen, "input_hash": stable_hash(frozen),
            "project_id": "ws", "run_id": "run", "shot_id": "clip",
            "take_id": "take", "job_id": "job"}
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        media_root, input_root, owner_root = root / "media", root / "ComfyUI/input", root / "owners"
        input_root.mkdir(parents=True)
        stages = []
        def stage(**kwargs):
            stages.append(kwargs)
            row = frozen["images"][0]
            return {row["asset_id"]: ResolvedAsset(row["asset_id"], "image",
                "owner_image.png", row["sha256"])}
        with patch.object(jobs_module, "stage_r2v_references", side_effect=stage):
            with self.assertRaisesRegex(RuntimeError, "readiness failed"):
                prepare_isolated_take(take, media_root=media_root, comfy_input_root=input_root,
                    r2v_owner_root=owner_root,
                    r2v_capability_provider=lambda: {"available": False,
                        "disabled_reason": "R2V readiness failed"})
            self.assertEqual(stages, [])
            prepared = prepare_isolated_take(take, media_root=media_root, comfy_input_root=input_root,
                r2v_owner_root=owner_root,
                r2v_capability_provider=lambda: {"available": True})
        self.assertTrue(prepared.graph["136"]["inputs"]["ref_images.ref_image_0"])
        image = prepared.graph["137"]["inputs"]["image"]
        self.assertEqual(image, "owner_image.png")
        self.assertEqual(len(stages), 1)
        self.assertEqual(stages[0]["request"]["workflow_id"], WORKFLOW_ID)
        prepared.cleanup()

    def test_prepare_failure_does_not_cleanup_through_symlinked_job_directory(self):
        frozen = normalize_request(request())
        take = {"input_snapshot": frozen, "input_hash": stable_hash(frozen),
            "project_id": "ws", "run_id": "run", "shot_id": "clip",
            "take_id": "take", "job_id": "job"}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            input_root, owner_root, outside = root / "input", root / "owners", root / "outside"
            input_root.mkdir()
            owner_root.mkdir()
            outside.mkdir()
            sentinel = outside / "keep.txt"
            sentinel.write_text("preserve", encoding="utf-8")
            (owner_root / "job").symlink_to(outside, target_is_directory=True)
            with self.assertRaisesRegex(R2VStagingError, "symlinks"):
                prepare_isolated_take(take, media_root=root / "media",
                    comfy_input_root=input_root, r2v_owner_root=owner_root,
                    r2v_capability_provider=lambda: {"available": True})
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "preserve")

    def test_capability_requires_r2v_specific_model_node_flag_and_smoke_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for relative in ("diffusion_models/minimax_h3_ref2va_pruned_int8_convrot.safetensors",
                             "vae/minimax_h3_video_vae_fp16.safetensors",
                             "vae/minimax_h3_audio_vae_fp32.safetensors",
                             "text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors"):
                model = root / "models" / relative
                model.parent.mkdir(parents=True, exist_ok=True)
                model.write_bytes(b"fixture")
            graph = json.loads(GRAPH_PATH.read_text())
            node_names = {node["class_type"] for node in graph.values()} | {"LoadAudio", "VHS_LoadVideo"}
            nodes = {name: {"input": {"required": {}, "optional": {}}} for name in node_names}
            nodes["MiniMaxH3ReferenceToVideo"]["input"]["required"] = {
                key: [] for key in ("clip", "vae", "audio_vae", "prompt", "width", "height", "length", "ref_image_size")}
            nodes["MiniMaxH3ReferenceToVideo"]["input"]["optional"] = {
                key: [] for key in ("ref_images", "ref_videos", "ref_video_audios", "ref_audios")}
            nodes["VHS_LoadVideo"]["input"]["required"] = {
                key: [] for key in ("video", "force_rate", "custom_width", "custom_height", "frame_load_cap", "skip_first_frames", "select_every_nth")}
            smoke = root / "manifest.json"
            output = root / "clip.mp4"
            output.write_bytes(b"verified fixture")
            digest = hashlib.sha256(output.read_bytes()).hexdigest()
            smoke.write_text(json.dumps({"workflow_id": WORKFLOW_ID, "workflow_version": 1,
                "workflow_sha256": EXPECTED_GRAPH_SHA256, "status": "completed",
                "has_video": True, "has_audio": True,
                "reference_map": {"pictures": [{"tag": "<Picture 1>"}], "videos": [], "audios": []},
                "outputs": [{"kind": "video", "relative_path": "clip.mp4", "sha256": digest,
                    "probe": {"streams": [{"codec_type": "video"}, {"codec_type": "audio"}]}}]}))
            with patch.dict("os.environ", {"VIBE_DIRECTOR_ENABLE_R2V": "1"}, clear=False):
                result = r2v_capability(root=root, object_info=nodes, smoke_path=smoke)
            self.assertTrue(result["available"])
            missing_core = dict(nodes)
            missing_core.pop("UNETLoader")
            with patch.dict("os.environ", {"VIBE_DIRECTOR_ENABLE_R2V": "1"}, clear=False):
                rejected_core = r2v_capability(root=root, object_info=missing_core, smoke_path=smoke)
            self.assertFalse(rejected_core["available"])
            self.assertIn("UNETLoader", rejected_core["disabled_reason"])
            t2v_smoke = json.loads(smoke.read_text())
            t2v_smoke["workflow_id"] = "minimax_h3_t2v_local_v1"
            smoke.write_text(json.dumps(t2v_smoke))
            with patch.dict("os.environ", {"VIBE_DIRECTOR_ENABLE_R2V": "1"}, clear=False):
                rejected = r2v_capability(root=root, object_info=nodes, smoke_path=smoke)
            self.assertTrue(rejected["available"])
            self.assertFalse(rejected["automation_available"])
            self.assertFalse(rejected["render_verified"])
            self.assertIn("R2V video+audio smoke", rejected["automation_disabled_reason"])
            with patch.dict("os.environ", {"VIBE_DIRECTOR_ENABLE_R2V": "0"}, clear=False):
                disabled = r2v_capability(root=root, object_info=nodes, smoke_path=smoke)
            self.assertFalse(disabled["available"])
            self.assertFalse(disabled["automation_available"])
            smoke.unlink()
            with patch.dict("os.environ", {"VIBE_DIRECTOR_ENABLE_R2V": "1"}, clear=False):
                first_test = r2v_capability(root=root, object_info=nodes, smoke_path=smoke)
            self.assertTrue(first_test["available"])
            self.assertFalse(first_test["automation_available"])
            # Mock collector output: this does not represent a GPU render.
            collected = {"relative_path": "clip.mp4", "sha256": digest,
                "has_video": True, "has_audio": True,
                "probe": {"streams": [{"codec_type": "video"}, {"codec_type": "audio"}]}}
            self.assertFalse(record_successful_r2v_smoke(data_root=root, request=request(),
                job_id="job-no-audio", output={**collected, "has_audio": False}))
            self.assertTrue(record_successful_r2v_smoke(data_root=root, request=request(),
                job_id="job-valid", output=collected))
            recorded = root / ".vibe-director-r2v-smoke.json"
            with patch.dict("os.environ", {"VIBE_DIRECTOR_ENABLE_R2V": "1"}, clear=False):
                verified = r2v_capability(root=root, object_info=nodes, smoke_path=recorded)
            self.assertTrue(verified["automation_available"])
            output.write_bytes(b"changed output")
            with patch.dict("os.environ", {"VIBE_DIRECTOR_ENABLE_R2V": "1"}, clear=False):
                tampered = r2v_capability(root=root, object_info=nodes, smoke_path=recorded)
            self.assertTrue(tampered["available"])
            self.assertFalse(tampered["automation_available"])
