"""Validated image prompt preparation shared by manual controls and Director."""
import re

from .image_prompt_drafts import prepare_image_prompt
from .isolated_image_references import validate_image_references
from .media_library import list_assets as list_media_assets
from .production_ledger import LedgerConflict
from .prompt_director import read_guidance, image_brief


def prepare(payload, *, root, story, styles, ledger, workflow_knowledge, lineage_resolver, provider=None):
    allowed = {"workspace_id", "workflow_id", "asset_role", "prompt", "screenplay_revision_id",
        "target_record_id", "scene_number", "shot_number", "clip_id", "source_references", "world_view_count"}
    if set(payload) - allowed:
        raise ValueError("Image prompt preparation received unsupported fields.")
    workspace = payload.get("workspace_id")
    if not isinstance(workspace, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", workspace):
        raise ValueError("A valid workspace_id is required.")
    role = payload.get("asset_role")
    workflow_id = payload.get("workflow_id")
    references = payload.get("source_references") or []
    if references and workflow_id not in {"qwen_image_edit_2511", "qwen_image_multi_angle_2511"}:
        raise ValueError("Only Qwen Image Edit workflows accept source image references.")
    if workflow_id == "qwen_image_multi_angle_2511" and len(references) != 1:
        raise ValueError("Qwen multi-angle views require exactly one selected base image.")
    lineage_payload = {**payload, "asset_role": role}
    lineage = lineage_resolver(story, workspace, lineage_payload)
    screenplay_context = {}
    target_context = {}
    style_context = {}
    style_selection = None
    if lineage:
        envelope = story.get_screenplay_revision(workspace, lineage["screenplay_revision_id"])
        if not envelope.get("accepted"):
            raise LedgerConflict("Image prompt preparation requires the current accepted screenplay.")
        screenplay = envelope.get("screenplay") or {}
        screenplay_context = {"title": screenplay.get("title"), "logline": screenplay.get("logline"),
            "characters": screenplay.get("characters", []),
            "scenes": [{"scene_number": scene.get("scene_number"), "slugline": scene.get("slugline"),
                "summary": scene.get("summary"), "shots": [{key: shot.get(key) for key in
                    ("shot_number", "action", "dialogue", "camera", "lighting", "mood", "sound_effects", "music", "continuity_notes")}
                    for shot in scene.get("shots", [])]}
                for scene in screenplay.get("scenes", [])]}
        style_selection = (story.get_workspace(workspace, include_source=False) or {}).get("style_selection")
        snapshot_id = envelope.get("style_selection_snapshot_id")
        if snapshot_id:
            selected_style = styles.get_selection(snapshot_id)
            style_context = {key: selected_style.get(key) for key in
                ("production_type", "style_version_id", "directing_style", "director_profile", "narrative_guidance") if selected_style.get(key) is not None}
        if lineage.get("target_record_id"):
            graph = story.get_story_graph(workspace_id=workspace, snapshot_id=lineage["graph_snapshot_id"])
            target = next((item for item in graph.get("records", [])
                if item.get("record_id") == lineage["target_record_id"]), None)
            target_context = {"kind": target.get("type"), "name": target.get("name"),
                "detail": target.get("detail"), "evidence": target.get("evidence", [])} if target else {}
        else:
            scene_no, shot_no = lineage["scene_number"], lineage["shot_number"]
            target_context = {"scene_number": scene_no, "shot_number": shot_no,
                "clip_id": lineage["clip_id"], "asset_role": role}
            scene = next(item for item in screenplay.get("scenes", []) if item.get("scene_number") == scene_no)
            shot = next(item for item in scene.get("shots", []) if item.get("shot_number") == shot_no)
            target_context.update(scene_slugline=scene.get("slugline"), scene_summary=scene.get("summary"), shot=shot)
    references = validate_image_references(media_root=root, workspace_id=workspace,
        references=references, style_selection=style_selection,
        required_role=("character_master" if role == "character_view" else "world_master") if workflow_id == "qwen_image_multi_angle_2511" else None) if references else []
    reference_context = []
    if references:
        offset, by_id = 0, {}
        while True:
            page = list_media_assets(root, workspace, kind="image", limit=100, offset=offset,
                style_selection=style_selection)
            by_id.update((asset["asset_id"], asset) for asset in page["assets"])
            offset += page["limit"]
            if offset >= page["total"] or not page["assets"]: break
        reference_context = [{"asset_id": item["asset_id"], "filename": by_id[item["asset_id"]].get("filename"),
            "roles": by_id[item["asset_id"]].get("roles", []), "annotations": by_id[item["asset_id"]].get("annotations", {}),
            "lineage": by_id[item["asset_id"]].get("metadata", {}).get("production_image_job", {}).get("settings", {}).get("lineage", {})}
            for item in references if item["asset_id"] in by_id]
    def image_prompt_provider(*, temperature, prompt):
        from story_builder.services.reasoning_provider import generate_json, get_settings
        generate = provider or generate_json
        scope = 'character' if str(role).startswith('character') else 'world' if str(role).startswith('world') else 'all'
        return generate(prompt=prompt + '\n' + read_guidance(ledger, workspace, scope), provider=get_settings()["provider"], temperature=0)
    seed = payload.get("prompt", "")
    if not seed and lineage and lineage.get("target_record_id") and role in ('character_master', 'world_master'):
        seed = image_brief(ledger, workspace, lineage['screenplay_revision_id'], lineage['target_record_id'])
    result = prepare_image_prompt(workflow_knowledge=workflow_knowledge,
        workflow_id=workflow_id, asset_role=role, prompt_seed=seed,
        story_context=screenplay_context, target_context=target_context,
        style_context=style_context, references=reference_context,
        world_view_count=payload.get("world_view_count"), provider_call=image_prompt_provider)
    return result
