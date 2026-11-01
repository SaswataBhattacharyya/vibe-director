"""Durable, revision-scoped automation policy before prompt preparation."""
from __future__ import annotations

import json
import math
import re
from contextlib import contextmanager

from story_builder.services.production_ledger import LedgerConflict, LedgerNotFound

AUTOMATION_STEPS = (
    "character_images", "character_voice", "world_images", "frame_images", "video",
)
# Preserve the legacy standard key for existing saved setup hashes and manifests.
QUALITY = {"high": 0.98, "standard": 0.4, "standard_608": 0.6, "medium": 0.8, "t2v_low": 0.8, "t2v_standard": 0.98, "t2v_high": 1.5, "t2v_max": 2.0}
IMAGE_STEPS = ("character_images", "world_images", "frame_images")
TEXT_IMAGE_WORKFLOWS = {"qwen_image_2512", "z_image_turbo"}
FRAME_IMAGE_WORKFLOWS = TEXT_IMAGE_WORKFLOWS | {"qwen_image_edit_2511"}
VIDEO_WORKFLOWS = {"minimax_h3_t2v_local_v1", "minimax_h3_fl2va_first_last_v1", "minimax_h3_r2v_dynamic_v1"}


@contextmanager
def _connection(ledger):
    db = ledger._connect()
    try:
        yield db
    finally:
        db.close()


