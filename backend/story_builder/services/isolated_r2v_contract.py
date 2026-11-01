"""CPU-only, workspace-asset contract for isolated MiniMax H3 R2V."""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any, Mapping

from story_builder.services.minimax_h3_graph_compiler import (
    ASPECT_RATIOS, resolution_dimensions, RESOLUTION_PRESETS, AudioReference, GraphPlanError, ImageReference, ReferencePlan, ResolvedAsset,
    VideoReference, compile_r2v_graph, validate_reference_plan,
)

WORKFLOW_ID = "minimax_h3_r2v_dynamic_v1"
WORKFLOW_VERSION = 2
GRAPH_PATH = Path(__file__).resolve().parents[1] / "workflows/api/minimax_h3_turbo_r2v_api.json"
LEGACY_GRAPH_SHA256 = "5ebac422ff9dd1eb467265d36610f10fa8744ff8c8d31262cd9bf871b814332d"
EXPECTED_GRAPH_SHA256 = "7c9f2ec6bed283f0b0b761370e7798fe155ee1b1e04feb12a0d91a05c516a6b4"
LEGACY_GRAPH_PATH = Path(__file__).resolve().parents[1] / "workflows/api/minimax_h3_r2v_api.json"
from story_builder.services.minimax_h3_t2v import pipeline_digest, final_dimensions


def request_graph_path(payload, graph_path=GRAPH_PATH):
    if not isinstance(payload, Mapping):
        _err("request_type_invalid", "Request must be a JSON object.")
    if payload.get("workflow_version") == 1 and Path(graph_path) == GRAPH_PATH:
        return LEGACY_GRAPH_PATH
    return Path(graph_path)


def request_digest(payload, graph_path=GRAPH_PATH):
    path = request_graph_path(payload, graph_path)
    try:
        return (pipeline_digest(path) if payload.get("workflow_version") == 2
                else hashlib.sha256(path.read_bytes()).hexdigest())
    except OSError as exc:
        _err("workflow_graph_unavailable", f"Cannot read pinned Turbo/LTX graphs: {exc}")


PROMPT_CHARACTER_LIMIT = 7000
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$")
_HASH = re.compile(r"^[a-f0-9]{64}$")
FIELDS = frozenset({"workflow_id", "workflow_version", "workflow_sha256", "prompt",
    "duration_seconds", "aspect_ratio", "resolution_preset", "steps", "seed",
    "ref_image_size", "images", "videos", "audios"})


class R2VContractError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _err(code: str, message: str):
    raise R2VContractError(code, message)


def _ref(row: Any, kind: str) -> dict[str, Any]:
    common = {"asset_id", "sha256", "role", "intent"}
    extra = ({"start_sec", "end_sec", "include_paired_soundtrack", "audio_intent"}
             if kind == "video" else {"speaker_id"} if kind == "audio" else set())
    shared_speakers = (isinstance(row, Mapping) and kind == "audio"
        and set(row) == common | {"speaker_ids"})
    if not isinstance(row, Mapping) or (set(row) != common | extra and not shared_speakers):
        _err("invalid_reference", f"Each {kind} reference must use the supported fields.")
    asset_id, digest = row["asset_id"], row["sha256"]
    if type(asset_id) is not str or not _ID.fullmatch(asset_id):
        _err("invalid_asset_id", "References require safe server-side asset IDs, not paths.")
    if type(digest) is not str or not _HASH.fullmatch(digest):
        _err("invalid_asset_hash", "Each reference requires a frozen lowercase SHA-256.")
    if any(type(row[key]) is not str or not row[key].strip() for key in ("role", "intent")):
        _err("invalid_reference_intent", "Each reference needs a role and intent.")
    result = {"asset_id": asset_id, "sha256": digest, "role": row["role"], "intent": row["intent"]}
    if kind == "video":
        start, end = row["start_sec"], row["end_sec"]
        if (start is None) != (end is None):
            _err("incomplete_video_interval", "Video interval start and end must be supplied together.")
        for value in (start, end):
            if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)):
                _err("invalid_video_interval", "Video interval values must be finite seconds.")
        paired = row["include_paired_soundtrack"]
        if type(paired) is not bool:
            _err("invalid_paired_audio", "include_paired_soundtrack must be true or false.")
        audio_intent = row["audio_intent"]
        if type(audio_intent) is not str:
            _err("invalid_paired_audio", "audio_intent must be text.")
        result.update(start_sec=start, end_sec=end, include_paired_soundtrack=paired, audio_intent=audio_intent)
    if kind == "audio":
        if shared_speakers:
            speakers = row["speaker_ids"]
            if (type(speakers) is not list or len(speakers) > 12
                    or any(type(speaker) is not str or not _ID.fullmatch(speaker) for speaker in speakers)
                    or len(set(speakers)) != len(speakers)):
                _err("invalid_speaker_ids", "speaker_ids must be a list of up to 12 unique safe character IDs.")
            result["speaker_ids"] = speakers
        else:
            speaker = row["speaker_id"]
            if speaker is not None and (type(speaker) is not str or not _ID.fullmatch(speaker)):
                _err("invalid_speaker_id", "speaker_id must be a safe identifier or null.")
            result["speaker_id"] = speaker
    return result


