"""Explicitly enabled durable consumer for product image candidates.

The API never starts this process. Start it separately with --enable-worker
after reviewing local ComfyUI and GPU readiness.
"""
from __future__ import annotations
from story_builder.services.storage_paths import generated_root

import argparse
import fcntl
import hashlib
import json
import logging
import os
import signal
import threading
import time
from urllib.parse import quote
from contextlib import contextmanager
from pathlib import Path

from story_builder.services.media_library import register_generated_image, list_assets
from story_builder.services.media_library import asset_path, assign_role as assign_media_role
from story_builder.services.production_image_jobs import ProductionImageJobStore
from story_builder.services.production_image_admission import build_world_view_image_batch
from story_builder.services.production_image_selection import ProductionImageSelection
from story_builder.services.isolated_video_jobs import story_clip_id
from story_builder.services.production_setup import ProductionSetup
from story_builder.services.production_ledger import ProductionLedger
from story_builder.services.character_voice_bindings import CharacterVoiceBindings
from story_builder.services.production_image_worker import (
    ProductionImageWorker, ProductionImageWorkerSupervisor, comfyui_root, _request_json,
)
from story_builder.services.isolated_image_references import (
    cleanup_image_reference_staging, prepare_image_edit_graph,
)
from story_builder.services.reasoning_provider import generate_json, provider_catalog
from story_builder.services.story_authoring import StoryAuthoring

LOGGER = logging.getLogger(__name__)


def _director_review(job: dict, image_path: Path) -> dict:
    """Ask the saved Codex provider to judge one image; never infer acceptance locally."""
    settings = job.get("settings") or {}
    lineage = settings.get("lineage") or {}
    role = job.get("asset_role")
    target_type = lineage.get("target_type")
    target_name = lineage.get("target_name") or "the screenplay target"
    style = lineage.get("style_selection") or {}
    is_frame = role in {"first_frame", "last_frame"} and target_type == "clip"
    is_entity = role in {"character_master", "world_master"} and target_type in {"character", "location"}
    if not (is_frame or is_entity):
        return {"schema_version": 1, "action": "blocked",
            "reason": "Automated image review requires a canonical screenplay character, location, or clip-frame target.",
            "prompt_delta": "", "criteria": [], "confidence": 0.0,
            "image_sha256": hashlib.sha256(image_path.read_bytes()).hexdigest()}
    prompt = (
        "Review the attached generated image for the specified Vibe Director screenplay target. "
        "Judge whether it clearly depicts the target and follows its saved image prompt. "
        "Do not claim visual details that are not visible. Return JSON only with keys: "
        "schema_version (1), action (accept, retake, or blocked), reason (short string), "
        "prompt_delta (string), criteria (array of short strings), confidence (0 to 1). "
        "Use retake only for a clear, correctable mismatch; use blocked if uncertain.\n\n"
        f"Target type: {target_type}\nTarget: {target_name}\n"
        f"Image prompt: {job.get('prompt', '')}\n"
        f"Saved screenplay description: {lineage.get('target_detail', '')}\n"
        f"Pinned production style: {style.get('production_type', 'none')} / {style.get('style_version_id', 'none')}\n"
        f"Relevant screenplay direction: {lineage.get('screenplay_context', '')}"
    )
    digest = hashlib.sha256(image_path.read_bytes()).hexdigest()
    decision = generate_json(prompt=prompt, provider=settings.get("director_provider", "codex"),
        image_paths=[image_path])
    action = decision.get("action")
    confidence = decision.get("confidence")
    criteria = decision.get("criteria")
    if (decision.get("schema_version") != 1 or action not in {"accept", "retake", "blocked"}
            or not isinstance(confidence, (int, float)) or isinstance(confidence, bool)
            or not 0 <= confidence <= 1 or not isinstance(criteria, list)
            or not all(isinstance(item, str) for item in criteria)):
        raise ValueError("Codex returned an invalid visual review decision.")
    return {"schema_version": 1, "action": action,
        "reason": str(decision.get("reason", ""))[:1200],
        "prompt_delta": str(decision.get("prompt_delta", ""))[:1200],
        "criteria": criteria[:12], "confidence": float(confidence), "image_sha256": digest}


