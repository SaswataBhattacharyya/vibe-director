"""Shared routing and isolated CPU evidence: no models/providers/GPU execution."""
import io
import json
import subprocess
import uuid
from unittest.mock import Mock, patch
from PIL import Image
from story_builder.tests.test_agent_tasks import AgentTaskFixture
from story_builder.services import agent_analysis_tools as analysis, agent_workspace_tools as workspace
from story_builder.services import agent_tools, media_library, video_repertoire, vibe_editor
from story_builder.services.agent_conversation import AgentConversation
from story_builder.services.agent_generation_tools import bridge
from story_builder.services.agent_tool_routing import propose
from story_builder.services.production_ledger import LedgerConflict


class ToolAccessTests(AgentTaskFixture):
    def image(self):
        stream = io.BytesIO()
        Image.new('RGB', (32, 32), 'red').save(stream, 'PNG')
        return media_library.register_upload(self.root, self.owner, filename='test.png', content=stream.getvalue(), role='project_image')['asset_id']

    def run_workspace(self, row):
        self.tasks.approve(self.owner, row['task_id'], self.approval(row))
        task = self.tasks.run(self.owner, row['task_id'], self.approval(row))
        job = video_repertoire.read_job(workspace.KIND, task['invocation']['job_id'])
        job.update(status='completed', result=workspace.run(self.root, job['job_id'], job['request']))
        video_repertoire._atomic_json(video_repertoire.job_path(workspace.KIND, job['job_id']), job)
        return self.tasks.poll(self.owner, row['task_id'])

    def test_both_chat_surfaces_route_live_catalogue_and_keep_proposals_inert(self):
        for surface in ('director', 'editor'):
            reason = Mock(return_value={'reply': 'Review inspection.', 'quality': 2, 'intent': 'tool.call',
                'tool_call': {'tool_id': 'media.inspect', 'asset_ids': [self.asset['asset_id']], 'settings': {}}})
            result = AgentConversation(self.tasks, reason).send(self.owner, {'request_id': str(uuid.uuid4()),
                'surface': surface, 'text': 'Inspect this audio.', 'asset_ids': [self.asset['asset_id']], 'skill_refs': []})
            task = self.tasks.get(self.owner, result['messages'][-1]['task_id'])
            self.assertEqual(task['plan']['tool_id'], 'media.inspect')
            self.assertEqual(task['status'], 'draft')
        self.dispatch.assert_not_called()

    def test_unknown_blocked_malformed_nonfinite_and_foreign_calls_rejected(self):
        catalogue = agent_tools.tools()['tools']
        for call in ({'tool_id': 'unsafe.shell', 'settings': {}, 'asset_ids': []},
                     {'tool_id': 'media.inspect', 'settings': {'command': 'x'}, 'asset_ids': [self.asset['asset_id']]},
                     {'tool_id': 'media.inspect', 'settings': {}, 'asset_ids': ['pa-not-owned']},
                     {'tool_id': 'video.sample_frames', 'settings': {'timestamps_seconds': [float('nan')]}, 'asset_ids': [self.asset['asset_id']]}):
            with self.assertRaises(ValueError):
                propose(self.tasks, self.owner, catalogue, call)
        with self.assertRaisesRegex(ValueError, 'fixture offline'):
            propose(self.tasks, self.owner, [{'id': 'blocked', 'execution_enabled': False, 'reason': 'fixture offline'}],
                {'tool_id': 'blocked', 'settings': {}, 'asset_ids': []})
        self.dispatch.assert_not_called()

    def test_computer_tool_reachable_without_new_execution_path(self):
        row = {'tool_id': 'computer.execute', 'settings': {'instruction': 'Read project files.', 'access_mode': 'project', 'skill_refs': []}, 'asset_ids': []}
        catalogue = agent_tools.tools()['tools']
        next(t for t in catalogue if t['id'] == row['tool_id'])['execution_enabled'] = True
        with patch.object(self.tasks, 'propose', return_value={'status': 'draft'}) as submit:
            self.assertEqual(propose(self.tasks, self.owner, catalogue, row)['status'], 'draft')
        submit.assert_called_once_with(self.owner, row)
        self.dispatch.assert_not_called()

    def test_media_adapters_call_fixed_existing_routes(self):
        cases = [('image.analyze', {'mode': 'quick'}, [self.image()], '/image-detailer/'),
            ('video.analyze', {'parameters': {}}, [self.asset['asset_id']], '/analysis/jobs'),
            ('media.index_content', {}, [self.asset['asset_id']], '/semantic-content-index'),
            ('audio.split_scene', {'edits': [{'start': 0, 'end': .2, 'text': 'hello'}], 'transcript': 'hello'}, [self.asset['asset_id']], '/scene-surgery/jobs'),
            ('media.download_youtube', {'urls': [{'url': 'https://youtu.be/example'}]}, [], '/youtube/jobs'),
            ('video.extract_style_frames', {'directing_style_id': 'style-example', 'timestamps_seconds': [0]}, [self.asset['asset_id']], '/style-frames')]
        for tool, settings, ids, route in cases:
            assets = self.tasks._assets(self.owner, ids, extensions={'.png', '.wav'}) if ids else []
            def call(method, path, body):
                self.assertEqual(method, 'POST')
                self.assertIn(route, path)
                job = video_repertoire.create_job(analysis.TOOLS[tool], {'workspace_id': self.owner, 'body': body})
                return {'job_id': job['job_id']}
            self.assertEqual(analysis.submit(call, self.owner, tool, settings, assets)['kind'], analysis.TOOLS[tool])
        self.assertEqual(self.original.read_bytes(), self.before)

    def test_audio_split_existing_route_and_stitch_freezes_result(self):
        self.tasks.native_request = bridge(self.app)
        with patch.object(analysis.audio_scene, 'capabilities', return_value={'checks': {'split': {'available': True}}}):
            row = self.tasks.propose(self.owner, {'tool_id': 'audio.split_scene', 'asset_ids': [self.asset['asset_id']],
                'settings': {'edits': [{'start': 0, 'end': .2, 'text': 'test'}], 'transcript': 'test'}})
            self.tasks.approve(self.owner, row['task_id'], self.approval(row))
            task = self.tasks.run(self.owner, row['task_id'], self.approval(row))
        job = video_repertoire.read_job('audio-scene-split', task['invocation']['job_id'])
        self.assertEqual(job['request']['agent_plan'], row['plan'])
        job.update(status='completed', result={'manifest': {'clips': [{'clip_index': 0}]}})
        video_repertoire._atomic_json(video_repertoire.job_path('audio-scene-split', job['job_id']), job)
        stitch = self.tasks.propose(self.owner, {'tool_id': 'audio.stitch_scene', 'asset_ids': [], 'settings': {
            'split_job_id': job['job_id'], 'replacement_asset_ids': {}, 'gaps': {}, 'mode': 'simple'}})
        job['result']['manifest']['clips'].append({'clip_index': 1})
        video_repertoire._atomic_json(video_repertoire.job_path('audio-scene-split', job['job_id']), job)
        with self.assertRaises(LedgerConflict):
            self.tasks.approve(self.owner, stitch['task_id'], self.approval(stitch))
        self.assertEqual(self.original.read_bytes(), self.before)

    def test_chat_can_create_session_and_select_ranges_without_rendering(self):
        created = self.tasks.propose(self.owner, {'tool_id': 'editor.create_session', 'asset_ids': [], 'settings': {'name': 'Chat cut'}})
        result = json.loads(self.run_workspace(created)['report'])['result']['result']
        session = result['project_id']
        settings = {'project_id': session, 'revision': 0, 'selection': [{'asset_id': self.asset['asset_id'], 'start': 0, 'end': .2}]}
        selected = self.tasks.propose(self.owner, {'tool_id': 'editor.select_media', 'asset_ids': [self.asset['asset_id']], 'settings': settings})
        self.run_workspace(selected)
        with vibe_editor.state(self.root, readonly=True) as data:
            p = vibe_editor.project(data, session)
            self.assertEqual(p['revision'], 1)
            self.assertEqual(p['selection'][0]['end'], .2)
            self.assertIsNone(p['job_id'])
            self.assertNotIn('brief', p)
        with self.assertRaisesRegex(ValueError, 'revision changed'):
            vibe_editor.update_project(self.root, session, {'selection': []}, expected_revision=0)
        with self.assertRaisesRegex(ValueError, 'ownership or revision'):
            self.tasks.propose(self.owner, {'tool_id': 'editor.select_media', 'asset_ids': [self.asset['asset_id']], 'settings': settings})
        settings['revision'] = 1
        settings['selection'][0]['end'] = 999
        with self.assertRaisesRegex(ValueError, 'duration'):
            self.tasks.propose(self.owner, {'tool_id': 'editor.select_media', 'asset_ids': [self.asset['asset_id']], 'settings': settings})
        self.assertEqual(self.original.read_bytes(), self.before)

    def test_cpu_inspection_results_reach_followup_chat(self):
        row = self.tasks.propose(self.owner, {'tool_id': 'media.inspect', 'asset_ids': [self.asset['asset_id']], 'settings': {}})
        self.assertIn('duration_seconds', self.run_workspace(row)['report'])
        reason = Mock(return_value={'reply': 'It is 0.3 seconds.', 'intent': 'discuss', 'quality': 2})
        AgentConversation(self.tasks, reason).send(self.owner, {'request_id': str(uuid.uuid4()), 'surface': 'director',
            'text': 'What is its duration?', 'asset_ids': [self.asset['asset_id']], 'skill_refs': []})
        self.assertIn('duration_seconds', reason.call_args.kwargs['prompt'])
        self.assertEqual(self.original.read_bytes(), self.before)

    def test_cpu_frames_are_owned_and_transients_removed(self):
        path = self.root / 'fixture.mp4'
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'color=c=red:s=64x64:r=10:d=1', '-threads', '1', '-y', str(path)], check=True)
        video = media_library.register_upload(self.root, self.owner, filename='fixture.mp4', content=path.read_bytes(), role='project_video')
        row = self.tasks.propose(self.owner, {'tool_id': 'video.sample_frames', 'asset_ids': [video['asset_id']], 'settings': {'timestamps_seconds': [0, .8]}})
        result = json.loads(self.run_workspace(row)['report'])['result']['result']
        self.assertEqual(len(result['frames']), 2)
        for frame in result['frames']:
            image, mime, _ = media_library.asset_path(self.root, self.owner, frame['asset']['asset_id'])
            self.assertTrue(image.is_file())
            self.assertTrue(mime.startswith('image/'))
        reason = Mock(return_value={'reply': 'Red frames.', 'intent': 'discuss', 'quality': 2})
        AgentConversation(self.tasks, reason).send(self.owner, {'request_id': str(uuid.uuid4()), 'surface': 'director',
            'text': 'Inspect the sampled frames.', 'asset_ids': [video['asset_id']], 'skill_refs': []})
        self.assertEqual(len(reason.call_args.kwargs['image_paths']), 2)
        self.assertFalse(list(self.root.rglob('*.tmp.png')))
        self.assertEqual(media_library.asset_path(self.root, self.owner, video['asset_id'])[0].read_bytes(), path.read_bytes())

    def test_failed_extraction_removes_only_transients(self):
        from pathlib import Path
        aid = self.image()
        source = self.tasks._assets(self.owner, [aid], extensions={'.png'})[0]
        def fail(command, **kwargs):
            Path(command[-1]).write_bytes(b'partial')
            raise subprocess.CalledProcessError(1, command)
        with patch.object(workspace.subprocess, 'run', side_effect=fail), self.assertRaises(subprocess.CalledProcessError):
            workspace.sample_frames(self.root, self.owner, 'owned-fixture', source, self.original, [0])
        self.assertFalse(list(self.root.rglob('*.tmp.png')))
        self.assertEqual(self.original.read_bytes(), self.before)

    def test_timeline_proposal_retains_review_and_rejects_stale_session(self):
        aid = self.image()
        p = vibe_editor.add_project(self.root, {'workspace_id': self.owner, 'name': 'Owned edit'})
        p = vibe_editor.update_project(self.root, p['id'], {'selection': [{'asset_id': aid, 'start': 0, 'end': 3}]})
        with vibe_editor.state(self.root) as data:
            vibe_editor.project(data, p['id'])['brief'] = {'summary': 'Fixture', 'questions': []}
        settings = {'project_id': p['id'], 'revision': p['revision'], 'plan': {'clips': [{'asset_id': aid, 'start': .5, 'end': 2}], 'width': 320, 'height': 180, 'fps': 24}}
        row = self.tasks.propose(self.owner, {'tool_id': 'editor.prepare_timeline', 'asset_ids': [aid], 'settings': settings})
        self.assertIn('pending_clearance', self.run_workspace(row)['report'])
        with vibe_editor.state(self.root, readonly=True) as data:
            saved = vibe_editor.project(data, p['id'])
            self.assertEqual(saved['pending']['kind'], 'plan')
            self.assertIsNone(saved['job_id'])
        with self.assertRaises(ValueError):
            self.tasks.propose(self.owner, {'tool_id': 'editor.prepare_timeline', 'asset_ids': [aid], 'settings': settings})
