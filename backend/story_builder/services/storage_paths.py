"""Canonical storage and explicit historical-location translation; no filesystem links."""
from pathlib import Path
import re
import json


def checked(root: Path, *parts: str) -> Path:
    base = Path(root).resolve()
    current = base
    for part in parts:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,100}", part) or part in {".", ".."}:
            raise ValueError("Invalid storage path component.")
        current /= part
        if current.is_symlink():
            raise ValueError("Storage directories cannot be symlinks.")
    return current


def project_folders(root: Path) -> dict:
    path = checked(root, "library") / "project-folders.json"
    if path.is_symlink():
        raise ValueError("Project folder registry cannot be a symlink.")
    data = json.loads(path.read_text()) if path.exists() else {}
    if not isinstance(data, dict):
        raise ValueError("Invalid project folder registry.")
    for workspace, folder in data.items():
        checked(root, "projects", workspace)
        if not isinstance(folder, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 _.-]{0,100}", folder):
            raise ValueError("Invalid project folder name.")
    if len(set(data.values())) != len(data):
        raise ValueError("Project folders must be unique.")
    return data


def project_identity(root: Path, folder: str) -> str:
    return next((key for key, value in project_folders(root).items() if value == folder), folder)


def project_root(root: Path, workspace_id: str) -> Path:
    checked(root, "projects", workspace_id)
    retired = checked(root, "library") / "deleted-projects.json"
    if retired.is_symlink():
        raise ValueError("Deleted project registry cannot be a symlink.")
    if retired.exists() and workspace_id in json.loads(retired.read_text()):
        raise ValueError("This workspace was deleted. Choose an existing workspace or the tool library.")
    folder = project_folders(root).get(workspace_id, workspace_id)
    path = checked(root, "projects") / folder
    if path.is_symlink():
        raise ValueError("Project directories cannot be symlinks.")
    return path


def media_root(root: Path, workspace_id: str) -> Path:
    return checked(root, "library", "tool-media") if workspace_id == "tool-library" else checked(project_root(root, workspace_id), "media")


def generated_root(root: Path, workspace_id: str) -> Path:
    return checked(root, "library", "tool-media", "generated") if workspace_id == "tool-library" else checked(project_root(root, workspace_id), "media", "generated")


def intermediate_root(root: Path, workspace_id: str, category: str) -> Path:
    return checked(project_root(root, workspace_id), "intermediates", category)


def shared_downloads_root(root: Path) -> Path:
    return checked(root, "youtube_downloads", "files")


def repertoire_root(root: Path) -> Path:
    return checked(root, "video_repertoire")


def ace_root(root: Path) -> Path:
    return checked(root, "ace_step")


def shared_file(root: Path, location: dict) -> Path:
    """Resolve an explicit registered location, never an arbitrary absolute path."""
    if isinstance(location, dict) and location.get("store") == "output":
        from .output_destinations import locate_file
        return locate_file(root, location)
    stores = {"youtube": shared_downloads_root(root), "repertoire": repertoire_root(root),
              "audio": checked(root, "audio_studio"), "ace": ace_root(root)}
    if not isinstance(location, dict) or location.get("store") not in stores:
        raise ValueError("Unknown shared media store.")
    base = stores[location["store"]]
    relative = Path(location.get("path", ""))
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        raise ValueError("Invalid shared media path.")
    if location["store"] == "repertoire" and relative.parts[:1] == ("runs",):
        from .output_destinations import resolve_run_path
        mapped = resolve_run_path(root, base / relative)
        if mapped != base / relative:
            if not mapped.is_file(): raise FileNotFoundError("Analysis artifact is unavailable.")
            return mapped
    candidate = base
    for part in relative.parts:
        candidate /= part
        if candidate.is_symlink():
            raise ValueError("Shared media cannot contain symlinks.")
    if not candidate.resolve().is_relative_to(base.resolve()) or not candidate.is_file():
        raise FileNotFoundError("Shared media is unavailable; restore its registered location.")
    return candidate


def relocated_path(root: Path, path: Path) -> Path:
    """Translate historical locations without rewriting frozen request payloads."""
    root, path = Path(root).resolve(), Path(path)
    moves = [("library/downloads/youtube", "youtube_downloads/files"),
             ("engines/youtube-import/out_videos", "youtube_downloads/files/legacy_import"),
             ("services/media/analyses/video_audio_analyzer", "video_repertoire/runs"),
             ("library/catalog/donor-video", "video_repertoire/legacy/donor-video"),
             ("library/catalog/legacy-video/out_videos", "video_repertoire/legacy/out_videos"),
             ("services/music", "ace_step")]
    moves += [("services/media/" + name, "video_repertoire/" + name)
              for name in ("analyses", "uploads", "clips", "manifests", "indexes", "audio", "temp")]
    for old, new in moves:
        if path.is_relative_to(root / old):
            return root / new / path.relative_to(root / old)
    return path


_PATH_FIELDS = {
    "path", "source_path", "output_path", "artifact_path", "dataset_path",
    "run_path", "file_path", "directory", "output_dir", "source_dir",
    "dataset_dir", "run_dir", "checkpoint_dir",
}


def relocate_record_paths(root: Path, value):
    """Translate explicit path fields without editing logs or prompt text."""
    if isinstance(value, list):
        return [relocate_record_paths(root, item) for item in value]
    if not isinstance(value, dict):
        return value
    result = {}
    for key, item in value.items():
        if isinstance(item, str) and key in _PATH_FIELDS:
            candidate = Path(item).expanduser()
            if not candidate.is_absolute():
                candidate = Path(root) / candidate
            result[key] = str(relocated_path(root, candidate))
        else:
            result[key] = relocate_record_paths(root, item)
    return result


def load_project_documents(root: Path, data: dict) -> dict:
    """Expand the small service registry into existing in-memory project contracts."""
    import json
    if "project_files" in data:
        projects = []
        for relative in data["project_files"]:
            path = Path(relative)
            if path.is_absolute() or ".." in path.parts or path.parts[:1] != ("projects",):
                raise ValueError("Invalid project registry location.")
            candidate = Path(root)
            for part in path.parts:
                candidate /= part
                if candidate.is_symlink():
                    raise ValueError("Project documents cannot be symlinks.")
            projects.append(json.loads(candidate.read_text()))
        data["projects"] = projects
    return data


def save_project_documents(root: Path, data: dict, tool: str, write) -> dict:
    """Keep styles/service state global and each project document in its workspace."""
    registry = {k: v for k, v in data.items() if k not in {"projects", "project_files"}}
    registry["project_files"] = []
    for project in data.get("projects", []):
        workspace = project.get("workspace_id") or project["id"]
        path = checked(project_root(root, workspace), "music" if tool == "ace" else "editor", tool, project["id"]) / "project.json"
        write(path, project)
        registry["project_files"].append(path.relative_to(Path(root)).as_posix())
    return registry
