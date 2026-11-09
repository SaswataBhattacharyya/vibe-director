"""Metadata-first skill registry. Files are guidance, never execution grants."""
import hashlib
import json
import os
import re
from itertools import islice
from pathlib import Path
from .storage_paths import project_root

REPO = Path(__file__).resolve().parents[3]
BLUEPRINT = REPO / 'fixes/vibe-director-codex-agent-blueprint-v2/vibe-director-codex-agent-blueprint'
APPLICATION_ROOTS = {'vibe': REPO / 'skills', 'editor': REPO / 'design/vibe-editor/skills',
                     'filmmaking': BLUEPRINT / 'skills'}
MAX_SKILLS = 256


def selected_context(root, workspace, refs):
    """Load only explicitly selected, available identities within the same safe roots."""
    if not isinstance(refs, list) or len(refs) > 6 or any(not isinstance(ref, str) for ref in refs):
        raise ValueError('Select at most six skills.')
    registry = {row['ref']: row for row in discover(root, workspace)['skills']}
    configured = json.loads(os.environ.get('VIBE_DIRECTOR_AGENT_SKILL_ROOTS', '{}'))
    selected = []
    for ref in dict.fromkeys(refs):
        row = registry.get(ref)
        if not row or not row['available']:
            raise ValueError('Selected skill is unavailable; refresh capabilities.')
        scope, provider, ident = ref.split('/')
        if scope == 'global':
            folder = Path(configured[provider])
        elif scope == 'project':
            folder = project_root(root, workspace) / 'skills'
        else:
            folder = APPLICATION_ROOTS[provider]
        content = read_content(folder, f'{ident}/SKILL.md')
        if hashlib.sha256(content.encode()).hexdigest() != row['sha256']:
            raise ValueError('Skill changed while loading; refresh capabilities.')
        selected.append({'ref': ref, 'sha256': row['sha256'], 'content': content})
    if any(row['ref'].startswith('application/filmmaking/') for row in selected):
        contract = read_content(BLUEPRINT, 'shared/CONTRACT.md')
        selected.append({'ref': 'application/filmmaking/shared-contract',
                         'sha256': hashlib.sha256(contract.encode()).hexdigest(), 'content': contract})
    if sum(len(row['content']) for row in selected) > 48000:
        raise ValueError('Selected skills exceed the combined context budget.')
    return selected


def read_content(root: Path, relative: str, *, limit: int = 24000) -> str:
    root = Path(root)
    relative = Path(relative)
    if relative.is_absolute() or '..' in relative.parts or not relative.parts:
        raise ValueError('Invalid skill reference.')
    path = root / relative
    if any(p.is_symlink() for p in (path, *path.parents)) or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('Skill references cannot escape their registered root or use symlinks.')
    if not path.is_file():
        raise FileNotFoundError('Skill source is unavailable.')
    with path.open(encoding='utf-8') as stream:
        content = stream.read(limit + 1)
    if len(content) > limit:
        raise ValueError('Skill exceeds its context budget.')
    return content


def _metadata(scope, provider, root, skill_id):
    result = {'ref': f'{scope}/{provider}/{skill_id}', 'id': skill_id, 'scope': scope,
        'provider': provider, 'description': '', 'sha256': None, 'version': None, 'available': False}
    try:
        text = read_content(root, f'{skill_id}/SKILL.md')
        result.update(available=True, sha256=hashlib.sha256(text.encode()).hexdigest())
        # Only presentation metadata is parsed; no YAML constructors or executable directives.
        front = text.split('---', 2)[1] if text.startswith('---\n') and text.count('---') >= 2 else ''
        for field in ('description', 'version'):
            match = re.search(rf'(?m)^{field}:\s*([^\n]+)(?:\n((?:[ \t]+[^\n]*\n?)*))?', front)
            if match:
                value = match[1].strip().strip('"\'')
                if value in {'>', '|', '>-', '|-'}:
                    value = ' '.join((match[2] or '').split())
                result[field] = value[:1000]
    except (OSError, ValueError):
        result['reason'] = 'Skill is missing, unreadable, unsafe, or exceeds its context budget.'
    return result


def discover(root: Path, workspace: str) -> dict:
    rows = [_metadata('application', 'vibe', REPO / 'skills', name)
        for name in ('vibe-director', 'video-prompting', 'prompt-craft', 'z-image-prompting', 'qwen-image-edit-prompting', 'flux-kontext-prompting', 'frame-interpolation', 'kdenlive-clip-continuity-and-stitching')]
    rows.append(_metadata('application', 'editor', REPO / 'design/vibe-editor/skills', 'vibe-editor-director'))
    configured = json.loads(os.environ.get('VIBE_DIRECTOR_AGENT_SKILL_ROOTS', '{}'))
    if not isinstance(configured, dict) or len(configured) > 16:
        raise ValueError('Skill roots must be a bounded provider-to-directory object.')
    roots = [('application', 'filmmaking', APPLICATION_ROOTS['filmmaking'])]
    for provider, folder in configured.items():
        if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,63}', provider) or not isinstance(folder, str) or not Path(folder).is_absolute():
            raise ValueError('Invalid global skill provider configuration.')
        roots.append(('global', provider, Path(folder)))
    if workspace != 'tool-library':
        roots.append(('project', workspace, project_root(root, workspace) / 'skills'))
    truncated = False
    for scope, provider, folder in roots:
        if len(rows) >= MAX_SKILLS:
            truncated = True
            break
        try:
            if not folder.is_dir() or any(p.is_symlink() for p in (folder, *folder.parents)):
                raise ValueError('Unavailable root')
            # One directory per skill; never recursively scan home or the fixes archive.
            with os.scandir(folder) as entries:
                names = sorted(entry.name for entry in islice(entries, MAX_SKILLS + 1))
        except (OSError, ValueError):
            rows.append({'ref': f'{scope}/{provider}', 'scope': scope, 'provider': provider, 'id': '',
                'description': '', 'sha256': None, 'version': None, 'available': False, 'reason': 'Skill root is unavailable.'})
            continue
        truncated |= len(names) > MAX_SKILLS
        for name in names[:MAX_SKILLS]:
            entry = folder / name
            if len(rows) >= MAX_SKILLS:
                truncated = True
                break
            if re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,100}', entry.name) and (entry.is_dir() or entry.is_symlink()):
                rows.append(_metadata(scope, provider, folder, entry.name))
    return {'skills': rows[:MAX_SKILLS], 'truncated': truncated or len(rows) > MAX_SKILLS}
