"""Build a read-only, screenplay-ordered preview of accepted video takes."""

from __future__ import annotations

import json
import hashlib
import math
import re
from typing import Any, Mapping


def clip_key(clip: Mapping[str, Any]) -> str:
    if isinstance(clip.get("clip_id"), str) and clip["clip_id"]:
        return clip["clip_id"]
    return f"{clip.get('scene_number')}.{clip.get('shot_number')}.{clip.get('clip_number', 1)}"


def validate_assembly_selection(preview: Mapping[str, Any], selections: Any) -> dict[str, str]:
    """Validate a partial, revision-scoped map of clip keys to accepted takes."""
    if not isinstance(selections, dict) or len(selections) > 10000:
        raise ValueError("Selections must be a clip-to-take map with at most 10,000 entries.")
    clips = {clip_key(clip): clip for clip in preview.get("clips", []) if isinstance(clip, dict)}
    clean: dict[str, str] = {}
    for key, job_id in selections.items():
        if not isinstance(key, str) or key not in clips:
            raise ValueError("A selected clip is not part of this screenplay assembly.")
        if not isinstance(job_id, str) or not job_id:
            raise ValueError("Each selected take needs a job ID.")
        accepted_ids = {take.get("job_id") for take in clips[key].get("accepted_takes", [])}
        if job_id not in accepted_ids:
            raise ValueError("Choose an accepted video take belonging to its screenplay clip.")
        clean[key] = job_id
    return clean


def validate_assembly_audio_tracks(assets: Mapping[str, Mapping[str, Any]], tracks: Any) -> list[dict[str, Any]]:
    """Validate explicit optional track placement against current audio assets."""
    import math
    if not isinstance(tracks, list) or len(tracks) > 20:
        raise ValueError("Choose at most 20 optional audio tracks.")
    result = []
    seen = set()
    required = {"asset_id", "sha256", "start_seconds", "trim_start_seconds", "trim_end_seconds", "gain"}
    for track in tracks:
        if not isinstance(track, dict) or set(track) != required:
            raise ValueError("Each audio track needs its asset hash, placement, trim range, and gain.")
        asset_id, digest = track["asset_id"], track["sha256"]
        asset = assets.get(asset_id) if isinstance(asset_id, str) else None
        if not asset or asset.get("kind") != "audio" or asset.get("sha256") != digest:
            raise ValueError("An audio track is missing from this workspace or its file changed.")
        if asset_id in seen:
            raise ValueError("An audio asset can be added only once to an export.")
        seen.add(asset_id)
        values = [track[key] for key in ("start_seconds", "trim_start_seconds", "trim_end_seconds", "gain")]
        if any(type(value) not in (int, float) or not math.isfinite(value) for value in values):
            raise ValueError("Audio timing and gain must be finite numbers.")
        start, trim_start, trim_end, gain = values
        duration = ((asset.get("media") or {}).get("duration_seconds")
            if isinstance(asset.get("media"), dict) else None)
        if type(duration) not in (int, float) or not math.isfinite(duration) or duration <= 0:
            raise ValueError("An audio track needs a verified file duration before it can be placed.")
        if (start < 0 or trim_start < 0 or trim_end <= trim_start or gain < 0 or gain > 2
                or start > 86400 or trim_end > 86400
                or trim_end > duration + 0.05):
            raise ValueError("Audio placement, trim range, or gain is outside the supported range.")
        result.append({"asset_id": asset_id, "sha256": digest,
            "start_seconds": float(start), "trim_start_seconds": float(trim_start),
            "trim_end_seconds": float(trim_end), "gain": float(gain)})
    return result


