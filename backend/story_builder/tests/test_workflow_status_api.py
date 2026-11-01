import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from story_builder.isolated_server import create_app
from story_builder.services.isolated_fl2va_contract import WORKFLOW_ID as FL2VA_ID
from story_builder.services.isolated_r2v_contract import WORKFLOW_ID as R2V_ID


class WorkflowStatusApiTest(unittest.TestCase):
    def test_page_catalog_and_library_routes_exist_without_generation(self):
        with tempfile.TemporaryDirectory() as folder:
            provider = lambda: {"available": False, "disabled_reason": "Disabled for route audit."}
            with patch("story_builder.isolated_server.image_workflow_catalog", return_value={"workflows": []}):
                app = create_app(data_root=Path(folder) / "data", capability_provider=provider,
                    fl2va_capability_provider=provider, r2v_capability_provider=provider,
                    gpu_reader=lambda: None,
                    reasoning_json_provider=lambda *args, **kwargs: self.fail("GET invoked reasoning"))
                workspace = "00000000-0000-4000-8000-000000000000"
                paths = [("/api/status", ""), ("/api/comfyui/queue", ""), ("/api/jobs/queue", ""), ("/api/video/runtime", ""),
                    ("/api/video/worker", ""), ("/api/images/worker", ""),
                    ("/api/images/workflows", ""), ("/api/styles/catalog", ""),
                    ("/api/story/workspaces", ""), (f"/api/media/{workspace}/assets/seo-styles", "")]
                paths += [(f"/api/media/{workspace}/assets", f"kind={kind}")
                          for kind in ("image", "video", "audio")]
                for path, query in paths:
                    with self.subTest(path=path, query=query):
                        started = []
                        response = json.loads(b"".join(app({"REQUEST_METHOD": "GET", "PATH_INFO": path,
                            "QUERY_STRING": query, "wsgi.input": io.BytesIO(b"")},
                            lambda status, headers: started.append(status))))
                        self.assertEqual(started, ["200 OK"], response)

    def test_status_reads_installed_preflights_without_submitting_jobs(self):
        with tempfile.TemporaryDirectory() as folder:
            supported = [FL2VA_ID, R2V_ID]
            app = create_app(data_root=Path(folder) / "data",
                capability_provider=lambda: {
                    "workflow_id": "minimax_h3_t2v_local_v1", "available": True,
                    "workflow_available": True, "feature_enabled": True,
                    "local_files": {"graph": {"present": True}},
                    "comfyui": {"reachable": True, "missing_nodes": []},
                },
                fl2va_capability_provider=lambda: {
                    "workflow_id": FL2VA_ID, "workflow_version": 1,
                    "label": "FL2VA", "available": False,
                    "disabled_reason": "No verified FL2VA smoke.",
                },
                r2v_capability_provider=lambda: {
                    "workflow_id": R2V_ID, "workflow_version": 1,
                    "label": "R2V", "available": True, "limits": {
                        "prompt_characters_exclusive": 7000,
                        "duration_seconds": [5, 15],
                    },
                },
                worker_status_provider=lambda: {
                    "enabled": True, "running": True, "available": True,
                    "worker_state": "running", "supported_workflows": supported,
                    "reason": None,
                },
                gpu_reader=lambda: {"temperature_c": 50, "graphics_clock_mhz": 1900})
            catalog = {"workflows": [
                {"workflow_id": "z_image_turbo", "label": "Z-Image", "available": True},
                {"workflow_id": "qwen_image_2512", "label": "Qwen Image", "available": False,
                 "disabled_reason": "Missing model."},
                {"workflow_id": "qwen_image_edit_2511", "label": "Qwen Edit", "available": True},
            ]}
            with patch("story_builder.isolated_server.image_workflow_catalog", return_value=catalog), \
                 patch("story_builder.isolated_server.urlopen") as urlopen:
                response_data = json.dumps({"queue_running": ["private"], "queue_pending": []}).encode()
                urlopen.return_value.__enter__.return_value.read.return_value = response_data
                started = []
                environ = {"REQUEST_METHOD": "GET", "PATH_INFO": "/api/status",
                    "QUERY_STRING": "", "wsgi.input": io.BytesIO(b"")}
                response = json.loads(b"".join(app(environ,
                    lambda status, headers: started.append(status))))

        self.assertEqual(started, ["200 OK"])
        workflows = {item["workflow_id"]: item for item in response["workflows"]}
        self.assertEqual(workflows[FL2VA_ID]["state"], "unavailable")
        self.assertIn("No verified FL2VA smoke", workflows[FL2VA_ID]["reason"])
        self.assertEqual(workflows[R2V_ID]["state"], "usable")
        self.assertEqual(workflows[R2V_ID]["prompt_limit"]["max"], 6999)
        self.assertFalse(workflows["z_image_turbo"]["available"])  # image worker is not running
        self.assertIn("Missing model", workflows["qwen_image_2512"]["reason"])
        self.assertEqual(response["comfyui_queue"]["running"], 1)
        self.assertEqual(response["comfyui_queue"]["pending"], 0)
        self.assertNotIn("private", repr(response["comfyui_queue"]))
        audio = [item for item in response["workflows"] if item.get("category") == "audio"]
        self.assertEqual(len(audio), 11)
        self.assertTrue(all(item.get("input_contract") for item in audio))
        self.assertTrue(all(item["state"] == "not_checked" for item in audio))
        self.assertTrue(response["local_queue"]["checked"])
        self.assertEqual(response["local_queue"]["pending"], 0)
        self.assertNotIn("job_id", repr(response["local_queue"]))


if __name__ == "__main__":
    unittest.main()
