"""CPU shared prompt chat: reviewed changes, scoped rules and durable recovery."""
import json
import unittest
import uuid
from pathlib import Path
from unittest.mock import Mock

from story_builder.isolated_server import create_app
from story_builder.services import projects
from story_builder.services.agent_conversation import AgentConversation
from story_builder.services.agent_prompts import PromptDirectorAdapter
from story_builder.services.agent_tasks import AgentTasks
from story_builder.tests import test_prompt_director, test_agent_tasks


class AgentPromptTests(unittest.TestCase):
    def setUp(self):
        test_prompt_director.PromptDirectorTests.setUp(self)
        self.addCleanup(self.cleanup)
        projects.activate(self.root, self.w, 'Prompt fixture', {})
        self.tasks = AgentTasks(self.root, self.ledger)
        self.provider = Mock(side_effect=self.reason)
        self.adapter = PromptDirectorAdapter(self.service, self.provider)
        self.chat = AgentConversation(self.tasks, self.provider, prompts=self.adapter)

    def cleanup(self):
        self.temp.cleanup()
        self.assertFalse(Path(self.temp.name).exists(), 'Test-owned database survived cleanup')

    def payload(self, text='Why this camera?'):
        return {'request_id': str(uuid.uuid4()), 'text': text, 'asset_ids': [], 'skill_refs': [],
                'surface': 'prompt', 'target': {'version': 1, 'workspace_id': self.w,
                    'screenplay_revision_id': self.r, 'prompts': {'shot:1.1': 'Mira holds a key.'}, 'workflows': {}}}

    @staticmethod
    def reason(**kwargs):
        if 'output_schema' in kwargs:
            text = json.loads(kwargs['prompt'].split('\n', 1)[1])['message']
            intent = 'prompt.propose' if text.startswith('Prepare') else 'prompt.learn' if text.startswith('Remember') else 'discuss'
            return {'reply': 'Review before Apply.', 'intent': intent, 'quality': 2}
        prompt = kwargs['prompt']
        if 'with changes array' in prompt:
            return {'replacement': json.dumps({'changes': [{'key': 'shot:1.1', 'before': 'Mira holds a key.', 'value': 'Mira holds a key. Slow push-in.'}]}), 'explanation': 'Camera proposal.'}
        if 'with lessons array' in prompt:
            return {'replacement': json.dumps({'lessons': [{'scope': 'video', 'rule': 'One concrete camera move.'}]}), 'explanation': 'Learning proposal.'}
        return {'replacement': 'Keep camera direction concise.', 'explanation': 'Discussion only'}

    def test_http_multi_turn_uuid_replay_and_explicit_rule_save(self):
        self.app = create_app(data_root=self.root, reasoning_json_provider=self.provider,
            gpu_reader=lambda: self.fail('Prompt discussion must not query GPU'),
            worker_status_provider=lambda: self.fail('Prompt discussion must not query worker'))
        path = f'/api/agent/projects/{self.w}/conversation'
        for text in ('Why this camera?', 'Prepare agreed camera changes.', 'Remember one camera move.'):
            payload = self.payload(text)
            status, value = test_agent_tasks.AgentTaskFixture.call(self, 'POST', path, payload)
            self.assertEqual(status, '200 OK', value)
            calls = self.provider.call_count
            self.assertEqual(test_agent_tasks.AgentTaskFixture.call(self, 'POST', path, payload)[1], value)
            self.assertEqual(self.provider.call_count, calls)
        saved = self.service.get(self.w, self.r)
        self.assertEqual(len(saved['items']), 3)
        self.assertEqual(saved['revision'], 0)
        self.assertEqual(saved['lessons'], [])
        self.assertIn('Slow push-in', saved['items'][1]['proposal']['changes'][0]['value'])
        self.service.save(self.w, self.r, {'expected_revision': 0, 'lessons': saved['items'][2]['proposal']['lessons'], 'assets': {}})
        self.assertIn('One concrete camera move.', self.service.export(self.w, self.r))
        self.assertEqual(self.tasks.list(self.w)['tasks'], [])

    def test_invalid_context_rejected_before_provider(self):
        target = self.payload()['target']
        for changes in ({'version': True}, {'workspace_id': 'other'}, {'extra': 1},
                        {'prompts': {'shot:99.1': 'Foreign shot'}}, {'workflows': {'shot:1.1': 'unknown'}},
                        {'prompts': {'shot:1.1': 'x' * 7000}}):
            with self.assertRaises(ValueError):
                self.chat.send(self.w, {**self.payload(), 'target': {**target, **changes}})
        with self.assertRaises(ValueError):
            self.chat.send(self.w, self.payload('x' * 4001))
        self.provider.assert_not_called()

    def test_saved_proposal_survives_lost_shared_reply_without_replay(self):
        respond = self.adapter.respond
        def lose_reply(*args, **kwargs):
            respond(*args, **kwargs)
            raise RuntimeError('Reply lost after prompt proposal saved')
        self.adapter.respond = Mock(side_effect=lose_reply)
        payload = self.payload('Prepare camera changes.')
        with self.assertRaises(RuntimeError):
            self.chat.send(self.w, payload)
        self.assertEqual(self.chat.send(self.w, payload)['messages'][-1]['status'], 'interrupted')
        self.adapter.respond.assert_called_once()
        proposal = self.service.get(self.w, self.r)['items'][-1]
        self.assertEqual(proposal['key'], payload['request_id'])
        self.assertEqual(len(proposal['proposal']['changes']), 1)
        self.assertEqual(self.service.get(self.w, self.r)['revision'], 0)
