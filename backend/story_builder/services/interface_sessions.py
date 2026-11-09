"""Owned, expiring native GUI processes; never manage another application's process."""
import atexit
import os
import secrets
import shutil
import signal
import socket
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from urllib.request import Request, urlopen

_sessions = {}
_lock = threading.RLock()


def create(root, kind, owner):
    token = secrets.token_urlsafe(32)
    session = {'token': token, 'root': Path(root).resolve(), 'kind': kind, 'owner': owner,
               'folder': Path(tempfile.mkdtemp(prefix=f'vibe-{kind}-')), 'used': time.monotonic(),
               'operation_lock': threading.RLock()}
    with _lock:
        _sessions[token] = session
    return session


def get(root, token, kind, owner, *, allow_stopped=False):
    with _lock:
        s = _sessions.get(token) if isinstance(token, str) else None
        if not s or (s['root'], s['kind'], s['owner']) != (Path(root).resolve(), kind, owner):
            raise ValueError('Native workspace expired or belongs to another session. Open it again.')
        s['used'] = time.monotonic()
        if not allow_stopped and s.get('process') and s['process'].poll() is not None:
            raise ValueError('Native workspace stopped. Close and reopen it.')
        return s


def launch(s, command, *, env=None, health='/'):
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    s['url'] = f'http://127.0.0.1:{port}'
    s['log'] = open(s['folder'] / 'server.log', 'wb')
    # Do not pass provider credentials or the user's HOME to specialist runtimes.
    clean_env = {'PATH': os.environ.get('PATH', '/usr/bin:/bin'), 'HOME': str(s['folder']),
                 'DO_NOT_TRACK': '1', 'HYPERFRAMES_NO_TELEMETRY': '1', **(env or {})}
    try:
        s['process'] = subprocess.Popen([*map(str, command), str(port), s['token']],
            env=clean_env, cwd=s['folder'], stdout=s['log'], stderr=subprocess.STDOUT, start_new_session=True)
        for _ in range(100):
            if s['process'].poll() is not None:
                raise ValueError('Native workspace failed: ' + (s['folder'] / 'server.log').read_text()[-1800:])
            try:
                with urlopen(Request(s['url'] + health, headers={'Cookie': f'vibe-interface-{s["token"][:12]}={s["token"]}'}), timeout=.3) as response:
                    if response.status == 200:
                        return {'token': s['token'], 'url': s['url'] + f'/?vibe_token={s["token"]}'}
            except OSError:
                time.sleep(.1)
        raise ValueError('Native workspace did not become ready.')
    except BaseException:
        close(s)
        raise


def close(s):
    with s['operation_lock']:
        _close(s)


def _close(s):
    with _lock:
        if s.get('closed'):
            return
        s['closed'] = True
        _sessions.pop(s['token'], None)
        process = s.get('process')
        if process and process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=3)
            except ProcessLookupError:
                pass
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=3)
        if s.get('log'):
            s['log'].close()
        if s['folder'].exists():
            shutil.rmtree(s['folder'])


def _reap():
    with _lock:
        expired = [s for s in _sessions.values() if time.monotonic() - s['used'] > 1800]
    for s in expired:
        close(s)
    timer = threading.Timer(60, _reap)
    timer.daemon = True
    timer.start()


def _shutdown():
    for s in list(_sessions.values()):
        close(s)


atexit.register(_shutdown)
_reap()
