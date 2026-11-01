"""Register canonical analyzer artifacts without making workspace copies."""
from __future__ import annotations
from story_builder.services.storage_paths import repertoire_root

import hashlib
import re
from pathlib import Path
from typing import Any

from story_builder.services.media_library import ProductionAssetError, SUFFIX_KIND, register_derived_media


_SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
_SAFE_OCCURRENCE = re.compile(r"^[A-Za-z0-9_-]{1,160}$")
_SAFE_WORKSPACE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$")
_MAX_OUTPUTS_PER_RUN = 1000


def publish_analyzer_outputs(root: Path, workspace_id: str, *, source_asset_id: str,
                             source_sha256: str, derivation_id: str,
                             run_dir: Path, outputs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Index selected run-relative image/video/audio outputs without copying bytes.

    ``outputs`` is a bounded projection from the analyzer manifest. Paths must
    be relative to ``run_dir``; container paths and arbitrary absolute paths
    are resolved by the job adapter before this call, never guessed here.
    Each row requires kind and a stable occurrence_id. Remaining fields are
    retained as searchable provenance metadata.
    """
    if not isinstance(outputs, list) or len(outputs) > _MAX_OUTPUTS_PER_RUN:
        raise ProductionAssetError("Analyzer output list is invalid or too large.")
    if not _SAFE_ID.fullmatch(derivation_id) or not _SAFE_WORKSPACE.fullmatch(workspace_id):
        raise ProductionAssetError("Analyzer derivation or workspace ID is invalid.")

    root = Path(root).resolve()
    run_dir = Path(run_dir).resolve(strict=True)
    shared_root = repertoire_root(root)
    if not run_dir.is_relative_to(shared_root.resolve()):
        raise ProductionAssetError("Analyzer runs must be inside the shared repertoire.")

    published: list[dict[str, Any]] = []
    for row in outputs:
        if not isinstance(row, dict):
            raise ProductionAssetError("Analyzer output record is invalid.")
        relative_value = row.get("relative_path")
        kind = row.get("kind")
        occurrence_id = row.get("occurrence_id")
        if (type(relative_value) is not str or not relative_value
                or type(kind) is not str or kind not in {"image", "video", "audio"}
                or type(occurrence_id) is not str or not _SAFE_OCCURRENCE.fullmatch(occurrence_id)):
            raise ProductionAssetError("Analyzer output identity is invalid.")
        relative = Path(relative_value)
        if relative.is_absolute() or ".." in relative.parts or not relative.parts:
            raise ProductionAssetError("Analyzer output path must remain inside its run.")
        source = run_dir / relative
        resolved_source = source.resolve()
        cursor = source
        symlinked = False
        while cursor == run_dir or cursor.is_relative_to(run_dir):
            symlinked = symlinked or cursor.is_symlink()
            if cursor == run_dir:
                break
            cursor = cursor.parent
        suffix = resolved_source.suffix.lower()
        if (not resolved_source.is_relative_to(run_dir) or not source.is_file() or symlinked
                or SUFFIX_KIND.get(suffix) != kind):
            raise ProductionAssetError("Analyzer output is missing or outside its run.")

        output_relative = resolved_source.relative_to(shared_root).as_posix()
        metadata = {key: value for key, value in row.items()
                    if key not in {"relative_path", "kind", "occurrence_id"}}
        metadata["occurrence_id"] = occurrence_id
        metadata["analyzer_relative_path"] = relative.as_posix()
        published.append(register_derived_media(root, workspace_id, output_relative,
            source_asset_id=source_asset_id, source_sha256=source_sha256,
            derivation_id=derivation_id, kind=kind, metadata=metadata,
            storage_location={"store": "repertoire", "path": output_relative}))
    return published
