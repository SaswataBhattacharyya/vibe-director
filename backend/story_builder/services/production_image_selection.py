"""Durable screenplay-target image choices; bytes remain in the shared media library."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from story_builder.services.production_ledger import ClosingSQLiteConnection, LedgerConflict


class ProductionImageSelection:
    """Record one current master per target while retaining every prior choice."""

    def __init__(self, path: str | Path):
        self.path = Path(path).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS production_image_selections (
                    project_id TEXT NOT NULL,
                    screenplay_revision_id TEXT NOT NULL,
                    target_type TEXT NOT NULL,
                    target_record_id TEXT NOT NULL,
                    asset_id TEXT NOT NULL,
                    job_id TEXT NOT NULL,
                    authority TEXT NOT NULL,
                    decision_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY(project_id, screenplay_revision_id, target_type, target_record_id)
                );
                CREATE TABLE IF NOT EXISTS production_image_selection_history (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id TEXT NOT NULL,
                    screenplay_revision_id TEXT NOT NULL,
                    target_type TEXT NOT NULL,
                    target_record_id TEXT NOT NULL,
                    prior_asset_id TEXT,
                    asset_id TEXT NOT NULL,
                    job_id TEXT NOT NULL,
                    authority TEXT NOT NULL,
                    decision_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
            """)

    def _connect(self):
        db = sqlite3.connect(
            self.path, timeout=30, isolation_level=None, factory=ClosingSQLiteConnection
        )
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout=30000")
        return db

    def select(self, *, project_id: str, screenplay_revision_id: str,
               target_type: str, target_record_id: str, asset_id: str, job_id: str,
               authority: str, decision: dict[str, Any] | None = None) -> dict[str, Any]:
        if (not all(isinstance(value, str) and value.strip() for value in
                    (project_id, screenplay_revision_id, target_type, target_record_id,
                     asset_id, job_id)) or authority not in {"user", "director"}):
            raise ValueError("A complete image target, asset, job and selection authority are required.")
        if not isinstance(decision, (dict, type(None))):
            raise ValueError("Image selection decision must be an object.")
        decision_json = json.dumps(decision or {}, sort_keys=True, separators=(",", ":"))
        now = datetime.now(timezone.utc).isoformat()
        key = (project_id, screenplay_revision_id, target_type, target_record_id)
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM production_image_selections WHERE project_id=? AND screenplay_revision_id=? AND target_type=? AND target_record_id=?", key).fetchone()
            if row and row["asset_id"] == asset_id and row["job_id"] == job_id:
                db.commit()
                return {**dict(row), "replayed": True}
            if row and authority == "director":
                db.rollback()
                raise LedgerConflict("A Director-selected master already exists for this target; automatic review cannot replace it.")
            prior_asset_id = row["asset_id"] if row else None
            db.execute("""INSERT INTO production_image_selection_history
                (project_id,screenplay_revision_id,target_type,target_record_id,prior_asset_id,
                 asset_id,job_id,authority,decision_json,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (*key, prior_asset_id, asset_id, job_id, authority, decision_json, now))
            db.execute("""INSERT INTO production_image_selections
                (project_id,screenplay_revision_id,target_type,target_record_id,asset_id,job_id,
                 authority,decision_json,updated_at) VALUES(?,?,?,?,?,?,?,?,?)
                ON CONFLICT(project_id,screenplay_revision_id,target_type,target_record_id)
                DO UPDATE SET asset_id=excluded.asset_id,job_id=excluded.job_id,
                    authority=excluded.authority,decision_json=excluded.decision_json,
                    updated_at=excluded.updated_at""",
                (*key, asset_id, job_id, authority, decision_json, now))
            selected = db.execute("SELECT * FROM production_image_selections WHERE project_id=? AND screenplay_revision_id=? AND target_type=? AND target_record_id=?", key).fetchone()
            db.commit()
            return {**dict(selected), "replayed": False}

    def get(self, *, project_id: str, screenplay_revision_id: str,
            target_type: str, target_record_id: str) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute("SELECT * FROM production_image_selections WHERE project_id=? AND screenplay_revision_id=? AND target_type=? AND target_record_id=?",
                (project_id, screenplay_revision_id, target_type, target_record_id)).fetchone()
        return dict(row) if row else None