def _normalize(payload: Mapping[str, Any], digest: str) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        _err("request_type_invalid", "Request must be a JSON object.")
    value = dict(payload)
    if any(type(key) is not str for key in value):
        _err("request_keys_invalid", "Request field names must be strings.")
    if set(value) != FIELDS:
        _err("request_fields_invalid", "R2V request fields are missing or unsupported.")
    if value["workflow_id"] != WORKFLOW_ID or type(value["workflow_id"]) is not str:
        _err("workflow_mismatch", "Only the pinned local H3 R2V workflow is accepted.")
    if type(value["workflow_version"]) is not int or value["workflow_version"] not in (1, WORKFLOW_VERSION):
        _err("workflow_version_mismatch", "Unsupported R2V workflow version.")
    if digest != (EXPECTED_GRAPH_SHA256 if value["workflow_version"] == 2 else LEGACY_GRAPH_SHA256) or value["workflow_sha256"] != digest:
        _err("workflow_graph_drift", "Request graph hash does not match the pinned R2V graph.")
    prompt = value["prompt"]
    if type(prompt) is not str or not prompt.strip():
        _err("missing_prompt", "Prompt must contain text.")
    if len(prompt) >= PROMPT_CHARACTER_LIMIT:
        _err("prompt_too_long", "MiniMax prompt must be below 7000 Unicode code points.")
    duration = value["duration_seconds"]
    if isinstance(duration, bool) or not isinstance(duration, (int, float)) or not math.isfinite(duration) or not 5 <= duration <= 15:
        _err("invalid_duration", "R2V duration must be 5 through 15 seconds.")
    if type(value["aspect_ratio"]) is not str or value["aspect_ratio"] not in ASPECT_RATIOS:
        _err("unsupported_aspect_ratio", "Choose a supported video aspect ratio and quality preset.")
    preset = value["resolution_preset"]
    if isinstance(preset, bool) or preset not in RESOLUTION_PRESETS:
        _err("unsupported_resolution_preset", "Choose Low (0.8), Standard (0.98), High (1.5) or Max (2.0).")
    steps, seed = value["steps"], value["seed"]
    if type(steps) is not int or not (steps == 4 if value["workflow_version"] == 2 else 8 <= steps <= 40):
        _err("invalid_steps", "Turbo R2V requires four steps; legacy requests require 8 through 40.")
    if type(seed) is not int or not 0 <= seed <= 0xFFFFFFFF:
        _err("invalid_seed", "Seed must be an unsigned 32-bit integer.")
    if value["ref_image_size"] not in {"match", "max"}:
        _err("invalid_ref_image_size", "ref_image_size must be match or max.")
    for key in ("images", "videos", "audios"):
        if type(value[key]) is not list:
            _err("invalid_reference_list", f"{key} must be a list.")
    images = [_ref(row, "image") for row in value["images"]]
    videos = [_ref(row, "video") for row in value["videos"]]
    audios = [_ref(row, "audio") for row in value["audios"]]
    if len({row["asset_id"] for row in [*images, *videos, *audios]}) != len(images) + len(videos) + len(audios):
        _err("duplicate_reference", "One asset cannot occupy multiple reference slots.")
    normalized = {"workflow_id": WORKFLOW_ID, "workflow_version": value["workflow_version"],
        "workflow_sha256": digest, "prompt": prompt, "duration_seconds": float(duration),
        "aspect_ratio": value["aspect_ratio"], "resolution_preset": float(preset), "steps": steps,
        "seed": seed, "ref_image_size": value["ref_image_size"],
        "images": images, "videos": videos, "audios": audios}
    plan = plan_from_request(normalized, "workspace", "run", "clip")
    try:
        validate_reference_plan(plan)
    except GraphPlanError as exc:
        _err(exc.code, str(exc))
    return normalized