def validate_export_settings(value: Any) -> dict[str, Any]:
    """Validate the first supported local export profile and explicit audio policy."""
    required = {"resolution", "frame_rate", "quality", "audio_policy"}
    allowed = required | {"container", "video_codec", "audio_codec"}
    if not isinstance(value, dict) or not required.issubset(value) or not set(value).issubset(allowed):
        raise ValueError("Choose resolution, frame rate, quality and audio policy.")
    if (value.get("container", "mp4") != "mp4" or value.get("video_codec", "libx264") != "libx264"
            or value.get("audio_codec", "aac") != "aac"):
        raise ValueError("Only the supported MP4, H.264 and AAC export profile is available.")
    if type(value["resolution"]) is not str or value["resolution"] not in {"720p", "1080p", "1440p"}:
        raise ValueError("Export resolution must be 720p, 1080p or 1440p.")
    if type(value["frame_rate"]) is not int or value["frame_rate"] not in {24, 30, 60}:
        raise ValueError("Export frame rate must be 24, 30 or 60 fps.")
    if type(value["quality"]) is not int or not 18 <= value["quality"] <= 28:
        raise ValueError("H.264 quality must be an integer from 18 to 28.")
    if type(value["audio_policy"]) is not str or value["audio_policy"] not in {"preserve_and_mix", "selected_tracks_only", "mute"}:
        raise ValueError("Choose how clip audio and optional tracks should be handled.")
    return {"container": "mp4", "video_codec": "libx264", "audio_codec": "aac",
        **value}


def build_export_manifest(snapshot_record: Mapping[str, Any], settings: Mapping[str, Any]) -> dict[str, Any]:
    snapshot = snapshot_record.get("snapshot")
    if not isinstance(snapshot, dict) or snapshot.get("state") != "awaiting_export_settings":
        raise ValueError("Choose a frozen assembly snapshot that is ready for export settings.")
    return {"schema_version": 1, "state": "ready_for_render",
        "snapshot_id": snapshot_record["snapshot_id"],
        "snapshot_sha256": snapshot_record["snapshot_sha256"],
        "screenplay_revision_id": snapshot_record["screenplay_revision_id"],
        "clips": [dict(clip) for clip in snapshot["clips"]],
        "audio_tracks": [dict(track) for track in snapshot["audio_tracks"]],
        "export_settings": dict(settings)}


