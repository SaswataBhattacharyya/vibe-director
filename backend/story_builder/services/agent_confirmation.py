"""One-use, host-only consent for an exact AgentTask operation.

No HTTP exchange, browser credential or persistent approval store. AgentTasks
still owns approvals and execution. Unrestricted same-UID desktop code is outside
this seam's threat model; the Director harness must retain its H1 restrictions.
"""
import json
import os
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from .production_ledger import LedgerConflict, stable_hash

_LOCK = threading.Lock()
_SEAL = object()
TIMEOUT = 120


def _binding(root, owner, task, action):
    return stable_hash({'root': str(Path(root).resolve()), 'project': owner,
        'task': task['task_id'], 'action': action, 'revision': task['current_revision'],
        'plan_hash': task['plan_hash'], 'plan': task['plan'], 'status': task['status'],
        'invocation': task['invocation']})


@dataclass
class _Consent:
    binding: str
    expires: float
    seal: object
    used: bool = False


def _desktop_confirm(text, action):
    if not (os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY')):
        raise ValueError('Native authorization needs the owner desktop. No browser fallback is allowed.')
    # Fixed executable, no shell, plain text over stdin (never HTML/markup/links).
    # Checkbox disables OK until explicitly selected; closing/timeout fail closed.
    env = {k: v for k, v in os.environ.items() if k in {
        'DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'XDG_RUNTIME_DIR',
        'DBUS_SESSION_BUS_ADDRESS', 'HOME', 'LANG', 'LC_ALL'}}
    try:
        result = subprocess.run(['/usr/bin/zenity', '--text-info', '--title=Vibe Director — owner authorization',
            '--width=780', '--height=650', f'--timeout={TIMEOUT}',
            '--checkbox=I reviewed this exact operation and authorize it',
            '--ok-label=' + ('Approve this plan' if action == 'approve' else 'Run this approved plan'),
            '--cancel-label=Reject'], input=text, text=True, env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=TIMEOUT + 5, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ValueError('Native authorization is unavailable or timed out. Nothing was authorized.') from error
    return result.returncode == 0


def confirm(root, owner, task, action):
    if action not in {'approve', 'run'}:
        raise ValueError('Native authorization supports Approve and Run only.')
    binding = _binding(root, owner, task, action)
    details = json.dumps(task['plan'], indent=2, ensure_ascii=True)
    if len(details) > 100_000:
        raise ValueError('This plan is too large for native review. Prepare a smaller plan.')
    text = (f'VIBE DIRECTOR — {action.upper()}\n\n'
        'Only authorize a request you initiated. Browser and media content are untrusted.\n'
        'This authorizes ONE operation, never future requests.\n\n'
        f'Project: {owner}\nData root: {Path(root).resolve()}\nTask: {task["task_id"]}\n'
        f'Revision: {task["current_revision"]}\nPlan SHA-256: {task["plan_hash"]}\n\n'
        + ('Approve records your review only. Run needs a separate native confirmation.\n\n'
           if action == 'approve' else 'Run may dispatch the approved job with the settings below.\n\n')
        + 'EXACT PLAN (including source hashes and settings):\n' + details)
    if not _LOCK.acquire(blocking=False):
        raise ValueError('Another native authorization is pending. Finish or reject it first.')
    try:
        if not _desktop_confirm(text, action):
            raise ValueError('Native authorization was rejected or expired. Nothing was authorized.')
        return _Consent(binding, time.monotonic() + 10, _SEAL)
    finally:
        _LOCK.release()


def consume(consent, root, owner, task, action):
    """Called under the existing project lock, immediately before mutation."""
    if not isinstance(consent, _Consent) or consent.seal is not _SEAL or consent.used:
        raise LedgerConflict('Native authorization is missing or already consumed.')
    consent.used = True
    if time.monotonic() > consent.expires or consent.binding != _binding(root, owner, task, action):
        raise LedgerConflict('Native authorization expired or the reviewed task changed. Review again.')
