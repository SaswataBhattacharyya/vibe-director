"""Immutable, source-linked workflow knowledge snapshots.

This is a small SQLite-backed graph store, not a runtime capability check. Its
facts describe the selected workflow's prompt contract and reference rules;
the caller must still check whether the graph, models, nodes, worker and GPU
are available before submitting a job.
"""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from story_builder.services.production_ledger import ProductionLedger, stable_hash

_ID = re.compile(r"^[a-z][a-z0-9_.:-]{1,127}$")
_SHA = re.compile(r"^[a-f0-9]{64}$")


class WorkflowKnowledgeError(ValueError):
    pass


@contextmanager
def _connection(ledger: ProductionLedger):
    db = ledger._connect()
    try:
        yield db
    finally:
        db.close()


class WorkflowKnowledge:
    """Append-only workflow records with typed facts, evidence and graph links."""

    def __init__(self, ledger: ProductionLedger) -> None:
        self.ledger = ledger
        with _connection(ledger) as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS workflow_knowledge_snapshots (
                    knowledge_id TEXT PRIMARY KEY,
                    model_id TEXT NOT NULL,
                    workflow_id TEXT NOT NULL,
                    workflow_version TEXT NOT NULL,
                    guidance_version INTEGER NOT NULL,
                    workflow_sha256 TEXT NOT NULL,
                    graph_json TEXT NOT NULL,
                    graph_sha256 TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(model_id, workflow_id, guidance_version)
                );
                CREATE INDEX IF NOT EXISTS workflow_knowledge_lookup_idx
                    ON workflow_knowledge_snapshots(model_id, workflow_id, guidance_version DESC);
                CREATE TRIGGER IF NOT EXISTS workflow_knowledge_no_update
                    BEFORE UPDATE ON workflow_knowledge_snapshots BEGIN
                    SELECT RAISE(ABORT, 'workflow knowledge snapshots are immutable'); END;
                CREATE TRIGGER IF NOT EXISTS workflow_knowledge_no_delete
                    BEFORE DELETE ON workflow_knowledge_snapshots BEGIN
                    SELECT RAISE(ABORT, 'workflow knowledge snapshots are immutable'); END;
                CREATE TRIGGER IF NOT EXISTS workflow_knowledge_no_replacement
                    BEFORE INSERT ON workflow_knowledge_snapshots
                    WHEN EXISTS (SELECT 1 FROM workflow_knowledge_snapshots
                        WHERE knowledge_id=NEW.knowledge_id
                        OR (model_id=NEW.model_id AND workflow_id=NEW.workflow_id
                            AND guidance_version=NEW.guidance_version))
                    BEGIN SELECT RAISE(ABORT, 'workflow knowledge snapshots are immutable'); END;
            """)

    @staticmethod
    def _validate_graph(model_id: str, workflow_id: str, workflow_version: str,
                        workflow_sha256: str, graph: dict[str, Any]) -> dict[str, Any]:
        for value, field in ((model_id, "model_id"), (workflow_id, "workflow_id")):
            if type(value) is not str or not _ID.fullmatch(value):
                raise WorkflowKnowledgeError(f"{field} must be a lowercase identifier.")
        if type(workflow_version) is not str or not workflow_version.strip() or len(workflow_version) > 80:
            raise WorkflowKnowledgeError("workflow_version must be non-empty text under 80 characters.")
        if type(workflow_sha256) is not str or not _SHA.fullmatch(workflow_sha256):
            raise WorkflowKnowledgeError("workflow_sha256 must be a lowercase SHA-256 digest.")
        if not isinstance(graph, dict) or set(graph) != {"sources", "nodes", "edges"}:
            raise WorkflowKnowledgeError("Graph must contain sources, nodes, and edges only.")
        sources = graph["sources"]
        nodes = graph["nodes"]
        edges = graph["edges"]
        if not isinstance(sources, list) or not sources or not isinstance(nodes, list) or not nodes or not isinstance(edges, list):
            raise WorkflowKnowledgeError("Graph needs source evidence and nodes; edges may be empty.")
        source_ids: set[str] = set()
        for source in sources:
            if (not isinstance(source, dict) or set(source) != {"source_id", "uri", "version", "section", "sha256"}
                    or type(source.get("source_id")) is not str or not _ID.fullmatch(source["source_id"])
                    or type(source.get("uri")) is not str or not source["uri"].strip()
                    or type(source.get("version")) is not str or not source["version"].strip()
                    or type(source.get("section")) is not str or not source["section"].strip()
                    or type(source.get("sha256")) is not str or not _SHA.fullmatch(source["sha256"])):
                raise WorkflowKnowledgeError("Every evidence source needs an ID, URI, version, section, and SHA-256.")
            if source["source_id"] in source_ids:
                raise WorkflowKnowledgeError("Evidence source IDs must be unique within a graph snapshot.")
            source_ids.add(source["source_id"])
        node_ids: set[str] = set()
        for node in nodes:
            if (not isinstance(node, dict) or set(node) != {"node_id", "kind", "text", "source_ids"}
                    or type(node.get("node_id")) is not str or not _ID.fullmatch(node["node_id"])
                    or type(node.get("kind")) is not str or not re.fullmatch(r"[a-z][a-z0-9_]{1,39}", node["kind"])
                    or type(node.get("text")) is not str or not node["text"].strip()
                    or not isinstance(node.get("source_ids"), list) or not node["source_ids"]
                    or any(source_id not in source_ids for source_id in node["source_ids"])):
                raise WorkflowKnowledgeError("Each knowledge node must be typed, source-linked text.")
            if node["node_id"] in node_ids:
                raise WorkflowKnowledgeError("Knowledge node IDs must be unique within a graph snapshot.")
            node_ids.add(node["node_id"])
        # A source digest covers the exact captured evidence statements linked
        # to that source (sorted by node ID). The URI/version/section pin the
        # upstream document; this digest makes our local capture tamper-evident.
        for source in sources:
            captured = "\n".join(sorted(node["text"] for node in nodes
                if source["source_id"] in node["source_ids"]))
            if hashlib.sha256(captured.encode("utf-8")).hexdigest() != source["sha256"]:
                raise WorkflowKnowledgeError(
                    f"Evidence digest does not match captured text for {source['source_id']}."
                )
        for edge in edges:
            if (not isinstance(edge, dict) or set(edge) != {"from", "relation", "to"}
                    or edge.get("from") not in node_ids or edge.get("to") not in node_ids
                    or type(edge.get("relation")) is not str
                    or not re.fullmatch(r"[a-z][a-z0-9_]{1,39}", edge["relation"])):
                raise WorkflowKnowledgeError("Edges must connect existing nodes with a named relation.")
        return json.loads(json.dumps(graph, ensure_ascii=False, sort_keys=True))

    def publish(self, *, model_id: str, workflow_id: str, workflow_version: str,
                workflow_sha256: str, graph: dict[str, Any]) -> dict[str, Any]:
        graph = self._validate_graph(model_id, workflow_id, workflow_version, workflow_sha256, graph)
        encoded = json.dumps(graph, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        graph_hash = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        now = datetime.now(timezone.utc).isoformat()
        with _connection(self.ledger) as db:
            db.execute("BEGIN IMMEDIATE")
            latest = db.execute("SELECT guidance_version,graph_sha256,workflow_version,workflow_sha256 FROM workflow_knowledge_snapshots WHERE model_id=? AND workflow_id=? ORDER BY guidance_version DESC LIMIT 1", (model_id, workflow_id)).fetchone()
            if (latest and latest["graph_sha256"] == graph_hash
                    and latest["workflow_version"] == workflow_version
                    and latest["workflow_sha256"] == workflow_sha256):
                existing = db.execute("SELECT * FROM workflow_knowledge_snapshots WHERE model_id=? AND workflow_id=? AND guidance_version=?",
                    (model_id, workflow_id, latest["guidance_version"])).fetchone()
                result = self._decode(existing)
                db.rollback()
                return result
            version = (latest["guidance_version"] if latest else 0) + 1
            knowledge_id = uuid.uuid4().hex
            db.execute("""INSERT INTO workflow_knowledge_snapshots
                (knowledge_id,model_id,workflow_id,workflow_version,guidance_version,workflow_sha256,graph_json,graph_sha256,created_at)
                VALUES(?,?,?,?,?,?,?,?,?)""", (knowledge_id, model_id, workflow_id, workflow_version,
                version, workflow_sha256, encoded, graph_hash, now))
            inserted = db.execute("SELECT * FROM workflow_knowledge_snapshots WHERE knowledge_id=?", (knowledge_id,)).fetchone()
            result = self._decode(inserted)
            db.commit()
        return result

    @staticmethod
    def _decode(row) -> dict[str, Any]:
        graph = json.loads(row["graph_json"])
        return {"knowledge_id": row["knowledge_id"], "model_id": row["model_id"],
            "workflow_id": row["workflow_id"], "workflow_version": row["workflow_version"],
            "guidance_version": row["guidance_version"], "workflow_sha256": row["workflow_sha256"],
            "graph_sha256": row["graph_sha256"], "created_at": row["created_at"],
            **graph, "retrieval_status": "matched"}

    def get(self, workflow_id: str, *, model_id: str) -> dict[str, Any]:
        if type(workflow_id) is not str or not _ID.fullmatch(workflow_id):
            raise WorkflowKnowledgeError("workflow_id must be a lowercase identifier.")
        if type(model_id) is not str or not _ID.fullmatch(model_id):
            raise WorkflowKnowledgeError("model_id must be a lowercase identifier.")
        with _connection(self.ledger) as db:
            row = db.execute("SELECT * FROM workflow_knowledge_snapshots WHERE workflow_id=? AND model_id=? ORDER BY guidance_version DESC LIMIT 1",
                (workflow_id, model_id)).fetchone()
        if row is None:
            return {"workflow_id": workflow_id, "model_id": model_id, "retrieval_status": "not_curated",
                "guidance_version": None, "sources": [], "nodes": [], "edges": []}
        return self._decode(row)

    def list_versions(self, workflow_id: str) -> list[dict[str, Any]]:
        if type(workflow_id) is not str or not _ID.fullmatch(workflow_id):
            raise WorkflowKnowledgeError("workflow_id must be a lowercase identifier.")
        with _connection(self.ledger) as db:
            rows = db.execute("SELECT * FROM workflow_knowledge_snapshots WHERE workflow_id=? ORDER BY model_id,guidance_version", (workflow_id,)).fetchall()
        return [self._decode(row) for row in rows]
