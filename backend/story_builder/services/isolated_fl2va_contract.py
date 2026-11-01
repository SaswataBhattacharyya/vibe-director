"""CPU-only contract and preview compiler for isolated H3 first/last-frame video.

The compiled graph contains symbolic Comfy input filenames. It is not submit-ready:
the future job adapter must resolve the frozen asset IDs/hashes and stage bytes.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any, Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FL2VA_GRAPH_PATH = PROJECT_ROOT / "workflows/api/minimax_h3_turbo_fl2va_api.json"
WORKFLOW_ID = "minimax_h3_fl2va_first_last_v1"
WORKFLOW_VERSION = 2
LEGACY_GRAPH_SHA256 = "6c88479ce6f4ffad53b0a546bcf97de077b4ceb7affef2482d52d9455348271d"
EXPECTED_GRAPH_SHA256 = "575afcdef3a80e52828bdb4df07c0c5b27939d4dbc44d074aef665f3bad18fb0"
LEGACY_GRAPH_PATH = PROJECT_ROOT / "workflows/api/minimax_h3_fl2va_first_last_api.json"
from story_builder.services.minimax_h3_t2v import pipeline_digest


def request_graph_path(payload, graph_path=FL2VA_GRAPH_PATH):
    if not isinstance(payload, Mapping):
        _fail("request_type_invalid", "Request must be a JSON object.")
    if payload.get("workflow_version") == 1 and Path(graph_path) == FL2VA_GRAPH_PATH:
        return LEGACY_GRAPH_PATH
    return Path(graph_path)


def request_digest(payload, graph_path=FL2VA_GRAPH_PATH):
    path = request_graph_path(payload, graph_path)
    try:
        return (pipeline_digest(path) if payload.get("workflow_version") == 2
                else hashlib.sha256(path.read_bytes()).hexdigest())
    except OSError as exc:
        _fail("workflow_graph_unavailable", f"Cannot read pinned Turbo/LTX graphs: {exc}")


PROMPT_CHARACTER_LIMIT = 7000
FPS = 24
from story_builder.services.minimax_h3_graph_compiler import ASPECT_RATIOS, resolution_dimensions, RESOLUTION_PRESETS
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$")
_SHA256 = re.compile(r"^[a-f0-9]{64}$")
REQUEST_FIELDS = frozenset({
    "workflow_id", "workflow_version", "workflow_sha256", "prompt",
    "duration_seconds", "aspect_ratio", "resolution_preset", "first_frame", "last_frame",
})


class FL2VAContractError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str) -> None:
    raise FL2VAContractError(code, message)


def _image_ref(value: Any, role: str) -> dict[str, str]:
    if not isinstance(value, Mapping) or set(value) != {"asset_id", "sha256"}:
        _fail("invalid_reference", f"{role} must contain exactly an asset_id and SHA-256 hash.")
    asset_id, digest = value["asset_id"], value["sha256"]
    if type(asset_id) is not str or not _SAFE_ID.fullmatch(asset_id):
        _fail("invalid_asset_id", f"{role} must use a safe server-side asset ID, not a path.")
    if type(digest) is not str or not _SHA256.fullmatch(digest):
        _fail("invalid_asset_hash", f"{role} must include a lowercase SHA-256 hash.")
    return {"asset_id": asset_id, "sha256": digest}


def _normalize_with_digest(payload: Mapping[str, Any], actual_sha: str) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        _fail("request_type_invalid", "Request must be a JSON object.")
    copied = dict(payload)
    if any(type(key) is not str for key in copied):
        _fail("request_keys_invalid", "Request field names must be strings.")
    unknown, missing = set(copied) - REQUEST_FIELDS, REQUEST_FIELDS - set(copied)
    if unknown:
        _fail("unknown_fields", f"Unknown request fields: {', '.join(sorted(unknown))}.")
    if missing:
        _fail("missing_fields", f"Missing request fields: {', '.join(sorted(missing))}.")
    if copied["workflow_id"] != WORKFLOW_ID or type(copied["workflow_id"]) is not str:
        _fail("workflow_mismatch", "Only the exact local MiniMax H3 FL2VA workflow is accepted.")
    if type(copied["workflow_version"]) is not int or copied["workflow_version"] not in (1, WORKFLOW_VERSION):
        _fail("workflow_version_mismatch", "Unsupported FL2VA workflow version.")
    if actual_sha != (EXPECTED_GRAPH_SHA256 if copied["workflow_version"] == 2 else LEGACY_GRAPH_SHA256):
        _fail("workflow_graph_drift", "Installed FL2VA graph differs from the pinned version.")
    if type(copied["workflow_sha256"]) is not str or copied["workflow_sha256"] != actual_sha:
        _fail("workflow_hash_mismatch", "Request hash does not match the pinned FL2VA graph.")

    prompt = copied["prompt"]
    if type(prompt) is not str or not prompt.strip():
        _fail("missing_prompt", "Prompt must contain non-whitespace text.")
    if len(prompt) >= PROMPT_CHARACTER_LIMIT:
        _fail("prompt_too_long", "MiniMax prompt must be strictly below 7000 Unicode code points.")
    duration = copied["duration_seconds"]
    if isinstance(duration, bool) or not isinstance(duration, (int, float)):
        _fail("invalid_duration", "FL2VA duration must be a finite number from 5 through 15 seconds.")
    try:
        duration = float(duration)
    except (OverflowError, ValueError):
        _fail("invalid_duration", "FL2VA duration must be a finite number from 5 through 15 seconds.")
    if not math.isfinite(duration):
        _fail("invalid_duration", "FL2VA duration must be a finite number from 5 through 15 seconds.")
    if not 5 <= duration <= 15:
        _fail("invalid_duration", "Local FL2VA duration must be between 5 and 15 seconds.")
    if type(copied["aspect_ratio"]) is not str or copied["aspect_ratio"] not in ASPECT_RATIOS:
        _fail("unsupported_aspect_ratio", "Choose a supported video aspect ratio and quality preset.")
    preset = copied["resolution_preset"]
    try:
        preset = float(preset) if not isinstance(preset, bool) and isinstance(preset, (int, float)) else None
    except (OverflowError, ValueError):
        preset = None
    if preset not in RESOLUTION_PRESETS:
        _fail("unsupported_resolution_preset", "Choose a supported FL2VA resolution preset.")
    return {
        "workflow_id": WORKFLOW_ID, "workflow_version": copied["workflow_version"],
        "workflow_sha256": actual_sha, "prompt": prompt,
        "duration_seconds": duration, "aspect_ratio": copied["aspect_ratio"],
        "resolution_preset": preset,
        "first_frame": _image_ref(copied["first_frame"], "first_frame"),
        "last_frame": _image_ref(copied["last_frame"], "last_frame"),
    }


def normalize_request(payload: Mapping[str, Any], *, graph_path: Path = FL2VA_GRAPH_PATH) -> dict[str, Any]:
    try:
        raw = request_graph_path(payload, graph_path).read_bytes()
    except OSError as exc:
        _fail("workflow_graph_unavailable", f"Cannot read configured FL2VA graph: {exc}")
    return _normalize_with_digest(payload, request_digest(payload, graph_path))


def compile_preview(payload: Mapping[str, Any], *, graph_path: Path = FL2VA_GRAPH_PATH) -> dict[str, Any]:
    """Compile a symbolic preview only; no filesystem media lookup or submission."""
    try:
        raw = request_graph_path(payload, graph_path).read_bytes()
    except OSError as exc:
        _fail("workflow_graph_unavailable", f"Cannot read configured FL2VA graph: {exc}")
    digest = request_digest(payload, graph_path)
    normalized = _normalize_with_digest(payload, digest)
    try:
        graph = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        _fail("workflow_graph_invalid", f"Cannot parse FL2VA graph: {exc}")
    if not isinstance(graph, dict):
        _fail("workflow_graph_invalid", "FL2VA graph must be a JSON object.")
    graph = copy.deepcopy(graph)
    loaders = sorted(
        ((int(node_id), node) for node_id, node in graph.items()
         if isinstance(node, dict) and node.get("class_type") == "LoadImage"),
        key=lambda row: row[0],
    )
    generators = [node for node in graph.values()
                  if isinstance(node, dict) and node.get("class_type") == "MiniMaxH3ImageToVideo"]
    schedulers = [node for node in graph.values()
                  if isinstance(node, dict) and node.get("class_type") == "BasicScheduler"]
    noises = [node for node in graph.values()
              if isinstance(node, dict) and node.get("class_type") == "RandomNoise"]
    if len(loaders) != 2 or len(generators) != 1 or len(schedulers) != 1 or len(noises) != 1:
        _fail("workflow_graph_contract", "FL2VA graph must contain two image loaders, one generator, scheduler and noise node.")
    # Symbolic basenames are placeholders, not ComfyUI-submittable filenames.
    loaders[0][1].setdefault("inputs", {})["image"] = "__vibe_preview_first_frame.png"
    loaders[1][1].setdefault("inputs", {})["image"] = "__vibe_preview_last_frame.png"
    width, height = resolution_dimensions(normalized["resolution_preset"], normalized["aspect_ratio"])
    final_width, final_height = width, height
    if normalized["workflow_version"] == 2:
        width, height = (max(32, math.floor(v * 2 / 3 / 32 + .5) * 32) for v in (width, height))
    frames = max(5, math.ceil(normalized["duration_seconds"] * FPS))
    while frames % 17 != 5:
        frames += 1
    gen_inputs = generators[0].setdefault("inputs", {})
    gen_inputs.update({"prompt": normalized["prompt"], "width": width, "height": height, "length": frames})
    schedulers[0].setdefault("inputs", {})["steps"] = 4 if normalized["workflow_version"] == 2 else 20
    noises[0].setdefault("inputs", {})["noise_seed"] = 1
    for node in graph.values():
        if isinstance(node, dict) and node.get("class_type") == "SaveVideo":
            node.setdefault("inputs", {})["filename_prefix"] = "isolated_preview/fl2va_preview_only"
    return {
        "preview_only": True, "submission_performed": False,
        "workflow_id": WORKFLOW_ID, "workflow_sha256": digest,
        "request": normalized,
        "compiled": {"final_width": final_width, "final_height": final_height, "width": width, "height": height, "frame_count": frames,
                     "fps": FPS, "requested_duration_seconds": normalized["duration_seconds"],
                     "predicted_duration_seconds": frames / FPS, "duration_kind": "aligned_compiled_frames"},
        "graph": graph,
        "asset_staging_required": True,
    }
