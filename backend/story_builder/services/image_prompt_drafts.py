"""Prepare one editable image prompt from screenplay context and exact workflow guidance."""
from __future__ import annotations

import json

from story_builder.services.production_image_workflows import SPECS, IMAGE_PROMPT_MAX_CODEPOINTS, validate_multi_angle_prompt, ImageWorkflowError
from story_builder.services.production_ledger import LedgerConflict


CHARACTER_APPEARANCE_BRIEF = (
    "The final image prompt must describe only the human's visible physical features, hair, face, build, "
    "clothing, neutral pose, framing and plain white studio background. "
    "Translate any relevant occupation into concrete visible clothing; omit the occupation/job title itself. "
    "Keep story actions, locations, equipment, tools, vehicles, handheld objects and other characters out of the final prompt. "
    "This applies to the current notes too: rewrite them rather than repeating their story-role wording. "
    "Use positive visual descriptions only; do not list unwanted objects, even in negations such as 'no bicycle'. "
    "For example, 'bicycle mechanic' may become 'a man wearing a plain work shirt and trousers, standing upright "
    "with relaxed empty hands, full-length against a plain white studio background'; "
    "the job title and its associated object must not appear in the final prompt. "
    "Describe established appearance facts; omit unknown details instead of inventing canon or discussing missing information."
)


