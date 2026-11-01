"""Story-free T2V job facade over the existing durable production ledger.

This module owns identity/snapshots only. It deliberately does not start a
worker, probe ComfyUI, submit a prompt, or delete media during construction.
"""
from __future__ import annotations
from story_builder.services.storage_paths import intermediate_root
from story_builder.services.storage_paths import generated_root

from story_builder.services.director_skills import bind_h3_reference_prompt

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Any, Callable, Mapping

from story_builder.services.isolated_video_contract import (
    IsolatedVideoContractError, EXPECTED_GRAPH_SHA256, WORKFLOW_VERSION as T2V_WORKFLOW_VERSION,
    T2V_WORKFLOW_ID, canonical_request_hash,
    compile_preview, normalize_request,
)
from story_builder.services.isolated_fl2va_contract import (
    FL2VAContractError, FL2VA_GRAPH_PATH, WORKFLOW_ID as FL2VA_WORKFLOW_ID,
    EXPECTED_GRAPH_SHA256 as FL2VA_EXPECTED_GRAPH_SHA256,
    WORKFLOW_VERSION as FL2VA_WORKFLOW_VERSION,
    compile_preview as compile_fl2va_preview, normalize_request as normalize_fl2va_request,
)
from story_builder.services.isolated_fl2va_assets import (
    cleanup_fl2va_staging_job, stage_fl2va_frames,
)
from story_builder.services.production_fl2va_capability import fl2va_capability
from story_builder.services.isolated_r2v_contract import (
    GRAPH_PATH as R2V_GRAPH_PATH, WORKFLOW_ID as R2V_WORKFLOW_ID,
    WORKFLOW_VERSION as R2V_WORKFLOW_VERSION, EXPECTED_GRAPH_SHA256 as R2V_GRAPH_SHA256,
    R2VContractError, compile_preview as compile_r2v_preview,
    normalize_request as normalize_r2v_request, plan_from_request,
)
from story_builder.services.isolated_r2v_assets import stage_r2v_references, cleanup_r2v_staging_job
from story_builder.services.minimax_h3_graph_compiler import compile_r2v_graph
from story_builder.services.production_r2v_capability import r2v_capability
from story_builder.services.minimax_h3_t2v import T2V_GRAPH_PATH
from story_builder.services.production_job_worker import PreparedTake, ProductionJobWorker
from story_builder.services.production_ledger import (
    LedgerConflict, LedgerNotFound, ProductionLedger, stable_hash,
)
from story_builder.services.video_continuity import last_frame, INTENT as CONTINUITY_INTENT
from story_builder.services.media_library import register_generated_video, set_asset_archived
from story_builder.services.media_library import list_assets as list_workspace_media_assets
from story_builder.services.fully_automated_clip_plan import generate_clip_plan, generate_scene_clip_plan, validate_clip_plan
from story_builder.services.fully_automated_clip_plan import ClipPlanError

_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$")
_WORKSPACE_NS = uuid.UUID("ec00c6b2-2bbb-4a36-9f50-755d47913f0e")
_SOURCE_LINEAGE_FIELDS = {"screenplay_revision_id", "setup_hash", "scene_number", "shot_number", "source_prompt_sha256"}
_OPTIONAL_SOURCE_LINEAGE_FIELDS = {"knowledge_ref", "style_ref", "planned_clip_id"}


class IsolatedJobConflict(ValueError):
    """HTTP adapter should map this and LedgerConflict to 409."""


class StoryHandoffRejected(IsolatedJobConflict):
    """A story handoff failed before any durable take was admitted."""


def _identifier(value: Any, name: str) -> str:
    if type(value) is not str or not _SAFE_ID.fullmatch(value):
        raise ValueError(f"{name} must be a safe 1–80 character identifier.")
    return value


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def story_clip_id(workspace_id: str, screenplay_revision_id: str,
                  scene_number: int, shot_number: int) -> str:
    identity = f"{workspace_id}\0{screenplay_revision_id}\0{scene_number}\0{shot_number}"
    return "story-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:40]


def _lineage_identity(value):
    if (not isinstance(value, Mapping) or not _SOURCE_LINEAGE_FIELDS <= set(value)
            or set(value) - _SOURCE_LINEAGE_FIELDS - _OPTIONAL_SOURCE_LINEAGE_FIELDS):
        raise ValueError("source_lineage must identify one saved screenplay shot and setup.")
    revision = _identifier(value["screenplay_revision_id"], "screenplay_revision_id")
    setup_hash = value["setup_hash"]
    scene, shot = value["scene_number"], value["shot_number"]
    if type(setup_hash) is not str or not re.fullmatch(r"[0-9a-f]{64}", setup_hash):
        raise ValueError("source_lineage.setup_hash must be a SHA-256 digest.")
    source_prompt_sha256 = value["source_prompt_sha256"]
    if type(source_prompt_sha256) is not str or not re.fullmatch(r"[0-9a-f]{64}", source_prompt_sha256):
        raise ValueError("source_lineage.source_prompt_sha256 must be a SHA-256 digest.")
    if type(scene) is not int or scene < 1 or type(shot) is not int or shot < 1:
        raise ValueError("source_lineage scene and shot numbers must be positive integers.")
    result = {"screenplay_revision_id": revision, "setup_hash": setup_hash,
            "source_prompt_sha256": source_prompt_sha256,
            "scene_number": scene, "shot_number": shot}
    if "planned_clip_id" in value:
        result["planned_clip_id"] = _identifier(value["planned_clip_id"], "planned_clip_id")
    if "knowledge_ref" in value:
        ref = value["knowledge_ref"]
        if (not isinstance(ref, Mapping) or set(ref) != {"knowledge_id", "guidance_version", "workflow_sha256"}
                or type(ref["knowledge_id"]) is not str or not ref["knowledge_id"]
                or type(ref["guidance_version"]) is not int or ref["guidance_version"] < 1
                or type(ref["workflow_sha256"]) is not str or not re.fullmatch(r"[a-f0-9]{64}", ref["workflow_sha256"])):
            raise ValueError("source_lineage.knowledge_ref is malformed.")
        result["knowledge_ref"] = dict(ref)
    if "style_ref" in value:
        ref = value["style_ref"]
        fields = {"snapshot_id", "style_version_id", "narrative_hash", "director_profile_hash", "directing_style_hash"}
        if (not isinstance(ref, Mapping) or set(ref) != fields
                or type(ref["snapshot_id"]) is not str or not ref["snapshot_id"]
                or type(ref["style_version_id"]) is not str or not ref["style_version_id"]
                or any(type(ref[name]) is not str or not re.fullmatch(r"[a-f0-9]{64}", ref[name])
                       for name in fields - {"snapshot_id", "style_version_id"})):
            raise ValueError("source_lineage.style_ref is malformed.")
        result["style_ref"] = dict(ref)
    return result


def _draft_knowledge_lineage(draft):
    ref = draft.get("knowledge_ref") if isinstance(draft, Mapping) else None
    result = {"knowledge_ref": dict(ref)} if isinstance(ref, Mapping) else {}
    style_ref = draft.get("style_ref") if isinstance(draft, Mapping) else None
    if isinstance(style_ref, Mapping):
        result["style_ref"] = dict(style_ref)
    return result


