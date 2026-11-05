"""Explicit output-folder grants, saved choices and frozen job publication targets."""
from __future__ import annotations
import hashlib
import json
import os
import re
import shutil
import subprocess
import uuid
from pathlib import Path
from .storage_paths import checked, generated_root

TOOLS = {
    'audio-effects': 'audio_studio/voice_changes', 'voice-studio': 'audio_studio/output',
    'audio-utilities': 'audio_studio/output', 'timed-tts': 'audio_studio/output',
    'recordings': 'audio_studio/recordings', 'ace-studio': 'ace_step/output',
    'ace-music': 'ace_step/output', 'control-foley': 'audio_studio/output',
    'audio-scene-split': 'audio_studio/output', 'audio-scene-stitch': 'audio_studio/output',
    'analysis': 'video_repertoire/runs',
    'image-generation': None, 'video-generation': None, 'assembly-export': None,
}

def home(root):
    return checked(root, 'library', 'output_destinations')

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        temporary.write_text(json.dumps(value, indent=2))
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)

def grant(root, value=None):
    if not value:
        result = subprocess.run(['zenity', '--file-selection', '--directory', '--title=Choose output folder'],
                                capture_output=True, text=True, timeout=120)
        if result.returncode: raise ValueError('Folder selection cancelled. You can also enter an existing absolute folder path.')
        value = result.stdout.strip()
    path = Path(str(value)).expanduser()
    if not path.is_absolute() or not path.is_dir(): raise ValueError('Choose an existing absolute folder path.')
    path = path.resolve(strict=True)
    token = uuid.uuid4().hex
    write(checked(root, 'library', 'output_destinations', 'grants') / f'{token}.json', {'path': str(path)})
    return {'grant': token, 'path': str(path)}

def granted(root, token):
    if not isinstance(token, str) or not re.fullmatch(r'[a-f0-9]{32}', token): raise ValueError('Invalid output folder grant.')
    path = checked(root, 'library', 'output_destinations', 'grants') / f'{token}.json'
    if path.is_symlink(): raise ValueError('Invalid output folder grant.')
    value = Path(json.loads(path.read_text())['path'])
    if not value.is_absolute() or not value.is_dir() or value.resolve() != value:
        raise ValueError('Output folder unavailable. Locate it again; no fallback folder was used.')
    return value

def preference_path(root, tool, workspace):
    if tool not in TOOLS: raise ValueError('Unsupported output tool.')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}', workspace): raise ValueError('Invalid workspace context.')
    return checked(root, 'library', 'output_destinations', 'preferences') / f'{tool}--{workspace}.json'

def resolve(root, tool, workspace, choice):
    mode = choice.get('mode', 'default')
    if mode == 'folder': path = granted(root, choice.get('grant'))
    elif mode == 'workspace':
        if workspace == 'tool-library': raise ValueError('Select a workspace to save workspace output.')
        path = generated_root(root, workspace)
    elif mode == 'default': path = Path(root).resolve() / TOOLS[tool] if TOOLS[tool] else generated_root(root, workspace)
    else: raise ValueError('Unknown output destination.')
    return {**choice, 'mode': mode, 'path': str(path)}

def preference(root, tool, workspace, choice=None, *, allow_unavailable=False):
    path = preference_path(root, tool, workspace)
    if choice is None: choice = json.loads(path.read_text()) if path.exists() else {'mode': 'default'}
    else:
        choice = {k: choice[k] for k in ('mode', 'grant') if k in choice}
        resolved = resolve(root, tool, workspace, choice)
        write(path, choice)
        return resolved
    try:
        return resolve(root, tool, workspace, choice)
    except (ValueError, FileNotFoundError):
        if not allow_unavailable or choice.get('mode') != 'folder': raise
        token = choice.get('grant')
        if not isinstance(token, str) or not re.fullmatch(r'[a-f0-9]{32}', token): raise
        record = checked(root, 'library', 'output_destinations', 'grants') / f'{token}.json'
        if record.is_symlink(): raise ValueError('Invalid saved folder.')
        return {**choice, 'path': (json.loads(record.read_text())['path'] if record.exists() else ''), 'available': False}

