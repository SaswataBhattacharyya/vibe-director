"""Shared image proposals use existing preparation, with disposable project records."""
import uuid
from unittest.mock import Mock

from story_builder.isolated_server import create_app
from story_builder.services.agent_conversation import AgentConversation
from story_builder.services.production_ledger import LedgerConflict
from story_builder.tests.test_agent_tasks import AgentTaskFixture


class AgentImageTests(AgentTaskFixture):
    def payload(self):
        return {'request_id': str(uuid.uuid4()), 'text': 'Cover the room in slime.',
                'asset_ids': [], 'skill_refs': [], 'surface': 'image',
                'target': {'version': 1, 'request': {'workspace_id': self.owner,
                    'workflow_id': 'z_image_turbo', 'asset_role': 'world_master', 'prompt': 'A ruined room.'}}}

    def test_shared_route_uses_manual_preparation_and_recovers_saved_proposal(self):
        def reason(**kwargs):
            if 'output_schema' in kwargs:
                return {'reply': 'Review the image suggestion before applying.', 'intent': 'image.prepare_prompt', 'quality': 2}
            return {'prompt': 'A ruined room covered in slime.'}
        provider = Mock(side_effect=reason)
        self.app = create_app(data_root=self.root, reasoning_json_provider=provider,
            gpu_reader=lambda: self.fail('Prompt proposal must not query GPU'),
            worker_status_provider=lambda: self.fail('Prompt proposal must not query worker'))
        payload = self.payload()
        path = '/api/agent/projects/tool-library/conversation'
        status, result = self.call('POST', path, payload)
        self.assertEqual(status, '200 OK', result)
        proposal = result['messages'][-1]['proposal']
        self.assertEqual(proposal['target'], payload['target'])
        self.assertEqual(proposal['draft']['prompt'], 'A ruined room covered in slime.')
        self.assertTrue(proposal['draft']['sources'])
        self.assertEqual(self.call('POST', path, payload)[1], result)
        self.assertEqual(self.call('GET', path)[1], result)
        self.assertEqual(provider.call_count, 2)
        self.assertEqual(self.tasks.list(self.owner)['tasks'], [])
        self.dispatch.assert_not_called()
        self.assertEqual(self.original.read_bytes(), self.before)

    def test_wrong_owner_and_unknown_target_versions_do_not_call_provider(self):
        reason = Mock()
        chat = AgentConversation(self.tasks, reason)
        for target in ({'version': True, 'request': self.payload()['target']['request']},
                       {'version': 2, 'request': {}},
                       {'version': 1, 'request': {'workspace_id': 'other', 'prompt': ''}}):
            with self.assertRaises(ValueError):
                chat.send(self.owner, {**self.payload(), 'target': target})
        reason.assert_not_called()

    def test_interrupted_preparation_is_recorded_and_never_replayed(self):
        reason = Mock(return_value={'reply': 'Drafting.', 'intent': 'image.prepare_prompt', 'quality': 2})
        prepare = Mock(side_effect=RuntimeError('Provider interrupted'))
        chat = AgentConversation(self.tasks, reason, image_prepare=prepare)
        payload = self.payload()
        with self.assertRaises(RuntimeError):
            chat.send(self.owner, payload)
        saved = chat.send(self.owner, payload)['messages'][-1]
        self.assertEqual(saved['status'], 'interrupted')
        self.assertNotIn('proposal', saved)
        prepare.assert_called_once()
        with self.assertRaises(LedgerConflict):
            chat.send(self.owner, {**payload, 'text': 'Different request'})

    def test_discussion_never_prepares_or_submits_an_image(self):
        prepare = Mock()
        chat = AgentConversation(self.tasks, Mock(return_value={'reply': 'Discuss the lighting.', 'intent': 'discuss', 'quality': 2}), image_prepare=prepare)
        result = chat.send(self.owner, self.payload())
        self.assertNotIn('proposal', result['messages'][-1])
        prepare.assert_not_called()
        self.dispatch.assert_not_called()
