"""Read-only counts for Vibe Director's durable job stores."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


_QUEUE_GROUPS = {
    "video_production": {
        "pending": {"queued", "retrying", "waiting_for_predecessor", "waiting_for_user"},
        "active": {"submitting", "running", "collecting", "cancel_requested"},
        "attention": {"failed", "stale", "recovery_required"},
        "ignored": {"draft", "validated", "needs_review", "accepted", "cancelled"},
    },
    "image_production": {
        "pending": {"queued"},
        "active": {"preparing", "submitting", "running"},
        "attention": {"failed", "recovery_required"},
        "ignored": {"completed", "cancelled"},
    },
    "video_exports": {
        "pending": {"queued"},
        "active": {"rendering"},
        "attention": {"failed"},
        "ignored": {"completed"},
    },
    "media_prep": {
        "pending": {"queued"},
        "active": {"running"},
        "attention": {"failed", "interrupted"},
        "ignored": {"completed", "cancelled"},
    },
}


def _summary(counts: dict[str, int], groups: dict[str, set[str]]) -> dict[str, int]:
    known = set().union(*groups.values())
    return {
        **{key: sum(counts.get(state, 0) for state in groups[key])
           for key in ("pending", "active")},
        # Unknown states must not make an otherwise idle queue look clear.
        "attention": (sum(counts.get(state, 0) for state in groups["attention"])
                      + sum(count for state, count in counts.items() if state not in known)),
    }


def _read_only_status_counts(path: Path, query: str) -> dict[str, int]:
    uri = f"{path.resolve().as_uri()}?mode=ro"
    with sqlite3.connect(uri, uri=True, timeout=2) as db:
        return {str(status): int(count) for status, count in db.execute(query)}


def _store_result(counts: dict[str, int], key: str) -> dict[str, Any]:
    return {"id": key, "checked": True, **_summary(counts, _QUEUE_GROUPS[key])}


def local_job_queue_status(*, ledger_path: Path, image_jobs_path: Path,
                           repertoire_root: Path) -> dict[str, Any]:
    """Summarize queued, active and attention-required jobs without mutation."""
    sources: list[dict[str, Any]] = []
    try:
        sources.append(_store_result(_read_only_status_counts(
            ledger_path, "SELECT status, COUNT(*) FROM production_takes GROUP BY status"),
            "video_production"))
    except (OSError, sqlite3.Error, ValueError):
        sources.append({"id": "video_production", "checked": False, "reason": "Video production queue could not be checked."})
    try:
        sources.append(_store_result(_read_only_status_counts(
            image_jobs_path, "SELECT status, COUNT(*) FROM production_image_jobs GROUP BY status"),
            "image_production"))
    except (OSError, sqlite3.Error, ValueError):
        sources.append({"id": "image_production", "checked": False, "reason": "Image production queue could not be checked."})
    try:
        sources.append(_store_result(_read_only_status_counts(
            ledger_path, "SELECT state, COUNT(*) FROM story_assembly_export_jobs GROUP BY state"),
            "video_exports"))
    except (OSError, sqlite3.Error, ValueError):
        sources.append({"id": "video_exports", "checked": False, "reason": "Video export queue could not be checked."})

    try:
        from story_builder.services.video_repertoire import JOB_KINDS

        counts: dict[str, int] = {}
        jobs_root = Path(repertoire_root) / "jobs"
        for kind in JOB_KINDS:
            root = jobs_root / kind
            if not root.is_dir():
                continue
            for path in root.glob("*/job.json"):
                with path.open("r", encoding="utf-8") as handle:
                    job = json.load(handle)
                state = job.get("status") if isinstance(job, dict) else None
                if not isinstance(state, str):
                    raise ValueError(f"Unrecognized job record: {path.name}")
                counts[state] = counts.get(state, 0) + 1
        sources.append(_store_result(counts, "media_prep"))
    except (OSError, ValueError, json.JSONDecodeError):
        sources.append({"id": "media_prep", "checked": False, "reason": "Media Prep job queue could not be checked."})

    checked = all(item["checked"] for item in sources)
    result: dict[str, Any] = {"checked": checked, "sources": sources}
    if checked:
        result.update({key: sum(int(item[key]) for item in sources)
                       for key in ("pending", "active", "attention")})
    else:
        result.update({"pending": None, "active": None, "attention": None,
                       "reason": "One or more Vibe Director job stores could not be checked."})
    return result
