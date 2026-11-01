"""Fail-closed preflight for the separately tested H3 T2V production route."""
from __future__ import annotations

import json
import hashlib
import os
import re
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

from story_builder.services.minimax_h3_t2v import T2V_GRAPH_PATH, T2V_WORKFLOW_ID, LTX_GRAPH_PATH, pipeline_digest
from story_builder.services.isolated_video_contract import EXPECTED_GRAPH_SHA256, WORKFLOW_VERSION

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FEATURE_FLAG = "VIBE_DIRECTOR_ENABLE_T2V"
LEGACY_FEATURE_FLAG = "STORY_BUILDER_ENABLE_H3_T2V"

def feature_enabled(environ: Any = None) -> bool:
    """Honor Vibe's product flag, with the donor name as a migration fallback."""
    values = os.environ if environ is None else environ
    value = values.get(FEATURE_FLAG)
    if value is None:
        value = values.get(LEGACY_FEATURE_FLAG, "0")
    return str(value).strip().lower() in {"1", "true", "yes", "on"}
COMFY_URL = os.environ.get("COMFYUI_URL", "http://127.0.0.1:3008")
SMOKE_MANIFEST = (os.environ.get("VIBE_DIRECTOR_T2V_SMOKE_MANIFEST")
                  or os.environ.get("STORY_BUILDER_H3_T2V_SMOKE_MANIFEST"))


def smoke_manifest_path(data_root: Path | None = None) -> Path:
    """Use a product-owned evidence file beside the durable media library."""
    if SMOKE_MANIFEST:
        return Path(SMOKE_MANIFEST).expanduser().resolve()
    root = data_root or (Path(os.environ["VIBE_DIRECTOR_DATA_DIR"]).expanduser()
        if os.environ.get("VIBE_DIRECTOR_DATA_DIR") else None)
    if root is not None:
        return root.resolve() / ".vibe-director-t2v-smoke.json"
    return PROJECT_ROOT / "output/disposable-h3-t2v-smoke/manifest.json"


def record_successful_t2v_smoke(*, data_root: Path, workflow_sha256: str,
                                job_id: str, output: dict[str, Any],
                                manifest_path: Path | None = None) -> bool:
    """Persist smoke evidence from a completed, playable Vibe T2V take."""
    if (workflow_sha256 != EXPECTED_GRAPH_SHA256
            or not isinstance(job_id, str)
            or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", job_id)):
        return False
    root = Path(data_root).expanduser().resolve()
    try:
        relative_output = Path(str(output["relative_path"]))
        if relative_output.is_absolute() or ".." in relative_output.parts:
            return False
        resolved_output = (root / relative_output).resolve()
        resolved_output.relative_to(root)
        if not resolved_output.is_file():
            return False
        digest = hashlib.sha256(resolved_output.read_bytes()).hexdigest()
        probe = output.get("probe") if isinstance(output.get("probe"), dict) else {}
        stream_types = {row.get("codec_type") for row in probe.get("streams", []) if isinstance(row, dict)}
        if (digest != output.get("sha256")
                or output.get("has_video") is not True or output.get("has_audio") is not True
                or not {"video", "audio"}.issubset(stream_types)):
            return False
        destination = (manifest_path or smoke_manifest_path(root)).expanduser().resolve()
        relative_to_manifest = resolved_output.relative_to(destination.parent.resolve()).as_posix()
    except (OSError, KeyError, ValueError, TypeError):
        return False
    record = {"workflow_id": T2V_WORKFLOW_ID, "workflow_version": WORKFLOW_VERSION,
        "workflow_sha256": workflow_sha256, "status": "completed",
        "has_video": True, "has_audio": True,
        "outputs": [{"kind": "video", "relative_path": relative_to_manifest,
            "sha256": digest, "probe": probe}],
        "evidence": {"source": "vibe_director_successful_manual_t2v_job", "job_id": job_id}}
    temporary = destination.with_suffix(destination.suffix + f".{job_id}.tmp")
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, destination)
    except OSError:
        temporary.unlink(missing_ok=True)
        return False
    return True