def prepare_image_prompt(*, workflow_knowledge, workflow_id: str, asset_role: str,
                         prompt_seed: str, story_context: dict | None = None,
                         target_context: dict | None = None,
                         style_context: dict | None = None,
                         references: list[dict] | None = None,
                         world_view_count: int | None = None,
                         provider_call=None) -> dict:
    """Draft without submitting work; the caller owns authorization/context checks."""
    if workflow_id not in SPECS:
        raise ValueError("Choose a supported image workflow.")
    if asset_role not in {"character_master", "world_master", "first_frame", "last_frame", "character_view", "world_view", "image_candidate"}:
        raise ValueError("Choose a supported image asset role.")
    if not isinstance(prompt_seed, str) or len(prompt_seed) > IMAGE_PROMPT_MAX_CODEPOINTS:
        raise ValueError("The existing image prompt must be under 7,000 characters.")
    if world_view_count is not None and world_view_count not in {2, 3, 4, 8}:
        raise ValueError("World view count must be two, three, four or eight.")
    model_id = "qwen_image_edit_2511" if workflow_id == "qwen_image_multi_angle_2511" else workflow_id
    guidance = workflow_knowledge.get(workflow_id, model_id=model_id)
    if guidance.get("retrieval_status") != "matched":
        raise LedgerConflict("No curated guidance exists for this exact image model and workflow.")
    facts = [{"kind": node["kind"], "guidance": node["text"], "sources": [
        {"uri": source["uri"], "version": source["version"], "section": source["section"]}
        for source in guidance["sources"] if source["source_id"] in node["source_ids"]]}
        for node in guidance["nodes"]]
    asset_brief = (
        "CHARACTER MASTER: Show exactly one character, alone against a plain white studio background. "
        "Do not depict story scenery, buildings, landscapes, other people or a scene from the screenplay. "
        "Use supplied character facts for appearance and clothing; this is a reusable character asset. " + CHARACTER_APPEARANCE_BRIEF
        if asset_role == "character_master" else
        "WORLD MASTER: Show only the environment/location. No people or characters. "
        "Use supplied location facts; this is a reusable empty environment asset. "
        "Treat aliases, landmark mentions and exterior framings of this setting as one location identity. "
        "Preserve established architecture, landmark placement and layout from selected references; do not redesign "
        "the same building for a closer view. A separately established interior may have its own master, "
        "but must remain consistent with its parent setting. Do not invent a parent relationship or claim "
        "a reference is attached unless it appears in SELECTED IMAGE REFERENCES."
        if asset_role == "world_master" else
        "CHARACTER REFERENCE: Preserve the referenced character's identity, clothing and plain white background; no scenery or other characters. " + CHARACTER_APPEARANCE_BRIEF
        if asset_role == "character_view" else
        "WORLD REFERENCE: Preserve the referenced environment, with no people or characters."
        if asset_role == "world_view" else
        "FIRST FRAME: Compose one still showing the opening state of the exact TARGET shot/clip, before its action unfolds. "
        "Use the selected character and world references for identity, clothing, architecture and layout. "
        "Describe the visible composition, positions, lighting and starting expressions in concrete language. "
        "Do not depict the ending, multiple moments, a contact sheet or unrelated scenes."
        if asset_role == "first_frame" else
        "LAST FRAME: Compose one still showing the ending state of the same TARGET shot/clip after its action. "
        "Maintain identity, clothing, location geometry, lighting and screen direction from selected references. "
        "If a selected first frame is attached, use it as the continuity anchor and change only what the shot action requires. "
        "Do not invent an attached first frame. Describe the final visible state, not an action sequence or unrelated scene."
        if asset_role == "last_frame" else "Follow the supplied shot and frame direction."
    )
    if workflow_id == "qwen_image_multi_angle_2511":
        asset_brief += (" Native camera nodes supply every viewing direction separately. "
            "Write only a shared identity/environment preservation instruction. Do not specify side, front, back, "
            "viewpoint, camera angle, zoom or framing in this shared prompt. Rewrite conflicting angle instructions "
            "in the current notes; do not copy them into the result.")
    prompt = provider_call or _default_provider
    request = (
        "Prepare one editable image-generation prompt. Return only JSON: {\"prompt\":\"...\"}. "
        "Use only supplied screenplay and target facts. Do not invent story canon, character traits, locations, "
        "or claim unselected images are attached. Apply the selected workflow's source-linked constraints. "
        "Use parameter and reference limits to avoid impossible directions, but do not put workflow settings or metadata in the image prompt. "
        "The result is a draft for the director to review; do not submit generation. "
        f"Keep prompt shorter than {IMAGE_PROMPT_MAX_CODEPOINTS + 1} Unicode code points.\n"
        f"ASSET BRIEF (required): {asset_brief}\n"
        f"MODEL: {model_id}\nWORKFLOW: {workflow_id}\nASSET ROLE: {asset_role}\n"
        f"WORKFLOW GUIDANCE: {json.dumps(facts, ensure_ascii=False)}\n"
        f"SCREENPLAY CONTEXT: {json.dumps(story_context or {}, ensure_ascii=False)}\n"
        f"TARGET CONTEXT: {json.dumps(target_context or {}, ensure_ascii=False)}\n"
        f"PINNED STYLE DIRECTION: {json.dumps(style_context or {}, ensure_ascii=False)}\n"
        f"SELECTED IMAGE REFERENCES: {json.dumps(references or [], ensure_ascii=False)}\n"
        f"WORLD VIEW COUNT: {world_view_count if world_view_count is not None else 'not applicable'}\n"
        f"DIRECTOR'S CURRENT PROMPT / NOTES: {prompt_seed}"
    )
    result = prompt(temperature=0, prompt=request)
    value = result.get("prompt") if isinstance(result, dict) else None
    if not isinstance(value, str) or not value.strip() or len(value) > IMAGE_PROMPT_MAX_CODEPOINTS:
        raise ValueError("The reasoning model did not return an image prompt under the 7,000-character limit.")
    if workflow_id == "qwen_image_multi_angle_2511":
        try:
            validate_multi_angle_prompt(value)
        except ImageWorkflowError:
            result = prompt(temperature=0, prompt=request +
                "\nCORRECTION: The previous draft incorrectly fixed a viewing direction: " + value +
                "\nReturn corrected JSON with a neutral preservation instruction only. "
                "Remove side/front/back/profile view wording; native camera nodes supply orientation.")
            value = result.get("prompt") if isinstance(result, dict) else None
            if not isinstance(value, str) or not value.strip() or len(value) > IMAGE_PROMPT_MAX_CODEPOINTS:
                raise ValueError("The reasoning model did not return a valid corrected image prompt.")
            validate_multi_angle_prompt(value)
    return {"workflow_id": workflow_id, "asset_role": asset_role, "prompt": value,
        "knowledge_ref": {"knowledge_id": guidance["knowledge_id"],
            "guidance_version": guidance["guidance_version"],
            "workflow_sha256": guidance["workflow_sha256"]},
        "sources": guidance["sources"]}


def _default_provider(*, temperature: float, prompt: str) -> dict:
    from story_builder.services.reasoning_provider import generate_json
    return generate_json(temperature=temperature, prompt=prompt)