class ProductionSetup:
    def __init__(self, ledger, story):
        self.ledger = ledger
        self.story = story
        with _connection(self.ledger) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS story_production_setups (
                workspace_id TEXT NOT NULL,
                screenplay_revision_id TEXT NOT NULL,
                setup_json TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(workspace_id, screenplay_revision_id)
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS story_frame_preparation_skips (
                workspace_id TEXT NOT NULL,
                screenplay_revision_id TEXT NOT NULL,
                scene_number INTEGER NOT NULL,
                shot_number INTEGER NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(workspace_id, screenplay_revision_id, scene_number, shot_number)
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS story_assisted_stage_skips (
                workspace_id TEXT NOT NULL,
                screenplay_revision_id TEXT NOT NULL,
                step TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(workspace_id, screenplay_revision_id, step)
            )""")

    @staticmethod
    def _style_video_references(value):
        if "style_video_references" not in value:
            return None  # Older saved setups remain readable without changing their hash.
        refs = value["style_video_references"]
        if not isinstance(refs, list) or len(refs) > 2:
            raise ValueError("Choose at most two style videos for an automated run.")
        seen = set()
        result = []
        for row in refs:
            if not isinstance(row, dict) or set(row) != {"asset_id", "sha256", "intent"}:
                raise ValueError("Each style video needs an asset ID, SHA-256, and intended use.")
            asset_id, digest, intent = row["asset_id"], row["sha256"], row["intent"]
            if type(asset_id) is not str or not re.fullmatch(r"pa-[a-f0-9]{16}", asset_id):
                raise ValueError("Style video references must use a saved media asset ID.")
            if type(digest) is not str or not re.fullmatch(r"[a-f0-9]{64}", digest):
                raise ValueError("Each style video must have a frozen SHA-256.")
            if type(intent) is not str or not intent.strip() or len(intent) > 500:
                raise ValueError("Each style video needs an intended use under 500 characters.")
            if asset_id in seen:
                raise ValueError("A style video can be selected only once.")
            seen.add(asset_id)
            result.append({"asset_id": asset_id, "sha256": digest, "intent": intent.strip()})
        return result

    def _accepted_revision(self, db, workspace_id, revision_id):
        row = db.execute("SELECT * FROM story_screenplay_revisions WHERE workspace_id=? AND screenplay_revision_id=?",
            (workspace_id, revision_id)).fetchone()
        if row is None:
            raise LedgerNotFound("Screenplay revision not found.")
        if not self.story._screenplay_is_currently_accepted(db, row):
            raise LedgerConflict("Setup requires the current accepted screenplay revision.")
        return row

    @staticmethod
    def validate(value, *, require_image_settings=False):
        required = {"mode", "automate_steps", "video_quality", "duration_policy"}
        optional = {"style_video_references", "image_stage_settings", "video_workflow_id", "aspect_ratio"}
        if not isinstance(value, dict) or not required <= set(value) or set(value) - required - optional:
            raise ValueError("Setup must include mode, automate_steps, video_quality, and duration_policy, with optional media settings.")
        aspect_ratio = value.get("aspect_ratio", "16:9")
        if aspect_ratio not in {"16:9", "9:16", "4:3", "3:4", "1:1"}:
            raise ValueError("Choose a supported aspect ratio.")
        style_refs = ProductionSetup._style_video_references(value)
        mode = value["mode"]
        if type(mode) is not str or mode not in {"assisted_manual", "fully_automated"}:
            raise ValueError("Choose Assisted manual or Fully automated.")
        steps = value["automate_steps"]
        if not isinstance(steps, dict) or set(steps) != set(AUTOMATION_STEPS) or any(type(steps[key]) is not bool for key in AUTOMATION_STEPS):
            raise ValueError("All five automation steps must be explicit true/false values.")
        if mode == "fully_automated" and any(steps.values()):
            raise ValueError("Fully automated uses the image-free route; Assisted manual checkboxes must all be off.")
        video_workflow = value.get("video_workflow_id")
        if video_workflow is not None and (mode != "assisted_manual" or steps["video"] is not True
                or type(video_workflow) is not str or video_workflow not in VIDEO_WORKFLOWS):
            raise ValueError("Choose T2V, FFLF or R2V only when Assisted manual Video Generation is checked.")
        if require_image_settings and mode == "assisted_manual" and steps["video"] and video_workflow is None:
            raise ValueError("Choose one video workflow for the complete Assisted manual run.")
        if mode == "assisted_manual" and style_refs and steps["video"]:
            if video_workflow != "minimax_h3_r2v_dynamic_v1":
                raise ValueError("Selected style videos require Reference to video (R2V) for Assisted automatic video. Choose R2V or remove the style videos.")
        image_settings = value.get("image_stage_settings")
        selected_image_steps = {step for step in IMAGE_STEPS if steps[step]}
        if image_settings is not None:
            if not isinstance(image_settings, dict) or set(image_settings) - selected_image_steps:
                raise ValueError("Image settings may only be provided for automated image steps.")
            if require_image_settings and set(image_settings) != selected_image_steps:
                raise ValueError("Confirm image workflow and parameters for every automated image step.")
            normalized_image_settings = {}
            for step, setting in image_settings.items():
                fields = {"workflow_id", "width", "height", "steps", "cfg"}
                allowed_fields = fields | ({"world_view_count"} if step == "world_images" else set())
                if (not isinstance(setting, dict) or not fields <= set(setting)
                        or set(setting) - allowed_fields):
                    raise ValueError(f"{step} needs a workflow and width, height, steps, and CFG settings.")
                workflow = setting["workflow_id"]
                supported_workflows = FRAME_IMAGE_WORKFLOWS if step == "frame_images" else TEXT_IMAGE_WORKFLOWS
                if type(workflow) is not str or workflow not in supported_workflows:
                    if step == "frame_images":
                        raise ValueError("Choose a supported frame workflow: text-to-image or Qwen Image Edit.")
                    raise ValueError("Choose a supported text-to-image workflow for character and world image steps.")
                width, height, image_steps, cfg = (setting[key] for key in ("width", "height", "steps", "cfg"))
                if any(type(number) is not int or not 256 <= number <= 2048 or number % 8
                       for number in (width, height)):
                    raise ValueError("Image width and height must be 256–2048 pixels and divisible by 8.")
                step_range = (4, 16) if workflow in {"z_image_turbo", "qwen_image_edit_2511"} else (20, 80)
                if type(image_steps) is not int or not step_range[0] <= image_steps <= step_range[1]:
                    raise ValueError(f"Image steps must be {step_range[0]}–{step_range[1]} for {workflow}.")
                cfg_max = 2.0 if workflow == "z_image_turbo" else 8.0
                if type(cfg) not in (int, float) or not math.isfinite(cfg) or not 0.1 <= cfg <= cfg_max:
                    raise ValueError(f"Image CFG must be 0.1–{cfg_max} for {workflow}.")
                normalized = dict(setting)
                if step == "world_images":
                    view_count = setting.get("world_view_count", 4)
                    if type(view_count) is not int or view_count not in {2, 3, 4, 8}:
                        raise ValueError("World image view count must be exactly two, three, four or eight directions.")
                    normalized["world_view_count"] = view_count
                normalized_image_settings[step] = normalized
            image_settings = normalized_image_settings
        elif require_image_settings and selected_image_steps:
            raise ValueError("Confirm image workflow and parameters for every automated image step.")
        if type(value["video_quality"]) is not str or value["video_quality"] not in QUALITY:
            raise ValueError("Choose a supported video quality.")
        policy = value["duration_policy"]
        if not isinstance(policy, dict) or type(policy.get("kind")) is not str or policy.get("kind") not in {"fixed", "director_selected"}:
            raise ValueError("Choose a fixed duration or Director-selected duration.")
        if policy["kind"] == "fixed":
            if set(policy) != {"kind", "seconds"} or type(policy.get("seconds")) is not int or not 5 <= policy["seconds"] <= 30:
                raise ValueError("Fixed duration must be 5–30 seconds.")
        elif (set(policy) != {"kind", "min_seconds", "max_seconds"}
                or type(policy.get("min_seconds")) is not int or type(policy.get("max_seconds")) is not int
                or not 5 <= policy["min_seconds"] <= policy["max_seconds"] <= 30):
            raise ValueError("Director-selected duration range must be within 5–30 seconds.")
        result = {"mode": mode, "automate_steps": {key: steps[key] for key in AUTOMATION_STEPS},
            "video_quality": value["video_quality"], "duration_policy": dict(policy), "aspect_ratio": aspect_ratio}
        if style_refs is not None:
            result["style_video_references"] = style_refs
        if image_settings is not None:
            result["image_stage_settings"] = image_settings
        if video_workflow is not None:
            result["video_workflow_id"] = video_workflow
        return result

    def get(self, workspace_id: str, screenplay_revision_id: str):
        with _connection(self.ledger) as db:
            self._accepted_revision(db, workspace_id, screenplay_revision_id)
            row = db.execute("SELECT setup_json,updated_at FROM story_production_setups WHERE workspace_id=? AND screenplay_revision_id=?",
                (workspace_id, screenplay_revision_id)).fetchone()
        return {"workspace_id": workspace_id, "screenplay_revision_id": screenplay_revision_id,
            "setup": json.loads(row["setup_json"]) if row else None,
            "updated_at": row["updated_at"] if row else None}

    @staticmethod
    def require_manual_step(db, workspace_id: str, screenplay_revision_id: str, step: str):
        """Reject manual writes for stages configured to run automatically.

        Call inside the caller's write transaction so a concurrent setup change
        cannot race the admission decision. Read-only status remains available.
        """
        if step not in AUTOMATION_STEPS:
            raise ValueError("Unknown production step.")
        row = db.execute("SELECT setup_json FROM story_production_setups WHERE workspace_id=? AND screenplay_revision_id=?",
            (workspace_id, screenplay_revision_id)).fetchone()
        setup = json.loads(row["setup_json"]) if row else None
        if not isinstance(setup, dict):
            raise LedgerConflict("Save Automation & Parameters before assigning screenplay character voices.")
        if setup.get("mode") != "assisted_manual":
            raise LedgerConflict("Manual character voice assignment is skipped in Fully automated mode.")
        if setup.get("automate_steps", {}).get(step) is not False:
            raise LedgerConflict("Character-to-audio selection is configured for automation; use its automatic matching stage or resolve an unresolved match.")
        return setup

    def save(self, workspace_id: str, screenplay_revision_id: str, value):
        setup = self.validate(value, require_image_settings=True)
        if setup.get("style_video_references"):
            from story_builder.services.media_library import list_assets
            workspace = self.story.get_workspace(workspace_id, include_source=False)
            eligible = {}
            offset = 0
            while True:
                media = list_assets(self.story.data_root, workspace_id, kind="video", limit=100,
                    offset=offset, style_selection=workspace.get("style_selection"))
                eligible.update((row["asset_id"], row) for row in media["assets"] if row.get("recommended"))
                offset += len(media["assets"])
                if offset >= media["total"] or not media["assets"]:
                    break
            for ref in setup["style_video_references"]:
                asset = eligible.get(ref["asset_id"])
                if not asset or asset.get("sha256") != ref["sha256"]:
                    raise ValueError("Selected style videos must be recommended videos from this story's pinned style.")
        encoded = json.dumps(setup, sort_keys=True, separators=(",", ":"))
        with _connection(self.ledger) as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                self._accepted_revision(db, workspace_id, screenplay_revision_id)
                db.execute("""INSERT INTO story_production_setups(workspace_id,screenplay_revision_id,setup_json)
                    VALUES(?,?,?) ON CONFLICT(workspace_id,screenplay_revision_id)
                    DO UPDATE SET setup_json=excluded.setup_json,updated_at=CURRENT_TIMESTAMP""",
                    (workspace_id, screenplay_revision_id, encoded))
                # A return to automatic mode must not revive an old Skip later.
                for step in IMAGE_STEPS:
                    if setup.get("mode") != "assisted_manual" or setup.get("automate_steps", {}).get(step) is not False:
                        db.execute("DELETE FROM story_assisted_stage_skips WHERE workspace_id=? AND screenplay_revision_id=? AND step=?",
                            (workspace_id, screenplay_revision_id, step))
                db.commit()
            except Exception:
                db.rollback()
                raise
        return self.get(workspace_id, screenplay_revision_id)

    @staticmethod
    def _screenplay_shot_exists(row, scene_number, shot_number):
        screenplay = json.loads(row["screenplay_json"])
        return any(isinstance(scene, dict) and scene.get("scene_number") == scene_number
            and any(isinstance(shot, dict) and shot.get("shot_number") == shot_number
                    for shot in scene.get("shots", []))
            for scene in screenplay.get("scenes", []))

    def list_frame_preparation_skips(self, workspace_id: str, screenplay_revision_id: str):
        with _connection(self.ledger) as db:
            row = self._accepted_revision(db, workspace_id, screenplay_revision_id)
            rows = db.execute("""SELECT scene_number,shot_number FROM story_frame_preparation_skips
                WHERE workspace_id=? AND screenplay_revision_id=? ORDER BY scene_number,shot_number""",
                (workspace_id, screenplay_revision_id)).fetchall()
            valid = [(item["scene_number"], item["shot_number"]) for item in rows
                if self._screenplay_shot_exists(row, item["scene_number"], item["shot_number"])]
        return {"workspace_id": workspace_id, "screenplay_revision_id": screenplay_revision_id,
            "skipped": [{"scene_number": scene, "shot_number": shot} for scene, shot in valid]}

    def frame_preparation_is_skipped(self, workspace_id: str, screenplay_revision_id: str,
                                     scene_number: int, shot_number: int) -> bool:
        """Check a skip against the current accepted screenplay before frame admission."""
        with _connection(self.ledger) as db:
            revision = self._accepted_revision(db, workspace_id, screenplay_revision_id)
            if not self._screenplay_shot_exists(revision, scene_number, shot_number):
                raise LedgerConflict("Frame preparation must target a shot in the accepted screenplay revision.")
            row = db.execute("""SELECT 1 FROM story_frame_preparation_skips
                WHERE workspace_id=? AND screenplay_revision_id=? AND scene_number=? AND shot_number=?""",
                (workspace_id, screenplay_revision_id, scene_number, shot_number)).fetchone()
        return row is not None

    def set_frame_preparation_skip(self, workspace_id: str, screenplay_revision_id: str,
                                   scene_number: int, shot_number: int, skipped: bool):
        if (type(scene_number) is not int or scene_number < 1 or type(shot_number) is not int
                or shot_number < 1 or type(skipped) is not bool):
            raise ValueError("Frame skip requires positive scene/shot numbers and a boolean skipped value.")
        with _connection(self.ledger) as db:
            db.execute("BEGIN IMMEDIATE")
            row = self._accepted_revision(db, workspace_id, screenplay_revision_id)
            if not self._screenplay_shot_exists(row, scene_number, shot_number):
                raise LedgerConflict("Frame skip must target a shot in the accepted screenplay revision.")
            if skipped:
                db.execute("""INSERT OR IGNORE INTO story_frame_preparation_skips
                    (workspace_id,screenplay_revision_id,scene_number,shot_number)
                    VALUES(?,?,?,?)""", (workspace_id, screenplay_revision_id, scene_number, shot_number))
            else:
                db.execute("""DELETE FROM story_frame_preparation_skips WHERE workspace_id=?
                    AND screenplay_revision_id=? AND scene_number=? AND shot_number=?""",
                    (workspace_id, screenplay_revision_id, scene_number, shot_number))
            db.commit()
        return self.list_frame_preparation_skips(workspace_id, screenplay_revision_id)

    def list_assisted_stage_skips(self, workspace_id: str, screenplay_revision_id: str):
        with _connection(self.ledger) as db:
            self._accepted_revision(db, workspace_id, screenplay_revision_id)
            row = db.execute("SELECT setup_json FROM story_production_setups WHERE workspace_id=? AND screenplay_revision_id=?",
                (workspace_id, screenplay_revision_id)).fetchone()
            setup = json.loads(row["setup_json"]) if row else None
            skipped = db.execute("SELECT step FROM story_assisted_stage_skips WHERE workspace_id=? AND screenplay_revision_id=? ORDER BY step",
                (workspace_id, screenplay_revision_id)).fetchall()
        allowed = {step for step in IMAGE_STEPS if isinstance(setup, dict)
            and setup.get("mode") == "assisted_manual"
            and setup.get("automate_steps", {}).get(step) is False}
        return {"workspace_id": workspace_id, "screenplay_revision_id": screenplay_revision_id,
            "skipped": [row["step"] for row in skipped if row["step"] in allowed]}

    def set_assisted_stage_skip(self, workspace_id: str, screenplay_revision_id: str,
                                step: str, skipped: bool):
        if step not in IMAGE_STEPS or type(skipped) is not bool:
            raise ValueError("Choose an optional Assisted image stage and a boolean skipped value.")
        with _connection(self.ledger) as db:
            db.execute("BEGIN IMMEDIATE")
            self._accepted_revision(db, workspace_id, screenplay_revision_id)
            row = db.execute("SELECT setup_json FROM story_production_setups WHERE workspace_id=? AND screenplay_revision_id=?",
                (workspace_id, screenplay_revision_id)).fetchone()
            setup = json.loads(row["setup_json"]) if row else None
            if (not isinstance(setup, dict) or setup.get("mode") != "assisted_manual"
                    or setup.get("automate_steps", {}).get(step) is not False):
                db.rollback()
                raise LedgerConflict("Only an unchecked optional image stage in Assisted manual can be skipped.")
            if skipped:
                db.execute("INSERT OR IGNORE INTO story_assisted_stage_skips(workspace_id,screenplay_revision_id,step) VALUES(?,?,?)",
                    (workspace_id, screenplay_revision_id, step))
            else:
                db.execute("DELETE FROM story_assisted_stage_skips WHERE workspace_id=? AND screenplay_revision_id=? AND step=?",
                    (workspace_id, screenplay_revision_id, step))
            db.commit()
        return self.list_assisted_stage_skips(workspace_id, screenplay_revision_id)
