import unittest

from story_builder.services.workflow_status import build_workflow_status


class WorkflowStatusTest(unittest.TestCase):
    def snapshot(self, *, safe=True, dispatch=True):
        return {
            "workflow_id": "minimax_h3_t2v_local_v1", "workflow_version": 1,
            "available": True, "workflow_available": True, "feature_enabled": True,
            "local_files": {"graph": {"present": True, "path": "/secret/graph.json"},
                           "unet": {"present": True, "path": "/secret/model.safetensors"}},
            "comfyui": {"reachable": True, "missing_nodes": [], "live_smoke": {"secret": True}},
            "runtime_guard": {"monitor_available": safe, "safe_to_submit": safe,
                              "temperature_cutoff_c": 83, "graphics_clock_ceiling_mhz": 2100,
                              "operating_point": {"temperature_c": 48, "graphics_clock_mhz": 1900},
                              "reason": None if safe else "GPU clock exceeds the configured ceiling."},
            "dispatch": {"enabled": dispatch, "running": dispatch, "available": dispatch,
                         "worker_state": "running" if dispatch else "disabled",
                         "reason": None if dispatch else "Worker dispatch is disabled."},
        }

    def test_path_free_exact_catalog_and_readiness_blockers(self):
        result = build_workflow_status(self.snapshot(), backend_connected=True)
        t2v = result["workflows"][0]
        self.assertEqual(t2v["state"], "usable")
        self.assertEqual(t2v["prompt_limit"]["max"], 6999)
        self.assertEqual(t2v["duration_seconds"], {"min": 5, "max": 10, "unit": "seconds"})
        self.assertEqual(t2v["outputs"], [{"preset": 0.98, "width": 1344, "height": 768}, {"preset": 0.4, "width": 864, "height": 480}])
        self.assertEqual(t2v["fixed_parameters"], {"seed": 1, "steps": 20, "aspect_ratio": "16:9", "reference_count": 0})
        self.assertTrue(all(row["state"] == "not_integrated" and row["available"] is False for row in result["workflows"][1:7]))
        audio = [row for row in result["workflows"] if row.get("category") == "audio"]
        self.assertEqual(len(audio), 11)
        self.assertTrue(all(row["state"] == "not_checked" and row["available"] is False for row in audio))
        self.assertTrue(all(row["graph_present"] is True for row in audio))
        self.assertTrue(all("model and node compatibility" in row["reason"] for row in audio))
        by_id = {row["workflow_id"]: row for row in audio}
        self.assertEqual(by_id["ace_step_music_api"]["input_limits"]["tags"]["max"], 4000)
        self.assertEqual(by_id["ace_step_music_api"]["input_limits"]["lyrics"]["max"], 10000)
        self.assertEqual(by_id["control_foley_text_audio_api"]["prompt_limit"]["max"], 4000)
        self.assertEqual(by_id["noise_cleanup_api"]["prompt_limit"]["unit"], "not applicable")
        self.assertIn("audio", by_id["noise_cleanup_api"]["input_roles"])
        self.assertNotIn("transcript", by_id["noise_cleanup_api"]["input_roles"])
        self.assertIn("transcript", by_id["emotion_edit_api"]["input_roles"])
        self.assertIn("transcript", by_id["style_edit_api"]["input_roles"])
        self.assertNotIn("production_vibevoice_dialogue_api", {row["workflow_id"] for row in audio})
        edit = next(row for row in result["workflows"] if row["workflow_id"] == "qwen_image_edit_2511")
        self.assertEqual(edit["input_roles"], ["image", "prompt"])
        self.assertEqual(edit["prompt_limit"]["max"], 6999)
        self.assertIn("workflow-specific lower limits", edit["prompt_limit"]["basis"])
        rendered = repr(result)
        self.assertNotIn("/secret/", rendered)
        self.assertNotIn("live_smoke", rendered)
        self.assertNotIn("secret", rendered)

    def test_audio_status_exposes_pinned_input_contract_without_claiming_readiness(self):
        from story_builder.services.workflow_status import _AUDIO_KNOWLEDGE_IDS

        knowledge = [{"workflow_id": knowledge_id, "nodes": [{
            "kind": "parameter_contract", "text": f"Local bounds for {workflow_id}."}]}
            for workflow_id, knowledge_id in _AUDIO_KNOWLEDGE_IDS.items()]
        audio = [row for row in build_workflow_status(self.snapshot(), backend_connected=True,
                    audio_workflow_knowledge=knowledge)["workflows"] if row.get("category") == "audio"]
        self.assertEqual(len(audio), len(_AUDIO_KNOWLEDGE_IDS))
        self.assertTrue(all(row["input_contract"].startswith("Local bounds for ") for row in audio))
        self.assertTrue(all(row["state"] == "not_checked" and row["available"] is False for row in audio))

    def test_audio_catalog_reports_a_missing_graph_explicitly(self):
        from unittest.mock import patch

        with patch("story_builder.services.workflow_status._AUDIO_ROOT") as audio_root:
            audio_root.__truediv__.return_value.is_file.return_value = False
            audio = [row for row in build_workflow_status(self.snapshot(), backend_connected=True)["workflows"]
                     if row.get("category") == "audio"]
        self.assertTrue(all(row["state"] == "not_integrated" for row in audio))
        self.assertTrue(all(row["graph_present"] is False for row in audio))
        self.assertTrue(all("Workflow file is missing" in row["reason"] for row in audio))

        blocked = build_workflow_status(self.snapshot(safe=False, dispatch=False), backend_connected=True)["workflows"][0]
        self.assertEqual(blocked["state"], "unavailable")
        self.assertIn("GPU clock exceeds", blocked["reason"])
        self.assertIn("Worker dispatch is disabled", blocked["reason"])

    def test_audio_status_checks_installed_node_types_without_claiming_runtime_ready(self):
        from story_builder.services.workflow_status import _AUDIO, _AUDIO_ROOT

        installed = set()
        for _, _, graph_name, _ in _AUDIO:
            import json
            graph = json.loads((_AUDIO_ROOT / graph_name).read_text(encoding="utf-8"))
            installed.update(node["class_type"] for node in graph.values()
                if isinstance(node, dict) and isinstance(node.get("class_type"), str))
        status = build_workflow_status(self.snapshot(), backend_connected=True,
            audio_object_info={node: {} for node in installed})
        audio = [row for row in status["workflows"] if row.get("category") == "audio"]
        self.assertTrue(all(row["nodes"] == {"checked": True, "missing_count": 0} for row in audio))
        self.assertTrue(all(row["state"] == "not_checked" and not row["available"] for row in audio))
        self.assertTrue(all("all graph node types are present" in row["reason"] for row in audio))

        partial = build_workflow_status(self.snapshot(), backend_connected=True,
            audio_object_info={"LoadAudio": {}})
        chatterbox = next(row for row in partial["workflows"]
            if row["workflow_id"] == "tts_multichar_timed_chatterbox_api")
        self.assertGreater(chatterbox["nodes"]["missing_count"], 0)
        self.assertFalse(chatterbox["available"])

    def test_comfyui_queue_is_counts_only_and_fails_closed_when_unknown(self):
        status = build_workflow_status(self.snapshot(), backend_connected=True,
            comfyui_queue={"checked": True, "running": 1, "pending": 2})
        self.assertEqual(status["comfyui_queue"],
            {"checked": True, "running": 1, "pending": 2, "reason": None})
        self.assertNotIn("prompt_id", repr(status["comfyui_queue"]))
        unknown = build_workflow_status(self.snapshot(), backend_connected=True,
            comfyui_queue={"checked": False, "running": 9, "pending": 1})
        self.assertEqual(unknown["comfyui_queue"]["running"], None)
        invalid = build_workflow_status(self.snapshot(), backend_connected=True,
            comfyui_queue={"checked": True, "running": True, "pending": -1})
        self.assertFalse(invalid["comfyui_queue"]["checked"])

    def test_installed_video_and_image_preflights_replace_placeholder_labels(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch

        video = [
            {"workflow_id": "minimax_h3_fl2va_first_last_v1", "workflow_version": 1,
             "label": "FL2VA", "available": False, "feature_enabled": True,
             "disabled_reason": "No verified FL2VA smoke.", "dispatch": {"available": True}},
            {"workflow_id": "minimax_h3_r2v_dynamic_v1", "workflow_version": 1,
             "label": "R2V", "available": True, "feature_enabled": True,
             "limits": {"prompt_characters_exclusive": 7000, "duration_seconds": [5, 15]},
             "dispatch": {"available": True}},
        ]
        image_catalog = {"workflows": [
            {"workflow_id": "z_image_turbo", "label": "Z Image", "version": "1", "available": True},
            {"workflow_id": "qwen_image_2512", "label": "Qwen Image", "version": "1",
             "available": False, "disabled_reason": "Missing model."},
            {"workflow_id": "qwen_image_edit_2511", "label": "Qwen Edit", "version": "1", "available": True},
        ]}
        with TemporaryDirectory() as directory:
            root = Path(directory)
            fl2va = root / "minimax_h3_fl2va_first_last_api.json"
            r2v = root / "minimax_h3_r2v_api.json"
            fl2va.touch()
            r2v.touch()
            with patch("story_builder.services.workflow_status._VIDEO_ROOT", root):
                result = build_workflow_status(self.snapshot(), backend_connected=True,
                    video_capabilities=video, image_catalog=image_catalog,
                    image_dispatch={"available": True})
                by_id = {row["workflow_id"]: row for row in result["workflows"]}
                self.assertEqual(by_id["minimax_h3_fl2va_first_last_v1"]["state"], "unavailable")
                self.assertIn("No verified FL2VA smoke", by_id["minimax_h3_fl2va_first_last_v1"]["reason"])
                self.assertTrue(by_id["minimax_h3_fl2va_first_last_v1"]["graph_present"])
                self.assertTrue(by_id["minimax_h3_r2v_dynamic_v1"]["available"])
                self.assertEqual(by_id["minimax_h3_r2v_dynamic_v1"]["prompt_limit"]["max"], 6999)
                self.assertTrue(by_id["minimax_h3_r2v_dynamic_v1"]["graph_present"])
                r2v.unlink()
                result = build_workflow_status(self.snapshot(), backend_connected=True,
                    video_capabilities=video, image_catalog=image_catalog,
                    image_dispatch={"available": True})
                r2v_status = next(row for row in result["workflows"]
                    if row["workflow_id"] == "minimax_h3_r2v_dynamic_v1")
                self.assertFalse(r2v_status["graph_present"])
                self.assertFalse(r2v_status["available"])
                self.assertIn("workflow graph file is missing", r2v_status["reason"])
        self.assertTrue(by_id["z_image_turbo"]["available"])
        self.assertIn("Missing model", by_id["qwen_image_2512"]["reason"])
        self.assertFalse(by_id["qwen_image_2512"]["available"])

    def test_image_readiness_also_requires_worker_and_gpu(self):
        ids = ("z_image_turbo", "qwen_image_2512", "qwen_image_edit_2511", "qwen_image_multi_angle_2511")
        result = build_workflow_status(self.snapshot(safe=False), backend_connected=True,
            image_catalog={"workflows": [{"workflow_id": identifier, "available": True} for identifier in ids]},
            image_dispatch={"available": False, "reason": "Image worker is stopped."})
        image_rows = [row for row in result["workflows"] if row.get("category") == "image"]
        self.assertEqual(len(image_rows), 4)
        self.assertTrue(all(not row["available"] for row in image_rows))
        self.assertTrue(all("GPU clock exceeds" in row["reason"] for row in image_rows))
        self.assertTrue(all("Image worker is stopped" in row["reason"] for row in image_rows))

    def test_monitor_and_disconnected_backend_cannot_claim_ready(self):
        snapshot = self.snapshot()
        snapshot["runtime_guard"]["monitor_available"] = False
        t2v = build_workflow_status(snapshot, backend_connected=True)["workflows"][0]
        self.assertFalse(t2v["available"])
        self.assertIn("GPU safety", t2v["reason"])
        result = build_workflow_status(self.snapshot(), backend_connected=False,
            image_catalog={"workflows": [{"workflow_id": "z_image_turbo", "available": True}]},
            image_dispatch={"available": True})
        self.assertTrue(all(not item["available"] for item in result["workflows"]))

    def test_bad_installation_is_not_overridden_by_available_flag(self):
        for change in ("graph", "model", "nodes", "feature"):
            with self.subTest(change=change):
                snapshot = self.snapshot()
                if change == "graph": snapshot["local_files"]["graph"]["present"] = False
                if change == "model": snapshot["local_files"]["unet"]["present"] = False
                if change == "nodes": snapshot["comfyui"]["missing_nodes"] = ["MissingNode"]
                if change == "feature": snapshot["feature_enabled"] = False
                result = build_workflow_status(snapshot, backend_connected=True)["workflows"][0]
                self.assertFalse(result["available"])
                self.assertFalse(result["workflow_available"])

    def test_ready_does_not_imply_render_or_owner_acceptance(self):
        snapshot = self.snapshot()
        # A manifest alone has not passed the capability's hash/output checks.
        snapshot["live_smoke"] = {"status": "completed"}
        row = build_workflow_status(snapshot, backend_connected=True)["workflows"][0]
        self.assertTrue(row["available"])
        self.assertFalse(row["render_verified"])
        self.assertEqual(row["acceptance"], "not_recorded")
        snapshot["render_verified"] = True
        self.assertTrue(build_workflow_status(snapshot, backend_connected=True)["workflows"][0]["render_verified"])


if __name__ == "__main__":
    unittest.main()
