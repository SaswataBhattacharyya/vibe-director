"""Disposable shared studio guidance: no job submission or implicit Apply."""
import uuid
from unittest.mock import Mock
from story_builder.isolated_server import create_app
from story_builder.services.agent_conversation import AgentConversation
from story_builder.services import studio_guidance
from story_builder.tests.test_agent_tasks import AgentTaskFixture


class AgentStudioTests(AgentTaskFixture):
    def payload(self, backend='trellis'):
        return {'request_id': str(uuid.uuid4()), 'text': 'Set seed to 12.', 'asset_ids': [], 'skill_refs': [],
                'surface': 'studio', 'target': {'version': 1, 'workspace_id': self.owner, 'name': 'trellis',
                    'context': {'settings': {'backend': backend, 'input_mode': 'single', 'settings': {}}}, 'history': []}}

    def test_http_guidance_replays_and_never_dispatches(self):
        provider = Mock(side_effect=lambda **kw: {'reply': 'Review.', 'intent': 'studio.suggest', 'quality': 2}
            if 'intent' in kw['output_schema']['properties'] else {'reply': 'Seed suggestion.', 'settings': {'seed': 12}})
        self.app = create_app(data_root=self.root, reasoning_json_provider=provider)
        payload = self.payload('pixal')
        path = f'/api/agent/projects/{self.owner}/conversation'
        status, result = self.call('POST', path, payload)
        self.assertEqual(status, '200 OK', result)
        self.assertEqual(result['messages'][-1]['proposal']['settings'], {'seed': 12})
        self.assertEqual(self.call('POST', path, payload)[1], result)
        self.assertEqual(provider.call_count, 2)
        keys = provider.call_args.kwargs['output_schema']['properties']['settings']['properties']
        self.assertEqual(set(keys), {'seed', 'fov', 'faces'})
        self.assertEqual(self.tasks.list(self.owner)['tasks'], [])
        self.dispatch.assert_not_called()
        self.assertEqual(self.original.read_bytes(), self.before)

    def test_validation_rejects_wrong_owner_and_unsupported_or_nonfinite_settings(self):
        reason = Mock()
        chat = AgentConversation(self.tasks, reason)
        for change in ({'workspace_id': 'other'}, {'version': True}, {'name': 'shell'}, {'extra': 1}):
            payload = self.payload()
            with self.assertRaises(ValueError):
                chat.send(self.owner, {**payload, 'target': {**payload['target'], **change}})
        reason.assert_not_called()
        for settings in ({'run': 1}, {'seed': float('nan')}, {'seed': True}):
            with self.assertRaises(ValueError):
                studio_guidance.suggest('Set seed.', {'backend': 'pixal'}, [], Mock(return_value={'reply': 'Review.', 'settings': settings}))
        result = studio_guidance.suggest('Discuss repair.', {'settings': {'activity': 'simple'}}, [], Mock(return_value={'reply': 'Discuss.', 'settings': {}}))
        self.assertEqual(result['settings'], {})

    def test_interrupted_request_is_durable_without_automatic_replay(self):
        provider = Mock(side_effect=[{'reply': 'Review.', 'intent': 'studio.suggest', 'quality': 1}, RuntimeError('Lost provider reply')])
        chat = AgentConversation(self.tasks, provider)
        payload = self.payload()
        with self.assertRaises(RuntimeError):
            chat.send(self.owner, payload)
        self.assertEqual(chat.send(self.owner, payload)['messages'][-1]['status'], 'interrupted')
        self.assertEqual(provider.call_count, 2)
