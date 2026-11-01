"""Fail-closed readiness for Vibe Director's independent MiniMax H3 R2V."""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Mapping
from urllib.request import urlopen

from story_builder.services.isolated_r2v_contract import (
    EXPECTED_GRAPH_SHA256, GRAPH_PATH, WORKFLOW_ID, WORKFLOW_VERSION,
)
from story_builder.services.minimax_h3_graph_compiler import GraphPlanError, validate_comfy_capabilities
from story_builder.services.production_image_workflows import comfyui_root
from story_builder.services.minimax_h3_t2v import LTX_GRAPH_PATH, pipeline_digest

FEATURE_FLAG = "VIBE_DIRECTOR_ENABLE_R2V"


def smoke_manifest_path(data_root: Path | None = None) -> Path:
    root = data_root or (Path(os.environ["VIBE_DIRECTOR_DATA_DIR"])
        if os.environ.get("VIBE_DIRECTOR_DATA_DIR") else None)
    if root is not None:
        return root.expanduser().resolve() / ".vibe-director-r2v-smoke.json"
    return Path(__file__).resolve().parents[1] / "output/disposable-h3-r2v-smoke/manifest.json"


def record_successful_r2v_smoke(*, data_root: Path, request: dict[str, Any],
                               job_id: str, output: dict[str, Any]) -> bool:
    return _record_guided_smoke(mode="r2v", data_root=data_root, request=request, job_id=job_id, output=output)


def _record_guided_smoke(*, mode: str, data_root: Path, request: dict[str, Any],
                          job_id: str, output: dict[str, Any]) -> bool:
    """Record completed current-version guided outputs, never legacy evidence."""
    if mode == "fl2va":
        from story_builder.services.isolated_fl2va_contract import compile_preview, WORKFLOW_ID as workflow_id, WORKFLOW_VERSION as version, EXPECTED_GRAPH_SHA256 as graph_hash
        from story_builder.services.production_fl2va_capability import smoke_manifest_path as manifest_path
    else:
        from story_builder.services.isolated_r2v_contract import compile_preview
        workflow_id, version, graph_hash = WORKFLOW_ID, WORKFLOW_VERSION, EXPECTED_GRAPH_SHA256
        manifest_path = smoke_manifest_path
    if request.get("workflow_id") != workflow_id or request.get("workflow_version") != version or request.get("workflow_sha256") != graph_hash:
        return False
    if not isinstance(job_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", job_id):
        return False
    root = Path(data_root).expanduser().resolve()
    try:
        preview = compile_preview(request)
        relative = Path(str(output["relative_path"]))
        if relative.is_absolute() or ".." in relative.parts:
            return False
        media = (root / relative).resolve()
        media.relative_to(root)
        digest = hashlib.sha256(media.read_bytes()).hexdigest()
        probe = output.get("probe") or {}
        streams = {row.get("codec_type") for row in probe.get("streams", []) if isinstance(row, dict)}
        if (digest != output.get("sha256") or output.get("has_video") is not True
                or output.get("has_audio") is not True or not {"video", "audio"}.issubset(streams)):
            return False
    except (OSError, KeyError, ValueError, TypeError):
        return False
    destination = manifest_path(root)
    record = {"workflow_id": workflow_id, "workflow_version": version,
        "workflow_sha256": graph_hash, "status": "completed",
        "has_video": True, "has_audio": True,
        "outputs": [{"kind": "video", "relative_path": media.relative_to(root).as_posix(),
            "sha256": digest, "probe": probe}],
        "evidence": {"source": "vibe_director_successful_manual_r2v_job", "job_id": job_id}}
    if mode == "fl2va":
        record["input_roles"] = ["first_frame", "last_frame"]
    else:
        record["reference_map"] = preview["reference_map"]
    record["evidence"]["source"] = f"vibe_director_successful_manual_{mode}_job"
    temporary = destination.with_suffix(f".{job_id}.tmp")
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, destination)
    except OSError:
        temporary.unlink(missing_ok=True)
        return False
    return True


