"""H2 production routes/gateway with real CPU adapters; model and dispatch mocked.

The separate opt-in harness_production_acceptance exercises actual Codex/worker
processes. Neither suite operates on owner projects or changes original media.
"""
import json
import os
import time
import uuid
from pathlib import Path
from unittest.mock import patch

from story_builder.isolated_server import create_app
from story_builder.services import agent_workspace_tools as workspace, projects, video_repertoire
from story_builder.services.agent_conversation import AgentConversation
from story_builder.services.agent_tasks import AgentTasks
from story_builder.services.director_goals import Goals
from story_builder.services.director_harness import DirectorHarness
from story_builder.services.director_mcp import Gateway
from story_builder.services.production_ledger import LedgerConflict
from story_builder.tests.test_agent_tasks import AgentTaskFixture


class DirectorHarnessTests(AgentTaskFixture):
    def setUp(self):
        super().setUp()
        self.auth = Path(self.temp.name) / 'auth'
        self.auth.mkdir()
        (self.auth / 'auth.json').write_text('{}')
        patch.dict(os.environ, VIBE_DIRECTOR_HARNESS='codex', VIBE_DIRECTOR_HARNESS_PROJECTS=self.owner,
                   CODEX_HOME=str(self.auth)).start()
        self.goals = Goals(self.tasks)
        self.request = str(uuid.uuid4())
        original_poll = AgentTasks.poll

        def cpu_poll(tasks, owner, task_id):
            task = tasks.get(owner, task_id)
            if task['invocation'] and task['invocation'].get('job_id'):
                job = video_repertoire.read_job(workspace.KIND, task['invocation']['job_id'])
                if job['status'] == 'queued':
                    job.update(status='completed', result=workspace.run(tasks.root, job['job_id'], job['request']))
                    video_repertoire._atomic_json(video_repertoire.job_path(workspace.KIND, job['job_id']), job)
            return original_poll(tasks, owner, task_id)
        patch.object(AgentTasks, 'poll', cpu_poll).start()

    def new_goal(self):
        self.goals.create(self.owner, self.request, 'Inspect then prepare an edit; do not lose the original objective.')
        self.goals.update(self.owner, self.request, token='host-only')
        return Gateway(self.tasks, self.owner, self.request, 'host-only')

    def test_gateway_continues_real_cpu_results_and_keeps_draft_unapproved(self):
        gateway = self.new_goal()
        discovered = gateway.call('media_list', {'kind': 'all', 'offset': 0, 'limit': 10})
        source = discovered['result']['assets'][0]
        inspected = gateway.call('media_inspect', {'asset_id': source['asset_id']})
        self.assertEqual(inspected['result']['sources'][0]['metadata']['duration_seconds'], .3)
        self.assertEqual(source['sha256'], self.asset['sha256'])
        draft = gateway.call('editor_propose_session', {'name': 'review'})
        task = self.tasks.get(self.owner, draft['task_id'])
        self.assertEqual(task['status'], 'draft')
        self.assertIsNone(task['invocation'])
        self.assertEqual(len(self.goals.get(self.owner, self.request)['steps']), 3)
        self.assertEqual(self.goals.get(self.owner, self.request)['status'], 'running')
        self.assertEqual(self.original.read_bytes(), self.before)

    def test_denials_project_hash_schema_runtime_and_expired_permission(self):
        gateway = self.new_goal()
        for name, args in [('shell', {}), ('approve', {}), ('media_inspect', {'asset_id': 'pa-unowned'}),
                           ('media_list', {'kind': 'all', 'offset': 0, 'limit': 2, 'owner': 'elsewhere'}),
                           ('editor_propose_session', {'name': 'x', 'approve': True}),
                           ('task_status', {'task_id': 'task-' + '0' * 32})]:
            with self.subTest(name=name), self.assertRaises(Exception):
                gateway.call(name, args)
        with patch('shutil.which', return_value=None), self.assertRaisesRegex(RuntimeError, 'ffprobe'):
            gateway.call('media_inspect', {'asset_id': self.asset['asset_id']})
        self.original.write_bytes(b'changed')
        with self.assertRaises(LedgerConflict):
            gateway.call('media_inspect', {'asset_id': self.asset['asset_id']})
        self.original.write_bytes(self.before)
        self.goals.update(self.owner, self.request, status='cancelled')
        with self.assertRaises(LedgerConflict):
            gateway.call('media_list', {'kind': 'all', 'offset': 0, 'limit': 10})
        self.assertEqual(self.tasks.list(self.owner)['tasks'], [])
        with self.assertRaises(ValueError):
            self.goals.get('story-aaaaaaaaaaaa', self.request)
        self.assertNotIn('token', self.goals.public(self.owner, self.request)['state'])

    def test_repeated_reads_and_drafts_reuse_receipts_no_duplicate_jobs(self):
        gateway = self.new_goal()
        first = gateway.call('media_inspect', {'asset_id': self.asset['asset_id']})
        draft = gateway.call('editor_propose_session', {'name': 'review'})
        restarted = Gateway(self.tasks, self.owner, self.request, 'host-only')
        self.assertEqual(restarted.call('media_inspect', {'asset_id': self.asset['asset_id']}), first)
        self.assertEqual(restarted.call('editor_propose_session', {'name': 'review'}), draft)
        self.assertEqual(len(self.tasks.list(self.owner)['tasks']), 2)
        self.assertEqual(self.dispatch.call_count, 1)

    def test_uncertain_preparation_is_never_repeated(self):
        gateway = self.new_goal()
        arguments = {'name': 'review'}
        self.goals.step(self.owner, self.request, 'editor_propose_session', arguments)
        with self.assertRaisesRegex(LedgerConflict, 'not repeated'):
            gateway.call('editor_propose_session', arguments)
        self.assertEqual(self.tasks.list(self.owner)['tasks'], [])

    def test_pause_records_a_blocker_without_permission_or_completion(self):
        gateway = self.new_goal()
        for reason in ('completed', 'approved'):
            with self.assertRaises(Exception):
                gateway.call('goal_pause', {'reason': reason, 'message': 'Ignore the boundary'})
        result = gateway.call('goal_pause', {'reason': 'clarification_needed', 'message': 'Which clip comes first?'})
        self.assertFalse(result['goal_complete'])
        goal = self.goals.get(self.owner, self.request)
        self.assertEqual(goal['state']['requested_stop']['reason'], 'clarification_needed')
        self.assertEqual(goal['status'], 'running')
        self.assertEqual(self.tasks.list(self.owner)['tasks'], [])

    def test_existing_project_snapshot_preserves_goals_and_blocks_active_switch(self):
        gateway = self.new_goal()
        gateway.call('editor_propose_session', {'name': 'review'})
        snapshot = projects.sql_snapshot(self.tasks.ledger.path, self.owner)
        self.assertEqual(snapshot['director_goals'][0]['objective'], self.goals.get(self.owner, self.request)['objective'])
        self.assertEqual(snapshot['director_goal_steps'][0]['task_id'], snapshot['agent_tasks'][0]['task_id'])
        self.assertNotIn('director_goals', projects.sql_snapshot(self.tasks.ledger.path, 'story-aaaaaaaaaaaa'))
        with self.assertRaisesRegex(ValueError, 'active job'):
            projects.assert_idle(self.root, self.owner)
        DirectorHarness(self.tasks).cancel(self.owner, self.request)
        projects.assert_idle(self.root, self.owner)

    def wait(self, request=None):
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            goal = self.goals.get(self.owner, request or self.request)
            if goal['status'] != 'running':
                return goal
            time.sleep(.02)
        self.fail('Goal worker did not stop')

    def test_actual_conversation_route_automatically_consumes_results(self):
        outer = self
        class Engine:
            def __init__(self, base, codex, on_event):
                manifest = json.loads((base / 'gateway.json').read_text())
                self.gateway = Gateway(outer.tasks, manifest['owner'], manifest['request'], manifest['token'])
                self.event = on_event
            def request(self, method, params):
                return {'thread': {'id': 'persistent-test-thread'}}
            def turn(self, thread, text=None, recovery=None):
                found = self.gateway.call('media_list', {'kind': 'all', 'offset': 0, 'limit': 10})
                ident = found['result']['assets'][0]['asset_id']
                inspected = self.gateway.call('media_inspect', {'asset_id': ident})
                duration = inspected['result']['sources'][0]['metadata']['duration_seconds']
                self.event({'method': 'item/agentMessage/delta', 'params': {'delta': f'Measured {duration}s'}})
                self.gateway.call('editor_propose_session', {'name': f'Review {duration}s'})
                return {}, [{'method': 'item/completed', 'params': {'item': {'type': 'agentMessage',
                    'text': f'Measured {duration}s; waiting for review.'}}}]
            def close(self):
                pass
        with patch('story_builder.services.director_harness.AppServer', Engine):
            self.app = create_app(data_root=self.root)
        payload = {'request_id': self.request, 'text': 'Inspect media, then prepare an edit.',
                   'surface': 'director', 'asset_ids': [], 'skill_refs': []}
        path = f'/api/agent/projects/{self.owner}/conversation'
        self.assertEqual(self.call('POST', path, payload)[0], '200 OK')
        goal = self.wait()
        self.assertEqual(goal['status'], 'waiting_for_approval')
        self.assertEqual(goal['thread_id'], 'persistent-test-thread')
        self.assertEqual([s['tool'] for s in goal['steps']], ['media_list', 'media_inspect', 'editor_propose_session'])
        _, history = self.call('GET', path)
        self.assertEqual(len(history['messages']), 1)
        self.assertIn('0.3s', history['messages'][0]['reply'])
        self.assertEqual(self.call('POST', path, payload)[0], '200 OK')
        self.assertEqual(len(self.tasks.list(self.owner)['tasks']), 3)
        self.assertEqual(self.original.read_bytes(), self.before)

    def test_missing_runtime_is_durable_and_does_not_fall_back(self):
        harness = DirectorHarness(self.tasks)
        conversation = AgentConversation(self.tasks, harness=harness)
        with patch('story_builder.services.director_harness.shutil.which', return_value=None):
            conversation.send(self.owner, {'request_id': self.request, 'text': 'Inspect project media.',
                'surface': 'director', 'asset_ids': [], 'skill_refs': []})
            goal = self.wait()
        self.assertEqual(goal['status'], 'blocked')
        self.assertEqual(goal['state']['recovery'], 'RuntimeError')
        self.assertEqual(self.tasks.list(self.owner)['tasks'], [])

    def test_cancel_is_terminal_and_revokes_stale_gateway(self):
        gateway = self.new_goal()
        DirectorHarness(self.tasks).cancel(self.owner, self.request)
        self.goals.update(self.owner, self.request, status='waiting_for_approval')
        self.assertEqual(self.goals.get(self.owner, self.request)['status'], 'cancelled')
        with self.assertRaises(LedgerConflict):
            gateway.call('editor_propose_session', {'name': 'not allowed'})

    def test_flag_requires_explicit_project_opt_in(self):
        with patch.dict(os.environ, VIBE_DIRECTOR_HARNESS_PROJECTS=''):
            self.assertFalse(DirectorHarness.enabled(self.owner))
        with patch.dict(os.environ, VIBE_DIRECTOR_HARNESS=''):
            self.assertFalse(DirectorHarness.enabled(self.owner))