def build_assembly_snapshot(preview: Mapping[str, Any], selections: Mapping[str, str],
                            audio_tracks: list[dict[str, Any]], *,
                            screenplay: Mapping[str, Any], setup: Mapping[str, Any]) -> dict[str, Any]:
    """Freeze fully selected accepted clip outputs and optional audio instructions."""
    if preview.get("planning_incomplete") or not preview.get("clips"):
        raise ValueError("The screenplay clip plan must be complete before saving an assembly snapshot.")
    expected = {clip_key(clip) for clip in preview["clips"]}
    if set(selections) != expected:
        raise ValueError("Choose one accepted take for every planned clip before saving an assembly snapshot.")
    clips = []
    for clip in preview["clips"]:
        key = clip_key(clip)
        job_id = selections[key]
        take = next((item for item in clip.get("accepted_takes", []) if item.get("job_id") == job_id), None)
        if take is None:
            raise ValueError("An assembly choice no longer matches an accepted take.")
        outputs = []
        for output in take.get("outputs", []):
            if output.get("kind") != "video":
                continue
            asset_id, digest = output.get("asset_id"), output.get("sha256")
            duration = output.get("duration_seconds")
            if (not isinstance(asset_id, str) or not asset_id or not isinstance(digest, str)
                    or not re.fullmatch(r"[a-f0-9]{64}", digest)
                    or type(duration) not in (int, float) or not math.isfinite(duration) or duration <= 0):
                continue
            outputs.append({key: output[key] for key in ("kind", "asset_id", "shared_asset_id", "sha256", "duration_seconds", "has_audio", "has_video") if key in output})
        if not outputs:
            raise ValueError("Each selected take needs a playable video output with a verified asset hash.")
        request = take.get("request")
        request_hash = take.get("request_hash")
        if request is not None:
            if not isinstance(request, dict):
                raise ValueError("A selected take has invalid frozen request provenance.")
            encoded_request = json.dumps(request, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            if len(encoded_request.encode("utf-8")) > 128 * 1024:
                raise ValueError("A selected take's frozen request is too large to include in an assembly snapshot.")
            actual_hash = hashlib.sha256(encoded_request.encode("utf-8")).hexdigest()
            if not isinstance(request_hash, str) or request_hash != actual_hash:
                raise ValueError("A selected take's frozen request does not match its request hash.")
        lineage = take.get("source_lineage")
        if lineage is not None and not isinstance(lineage, dict):
            raise ValueError("A selected take has invalid source lineage.")
        clips.append({"clip_id": clip.get("clip_id"), "scene_number": clip.get("scene_number"),
            "shot_number": clip.get("shot_number"), "clip_number": clip.get("clip_number", 1),
            "job_id": job_id, "request_hash": request_hash, "request": request,
            "source_lineage": lineage, "take_created_at": take.get("created_at"),
            "outputs": outputs})
    # Snapshots contain only validated video outputs; the renderer selects the
    # first output for each clip, so timeline duration must use that same choice.
    total_duration = sum(float(clip["outputs"][0]["duration_seconds"]) for clip in clips)
    for track in audio_tracks:
        start = track.get("start_seconds") if isinstance(track, dict) else None
        if (type(start) not in (int, float) or not math.isfinite(start)
                or start >= total_duration):
            raise ValueError("Each optional audio track must start before the assembled video ends.")
    return {"schema_version": 1, "state": "awaiting_export_settings",
        "screenplay_revision_id": preview["screenplay_revision_id"],
        "source_revision_id": screenplay.get("source_revision_id"),
        "style_selection_snapshot_id": screenplay.get("style_selection_snapshot_id"),
        "production_setup": dict(setup), "clips": clips,
        "audio_tracks": [dict(track) for track in audio_tracks],
        "export_settings": None}


class AssemblySelections:
    """Persist the Director's partial clip choices in the local production ledger."""

    def __init__(self, ledger):
        self.ledger = ledger
        with self.ledger._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS story_assembly_selections (
                workspace_id TEXT NOT NULL,
                screenplay_revision_id TEXT NOT NULL,
                selections_json TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(workspace_id, screenplay_revision_id)
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS story_assembly_audio_tracks (
                workspace_id TEXT NOT NULL,
                screenplay_revision_id TEXT NOT NULL,
                tracks_json TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(workspace_id, screenplay_revision_id)
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS story_assembly_snapshots (
                snapshot_id TEXT PRIMARY KEY,
                workspace_id TEXT NOT NULL,
                screenplay_revision_id TEXT NOT NULL,
                snapshot_sha256 TEXT NOT NULL,
                snapshot_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(workspace_id, screenplay_revision_id, snapshot_sha256)
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS story_assembly_export_manifests (
                manifest_id TEXT PRIMARY KEY,
                workspace_id TEXT NOT NULL,
                screenplay_revision_id TEXT NOT NULL,
                manifest_sha256 TEXT NOT NULL,
                manifest_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(workspace_id, screenplay_revision_id, manifest_sha256)
            )""")

    def get(self, workspace_id: str, revision_id: str) -> dict[str, Any]:
        with self.ledger._connect() as db:
            row = db.execute("SELECT selections_json,updated_at FROM story_assembly_selections WHERE workspace_id=? AND screenplay_revision_id=?",
                (workspace_id, revision_id)).fetchone()
        return {"workspace_id": workspace_id, "screenplay_revision_id": revision_id,
            "selections": json.loads(row["selections_json"]) if row else {},
            "updated_at": row["updated_at"] if row else None}

    def save(self, workspace_id: str, revision_id: str, selections: dict[str, str]) -> dict[str, Any]:
        with self.ledger._connect() as db:
            db.execute("""INSERT INTO story_assembly_selections
                (workspace_id,screenplay_revision_id,selections_json,updated_at) VALUES(?,?,?,CURRENT_TIMESTAMP)
                ON CONFLICT(workspace_id,screenplay_revision_id) DO UPDATE SET
                selections_json=excluded.selections_json,updated_at=CURRENT_TIMESTAMP""",
                (workspace_id, revision_id, json.dumps(selections, sort_keys=True, separators=(",", ":"))))
        return self.get(workspace_id, revision_id)

    def get_audio(self, workspace_id: str, revision_id: str) -> dict[str, Any]:
        with self.ledger._connect() as db:
            row = db.execute("SELECT tracks_json,updated_at FROM story_assembly_audio_tracks WHERE workspace_id=? AND screenplay_revision_id=?",
                (workspace_id, revision_id)).fetchone()
        return {"workspace_id": workspace_id, "screenplay_revision_id": revision_id,
            "audio_tracks": json.loads(row["tracks_json"]) if row else [],
            "updated_at": row["updated_at"] if row else None}

    def save_audio(self, workspace_id: str, revision_id: str, tracks: list[dict[str, Any]]) -> dict[str, Any]:
        with self.ledger._connect() as db:
            db.execute("""INSERT INTO story_assembly_audio_tracks
                (workspace_id,screenplay_revision_id,tracks_json,updated_at) VALUES(?,?,?,CURRENT_TIMESTAMP)
                ON CONFLICT(workspace_id,screenplay_revision_id) DO UPDATE SET
                tracks_json=excluded.tracks_json,updated_at=CURRENT_TIMESTAMP""",
                (workspace_id, revision_id, json.dumps(tracks, sort_keys=True, separators=(",", ":"))))
        return self.get_audio(workspace_id, revision_id)

    def save_snapshot(self, workspace_id: str, revision_id: str, snapshot: dict[str, Any]) -> dict[str, Any]:
        encoded = json.dumps(snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        identity = f"{workspace_id}\0{revision_id}\0{digest}"
        snapshot_id = f"assembly-{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:32]}"
        with self.ledger._connect() as db:
            db.execute("""INSERT OR IGNORE INTO story_assembly_snapshots
                (snapshot_id,workspace_id,screenplay_revision_id,snapshot_sha256,snapshot_json)
                VALUES(?,?,?,?,?)""", (snapshot_id, workspace_id, revision_id, digest, encoded))
            row = db.execute("SELECT * FROM story_assembly_snapshots WHERE workspace_id=? AND screenplay_revision_id=? AND snapshot_sha256=?",
                (workspace_id, revision_id, digest)).fetchone()
        return {"snapshot_id": row["snapshot_id"], "workspace_id": row["workspace_id"],
            "screenplay_revision_id": row["screenplay_revision_id"], "snapshot_sha256": row["snapshot_sha256"],
            "snapshot": json.loads(row["snapshot_json"]), "created_at": row["created_at"]}

    def list_snapshots(self, workspace_id: str, revision_id: str) -> list[dict[str, Any]]:
        with self.ledger._connect() as db:
            rows = db.execute("SELECT * FROM story_assembly_snapshots WHERE workspace_id=? AND screenplay_revision_id=? ORDER BY created_at DESC,snapshot_id DESC",
                (workspace_id, revision_id)).fetchall()
        return [{"snapshot_id": row["snapshot_id"], "workspace_id": row["workspace_id"],
            "screenplay_revision_id": row["screenplay_revision_id"], "snapshot_sha256": row["snapshot_sha256"],
            "snapshot": json.loads(row["snapshot_json"]), "created_at": row["created_at"]} for row in rows]

    def get_snapshot(self, workspace_id: str, revision_id: str, snapshot_id: str) -> dict[str, Any] | None:
        with self.ledger._connect() as db:
            row = db.execute("SELECT * FROM story_assembly_snapshots WHERE workspace_id=? AND screenplay_revision_id=? AND snapshot_id=?",
                (workspace_id, revision_id, snapshot_id)).fetchone()
        return None if row is None else {"snapshot_id": row["snapshot_id"],
            "workspace_id": row["workspace_id"], "screenplay_revision_id": row["screenplay_revision_id"],
            "snapshot_sha256": row["snapshot_sha256"], "snapshot": json.loads(row["snapshot_json"]),
            "created_at": row["created_at"]}

    def save_export_manifest(self, workspace_id: str, revision_id: str, manifest: dict[str, Any]) -> dict[str, Any]:
        encoded = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        identity = f"{workspace_id}\0{revision_id}\0{digest}"
        manifest_id = f"export-{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:32]}"
        with self.ledger._connect() as db:
            db.execute("""INSERT OR IGNORE INTO story_assembly_export_manifests
                (manifest_id,workspace_id,screenplay_revision_id,manifest_sha256,manifest_json)
                VALUES(?,?,?,?,?)""", (manifest_id, workspace_id, revision_id, digest, encoded))
            row = db.execute("SELECT * FROM story_assembly_export_manifests WHERE workspace_id=? AND screenplay_revision_id=? AND manifest_sha256=?",
                (workspace_id, revision_id, digest)).fetchone()
        return {"manifest_id": row["manifest_id"], "workspace_id": row["workspace_id"],
            "screenplay_revision_id": row["screenplay_revision_id"],
            "manifest_sha256": row["manifest_sha256"], "manifest": json.loads(row["manifest_json"]),
            "created_at": row["created_at"]}

    def list_export_manifests(self, workspace_id: str, revision_id: str) -> list[dict[str, Any]]:
        with self.ledger._connect() as db:
            rows = db.execute("SELECT * FROM story_assembly_export_manifests WHERE workspace_id=? AND screenplay_revision_id=? ORDER BY created_at DESC,manifest_id DESC",
                (workspace_id, revision_id)).fetchall()
        return [{"manifest_id": row["manifest_id"], "workspace_id": row["workspace_id"],
            "screenplay_revision_id": row["screenplay_revision_id"],
            "manifest_sha256": row["manifest_sha256"], "manifest": json.loads(row["manifest_json"]),
            "created_at": row["created_at"]} for row in rows]

    def get_export_manifest(self, workspace_id: str, revision_id: str, manifest_id: str):
        with self.ledger._connect() as db:
            row = db.execute("SELECT * FROM story_assembly_export_manifests WHERE workspace_id=? AND screenplay_revision_id=? AND manifest_id=?",
                (workspace_id, revision_id, manifest_id)).fetchone()
        if row is None:
            return None
        return {"manifest_id": row["manifest_id"], "workspace_id": row["workspace_id"],
            "screenplay_revision_id": row["screenplay_revision_id"], "manifest_sha256": row["manifest_sha256"],
            "manifest": json.loads(row["manifest_json"]), "created_at": row["created_at"]}


class AssemblyExportJobs:
    """Durable, idempotent export queue consumed only by the explicit export worker."""

    def __init__(self, ledger):
        self.ledger = ledger
        with ledger._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS story_assembly_export_jobs (
                job_id TEXT PRIMARY KEY,
                workspace_id TEXT NOT NULL,
                screenplay_revision_id TEXT NOT NULL,
                manifest_id TEXT NOT NULL,
                manifest_sha256 TEXT NOT NULL,
                state TEXT NOT NULL,
                progress_percent INTEGER NOT NULL DEFAULT 0,
                output_asset_id TEXT,
                error TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(workspace_id, screenplay_revision_id, manifest_id)
            )""")
            columns = {row["name"] for row in db.execute("PRAGMA table_info(story_assembly_export_jobs)")}
            if "progress_percent" not in columns:
                db.execute("ALTER TABLE story_assembly_export_jobs ADD COLUMN progress_percent INTEGER NOT NULL DEFAULT 0")

            for name in ("output_destination_json", "publication_asset_id"):
                if name not in columns:
                    db.execute(f"ALTER TABLE story_assembly_export_jobs ADD COLUMN {name} TEXT")

    @staticmethod
    def _row(row):
        return dict(row) if row else None

    def enqueue(self, workspace_id: str, revision_id: str, manifest_record: dict[str, Any], *, output_destination=None):
        manifest_id = manifest_record["manifest_id"]
        digest = manifest_record["manifest_sha256"]
        identity = f"{workspace_id}\0{revision_id}\0{manifest_id}\0{digest}"
        job_id = "assembly-" + hashlib.sha256(identity.encode()).hexdigest()[:32]
        with self.ledger._connect() as db:
            db.execute("""INSERT OR IGNORE INTO story_assembly_export_jobs
                (job_id,workspace_id,screenplay_revision_id,manifest_id,manifest_sha256,state,output_destination_json)
                VALUES(?,?,?,?,?,'queued',?)""", (job_id, workspace_id, revision_id, manifest_id, digest, json.dumps(output_destination) if output_destination else None))
            row = db.execute("SELECT * FROM story_assembly_export_jobs WHERE workspace_id=? AND screenplay_revision_id=? AND manifest_id=?",
                (workspace_id, revision_id, manifest_id)).fetchone()
        if row["manifest_sha256"] != digest:
            raise ValueError("This export manifest ID is already associated with different content.")
        return self._row(row)

    def get(self, workspace_id: str, revision_id: str, job_id: str):
        with self.ledger._connect() as db:
            row = db.execute("SELECT * FROM story_assembly_export_jobs WHERE workspace_id=? AND screenplay_revision_id=? AND job_id=?",
                (workspace_id, revision_id, job_id)).fetchone()
        return self._row(row)

    def list(self, workspace_id: str, revision_id: str):
        with self.ledger._connect() as db:
            rows = db.execute("SELECT * FROM story_assembly_export_jobs WHERE workspace_id=? AND screenplay_revision_id=? ORDER BY created_at DESC,job_id DESC",
                (workspace_id, revision_id)).fetchall()
        return [self._row(row) for row in rows]

    def recover_running(self):
        """A single-worker lifetime lock makes stale running jobs safe to retry at startup."""
        with self.ledger._connect() as db:
            return db.execute("UPDATE story_assembly_export_jobs SET state='queued',progress_percent=0,error='Recovered after worker restart.',updated_at=CURRENT_TIMESTAMP WHERE state='rendering'").rowcount

    def claim_next(self):
        with self.ledger._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM story_assembly_export_jobs WHERE state='queued' ORDER BY created_at,job_id LIMIT 1").fetchone()
            if row is None:
                db.commit()
                return None
            db.execute("UPDATE story_assembly_export_jobs SET state='rendering',progress_percent=0,error=NULL,updated_at=CURRENT_TIMESTAMP WHERE job_id=? AND state='queued'", (row["job_id"],))
            claimed = db.execute("SELECT * FROM story_assembly_export_jobs WHERE job_id=?", (row["job_id"],)).fetchone()
            db.commit()
        return self._row(claimed)

    def complete(self, job_id: str, output_asset_id: str):
        with self.ledger._connect() as db:
            db.execute("UPDATE story_assembly_export_jobs SET state='completed',progress_percent=100,output_asset_id=?,error=NULL,updated_at=CURRENT_TIMESTAMP WHERE job_id=? AND state='rendering'",
                (output_asset_id, job_id))

    def update_progress(self, job_id: str, progress_percent: int):
        """Persist monotonic FFmpeg progress without marking an unverified output complete."""
        value = max(0, min(99, int(progress_percent)))
        with self.ledger._connect() as db:
            db.execute("UPDATE story_assembly_export_jobs SET progress_percent=MAX(progress_percent,?),updated_at=CURRENT_TIMESTAMP WHERE job_id=? AND state='rendering'",
                (value, job_id))

    def fail(self, job_id: str, error: str):
        with self.ledger._connect() as db:
            db.execute("UPDATE story_assembly_export_jobs SET state='failed',error=?,updated_at=CURRENT_TIMESTAMP WHERE job_id=? AND state='rendering'",
                (error[-2000:], job_id))

    def retry(self, workspace_id: str, revision_id: str, job_id: str):
        with self.ledger._connect() as db:
            db.execute("UPDATE story_assembly_export_jobs SET state='queued',progress_percent=0,error=NULL,updated_at=CURRENT_TIMESTAMP WHERE workspace_id=? AND screenplay_revision_id=? AND job_id=? AND state='failed'",
                (workspace_id, revision_id, job_id))
        return self.get(workspace_id, revision_id, job_id)

def build_assembly_preview(screenplay: Mapping[str, Any], jobs: list[dict[str, Any]], *,
                           screenplay_revision_id: str,
                           full_run: Mapping[str, Any] | None = None,
                           assisted_plan: Mapping[str, Any] | None = None) -> dict[str, Any]:
    scenes = screenplay.get("scenes")
    if not isinstance(scenes, list):
        raise ValueError("The accepted screenplay has no scene list.")

    # Full runs may split a shot into several clips. Use their frozen order when
    # available; otherwise an unplanned Full run is explicitly marked provisional.
    planned = []
    if full_run and full_run.get("clips"):
        planned = [{key: clip[key] for key in ("clip_id", "scene_number", "shot_number", "clip_number") if key in clip}
                   for clip in full_run["clips"]]
        planned_source = "full_run"
    elif assisted_plan and assisted_plan.get("clips"):
        planned = [{key: clip[key] for key in ("clip_id", "scene_number", "shot_number", "clip_number") if key in clip}
                   for clip in assisted_plan["clips"]]
        planned_source = "assisted_plan"
    else:
        planned_source = "screenplay"
        for scene in scenes:
            if not isinstance(scene, dict) or type(scene.get("scene_number")) is not int:
                continue
            for shot in scene.get("shots", []):
                if isinstance(shot, dict) and type(shot.get("shot_number")) is int:
                    planned.append({"scene_number": scene["scene_number"],
                                    "shot_number": shot["shot_number"], "clip_number": 1})

    ordered = []
    for item in planned:
        scene_number, shot_number = item.get("scene_number"), item.get("shot_number")
        clip_number = item.get("clip_number", 1)
        lineage_jobs = [job for job in jobs if job.get("clip_id") == item["clip_id"]] if item.get("clip_id") else [job for job in jobs
                if isinstance(job.get("source_lineage"), dict)
                and job["source_lineage"].get("screenplay_revision_id") == screenplay_revision_id
                and job["source_lineage"].get("scene_number") == scene_number
                and job["source_lineage"].get("shot_number") == shot_number]
        # A take is selectable only after explicit acceptance and with a video output.
        accepted, review = [], []
        for job in lineage_jobs:
            if job.get("candidate_disposition") == "discard_requested":
                continue
            videos = [output for output in job.get("outputs", [])
                if output.get("kind") == "video" and output.get("playback_url")]
            if not videos:
                continue
            candidate = {"job_id": job["job_id"], "outputs": videos,
                         "created_at": job.get("created_at"), "status": job.get("status"),
                         "request_hash": job.get("request_hash"), "request": job.get("request"),
                         "source_lineage": job.get("source_lineage")}
            if job.get("status") == "accepted":
                accepted.append(candidate)
            elif job.get("status") == "needs_review":
                review.append(candidate)
        ordered.append({**item, "scene_number": scene_number, "shot_number": shot_number,
            "clip_number": clip_number, "accepted_takes": accepted, "review_takes": review,
            "missing_accepted_take": not accepted})

    full_incomplete = bool(full_run and (full_run.get("run_state") != "completed"
        or full_run.get("planned_count") is None
        or len(planned) < full_run.get("planned_count", 0)))
    return {"screenplay_revision_id": screenplay_revision_id,
        "clips": ordered, "planned_source": planned_source,
        "missing_clip_count": sum(item["missing_accepted_take"] for item in ordered),
        "planning_incomplete": full_incomplete,
        "warnings": (["The Full run has not frozen a complete clip sequence yet."] if full_incomplete else [])}
