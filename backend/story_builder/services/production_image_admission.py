"""Build deterministic checked-stage image batches from accepted screenplay data."""
from __future__ import annotations

import hashlib
import json
from typing import Any

from story_builder.services.production_image_workflows import IMAGE_PROMPT_MAX_CODEPOINTS, compile_image_candidates


STEP_CONFIG = {
    "character_images": ("character", "character_master", "characters"),
    "world_images": ("location", "world_master", "worlds"),
}
FRAME_ROLES = ("first_frame", "last_frame")


def build_entity_image_batches(*, workspace_id: str, screenplay: dict[str, Any],
                               graph: dict[str, Any], setup: dict[str, Any],
                               step: str, run_id: str,
                               selected_targets: set[str] | None = None,
                               style_selection: dict[str, Any] | None = None,
                               character_prompt_drafter=None) -> list[dict[str, Any]]:
    """Compile one Director-reviewed candidate batch per unselected canonical entity.

    The caller must verify accepted-revision, setup, workflow, GPU and worker readiness
    before enqueuing the returned batches. Only the optional character prompt drafter performs provider I/O; this function never dispatches GPU work.
    """
    if step not in STEP_CONFIG:
        raise ValueError("Automated image admission currently supports character and world image stages.")
    setup_data = setup.get("setup") if isinstance(setup, dict) else None
    if (not isinstance(setup_data, dict) or setup_data.get("mode") != "assisted_manual"
            or setup_data.get("automate_steps", {}).get(step) is not True):
        raise ValueError(f"Save Assisted manual setup with {step.replace('_', ' ')} checked before admission.")
    settings = setup_data.get("image_stage_settings", {}).get(step)
    if not isinstance(settings, dict):
        raise ValueError(f"Confirmed workflow settings are missing for {step}.")
    records = graph.get("records") if isinstance(graph, dict) and graph.get("status") == "complete" else None
    if not isinstance(records, list):
        raise ValueError("Automated image generation requires the complete graph snapshot pinned to the screenplay.")

    target_type, asset_role, prompt_label = STEP_CONFIG[step]
    selected = selected_targets or set()
    setup_hash = hashlib.sha256(json.dumps(setup_data, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    style_context = _style_context(style_selection)
    style_hash = style_context_sha256(style_selection)
    batches = []
    targets = sorted((record for record in records
        if isinstance(record, dict) and record.get("kind") == "entity"
        and str(record.get("type", "")).casefold() == target_type
        and isinstance(record.get("record_id"), str) and record.get("record_id")
        and record.get("record_id") not in selected),
        key=lambda record: (str(record.get("name", "")).casefold(), record["record_id"]))
    for target in targets:
        name = str(target.get("name", "")).strip()
        detail = str(target.get("detail", "")).strip()
        if not name:
            continue
        screenplay_context = _screenplay_context(screenplay, name)
        prompt_body = (f"{prompt_label[:-1].capitalize()} reference image for {name}. "
                  f"Target description: {detail}. Screenplay context: {screenplay_context}. "
                  f"Production style: {style_context['guidance']}. ").strip()
        asset_brief = ("Show exactly one character alone against a plain white studio background. "
            "No story scenery, buildings, landscapes or other people. Use the story only for appearance and clothing."
            if asset_role == "character_master" else
            "Show only the environment/location. No people or characters; do not illustrate actions involving characters.")
        prompt = prompt_body + " " + asset_brief + " Create one clear, production-ready reference image; avoid text, labels, watermarks, and collage layouts."
        identity = (f"{workspace_id}\0{screenplay['screenplay_revision_id']}\0{step}\0"
            f"{target['record_id']}\0{setup_hash}\0{style_hash}")
        digest = hashlib.sha256(identity.encode()).hexdigest()
        if asset_role == "character_master" and character_prompt_drafter is not None:
            prompt = character_prompt_drafter(target=target, idempotency_key=f"image-stage-{digest}")
            if not isinstance(prompt, str) or not prompt.strip():
                raise ValueError("Director did not prepare a character appearance prompt.")
        if len(prompt) > IMAGE_PROMPT_MAX_CODEPOINTS:
            raise ValueError(f"{prompt_label[:-1].capitalize()} image prompt for {name} exceeds the "
                f"{IMAGE_PROMPT_MAX_CODEPOINTS:,}-character image limit; shorten its graph description "
                "or related screenplay direction before generating.")
        seed = int(digest[:8], 16)
        compiled = compile_image_candidates(workflow_id=settings["workflow_id"], prompt=prompt,
            control_mode="assisted_manual", seed=seed, initial_candidate_count=1,
            output_prefix=f"{workspace_id}/{asset_role}/{digest[:16]}",
            width=settings["width"], height=settings["height"], steps=settings["steps"], cfg=settings["cfg"])
        lineage = {"screenplay_revision_id": screenplay["screenplay_revision_id"],
            "source_revision_id": screenplay["source_revision_id"],
            "graph_snapshot_id": screenplay["graph_snapshot_id"], "target_type": target_type,
            "target_record_id": target["record_id"], "target_name": name, "target_detail": detail,
            "screenplay_context": screenplay_context, "style_selection_snapshot_id": screenplay.get("style_selection_snapshot_id"),
            "style_selection_sha256": style_hash, "style_selection": style_context["selection"]}
        job_settings = {**compiled["settings"], "workflow_id": compiled["workflow_id"], "director_review_required": True,
            "director_provider": "codex", "control_mode": "assisted_manual",
            "stage": step, "setup_sha256": setup_hash, "lineage": lineage}
        batches.append({"project_id": workspace_id,
            "run_id": run_id,
            "idempotency_key": f"image-stage-{digest}",
            "workflow_id": compiled["workflow_id"], "workflow_version": compiled["workflow_version"],
            "asset_role": asset_role, "prompt": compiled["prompt"],
            "settings": job_settings, "candidates": compiled["candidates"]})
    return batches


def build_clip_frame_image_batches(*, workspace_id: str, screenplay: dict[str, Any],
                                   setup: dict[str, Any], run_id: str,
                                   skipped_shots: set[tuple[int, int]] | None = None,
                                   selected_frames: set[tuple[str, str]] | None = None,
                                   graph: dict[str, Any] | None = None,
                                   selected_entity_images: dict[str, dict[str, str]] | None = None,
                                   selected_frame_images: dict[tuple[str, str], dict[str, str]] | None = None,
                                   style_selection: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Compile one Director-reviewed first/last-frame batch per unskipped clip role."""
    step = "frame_images"
    setup_data = setup.get("setup") if isinstance(setup, dict) else None
    if (not isinstance(setup_data, dict) or setup_data.get("mode") != "assisted_manual"
            or setup_data.get("automate_steps", {}).get(step) is not True):
        raise ValueError("Save Assisted manual setup with frame images checked before admission.")
    settings = setup_data.get("image_stage_settings", {}).get(step)
    if not isinstance(settings, dict):
        raise ValueError("Confirmed workflow settings are missing for frame_images.")
    body = screenplay.get("screenplay") if isinstance(screenplay.get("screenplay"), dict) else {}
    scenes = body.get("scenes")
    if not isinstance(scenes, list):
        raise ValueError("Automated frame generation requires the accepted screenplay scenes.")
    selected = selected_frames or set()
    graph_records = {record.get("record_id"): record for record in (graph or {}).get("records", [])
        if isinstance(record, dict) and isinstance(record.get("record_id"), str)}
    entity_images = selected_entity_images or {}
    frame_images = selected_frame_images or {}
    skipped = skipped_shots or set()
    setup_hash = hashlib.sha256(json.dumps(setup_data, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    style_context = _style_context(style_selection)
    style_hash = style_context_sha256(style_selection)
    batches = []
    for scene in scenes:
        if not isinstance(scene, dict) or type(scene.get("scene_number")) is not int:
            continue
        scene_number = scene["scene_number"]
        shots = scene.get("shots") if isinstance(scene.get("shots"), list) else []
        for shot in shots:
            if not isinstance(shot, dict) or type(shot.get("shot_number")) is not int:
                continue
            shot_number = shot["shot_number"]
            if (scene_number, shot_number) in skipped:
                continue
            clip_id = _story_clip_id(workspace_id, screenplay["screenplay_revision_id"], scene_number, shot_number)
            for role in FRAME_ROLES:
                if (role, clip_id) in selected:
                    continue
                frame_label = "opening" if role == "first_frame" else "ending"
                scene_title = str(scene.get("slugline") or scene.get("title") or f"Scene {scene_number}")
                summary = str(shot.get("action") or shot.get("summary") or scene.get("summary") or "")
                shot_direction = shot.get("direction") if isinstance(shot.get("direction"), dict) else {}
                direction = " ".join(str(shot_direction.get(field, "")) for field in
                    ("camera", "lighting", "mood", "sfx", "music"))
                cited_entities = [graph_records[record_id] for record_id in shot.get("evidence_record_ids", [])
                    if record_id in graph_records and graph_records[record_id].get("kind") == "entity"
                    and str(graph_records[record_id].get("type", "")).casefold() in {"character", "location"}]
                reference_items = []
                # A final frame may use its accepted opening frame as a direct continuity reference.
                if role == "last_frame":
                    opening = frame_images.get(("first_frame", clip_id))
                    if opening:
                        reference_items.append(("opening frame", opening))
                for entity in cited_entities:
                    reference = entity_images.get(entity["record_id"])
                    if reference and all(item[1].get("asset_id") != reference.get("asset_id") for item in reference_items):
                        reference_items.append((f"{entity.get('type', 'entity')} {entity.get('name', '')}".strip(), reference))
                reference_items = reference_items[:3]
                workflow_id = settings["workflow_id"]
                if workflow_id != "qwen_image_edit_2511":
                    reference_items = []
                reference_notes = " ".join(f"Reference {index}: {label}." for index, (label, _item) in enumerate(reference_items, 1))
                cast_context = ", ".join(str(entity.get("name", "")).strip() for entity in cited_entities
                    if str(entity.get("name", "")).strip())
                prompt_body = (f"Create the {frame_label} frame for {scene_title}, shot {scene_number}.{shot_number}. "
                    f"Screenplay action: {summary}. Production direction: {direction}. "
                    f"Screenplay-cited characters and locations: {cast_context or 'none explicitly cited'}. {reference_notes} "
                    f"Pinned style: {style_context['guidance']}. Preserve the screenplay's characters, setting, "
                    "wardrobe, lighting and spatial continuity. Do not add text or a collage.")
                prompt = prompt_body + " Produce one cinematic frame, with no captions, labels, or watermark."
                if len(prompt) > IMAGE_PROMPT_MAX_CODEPOINTS:
                    raise ValueError(f"Frame image prompt for scene {scene_number}, shot {shot_number} exceeds "
                        f"the {IMAGE_PROMPT_MAX_CODEPOINTS:,}-character image limit; shorten the screenplay direction.")
                reference_hash = hashlib.sha256(json.dumps([item for _, item in reference_items], sort_keys=True,
                    separators=(",", ":")).encode()).hexdigest()
                identity = (f"{workspace_id}\0{screenplay['screenplay_revision_id']}\0{step}\0"
                    f"{clip_id}\0{role}\0{setup_hash}\0{style_hash}")
                if reference_items:
                    identity += f"\0{reference_hash}"
                if workflow_id == "qwen_image_edit_2511" and not reference_items:
                    raise ValueError(f"Qwen Image Edit needs at least one selected character, location, or opening-frame image for {scene_title}, shot {scene_number}.{shot_number}.")
                source_images = [f"frame-ref-{index}.png" for index in range(1, len(reference_items) + 1)]
                digest = hashlib.sha256(identity.encode()).hexdigest()
                compiled = compile_image_candidates(workflow_id=workflow_id, prompt=prompt,
                    control_mode="assisted_manual", seed=int(digest[:8], 16), initial_candidate_count=1,
                    output_prefix=f"{workspace_id}/{role}/{digest[:16]}",
                    width=settings["width"], height=settings["height"], steps=settings["steps"], cfg=settings["cfg"],
                    source_images=source_images if workflow_id == "qwen_image_edit_2511" else None)
                lineage = {"screenplay_revision_id": screenplay["screenplay_revision_id"],
                    "source_revision_id": screenplay["source_revision_id"],
                    "graph_snapshot_id": screenplay["graph_snapshot_id"], "target_type": "clip",
                    "target_name": f"{scene_title} · shot {scene_number}.{shot_number} · {frame_label} frame",
                    "clip_id": clip_id, "scene_number": scene_number, "shot_number": shot_number,
                    "referenced_entity_ids": [entity["record_id"] for entity in cited_entities],
                    "image_reference_asset_ids": [item["asset_id"] for _, item in reference_items],
                    "screenplay_context": f"{scene_title}. {summary}. {direction}"[:1800],
                    "style_selection_snapshot_id": screenplay.get("style_selection_snapshot_id"),
                    "style_selection_sha256": style_hash, "style_selection": style_context["selection"]}
                job_settings = {**compiled["settings"], "workflow_id": compiled["workflow_id"],
                    "director_review_required": True, "director_provider": "codex",
                    "control_mode": "assisted_manual", "stage": step,
                    "setup_sha256": setup_hash, "lineage": lineage}
                if workflow_id == "qwen_image_edit_2511":
                    job_settings["image_references"] = [item for _, item in reference_items]
                batches.append({"project_id": workspace_id, "run_id": run_id,
                    "idempotency_key": f"image-stage-{digest}",
                    "workflow_id": compiled["workflow_id"], "workflow_version": compiled["workflow_version"],
                    "asset_role": role, "prompt": compiled["prompt"],
                    "settings": job_settings, "candidates": compiled["candidates"]})
    return batches


def build_world_view_image_batch(*, workspace_id: str, screenplay: dict[str, Any],
                                 setup: dict[str, Any], target: dict[str, Any],
                                 base_asset: dict[str, Any], prompt: str,
                                 knowledge_ref: dict[str, Any], run_id: str,
                                 style_selection: dict[str, Any] | None = None) -> dict[str, Any]:
    """Compile the saved, selected world master into its configured direction views."""
    setup_data = setup.get("setup") if isinstance(setup, dict) else None
    stage = (setup_data or {}).get("image_stage_settings", {}).get("world_images", {})
    count = stage.get("world_view_count", 4)
    if (not isinstance(setup_data, dict) or setup_data.get("mode") != "assisted_manual"
            or setup_data.get("automate_steps", {}).get("world_images") is not True
            or type(count) is not int or count not in {2, 3, 4, 8}):
        raise ValueError("Automated world views require an Assisted manual setup with two, three, four or eight views.")
    if (target.get("kind") != "entity" or str(target.get("type", "")).casefold() != "location"
            or not isinstance(target.get("record_id"), str) or not target.get("record_id")
            or "world_master" not in base_asset.get("roles", [])
            or not isinstance(base_asset.get("asset_id"), str)
            or not isinstance(base_asset.get("sha256"), str)):
        raise ValueError("World views require a selected location and its saved world master image.")
    setup_hash = hashlib.sha256(json.dumps(setup_data, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    style_context = _style_context(style_selection)
    style_hash = style_context_sha256(style_selection)
    prompt = prompt.strip()
    if style_selection:
        prompt = f"{prompt}\n\nPinned directing style: {style_context['guidance']}"
    if len(prompt) > IMAGE_PROMPT_MAX_CODEPOINTS:
        raise ValueError(f"World-view prompt exceeds the {IMAGE_PROMPT_MAX_CODEPOINTS:,}-character image limit; shorten the prompt or style guidance.")
    digest = world_view_batch_digest(workspace_id=workspace_id,
        screenplay_revision_id=screenplay["screenplay_revision_id"], target_record_id=target["record_id"],
        base_asset=base_asset, view_count=count, setup_sha256=setup_hash, style_sha256=style_hash)
    defaults = compile_image_candidates(workflow_id="qwen_image_multi_angle_2511", prompt=prompt,
        control_mode="assisted_manual", seed=int(digest[:8], 16), output_prefix=f"{workspace_id}/world_view/{digest[:16]}",
        world_view_count=count, source_images=["world-master.png"])
    lineage = {"screenplay_revision_id": screenplay["screenplay_revision_id"],
        "source_revision_id": screenplay["source_revision_id"], "graph_snapshot_id": screenplay["graph_snapshot_id"],
        "target_type": "location", "target_record_id": target["record_id"],
        "target_name": target.get("name", "Location"), "target_detail": target.get("detail", ""),
        "base_asset_id": base_asset["asset_id"], "base_asset_sha256": base_asset["sha256"],
        "style_selection_snapshot_id": screenplay.get("style_selection_snapshot_id"),
        "style_selection_sha256": style_hash, "style_selection": style_context["selection"]}
    settings = {**defaults["settings"], "workflow_id": defaults["workflow_id"],
        "control_mode": "assisted_manual", "stage": "world_images", "automated_world_views": True,
        "setup_sha256": setup_hash, "lineage": lineage,
        "image_references": [{"asset_id": base_asset["asset_id"], "sha256": base_asset["sha256"]}],
        "required_reference_role": "world_master", "style_selection": style_selection,
        "prompt_knowledge_ref": knowledge_ref}
    return {"project_id": workspace_id, "run_id": run_id,
        "idempotency_key": f"world-view-stage-{digest}", "workflow_id": defaults["workflow_id"],
        "workflow_version": defaults["workflow_version"], "asset_role": "world_view",
        "prompt": defaults["prompt"], "settings": settings, "candidates": defaults["candidates"]}


def world_view_batch_digest(*, workspace_id: str, screenplay_revision_id: str,
                            target_record_id: str, base_asset: dict[str, Any],
                            view_count: int, setup_sha256: str, style_sha256: str = "") -> str:
    identity = (f"{workspace_id}\0{screenplay_revision_id}\0world_views\0{target_record_id}\0"
        f"{base_asset.get('asset_id')}\0{base_asset.get('sha256')}\0{view_count}\0{setup_sha256}\0{style_sha256}")
    return hashlib.sha256(identity.encode()).hexdigest()


def _story_clip_id(workspace_id: str, screenplay_revision_id: str, scene_number: int, shot_number: int) -> str:
    identity = f"{workspace_id}\0{screenplay_revision_id}\0{scene_number}\0{shot_number}"
    return "story-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:40]


def _style_context(selection: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(selection, dict):
        return {"selection": None, "guidance": "No pinned production style was selected."}
    guidance = selection.get("narrative_guidance")
    profile = selection.get("director_profile")
    direction = selection.get("directing_style")
    parts = [f"Production type: {selection.get('production_type', 'unspecified')}"]
    if isinstance(guidance, dict):
        for stage in ("image", "scene_direction", "story"):
            value = guidance.get(stage)
            if isinstance(value, str) and value.strip():
                parts.append(f"{stage}: {value.strip()[:1200]}")
    if isinstance(profile, dict):
        for field in ("purpose", "behavior"):
            value = profile.get(field)
            if isinstance(value, str) and value.strip():
                parts.append(f"director {field}: {value.strip()[:800]}")
            elif isinstance(value, list):
                parts.extend(f"director {field}: {item.strip()[:300]}" for item in value[:4]
                    if isinstance(item, str) and item.strip())
    if isinstance(direction, dict):
        direction_name = direction.get("display_name")
        direction_guidance = direction.get("guidance")
        if isinstance(direction_name, str) and direction_name.strip():
            parts.append(f"Directing style: {direction_name.strip()}")
        if isinstance(direction_guidance, str) and direction_guidance.strip():
            parts.append(f"directing style guidance: {direction_guidance.strip()[:1600]}")
    frozen = {key: selection.get(key) for key in ("snapshot_id", "production_type", "style_version_id", "narrative_hash", "director_profile_hash")}
    if isinstance(direction, dict):
        frozen["directing_style"] = {key: direction.get(key) for key in
            ("style_id", "style_version_id", "version", "style_hash") if direction.get(key) is not None}
    return {"selection": frozen, "guidance": " ".join(parts)}


def style_context_sha256(selection: dict[str, Any] | None) -> str:
    context = _style_context(selection)
    return hashlib.sha256(json.dumps(context, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _screenplay_context(screenplay: dict[str, Any], target_name: str) -> str:
    body = screenplay.get("screenplay") if isinstance(screenplay.get("screenplay"), dict) else {}
    scenes = body.get("scenes") if isinstance(body.get("scenes"), list) else []
    # Include compact, accepted screenplay direction that directly names this target.
    excerpts = []
    for scene in scenes:
        if not isinstance(scene, dict):
            continue
        text = " ".join(str(scene.get(key, "")) for key in ("slugline", "summary"))
        shots = scene.get("shots") if isinstance(scene.get("shots"), list) else []
        text += " " + " ".join(" ".join(str(shot.get(key, "")) for key in ("action", "lighting", "mood"))
            for shot in shots if isinstance(shot, dict))
        if target_name.casefold() in text.casefold():
            excerpts.append(text.strip()[:700])
        if len(excerpts) >= 3:
            break
    return " ".join(excerpts)[:1800] or "No scene directly names this target; use its canonical graph description."
