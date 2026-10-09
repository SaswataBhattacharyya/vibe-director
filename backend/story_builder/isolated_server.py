"""Local-only, standard-library HTTP adapter for isolated T2V jobs.

Starting this server performs no capability probe and starts no render worker.
"""
from __future__ import annotations

import json
import mimetypes
import os
import re
import time
from pathlib import Path
from socketserver import ThreadingMixIn
from typing import Any
from urllib.parse import parse_qs, unquote
from wsgiref.simple_server import WSGIServer, make_server

from story_builder.services.isolated_video_contract import IsolatedVideoContractError
from story_builder.services.isolated_video_jobs import (
    IsolatedJobConflict, IsolatedVideoJobs,
)
from story_builder.services.production_ledger import LedgerConflict, LedgerNotFound, ProductionLedger
from story_builder.services.workflow_status import build_workflow_status
from story_builder.services.gpu_runtime import (
    GPU_RENDER_CLOCK_CEILING_MHZ, GPU_RENDER_TEMP_CUTOFF, read_gpu_operating_point,
)

_JOB_ID = re.compile(r"^[0-9a-f-]{36}$")
_ASSET_ID = re.compile(r"^video_[0-9a-f]{32}$")
_MAX_BODY = 2 * 1024 * 1024


class ThreadedWSGIServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


class RuntimeNotReady(RuntimeError):
    def __init__(self, capability):
        super().__init__(capability.get("disabled_reason") or "The T2V runtime is not ready for submission.")
        self.capability = capability


def _json_response(start_response, status: str, value: Any, headers: list[tuple[str, str]] | None = None):
    body = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    start_response(status, [("Content-Type", "application/json; charset=utf-8"),
                            ("Content-Length", str(len(body))),
                            ("Cache-Control", "no-store")] + (headers or []))
    return [body]


