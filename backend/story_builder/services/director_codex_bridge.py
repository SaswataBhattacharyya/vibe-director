"""Host-only Codex stdio transport; no application permissions or storage here.

The caller owns a private, reviewed CODEX_HOME, sandbox profile and MCP config.
Never pass browser/model requests through this interface. Only Vibe's gateway
can authorize tools. Production conversation routing is deliberately unchanged.
One host worker owns a client; callbacks observe untrusted streamed data.
"""
import json
import os
import queue
import signal
import stat
import subprocess
import threading
import time
from pathlib import Path
from typing import Callable


class AppServer:
    METHODS = frozenset({'initialize', 'thread/start', 'thread/resume', 'thread/read',
        'turn/start', 'turn/interrupt', 'mcpServerStatus/list', 'mcpServer/tool/call'})
    FRAME_LIMIT = 1024 * 1024
    EVENT_LIMIT = 4 * 1024 * 1024

    def __init__(self, base: Path, codex: str, *, on_event: Callable[[dict], None] | None = None):
        self.events: list[dict] = []
        self.inbox: queue.Queue = queue.Queue(maxsize=512)
        self.serial, self.event_bytes = 0, 0
        self.on_event = on_event
        self.closed = threading.Event()
        base = Path(base)
        for path in (base, base / 'home', base / 'codex', base / 'tmp', base / 'workspace'):
            info = path.lstat()
            if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
                raise ValueError('Codex runtime directories must be private, owned directories (0700).')
        if not (base / 'codex/config.toml').is_file():
            raise ValueError('An isolated, host-reviewed Codex configuration is required.')
        env = {'PATH': '/usr/local/bin:/usr/bin:/bin', 'HOME': str(base / 'home'),
               'CODEX_HOME': str(base / 'codex'), 'LANG': 'C.UTF-8', 'TMPDIR': str(base / 'tmp')}
        # Logs are private; authenticated protocol messages are never printed.
        fd = os.open(base / 'stderr.log', os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)
        self.log = os.fdopen(fd, 'ab')
        try:
            self.process = subprocess.Popen([codex, 'app-server', '--listen', 'stdio://'],
                cwd=base / 'workspace', env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=self.log, text=True, start_new_session=True)
        except BaseException:
            self.log.close()
            raise
        self.reader = threading.Thread(target=self._reader, daemon=True)
        self.reader.start()
        try:
            self.request('initialize', {'clientInfo': {'name': 'vibe-director', 'version': '1'},
                                        'capabilities': {'experimentalApi': True}})
            self._send({'method': 'initialized'})
        except BaseException:
            self.close()
            raise

    def _enqueue(self, value):
        while not self.closed.is_set():
            try:
                self.inbox.put(value, timeout=.1)
                return
            except queue.Full:
                continue

    def _reader(self):
        try:
            while not self.closed.is_set():
                line = self.process.stdout.readline(self.FRAME_LIMIT + 1)
                if not line:
                    break
                if len(line.encode('utf-8')) > self.FRAME_LIMIT:
                    raise ValueError('Codex protocol frame exceeded its budget')
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise ValueError('Invalid Codex protocol frame')
                self._enqueue(value)
        except (ValueError, OSError):
            self._enqueue({'transport_error': True})
        finally:
            self._enqueue({'transport_closed': True})

    def _send(self, value):
        if self.closed.is_set():
            raise RuntimeError('Codex transport is closed')
        self.process.stdin.write(json.dumps(value) + '\n')
        self.process.stdin.flush()

    def receive(self, timeout: float):
        try:
            value = self.inbox.get(timeout=max(0, timeout))
        except queue.Empty:
            raise TimeoutError('Codex response deadline exceeded') from None
        if value.get('transport_error') or value.get('transport_closed'):
            raise RuntimeError('Codex transport closed or returned invalid data')
        if 'method' in value:
            # A Codex transport approval is never a Vibe approval. Deny every
            # server-initiated host request, even an unknown future variant.
            if 'id' in value:
                self._send({'id': value['id'], 'error': {'code': -32000,
                            'message': 'Vibe host denies agent escalation'}})
            self.event_bytes += len(json.dumps(value).encode('utf-8'))
            if self.event_bytes > self.EVENT_LIMIT:
                raise RuntimeError('Codex event budget exceeded')
            self.events.append(value)
            if self.on_event:
                self.on_event(value)
        return value

    def request(self, method: str, params: dict, timeout: float = 45):
        if method not in self.METHODS:
            raise ValueError('Host protocol method is not allowed')
        self.serial += 1
        ident = self.serial
        self._send({'id': ident, 'method': method, 'params': params})
        deadline = time.monotonic() + timeout
        while True:
            value = self.receive(deadline - time.monotonic())
            if value.get('id') == ident and 'method' not in value:
                if 'error' in value:
                    raise RuntimeError(f'Codex {method} failed; inspect private runtime diagnostics')
                return value['result']

    def turn(self, thread: str, text: str | None = None, recovery: str | None = None):
        self.events.clear()
        self.event_bytes = 0
        params = {'threadId': thread, 'input': [{'type': 'text', 'text': text}] if text else [], 'effort': 'low'}
        if recovery:
            params.update(turnTrigger='vibe_recovery', additionalContext={
                'recovery': {'kind': 'application', 'value': recovery}})
        try:
            result = self.request('turn/start', params)
            deadline = time.monotonic() + 150
            while True:
                event = self.receive(deadline - time.monotonic())
                if (event.get('method') == 'turn/completed'
                        and event['params'].get('threadId') == thread
                        and event['params']['turn']['id'] == result['turn']['id']):
                    if event['params']['turn']['status'] != 'completed':
                        raise RuntimeError('Codex turn did not complete')
                    return result, self.events[:]
        except BaseException:
            # Never leave an agent executing tools after its host stops waiting.
            self.close()
            raise

    def close(self):
        if self.closed.is_set():
            return
        self.closed.set()
        if self.process.poll() is None:
            try:
                os.killpg(self.process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(self.process.pid, signal.SIGKILL)
                self.process.wait(timeout=5)
        self.reader.join(timeout=1)
        self.process.stdin.close()
        self.process.stdout.close()
        self.log.close()
