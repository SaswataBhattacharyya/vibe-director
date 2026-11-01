"""CPU-only contract and preview compiler for isolated MiniMax H3 T2V.

This module validates a proposed UI/API payload and can compile a preview graph.
It does not create jobs, check runtime readiness, access ComfyUI, persist data, or
submit work. Preview results predict frame-derived duration; only output probing
can establish a rendered duration.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping

from story_builder.services.minimax_h3_graph_compiler import ASPECT_RATIOS, resolution_dimensions, GraphPlanError, ReferencePlan, RESOLUTION_PRESETS
from story_builder.services.minimax_h3_t2v import T2V_GRAPH_PATH, T2V_WORKFLOW_ID, compile_t2v_graph, LEGACY_T2V_GRAPH_PATH, LTX_GRAPH_PATH, T2V_RESOLUTION_PRESETS, pipeline_digest

WORKFLOW_VERSION = 2
LEGACY_GRAPH_SHA256 = "4735e3662333493d488bc2ba6970810e620c13196ccac15b1155010e8cf3e1f9"
EXPECTED_GRAPH_SHA256 = "b1c9292f4786baa4ace638b9bb9f455c42a9ed20a6bccb36cdb2b313cabf62d3"
PROMPT_CHARACTER_LIMIT = 7000  # Python Unicode code points; UI should use the same counting rule.
REQUEST_FIELDS = frozenset({
    "workflow_id", "workflow_version", "workflow_sha256", "prompt",
    "duration_seconds", "aspect_ratio", "resolution_preset", "steps", "seed", "references",
})


class IsolatedVideoContractError(ValueError):
    """Stable CPU contract error suitable for later HTTP adaptation."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str) -> None:
    raise IsolatedVideoContractError(code, message)


