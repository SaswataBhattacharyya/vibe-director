"""Fail-closed, read-only readiness check for isolated MiniMax H3 FL2VA."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping
from urllib.request import urlopen

from story_builder.services.isolated_fl2va_contract import (
    EXPECTED_GRAPH_SHA256, FL2VA_GRAPH_PATH, WORKFLOW_ID, WORKFLOW_VERSION,
)
from story_builder.services.production_image_workflows import comfyui_root
from story_builder.services.minimax_h3_t2v import LTX_GRAPH_PATH, pipeline_digest

FEATURE_FLAG = "VIBE_DIRECTOR_ENABLE_FL2VA"


def smoke_manifest_path(data_root: Path | None = None) -> Path:
    root = data_root or (Path(os.environ["VIBE_DIRECTOR_DATA_DIR"]) if os.environ.get("VIBE_DIRECTOR_DATA_DIR") else None)
    return (root.expanduser().resolve() / ".vibe-director-fl2va-smoke.json" if root is not None
            else Path(__file__).resolve().parents[1] / "output/disposable-h3-fl2va-smoke/manifest.json")


def record_successful_fl2va_smoke(**kwargs) -> bool:
    from story_builder.services.production_r2v_capability import _record_guided_smoke
    return _record_guided_smoke(mode="fl2va", **kwargs)


def fl2va_capability(*, comfy_url: str | None = None, root: Path | None = None,
                     graph_path: Path = FL2VA_GRAPH_PATH, smoke_path: Path | None = None,
                     object_info: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Report readiness only; never submits a prompt or loads a model."""
    url = (comfy_url or os.environ.get("COMFYUI_URL", "http://127.0.0.1:3008")).rstrip("/")
    models = Path(root or comfyui_root()) / "models"
    required = {
        "fl2va_unet": models / "diffusion_models/minimax_h3_fl2va_pruned_int8_convrot.safetensors",
        "video_vae": models / "vae/minimax_h3_video_vae_fp16.safetensors",
        "audio_vae": models / "vae/minimax_h3_audio_vae_fp32.safetensors",
        "text_encoder": models / "text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors",
    }
    required.update({
        "turbo_lora": models / "loras/minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors",
        "ltx_checkpoint": models / "checkpoints/ltx-2.3-22b-dev.safetensors",
        "ltx_encoder": models / "text_encoders/gemma_3_12B_it.safetensors",
        "ltx_lora": models / "loras/ltxv/ltx2/ltx-2.3-22b-distilled-lora-384-1.1.safetensors",
    })
    missing = [key for key, path in required.items() if not path.is_file()]
    graph_error = None
    graph_nodes: set[str] = set()
    try:
        raw = Path(graph_path).read_bytes()
        if pipeline_digest(graph_path) != EXPECTED_GRAPH_SHA256:
            graph_error = "The installed FL2VA graph differs from the pinned version."
        graph = json.loads(raw.decode("utf-8"))
        graph.update({"ltx_" + key: node for key, node in json.loads(LTX_GRAPH_PATH.read_text()).items()})
        graph_nodes = {node.get("class_type") for node in graph.values()
                       if isinstance(node, dict) and isinstance(node.get("class_type"), str)}
        if not {"MiniMaxH3ImageToVideo", "LoadImage", "CreateVideo", "SaveVideo"}.issubset(graph_nodes):
            graph_error = "The pinned API graph is missing required FL2VA nodes."
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, AttributeError) as exc:
        graph_error = f"The FL2VA graph could not be validated: {type(exc).__name__}: {exc}"

    info = object_info
    reachable = info is not None
    connection_error = None
    if info is None:
        try:
            with urlopen(url + "/object_info", timeout=5) as response:
                info = json.loads(response.read().decode("utf-8"))
            reachable = isinstance(info, dict)
            if not reachable:
                connection_error = "ComfyUI returned an invalid object_info document."
        except (OSError, TimeoutError, json.JSONDecodeError) as exc:
            connection_error = f"ComfyUI node preflight unavailable: {type(exc).__name__}: {exc}"
            info = {}
    needed = graph_nodes | {"MiniMaxH3ImageToVideo", "LoadImage", "CreateVideo", "SaveVideo"}
    missing_nodes = sorted(needed - set(info or {})) if reachable else sorted(needed)

    manifest = Path(smoke_path) if smoke_path else smoke_manifest_path()
    try:
        smoke = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        smoke = None
    smoke_output_verified = False
    if isinstance(smoke, dict) and smoke.get("status") == "completed" and smoke.get("has_video") is True and smoke.get("has_audio") is True:
        for item in smoke.get("outputs", []):
            if not isinstance(item, dict) or item.get("kind") != "video":
                continue
            try:
                output = (manifest.parent / str(item["relative_path"])).resolve()
                output.relative_to(manifest.parent.resolve())
                digest = hashlib.sha256(output.read_bytes()).hexdigest()
                probe = item.get("probe")
                streams = probe.get("streams", []) if isinstance(probe, dict) else []
                types = {row.get("codec_type") for row in streams if isinstance(row, dict)}
                if (output.is_file() and digest == item.get("sha256")
                        and {"video", "audio"}.issubset(types)):
                    smoke_output_verified = True
                    break
            except (OSError, ValueError, KeyError, TypeError):
                continue
    # A successful render is evidence only for the exact graph and ordered
    # input contract that produced it. In particular, T2V smoke must never
    # enable first/last-frame generation.
    smoke_matches_contract = (isinstance(smoke, dict)
        and smoke.get("workflow_id") == WORKFLOW_ID
        and type(smoke.get("workflow_version")) is int
        and smoke.get("workflow_version") == WORKFLOW_VERSION
        and smoke.get("workflow_sha256") == EXPECTED_GRAPH_SHA256
        and smoke.get("input_roles") == ["first_frame", "last_frame"])
    passed_smoke = (smoke_matches_contract and smoke.get("status") == "completed"
                    and smoke.get("has_video") is True and smoke.get("has_audio") is True
                    and smoke_output_verified)
    enabled = os.environ.get(FEATURE_FLAG, "0").strip().lower() in {"1", "true", "yes", "on"}
    reasons = []
    if missing: reasons.append("Required FL2VA checkpoint files are missing: " + ", ".join(missing) + ".")
    if graph_error: reasons.append(graph_error)
    if not reachable: reasons.append(connection_error or "ComfyUI object_info is unavailable.")
    elif missing_nodes: reasons.append("Required FL2VA ComfyUI nodes are missing: " + ", ".join(missing_nodes) + ".")
    if not enabled: reasons.append(f"Opt-in feature flag {FEATURE_FLAG}=1 is not set.")
    automation_reasons = list(reasons)
    if not passed_smoke: automation_reasons.append("No successful disposable FL2VA video+audio smoke with an intact, hash-verified output is recorded.")
    available = not missing and not graph_error and reachable and not missing_nodes and enabled
    return {"workflow_id": WORKFLOW_ID, "workflow_version": WORKFLOW_VERSION,
        "label": "MiniMax H3 · First/last frame (FL2VA)", "available": available,
        "automation_available": available and passed_smoke,
        "automation_disabled_reason": None if available and passed_smoke else " ".join(automation_reasons),
        "feature_enabled": enabled, "disabled_reason": None if available else " ".join(reasons),
        "workflow_family": "minimax_h3_fl2va_local_v1",
        "base_graph": "workflows/api/minimax_h3_turbo_fl2va_api.json",
        "accepted_slots": {"first_frame": {"required": True}, "last_frame": {"required": True}},
        "settings": {"fps": 24, "resolution_presets": {"0.98": [1344, 768], "0.4": [864, 480], "0.6": [1056, 608], "0.8": [1216, 672], "1.5": [1664, 928], "2.0": [1920, 1088]},
                     "duration_seconds": {"min": 5, "max": 15}},
        "local_files": {name: {"path": str(path), "present": path.is_file()} for name, path in required.items()},
        "comfyui": {"reachable": reachable, "missing_nodes": missing_nodes,
                    "error": connection_error}, "render_verified": passed_smoke, "live_smoke": smoke}
