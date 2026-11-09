"""Host-written restricted Codex profile, matching the accepted H1 boundary."""
import json
import os
import stat
import sys
from pathlib import Path


def private_directory(path):
    path = Path(path)
    if path.is_symlink():
        raise ValueError('Runtime directory must not be a symlink.')
    path.mkdir(mode=0o700, exist_ok=True)
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
        raise ValueError('Runtime directory must be owned and 0700; permissions were not changed.')
    return path


def private_json(path, value):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(value, stream)


def configure(base, codex, manifest, auth_home):
    for name in ('home', 'codex', 'tmp', 'workspace'):
        private_directory(base / name)
    source = Path(auth_home) / 'auth.json'
    if not source.is_file():
        raise RuntimeError('Codex authentication is missing. Sign in outside Vibe before retrying.')
    # Copy only auth; never inherit global MCP, hooks, skills, plugins or env secrets.
    private_json(base / 'codex/auth.json', json.loads(source.read_text()))
    private_json(base / 'gateway.json', manifest)
    features = ['shell_tool', 'unified_exec', 'shell_snapshot', 'multi_agent', 'apps', 'plugins',
                'remote_plugin', 'plugin_discovery_prefetch', 'browser_use', 'browser_use_external',
                'computer_use', 'in_app_browser', 'view_image', 'image_generation', 'hooks',
                'skill_search', 'skill_mcp_dependency_install']
    lines = ['model = "gpt-6-luna"', 'model_reasoning_effort = "low"', 'approval_policy = "never"',
             'web_search = "disabled"', 'default_permissions = "vibe-director"', 'project_doc_max_bytes = 0',
             '[permissions.vibe-director.filesystem]', '":root" = "deny"', '":minimal" = "read"',
             f'{json.dumps(str(base / "workspace"))} = "read"',
             f'{json.dumps(str(Path(codex).resolve()))} = "read"',
             '[permissions.vibe-director.network]', 'enabled = false', '[features]']
    lines += [f'{name} = false' for name in features]
    lines += ['skip_host_skill_discovery = true', '[mcp_servers.vibe]',
              'command = ' + json.dumps(sys.executable),
              'args = ' + json.dumps(['-m', 'story_builder.services.director_mcp', str(base / 'gateway.json')]),
              'required = true', 'enabled_tools = ["media_list", "media_inspect", "task_status", "editor_propose_session", "goal_pause"]',
              'default_tools_approval_mode = "approve"', 'tool_timeout_sec = 40', '[mcp_servers.vibe.env]',
              'PYTHONPATH = ' + json.dumps(str(Path(__file__).resolve().parents[2])),
              'VIBE_DIRECTOR_DATA_DIR = ' + json.dumps(manifest['root'])]
    fd = os.open(base / 'codex/config.toml', os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as stream:
        stream.write('\n'.join(lines) + '\n')
