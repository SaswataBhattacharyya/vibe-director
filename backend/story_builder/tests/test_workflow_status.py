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
        self.assertTrue(all(row["state"] == "not_integrated" and row["available"] is False for row in result["workflows"][1:]))
        edit = next(row for row in result["workflows"] if row["workflow_id"] == "qwen_image_edit_2511")
        self.assertEqual(edit["input_roles"], ["image", "prompt"])
        rendered = repr(result)
        self.assertNotIn("/secret/", rendered)
        self.assertNotIn("live_smoke", rendered)
        self.assertNotIn("secret", rendered)

        blocked = build_workflow_status(self.snapshot(safe=False, dispatch=False), backend_connected=True)["workflows"][0]
        self.assertEqual(blocked["state"], "unavailable")
        self.assertIn("GPU clock exceeds", blocked["reason"])
        self.assertIn("Worker dispatch is disabled", blocked["reason"])


if __name__ == "__main__":
    unittest.main()
