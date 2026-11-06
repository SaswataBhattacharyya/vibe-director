"""Computer boundary checks. Provider execution is mocked; all storage is disposable."""
import io
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from story_builder.services import agent_access, agent_computer, agent_permissions, projects, video_repertoire
from story_builder.services.production_ledger import LedgerConflict
from story_builder.tests.test_agent_tasks import AgentTaskFixture


class AgentComputerTests(AgentTaskFixture):
    def setUp(self):
        super().setUp()
        self.owner = 'story-aaaaaaaaaaaa'
        with sqlite3.connect(projects.database_path(self.root, projects.DATABASES[0])) as db:
            db.execute('INSERT INTO story_workspaces(workspace_id,title,authoring_uuid) VALUES (?,?,?)',
                       (self.owner, 'Test computer film', self.owner))
        (self.root / 'library/projects').mkdir(parents=True, exist_ok=True)
        (self.root / 'library/projects/active.json').write_text(json.dumps({'workspace_id': self.owner}))
        self.folder = self.root / 'projects' / self.owner
        self.folder.mkdir(parents=True)
        patch.object(agent_computer.reasoning_provider, 'get_settings', return_value={
            'provider': 'codex', 'model': 'test', 'reasoning_effort': 'low'}).start()
        self.real_codex = shutil.which('codex')
        patch.object(agent_permissions.shutil, 'which', return_value='/usr/bin/codex').start()

    def proposal(self, mode='project'):
        return {'tool_id': 'computer.execute', 'asset_ids': [], 'settings': {
            'instruction': 'Write a shot list in agent-work/', 'access_mode': mode, 'skill_refs': []}}

    def test_exact_access_revision_and_lost_mapping(self):
        row = self.tasks.propose(self.owner, self.proposal())
        self.dispatch.assert_not_called()
        self.tasks.approve(self.owner, row['task_id'], self.approval(row))
        changed = self.tasks.revise(self.owner, row['task_id'], {**self.approval(row), 'proposal': self.proposal('full')})
        self.assertEqual(changed['status'], 'draft')
        with self.assertRaises(LedgerConflict):
            self.tasks.run(self.owner, row['task_id'], self.approval(row))
        with self.assertRaises(LedgerConflict):
            self.tasks.run(self.owner, row['task_id'], self.approval(changed))
        self.tasks.approve(self.owner, row['task_id'], self.approval(changed))
        with patch.object(self.tasks, '_map_job', side_effect=RuntimeError('lost acknowledgment')), self.assertRaises(RuntimeError):
            self.tasks.run(self.owner, row['task_id'], self.approval(changed))
        recovered = self.tasks.run(self.owner, row['task_id'], self.approval(changed))
        self.assertEqual(recovered['job_status'], 'queued')
        self.assertEqual(len(list((self.root / 'services/media/jobs/agent-computer').glob('*/job.json'))), 1)
        self.assertEqual(self.tasks.cancel(self.owner, row['task_id'])['status'], 'cancelled')

    def test_strict_scope_and_command_contract(self):
        with self.assertRaises(ValueError):
            self.tasks.propose(self.owner, self.proposal('anything'))
        row = self.tasks.propose(self.owner, self.proposal())
        settings = row['plan']['settings']
        command = agent_computer.validate(self.root, self.owner, settings)
        self.assertIn('default_permissions="vibe-project"', command)
        self.assertIn('shell_environment_policy.inherit="none"', command)
        self.assertNotIn('danger-full-access', command)
        self.assertIn('danger-full-access', agent_permissions.execution_args('full', self.folder))
        settings['workspace_path'] = str(self.root)
        with self.assertRaises(ValueError):
            agent_computer.validate(self.root, self.owner, settings)
        with self.assertRaises(ValueError):
            self.tasks.propose('tool-library', self.proposal())

    def http(self, path, payload=None, **headers):
        response = []
        raw = json.dumps(payload).encode() if payload is not None else b''
        environ = {'PATH_INFO': path, 'REQUEST_METHOD': 'POST' if payload is not None else 'GET',
            'CONTENT_LENGTH': str(len(raw)), 'wsgi.input': io.BytesIO(raw), 'HTTP_HOST': '127.0.0.1:8082', **headers}
        result = b''.join(self.app(environ, lambda status, _: response.append(status)))
        return response[0], json.loads(result)

    def test_local_browser_grant_and_cross_site_rejection(self):
        path = f'/api/agent/projects/{self.owner}/tasks'
        self.assertEqual(self.http(path, self.proposal())[0], '400 Bad Request')
        status, access = self.http('/api/agent/computer-access')
        self.assertEqual(status, '200 OK')
        token = {'HTTP_X_VIBE_COMPUTER_TOKEN': access['session_token']}
        for headers in ({'HTTP_ORIGIN': 'https://attacker.example'}, {'HTTP_HOST': 'attacker.example'},
                        {'HTTP_SEC_FETCH_SITE': 'cross-site'}):
            self.assertEqual(self.http(path, self.proposal(), **{**token, **headers})[0], '400 Bad Request')
        status, row = self.http(path, self.proposal(), **token)
        self.assertEqual(status, '200 OK')
        self.assertEqual(self.http(path + '/' + row['task_id'] + '/approve', self.approval(row))[0], '400 Bad Request')
        self.assertEqual(self.http(path + '/' + row['task_id'] + '/approve', self.approval(row), **token)[0], '200 OK')
        self.dispatch.assert_not_called()

    def test_worker_report_and_no_replay(self):
        row = self.tasks.propose(self.owner, self.proposal())
        self.tasks.approve(self.owner, row['task_id'], self.approval(row))
        started = self.tasks.run(self.owner, row['task_id'], self.approval(row))
        job_id = started['invocation']['job_id']
        def launch(command, **kwargs):
            Path(command[command.index('--output-last-message') + 1]).write_text('Prepared a shot list; review it.')
            return Mock(stdin=io.BytesIO(), poll=Mock(return_value=0), returncode=0)
        from story_builder.services import video_repertoire_worker as worker
        with patch.object(agent_computer.subprocess, 'Popen', side_effect=launch) as provider, \
                patch('sys.argv', ['worker', agent_computer.KIND, job_id]), patch.object(worker.signal, 'signal'), \
                patch.object(worker, 'gpu_workload_lock', side_effect=AssertionError('Computer adapter requested GPU')):
            self.assertEqual(worker.main(), 0)
            provider.assert_called_once()
        result = self.tasks.poll(self.owner, row['task_id'])
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['outputs'], [])
        self.assertIn('review', result['report'])
        request = video_repertoire.read_job(agent_computer.KIND, job_id)['request']
        with self.assertRaises(ValueError):
            agent_computer.run(self.root, job_id, request)
        self.assertEqual(self.original.read_bytes(), self.before)

    def test_cancellation_terminates_owned_provider_group(self):
        row = self.tasks.propose(self.owner, self.proposal())
        self.tasks.approve(self.owner, row['task_id'], self.approval(row))
        started = self.tasks.run(self.owner, row['task_id'], self.approval(row))
        job_id = started['invocation']['job_id']
        request = video_repertoire.read_job(agent_computer.KIND, job_id)['request']
        process = Mock(stdin=io.BytesIO(), pid=999999, poll=Mock(return_value=None))
        with patch.object(agent_computer.subprocess, 'Popen', return_value=process), \
                patch.object(agent_computer.time, 'sleep', side_effect=KeyboardInterrupt), \
                patch.object(agent_computer.os, 'killpg') as terminate:
            with self.assertRaises(KeyboardInterrupt):
                agent_computer.run(self.root, job_id, request)
            terminate.assert_called_once_with(process.pid, agent_computer.signal.SIGTERM)
            process.wait.assert_called_once_with(timeout=5)
        with self.assertRaises(ValueError):
            agent_computer.run(self.root, job_id, request)

    @unittest.skipUnless(os.environ.get('VIBE_TEST_CODEX_SANDBOX') == '1', 'Opt-in offline Linux sandbox acceptance')
    def test_real_project_sandbox_hides_sibling_and_blocks_network(self):
        binary = self.real_codex
        outside = self.root / 'outside.txt'
        outside.write_text('test-owned secret')
        (self.folder / 'escape').symlink_to(outside)
        probe = f"""import pathlib, socket
pathlib.Path('inside.txt').write_text('ok')
assert not pathlib.Path({str(outside)!r}).exists()
assert not pathlib.Path('escape').exists()
try:
    pathlib.Path({str(outside)!r}).write_text('changed')
    raise AssertionError('outside write allowed')
except OSError as exc:
    assert exc.errno in {{1, 2, 13, 30}}
try:
    connection = socket.socket()
    connection.settimeout(0.2)
    assert connection.connect_ex(('1.1.1.1',443)) != 0
except PermissionError:
    pass
"""
        command = ['codex', '--no-daemon', 'sandbox', '-P', 'vibe-project', '-C', str(self.folder),
            *agent_permissions.profile_args(binary), '--', sys.executable, '-c', probe]
        # Use system Python, covered by :minimal, rather than a private venv.
        command[command.index('--') + 1] = '/usr/bin/python3'
        completed = subprocess.run(command, capture_output=True, text=True, timeout=25)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual((self.folder / 'inside.txt').read_text(), 'ok')
        self.assertEqual(outside.read_text(), 'test-owned secret')
