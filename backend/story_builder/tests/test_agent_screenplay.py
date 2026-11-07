"""CPU-only shared screenplay discussion, selective Apply and lost-response recovery."""
import json
import unittest
import uuid
from pathlib import Path
from unittest.mock import Mock

from story_builder.isolated_server import create_app
from story_builder.services.agent_conversation import AgentConversation
from story_builder.services.agent_screenplay import ScreenplayDirector
from story_builder.services.agent_tasks import AgentTasks
from story_builder.services.production_ledger import LedgerConflict
from story_builder.services import projects
from story_builder.tests import test_storyboard, test_agent_tasks


class AgentScreenplayTests(unittest.TestCase):
    def setUp(self):
        test_storyboard.StoryboardTests.setUp(self)
        self.addCleanup(self.cleanup)
        self.tasks = AgentTasks(self.root, self.ledger)
        projects.activate(self.root, self.w, 'Screenplay fixture', {})
        self.screenplay = self.board.screenplay(self.w, self.r)
        self.provider = Mock(side_effect=self.reason)
        self.adapter = ScreenplayDirector(self.board, lambda prompt: self.provider(prompt=prompt))
        self.chat = AgentConversation(self.tasks, self.provider, screenplay=self.adapter)

    def cleanup(self):
        self.temp.cleanup()
        self.assertFalse(Path(self.temp.name).exists(), 'Test-owned database/media survived cleanup')

    def payload(self, text='Can Mira speak?'):
        return {'request_id': str(uuid.uuid4()), 'text': text, 'asset_ids': [], 'skill_refs': [],
                'surface': 'screenplay', 'target': {'version': 1, 'workspace_id': self.w,
                    'screenplay_revision_id': self.r}}

    @staticmethod
    def reason(**kwargs):
        if 'output_schema' in kwargs:
            message = json.loads(kwargs['prompt'].split('\n', 1)[1])['message']
            return {'reply': 'Review changes before Apply.', 'intent': 'screenplay.propose' if message.startswith('Prepare') else 'discuss', 'quality': 2}
        if kwargs['prompt'].startswith('Propose targeted'):
            return {'replacement': json.dumps({'changes': [
                {'scene_number': 1, 'shot_number': 1, 'field': 'planned_duration_seconds', 'value': 3},
                {'scene_number': 1, 'shot_number': 1, 'field': 'dialogue', 'value': 'MIRA: I found it.'}]}),
                'explanation': 'Timing and dialogue proposals.'}
        return {'replacement': 'Let Mira speak; keep narration for context.', 'explanation': 'Discussion only'}

    def test_http_discussion_proposal_selective_apply_and_uuid_replay(self):
        self.app = create_app(data_root=self.root, reasoning_json_provider=self.provider,
            gpu_reader=lambda: self.fail('Screenplay guidance must not query GPU'),
            worker_status_provider=lambda: self.fail('Screenplay guidance must not query worker'))
        path = f'/api/agent/projects/{self.w}/conversation'
        call = lambda method, payload=None: test_agent_tasks.AgentTaskFixture.call(self, method, path, payload)
        for message in ('Can Mira speak?', 'Keep narration too.', 'Prepare our agreed changes.'):
            payload = self.payload(message)
            status, result = call('POST', payload)
            self.assertEqual(status, '200 OK', result)
            calls = self.provider.call_count
            self.assertEqual(call('POST', payload)[1], result)
            self.assertEqual(self.provider.call_count, calls)
        history = self.board.conversations(self.w, self.r)
        self.assertEqual(len(history), 3)
        self.assertEqual(call('GET')[1], result)
        self.assertEqual(self.board.screenplay(self.w, self.r), self.screenplay)
        saved = self.board.apply(self.w, self.r, {'request_key': payload['request_id'],
            'selected': [0], 'idempotency_key': str(uuid.uuid4())})
        shot = saved['screenplay']['scenes'][0]['shots'][0]
        self.assertEqual(shot['planned_duration_seconds'], 3)
        self.assertEqual(shot['dialogue'], 'MIRA: Here it is.')
        self.assertEqual(shot['evidence'], self.screenplay['screenplay']['scenes'][0]['shots'][0]['evidence'])
        with self.assertRaises(LedgerConflict):
            self.board.apply(self.w, self.r, {'request_key': payload['request_id'],
                'selected': [1], 'idempotency_key': str(uuid.uuid4())})
        self.assertEqual(self.tasks.list(self.w)['tasks'], [])

    def test_invalid_target_and_oversized_message_never_call_provider(self):
        for target in ({**self.payload()['target'], 'version': True},
                       {**self.payload()['target'], 'workspace_id': 'other'},
                       {**self.payload()['target'], 'extra': True}):
            with self.assertRaises(ValueError):
                self.chat.send(self.w, {**self.payload(), 'target': target})
        with self.assertRaises(ValueError):
            self.chat.send(self.w, self.payload('x' * 4001))
        self.provider.assert_not_called()

    def test_saved_proposal_remains_recoverable_when_shared_reply_is_lost(self):
        respond = self.adapter.respond
        def lose_reply(*args, **kwargs):
            respond(*args, **kwargs)
            raise RuntimeError('Reply lost after proposal saved')
        self.adapter.respond = Mock(side_effect=lose_reply)
        payload = self.payload('Prepare our agreed changes.')
        with self.assertRaises(RuntimeError):
            self.chat.send(self.w, payload)
        self.assertEqual(self.chat.send(self.w, payload)['messages'][-1]['status'], 'interrupted')
        self.adapter.respond.assert_called_once()
        proposal = self.board.conversations(self.w, self.r)[-1]
        self.assertEqual(proposal['key'], payload['request_id'])
        self.assertEqual(len(proposal['proposal']['changes']), 2)
        self.assertEqual(self.board.screenplay(self.w, self.r), self.screenplay)
