"""Read-only status projection for the isolated UI.

It accepts the established T2V capability snapshot instead of independently
probing ComfyUI, loading models, checking GPU safety, or dispatching work.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


_IMAGES = (
    ("z_image_turbo", "Z-Image Turbo · text to image"),
    ("qwen_image_2512", "Qwen Image 2512 · text to image"),
    ("qwen_image_edit_2511", "Qwen Image Edit 2511 · image edit"),
    ("qwen_image_multi_angle_2511", "Qwen Image Edit 2511 · world views"),
)
_VIDEO_ROOT = Path(__file__).resolve().parent.parent / "workflows" / "api"
_VIDEO_GRAPHS = {
    "minimax_h3_fl2va_first_last_v1": "minimax_h3_fl2va_first_last_api.json",
    "minimax_h3_r2v_dynamic_v1": "minimax_h3_r2v_api.json",
}
_AUDIO_ROOT = Path(__file__).resolve().parent.parent / "workflows" / "api" / "audio"
_AUDIO = (
    ("ace_step_music_api", "ACE-Step music", "ace_step_music_api.json", ["tags", "lyrics"]),
    ("tts_multichar_timed_chatterbox_api", "Timed multi-character ChatterBox TTS", "tts_multichar_timed_chatterbox_api.json", ["timed dialogue", "voice references"]),
    ("noise_cleanup_api", "Noise cleanup", "noise_cleanup_api.json", ["audio"]),
    ("voice_repair_api", "Voice repair", "voice_repair_api.json", ["audio"]),
    ("voice_changer_api", "Voice changer", "voice_changer_api.json", ["audio", "voice reference"]),
    ("rvc_voice_api", "RVC voice conversion", "rvc_voice_api.json", ["audio", "RVC model"]),
    ("emotion_edit_api", "Emotion edit", "emotion_edit_api.json", ["audio", "transcript", "emotion"]),
    ("style_edit_api", "Style edit", "style_edit_api.json", ["audio", "transcript", "style"]),
    ("control_foley_text_audio_api", "Control-Foley · text to audio", "control_foley/text_audio_api.json", ["prompt"]),
    ("control_foley_text_video_audio_api", "Control-Foley · text and video to audio", "control_foley/text_video_audio_api.json", ["prompt", "video"]),
    ("control_foley_reference_video_audio_api", "Control-Foley · reference audio and video", "control_foley/reference_video_audio_api.json", ["audio reference", "video"]),
)
_AUDIO_KNOWLEDGE_IDS = {
    "ace_step_music_api": "ace_step_music_v1",
    "tts_multichar_timed_chatterbox_api": "chatterbox_timed_multichar_v1",
    "noise_cleanup_api": "audio_effects_noise_cleanup_v1",
    "voice_repair_api": "audio_effects_voice_repair_v1",
    "voice_changer_api": "audio_effects_voice_changer_v1",
    "rvc_voice_api": "audio_effects_rvc_v1",
    "emotion_edit_api": "audio_effects_emotion_v1",
    "style_edit_api": "audio_effects_style_v1",
    "control_foley_text_audio_api": "control_foley_text_audio_v1",
    "control_foley_text_video_audio_api": "control_foley_text_video_audio_v1",
    "control_foley_reference_video_audio_api": "control_foley_reference_video_audio_v1",
}


def _video_status(capability: dict[str, Any], *, backend_connected: bool,
                 guard: dict[str, Any], dispatch: dict[str, Any]) -> dict[str, Any]:
    """Project one video preflight without treating its existence as readiness."""
    reasons = []
    if not backend_connected:
        reasons.append("Backend did not respond.")
    workflow_ready = capability.get("workflow_available", capability.get("available")) is True
    workflow_id = capability.get("workflow_id")
    graph_name = _VIDEO_GRAPHS.get(workflow_id)
    graph_present = (_VIDEO_ROOT / graph_name).is_file() if graph_name else None
    if graph_present is False:
        reasons.append("Versioned workflow graph file is missing from this Vibe Director checkout.")
    if not workflow_ready:
        reasons.append(capability.get("disabled_reason") or "Workflow preflight did not pass.")
    if guard.get("monitor_available") is not True or guard.get("safe_to_submit") is not True:
        reasons.append(guard.get("reason") or "GPU safety monitor has not admitted rendering.")
    if dispatch.get("available") is not True:
        reasons.append(dispatch.get("reason") or "Explicit video worker dispatch is unavailable.")
    limits = capability.get("limits") if isinstance(capability.get("limits"), dict) else {}
    settings = capability.get("settings") if isinstance(capability.get("settings"), dict) else {}
    duration = limits.get("duration_seconds") or settings.get("duration_seconds")
    if isinstance(duration, dict):
        duration = [duration.get("min"), duration.get("max")]
    presets = settings.get("resolution_presets")
    outputs = ([{"preset": float(name), "width": value[0], "height": value[1]}
               for name, value in presets.items()
               if isinstance(value, (list, tuple)) and len(value) == 2]
              if isinstance(presets, dict) else None)
    return {
        **_evidence(capability),
        "graph_present": graph_present if graph_present is not None else _evidence(capability)["graph_present"],
        "workflow_id": workflow_id,
        "label": capability.get("label", capability.get("workflow_id", "Video workflow")),
        "category": "video", "version": capability.get("workflow_version"),
        "state": "usable" if not reasons else "unavailable",
        "available": not reasons,
        "workflow_available": workflow_ready,
        "workflow_reason": capability.get("disabled_reason") if not workflow_ready else None,
        "worker_available": dispatch.get("available") is True,
        "worker_reason": dispatch.get("reason") if dispatch.get("available") is not True else None,
        "reason": " ".join(dict.fromkeys(reasons)) or None,
        "feature_enabled": capability.get("feature_enabled") is True,
        "input_roles": list(capability.get("accepted_slots", {}).keys()) + ["prompt"]
            if isinstance(capability.get("accepted_slots"), dict)
            else ["image_references", "video_references", "audio_references", "prompt"],
        "duration_seconds": {"min": duration[0], "max": duration[1], "unit": "seconds"}
            if isinstance(duration, list) and len(duration) == 2 else None,
        "outputs": outputs,
        "prompt_limit": {"max": limits.get("prompt_characters_exclusive", 7000) - 1,
            "unit": "Unicode code points", "basis": "Workflow exclusive character limit."}
            if isinstance(limits.get("prompt_characters_exclusive"), int) else
            {"max": 6999, "unit": "Unicode code points", "basis": "Product input cap; workflow-specific lower limits may apply."},
    }


def _evidence(capability: dict[str, Any]) -> dict[str, Any]:
    files = capability.get("local_files") or {}
    graph = files.get("graph", {})
    models = [item for key, item in files.items() if key != "graph" and isinstance(item, dict)]
    comfy = capability.get("comfyui") or {}
    return {
        "graph_present": graph.get("present") if graph else None,
        "models": {"present": sum(item.get("present") is True for item in models),
                   "required": len(models)} if models else None,
        "nodes": {"checked": bool(comfy.get("reachable")),
                  "missing_count": len(comfy.get("missing_nodes") or [])}
            if "missing_nodes" in comfy else None,
        "render_verified": capability.get("render_verified") is True,
        "acceptance": "not_recorded",
    }


def build_workflow_status(snapshot: dict[str, Any], *, backend_connected: bool,
                          video_capabilities: list[dict[str, Any]] | None = None,
                          image_catalog: dict[str, Any] | None = None,
                          image_dispatch: dict[str, Any] | None = None,
                          comfyui_queue: dict[str, Any] | None = None,
                          audio_object_info: dict[str, Any] | None = None,
                          audio_workflow_knowledge: list[dict[str, Any]] | None = None) -> dict[str, Any]:
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
        **_evidence(snapshot),
        "workflow_id": snapshot.get("workflow_id", "minimax_h3_t2v_local_v1"),
        "label": snapshot.get("label", "MiniMax H3 · Text to video"),
        "version": snapshot.get("workflow_version", 1),
        "state": "usable" if not workflow_reasons else "unavailable",
        "available": not workflow_reasons,
        "workflow_available": backend_connected and workflow_available and graph.get("present") is True and not any(model.get("present") is not True for model in models) and bool(comfy.get("reachable")) and not missing_nodes and snapshot.get("feature_enabled") is True,
        "workflow_reason": " ".join(dict.fromkeys(workflow_reasons)) or None,
        "reason": " ".join(dict.fromkeys(workflow_reasons)) or None,
        "feature_enabled": snapshot.get("feature_enabled") is True,
        "automation_available": snapshot.get("automation_available") is True,
        "automation_reason": snapshot.get("automation_disabled_reason"),
        "graph_present": graph.get("present") is True,
        "models": {"present": sum(model.get("present") is True for model in models), "required": len(models)},
        "nodes": {"checked": bool(comfy.get("reachable")), "missing_count": len(missing_nodes)},
        "input_roles": ["prompt"],
        "duration_seconds": {"min": 5, "max": 30, "unit": "seconds"},
        "outputs": [
            {"preset": 0.98, "width": 1344, "height": 768},
            {"preset": 1.5, "width": 1664, "height": 928},
            {"preset": 2, "width": 1920, "height": 1088},
            {"preset": 0.8, "width": 1216, "height": 672},
        ],
        "fixed_parameters": {"seed": 1, "steps": 4, "refinement_steps": 3, "reference_count": 0},
        "aspect_ratios": ["16:9", "9:16", "4:3", "3:4", "1:1"],
        "prompt_limit": {"max": 6999, "unit": "Unicode code points", "basis": "Product input cap; workflow-specific lower limits may apply."},
    }
    unavailable = lambda identifier, label, category, roles, *, state="not_integrated", reason=None: {
        "acceptance": "not_recorded", "render_verified": False,
        "workflow_id": identifier, "label": label, "category": category,
        "state": state, "available": False,
        "reason": reason or "No readiness adapter for this workflow. Its tool page may offer other operations.", "input_roles": roles,
        "prompt_limit": {"value": None, "unit": "unknown", "reason": "Not verified for this workflow."},
    }
    capabilities_by_id = {item.get("workflow_id"): item for item in video_capabilities or []}
    video_rows = []
    for identifier, label in (("minimax_h3_fl2va_first_last_v1", "MiniMax H3 · First/last frame (FL2VA)"),
                              ("minimax_h3_r2v_dynamic_v1", "MiniMax H3 · Reference to video")):
        capability = capabilities_by_id.get(identifier)
        if capability is None:
            video_rows.append(unavailable(identifier, label, "video", ["prompt"]))
        else:
            # Per-workflow dispatch is checked by the caller and embedded with
            # the same GPU guard. Capability existence alone never means usable.
            dispatch_for_workflow = capability.get("dispatch") if isinstance(capability.get("dispatch"), dict) else {}
            video_rows.append(_video_status(capability, backend_connected=backend_connected,
                guard=guard, dispatch=dispatch_for_workflow))
    image_entries = (image_catalog or {}).get("workflows", [])
    image_entries = image_entries if isinstance(image_entries, list) else []
    image_worker_ready = bool((image_dispatch or {}).get("available"))
    planned_images = []
    for identifier, label in _IMAGES:
        entry = next((item for item in image_entries if item.get("workflow_id") == identifier), None)
        if entry is None:
            planned_images.append({**unavailable(identifier, label, "image",
                ["image", "prompt"] if identifier in {"qwen_image_edit_2511", "qwen_image_multi_angle_2511"} else ["prompt"]),
                "prompt_limit": {"max": 6999, "unit": "Unicode code points",
                    "basis": "Product input cap; workflow-specific lower limits may apply."}})
            continue
        reasons = []
        if not backend_connected:
            reasons.append("Backend did not respond.")
        if entry.get("available") is not True:
            reasons.append(entry.get("disabled_reason") or "Image workflow preflight did not pass.")
        if not image_worker_ready:
            reasons.append((image_dispatch or {}).get("reason") or "Image worker is unavailable.")
        if guard.get("monitor_available") is not True or guard.get("safe_to_submit") is not True:
            reasons.append(guard.get("reason") or "GPU safety monitor has not admitted rendering.")
        planned_images.append({"workflow_id": identifier, "label": entry.get("label", label),
            "graph_present": entry.get("graph_present"),
            "models": {"present": sum(item.get("present") is True for item in entry.get("models", {}).values()),
                       "required": len(entry.get("models", {}))} if entry.get("models") else None,
            "nodes": {"checked": entry.get("comfyui_online") is True,
                      "missing_count": len(entry.get("missing_nodes") or [])},
            "render_verified": entry.get("live_smoke") is not None,
            "acceptance": "not_recorded",
            "category": "image", "version": entry.get("version"),
            "state": "usable" if not reasons else "unavailable", "available": not reasons,
            "workflow_available": entry.get("available") is True,
            "workflow_reason": entry.get("disabled_reason") if entry.get("available") is not True else None,
            "worker_available": image_worker_ready,
            "worker_reason": (image_dispatch or {}).get("reason") if not image_worker_ready else None,
            "reason": " ".join(dict.fromkeys(reasons)) or None,
            "input_roles": ["image", "prompt"] if identifier in {"qwen_image_edit_2511", "qwen_image_multi_angle_2511"} else ["prompt"],
            "prompt_limit": {"max": 6999, "unit": "Unicode code points", "basis": "Product input cap; workflow-specific lower limits may apply."}})
    planned_audio = []
    knowledge_by_id = {item.get("workflow_id"): item for item in audio_workflow_knowledge or []
                       if isinstance(item, dict)}
    for identifier, label, graph_name, roles in _AUDIO:
        graph_path = _AUDIO_ROOT / graph_name
        graph_present = graph_path.is_file()
        required_nodes: set[str] = set()
        if graph_present and isinstance(audio_object_info, dict) and audio_object_info:
            try:
                graph = json.loads(graph_path.read_text(encoding="utf-8"))
                required_nodes = {node["class_type"] for node in graph.values()
                    if isinstance(node, dict) and isinstance(node.get("class_type"), str)}
            except (OSError, json.JSONDecodeError):
                required_nodes = set()
        nodes_checked = graph_present and isinstance(audio_object_info, dict) and bool(audio_object_info) and bool(required_nodes)
        missing_nodes = required_nodes - set(audio_object_info or {}) if nodes_checked else set()
        reason = "Workflow file is missing from this Vibe Director checkout." if not graph_present else (
            f"ComfyUI node catalog checked; {len(missing_nodes)} required node type(s) are missing. Model compatibility and runtime safety remain unchecked."
            if nodes_checked and missing_nodes else
            "ComfyUI node catalog checked; all graph node types are present. Model compatibility and runtime safety remain unchecked."
            if nodes_checked else
            "Workflow file is present; model and node compatibility and runtime safety are not checked here.")
        planned_audio.append({
            **unavailable(identifier, label, "audio", roles,
                state="not_checked" if graph_present else "not_integrated", reason=reason),
            "graph_present": graph_present,
            "nodes": {"checked": nodes_checked, "missing_count": len(missing_nodes)}
                if nodes_checked else {"checked": False, "missing_count": 0},
        })
        # A prompt limit is not applicable to transformations that accept only
        # media and settings. Keep unknown limits only for workflows with text.
        if not any(any(term in role.casefold() for term in ("prompt", "text", "tag", "lyric", "dialogue", "transcript"))
                   for role in roles):
            planned_audio[-1]["prompt_limit"] = {
                "unit": "not applicable",
                "reason": "This workflow accepts audio and settings, not text input.",
            }
        knowledge = knowledge_by_id.get(_AUDIO_KNOWLEDGE_IDS.get(identifier))
        if isinstance(knowledge, dict):
            parameter = next((node.get("text") for node in knowledge.get("nodes", [])
                              if isinstance(node, dict) and node.get("kind") == "parameter_contract"
                              and isinstance(node.get("text"), str)), None)
            if parameter:
                planned_audio[-1]["input_contract"] = parameter
        if identifier == "ace_step_music_api":
            planned_audio[-1]["input_limits"] = {
                "tags": {"max": 4000, "unit": "Unicode code points", "basis": "Vibe Director music form and backend validation."},
                "lyrics": {"max": 10000, "unit": "Unicode code points", "basis": "Vibe Director song form and backend validation."},
            }
            planned_audio[-1]["prompt_limit"] = {"value": None, "unit": "not applicable", "reason": "ACE-Step uses separate tags and lyrics inputs; see input limits."}
        elif identifier.startswith("control_foley_"):
            planned_audio[-1]["input_limits"] = {
                "prompt": {"max": 4000, "unit": "Unicode code points", "basis": "Vibe Director form and backend validation."},
                "negative_prompt": {"max": 4000, "unit": "Unicode code points", "basis": "Vibe Director form and backend validation."},
            }
            planned_audio[-1]["prompt_limit"] = {"max": 4000, "unit": "Unicode code points", "basis": "Vibe Director form and backend validation."}
    return {
        "schema_version": 1,
        "backend": {"connected": backend_connected},
        "comfyui": {"reachable": bool(comfy.get("reachable")),
                     "reason": None if comfy.get("reachable") else "ComfyUI node catalog is unreachable."},
        "comfyui_queue": _queue_evidence(comfyui_queue),
        "runtime_guard": {key: guard.get(key) for key in (
            "monitor_available", "safe_to_submit", "temperature_cutoff_c",
            "graphics_clock_ceiling_mhz", "operating_point", "reason")},
        "dispatch": {key: dispatch.get(key) for key in ("enabled", "running", "available", "worker_state", "reason")},
        "workflows": [t2v, *video_rows, *planned_images, *planned_audio],
    }


def _queue_evidence(queue: dict[str, Any] | None) -> dict[str, Any]:
    """Expose counts only; a missing/invalid observation must remain unknown."""
    if not isinstance(queue, dict) or queue.get("checked") is not True:
        return {"checked": False, "running": None, "pending": None,
                "reason": "ComfyUI queue state could not be checked."}
    running, pending = queue.get("running"), queue.get("pending")
    if type(running) is not int or type(pending) is not int or running < 0 or pending < 0:
        return {"checked": False, "running": None, "pending": None,
                "reason": "ComfyUI returned an invalid queue response."}
    return {"checked": True, "running": running, "pending": pending, "reason": None}