def freeze(root, tool, request):
    if tool not in TOOLS: return request
    # Training artifacts have their own model publication and resume contract.
    if request.get('operation') in {'finetune', 'training', 'chat'}: return request
    workspace = request.get('workspace_id') or 'tool-library'
    choice = preference(root, tool, workspace)
    base = target_root(root, choice)
    # Fail before rendering if the chosen destination is not writable.
    probe = base / ('.vibe-write-check-' + uuid.uuid4().hex)
    try:
        with probe.open('xb') as stream: stream.write(b'')
    finally: probe.unlink(missing_ok=True)
    return {**request, 'output_destination': choice}

def target_root(root, choice):
    if choice['mode'] == 'folder': return granted(root, choice['grant'])
    path = Path(choice['path'])
    if not path.is_relative_to(Path(root).resolve()): raise ValueError('Invalid internal output destination.')
    cursor = path
    while cursor != Path(root).resolve():
        if cursor.is_symlink(): raise ValueError('Output path cannot contain symlinks.')
        cursor = cursor.parent
    path.mkdir(parents=True, exist_ok=True)
    return path

def locate_file(root, location):
    base = granted(root, location.get('grant'))
    relative = Path(location.get('path', ''))
    if relative.is_absolute() or not relative.parts or '..' in relative.parts: raise ValueError('Invalid output file location.')
    cursor = base
    for part in relative.parts:
        cursor /= part
        if cursor.is_symlink(): raise ValueError('Output files cannot use symlinks.')
    if not cursor.is_file(): raise FileNotFoundError('Output unavailable. Locate its folder again.')
    return cursor

def digest(path):
    with path.open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()

def copy_verified(source, target):
    """Publish without overwriting unrelated user files; source survives failures."""
    cursor = target
    while cursor != cursor.parent:
        if cursor.is_symlink(): raise ValueError('Output path cannot contain symlinks.')
        cursor = cursor.parent
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if not target.is_file() or digest(source) != digest(target): raise ValueError('Output filename already exists with different content.')
        return
    temporary = target.with_name('.' + target.name + '.' + uuid.uuid4().hex + '.part')
    try:
        shutil.copyfile(source, temporary)
        if digest(source) != digest(temporary): raise ValueError('Output verification failed; original retained.')
        # Atomic no-clobber publication even when another process writes this name.
        os.link(temporary, target)
    finally: temporary.unlink(missing_ok=True)

def finalize(root, job, result):
    """Relocate only this job's registered final assets, preserving IDs and URLs."""
    choice = job['request'].get('output_destination')
    if not choice or result.get('job_status') == 'recovery_required': return result
    if job['kind'] == 'analysis': return finalize_analysis(root, job, result, choice)
    from . import media_library
    workspace = job['request'].get('workspace_id') or 'tool-library'
    identities = set()
    def visit(value):
        if isinstance(value, dict):
            if value.get('asset_id') and value.get('content_url'): identities.add((value.get('workspace_id') or workspace, value['asset_id']))
            for item in value.values(): visit(item)
        elif isinstance(value, list):
            for item in value: visit(item)
    visit(result)
    relocated = {}
    for owner, identity in identities:
        relocated[(owner, identity)] = media_library.relocate_output(root, owner, identity, choice, job['job_id'])
    def refresh(value):
        if isinstance(value, dict):
            key = (value.get('workspace_id') or workspace, value.get('asset_id'))
            if key in relocated and value.get('content_url'): return relocated[key]
            return {k: refresh(v) for k, v in value.items()}
        if isinstance(value, list): return [refresh(v) for v in value]
        return value
    return refresh(result)


def run_location(root, run_id):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,160}', run_id):
        raise ValueError('Invalid analyzer run ID.')
    return checked(root, 'library', 'output_destinations', 'runs') / (run_id + '.json')


