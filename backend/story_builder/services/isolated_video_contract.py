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

from story_builder.services.minimax_h3_graph_compiler import GraphPlanError, ReferencePlan, RESOLUTION_PRESETS
from story_builder.services.minimax_h3_t2v import T2V_GRAPH_PATH, T2V_WORKFLOW_ID, compile_t2v_graph

WORKFLOW_VERSION = 1
EXPECTED_GRAPH_SHA256 = "4735e3662333493d488bc2ba6970810e620c13196ccac15b1155010e8cf3e1f9"
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
    unknown = set(copied) - REQUEST_FIELDS
    missing = REQUEST_FIELDS - set(copied)
    if unknown:
        _fail("unknown_fields", f"Unknown request fields: {', '.join(sorted(unknown))}.")
    if missing:
        _fail("missing_fields", f"Missing request fields: {', '.join(sorted(missing))}.")

    if copied["workflow_id"] != T2V_WORKFLOW_ID or type(copied["workflow_id"]) is not str:
        _fail("workflow_mismatch", "Only the exact local MiniMax H3 T2V workflow is accepted.")
    if type(copied["workflow_version"]) is not int or copied["workflow_version"] != WORKFLOW_VERSION:
        _fail("workflow_version_mismatch", "Unsupported T2V workflow version.")
    if actual_graph_sha != EXPECTED_GRAPH_SHA256:
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
        _fail("invalid_duration", "Duration must be a finite number from 5 through 10 seconds.")
    try:
        duration = float(duration)
    except (OverflowError, ValueError):
        _fail("invalid_duration", "Duration must be a finite number from 5 through 10 seconds.")
    if not math.isfinite(duration):
        _fail("invalid_duration", "Duration must be a finite number from 5 through 10 seconds.")
    if not 5.0 <= duration <= 10.0:
        _fail("invalid_duration", "Local H3 T2V duration must be between 5 and 10 seconds.")

    if type(copied["aspect_ratio"]) is not str or copied["aspect_ratio"] != "16:9":
        _fail("unsupported_aspect_ratio", "Local H3 T2V supports 16:9 only.")
    preset = copied["resolution_preset"]
    if isinstance(preset, bool) or not isinstance(preset, (int, float)):
        _fail("unsupported_resolution_preset", "Resolution preset must be a numeric key from the local graph catalog.")
    try:
        preset = float(preset)
    except (OverflowError, ValueError):
        _fail("unsupported_resolution_preset", "Choose a known local T2V resolution preset.")
    if preset not in RESOLUTION_PRESETS:
        _fail("unsupported_resolution_preset", "Choose a known local T2V resolution preset.")

    # Keep the first slice aligned with exact graph and ReferencePlan defaults.
    # User-editable steps/seed need a separately reviewed capability contract.
    steps = copied["steps"]
    if type(steps) is not int or steps != 20:
        _fail("unsupported_steps", "First isolated T2V slice fixes steps at the graph default 20.")
    seed = copied["seed"]
    if type(seed) is not int or seed != 1:
        _fail("unsupported_seed", "First isolated T2V slice fixes seed at the graph default 1.")
    if type(copied["references"]) is not list or copied["references"]:
        _fail("t2v_references_unsupported", "Isolated H3 T2V accepts an empty references list only.")

    # Rebuild in stable order and normalize equivalent numeric JSON values.
    # Keep prompt bytes/code points exactly as authored, including whitespace.
    return {
        "workflow_id": T2V_WORKFLOW_ID,
        "workflow_version": WORKFLOW_VERSION,
        "workflow_sha256": actual_graph_sha,
        "prompt": prompt,
        "duration_seconds": duration,
        "aspect_ratio": "16:9",
        "resolution_preset": preset,
        "steps": steps,
        "seed": seed,
        "references": [],
    }


def normalize_request(payload: Mapping[str, Any], *, graph_path: Path = T2V_GRAPH_PATH) -> dict[str, Any]:
    """Read, pin, then validate request against the exact graph file bytes."""
    path = Path(graph_path)
    try:
        raw = path.read_bytes()
    except OSError as exc:
        _fail("workflow_graph_unavailable", f"Cannot read configured T2V graph: {exc}")
    return _normalize_request_with_digest(payload, hashlib.sha256(raw).hexdigest())


def canonical_request_hash(payload: Mapping[str, Any], *, graph_path: Path = T2V_GRAPH_PATH) -> str:
    normalized = normalize_request(payload, graph_path=graph_path)
    encoded = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def compile_preview(payload: Mapping[str, Any], *, graph_path: Path = T2V_GRAPH_PATH) -> dict[str, Any]:
    """Return isolated preview-only graph and predicted duration; never submit it."""
    try:
        graph_bytes = Path(graph_path).read_bytes()
    except OSError as exc:
        _fail("workflow_graph_unavailable", f"Cannot read configured T2V graph: {exc}")
    graph_sha256 = hashlib.sha256(graph_bytes).hexdigest()
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
        compiled = compile_t2v_graph(plan, base_graph=base_graph)
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
            "width": compiled["width"],
            "height": compiled["height"],
            "frame_count": frame_count,
            "fps": 24,
            "requested_duration_seconds": normalized["duration_seconds"],
            "predicted_duration_seconds": frame_count / 24,
            "duration_kind": "predicted_from_compiled_frames",
        },
        "graph": graph,
    }
