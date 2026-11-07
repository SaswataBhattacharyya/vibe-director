"""Shared music chat delegates to the existing CPU job; never confirms media work."""
import uuid
from unittest.mock import Mock, patch
from story_builder.services import ace_studio
from story_builder.services.agent_conversation import AgentConversation
from story_builder.tests.test_agent_tasks import AgentTaskFixture


class AgentMusicTests(AgentTaskFixture):
    def payload(self):
        p = ace_studio.add_project(self.root, {'name': 'Disposable music', 'workspace_id': self.owner})
        return {'request_id': str(uuid.uuid4()), 'text': 'A quiet piano instrumental.', 'asset_ids': [], 'skill_refs': [],
                'surface': 'music', 'target': {'version': 1, 'workspace_id': self.owner, 'project_id': p['id'], 'revision': p['revision']}}

    def test_chat_uses_existing_job_once_and_preserves_confirmation(self):
        chat = AgentConversation(self.tasks, Mock(return_value={'reply': 'Discuss.', 'intent': 'music.discuss', 'quality': 1}))
        payload = self.payload()
        with patch.object(ace_studio.jobs, 'create_job', return_value={'job_id': 'test-chat'}) as create, patch.object(ace_studio.jobs, 'start_job') as start:
            result = chat.send(self.owner, payload)
            self.assertEqual(chat.send(self.owner, payload), result)
        self.assertEqual(create.call_args.args[1]['operation'], 'chat')
        create.assert_called_once()
        start.assert_called_once_with('ace-studio', 'test-chat')
        with ace_studio.state(self.root) as data:
            project = ace_studio.project(data, payload['target']['project_id'])
            self.assertIsNone(project['confirmed_revision'])
            self.assertEqual(project['messages'][-1]['content'], payload['text'])
        self.dispatch.assert_not_called()
        self.assertEqual(self.original.read_bytes(), self.before)

    def test_wrong_owner_revision_and_invalid_target_do_not_dispatch(self):
        provider = Mock()
        chat = AgentConversation(self.tasks, provider)
        payload = self.payload()
        for changes in ({'workspace_id': 'other'}, {'revision': True}, {'version': 2}, {'extra': 1}, {'revision': 99}):
            with self.assertRaises(ValueError):
                chat.send(self.owner, {**payload, 'target': {**payload['target'], **changes}})
        with ace_studio.state(self.root) as data:
            ace_studio.project(data, payload['target']['project_id'])['workspace_id'] = 'other'
        with self.assertRaises(ValueError):
            chat.send(self.owner, payload)
        provider.assert_not_called()
