"""Durable, preview-only selected-text suggestions for non-story fields."""
from __future__ import annotations

import hashlib
import json
import uuid
from contextlib import contextmanager

from story_builder.services.production_ledger import LedgerConflict, LedgerNotFound


@contextmanager
def _connection(ledger):
    db = ledger._connect()
    try:
        yield db
    finally:
        db.close()


class FieldEditProposals:
    """Key provider calls by exact field revision and selection; never auto-apply."""
    SURFACES = {"screenplay", "prompt"}

    def __init__(self, ledger):
        self.ledger = ledger
        with _connection(ledger) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS story_field_edit_requests (
                idempotency_key TEXT PRIMARY KEY, workspace_id TEXT NOT NULL,
                request_hash TEXT NOT NULL, request_json TEXT NOT NULL,
                status TEXT NOT NULL, response_json TEXT, error_message TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""")

    @classmethod
    def _validate(cls, workspace_id, payload):
        required = {"surface", "revision_id", "field_key", "field_text", "start_codepoint",
                    "end_codepoint", "expected_text", "instruction", "idempotency_key"}
        if not isinstance(payload, dict) or set(payload) != required:
            raise ValueError("Selected edit request has missing or unexpected fields.")
        if payload["surface"] not in cls.SURFACES:
            raise ValueError("Selected edit surface is unsupported.")
        for key in ("revision_id", "field_key", "field_text", "expected_text", "instruction", "idempotency_key"):
            if type(payload[key]) is not str:
                raise ValueError(f"{key} must be text.")
        if not payload["revision_id"] or not payload["field_key"] or not payload["idempotency_key"]:
            raise ValueError("Revision, field and request identifiers are required.")
        if not payload["instruction"].strip() or len(payload["instruction"]) > 4000:
            raise ValueError("Instruction must contain 1–4000 characters.")
        start, end, text = payload["start_codepoint"], payload["end_codepoint"], payload["field_text"]
        if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(text):
            raise ValueError("Selected text range is invalid.")
        if text[start:end] != payload["expected_text"]:
            raise LedgerConflict("Selected text no longer matches this field. Select it again.")

    def propose(self, workspace_id, payload, provider_call):
        self._validate(workspace_id, payload)
        canonical = json.dumps({"workspace_id": workspace_id, **payload}, ensure_ascii=False,
                               sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(canonical.encode()).hexdigest()
        key = payload["idempotency_key"]
        with _connection(self.ledger) as db:
            db.execute("BEGIN IMMEDIATE")
            prior = db.execute("SELECT * FROM story_field_edit_requests WHERE idempotency_key=?", (key,)).fetchone()
            if prior:
                if prior["workspace_id"] != workspace_id or prior["request_hash"] != digest:
                    raise LedgerConflict("This edit request key belongs to different content.")
                db.commit()
                if prior["status"] == "complete":
                    return json.loads(prior["response_json"])
                raise LedgerConflict("This edit may already have reached the model. Start a new request after checking its status.")
            db.execute("INSERT INTO story_field_edit_requests(idempotency_key,workspace_id,request_hash,request_json,status) VALUES(?,?,?,?, 'in_progress')",
                       (key, workspace_id, digest, canonical))
            db.commit()
        try:
            result = provider_call(field_text=payload["field_text"], expected_text=payload["expected_text"], instruction=payload["instruction"],
                                   surface=payload["surface"], field_key=payload["field_key"])
            replacement = result.get("replacement") if isinstance(result, dict) else None
            if type(replacement) is not str or not replacement.strip():
                raise ValueError("Model returned no replacement text.")
            response = {"proposal_id": str(uuid.uuid4()), "workspace_id": workspace_id,
                "surface": payload["surface"], "revision_id": payload["revision_id"],
                "field_key": payload["field_key"], "field_sha256": hashlib.sha256(payload["field_text"].encode()).hexdigest(),
                "start_codepoint": payload["start_codepoint"], "end_codepoint": payload["end_codepoint"],
                "expected_text": payload["expected_text"], "replacement": replacement,
                "explanation": result.get("explanation", "")[:1000], "status": "pending"}
            with _connection(self.ledger) as db:
                changed = db.execute("UPDATE story_field_edit_requests SET status='complete',response_json=?,updated_at=CURRENT_TIMESTAMP WHERE idempotency_key=? AND status='in_progress'",
                                     (json.dumps(response, ensure_ascii=False), key))
                if changed.rowcount != 1:
                    raise LedgerConflict("Edit request changed while the model was working.")
            return response
        except Exception as exc:
            with _connection(self.ledger) as db:
                db.execute("UPDATE story_field_edit_requests SET status='failed',error_message=?,updated_at=CURRENT_TIMESTAMP WHERE idempotency_key=? AND status='in_progress'", (str(exc)[:500], key))
            raise

    def get_by_key(self, key):
        with _connection(self.ledger) as db:
            row = db.execute("SELECT * FROM story_field_edit_requests WHERE idempotency_key=?", (key,)).fetchone()
        if row is None:
            raise LedgerNotFound("Selected edit request not found.")
        value = {"idempotency_key": key, "workspace_id": row["workspace_id"], "status": row["status"]}
        if row["response_json"]:
            value["proposal"] = json.loads(row["response_json"])
        if row["status"] in {"in_progress", "failed"}:
            value["recovery_message"] = "The model request may have been submitted; this key cannot be resubmitted."
        return value
