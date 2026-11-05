"""Validate and freeze a Full-mode duration plan before video admission.

The Director proposes the segmentation. This module enforces ordered, exact
coverage of screenplay action/dialogue and the supported video contract.
"""
from __future__ import annotations

from story_builder.services.director_skills import director_skill_context

import hashlib
import json
import re
from typing import Any, Mapping

from story_builder.services.isolated_video_contract import T2V_WORKFLOW_ID
from story_builder.services.isolated_r2v_contract import WORKFLOW_ID as R2V_WORKFLOW_ID
from story_builder.services.isolated_fl2va_contract import WORKFLOW_ID as FL2VA_WORKFLOW_ID

PROMPT_LIMIT = 7000
_FIELDS = {"action", "dialogue"}


class ClipPlanError(ValueError):
    pass


def clip_id(workspace_id: str, screenplay_revision_id: str,
            scene_number: int, shot_number: int, clip_number: int) -> str:
    identity = f"{workspace_id}\0{screenplay_revision_id}\0{scene_number}\0{shot_number}\0{clip_number}"
    return "story-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:40]


def generate_clip_plan(*, workspace_id: str, screenplay_revision_id: str,
                       screenplay: Mapping[str, Any], drafts: Mapping[str, Any],
                       min_seconds: int, max_seconds: int,
                       has_style_video: bool = False, generate_json=None,
                       fixed_workflow_id: str | None = None,
                       scene_start_identity_refs: bool = False,
                       prompt_guidance: str = '') -> dict[str, Any]:
    """Ask the configured reasoning provider to segment each scene, then validate it.

    Planning one scene per provider call keeps long screenplays out of a single
    context window. Calls are explicit and have no media, storage, or GPU side
    effects; callers decide when to persist and execute the returned plan.
    """
    if not isinstance(screenplay, Mapping) or type(screenplay.get("scenes")) is not list:
        raise ClipPlanError("Accepted screenplay has no valid scenes to plan.")
    if not isinstance(drafts, Mapping):
        raise ClipPlanError("Saved workflow prompts must be an object.")
    if fixed_workflow_id is not None and fixed_workflow_id not in {T2V_WORKFLOW_ID, FL2VA_WORKFLOW_ID, R2V_WORKFLOW_ID}:
        raise ClipPlanError("A fixed Assisted video workflow must be T2V, FFLF or R2V.")
    if generate_json is None:
        from story_builder.services.reasoning_provider import generate_json as provider_generate_json
        generate_json = provider_generate_json

    all_clips = []
    expected_draft_keys = set()
    for scene in screenplay["scenes"]:
        if not isinstance(scene, Mapping) or type(scene.get("scene_number")) is not int:
            raise ClipPlanError("Every scene needs a valid positive scene number.")
        shots = scene.get("shots")
        if type(shots) is not list or not shots:
            raise ClipPlanError(f"Scene {scene['scene_number']} has no shots to plan.")
        scene_drafts = {}
        for shot_index, shot in enumerate(shots):
            if not isinstance(shot, Mapping) or type(shot.get("shot_number")) is not int:
                raise ClipPlanError(f"Scene {scene['scene_number']} contains a shot without a valid number.")
            key = f"{scene['scene_number']}.{shot['shot_number']}"
            if key in expected_draft_keys:
                raise ClipPlanError("Accepted screenplay contains duplicate scene/shot identities.")
            expected_draft_keys.add(key)
            draft = drafts.get(key)
            if (not isinstance(draft, Mapping) or type(draft.get("workflow_id")) is not str
                    or type(draft.get("prompt")) is not str or not draft["prompt"].strip()
                    or len(draft["prompt"]) >= PROMPT_LIMIT):
                raise ClipPlanError(f"A valid saved prompt is required for Scene {scene['scene_number']}, Shot {shot['shot_number']}.")
            expected_workflow = (fixed_workflow_id if fixed_workflow_id is not None else
                T2V_WORKFLOW_ID)
            if draft["workflow_id"] != expected_workflow:
                raise ClipPlanError(f"Saved workflow prompt for Scene {scene['scene_number']}, Shot {shot['shot_number']} must use {expected_workflow}.")
            scene_drafts[key] = dict(draft)
        # The model chooses printed word IDs; Python owns Unicode offsets and whitespace.
        source_units = {}
        unit_offsets = {}
        for shot in shots:
            key = f"{scene['scene_number']}.{shot['shot_number']}"
            source_units[key], unit_offsets[key] = {}, {}
            for field in ("action", "dialogue"):
                source = shot.get(field, "")
                if type(source) is not str:
                    raise ClipPlanError(f"Scene {scene['scene_number']}, Shot {shot['shot_number']} {field} must be text.")
                tokens = list(re.finditer(r"\S+\s*", source))
                boundaries = [0] + [match.end() for match in tokens]
                if source and not tokens:
                    boundaries.append(len(source))
                source_units[key][field] = [
                    {"id": index + 1, "text": source[start:end]}
                    for index, (start, end) in enumerate(zip(boundaries, boundaries[1:]))]
                unit_offsets[key][field] = boundaries
        payload = {"scene": dict(scene), "source_units": source_units, "saved_workflow_prompts": scene_drafts,
            "duration_bounds_seconds": {"minimum": min_seconds, "maximum": max_seconds},
            "style_video_selected": bool(has_style_video),
            "scene_start_identity_refs_available": bool(scene_start_identity_refs)}
        prompt = (
            "Plan video clips for this one accepted screenplay scene. Return only a JSON object "
            'with exactly one key: {"clips":[...]}. Every row must contain exactly '
            'scene_number, shot_number, duration_seconds, duration_reason, prompt, source_spans. '
            "Cover every shot's action and dialogue exactly once, in order. Split long material "
            "into additional clips only at natural action/dialogue boundaries. Each source_spans entry is "
            '{"field":"action" or "dialogue","first_unit":1,"last_unit":N}. '
            "Copy the inclusive first and last word IDs from source_units for that shot and field. "
            "IDs restart at 1 for each field. Cover every unit once, in order, without gaps or overlap; "
            "finish all action units before starting dialogue units. Do not calculate character offsets. "
            "For an unsplit field, use first_unit=1 and last_unit=the final printed ID. "
            "Use an empty source_spans list only when both fields are empty. "
            f"Each duration is an integer from {min_seconds} through {max_seconds} seconds. "
            "When a shot has planned_duration_seconds, use it as the target for the combined duration of its clips. "
            "Respect workflow duration bounds and complete story coverage; explain necessary deviations in duration_reason. "
            "Write short, crisp production prompts: concrete subject and essential setting/light, one observable event or tightly linked action, at most one camera move, and a clear endpoint. Aim for 60–120 words of visual direction, fewer when sufficient; this is a soft target excluding exact dialogue and required workflow fields. Never pad to the target or truncate source action or speech. Remove repeated instructions, decorative adjective/lens lists, reasoning and story summaries. Keep mandatory model section names, exact speaker-labelled dialogue and essential sound balance. "
            "Give a brief duration_reason. Build each clip prompt from that shot's saved "
            "workflow prompt and only the source spans assigned to this clip; preserve its "
            "direction and do not add story events. Each prompt must be non-empty and shorter "
            "than 7000 characters. Keep rows in screenplay order. Workflow routing "
            "is applied by the server; do not include workflow_id. Preserve the saved prompt's model-specific section structure and audio direction when splitting. Each T2V clip is independent: explicitly describe the setting/background, lighting, named characters and their appearance, exact speaker-labelled dialogue, camera, action and sound. Never rely on a prior clip or media reference. Advance the story briskly with a new beat, without padding or repeated establishment. Choose the shortest sufficient supported duration (never above 30 seconds).\n\n"
            + director_skill_context(video=True) + "\n\nINPUT JSON:\n"
            + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        )
        result = generate_json(prompt=prompt + ('\n' + prompt_guidance if prompt_guidance else ''), temperature=0.2)
        if not isinstance(result, Mapping) or type(result.get("clips")) is not list:
            raise ClipPlanError(f"The Director returned an invalid clip plan for Scene {scene['scene_number']}.")
        for row in result["clips"]:
            if isinstance(row, Mapping) and type(row.get("source_spans")) is list:
                row = dict(row)
                spans = []
                for span in row["source_spans"]:
                    if isinstance(span, Mapping) and set(span) == {"field", "first_unit", "last_unit"}:
                        field, first, last = span["field"], span["first_unit"], span["last_unit"]
                        key = f"{row.get('scene_number')}.{row.get('shot_number')}"
                        offsets = unit_offsets.get(key, {}).get(field, []) if type(field) is str else []
                        if type(first) is not int or type(last) is not int or not 1 <= first <= last < len(offsets):
                            raise ClipPlanError(f"Scene {row.get('scene_number')}, Shot {row.get('shot_number')}: choose valid printed source word IDs for {field}.")
                        span = {"field": field, "start": offsets[first - 1], "end": offsets[last]}
                    spans.append(span)
                row["source_spans"] = spans
            all_clips.append(row)

    if set(drafts) != expected_draft_keys:
        raise ClipPlanError("Saved workflow prompts must match the accepted screenplay's exact scene/shot set.")

    return validate_clip_plan(workspace_id=workspace_id,
        screenplay_revision_id=screenplay_revision_id, screenplay=screenplay,
        proposed={"clips": all_clips}, min_seconds=min_seconds,
        max_seconds=max_seconds, has_style_video=has_style_video,
        fixed_workflow_id=fixed_workflow_id,
        scene_start_identity_refs=scene_start_identity_refs)