def _graph_digest(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        _fail("workflow_graph_unavailable", f"Cannot read configured T2V graph: {exc}")


def _normalize_request_with_digest(payload: Mapping[str, Any], actual_graph_sha: str) -> dict[str, Any]:
    """Validate payload against a graph digest already read from its exact bytes."""
    if not isinstance(payload, Mapping):
        _fail("request_type_invalid", "Request must be a JSON object.")
    copied = copy.deepcopy(dict(payload))
    if any(type(key) is not str for key in copied):
        _fail("request_keys_invalid", "Request field names must be strings.")
    unknown = set(copied) - REQUEST_FIELDS - {"source_resolution_preset"}
    missing = REQUEST_FIELDS - set(copied)
    if unknown:
        _fail("unknown_fields", f"Unknown request fields: {', '.join(sorted(unknown))}.")
    if missing:
        _fail("missing_fields", f"Missing request fields: {', '.join(sorted(missing))}.")

    if copied["workflow_id"] != T2V_WORKFLOW_ID or type(copied["workflow_id"]) is not str:
        _fail("workflow_mismatch", "Only the exact local MiniMax H3 T2V workflow is accepted.")
    if type(copied["workflow_version"]) is not int or copied["workflow_version"] not in {1, WORKFLOW_VERSION}:
        _fail("workflow_version_mismatch", "Unsupported T2V workflow version.")
    if actual_graph_sha != (LEGACY_GRAPH_SHA256 if copied["workflow_version"] == 1 else EXPECTED_GRAPH_SHA256):
        _fail("workflow_graph_drift", "Installed T2V graph differs from the versioned CPU contract.")
    if type(copied["workflow_sha256"]) is not str or copied["workflow_sha256"] != actual_graph_sha:
        _fail("workflow_hash_mismatch", "Request workflow hash does not match the exact installed graph.")

    prompt = copied["prompt"]
    if type(prompt) is not str or not prompt.strip():
        _fail("missing_prompt", "Prompt must contain non-whitespace text.")
    if len(prompt) >= PROMPT_CHARACTER_LIMIT:
        _fail("prompt_too_long", "MiniMax prompt must be strictly below 7000 Unicode code points.")

    duration = copied["duration_seconds"]
    if isinstance(duration, bool) or not isinstance(duration, (int, float)):
        _fail("invalid_duration", "Duration must be a finite number from 5 through 30 seconds.")
    try:
        duration = float(duration)
    except (OverflowError, ValueError):
        _fail("invalid_duration", "Duration must be a finite number from 5 through 30 seconds.")
    if not math.isfinite(duration):
        _fail("invalid_duration", "Duration must be a finite number from 5 through 30 seconds.")
    if not 5.0 <= duration <= 30.0:
        _fail("invalid_duration", "Local H3 T2V duration must be between 5 and 30 seconds.")

    if type(copied["aspect_ratio"]) is not str or copied["aspect_ratio"] not in ASPECT_RATIOS:
        _fail("unsupported_aspect_ratio", "Choose a supported video aspect ratio and quality preset.")
    preset = copied["resolution_preset"]
    if isinstance(preset, bool) or not isinstance(preset, (int, float)):
        _fail("unsupported_resolution_preset", "Resolution preset must be a numeric key from the local graph catalog.")
    try:
        preset = float(preset)
    except (OverflowError, ValueError):
        _fail("unsupported_resolution_preset", "Choose a known local T2V resolution preset.")
    if preset not in (RESOLUTION_PRESETS if copied["workflow_version"] == 1 else T2V_RESOLUTION_PRESETS):
        _fail("unsupported_resolution_preset", "Choose a known local T2V resolution preset.")

    source_fields = {}
    if "source_resolution_preset" in copied:
        source = copied["source_resolution_preset"]
        if (copied["workflow_version"] != WORKFLOW_VERSION or isinstance(source, bool)
                or not isinstance(source, (int, float)) or source not in T2V_RESOLUTION_PRESETS):
            _fail("unsupported_source_resolution_preset", "H3 source quality must be a known numeric Turbo resolution preset.")
        source_fields["source_resolution_preset"] = float(source)

    # Keep the first slice aligned with exact graph and ReferencePlan defaults.
    # User-editable steps/seed need a separately reviewed capability contract.
    steps = copied["steps"]
    if type(steps) is not int or steps != (20 if copied["workflow_version"] == 1 else 4):
        _fail("unsupported_steps", "T2V Turbo uses four steps; frozen version 1 uses twenty.")
    seed = copied["seed"]
    if type(seed) is not int or seed != 1:
        _fail("unsupported_seed", "First isolated T2V slice fixes seed at the graph default 1.")
    if type(copied["references"]) is not list or copied["references"]:
        _fail("t2v_references_unsupported", "Isolated H3 T2V accepts an empty references list only.")

    # Rebuild in stable order and normalize equivalent numeric JSON values.
    # Keep prompt bytes/code points exactly as authored, including whitespace.
    return {
        "workflow_id": T2V_WORKFLOW_ID,
        "workflow_version": copied["workflow_version"],
        "workflow_sha256": actual_graph_sha,
        "prompt": prompt,
        "duration_seconds": duration,
        "aspect_ratio": copied["aspect_ratio"],
        "resolution_preset": preset,
        **source_fields,
        "steps": steps,
        "seed": seed,
        "references": [],
    }


def normalize_request(payload: Mapping[str, Any], *, graph_path: Path = T2V_GRAPH_PATH) -> dict[str, Any]:
    """Read, pin, then validate request against the exact graph file bytes."""
    if not isinstance(payload, Mapping):
        _fail("invalid_request", "Request must be an object.")
    path = LEGACY_T2V_GRAPH_PATH if payload.get("workflow_version") == 1 and Path(graph_path) == T2V_GRAPH_PATH else Path(graph_path)
    try:
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest() if payload.get("workflow_version") == 1 else pipeline_digest(path)
    except OSError as exc:
        _fail("workflow_graph_unavailable", f"Cannot read configured T2V graph: {exc}")
    return _normalize_request_with_digest(payload, digest)


def canonical_request_hash(payload: Mapping[str, Any], *, graph_path: Path = T2V_GRAPH_PATH) -> str:
    normalized = normalize_request(payload, graph_path=graph_path)
    encoded = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def compile_preview(payload: Mapping[str, Any], *, graph_path: Path = T2V_GRAPH_PATH) -> dict[str, Any]:
    """Return isolated preview-only graph and predicted duration; never submit it."""
    if not isinstance(payload, Mapping):
        _fail("invalid_request", "Request must be an object.")
    try:
        path = LEGACY_T2V_GRAPH_PATH if payload.get("workflow_version") == 1 and Path(graph_path) == T2V_GRAPH_PATH else Path(graph_path)
        graph_bytes = path.read_bytes()
        graph_sha256 = hashlib.sha256(graph_bytes).hexdigest() if payload.get("workflow_version") == 1 else pipeline_digest(path)
    except OSError as exc:
        _fail("workflow_graph_unavailable", f"Cannot read configured T2V graph: {exc}")
    normalized = _normalize_request_with_digest(payload, graph_sha256)
    try:
        base_graph = json.loads(graph_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        _fail("workflow_graph_unavailable", f"Cannot parse configured T2V graph: {exc}")
    if not isinstance(base_graph, dict):
        _fail("workflow_graph_invalid", "T2V graph must be a JSON object.")

    # The upstream compiler requires story-shaped IDs only to form its output
    # filename prefix. These fixed compatibility values are not persisted and
    # do not represent screenplay, project, run, or shot canon.
    plan = ReferencePlan(
        schema_version=1,
        project_id="isolated_preview",
        run_id="preview",
        shot_id="preview",
        prompt=normalized["prompt"],
        duration_seconds=normalized["duration_seconds"],
        resolution_preset=normalized["resolution_preset"],
        aspect_ratio=normalized["aspect_ratio"],
        steps=normalized["steps"],
        seed=normalized["seed"],
    )
    try:
        compiled = compile_t2v_graph(plan, base_graph=base_graph,
                                     source_resolution_preset=normalized.get("source_resolution_preset"))
    except GraphPlanError as exc:
        _fail(exc.code, str(exc))
    graph = copy.deepcopy(compiled["graph"])
    for node in graph.values():
        if isinstance(node, dict) and node.get("class_type") == "SaveVideo":
            node.setdefault("inputs", {})["filename_prefix"] = "isolated_preview/preview_only"
    frame_count = compiled["frame_count"]
    return {
        "preview_only": True,
        "submission_performed": False,
        "workflow_id": compiled["workflow_id"],
        "workflow_sha256": normalized["workflow_sha256"],
        "request": normalized,
        "request_sha256": hashlib.sha256(json.dumps(
            normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")).hexdigest(),
        "compiled": {
            "width": compiled["final_width"],
            "height": compiled["final_height"],
            "source_width": compiled["width"], "source_height": compiled["height"],
            "pipeline": "H3 Turbo → LTX refinement" if normalized["workflow_version"] == 2 else "legacy H3",
            "frame_count": frame_count,
            "fps": 24,
            "requested_duration_seconds": normalized["duration_seconds"],
            "predicted_duration_seconds": math.ceil(normalized["duration_seconds"] * 24) / 24 if normalized["workflow_version"] == 2 else frame_count / 24,
            "duration_kind": "predicted_from_compiled_frames",
        },
        "graph": graph,
    }