def normalize_request(payload: Mapping[str, Any], *, graph_path: Path = GRAPH_PATH) -> dict[str, Any]:
    try:
        raw = request_graph_path(payload, graph_path).read_bytes()
    except OSError as exc:
        _err("workflow_graph_unavailable", f"Cannot read pinned R2V graph: {exc}")
    return _normalize(payload, request_digest(payload, graph_path))


def plan_from_request(request: Mapping[str, Any], workspace_id: str, run_id: str, clip_id: str) -> ReferencePlan:
    return ReferencePlan(schema_version=1, project_id=workspace_id, run_id=run_id,
        shot_id=clip_id, prompt=request["prompt"], duration_seconds=request["duration_seconds"],
        resolution_preset=request["resolution_preset"], aspect_ratio=request["aspect_ratio"],
        steps=request["steps"], seed=request["seed"], ref_image_size=request["ref_image_size"],
        images=tuple(ImageReference(row["asset_id"], row["role"], row["intent"]) for row in request["images"]),
        videos=tuple(VideoReference(row["asset_id"], row["role"], row["intent"], row["start_sec"], row["end_sec"], row["include_paired_soundtrack"], row["audio_intent"]) for row in request["videos"]),
        standalone_audios=tuple(AudioReference(row["asset_id"], row["role"], row["intent"],
            row.get("speaker_id"), tuple(row.get("speaker_ids", []))) for row in request["audios"]))


def compile_preview(payload: Mapping[str, Any], *, graph_path: Path = GRAPH_PATH) -> dict[str, Any]:
    normalized = normalize_request(payload, graph_path=graph_path)
    plan = plan_from_request(normalized, "preview", "preview", "preview")
    if not (plan.images or plan.videos or plan.standalone_audios):
        _err("zero_reference_route", "R2V needs at least one image, video, or audio reference.")
    index: dict[str, ResolvedAsset] = {}
    for row in normalized["images"]:
        index[row["asset_id"]] = ResolvedAsset(row["asset_id"], "image", f"preview-{row['asset_id']}.png", row["sha256"])
    for row in normalized["videos"]:
        start, end = row["start_sec"], row["end_sec"]
        if start is None:
            start, end = 0.0, 2.0
        index[row["asset_id"]] = ResolvedAsset(row["asset_id"], "video", f"preview-{row['asset_id']}.mp4", row["sha256"], start, end, row["include_paired_soundtrack"])
    for row in normalized["audios"]:
        index[row["asset_id"]] = ResolvedAsset(row["asset_id"], "audio", f"preview-{row['asset_id']}.wav", row["sha256"])
    try:
        compiled = compile_r2v_graph(plan, index, base_graph=json.loads(request_graph_path(payload, graph_path).read_text()))
    except GraphPlanError as exc:
        _err(exc.code, str(exc))
    normalized_hash = hashlib.sha256(json.dumps(normalized, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
    return {"preview_only": True, "submission_performed": False, "workflow_id": WORKFLOW_ID,
        "workflow_version": normalized["workflow_version"], "workflow_sha256": normalized["workflow_sha256"],
        "request": normalized, "request_sha256": normalized_hash,
        "reference_map": compiled.reference_map.as_dict(),
        "compiled": {"final_width": final_dimensions(plan.resolution_preset, plan.aspect_ratio)[0],
            "final_height": final_dimensions(plan.resolution_preset, plan.aspect_ratio)[1], "width": compiled.width, "height": compiled.height,
            "frame_count": compiled.frame_count, "fps": 24,
            "requested_duration_seconds": normalized["duration_seconds"],
            "predicted_duration_seconds": compiled.frame_count / 24,
            "duration_kind": "aligned_compiled_frames"},
        "graph": dict(compiled.graph), "asset_staging_required": True}
