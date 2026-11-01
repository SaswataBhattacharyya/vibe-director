"""Durable editable prompt drafts tied to the current screenplay and setup."""
from __future__ import annotations

from story_builder.services.director_skills import director_skill_context

import hashlib
import json
import re
from contextlib import contextmanager

from story_builder.services.production_ledger import LedgerConflict, LedgerNotFound
from story_builder.services.isolated_video_contract import T2V_WORKFLOW_ID
from story_builder.services.isolated_fl2va_contract import WORKFLOW_ID as FL2VA_WORKFLOW_ID
from story_builder.services.isolated_r2v_contract import WORKFLOW_ID as R2V_WORKFLOW_ID

WORKFLOWS = {T2V_WORKFLOW_ID, FL2VA_WORKFLOW_ID, R2V_WORKFLOW_ID}
_SHOT_KEY = re.compile(r"^[1-9][0-9]{0,3}\.[1-9][0-9]{0,3}$")
_PROMPT_LIMIT = 7000


@contextmanager
def _connection(ledger):
    db = ledger._connect()
    try:
        yield db
    finally:
        db.close()


class PromptDrafts:
    def __init__(self, ledger, story, workflow_knowledge=None, styles=None):
        self.ledger = ledger
        self.story = story
        self.workflow_knowledge = workflow_knowledge
        self.styles = styles
        with _connection(ledger) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS story_prompt_drafts (
                workspace_id TEXT NOT NULL,
                screenplay_revision_id TEXT NOT NULL,
                setup_hash TEXT NOT NULL,
                drafts_json TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(workspace_id, screenplay_revision_id)
            )""")

    def _accepted_and_setup(self, db, workspace_id, revision_id):
        revision = db.execute("SELECT * FROM story_screenplay_revisions WHERE workspace_id=? AND screenplay_revision_id=?",
            (workspace_id, revision_id)).fetchone()
        if revision is None:
            raise LedgerNotFound("Screenplay revision not found.")
        if not self.story._screenplay_is_currently_accepted(db, revision):
            raise LedgerConflict("Prompt drafts require the current accepted screenplay revision.")
        row = db.execute("SELECT setup_json,updated_at FROM story_production_setups WHERE workspace_id=? AND screenplay_revision_id=?",
            (workspace_id, revision_id)).fetchone()
        if row is None:
            raise LedgerConflict("Save Automation & Parameters before preparing prompts.")
        setup = json.loads(row["setup_json"])
        digest = hashlib.sha256(json.dumps(setup, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
        screenplay = json.loads(revision["screenplay_json"])
        expected = {f"{scene['scene_number']}.{shot['shot_number']}"
            for scene in screenplay.get("scenes", []) for shot in scene.get("shots", [])}
        return setup, digest, row["updated_at"], expected

    @staticmethod
    def validate_drafts(value, expected_keys, *, required_workflow=None):
        if not isinstance(value, dict) or not value:
            raise ValueError("Provide every scene.shot prompt draft from the accepted screenplay.")
        result = {}
        for key, draft in value.items():
            if not isinstance(key, str) or not _SHOT_KEY.fullmatch(key):
                raise ValueError("Prompt draft keys must use the scene.shot number format.")
            if not isinstance(draft, dict) or set(draft) - {"workflow_id", "prompt", "knowledge_ref", "style_ref"} or not {"workflow_id", "prompt"} <= set(draft):
                raise ValueError(f"Prompt draft {key} must contain workflow_id and prompt, with optional knowledge_ref.")
            if type(draft["workflow_id"]) is not str or draft["workflow_id"] not in WORKFLOWS:
                raise ValueError(f"Prompt draft {key} uses an unsupported workflow.")
            if required_workflow is not None and draft["workflow_id"] != required_workflow:
                raise ValueError("Automated video prompt drafts must use the single workflow selected for this Assisted manual run.")
            if type(draft["prompt"]) is not str or len(draft["prompt"]) >= _PROMPT_LIMIT:
                raise ValueError(f"Prompt draft {key} must be text shorter than 7000 Unicode code points.")
            normalized = {"workflow_id": draft["workflow_id"], "prompt": draft["prompt"]}
            ref = draft.get("knowledge_ref")
            if ref is not None:
                if (not isinstance(ref, dict) or set(ref) != {"knowledge_id", "guidance_version", "workflow_sha256"}
                        or type(ref["knowledge_id"]) is not str or not ref["knowledge_id"]
                        or type(ref["guidance_version"]) is not int or ref["guidance_version"] < 1
                        or type(ref["workflow_sha256"]) is not str or not re.fullmatch(r"[a-f0-9]{64}", ref["workflow_sha256"])):
                    raise ValueError(f"Prompt draft {key} has malformed workflow knowledge provenance.")
                normalized["knowledge_ref"] = ref
            style_ref = draft.get("style_ref")
            if style_ref is not None:
                fields = {"snapshot_id", "style_version_id", "narrative_hash", "director_profile_hash", "directing_style_hash"}
                if (not isinstance(style_ref, dict) or set(style_ref) != fields
                        or type(style_ref["snapshot_id"]) is not str or not style_ref["snapshot_id"]
                        or type(style_ref["style_version_id"]) is not str or not style_ref["style_version_id"]
                        or any(type(style_ref[name]) is not str or not re.fullmatch(r"[a-f0-9]{64}", style_ref[name])
                               for name in fields - {"snapshot_id", "style_version_id"})):
                    raise ValueError(f"Prompt draft {key} has malformed creative style provenance.")
                normalized["style_ref"] = style_ref
            result[key] = normalized
        if set(result) != expected_keys:
            raise ValueError("Prompt drafts must match every scene and shot in the accepted screenplay exactly.")
        return result

    def prepare(self, workspace_id, revision_id, shot_key, workflow_id, *, setup_snapshot=None,
                prior_prompt_context=None):
        """Use exact workflow guidance to draft one editable screenplay-shot prompt."""
        from story_builder.services.reasoning_provider import generate_json
        if workflow_id not in WORKFLOWS:
            raise ValueError("Choose a supported MiniMax video workflow.")
        if not isinstance(shot_key, str) or not _SHOT_KEY.fullmatch(shot_key):
            raise ValueError("shot_key must use the scene.shot number format.")
        if self.workflow_knowledge is None:
            raise LedgerConflict("Workflow guidance is not connected.")
        with _connection(self.ledger) as db:
            setup, _, _, expected = self._accepted_and_setup(db, workspace_id, revision_id)
            if shot_key not in expected:
                raise LedgerNotFound("That scene and shot are not in the current accepted screenplay.")
            row = db.execute("SELECT screenplay_json,style_selection_snapshot_id FROM story_screenplay_revisions WHERE workspace_id=? AND screenplay_revision_id=?",
                (workspace_id, revision_id)).fetchone()
            screenplay = json.loads(row["screenplay_json"])
            style_snapshot_id = row["style_selection_snapshot_id"]
        if setup_snapshot is not None:
            # Later Full-run scenes must retain the settings frozen at run start.
            setup = setup_snapshot
        guidance = self.workflow_knowledge.get(workflow_id, model_id="minimax_h3")
        if guidance["retrieval_status"] != "matched":
            raise LedgerConflict("No curated guidance exists for this exact model and workflow.")
        scene_number, shot_number = map(int, shot_key.split("."))
        scene = next(item for item in screenplay["scenes"] if item["scene_number"] == scene_number)
        shot = next(item for item in scene["shots"] if item["shot_number"] == shot_number)
        compact_story = {"title": screenplay.get("title"), "logline": screenplay.get("logline"),
            "characters": screenplay.get("characters", []),
            "scene_outline": [{"scene_number": item.get("scene_number"), "slugline": item.get("slugline"),
                "summary": item.get("summary")} for item in screenplay.get("scenes", [])]}
        facts = [{"kind": node["kind"], "guidance": node["text"], "sources": [
            {"uri": source["uri"], "version": source["version"], "section": source["section"]}
            for source in guidance["sources"] if source["source_id"] in node["source_ids"]]}
            for node in guidance["nodes"]]
        style = self.styles.get_selection(style_snapshot_id) if self.styles and style_snapshot_id else None
        style_context = None if style is None else {
            "production_type": style.get("production_type"),
            "style_version_id": style.get("style_version_id"),
            "directing_style": style.get("directing_style"),
            "narrative_guidance": {"video": style.get("narrative_guidance", {}).get("video")},
            "director_profile": style.get("director_profile"),
        }
        parameters = {key: setup[key] for key in ("video_quality", "duration_policy", "video_workflow_id") if key in setup}
        prior_context = ""
        if prior_prompt_context is not None:
            if type(prior_prompt_context) is not str or len(prior_prompt_context) >= _PROMPT_LIMIT:
                raise ValueError("A prior prompt context must be text below the 7,000-character limit.")
            prior_context = ("DIRECTOR'S PREVIOUS WORKFLOW PROMPT (preserve its visual intent and all useful direction, "
                "but adapt it to the selected workflow; do not treat its workflow syntax or reference claims as binding):\n"
                + json.dumps(prior_prompt_context, ensure_ascii=False) + "\n")
        result = generate_json(temperature=0, prompt=(
            "Prepare one editable video-generation prompt for a screenplay shot. Return only JSON: {\\\"prompt\\\":\\\"...\\\"}. "
            "Use only the screenplay facts supplied; do not add plot events, characters, props, references, or dialogue. "
            "Turn integrated camera, lighting, mood, sound-effect and music direction into one coherent shot. "
            "Apply the selected workflow's cited guidance below. Do not fabricate reference labels or claim media is attached. "
            "For T2V, describe the location/background, lighting, named character appearances, speaker-labelled exact dialogue and clear foreground speech independently of other clips. Advance the next story beat briskly without padding. "
            "Write short, crisp production prompts: concrete subject and essential setting/light, one observable event or tightly linked action, at most one camera move, and a clear endpoint. Aim for 60–120 words of visual direction, fewer when sufficient; this is a soft target excluding exact dialogue and required workflow fields. Never pad to the target or truncate source action or speech. Remove repeated instructions, decorative adjective/lens lists, reasoning and story summaries. Keep mandatory model section names, exact speaker-labelled dialogue and essential sound balance. "
            "Keep the final prompt strictly below 7000 Unicode code points. The user will review and edit it.\n\n"
            f"{director_skill_context(video=True)}\n\n"
            f"MODEL: minimax_h3\nWORKFLOW: {workflow_id}\n"
            f"SOURCE-LINKED WORKFLOW GUIDANCE: {json.dumps(facts, ensure_ascii=False)}\n"
            f"PINNED CREATIVE STYLE (direction only; never new story canon): {json.dumps(style_context, ensure_ascii=False)}\n"
            f"CONFIRMED PRODUCTION PARAMETERS: {json.dumps(parameters, ensure_ascii=False)}\n"
            f"{prior_context}"
            f"SCREENPLAY CONTEXT: {json.dumps(compact_story, ensure_ascii=False)}\n"
            f"TARGET SCENE: {json.dumps(scene, ensure_ascii=False)}\nTARGET SHOT: {json.dumps(shot, ensure_ascii=False)}"
        ))
        prompt = result.get("prompt")
        if type(prompt) is not str or not prompt.strip() or len(prompt) >= _PROMPT_LIMIT:
            raise ValueError("The reasoning model did not return a non-empty prompt under the 7,000-character limit.")
        style_ref = None if style is None else {"snapshot_id": style["snapshot_id"],
            "style_version_id": style["style_version_id"], "narrative_hash": style["narrative_hash"],
            "director_profile_hash": style["director_profile_hash"],
            "directing_style_hash": style["directing_style"]["style_hash"]}
        return {"shot_key": shot_key, "workflow_id": workflow_id, "prompt": prompt,
            "knowledge_ref": {"knowledge_id": guidance["knowledge_id"],
                "guidance_version": guidance["guidance_version"], "workflow_sha256": guidance["workflow_sha256"]},
            **({"style_ref": style_ref} if style_ref else {}),
            "sources": guidance["sources"]}

    def get(self, workspace_id, revision_id):
        with _connection(self.ledger) as db:
            _, setup_hash, _, _ = self._accepted_and_setup(db, workspace_id, revision_id)
            row = db.execute("SELECT setup_hash,drafts_json,updated_at FROM story_prompt_drafts WHERE workspace_id=? AND screenplay_revision_id=?",
                (workspace_id, revision_id)).fetchone()
        return {"workspace_id": workspace_id, "screenplay_revision_id": revision_id,
            "setup_hash": setup_hash, "setup_matches_current": row is None or row["setup_hash"] == setup_hash,
            "drafts": json.loads(row["drafts_json"]) if row else {}, "updated_at": row["updated_at"] if row else None}

    def save_shot(self, workspace_id, revision_id, setup_value, shot_key, draft_value):
        """Persist one reached shot without requiring future prompts to exist."""
        from story_builder.services.production_setup import ProductionSetup
        setup = ProductionSetup.validate(setup_value)
        if not isinstance(shot_key, str) or not _SHOT_KEY.fullmatch(shot_key):
            raise ValueError("shot_key must use the scene.shot number format.")
        with _connection(self.ledger) as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                current_setup, current_hash, _, expected_keys = self._accepted_and_setup(db, workspace_id, revision_id)
                if current_setup != setup:
                    raise LedgerConflict("Production setup changed; reload before saving prompt drafts.")
                if shot_key not in expected_keys:
                    raise LedgerNotFound("That scene and shot are not in the current accepted screenplay.")
                required_workflow = (setup.get("video_workflow_id")
                    if setup.get("mode") == "assisted_manual"
                    and setup.get("automate_steps", {}).get("video") is True else None)
                draft = self.validate_drafts({shot_key: draft_value}, {shot_key},
                    required_workflow=required_workflow)[shot_key]
                if self.workflow_knowledge is not None:
                    ref = draft.get("knowledge_ref")
                    if ref is not None:
                        current = self.workflow_knowledge.get(draft["workflow_id"], model_id="minimax_h3")
                        if current["retrieval_status"] != "matched" or any(ref[name] != current[name]
                                for name in ("knowledge_id", "guidance_version", "workflow_sha256")):
                            raise LedgerConflict(f"Workflow guidance changed for prompt {shot_key}; regenerate or review it before saving.")
                self._validate_style_refs(db, {shot_key: draft}, revision_id)
                row = db.execute("SELECT setup_hash,drafts_json FROM story_prompt_drafts WHERE workspace_id=? AND screenplay_revision_id=?",
                    (workspace_id, revision_id)).fetchone()
                drafts = json.loads(row["drafts_json"]) if row and row["setup_hash"] == current_hash else {}
                drafts[shot_key] = draft
                encoded = json.dumps(drafts, sort_keys=True, separators=(",", ":"))
                db.execute("""INSERT INTO story_prompt_drafts(workspace_id,screenplay_revision_id,setup_hash,drafts_json)
                    VALUES(?,?,?,?) ON CONFLICT(workspace_id,screenplay_revision_id)
                    DO UPDATE SET setup_hash=excluded.setup_hash,drafts_json=excluded.drafts_json,updated_at=CURRENT_TIMESTAMP""",
                    (workspace_id, revision_id, current_hash, encoded))
                db.commit()
            except Exception:
                db.rollback()
                raise
        return self.get(workspace_id, revision_id)

    def save(self, workspace_id, revision_id, setup_value, drafts_value):
        """Persist a complete prompt set for batch/automation preparation."""
        from story_builder.services.production_setup import ProductionSetup
        setup = ProductionSetup.validate(setup_value)
        with _connection(self.ledger) as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                current_setup, current_hash, _, expected_keys = self._accepted_and_setup(db, workspace_id, revision_id)
                if current_setup != setup:
                    raise LedgerConflict("Production setup changed; reload before saving prompt drafts.")
                required_workflow = (setup.get("video_workflow_id")
                    if setup.get("mode") == "assisted_manual"
                    and setup.get("automate_steps", {}).get("video") is True else None)
                drafts = self.validate_drafts(drafts_value, expected_keys, required_workflow=required_workflow)
                self._validate_knowledge_refs(drafts)
                self._validate_style_refs(db, drafts, revision_id)
                encoded = json.dumps(drafts, sort_keys=True, separators=(",", ":"))
                db.execute("""INSERT INTO story_prompt_drafts(workspace_id,screenplay_revision_id,setup_hash,drafts_json)
                    VALUES(?,?,?,?) ON CONFLICT(workspace_id,screenplay_revision_id)
                    DO UPDATE SET setup_hash=excluded.setup_hash,drafts_json=excluded.drafts_json,updated_at=CURRENT_TIMESTAMP""",
                    (workspace_id, revision_id, current_hash, encoded))
                db.commit()
            except Exception:
                db.rollback()
                raise
        return self.get(workspace_id, revision_id)

    def _validate_knowledge_refs(self, drafts):
        if self.workflow_knowledge is None:
            return
        for key, draft in drafts.items():
            ref = draft.get("knowledge_ref")
            if ref is None:
                continue  # User-authored legacy/manual prompts remain valid.
            current = self.workflow_knowledge.get(draft["workflow_id"], model_id="minimax_h3")
            if current["retrieval_status"] != "matched" or any(ref[name] != current[name]
                    for name in ("knowledge_id", "guidance_version", "workflow_sha256")):
                raise LedgerConflict(f"Workflow guidance changed for prompt {key}; regenerate or review it before saving.")

    def _validate_style_refs(self, db, drafts, revision_id):
        refs = {key: draft["style_ref"] for key, draft in drafts.items() if draft.get("style_ref") is not None}
        if not refs:
            return  # User-authored legacy/manual prompts remain valid.
        row = db.execute("SELECT style_selection_snapshot_id FROM story_screenplay_revisions WHERE screenplay_revision_id=?",
            (revision_id,)).fetchone()
        snapshot_id = row["style_selection_snapshot_id"] if row else None
        if not snapshot_id or self.styles is None:
            raise LedgerConflict("Creative style provenance cannot be verified; reload Prompt Preparation.")
        style = self.styles.get_selection(snapshot_id)
        current = {"snapshot_id": style["snapshot_id"], "style_version_id": style["style_version_id"],
            "narrative_hash": style["narrative_hash"], "director_profile_hash": style["director_profile_hash"],
            "directing_style_hash": style["directing_style"]["style_hash"]}
        if any(ref != current for ref in refs.values()):
            raise LedgerConflict("Pinned creative style changed for a prompt; regenerate or review it before saving.")
