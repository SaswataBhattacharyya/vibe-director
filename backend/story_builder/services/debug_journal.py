"""Opt-in, bounded local journal for manual UI investigation; never runs workloads."""
import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path


class DebugJournal:
    MAX_BYTES = 8 * 1024 * 1024
    FIELDS = {'kind', 'route', 'target', 'action', 'value', 'method', 'path',
              'status', 'message', 'outcome', 'job_id', 'state', 'client_time'}

    def __init__(self, root):
        self.directory = Path(root) / 'reports/debug'
        self.policy_path = self.directory / 'policy.json'
        self.lock = threading.RLock()

    def status(self):
        with self.lock:
            try:
                policy = json.loads(self.policy_path.read_text())
            except FileNotFoundError:
                policy = {'enabled': False, 'session_id': None}
            session = policy.get('session_id')
            if session is not None and not re_valid_session(session):
                raise ValueError('Invalid debug session.')
            log = self.directory / f'{session}.jsonl' if session else None
            return {**policy, 'log_path': str(log) if log else None,
                    'bytes': log.stat().st_size if log and log.exists() else 0,
                    'max_bytes': self.MAX_BYTES}

    def set_enabled(self, enabled):
        if type(enabled) is not bool:
            raise ValueError('Supply enabled as a boolean.')
        with self.lock:
            policy = self.status()
            if enabled and not policy['enabled']:
                policy['session_id'] = uuid.uuid4().hex
            policy['enabled'] = enabled
            self.directory.mkdir(parents=True, exist_ok=True)
            temporary = self.policy_path.with_suffix('.tmp')
            temporary.write_text(json.dumps({key: policy[key] for key in ('enabled', 'session_id')}))
            temporary.replace(self.policy_path)
            if enabled:
                self.record([{'kind': 'session', 'action': 'recording_enabled'}])
            return self.status()

    def record(self, events):
        if not isinstance(events, list) or len(events) > 50:
            raise ValueError('Supply at most 50 debug events.')
        clean = []
        for event in events:
            if not isinstance(event, dict) or not isinstance(event.get('kind'), str):
                raise ValueError('Each debug event needs a kind.')
            item = {key: str(value)[:1000] for key, value in event.items()
                    if key in self.FIELDS and isinstance(value, (str, int, float, bool))}
            item['recorded_at'] = datetime.now(timezone.utc).isoformat()
            clean.append(item)
        with self.lock:
            policy = self.status()
            if not policy['enabled']:
                return {'recorded': 0, 'enabled': False}
            text = ''.join(json.dumps(item, ensure_ascii=False) + '\n' for item in clean)
            if policy['bytes'] + len(text.encode()) > self.MAX_BYTES:
                raise ValueError('Debug log is full. Turn Debug off and on to start a new session.')
            with Path(policy['log_path']).open('a', encoding='utf-8') as stream:
                stream.write(text)
            return {'recorded': len(clean), 'enabled': True}

    def read_log(self):
        with self.lock:
            policy = self.status()
            if not policy['log_path'] or not Path(policy['log_path']).exists():
                return b''
            return Path(policy['log_path']).read_bytes()


def re_valid_session(value):
    return isinstance(value, str) and len(value) == 32 and all(c in '0123456789abcdef' for c in value)
