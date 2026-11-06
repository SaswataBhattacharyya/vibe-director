"""Both chat surfaces propose through the same durable gateway; no provider calls."""
import json
import uuid
from unittest.mock import Mock

from story_builder.services.agent_conversation import AgentConversation
from story_builder.services import agent_knowledge
from story_builder.services.production_ledger import LedgerConflict
from story_builder.tests.test_agent_tasks import AgentTaskFixture


class ConversationTests(AgentTaskFixture):
    def test_knowledge_is_revisioned_and_included_in_both_surfaces(self):
        self.assertEqual(agent_knowledge.read(self.root, self.tasks.ledger, self.owner)['revision'], 0)
        payload = {'revision': 0, 'content': 'The same room becomes covered in slime in scene five.'}
        saved = agent_knowledge.save(self.root, self.tasks.ledger, self.owner, payload)
        with self.assertRaises(LedgerConflict):
            agent_knowledge.save(self.root, self.tasks.ledger, self.owner, payload)
        with self.assertRaises(ValueError):
            agent_knowledge.read(self.root, self.tasks.ledger, 'story-aaaaaaaaaaaa')
        reason = Mock(return_value={'reply': 'I will preserve the room layout.', 'intent': 'discuss', 'quality': 2})
        chat = AgentConversation(self.tasks, reason)
        for surface in ('director', 'editor'):
            chat.send(self.owner, self.payload(surface))
            self.assertIn(saved['content'], reason.call_args.kwargs['prompt'])
        self.assertEqual(self.call('GET', f'/api/agent/projects/{self.owner}/knowledge')[1], saved)
        self.assertEqual(self.call('POST', f'/api/agent/projects/{self.owner}/knowledge', payload)[0], '409 Conflict')

    def payload(self, surface):
        return {'request_id': str(uuid.uuid4()), 'text': 'Please extract the selected audio as MP3.',
                'surface': surface, 'asset_ids': [self.asset['asset_id']], 'skill_refs': ['application/vibe/vibe-director']}

    def test_both_surfaces_propose_without_dispatch_and_request_retry_is_inert(self):
        reason = Mock(return_value={'reply': 'Review this extraction plan.', 'intent': 'extract_mp3', 'quality': 2})
        chat = AgentConversation(self.tasks, reason)
        for surface in ('director', 'editor'):
            payload = self.payload(surface)
            result = chat.send(self.owner, payload)
            row = result['messages'][-1]
            self.assertEqual(row['status'], 'answered')
            self.assertEqual(self.tasks.get(self.owner, row['task_id'])['status'], 'draft')
            chat.send(self.owner, payload)
            with self.assertRaises(LedgerConflict):
                chat.send(self.owner, {**payload, 'text': 'Different content'})
        self.assertEqual(reason.call_count, 2)
        self.dispatch.assert_not_called()
        options = reason.call_args.kwargs
        self.assertTrue(options['cpu_only'])
        self.assertIn('sha256', options['prompt'])
        self.assertIn('vibe-director', options['prompt'])
        restored = AgentConversation(self.tasks, reason).history(self.owner)
        self.assertEqual(len(restored['messages']), 2)

    def test_invalid_reasoning_and_failed_request_are_retained_without_execution(self):
        reason = Mock(return_value={'reply': 'Bad', 'intent': 'shell', 'quality': 2})
        chat = AgentConversation(self.tasks, reason)
        payload = self.payload('director')
        with self.assertRaises(ValueError):
            chat.send(self.owner, payload)
        self.assertEqual(chat.history(self.owner)['messages'][0]['status'], 'interrupted')
        chat.send(self.owner, payload)
        self.assertEqual(reason.call_count, 1)
        self.assertEqual(self.tasks.list(self.owner)['tasks'], [])
        self.dispatch.assert_not_called()

    def test_wrong_owner_or_skill_or_asset_is_rejected_before_reasoning(self):
        reason = Mock()
        chat = AgentConversation(self.tasks, reason)
        for changes in ({'asset_ids': ['pa-other']}, {'skill_refs': ['global/invalid/nope']}, {'surface': 'shell'}):
            with self.assertRaises((ValueError, FileNotFoundError)):
                chat.send(self.owner, {**self.payload('director'), **changes})
        reason.assert_not_called()

    def test_project_switch_during_reasoning_does_not_create_a_task(self):
        def changed(**kwargs):
            path = self.root / 'library/projects/active.json'
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({'workspace_id': 'story-aaaaaaaaaaaa'}))
            return {'reply': 'Review this plan.', 'intent': 'extract_mp3', 'quality': 2}
        chat = AgentConversation(self.tasks, changed)
        with self.assertRaises(ValueError):
            chat.send(self.owner, self.payload('director'))
        self.dispatch.assert_not_called()

