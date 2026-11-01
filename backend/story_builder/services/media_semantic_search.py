"""Workspace-scoped semantic lookup over analyzed Video Summariser records."""
from __future__ import annotations

import importlib
import hashlib
import json
import math
import os
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any

from story_builder.services import video_repertoire
from story_builder.services.media_library import list_assets, public_asset_record, save_semantic_annotation_index, semantic_annotation_text


def _finite_seconds(value: Any) -> float | None:
    """Parse persisted media timestamps without letting malformed metadata break search."""
    if isinstance(value, bool) or value is None:
        return None
    try:
        seconds = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return seconds if math.isfinite(seconds) else None


def _retrieval_module():
    source = video_repertoire.ANALYZER_ROOT / "src"
    if not (source / "video_audio_analyzer" / "retrieval.py").is_file():
        raise RuntimeError("Video analyzer retrieval code is unavailable.")
    if str(source) not in sys.path:
        sys.path.insert(0, str(source))
    return importlib.import_module("video_audio_analyzer.retrieval")


def index_workspace_asset(root: Path, workspace_id: str, asset_id: str) -> dict[str, Any]:
    """Embed saved filename/description/tags using the real PE-AV text worker."""
    if not isinstance(asset_id, str) or not re.fullmatch(r"pa-[a-f0-9]{16}", asset_id):
        raise ValueError("Choose a workspace library asset to index.")
    asset = None
    offset = 0
    while asset is None:
        page = list_assets(root, workspace_id, kind=None, limit=100, offset=offset)
        asset = next((row for row in page["assets"] if row.get("asset_id") == asset_id
                      and not row.get("recommended") and not row.get("catalog_only")), None)
        offset += len(page["assets"])
        if asset is not None or not page["assets"] or offset >= page["total"]:
            break
    if asset is None:
        raise ValueError("Asset was not found in this workspace library.")
    text = semantic_annotation_text(asset)
    if not text:
        raise ValueError("Add a description or search tags before indexing this asset.")
    if len(text.encode("utf-8")) > 16_000:
        raise ValueError("Saved search details are too long to index.")
    worker = os.environ.get("VIDEO_AUDIO_ANALYZER_PE_AV_WORKER_URL", "").rstrip("/")
    if not worker:
        raise RuntimeError("The PE-AV text embedding worker is not configured.")
    request = urllib.request.Request(f"{worker}/embed/text",
        data=json.dumps({"text": text}, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    timeout = max(1.0, float(os.environ.get("VIDEO_AUDIO_ANALYZER_PE_AV_WORKER_TIMEOUT", "45")))
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    vector = payload.get("embedding") if isinstance(payload, dict) else None
    if not isinstance(payload, dict) or payload.get("model") != "facebook/pe-av-base" or type(vector) is not list or not vector:
        raise RuntimeError("The PE-AV worker returned an invalid text embedding.")
    if type(payload.get("dimension")) is not int or payload["dimension"] != len(vector):
        raise RuntimeError("The PE-AV worker returned an inconsistent embedding dimension.")
    if any(type(value) not in {int, float} or not math.isfinite(value) for value in vector):
        raise RuntimeError("The PE-AV worker returned invalid embedding values.")
    annotation_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return save_semantic_annotation_index(root, workspace_id, asset_id,
        source_sha256=asset["sha256"], annotation_sha256=annotation_hash,
        model=payload["model"], vector=vector)


def search_workspace(root: Path, workspace_id: str, query: str, *, kind: str,
                     limit: int = 30, offset: int = 0) -> dict[str, Any]:
    """Search only analyzer runs owned by this workspace and map hits to its assets."""
    if kind not in {"image", "video", "audio"}:
        raise ValueError("Choose image, video, or audio search.")
    if not isinstance(query, str) or not query.strip() or len(query) > 500:
        raise ValueError("Enter a search phrase of up to 500 characters.")
    if type(limit) is not int or not 1 <= limit <= 50 or type(offset) is not int or offset < 0:
        raise ValueError("Invalid semantic search page.")

    run_ids = set()
    for job in video_repertoire.list_jobs("analysis"):
        if (job.get("request", {}).get("workspace_id") != workspace_id
                or job.get("status") != "completed"):
            continue
        for result in (job.get("result", {}).get("audio_analysis", []) or []):
            run_id = result.get("run_id") if isinstance(result, dict) else None
            if isinstance(run_id, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,128}", run_id):
                run_ids.add(run_id)

    retrieval = _retrieval_module()
    runs_root = video_repertoire.analyzer_runs_root().resolve()
    records: list[dict[str, Any]] = []
    run_count = 0
    for run_id in sorted(run_ids):
        run_dir = video_repertoire.safe_path(runs_root / run_id, runs_root)
        manifest_path = run_dir / "manifest.json"
        if (manifest_path.is_symlink()
                or not manifest_path.is_file()):
            continue
        shared_root = video_repertoire.REPERTOIRE_ROOT / "analyses" / "corpus_index_v2"
        shared_index = shared_root / run_id / "index"
        local_v2 = run_dir / "index_v2"
        index_dir = shared_index if (shared_index / "records.jsonl").is_file() else local_v2 if (local_v2 / "records.jsonl").is_file() else run_dir / "index"
        index_root = video_repertoire.REPERTOIRE_ROOT.resolve()
        if (index_dir.is_symlink() or not (index_dir.resolve().is_relative_to(index_root) or index_dir.resolve().is_relative_to(run_dir))
                or any((index_dir / name).is_symlink() for name in ("records.jsonl", "index_manifest.json"))):
            continue
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            index_manifest = json.loads((index_dir / "index_manifest.json").read_text(encoding="utf-8"))
            rows = retrieval._load_records(index_dir)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        if not rows:
            continue
        model = index_manifest.get("model", {})
        vector_fields = index_manifest.get("vector_fields", {})
        peav_dim = int(vector_fields.get("pe_av_vector", 0) or 0)
        text_dim = int(vector_fields.get("pe_av_text_vector", 0) or 0)
        clap_dim = int(vector_fields.get("clap_vector", 0) or 0)
        embeddings = manifest.get("embeddings", {})
        actual_peav = (index_manifest.get("record_schema_version", 0) >= 2
            and model.get("backend") == "pe_av"
            and (embeddings.get("pe_av", {}).get("status") == "completed"
                 or embeddings.get("pe_av", {}).get("text_summary", {}).get("status") == "completed")
            and (peav_dim > 0 or text_dim > 0))
        actual_clap = index_manifest.get("clap", {}).get("status") == "completed" and clap_dim > 0
        if not actual_peav and not actual_clap:
            continue
        for row in rows:
            row_kind = row.get("kind")
            if ((kind == "video" and row_kind not in {"scene_clip", "video_summary"})
                    or (kind == "image" and row_kind != "frame")
                    or (kind == "audio" and row_kind not in {"audio_event", "video_summary"})):
                continue
            has_peav = (actual_peav and ((row.get("index_embedding_backend") == "pe_av"
                and peav_dim and len(row.get("pe_av_vector") or []) == peav_dim)
                or (row.get("pe_av_text_embedding_backend") == "pe_av"
                and text_dim and len(row.get("pe_av_text_vector") or []) == text_dim)))
            has_clap = actual_clap and len(row.get("clap_vector") or []) == clap_dim
            if not (has_peav or has_clap):
                continue
            records.append({**row, "run_id": run_id, "result_id": f"{run_id}:{row.get('record_id')}",
                "index_embedding_backend": "pe_av" if has_peav else "deterministic_fallback",
                "clap_embedding_backend": "laion_clap" if has_clap else "unavailable"})
        run_count += 1

    all_assets = []
    page_offset = 0
    while True:
        page = list_assets(root, workspace_id, kind=kind, limit=100, offset=page_offset,
            include_semantic_vectors=True)
        all_assets.extend(page["assets"])
        page_offset += len(page["assets"])
        if not page["assets"] or page_offset >= page["total"]:
            break
    indexed_count = 0
    content_index_count = 0
    for asset in all_assets:
        saved = asset.get("semantic_annotation_index")
        if asset.get("kind") != kind:
            continue
        if isinstance(saved, dict):
            text = semantic_annotation_text(asset)
            text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
            vector = saved.get("vector")
            if (saved.get("source") == "saved_filename_description_tags_roles"
                    and saved.get("model") == "facebook/pe-av-base"
                    and saved.get("source_sha256") == asset.get("sha256")
                    and saved.get("annotation_sha256") == text_hash
                    and type(saved.get("dimension")) is int
                    and type(vector) is list and len(vector) == saved.get("dimension")
                    and all(type(value) in {int, float} and math.isfinite(value) for value in vector)):
                records.append({"record_id": asset["asset_id"], "result_id": f"asset:{asset['asset_id']}",
                    "asset_id": asset["asset_id"], "kind": {"image":"frame", "video":"scene_clip", "audio":"audio_event"}[kind],
                    "text": text, "pe_av_text_vector": vector, "pe_av_text_embedding_backend": "pe_av",
                    "index_embedding_backend": "unavailable", "clap_embedding_backend": "unavailable",
                    "semantic_source": "saved_annotations"})
                indexed_count += 1
        content = asset.get("semantic_content_index")
        expected_content_source = "image_visual_content" if kind == "image" else f"{kind}_content"
        if (kind in {"audio", "video", "image"} and isinstance(content, dict)
                and content.get("source") == expected_content_source
                and content.get("model") == "facebook/pe-av-base"
                and content.get("source_sha256") == asset.get("sha256")):
            vector = content.get("vector")
            if (type(content.get("dimension")) is int and type(vector) is list
                    and len(vector) == content.get("dimension")
                    and all(type(value) in {int, float} and math.isfinite(value) for value in vector)):
                records.append({"record_id": asset["asset_id"], "result_id": f"asset:{asset['asset_id']}",
                    "asset_id": asset["asset_id"], "kind": {"video":"scene_clip", "audio":"audio_event", "image":"frame"}[kind],
                    "text": asset.get("description") or asset.get("filename") or "",
                    "pe_av_vector": vector, "index_embedding_backend": "pe_av",
                    "clap_embedding_backend": "unavailable", "semantic_source": "media_content" if kind != "image" else "image_visual_content"})
                content_index_count += 1
    published_records = []
    assets_by_record = {}
    for row in records:
        candidates = []
        if row.get("semantic_source") in {"saved_annotations", "media_content", "image_visual_content"}:
            candidates = [asset for asset in all_assets if asset["asset_id"] == row.get("asset_id")]
        else:
            run_assets = [asset for asset in all_assets
                if (asset.get("metadata") or {}).get("analyzer_run_id") == row.get("run_id")]
            if row.get("kind") == "video_summary":
                candidates = run_assets if kind == "video" else [asset for asset in run_assets
                    if (asset.get("metadata") or {}).get("semantic_text_source") == "video_summary"
                    or not str(asset.get("description") or "").strip()
                    or asset.get("description") == "Analyzed audio clip"]
            elif kind == "video":
                candidates = [asset for asset in run_assets
                    if (asset.get("metadata") or {}).get("scene_id") == row.get("scene_id")]
            elif kind == "image":
                candidates = [asset for asset in run_assets
                    if (asset.get("metadata") or {}).get("frame_id") == row.get("record_id")]
            elif kind == "audio":
                candidates = [asset for asset in run_assets
                    if (asset.get("metadata") or {}).get("audio_event_id") == row.get("record_id")]
                if not candidates:
                    start, end = _finite_seconds(row.get("start_time_sec")), _finite_seconds(row.get("end_time_sec"))
                    if start is not None and end is not None and start < end:
                        for asset in run_assets:
                            metadata = asset.get("metadata") or {}
                            clip_start = _finite_seconds(metadata.get("timestamp_start_seconds"))
                            clip_end = _finite_seconds(metadata.get("timestamp_end_seconds"))
                            event_type = str(row.get("event_type") or "").lower()
                            category = asset.get("audio_category")
                            if event_type in {"music", "speech", "sfx"} and category != {"speech":"voice"}.get(event_type,event_type):
                                continue
                            if clip_start is not None and clip_end is not None and clip_start < end and clip_end > start:
                                candidates.append(asset)
        if candidates:
            # Rank semantic records, then expand the complete surviving group. A page
            # limit must not truncate a source video's set of cut clips.
            published_records.append(row)
            assets_by_record[(row.get("run_id"), row.get("record_id"))] = candidates
    result = retrieval.search_records(published_records, query.strip(), top_n=limit, mode="semantic", offset=offset)
    hits, seen = [], set()
    for row in result.get("results", []):
        candidates = assets_by_record.get((row.get("run_id"), row.get("record_id")), [])
        for asset in candidates:
            if asset["asset_id"] in seen:
                continue
            seen.add(asset["asset_id"])
            metadata = asset.get("metadata") or {}
            hits.append({"asset": public_asset_record(asset, workspace_id), "score": row.get("score"), "text": row.get("text", ""),
                "start_time_sec": metadata.get("timestamp_start_seconds", row.get("start_time_sec")),
                "end_time_sec": metadata.get("timestamp_end_seconds", row.get("end_time_sec")),
                "run_id": row.get("run_id"), "record_id": row.get("record_id"),
                "group_id": row.get("run_id") if kind == "video" else None,
                "group_size": len(candidates) if kind == "video" else None,
                "semantic_source": "video_summary" if row.get("kind") == "video_summary" else row.get("semantic_source", "analyzer")})
    result["pagination_unit"] = "semantic_records"
    result.update(results=hits, corpus_run_count=run_count,
        annotation_index_count=indexed_count,
        content_index_count=content_index_count,
        reason=result.get("reason") or (None if hits else "No matching, published semantic results are available for this workspace and media type."))
    return result
