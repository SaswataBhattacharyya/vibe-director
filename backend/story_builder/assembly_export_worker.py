"""Explicit CPU worker for screenplay-ordered FFmpeg exports.

Start separately from the API with ``--enable-worker``. The API never launches it.
"""
from __future__ import annotations
from story_builder.services.storage_paths import generated_root

import argparse
import hashlib
import fcntl
import json
import os
import time
from pathlib import Path

from story_builder.services.assembly import AssemblyExportJobs, AssemblySelections
from story_builder.services.assembly_renderer import render_manifest
from story_builder.services.media_library import register_generated_video
from story_builder.services.production_ledger import ProductionLedger
from story_builder.services.media_jobs import gpu_workload_lock


def process_one(root: Path, store: AssemblyExportJobs, selections: AssemblySelections) -> bool:
    """Process one export under the app-wide workload slot."""
    # Acquire before claiming so an export stays queued while another Vibe
    # workload owns the slot. In parallel mode this becomes a shared lease.
    with gpu_workload_lock():
        job = store.claim_next()
        if job is None:
            return False
        try:
            manifest = selections.get_export_manifest(job["workspace_id"],
                job["screenplay_revision_id"], job["manifest_id"])
            if not manifest or manifest["manifest_sha256"] != job["manifest_sha256"]:
                raise RuntimeError("Frozen export manifest is missing or changed.")
            encoded = json.dumps(manifest["manifest"], sort_keys=True,
                separators=(",", ":"), ensure_ascii=False)
            if hashlib.sha256(encoded.encode("utf-8")).hexdigest() != manifest["manifest_sha256"]:
                raise RuntimeError("Frozen export manifest content does not match its recorded hash.")
            if job.get("publication_asset_id"):
                asset = {"asset_id": job["publication_asset_id"]}
            else:
                relative = f"exports/{job['job_id']}.mp4"
                output = generated_root(root, job["workspace_id"]) / relative
                rendered = render_manifest(root, job["workspace_id"], manifest, output,
                    progress=lambda percent: store.update_progress(job["job_id"], percent))
                asset = register_generated_video(root, job["workspace_id"], relative,
                    {"assembly_job_id": job["job_id"], "manifest_id": job["manifest_id"],
                     "manifest_sha256": job["manifest_sha256"], "probe": rendered["probe"]})
                with store.ledger._connect() as db:
                    db.execute("UPDATE story_assembly_export_jobs SET publication_asset_id=? WHERE job_id=?", (asset["asset_id"], job["job_id"]))
            if job.get("output_destination_json"):
                from story_builder.services.media_library import relocate_output
                relocate_output(root, job["workspace_id"], asset["asset_id"], json.loads(job["output_destination_json"]), job["job_id"])
            store.complete(job["job_id"], asset["asset_id"])
            print(f"Export {job['job_id']} completed", flush=True)
        except Exception as exc:
            store.fail(job["job_id"], str(exc) or type(exc).__name__)
            print(f"Export {job['job_id']} failed: {exc}", flush=True)
        return True


def run(root: Path, db_path: Path) -> None:
    ledger = ProductionLedger(db_path)
    store = AssemblyExportJobs(ledger)
    selections = AssemblySelections(ledger)
    (root / "runtime").mkdir(parents=True, exist_ok=True)
    lock_path = root / "runtime/assembly-export-worker.lock"
    with lock_path.open("a+b") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise SystemExit("An assembly export worker already owns this data root.") from exc
        store.recover_running()
        print(f"Assembly export worker enabled; ledger={db_path}", flush=True)
        while True:
            if not process_one(root, store, selections):
                time.sleep(1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--enable-worker", action="store_true")
    args = parser.parse_args()
    if not (args.enable_worker or os.environ.get("VIBE_DIRECTOR_ENABLE_EXPORT_WORKER") == "1"):
        raise SystemExit("Worker is disabled. Pass --enable-worker or set VIBE_DIRECTOR_ENABLE_EXPORT_WORKER=1.")
    data = os.environ.get("VIBE_DIRECTOR_DATA_DIR")
    if not data:
        raise SystemExit("Set VIBE_DIRECTOR_DATA_DIR to the Vibe Director data directory.")
    root = Path(data).expanduser().resolve()
    db_path = Path(os.environ.get("VIBE_DIRECTOR_LEDGER_PATH", root / "services/production/ledger.sqlite3")).expanduser().resolve()
    try:
        db_path.relative_to(root)
    except ValueError as exc:
        raise SystemExit("VIBE_DIRECTOR_LEDGER_PATH must remain under VIBE_DIRECTOR_DATA_DIR.") from exc
    run(root, db_path)


if __name__ == "__main__":
    main()
