"""Read-only status projection for the isolated UI.

It accepts the established T2V capability snapshot instead of independently
probing ComfyUI, loading models, checking GPU safety, or dispatching work.
"""
from __future__ import annotations

from typing import Any


_IMAGES = (
    ("z_image_turbo", "Z-Image Turbo · text to image"),
    ("qwen_image_2512", "Qwen Image 2512 · text to image"),
    ("qwen_image_edit_2511", "Qwen Image Edit 2511 · image edit"),
)
_AUDIO = (
    ("ace_step_music_api", "ACE-Step music"),
    ("production_vibevoice_dialogue_api", "VibeVoice dialogue"),
    ("tts_multichar_timed_chatterbox_api", "Timed multi-character ChatterBox TTS"),
    ("rvc_voice_api", "RVC voice conversion"),
    ("voice_changer_api", "Voice changer"),
    ("voice_repair_api", "Voice repair"),
    ("emotion_edit_api", "Emotion edit"),
    ("style_edit_api", "Style edit"),
    ("noise_cleanup_api", "Noise cleanup"),
)


def build_workflow_status(snapshot: dict[str, Any], *, backend_connected: bool) -> dict[str, Any]:
    """Return compact, path-free workflow/readiness metadata for GET /api/status."""
    guard = snapshot.get("runtime_guard") if isinstance(snapshot.get("runtime_guard"), dict) else {}
    dispatch = snapshot.get("dispatch") if isinstance(snapshot.get("dispatch"), dict) else {}
    comfy = snapshot.get("comfyui") if isinstance(snapshot.get("comfyui"), dict) else {}
    files = snapshot.get("local_files") if isinstance(snapshot.get("local_files"), dict) else {}
    graph = files.get("graph") if isinstance(files.get("graph"), dict) else {}
    models = [value for name, value in files.items() if name != "graph" and isinstance(value, dict)]
    missing_nodes = comfy.get("missing_nodes")
    missing_nodes = missing_nodes if isinstance(missing_nodes, list) else []
    workflow_available = bool(snapshot.get("workflow_available", snapshot.get("available")))
    workflow_reasons = []
    if not backend_connected:
        workflow_reasons.append("Backend did not respond.")
    if graph.get("present") is not True:
        workflow_reasons.append("Versioned graph file is missing.")
    if models and any(model.get("present") is not True for model in models):
        absent = sum(model.get("present") is not True for model in models)
        workflow_reasons.append(f"{absent} required model file(s) are missing.")
    if not comfy.get("reachable"):
        workflow_reasons.append("ComfyUI node catalog is unreachable.")
    elif missing_nodes:
        workflow_reasons.append(f"{len(missing_nodes)} required ComfyUI node type(s) are missing.")
    if snapshot.get("feature_enabled") is not True:
        workflow_reasons.append("The local H3 T2V opt-in is disabled.")
    if not workflow_available:
        workflow_reasons.append("Exact T2V workflow readiness has not passed.")
    if guard.get("monitor_available") is not True or guard.get("safe_to_submit") is not True:
        workflow_reasons.append(guard.get("reason") or "GPU safety monitor has not admitted rendering.")
    if dispatch.get("available") is not True:
        workflow_reasons.append(dispatch.get("reason") or "Explicit video worker dispatch is unavailable.")

    t2v = {
        "workflow_id": snapshot.get("workflow_id", "minimax_h3_t2v_local_v1"),
        "label": snapshot.get("label", "MiniMax H3 · Text to video"),
        "version": snapshot.get("workflow_version", 1),
        "state": "usable" if backend_connected and workflow_available and guard.get("safe_to_submit") is True and dispatch.get("available") is True else "unavailable",
        "available": backend_connected and workflow_available and guard.get("safe_to_submit") is True and dispatch.get("available") is True,
        "workflow_available": backend_connected and workflow_available,
        "workflow_reason": " ".join(dict.fromkeys(workflow_reasons)) or None,
        "reason": " ".join(dict.fromkeys(workflow_reasons)) or None,
        "feature_enabled": snapshot.get("feature_enabled") is True,
        "graph_present": graph.get("present") is True,
        "models": {"present": sum(model.get("present") is True for model in models), "required": len(models)},
        "nodes": {"checked": bool(comfy.get("reachable")), "missing_count": len(missing_nodes)},
        "input_roles": ["prompt"],
        "duration_seconds": {"min": 5, "max": 10, "unit": "seconds"},
        "outputs": [
            {"preset": 0.98, "width": 1344, "height": 768},
            {"preset": 0.4, "width": 864, "height": 480},
        ],
        "fixed_parameters": {"seed": 1, "steps": 20, "aspect_ratio": "16:9", "reference_count": 0},
        "prompt_limit": {"max": 6999, "unit": "Unicode code points", "basis": "Product rule: strictly below 7,000."},
    }
    unavailable = lambda identifier, label, category, roles: {
        "workflow_id": identifier, "label": label, "category": category,
        "state": "not_integrated", "available": False,
        "reason": "Not integrated in this application yet.", "input_roles": roles,
        "prompt_limit": {"value": None, "unit": "unknown", "reason": "Not verified for this workflow."},
    }
    planned_video = [
        unavailable("first_last_frame", "First + last frame", "video", ["first_frame", "last_frame", "prompt"]),
        unavailable("reference_to_video", "Reference to video", "video", ["image_references", "video_references", "audio_references", "prompt"]),
    ]
    planned_images = [unavailable(identifier, label, "image", ["image", "prompt"] if identifier == "qwen_image_edit_2511" else ["prompt"]) for identifier, label in _IMAGES]
    planned_audio = [unavailable(identifier, label, "audio", ["workflow-specific inputs"]) for identifier, label in _AUDIO]
    return {
        "schema_version": 1,
        "backend": {"connected": backend_connected},
        "comfyui": {"reachable": bool(comfy.get("reachable")),
                     "reason": None if comfy.get("reachable") else "ComfyUI node catalog is unreachable."},
        "runtime_guard": {key: guard.get(key) for key in (
            "monitor_available", "safe_to_submit", "temperature_cutoff_c",
            "graphics_clock_ceiling_mhz", "operating_point", "reason")},
        "dispatch": {key: dispatch.get(key) for key in ("enabled", "running", "available", "worker_state", "reason")},
        "workflows": [t2v, *planned_video, *planned_images, *planned_audio],
    }
