#!/usr/bin/env python3
"""Rebase copied Video Repertoire manifests onto their copied media files."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path


def rebase_manifests(stage_root: Path, donor_root: Path, downloads_root: Path | None = None, youtube_root: Path | None = None) -> tuple[int, int]:
    stage_root = stage_root.resolve(strict=True)
    donor_root = donor_root.resolve(strict=True)
    downloads_root = (downloads_root or stage_root / "downloads").resolve()
    youtube_root = (youtube_root or stage_root.parent / "youtube_code").resolve()
    changed = missing = 0
    manifest_root = stage_root / "manifests"
    if not manifest_root.is_dir():
        return changed, missing
    for manifest_path in manifest_root.glob("video-*.json"):
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        old_value = manifest.get("path")
        if not isinstance(old_value, str):
            continue
        old_path = Path(old_value)
        fallback_source = old_path.parts[-3:-1] in {
            ("video_summarizer", "out_videos"), ("video_summariser", "out_videos")}
        try:
            relative = old_path.resolve(strict=False).relative_to(donor_root)
        except ValueError:
            if not fallback_source:
                continue
            relative = None
        if relative is not None and (not relative.parts or relative.parts[0] not in {"downloads", "uploads", "clips", "frames", "audio", "music"}):
            continue
        staged_path = (stage_root / relative).resolve(strict=False) if relative is not None else stage_root
        if relative is not None and relative.parts[0] == "downloads":
            staged_path = (downloads_root / Path(*relative.parts[1:])).resolve()
        # Retained manifests may name an old summarizer export that
        # was later kept in `youtube_code/out_videos`; allow only byte-identical files.
        if not staged_path.is_file() and fallback_source:
            alternative = (youtube_root / "out_videos" / old_path.name).resolve(strict=False)
            expected_hash = manifest.get("sha256")
            if (alternative.is_relative_to(youtube_root) and alternative.is_file()
                    and isinstance(expected_hash, str) and len(expected_hash) == 64):
                digest = hashlib.sha256()
                with alternative.open("rb") as media:
                    for block in iter(lambda: media.read(1024 * 1024), b""):
                        digest.update(block)
                if digest.hexdigest() == expected_hash:
                    staged_path = alternative
        if not any(staged_path.is_relative_to(base) for base in (stage_root, downloads_root, youtube_root)):
            missing += 1
            continue
        if not staged_path.is_file():
            missing += 1
            continue
        new_value = str(staged_path)
        if old_value == new_value:
            continue
        manifest["path"] = new_value
        fd, temporary = tempfile.mkstemp(prefix=".manifest-", dir=manifest_root)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(manifest, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, manifest_path)
        except Exception:
            Path(temporary).unlink(missing_ok=True)
            raise
        changed += 1
    return changed, missing


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage-root", type=Path, required=True)
    parser.add_argument("--donor-root", type=Path, required=True)
    parser.add_argument("--downloads-root", type=Path)
    parser.add_argument("--youtube-root", type=Path)
    args = parser.parse_args()
    changed, missing = rebase_manifests(args.stage_root, args.donor_root, args.downloads_root, args.youtube_root)
    print(f"Rebased {changed} copied video manifests; {missing} staged media files were missing.")


if __name__ == "__main__":
    main()