def resolve_run_path(root, path):
    """Translate only registered canonical run paths, preserving all relative artifacts."""
    base = Path(root).resolve() / 'video_repertoire' / 'runs'
    path = Path(path)
    if not path.is_relative_to(base): return path
    parts = path.relative_to(base).parts
    if not parts: return path
    mapping = run_location(root, parts[0])
    if not mapping.exists(): return path
    location = json.loads(mapping.read_text())
    destination = granted(root, location['grant'])
    candidate = destination
    for part in Path(location['path'], *parts[1:]).parts:
        if part in {'..', '.'} or Path(part).is_absolute(): raise ValueError('Invalid analyzer artifact path.')
        candidate /= part
        if candidate.is_symlink(): raise ValueError('Analyzer artifacts cannot use symlinks.')
    if not candidate.is_relative_to(destination): raise ValueError('Invalid analyzer artifact path.')
    if not candidate.exists(): raise FileNotFoundError('Analysis output unavailable; locate its output folder again.')
    return candidate


def finalize_analysis(root, job, result, choice):
    """Publish complete runs, then switch their single location after byte verification."""
    base = target_root(root, choice)
    canonical = Path(root).resolve() / 'video_repertoire' / 'runs'
    if base == canonical: return result
    for row in result.get('audio_analysis') or []:
        run_id = row.get('run_id')
        if not run_id: continue
        mapping = run_location(root, run_id)
        source = canonical / run_id
        if not source.is_dir():
            resolve_run_path(root, source)  # An already published retry must still be available.
            continue
        if mapping.exists(): raise ValueError('Analyzer run already has a saved location; staging retained for recovery.')
        target = base / job['job_id'] / run_id
        if target.exists(): raise ValueError('Analysis output folder already exists; staging retained for recovery.')
        files = list(source.rglob('*'))
        if any(p.is_symlink() for p in files): raise ValueError('Analyzer run contains a symlink; staging retained.')
        try:
            target.mkdir(parents=True, exist_ok=False)
            for item in files:
                if item.is_file(): copy_verified(item, target / item.relative_to(source))
            token = choice.get('grant') or grant(root, str(base))['grant']
            write(mapping, {'grant': token, 'path': target.relative_to(base).as_posix(), 'job_id': job['job_id'], 'files': {item.relative_to(source).as_posix(): digest(item) for item in files if item.is_file()}})
        except Exception:
            # This directory was created by us, and publication has not switched.
            if not mapping.exists(): shutil.rmtree(target, ignore_errors=True)
            raise
        shutil.rmtree(source)
        row['saved_path'] = str(target)
    return result


def locate_saved_folder(root, tool, workspace, selected_grant):
    """Repair an unavailable grant only after all registered files match their hashes."""
    saved = json.loads(preference_path(root, tool, workspace).read_text())
    if saved.get('mode') != 'folder': raise ValueError('This tool has no saved external folder to locate.')
    token = saved['grant']
    old_file = checked(root, 'library', 'output_destinations', 'grants') / f'{token}.json'
    if not re.fullmatch(r'[a-f0-9]{32}', token) or old_file.is_symlink(): raise ValueError('Invalid saved folder.')
    target = granted(root, selected_grant)
    expected = {}
    manifests = list((Path(root) / 'projects').glob('*/media/assets.json'))
    manifests.append(checked(root, 'library', 'tool-media') / 'assets.json')
    for manifest in manifests:
        if manifest.is_symlink(): raise ValueError('Invalid media catalogue.')
        if not manifest.is_file(): continue
        for record in json.loads(manifest.read_text()).get('assets', []):
            location = record.get('storage_location') or {}
            if location.get('store') == 'output' and location.get('grant') == token:
                expected[location['path']] = record['sha256']
    for mapping in checked(root, 'library', 'output_destinations', 'runs').glob('*.json'):
        if mapping.is_symlink(): raise ValueError('Invalid run location.')
        location = json.loads(mapping.read_text())
        if location.get('grant') != token: continue
        if not location.get('files'): raise ValueError('This older analysis needs manual location verification before relinking.')
        expected.update({str(Path(location['path']) / path): sha for path, sha in location['files'].items()})
    for relative, sha in expected.items():
        path = Path(relative)
        if path.is_absolute() or '..' in path.parts: raise ValueError('Invalid saved file location.')
        current = target
        for part in path.parts:
            current /= part
            if current.is_symlink(): raise ValueError('Located output cannot contain symlinks.')
        if not current.is_file() or digest(current) != sha:
            raise ValueError('That folder does not contain the saved files with matching content. Nothing was relinked.')
    write(old_file, {'path': str(target)})
    return preference(root, tool, workspace)