def generate_scene_clip_plan(*, workspace_id: str, screenplay_revision_id: str,
                             screenplay: Mapping[str, Any], scene: Mapping[str, Any],
                             drafts: Mapping[str, Any], min_seconds: int,
                             max_seconds: int, has_style_video: bool = False,
                             generate_json=None,
                             scene_start_identity_refs: bool = False) -> dict[str, Any]:
    """Plan one reached scene; validate complete source coverage within it."""
    scene_number = scene.get("scene_number") if isinstance(scene, Mapping) else None
    if type(scene_number) is not int:
        raise ClipPlanError("The scene to plan needs a valid scene number.")
    scene_keys = {f"{scene_number}.{shot.get('shot_number')}"
        for shot in scene.get("shots", []) if isinstance(shot, Mapping)}
    if set(drafts) != scene_keys:
        raise ClipPlanError("Scene prompts must match that scene's exact shot set.")
    scene_source = dict(screenplay)
    scene_source["scenes"] = [dict(scene)]
    return generate_clip_plan(workspace_id=workspace_id,
        screenplay_revision_id=screenplay_revision_id, screenplay=scene_source,
        drafts=drafts, min_seconds=min_seconds, max_seconds=max_seconds,
        has_style_video=has_style_video, generate_json=generate_json,
        scene_start_identity_refs=scene_start_identity_refs)


