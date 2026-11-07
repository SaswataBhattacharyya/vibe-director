"""CPU-only Story handoff, Unicode revisions and durable lost-response recovery."""
import json
import unittest
import uuid
from pathlib import Path
from unittest.mock import Mock

from story_builder.isolated_server import create_app
from story_builder.services import projects
from story_builder.services.agent_conversation import AgentConversation
from story_builder.services.agent_story import StoryDirector
from story_builder.services.agent_tasks import AgentTasks
from story_builder.services.production_ledger import LedgerConflict
from story_builder.tests import test_story_selected_edit_api as selected_edit_tests


class AgentStoryTests(unittest.TestCase):
    call = selected_edit_tests.StorySelectedEditApiTests.call

    def setUp(self):
        selected_edit_tests.StorySelectedEditApiTests.setUp(self)
        self.addCleanup(self.cleanup)
        projects.activate(self.root, self.workspace, 'Story fixture', {})
        self.tasks = AgentTasks(self.root, self.ledger)
        self.provider = Mock(side_effect=self.reason)
        self.adapter = StoryDirector(self.story, self.provider)
        self.chat = AgentConversation(self.tasks, self.provider, story=self.adapter)
        self.app = create_app(data_root=self.root, reasoning_json_provider=self.provider,
            gpu_reader=lambda: self.fail('Story guidance must not query GPU'),
            worker_status_provider=lambda: self.fail('Story guidance must not query worker'))

    def cleanup(self):
        self.temp.cleanup()
        self.assertFalse(Path(self.temp.name).exists(), 'Test-owned database/media survived cleanup')

    def payload(self, text='Can we clarify this?'):
        target = selected_edit_tests.StorySelectedEditApiTests.request(self)
        return {'request_id': str(uuid.uuid4()), 'text': text, 'asset_ids': [], 'skill_refs': [],
            'surface': 'story', 'target': {key: value for key, value in target.items()
                if key not in {'instruction', 'idempotency_key'}} | {'version': 1, 'workspace_id': self.workspace}}

    @staticmethod
    def reason(**kwargs):
        if 'output_schema' in kwargs:
            message = json.loads(kwargs['prompt'].split('\n', 1)[1])['message']
            return {'reply': 'We can clarify the passage.', 'intent': 'story.propose' if message.startswith('Prepare') else 'discuss', 'quality': 2}
        return {'replacement': 'new phrase', 'explanation': 'Clearer.'}

    def test_http_discussion_proposal_replay_and_explicit_revision(self):
        path = f'/api/agent/projects/{self.workspace}/conversation'
        discussion = self.payload()
        status, result = self.call('POST', path, discussion)
        self.assertEqual(status, '200 OK', result)
        self.assertNotIn('story_target', result['messages'][-1])
        self.assertEqual(self.provider.call_count, 1)
        payload = self.payload('Prepare the clearer wording.')
        status, result = self.call('POST', path, payload)
        self.assertEqual(status, '200 OK', result)
        self.assertEqual(result['messages'][-1]['story_target'], payload['target'])
        calls = self.provider.call_count
        self.assertEqual(self.call('POST', path, payload)[1], result)
        self.assertEqual(self.call('GET', path)[1], result)
        self.assertEqual(self.provider.call_count, calls)
        self.assertIn('Before 😀', self.provider.call_args.kwargs['prompt'])
        self.assertIn('SOURCE GRAPH', self.provider.call_args.kwargs['prompt'])
        self.assertEqual(self.story.get_workspace(self.workspace)['current_revision_id'], self.revision)
        proposal = self.story.get_ai_edit_request(payload['request_id'])['proposal']
        status, revision = self.call('POST', f'/api/story/workspaces/{self.workspace}/edit-proposals/accept',
            {'proposal_id': proposal['proposal_id'], 'expected_current_revision_id': self.revision})
        self.assertEqual(status, '201 Created', revision)
        self.assertEqual(revision['source_text'], 'Before 😀. The new phrase. After Ω.')
        self.assertEqual(self.tasks.list(self.workspace)['tasks'], [])

    def test_invalid_stale_and_oversized_targets_never_call_provider(self):
        original = self.payload()['target']
        for changes in ({'version': True}, {'workspace_id': 'other'}, {'extra': True},
                        {'start_codepoint': True}, {'start_codepoint': -1}, {'end_codepoint': 1000},
                        {'expected_text': 'wrong'}, {'expected_text': 'x' * 12001}):
            with self.subTest(changes=changes), self.assertRaises((ValueError, LedgerConflict)):
                self.chat.send(self.workspace, {**self.payload(), 'target': {**original, **changes}})
        with self.assertRaises(ValueError):
            self.chat.send(self.workspace, self.payload('x' * 4001))
        self.story.write_revision(workspace_id=self.workspace, source_text='Changed', expected_current_revision_id=self.revision)
        with self.assertRaises(LedgerConflict):
            self.chat.send(self.workspace, {**self.payload(), 'target': original})
        self.provider.assert_not_called()

    def test_saved_proposal_recovers_after_reply_loss_without_resubmission(self):
        propose = self.adapter.propose
        def lose_reply(*args):
            propose(*args)
            raise RuntimeError('Reply lost after proposal saved')
        self.adapter.propose = Mock(side_effect=lose_reply)
        payload = self.payload('Prepare clearer wording.')
        with self.assertRaises(RuntimeError):
            self.chat.send(self.workspace, payload)
        history = self.chat.send(self.workspace, payload)
        self.assertEqual(history['messages'][-1]['status'], 'interrupted')
        self.assertEqual(history['messages'][-1]['story_target'], payload['target'])
        self.adapter.propose.assert_called_once()
        self.assertEqual(self.story.get_ai_edit_request(payload['request_id'])['proposal']['status'], 'pending')
        self.assertEqual(self.story.get_workspace(self.workspace)['current_revision_id'], self.revision)

    def test_story_intent_on_generic_surface_is_rejected(self):
        payload = self.payload('Prepare clearer wording.')
        payload.pop('target')
        payload['surface'] = 'director'
        with self.assertRaises(ValueError):
            self.chat.send(self.workspace, payload)
        self.assertEqual(self.provider.call_count, 1)
        with self.ledger._connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM story_ai_edit_requests').fetchone()[0], 0)