def _validate_story_source_lineage(db, story, workspace, clip, request, supplied, media_root=None):
    identity = _lineage_identity(supplied)
    if story is None:
        raise StoryHandoffRejected("Story-linked video handoff is not configured on this server.")
    revision = db.execute("SELECT * FROM story_screenplay_revisions WHERE workspace_id=? AND screenplay_revision_id=?",
        (workspace, identity["screenplay_revision_id"])).fetchone()
    if revision is None or not story._screenplay_is_currently_accepted(db, revision):
        raise StoryHandoffRejected("Story-linked video requires the current accepted screenplay revision.")
    setup_row = db.execute("SELECT setup_json FROM story_production_setups WHERE workspace_id=? AND screenplay_revision_id=?",
        (workspace, identity["screenplay_revision_id"])).fetchone()
    if setup_row is None:
        raise StoryHandoffRejected("Story-linked video requires the saved Automation & Parameters setup.")
    setup = json.loads(setup_row["setup_json"])
    if (setup.get("mode") == "fully_automated"
            or setup.get("mode") == "assisted_manual"
            and setup.get("automate_steps", {}).get("video") is True):
        raise StoryHandoffRejected(
            "This run automates video generation; per-shot manual Video submissions are disabled.")
    setup_hash = hashlib.sha256(json.dumps(setup, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    if setup_hash != identity["setup_hash"]:
        raise StoryHandoffRejected("Production setup changed after this prompt was saved. Reload Prompt Preparation.")
    draft_row = db.execute("SELECT setup_hash,drafts_json FROM story_prompt_drafts WHERE workspace_id=? AND screenplay_revision_id=?",
        (workspace, identity["screenplay_revision_id"])).fetchone()
    if draft_row is None or draft_row["setup_hash"] != setup_hash:
        raise StoryHandoffRejected("Saved prompt drafts no longer match the current production setup.")
    shot_key = f"{identity['scene_number']}.{identity['shot_number']}"
    draft = json.loads(draft_row["drafts_json"]).get(shot_key)
    if not draft:
        raise StoryHandoffRejected("Saved shot prompt or workflow no longer matches this Video request.")
    if draft.get("knowledge_ref") != identity.get("knowledge_ref"):
        raise StoryHandoffRejected("Saved prompt guidance provenance changed. Return to Prompt Preparation and reopen the shot.")
    if draft.get("style_ref") != identity.get("style_ref"):
        raise StoryHandoffRejected("Saved prompt creative style provenance changed. Return to Prompt Preparation and reopen the shot.")
    if hashlib.sha256(draft["prompt"].encode("utf-8")).hexdigest() != identity["source_prompt_sha256"]:
        raise StoryHandoffRejected("Saved shot prompt changed after opening it in Video. Return to Prompt Preparation and reopen the shot.")
    expected_clip = story_clip_id(workspace, identity["screenplay_revision_id"],
        identity["scene_number"], identity["shot_number"])
    if identity.get("planned_clip_id"):
        row = db.execute("SELECT plan_json,input_hash FROM assisted_video_clip_plans WHERE workspace_id=? AND screenplay_revision_id=?",
            (workspace, identity["screenplay_revision_id"])).fetchone()
        plans = json.loads(row["plan_json"]) if row else []
        expected_hash = hashlib.sha256(json.dumps({"screenplay": json.loads(revision["screenplay_json"]),
            "setup": setup, "drafts": json.loads(draft_row["drafts_json"])}, sort_keys=True,
            ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
        if not row or row["input_hash"] != expected_hash:
            raise StoryHandoffRejected("Clip plan is stale. Prepare screenplay clips again.")
        index = next((i for i, item in enumerate(plans) if item["clip_id"] == clip), -1)
        if (index < 0 or identity["planned_clip_id"] != clip
                or plans[index]["scene_number"] != identity["scene_number"]
                or plans[index]["shot_number"] != identity["shot_number"]
                or plans[index]["duration_seconds"] != request["duration_seconds"]):
            raise StoryHandoffRejected("Video request does not match the selected planned clip and duration.")
        predecessor = None
        for prior in plans[:index]:
            accepted = db.execute("SELECT t.output_hashes_json FROM production_takes t JOIN isolated_video_jobs m USING(job_id) LEFT JOIN isolated_video_retake_decisions d ON d.source_job_id=m.job_id WHERE m.workspace_id=? AND m.clip_id=? AND t.status='accepted' AND COALESCE(d.disposition,'')!='discard_requested' ORDER BY t.created_at DESC,t.take_id DESC LIMIT 1",
                (workspace, prior["clip_id"])).fetchone()
            if not accepted:
                raise StoryHandoffRejected("Accept the preceding video before advancing to this clip.")
            predecessor = accepted

    elif clip != expected_clip:
        raise StoryHandoffRejected("Story-linked clip identity does not match the selected screenplay shot.")
    return {**identity, "workflow_id": request["workflow_id"]}


class IsolatedVideoJobs:
    """Create/read jobs in the normal durable ledger with isolated aliases.

    `workspace_id` aliases the ledger's project_id; `clip_id` aliases shot_id.
    No screenplay, scene, or project-canon record is created.
    """

    def __init__(self, ledger: ProductionLedger, *, graph_path: Path | None = None,
                 fl2va_graph_path: Path | None = None, fl2va_capability_provider=None,
                 r2v_graph_path: Path | None = None, r2v_capability_provider=None,
                 full_clip_plan_provider=None,
                 story=None, media_root: Path | None = None):
        self.ledger = ledger
        self.story = story
        self.media_root = Path(media_root).resolve() if media_root is not None else None
        self.graph_path = Path(graph_path).resolve() if graph_path is not None else T2V_GRAPH_PATH
        self.fl2va_graph_path = Path(fl2va_graph_path).resolve() if fl2va_graph_path is not None else FL2VA_GRAPH_PATH
        self.fl2va_capability_provider = fl2va_capability_provider or fl2va_capability
        self.r2v_graph_path = Path(r2v_graph_path).resolve() if r2v_graph_path is not None else R2V_GRAPH_PATH
        self.r2v_capability_provider = r2v_capability_provider or r2v_capability
        self.full_clip_plan_provider = full_clip_plan_provider
        self.prompt_drafts = None
        with ledger._connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS isolated_video_jobs (
                    job_id TEXT PRIMARY KEY REFERENCES production_takes(job_id) ON DELETE CASCADE,
                    workspace_id TEXT NOT NULL,
                    clip_id TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    request_hash TEXT NOT NULL,
                    request_json TEXT NOT NULL,
                    retake_of_job_id TEXT,
                    attempt INTEGER NOT NULL,
                    keep_original INTEGER,
                    source_lineage_json TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(workspace_id, idempotency_key)
                );
                CREATE INDEX IF NOT EXISTS isolated_video_jobs_clip_idx
                    ON isolated_video_jobs(workspace_id, clip_id, created_at);
                CREATE TABLE IF NOT EXISTS isolated_video_assets (
                    asset_id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL REFERENCES isolated_video_jobs(job_id) ON DELETE CASCADE,
                    workspace_id TEXT NOT NULL,
                    sha256 TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    retention_state TEXT NOT NULL DEFAULT 'active',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS isolated_video_asset_refs (
                    asset_id TEXT NOT NULL REFERENCES isolated_video_assets(asset_id) ON DELETE CASCADE,
                    job_id TEXT NOT NULL REFERENCES isolated_video_jobs(job_id) ON DELETE CASCADE,
                    PRIMARY KEY(asset_id, job_id)
                );
                CREATE TABLE IF NOT EXISTS isolated_video_retake_decisions (
                    source_job_id TEXT PRIMARY KEY REFERENCES isolated_video_jobs(job_id) ON DELETE CASCADE,
                    workspace_id TEXT NOT NULL,
                    disposition TEXT NOT NULL CHECK(disposition IN ('keep', 'discard_requested')),
                    actor TEXT NOT NULL DEFAULT 'user',
                    chosen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS fully_automated_first_clip_bindings (
                    workspace_id TEXT NOT NULL,
                    screenplay_revision_id TEXT NOT NULL,
                    job_id TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY(workspace_id, screenplay_revision_id)
                );
                CREATE TABLE IF NOT EXISTS fully_automated_runs (
                    workspace_id TEXT NOT NULL, screenplay_revision_id TEXT NOT NULL,
                    manifest_json TEXT NOT NULL, run_state TEXT NOT NULL DEFAULT 'running',
                    error_message TEXT, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY(workspace_id, screenplay_revision_id)
                );
                CREATE TABLE IF NOT EXISTS fully_automated_run_clips (
                    workspace_id TEXT NOT NULL, screenplay_revision_id TEXT NOT NULL,
                    scene_number INTEGER NOT NULL, shot_number INTEGER NOT NULL,
                    clip_number INTEGER NOT NULL DEFAULT 1,
                    job_id TEXT NOT NULL UNIQUE, predecessor_job_id TEXT,
                    clip_state TEXT NOT NULL DEFAULT 'queued', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY(workspace_id, screenplay_revision_id, scene_number, shot_number, clip_number)
                );
                CREATE TABLE IF NOT EXISTS fully_automated_run_attempts (
                    job_id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL, screenplay_revision_id TEXT NOT NULL,
                    scene_number INTEGER NOT NULL, shot_number INTEGER NOT NULL,
                    clip_number INTEGER NOT NULL DEFAULT 1, attempt_number INTEGER NOT NULL,
                    predecessor_job_id TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(workspace_id, screenplay_revision_id, scene_number, shot_number, clip_number, attempt_number)
                );
                CREATE TABLE IF NOT EXISTS assisted_video_reference_maps (
                    workspace_id TEXT NOT NULL,
                    screenplay_revision_id TEXT NOT NULL,
                    scene_number INTEGER NOT NULL,
                    shot_number INTEGER NOT NULL,
                    references_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY(workspace_id, screenplay_revision_id, scene_number, shot_number)
                );
                CREATE TABLE IF NOT EXISTS assisted_video_clip_plans (
                    workspace_id TEXT NOT NULL, screenplay_revision_id TEXT NOT NULL,
                    input_hash TEXT NOT NULL, plan_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY(workspace_id, screenplay_revision_id)
                );
                CREATE TABLE IF NOT EXISTS assisted_video_clip_references (
                    workspace_id TEXT NOT NULL, screenplay_revision_id TEXT NOT NULL,
                    clip_id TEXT NOT NULL, references_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY(workspace_id, screenplay_revision_id, clip_id)
                );
                CREATE TABLE IF NOT EXISTS assisted_video_runs (
                    workspace_id TEXT NOT NULL, screenplay_revision_id TEXT NOT NULL,
                    manifest_json TEXT NOT NULL, run_state TEXT NOT NULL DEFAULT 'running',
                    error_message TEXT, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY(workspace_id, screenplay_revision_id)
                );
                CREATE TABLE IF NOT EXISTS assisted_video_run_clips (
                    workspace_id TEXT NOT NULL, screenplay_revision_id TEXT NOT NULL,
                    clip_id TEXT NOT NULL, job_id TEXT NOT NULL UNIQUE,
                    predecessor_job_id TEXT, clip_state TEXT NOT NULL DEFAULT 'queued',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY(workspace_id, screenplay_revision_id, clip_id)
                );
            """)
            self._migrate_full_run_clip_numbers(db)
            columns = {row["name"] for row in db.execute("PRAGMA table_info(isolated_video_jobs)")}
            if "source_lineage_json" not in columns:
                db.execute("ALTER TABLE isolated_video_jobs ADD COLUMN source_lineage_json TEXT")

    def _prepare_full_scene_drafts(self, workspace, revision_id, setup,
                                   scene, saved_drafts, *, persist=True,
                                   scene_start_identity_refs=False):
        """Prepare missing prompts for one scene immediately before planning it."""
        drafts = dict(saved_drafts) if isinstance(saved_drafts, dict) else {}
        has_style_video = False
        for shot_index, shot in enumerate(scene.get("shots", [])):
            key = f"{scene['scene_number']}.{shot['shot_number']}"
            workflow_id = T2V_WORKFLOW_ID
            current = drafts.get(key)
            if isinstance(current, dict):
                if current.get("workflow_id") != workflow_id:
                    if self.prompt_drafts is None:
                        raise StoryHandoffRejected("The scene's T2V route needs a matching workflow-aware prompt, but the prompt preparer is unavailable.")
                    prepared = self.prompt_drafts.prepare(workspace, revision_id, key, workflow_id,
                        **({"setup_snapshot": setup} if not persist else {}),
                        prior_prompt_context=current.get("prompt"))
                    draft = {name: prepared[name] for name in ("workflow_id", "prompt", "knowledge_ref", "style_ref")
                        if name in prepared}
                    if persist:
                        self.prompt_drafts.save_shot(workspace, revision_id, setup, key, draft)
                    drafts[key] = draft
                    continue
                if (not isinstance(current.get("prompt"), str)
                        or not current["prompt"].strip() or len(current["prompt"]) >= 7000):
                    raise ValueError(f"Prompt draft {key} must be non-empty and below the 7,000-character limit.")
                continue
            if self.prompt_drafts is None:
                raise StoryHandoffRejected("Full mode needs the connected prompt preparer to draft each scene as it is reached.")
            prepared = self.prompt_drafts.prepare(workspace, revision_id, key, workflow_id,
                **({"setup_snapshot": setup} if not persist else {}))
            draft = {name: prepared[name] for name in ("workflow_id", "prompt", "knowledge_ref", "style_ref")
                if name in prepared}
            if persist:
                self.prompt_drafts.save_shot(workspace, revision_id, setup, key, draft)
            drafts[key] = draft
        return drafts

    @staticmethod
    def _migrate_full_run_clip_numbers(db):
        """Add clip identity without changing existing Full-run rows or job IDs."""
        schemas = {
            "fully_automated_run_clips": """CREATE TABLE {table} (
                workspace_id TEXT NOT NULL, screenplay_revision_id TEXT NOT NULL,
                scene_number INTEGER NOT NULL, shot_number INTEGER NOT NULL,
                clip_number INTEGER NOT NULL DEFAULT 1,
                job_id TEXT NOT NULL UNIQUE, predecessor_job_id TEXT,
                clip_state TEXT NOT NULL DEFAULT 'queued', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(workspace_id, screenplay_revision_id, scene_number, shot_number, clip_number)
            )""",
            "fully_automated_run_attempts": """CREATE TABLE {table} (
                job_id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL, screenplay_revision_id TEXT NOT NULL,
                scene_number INTEGER NOT NULL, shot_number INTEGER NOT NULL,
                clip_number INTEGER NOT NULL DEFAULT 1, attempt_number INTEGER NOT NULL,
                predecessor_job_id TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(workspace_id, screenplay_revision_id, scene_number, shot_number, clip_number, attempt_number)
            )""",
        }
        legacy_tables = []
        for table in schemas:
            columns = {row["name"] for row in db.execute(f"PRAGMA table_info({table})")}
            if "clip_number" not in columns:
                legacy_tables.append(table)
        if not legacy_tables:
            return

        db.execute("BEGIN IMMEDIATE")
        try:
            for table in legacy_tables:
                # Another process may have completed this migration while we
                # were waiting for the write lock. Recheck under the lock so
                # we never rebuild a new table and collapse clip IDs to 1.
                columns = {row["name"] for row in db.execute(f"PRAGMA table_info({table})")}
                if "clip_number" in columns:
                    continue
                legacy = f"{table}_legacy_clip_number"
                replacement = f"{table}_clip_number_v2"
                if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name IN (?,?)", (legacy, replacement)).fetchone():
                    raise RuntimeError(f"Incomplete prior Full-run schema migration detected for {table}.")
                db.execute(f"ALTER TABLE {table} RENAME TO {legacy}")
                db.execute(schemas[table].format(table=replacement))
                if table == "fully_automated_run_clips":
                    db.execute(f"""INSERT INTO {replacement}
                        (workspace_id,screenplay_revision_id,scene_number,shot_number,clip_number,
                         job_id,predecessor_job_id,clip_state,created_at)
                        SELECT workspace_id,screenplay_revision_id,scene_number,shot_number,1,
                               job_id,predecessor_job_id,clip_state,created_at FROM {legacy}""")
                else:
                    db.execute(f"""INSERT INTO {replacement}
                        (job_id,workspace_id,screenplay_revision_id,scene_number,shot_number,
                         clip_number,attempt_number,predecessor_job_id,created_at)
                        SELECT job_id,workspace_id,screenplay_revision_id,scene_number,shot_number,
                               1,attempt_number,predecessor_job_id,created_at FROM {legacy}""")
                db.execute(f"DROP TABLE {legacy}")
                db.execute(f"ALTER TABLE {replacement} RENAME TO {table}")
            db.commit()
        except Exception:
            db.rollback()
            raise

    def validate(self, request: Mapping[str, Any]) -> dict[str, Any]:
        if isinstance(request, Mapping) and request.get("workflow_id") in {FL2VA_WORKFLOW_ID, R2V_WORKFLOW_ID} and request.get("workflow_version") != 2:
            raise IsolatedVideoContractError("workflow_version_retired", "New guided jobs require Turbo + LTX. Reload the draft; existing job recovery remains available.")
        normalized = _normalize_workflow_request(request, self.graph_path, self.fl2va_graph_path, self.r2v_graph_path)
        preview = _compile_workflow_preview(normalized, self.graph_path, self.fl2va_graph_path, self.r2v_graph_path)
        return {"valid": True, "request_hash": _canonical_workflow_hash(normalized),
                "normalized_request": normalized, "compiled_preview": preview}

    @staticmethod
    def _full_style_videos(setup):
        # Style analysis informs prompts; video bytes require an explicit per-clip mapping.
        return []

    @classmethod
    def _full_r2v_request(cls, *, setup, prompt, duration_seconds=None, continuity=None,
                          identity_images=(), include_style=True):
        videos = cls._full_style_videos(setup) if include_style else []
        images = [dict(row) for row in identity_images]
        instructions = [f"<Video {index}> Use this selected style video as directed: {row['intent']}"
            for index, row in enumerate(videos, 1)]
        instructions.extend(f"<Picture {index}> Preserve the appearance of this screenplay character: {row['intent']}"
            for index, row in enumerate(images, 1))
        if continuity is not None:
            if len(images) >= 9:
                raise StoryHandoffRejected("Leave one of the nine image slots for the last-frame continuity reference.")
            images.append({"asset_id": continuity["asset_id"], "sha256": continuity["sha256"],
                "role": "continuity", "intent": CONTINUITY_INTENT})
            instructions.append(f"<Picture {len(images)}> {CONTINUITY_INTENT}")
        compiled_prompt = bind_h3_reference_prompt(prompt, instructions)
        if len(compiled_prompt) >= 7000:
            raise StoryHandoffRejected("The complete R2V prompt exceeds MiniMax's 6,999-character limit after reference instructions.")
        duration = duration_seconds
        if duration is None:
            duration = setup.get("duration_policy", {}).get("seconds")
        if type(duration) is not int or not 5 <= duration <= 15:
            raise StoryHandoffRejected("A reference-guided clip needs a confirmed duration from 5–15 seconds.")
        return {"workflow_id": R2V_WORKFLOW_ID, "workflow_version": R2V_WORKFLOW_VERSION,
            "workflow_sha256": R2V_GRAPH_SHA256,
            "prompt": compiled_prompt,
            "duration_seconds": duration, "aspect_ratio": manifest["setup"].get("aspect_ratio", "16:9"),
            "resolution_preset": cls._quality_preset(setup["video_quality"]), "steps": 4, "seed": 1,
            "ref_image_size": "match", "images": images, "audios": [], "videos": videos}

    def _full_identity_images(self, db, workspace, revision_id, plan, before_index, clip):
        """Resolve earlier identity crops for characters targeted by this clip."""
        cited = set(clip.get("target_character_ids", []))
        if not cited or self.media_root is None or before_index <= 0:
            return []
        if not self._table_exists(db, "fully_automated_identity_reviews"):
            return []
        earlier = [(row["scene_number"], row["shot_number"], row["clip_number"])
            for row in plan[:before_index]]
        bound = {}
        for order, (scene, shot, number) in enumerate(earlier):
            row = db.execute("SELECT job_id FROM fully_automated_run_clips WHERE workspace_id=? AND screenplay_revision_id=? AND scene_number=? AND shot_number=? AND clip_number=?",
                (workspace, revision_id, scene, shot, number)).fetchone()
            if row:
                bound[row["job_id"]] = order
        if not bound:
            return []
        # Avoid a dynamically sized SQL IN clause: long screenplays can exceed
        # SQLite's bind-variable limit. Keep only reviews bound to earlier clips.
        rows = db.execute("SELECT source_job_id,input_json,result_json FROM fully_automated_identity_reviews WHERE workspace_id=? AND screenplay_revision_id=? AND state='complete'",
            (workspace, revision_id)).fetchall()
        from story_builder.services.media_library import asset_path
        latest = {}
        for row in sorted((row for row in rows if row["source_job_id"] in bound),
                          key=lambda row: bound[row["source_job_id"]], reverse=True):
            try:
                inputs, result = json.loads(row["input_json"]), json.loads(row["result_json"])
                names = {item["character_id"]: item["name"] for item in inputs["characters"]}
                for ref in result.get("derived_references", []):
                    character_id, asset_id, digest = ref["character_id"], ref["asset_id"], ref["sha256"]
                    if ref.get("frame_kind") != "last" or character_id not in cited or character_id in latest:
                        continue
                    path, media_type, _name = asset_path(self.media_root, workspace, asset_id)
                    if (media_type not in {"image/jpeg", "image/png", "image/webp"}
                            or not re.fullmatch(r"[a-f0-9]{64}", str(digest))
                            or _file_sha256(Path(path)) != digest):
                        continue
                    latest[character_id] = {"asset_id": asset_id, "sha256": digest,
                        "role": "character_identity", "intent": f"Character {names.get(character_id, character_id)}; preserve the visible identity and appearance shown in this crop."}
            except (OSError, TypeError, ValueError, KeyError, json.JSONDecodeError):
                continue
        # Stable character-target order; source-evidence IDs describe story
        # support and must never be used as cast identity keys.
        return [latest[key] for key in clip.get("target_character_ids", [])
            if key in latest][:9]

    def _validate_v2_full_request(self, db, manifest, clip, normalized, run_identity, predecessor_id):
        plan = manifest.get("clip_plan", {}).get("clips", [])
        identity = (clip["scene_number"], clip["shot_number"], clip["clip_number"])
        plan_identities = [(row["scene_number"], row["shot_number"], row["clip_number"]) for row in plan]
        if identity not in plan_identities:
            raise StoryHandoffRejected("Automated request is not present in the frozen Full clip plan.")
        index = plan_identities.index(identity)
        is_scene_start = index == 0 or plan[index - 1]["scene_number"] != clip["scene_number"]
        if index == 0:
            expected_predecessor = None
        else:
            prior = plan[index - 1]
            bound = db.execute("SELECT job_id FROM fully_automated_run_clips WHERE workspace_id=? AND screenplay_revision_id=? AND scene_number=? AND shot_number=? AND clip_number=?",
                (*run_identity, prior["scene_number"], prior["shot_number"], prior["clip_number"])).fetchone()
            expected_predecessor = bound["job_id"] if bound else None
        if predecessor_id != expected_predecessor:
            raise StoryHandoffRejected("Automated clip predecessor does not match frozen screenplay order.")
        if clip["workflow_id"] == T2V_WORKFLOW_ID:
            expected = {"workflow_id": T2V_WORKFLOW_ID, "workflow_version": T2V_WORKFLOW_VERSION,
                "workflow_sha256": EXPECTED_GRAPH_SHA256, "prompt": clip["prompt"],
                "duration_seconds": clip["duration_seconds"], "aspect_ratio": manifest["setup"].get("aspect_ratio", "16:9"),
                "resolution_preset": self._quality_preset(manifest["setup"]["video_quality"]),
                "steps": 4, "seed": 1, "references": []}
        else:
            continuity = None
            if not is_scene_start:
                if not predecessor_id:
                    raise StoryHandoffRejected("A same-scene R2V continuation needs its previous clip.")
                previous = db.execute("SELECT t.status,t.output_hashes_json FROM production_takes t WHERE t.job_id=?",
                    (predecessor_id,)).fetchone()
                if previous is None or previous["status"] not in {"needs_review", "accepted"}:
                    raise StoryHandoffRejected("A same-scene R2V continuation needs a successful previous clip.")
                output = next((asset for asset in json.loads(previous["output_hashes_json"] or "[]")
                    if asset.get("shared_asset_id") and asset.get("kind") == "video" and asset.get("has_video")), None)
                if not output:
                    raise StoryHandoffRejected("The previous clip has no reusable shared video asset.")
                continuity = last_frame(self.media_root, run_identity[0], output, create=False)
            identity_images = self._full_identity_images(db, run_identity[0], run_identity[1], plan, index, clip)
            if clip.get("character_refs_required") and not identity_images:
                raise StoryHandoffRejected("The scene-start character references frozen for this Full clip are no longer available.")
            expected = self._full_r2v_request(setup=manifest["setup"], prompt=clip["prompt"],
                duration_seconds=clip["duration_seconds"], continuity=continuity,
                identity_images=identity_images, include_style=True)
        expected = _normalize_workflow_request(expected, self.graph_path,
            self.fl2va_graph_path, self.r2v_graph_path)
        if dict(normalized) != dict(expected):
            raise StoryHandoffRejected("Automated request differs from the frozen clip plan or its approved references.")

    def _fully_automated_first_clip_input(self, workspace_id: str, screenplay_revision_id: str):
        """Plan and freeze the first clip from current durable Full-mode inputs."""
        from story_builder.services.production_setup import ProductionSetup, QUALITY

        workspace = _identifier(workspace_id, "workspace_id")
        revision_id = _identifier(screenplay_revision_id, "screenplay_revision_id")
        if self.story is None:
            raise StoryHandoffRejected("Automated story video is not configured on this server.")
        with self.ledger._connect() as db:
            revision = db.execute("SELECT * FROM story_screenplay_revisions WHERE workspace_id=? AND screenplay_revision_id=?",
                (workspace, revision_id)).fetchone()
            if revision is None or not self.story._screenplay_is_currently_accepted(db, revision):
                raise StoryHandoffRejected("Fully automated video requires the current accepted screenplay.")
            setup_row = db.execute("SELECT setup_json FROM story_production_setups WHERE workspace_id=? AND screenplay_revision_id=?",
                (workspace, revision_id)).fetchone()
            if setup_row is None:
                raise StoryHandoffRejected("Save Automation & Parameters before starting the first clip.")
            setup = ProductionSetup.validate(json.loads(setup_row["setup_json"]))
            if setup["mode"] != "fully_automated":
                raise StoryHandoffRejected("The first-clip runner is available only for Fully automated mode.")
            screenplay = json.loads(revision["screenplay_json"])
            scenes = screenplay.get("scenes") if isinstance(screenplay, dict) else None
            if not isinstance(scenes, list) or not scenes:
                raise StoryHandoffRejected("The accepted screenplay has no scenes to generate.")
            setup_hash = hashlib.sha256(json.dumps(setup, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
            draft_row = db.execute("SELECT setup_hash,drafts_json FROM story_prompt_drafts WHERE workspace_id=? AND screenplay_revision_id=?",
                (workspace, revision_id)).fetchone()
            drafts = (json.loads(draft_row["drafts_json"])
                if draft_row is not None and draft_row["setup_hash"] == setup_hash else {})
            if not isinstance(drafts, dict):
                raise StoryHandoffRejected("Saved prompt drafts are malformed.")
            policy = setup["duration_policy"]
            minimum, maximum = ((policy["seconds"], policy["seconds"]) if policy["kind"] == "fixed"
                else (policy["min_seconds"], policy["max_seconds"]))
            input_hash = hashlib.sha256(json.dumps({"screenplay": screenplay, "setup": setup,
                "drafts": drafts}, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
            saved_plan = db.execute("SELECT input_hash,plan_json FROM assisted_video_clip_plans WHERE workspace_id=? AND screenplay_revision_id=?",
                (workspace, revision_id)).fetchone()
            if saved_plan is None or saved_plan["input_hash"] != input_hash:
                raise StoryHandoffRejected("Prepare and save the current clip prompts on Prompt Preparation before starting.")
            planned = json.loads(saved_plan["plan_json"])
            proposed = {"clips": [{**{key: clip[key] for key in
                ("scene_number", "shot_number", "duration_seconds", "duration_reason", "prompt")},
                "source_spans": [{key: span[key] for key in ("field", "start", "end")}
                    for span in clip["source_spans"]]} for clip in planned]}
            try:
                clip_plan = validate_clip_plan(workspace_id=workspace,
                    screenplay_revision_id=revision_id, screenplay=screenplay, proposed=proposed,
                    min_seconds=minimum, max_seconds=maximum, fixed_workflow_id=T2V_WORKFLOW_ID)
            except ClipPlanError as exc:
                raise StoryHandoffRejected(str(exc)) from exc
            # Validation is read-only: preserve the exact reviewed prompts and clip identities.
            clip_plan = {"clips": planned}
            if any(clip["workflow_id"] != T2V_WORKFLOW_ID for clip in planned):
                raise StoryHandoffRejected("Fully automated clips must use T2V without media references.")
            planned = clip_plan["clips"]
            for index, clip in enumerate(planned):
                previous = planned[index - 1] if index else None
                same_scene_continuation = previous is not None and previous["scene_number"] == clip["scene_number"]
                if clip["workflow_id"] == T2V_WORKFLOW_ID:
                    route_request = {"workflow_id": T2V_WORKFLOW_ID,
                        "workflow_version": T2V_WORKFLOW_VERSION,
                        "workflow_sha256": EXPECTED_GRAPH_SHA256, "prompt": clip["prompt"],
                        "duration_seconds": clip["duration_seconds"], "aspect_ratio": setup.get("aspect_ratio", "16:9"),
                        "resolution_preset": QUALITY[setup["video_quality"]],
                        "steps": 4, "seed": 1, "references": []}
                else:
                    route_request = self._full_r2v_request(setup=setup, prompt=clip["prompt"],
                        duration_seconds=clip["duration_seconds"],
                        continuity=({"asset_id": "fullrun-preflight-video", "sha256": "0" * 64}
                            if same_scene_continuation else None),
                        include_style=True)
                route_normalized = _normalize_workflow_request(route_request, self.graph_path,
                    self.fl2va_graph_path, self.r2v_graph_path)
                _compile_workflow_preview(route_normalized, self.graph_path,
                    self.fl2va_graph_path, self.r2v_graph_path)
            first = planned[0]
            scene_number, shot_number = first["scene_number"], first["shot_number"]
            source_draft = drafts[f"{scene_number}.{shot_number}"]
            prompt_hash = hashlib.sha256(source_draft["prompt"].encode("utf-8")).hexdigest()
            with self.ledger._connect() as prompt_db:
                saved = prompt_db.execute("SELECT setup_hash,drafts_json FROM story_prompt_drafts WHERE workspace_id=? AND screenplay_revision_id=?",
                    (workspace, revision_id)).fetchone()
            if saved is None or saved["setup_hash"] != setup_hash:
                raise StoryHandoffRejected("Scene prompts were not durably saved with the current setup.")
            drafts = json.loads(saved["drafts_json"])
            manifest = {"screenplay": screenplay, "setup": setup,
                "setup_hash": setup_hash, "drafts": drafts,
                "manifest_version": 2, "reviewed_input_hash": input_hash,
                "clip_plan": clip_plan,
                "clip_plan_sha256": hashlib.sha256(json.dumps(clip_plan, sort_keys=True,
                    ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest(),
                "screenplay_sha256": hashlib.sha256(json.dumps(screenplay, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest(),
                "drafts_sha256": hashlib.sha256(json.dumps(drafts, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()}

        if first["workflow_id"] == T2V_WORKFLOW_ID:
            request = {"workflow_id": T2V_WORKFLOW_ID, "workflow_version": T2V_WORKFLOW_VERSION,
                "workflow_sha256": EXPECTED_GRAPH_SHA256, "prompt": first["prompt"],
                "duration_seconds": first["duration_seconds"], "aspect_ratio": setup.get("aspect_ratio", "16:9"),
                "resolution_preset": QUALITY[setup["video_quality"]], "steps": 4, "seed": 1,
                "references": []}
        else:
            request = self._full_r2v_request(setup=setup, prompt=first["prompt"],
                duration_seconds=first["duration_seconds"])
        if isinstance(request, Mapping) and request.get("workflow_id") in {FL2VA_WORKFLOW_ID, R2V_WORKFLOW_ID} and request.get("workflow_version") != 2:
            raise IsolatedVideoContractError("workflow_version_retired", "New guided jobs require Turbo + LTX. Reload the draft; existing job recovery remains available.")
        normalized = _normalize_workflow_request(request, self.graph_path, self.fl2va_graph_path, self.r2v_graph_path)
        _compile_workflow_preview(normalized, self.graph_path, self.fl2va_graph_path, self.r2v_graph_path)
        lineage = {"screenplay_revision_id": revision_id, "setup_hash": setup_hash,
            "scene_number": scene_number, "shot_number": shot_number,
            "source_prompt_sha256": prompt_hash, **_draft_knowledge_lineage(source_draft)}
        # One Full first-clip attempt is bound to a screenplay revision. If its
        # mutable setup or prompt later changes, recovery returns the frozen job;
        # a new accepted screenplay revision creates a new identity.
        identity = hashlib.sha256((workspace + "\0" + revision_id).encode()).hexdigest()
        return {"workspace_id": workspace, "screenplay_revision_id": revision_id,
            "setup_hash": setup_hash, "prompt_sha256": prompt_hash,
            "scene_number": scene_number, "shot_number": shot_number,
            "clip_number": first["clip_number"], "planned_clip": first,
            "clip_id": first["clip_id"],
            "idempotency_key": "fullfirst-" + identity, "request": normalized, "source_lineage": lineage,
            "run_manifest": manifest}

    def start_fully_automated_first_clip(self, workspace_id: str, screenplay_revision_id: str):
        """Queue/recover exactly the first accepted Full-mode T2V shot."""
        workspace = _identifier(workspace_id, "workspace_id")
        revision_id = _identifier(screenplay_revision_id, "screenplay_revision_id")
        recovered = self.recover_fully_automated_first_clip(workspace, revision_id)
        if recovered is not None:
            return recovered
        snapshot = self._fully_automated_first_clip_input(workspace_id, screenplay_revision_id)
        job = self.create_job(workspace_id=snapshot["workspace_id"], clip_id=snapshot["clip_id"],
            idempotency_key=snapshot["idempotency_key"], request=snapshot["request"],
            source_lineage=snapshot["source_lineage"],
            _full_run_binding=(workspace, revision_id),
            _full_run_manifest=snapshot["run_manifest"],
            _full_run_clip=(workspace, revision_id, snapshot["scene_number"], snapshot["shot_number"],
                snapshot["clip_number"], None))
        return self._fully_automated_run_result(workspace, revision_id, job)

    def recover_fully_automated_first_clip(self, workspace_id: str, screenplay_revision_id: str):
        """Return an existing frozen first-clip job without checking admission readiness."""
        workspace = _identifier(workspace_id, "workspace_id")
        revision_id = _identifier(screenplay_revision_id, "screenplay_revision_id")
        frozen = self._get_bound_first_clip(workspace, revision_id)
        return self._fully_automated_run_result(workspace, revision_id, frozen) if frozen is not None else None

    def get_fully_automated_first_clip(self, workspace_id: str, screenplay_revision_id: str):
        workspace = _identifier(workspace_id, "workspace_id")
        revision_id = _identifier(screenplay_revision_id, "screenplay_revision_id")
        frozen = self._get_bound_first_clip(workspace, revision_id)
        if frozen is not None:
            return self._fully_automated_run_result(workspace, revision_id, frozen)
        # Reading status must never spend a model call or make an ephemeral plan.
        # Planning is explicit on Prompt Preparation, never on a status read.
        plan = self.get_assisted_video_clip_plan(workspace, revision_id)
        return {"run_state": "not_started", "workspace_id": workspace,
            "screenplay_revision_id": revision_id, "job": None, "clips": [],
            "completed_count": 0, "planned_count": len(plan["clips"]) or None,
            "prompt_plan_ready": bool(plan["clips"] and plan["setup_matches_current"])}

    def get_assisted_video_reference_maps(self, workspace_id: str, screenplay_revision_id: str):
        """Return the Director-authored per-shot R2V maps for this screenplay."""
        workspace = _identifier(workspace_id, "workspace_id")
        revision = _identifier(screenplay_revision_id, "screenplay_revision_id")
        with self.ledger._connect() as db:
            rows = db.execute("SELECT scene_number,shot_number,references_json,updated_at FROM assisted_video_reference_maps WHERE workspace_id=? AND screenplay_revision_id=? ORDER BY scene_number,shot_number",
                (workspace, revision)).fetchall()
        return {"workspace_id": workspace, "screenplay_revision_id": revision,
            "clips": [{"scene_number": row["scene_number"], "shot_number": row["shot_number"],
                "references": json.loads(row["references_json"]), "updated_at": row["updated_at"]}
                for row in rows]}

    def prepare_assisted_video_clip_plan(self, workspace_id: str, screenplay_revision_id: str, *, discard_references=False):
        """Plan and persist Assisted clips only after an explicit user action."""
        from story_builder.services.production_setup import ProductionSetup
        workspace = _identifier(workspace_id, "workspace_id")
        revision_id = _identifier(screenplay_revision_id, "screenplay_revision_id")
        with self.ledger._connect() as db:
            revision = db.execute("SELECT * FROM story_screenplay_revisions WHERE workspace_id=? AND screenplay_revision_id=?",
                (workspace, revision_id)).fetchone()
            if revision is None or self.story is None or not self.story._screenplay_is_currently_accepted(db, revision):
                raise StoryHandoffRejected("Clip planning requires the current accepted screenplay.")
            setup_row = db.execute("SELECT setup_json FROM story_production_setups WHERE workspace_id=? AND screenplay_revision_id=?",
                (workspace, revision_id)).fetchone()
            if setup_row is None:
                raise StoryHandoffRejected("Save Automation & Parameters before planning clips.")
            setup = ProductionSetup.validate(json.loads(setup_row["setup_json"]))
            workflow = (setup.get("video_workflow_id", T2V_WORKFLOW_ID)
                if setup["mode"] == "assisted_manual" and setup["automate_steps"]["video"] else T2V_WORKFLOW_ID)
            if workflow not in {T2V_WORKFLOW_ID, FL2VA_WORKFLOW_ID, R2V_WORKFLOW_ID}:
                raise StoryHandoffRejected("Choose T2V, FFLF or R2V before planning Assisted video clips.")
            screenplay = json.loads(revision["screenplay_json"])
            setup_hash = hashlib.sha256(json.dumps(setup, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            draft_row = db.execute("SELECT setup_hash,drafts_json FROM story_prompt_drafts WHERE workspace_id=? AND screenplay_revision_id=?",
                (workspace, revision_id)).fetchone()
            if draft_row is None or draft_row["setup_hash"] != setup_hash:
                raise StoryHandoffRejected("Save current prompt drafts before planning clips.")
            drafts = json.loads(draft_row["drafts_json"])
            policy = setup["duration_policy"]
            minimum, maximum = ((policy["seconds"], policy["seconds"]) if policy["kind"] == "fixed"
                else (policy["min_seconds"], policy["max_seconds"]))
            input_hash = hashlib.sha256(json.dumps({"screenplay": screenplay, "setup": setup,
                "drafts": drafts}, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
            existing = db.execute("SELECT input_hash,plan_json FROM assisted_video_clip_plans WHERE workspace_id=? AND screenplay_revision_id=?",
                (workspace, revision_id)).fetchone()
            if existing and existing["input_hash"] == input_hash:
                return self.get_assisted_video_clip_plan(workspace, revision_id)
            if (db.execute("SELECT 1 FROM assisted_video_runs WHERE workspace_id=? AND screenplay_revision_id=?",
                    (workspace, revision_id)).fetchone() or db.execute(
                    "SELECT 1 FROM fully_automated_runs WHERE workspace_id=? AND screenplay_revision_id=?",
                    (workspace, revision_id)).fetchone()):
                raise IsolatedJobConflict("The Assisted run has started; its clip plan is frozen.")
            if existing:
                for planned in json.loads(existing["plan_json"]):
                    if db.execute("SELECT 1 FROM isolated_video_jobs WHERE workspace_id=? AND clip_id=? LIMIT 1",
                            (workspace, planned["clip_id"])).fetchone():
                        raise IsolatedJobConflict("Video generation has started; preserve this clip plan and use Retake to revise a clip.")
            mapped = db.execute("SELECT 1 FROM assisted_video_clip_references WHERE workspace_id=? AND screenplay_revision_id=? LIMIT 1",
                (workspace, revision_id)).fetchone()
            if mapped:
                if discard_references is not True:
                    raise IsolatedJobConflict("Confirm discarding the current clip references before replanning.")
        try:
            plan = generate_clip_plan(workspace_id=workspace, screenplay_revision_id=revision_id,
                screenplay=screenplay, drafts=drafts, min_seconds=minimum, max_seconds=maximum,
                fixed_workflow_id=workflow, generate_json=self.full_clip_plan_provider)
        except ClipPlanError as exc:
            raise StoryHandoffRejected(str(exc)) from exc
        with self.ledger._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            current_revision = db.execute("SELECT * FROM story_screenplay_revisions WHERE workspace_id=? AND screenplay_revision_id=?", (workspace, revision_id)).fetchone()
            current_setup = db.execute("SELECT setup_json FROM story_production_setups WHERE workspace_id=? AND screenplay_revision_id=?", (workspace, revision_id)).fetchone()
            current_drafts = db.execute("SELECT drafts_json FROM story_prompt_drafts WHERE workspace_id=? AND screenplay_revision_id=?", (workspace, revision_id)).fetchone()
            if (current_revision is None or not self.story._screenplay_is_currently_accepted(db, current_revision)
                    or current_setup is None or current_drafts is None):
                raise IsolatedJobConflict("Story inputs changed during planning. Reload Prompt Preparation.")
            current_hash = hashlib.sha256(json.dumps({"screenplay": json.loads(current_revision["screenplay_json"]),
                "setup": json.loads(current_setup["setup_json"]), "drafts": json.loads(current_drafts["drafts_json"])},
                sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
            current_plan = db.execute("SELECT input_hash,plan_json FROM assisted_video_clip_plans WHERE workspace_id=? AND screenplay_revision_id=?", (workspace, revision_id)).fetchone()
            if current_hash != input_hash or (tuple(current_plan) if current_plan else None) != (tuple(existing) if existing else None):
                raise IsolatedJobConflict("Inputs or clip prompts changed during planning. Reload before retrying.")
            for table in ("assisted_video_runs", "fully_automated_runs"):
                if db.execute(f"SELECT 1 FROM {table} WHERE workspace_id=? AND screenplay_revision_id=?", (workspace, revision_id)).fetchone():
                    raise IsolatedJobConflict("The run started during planning; its prompts are frozen.")
            if existing:
                for planned in json.loads(existing["plan_json"]):
                    if db.execute("SELECT 1 FROM isolated_video_jobs WHERE workspace_id=? AND clip_id=? LIMIT 1", (workspace, planned["clip_id"])).fetchone():
                        raise IsolatedJobConflict("Generation started during planning; preserve the saved plan.")
            if discard_references:
                db.execute("DELETE FROM assisted_video_clip_references WHERE workspace_id=? AND screenplay_revision_id=?", (workspace, revision_id))
            db.execute("INSERT INTO assisted_video_clip_plans(workspace_id,screenplay_revision_id,input_hash,plan_json) VALUES(?,?,?,?) ON CONFLICT(workspace_id,screenplay_revision_id) DO UPDATE SET input_hash=excluded.input_hash,plan_json=excluded.plan_json,updated_at=CURRENT_TIMESTAMP",
                (workspace, revision_id, input_hash, json.dumps(plan["clips"], ensure_ascii=False, sort_keys=True, separators=(",", ":"))))
        return self.get_assisted_video_clip_plan(workspace, revision_id)

    def get_assisted_video_clip_plan(self, workspace_id: str, screenplay_revision_id: str):
        workspace = _identifier(workspace_id, "workspace_id")
        revision = _identifier(screenplay_revision_id, "screenplay_revision_id")
        with self.ledger._connect() as db:
            row = db.execute("SELECT input_hash,plan_json,updated_at FROM assisted_video_clip_plans WHERE workspace_id=? AND screenplay_revision_id=?",
                (workspace, revision)).fetchone()
            refs = db.execute("SELECT clip_id,references_json FROM assisted_video_clip_references WHERE workspace_id=? AND screenplay_revision_id=?",
                (workspace, revision)).fetchall()
            revision_row = db.execute("SELECT * FROM story_screenplay_revisions WHERE workspace_id=? AND screenplay_revision_id=?", (workspace, revision)).fetchone()
            setup_row = db.execute("SELECT setup_json FROM story_production_setups WHERE workspace_id=? AND screenplay_revision_id=?", (workspace, revision)).fetchone()
            draft_row = db.execute("SELECT drafts_json FROM story_prompt_drafts WHERE workspace_id=? AND screenplay_revision_id=?", (workspace, revision)).fetchone()
            current_hash = None
            if revision_row and setup_row and draft_row and self.story and self.story._screenplay_is_currently_accepted(db, revision_row):
                current_hash = hashlib.sha256(json.dumps({"screenplay": json.loads(revision_row["screenplay_json"]),
                    "setup": json.loads(setup_row["setup_json"]), "drafts": json.loads(draft_row["drafts_json"])},
                    sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
        clips = json.loads(row["plan_json"]) if row else []
        return {"workspace_id": workspace, "screenplay_revision_id": revision,
            "input_hash": row["input_hash"] if row else None,
            "clips": clips, "setup_matches_current": bool(row and current_hash == row["input_hash"]),
            "references": {item["clip_id"]: json.loads(item["references_json"]) for item in refs},
            "updated_at": row["updated_at"] if row else None}

    def save_assisted_video_clip_prompt(self, workspace_id: str, screenplay_revision_id: str,
                                       clip_id: str, *, expected_prompt: str, prompt: str):
        """Save one Director-edited prompt without changing its source shot draft."""
        workspace = _identifier(workspace_id, "workspace_id")
        revision_id = _identifier(screenplay_revision_id, "screenplay_revision_id")
        clip_id = _identifier(clip_id, "clip_id")
        if type(expected_prompt) is not str or type(prompt) is not str or not prompt.strip() or len(prompt) >= 7000:
            raise ValueError("Clip prompt must contain 1–6,999 characters.")
        with self.ledger._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT input_hash,plan_json FROM assisted_video_clip_plans WHERE workspace_id=? AND screenplay_revision_id=?",
                (workspace, revision_id)).fetchone()
            if row is None:
                raise StoryHandoffRejected("Plan clips before editing a clip prompt.")
            if (db.execute("SELECT 1 FROM assisted_video_runs WHERE workspace_id=? AND screenplay_revision_id=?",
                    (workspace, revision_id)).fetchone() or db.execute(
                    "SELECT 1 FROM fully_automated_runs WHERE workspace_id=? AND screenplay_revision_id=?",
                    (workspace, revision_id)).fetchone()):
                raise IsolatedJobConflict("Clip prompts are frozen after the run starts.")
            revision = db.execute("SELECT * FROM story_screenplay_revisions WHERE workspace_id=? AND screenplay_revision_id=?",
                (workspace, revision_id)).fetchone()
            setup_row = db.execute("SELECT setup_json FROM story_production_setups WHERE workspace_id=? AND screenplay_revision_id=?",
                (workspace, revision_id)).fetchone()
            draft_row = db.execute("SELECT drafts_json FROM story_prompt_drafts WHERE workspace_id=? AND screenplay_revision_id=?",
                (workspace, revision_id)).fetchone()
            if (revision is None or self.story is None or not self.story._screenplay_is_currently_accepted(db, revision)
                    or setup_row is None or draft_row is None):
                raise StoryHandoffRejected("Clip prompt edits require the current accepted screenplay, setup and prompts.")
            source_hash = hashlib.sha256(json.dumps({"screenplay": json.loads(revision["screenplay_json"]),
                "setup": json.loads(setup_row["setup_json"]), "drafts": json.loads(draft_row["drafts_json"])},
                sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
            if source_hash != row["input_hash"]:
                raise StoryHandoffRejected("Screenplay, setup or prompts changed after planning. Replan before editing clips.")
            clips = json.loads(row["plan_json"])
            clip = next((item for item in clips if item.get("clip_id") == clip_id), None)
            if clip is None:
                raise StoryHandoffRejected("This clip is no longer in the saved plan. Replan before editing.")
            if clip.get("prompt") != expected_prompt:
                raise IsolatedJobConflict("This clip prompt changed elsewhere. Reload the plan before saving.")
            if db.execute("SELECT 1 FROM isolated_video_jobs WHERE workspace_id=? AND clip_id=? LIMIT 1",
                    (workspace, clip_id)).fetchone():
                raise IsolatedJobConflict("Generation has started for this clip. Use Retake to revise its prompt.")
            clip["prompt"] = prompt
            db.execute("UPDATE assisted_video_clip_plans SET plan_json=?,updated_at=CURRENT_TIMESTAMP WHERE workspace_id=? AND screenplay_revision_id=?",
                (json.dumps(clips, sort_keys=True, ensure_ascii=False, separators=(",", ":")), workspace, revision_id))
            db.commit()
        return self.get_assisted_video_clip_plan(workspace, revision_id)

    def save_assisted_video_clip_references(self, workspace_id: str, screenplay_revision_id: str, references: Any):
        """Save references against the exact frozen plan clip IDs."""
        workspace = _identifier(workspace_id, "workspace_id")
        revision_id = _identifier(screenplay_revision_id, "screenplay_revision_id")
        state = self.get_assisted_video_clip_plan(workspace, revision_id)
        clips = state["clips"]
        if not clips:
            raise StoryHandoffRejected("Plan clips before mapping references.")
        with self.ledger._connect() as db:
            revision_row = db.execute("SELECT * FROM story_screenplay_revisions WHERE workspace_id=? AND screenplay_revision_id=?",
                (workspace, revision_id)).fetchone()
            setup_row = db.execute("SELECT setup_json FROM story_production_setups WHERE workspace_id=? AND screenplay_revision_id=?",
                (workspace, revision_id)).fetchone()
            draft_row = db.execute("SELECT drafts_json FROM story_prompt_drafts WHERE workspace_id=? AND screenplay_revision_id=?",
                (workspace, revision_id)).fetchone()
            if (revision_row is None or self.story is None or not self.story._screenplay_is_currently_accepted(db, revision_row)
                    or setup_row is None or draft_row is None):
                raise StoryHandoffRejected("Clip references require the current accepted screenplay, setup and prompts.")
            current_hash = hashlib.sha256(json.dumps({"screenplay": json.loads(revision_row["screenplay_json"]),
                "setup": json.loads(setup_row["setup_json"]), "drafts": json.loads(draft_row["drafts_json"])},
                sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
        if current_hash != state["input_hash"]:
            raise StoryHandoffRejected("Screenplay, setup or prompts changed after planning. Replan before mapping references.")
        if type(references) is not list or any(not isinstance(row, Mapping)
                or set(row) - {"clip_id", "references", "continue_previous_clip"}
                or not {"clip_id", "references"} <= set(row)
                or type(row["clip_id"]) is not str or type(row["references"]) is not list
                or type(row.get("continue_previous_clip", False)) is not bool for row in references):
            raise ValueError("Supply clip_id, references, and an optional boolean continue_previous_clip.")
        expected = {clip["clip_id"] for clip in clips}
        if len(references) != len(expected) or {row["clip_id"] for row in references} != expected:
            raise ValueError("Map every planned clip exactly once; no shot-level maps are accepted.")
        planned_workflow = clips[0]["workflow_id"]
        if any(clip["workflow_id"] != planned_workflow for clip in clips):
            raise StoryHandoffRejected("Assisted plans must keep one video workflow for every clip.")
        workspace_state = self.story.get_workspace(workspace, include_source=False)
        style_selection = workspace_state.get("style_selection")
        with self.ledger._connect() as db:
            setup_row = db.execute("SELECT setup_json FROM story_production_setups WHERE workspace_id=? AND screenplay_revision_id=?",
                (workspace, revision_id)).fetchone()
        setup = json.loads(setup_row["setup_json"]) if setup_row else {}
        inherited_style_videos = []
        inherited_ids = {ref["asset_id"] for ref in inherited_style_videos}
        saved = []
        continuity = {}
        clip_by_id = {clip["clip_id"]: clip for clip in clips}
        for row in references:
            refs = row["references"]
            continue_previous = row.get("continue_previous_clip", False)
            clip = clip_by_id[row["clip_id"]]
            index = clips.index(clip)
            previous = clips[index - 1] if index else None
            if continue_previous and (planned_workflow != R2V_WORKFLOW_ID or previous is None
                    or previous["scene_number"] != clip["scene_number"]):
                raise ValueError("Previous-clip continuity is available only for R2V clips after the first clip in a scene.")
            continuity[row["clip_id"]] = continue_previous
            counts = {"image": 0, "video": 0, "audio": 0}
            seen = set()
            for ref in refs:
                if not isinstance(ref, Mapping) or ref.get("kind") not in counts:
                    raise ValueError("Each clip reference needs a supported media kind.")
                kind = ref["kind"]
                required = {"image": {"kind","asset_id","sha256","role","intent"},
                    "video": {"kind","asset_id","sha256","role","intent","start_sec","end_sec","include_paired_soundtrack","audio_intent"},
                    "audio": {"kind","asset_id","sha256","role","intent","speaker_id"}}[kind]
                shared_audio = kind == "audio" and set(ref) == {"kind","asset_id","sha256","role","intent","speaker_ids"}
                if (set(ref) != required and not shared_audio) or not all(type(ref[key]) is str and ref[key].strip() for key in ("role", "intent")):
                    raise ValueError("Each reference must include supported fields, a role, and its intended use.")
                if shared_audio and (type(ref["speaker_ids"]) is not list or len(ref["speaker_ids"]) > 12
                        or any(type(value) is not str or not value.strip() or len(value) > 80 for value in ref["speaker_ids"])
                        or len(set(ref["speaker_ids"])) != len(ref["speaker_ids"])):
                    raise ValueError("Shared voice mappings must use up to 12 unique character IDs.")
                if ref["asset_id"] in seen:
                    raise ValueError("A media asset can be mapped only once per clip.")
                if kind == "video" and ref["asset_id"] in inherited_ids:
                    raise ValueError("This video is already included as a run-level style reference. Choose a different per-clip video.")
                seen.add(ref["asset_id"])
                found = None
                offset = 0
                while True:
                    page = list_workspace_media_assets(self.media_root, workspace, kind=kind, limit=100,
                        offset=offset, style_selection=style_selection)
                    found = next((asset for asset in page["assets"] if asset["asset_id"] == ref["asset_id"]), found)
                    offset += len(page["assets"])
                    if found or offset >= page["total"] or not page["assets"]: break
                if not found or found.get("sha256") != ref["sha256"]:
                    raise StoryHandoffRejected("A selected clip reference is missing, changed, or outside this workspace.")
                counts[kind] += 1
                if planned_workflow == FL2VA_WORKFLOW_ID and (kind != "image" or ref["role"] not in {"first_frame", "last_frame"}):
                    raise ValueError("FFLF clip mappings must use first_frame and last_frame image references.")
            if planned_workflow == T2V_WORKFLOW_ID and (refs or continue_previous):
                raise ValueError("T2V clips cannot have media references or continuity frames.")
            if planned_workflow == R2V_WORKFLOW_ID and not refs and not continue_previous:
                raise ValueError("Every R2V clip needs at least one user-selected reference.")
            if planned_workflow == FL2VA_WORKFLOW_ID and (counts["image"] != 2
                    or {ref["role"] for ref in refs} != {"first_frame", "last_frame"}):
                raise ValueError("Every FFLF clip needs exactly one first frame and one last frame image.")
            if counts["image"] + int(continue_previous) > 9 or counts["video"] + len(inherited_style_videos) > 3 or counts["audio"] > 3:
                raise ValueError("R2V allows up to 9 images, 3 videos, and 3 audio references per clip.")
            saved.append((workspace, revision_id, row["clip_id"], json.dumps(refs, sort_keys=True, separators=(",", ":"))))
        with self.ledger._connect() as db:
            if db.execute("SELECT 1 FROM assisted_video_runs WHERE workspace_id=? AND screenplay_revision_id=? LIMIT 1",
                    (workspace, revision_id)).fetchone() if self._table_exists(db, "assisted_video_runs") else False:
                raise IsolatedJobConflict("Clip references are frozen after the Assisted run starts.")
            db.execute("DELETE FROM assisted_video_clip_references WHERE workspace_id=? AND screenplay_revision_id=?", (workspace, revision_id))
            db.executemany("INSERT INTO assisted_video_clip_references(workspace_id,screenplay_revision_id,clip_id,references_json) VALUES(?,?,?,?)", saved)
            plan_row = db.execute("SELECT plan_json FROM assisted_video_clip_plans WHERE workspace_id=? AND screenplay_revision_id=?",
                (workspace, revision_id)).fetchone()
            if plan_row is None:
                raise StoryHandoffRejected("The saved clip plan disappeared while references were being saved.")
            saved_clips = json.loads(plan_row["plan_json"])
            for clip in saved_clips:
                clip["continue_previous_clip"] = continuity.get(clip["clip_id"], False)
            db.execute("UPDATE assisted_video_clip_plans SET plan_json=?,updated_at=CURRENT_TIMESTAMP WHERE workspace_id=? AND screenplay_revision_id=?",
                (json.dumps(saved_clips, sort_keys=True, ensure_ascii=False, separators=(",", ":")), workspace, revision_id))
        return self.get_assisted_video_clip_plan(workspace, revision_id)

    def _assisted_video_result(self, workspace, revision_id):
        with self.ledger._connect() as db:
            run = db.execute("SELECT manifest_json,run_state,error_message,updated_at FROM assisted_video_runs WHERE workspace_id=? AND screenplay_revision_id=?",
                (workspace, revision_id)).fetchone()
            rows = db.execute("SELECT clip_id,job_id,predecessor_job_id,clip_state FROM assisted_video_run_clips WHERE workspace_id=? AND screenplay_revision_id=?",
                (workspace, revision_id)).fetchall()
        manifest = json.loads(run["manifest_json"]) if run else None
        by_id = {row["clip_id"]: row for row in rows}
        clips = []
        for planned in (manifest or {}).get("clips", []):
            row = by_id.get(planned["clip_id"])
            if row:
                job = self.get_job(row["job_id"])
                clips.append({"clip_id": planned["clip_id"], "scene_number": planned["scene_number"],
                    "shot_number": planned["shot_number"], "clip_number": planned["clip_number"],
                    "predecessor_job_id": row["predecessor_job_id"], "state": job["status"], "job": job})
        return {"workspace_id": workspace, "screenplay_revision_id": revision_id,
            "run_state": run["run_state"] if run else "not_started",
            "error": run["error_message"] if run else None,
            "updated_at": run["updated_at"] if run else None,
            "planned_count": len((manifest or {}).get("clips", [])),
            "completed_count": sum(item["state"] in {"needs_review", "accepted"} for item in clips),
            "clips": clips}

    def get_assisted_video_run(self, workspace_id: str, screenplay_revision_id: str):
        workspace = _identifier(workspace_id, "workspace_id")
        revision = _identifier(screenplay_revision_id, "screenplay_revision_id")
        return self._assisted_video_result(workspace, revision)

    def start_assisted_video_run(self, workspace_id: str, screenplay_revision_id: str,
                                 *, readiness: Mapping[str, Any] | None = None):
        """Freeze the saved Assisted plan and references, then queue through the shared worker."""
        workspace = _identifier(workspace_id, "workspace_id")
        revision_id = _identifier(screenplay_revision_id, "screenplay_revision_id")
        existing = self.get_assisted_video_run(workspace, revision_id)
        if existing["run_state"] != "not_started":
            return existing
        plan = self.get_assisted_video_clip_plan(workspace, revision_id)
        if not plan["clips"]:
            raise StoryHandoffRejected("Plan clips before starting the Assisted video run.")
        with self.ledger._connect() as db:
            revision = db.execute("SELECT * FROM story_screenplay_revisions WHERE workspace_id=? AND screenplay_revision_id=?",
                (workspace, revision_id)).fetchone()
            setup_row = db.execute("SELECT setup_json FROM story_production_setups WHERE workspace_id=? AND screenplay_revision_id=?",
                (workspace, revision_id)).fetchone()
            draft_row = db.execute("SELECT setup_hash,drafts_json FROM story_prompt_drafts WHERE workspace_id=? AND screenplay_revision_id=?",
                (workspace, revision_id)).fetchone()
            if (revision is None or self.story is None or not self.story._screenplay_is_currently_accepted(db, revision)
                    or setup_row is None or draft_row is None):
                raise StoryHandoffRejected("Starting video requires the current accepted screenplay, setup, and saved prompts.")
            from story_builder.services.production_setup import ProductionSetup
            setup = ProductionSetup.validate(json.loads(setup_row["setup_json"]))
            if setup["mode"] != "assisted_manual" or not setup["automate_steps"]["video"]:
                raise StoryHandoffRejected("Automatic video is not selected in Assisted manual setup.")
            setup_hash = hashlib.sha256(json.dumps(setup, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            if draft_row["setup_hash"] != setup_hash:
                raise StoryHandoffRejected("Save prompts against the current setup before starting video.")
            drafts = json.loads(draft_row["drafts_json"])
            input_hash = hashlib.sha256(json.dumps({"screenplay": json.loads(revision["screenplay_json"]),
                "setup": setup, "drafts": drafts},
                sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
            if plan["input_hash"] != input_hash:
                raise StoryHandoffRejected("The screenplay, setup, or prompts changed after clip planning. Replan first.")
        references = plan["references"]
        if any(clip["clip_id"] not in references for clip in plan["clips"]):
            raise StoryHandoffRejected("Save a reference map for every planned clip before starting video.")
        if readiness is None or not readiness.get("available"):
            raise IsolatedVideoContractError("workflow_not_ready", (readiness or {}).get("reason") or "The selected Assisted workflow is not ready.")
        frozen_clips = [{**clip, "references": references[clip["clip_id"]]}
            for clip in plan["clips"]]
        manifest = {"manifest_version": 1, "setup": setup, "setup_hash": setup_hash,
            "input_hash": input_hash, "drafts": drafts,
            "clip_plan_sha256": hashlib.sha256(json.dumps(frozen_clips, sort_keys=True,
                ensure_ascii=False, separators=(",", ":")).encode()).hexdigest(),
            "clips": frozen_clips}
        encoded = json.dumps(manifest, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        with self.ledger._connect() as db:
            # Serialize the final snapshot with prompt/reference edits. Without
            # this lock, an edit can land after the manifest is assembled but
            # before the run row freezes its inputs.
            db.execute("BEGIN IMMEDIATE")
            current_plan = db.execute("SELECT input_hash,plan_json FROM assisted_video_clip_plans WHERE workspace_id=? AND screenplay_revision_id=?",
                (workspace, revision_id)).fetchone()
            current_refs = db.execute("SELECT clip_id,references_json FROM assisted_video_clip_references WHERE workspace_id=? AND screenplay_revision_id=?",
                (workspace, revision_id)).fetchall()
            current_revision = db.execute("SELECT * FROM story_screenplay_revisions WHERE workspace_id=? AND screenplay_revision_id=?",
                (workspace, revision_id)).fetchone()
            current_setup = db.execute("SELECT setup_json FROM story_production_setups WHERE workspace_id=? AND screenplay_revision_id=?",
                (workspace, revision_id)).fetchone()
            current_drafts = db.execute("SELECT drafts_json,setup_hash FROM story_prompt_drafts WHERE workspace_id=? AND screenplay_revision_id=?",
                (workspace, revision_id)).fetchone()
            current_clip_rows = json.loads(current_plan["plan_json"]) if current_plan else []
            current_reference_map = {row["clip_id"]: json.loads(row["references_json"]) for row in current_refs}
            if (current_revision is None or self.story is None
                    or not self.story._screenplay_is_currently_accepted(db, current_revision)
                    or current_setup is None or current_drafts is None):
                raise StoryHandoffRejected("Starting video requires the current accepted screenplay, setup, and saved prompts.")
            latest_setup = ProductionSetup.validate(json.loads(current_setup["setup_json"]))
            latest_setup_hash = hashlib.sha256(json.dumps(latest_setup, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            latest_input_hash = hashlib.sha256(json.dumps({"screenplay": json.loads(current_revision["screenplay_json"]),
                "setup": latest_setup, "drafts": json.loads(current_drafts["drafts_json"])},
                sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
            if (latest_setup_hash != setup_hash or current_drafts["setup_hash"] != setup_hash
                    or latest_input_hash != input_hash
                    or current_plan is None or current_plan["input_hash"] != plan["input_hash"]
                    or current_clip_rows != plan["clips"] or current_reference_map != references):
                raise IsolatedJobConflict("The screenplay, setup, prompts, Assisted plan or references changed while the run was starting. Reload and retry.")
            db.execute("INSERT OR IGNORE INTO assisted_video_runs(workspace_id,screenplay_revision_id,manifest_json,run_state) VALUES(?,?,?,'running')",
                (workspace, revision_id, encoded))
            db.commit()
        return self.advance_assisted_video_run(workspace, revision_id, readiness=readiness)

    def _assisted_request(self, manifest, clip, predecessor_job=None, identity_images=()):
        from story_builder.services.production_setup import QUALITY
        workflow = clip["workflow_id"]
        refs = clip["references"]
        style_refs = []  # Video references must be mapped explicitly for a copying/edit task.
        duration = clip["duration_seconds"]
        prompt = clip["prompt"]
        if workflow == T2V_WORKFLOW_ID:
            if refs or clip.get("continue_previous_clip"):
                raise StoryHandoffRejected("T2V cannot use media references or continuity frames.")
            return {"workflow_id": T2V_WORKFLOW_ID, "workflow_version": T2V_WORKFLOW_VERSION,
                "workflow_sha256": EXPECTED_GRAPH_SHA256, "prompt": prompt,
                "duration_seconds": duration, "aspect_ratio": manifest["setup"].get("aspect_ratio", "16:9"),
                "resolution_preset": QUALITY[manifest["setup"]["video_quality"]],
                "steps": 4, "seed": 1, "references": []}
        if workflow == FL2VA_WORKFLOW_ID:
            if style_refs:
                raise StoryHandoffRejected("Selected style videos require R2V; this Assisted clip is configured for FFLF.")
            first = next((ref for ref in refs if ref["role"] == "first_frame"), None)
            last = next((ref for ref in refs if ref["role"] == "last_frame"), None)
            if not first or not last:
                raise StoryHandoffRejected("FFLF needs its mapped first and last frame for every clip.")
            request = {"workflow_id": FL2VA_WORKFLOW_ID, "workflow_version": FL2VA_WORKFLOW_VERSION,
                "workflow_sha256": FL2VA_EXPECTED_GRAPH_SHA256, "prompt": prompt,
                "duration_seconds": duration, "aspect_ratio": manifest["setup"].get("aspect_ratio", "16:9"),
                "resolution_preset": QUALITY[manifest["setup"]["video_quality"]],
                "first_frame": {"asset_id": first["asset_id"], "sha256": first["sha256"]},
                "last_frame": {"asset_id": last["asset_id"], "sha256": last["sha256"]}}
            return request
        if workflow != R2V_WORKFLOW_ID:
            raise StoryHandoffRejected("The Assisted run contains an unsupported workflow.")
        images = [ref for ref in refs if ref["kind"] == "image"]
        if len(images) + int(bool(clip.get("continue_previous_clip"))) > 9:
            raise StoryHandoffRejected("Leave room for the last-frame and character image references.")
        mapped_videos = [ref for ref in refs if ref["kind"] == "video"]
        if {ref["asset_id"] for ref in mapped_videos} & {ref["asset_id"] for ref in style_refs}:
            raise StoryHandoffRejected("A style video is already included for the whole Assisted run; remove its duplicate per-clip mapping.")
        videos = [{"asset_id": ref["asset_id"], "sha256": ref["sha256"], "role": "style",
            "intent": ref["intent"], "start_sec": None, "end_sec": None,
            "include_paired_soundtrack": False, "audio_intent": ""} for ref in style_refs]
        videos.extend(mapped_videos)
        audios = [ref for ref in refs if ref["kind"] == "audio"]
        instructions = []
        paired_audio_count = sum(bool(ref["include_paired_soundtrack"]) for ref in videos)
        for kind, rows, tag in (("image", images, "Picture"), ("video", videos, "Video"), ("audio", audios, "Audio")):
            for index, ref in enumerate(rows, 1):
                if kind == "audio":
                    index += paired_audio_count
                speaker_ids = ref.get("speaker_ids", [])
                if ref.get("speaker_id"):
                    speaker_ids = [ref["speaker_id"]]
                instructions.append(f"<{tag} {index}> {ref['role']}: {ref['intent']}")
                if kind == "audio":
                    # Keep each binding independent of punctuation in user intent
                    # and of how many characters share this one voice asset.
                    instructions.extend(f"<{tag} {index}> is the voice reference for Subject ({speaker_id})."
                        for speaker_id in speaker_ids)
        paired_index = 0
        for index, ref in enumerate(videos, 1):
            if ref["include_paired_soundtrack"]:
                paired_index += 1
                instructions.append(f"<Audio {paired_index}> is the soundtrack of <Video {index}>: {ref['audio_intent']}")
        if clip.get("continue_previous_clip"):
            planned_clips = manifest.get("clips", [])
            clip_index = next((index for index, item in enumerate(planned_clips)
                if item.get("clip_id") == clip.get("clip_id")), None)
            expected_predecessor = (planned_clips[clip_index - 1]
                if clip_index is not None and clip_index > 0 else None)
            if (predecessor_job is None or predecessor_job.get("status") not in {"needs_review", "accepted"}
                    or expected_predecessor is None
                    or expected_predecessor.get("scene_number") != clip.get("scene_number")
                    or predecessor_job.get("clip_id") != expected_predecessor.get("clip_id")):
                raise StoryHandoffRejected("The previous clip is not ready for continuity reference.")
            output = next((asset for asset in predecessor_job.get("outputs", [])
                if asset.get("shared_asset_id") and asset.get("kind") == "video" and asset.get("has_video")), None)
            if output is None:
                raise StoryHandoffRejected("The preceding clip has no reusable shared video asset.")
            frame = last_frame(self.media_root, predecessor_job["workspace_id"], output)
            images.append(frame)
            instructions.append(f"<Picture {len(images)}> {CONTINUITY_INTENT}")
        compiled_prompt = bind_h3_reference_prompt(prompt, instructions)
        if len(compiled_prompt) >= 7000:
            raise StoryHandoffRejected("The complete R2V prompt exceeds MiniMax's 6,999-character limit.")
        return {"workflow_id": R2V_WORKFLOW_ID, "workflow_version": R2V_WORKFLOW_VERSION,
            "workflow_sha256": R2V_GRAPH_SHA256, "prompt": compiled_prompt,
            "duration_seconds": duration, "aspect_ratio": manifest["setup"].get("aspect_ratio", "16:9"),
            "resolution_preset": QUALITY[manifest["setup"]["video_quality"]],
            "steps": 4, "seed": 1, "ref_image_size": "match",
            "images": [{key: ref[key] for key in ("asset_id", "sha256", "role", "intent")} for ref in images],
            "videos": [{key: ref[key] for key in ("asset_id", "sha256", "role", "intent", "start_sec", "end_sec", "include_paired_soundtrack", "audio_intent")} for ref in videos],
            "audios": [{key: ref[key] for key in ("asset_id", "sha256", "role", "intent", "speaker_id", "speaker_ids") if key in ref} for ref in audios]}

    def advance_assisted_video_run(self, workspace_id: str, screenplay_revision_id: str,
                                   *, readiness: Mapping[str, Any] | Callable | None = None):
        """Advance one saved clip at a time; use the existing durable video job queue."""
        workspace = _identifier(workspace_id, "workspace_id")
        revision_id = _identifier(screenplay_revision_id, "screenplay_revision_id")
        with self.ledger._connect() as db:
            run = db.execute("SELECT manifest_json,run_state FROM assisted_video_runs WHERE workspace_id=? AND screenplay_revision_id=?",
                (workspace, revision_id)).fetchone()
            rows = db.execute("SELECT clip_id,job_id,predecessor_job_id FROM assisted_video_run_clips WHERE workspace_id=? AND screenplay_revision_id=?",
                (workspace, revision_id)).fetchall()
        if run is None:
            return {"status": "idle"}
        if run["run_state"] in {"completed", "paused"}:
            return {"status": run["run_state"]}
        manifest = json.loads(run["manifest_json"])
        clips = manifest.get("clips", [])
        bound = {row["clip_id"]: row for row in rows}
        # SQLite does not promise row order without ORDER BY. The manifest is
        # authoritative for clip order; persisted rows only prove which prefix
        # has been admitted. Do not pause a valid recovered run because the
        # query happened to return those rows in a different order.
        if bound and set(bound) != {clip["clip_id"] for clip in clips[:len(bound)]}:
            self._set_assisted_run_state(workspace, revision_id, "paused", "The saved clip ledger does not match the frozen plan order.")
            return {"status": "paused"}
        index = len(bound)
        predecessor = None
        predecessor_id = None
        if index:
            prior = clips[index - 1]
            prior_row = bound[prior["clip_id"]]
            predecessor_id = prior_row["job_id"]
            predecessor = self.get_job(predecessor_id)
            if predecessor["status"] in {"failed", "cancelled", "stale", "recovery_required"}:
                reason = f"Clip {prior['clip_number']} needs retry or recovery ({predecessor['status']})."
                self._set_assisted_run_state(workspace, revision_id, "paused", reason)
                return {"status": "paused", "reason": reason}
            pure_t2v = all(c.get("workflow_id") == T2V_WORKFLOW_ID for c in clips)
            allowed = {"needs_review", "accepted"} | ({"refinement_pending"} if pure_t2v else set())
            if predecessor["status"] not in allowed:
                return {"status": "waiting", "job": predecessor}
        for row in bound.values():
            state = self.get_job(row["job_id"])["status"]
            if state in {"failed", "cancelled", "stale", "recovery_required"}:
                self._set_assisted_run_state(workspace, revision_id, "paused", "A clip requires retry or recovery.")
                return {"status": "paused"}
        if index >= len(clips) and any(self.get_job(row["job_id"])["status"] not in {"needs_review", "accepted"} for row in bound.values()):
            return {"status": "waiting_for_refinement", "job": predecessor}
        if index >= len(clips):
            self._set_assisted_run_state(workspace, revision_id, "completed", None)
            return {"status": "completed", "job": predecessor}
        clip = clips[index]
        workflow = clip["workflow_id"]
        ready = readiness(workflow) if callable(readiness) else readiness
        if not ready or not ready.get("available"):
            reason = (ready or {}).get("reason") or "The selected Assisted workflow is not ready."
            self._set_assisted_run_state(workspace, revision_id, "waiting_for_readiness", reason)
            return {"status": "waiting_for_readiness", "reason": reason}
        try:
            request = self._assisted_request(manifest, clip, predecessor)
            normalized = _normalize_workflow_request(request, self.graph_path, self.fl2va_graph_path, self.r2v_graph_path)
            _compile_workflow_preview(normalized, self.graph_path, self.fl2va_graph_path, self.r2v_graph_path)
            source_prompt = clip["prompt"]
            source_lineage = {"screenplay_revision_id": revision_id, "setup_hash": manifest["setup_hash"],
                "scene_number": clip["scene_number"], "shot_number": clip["shot_number"],
                "source_prompt_sha256": hashlib.sha256(source_prompt.encode()).hexdigest(),
                "workflow_id": workflow, "assisted_clip_id": clip["clip_id"]}
            source_draft = manifest.get("drafts", {}).get(f"{clip['scene_number']}.{clip['shot_number']}")
            if source_draft:
                source_lineage.update(_draft_knowledge_lineage(source_draft))
            key = "assistclip-" + hashlib.sha256(f"{workspace}\0{revision_id}\0{clip['clip_id']}".encode()).hexdigest()
            job = self.create_job(workspace_id=workspace, clip_id=clip["clip_id"], idempotency_key=key,
                request=normalized,
                source_lineage={key: value for key, value in source_lineage.items()
                    if key in _SOURCE_LINEAGE_FIELDS | _OPTIONAL_SOURCE_LINEAGE_FIELDS},
                _assisted_run_clip=(workspace, revision_id, clip["clip_id"], predecessor_id))
            return {"status": "queued", "job": job}
        except (IsolatedVideoContractError, StoryHandoffRejected, IsolatedJobConflict, ValueError) as exc:
            reason = str(exc)[:1200]
            self._set_assisted_run_state(workspace, revision_id, "paused", reason)
            return {"status": "paused", "reason": reason}

    def retry_assisted_video_clip(self, workspace_id: str, screenplay_revision_id: str,
                                  clip_id: str, *, readiness: Mapping[str, Any] | Callable | None = None):
        """Retry only the paused run's latest failed clip, preserving its frozen inputs."""
        workspace = _identifier(workspace_id, "workspace_id")
        revision_id = _identifier(screenplay_revision_id, "screenplay_revision_id")
        clip_id = _identifier(clip_id, "clip_id")
        with self.ledger._connect() as db:
            run = db.execute("SELECT manifest_json,run_state FROM assisted_video_runs WHERE workspace_id=? AND screenplay_revision_id=?",
                (workspace, revision_id)).fetchone()
            rows = db.execute("SELECT clip_id,job_id,predecessor_job_id FROM assisted_video_run_clips WHERE workspace_id=? AND screenplay_revision_id=?",
                (workspace, revision_id)).fetchall()
        if run is None:
            raise IsolatedJobConflict("The Assisted video run does not exist.")
        manifest = json.loads(run["manifest_json"])
        clips = manifest.get("clips", [])
        bound = {row["clip_id"]: row for row in rows}
        target_index = next((index for index, clip in enumerate(clips)
            if clip.get("clip_id") == clip_id), -1)
        if target_index < 0 or clip_id not in bound:
            raise IsolatedJobConflict("That clip has no Assisted run attempt to retry.")
        if target_index != max((index for index, clip in enumerate(clips)
                if clip.get("clip_id") in bound), default=-1):
            raise IsolatedJobConflict("Only the latest failed Assisted clip can be retried.")
        target = bound[clip_id]
        source = self.get_job(target["job_id"])
        if run["run_state"] in {"running", "waiting_for_readiness"} and source["status"] not in {
                "failed", "cancelled", "stale", "recovery_required"}:
            return {"status": "queued", "job": source,
                "run": self.get_assisted_video_run(workspace, revision_id)}
        key = "assistretry-" + hashlib.sha256(
            f"{workspace}\0{revision_id}\0{clip_id}\0{source['job_id']}".encode()).hexdigest()
        try:
            existing = self.get_by_idempotency_key(workspace_id=workspace, idempotency_key=key)
            return {"status": "queued", "job": existing,
                "run": self.get_assisted_video_run(workspace, revision_id)}
        except LedgerNotFound:
            pass
        if run["run_state"] != "paused":
            raise IsolatedJobConflict("Only a paused Assisted video run can retry a failed clip.")
        if source["status"] not in {"failed", "cancelled", "stale", "recovery_required"}:
            raise IsolatedJobConflict("Retry is available only for a failed, cancelled, stale, or recovery-required clip.")
        clip = clips[target_index]
        workflow = clip["workflow_id"]
        ready = readiness(workflow) if callable(readiness) else readiness
        if not ready or not ready.get("available"):
            raise IsolatedVideoContractError("workflow_not_ready",
                (ready or {}).get("reason") or "Retry workflow readiness is unavailable.")
        predecessor_id = target["predecessor_job_id"]
        predecessor = self.get_job(predecessor_id) if predecessor_id else None
        request = source["request"]  # Retry the admitted reference snapshot, not a later identity review.
        normalized = _normalize_workflow_request(request, self.graph_path,
            self.fl2va_graph_path, self.r2v_graph_path)
        _compile_workflow_preview(normalized, self.graph_path, self.fl2va_graph_path, self.r2v_graph_path)
        source_prompt = clip["prompt"]
        lineage = {"screenplay_revision_id": revision_id, "setup_hash": manifest["setup_hash"],
            "scene_number": clip["scene_number"], "shot_number": clip["shot_number"],
            "source_prompt_sha256": hashlib.sha256(source_prompt.encode()).hexdigest()}
        source_draft = manifest.get("drafts", {}).get(f"{clip['scene_number']}.{clip['shot_number']}")
        if source_draft and source_draft.get("knowledge_ref"):
            lineage["knowledge_ref"] = source_draft["knowledge_ref"]
        if source_draft and source_draft.get("style_ref"):
            lineage["style_ref"] = source_draft["style_ref"]
        job = self.create_job(workspace_id=workspace, clip_id=clip_id, idempotency_key=key,
            request=normalized, source_lineage=lineage,
            _assisted_run_clip=(workspace, revision_id, clip_id, predecessor_id),
            _assisted_run_retry=(workspace, revision_id, clip_id, source["job_id"], predecessor_id))
        return {"status": "queued", "job": job,
            "run": self.get_assisted_video_run(workspace, revision_id)}

    def _set_assisted_run_state(self, workspace, revision, state, error):
        with self.ledger._connect() as db:
            db.execute("UPDATE assisted_video_runs SET run_state=?,error_message=?,updated_at=CURRENT_TIMESTAMP WHERE workspace_id=? AND screenplay_revision_id=? AND run_state NOT IN ('owner_paused','stopped')",
                (state, error, workspace, revision))

    def save_assisted_video_reference_maps(self, workspace_id: str, screenplay_revision_id: str,
                                           clips: Any):
        """Save exact per-shot reference identities before an Assisted R2V run.

        This endpoint intentionally stores Director choices; it never infers cast,
        voice, or location references from screenplay prose.
        """
        from story_builder.services.production_setup import ProductionSetup

        workspace = _identifier(workspace_id, "workspace_id")
        revision_id = _identifier(screenplay_revision_id, "screenplay_revision_id")
        if type(clips) is not list:
            raise ValueError("clips must be an array of per-shot reference maps.")
        with self.ledger._connect() as db:
            revision = db.execute("SELECT * FROM story_screenplay_revisions WHERE workspace_id=? AND screenplay_revision_id=?",
                (workspace, revision_id)).fetchone()
            if revision is None or self.story is None or not self.story._screenplay_is_currently_accepted(db, revision):
                raise StoryHandoffRejected("Reference maps require the current accepted screenplay.")
            setup_row = db.execute("SELECT setup_json FROM story_production_setups WHERE workspace_id=? AND screenplay_revision_id=?",
                (workspace, revision_id)).fetchone()
            if setup_row is None:
                raise StoryHandoffRejected("Save Automation & Parameters before mapping video references.")
            setup = ProductionSetup.validate(json.loads(setup_row["setup_json"]))
            if (setup.get("mode") != "assisted_manual" or setup.get("automate_steps", {}).get("video") is not True
                    or setup.get("video_workflow_id") != R2V_WORKFLOW_ID):
                raise StoryHandoffRejected("Per-clip reference maps are only used by Assisted automatic R2V runs.")
            screenplay = json.loads(revision["screenplay_json"])
            valid_shots = {(scene["scene_number"], shot["shot_number"])
                for scene in screenplay.get("scenes", []) for shot in scene.get("shots", [])}

        normalized_clips = {}
        workspace_state = (self.story.get_workspace(workspace, include_source=False)
            if callable(getattr(self.story, "get_workspace", None)) else {})
        style_selection = workspace_state.get("style_selection")
        for clip in clips:
            if (not isinstance(clip, Mapping) or set(clip) != {"scene_number", "shot_number", "references"}
                    or type(clip["scene_number"]) is not int or type(clip["shot_number"]) is not int
                    or (clip["scene_number"], clip["shot_number"]) not in valid_shots
                    or type(clip["references"]) is not list):
                raise ValueError("Each map must identify a screenplay shot and an array of references.")
            identity = (clip["scene_number"], clip["shot_number"])
            if identity in normalized_clips:
                raise ValueError("Each screenplay shot may appear only once in the reference map.")
            refs = []
            counts = {"image": 0, "video": 0, "audio": 0}
            seen_assets = set()
            for ref in clip["references"]:
                if not isinstance(ref, Mapping) or set(ref) - {"kind", "asset_id", "sha256", "role", "intent", "start_sec", "end_sec", "include_paired_soundtrack", "audio_intent", "speaker_id"}:
                    raise ValueError("A reference contains unsupported fields.")
                kind = ref.get("kind")
                fields = {"image": {"kind", "asset_id", "sha256", "role", "intent"},
                    "video": {"kind", "asset_id", "sha256", "role", "intent", "start_sec", "end_sec", "include_paired_soundtrack", "audio_intent"},
                    "audio": {"kind", "asset_id", "sha256", "role", "intent", "speaker_id"}}
                if kind not in fields or set(ref) != fields[kind]:
                    raise ValueError("Each reference must use the fields supported for its media kind.")
                if type(ref["role"]) is not str or not ref["role"].strip() or type(ref["intent"]) is not str or not ref["intent"].strip():
                    raise ValueError("Each reference needs a role and an explanation of how to use it.")
                if self.media_root is None:
                    raise StoryHandoffRejected("Workspace media storage is not configured for reference mapping.")
                if ref["asset_id"] in seen_assets:
                    raise ValueError("An asset may appear only once in a clip reference map.")
                seen_assets.add(ref["asset_id"])
                if len(ref["intent"].strip()) > 500 or len(ref["role"].strip()) > 80:
                    raise ValueError("Reference roles must be under 80 characters and intents under 500.")
                media_rows = []
                offset = 0
                while True:
                    page = list_workspace_media_assets(self.media_root, workspace, kind=kind,
                        limit=100, offset=offset, style_selection=style_selection)
                    media_rows.extend(page["assets"])
                    offset += len(page["assets"])
                    if offset >= page["total"] or not page["assets"]:
                        break
                asset = next((item for item in media_rows if item["asset_id"] == ref["asset_id"]), None)
                if asset is None or asset.get("sha256") != ref["sha256"]:
                    raise StoryHandoffRejected("A selected reference is missing, changed, or belongs to another workspace.")
                counts[kind] += 1
                if kind == "image":
                    refs.append({key: ref[key] for key in ("asset_id", "sha256", "role", "intent")})
                elif kind == "video":
                    refs.append({key: ref[key] for key in ("asset_id", "sha256", "role", "intent", "start_sec", "end_sec", "include_paired_soundtrack", "audio_intent")})
                else:
                    refs.append({key: ref[key] for key in ("asset_id", "sha256", "role", "intent", "speaker_id")})
            if counts["image"] > 9 or counts["video"] > 3 or counts["audio"] > 3:
                raise ValueError("R2V supports up to 9 images, 3 videos, and 3 audio references per clip.")
            normalized_clips[identity] = refs

        # Refuse late edits once a run exists, so the map can be snapshotted safely.
        with self.ledger._connect() as db:
            run = db.execute("SELECT 1 FROM assisted_video_runs WHERE workspace_id=? AND screenplay_revision_id=?",
                (workspace, revision_id)).fetchone() if self._table_exists(db, "assisted_video_runs") else None
            if run:
                raise IsolatedJobConflict("Reference maps are frozen after the Assisted run starts.")
            db.execute("DELETE FROM assisted_video_reference_maps WHERE workspace_id=? AND screenplay_revision_id=?", (workspace, revision_id))
            db.executemany("INSERT INTO assisted_video_reference_maps(workspace_id,screenplay_revision_id,scene_number,shot_number,references_json) VALUES(?,?,?,?,?)",
                [(workspace, revision_id, scene, shot, json.dumps(refs, sort_keys=True, separators=(",", ":")))
                    for (scene, shot), refs in normalized_clips.items()])
        return self.get_assisted_video_reference_maps(workspace, revision_id)

    @staticmethod
    def _table_exists(db, name):
        return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None

    def _get_bound_first_clip(self, workspace_id: str, screenplay_revision_id: str):
        with self.ledger._connect() as db:
            row = db.execute("SELECT job_id FROM fully_automated_first_clip_bindings WHERE workspace_id=? AND screenplay_revision_id=?",
                (workspace_id, screenplay_revision_id)).fetchone()
        return self.get_job(row["job_id"]) if row else None

    def _fully_automated_run_result(self, workspace_id, revision_id, first_job=None):
        with self.ledger._connect() as db:
            run = db.execute("SELECT run_state,error_message,manifest_json FROM fully_automated_runs WHERE workspace_id=? AND screenplay_revision_id=?",
                (workspace_id, revision_id)).fetchone()
            rows = db.execute("SELECT job_id,scene_number,shot_number,clip_number,predecessor_job_id,clip_state FROM fully_automated_run_clips WHERE workspace_id=? AND screenplay_revision_id=?",
                (workspace_id, revision_id)).fetchall()
            identity_reviews = {}
            if self._table_exists(db, "fully_automated_identity_reviews"):
                review_rows = db.execute("SELECT source_job_id,state,result_json,error_message,updated_at,input_json FROM fully_automated_identity_reviews WHERE workspace_id=? AND screenplay_revision_id=?",
                    (workspace_id, revision_id)).fetchall()
                for review in review_rows:
                    try:
                        names = {item["character_id"]: item["name"] for item in json.loads(review["input_json"]).get("characters", [])}
                        result_json = json.loads(review["result_json"]) if review["result_json"] else None
                        frames = []
                        for frame in (result_json or {}).get("frames", []):
                            observations = []
                            for observation in frame.get("observations", []):
                                character_id = observation.get("character_id")
                                observations.append({"status": observation.get("status"),
                                    "character_id": character_id,
                                    "character_name": names.get(character_id) if character_id else None,
                                    "visual_evidence": observation.get("visual_evidence")})
                            frames.append({"sample_index": frame.get("sample_index"),
                                "timestamp_seconds": frame.get("timestamp_seconds"), "observations": observations})
                        identity_reviews[review["source_job_id"]] = {
                            "state": review["state"], "updated_at": review["updated_at"],
                            "error": "Review failed. Check worker status or retry." if review["state"] == "failed" else None,
                            "frames": frames,
                        }
                    except (TypeError, ValueError, KeyError, AttributeError):
                        # Keep the run readable if a legacy/corrupt review row cannot be rendered.
                        identity_reviews[review["source_job_id"]] = {"state": review["state"],
                            "updated_at": review["updated_at"], "error": "Review result could not be read.", "frames": []}
        manifest = json.loads(run["manifest_json"]) if run else {}
        v2 = manifest.get("manifest_version") in {2, 3}
        planned = manifest.get("clip_plan", {}).get("clips", []) if v2 else []
        plan_order = {(clip["scene_number"], clip["shot_number"], clip["clip_number"]): index
            for index, clip in enumerate(planned)}
        rows = sorted(rows, key=lambda row: (0, plan_order[(row["scene_number"], row["shot_number"], row["clip_number"])])
            if v2 and (row["scene_number"], row["shot_number"], row["clip_number"]) in plan_order
            else (1, row["scene_number"], row["shot_number"], row["clip_number"]))
        clips = []
        for row in rows:
            job = self.get_job(row["job_id"])
            with self.ledger._connect() as db:
                attempts = db.execute("SELECT job_id,attempt_number,predecessor_job_id FROM fully_automated_run_attempts WHERE workspace_id=? AND screenplay_revision_id=? AND scene_number=? AND shot_number=? AND clip_number=? ORDER BY attempt_number",
                    (workspace_id, revision_id, row["scene_number"], row["shot_number"], row["clip_number"])).fetchall()
            history = []
            for attempt in attempts:
                prior = self.get_job(attempt["job_id"])
                history.append({"attempt_number": attempt["attempt_number"], "predecessor_job_id": attempt["predecessor_job_id"], "job": prior})
            if not history:
                history = [{"attempt_number": 1, "predecessor_job_id": row["predecessor_job_id"], "job": job}]
            plan_item = next((clip for clip in planned if (clip["scene_number"], clip["shot_number"], clip["clip_number"])
                == (row["scene_number"], row["shot_number"], row["clip_number"])), None) if v2 else None
            clips.append({"scene_number": row["scene_number"], "shot_number": row["shot_number"],
                "clip_number": row["clip_number"], "clip_id": job["clip_id"],
                "duration_seconds": plan_item["duration_seconds"] if plan_item else job.get("request", {}).get("duration_seconds"),
                "duration_reason": plan_item.get("duration_reason") if plan_item else None,
                "predecessor_job_id": row["predecessor_job_id"], "state": job["status"], "job": job,
                "identity_review": identity_reviews.get(row["job_id"]),
                "attempts": history})
        if first_job is None:
            first_job = next((clip["job"] for clip in clips if clip["scene_number"] == clips[0]["scene_number"] and clip["shot_number"] == clips[0]["shot_number"]), None) if clips else None
        result = self._first_clip_result(first_job) if first_job else {}
        state = run["run_state"] if run else "not_started"
        if state == "running":
            state = "first_clip_queued"
        resume_available = False
        if (run and run["run_state"] == "paused" and manifest.get("manifest_version") == 3
                and len(rows) == len(planned) and planned
                and len(manifest.get("planned_scene_numbers", [])) < len(manifest.get("screenplay", {}).get("scenes", []))):
            latest = next((clip for clip in clips if
                (clip["scene_number"], clip["shot_number"], clip["clip_number"]) ==
                (planned[-1]["scene_number"], planned[-1]["shot_number"], planned[-1]["clip_number"])), None)
            resume_available = bool(latest and latest["state"] in {"needs_review", "accepted"})
        return {**result, "run_state": state,
            "error": None if not run else run["error_message"], "clips": clips,
            "resume_available": resume_available,
            "planned_count": len(planned) if v2 else None,
            "completed_count": sum(clip["state"] in {"needs_review", "accepted"} for clip in clips)}

    def resume_fully_automated_planning(self, workspace_id: str, screenplay_revision_id: str):
        """Resume a paused V3 run only when its completed plan can safely extend."""
        workspace = _identifier(workspace_id, "workspace_id")
        revision_id = _identifier(screenplay_revision_id, "screenplay_revision_id")
        with self.ledger._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            run = db.execute("SELECT run_state,manifest_json FROM fully_automated_runs WHERE workspace_id=? AND screenplay_revision_id=?",
                (workspace, revision_id)).fetchone()
            manifest = json.loads(run["manifest_json"]) if run else {}
            plan = manifest.get("clip_plan", {}).get("clips", [])
            scenes = manifest.get("screenplay", {}).get("scenes", [])
            planned_scenes = manifest.get("planned_scene_numbers", [])
            bindings = db.execute("SELECT scene_number,shot_number,clip_number,job_id FROM fully_automated_run_clips WHERE workspace_id=? AND screenplay_revision_id=?",
                (workspace, revision_id)).fetchall()
            eligible = bool(run and run["run_state"] == "paused"
                and manifest.get("manifest_version") == 3 and plan
                and len(bindings) == len(plan) and len(planned_scenes) < len(scenes))
            if eligible:
                last = plan[-1]
                binding = next((item for item in bindings if
                    (item["scene_number"], item["shot_number"], item["clip_number"]) ==
                    (last["scene_number"], last["shot_number"], last["clip_number"])), None)
                job = db.execute("SELECT status FROM production_takes WHERE job_id=?", (binding["job_id"],)).fetchone() if binding else None
                eligible = bool(job and job["status"] in {"needs_review", "accepted"})
            if not eligible:
                db.rollback()
                raise IsolatedJobConflict("This Full run cannot resume planning; retry its failed clip or refresh its status.")
            cursor = db.execute("UPDATE fully_automated_runs SET run_state='running',error_message=NULL,updated_at=CURRENT_TIMESTAMP WHERE workspace_id=? AND screenplay_revision_id=? AND run_state='paused'",
                (workspace, revision_id))
            if cursor.rowcount != 1:
                db.rollback()
                raise IsolatedJobConflict("The Full run changed while resuming; refresh its status.")
            db.commit()
        return self._fully_automated_run_result(workspace, revision_id)

    def _extend_v3_full_run(self, workspace, revision_id, manifest, old_json):
        """Freeze the next scene's prompts and plan after the prior scene finishes."""
        screenplay = manifest["screenplay"]
        scene_index = len(manifest.get("planned_scene_numbers", []))
        if scene_index >= len(screenplay.get("scenes", [])):
            return manifest
        scene = screenplay["scenes"][scene_index]
        if not isinstance(scene, dict) or type(scene.get("scene_number")) is not int:
            raise StoryHandoffRejected("The next frozen screenplay scene is malformed.")
        setup = manifest["setup"]
        scene_start_identity_refs = False
        # The manifest is the run's source of truth. Do not reread mutable prompt
        # edits made after the run began; only prepare drafts absent from its snapshot.
        drafts = self._prepare_full_scene_drafts(workspace, revision_id, setup,
            scene, manifest.get("drafts", {}), persist=False,
            scene_start_identity_refs=scene_start_identity_refs)
        scene_drafts = {f"{scene['scene_number']}.{shot['shot_number']}":
            drafts[f"{scene['scene_number']}.{shot['shot_number']}"] for shot in scene["shots"]}
        policy = setup["duration_policy"]
        minimum, maximum = ((policy["seconds"], policy["seconds"]) if policy["kind"] == "fixed"
            else (policy["min_seconds"], policy["max_seconds"]))
        next_plan = generate_scene_clip_plan(workspace_id=workspace,
            screenplay_revision_id=revision_id, screenplay=screenplay, scene=scene,
            drafts=scene_drafts, min_seconds=minimum, max_seconds=maximum,
            has_style_video=False,
            generate_json=self.full_clip_plan_provider,
            scene_start_identity_refs=scene_start_identity_refs)
        merged = {**manifest, "drafts": drafts,
            "planned_scene_numbers": [*manifest.get("planned_scene_numbers", []), scene["scene_number"]],
            "clip_plan": {"clips": [*manifest["clip_plan"]["clips"], *next_plan["clips"]]}}
        merged["clip_plan_sha256"] = hashlib.sha256(json.dumps(merged["clip_plan"],
            sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()
        merged["drafts_sha256"] = hashlib.sha256(json.dumps(drafts, sort_keys=True,
            ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()
        with self.ledger._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                current = db.execute("SELECT manifest_json FROM fully_automated_runs WHERE workspace_id=? AND screenplay_revision_id=?",
                    (workspace, revision_id)).fetchone()
                if current is None:
                    raise StoryHandoffRejected("The Full-run record disappeared while planning the next scene.")
                if current["manifest_json"] != old_json:
                    latest = json.loads(current["manifest_json"])
                    db.rollback()
                    return latest
                revision = db.execute("SELECT * FROM story_screenplay_revisions WHERE workspace_id=? AND screenplay_revision_id=?",
                    (workspace, revision_id)).fetchone()
                screenplay_hash = hashlib.sha256(json.dumps(json.loads(revision["screenplay_json"]),
                    sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest() if revision else None
                if (revision is None or self.story is None
                        or not self.story._screenplay_is_currently_accepted(db, revision)
                        or screenplay_hash != manifest["screenplay_sha256"]):
                    raise StoryHandoffRejected("The accepted screenplay changed while planning the next scene.")
                encoded = json.dumps(merged, sort_keys=True, separators=(",", ":"))
                cursor = db.execute("UPDATE fully_automated_runs SET manifest_json=?,run_state='running',error_message=NULL,updated_at=CURRENT_TIMESTAMP WHERE workspace_id=? AND screenplay_revision_id=? AND manifest_json=?",
                    (encoded, workspace, revision_id, old_json))
                if cursor.rowcount != 1:
                    raise StoryHandoffRejected("The Full-run scene plan changed during admission; reload its status.")
                db.commit()
            except Exception:
                db.rollback()
                raise
        return merged

    def advance_fully_automated_run(self, workspace_id: str, screenplay_revision_id: str,
                                    *, readiness: Mapping[str, Any] | None = None):
        """Queue at most the next frozen shot after its predecessor completed."""
        workspace = _identifier(workspace_id, "workspace_id")
        revision_id = _identifier(screenplay_revision_id, "screenplay_revision_id")
        version = None
        with self.ledger._connect() as db:
            run_row = db.execute("SELECT * FROM fully_automated_runs WHERE workspace_id=? AND screenplay_revision_id=?",
                (workspace, revision_id)).fetchone()
            if run_row is None:
                return {"status": "idle"}
            if run_row["run_state"] not in {"running", "waiting_for_readiness"}:
                return {"status": run_row["run_state"]}
            manifest = json.loads(run_row["manifest_json"])
            if manifest.get("manifest_version") in {2, 3}:
                plan = manifest.get("clip_plan", {}).get("clips", [])
                bound_rows = db.execute("SELECT * FROM fully_automated_run_clips WHERE workspace_id=? AND screenplay_revision_id=?",
                    (workspace, revision_id)).fetchall()
                bound = {(row["scene_number"], row["shot_number"], row["clip_number"]): row for row in bound_rows}
                current_manifest_json = run_row["manifest_json"]
                version = manifest.get("manifest_version")
            else:
                ordered = [(scene["scene_number"], shot["shot_number"], scene, shot)
                    for scene in manifest["screenplay"].get("scenes", [])
                    for shot in scene.get("shots", [])]
                bound = {(row["scene_number"], row["shot_number"]): row for row in db.execute(
                    "SELECT * FROM fully_automated_run_clips WHERE workspace_id=? AND screenplay_revision_id=?",
                    (workspace, revision_id)).fetchall()}
        if version in {2, 3}:
            if version == 3 and len(bound) == len(plan) and plan:
                previous = self.get_job(bound[(plan[-1]["scene_number"], plan[-1]["shot_number"], plan[-1]["clip_number"])]["job_id"])
                next_index = len(manifest.get("planned_scene_numbers", []))
                if (previous["status"] in {"needs_review", "accepted", "refinement_pending"}
                        and next_index < len(manifest["screenplay"].get("scenes", []))):
                    try:
                        manifest = self._extend_v3_full_run(workspace, revision_id,
                            manifest, current_manifest_json)
                    except (ClipPlanError, LedgerConflict, LedgerNotFound,
                            StoryHandoffRejected, ValueError) as exc:
                        self._set_full_run_state(workspace, revision_id, "paused", str(exc)[:1200])
                        return {"status": "paused", "reason": str(exc)}
                    plan = manifest.get("clip_plan", {}).get("clips", [])
            # V2 runs keep the entire immutable plan; V3 appends one validated
            # scene only after the previous scene's clips have settled.
            return self._advance_v2_full_run(workspace, revision_id, manifest, plan, bound, readiness)
        if not ordered:
            self._set_full_run_state(workspace, revision_id, "paused", "The frozen screenplay has no shots.")
            return {"status": "paused"}
        last_bound = max((index for index, (scene, shot, *_rest) in enumerate(ordered) if (scene, shot) in bound), default=-1)
        if last_bound < 0:
            return {"status": "idle"}
        previous = ordered[last_bound]
        previous_binding = bound[(previous[0], previous[1])]
        previous_job = self.get_job(previous_binding["job_id"])
        # Unknown submission outcomes remain owned by reconciliation. Waiting
        # here preserves the same prompt instead of offering a duplicate retry.
        if previous_job["status"] in {"failed", "cancelled", "stale"}:
            self._set_full_run_state(workspace, revision_id, "paused",
                f"Scene {previous[0]}, Shot {previous[1]} ended as {previous_job['status']}; retry or resume is required.")
            return {"status": "paused", "job": previous_job}
        if previous_job["status"] not in {"needs_review", "accepted"}:
            return {"status": "waiting", "job": previous_job}
        if last_bound + 1 >= len(ordered):
            self._set_full_run_state(workspace, revision_id, "completed", None)
            return {"status": "completed", "job": previous_job}
        scene_number, shot_number, scene, shot = ordered[last_bound + 1]
        is_scene_start = last_bound < 0 or ordered[last_bound][0] != scene_number
        workflow_id = (T2V_WORKFLOW_ID if is_scene_start else R2V_WORKFLOW_ID)
        draft = manifest["drafts"].get(f"{scene_number}.{shot_number}")
        if not isinstance(draft, dict) or draft.get("workflow_id") != workflow_id or type(draft.get("prompt")) is not str or not draft["prompt"].strip():
            self._set_full_run_state(workspace, revision_id, "paused",
                f"Frozen prompt or workflow is missing for Scene {scene_number}, Shot {shot_number}.")
            return {"status": "paused"}
        readiness = readiness(workflow_id) if callable(readiness) else readiness
        if not readiness or not readiness.get("available"):
            reason = (readiness or {}).get("reason") or "The next workflow is not ready."
            self._set_full_run_state(workspace, revision_id, "waiting_for_readiness", reason)
            return {"status": "waiting_for_readiness", "reason": reason}
        if workflow_id == T2V_WORKFLOW_ID:
            request = {"workflow_id": T2V_WORKFLOW_ID, "workflow_version": T2V_WORKFLOW_VERSION,
                "workflow_sha256": EXPECTED_GRAPH_SHA256, "prompt": draft["prompt"],
                "duration_seconds": manifest["setup"]["duration_policy"]["seconds"],
                "aspect_ratio": manifest["setup"].get("aspect_ratio", "16:9"), "resolution_preset": self._quality_preset(manifest["setup"]["video_quality"]),
                "steps": 4, "seed": 1, "references": []}
        elif is_scene_start:
            request = self._full_r2v_request(setup=manifest["setup"], prompt=draft["prompt"])
        else:
            output = next((asset for asset in previous_job.get("outputs", [])
                if asset.get("shared_asset_id") and asset.get("kind") == "video" and asset.get("has_video")), None)
            if not output:
                self._set_full_run_state(workspace, revision_id, "paused", "The preceding clip has no reusable shared video asset.")
                return {"status": "paused", "job": previous_job}
            request = self._full_r2v_request(setup=manifest["setup"], prompt=draft["prompt"],
                continuity=last_frame(self.media_root, workspace, output))
        clip_id = story_clip_id(workspace, revision_id, scene_number, shot_number)
        key = "fullshot-" + hashlib.sha256(f"{workspace}\0{revision_id}\0{scene_number}\0{shot_number}".encode()).hexdigest()
        prompt_hash = hashlib.sha256(draft["prompt"].encode()).hexdigest()
        lineage = {"screenplay_revision_id": revision_id, "setup_hash": manifest["setup_hash"],
            "scene_number": scene_number, "shot_number": shot_number, "source_prompt_sha256": prompt_hash,
            **_draft_knowledge_lineage(draft)}
        try:
            job = self.create_job(workspace_id=workspace, clip_id=clip_id, idempotency_key=key, request=request,
                source_lineage=lineage, _full_run_clip=(workspace, revision_id, scene_number, shot_number, previous_job["job_id"]),
                _full_run_continuation=True)
        except (IsolatedVideoContractError, StoryHandoffRejected, IsolatedJobConflict, ValueError) as exc:
            self._set_full_run_state(workspace, revision_id, "paused", str(exc)[:1200])
            return {"status": "paused", "reason": str(exc)}
        self._set_full_run_state(workspace, revision_id, "running", None)
        return {"status": "queued", "job": job}

    def _advance_v2_full_run(self, workspace, revision_id, manifest, plan, bound, readiness):
        identities = [(clip["scene_number"], clip["shot_number"], clip["clip_number"]) for clip in plan]
        if not identities or len(set(identities)) != len(identities):
            self._set_full_run_state(workspace, revision_id, "paused", "The frozen clip plan is empty or has duplicate identities.")
            return {"status": "paused"}
        prefix_length = len(bound)
        if list(bound) and any(identity not in identities[:prefix_length] for identity in bound):
            self._set_full_run_state(workspace, revision_id, "paused", "The durable clip ledger does not match the frozen clip-plan order.")
            return {"status": "paused"}
        if set(bound) != set(identities[:prefix_length]):
            self._set_full_run_state(workspace, revision_id, "paused", "The durable clip ledger has a gap before its latest clip.")
            return {"status": "paused"}
        if prefix_length == 0:
            return {"status": "idle"}
        previous_clip = plan[prefix_length - 1]
        previous_row = bound[identities[prefix_length - 1]]
        previous_job = self.get_job(previous_row["job_id"])
        # Unknown submission outcomes remain owned by reconciliation. Waiting
        # here preserves the same prompt instead of offering a duplicate retry.
        if previous_job["status"] in {"failed", "cancelled", "stale"}:
            self._set_full_run_state(workspace, revision_id, "paused",
                f"Scene {previous_clip['scene_number']}, Shot {previous_clip['shot_number']}, Clip {previous_clip['clip_number']} ended as {previous_job['status']}; retry is required.")
            return {"status": "paused", "job": previous_job}
        pure_t2v = all(c.get("workflow_id") == T2V_WORKFLOW_ID for c in plan)
        for bound_row in bound.values():
            earlier = self.get_job(bound_row["job_id"])
            if earlier["status"] in {"failed", "cancelled", "stale", "recovery_required"}:
                self._set_full_run_state(workspace, revision_id, "paused", "A saved clip requires retry or recovery before continuing.")
                return {"status": "paused", "job": earlier}
        allowed = {"needs_review", "accepted"} | ({"refinement_pending"} if pure_t2v else set())
        if previous_job["status"] not in allowed:
            return {"status": "waiting", "job": previous_job}
        if prefix_length == len(plan) and any(self.get_job(row["job_id"])["status"] not in {"needs_review", "accepted"} for row in bound.values()):
            return {"status": "waiting_for_refinement", "job": previous_job}
        if prefix_length == len(plan):
            self._set_full_run_state(workspace, revision_id, "completed", None)
            return {"status": "completed", "job": previous_job}

        clip = plan[prefix_length]
        scene_number, shot_number, clip_number = clip["scene_number"], clip["shot_number"], clip["clip_number"]
        is_scene_start = prefix_length == 0 or plan[prefix_length - 1]["scene_number"] != scene_number
        workflow_id = clip["workflow_id"]
        ready = readiness(workflow_id) if callable(readiness) else readiness
        if not ready or not ready.get("available"):
            reason = (ready or {}).get("reason") or "The next workflow is not ready."
            self._set_full_run_state(workspace, revision_id, "waiting_for_readiness", reason)
            return {"status": "waiting_for_readiness", "reason": reason}
        if workflow_id == T2V_WORKFLOW_ID:
            request = {"workflow_id": T2V_WORKFLOW_ID, "workflow_version": T2V_WORKFLOW_VERSION,
                "workflow_sha256": EXPECTED_GRAPH_SHA256, "prompt": clip["prompt"],
                "duration_seconds": clip["duration_seconds"], "aspect_ratio": manifest["setup"].get("aspect_ratio", "16:9"),
                "resolution_preset": self._quality_preset(manifest["setup"]["video_quality"]),
                "steps": 4, "seed": 1, "references": []}
        else:
            continuity = None
            # Selected style videos remain distinct references throughout the
            # Full run. Scene boundaries reset only predecessor continuity.
            include_style = True
            if not is_scene_start:
                output = next((asset for asset in previous_job.get("outputs", [])
                    if asset.get("shared_asset_id") and asset.get("kind") == "video" and asset.get("has_video")), None)
                if not output:
                    self._set_full_run_state(workspace, revision_id, "paused", "The preceding clip has no reusable shared video asset.")
                    return {"status": "paused", "job": previous_job}
                continuity = last_frame(self.media_root, workspace, output)
            with self.ledger._connect() as db:
                identity_images = self._full_identity_images(db, workspace, revision_id, plan, prefix_length, clip)
            if clip.get("character_refs_required") and not identity_images:
                self._set_full_run_state(workspace, revision_id, "paused",
                    "The verified character reference for this scene start is no longer available.")
                return {"status": "paused", "reason": "The verified character reference for this scene start is no longer available."}
            request = self._full_r2v_request(setup=manifest["setup"], prompt=clip["prompt"],
                duration_seconds=clip["duration_seconds"], continuity=continuity,
                identity_images=identity_images, include_style=include_style)
        draft = manifest["drafts"].get(f"{scene_number}.{shot_number}")
        if not isinstance(draft, dict):
            self._set_full_run_state(workspace, revision_id, "paused", "The frozen source prompt is missing.")
            return {"status": "paused"}
        lineage = {"screenplay_revision_id": revision_id, "setup_hash": manifest["setup_hash"],
            "scene_number": scene_number, "shot_number": shot_number,
            "source_prompt_sha256": hashlib.sha256(draft["prompt"].encode()).hexdigest(),
            **_draft_knowledge_lineage(draft)}
        key = "fullclip-" + hashlib.sha256(
            f"{workspace}\0{revision_id}\0{scene_number}\0{shot_number}\0{clip_number}".encode()).hexdigest()
        try:
            job = self.create_job(workspace_id=workspace, clip_id=clip["clip_id"],
                idempotency_key=key, request=request, source_lineage=lineage,
                _full_run_clip=(workspace, revision_id, scene_number, shot_number, clip_number,
                    previous_job["job_id"]), _full_run_continuation=True)
        except (IsolatedVideoContractError, StoryHandoffRejected, IsolatedJobConflict, ValueError) as exc:
            self._set_full_run_state(workspace, revision_id, "paused", str(exc)[:1200])
            return {"status": "paused", "reason": str(exc)}
        self._set_full_run_state(workspace, revision_id, "running", None)
        return {"status": "queued", "job": job}

    def retry_fully_automated_shot(self, workspace_id: str, screenplay_revision_id: str,
                                   scene_number: int, shot_number: int, *, clip_number: int = 1,
                                   readiness: Mapping[str, Any] | None = None):
        """Create one frozen-manifest retry for the paused run's latest failed shot."""
        workspace = _identifier(workspace_id, "workspace_id")
        revision_id = _identifier(screenplay_revision_id, "screenplay_revision_id")
        if (type(scene_number) is not int or scene_number < 1 or type(shot_number) is not int
                or shot_number < 1 or type(clip_number) is not int or clip_number < 1):
            raise ValueError("Retry scene_number, shot_number, and clip_number must be positive integers.")
        with self.ledger._connect() as db:
            run = db.execute("SELECT manifest_json,run_state FROM fully_automated_runs WHERE workspace_id=? AND screenplay_revision_id=?",
                (workspace, revision_id)).fetchone()
            if run is None:
                raise IsolatedJobConflict("The Fully automated run does not exist.")
            manifest = json.loads(run["manifest_json"])
            clips = db.execute("SELECT * FROM fully_automated_run_clips WHERE workspace_id=? AND screenplay_revision_id=?",
                (workspace, revision_id)).fetchall()
        if manifest.get("manifest_version") in {2, 3}:
            return self._retry_v2_full_clip(workspace, revision_id, manifest,
                run["run_state"], clips, scene_number, shot_number, clip_number, readiness)
        bound = {(row["scene_number"], row["shot_number"]): row for row in clips}
        target = bound.get((scene_number, shot_number))
        if target is None:
            raise IsolatedJobConflict("That shot has no failed Full-run attempt to retry.")
        source_job_id = target["job_id"]
        source = self.get_job(source_job_id)
        if run["run_state"] == "running" and source["status"] not in {"failed", "cancelled", "recovery_required", "stale"}:
            return {"status": "queued", "job": source, "run": self._fully_automated_run_result(workspace, revision_id)}
        key = "fullretry-" + hashlib.sha256(f"{workspace}\0{revision_id}\0{scene_number}\0{shot_number}\0{source_job_id}".encode()).hexdigest()
        try:
            existing = self.get_by_idempotency_key(workspace_id=workspace, idempotency_key=key)
            return {"status": "queued", "job": existing, "run": self._fully_automated_run_result(workspace, revision_id)}
        except LedgerNotFound:
            pass
        if run["run_state"] != "paused":
            raise IsolatedJobConflict("Only a paused Fully automated run can retry a failed shot.")
        if source["status"] not in {"failed", "cancelled", "recovery_required", "stale"}:
            raise IsolatedJobConflict("Retry is available only for a failed, cancelled, stale, or recovery-required shot.")
        order = [(scene["scene_number"], shot["shot_number"]) for scene in manifest["screenplay"].get("scenes", []) for shot in scene.get("shots", [])]
        target_index = order.index((scene_number, shot_number)) if (scene_number, shot_number) in order else -1
        last_bound_index = max((i for i, pair in enumerate(order) if pair in bound), default=-1)
        if target_index != last_bound_index:
            raise IsolatedJobConflict("Only the latest failed shot can be retried; downstream clips must not be rebound.")
        predecessor_id = target["predecessor_job_id"]
        draft = manifest["drafts"].get(f"{scene_number}.{shot_number}")
        if not isinstance(draft, dict) or not isinstance(draft.get("prompt"), str):
            raise IsolatedJobConflict("The frozen retry prompt is missing.")
        scene_start = target_index == 0 or order[target_index - 1][0] != scene_number
        workflow_id = (T2V_WORKFLOW_ID if scene_start else R2V_WORKFLOW_ID)
        if draft.get("workflow_id") != workflow_id:
            raise IsolatedJobConflict("The frozen retry workflow does not match the Full-run route.")
        if workflow_id == T2V_WORKFLOW_ID:
            request = {"workflow_id": T2V_WORKFLOW_ID, "workflow_version": T2V_WORKFLOW_VERSION,
                "workflow_sha256": EXPECTED_GRAPH_SHA256, "prompt": draft["prompt"],
                "duration_seconds": manifest["setup"]["duration_policy"]["seconds"], "aspect_ratio": manifest["setup"].get("aspect_ratio", "16:9"),
                "resolution_preset": self._quality_preset(manifest["setup"]["video_quality"]), "steps": 4, "seed": 1, "references": []}
        elif scene_start:
            request = self._full_r2v_request(setup=manifest["setup"], prompt=draft["prompt"])
        else:
            prior = self.get_job(predecessor_id) if predecessor_id else None
            output = next((asset for asset in (prior or {}).get("outputs", [])
                if asset.get("shared_asset_id") and asset.get("kind") == "video" and asset.get("has_video")), None)
            if not output or prior["status"] not in {"needs_review", "accepted"}:
                raise IsolatedJobConflict("The previous successful clip is unavailable as the retry's continuity reference.")
            request = self._full_r2v_request(setup=manifest["setup"], prompt=draft["prompt"],
                continuity=last_frame(self.media_root, workspace, output))
        readiness = readiness(workflow_id) if callable(readiness) else readiness
        if not readiness or not readiness.get("available"):
            raise IsolatedVideoContractError("workflow_not_ready", (readiness or {}).get("reason") or "Retry workflow readiness is unavailable.")
        with self.ledger._connect() as db:
            attempt_number = db.execute("SELECT COALESCE(MAX(attempt_number),0)+1 FROM fully_automated_run_attempts WHERE workspace_id=? AND screenplay_revision_id=? AND scene_number=? AND shot_number=?",
                (workspace, revision_id, scene_number, shot_number)).fetchone()[0] + (1 if not db.execute("SELECT 1 FROM fully_automated_run_attempts WHERE job_id=?", (source_job_id,)).fetchone() else 0)
        # Legacy first attempts predate the attempts table; keep their retry
        # numbered 2, while new run rows begin with attempt 1.
        attempt_number = max(2, int(attempt_number))
        clip_id = story_clip_id(workspace, revision_id, scene_number, shot_number)
        prompt_hash = hashlib.sha256(draft["prompt"].encode()).hexdigest()
        lineage = {"screenplay_revision_id": revision_id, "setup_hash": manifest["setup_hash"],
            "scene_number": scene_number, "shot_number": shot_number, "source_prompt_sha256": prompt_hash,
            **_draft_knowledge_lineage(draft)}
        job = self.create_job(workspace_id=workspace, clip_id=clip_id, idempotency_key=key, request=request,
            source_lineage=lineage, _full_run_clip=(workspace, revision_id, scene_number, shot_number, predecessor_id),
            _full_run_continuation=True,
            _full_run_retry=(workspace, revision_id, scene_number, shot_number, source_job_id, attempt_number, predecessor_id))
        return {"status": "queued", "job": job, "run": self._fully_automated_run_result(workspace, revision_id)}

    def _retry_v2_full_clip(self, workspace, revision_id, manifest, run_state, rows,
                            scene_number, shot_number, clip_number, readiness):
        plan = manifest.get("clip_plan", {}).get("clips", [])
        identities = [(clip["scene_number"], clip["shot_number"], clip["clip_number"]) for clip in plan]
        identity = (scene_number, shot_number, clip_number)
        if identity not in identities:
            raise IsolatedJobConflict("That planned clip does not exist in this Full run.")
        bound = {(row["scene_number"], row["shot_number"], row["clip_number"]): row for row in rows}
        target = bound.get(identity)
        if target is None:
            raise IsolatedJobConflict("That clip has no failed Full-run attempt to retry.")
        source_job_id = target["job_id"]
        source = self.get_job(source_job_id)
        if run_state == "running" and source["status"] not in {"failed", "cancelled", "recovery_required", "stale"}:
            return {"status": "queued", "job": source, "run": self._fully_automated_run_result(workspace, revision_id)}
        key = "fullretry-" + hashlib.sha256(
            f"{workspace}\0{revision_id}\0{scene_number}\0{shot_number}\0{clip_number}\0{source_job_id}".encode()).hexdigest()
        try:
            existing = self.get_by_idempotency_key(workspace_id=workspace, idempotency_key=key)
            return {"status": "queued", "job": existing, "run": self._fully_automated_run_result(workspace, revision_id)}
        except LedgerNotFound:
            pass
        if run_state != "paused" or source["status"] not in {"failed", "cancelled", "recovery_required", "stale"}:
            raise IsolatedJobConflict("Only the latest failed clip in a paused Full run can be retried.")
        target_index = identities.index(identity)
        if target_index != max((index for index, key_identity in enumerate(identities) if key_identity in bound), default=-1):
            raise IsolatedJobConflict("Only the latest failed clip can be retried; later clips must not be rebound.")
        clip = plan[target_index]
        predecessor_id = target["predecessor_job_id"]
        is_scene_start = target_index == 0 or plan[target_index - 1]["scene_number"] != scene_number
        # A retry is a new job attempt for the exact request that failed. The
        # source request is immutable; later identity reviews must not silently
        # change its references between attempts.
        request = source.get("request")
        if not isinstance(request, Mapping) or request.get("workflow_id") != clip["workflow_id"]:
            raise IsolatedJobConflict("The failed clip's frozen request is unavailable or no longer matches its plan.")
        if clip["workflow_id"] == T2V_WORKFLOW_ID:
            if request.get("prompt") != clip["prompt"] or request.get("duration_seconds") != clip["duration_seconds"]:
                raise IsolatedJobConflict("The failed clip's frozen T2V request differs from its plan.")
        elif not is_scene_start:
            prior = self.get_job(predecessor_id) if predecessor_id else None
            output = next((asset for asset in (prior or {}).get("outputs", [])
                if asset.get("shared_asset_id") and asset.get("kind") == "video" and asset.get("has_video")), None)
            if not output or prior["status"] not in {"needs_review", "accepted"}:
                raise IsolatedJobConflict("The previous same-scene clip is unavailable as the retry continuity reference.")
            # Also ensure the exact frozen request remains bound to this retry.
            continuity = next((item for item in request.get("images", [])
                if item.get("role") == "continuity"), None)
            expected_frame = last_frame(self.media_root, workspace, output, create=False)
            if not continuity or (continuity.get("asset_id"), continuity.get("sha256")) != (
                    expected_frame["asset_id"], expected_frame["sha256"]):
                raise IsolatedJobConflict("The failed clip's frozen continuity reference no longer matches its predecessor.")
        ready = readiness(clip["workflow_id"]) if callable(readiness) else readiness
        if not ready or not ready.get("available"):
            raise IsolatedVideoContractError("workflow_not_ready", (ready or {}).get("reason") or "Retry workflow readiness is unavailable.")
        with self.ledger._connect() as db:
            attempts = db.execute("SELECT COALESCE(MAX(attempt_number),0) FROM fully_automated_run_attempts WHERE workspace_id=? AND screenplay_revision_id=? AND scene_number=? AND shot_number=? AND clip_number=?",
                (workspace, revision_id, scene_number, shot_number, clip_number)).fetchone()[0]
        attempt_number = max(2, int(attempts) + 1)
        draft = manifest["drafts"].get(f"{scene_number}.{shot_number}")
        lineage = {"screenplay_revision_id": revision_id, "setup_hash": manifest["setup_hash"],
            "scene_number": scene_number, "shot_number": shot_number,
            "source_prompt_sha256": hashlib.sha256(draft["prompt"].encode()).hexdigest(),
            **_draft_knowledge_lineage(draft)}
        job = self.create_job(workspace_id=workspace, clip_id=clip["clip_id"], idempotency_key=key,
            request=request, source_lineage=lineage,
            _full_run_clip=(workspace, revision_id, scene_number, shot_number, clip_number, predecessor_id),
            _full_run_continuation=True,
            _full_run_retry=(workspace, revision_id, scene_number, shot_number, clip_number,
                source_job_id, attempt_number, predecessor_id))
        return {"status": "queued", "job": job, "run": self._fully_automated_run_result(workspace, revision_id)}

    @staticmethod
    def _quality_preset(quality):
        from story_builder.services.production_setup import QUALITY
        return QUALITY[quality]

    def _preceding_character_crops(self, predecessor, revision_id, clip):
        if not predecessor or not clip or self.media_root is None:
            return []
        from story_builder.services.media_library import asset_path
        with self.ledger._connect() as db:
            if not self._table_exists(db, "fully_automated_identity_reviews"):
                return []
            revision = db.execute("SELECT screenplay_json FROM story_screenplay_revisions WHERE workspace_id=? AND screenplay_revision_id=?",
                (predecessor["workspace_id"], revision_id)).fetchone()
            review = db.execute("SELECT input_json,result_json FROM fully_automated_identity_reviews WHERE source_job_id=? AND state='complete'",
                (predecessor["job_id"],)).fetchone()
        if not revision or not review:
            return []
        screenplay = json.loads(revision["screenplay_json"])
        shot = next((shot for scene in screenplay.get("scenes", []) if scene.get("scene_number") == clip.get("scene_number")
            for shot in scene.get("shots", []) if shot.get("shot_number") == clip.get("shot_number")), {})
        cited = set(shot.get("character_record_ids", []))
        names = {row["character_id"]:row["name"] for row in json.loads(review["input_json"]).get("characters", [])}
        refs = []
        for ref in json.loads(review["result_json"]).get("derived_references", []):
            if ref.get("frame_kind") != "last" or ref.get("character_id") not in cited:
                continue
            try:
                path, media_type, _ = asset_path(self.media_root, predecessor["workspace_id"], ref["asset_id"])
                if not media_type.startswith("image/") or _file_sha256(Path(path)) != ref["sha256"]:
                    continue
            except (OSError, ValueError, KeyError):
                continue
            refs.append({"asset_id":ref["asset_id"], "sha256":ref["sha256"], "role":"character_identity",
                "intent":f"Character {names.get(ref['character_id'], ref['character_id'])}; preserve the visible identity in this last-frame crop."})
        return refs[:8]

    def continuity_frame(self, job_id):
        job = self.get_job(job_id)
        if job["status"] not in {"accepted", "needs_review"}:
            raise IsolatedJobConflict("The preceding clip must finish before preparing continuity.")
        output = next((row for row in job.get("outputs", [])
            if row.get("kind") == "video" and row.get("shared_asset_id")), None)
        if not output:
            raise IsolatedJobConflict("The preceding clip has no usable video output.")
        frame = last_frame(self.media_root, job["workspace_id"], output)
        with self.ledger._connect() as db:
            if self._table_exists(db, "fully_automated_identity_reviews"):
                row = db.execute("SELECT result_json FROM fully_automated_identity_reviews WHERE source_job_id=? AND state='complete'", (job_id,)).fetchone()
                frame["character_crops"] = [ref for ref in json.loads(row["result_json"]).get("derived_references", []) if ref.get("frame_kind") == "last"] if row else []
        return frame

    def control_fully_automated_run(self, workspace_id, revision_id, action):
        """Persist owner intent before touching a remote render. Refresh is read only."""
        workspace = _identifier(workspace_id, "workspace_id")
        revision = _identifier(revision_id, "screenplay_revision_id")
        if action not in {"pause", "resume", "stop"}:
            raise ValueError("Choose pause, resume or stop.")
        with self.ledger._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            run = db.execute("SELECT run_state FROM fully_automated_runs WHERE workspace_id=? AND screenplay_revision_id=?", (workspace, revision)).fetchone()
            if not run:
                raise IsolatedJobConflict("No saved run exists.")
            state = run["run_state"]
            if action == "resume" and state != "owner_paused":
                raise IsolatedJobConflict("Only an owner-paused run can resume with this control.")
            if action == "pause" and state not in {"running", "waiting_for_readiness", "owner_paused"}:
                raise IsolatedJobConflict("This run cannot be paused.")
            if action == "stop" and state == "completed":
                raise IsolatedJobConflict("The run has already completed.")
            target = {"pause": "owner_paused", "resume": "running", "stop": "stopped"}[action]
            message = {"pause": "Paused by you. The current clip may finish; no next clip will start.", "resume": None,
                "stop": "Stopped by you. No further clips will start."}[action]
            db.execute("UPDATE fully_automated_runs SET run_state=?,error_message=?,updated_at=CURRENT_TIMESTAMP WHERE workspace_id=? AND screenplay_revision_id=?", (target, message, workspace, revision))
            rows = db.execute("SELECT t.* FROM production_takes t WHERE t.job_id IN (SELECT job_id FROM fully_automated_run_attempts WHERE workspace_id=? AND screenplay_revision_id=? UNION SELECT job_id FROM fully_automated_run_clips WHERE workspace_id=? AND screenplay_revision_id=?)", (workspace, revision, workspace, revision)).fetchall()
        if action == "stop":
            from story_builder.services.gpu_runtime import interrupt_if_owned_prompt
            from story_builder.services.production_job_worker import _request_json
            for original in rows:
                for attempt in range(2):
                    with self.ledger._connect() as db:
                        row = db.execute("SELECT * FROM production_takes WHERE job_id=?", (original["job_id"],)).fetchone()
                    status = row["status"]
                    next_state = ("cancelled" if status in {"draft", "validated", "queued", "refinement_pending", "waiting_for_user", "waiting_for_predecessor"}
                        else "cancel_requested" if status in {"submitting", "running", "collecting", "recovery_required"} else None)
                    if not next_state:
                        break
                    try:
                        self.ledger.transition_take(project_id=row["project_id"], take_id=row["take_id"], status=next_state, payload={"reason": "owner_stopped_run"})
                        break
                    except LedgerConflict:
                        if attempt:
                            raise IsolatedJobConflict("Run stopped, but the active take changed during cancellation. Refresh and Stop again.")
                if row["prompt_id"] and status in {"submitting", "running", "collecting", "recovery_required", "cancel_requested"}:
                    ok, detail = interrupt_if_owned_prompt(comfy_url=os.environ.get("COMFYUI_URL", "http://127.0.0.1:3008"), prompt_id=row["prompt_id"], request_json=_request_json)
                    if not ok:
                        with self.ledger._connect() as db:
                            db.execute("UPDATE fully_automated_runs SET error_message=? WHERE workspace_id=? AND screenplay_revision_id=?", (message + " " + detail, workspace, revision))
        return self.get_fully_automated_first_clip(workspace, revision)

    def _set_full_run_state(self, workspace, revision, state, error):
        with self.ledger._connect() as db:
            db.execute("UPDATE fully_automated_runs SET run_state=?,error_message=?,updated_at=CURRENT_TIMESTAMP WHERE workspace_id=? AND screenplay_revision_id=? AND run_state NOT IN ('owner_paused','stopped')",
                (state, error, workspace, revision))

    @staticmethod
    def _first_clip_result(job):
        lineage = job.get("source_lineage") or {}
        revision_id = lineage.get("screenplay_revision_id")
        return {"run_state": "first_clip_queued", "workspace_id": job["workspace_id"],
            "screenplay_revision_id": revision_id,
            "setup_hash": lineage.get("setup_hash"), "prompt_sha256": lineage.get("source_prompt_sha256"),
            "scene_number": lineage.get("scene_number"), "shot_number": lineage.get("shot_number"),
            "clip_id": job["clip_id"], "idempotency_key": job["idempotency_key"],
            "request": job.get("request"), "source_lineage": lineage, "job": job}

    def create_job(self, *, workspace_id: str, clip_id: str, idempotency_key: str,
                   request: Mapping[str, Any], retake_of_job_id: str | None = None,
                   keep_original: bool | None = None,
                   source_lineage: Mapping[str, Any] | None = None,
                   _frozen_source_lineage: Mapping[str, Any] | None = None,
                   _full_run_binding: tuple[str, str] | None = None,
                   _full_run_manifest: Mapping[str, Any] | None = None,
                   _full_run_clip: tuple | None = None,
                   _assisted_run_clip: tuple | None = None,
                   _full_run_continuation: bool = False,
                   _full_run_retry: tuple[str, str, int, int, str, int, str | None] | None = None,
                   _assisted_run_retry: tuple[str, str, str, str, str | None] | None = None) -> dict[str, Any]:
        workspace = _identifier(workspace_id, "workspace_id")
        clip = _identifier(clip_id, "clip_id")
        key = _identifier(idempotency_key, "idempotency_key")
        if isinstance(request, Mapping) and request.get("workflow_id") == T2V_WORKFLOW_ID and request.get("workflow_version") != T2V_WORKFLOW_VERSION:
            raise IsolatedVideoContractError("workflow_version_retired", "New T2V jobs require Turbo + LTX. Reload the draft or restart from the saved screenplay; existing job recovery remains available.")
        if isinstance(request, Mapping) and request.get("workflow_id") in {FL2VA_WORKFLOW_ID, R2V_WORKFLOW_ID} and request.get("workflow_version") != 2:
            raise IsolatedVideoContractError("workflow_version_retired", "New guided jobs require Turbo + LTX. Reload the draft; existing job recovery remains available.")
        normalized = _normalize_workflow_request(request, self.graph_path, self.fl2va_graph_path, self.r2v_graph_path)
        if (_full_run_binding is not None or _full_run_continuation or _full_run_retry is not None) and normalized["workflow_id"] != T2V_WORKFLOW_ID:
            raise StoryHandoffRejected("This saved Full run uses the previous reference policy. Stop it and start a new text-to-video run from the saved screenplay.")
        if normalized["workflow_id"] == FL2VA_WORKFLOW_ID:
            capability = self.fl2va_capability_provider()
            if not capability.get("available"):
                raise IsolatedVideoContractError("workflow_not_ready",
                    capability.get("disabled_reason") or "FL2VA readiness checks have not passed.")
        elif normalized["workflow_id"] == R2V_WORKFLOW_ID:
            # Admission must prove the same reference tags and non-empty route
            # that preview compilation validates before creating durable state.
            _compile_workflow_preview(normalized, self.graph_path,
                self.fl2va_graph_path, self.r2v_graph_path)
            capability = self.r2v_capability_provider()
            automated = _assisted_run_clip is not None
            ready = (capability.get("automation_available", capability.get("available"))
                if automated else capability.get("available"))
            if not ready:
                reason = capability.get("automation_disabled_reason") if automated else None
                raise IsolatedVideoContractError("workflow_not_ready",
                    reason or capability.get("disabled_reason") or "R2V readiness checks have not passed.")
        request_hash = _canonical_workflow_hash(normalized)
        if source_lineage is not None and _frozen_source_lineage is not None:
            raise ValueError("Supply source_lineage only for a new handoff.")
        if (_full_run_manifest is not None and _full_run_binding is None) or (_full_run_clip is not None and _full_run_manifest is None and _full_run_binding is not None):
            raise ValueError("Fully automated run binding metadata is incomplete.")
        if _full_run_continuation and (_full_run_binding is not None or _full_run_manifest is not None or _full_run_clip is None):
            raise ValueError("Automated continuation must bind one run clip only.")
        if _full_run_retry is not None and (not _full_run_continuation or _full_run_clip is None):
            raise ValueError("Automated retry must bind one continuation run clip.")
        if _assisted_run_clip is not None and (not isinstance(_assisted_run_clip, tuple)
                or len(_assisted_run_clip) != 4 or retake_of_job_id is not None
                or _full_run_binding is not None or _full_run_clip is not None):
            raise ValueError("Assisted run binding metadata is malformed or conflicts with another automation mode.")
        if _assisted_run_retry is not None and (_assisted_run_clip is None
                or not isinstance(_assisted_run_retry, tuple) or len(_assisted_run_retry) != 5):
            raise ValueError("Assisted retry must bind one existing Assisted run clip.")
        if _full_run_binding is not None:
            if (not isinstance(_full_run_binding, tuple) or len(_full_run_binding) != 2
                    or _full_run_binding != (workspace, (source_lineage or {}).get("screenplay_revision_id") if isinstance(source_lineage, Mapping) else None)
                    or retake_of_job_id is not None):
                raise ValueError("Automated first-clip binding must match a new linked screenplay job.")
        source_take = source_meta = None
        if retake_of_job_id is not None:
            if type(keep_original) is not bool:
                raise ValueError("A retake requires an explicit keep_original boolean.")
            source_take, source_meta = self._take_and_meta(retake_of_job_id)
            if source_meta["workspace_id"] != workspace or source_meta["clip_id"] != clip:
                raise IsolatedJobConflict("Retake source belongs to a different workspace or clip.")
            if source_take["status"] not in {"needs_review", "accepted", "failed", "cancelled", "stale"}:
                raise IsolatedJobConflict("Retake source is not settled or reviewable.")
        workspace_run_key = f"isolated-workspace:{workspace}"
        # A workspace may contain different isolated workflows. Keep the run
        # envelope workflow-neutral; the immutable take snapshot owns the
        # selected workflow and graph digest. Reuse historical isolated runs
        # whose config recorded the first workflow so upgrades stay replayable.
        with self.ledger._connect() as db:
            prior_run = db.execute(
                "SELECT run_id,config_json FROM production_runs WHERE project_id=? AND idempotency_key=?",
                (workspace, workspace_run_key)).fetchone()
        if prior_run is not None and json.loads(prior_run["config_json"]).get("entry") == "isolated":
            run = {"run_id": prior_run["run_id"]}
        else:
            run = self.ledger.create_run(project_id=workspace, idempotency_key=workspace_run_key,
                config={"control_mode": "manual", "entry": "isolated", "director_gates": "disabled"})
        internal_key = f"isolated:{key}"
        take_id = str(uuid.uuid5(_WORKSPACE_NS, f"{workspace}\0{key}"))
        retake_of = None if source_meta is None else retake_of_job_id
        attempt = 1 if source_meta is None else int(source_meta["attempt"]) + 1
        keep = None if keep_original is None else int(keep_original)

        def store_metadata(db, durable_take):
            if _full_run_binding is not None:
                run_workspace, run_revision = _full_run_binding
                frozen = dict(_full_run_manifest or {})
                revision_row = db.execute("SELECT * FROM story_screenplay_revisions WHERE workspace_id=? AND screenplay_revision_id=?",
                    (run_workspace, run_revision)).fetchone()
                if (revision_row is None or self.story is None
                        or not self.story._screenplay_is_currently_accepted(db, revision_row)):
                    raise StoryHandoffRejected("The accepted screenplay changed before the Full run could be admitted.")
                current_screenplay = json.loads(revision_row["screenplay_json"])
                screenplay_hash = hashlib.sha256(json.dumps(current_screenplay, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()
                setup_row = db.execute("SELECT setup_json FROM story_production_setups WHERE workspace_id=? AND screenplay_revision_id=?",
                    (run_workspace, run_revision)).fetchone()
                draft_row = db.execute("SELECT setup_hash,drafts_json FROM story_prompt_drafts WHERE workspace_id=? AND screenplay_revision_id=?",
                    (run_workspace, run_revision)).fetchone()
                current_setup = None if setup_row is None else json.loads(setup_row["setup_json"])
                if current_setup is not None:
                    from story_builder.services.production_setup import ProductionSetup
                    current_setup = ProductionSetup.validate(current_setup)
                current_drafts = None if draft_row is None else json.loads(draft_row["drafts_json"])
                current_setup_hash = hashlib.sha256(json.dumps(current_setup, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest() if current_setup is not None else None
                current_drafts_hash = hashlib.sha256(json.dumps(current_drafts, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest() if current_drafts is not None else None
                if (screenplay_hash != frozen.get("screenplay_sha256")
                        or current_setup_hash != frozen.get("setup_hash")
                        or draft_row is None or draft_row["setup_hash"] != frozen.get("setup_hash")
                        or current_drafts_hash != frozen.get("drafts_sha256")):
                    raise StoryHandoffRejected("Screenplay, setup, or saved prompts changed during Full-run admission. Reload and save again.")
                if frozen.get("manifest_version") in {2, 3}:
                    clip_plan_hash = hashlib.sha256(json.dumps(frozen.get("clip_plan"), sort_keys=True,
                        ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()
                    if frozen.get("reviewed_input_hash"):
                        reviewed = db.execute("SELECT input_hash,plan_json FROM assisted_video_clip_plans WHERE workspace_id=? AND screenplay_revision_id=?", (run_workspace, run_revision)).fetchone()
                        reviewed_hash = hashlib.sha256(json.dumps({"clips": json.loads(reviewed["plan_json"])}, sort_keys=True,
                            ensure_ascii=False, separators=(",", ":")).encode()).hexdigest() if reviewed else None
                        if not reviewed or reviewed["input_hash"] != frozen["reviewed_input_hash"] or reviewed_hash != clip_plan_hash:
                            raise StoryHandoffRejected("Reviewed clip prompts changed before admission. Reload and start again.")
                    if clip_plan_hash != frozen.get("clip_plan_sha256"):
                        raise StoryHandoffRejected("The generated clip plan changed before Full-run admission.")
            if _full_run_binding is not None:
                binding = db.execute("SELECT job_id FROM fully_automated_first_clip_bindings WHERE workspace_id=? AND screenplay_revision_id=?",
                    _full_run_binding).fetchone()
                if binding is not None and binding["job_id"] != durable_take["job_id"]:
                    raise StoryHandoffRejected("A first clip is already bound to this screenplay revision; recover its frozen job.")
            saved = db.execute("SELECT * FROM isolated_video_jobs WHERE job_id=? OR (workspace_id=? AND idempotency_key=?)",
                (durable_take["job_id"], workspace, key)).fetchone()
            if _full_run_clip is not None:
                if len(_full_run_clip) == 5:
                    run_workspace, run_revision, run_scene, run_shot, predecessor = _full_run_clip
                    run_clip_number = 1
                elif len(_full_run_clip) == 6:
                    run_workspace, run_revision, run_scene, run_shot, run_clip_number, predecessor = _full_run_clip
                else:
                    raise ValueError("Full-run clip identity is malformed.")
                owner_state = db.execute("SELECT run_state FROM fully_automated_runs WHERE workspace_id=? AND screenplay_revision_id=?", (run_workspace, run_revision)).fetchone()
                if owner_state and owner_state["run_state"] in {"owner_paused", "stopped"}:
                    raise StoryHandoffRejected("The owner paused or stopped this run before admission.")
                existing_clip = db.execute("SELECT job_id,predecessor_job_id FROM fully_automated_run_clips WHERE workspace_id=? AND screenplay_revision_id=? AND scene_number=? AND shot_number=? AND clip_number=?",
                    (run_workspace, run_revision, run_scene, run_shot, run_clip_number)).fetchone()
                if _full_run_retry is not None and saved is None:
                    if len(_full_run_retry) == 7:
                        retry_workspace, retry_revision, retry_scene, retry_shot, failed_job_id, attempt_number, retry_predecessor = _full_run_retry
                        retry_clip_number = 1
                    elif len(_full_run_retry) == 8:
                        retry_workspace, retry_revision, retry_scene, retry_shot, retry_clip_number, failed_job_id, attempt_number, retry_predecessor = _full_run_retry
                    else:
                        raise ValueError("Full-run retry identity is malformed.")
                    run = db.execute("SELECT run_state FROM fully_automated_runs WHERE workspace_id=? AND screenplay_revision_id=?",
                        (retry_workspace, retry_revision)).fetchone()
                    source = db.execute("SELECT status FROM production_takes WHERE job_id=?", (failed_job_id,)).fetchone()
                    attempts = db.execute("SELECT COALESCE(MAX(attempt_number),0) FROM fully_automated_run_attempts WHERE workspace_id=? AND screenplay_revision_id=? AND scene_number=? AND shot_number=? AND clip_number=?",
                        (retry_workspace, retry_revision, retry_scene, retry_shot, retry_clip_number)).fetchone()[0]
                    allowed_failure = db.execute("SELECT status FROM production_takes WHERE job_id=?", (failed_job_id,)).fetchone()
                    if (run is None or run["run_state"] != "paused" or existing_clip is None
                            or existing_clip["job_id"] != failed_job_id
                            or existing_clip["predecessor_job_id"] != retry_predecessor
                            or (retry_workspace, retry_revision, retry_scene, retry_shot, retry_clip_number) != (run_workspace, run_revision, run_scene, run_shot, run_clip_number)
                            or source is None or allowed_failure is None
                            or allowed_failure["status"] not in {"failed", "cancelled", "stale", "recovery_required"}
                            or attempt_number != max(2, attempts + 1)):
                        raise StoryHandoffRejected("The paused shot changed before its retry could be admitted; reload the run.")
                elif _full_run_retry is None and existing_clip is not None and (existing_clip["job_id"] != durable_take["job_id"] or existing_clip["predecessor_job_id"] != predecessor):
                    raise StoryHandoffRejected("This Fully automated shot is already bound to a different frozen job.")
            if saved is None:
                if source_meta is not None:
                    original = db.execute("SELECT source_lineage_json FROM isolated_video_jobs WHERE job_id=?",
                        (retake_of_job_id,)).fetchone()
                    frozen = None if original is None else json.loads(original["source_lineage_json"] or "null")
                    if _frozen_source_lineage is not None and frozen != dict(_frozen_source_lineage):
                        raise IsolatedJobConflict("Retake source lineage does not match its frozen source job.")
                    if source_lineage is not None:
                        if frozen is None or _lineage_identity(source_lineage) != _lineage_identity({key: frozen[key] for key in _SOURCE_LINEAGE_FIELDS | _OPTIONAL_SOURCE_LINEAGE_FIELDS if key in frozen}):
                            raise StoryHandoffRejected("Retake cannot replace or drop its frozen story lineage.")
                    elif frozen is not None and _frozen_source_lineage is None:
                        raise StoryHandoffRejected("Retake must preserve its frozen story lineage.")
                    lineage = frozen
                else:
                    if _frozen_source_lineage is not None:
                        raise IsolatedJobConflict("Retake source job is missing.")
                    if _full_run_binding is not None:
                        lineage = _lineage_identity(source_lineage)
                        manifest = dict(_full_run_manifest or {})
                        _, _, run_scene, run_shot, run_clip_number, _ = _full_run_clip
                        plan = manifest.get("clip_plan", {}).get("clips", [])
                        frozen_clip = next((item for item in plan if
                            (item["scene_number"], item["shot_number"], item["clip_number"])
                            == (run_scene, run_shot, run_clip_number)), None)
                        plan_hash = hashlib.sha256(json.dumps(manifest.get("clip_plan"), sort_keys=True,
                            ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
                        if (not frozen_clip or manifest.get("clip_plan_sha256") != plan_hash
                                or clip != frozen_clip["clip_id"]
                                or normalized.get("workflow_id") != frozen_clip["workflow_id"]
                                or normalized.get("duration_seconds") != frozen_clip["duration_seconds"]):
                            raise StoryHandoffRejected("First Full-mode take does not match the frozen clip plan.")
                        prompt_matches = (normalized.get("prompt") == frozen_clip["prompt"]
                            if frozen_clip["workflow_id"] == T2V_WORKFLOW_ID else
                            normalized.get("prompt", "").endswith("\n\n" + frozen_clip["prompt"]))
                        if not prompt_matches:
                            raise StoryHandoffRejected("First Full-mode prompt differs from the frozen clip plan.")
                        self._validate_v2_full_request(db, manifest, frozen_clip, normalized,
                            _full_run_binding, _full_run_clip[-1])
                        draft = manifest["drafts"].get(f"{run_scene}.{run_shot}")
                        if (lineage["screenplay_revision_id"] != _full_run_binding[1]
                                or lineage["setup_hash"] != manifest.get("setup_hash")
                                or draft and draft.get("knowledge_ref") != lineage.get("knowledge_ref")
                                or not draft or hashlib.sha256(draft["prompt"].encode()).hexdigest()
                                    != lineage["source_prompt_sha256"]):
                            raise StoryHandoffRejected("First Full-mode take has stale source lineage.")
                        lineage = {**lineage, "workflow_id": frozen_clip["workflow_id"]}
                    elif _full_run_continuation:
                        lineage = _lineage_identity(source_lineage)
                        run = db.execute("SELECT manifest_json FROM fully_automated_runs WHERE workspace_id=? AND screenplay_revision_id=?",
                            (workspace, lineage["screenplay_revision_id"])).fetchone()
                        if run is None:
                            raise StoryHandoffRejected("The frozen Fully automated run manifest is missing.")
                        manifest = json.loads(run["manifest_json"])
                        draft = manifest["drafts"].get(f"{lineage['scene_number']}.{lineage['shot_number']}")
                        if (manifest.get("setup_hash") != lineage["setup_hash"] or not draft
                                or hashlib.sha256(draft["prompt"].encode()).hexdigest() != lineage["source_prompt_sha256"]
                                or draft.get("knowledge_ref") != lineage.get("knowledge_ref")
                                or (manifest.get("manifest_version") not in {2, 3}
                                    and draft.get("workflow_id") != normalized.get("workflow_id"))):
                            raise StoryHandoffRejected("The continuation does not match the frozen Fully automated manifest.")
                        if manifest.get("manifest_version") in {2, 3}:
                            clip_identity = (run_scene, run_shot, run_clip_number)
                            plan = manifest.get("clip_plan", {}).get("clips", [])
                            frozen_clip = next((item for item in plan if
                                (item["scene_number"], item["shot_number"], item["clip_number"]) == clip_identity), None)
                            expected_hash = hashlib.sha256(json.dumps(manifest.get("clip_plan"), sort_keys=True,
                                ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
                            if (not frozen_clip or manifest.get("clip_plan_sha256") != expected_hash
                                    or clip != frozen_clip["clip_id"]
                                    or normalized.get("workflow_id") != frozen_clip["workflow_id"]
                                    or normalized.get("duration_seconds") != frozen_clip["duration_seconds"]):
                                raise StoryHandoffRejected("Automated continuation does not match its frozen clip-plan identity, route, or duration.")
                            if frozen_clip["workflow_id"] == T2V_WORKFLOW_ID:
                                prompt_matches = normalized.get("prompt") == frozen_clip["prompt"]
                            else:
                                prompt_matches = normalized.get("prompt", "").endswith("\n\n" + frozen_clip["prompt"])
                            if not prompt_matches:
                                raise StoryHandoffRejected("Automated continuation prompt differs from the frozen clip plan.")
                            if _full_run_retry is not None:
                                retry_source_id = _full_run_retry[4] if len(_full_run_retry) == 7 else _full_run_retry[5]
                                source_request = db.execute("SELECT request_json FROM isolated_video_jobs WHERE job_id=? AND workspace_id=?",
                                    (retry_source_id, workspace)).fetchone()
                                frozen_request = json.loads(source_request["request_json"]) if source_request else None
                                if not isinstance(frozen_request, dict) or dict(normalized) != frozen_request:
                                    raise StoryHandoffRejected("Automated retry must reuse the failed job's exact frozen request.")
                            else:
                                self._validate_v2_full_request(db, manifest, frozen_clip, normalized,
                                    (workspace, lineage["screenplay_revision_id"]), _full_run_clip[-1])
                        else:
                            expected = story_clip_id(workspace, lineage["screenplay_revision_id"], lineage["scene_number"], lineage["shot_number"])
                            if clip != expected:
                                raise StoryHandoffRejected("Automated continuation clip identity does not match its screenplay shot.")
                        lineage = {**lineage, "workflow_id": draft["workflow_id"]}
                    elif _assisted_run_clip is not None:
                        lineage = _lineage_identity(source_lineage)
                        run_workspace, run_revision, run_clip_id, run_predecessor = _assisted_run_clip
                        run_row = db.execute("SELECT manifest_json,run_state FROM assisted_video_runs WHERE workspace_id=? AND screenplay_revision_id=?",
                            (run_workspace, run_revision)).fetchone()
                        allowed_run_states = {"running", "waiting_for_readiness"}
                        if _assisted_run_retry is not None:
                            allowed_run_states.add("paused")
                        if run_row is None or run_row["run_state"] not in allowed_run_states:
                            raise StoryHandoffRejected("The frozen Assisted run is unavailable or no longer active.")
                        manifest = json.loads(run_row["manifest_json"])
                        frozen_clip = next((item for item in manifest.get("clips", []) if item.get("clip_id") == run_clip_id), None)
                        revision_row = db.execute("SELECT * FROM story_screenplay_revisions WHERE workspace_id=? AND screenplay_revision_id=?",
                            (run_workspace, run_revision)).fetchone()
                        setup_row = db.execute("SELECT setup_json FROM story_production_setups WHERE workspace_id=? AND screenplay_revision_id=?",
                            (run_workspace, run_revision)).fetchone()
                        draft_row = db.execute("SELECT setup_hash,drafts_json FROM story_prompt_drafts WHERE workspace_id=? AND screenplay_revision_id=?",
                            (run_workspace, run_revision)).fetchone()
                        if (revision_row is None or self.story is None
                                or not self.story._screenplay_is_currently_accepted(db, revision_row)
                                or setup_row is None or draft_row is None):
                            raise StoryHandoffRejected("The accepted screenplay or its saved setup/prompts changed before Assisted job admission.")
                        from story_builder.services.production_setup import ProductionSetup
                        current_screenplay = json.loads(revision_row["screenplay_json"])
                        current_setup = ProductionSetup.validate(json.loads(setup_row["setup_json"]))
                        current_drafts = json.loads(draft_row["drafts_json"])
                        current_setup_hash = hashlib.sha256(json.dumps(current_setup, sort_keys=True,
                            separators=(",", ":")).encode()).hexdigest()
                        current_input_hash = hashlib.sha256(json.dumps({"screenplay": current_screenplay,
                            "setup": current_setup, "drafts": current_drafts}, sort_keys=True,
                            ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
                        current_clip_plan = db.execute("SELECT input_hash,plan_json FROM assisted_video_clip_plans WHERE workspace_id=? AND screenplay_revision_id=?",
                            (run_workspace, run_revision)).fetchone()
                        current_ref_rows = db.execute("SELECT clip_id,references_json FROM assisted_video_clip_references WHERE workspace_id=? AND screenplay_revision_id=?",
                            (run_workspace, run_revision)).fetchall()
                        current_refs = {row["clip_id"]: json.loads(row["references_json"]) for row in current_ref_rows}
                        current_clips = ([{**clip, "references": current_refs.get(clip["clip_id"])}
                            for clip in json.loads(current_clip_plan["plan_json"])] if current_clip_plan else [])
                        current_plan_hash = hashlib.sha256(json.dumps(current_clips, sort_keys=True,
                            ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
                        if (draft_row["setup_hash"] != current_setup_hash
                                or current_setup_hash != manifest.get("setup_hash")
                                or current_input_hash != manifest.get("input_hash")
                                or not current_clip_plan
                                or current_clip_plan["input_hash"] != manifest.get("input_hash")
                                or current_plan_hash != manifest.get("clip_plan_sha256")
                                or current_clips != manifest.get("clips")):
                            raise StoryHandoffRejected("The screenplay, setup, prompts, clip plan, or mapped references changed before Assisted job admission.")
                        frozen_clips = manifest.get("clips", [])
                        frozen_index = next((index for index, item in enumerate(frozen_clips)
                            if item.get("clip_id") == run_clip_id), -1)
                        if frozen_index < 0:
                            raise StoryHandoffRejected("The requested clip is not in the frozen Assisted plan.")
                        expected_predecessor = None
                        if frozen_index:
                            previous_id = frozen_clips[frozen_index - 1]["clip_id"]
                            previous_row = db.execute("SELECT job_id FROM assisted_video_run_clips WHERE workspace_id=? AND screenplay_revision_id=? AND clip_id=?",
                                (run_workspace, run_revision, previous_id)).fetchone()
                            if previous_row is None:
                                raise StoryHandoffRejected("The previous Assisted clip must be queued before this clip.")
                            expected_predecessor = previous_row["job_id"]
                        if expected_predecessor != run_predecessor:
                            raise StoryHandoffRejected("The Assisted clip predecessor does not match the frozen plan order.")
                        predecessor_job = self.get_job(expected_predecessor) if expected_predecessor else None
                        expected = self._assisted_request(manifest, frozen_clip, predecessor_job) if frozen_clip else None
                        expected = _normalize_workflow_request(expected, self.graph_path,
                            self.fl2va_graph_path, self.r2v_graph_path) if expected else None
                        if (not frozen_clip or clip != run_clip_id or dict(normalized) != dict(expected)
                                or lineage["screenplay_revision_id"] != run_revision
                                or lineage["setup_hash"] != manifest.get("setup_hash")
                                or lineage["scene_number"] != frozen_clip["scene_number"]
                                or lineage["shot_number"] != frozen_clip["shot_number"]
                                or lineage["source_prompt_sha256"] != hashlib.sha256(frozen_clip["prompt"].encode()).hexdigest()):
                            raise StoryHandoffRejected("The Assisted job differs from its frozen clip plan or mapped references.")
                        source_draft = manifest.get("drafts", {}).get(f"{lineage['scene_number']}.{lineage['shot_number']}")
                        if source_draft and source_draft.get("knowledge_ref"):
                            lineage["knowledge_ref"] = source_draft["knowledge_ref"]
                        if source_draft != current_drafts.get(f"{lineage['scene_number']}.{lineage['shot_number']}"):
                            raise StoryHandoffRejected("The frozen Assisted prompt source changed before job admission.")
                        lineage["workflow_id"] = frozen_clip["workflow_id"]
                    else:
                        lineage = (_validate_story_source_lineage(db, self.story, workspace, clip, normalized, source_lineage, self.media_root)
                            if source_lineage is not None else None)
                db.execute("INSERT INTO isolated_video_jobs(job_id,workspace_id,clip_id,idempotency_key,request_hash,request_json,retake_of_job_id,attempt,keep_original,source_lineage_json) VALUES(?,?,?,?,?,?,?,?,?,?)",
                    (durable_take["job_id"], workspace, clip, key, request_hash,
                     json.dumps(normalized, sort_keys=True, ensure_ascii=False), retake_of, attempt, keep,
                     json.dumps(lineage, sort_keys=True, separators=(",", ":")) if lineage is not None else None))
                if _full_run_binding is not None:
                    db.execute("INSERT INTO fully_automated_first_clip_bindings(workspace_id,screenplay_revision_id,job_id) VALUES(?,?,?)",
                        (*_full_run_binding, durable_take["job_id"]))
                    db.execute("INSERT INTO fully_automated_runs(workspace_id,screenplay_revision_id,manifest_json,run_state) VALUES(?,?,?,'running')",
                        (*_full_run_binding, json.dumps(_full_run_manifest, sort_keys=True, separators=(",", ":"))))
                if _full_run_clip is not None:
                    if _full_run_retry is not None:
                        db.execute("UPDATE fully_automated_run_clips SET job_id=?,clip_state='queued',created_at=CURRENT_TIMESTAMP WHERE workspace_id=? AND screenplay_revision_id=? AND scene_number=? AND shot_number=? AND clip_number=? AND job_id=?",
                            (durable_take["job_id"], run_workspace, run_revision, run_scene, run_shot, run_clip_number, failed_job_id))
                        db.execute("UPDATE fully_automated_runs SET run_state='running',error_message=NULL,updated_at=CURRENT_TIMESTAMP WHERE workspace_id=? AND screenplay_revision_id=?",
                            (retry_workspace, retry_revision))
                        db.execute("INSERT INTO fully_automated_run_attempts(job_id,workspace_id,screenplay_revision_id,scene_number,shot_number,clip_number,attempt_number,predecessor_job_id) VALUES(?,?,?,?,?,?,?,?)",
                            (durable_take["job_id"], retry_workspace, retry_revision, retry_scene, retry_shot, retry_clip_number, attempt_number, retry_predecessor))
                    else:
                        db.execute("INSERT OR IGNORE INTO fully_automated_run_clips(workspace_id,screenplay_revision_id,scene_number,shot_number,clip_number,job_id,predecessor_job_id,clip_state) VALUES(?,?,?,?,?,?,?,'queued')",
                            (run_workspace, run_revision, run_scene, run_shot, run_clip_number, durable_take["job_id"], predecessor))
                        db.execute("INSERT OR IGNORE INTO fully_automated_run_attempts(job_id,workspace_id,screenplay_revision_id,scene_number,shot_number,clip_number,attempt_number,predecessor_job_id) VALUES(?,?,?,?,?,?,1,?)",
                            (durable_take["job_id"], run_workspace, run_revision, run_scene, run_shot, run_clip_number, predecessor))
                if _assisted_run_clip is not None:
                    run_workspace, run_revision, run_clip_id, run_predecessor = _assisted_run_clip
                    existing_clip = db.execute("SELECT job_id,predecessor_job_id FROM assisted_video_run_clips WHERE workspace_id=? AND screenplay_revision_id=? AND clip_id=?",
                        (run_workspace, run_revision, run_clip_id)).fetchone()
                    if _assisted_run_retry is not None:
                        retry_workspace, retry_revision, retry_clip_id, failed_job_id, retry_predecessor = _assisted_run_retry
                        run_row = db.execute("SELECT manifest_json,run_state FROM assisted_video_runs WHERE workspace_id=? AND screenplay_revision_id=?",
                            (retry_workspace, retry_revision)).fetchone()
                        failed = db.execute("SELECT status FROM production_takes WHERE job_id=?", (failed_job_id,)).fetchone()
                        manifest = json.loads(run_row["manifest_json"]) if run_row else {}
                        frozen = manifest.get("clips", [])
                        frozen_index = next((i for i, item in enumerate(frozen)
                            if item.get("clip_id") == retry_clip_id), -1)
                        retry_rows = db.execute("SELECT clip_id FROM assisted_video_run_clips WHERE workspace_id=? AND screenplay_revision_id=?",
                            (retry_workspace, retry_revision)).fetchall()
                        bound_ids = {row["clip_id"] for row in retry_rows}
                        latest_index = max((i for i, item in enumerate(frozen)
                            if item.get("clip_id") in bound_ids), default=-1)
                        if ((retry_workspace, retry_revision, retry_clip_id, retry_predecessor) != (
                                run_workspace, run_revision, run_clip_id, run_predecessor)
                                or run_row is None or run_row["run_state"] != "paused"
                                or existing_clip is None or existing_clip["job_id"] != failed_job_id
                                or existing_clip["predecessor_job_id"] != retry_predecessor
                                or frozen_index != latest_index or failed is None
                                or failed["status"] not in {"failed", "cancelled", "stale", "recovery_required"}):
                            raise StoryHandoffRejected("The paused Assisted clip changed before retry admission; reload the run.")
                        updated = db.execute("UPDATE assisted_video_run_clips SET job_id=?,clip_state='queued',created_at=CURRENT_TIMESTAMP WHERE workspace_id=? AND screenplay_revision_id=? AND clip_id=? AND job_id=? AND predecessor_job_id IS ?",
                            (durable_take["job_id"], run_workspace, run_revision, run_clip_id,
                             failed_job_id, run_predecessor)).rowcount
                        if updated != 1:
                            raise StoryHandoffRejected("The failed Assisted clip binding changed before retry admission.")
                    else:
                        if existing_clip and (existing_clip["job_id"] != durable_take["job_id"]
                                or existing_clip["predecessor_job_id"] != run_predecessor):
                            raise StoryHandoffRejected("This Assisted clip is already bound to a different durable job.")
                        db.execute("INSERT OR IGNORE INTO assisted_video_run_clips(workspace_id,screenplay_revision_id,clip_id,job_id,predecessor_job_id,clip_state) VALUES(?,?,?,?,?,'queued')",
                            (run_workspace, run_revision, run_clip_id, durable_take["job_id"], run_predecessor))
                    db.execute("UPDATE assisted_video_runs SET run_state='running',error_message=NULL,updated_at=CURRENT_TIMESTAMP WHERE workspace_id=? AND screenplay_revision_id=?",
                        (run_workspace, run_revision))
                return
            if (saved["job_id"] != durable_take["job_id"] or saved["workspace_id"] != workspace
                    or saved["clip_id"] != clip or saved["request_hash"] != request_hash
                    or saved["idempotency_key"] != key or saved["retake_of_job_id"] != retake_of
                    or saved["keep_original"] != keep):
                raise IsolatedJobConflict("Idempotency key conflicts with the saved isolated job.")
            frozen_lineage = json.loads(saved["source_lineage_json"] or "null")
            if source_lineage is None and _frozen_source_lineage is None:
                supplied_matches = frozen_lineage is None
            elif _frozen_source_lineage is not None:
                supplied_matches = frozen_lineage == dict(_frozen_source_lineage)
            else:
                supplied_matches = frozen_lineage is not None and _lineage_identity({key: frozen_lineage[key] for key in _SOURCE_LINEAGE_FIELDS | _OPTIONAL_SOURCE_LINEAGE_FIELDS if key in frozen_lineage}) == _lineage_identity(source_lineage)
            if not supplied_matches:
                raise IsolatedJobConflict("Idempotency key conflicts with the saved story lineage.")
        if self.media_root is not None:
            # Preserve a retry's frozen destination, including pre-feature snapshots.
            with self.ledger._connect() as db:
                prior_output = db.execute("SELECT input_snapshot_json FROM production_takes WHERE project_id=? AND idempotency_key=?", (workspace, internal_key)).fetchone()
            if prior_output:
                saved_destination = json.loads(prior_output["input_snapshot_json"]).get("output_destination")
                if saved_destination: normalized["output_destination"] = saved_destination
            else:
                from story_builder.services.output_destinations import freeze
                normalized["output_destination"] = freeze(self.media_root, "video-generation", {"workspace_id": workspace})["output_destination"]
        try:
            take = self.ledger.queue_take(project_id=workspace, run_id=run["run_id"], shot_id=clip,
                take_id=take_id, idempotency_key=internal_key, input_snapshot=normalized,
                on_create=store_metadata)
        except LedgerConflict as exc:
            raise IsolatedJobConflict(str(exc)) from exc
        return self.get_job(take["job_id"])

    def get_job(self, job_id: str) -> dict[str, Any]:
        row = self._take_and_meta(job_id)
        return self._public_job(row[0], row[1]["workspace_id"], row[1]["clip_id"], row[1])

    def list_jobs(self, *, workspace_id: str, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        """List recent isolated takes for one workspace without exposing other projects."""
        workspace = _identifier(workspace_id, "workspace_id")
        bounded_limit = max(1, min(200, int(limit)))
        if type(offset) is not int or offset < 0:
            raise ValueError("offset must be a nonnegative integer.")
        with self.ledger._connect() as db:
            rows = db.execute(
                "SELECT t.*,m.workspace_id,m.clip_id,m.idempotency_key AS public_idempotency_key,"
                "m.request_json,m.attempt,m.retake_of_job_id,m.keep_original,m.request_hash,m.source_lineage_json,"
                "d.disposition AS candidate_disposition "
                "FROM production_takes t JOIN isolated_video_jobs m USING(job_id) "
                "LEFT JOIN isolated_video_retake_decisions d ON d.source_job_id=t.job_id "
                "WHERE m.workspace_id=? ORDER BY t.created_at DESC,t.take_id DESC LIMIT ? OFFSET ?",
                (workspace, bounded_limit, offset),
            ).fetchall()
        return [self._public_job(self.ledger._row(row), workspace, row["clip_id"], row) for row in rows]

    def get_by_idempotency_key(self, *, workspace_id: str, idempotency_key: str) -> dict[str, Any]:
        """Read-only recovery lookup used after a lost HTTP response."""
        workspace = _identifier(workspace_id, "workspace_id")
        key = _identifier(idempotency_key, "idempotency_key")
        with self.ledger._connect() as db:
            row = db.execute("SELECT * FROM production_takes WHERE project_id=? AND idempotency_key=?",
                (workspace, f"isolated:{key}")).fetchone()
        if not row:
            raise LedgerNotFound("No durable isolated job exists for this idempotency key.")
        take = self.ledger._row(row)
        with self.ledger._connect() as db:
            meta = db.execute("SELECT m.*,m.idempotency_key AS public_idempotency_key,d.disposition AS candidate_disposition FROM isolated_video_jobs m LEFT JOIN isolated_video_retake_decisions d ON d.source_job_id=m.job_id WHERE m.job_id=?", (take["job_id"],)).fetchone()
        if meta is None:
            # Metadata and the durable queued take are committed atomically by
            # queue_take(on_create); a GET never invents or repairs lineage.
            raise IsolatedJobConflict("Durable ledger job is missing isolated metadata; operator reconciliation is required.")
        return self._public_job(take, workspace, meta["clip_id"], meta)

    def events(self, job_id: str) -> list[dict[str, Any]]:
        take, meta = self._take_and_meta(job_id)
        run = self.ledger.get_run(project_id=meta["workspace_id"], run_id=take["run_id"])
        return [event for event in run["events"] if event.get("job_id") == job_id]

    def retake_draft(self, job_id: str, *, keep_original: bool) -> dict[str, Any]:
        """Persist the director's choice and return the editable snapshot; never queues a take."""
        if type(keep_original) is not bool:
            raise ValueError("keep_original must be an explicit boolean choice.")
        take, meta = self._take_and_meta(job_id)
        if take["status"] not in {"needs_review", "accepted", "failed", "cancelled", "stale"}:
            raise IsolatedJobConflict("Retake draft is unavailable until the source job has a settled or reviewable result.")
        disposition = "keep" if keep_original else "discard_requested"
        # Discard is a reversible library archive, never physical deletion.
        # Keep output bytes and any immutable references usable; hide an output
        # from normal search only when no other video job produced that same
        # shared-library asset.
        if keep_original and meta["candidate_disposition"] == "discard_requested":
            asset_cleanup = self._set_discarded_outputs_archived(job_id, meta["workspace_id"], archived=False)
        elif keep_original:
            asset_cleanup = "kept"
        else:
            asset_cleanup = self._set_discarded_outputs_archived(job_id, meta["workspace_id"], archived=True)
        with self.ledger._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("""INSERT INTO isolated_video_retake_decisions
                (source_job_id,workspace_id,disposition,actor,chosen_at)
                VALUES(?,?,?,'user',CURRENT_TIMESTAMP)
                ON CONFLICT(source_job_id) DO UPDATE SET
                    workspace_id=excluded.workspace_id,
                    disposition=excluded.disposition,
                    actor=excluded.actor,
                    chosen_at=CURRENT_TIMESTAMP""",
                (job_id, meta["workspace_id"], disposition))
        return {"source_job_id": job_id, "request": json.loads(meta["request_json"]),
                "source_lineage": json.loads(meta["source_lineage_json"] or "null"),
                "keep_original": keep_original, "submission_created": False,
                "candidate_disposition": disposition,
                "asset_cleanup": asset_cleanup}

    def _set_discarded_outputs_archived(self, job_id: str, workspace_id: str, *, archived: bool) -> str:
        with self.ledger._connect() as db:
            rows = db.execute(
                "SELECT asset_id,sha256,metadata_json FROM isolated_video_assets WHERE job_id=? AND workspace_id=?",
                (job_id, workspace_id)).fetchall()
        if not rows:
            return "none"
        if self.media_root is None:
            return "unavailable"
        with self.ledger._connect() as db:
            other_rows = db.execute(
                "SELECT a.sha256,a.metadata_json FROM isolated_video_asset_refs r "
                "JOIN isolated_video_assets a USING(asset_id) "
                "WHERE a.workspace_id=? AND r.job_id<>?",
                (workspace_id, job_id)).fetchall()
        other_shared_ids = set()
        for row in other_rows:
            try:
                metadata = json.loads(row["metadata_json"])
                shared_id = metadata.get("shared_asset_id")
            except (TypeError, json.JSONDecodeError):
                shared_id = None
            if type(shared_id) is str:
                other_shared_ids.add(shared_id)
            if row["sha256"]:
                other_shared_ids.add(f"sha256:{row['sha256']}")
        changed = 0
        retained = 0
        for row in rows:
            try:
                metadata = json.loads(row["metadata_json"])
            except (TypeError, json.JSONDecodeError) as exc:
                raise IsolatedJobConflict("The generated video asset record is unreadable; it was left unchanged.") from exc
            shared_id = metadata.get("shared_asset_id") if isinstance(metadata, dict) else None
            if type(shared_id) is not str:
                raise IsolatedJobConflict("The generated video has no shared-library identity; it was left unchanged.")
            if archived and (shared_id in other_shared_ids or f"sha256:{row['sha256']}" in other_shared_ids):
                retained += 1
                continue
            set_asset_archived(self.media_root, workspace_id, shared_id, archived=archived)
            changed += 1
        if archived and changed and retained:
            return "partially_archived"
        if archived and retained:
            return "retained_shared"
        if archived:
            return "archived_recoverable" if changed else "none"
        return "restored" if changed else "kept"

    def create_retake(self, job_id: str, *, idempotency_key: str,
                      keep_original: bool, overrides: Mapping[str, Any] | None = None) -> dict[str, Any]:
        if type(keep_original) is not bool:
            raise ValueError("keep_original must be an explicit boolean choice.")
        source_take, source_meta = self._take_and_meta(job_id)
        if source_take["status"] not in {"needs_review", "accepted", "failed", "cancelled", "stale"}:
            raise IsolatedJobConflict("Retake is unavailable until the source job has a settled or reviewable result.")
        saved = json.loads(source_meta["request_json"])
        changes = dict(overrides or {})
        if set(changes) - set(saved):
            raise IsolatedVideoContractError("unknown_fields", "Retake overrides contain unsupported request fields.")
        saved.update(changes)
        normalized = _normalize_workflow_request(saved, self.graph_path, self.fl2va_graph_path, self.r2v_graph_path)
        # Preserve all saved fields, including seed, unless caller explicitly changes them.
        workspace, clip = source_meta["workspace_id"], source_meta["clip_id"]
        return self.create_job(workspace_id=workspace, clip_id=clip,
            idempotency_key=idempotency_key, request=normalized, retake_of_job_id=job_id,
            keep_original=keep_original,
            _frozen_source_lineage=json.loads(source_meta["source_lineage_json"] or "null"))

    def accept_job(self, job_id: str, *, actor: str = "user") -> dict[str, Any]:
        take, meta = self._take_and_meta(job_id)
        result = self.ledger.accept_take(project_id=meta["workspace_id"], run_id=take["run_id"],
            take_id=take["take_id"], actor=actor)
        if result.get("accepted"):
            with self.ledger._connect() as db:
                if meta["keep_original"] == 0 and meta["retake_of_job_id"]:
                    db.execute("UPDATE isolated_video_assets SET retention_state='candidate_for_gc' WHERE job_id=?",
                               (meta["retake_of_job_id"],))
            return self.get_job(job_id)
        return result

    def _take_and_meta(self, job_id: str) -> tuple[dict[str, Any], Any]:
        with self.ledger._connect() as db:
            row = db.execute("SELECT t.*,m.workspace_id,m.clip_id,m.idempotency_key AS public_idempotency_key,m.request_json,m.attempt,m.retake_of_job_id,m.keep_original,m.request_hash,m.source_lineage_json,d.disposition AS candidate_disposition FROM production_takes t JOIN isolated_video_jobs m USING(job_id) LEFT JOIN isolated_video_retake_decisions d ON d.source_job_id=t.job_id WHERE t.job_id=?", (job_id,)).fetchone()
        if not row:
            raise LedgerNotFound("Isolated video job not found.")
        take = self.ledger._row(row)
        return take, row

    def _public_job(self, take: dict[str, Any], workspace_id: str, clip_id: str,
                    meta: Any | None = None, *, request_hash: str | None = None) -> dict[str, Any]:
        if meta is not None:
            request_hash = meta["request_hash"]
        error = take.get("error")
        if take["status"] == "failed" and isinstance(error, dict) and error.get("execution_interrupted"):
            # Reconciliation replaces the last error; retain the earlier durable safety cause.
            with self.ledger._connect() as db:
                rows = db.execute("SELECT payload_json FROM production_events WHERE project_id=? AND job_id=? "
                    "AND event_type='take_transition' ORDER BY created_at DESC", (workspace_id, take["job_id"])).fetchall()
            for row in rows:
                cause = json.loads(row["payload_json"])
                if cause.get("code") in {"gpu_limit_monitor_failed", "gpu_render_limit_reached", "gpu_monitor_failed"}:
                    reason = cause.get("message") or "GPU safety monitoring stopped this render."
                    error = {**error, "safety_cause": cause, "message": f"{reason} ComfyUI confirmed the render was interrupted; no completed video was produced. Let the GPU cool and check cooling before retrying."}
                    break
        outputs = []
        for item in take.get("output_hashes", []):
            if not isinstance(item, dict):
                continue
            asset_id = item.get("asset_id")
            output = {key: item[key] for key in ("asset_id", "shared_asset_id", "shared_asset_url", "kind", "sha256", "duration_seconds", "has_video", "has_audio") if key in item}
            available = None
            if self.media_root is not None and isinstance(asset_id, str):
                with self.ledger._connect() as db:
                    record = db.execute("SELECT metadata_json FROM isolated_video_assets WHERE asset_id=?", (asset_id,)).fetchone()
                available = False
                if record:
                    try:
                        metadata = json.loads(record["metadata_json"])
                        relative_path = metadata.get("relative_path") if isinstance(metadata, dict) else None
                        if isinstance(relative_path, str) and relative_path:
                            if metadata.get("shared_asset_id"):
                                from story_builder.services.media_library import asset_path
                                path, _, _ = asset_path(self.media_root, workspace_id, metadata["shared_asset_id"])
                            else:
                                path = (self.media_root / relative_path).resolve()
                                path.relative_to(self.media_root)
                            available = path.is_file() and not metadata.get("overwritten")
                    except (ValueError, OSError, TypeError):
                        available = False
                output["available"] = available
            if isinstance(asset_id, str) and available is not False:
                output["playback_url"] = f"/api/video/assets/{asset_id}"
            elif available is False:
                output.pop("shared_asset_url", None)
            outputs.append(output)
        return {"job_id": take["job_id"], "workspace_id": workspace_id, "clip_id": clip_id,
            "idempotency_key": None if meta is None else meta["public_idempotency_key"],
            "status": take["status"], "request_hash": request_hash,
            "pipeline": {"stage": take.get("pipeline", {}).get("stage", "turbo_original"), "original_ready": bool(take.get("pipeline", {}).get("original")), "original_prompt_id": take.get("pipeline", {}).get("original_prompt_id")},
            "request": take["input_snapshot"], "engine_prompt_id": take.get("prompt_id"),
            "outputs": outputs, "error": error,
            "created_at": take.get("created_at"), "updated_at": take.get("updated_at"),
            "retake_of_job_id": None if meta is None else meta["retake_of_job_id"],
            "attempt": 1 if meta is None else meta["attempt"],
            "keep_original": None if meta is None else (None if meta["keep_original"] is None else bool(meta["keep_original"])),
            "candidate_disposition": None if meta is None else meta["candidate_disposition"],
            "source_lineage": None if meta is None else json.loads(meta["source_lineage_json"] or "null")}


def _normalize_workflow_request(request: Mapping[str, Any], t2v_graph: Path,
                                fl2va_graph: Path, r2v_graph: Path = R2V_GRAPH_PATH) -> dict[str, Any]:
    if isinstance(request, Mapping) and request.get("workflow_id") == FL2VA_WORKFLOW_ID:
        try:
            return normalize_fl2va_request(request, graph_path=fl2va_graph)
        except FL2VAContractError as exc:
            raise IsolatedVideoContractError(exc.code, str(exc)) from exc
    if isinstance(request, Mapping) and request.get("workflow_id") == R2V_WORKFLOW_ID:
        try:
            return normalize_r2v_request(request, graph_path=r2v_graph)
        except R2VContractError as exc:
            raise IsolatedVideoContractError(exc.code, str(exc)) from exc
    return normalize_request(request, graph_path=t2v_graph)


def _compile_workflow_preview(request: Mapping[str, Any], t2v_graph: Path,
                              fl2va_graph: Path, r2v_graph: Path = R2V_GRAPH_PATH) -> dict[str, Any]:
    if request.get("workflow_id") == FL2VA_WORKFLOW_ID:
        try:
            return compile_fl2va_preview(request, graph_path=fl2va_graph)
        except FL2VAContractError as exc:
            raise IsolatedVideoContractError(exc.code, str(exc)) from exc
    if request.get("workflow_id") == R2V_WORKFLOW_ID:
        try:
            return compile_r2v_preview(request, graph_path=r2v_graph)
        except R2VContractError as exc:
            raise IsolatedVideoContractError(exc.code, str(exc)) from exc
    return compile_preview(request, graph_path=t2v_graph)


def _canonical_workflow_hash(normalized: Mapping[str, Any]) -> str:
    """Hash normalized workflow snapshots with the established T2V encoding."""
    encoded = json.dumps(normalized, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def prepare_isolated_take(take: dict[str, Any], *, graph_path: Path | None = None,
                          fl2va_graph_path: Path | None = None,
                          r2v_graph_path: Path | None = None,
                          media_root: Path | None = None,
                          comfy_input_root: Path | None = None,
                          fl2va_capability_provider=None, r2v_capability_provider=None,
                          r2v_owner_root: Path | None = None,
                          style_selection_resolver=None) -> PreparedTake:
    """Compile a submitted immutable request with stable isolated output prefix."""
    request = take.get("input_snapshot")
    if not isinstance(request, dict):
        raise ValueError("Durable isolated request snapshot is missing.")
    if take.get("input_hash") != stable_hash(request):
        raise IsolatedVideoContractError("snapshot_hash_mismatch", "Durable input snapshot does not match its ledger hash.")
    t2v_graph = Path(graph_path) if graph_path is not None else T2V_GRAPH_PATH
    fl_graph = Path(fl2va_graph_path) if fl2va_graph_path is not None else FL2VA_GRAPH_PATH
    r2v_graph = Path(r2v_graph_path) if r2v_graph_path is not None else R2V_GRAPH_PATH
    from story_builder.services.isolated_r2v_contract import request_graph_path as r2v_request_graph_path
    r2v_graph = r2v_request_graph_path(request, r2v_graph)
    preview = _compile_workflow_preview(request, t2v_graph, fl_graph, r2v_graph)
    clip = str(take["shot_id"])
    ledger_take = str(take["take_id"])
    safe = lambda value: re.sub(r"[^A-Za-z0-9_-]", "_", str(value))
    graph = preview["graph"]
    cleanup = lambda: None
    if request.get("workflow_id") == FL2VA_WORKFLOW_ID:
        checker = fl2va_capability_provider or fl2va_capability
        capability = checker()
        if not capability.get("available"):
            raise RuntimeError(capability.get("disabled_reason") or "FL2VA readiness checks have not passed.")
        if media_root is None or comfy_input_root is None:
            raise RuntimeError("FL2VA staging roots are not configured.")
        staged, cleanup = stage_fl2va_frames(media_root=Path(media_root),
            workspace_id=str(take["project_id"]), job_id=str(take["job_id"]),
            first_frame=request["first_frame"], last_frame=request["last_frame"],
            comfy_input_root=Path(comfy_input_root))
        loaders = sorted(((int(node_id), node) for node_id, node in graph.items()
            if isinstance(node, dict) and node.get("class_type") == "LoadImage"), key=lambda row: row[0])
        if len(loaders) != 2:
            cleanup()
            raise RuntimeError("Pinned FL2VA graph no longer has exactly two ordered image inputs.")
        loaders[0][1].setdefault("inputs", {})["image"] = staged["first_frame"]
        loaders[1][1].setdefault("inputs", {})["image"] = staged["last_frame"]
    elif request.get("workflow_id") == R2V_WORKFLOW_ID:
        checker = r2v_capability_provider or r2v_capability
        capability = checker()
        if not capability.get("available"):
            raise RuntimeError(capability.get("disabled_reason") or "R2V readiness checks have not passed.")
        if media_root is None or comfy_input_root is None or r2v_owner_root is None:
            raise RuntimeError("R2V staging roots are not configured.")
        try:
            assets = stage_r2v_references(media_root=Path(media_root),
                workspace_id=str(take["project_id"]), job_id=str(take["job_id"]),
                request=request, comfy_input_root=Path(comfy_input_root), owner_root=Path(r2v_owner_root),
                style_selection=(style_selection_resolver(str(take["project_id"]))
                    if callable(style_selection_resolver) else None))
            plan = plan_from_request(request, str(take["project_id"]), str(take["run_id"]), clip)
            compiled = compile_r2v_graph(plan, assets,
                base_graph=json.loads(Path(r2v_graph).read_text(encoding="utf-8")))
            graph = dict(compiled.graph)
        except Exception:
            try:
                cleanup_r2v_staging_job(job_id=str(take["job_id"]),
                    comfy_input_root=Path(comfy_input_root), owner_root=Path(r2v_owner_root))
            except Exception:
                # Cleanup can reject the same unsafe paths that caused staging
                # to fail. Preserve the original prepare error either way.
                pass
            raise
        cleanup = lambda: cleanup_r2v_staging_job(job_id=str(take["job_id"]),
            comfy_input_root=Path(comfy_input_root), owner_root=Path(r2v_owner_root))
    prefix = f"isolated/{safe(take['project_id'])}/{safe(clip)}/{safe(ledger_take)}"
    for node in graph.values():
        if isinstance(node, dict) and node.get("class_type") == "SaveVideo":
            node.setdefault("inputs", {})["filename_prefix"] = prefix
    return PreparedTake(graph=graph, cleanup=cleanup)


def build_worker(ledger: ProductionLedger, *, comfy_url: str,
                 collect: Callable[[dict[str, Any], dict[str, Any]], list[dict[str, Any]]],
                 graph_path: Path | None = None,
                 fl2va_graph_path: Path | None = None,
                 r2v_graph_path: Path | None = None,
                 media_root: Path | None = None,
                 comfy_input_root: Path | None = None,
                 fl2va_capability_provider=None, r2v_capability_provider=None,
                 r2v_owner_root: Path | None = None,
                 style_selection_resolver=None,
                 prepare_guard: Callable[[], None] | None = None,
                 workflow_prepare_guard: Callable[[str], None] | None = None,
                 **worker_options: Any) -> ProductionJobWorker:
    """Construct worker only when an operator explicitly starts it."""
    last_pipeline_stage = None
    def prepare(take):
        nonlocal last_pipeline_stage
        request = take.get("input_snapshot") or {}
        workflow_id = request.get("workflow_id", "minimax_h3_t2v_local_v1")
        if prepare_guard is not None and workflow_id == "minimax_h3_t2v_local_v1":
            prepare_guard()
        if workflow_prepare_guard is not None:
            workflow_prepare_guard(workflow_id)
        from story_builder.services.t2v_pipeline import is_pipeline, prepare_refinement
        pipeline_stage = ("ltx_refinement" if take.get("pipeline", {}).get("stage") == "ltx_refinement"
                          else "turbo_original") if is_pipeline(take) else None
        pipeline_key = pipeline_stage
        if pipeline_stage is not None and pipeline_key != last_pipeline_stage:
            from story_builder.services.media_jobs import release_comfyui_models_if_idle
            def still_owned():
                with ledger._connect() as db:
                    current = db.execute("SELECT status FROM production_takes WHERE job_id=?",
                                         (take["job_id"],)).fetchone()
                return bool(current and current["status"] not in {"cancel_requested", "cancelled"})
            released = release_comfyui_models_if_idle(comfy_url=comfy_url,
                wait_for_memory_release=True, keep_waiting=still_owned)
            journal = worker_options.get("performance_journal")
            if journal is not None and "elapsed_seconds" in released:
                journal.measure(take, "model_unload_observation", released["elapsed_seconds"],
                                released["status"])
            if not released.get("memory_release_observed"):
                from story_builder.services.media_jobs import ComfyMemoryReleasePending
                raise ComfyMemoryReleasePending(f"ComfyUI memory handoff waiting before {pipeline_stage}: {released}")
            last_pipeline_stage = pipeline_key
        if is_pipeline(take) and take.get("pipeline", {}).get("stage") == "ltx_refinement":
            if media_root is None or comfy_input_root is None:
                raise RuntimeError("Turbo/LTX staging roots are not configured.")
            graph, stage_cleanup = prepare_refinement(take, data_root=media_root, input_root=comfy_input_root,
                                                      save_plan=ledger.save_ltx_chunk_plan)
            return PreparedTake(graph=graph, cleanup=stage_cleanup)
        last_pipeline_stage = pipeline_key
        return prepare_isolated_take(take, graph_path=graph_path,
            fl2va_graph_path=fl2va_graph_path, r2v_graph_path=r2v_graph_path, media_root=media_root,
            comfy_input_root=comfy_input_root,
            fl2va_capability_provider=fl2va_capability_provider,
            r2v_capability_provider=r2v_capability_provider, r2v_owner_root=r2v_owner_root,
            style_selection_resolver=style_selection_resolver)
    def cleanup(take):
        from story_builder.services.t2v_pipeline import is_pipeline
        request = take.get("input_snapshot") or {}
        if is_pipeline(take) and comfy_input_root is not None:
            (Path(comfy_input_root) / "vibe_t2v" / str(take["job_id"]) / "ltx_input.mkv").unlink(missing_ok=True)
        if request.get("workflow_id") == FL2VA_WORKFLOW_ID and comfy_input_root is not None:
            cleanup_fl2va_staging_job(Path(comfy_input_root), str(take.get("job_id", "")))
        elif request.get("workflow_id") == R2V_WORKFLOW_ID and comfy_input_root is not None and r2v_owner_root is not None:
            cleanup_r2v_staging_job(job_id=str(take.get("job_id", "")),
                comfy_input_root=Path(comfy_input_root), owner_root=Path(r2v_owner_root))
    if media_root is not None:
        from story_builder.services.performance_journal import PerformanceJournal
        worker_options.setdefault("performance_journal", PerformanceJournal(media_root))
    return ProductionJobWorker(ledger, comfy_url=comfy_url,
        prepare=prepare,
        collect=collect, cleanup=cleanup, **worker_options)


def make_output_collector(*, data_root: Path, ledger: ProductionLedger, comfy_url: str,
                          ffprobe: str | None = None) -> Callable[[dict[str, Any], dict[str, Any]], list[dict[str, Any]]]:
    """Return a native video+audio collector into durable product asset storage.

    Uses media_jobs only to fetch Comfy output into a disposable staging area;
    every accepted output is probed, hashed, and atomically placed under its
    workspace. Named batch finals replace only their reserved output filename.
    """
    from story_builder.services.media_jobs import collect_outputs

    root = Path(data_root).expanduser().resolve()
    probe_bin = ffprobe or os.environ.get("FFPROBE", "ffprobe")

    def collect(take: dict[str, Any], history: dict[str, Any]) -> list[dict[str, Any]]:
        workspace = _identifier(take["project_id"], "workspace_id")
        job_id = _identifier(take["job_id"], "job_id")
        final_dir = generated_root(root, workspace)
        final_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="isolated-video-") as temporary:
            downloaded = collect_outputs(history, destination_dir=Path(temporary), comfy_url=comfy_url)
            records = []
            for item in downloaded:
                if item.get("kind") != "video":
                    continue
                source = (Path(temporary) / Path(str(item.get("relative_path", ""))).name).resolve()
                if source.parent != Path(temporary).resolve() or not source.is_file():
                    continue
                probe_result = subprocess.run([probe_bin, "-v", "error", "-show_entries",
                    "format=duration:stream=codec_type", "-of", "json", str(source)],
                    capture_output=True, text=True, timeout=30, check=False)
                if probe_result.returncode:
                    continue
                try:
                    probe = json.loads(probe_result.stdout)
                    stream_types = {row.get("codec_type") for row in probe.get("streams", []) if isinstance(row, dict)}
                    duration = float(probe.get("format", {}).get("duration"))
                except (ValueError, TypeError, json.JSONDecodeError):
                    continue
                chunked_ltx = (take.get("pipeline", {}).get("stage") == "ltx_refinement"
                               and "ltx_chunks" in take.get("pipeline", {}))
                if "video" not in stream_types or (not chunked_ltx and "audio" not in stream_types) or duration <= 0:
                    continue
                from story_builder.services.t2v_pipeline import is_pipeline, probe as pipeline_probe, video_stream, remux_final
                if is_pipeline(take):
                    if take.get("pipeline", {}).get("stage") != "ltx_refinement":
                        original_probe = pipeline_probe(source)
                        video_stream(original_probe)
                        source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
                        original_dir = intermediate_root(root, workspace, "originals") / job_id
                        original_dir.mkdir(parents=True, exist_ok=True)
                        original_path = original_dir / f"{source_hash}.mp4"
                        if not original_path.exists():
                            staged_original = original_dir / f".{uuid.uuid4().hex}.tmp"
                            shutil.copy2(source, staged_original)
                            os.replace(staged_original, original_path)
                        return [{"pipeline_original": True, "sha256": source_hash,
                            "relative_path": original_path.relative_to(root).as_posix(),
                            "probe": original_probe, "kind": "video"}]
                    if chunked_ltx:
                        from story_builder.services.ltx_chunks import collect_chunk
                        joined = Path(temporary) / "ltx_joined.mp4"
                        chunk_record = collect_chunk(take, source, data_root=root, joined_path=joined)
                        if chunk_record is not None:
                            return [chunk_record]
                        source = joined
                    remuxed = Path(temporary) / "final_original_audio.mp4"
                    probe = remux_final(take, source, remuxed, data_root=root)
                    source = remuxed
                    duration = float(probe["format"]["duration"])
                digest = hashlib.sha256(source.read_bytes()).hexdigest()
                batch_filename = None
                with ledger._connect() as db:
                    if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='t2v_batch_output_names'").fetchone():
                        named = db.execute("SELECT filename FROM t2v_batch_output_names WHERE workspace_id=? AND clip_id=?",
                                           (workspace, take["shot_id"])).fetchone()
                        batch_filename = named["filename"] if named else None
                asset_id = f"video_{digest[:32]}"
                if batch_filename:
                    # Named versions need distinct asset identities even for identical bytes.
                    asset_id = 'video_' + hashlib.sha256(f'{workspace}/{batch_filename}/{digest}'.encode()).hexdigest()[:32]
                destination = final_dir / (batch_filename or f"{asset_id}{source.suffix.lower()}")
                if destination.is_symlink() or destination.resolve().parent != final_dir.resolve():
                    raise ValueError("Unsafe batch output path.")
                if batch_filename or not destination.exists():
                    temporary_target = final_dir / f".{asset_id}.{uuid.uuid4().hex}.tmp"
                    shutil.copy2(source, temporary_target)
                    os.replace(temporary_target, destination)
                metadata = {"kind": "video", "sha256": digest, "duration_seconds": duration,
                    "has_video": True, "has_audio": True, "relative_path": destination.relative_to(root).as_posix(),
                    "job_id": job_id, "prompt_id": take.get("prompt_id"), "probe": probe}
                if batch_filename:
                    metadata["batch_filename"] = batch_filename
                    # Old jobs must not play the replacement under their old identity.
                    with ledger._connect() as db:
                        for old in db.execute("SELECT asset_id,metadata_json FROM isolated_video_assets WHERE workspace_id=? AND asset_id!=?", (workspace, asset_id)).fetchall():
                            previous = json.loads(old["metadata_json"])
                            if previous.get("relative_path") == metadata["relative_path"]:
                                previous["relative_path"] = f"overwritten/{old['asset_id']}.mp4"
                                previous["overwritten"] = True
                                db.execute("UPDATE isolated_video_assets SET metadata_json=? WHERE asset_id=?", (json.dumps(previous), old["asset_id"]))
                shared_asset = register_generated_video(root, workspace, destination.name, metadata)
                if batch_filename:
                    legacy_asset_id = None
                    with ledger._connect() as db:
                        for batch in db.execute("SELECT entries_json FROM t2v_batches WHERE workspace_id=?", (workspace,)):
                            for entry in json.loads(batch["entries_json"]):
                                if entry.get("admission_key") == take["shot_id"]:
                                    legacy_asset_id = entry.get("replace_legacy_asset_id")
                        previous = db.execute("SELECT metadata_json FROM isolated_video_assets WHERE asset_id=? AND workspace_id=?", (legacy_asset_id, workspace)).fetchone() if legacy_asset_id else None
                        refs = db.execute("SELECT COUNT(*) FROM isolated_video_asset_refs WHERE asset_id=?", (legacy_asset_id,)).fetchone()[0] if previous else 0
                    if previous and refs <= 1:
                        old_metadata = json.loads(previous["metadata_json"])
                        old_path = root / old_metadata["relative_path"]
                        # Do not remove a shared/deduplicated output used by another job.
                        if old_path.parent.resolve() == final_dir.resolve() and old_path != destination and not old_path.is_symlink():
                            old_path.unlink(missing_ok=True)
                choice = (take.get("input_snapshot") or {}).get("output_destination")
                if choice:
                    from story_builder.services.media_library import relocate_output
                    shared_asset = relocate_output(root, workspace, shared_asset["asset_id"], choice, job_id)
                    metadata["saved_path"] = shared_asset.get("saved_path")
                metadata["shared_asset_id"] = shared_asset["asset_id"]
                metadata["shared_asset_url"] = shared_asset["content_url"]
                records.append({"asset_id": asset_id, **metadata})
            if not records:
                return []
            with ledger._connect() as db:
                for record in records:
                    db.execute("INSERT OR IGNORE INTO isolated_video_assets(asset_id,job_id,workspace_id,sha256,metadata_json) VALUES(?,?,?,?,?)",
                        (record["asset_id"], job_id, workspace, record["sha256"],
                         json.dumps(record, sort_keys=True, ensure_ascii=False)))
                    if record.get("batch_filename"):
                        db.execute("UPDATE isolated_video_assets SET metadata_json=? WHERE asset_id=?",
                                   (json.dumps(record, sort_keys=True, ensure_ascii=False), record["asset_id"]))
                    db.execute("INSERT OR IGNORE INTO isolated_video_asset_refs(asset_id,job_id) VALUES(?,?)",
                               (record["asset_id"], job_id))
            return records
    return collect