def r2v_capability(*, comfy_url: str | None = None, root: Path | None = None,
                   graph_path: Path = GRAPH_PATH, smoke_path: Path | None = None,
                   object_info: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Read-only preflight; R2V evidence is never inferred from T2V/FL2VA."""
    url = (comfy_url or os.environ.get("COMFYUI_URL", "http://127.0.0.1:3008")).rstrip("/")
    models = Path(root or comfyui_root()) / "models"
    required = {
        "r2v_unet": models / "diffusion_models/minimax_h3_ref2va_pruned_int8_convrot.safetensors",
        "video_vae": models / "vae/minimax_h3_video_vae_fp16.safetensors",
        "audio_vae": models / "vae/minimax_h3_audio_vae_fp32.safetensors",
        "text_encoder": models / "text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors",
    }
    required.update({
        "turbo_lora": models / "loras/minimax_h3_ref2v_turbo_4step_v0.1_comfyui_bf16.safetensors",
        "ltx_checkpoint": models / "checkpoints/ltx-2.3-22b-dev.safetensors",
        "ltx_encoder": models / "text_encoders/gemma_3_12B_it.safetensors",
        "ltx_lora": models / "loras/ltxv/ltx2/ltx-2.3-22b-distilled-lora-384-1.1.safetensors",
    })
    missing = [name for name, path in required.items() if not path.is_file()]
    graph_error = None
    graph_nodes: set[str] = set()
    try:
        raw = Path(graph_path).read_bytes()
        if pipeline_digest(graph_path) != EXPECTED_GRAPH_SHA256:
            graph_error = "Installed R2V graph differs from the pinned source graph."
        graph = json.loads(raw.decode("utf-8"))
        graph.update({"ltx_" + key: node for key, node in json.loads(LTX_GRAPH_PATH.read_text()).items()})
        graph_nodes = {node.get("class_type") for node in graph.values()
                       if isinstance(node, dict) and isinstance(node.get("class_type"), str)}
        if not graph_nodes:
            graph_error = "Pinned R2V graph contains no valid node types."
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, AttributeError) as exc:
        graph_error = f"R2V graph could not be validated: {type(exc).__name__}: {exc}"

    info = object_info
    reachable = info is not None
    connection_error = None
    if info is None:
        try:
            with urlopen(url + "/object_info", timeout=5) as response:
                info = json.loads(response.read().decode("utf-8"))
            reachable = isinstance(info, dict)
        except (OSError, TimeoutError, json.JSONDecodeError) as exc:
            info = {}
            reachable = False
            connection_error = f"ComfyUI R2V node preflight unavailable: {type(exc).__name__}: {exc}"
    node_error = None
    if reachable:
        missing_graph_nodes = sorted(graph_nodes - set(info or {}))
        if missing_graph_nodes:
            node_error = "Installed ComfyUI lacks pinned R2V graph nodes: " + ", ".join(missing_graph_nodes)
        else:
            try:
                # Also require the dynamic media loaders and their input schemas;
                # they are injected by the compiler and do not appear in base graph.
                validate_comfy_capabilities(info or {})
            except GraphPlanError as exc:
                node_error = str(exc)

    manifest = Path(smoke_path) if smoke_path else smoke_manifest_path()
    try:
        smoke = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        smoke = None
    smoke_output_verified = False
    if isinstance(smoke, dict):
        for item in smoke.get("outputs", []):
            if not isinstance(item, dict) or item.get("kind") != "video":
                continue
            try:
                output = (manifest.parent / str(item["relative_path"])).resolve()
                output.relative_to(manifest.parent.resolve())
                streams = {row.get("codec_type") for row in (item.get("probe") or {}).get("streams", []) if isinstance(row, dict)}
                if (output.is_file() and hashlib.sha256(output.read_bytes()).hexdigest() == item.get("sha256")
                        and {"video", "audio"}.issubset(streams)):
                    smoke_output_verified = True
                    break
            except (OSError, ValueError, KeyError, TypeError):
                continue
    smoke_matches = (isinstance(smoke, dict) and smoke.get("workflow_id") == WORKFLOW_ID
        and type(smoke.get("workflow_version")) is int and smoke.get("workflow_version") == WORKFLOW_VERSION
        and smoke.get("workflow_sha256") == EXPECTED_GRAPH_SHA256
        and isinstance(smoke.get("reference_map"), dict)
        and all(isinstance(smoke["reference_map"].get(key), list) for key in ("pictures", "videos", "audios"))
        and any(smoke["reference_map"].get(key) for key in ("pictures", "videos", "audios")))
    passed_smoke = (smoke_matches and smoke.get("status") == "completed"
        and smoke.get("has_video") is True and smoke.get("has_audio") is True and smoke_output_verified)
    enabled = os.environ.get(FEATURE_FLAG, "0").strip().lower() in {"1", "true", "yes", "on"}
    reasons = []
    if missing: reasons.append("Required R2V model files are missing: " + ", ".join(missing) + ".")
    if graph_error: reasons.append(graph_error)
    if not reachable: reasons.append(connection_error or "ComfyUI object_info is unavailable.")
    elif node_error: reasons.append("Required R2V node inputs are unavailable: " + node_error)
    if not enabled: reasons.append(f"Opt-in feature flag {FEATURE_FLAG}=1 is not set.")
    automation_reasons = list(reasons)
    if not passed_smoke: automation_reasons.append("No completed, provenance-matched R2V video+audio smoke with verified output is recorded.")
    available = not reasons
    return {"workflow_id": WORKFLOW_ID, "workflow_version": WORKFLOW_VERSION,
        "label": "MiniMax H3 · Reference to video", "available": available,
        "automation_available": available and passed_smoke,
        "automation_disabled_reason": None if available and passed_smoke else " ".join(automation_reasons),
        "feature_enabled": enabled, "disabled_reason": None if available else " ".join(reasons),
        "base_graph": "workflows/api/minimax_h3_turbo_r2v_api.json", "graph_sha256": EXPECTED_GRAPH_SHA256,
        "limits": {"images": 9, "videos": 3, "standalone_audios": 3,
            "video_excerpt_seconds": 15, "prompt_characters_exclusive": 7000,
            "duration_seconds": [5, 15], "aspect_ratio": "16:9",
            "aspect_ratios": ["16:9", "9:16", "4:3", "3:4", "1:1"]},
        "local_files": {name: {"path": str(path), "present": path.is_file()} for name, path in required.items()},
        "comfyui": {"reachable": reachable, "error": connection_error or node_error},
        "render_verified": passed_smoke, "live_smoke": smoke}
