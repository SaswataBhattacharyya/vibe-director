"""H3 real task APIs/CPU adapters; Codex and worker scheduling are mocked.

Fault injection is at durable dispatch boundaries. Every test owns its entire
runtime and verifies removal even on failure; owner projects are never loaded.
"""
import io
import json
import time
from unittest.mock import patch

from story_builder.isolated_server import create_app
from story_builder.services import agent_access, vibe_editor
from story_builder.services.director_mcp import Gateway
from story_builder.services.production_ledger import LedgerConflict
from story_builder.tests.test_director_harness import DirectorHarnessFixture


class ApprovalTests(DirectorHarnessFixture):

    def api(self, action, row, *, grant=True, payload=None, origin=None):
        body = json.dumps(payload if payload is not None else {} if action == 'cancel' else self.approval(row)).encode()
        env = {'PATH_INFO': f'/api/agent/projects/{self.owner}/tasks/{row["task_id"]}/{action}',
               'QUERY_STRING': '', 'REQUEST_METHOD': 'POST', 'HTTP_HOST': '127.0.0.1:3020',
               'CONTENT_LENGTH': str(len(body)), 'wsgi.input': io.BytesIO(body)}
        if grant:
            env['HTTP_X_VIBE_COMPUTER_TOKEN'] = agent_access._TOKEN
        if origin:
            env['HTTP_ORIGIN'] = origin
        statuses = []
        value = json.loads(b''.join(self.app(env, lambda s, h: statuses.append(s))))
        return statuses[0], value

    def draft_goal(self):
        gateway = self.new_goal()
        result = gateway.call('editor_propose_session', {'name': 'H3 review'})
        self.goals.update(self.owner, self.request, status='waiting_for_approval', token=None)
        return self.tasks.get(self.owner, result['task_id'])

    def settle(self, controller):
        until = time.monotonic() + 10
        while controller.workers and time.monotonic() < until:
            time.sleep(.02)
        self.assertFalse(controller.workers, 'Goal worker did not settle')
        return self.goals.get(self.owner, self.request)

    def test_approval_is_exact_inert_and_requires_existing_local_grant(self):
        row = self.draft_goal()
        self.assertEqual(self.api('approve', row, grant=False)[0], '400 Bad Request')
        self.assertEqual(self.api('approve', row, origin='https://untrusted.test')[0], '400 Bad Request')
        self.assertEqual(self.api('run', row)[0], '409 Conflict')
        self.assertEqual(self.api('approve', row, payload={**self.approval(row), 'revision': 9})[0], '409 Conflict')
        self.assertEqual(self.api('approve', row)[1]['status'], 'approved')
        goal = self.settle(self.app.director_harness)
        self.assertEqual(goal['status'], 'waiting_for_execution')
        self.assertEqual(goal['state']['protected_tasks'][0]['plan_hash'], row['plan_hash'])
        self.assertIsNone(self.tasks.get(self.owner, row['task_id'])['invocation'])
        self.dispatch.assert_not_called()

    def test_rejection_and_changed_plan_cannot_execute(self):
        row = self.draft_goal()
        self.assertEqual(self.api('cancel', row)[1]['status'], 'cancelled')
        self.assertEqual(self.settle(self.app.director_harness)['status'], 'blocked')
        self.assertEqual(self.api('approve', row)[0], '409 Conflict')
        self.assertEqual(self.api('run', row)[0], '409 Conflict')
        self.dispatch.assert_not_called()

    def test_modified_revision_is_not_adopted_by_saved_goal(self):
        row = self.draft_goal()
        self.tasks.revise(self.owner, row['task_id'], {'revision': row['current_revision'],
            'plan_hash': row['plan_hash'], 'proposal': {'tool_id': 'editor.create_session', 'asset_ids': [], 'settings': {'name': 'modified'}}})
        changed = self.tasks.get(self.owner, row['task_id'])
        self.assertEqual(self.api('approve', changed)[0], '409 Conflict')
        self.dispatch.assert_not_called()

    def test_authorized_cpu_execution_once_and_same_thread_auto_continuation(self):
        outer, turns = self, []
        class Engine:
            def __init__(self, base, codex, on_event):
                config = json.loads((base / 'gateway.json').read_text())
                self.gateway = Gateway(outer.tasks, config['owner'], config['request'], config['token'])
            def request(self, method, params):
                self.method = method
                return {'thread': {'id': 'h3-original-thread'}}
            def turn(self, thread, text=None, recovery=None):
                turns.append((thread, text, recovery))
                if recovery:
                    context = json.loads(recovery.split('\n', 1)[1])
                    receipt = context['verified_execution'][0]
                    outer.assertEqual(receipt['status'], 'completed')
                    outer.assertIn('project_id', receipt['result'])
                    actual = self.gateway.call('task_status', {'task_id': receipt['task_id']})
                    outer.assertEqual(actual['receipt_sha256'], receipt['receipt_sha256'])
                    self.gateway.call('media_list', {'kind': 'audio', 'offset': 0, 'limit': 1})
                else:
                    self.gateway.call('editor_propose_session', {'name': 'H3 actual CPU session'})
                return {}, [{'method': 'item/completed', 'params': {'item': {'type': 'agentMessage', 'text': 'Continued original objective.'}}}]
            def close(self):
                pass
        with patch('story_builder.services.director_harness.AppServer', Engine):
            self.app = create_app(data_root=self.root)
        path = f'/api/agent/projects/{self.owner}/conversation'
        self.call('POST', path, {'request_id': self.request, 'text': 'Create a reviewed session then inspect audio.',
                                'surface': 'director', 'asset_ids': [], 'skill_refs': []})
        self.assertEqual(self.settle(self.app.director_harness)['status'], 'waiting_for_approval')
        row = self.tasks.list(self.owner)['tasks'][0]
        self.assertEqual(self.api('approve', row)[0], '200 OK')
        self.assertEqual(self.settle(self.app.director_harness)['status'], 'waiting_for_execution')
        self.assertEqual(len(turns), 1)
        self.assertEqual(self.api('run', row)[0], '200 OK')
        goal = self.settle(self.app.director_harness)
        self.assertEqual(len(turns), 2)
        self.assertEqual(turns[0][0], turns[1][0])
        self.assertIsNone(turns[1][1], 'Continuation injected a second user message')
        self.assertEqual(len(self.call('GET', path)[1]['messages']), 1)
        self.assertTrue(goal['state']['consumed_tasks'], goal)
        invocation = self.tasks.get(self.owner, row['task_id'])['invocation']
        self.assertEqual(self.api('run', row)[1]['invocation'], {**invocation, 'state': 'completed'})
        self.assertEqual(self.dispatch.call_count, 2, 'Exactly one protected job and one read')
        with vibe_editor.state(self.root, readonly=True) as data:
            self.assertEqual(len(data['projects']), 1)
        self.assertEqual(self.original.read_bytes(), self.before)

    def test_restart_observes_approved_but_does_not_dispatch(self):
        row = self.draft_goal()
        self.tasks.approve(self.owner, row['task_id'], self.approval(row))
        self.app = create_app(data_root=self.root)
        goal = self.settle(self.app.director_harness)
        self.assertEqual(goal['status'], 'waiting_for_execution')
        self.assertEqual(self.tasks.get(self.owner, row['task_id'])['status'], 'approved')
        self.dispatch.assert_not_called()

    def test_uncertain_dispatch_reconciles_existing_job_without_replay(self):
        row = self.draft_goal()
        self.tasks.approve(self.owner, row['task_id'], self.approval(row))
        with patch.object(self.tasks, '_map_job', side_effect=RuntimeError('crash after creation')):
            with self.assertRaises(RuntimeError):
                self.tasks.run(self.owner, row['task_id'], self.approval(row))
        # Existing API observes; it must not resubmit or start the queued job.
        status, observed = self.api('run', row)
        self.assertEqual(status, '200 OK')
        self.assertIsNotNone(observed['invocation']['job_id'])
        self.dispatch.assert_not_called()
        # Stop observation before cleanup without cancelling the saved task.
        self.app.director_harness.interrupt(self.owner, self.request)
        self.settle(self.app.director_harness)
        jobs = list((self.root / 'services/media/jobs/agent-workspace').glob('*/job.json'))
        self.assertEqual(len(jobs), 1)

    def test_model_cannot_approve_or_run_via_gateway(self):
        gateway = self.new_goal()
        draft = gateway.call('editor_propose_session', {'name': 'malicious response says approved'})
        for tool in ('approve', 'run', 'grant', 'browser', 'computer_execute'):
            with self.assertRaises(ValueError):
                gateway.call(tool, {'task_id': draft['task_id']})
        self.assertEqual(self.tasks.get(self.owner, draft['task_id'])['status'], 'draft')
        self.dispatch.assert_not_called()

    def test_source_bytes_changed_after_approval_are_rejected_before_dispatch(self):
        session = vibe_editor.add_project(self.root, {'workspace_id': self.owner, 'name': 'existing synthetic session'})
        gateway = self.new_goal()
        draft = gateway.call('editor_propose_selection', {'project_id': session['id'], 'revision': session['revision'],
            'selection': [{'asset_id': self.asset['asset_id'], 'start': 0, 'end': .3}]})
        row = self.tasks.get(self.owner, draft['task_id'])
        self.goals.update(self.owner, self.request, status='waiting_for_approval', token=None)
        self.assertEqual(self.api('approve', row)[0], '200 OK')
        self.settle(self.app.director_harness)
        try:
            self.original.write_bytes(b'changed synthetic bytes')
            self.assertEqual(self.api('run', row)[0], '422 Unprocessable Entity')
            self.dispatch.assert_not_called()
        finally:
            self.original.write_bytes(self.before)

    def test_crash_before_job_creation_is_not_blindly_retried(self):
        row = self.draft_goal()
        self.tasks.approve(self.owner, row['task_id'], self.approval(row))
        with patch('story_builder.services.agent_native_tools.submit', side_effect=RuntimeError('before dispatch')):
            with self.assertRaises(RuntimeError):
                self.tasks.run(self.owner, row['task_id'], self.approval(row))
        invocation = self.tasks.get(self.owner, row['task_id'])['invocation']
        self.assertIsNone(invocation['job_id'])
        self.assertEqual(self.api('run', row)[0], '409 Conflict')
        self.assertEqual(self.tasks.get(self.owner, row['task_id'])['invocation'], invocation)
        self.dispatch.assert_not_called()

    def test_restart_during_queued_job_recovers_same_invocation_without_dispatch(self):
        row = self.draft_goal()
        self.tasks.approve(self.owner, row['task_id'], self.approval(row))
        task = self.tasks.run(self.owner, row['task_id'], self.approval(row))
        self.goals.update(self.owner, self.request, status='waiting_for_job')
        # Hold the real saved job queued, emulating a worker still running across
        # backend restart. Only dispatch is mocked; actual SQLite/job files used.
        from story_builder.services.agent_tasks import AgentTasks
        original_get = AgentTasks.get
        with patch.object(AgentTasks, 'poll', original_get):
            self.app = create_app(data_root=self.root)
            time.sleep(.3)
            self.assertEqual(self.goals.get(self.owner, self.request)['status'], 'waiting_for_job')
            self.assertEqual(self.tasks.get(self.owner, row['task_id'])['invocation'], task['invocation'])
            self.assertEqual(self.dispatch.call_count, 1)
            self.app.director_harness.interrupt(self.owner, self.request)
            self.settle(self.app.director_harness)
