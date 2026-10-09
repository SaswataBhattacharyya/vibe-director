"""Versioned production style and type setup on the shared production ledger.

This service owns setup snapshots only. It does not extract/analyze media or
submit generation jobs. Guidance and Director profiles are frozen in published
versions; selections are append-only snapshots tied to one context.
"""
from __future__ import annotations

import json
import re
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

from story_builder.services.production_director_profiles import (
    REQUIRED_KEYS as PROFILE_REQUIRED_KEYS,
    load_registry,
)
from story_builder.services.production_ledger import ProductionLedger, stable_hash
from story_builder.services.prompt_styles import REQUIRED_STAGES, list_styles


class ProductionStyleError(ValueError):
    """Invalid style setup or selection."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def _ledger_connection(ledger: ProductionLedger):
    db = ledger._connect()
    try:
        with db:
            yield db
    finally:
        db.close()


def _validate_context(workspace_id: Any, isolated_context_id: Any) -> tuple[str, str]:
    if workspace_id is not None and (type(workspace_id) is not str or not workspace_id):
        raise ProductionStyleError("workspace_id must be a non-empty string or null.")
    if isolated_context_id is not None and (type(isolated_context_id) is not str or not isolated_context_id):
        raise ProductionStyleError("isolated_context_id must be a non-empty string or null.")
    if (workspace_id is None) == (isolated_context_id is None):
        raise ProductionStyleError("Supply exactly one of workspace_id or isolated_context_id.")
    context_id = workspace_id if workspace_id is not None else isolated_context_id
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}", context_id):
        raise ProductionStyleError("Context IDs must be 1–128 letters, digits, dots, underscores, colons, or hyphens.")
    return ("workspace_id", workspace_id) if workspace_id is not None else ("isolated_context_id", isolated_context_id)


def _validate_type(style_id: str, narrative_guidance: dict[str, Any], profile: dict[str, Any]) -> tuple[str, dict[str, Any], dict[str, Any]]:
    if not isinstance(style_id, str) or not re.fullmatch(r"[a-z][a-z0-9_]{1,63}", style_id):
        raise ProductionStyleError("production_type must be a lowercase identifier (2–64 characters).")
    if not isinstance(narrative_guidance, dict):
        raise ProductionStyleError("narrative_guidance must be an object.")
    if set(REQUIRED_STAGES) - set(narrative_guidance):
        raise ProductionStyleError(f"narrative_guidance requires all six stages: {', '.join(REQUIRED_STAGES)}.")
    guidance = {stage: narrative_guidance[stage] for stage in REQUIRED_STAGES}
    if any(not isinstance(value, str) or not value.strip() for value in guidance.values()):
        raise ProductionStyleError("Each narrative guidance stage must be non-empty text.")
    if not isinstance(profile, dict):
        raise ProductionStyleError("director_profile must be an object.")
    missing = [key for key in PROFILE_REQUIRED_KEYS if key not in profile]
    if missing:
        raise ProductionStyleError(f"director_profile is missing required fields: {', '.join(missing)}.")
    result = {key: profile[key] for key in PROFILE_REQUIRED_KEYS}
    if any(not isinstance(result[key], str) or not result[key].strip() for key in PROFILE_REQUIRED_KEYS[:2]):
        raise ProductionStyleError("Director display_name and purpose must be non-empty text.")
    for field in ("behavior", "review_priorities"):
        values = result[field]
        if not isinstance(values, list) or not values or any(not isinstance(item, str) or not item.strip() for item in values):
            raise ProductionStyleError(f"Director {field} must be a non-empty list of non-empty strings.")
    return style_id, guidance, result


class ProductionStyleService:
    """Style catalog, custom type publishing, and immutable setup selections."""

    def __init__(self, ledger: ProductionLedger) -> None:
        self.ledger = ledger
        with _ledger_connection(self.ledger) as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS production_style_versions (
                    style_version_id TEXT PRIMARY KEY,
                    production_type TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    narrative_json TEXT NOT NULL,
                    narrative_hash TEXT NOT NULL,
                    director_profile_json TEXT NOT NULL,
                    director_profile_hash TEXT NOT NULL,
                    published_at TEXT NOT NULL,
                    UNIQUE(production_type, version)
                );
                CREATE TABLE IF NOT EXISTS production_style_selections (
                    snapshot_id TEXT PRIMARY KEY,
                    workspace_id TEXT,
                    isolated_context_id TEXT,
                    production_type TEXT NOT NULL,
                    style_version_id TEXT NOT NULL,
                    style_version INTEGER NOT NULL,
                    narrative_hash TEXT NOT NULL,
                    director_profile_hash TEXT NOT NULL,
                    snapshot_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    CHECK ((workspace_id IS NOT NULL AND isolated_context_id IS NULL) OR
                           (workspace_id IS NULL AND isolated_context_id IS NOT NULL))
                );
                CREATE INDEX IF NOT EXISTS production_style_selection_context_idx
                    ON production_style_selections(workspace_id, isolated_context_id, created_at);
                CREATE TRIGGER IF NOT EXISTS production_style_versions_no_update
                    BEFORE UPDATE ON production_style_versions BEGIN SELECT RAISE(ABORT, 'published style versions are immutable'); END;
                CREATE TRIGGER IF NOT EXISTS production_style_versions_no_delete
                    BEFORE DELETE ON production_style_versions BEGIN SELECT RAISE(ABORT, 'published style versions are immutable'); END;
                CREATE TRIGGER IF NOT EXISTS production_style_selections_no_update
                    BEFORE UPDATE ON production_style_selections BEGIN SELECT RAISE(ABORT, 'style selections are immutable'); END;
                CREATE TRIGGER IF NOT EXISTS production_style_selections_no_delete
                    BEFORE DELETE ON production_style_selections BEGIN SELECT RAISE(ABORT, 'style selections are immutable'); END;
            """)

    def list_catalog(self) -> dict[str, Any]:
        """Return six validated bundled types plus latest published custom types."""
        registry = load_registry()
        packs = {str(item["style_id"]): item for item in list_styles()}
        ids = set(registry["profiles"])
        if set(packs) != ids:
            raise ProductionStyleError("Bundled style packs and Director profile IDs do not match.")
        bases = []
        for type_id in sorted(ids):
            bases.append({
                "production_type": type_id,
                "display_name": registry["profiles"][type_id]["display_name"],
                "style_version": packs[type_id]["version"],
                "style_version_id": f"base:{type_id}:v{packs[type_id]['version']}",
                "narrative_guidance": packs[type_id]["stages"],
                "narrative_hash": stable_hash(packs[type_id]),
                "director_profile": registry["profiles"][type_id],
                "director_profile_version": registry["version"],
                "director_profile_hash": registry["content_hash"],
                "custom": False,
            })
        with _ledger_connection(self.ledger) as db:
            rows = db.execute("""SELECT v.* FROM production_style_versions v
                JOIN (SELECT production_type, MAX(version) version FROM production_style_versions GROUP BY production_type) latest
                USING (production_type, version) ORDER BY production_type""").fetchall()
        for row in rows:
            bases.append({
                "production_type": row["production_type"],
                "display_name": json.loads(row["director_profile_json"])["display_name"],
                "style_version": row["version"], "style_version_id": row["style_version_id"],
                "narrative_guidance": json.loads(row["narrative_json"]),
                "narrative_hash": row["narrative_hash"],
                "director_profile": json.loads(row["director_profile_json"]),
                "director_profile_version": f"custom_v{row['version']}",
                "director_profile_hash": row["director_profile_hash"], "custom": True,
            })
        return {"catalog_version": "production_style_setup_v1", "production_types": bases}

    def publish_custom_type(self, production_type: str, narrative_guidance: dict[str, Any], director_profile: dict[str, Any]) -> dict[str, Any]:
        """Validate and publish a new immutable custom production type version."""
        type_id, guidance, profile = _validate_type(production_type, narrative_guidance, director_profile)
        registry = load_registry()
        if type_id in registry["profiles"]:
            raise ProductionStyleError(f"{type_id!r} is a bundled production type; custom publication requires a new identifier.")
        narrative_hash = stable_hash(guidance)
        profile_hash = stable_hash(profile)
        now = _now()
        with _ledger_connection(self.ledger) as db:
            db.execute("BEGIN IMMEDIATE")
            version = db.execute("SELECT COALESCE(MAX(version), 0) + 1 FROM production_style_versions WHERE production_type=?", (type_id,)).fetchone()[0]
            style_version_id = f"custom:{type_id}:v{version}:{narrative_hash[:12]}:{profile_hash[:12]}"
            db.execute("""INSERT INTO production_style_versions
                (style_version_id,production_type,version,narrative_json,narrative_hash,director_profile_json,director_profile_hash,published_at)
                VALUES (?,?,?,?,?,?,?,?)""", (style_version_id, type_id, version,
                json.dumps(guidance, ensure_ascii=False, sort_keys=True), narrative_hash,
                json.dumps(profile, ensure_ascii=False, sort_keys=True), profile_hash, now))
            db.commit()
        return {"production_type": type_id, "style_version": version, "style_version_id": style_version_id,
                "narrative_guidance": guidance, "narrative_hash": narrative_hash,
                "director_profile": profile, "director_profile_hash": profile_hash, "published_at": now}

    def select(self, *, workspace_id: str | None = None, isolated_context_id: str | None = None,
               production_type: str, style_version_id: str | None = None) -> dict[str, Any]:
        """Append a frozen selection for exactly one workspace or isolated context."""
        if type(production_type) is not str or not production_type:
            raise ProductionStyleError("production_type must be a non-empty string.")
        if style_version_id is not None and type(style_version_id) is not str:
            raise ProductionStyleError("style_version_id must be a string when supplied.")
        _validate_context(workspace_id, isolated_context_id)
        if style_version_id is not None and style_version_id.startswith("base:"):
            catalog_item = next((item for item in self.list_catalog()["production_types"]
                                 if item["production_type"] == production_type and not item["custom"]), None)
            if not catalog_item or catalog_item["style_version_id"] != style_version_id:
                raise ProductionStyleError("Unknown or mismatched bundled style version.")
            selected = catalog_item
        elif style_version_id is not None:
            with _ledger_connection(self.ledger) as db:
                row = db.execute("SELECT * FROM production_style_versions WHERE style_version_id=? AND production_type=?", (style_version_id, production_type)).fetchone()
            if not row:
                raise ProductionStyleError("Unknown or mismatched custom style version.")
            selected = {"production_type": production_type, "style_version": row["version"],
                        "style_version_id": row["style_version_id"], "narrative_guidance": json.loads(row["narrative_json"]),
                        "narrative_hash": row["narrative_hash"], "director_profile": json.loads(row["director_profile_json"]),
                        "director_profile_hash": row["director_profile_hash"]}
        else:
            item = next((item for item in self.list_catalog()["production_types"] if item["production_type"] == production_type), None)
            if item is None:
                raise ProductionStyleError(f"Unknown production type {production_type!r}.")
            selected = item
        snapshot_id, now = uuid.uuid4().hex, _now()
        frozen = {"snapshot_id": snapshot_id, "workspace_id": workspace_id, "isolated_context_id": isolated_context_id,
                  "production_type": production_type, "style_version_id": selected["style_version_id"],
                  "style_version": selected["style_version"], "narrative_guidance": selected["narrative_guidance"],
                  "narrative_hash": selected["narrative_hash"], "director_profile": selected["director_profile"],
                  "director_profile_hash": selected["director_profile_hash"], "created_at": now}
        with _ledger_connection(self.ledger) as db:
            db.execute("""INSERT INTO production_style_selections
                (snapshot_id,workspace_id,isolated_context_id,production_type,style_version_id,style_version,narrative_hash,director_profile_hash,snapshot_json,created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?)""", (snapshot_id, workspace_id, isolated_context_id, production_type,
                selected["style_version_id"], selected["style_version"], selected["narrative_hash"],
                selected["director_profile_hash"], json.dumps(frozen, ensure_ascii=False, sort_keys=True), now))
        return frozen

    def get_selection(self, snapshot_id: str) -> dict[str, Any]:
        if type(snapshot_id) is not str or not re.fullmatch(r"[0-9a-f]{32}", snapshot_id):
            raise ProductionStyleError("snapshot_id must be a 32-character lowercase hex identifier.")
        with _ledger_connection(self.ledger) as db:
            row = db.execute("SELECT snapshot_json FROM production_style_selections WHERE snapshot_id=?", (snapshot_id,)).fetchone()
        if not row:
            raise KeyError(snapshot_id)
        return json.loads(row["snapshot_json"])

    def list_selections(self, *, workspace_id: str | None = None, isolated_context_id: str | None = None) -> list[dict[str, Any]]:
        column, value = _validate_context(workspace_id, isolated_context_id)
        with _ledger_connection(self.ledger) as db:
            rows = db.execute(f"SELECT snapshot_json FROM production_style_selections WHERE {column}=? ORDER BY created_at,snapshot_id", (value,)).fetchall()
        return [json.loads(row["snapshot_json"]) for row in rows]
