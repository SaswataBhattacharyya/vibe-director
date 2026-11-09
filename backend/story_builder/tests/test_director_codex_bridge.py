"""Transport tests with a disposable protocol peer; not live MCP acceptance."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from story_builder.services.director_codex_bridge import AppServer


PEER = r'''#!/usr/bin/python3
import json,os,sys
from pathlib import Path
base=Path.cwd().parent
(base/'environment.json').write_text(json.dumps(sorted(os.environ)))
mode=(base/'mode').read_text()
def emit(value):
    print(json.dumps(value),flush=True)
def finish():
    emit({'method':'item/agentMessage/delta','params':{'delta':'Inspected source'}})
    emit({'method':'turn/completed','params':{'threadId':'thread-owned',
        'turn':{'id':'turn-owned','status':'failed' if mode=='failed' else 'completed'}}})
for line in sys.stdin:
    value=json.loads(line)
    if 'method' not in value:
        (base/'host-response.json').write_text(json.dumps(value))
        finish()
        continue
    method=value['method']
    if method=='initialized': continue
    if method=='turn/start':
        (base/'turn.json').write_text(json.dumps(value['params']))
        emit({'id':value['id'],'result':{'turn':{'id':'turn-owned'}}})
        if mode=='close': sys.exit(0)
        if mode=='invalid': print('not JSON',flush=True);continue
        if mode=='oversized': print('x'*1048577,flush=True);continue
        if mode=='approval':
            emit({'id':'host-escalation','method':'item/commandExecution/requestApproval',
                  'params':{'command':'forbidden'}})
        else: finish()
    elif method=='thread/start':
        emit({'id':value['id'],'result':{'thread':{'id':'thread-owned'}}})
    else: emit({'id':value['id'],'result':{}})
'''


class CodexBridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='vibe-h2-transport-')
        self.base = Path(self.temp.name)
        self.addCleanup(self.cleanup)
        for name in ('workspace', 'home', 'codex', 'tmp'):
            (self.base / name).mkdir(mode=0o700)
        (self.base / 'codex/config.toml').write_text('# protocol peer only\n')
        self.peer = self.base / 'peer'
        self.peer.write_text(PEER)
        self.peer.chmod(0o700)
        self.server = None

    def cleanup(self):
        if self.server:
            self.server.close()
            self.assertIsNotNone(self.server.process.poll())
            self.assertFalse(self.server.reader.is_alive())
        self.temp.cleanup()
        self.assertFalse(self.base.exists())

    def start(self, mode='normal', **kwargs):
        (self.base / 'mode').write_text(mode)
        self.server = AppServer(self.base, str(self.peer), **kwargs)
        return self.server

    def test_streams_events_and_passes_only_allowlisted_environment(self):
        events = []
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'synthetic-secret', 'VIBE_PARENT_SECRET': 'sentinel'}):
            server = self.start(on_event=events.append)
        thread = server.request('thread/start', {})['thread']['id']
        _, received = server.turn(thread, 'Inspect both sources')
        self.assertEqual(received, events)
        self.assertEqual([e['method'] for e in received], ['item/agentMessage/delta', 'turn/completed'])
        keys = json.loads((self.base / 'environment.json').read_text())
        self.assertNotIn('OPENAI_API_KEY', keys)
        self.assertNotIn('VIBE_PARENT_SECRET', keys)
        self.assertTrue(set(keys) <= {'PATH', 'HOME', 'CODEX_HOME', 'LANG', 'TMPDIR', 'LC_CTYPE'})

    def test_denies_server_escalation_without_an_approval_callback(self):
        server = self.start('approval')
        server.turn('thread-owned', 'Read only')
        reply = json.loads((self.base / 'host-response.json').read_text())
        self.assertEqual(reply['id'], 'host-escalation')
        self.assertEqual(reply['error']['code'], -32000)
        self.assertNotIn('result', reply)

    def test_recovery_uses_internal_context_without_a_user_message(self):
        server = self.start()
        server.turn('thread-owned', recovery='Resume existing objective from persisted receipt')
        params = json.loads((self.base / 'turn.json').read_text())
        self.assertEqual(params['input'], [])
        self.assertEqual(params['additionalContext']['recovery']['kind'], 'application')

    def test_arbitrary_host_execution_methods_are_rejected(self):
        server = self.start()
        for method in ('thread/shellCommand', 'command/exec', 'config/write', 'approve', 'fetch'):
            with self.subTest(method=method), self.assertRaises(ValueError):
                server.request(method, {})

    def test_transport_failure_never_reports_completion_and_stops_process(self):
        for mode in ('close', 'invalid', 'oversized', 'failed'):
            with self.subTest(mode=mode):
                server = self.start(mode)
                with self.assertRaises(RuntimeError):
                    server.turn('thread-owned', 'Read')
                self.assertTrue(server.closed.is_set())
                self.assertIsNotNone(server.process.poll())

    def test_deadline_stops_agent_instead_of_leaving_tools_running(self):
        server = self.start()
        with patch.object(server, 'receive', side_effect=TimeoutError('synthetic deadline')):
            with self.assertRaises(TimeoutError):
                server.turn('thread-owned', 'Read')
        self.assertIsNotNone(server.process.poll())

    def test_event_budget_stops_agent_without_retaining_unbounded_output(self):
        server = self.start()
        server.EVENT_LIMIT = 1
        with self.assertRaisesRegex(RuntimeError, 'event budget'):
            server.turn('thread-owned', 'Read')
        self.assertTrue(server.closed.is_set())
        self.assertEqual(server.events, [])

    def test_rejects_nonprivate_runtime_without_changing_permissions(self):
        (self.base / 'home').chmod(0o750)
        with self.assertRaises(ValueError):
            AppServer(self.base, str(self.peer))
        self.assertEqual((self.base / 'home').stat().st_mode & 0o777, 0o750)


if __name__ == '__main__':
    unittest.main()