def t2v_capability() -> dict[str, Any]:
    root_value = os.environ.get("COMFYUI_ROOT")
    root = Path(root_value).expanduser().resolve() if root_value else Path("/home/riki/web_dev/setup_comfy_and-stuff/ComfyUI")
    required = {"graph": T2V_GRAPH_PATH, "refinement_graph": LTX_GRAPH_PATH,
        "turbo_lora": root / "models/loras/minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors",
        "ltx_checkpoint": root / "models/checkpoints/ltx-2.3-22b-dev.safetensors",
        "ltx_text_encoder": root / "models/text_encoders/gemma_3_12B_it.safetensors",
        "ltx_distilled_lora": root / "models/loras/ltxv/ltx2/ltx-2.3-22b-distilled-lora-384-1.1.safetensors",
        "unet": root / "models/diffusion_models/minimax_h3_fl2va_pruned_int8_convrot.safetensors",
        "text_encoder": root / "models/text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors",
        "video_vae": root / "models/vae/minimax_h3_video_vae_fp16.safetensors",
        "audio_vae": root / "models/vae/minimax_h3_audio_vae_fp32.safetensors"}
    missing = [name for name, path in required.items() if not path.is_file()]
    graph_ok = False
    kinds: list[str] = []
    try:
        graph = json.loads(T2V_GRAPH_PATH.read_text(encoding="utf-8"))
        kinds = [n.get("class_type") for n in graph.values() if isinstance(n, dict)]
        ltx = json.loads(LTX_GRAPH_PATH.read_text(encoding="utf-8"))
        kinds += [n.get("class_type") for n in ltx.values() if isinstance(n, dict)]
        graph_ok = all(kinds.count(kind) >= count for kind, count in {
            "MiniMaxH3ImageToVideo": 1, "BasicScheduler": 1, "RandomNoise": 1,
            "SaveVideo": 2, "CreateVideo": 1, "RickyLTXSolAttention": 1, "LoadVideo": 1, "ImageScale": 1}.items())
    except (OSError, json.JSONDecodeError):
        pass
    smoke_path = smoke_manifest_path()
    smoke = None
    try:
        smoke = json.loads(smoke_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        pass
    enabled = feature_enabled()
    smoke_output_verified = False
    if isinstance(smoke, dict) and smoke.get("status") == "completed" and smoke.get("has_video") is True and smoke.get("has_audio") is True:
        for item in smoke.get("outputs", []):
            if not isinstance(item, dict) or item.get("kind") != "video":
                continue
            try:
                relative_output = Path(str(item["relative_path"]))
                if relative_output.is_absolute() or ".." in relative_output.parts:
                    continue
                output = (smoke_path.parent / relative_output).resolve()
                output.relative_to(smoke_path.parent.resolve())
                if not output.is_file():
                    continue
                actual_hash = hashlib.sha256(output.read_bytes()).hexdigest()
                probe = item.get("probe", {})
                streams = probe.get("streams", []) if isinstance(probe, dict) else []
                stream_types = {row.get("codec_type") for row in streams if isinstance(row, dict)}
                if (actual_hash == item.get("sha256")
                        and {"video", "audio"}.issubset(stream_types)):
                    smoke_output_verified = True
                    break
            except (OSError, KeyError, ValueError, TypeError):
                continue
    graph_sha256 = None
    try:
        graph_sha256 = pipeline_digest()
    except OSError:
        pass
    smoke_matches_graph = (isinstance(smoke, dict)
        and smoke.get("workflow_id") == T2V_WORKFLOW_ID
        and type(smoke.get("workflow_version")) is int
        and smoke.get("workflow_version") == WORKFLOW_VERSION
        and smoke.get("workflow_sha256") == graph_sha256 == EXPECTED_GRAPH_SHA256)
    passed = (smoke_matches_graph and smoke.get("status") == "completed"
        and smoke.get("has_video") is True and smoke.get("has_audio") is True
        and smoke_output_verified)
    reachable = False
    missing_nodes: list[str] = []
    comfy_error = None
    try:
        # The installed node catalog is several MB; a heavy render can delay this
        # read beyond 1.5 seconds. Keep it bounded without inferring readiness.
        with urlopen(f"{os.environ.get('COMFYUI_URL', COMFY_URL).rstrip('/')}/object_info", timeout=5) as response:
            info = json.loads(response.read().decode("utf-8"))
        reachable = isinstance(info, dict)
        if reachable:
            # The installed graph can contain loaders/operators beyond the
            # small T2V feature sentinel set. Fail closed if any exact graph
            # node type is absent from the live catalog.
            graph_node_types = {kind for kind in kinds if isinstance(kind, str)}
            missing_nodes = sorted((graph_node_types | {
                "MiniMaxH3ImageToVideo", "CreateVideo", "SaveVideo",
                "BasicScheduler", "RandomNoise",
            }) - set(info))
    except (OSError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        comfy_error = f"ComfyUI T2V node preflight unavailable: {type(exc).__name__}: {exc}"
    reasons = []
    if missing: reasons.append("Required local T2V graph/model files are missing: " + ", ".join(missing))
    if not graph_ok: reasons.append("The installed H3 T2V graph contract is invalid.")
    if not reachable: reasons.append(comfy_error or "ComfyUI object_info is unavailable.")
    elif missing_nodes: reasons.append("Required H3 T2V ComfyUI nodes are missing: " + ", ".join(missing_nodes))
    if not enabled: reasons.append(f"Opt-in feature flag {FEATURE_FLAG}=1 is not set (legacy {LEGACY_FEATURE_FLAG} is also accepted).")
    automation_reasons = list(reasons)
    if not passed: automation_reasons.append("No successful H3 T2V video+audio render from this exact workflow version has been hash-verified yet.")
    available = not reasons
    automation_available = available and passed
    return {"workflow_id": T2V_WORKFLOW_ID, "workflow_version": WORKFLOW_VERSION,
        "label": "MiniMax H3 Turbo → LTX · Text to video", "available": available,
        "automation_available": automation_available,
        "automation_disabled_reason": None if automation_available else " ".join(automation_reasons),
        "feature_enabled": enabled, "disabled_reason": None if available else " ".join(reasons),
        "workflow_family": "minimax_h3_t2v_local_v1", "base_graph": "workflows/api/minimax_h3_turbo_t2v_api.json", "refinement_graph": "workflows/api/minimax_h3_ltx_refine_api.json",
        "accepted_slots": {"images": {"min": 0, "max": 0}, "videos": {"min": 0, "max": 0}, "standalone_audios": {"min": 0, "max": 0}},
        "local_files": {name: {"path": str(path), "present": path.is_file()} for name, path in required.items()},
        "comfyui": {"reachable": reachable, "missing_nodes": missing_nodes, "error": comfy_error},
        "workflow_sha256": graph_sha256,
        "render_verified": passed, "live_smoke": smoke}
