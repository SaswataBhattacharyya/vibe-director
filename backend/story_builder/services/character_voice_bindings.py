"""Workspace-scoped voice bindings for canonical screenplay characters."""
from __future__ import annotations

import json
import hashlib
import re
from contextlib import contextmanager

from story_builder.services.production_ledger import LedgerConflict
from story_builder.services.media_library import list_assets


@contextmanager
def _connection(ledger):
    db = ledger._connect()
    try:
        yield db
    finally:
        db.close()


class CharacterVoiceBindings:
    def __init__(self, ledger, root, story, production_setup):
        self.ledger = ledger
        self.root = root
        self.story = story
        self.production_setup = production_setup
        with _connection(ledger) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS story_character_voice_bindings (
                workspace_id TEXT NOT NULL, screenplay_revision_id TEXT NOT NULL,
                character_id TEXT NOT NULL, voice_asset_id TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(workspace_id, screenplay_revision_id, character_id)
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS story_character_voice_auto_decisions (
                workspace_id TEXT NOT NULL, screenplay_revision_id TEXT NOT NULL,
                character_id TEXT NOT NULL, status TEXT NOT NULL, voice_asset_id TEXT,
                candidate_asset_ids_json TEXT NOT NULL, library_sha256 TEXT NOT NULL,
                reason TEXT NOT NULL, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(workspace_id, screenplay_revision_id, character_id)
            )""")

    def _context(self, workspace_id: str, screenplay_revision_id: str):
        revision = self.story.get_screenplay_revision(workspace_id, screenplay_revision_id)
        if not revision.get("accepted"):
            raise LedgerConflict("Voice assignments require the current accepted screenplay.")
        graph = self.story.get_story_graph(workspace_id=workspace_id, snapshot_id=revision["graph_snapshot_id"])
        if graph.get("status") != "complete":
            raise LedgerConflict("Voice assignments require the complete graph used by the accepted screenplay.")
        characters = [record for record in graph.get("records", [])
            if record.get("kind") == "entity" and record.get("type") == "character"]
        return revision, graph, characters

    def get(self, workspace_id: str, screenplay_revision_id: str):
        revision, graph, characters = self._context(workspace_id, screenplay_revision_id)
        speaking_ids, has_dialogue = self._speaking_character_ids(revision, characters)
        if not isinstance(revision.get("screenplay"), dict):
            speech_statuses = [{"character_id": row["record_id"], "status": "unknown",
                "reason": "The accepted screenplay's dialogue data is unavailable."} for row in characters]
        elif not has_dialogue:
            speech_statuses = [{"character_id": row["record_id"], "status": "not_speaking",
                "reason": "The accepted screenplay contains no dialogue; a voice is optional."} for row in characters]
        elif speaking_ids is None:
            speech_statuses = [{"character_id": row["record_id"], "status": "unknown",
                "reason": "Dialogue is present, but no speaker label maps to a canonical character."} for row in characters]
        else:
            speech_statuses = []
            for row in characters:
                is_speaking = row["record_id"] in speaking_ids
                is_narrator = is_speaking and re.sub(r"\s+", " ", str(row.get("name") or "").casefold()).strip() == "narrator"
                speech_statuses.append({"character_id": row["record_id"],
                    "status": "narrator" if is_narrator else "speaking" if is_speaking else "not_speaking",
                    "reason": "Narrator has labeled dialogue." if is_narrator else
                        "Labeled dialogue is present." if is_speaking else
                        "This character has no labeled dialogue in the accepted screenplay; a voice is optional."})
        with _connection(self.ledger) as db:
            rows = db.execute("SELECT character_id,voice_asset_id,updated_at FROM story_character_voice_bindings WHERE workspace_id=? AND screenplay_revision_id=?",
                (workspace_id, screenplay_revision_id)).fetchall()
        return {"workspace_id": workspace_id, "screenplay_revision_id": screenplay_revision_id,
            "graph_snapshot_id": graph["snapshot_id"], "characters": characters,
            "bindings": [dict(row) for row in rows], "speech_statuses": speech_statuses,
            "automation_decisions": self._decisions(workspace_id, screenplay_revision_id)}

    def _decisions(self, workspace_id, screenplay_revision_id):
        with _connection(self.ledger) as db:
            rows = db.execute("""SELECT character_id,status,voice_asset_id,candidate_asset_ids_json,
                reason,updated_at FROM story_character_voice_auto_decisions
                WHERE workspace_id=? AND screenplay_revision_id=?""",
                (workspace_id, screenplay_revision_id)).fetchall()
        return [{**dict(row), "candidate_asset_ids": json.loads(row["candidate_asset_ids_json"])}
            for row in rows]

    @classmethod
    def _explicit_voice_hints(cls, character):
        properties = character.get("properties") if isinstance(character.get("properties"), dict) else {}
        hints = [character.get("name", "")]
        for key in ("voice", "voice_style", "voice_description", "voice_guidance", "voice_reference"):
            value = properties.get(key)
            if isinstance(value, str) and value.strip():
                hints.append(value.strip())
        return [hint for hint in hints if isinstance(hint, str) and hint.strip()]

    @classmethod
    def _matching_assets(cls, character, assets):
        hints = cls._explicit_voice_hints(character)
        matches = []
        for asset in assets:
            if asset.get("audio_category") not in (None, "voice"):
                continue
            searchable = " ".join([asset.get("filename", ""), asset.get("description", ""),
                asset.get("provenance_notes", ""), *asset.get("tags", [])])
            normalized = " " + " ".join(re.findall(r"[a-z0-9]+", searchable.casefold())) + " "
            if any((phrase := " ".join(re.findall(r"[a-z0-9]+", hint.casefold())))
                   and f" {phrase} " in normalized for hint in hints):
                matches.append(asset)
        return matches

    @staticmethod
    def _speaking_character_ids(revision, characters):
        screenplay = revision.get("screenplay")
        if not isinstance(screenplay, dict):
            return None, False
        lines = []
        for scene in screenplay.get("scenes", []):
            for shot in scene.get("shots", []):
                dialogue = shot.get("dialogue") if isinstance(shot, dict) else None
                if isinstance(dialogue, str) and dialogue.strip():
                    lines.extend(line.strip() for line in dialogue.splitlines() if line.strip())
        if not lines:
            return set(), False
        by_name = {re.sub(r"\s+", " ", row.get("name", "").casefold()).strip(): row["record_id"]
            for row in characters}
        speakers = set()
        for line in lines:
            label, separator, _text = line.partition(":")
            if not separator:
                continue
            label = re.sub(r"\s*\([^)]*\)\s*$", "", label).strip()
            record_id = by_name.get(re.sub(r"\s+", " ", label.casefold()).strip())
            if record_id:
                speakers.add(record_id)
        return (speakers or None), True

    def run_automatic(self, workspace_id: str, screenplay_revision_id: str):
        """Bind only an unambiguous, explicit metadata match; leave the rest for review."""
        _revision, _graph, characters = self._context(workspace_id, screenplay_revision_id)
        speaking_ids, has_dialogue = self._speaking_character_ids(_revision, characters)
        with _connection(self.ledger) as db:
            setup_row = db.execute("SELECT setup_json FROM story_production_setups WHERE workspace_id=? AND screenplay_revision_id=?",
                (workspace_id, screenplay_revision_id)).fetchone()
        setup = json.loads(setup_row["setup_json"]) if setup_row else None
        if (not isinstance(setup, dict) or setup.get("mode") != "assisted_manual"
                or setup.get("automate_steps", {}).get("character_voice") is not True):
            raise LedgerConflict("Enable Character-to-audio selection in Assisted manual before running automatic matching.")
        assets = []
        offset = 0
        while True:
            page = list_assets(self.root, workspace_id, kind="audio", limit=100, offset=offset)
            assets.extend(asset for asset in page["assets"] if "voice_master" in asset.get("roles", []))
            if not page["assets"] or offset + len(page["assets"]) >= page["total"]:
                break
            offset += len(page["assets"])
        library_sha256 = hashlib.sha256(json.dumps(assets, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        with _connection(self.ledger) as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                revision, _current_graph, current_characters = self._context(workspace_id, screenplay_revision_id)
                self.production_setup._accepted_revision(db, workspace_id, screenplay_revision_id)
                setup_row = db.execute("SELECT setup_json FROM story_production_setups WHERE workspace_id=? AND screenplay_revision_id=?",
                    (workspace_id, screenplay_revision_id)).fetchone()
                setup = json.loads(setup_row["setup_json"]) if setup_row else None
                if (not isinstance(setup, dict) or setup.get("mode") != "assisted_manual"
                        or setup.get("automate_steps", {}).get("character_voice") is not True):
                    raise LedgerConflict("Enable Character-to-audio selection in Assisted manual before running automatic matching.")
                character_by_id = {row["record_id"]: row for row in current_characters}
                completed = []
                for character_id, character in character_by_id.items():
                    bound = db.execute("SELECT voice_asset_id FROM story_character_voice_bindings WHERE workspace_id=? AND screenplay_revision_id=? AND character_id=?",
                        (workspace_id, screenplay_revision_id, character_id)).fetchone()
                    previous = db.execute("SELECT status,voice_asset_id,candidate_asset_ids_json,reason FROM story_character_voice_auto_decisions WHERE workspace_id=? AND screenplay_revision_id=? AND character_id=?",
                        (workspace_id, screenplay_revision_id, character_id)).fetchone()
                    if previous and previous["status"] == "resolved_manually" and previous["voice_asset_id"] is None and not bound:
                        status, voice_id, candidate_ids, reason = "resolved_manually", None, [], previous["reason"]
                    elif bound:
                        if previous and previous["status"] in {"matched", "resolved_manually"}:
                            status, voice_id = previous["status"], bound["voice_asset_id"]
                            candidate_ids, reason = json.loads(previous["candidate_asset_ids_json"]), previous["reason"]
                        else:
                            status, voice_id, candidate_ids, reason = "kept", bound["voice_asset_id"], [bound["voice_asset_id"]], "Existing binding preserved."
                    elif speaking_ids is not None and not has_dialogue:
                        voice_id, status, candidate_ids = None, "not_speaking", []
                        reason = "The accepted screenplay contains no dialogue."
                    elif speaking_ids and character_id not in speaking_ids:
                        voice_id, status, candidate_ids = None, "not_speaking", []
                        reason = "This character has no labeled dialogue in the accepted screenplay."
                    elif speaking_ids is None and has_dialogue:
                        voice_id, status, candidate_ids = None, "unmatched", []
                        reason = "Dialogue is present, but no speaker label maps to a canonical character; choose manually."
                    else:
                        matches = self._matching_assets(character, assets)
                        candidate_ids = [row["asset_id"] for row in matches]
                        if len(matches) == 1:
                            voice_id, status, reason = matches[0]["asset_id"], "matched", "One voice asset explicitly names this character or matches its voice guidance."
                            db.execute("""INSERT INTO story_character_voice_bindings(workspace_id,screenplay_revision_id,character_id,voice_asset_id)
                                VALUES(?,?,?,?) ON CONFLICT(workspace_id,screenplay_revision_id,character_id)
                                DO NOTHING""", (workspace_id, screenplay_revision_id, character_id, voice_id))
                        elif matches:
                            voice_id, status, reason = None, "ambiguous", "More than one voice asset matches; choose one manually."
                        else:
                            voice_id, status, reason = None, "unmatched", "No voice asset explicitly matches; add identifying voice metadata or choose manually."
                    db.execute("""INSERT INTO story_character_voice_auto_decisions
                        (workspace_id,screenplay_revision_id,character_id,status,voice_asset_id,candidate_asset_ids_json,library_sha256,reason)
                        VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(workspace_id,screenplay_revision_id,character_id)
                        DO UPDATE SET status=excluded.status,voice_asset_id=excluded.voice_asset_id,
                        candidate_asset_ids_json=excluded.candidate_asset_ids_json,library_sha256=excluded.library_sha256,
                        reason=excluded.reason,updated_at=CURRENT_TIMESTAMP""",
                        (workspace_id, screenplay_revision_id, character_id, status, voice_id,
                         json.dumps(candidate_ids, separators=(",", ":")), library_sha256, reason))
                    completed.append({"character_id": character_id, "status": status,
                        "voice_asset_id": voice_id, "candidate_asset_ids": candidate_ids, "reason": reason})
                db.commit()
            except Exception:
                db.rollback()
                raise
        result = self.get(workspace_id, screenplay_revision_id)
        result["automation_result"] = completed
        return result

    def set(self, workspace_id: str, screenplay_revision_id: str, character_id: str, voice_asset_id: str | None):
        if voice_asset_id is not None:
            first = list_assets(self.root, workspace_id, kind="audio", limit=100, offset=0)
            voice = next((asset for asset in first["assets"] if asset["asset_id"] == voice_asset_id), None)
            offset = len(first["assets"])
            while voice is None and offset < first["total"]:
                page = list_assets(self.root, workspace_id, kind="audio", limit=100, offset=offset)
                voice = next((asset for asset in page["assets"] if asset["asset_id"] == voice_asset_id), None)
                if not page["assets"]:
                    break
                offset += len(page["assets"])
            if voice is None or "voice_master" not in voice.get("roles", []):
                raise ValueError("Choose an audio asset marked as a voice reference in this workspace.")
        with _connection(self.ledger) as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                # Keep this check under the same write lock as the binding mutation.
                _revision, _graph, characters = self._context(workspace_id, screenplay_revision_id)
                if not isinstance(character_id, str) or character_id not in {row["record_id"] for row in characters}:
                    raise LedgerConflict("Select a character in the current accepted graph.")
                setup_row = db.execute("SELECT setup_json FROM story_production_setups WHERE workspace_id=? AND screenplay_revision_id=?",
                    (workspace_id, screenplay_revision_id)).fetchone()
                setup = json.loads(setup_row["setup_json"]) if setup_row else None
                decision = db.execute("SELECT status FROM story_character_voice_auto_decisions WHERE workspace_id=? AND screenplay_revision_id=? AND character_id=?",
                    (workspace_id, screenplay_revision_id, character_id)).fetchone()
                if isinstance(setup, dict) and setup.get("mode") == "assisted_manual" and setup.get("automate_steps", {}).get("character_voice") is True:
                    if not decision:
                        raise LedgerConflict("Character-to-audio selection is configured for automation; run automatic matching before editing character voices.")
                    db.execute("UPDATE story_character_voice_auto_decisions SET status='resolved_manually',voice_asset_id=?,reason='Director set or cleared this voice assignment.',updated_at=CURRENT_TIMESTAMP WHERE workspace_id=? AND screenplay_revision_id=? AND character_id=?",
                        (voice_asset_id, workspace_id, screenplay_revision_id, character_id))
                else:
                    self.production_setup.require_manual_step(db, workspace_id, screenplay_revision_id, "character_voice")
                if voice_asset_id is None:
                    db.execute("DELETE FROM story_character_voice_bindings WHERE workspace_id=? AND screenplay_revision_id=? AND character_id=?",
                        (workspace_id, screenplay_revision_id, character_id))
                else:
                    db.execute("""INSERT INTO story_character_voice_bindings(workspace_id,screenplay_revision_id,character_id,voice_asset_id)
                        VALUES(?,?,?,?) ON CONFLICT(workspace_id,screenplay_revision_id,character_id)
                        DO UPDATE SET voice_asset_id=excluded.voice_asset_id,updated_at=CURRENT_TIMESTAMP""",
                        (workspace_id, screenplay_revision_id, character_id, voice_asset_id))
                db.commit()
            except Exception:
                db.rollback()
                raise
        return self.get(workspace_id, screenplay_revision_id)
