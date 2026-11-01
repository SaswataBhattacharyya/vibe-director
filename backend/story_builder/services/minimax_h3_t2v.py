"""Deterministic compiler for the installed local MiniMax H3 text-to-video graph."""
from __future__ import annotations

import copy
import json
import math
from pathlib import Path
from typing import Any, Mapping

from story_builder.services.minimax_h3_graph_compiler import ASPECT_RATIOS, resolution_dimensions, GraphPlanError, ReferencePlan, RESOLUTION_PRESETS

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LEGACY_T2V_GRAPH_PATH = PROJECT_ROOT / "workflows" / "api" / "minimax_h3_t2v_api.json"
T2V_GRAPH_PATH = PROJECT_ROOT / "workflows" / "api" / "minimax_h3_turbo_t2v_api.json"
LTX_GRAPH_PATH = PROJECT_ROOT / "workflows" / "api" / "minimax_h3_ltx_refine_api.json"
T2V_RESOLUTION_PRESETS = {**RESOLUTION_PRESETS, 1.5: (1664, 928), 2.0: (1920, 1088)}


def final_dimensions(preset: float, aspect_ratio: str) -> tuple[int, int]:
    width, height = T2V_RESOLUTION_PRESETS[preset]
    if aspect_ratio == "9:16":
        return height, width
    if aspect_ratio == "16:9":
        return width, height
    a, b = map(int, aspect_ratio.split(":"))
    area, ratio = width * height, a / b
    return (max(32, math.floor(math.sqrt(area * ratio) / 32 + .5) * 32),
            max(32, math.floor(math.sqrt(area / ratio) / 32 + .5) * 32))


def pipeline_digest(graph_path: Path = T2V_GRAPH_PATH) -> str:
    import hashlib
    return hashlib.sha256(Path(graph_path).read_bytes() + b"\nLTX_STAGE\n" + LTX_GRAPH_PATH.read_bytes()).hexdigest()

T2V_WORKFLOW_ID = "minimax_h3_t2v_local_v1"


def turbo_source_dimensions(preset: float, aspect_ratio: str) -> tuple[int, int]:
    """Budget the H3 original independently of the user's final LTX canvas.

    Retain the earlier .4 source budget for normal finals and the tested
    896x512 source budget for Max. Other ratios retain the legacy grid fitting.
    """
    source_preset = .98 if preset == 2.0 else .4
    canvas = final_dimensions(source_preset, aspect_ratio)
    return tuple(max(32, math.floor(v * 2 / 3 / 32 + .5) * 32) for v in canvas)


def compile_t2v_graph(plan: ReferencePlan, *, base_graph: Mapping[str, Any] | None = None,
                      source_resolution_preset: float | None = None) -> dict[str, Any]:
    """Compile an explicit zero-reference plan; any supplied media is rejected."""
    if plan.images or plan.videos or plan.standalone_audios:
        raise GraphPlanError("t2v_references_unsupported", "H3 T2V accepts no reference assets; choose a supported R2V workflow for references.")
    if not isinstance(plan.prompt, str) or not plan.prompt.strip():
        raise GraphPlanError("missing_prompt", "A non-empty H3 prompt is required.")
    if not math.isfinite(plan.duration_seconds) or not 5 <= plan.duration_seconds <= 30:
        raise GraphPlanError("invalid_duration", "Local H3 T2V duration must be between 5 and 30 seconds.")
    if plan.aspect_ratio not in ASPECT_RATIOS or plan.resolution_preset not in T2V_RESOLUTION_PRESETS:
        raise GraphPlanError("unsupported_t2v_canvas", "Choose a supported video aspect ratio and quality preset.")
    graph = copy.deepcopy(dict(base_graph if base_graph is not None else json.loads(T2V_GRAPH_PATH.read_text(encoding="utf-8"))))
    generators = [(node_id, node) for node_id, node in graph.items() if isinstance(node, dict) and node.get("class_type") == "MiniMaxH3ImageToVideo"]
    if len(generators) != 1:
        raise GraphPlanError("t2v_graph_contract", "H3 T2V base graph must contain exactly one MiniMaxH3ImageToVideo node.")
    _node_id, generator = generators[0]
    inputs = generator.setdefault("inputs", {})
    final_width, final_height = final_dimensions(plan.resolution_preset, plan.aspect_ratio)
    turbo = any(n.get("class_type") == "LoraLoaderModelOnly" and "turbo" in str(n.get("inputs", {}).get("lora_name", "")) for n in graph.values() if isinstance(n, dict))
    width, height = final_width, final_height
    if source_resolution_preset is not None:
        if (not turbo or isinstance(source_resolution_preset, bool)
                or not isinstance(source_resolution_preset, (int, float))
                or source_resolution_preset not in T2V_RESOLUTION_PRESETS):
            raise GraphPlanError("unsupported_source_resolution_preset", "Choose a known H3 Turbo source resolution preset.")
        width, height = final_dimensions(source_resolution_preset, plan.aspect_ratio)
    elif turbo:
        width, height = turbo_source_dimensions(plan.resolution_preset, plan.aspect_ratio)
    frames = max(5, math.ceil(plan.duration_seconds * 24))
    while frames % 17 != 5:
        frames += 1
    # Turbo source may contain an aligned tail. Final remux trims to the user's duration.
    if not turbo:
        frames = min(frames, 719)
    inputs.update({"prompt": plan.prompt, "width": width, "height": height, "length": frames})
    schedulers = [node["inputs"] for node in graph.values() if isinstance(node, dict) and node.get("class_type") == "BasicScheduler"]
    noises = [node["inputs"] for node in graph.values() if isinstance(node, dict) and node.get("class_type") == "RandomNoise"]
    if len(schedulers) != 1 or len(noises) != 1:
        raise GraphPlanError("t2v_graph_contract", "H3 T2V graph must contain exactly one scheduler and noise node.")
    schedulers[0]["steps"] = plan.steps
    noises[0]["noise_seed"] = plan.seed
    for node in graph.values():
        if isinstance(node, dict) and node.get("class_type") == "SaveVideo":
            node.setdefault("inputs", {})["filename_prefix"] = f"production_v2/{plan.run_id}/{plan.shot_id}"
    return {"workflow_id": T2V_WORKFLOW_ID, "graph": graph, "width": width, "height": height, "frame_count": frames, "final_width": final_width, "final_height": final_height}
