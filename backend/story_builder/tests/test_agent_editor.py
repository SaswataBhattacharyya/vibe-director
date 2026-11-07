"""Shared Director -> existing Editor, using disposable media and mocked reasoning."""
import base64
import json
import uuid
from unittest.mock import Mock, patch

from story_builder.services import agent_editor, media_library, vibe_editor, video_repertoire
from story_builder.services.agent_conversation import AgentConversation
from story_builder.services.production_ledger import LedgerConflict
from story_builder.tests.test_agent_tasks import AgentTaskFixture


class AgentEditorTests(AgentTaskFixture):
    def setUp(self):
        super().setUp()
        png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aD1cAAAAASUVORK5CYII=')
        self.image = media_library.register_upload(self.root, self.owner, filename='frame.png', content=png, role='project_image')
        self.editor = vibe_editor.add_project(self.root, {'name': 'Test edit', 'workspace_id': self.owner})
        self.editor = vibe_editor.update_project(self.root, self.editor['id'], {'selection': [
            {'asset_id': self.image['asset_id'], 'start': 1, 'end': 2}]})

    def target(self):
        return {'version': 1, 'editor_session_id': self.editor['id'], 'expected_revision': self.editor['revision'],
                'selected_ranges': agent_editor.ranges(self.editor['selection'])}

    def draft(self, instruction='Make a calm one-second edit.'):
        return self.tasks.propose(self.owner, {'tool_id': 'editor.prepare_brief', 'asset_ids': [self.image['asset_id']],
            'settings': {'instruction': instruction, 'target': self.target()}})

    def finish(self, row, value):
        job_id = row['invocation']['job_id']
        job = video_repertoire.read_job('vibe-editor', job_id)
        with patch('story_builder.services.reasoning_provider.generate_json', return_value=value):
            result = vibe_editor.run_job(self.root, job_id, job['request'], lambda *_: None)
        job.update(status='completed', result=result)
        video_repertoire.job_path('vibe-editor', job_id).write_text(json.dumps(job))
        return self.tasks.poll(self.owner, row['task_id'])

    def test_shared_chat_brief_clearances_and_plan_use_existing_session(self):
        chat = AgentConversation(self.tasks, Mock(return_value={'reply': 'Review brief preparation.', 'intent': 'editor.prepare_brief', 'quality': 2}))
        payload = {'request_id': str(uuid.uuid4()), 'text': 'Make a calm one-second edit.', 'asset_ids': [],
                   'skill_refs': [], 'surface': 'editor', 'target': self.target()}
        message = chat.send(self.owner, payload)['messages'][-1]
        chat.send(self.owner, payload)
        self.assertEqual(len(self.tasks.list(self.owner)['tasks']), 1)
        self.dispatch.assert_not_called()
        row = self.tasks.get(self.owner, message['task_id'])
        self.tasks.approve(self.owner, row['task_id'], self.approval(row))
        started = self.tasks.run(self.owner, row['task_id'], self.approval(row))
        self.assertEqual(self.tasks.run(self.owner, row['task_id'], self.approval(row))['invocation'], started['invocation'])
        result = self.finish(started, {'summary': 'A calm one-second edit.', 'questions': [], 'preference_proposal': ''})
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['outputs'], [])
        p = vibe_editor.snapshot(self.root)['projects'][0]
        self.assertEqual((p['id'], p['pending']['kind']), (self.editor['id'], 'brief'))
        self.assertNotIn('output', p)
        vibe_editor.command(self.root, p['id'], {'action': 'approve', 'revision': p['revision']})
        p = vibe_editor.snapshot(self.root)['projects'][0]
        job = video_repertoire.read_job('vibe-editor', p['job_id'])
        self.assertEqual(job['request']['operation'], 'plan')
        self.assertEqual(agent_editor.ranges(job['request']['selection']), payload['target']['selected_ranges'])
        with patch('story_builder.services.reasoning_provider.generate_json', return_value={
                'summary': 'One frame', 'tools': ['HyperFrames'], 'width': 320, 'height': 180, 'fps': 24,
                'clips': [{'asset_id': self.image['asset_id'], 'start': 1, 'end': 2}], 'audio': None, 'blocker': ''}):
            vibe_editor.run_job(self.root, job['job_id'], job['request'], lambda *_: None)
        p = vibe_editor.snapshot(self.root)['projects'][0]
        self.assertEqual(p['pending']['kind'], 'plan')
        self.assertCountEqual([j['request']['operation'] for j in [video_repertoire.read_job('vibe-editor', path.parent.name)
            for path in (self.root / 'services/media/jobs/vibe-editor').glob('*/job.json')]], ['brief', 'plan'])

    def test_wrong_owner_session_revision_and_ranges_fail_closed(self):
        original = self.target()
        for change in ({'editor_session_id': 'edit-missing'}, {'expected_revision': 99},
                       {'selected_ranges': []}, {'version': 2}, {'version': True},
                       {'selected_ranges': [{**original['selected_ranges'][0], 'start': True}]}):
            with self.assertRaises((ValueError, LedgerConflict)):
                agent_editor.context(self.root, self.owner, {**original, **change})
        with self.assertRaises(LedgerConflict):
            agent_editor.context(self.root, 'story-aaaaaaaaaaaa', original)
        row = self.draft()
        vibe_editor.update_project(self.root, self.editor['id'], {'selection': []})
        with self.assertRaises(LedgerConflict):
            self.tasks.approve(self.owner, row['task_id'], self.approval(row))
        self.dispatch.assert_not_called()

    def test_abrupt_mapping_loss_recovers_brief_without_restarting(self):
        row = self.ready()
        with patch.object(self.tasks, '_map_job', side_effect=KeyboardInterrupt), self.assertRaises(KeyboardInterrupt):
            self.tasks.run(self.owner, row['task_id'], self.approval(row))
        recovered = self.tasks.poll(self.owner, row['task_id'])
        self.assertEqual(recovered['status'], 'running')
        self.assertEqual(len(list((self.root / 'services/media/jobs/vibe-editor').glob('*/job.json'))), 1)
        self.dispatch.assert_not_called()
        self.assertEqual(self.tasks.cancel(self.owner, row['task_id'])['status'], 'cancelled')

    def test_brief_action_cannot_turn_assent_into_render_approval(self):
        row = self.ready()
        started = self.tasks.run(self.owner, row['task_id'], self.approval(row))
        self.finish(started, {'summary': 'Answer required', 'questions': ['What pace?'], 'preference_proposal': ''})
        self.editor = vibe_editor.snapshot(self.root)['projects'][0]
        row = self.draft('yes, apply')
        self.tasks.approve(self.owner, row['task_id'], self.approval(row))
        next_task = self.tasks.run(self.owner, row['task_id'], self.approval(row))
        job = video_repertoire.read_job('vibe-editor', next_task['invocation']['job_id'])
        self.assertEqual(job['request']['operation'], 'brief')
        self.assertEqual(vibe_editor.snapshot(self.root)['projects'][0]['revisions'], [])

    def test_approved_target_cannot_follow_a_changed_style_or_media(self):
        row = self.ready()
        vibe_editor.update_project(self.root, self.editor['id'], {'override': 'Use slow pacing'})
        with self.assertRaises(LedgerConflict):
            self.tasks.run(self.owner, row['task_id'], self.approval(row))
        self.dispatch.assert_not_called()

    def test_recovery_rejects_an_editor_job_with_changed_frozen_request(self):
        row = self.ready()
        started = self.tasks.run(self.owner, row['task_id'], self.approval(row))
        path = video_repertoire.job_path('vibe-editor', started['invocation']['job_id'])
        job = json.loads(path.read_text())
        job['request']['selection'][0]['end'] = 3
        path.write_text(json.dumps(job))
        with self.assertRaises(LedgerConflict):
            self.tasks.poll(self.owner, row['task_id'])

    def test_shared_chat_does_not_retarget_after_reasoning_changes_the_session(self):
        def reason(**_):
            vibe_editor.update_project(self.root, self.editor['id'], {'selection': []})
            return {'reply': 'Prepare brief.', 'intent': 'editor.prepare_brief', 'quality': 2}
        chat = AgentConversation(self.tasks, reason)
        with self.assertRaises(LedgerConflict):
            chat.send(self.owner, {'request_id': str(uuid.uuid4()), 'text': 'Edit the selected frame.',
                'asset_ids': [], 'skill_refs': [], 'surface': 'editor', 'target': self.target()})
        self.assertEqual(self.tasks.list(self.owner)['tasks'], [])
        self.assertEqual(chat.history(self.owner)['messages'][-1]['status'], 'interrupted')
        self.dispatch.assert_not_called()

    def test_extraction_uses_editor_sources_not_five_second_selection(self):
        self.editor = vibe_editor.update_project(self.root, self.editor['id'], {'selection': [
            {'asset_id': self.asset['asset_id'], 'start': 0, 'end': .1}]})
        reason = Mock(return_value={'reply': 'Already extracted!', 'intent': 'extract_mp3', 'quality': 2})
        payload = {'request_id': str(uuid.uuid4()), 'text': 'Extract the audio.', 'asset_ids': [],
                   'skill_refs': [], 'surface': 'editor', 'target': self.target()}
        chat = AgentConversation(self.tasks, reason)
        with patch('story_builder.services.agent_tools.shutil.which', return_value='/test/ffmpeg'):
            message = chat.send(self.owner, payload)['messages'][-1]
            chat.send(self.owner, payload)
        task = self.tasks.get(self.owner, message['task_id'])
        self.assertEqual([a['asset_id'] for a in task['plan']['assets']], [self.asset['asset_id']])
        self.assertEqual(task['plan']['settings'], {'quality': 2})
        self.assertIn('whole assets', task['plan']['scope'])
        self.assertNotIn('Already extracted', message['reply'])
        self.assertIn('No media has been processed', message['reply'])
        prompt = reason.call_args.kwargs['prompt']
        self.assertIn('"tools":', prompt)
        self.assertIn('whole_source', prompt)
        self.assertIn('source_assets', prompt)
        self.assertEqual(len(self.tasks.list(self.owner)['tasks']), 1)
        self.dispatch.assert_not_called()

    def test_explicit_attachments_override_editor_and_blocked_tools_do_not_propose(self):
        reason = Mock(return_value={'reply': 'Done', 'intent': 'extract_mp3', 'quality': 2})
        payload = {'request_id': str(uuid.uuid4()), 'text': 'Extract attached audio.',
                   'asset_ids': [self.asset['asset_id']], 'skill_refs': [], 'surface': 'editor', 'target': self.target()}
        chat = AgentConversation(self.tasks, reason)
        with patch('story_builder.services.agent_tools.shutil.which', return_value='/test/ffmpeg'):
            message = chat.send(self.owner, payload)['messages'][-1]
        self.assertEqual(self.tasks.get(self.owner, message['task_id'])['plan']['assets'][0]['asset_id'], self.asset['asset_id'])
        payload['request_id'] = str(uuid.uuid4())
        with patch('story_builder.services.agent_tools.shutil.which', return_value=None):
            message = chat.send(self.owner, payload)['messages'][-1]
        self.assertIsNone(message['task_id'])
        self.assertIn('ffmpeg is unavailable', message['reply'])
        reason.return_value['intent'] = 'analyze_speech'
        payload.update(request_id=str(uuid.uuid4()), text='Find the gibberish and remove it.')
        with patch('story_builder.services.agent_transcription.capability', return_value={
                'status': 'blocked', 'execution_enabled': False, 'reason': 'Prepared ASR model is missing.'}):
            message = chat.send(self.owner, payload)['messages'][-1]
        self.assertIsNone(message['task_id'])
        self.assertIn('Prepared ASR model is missing', message['reply'])
        self.assertIn('No processing has run', message['reply'])
        self.assertEqual(len(self.tasks.list(self.owner)['tasks']), 1)
        self.dispatch.assert_not_called()