def validate_clip_plan(*, workspace_id: str, screenplay_revision_id: str,
                       screenplay: Mapping[str, Any], proposed: Mapping[str, Any],
                       min_seconds: int, max_seconds: int,
                       has_style_video: bool = False,
                       fixed_workflow_id: str | None = None,
                       scene_start_identity_refs: bool = False) -> dict[str, Any]:
    """Return canonical ordered clips; reject incomplete or ambiguous coverage."""
    if not isinstance(proposed, Mapping) or set(proposed) != {"clips"} or type(proposed["clips"]) is not list:
        raise ClipPlanError("Director plan must contain only an ordered clips array.")
    if not isinstance(screenplay, Mapping):
        raise ClipPlanError("Accepted screenplay must be an object.")
    if type(min_seconds) is not int or type(max_seconds) is not int or not 5 <= min_seconds <= max_seconds <= 30:
        raise ClipPlanError("Duration bounds must be an integer range within 5–30 seconds.")
    if fixed_workflow_id is not None and fixed_workflow_id not in {T2V_WORKFLOW_ID, FL2VA_WORKFLOW_ID, R2V_WORKFLOW_ID}:
        raise ClipPlanError("A fixed Assisted video workflow must be T2V, FFLF or R2V.")
    scenes = screenplay.get("scenes")
    if type(scenes) is not list or not scenes:
        raise ClipPlanError("Accepted screenplay has no scenes to plan.")

    shots: list[tuple[int, int, Mapping[str, Any]]] = []
    scene_numbers = set()
    for scene in scenes:
        if not isinstance(scene, Mapping) or type(scene.get("scene_number")) is not int or scene["scene_number"] < 1:
            raise ClipPlanError("Every scene needs a valid positive scene number.")
        scene_number = scene["scene_number"]
        if scene_number in scene_numbers:
            raise ClipPlanError("Accepted screenplay contains duplicate scene numbers.")
        scene_numbers.add(scene_number)
        scene_shots = scene.get("shots")
        if type(scene_shots) is not list or not scene_shots:
            raise ClipPlanError(f"Scene {scene_number} has no shots to plan.")
        for shot in scene_shots:
            if not isinstance(shot, Mapping) or type(shot.get("shot_number")) is not int or shot["shot_number"] < 1:
                raise ClipPlanError(f"Scene {scene_number} contains a shot without a valid number.")
            if any(type(shot.get(field, "")) is not str for field in _FIELDS):
                raise ClipPlanError(f"Scene {scene_number}, Shot {shot['shot_number']} action and dialogue must be text.")
            evidence_ids = shot.get("evidence_record_ids")
            if (type(evidence_ids) is not list or not evidence_ids
                    or any(type(value) is not str or not value for value in evidence_ids)):
                raise ClipPlanError(f"Scene {scene_number}, Shot {shot['shot_number']} needs screenplay evidence record IDs.")
            character_ids = shot.get("character_record_ids", [])
            if (type(character_ids) is not list or len(character_ids) > 12
                    or any(type(value) is not str or not value for value in character_ids)
                    or len(set(character_ids)) != len(character_ids)):
                raise ClipPlanError(f"Scene {scene_number}, Shot {shot['shot_number']} has invalid target character IDs.")
            shots.append((scene_number, shot["shot_number"], shot))

    identities = [(scene, shot) for scene, shot, _ in shots]
    if len(set(identities)) != len(identities):
        raise ClipPlanError("Accepted screenplay contains duplicate scene/shot identities.")
    shot_indexes = {identity: index for index, identity in enumerate(identities)}
    cursors = {(scene, shot, field): 0 for scene, shot, source in shots
        for field in _FIELDS if type(source.get(field, "")) is str and source.get(field, "")}
    planned_per_shot: dict[tuple[int, int], int] = {}
    normalized = []
    last_shot_index = -1
    seen_scene_start: set[int] = set()

    for row in proposed["clips"]:
        fields = {"scene_number", "shot_number", "duration_seconds", "duration_reason", "prompt", "source_spans"}
        if not isinstance(row, Mapping) or set(row) != fields:
            raise ClipPlanError("Each clip must specify its screenplay shot, duration, reason, prompt and source spans.")
        scene_number, shot_number = row["scene_number"], row["shot_number"]
        identity = (scene_number, shot_number)
        if type(scene_number) is not int or type(shot_number) is not int or identity not in shot_indexes:
            raise ClipPlanError("A planned clip refers to a shot outside the accepted screenplay.")
        shot_index = shot_indexes[identity]
        if shot_index < last_shot_index:
            raise ClipPlanError("Clips must follow screenplay scene and shot order.")
        if shot_index > last_shot_index + 1:
            raise ClipPlanError("The plan omitted a screenplay shot.")
        if shot_index != last_shot_index:
            if last_shot_index >= 0:
                previous_identity = identities[last_shot_index]
                if planned_per_shot.get(previous_identity, 0) == 0:
                    raise ClipPlanError("The plan omitted a screenplay shot.")
            last_shot_index = shot_index
        source_spans = row["source_spans"]
        if type(source_spans) is not list:
            raise ClipPlanError("source_spans must be an ordered list.")
        shot_source = shots[shot_index][2]
        coverage = []
        clip_field_order = -1
        for span in source_spans:
            if not isinstance(span, Mapping) or set(span) != {"field", "start", "end"}:
                raise ClipPlanError("Each source span must name a field and half-open character offsets.")
            field, start, end = span["field"], span["start"], span["end"]
            if type(field) is not str or field not in _FIELDS or type(start) is not int or type(end) is not int or start < 0 or end <= start:
                raise ClipPlanError("Source spans must use action/dialogue and valid half-open character offsets.")
            field_order = 0 if field == "action" else 1
            if field_order < clip_field_order:
                raise ClipPlanError("Action and dialogue spans must retain screenplay order.")
            clip_field_order = field_order
            source = shot_source.get(field, "")
            cursor_key = (scene_number, shot_number, field)
            if type(source) is not str or not source or cursor_key not in cursors:
                raise ClipPlanError("A source span refers to empty screenplay text.")
            if start != cursors[cursor_key] or end > len(source):
                raise ClipPlanError(f"Scene {scene_number}, Shot {shot_number} {field}: the Director's clip ranges leave a gap or overlap (expected character {cursors[cursor_key]}, got {start}–{end}, field length {len(source)}). Prepare screenplay clips again.")
            if field == "dialogue" and cursors.get((scene_number, shot_number, "action"), 0) < len(shot_source.get("action", "")):
                raise ClipPlanError("Dialogue coverage cannot begin before the shot's action is fully covered.")
            if field == "action" and cursors.get((scene_number, shot_number, "dialogue"), 0) > 0:
                raise ClipPlanError("Action coverage cannot resume after dialogue has begun.")
            cursors[cursor_key] = end
            coverage.append({"field": field, "start": start, "end": end, "text": source[start:end]})
        if not source_spans and any(type(shot_source.get(field, "")) is str and shot_source.get(field, "") for field in _FIELDS):
            raise ClipPlanError("A clip with screenplay action/dialogue must identify the text it covers.")
        duration = row["duration_seconds"]
        if type(duration) is not int or not min_seconds <= duration <= max_seconds:
            raise ClipPlanError(f"Every clip duration must be an integer from {min_seconds} through {max_seconds} seconds.")
        reason, prompt = row["duration_reason"], row["prompt"]
        if type(reason) is not str or not reason.strip() or len(reason) > 1000:
            raise ClipPlanError("Every clip needs a concise duration reason.")
        if type(prompt) is not str or not prompt.strip() or len(prompt) >= PROMPT_LIMIT:
            raise ClipPlanError("Every final clip prompt must be non-empty and below 7000 characters.")
        clip_number = planned_per_shot.get(identity, 0) + 1
        if not any(type(shot_source.get(field, "")) is str and shot_source.get(field, "") for field in _FIELDS) and clip_number > 1:
            raise ClipPlanError("A direction-only screenplay shot can use one clip, not repeated empty coverage.")
        planned_per_shot[identity] = clip_number
        scene_start = scene_number not in seen_scene_start
        seen_scene_start.add(scene_number)
        workflow = (fixed_workflow_id if fixed_workflow_id is not None else
            T2V_WORKFLOW_ID)
        evidence_ids = shot_source["evidence_record_ids"]
        normalized.append({"clip_id": clip_id(workspace_id, screenplay_revision_id,
            scene_number, shot_number, clip_number), "scene_number": scene_number,
            "shot_number": shot_number, "clip_number": clip_number,
            "workflow_id": workflow, "duration_seconds": duration,
            "duration_reason": reason.strip(), "prompt": prompt,
            "source_spans": coverage, "evidence_record_ids": list(evidence_ids),
            "target_character_ids": list(shot_source.get("character_record_ids", [])),
            "character_refs_required": False})

    if not normalized:
        raise ClipPlanError("Director plan contains no clips.")
    if len(planned_per_shot) != len(shots):
        raise ClipPlanError("The plan must include every screenplay shot.")
    for scene_number, shot_number, shot in shots:
        for field in _FIELDS:
            source = shot.get(field, "")
            if type(source) is str and source and cursors.get((scene_number, shot_number, field), 0) != len(source):
                raise ClipPlanError(f"The plan does not fully cover Scene {scene_number}, Shot {shot_number} {field}.")
    return {"clips": normalized}
