"""Codex execution policies. Project scope denies unrelated user files and network."""
import json
import shutil
from pathlib import Path

MODES = ('project', 'full')


def profile_args(binary):
    # Codex re-enters its own binary inside bubblewrap; :minimal excludes ~/.codex.
    filesystem = {':root': 'deny', ':minimal': 'read', ':tmpdir': 'deny',
                  ':slash_tmp': 'deny', str(Path(binary).resolve().parent): 'read'}
    entries = [f'{json.dumps(key)}={json.dumps(value)}' for key, value in filesystem.items()]
    entries.append('\":workspace_roots\"={\".\"=\"write\"}')
    return ['-c', 'permissions.vibe-project.filesystem={' + ','.join(entries) + '}',
            '-c', 'permissions.vibe-project.network.enabled=false']


def execution_args(mode, workspace):
    if mode not in MODES:
        raise ValueError('Choose Project only or Full access.')
    binary = shutil.which('codex')
    if not binary:
        raise ValueError('Codex CLI is not installed.')
    args = [binary, '--no-daemon', '--ask-for-approval', 'never', 'exec',
            '--ignore-user-config', '--strict-config', '--ephemeral',
            '--skip-git-repo-check', '--cd', str(workspace)]
    # Project config/hooks/connectors must not silently expand this explicit grant.
    for key, value in {'features.hooks': False, 'features.apps': False,
                       'features.plugins': False, 'features.multi_agent': False,
                       'web_search': 'disabled',
                       f'projects.{json.dumps(str(workspace))}.trust_level': 'untrusted'}.items():
        args += ['-c', key + '=' + json.dumps(value)]
    if mode == 'project':
        args += [*profile_args(binary), '-c', 'default_permissions="vibe-project"',
                 '-c', 'shell_environment_policy.inherit="none"']
    else:
        args += ['--sandbox', 'danger-full-access']
    return args
