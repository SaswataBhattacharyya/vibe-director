"""CPU-only shared shot prompt preparation and lost-reply recovery."""
import uuid
from unittest.mock import Mock

from story_builder.isolated_server import create_app
from story_builder.services.agent_conversation import AgentConversation
from story_builder.services.agent_video_prompt import VideoPromptDirector
from story_builder.services.field_edit_proposals import FieldEditProposals
from story_builder.services.production_ledger import LedgerConflict
from story_builder.tests.test_agent_tasks import AgentTaskFixture


class AgentVideoPromptTests(AgentTaskFixture):
    def payload(self, prompt='A boat ⛵ at dawn.'):
        return {'request_id': str(uuid.uuid4()), 'text': 'Use a slow dolly.', 'asset_ids': [], 'skill_refs': [],
            'surface': 'video', 'target': {'version': 1, 'workspace_id': self.owner, 'clip_id': 'clip-a',
                'revision_id': 'clip-a', 'prompt': prompt, 'settings': {'workflow': 'minimax_h3_t2v_local_v1', 'duration': 6}, 'history': []}}

    def test_http_reuses_field_edits_without_changing_controls_or_running_jobs(self):
        provider = Mock(side_effect=lambda **kw: {'reply': 'Review the shot prompt.', 'intent': 'video.prepare_prompt', 'quality': 2}
            if 'output_schema' in kw else {'replacement': 'A boat at dawn, slow dolly.', 'explanation': 'Camera direction.'})
        self.app = create_app(data_root=self.root, reasoning_json_provider=provider,
            gpu_reader=lambda: self.fail('Prompt preparation must not query GPU'),
            worker_status_provider=lambda: self.fail('Prompt preparation must not query worker'))
        path = f'/api/agent/projects/{self.owner}/conversation'
        for prompt in ('A boat ⛵ at dawn.', ''):
            payload = self.payload(prompt)
            status, result = self.call('POST', path, payload)
            self.assertEqual(status, '200 OK', result)
            item = result['messages'][-1]
            self.assertEqual(item['proposal']['target'], payload['target'])
            saved = FieldEditProposals(self.tasks.ledger).get_by_key(payload['request_id'])
            self.assertEqual(saved['proposal'], item['proposal']['suggestion'])
            self.assertEqual(saved['proposal']['end_codepoint'], len(prompt or 'Write a new video shot prompt.'))
            calls = provider.call_count
            self.assertEqual(self.call('POST', path, payload)[1], result)
            self.assertEqual(provider.call_count, calls)
        self.assertEqual(self.tasks.list(self.owner)['tasks'], [])
        self.dispatch.assert_not_called()
        self.assertEqual(self.original.read_bytes(), self.before)

    def test_invalid_context_never_calls_provider(self):
        provider = Mock()
        adapter = VideoPromptDirector(FieldEditProposals(self.tasks.ledger), provider)
        chat = AgentConversation(self.tasks, provider, video=adapter)
        target = self.payload()['target']
        for change in ({'version': True}, {'workspace_id': 'other'}, {'clip_id': ''}, {'extra': 1},
                       {'history': [{'user': 3}]}, {'settings': []}, {'prompt': 'x' * 7000}):
            with self.assertRaises(ValueError):
                chat.send(self.owner, {**self.payload(), 'target': {**target, **change}})
        provider.assert_not_called()

    def test_lost_reply_keeps_exact_field_request_recoverable_without_resubmission(self):
        edits = FieldEditProposals(self.tasks.ledger)
        adapter = VideoPromptDirector(edits, Mock(return_value={'replacement': 'A boat, slow dolly.'}))
        respond = adapter.respond
        def lose_reply(*args):
            respond(*args)
            raise RuntimeError('Lost reply after field suggestion saved')
        adapter.respond = Mock(side_effect=lose_reply)
        chat = AgentConversation(self.tasks, Mock(return_value={'reply': 'Review.', 'intent': 'video.prepare_prompt', 'quality': 2}), video=adapter)
        payload = self.payload()
        with self.assertRaises(RuntimeError):
            chat.send(self.owner, payload)
        item = chat.send(self.owner, payload)['messages'][-1]
        self.assertEqual(item['status'], 'interrupted')
        self.assertEqual(item['video_target'], payload['target'])
        self.assertEqual(edits.get_by_key(payload['request_id'])['proposal']['replacement'], 'A boat, slow dolly.')
        adapter.respond.assert_called_once()
        with self.assertRaises(LedgerConflict):
            chat.send(self.owner, {**payload, 'text': 'Different content'})
