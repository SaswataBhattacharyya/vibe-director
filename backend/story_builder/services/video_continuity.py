"""Hash-bound last-frame continuity; no provider calls or video submission."""
import hashlib
import subprocess
import tempfile
from pathlib import Path
from story_builder.services.media_library import asset_path, list_assets, register_upload

INTENT = ("This is the last frame of the preceding clip, a spatial continuity reference. "
    "Preserve the world's layout, geometry and established character appearance unless the new shot explicitly changes them. Preserve lighting continuity unless directed otherwise. "
    "Advance ONLY the new screenplay shot/action described below; do not replay the preceding action "
    "or copy its camera movement. Follow the new shot's camera direction.")

def last_frame(root, workspace, output, *, create=True):
    source_id = output["shared_asset_id"]
    digest = output["sha256"]
    source, media_type, _ = asset_path(root, workspace, source_id)
    if not media_type.startswith("video/") or hashlib.sha256(source.read_bytes()).hexdigest() != digest:
        raise ValueError("The preceding video is missing or changed.")
    offset = 0
    while True:
        rows = list_assets(root, workspace, kind="image", limit=100, offset=offset)["assets"]
        for row in rows:
            metadata = row.get("metadata") or {}
            if {"asset_id": source_id, "sha256": digest, "frame": "last"} in (metadata.get("continuity_sources") or [metadata.get("continuity_source")]):
                path, _, _ = asset_path(root, workspace, row["asset_id"])
                if hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"]:
                    return {"asset_id": row["asset_id"], "sha256": row["sha256"], "role": "continuity", "intent": INTENT}
        if len(rows) < 100:
            break
        offset += 100
    if not create:
        raise ValueError("Prepare the preceding clip's last-frame image before generating.")
    with tempfile.TemporaryDirectory(prefix="vibe-last-frame-") as folder:
        target = Path(folder) / "last.png"
        # Decode the short clip in order; update leaves the actual last decoded frame.
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
            "-i", str(source), "-map", "0:v:0", "-an", "-fps_mode", "passthrough",
            "-update", "1", str(target)], check=True, capture_output=True, timeout=90)
        row = register_upload(root, workspace, filename="continuity-last-frame.png", content=target.read_bytes(),
            role="project_image", provenance_notes="Last frame extracted from generated predecessor video.",
            metadata={"continuity_sources": [{"asset_id": source_id, "sha256": digest, "frame": "last"}]})
    return {"asset_id": row["asset_id"], "sha256": row["sha256"], "role": "continuity", "intent": INTENT}
