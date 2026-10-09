"""CPU-only story source revisions and exact selected-text edit proposals.

This is a revision foundation, not the Codex collaborator, graph builder, or
screenplay derivation service. Revision files use the reused atomic V2 writer;
SQLite's story index/current pointer is authoritative for current state.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from story_builder.services.production_ledger import LedgerConflict, LedgerNotFound, ProductionLedger
from story_builder.services.production_story_revisions import load_revision, revision_root, write_revision
from story_builder.services.source_chunks import SourceChunk, split_source_text


_WORKSPACE_ID = re.compile(r"^story-[a-f0-9]{12}$")
_REVISION_ID = re.compile(r"^story-canon-[a-f0-9]{12}$")


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _check_workspace_id(value: Any) -> str:
    if type(value) is not str or not _WORKSPACE_ID.fullmatch(value):
        raise ValueError("Invalid story workspace identifier.")
    return value


def _check_revision_id(value: Any) -> str:
    if type(value) is not str or not _REVISION_ID.fullmatch(value):
        raise ValueError("Invalid story revision identifier.")
    return value


class StoryAuthoring:
    """Persist immutable story revisions and source-indexed chunks in V2 storage."""

    def __init__(self, ledger: ProductionLedger, *, data_root: Path, chunk_chars: int = 2400):
        if type(chunk_chars) is not int or chunk_chars < 128:
            raise ValueError("chunk_chars must be an integer of at least 128.")
        self.ledger = ledger
        self.data_root = Path(data_root).expanduser().resolve()
        self.data_root.mkdir(parents=True, exist_ok=True)
        self.chunk_chars = chunk_chars
        with ledger._connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS story_workspaces (
                    workspace_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    authoring_uuid TEXT NOT NULL UNIQUE,
                    current_revision_id TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS story_revision_index (
                    revision_id TEXT PRIMARY KEY,
                    workspace_id TEXT NOT NULL REFERENCES story_workspaces(workspace_id) ON DELETE CASCADE,
                    parent_revision_id TEXT,
                    revision_number INTEGER NOT NULL DEFAULT 1,
                    source_sha256 TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS story_revision_reservations (
                    revision_id TEXT PRIMARY KEY,
                    workspace_id TEXT NOT NULL REFERENCES story_workspaces(workspace_id) ON DELETE CASCADE,
                    state TEXT NOT NULL DEFAULT 'reserved',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS story_source_chunks (
                    revision_id TEXT NOT NULL REFERENCES story_revision_index(revision_id) ON DELETE CASCADE,
                    chunk_id TEXT NOT NULL,
                    start_codepoint INTEGER NOT NULL,
                    end_codepoint INTEGER NOT NULL,
                    sha256 TEXT NOT NULL,
                    PRIMARY KEY(revision_id, chunk_id)
                );
                CREATE TABLE IF NOT EXISTS story_edit_proposals (
                    proposal_id TEXT PRIMARY KEY,
                    workspace_id TEXT NOT NULL REFERENCES story_workspaces(workspace_id) ON DELETE CASCADE,
                    base_revision_id TEXT NOT NULL REFERENCES story_revision_index(revision_id),
                    start_codepoint INTEGER NOT NULL,
                    end_codepoint INTEGER NOT NULL,
                    expected_text TEXT NOT NULL,
                    replacement TEXT NOT NULL,
                    instruction TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    resulting_revision_id TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS story_edit_proposals_base_idx
                    ON story_edit_proposals(workspace_id, base_revision_id, status);
            """)
            revision_columns = {row["name"] for row in db.execute("PRAGMA table_info(story_revision_index)")}
            if "revision_number" not in revision_columns:
                db.execute("ALTER TABLE story_revision_index ADD COLUMN revision_number INTEGER NOT NULL DEFAULT 1")
                workspaces = db.execute("SELECT DISTINCT workspace_id FROM story_revision_index").fetchall()
                for item in workspaces:
                    rows = db.execute("SELECT revision_id FROM story_revision_index WHERE workspace_id=? ORDER BY created_at,revision_id",
                                      (item["workspace_id"],)).fetchall()
                    for number, revision in enumerate(rows, start=1):
                        db.execute("UPDATE story_revision_index SET revision_number=? WHERE revision_id=?",
                                   (number, revision["revision_id"]))
            db.execute("DROP INDEX IF EXISTS story_revision_workspace_idx")
            db.execute("CREATE INDEX IF NOT EXISTS story_revision_workspace_idx ON story_revision_index(workspace_id,revision_number)")
            db.execute("CREATE UNIQUE INDEX IF NOT EXISTS story_revision_number_idx ON story_revision_index(workspace_id,revision_number)")

    def create_workspace(self, *, title: str, source_text: str,
                         source_metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        if type(title) is not str or not title.strip():
            raise ValueError("Workspace title must contain non-whitespace text.")
        # Validate before making the workspace row; there is no story-length cap.
        split_source_text(source_text, max_chars=self.chunk_chars)
        workspace_id = f"story-{uuid.uuid4().hex[:12]}"
        authoring_uuid = str(uuid.uuid4())
        with self.ledger._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("INSERT INTO story_workspaces(workspace_id,title,authoring_uuid) VALUES(?,?,?)",
                       (workspace_id, title, authoring_uuid))
            db.commit()
        revision = self.initialize_workspace(workspace_id=workspace_id, source_text=source_text,
            metadata=source_metadata)
        return {"workspace_id": workspace_id, "title": title,
                "authoring_uuid": authoring_uuid, "current_revision": revision}

    def list_workspaces(self, *, limit: int = 50, offset: int = 0) -> dict[str, Any]:
        if type(limit) is not int or not 1 <= limit <= 100 or type(offset) is not int or offset < 0:
            raise ValueError("Pagination requires limit 1–100 and a nonnegative integer offset.")
        with self.ledger._connect() as db:
            total = db.execute("SELECT COUNT(*) FROM story_workspaces").fetchone()[0]
            rows = db.execute("SELECT w.*, (w.current_revision_id IS NOT NULL) AS initialized FROM story_workspaces w ORDER BY w.created_at DESC,w.workspace_id DESC LIMIT ? OFFSET ?",
                              (limit, offset)).fetchall()
        return {"items": [{"workspace_id": row["workspace_id"], "title": row["title"],
                            "authoring_uuid": row["authoring_uuid"],
                            "current_revision_id": row["current_revision_id"],
                            "initialized": bool(row["initialized"]),
                            "status": "ready" if row["initialized"] else "initializing",
                            "created_at": row["created_at"]} for row in rows],
                "limit": limit, "offset": offset, "total": total}

    def initialize_workspace(self, *, workspace_id: str, source_text: str,
                             metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        workspace_id = _check_workspace_id(workspace_id)
        with self.ledger._connect() as db:
            row = db.execute("SELECT current_revision_id FROM story_workspaces WHERE workspace_id=?",
                             (workspace_id,)).fetchone()
            count = db.execute("SELECT COUNT(*) FROM story_revision_index WHERE workspace_id=?",
                               (workspace_id,)).fetchone()[0]
        if row is None:
            raise LedgerNotFound("Story workspace not found.")
        if row["current_revision_id"] is not None or count:
            raise LedgerConflict("Story workspace is already initialized.")
        return self.write_revision(workspace_id=workspace_id, source_text=source_text,
            expected_current_revision_id=None, metadata=metadata or {"kind": "source_import"})

    def _reserve_revision_id(self, *, workspace_id: str, authoring_uuid: str) -> str:
        directory = revision_root(self.data_root, workspace_id, authoring_uuid)
        for _ in range(100):
            revision_id = f"story-canon-{uuid.uuid4().hex[:12]}"
            with self.ledger._connect() as db:
                db.execute("BEGIN IMMEDIATE")
                indexed = db.execute("SELECT 1 FROM story_revision_index WHERE revision_id=?", (revision_id,)).fetchone()
                if indexed:
                    db.rollback()
                    continue
                try:
                    db.execute("INSERT INTO story_revision_reservations(revision_id,workspace_id) VALUES(?,?)",
                               (revision_id, workspace_id))
                except sqlite3.IntegrityError:
                    db.rollback()
                    continue
                db.commit()
            destination = directory / f"{revision_id}.json"
            if destination.exists() or destination.is_symlink():
                with self.ledger._connect() as db:
                    db.execute("UPDATE story_revision_reservations SET state='collision' WHERE revision_id=?",
                               (revision_id,))
                continue
            return revision_id
        raise RuntimeError("Could not reserve a unique immutable story revision ID.")

    def get_workspace(self, workspace_id: str, *, include_source: bool = True) -> dict[str, Any]:
        workspace_id = _check_workspace_id(workspace_id)
        with self.ledger._connect() as db:
            row = db.execute("SELECT * FROM story_workspaces WHERE workspace_id=?", (workspace_id,)).fetchone()
        if row is None:
            raise LedgerNotFound("Story workspace not found.")
        result = {"workspace_id": row["workspace_id"], "title": row["title"],
                  "authoring_uuid": row["authoring_uuid"],
                  "current_revision_id": row["current_revision_id"],
                  "initialized": row["current_revision_id"] is not None,
                  "status": "ready" if row["current_revision_id"] is not None else "initializing",
                  "created_at": row["created_at"], "updated_at": row["updated_at"]}
        if include_source and row["current_revision_id"]:
            result["current_revision"] = self.get_revision(workspace_id, row["current_revision_id"])
        return result

    def write_revision(self, *, workspace_id: str, source_text: str,
                       expected_current_revision_id: str | None,
                       metadata: dict[str, Any] | None = None,
                       _accept_proposal_id: str | None = None) -> dict[str, Any]:
        workspace_id = _check_workspace_id(workspace_id)
        if type(source_text) is not str or not source_text.strip():
            raise ValueError("Story source must contain non-whitespace text.")
        if expected_current_revision_id is not None:
            expected_current_revision_id = _check_revision_id(expected_current_revision_id)
        if metadata is not None and not isinstance(metadata, dict):
            raise ValueError("Revision metadata must be an object.")
        chunks = split_source_text(source_text, max_chars=self.chunk_chars)
        chunk_rows = [{"chunk_id": chunk.chunk_id, "start": chunk.start, "end": chunk.end,
                       "sha256": _sha(chunk.text)} for chunk in chunks]
        with self.ledger._connect() as db:
            workspace = db.execute("SELECT * FROM story_workspaces WHERE workspace_id=?", (workspace_id,)).fetchone()
        if workspace is None:
            raise LedgerNotFound("Story workspace not found.")
        if workspace["current_revision_id"] != expected_current_revision_id:
            raise LedgerConflict("Story changed since this edit was prepared; reload before applying it.")
        authoring_uuid = workspace["authoring_uuid"]
        if expected_current_revision_id is None:
            revision_number = 1
        else:
            with self.ledger._connect() as db:
                parent = db.execute("SELECT revision_number FROM story_revision_index WHERE workspace_id=? AND revision_id=?",
                                    (workspace_id, expected_current_revision_id)).fetchone()
            if parent is None:
                raise LedgerConflict("Expected current story revision is not indexed in this workspace.")
            revision_number = int(parent["revision_number"]) + 1
        revision_id = self._reserve_revision_id(workspace_id=workspace_id, authoring_uuid=authoring_uuid)
        revision = {"revision_id": revision_id, "workspace_id": workspace_id,
                    "parent_revision_id": expected_current_revision_id,
                    "revision_number": revision_number,
                    "source_sha256": _sha(source_text), "source_text": source_text,
                    "source_chunks": chunk_rows, "metadata": metadata or {}}
        # Write immutable content before committing its authoritative index and
        # pointer. A losing optimistic writer may leave an unindexed safe orphan.
        write_revision(self.data_root, workspace_id, authoring_uuid, revision)
        try:
            with self.ledger._connect() as db:
                db.execute("BEGIN IMMEDIATE")
                current = db.execute("SELECT current_revision_id FROM story_workspaces WHERE workspace_id=?",
                                     (workspace_id,)).fetchone()
                if current is None:
                    raise LedgerNotFound("Story workspace not found.")
                if current["current_revision_id"] != expected_current_revision_id:
                    raise LedgerConflict("Story changed since this edit was prepared; reload before applying it.")
                if _accept_proposal_id is not None:
                    proposal = db.execute("SELECT * FROM story_edit_proposals WHERE proposal_id=? AND workspace_id=?",
                                          (_accept_proposal_id, workspace_id)).fetchone()
                    if proposal is None or proposal["status"] != "pending" or proposal["base_revision_id"] != expected_current_revision_id:
                        raise LedgerConflict("Edit proposal is stale or no longer pending.")
                db.execute("INSERT INTO story_revision_index(revision_id,workspace_id,parent_revision_id,revision_number,source_sha256,metadata_json) VALUES(?,?,?,?,?,?)",
                           (revision_id, workspace_id, expected_current_revision_id, revision_number,
                            revision["source_sha256"], json.dumps(metadata or {}, sort_keys=True, ensure_ascii=False)))
                db.executemany("INSERT INTO story_source_chunks(revision_id,chunk_id,start_codepoint,end_codepoint,sha256) VALUES(?,?,?,?,?)",
                               [(revision_id, chunk["chunk_id"], chunk["start"], chunk["end"], chunk["sha256"])
                                for chunk in chunk_rows])
                updated = db.execute("UPDATE story_workspaces SET current_revision_id=?,updated_at=CURRENT_TIMESTAMP WHERE workspace_id=? AND current_revision_id IS ?",
                                     (revision_id, workspace_id, expected_current_revision_id))
                if updated.rowcount != 1:
                    raise LedgerConflict("Story changed since this edit was prepared; reload before applying it.")
                if _accept_proposal_id is not None:
                    changed = db.execute("UPDATE story_edit_proposals SET status='accepted',resulting_revision_id=?,updated_at=CURRENT_TIMESTAMP WHERE proposal_id=? AND status='pending'",
                                         (revision_id, _accept_proposal_id))
                    if changed.rowcount != 1:
                        raise LedgerConflict("Edit proposal was already accepted or withdrawn.")
                db.execute("UPDATE story_revision_reservations SET state='committed' WHERE revision_id=?",
                           (revision_id,))
                db.commit()
        except Exception:
            with self.ledger._connect() as db:
                db.execute("UPDATE story_revision_reservations SET state='orphaned' WHERE revision_id=? AND state='reserved'",
                           (revision_id,))
            raise
        return self.get_revision(workspace_id, revision_id)

    def get_revision(self, workspace_id: str, revision_id: str) -> dict[str, Any]:
        workspace_id = _check_workspace_id(workspace_id)
        revision_id = _check_revision_id(revision_id)
        with self.ledger._connect() as db:
            row = db.execute("SELECT r.*,w.authoring_uuid FROM story_revision_index r JOIN story_workspaces w USING(workspace_id) WHERE r.workspace_id=? AND r.revision_id=?",
                             (workspace_id, revision_id)).fetchone()
            chunks = db.execute("SELECT chunk_id,start_codepoint,end_codepoint,sha256 FROM story_source_chunks WHERE revision_id=? ORDER BY start_codepoint",
                                (revision_id,)).fetchall()
        if row is None:
            raise LedgerNotFound("Story revision not found.")
        value = load_revision(self.data_root, workspace_id, row["authoring_uuid"], revision_id)
        if (value is None or value.get("workspace_id") != workspace_id
                or value.get("parent_revision_id") != row["parent_revision_id"]
                or value.get("revision_number", row["revision_number"]) != row["revision_number"]
                or value.get("source_sha256") != row["source_sha256"]
                or value.get("metadata") != json.loads(row["metadata_json"])):
            raise ValueError("Stored story revision is missing or its indexed hash does not match.")
        source = value.get("source_text")
        if type(source) is not str or _sha(source) != row["source_sha256"]:
            raise ValueError("Stored story source failed its integrity check.")
        checked = []
        cursor = 0
        for chunk in chunks:
            start, end = chunk["start_codepoint"], chunk["end_codepoint"]
            if type(start) is not int or type(end) is not int or start != cursor or end <= start or end > len(source):
                raise ValueError("Stored source chunk coverage has a gap, overlap, or invalid range.")
            text = source[start:end]
            if _sha(text) != chunk["sha256"]:
                raise ValueError("Stored source chunk hash does not match its indexed range.")
            checked.append(SourceChunk(chunk["chunk_id"], len(checked) + 1, start, end, text))
            cursor = end
        if not checked or cursor != len(source):
            raise ValueError("Stored source chunk index does not cover the full source.")
        value["source_chunks"] = [chunk.__dict__ for chunk in checked]
        value["parent_revision_id"] = row["parent_revision_id"]
        value["revision_number"] = row["revision_number"]
        value["metadata"] = json.loads(row["metadata_json"])
        return value

    def list_revisions(self, workspace_id: str, *, limit: int = 50, offset: int = 0) -> dict[str, Any]:
        workspace_id = _check_workspace_id(workspace_id)
        if type(limit) is not int or not 1 <= limit <= 100 or type(offset) is not int or offset < 0:
            raise ValueError("Pagination requires limit 1–100 and a nonnegative integer offset.")
        with self.ledger._connect() as db:
            exists = db.execute("SELECT 1 FROM story_workspaces WHERE workspace_id=?", (workspace_id,)).fetchone()
            if not exists:
                raise LedgerNotFound("Story workspace not found.")
            total = db.execute("SELECT COUNT(*) FROM story_revision_index WHERE workspace_id=?", (workspace_id,)).fetchone()[0]
            rows = db.execute("SELECT revision_id,parent_revision_id,revision_number,source_sha256,metadata_json,created_at FROM story_revision_index WHERE workspace_id=? ORDER BY revision_number DESC LIMIT ? OFFSET ?",
                              (workspace_id, limit, offset)).fetchall()
        return {"items": [{"revision_id": row["revision_id"],
                            "parent_revision_id": row["parent_revision_id"],
                            "revision_number": row["revision_number"],
                            "source_sha256": row["source_sha256"],
                            "metadata": json.loads(row["metadata_json"]),
                            "created_at": row["created_at"]} for row in rows],
                "limit": limit, "offset": offset, "total": total}

    def restore_revision(self, *, workspace_id: str, revision_id: str,
                         expected_current_revision_id: str) -> dict[str, Any]:
        source = self.get_revision(workspace_id, revision_id)
        return self.write_revision(workspace_id=workspace_id, source_text=source["source_text"],
            expected_current_revision_id=expected_current_revision_id,
            metadata={"kind": "restore", "restored_from_revision_id": revision_id})

    def propose_selected_edit(self, *, workspace_id: str, base_revision_id: str,
                              start_codepoint: int, end_codepoint: int,
                              expected_text: str, replacement: str,
                              instruction: str = "") -> dict[str, Any]:
        workspace_id = _check_workspace_id(workspace_id)
        base_revision_id = _check_revision_id(base_revision_id)
        if type(start_codepoint) is not int or type(end_codepoint) is not int:
            raise ValueError("Edit offsets must be integer Unicode code-point indexes.")
        if type(expected_text) is not str or type(replacement) is not str or type(instruction) is not str:
            raise ValueError("Expected text, replacement and instruction must be strings.")
        base = self.get_revision(workspace_id, base_revision_id)
        source = base["source_text"]
        if not 0 <= start_codepoint <= end_codepoint <= len(source):
            raise ValueError("Selected edit range is outside the base revision.")
        if source[start_codepoint:end_codepoint] != expected_text:
            raise LedgerConflict("Selected text does not match the exact quote in the base revision.")
        proposal_id = str(uuid.uuid4())
        with self.ledger._connect() as db:
            db.execute("INSERT INTO story_edit_proposals(proposal_id,workspace_id,base_revision_id,start_codepoint,end_codepoint,expected_text,replacement,instruction) VALUES(?,?,?,?,?,?,?,?)",
                       (proposal_id, workspace_id, base_revision_id, start_codepoint,
                        end_codepoint, expected_text, replacement, instruction))
        return {"proposal_id": proposal_id, "workspace_id": workspace_id,
                "base_revision_id": base_revision_id, "start_codepoint": start_codepoint,
                "end_codepoint": end_codepoint, "expected_text": expected_text,
                "replacement": replacement, "instruction": instruction,
                "status": "pending", "ai_generated": False}

    def accept_selected_edit(self, *, workspace_id: str, proposal_id: str,
                             expected_current_revision_id: str) -> dict[str, Any]:
        workspace_id = _check_workspace_id(workspace_id)
        expected_current_revision_id = _check_revision_id(expected_current_revision_id)
        try:
            proposal_uuid = str(uuid.UUID(proposal_id))
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError("Invalid edit proposal identifier.") from exc
        with self.ledger._connect() as db:
            proposal = db.execute("SELECT * FROM story_edit_proposals WHERE proposal_id=? AND workspace_id=?",
                                  (proposal_uuid, workspace_id)).fetchone()
        if proposal is None:
            raise LedgerNotFound("Selected edit proposal not found.")
        if proposal["status"] != "pending" or proposal["base_revision_id"] != expected_current_revision_id:
            raise LedgerConflict("Selected edit proposal is stale or no longer pending.")
        base = self.get_revision(workspace_id, expected_current_revision_id)
        start, end = proposal["start_codepoint"], proposal["end_codepoint"]
        source = base["source_text"]
        if source[start:end] != proposal["expected_text"]:
            raise LedgerConflict("Selected text changed; review the current story before applying.")
        edited = source[:start] + proposal["replacement"] + source[end:]
        return self.write_revision(workspace_id=workspace_id, source_text=edited,
            expected_current_revision_id=expected_current_revision_id,
            metadata={"kind": "selected_text_edit", "proposal_id": proposal_uuid},
            _accept_proposal_id=proposal_uuid)

    def get_edit_proposal(self, *, workspace_id: str, proposal_id: str) -> dict[str, Any]:
        workspace_id = _check_workspace_id(workspace_id)
        try:
            proposal_uuid = str(uuid.UUID(proposal_id))
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError("Invalid edit proposal identifier.") from exc
        with self.ledger._connect() as db:
            row = db.execute("SELECT * FROM story_edit_proposals WHERE workspace_id=? AND proposal_id=?",
                             (workspace_id, proposal_uuid)).fetchone()
        if row is None:
            raise LedgerNotFound("Selected edit proposal not found.")
        return {key: row[key] for key in ("proposal_id", "workspace_id", "base_revision_id",
                "start_codepoint", "end_codepoint", "expected_text", "replacement",
                "instruction", "status", "resulting_revision_id", "created_at", "updated_at")}
