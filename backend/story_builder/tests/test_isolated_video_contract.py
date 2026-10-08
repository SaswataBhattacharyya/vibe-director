from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from story_builder.services.isolated_video_contract import (
    EXPECTED_GRAPH_SHA256,
    IsolatedVideoContractError,
    canonical_request_hash,
    compile_preview,
    normalize_request,
)
from story_builder.services.minimax_h3_graph_compiler import RESOLUTION_PRESETS

ROOT = Path(__file__).resolve().parents[1]
GRAPH = ROOT / "workflows/api/minimax_h3_t2v_api.json"


def request(**changes):
    payload = {
        "workflow_id": "minimax_h3_t2v_local_v1",
        "workflow_version": 1,
        "workflow_sha256": EXPECTED_GRAPH_SHA256,
        "prompt": "A shot.",
        "duration_seconds": 6,
        "aspect_ratio": "16:9",
        "resolution_preset": 0.98,
        "steps": 20,
        "seed": 1,
        "references": [],
    }
    payload.update(changes)
    return payload


class IsolatedVideoContractTests(unittest.TestCase):
    def test_prompt_codepoint_boundary_and_exact_text_preservation(self):
        prompt = "x" * 6999
        normalized = normalize_request(request(prompt=prompt))
        self.assertEqual(normalized["prompt"], prompt)
        self.assertEqual(len(normalized["prompt"]), 6999)
        with self.assertRaisesRegex(IsolatedVideoContractError, "strictly below"):
            normalize_request(request(prompt="x" * 7000))
        authored = "  preserve edge whitespace  "
        self.assertEqual(normalize_request(request(prompt=authored))["prompt"], authored)

    def test_duration_endpoints_and_reject_invalid_or_nonfinite_values(self):
        for value in (5, 10):
            self.assertEqual(normalize_request(request(duration_seconds=value))["duration_seconds"], float(value))
        for value in (True, False, float("nan"), float("inf"), -float("inf"), 4.999, 10.001, "6"):
            with self.subTest(value=value), self.assertRaises(IsolatedVideoContractError):
                normalize_request(request(duration_seconds=value))

    def test_preset_dimensions_and_fixed_first_slice_settings(self):
        for preset, expected in RESOLUTION_PRESETS.items():
            preview = compile_preview(request(resolution_preset=preset), graph_path=GRAPH)
            self.assertEqual((preview["compiled"]["width"], preview["compiled"]["height"]), expected)
        self.assertEqual(normalize_request(request())["steps"], 20)
        self.assertEqual(normalize_request(request())["seed"], 1)
        for field, value in (("steps", True), ("steps", 19), ("steps", 21),
                             ("seed", True), ("seed", 0), ("seed", 2)):
            with self.subTest(field=field, value=value), self.assertRaises(IsolatedVideoContractError):
                normalize_request(request(**{field: value}))

    def test_hash_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            changed = Path(directory) / "graph.json"
            changed.write_bytes(GRAPH.read_bytes() + b" ")
            with self.assertRaisesRegex(IsolatedVideoContractError, "differs") as caught:
                normalize_request(request(), graph_path=changed)
            self.assertEqual(caught.exception.code, "workflow_graph_drift")

    def test_preview_hashes_and_compiles_same_single_graph_read(self):
        graph_bytes = GRAPH.read_bytes()
        drifted_bytes = graph_bytes + b" "
        with patch.object(Path, "read_bytes", autospec=True,
                          side_effect=lambda path: graph_bytes if path == GRAPH else drifted_bytes) as read_bytes:
            preview = compile_preview(request(), graph_path=GRAPH)
        self.assertEqual(read_bytes.call_count, 1)
        self.assertEqual(preview["workflow_sha256"], EXPECTED_GRAPH_SHA256)

    def test_references_unknown_fields_and_workflow_hash_are_rejected(self):
        for bad in (
            request(references=[{"asset_id": "media-1"}]),
            request(unreviewed_setting=1),
            request(workflow_sha256="0" * 64),
        ):
            with self.subTest(bad=bad), self.assertRaises(IsolatedVideoContractError):
                normalize_request(bad)

    def test_canonical_hash_normalizes_order_and_equivalent_numbers(self):
        left = request(duration_seconds=6, resolution_preset=0.98)
        right = dict(reversed(list(request(duration_seconds=6.0, resolution_preset=0.98).items())))
        self.assertEqual(canonical_request_hash(left), canonical_request_hash(right))
        self.assertNotEqual(canonical_request_hash(left), canonical_request_hash(request(prompt="A different shot.")))
        self.assertNotEqual(canonical_request_hash(left), canonical_request_hash(request(duration_seconds=6.1)))
        self.assertNotEqual(canonical_request_hash(left), canonical_request_hash(request(resolution_preset=0.4)))

    def test_preview_compiles_exact_graph_without_mutating_input_or_submission(self):
        original = request()
        before = copy.deepcopy(original)
        preview = compile_preview(original, graph_path=GRAPH)
        self.assertEqual(original, before)
        self.assertTrue(preview["preview_only"])
        self.assertFalse(preview["submission_performed"])
        self.assertEqual(preview["workflow_sha256"], EXPECTED_GRAPH_SHA256)
        self.assertEqual(preview["compiled"], {
            "width": 1344,
            "height": 768,
            "frame_count": 158,
            "fps": 24,
            "requested_duration_seconds": 6.0,
            "predicted_duration_seconds": 158 / 24,
            "duration_kind": "predicted_from_compiled_frames",
        })
        save_nodes = [node for node in preview["graph"].values()
                      if node.get("class_type") == "SaveVideo"]
        self.assertEqual(len(save_nodes), 1)
        self.assertEqual(save_nodes[0]["inputs"]["filename_prefix"], "isolated_preview/preview_only")
        source = json.loads(GRAPH.read_text(encoding="utf-8"))
        source_save = next(node for node in source.values() if node.get("class_type") == "SaveVideo")
        self.assertEqual(source_save["inputs"]["filename_prefix"], "hermes/minimax_h3")


if __name__ == "__main__":
    unittest.main()
