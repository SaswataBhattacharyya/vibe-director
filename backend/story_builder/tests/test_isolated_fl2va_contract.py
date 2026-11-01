from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from story_builder.services.isolated_fl2va_contract import (
    EXPECTED_GRAPH_SHA256, FL2VAContractError, compile_preview, normalize_request,
)

ROOT = Path(__file__).resolve().parents[1]
GRAPH = ROOT / "workflows/api/minimax_h3_fl2va_first_last_api.json"


def image(asset_id: str, marker: str) -> dict[str, str]:
    return {"asset_id": asset_id, "sha256": marker * 64}


def request(**changes):
    result = {
        "workflow_id": "minimax_h3_fl2va_first_last_v1", "workflow_version": 1,
        "workflow_sha256": EXPECTED_GRAPH_SHA256, "prompt": "Move from the first frame to the last.",
        "duration_seconds": 6, "aspect_ratio": "16:9", "resolution_preset": 0.98,
        "first_frame": image("image-first", "a"), "last_frame": image("image-last", "b"),
    }
    result.update(changes)
    return result


class IsolatedFL2VAContractTests(unittest.TestCase):
    def test_requires_ordered_role_inputs_and_rejects_paths(self):
        for bad in (
            request(first_frame=None), request(last_frame=None),
            request(first_frame={"asset_id": "../outside", "sha256": "a" * 64}),
            request(last_frame={"asset_id": "/tmp/frame.png", "sha256": "b" * 64}),
            request(first_frame={"asset_id": "ok", "path": "/tmp/frame.png", "sha256": "a" * 64}),
            request(last_frame={"asset_id": "ok", "sha256": "z" * 64}),
        ):
            with self.subTest(bad=bad), self.assertRaises(FL2VAContractError):
                normalize_request(bad)
        normalized = normalize_request(request())
        self.assertEqual(normalized["first_frame"]["asset_id"], "image-first")
        self.assertEqual(normalized["last_frame"]["asset_id"], "image-last")

    def test_prompt_duration_and_settings_limits(self):
        self.assertEqual(len(normalize_request(request(prompt="x" * 6999))["prompt"]), 6999)
        for bad in (
            request(prompt="x" * 7000), request(prompt="  "),
            request(duration_seconds=4.99), request(duration_seconds=15.01),
            request(duration_seconds=True), request(duration_seconds=float("nan")),
            request(duration_seconds=10**1000), request(aspect_ratio="9:16"),
            request(resolution_preset=0.7), request(resolution_preset=10**1000),
            request(unexpected="value"),
        ):
            with self.subTest(bad=bad), self.assertRaises(FL2VAContractError):
                normalize_request(bad)

    def test_graph_is_vendored_byte_exact_and_drift_is_rejected(self):
        self.assertEqual(hashlib.sha256(GRAPH.read_bytes()).hexdigest(), EXPECTED_GRAPH_SHA256)
        self.assertEqual(normalize_request(request())["workflow_sha256"], EXPECTED_GRAPH_SHA256)
        with tempfile.TemporaryDirectory() as directory:
            changed = Path(directory) / "changed.json"
            changed.write_bytes(GRAPH.read_bytes() + b" ")
            with self.assertRaisesRegex(FL2VAContractError, "differs"):
                normalize_request(request(), graph_path=changed)

    def test_preview_is_symbolic_only_and_compiles_frame_slots_and_prompt(self):
        preview = compile_preview(request(duration_seconds=5, resolution_preset=0.4), graph_path=GRAPH)
        self.assertTrue(preview["preview_only"])
        self.assertFalse(preview["submission_performed"])
        self.assertTrue(preview["asset_staging_required"])
        self.assertEqual(preview["compiled"]["fps"], 24)
        self.assertEqual((preview["compiled"]["width"], preview["compiled"]["height"]), (864, 480))
        graph = preview["graph"]
        self.assertEqual(graph["1"]["inputs"]["image"], "__vibe_preview_first_frame.png")
        self.assertEqual(graph["2"]["inputs"]["image"], "__vibe_preview_last_frame.png")
        self.assertEqual(graph["104"]["inputs"]["prompt"], "Move from the first frame to the last.")
        self.assertEqual(graph["104"]["inputs"]["length"], 124)
        self.assertAlmostEqual(preview["compiled"]["predicted_duration_seconds"], 124 / 24)
        self.assertEqual(graph["92"]["inputs"]["filename_prefix"], "isolated_preview/fl2va_preview_only")
        source = json.loads(GRAPH.read_text(encoding="utf-8"))
        self.assertEqual(source["1"]["inputs"]["image"], "input.png")


if __name__ == "__main__":
    unittest.main()
