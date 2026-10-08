"""Story-free T2V job facade over the existing durable production ledger.

This module owns identity/snapshots only. It deliberately does not start a
worker, probe ComfyUI, submit a prompt, or delete media during construction.
"""
from __future__ import annotations

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
    IsolatedVideoContractError, canonical_request_hash,
    compile_preview, normalize_request,
)
from story_builder.services.minimax_h3_t2v import T2V_GRAPH_PATH
from story_builder.services.production_job_worker import PreparedTake, ProductionJobWorker
from story_builder.services.production_ledger import (
    LedgerConflict, LedgerNotFound, ProductionLedger, stable_hash,
)

_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$")
_WORKSPACE_NS = uuid.UUID("ec00c6b2-2bbb-4a36-9f50-755d47913f0e")


class IsolatedJobConflict(ValueError):
    """HTTP adapter should map this and LedgerConflict to 409."""


def _identifier(value: Any, name: str) -> str:
    if type(value) is not str or not _SAFE_ID.fullmatch(value):
        raise ValueError(f"{name} must be a safe 1–80 character identifier.")
    return value


class IsolatedVideoJobs:
    """Create/read jobs in the normal durable ledger with isolated aliases.

    `workspace_id` aliases the ledger's project_id; `clip_id` aliases shot_id.
    No screenplay, scene, or project-canon record is created.
    """

    def __init__(self, ledger: ProductionLedger, *, graph_path: Path | None = None):
        self.ledger = ledger
        self.graph_path = Path(graph_path).resolve() if graph_path is not None else T2V_GRAPH_PATH
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
            """)

    def validate(self, request: Mapping[str, Any]) -> dict[str, Any]:
        normalized = normalize_request(request, graph_path=self.graph_path)
        preview = compile_preview(normalized, graph_path=self.graph_path)
        return {"valid": True, "request_hash": canonical_request_hash(normalized),
                "normalized_request": normalized, "compiled_preview": preview}

    def create_job(self, *, workspace_id: str, clip_id: str, idempotency_key: str,
                   request: Mapping[str, Any], retake_of_job_id: str | None = None,
                   keep_original: bool | None = None) -> dict[str, Any]:
        workspace = _identifier(workspace_id, "workspace_id")
        clip = _identifier(clip_id, "clip_id")
        key = _identifier(idempotency_key, "idempotency_key")
        normalized = normalize_request(request, graph_path=self.graph_path)
        request_hash = canonical_request_hash(normalized)
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
        run = self.ledger.create_run(project_id=workspace, idempotency_key=workspace_run_key,
            config={"control_mode": "manual", "entry": "isolated", "workflow_id": normalized["workflow_id"],
                    "workflow_sha256": normalized["workflow_sha256"], "director_gates": "disabled"})
        internal_key = f"isolated:{key}"
        take_id = str(uuid.uuid5(_WORKSPACE_NS, f"{workspace}\0{key}"))
        retake_of = None if source_meta is None else retake_of_job_id
        attempt = 1 if source_meta is None else int(source_meta["attempt"]) + 1
        keep = None if keep_original is None else int(keep_original)

        def store_metadata(db, durable_take):
            saved = db.execute("SELECT * FROM isolated_video_jobs WHERE job_id=? OR (workspace_id=? AND idempotency_key=?)",
                (durable_take["job_id"], workspace, key)).fetchone()
            if saved is None:
                db.execute("INSERT INTO isolated_video_jobs(job_id,workspace_id,clip_id,idempotency_key,request_hash,request_json,retake_of_job_id,attempt,keep_original) VALUES(?,?,?,?,?,?,?,?,?)",
                    (durable_take["job_id"], workspace, clip, key, request_hash,
                     json.dumps(normalized, sort_keys=True, ensure_ascii=False), retake_of, attempt, keep))
                return
            if (saved["job_id"] != durable_take["job_id"] or saved["workspace_id"] != workspace
                    or saved["clip_id"] != clip or saved["request_hash"] != request_hash
                    or saved["idempotency_key"] != key or saved["retake_of_job_id"] != retake_of
                    or saved["keep_original"] != keep):
                raise IsolatedJobConflict("Idempotency key conflicts with the saved isolated job.")
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
            meta = db.execute("SELECT * FROM isolated_video_jobs WHERE job_id=?", (take["job_id"],)).fetchone()
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
        """Return editable snapshot only; this method never queues a take."""
        if type(keep_original) is not bool:
            raise ValueError("keep_original must be an explicit boolean choice.")
        take, meta = self._take_and_meta(job_id)
        if take["status"] not in {"needs_review", "accepted", "failed", "cancelled", "stale"}:
            raise IsolatedJobConflict("Retake draft is unavailable until the source job has a settled or reviewable result.")
        return {"source_job_id": job_id, "request": json.loads(meta["request_json"]),
                "keep_original": keep_original, "submission_created": False,
                "referenced_assets_deletion": "never_by_retake"}

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
        normalized = normalize_request(saved, graph_path=self.graph_path)
        # Preserve all saved fields, including seed, unless caller explicitly changes them.
        workspace, clip = source_meta["workspace_id"], source_meta["clip_id"]
        return self.create_job(workspace_id=workspace, clip_id=clip,
            idempotency_key=idempotency_key, request=normalized, retake_of_job_id=job_id,
            keep_original=keep_original)

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
            row = db.execute("SELECT t.*,m.workspace_id,m.clip_id,m.request_json,m.attempt,m.retake_of_job_id,m.keep_original,m.request_hash FROM production_takes t JOIN isolated_video_jobs m USING(job_id) WHERE t.job_id=?", (job_id,)).fetchone()
        if not row:
            raise LedgerNotFound("Isolated video job not found.")
        take = self.ledger._row(row)
        return take, row

    @staticmethod
    def _public_job(take: dict[str, Any], workspace_id: str, clip_id: str,
                    meta: Any | None = None, *, request_hash: str | None = None) -> dict[str, Any]:
        if meta is not None:
            request_hash = meta["request_hash"]
        outputs = []
        for item in take.get("output_hashes", []):
            if not isinstance(item, dict):
                continue
            asset_id = item.get("asset_id")
            outputs.append({key: item[key] for key in ("asset_id", "kind", "sha256", "duration_seconds", "has_video", "has_audio") if key in item}
                | ({"playback_url": f"/api/video/assets/{asset_id}"} if isinstance(asset_id, str) else {}))
        return {"job_id": take["job_id"], "workspace_id": workspace_id, "clip_id": clip_id,
            "status": take["status"], "request_hash": request_hash,
            "request": take["input_snapshot"], "engine_prompt_id": take.get("prompt_id"),
            "outputs": outputs, "error": take.get("error"),
            "created_at": take.get("created_at"), "updated_at": take.get("updated_at"),
            "retake_of_job_id": None if meta is None else meta["retake_of_job_id"],
            "attempt": 1 if meta is None else meta["attempt"],
            "keep_original": None if meta is None else (None if meta["keep_original"] is None else bool(meta["keep_original"]))}


def prepare_isolated_take(take: dict[str, Any], *, graph_path: Path | None = None) -> PreparedTake:
    """Compile a submitted immutable request with stable isolated output prefix."""
    request = take.get("input_snapshot")
    if not isinstance(request, dict):
        raise ValueError("Durable isolated request snapshot is missing.")
    if take.get("input_hash") != stable_hash(request):
        raise IsolatedVideoContractError("snapshot_hash_mismatch", "Durable input snapshot does not match its ledger hash.")
    preview = compile_preview(request, graph_path=graph_path)
    clip = str(take["shot_id"])
    ledger_take = str(take["take_id"])
    safe = lambda value: re.sub(r"[^A-Za-z0-9_-]", "_", str(value))
    graph = preview["graph"]
    prefix = f"isolated/{safe(take['project_id'])}/{safe(clip)}/{safe(ledger_take)}"
    for node in graph.values():
        if isinstance(node, dict) and node.get("class_type") == "SaveVideo":
            node.setdefault("inputs", {})["filename_prefix"] = prefix
    return PreparedTake(graph=graph, cleanup=lambda: None)


def build_worker(ledger: ProductionLedger, *, comfy_url: str,
                 collect: Callable[[dict[str, Any], dict[str, Any]], list[dict[str, Any]]],
                 graph_path: Path | None = None,
                 prepare_guard: Callable[[], None] | None = None,
                 **worker_options: Any) -> ProductionJobWorker:
    """Construct worker only when an operator explicitly starts it."""
    def prepare(take):
        if prepare_guard is not None:
            prepare_guard()
        return prepare_isolated_take(take, graph_path=graph_path)
    return ProductionJobWorker(ledger, comfy_url=comfy_url,
        prepare=prepare,
        collect=collect, cleanup=lambda _take: None, **worker_options)


def make_output_collector(*, data_root: Path, ledger: ProductionLedger, comfy_url: str,
                          ffprobe: str | None = None) -> Callable[[dict[str, Any], dict[str, Any]], list[dict[str, Any]]]:
    """Return a native video+audio collector into durable product asset storage.

    Uses media_jobs only to fetch Comfy output into a disposable staging area;
    every accepted output is probed, hashed, and atomically placed under its
    workspace. Existing assets are never removed by this function.
    """
    from story_builder.services.media_jobs import collect_outputs

    root = Path(data_root).expanduser().resolve()
    probe_bin = ffprobe or os.environ.get("FFPROBE", "ffprobe")

    def collect(take: dict[str, Any], history: dict[str, Any]) -> list[dict[str, Any]]:
        workspace = _identifier(take["project_id"], "workspace_id")
        job_id = _identifier(take["job_id"], "job_id")
        final_dir = root / "assets" / workspace
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
                if not {"video", "audio"}.issubset(stream_types) or duration <= 0:
                    continue
                digest = hashlib.sha256(source.read_bytes()).hexdigest()
                asset_id = f"video_{digest[:32]}"
                destination = final_dir / f"{asset_id}{source.suffix.lower()}"
                if not destination.exists():
                    temporary_target = final_dir / f".{asset_id}.{uuid.uuid4().hex}.tmp"
                    shutil.copy2(source, temporary_target)
                    os.replace(temporary_target, destination)
                metadata = {"kind": "video", "sha256": digest, "duration_seconds": duration,
                    "has_video": True, "has_audio": True, "relative_path": destination.relative_to(root).as_posix(),
                    "job_id": job_id, "prompt_id": take.get("prompt_id"), "probe": probe}
                records.append({"asset_id": asset_id, **metadata})
            if not records:
                return []
            with ledger._connect() as db:
                for record in records:
                    db.execute("INSERT OR IGNORE INTO isolated_video_assets(asset_id,job_id,workspace_id,sha256,metadata_json) VALUES(?,?,?,?,?)",
                        (record["asset_id"], job_id, workspace, record["sha256"],
                         json.dumps(record, sort_keys=True, ensure_ascii=False)))
                    db.execute("INSERT OR IGNORE INTO isolated_video_asset_refs(asset_id,job_id) VALUES(?,?)",
                               (record["asset_id"], job_id))
            return records
    return collect