def _director_provider_preflight(provider: str) -> dict:
    entry = next((item for item in provider_catalog().get("providers", []) if item.get("id") == provider), None)
    if not entry or not entry.get("available"):
        raise RuntimeError(f"Saved Director provider {provider!r} is unavailable.")
    return entry


def _director_acceptor(*, root: Path, story: StoryAuthoring,
                       selections: ProductionImageSelection, setup_service: ProductionSetup,
                       image_jobs: ProductionImageJobStore | None = None,
                       character_voices: CharacterVoiceBindings | None = None):
    def validate_candidate(job: dict) -> str | None:
        settings = job.get("settings") or {}
        lineage = settings.get("lineage") or {}
        role = job.get("asset_role")
        target_type = lineage.get("target_type")
        is_world_views = role == "world_view" and target_type == "location" and settings.get("automated_world_views") is True
        is_frame = role in {"first_frame", "last_frame"} and target_type == "clip"
        is_entity = role in {"character_master", "world_master"} and target_type in {"character", "location"}
        if (not (is_frame or is_entity or is_world_views) or not lineage.get("screenplay_revision_id")
                or (is_entity and not lineage.get("target_record_id"))
                or (is_world_views and not lineage.get("target_record_id"))
                or (is_frame and (not lineage.get("clip_id") or type(lineage.get("scene_number")) is not int
                    or type(lineage.get("shot_number")) is not int))):
            return "Automated image generation requires a canonical accepted screenplay target."
        revision = story.get_screenplay_revision(job["project_id"], lineage["screenplay_revision_id"])
        if (not revision.get("accepted") or revision.get("source_revision_id") != lineage.get("source_revision_id")
                or revision.get("graph_snapshot_id") != lineage.get("graph_snapshot_id")
                or revision.get("style_selection_snapshot_id") != lineage.get("style_selection_snapshot_id")):
            return "The screenplay, pinned graph, or production style is no longer current."
        setup_state = setup_service.get(job["project_id"], lineage["screenplay_revision_id"])
        setup = setup_state.get("setup") or {}
        if is_frame:
            expected_clip = story_clip_id(job["project_id"], lineage["screenplay_revision_id"],
                lineage["scene_number"], lineage["shot_number"])
            if expected_clip != lineage.get("clip_id"):
                return "The frame target no longer matches its accepted screenplay clip."
            scenes = (revision.get("screenplay") or {}).get("scenes", [])
            shot_exists = any(isinstance(scene, dict) and scene.get("scene_number") == lineage["scene_number"]
                and any(isinstance(shot, dict) and shot.get("shot_number") == lineage["shot_number"]
                    for shot in scene.get("shots", [])) for scene in scenes)
            if not shot_exists:
                return "The frame target is no longer present in the accepted screenplay."
            if setup_service.frame_preparation_is_skipped(job["project_id"], lineage["screenplay_revision_id"],
                    lineage["scene_number"], lineage["shot_number"]):
                return "Frame preparation is skipped for this screenplay shot."
            step = "frame_images"
        elif is_world_views:
            step = "world_images"
        else:
            step = "character_images" if role == "character_master" else "world_images"
        setup_hash = hashlib.sha256(json.dumps(setup, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        if (setup.get("mode") != "assisted_manual" or setup.get("automate_steps", {}).get(step) is not True
                or settings.get("stage") != step or settings.get("setup_sha256") != setup_hash):
            return "The saved image stage changed after admission; this candidate cannot become the selected master."
        configured = setup.get("image_stage_settings", {}).get(step) or {}
        if is_world_views:
            count = configured.get("world_view_count", 4)
            current = selections.get(project_id=job["project_id"], screenplay_revision_id=lineage["screenplay_revision_id"],
                target_type="location", target_record_id=lineage["target_record_id"])
            reference = (settings.get("image_references") or [{}])[0]
            try:
                path, _media_type, _filename = asset_path(root, job["project_id"], lineage.get("base_asset_id", ""))
                actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
            except (OSError, ValueError):
                return "The selected world master is no longer available in this workspace."
            if (current is None or current.get("asset_id") != lineage.get("base_asset_id")
                    or reference.get("asset_id") != lineage.get("base_asset_id")
                    or reference.get("sha256") != lineage.get("base_asset_sha256")
                    or actual_hash != lineage.get("base_asset_sha256")
                    or type(count) is not int or len(settings.get("world_views", [])) != count):
                return "The selected world master or directional-view count changed after admission."
        elif any(settings.get(key) != configured.get(key) for key in ("workflow_id", "width", "height", "steps", "cfg")):
            return "The confirmed image workflow or parameters changed after admission."
        return None

    def accept_candidate(job: dict):
        settings = job.get("settings") or {}
        lineage = settings.get("lineage") or {}
        role = job.get("asset_role")
        target_type = lineage.get("target_type")
        is_world_views = (role == "world_view" and target_type == "location"
            and settings.get("automated_world_views") is True)
        is_frame = role in {"first_frame", "last_frame"} and target_type == "clip" and bool(lineage.get("clip_id"))
        is_entity = (role in {"character_master", "world_master"}
            and target_type in {"character", "location"} and bool(lineage.get("target_record_id")))
        if (not (is_frame or is_entity or is_world_views) or not lineage.get("screenplay_revision_id")):
            raise ValueError("Automated selection requires a canonical accepted screenplay target.")
        stale_reason = validate_candidate(job)
        if stale_reason:
            raise ValueError(stale_reason)
        if is_world_views:
            assign_media_role(root, job["project_id"], job["output_asset_id"], "world_view")
            return {"world_view": True, "asset_id": job["output_asset_id"]}
        setup_state = setup_service.get(job["project_id"], lineage["screenplay_revision_id"])
        setup = setup_state.get("setup") or {}
        step = "character_images" if role == "character_master" else "world_images"
        selection_type = role if is_frame else target_type
        selection_target = lineage["clip_id"] if is_frame else lineage["target_record_id"]
        current = selections.get(project_id=job["project_id"],
            screenplay_revision_id=lineage["screenplay_revision_id"], target_type=selection_type,
            target_record_id=selection_target)
        if current and current["asset_id"] != job["output_asset_id"]:
            return {"alternate": True, "asset_id": job["output_asset_id"]}
        assign_media_role(root, job["project_id"], job["output_asset_id"], role)
        selections.select(project_id=job["project_id"],
            screenplay_revision_id=lineage["screenplay_revision_id"], target_type=selection_type,
            target_record_id=selection_target, asset_id=job["output_asset_id"],
            job_id=job["job_id"], authority="director",
            decision={"kind": "codex_visual_review", "review_job_id": job["job_id"]})
        if (role == "character_master" and character_voices is not None
                and setup.get("automate_steps", {}).get("character_voice") is True):
            # Voice matching is deterministic and reads saved voice metadata.
            # Run it from the durable image owner after a checked character
            # stage produces its first accepted master; page refresh is not a
            # required trigger. The matcher preserves existing bindings and
            # records ambiguous/unmatched characters for Director resolution.
            character_voices.run_automatic(job["project_id"], lineage["screenplay_revision_id"])
        if (role == "world_master" and image_jobs is not None
                and setup.get("automate_steps", {}).get("world_images") is True):
            _enqueue_selected_world_views(root=root, image_jobs=image_jobs,
                story=story, selections=selections, setup_service=setup_service, job=job,
                lineage=lineage, setup=setup)
    accept_candidate.validate = validate_candidate
    return accept_candidate


def _enqueue_selected_world_views(*, root: Path, image_jobs: ProductionImageJobStore, story: StoryAuthoring,
                                  selections: ProductionImageSelection,
                                  setup_service: ProductionSetup, job: dict,
                                  lineage: dict, setup: dict) -> None:
    """Continue an admitted world stage after its accepted master is saved."""
    workspace = job["project_id"]
    revision_id = lineage["screenplay_revision_id"]
    target_id = lineage["target_record_id"]
    selection = selections.get(project_id=workspace, screenplay_revision_id=revision_id,
        target_type="location", target_record_id=target_id)
    if not selection or selection.get("asset_id") != job.get("output_asset_id"):
        return
    assets, offset = [], 0
    while True:
        page = list_assets(root, workspace, kind="image", limit=100, offset=offset)
        assets.extend(page["assets"])
        offset += page["limit"]
        if offset >= page["total"] or not page["assets"]:
            break
    base_asset = next((item for item in assets if item.get("asset_id") == selection["asset_id"]), None)
    if not base_asset or "world_master" not in base_asset.get("roles", []):
        raise RuntimeError("The accepted world master is missing from the shared image library.")
    revision = story.get_screenplay_revision(workspace, revision_id)
    graph = story.get_story_graph(workspace_id=workspace, snapshot_id=revision["graph_snapshot_id"])
    target_record = next((item for item in graph.get("records", [])
        if item.get("record_id") == target_id), None)
    if not target_record:
        raise RuntimeError("The accepted world target is missing from its pinned graph.")
    views = setup.get("image_stage_settings", {}).get("world_images", {}).get("world_view_count", 4)
    directions = "north, east, south, and west" if views == 4 else "north, northeast, east, southeast, south, southwest, west, and northwest"
    prompt = (f"Create {views} consistent directional environment views of {target_record.get('name', 'this location')}. "
        f"Use the selected world master as the source of truth. Show {directions}. Keep the same architecture, "
        "terrain, materials, season, time of day, lighting, and fixed object placement in every direction. "
        "Do not add people, text, labels, borders, or a collage.")
    digest = hashlib.sha256(json.dumps(setup, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    style = lineage.get("style_selection")
    batch = build_world_view_image_batch(workspace_id=workspace, screenplay=revision,
        setup={"setup": setup}, target={**target_record, "kind": "entity"}, base_asset=base_asset,
        prompt=prompt, knowledge_ref={"source": "accepted_world_master", "setup_sha256": digest},
        run_id=job["run_id"], style_selection=style)
    image_jobs.enqueue_batches([batch])


def _image_worker(root: Path, db_path: Path, comfy_url: str) -> ProductionImageWorker:
    store = ProductionImageJobStore(db_path)
    ledger_path = Path(os.environ.get("VIBE_DIRECTOR_LEDGER_PATH",
        root / "services/production/ledger.sqlite3")).expanduser().resolve()
    try:
        ledger_path.relative_to(root)
    except ValueError as exc:
        raise RuntimeError("VIBE_DIRECTOR_LEDGER_PATH must remain under VIBE_DIRECTOR_DATA_DIR.") from exc
    ledger = ProductionLedger(ledger_path)
    story = StoryAuthoring(ledger, data_root=root)
    selections = ProductionImageSelection(db_path)

    setup_service = ProductionSetup(ledger, story)
    character_voices = CharacterVoiceBindings(ledger, root, story, setup_service)
    accept_candidate = _director_acceptor(root=root, story=story,
        selections=selections, setup_service=setup_service, image_jobs=store,
        character_voices=character_voices)
    worker = ProductionImageWorker(store, comfy_url=comfy_url, output_root=root / "projects",
        workspace_output=lambda workspace_id: generated_root(root, workspace_id),
        comfy_output_root=comfyui_root() / "output",
        register_output=lambda project_id, relative_path, role, metadata: _register_image_output(
            root, project_id, relative_path, metadata),
        resolve_candidate=lambda project_id, asset_id: asset_path(root, project_id, asset_id)[0],
        prepare_graph=lambda job: prepare_image_edit_graph(job=job, media_root=root,
            comfy_input_root=comfyui_root() / "input",
            owner_root=root / "runtime/image-reference-owners"),
        cleanup_staging=lambda owner_id: cleanup_image_reference_staging(owner_id=owner_id,
            comfy_input_root=comfyui_root() / "input",
            owner_root=root / "runtime/image-reference-owners"),
        review_candidate=_director_review,
        director_provider_preflight=_director_provider_preflight,
        accept_candidate=accept_candidate,
        validate_candidate=accept_candidate.validate)
    stage_retry_after = {}
    worker.advance_assisted_stages = lambda: _advance_checked_image_stage(
        root=root, ledger=ledger, story=story, selections=selections,
        image_jobs=store, retry_after=stage_retry_after)
    return worker


_ASSISTED_IMAGE_STAGES = ("character_images", "world_images", "frame_images")


def _unresolved_assisted_voice_ids(state: dict) -> list[str]:
    """Only opted-in speaking/unknown characters without a saved binding block video."""
    bound = {row.get("character_id") for row in state.get("bindings", [])
        if isinstance(row, dict) and isinstance(row.get("character_id"), str)}
    required = {row.get("character_id") for row in state.get("speech_statuses", [])
        if isinstance(row, dict) and row.get("status") in {"speaking", "narrator", "unknown"}
        and isinstance(row.get("character_id"), str)}
    return sorted(required - bound)


def _accepted_world_view_labels(*, workspace: str, target: str, base_asset_id: str,
                                base_asset_sha256: str, stage_rows: list,
                                assets_by_id: dict, jobs: ProductionImageJobStore) -> set[str]:
    accepted = set()
    for job_id, output_asset_id, candidate_index, role, settings, status in stage_rows:
        lineage = settings.get("lineage") or {}
        if role != "world_view" or status != "completed" or lineage.get("target_record_id") != target:
            continue
        refs = settings.get("image_references") or []
        referenced = lineage.get("base_asset_id") or (refs[0].get("asset_id") if refs and isinstance(refs[0], dict) else None)
        referenced_hash = lineage.get("base_asset_sha256") or (refs[0].get("sha256") if refs and isinstance(refs[0], dict) else None)
        if referenced != base_asset_id or referenced_hash != base_asset_sha256:
            continue
        asset = assets_by_id.get(output_asset_id)
        # Automated directions need an accepted Director review; manual
        # directions need an explicit world_view role selection in the library.
        if settings.get("director_review_required") is True:
            review = jobs.get_director_review(project_id=workspace, job_id=job_id)
            is_accepted = (review or {}).get("resolution_status") == "accepted"
        else:
            is_accepted = asset is not None and "world_view" in asset.get("roles", [])
        views = settings.get("world_views")
        view = (views[candidate_index - 1] if isinstance(views, list)
            and type(candidate_index) is int and 1 <= candidate_index <= len(views) else settings.get("world_view"))
        label = view.get("label") if isinstance(view, dict) else None
        if is_accepted and isinstance(label, str) and label.strip():
            accepted.add(label.strip().casefold())
    return accepted


def _image_stage_is_complete(*, workspace: str, revision_id: str, step: str, setup: dict,
                             story: StoryAuthoring, selections: ProductionImageSelection,
                             jobs: ProductionImageJobStore) -> bool:
    setup_store = ProductionSetup(story.ledger, story)
    if step in setup_store.list_assisted_stage_skips(workspace, revision_id)["skipped"]:
        return True
    revision = story.get_screenplay_revision(workspace, revision_id)
    graph = story.get_story_graph(workspace_id=workspace, snapshot_id=revision["graph_snapshot_id"])
    records = [row for row in graph.get("records", []) if isinstance(row, dict)
        and row.get("kind") == "entity" and isinstance(row.get("record_id"), str)]
    if step == "character_images":
        targets = [row["record_id"] for row in records if str(row.get("type", "")).casefold() == "character"]
        target_type = "character"
        roles = ("character_master",)
    elif step == "world_images":
        targets = [row["record_id"] for row in records if str(row.get("type", "")).casefold() == "location"]
        target_type = "location"
        roles = ("world_master",)
    else:
        skip_state = ProductionSetup(story.ledger, story).list_frame_preparation_skips(workspace, revision_id)
        skipped = {(row["scene_number"], row["shot_number"]) for row in skip_state["skipped"]}
        targets = []
        for scene in (revision.get("screenplay") or {}).get("scenes", []):
            if not isinstance(scene, dict) or type(scene.get("scene_number")) is not int:
                continue
            for shot in scene.get("shots", []):
                if (not isinstance(shot, dict) or type(shot.get("shot_number")) is not int
                        or (scene["scene_number"], shot["shot_number"]) in skipped):
                    continue
                targets.append(story_clip_id(workspace, revision_id,
                    scene["scene_number"], shot["shot_number"]))
        target_type = "clip"
        roles = ("first_frame", "last_frame")

    with jobs._connect() as db:
        rows = db.execute("SELECT job_id,output_asset_id,candidate_index,asset_role,settings_json,status FROM production_image_jobs WHERE project_id=?",
            (workspace,)).fetchall()
    stage_rows = []
    setup_hash = hashlib.sha256(json.dumps(setup, sort_keys=True,
        separators=(",", ":")).encode()).hexdigest()
    for row in rows:
        try:
            settings = json.loads(row["settings_json"])
        except (TypeError, json.JSONDecodeError):
            continue
        lineage = settings.get("lineage") or {}
        if settings.get("stage") == step and lineage.get("screenplay_revision_id") == revision_id:
            if settings.get("setup_sha256") != setup_hash:
                return False
            stage_rows.append((row["job_id"], row["output_asset_id"], row["candidate_index"],
                row["asset_role"], settings, row["status"]))
    # Do not start another stage while work from this stage is still active.
    if any(status in {"queued", "preparing", "submitting", "running"}
            for _job_id, _asset_id, _index, _role, _settings, status in stage_rows):
        return False
    for target in targets:
        for role in roles:
            if not selections.get(project_id=workspace, screenplay_revision_id=revision_id,
                    target_type=role if role != "character_master" and role != "world_master" else target_type,
                    target_record_id=target):
                return False
    if step == "world_images" and targets:
        count = setup.get("image_stage_settings", {}).get(step, {}).get("world_view_count", 4)
        assets = []
        offset = 0
        while True:
            page = list_assets(story.data_root, workspace, kind="image", limit=100, offset=offset)
            assets.extend(page["assets"])
            offset += len(page["assets"])
            if not page["assets"] or offset >= page["total"]:
                break
        assets_by_id = {asset["asset_id"]: asset for asset in assets}
        for target in targets:
            target_selection = selections.get(project_id=workspace, screenplay_revision_id=revision_id,
                target_type="location", target_record_id=target)
            base_asset = assets_by_id.get(target_selection.get("asset_id")) if target_selection else None
            if (not target_selection or not base_asset or "world_master" not in base_asset.get("roles", [])
                    or not isinstance(base_asset.get("sha256"), str)):
                return False
            selected_views = _accepted_world_view_labels(workspace=workspace, target=target,
                base_asset_id=target_selection["asset_id"], base_asset_sha256=base_asset["sha256"],
                stage_rows=stage_rows, assets_by_id=assets_by_id, jobs=jobs)
            if len(selected_views) < count:
                return False
    return True


def _advance_checked_image_stage(*, root: Path, ledger: ProductionLedger,
                                 story: StoryAuthoring, selections: ProductionImageSelection,
                                 image_jobs: ProductionImageJobStore,
                                 retry_after: dict | None = None) -> dict | None:
    """Advance one checked image stage from durable selections, without a mounted page."""
    with ledger._connect() as db:
        setups = db.execute("SELECT workspace_id,screenplay_revision_id,setup_json "
            "FROM story_production_setups ORDER BY updated_at DESC").fetchall()
        admissions = db.execute("SELECT project_id,config_json,created_at FROM production_runs").fetchall()
    with image_jobs._connect() as db:
        all_jobs = db.execute("SELECT project_id,settings_json,created_at FROM production_image_jobs").fetchall()
    latest = {}
    for row in admissions:
        try:
            config = json.loads(row["config_json"])
        except (TypeError, json.JSONDecodeError):
            continue
        if (config.get("entry") == "automated_image_stage"
                and config.get("step") in _ASSISTED_IMAGE_STAGES
                and config.get("screenplay_revision_id")):
            key = (row["project_id"], config["screenplay_revision_id"])
            current = latest.get(key)
            if current is None or row["created_at"] > current[0]:
                latest[key] = (row["created_at"], config["step"])
    for row in all_jobs:
        try:
            settings = json.loads(row["settings_json"])
        except (TypeError, json.JSONDecodeError):
            continue
        lineage = settings.get("lineage") or {}
        stage = settings.get("stage")
        if stage in _ASSISTED_IMAGE_STAGES and lineage.get("screenplay_revision_id"):
            key = (row["project_id"], lineage["screenplay_revision_id"])
            current = latest.get(key)
            if current is None or row["created_at"] > current[0]:
                latest[key] = (row["created_at"], stage)
    for row in setups:
        workspace, revision_id = row["workspace_id"], row["screenplay_revision_id"]
        retry_key = (workspace, revision_id)
        if retry_after and retry_after.get(retry_key, 0) > time.monotonic():
            continue
        last = latest.get((workspace, revision_id))
        if not last:
            continue  # An explicit first-stage admission is still required.
        try:
            setup = json.loads(row["setup_json"])
            revision = story.get_screenplay_revision(workspace, revision_id)
            if (not revision.get("accepted") or setup.get("mode") != "assisted_manual"):
                continue
            previous_index = _ASSISTED_IMAGE_STAGES.index(last[1])
            if not _image_stage_is_complete(workspace=workspace, revision_id=revision_id,
                    step=last[1], setup=setup, story=story, selections=selections,
                    jobs=image_jobs):
                continue
            if (setup.get("automate_steps", {}).get("character_voice") is True
                    and _image_stage_is_complete(workspace=workspace, revision_id=revision_id,
                        step="character_images", setup=setup, story=story,
                        selections=selections, jobs=image_jobs)):
                bindings = CharacterVoiceBindings(ledger, root, story, ProductionSetup(ledger, story))
                state = bindings.get(workspace, revision_id)
                if state.get("characters") and not state.get("automation_decisions"):
                    bindings.run_automatic(workspace, revision_id)
            port = int(os.environ.get("VIBE_DIRECTOR_PORT", "3020"))
            for step in _ASSISTED_IMAGE_STAGES[previous_index + 1:]:
                complete = _image_stage_is_complete(workspace=workspace, revision_id=revision_id,
                    step=step, setup=setup, story=story, selections=selections,
                    jobs=image_jobs)
                if setup.get("automate_steps", {}).get(step) is not True:
                    if not complete:
                        return {"workspace_id": workspace, "screenplay_revision_id": revision_id,
                            "step": step, "status": "waiting_for_manual",
                            "message": f"Complete or explicitly skip the optional {step.replace('_', ' ')} stage to continue."}
                    continue
                if complete:
                    continue
                result = _request_json(f"http://127.0.0.1:{port}/api/images/automated-stage",
                    method="POST", payload={"workspace_id": workspace,
                        "screenplay_revision_id": revision_id, "step": step}, timeout_seconds=30)
                if retry_after is not None:
                    retry_after.pop(retry_key, None)
                return {"workspace_id": workspace, "screenplay_revision_id": revision_id,
                    "step": step, "result": result}
            enabled_image_steps = [step for step in _ASSISTED_IMAGE_STAGES
                if setup.get("automate_steps", {}).get(step) is True]
            for step in _ASSISTED_IMAGE_STAGES:
                if setup.get("automate_steps", {}).get(step) is not True and not _image_stage_is_complete(
                        workspace=workspace, revision_id=revision_id, step=step,
                        setup=setup, story=story, selections=selections, jobs=image_jobs):
                    return {"workspace_id": workspace, "screenplay_revision_id": revision_id,
                        "step": step, "status": "waiting_for_manual",
                        "message": f"Complete or explicitly skip the optional {step.replace('_', ' ')} stage to continue."}
            if (setup.get("automate_steps", {}).get("video") is True
                    and all(_image_stage_is_complete(workspace=workspace, revision_id=revision_id,
                        step=step, setup=setup, story=story, selections=selections,
                        jobs=image_jobs) for step in enabled_image_steps)):
                if setup.get("automate_steps", {}).get("character_voice") is True:
                    bindings = CharacterVoiceBindings(ledger, root, story, ProductionSetup(ledger, story))
                    state = bindings.get(workspace, revision_id)
                    if state.get("characters") and not state.get("automation_decisions"):
                        state = bindings.run_automatic(workspace, revision_id)
                    unresolved = _unresolved_assisted_voice_ids(state)
                    if unresolved:
                        return {"workspace_id": workspace, "screenplay_revision_id": revision_id,
                            "step": "character_voice", "status": "waiting_for_voice_resolution",
                            "character_ids": unresolved,
                            "message": "Resolve the opted-in voice choices for speaking characters before automated video can continue."}
                base = f"http://127.0.0.1:{port}/api/story/workspaces/{quote(workspace, safe='')}/assisted-video-run"
                query = f"screenplay_revision_id={quote(revision_id, safe='')}"
                run = _request_json(f"{base}?{query}", timeout_seconds=15)
                if run.get("run_state") == "not_started":
                    result = _request_json(base, method="POST",
                        payload={"screenplay_revision_id": revision_id}, timeout_seconds=30)
                    if retry_after is not None:
                        retry_after.pop(retry_key, None)
                    return {"workspace_id": workspace, "screenplay_revision_id": revision_id,
                        "step": "video", "result": result}
        except Exception:
            # Recheck transient readiness/API failures without filling the worker log every idle pass.
            if retry_after is not None:
                retry_after[retry_key] = time.monotonic() + 15
            LOGGER.warning("Could not advance saved Assisted stages workspace=%s revision=%s; retry in 15s",
                workspace, revision_id, exc_info=True)
    return None


def _register_image_output(root: Path, project_id: str, relative_path: str, metadata: dict) -> dict:
    asset = register_generated_image(root, project_id, relative_path, metadata)
    job = metadata.get("production_image_job") if isinstance(metadata, dict) else None
    settings = job.get("settings") if isinstance(job, dict) else None
    if isinstance(settings, dict) and settings.get("automated_world_views") is True:
        asset = assign_media_role(root, project_id, asset["asset_id"], "world_view")
    if isinstance(settings, dict) and settings.get("output_destination"):
        from story_builder.services.media_library import relocate_output
        asset = relocate_output(root, project_id, asset["asset_id"], settings["output_destination"], job["job_id"])
    return asset


@contextmanager
def image_worker_lifetime_lock(db_path: Path):
    """Give one process exclusive ownership of a durable image-job database."""
    canonical_db = Path(db_path).expanduser().resolve()
    key = hashlib.sha256(str(canonical_db).encode("utf-8")).hexdigest()[:24]
    lock_path = canonical_db.parent / f".{canonical_db.name}.{key}.worker.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = lock_path.open("a+")
    try:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError(f"An image worker already owns this job database: {canonical_db}") from exc
        yield
    finally:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()


def _status_writer(path: Path, pid: int):
    lock = threading.Lock()

    def write(state: str, reason: str | None = None):
        with lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps({"enabled": True, "pid": pid, "state": state,
                "reason": reason, "updated_unix": time.time()}), encoding="utf-8")
            os.replace(tmp, path)

    def touch():
        with lock:
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                value = {"enabled": True, "pid": pid, "state": "starting"}
            value["updated_unix"] = time.time()
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(value), encoding="utf-8")
            os.replace(tmp, path)
    write.touch = touch
    return write


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--enable-worker", action="store_true")
    args = parser.parse_args()
    if not (args.enable_worker or os.environ.get("VIBE_DIRECTOR_ENABLE_IMAGE_WORKER") == "1"):
        raise SystemExit("Image worker is disabled. Pass --enable-worker or set VIBE_DIRECTOR_ENABLE_IMAGE_WORKER=1.")
    configured_root = os.environ.get("VIBE_DIRECTOR_DATA_DIR")
    if not configured_root:
        raise SystemExit("Set VIBE_DIRECTOR_DATA_DIR to a product-owned data directory.")
    root = Path(configured_root).expanduser().resolve()
    db_path = Path(os.environ.get("VIBE_DIRECTOR_IMAGE_JOBS_DB",
        root / "services/production/image-jobs.sqlite3")).expanduser().resolve()
    try:
        db_path.relative_to(root)
    except ValueError as exc:
        raise SystemExit("VIBE_DIRECTOR_IMAGE_JOBS_DB must remain under VIBE_DIRECTOR_DATA_DIR.") from exc
    comfy_url = os.environ.get("COMFYUI_URL", "http://127.0.0.1:3008").rstrip("/")
    try:
        with image_worker_lifetime_lock(db_path):
            _run_worker(root, db_path, comfy_url)
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc


def _run_worker(root: Path, db_path: Path, comfy_url: str) -> None:
    status_path = root / "runtime/isolated-image-worker-status.json"
    write_status = _status_writer(status_path, os.getpid())
    write_status("starting")
    worker = _image_worker(root, db_path, comfy_url)
    recovered = worker.store.reconcile_after_restart()
    supervisor = ProductionImageWorkerSupervisor(worker,
        advance_assisted_stages=getattr(worker, "advance_assisted_stages", None))
    stopped = False

    def stop(_signum, _frame):
        nonlocal stopped
        stopped = True
        write_status("stopping")
        supervisor.stop(timeout_seconds=10)

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    supervisor.start()
    write_status("running", f"Requeued {recovered['requeued_unsubmitted']} unsubmitted job(s); "
        f"held {recovered['held_for_reconciliation']} uncertain submission(s) for reconciliation.")
    print(f"Image candidate worker enabled; db={db_path}; ComfyUI={comfy_url}", flush=True)
    try:
        while not stopped:
            write_status.touch()
            time.sleep(2)
    finally:
        supervisor.stop(timeout_seconds=10)
        write_status("stopped")


if __name__ == "__main__":
    main()
