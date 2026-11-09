"""Mocked native submissions: no models, providers or GPU work."""
from unittest.mock import patch
from story_builder.tests.test_agent_tasks import AgentTaskFixture
from story_builder.services import agent_native_tools as native, voice_studio, video_repertoire, media_library, trellis_studio
from story_builder.services.production_ledger import LedgerConflict


class NativeToolsTests(AgentTaskFixture):
    def image(self, name, size=(32, 32)):
        import io
        from PIL import Image
        stream = io.BytesIO()
        Image.new('RGB', size, name).save(stream, 'PNG')
        return media_library.register_upload(self.root, self.owner, filename=name+'.png', content=stream.getvalue(), role='project_image')['asset_id']

    def test_multiview_roles_exact_approval_receipt_and_staging_cleanup(self):
        ids = [self.image('red'), self.image('blue')]
        settings = {'backend': 'pixal', 'preset': 'bounded', 'parameters': {'seed': 2},
                    'view_profile': 'two', 'views_confirmed': True}
        row = self.tasks.propose(self.owner, {'tool_id': '3d.generate_multiview', 'asset_ids': ids, 'settings': settings})
        self.dispatch.assert_not_called()
        self.tasks.approve(self.owner, row['task_id'], self.approval(row))
        result = self.tasks.run(self.owner, row['task_id'], self.approval(row))
        request = video_repertoire.read_job('trellis', result['invocation']['job_id'])['request']
        self.assertEqual(request['backend'], 'pixal')
        self.assertEqual(list(request['items'][0]['views']), ['front', 'back'])
        self.assertEqual(request['agent_plan']['assets'], row['plan']['assets'])
        self.tasks.run(self.owner, row['task_id'], self.approval(row))
        self.dispatch.assert_called_once()
        # A new proposal failing before a job is created removes only its staging.
        before = set((trellis_studio.home(self.root)/'input').glob('*.png'))
        second = self.tasks.propose(self.owner, {'tool_id': '3d.generate_multiview', 'asset_ids': ids, 'settings': settings})
        self.tasks.approve(self.owner, second['task_id'], self.approval(second))
        with patch.object(trellis_studio, 'create', side_effect=ValueError('fixture refusal')):
            with self.assertRaisesRegex(ValueError, 'fixture refusal'):
                self.tasks.run(self.owner, second['task_id'], self.approval(second))
        self.assertEqual(set((trellis_studio.home(self.root)/'input').glob('*.png')), before)
        for aid in ids:
            self.assertTrue(media_library.asset_path(self.root, self.owner, aid)[0].is_file())

    def test_multiview_requires_confirmation_distinct_views_and_matching_canvases(self):
        ids = [self.image('red'), self.image('blue', (16, 32))]
        settings = {'backend': 'trellis', 'preset': 'mv512', 'parameters': {},
                    'view_profile': 'two', 'views_confirmed': True}
        for assets, values in ((ids, settings), ([ids[0], ids[0]], settings),
                               (ids, {**settings, 'views_confirmed': False})):
            with self.assertRaises(ValueError):
                self.tasks.propose(self.owner, {'tool_id': '3d.generate_multiview', 'asset_ids': assets, 'settings': values})
        self.dispatch.assert_not_called()

    def test_audio_effect_uses_existing_route_and_has_durable_native_correlation(self):
        from story_builder.services.agent_generation_tools import bridge
        self.tasks.native_request = bridge(self.app)
        row = self.tasks.propose(self.owner, {'tool_id': 'audio.effects', 'asset_ids': [self.asset['asset_id']],
            'settings': {'operation': 'simple', 'parameters': {'preset': 'telephone', 'strength': .5}}})
        self.dispatch.assert_not_called()
        self.tasks.approve(self.owner, row['task_id'], self.approval(row))
        result = self.tasks.run(self.owner, row['task_id'], self.approval(row))
        job = video_repertoire.read_job('audio-effects', result['invocation']['job_id'])
        self.assertEqual(job['request']['agent_plan'], row['plan'])
        self.assertEqual(job['request']['asset_id'], self.asset['asset_id'])
        self.tasks.run(self.owner, row['task_id'], self.approval(row))
        self.dispatch.assert_called_once()
        self.assertEqual(self.original.read_bytes(), self.before)

    def test_audio_effect_rejects_unknown_parameters_and_missing_transcript(self):
        for settings in ({'operation': 'simple', 'parameters': {'command': 'unsafe'}},
                         {'operation': 'emotion', 'parameters': {}},
                         {'operation': 'simple', 'parameters': {'strength': float('nan')}}):
            with self.assertRaises(ValueError):
                self.tasks.propose(self.owner, {'tool_id': 'audio.effects', 'asset_ids': [self.asset['asset_id']], 'settings': settings})
        self.dispatch.assert_not_called()

    def voice(self):
        with patch.object(voice_studio, 'compile_graph', return_value={}):
            return self.tasks.propose(self.owner, {'tool_id': 'voice.design', 'asset_ids': [],
                'settings': {'text': 'Hello', 'description': 'Warm low voice', 'seed': 3}})

    def test_inert_approval_native_receipt_and_retry(self):
        row = self.voice()
        self.dispatch.assert_not_called()
        def create(root, body):
            job = video_repertoire.create_job('voice-studio', body)
            return video_repertoire.start_job('voice-studio', job['job_id'])
        with patch.object(voice_studio, 'compile_graph', return_value={}), patch.object(voice_studio, 'create', side_effect=create) as submit:
            self.tasks.approve(self.owner, row['task_id'], self.approval(row))
            first = self.tasks.run(self.owner, row['task_id'], self.approval(row))
            self.assertEqual(first['status'], 'running')
            second = self.tasks.run(self.owner, row['task_id'], self.approval(row))
            self.assertEqual(first['invocation'], second['invocation'])
            submit.assert_called_once()
            job = video_repertoire.read_job('voice-studio', first['invocation']['job_id'])
            job['status'], job['result'] = 'completed', {'outputs': []}
            video_repertoire._atomic_json(video_repertoire.job_path('voice-studio', job['job_id']), job)
            self.assertEqual(self.tasks.poll(self.owner, row['task_id'])['status'], 'completed')
            job['request']['agent_plan']['settings']['seed'] = 9
            video_repertoire._atomic_json(video_repertoire.job_path('voice-studio', job['job_id']), job)
            with self.assertRaises(LedgerConflict):
                self.tasks.poll(self.owner, row['task_id'])

    def test_unknown_settings_and_wrong_image_rejected(self):
        with self.assertRaises(ValueError):
            self.tasks.propose(self.owner, {'tool_id': 'voice.design', 'asset_ids': [],
                'settings': {'text': 'Hi', 'description': 'Warm', 'seed': 1, 'operation': 'training'}})
        with self.assertRaises(ValueError):
            self.tasks.propose(self.owner, {'tool_id': '3d.generate', 'asset_ids': [self.asset['asset_id']],
                'settings': {'preset': 'bounded', 'parameters': {}}})
        self.dispatch.assert_not_called()

    def test_acknowledgement_loss_uses_existing_job(self):
        row = self.voice()
        def create(root, body):
            video_repertoire.create_job('voice-studio', body)
            raise OSError('lost response')
        with patch.object(voice_studio, 'compile_graph', return_value={}), patch.object(voice_studio, 'create', side_effect=create) as submit:
            self.tasks.approve(self.owner, row['task_id'], self.approval(row))
            with self.assertRaises(OSError):
                self.tasks.run(self.owner, row['task_id'], self.approval(row))
            resumed = self.tasks.run(self.owner, row['task_id'], self.approval(row))
            self.assertEqual(resumed['status'], 'running')
            submit.assert_called_once()
        # The context must not leak into manual jobs after an exception.
        manual = video_repertoire.create_job('voice-studio', {'workspace_id': self.owner})
        self.assertNotIn('agent_invocation_id', manual['request'])

    def test_foreign_native_job_cannot_be_claimed(self):
        row = self.voice()
        with native.capture(self.owner, row['plan'], 'test-call', lambda j: None):
            with self.assertRaises(LedgerConflict):
                video_repertoire.create_job('voice-studio', {'workspace_id': 'some-other-project'})

    def test_reference_voice_bytes_are_frozen_until_approval(self):
        transcript = self.root / 'reference.txt'
        transcript.write_text('Exact spoken reference')
        from story_builder.services import audio_catalog
        with patch.object(voice_studio, 'compile_graph', return_value={}), \
                patch.object(audio_catalog, 'voice_audio_path', return_value=(self.original, 'audio/wav')), \
                patch.object(audio_catalog, '_reference_transcript', return_value=transcript):
            row = self.tasks.propose(self.owner, {'tool_id': 'voice.speak', 'asset_ids': [],
                'settings': {'text': 'Hello', 'voice_id': 'test-voice', 'seed': 1}})
            transcript.write_text('A changed reference')
            with self.assertRaises(LedgerConflict):
                self.tasks.approve(self.owner, row['task_id'], self.approval(row))
        self.dispatch.assert_not_called()

    def test_foley_routes_through_existing_guarded_job_without_generation(self):
        from story_builder.services import agent_audio_generation, control_foley
        from story_builder.services.agent_generation_tools import bridge
        self.tasks.native_request = bridge(self.app)
        settings = {'parameters': {'mode': 'text_audio', 'prompt': 'Quiet rustling leaves', 'seed': 7}, 'references': {}}
        with patch.object(control_foley, 'capabilities', return_value={'status': 'available'}):
            row = self.tasks.propose(self.owner, {'tool_id': 'audio.foley', 'asset_ids': [], 'settings': settings})
            self.dispatch.assert_not_called()
            self.tasks.approve(self.owner, row['task_id'], self.approval(row))
            result = self.tasks.run(self.owner, row['task_id'], self.approval(row))
        job = video_repertoire.read_job('control-foley', result['invocation']['job_id'])
        self.assertEqual(job['request']['agent_plan'], row['plan'])
        self.assertEqual(job['request']['settings']['prompt'], 'Quiet rustling leaves')
        self.dispatch.assert_called_once()
        with self.assertRaises(ValueError):
            agent_audio_generation.validate_assets(self.root, self.owner, 'audio.foley', settings, [self.asset])

    def test_timed_speech_standalone_job_freezes_voice_and_rejects_changed_bytes(self):
        from story_builder.services import audio_catalog, audio_tts
        from story_builder.services.agent_generation_tools import bridge
        self.tasks.native_request = bridge(self.app)
        voice = {'id': 'fixture-voice', 'discoverable': True, 'source': 'user', 'relative_path': 'fixture.wav'}
        settings = {'srt_content': '1\n00:00:00,000 --> 00:00:00,200\n[Narrator] Hello\n',
                    'characters': [{'name': 'Narrator', 'reference_voice_id': voice['id']}], 'parameters': {}}
        with patch.object(audio_catalog, 'discover_voices', return_value=[voice]), \
                patch.object(audio_catalog, 'voice_audio_path', return_value=(self.original, 'audio/wav')), \
                patch.object(audio_tts, 'validate_live_nodes'):
            row = self.tasks.propose(self.owner, {'tool_id': 'voice.timed_speech', 'asset_ids': [], 'settings': settings})
            self.dispatch.assert_not_called()
            self.tasks.approve(self.owner, row['task_id'], self.approval(row))
            result = self.tasks.run(self.owner, row['task_id'], self.approval(row))
            job = video_repertoire.read_job('timed-tts', result['invocation']['job_id'])
            self.assertEqual(job['request']['agent_plan'], row['plan'])
            self.dispatch.assert_called_once()
            second = self.tasks.propose(self.owner, {'tool_id': 'voice.timed_speech', 'asset_ids': [], 'settings': settings})
            self.original.write_bytes(self.before + b'changed')
            with self.assertRaises(LedgerConflict):
                self.tasks.approve(self.owner, second['task_id'], self.approval(second))
            self.original.write_bytes(self.before)