def _read_json(environ) -> dict[str, Any]:
    try:
        length = int(environ.get("CONTENT_LENGTH") or 0)
    except ValueError as exc:
        raise ValueError("Content-Length is invalid.") from exc
    if length < 1 or length > _MAX_BODY:
        raise ValueError(f"Request body must be between 1 and {_MAX_BODY} bytes.")
    value = json.loads(environ["wsgi.input"].read(length).decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Request body must be a JSON object.")
    return value


def create_app(*, data_root: Path, ledger_path: Path | None = None,
               graph_path: Path | None = None,
               gpu_reader=read_gpu_operating_point, capability_provider=None,
               worker_status_provider=None):
    root = Path(data_root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    configured_db = Path(ledger_path).expanduser().resolve() if ledger_path else root / "storage/production/ledger.sqlite3"
    # Keep caller-selected ledger inside the configured product data root.
    try:
        configured_db.relative_to(root)
    except ValueError as exc:
        raise ValueError("Ledger path must remain under VIBE_DIRECTOR_DATA_DIR.") from exc
    ledger = ProductionLedger(configured_db)
    jobs = IsolatedVideoJobs(ledger, graph_path=graph_path)

    def dispatch_status():
        if worker_status_provider is not None:
            return worker_status_provider()
        status_path = root / "runtime/isolated-worker-status.json"
        try:
            value = json.loads(status_path.read_text(encoding="utf-8"))
            pid = value.get("pid")
            if type(pid) is not int or value.get("enabled") is not True:
                raise ValueError("worker is not enabled")
            os.kill(pid, 0)
            fresh = time.time() - float(value.get("updated_unix", 0)) < 15
            running = value.get("state") == "running" and fresh
            return {"enabled": True, "running": running, "available": running,
                    "worker_state": value.get("state"),
                    "reason": None if running else (value.get("reason") or "Explicit worker process is not healthy or its status is stale.")}
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return {"enabled": False, "running": False, "available": False,
                    "worker_state": "stopped",
                    "reason": "No explicitly enabled isolated worker consumer is running."}

    def capability_snapshot():
        provider = capability_provider
        if provider is None:
            from story_builder.services.production_t2v_capability import t2v_capability
            provider = t2v_capability
        result = provider()
        guard = _runtime_guard(gpu_reader)
        dispatch = dispatch_status()
        result["workflow_available"] = bool(result.get("available"))
        result["runtime_guard"] = guard
        result["dispatch"] = dispatch
        result["available"] = bool(result.get("available") and guard["safe_to_submit"] and dispatch["available"])
        if not guard["safe_to_submit"]:
            result["disabled_reason"] = "; ".join(filter(None, [result.get("disabled_reason"), guard["reason"]]))
        if not dispatch["available"]:
            result["disabled_reason"] = "; ".join(filter(None, [result.get("disabled_reason"), dispatch["reason"]]))
        return result

    def app(environ, start_response):
        method = environ.get("REQUEST_METHOD", "GET").upper()
        path = unquote(environ.get("PATH_INFO", ""))
        try:
            if method == "POST" and environ.get("CONTENT_TYPE", "").split(";", 1)[0].strip().lower() != "application/json":
                return _json_response(start_response, "415 Unsupported Media Type", {"error": {"code": "content_type_required", "message": "Send application/json."}})
            if method == "GET" and path == "/api/video/capabilities":
                # Explicit capability request; never probed at server startup.
                return _json_response(start_response, "200 OK", capability_snapshot())
            if method == "GET" and path == "/api/status":
                # A single explicit status read reuses the existing fail-closed
                # workflow and GPU/worker snapshot; no new execution path runs.
                return _json_response(start_response, "200 OK",
                    build_workflow_status(capability_snapshot(), backend_connected=True))
            if method == "GET" and path == "/api/video/runtime":
                return _json_response(start_response, "200 OK", _runtime_guard(gpu_reader))
            if method == "GET" and path == "/api/video/worker":
                return _json_response(start_response, "200 OK", dispatch_status())
            if method == "POST" and path == "/api/video/validations":
                payload = _read_json(environ)
                result = jobs.validate(payload.get("request"))
                return _json_response(start_response, "200 OK", result)
            if method == "POST" and path == "/api/video/jobs":
                payload = _read_json(environ)
                capability = capability_snapshot()
                if not capability.get("available"):
                    raise RuntimeNotReady(capability)
                result = jobs.create_job(workspace_id=payload.get("workspace_id"),
                    clip_id=payload.get("clip_id"), idempotency_key=payload.get("idempotency_key"),
                    request=payload.get("request"), retake_of_job_id=payload.get("retake_of_job_id"),
                    keep_original=payload.get("keep_original"))
                return _json_response(start_response, "202 Accepted", result)
            if method == "GET" and path.startswith("/api/video/jobs/by-idempotency/"):
                key = path.removeprefix("/api/video/jobs/by-idempotency/")
                query = parse_qs(environ.get("QUERY_STRING", ""))
                workspace = (query.get("workspace_id") or [None])[0]
                return _json_response(start_response, "200 OK", jobs.get_by_idempotency_key(
                    workspace_id=workspace, idempotency_key=key))
            if path.startswith("/api/video/jobs/"):
                tail = path.removeprefix("/api/video/jobs/")
                if "/" in tail:
                    job_id, suffix = tail.split("/", 1)
                else:
                    job_id, suffix = tail, ""
                if not _JOB_ID.fullmatch(job_id):
                    return _json_response(start_response, "404 Not Found", {"error": {"code": "not_found", "message": "Job not found."}})
                if method == "GET" and not suffix:
                    return _json_response(start_response, "200 OK", jobs.get_job(job_id))
                if method == "GET" and suffix == "events":
                    return _json_response(start_response, "200 OK", {"events": jobs.events(job_id)})
                if method == "POST" and suffix == "accept":
                    payload = _read_json(environ)
                    return _json_response(start_response, "200 OK", jobs.accept_job(job_id, actor=str(payload.get("actor", "user"))))
            if path.startswith("/api/video/retakes/") and method == "POST":
                job_id = path.removeprefix("/api/video/retakes/")
                if not _JOB_ID.fullmatch(job_id):
                    return _json_response(start_response, "404 Not Found", {"error": {"code": "not_found", "message": "Job not found."}})
                payload = _read_json(environ)
                result = jobs.retake_draft(job_id, keep_original=payload.get("keep_original"))
                return _json_response(start_response, "200 OK", result)
            if path.startswith("/api/video/assets/") and method == "GET":
                asset_id = path.removeprefix("/api/video/assets/")
                if not _ASSET_ID.fullmatch(asset_id):
                    return _json_response(start_response, "404 Not Found", {"error": {"code": "not_found", "message": "Asset not found."}})
                record = _asset_record(ledger, asset_id)
                if record is None:
                    return _json_response(start_response, "404 Not Found", {"error": {"code": "not_found", "message": "Asset not found."}})
                metadata = record["metadata"]
                media_path = (root / metadata["relative_path"]).resolve()
                try:
                    media_path.relative_to(root)
                except ValueError:
                    return _json_response(start_response, "404 Not Found", {"error": {"code": "not_found", "message": "Asset not found."}})
                if not media_path.is_file():
                    return _json_response(start_response, "404 Not Found", {"error": {"code": "not_found", "message": "Asset not found."}})
                return _serve_asset(environ, start_response, media_path)
            return _json_response(start_response, "404 Not Found", {"error": {"code": "not_found", "message": "Route not found."}})
        except IsolatedVideoContractError as exc:
            return _json_response(start_response, "422 Unprocessable Entity", {"error": {"code": exc.code, "message": str(exc)}})
        except (IsolatedJobConflict, LedgerConflict) as exc:
            return _json_response(start_response, "409 Conflict", {"error": {"code": "conflict", "message": str(exc)}})
        except RuntimeNotReady as exc:
            return _json_response(start_response, "503 Service Unavailable", {"error": {"code": "runtime_not_ready", "message": str(exc)}, "capability": exc.capability})
        except LedgerNotFound:
            return _json_response(start_response, "404 Not Found", {"error": {"code": "not_found", "message": "Isolated video job not found."}})
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            return _json_response(start_response, "400 Bad Request", {"error": {"code": "invalid_request", "message": str(exc)}})
        except Exception:
            return _json_response(start_response, "500 Internal Server Error", {"error": {"code": "internal_error", "message": "The isolated video request could not be completed."}})
    return app


def _asset_record(ledger: ProductionLedger, asset_id: str):
    with ledger._connect() as db:
        row = db.execute("SELECT * FROM isolated_video_assets WHERE asset_id=?", (asset_id,)).fetchone()
    if not row:
        return None
    return {"asset_id": row["asset_id"], "metadata": json.loads(row["metadata_json"])}


def _runtime_guard(reader):
    try:
        point = reader()
        safe = (point["temperature_c"] < GPU_RENDER_TEMP_CUTOFF
                and point["graphics_clock_mhz"] <= GPU_RENDER_CLOCK_CEILING_MHZ)
        reason = None if safe else (f"GPU operating limit reached: temperature must stay below {GPU_RENDER_TEMP_CUTOFF} C "
            f"and graphics clock at or below {GPU_RENDER_CLOCK_CEILING_MHZ} MHz.")
        return {"monitor_available": True, "safe_to_submit": safe,
            "temperature_cutoff_c": GPU_RENDER_TEMP_CUTOFF,
            "graphics_clock_ceiling_mhz": GPU_RENDER_CLOCK_CEILING_MHZ,
            "operating_point": point, "reason": reason}
    except Exception as exc:
        return {"monitor_available": False, "safe_to_submit": False,
            "temperature_cutoff_c": GPU_RENDER_TEMP_CUTOFF,
            "graphics_clock_ceiling_mhz": GPU_RENDER_CLOCK_CEILING_MHZ,
            "operating_point": None,
            "reason": f"GPU monitoring unavailable ({type(exc).__name__}); generation is blocked."}


def _serve_asset(environ, start_response, path: Path):
    size = path.stat().st_size
    start, end, status = 0, max(0, size - 1), "200 OK"
    headers = []
    range_header = environ.get("HTTP_RANGE")
    if range_header:
        match = re.fullmatch(r"bytes=(\d*)-(\d*)", range_header.strip())
        if not match or size == 0:
            return _json_response(start_response, "416 Range Not Satisfiable", {"error": {"code": "invalid_range", "message": "Invalid byte range."}}, [("Content-Range", f"bytes */{size}")])
        a, b = match.groups()
        if a:
            start = int(a)
            end = min(int(b), size - 1) if b else size - 1
        else:
            suffix = int(b or 0)
            start = max(0, size - suffix)
        if start > end or start >= size:
            return _json_response(start_response, "416 Range Not Satisfiable", {"error": {"code": "invalid_range", "message": "Invalid byte range."}}, [("Content-Range", f"bytes */{size}")])
        status = "206 Partial Content"
        headers.append(("Content-Range", f"bytes {start}-{end}/{size}"))
    length = max(0, end - start + 1)
    headers += [("Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream"),
        ("Content-Length", str(length)), ("Accept-Ranges", "bytes"), ("Cache-Control", "private, no-store")]
    start_response(status, headers)
    def chunks():
        with path.open("rb") as handle:
            handle.seek(start)
            remaining = length
            while remaining:
                chunk = handle.read(min(64 * 1024, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk
    return chunks()


def main() -> None:
    data_root = os.environ.get("VIBE_DIRECTOR_DATA_DIR")
    if not data_root:
        raise SystemExit("Set VIBE_DIRECTOR_DATA_DIR to a product-owned data directory before startup.")
    db_path = os.environ.get("VIBE_DIRECTOR_LEDGER_PATH")
    graph_path = os.environ.get("VIBE_DIRECTOR_GRAPH_PATH")
    port = int(os.environ.get("VIBE_DIRECTOR_PORT", "3020"))
    app = create_app(data_root=Path(data_root), ledger_path=Path(db_path) if db_path else None,
                     graph_path=Path(graph_path) if graph_path else None)
    with make_server("127.0.0.1", port, app, server_class=ThreadedWSGIServer) as server:
        print(f"Vibe Director isolated API listening on http://127.0.0.1:{port}; no worker auto-started", flush=True)
        server.serve_forever()


if __name__ == "__main__":
    main()
