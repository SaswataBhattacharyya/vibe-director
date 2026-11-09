"""Disposable CPU acceptance for exact approvals and cross-store recovery."""
import io
import json
import shutil
import tempfile
import unittest
import wave
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from story_builder.isolated_server import create_app
from story_builder.services import audio_utilities, media_library, projects, video_repertoire
from story_builder.services.agent_tasks import AgentTasks
from story_builder.services.production_ledger import LedgerConflict, LedgerNotFound, ProductionLedger


class AgentTaskFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='vibe-agent-task-')
        self.root = Path(self.temp.name) / 'runtime'
        self.addCleanup(self.cleanup)
        self.app = create_app(data_root=self.root)
        self.tasks = AgentTasks(self.root, ProductionLedger(projects.database_path(self.root, projects.DATABASES[0])))
        self.owner = 'tool-library'
        stream = io.BytesIO()
        with wave.open(stream, 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(8000)
            wav.writeframes(b'\0\0' * 2400)
        self.asset = media_library.register_upload(self.root, self.owner, filename='test.wav', content=stream.getvalue(), role='project_audio')
        self.original = media_library.asset_path(self.root, self.owner, self.asset['asset_id'])[0]
        self.before = self.original.read_bytes()
        self.addCleanup(patch.stopall)
        patch.object(audio_utilities, 'capabilities', return_value={'operations': [{'id': 'extract_mp3', 'status': 'available'}]}).start()
        self.dispatch = patch.object(video_repertoire, 'start_job', side_effect=lambda kind, ident: video_repertoire.read_job(kind, ident)).start()

    def cleanup(self):
        video_repertoire.configure_roots(self.root / 'reset')
        self.temp.cleanup()
        self.assertFalse(Path(self.temp.name).exists(), 'Test-owned records/media survived cleanup')

    def draft(self):
        return self.tasks.propose(self.owner, {'tool_id': 'audio.extract_mp3', 'asset_ids': [self.asset['asset_id']], 'settings': {'quality': 3}})

    @staticmethod
    def approval(row):
        return {'revision': row['current_revision'], 'plan_hash': row['plan_hash']}

    def ready(self):
        row = self.draft()
        self.tasks.approve(self.owner, row['task_id'], self.approval(row))
        return row

    def call(self, method, path, payload=None):
        raw = json.dumps(payload or {}).encode()
        response = []
        env = {'PATH_INFO': path, 'QUERY_STRING': '', 'REQUEST_METHOD': method, 'HTTP_HOST': '127.0.0.1:3020',
               'CONTENT_LENGTH': str(len(raw)), 'wsgi.input': io.BytesIO(raw)}
        result = b''.join(self.app(env, lambda status, headers: response.append(status)))
        return response[0], json.loads(result)


class AgentTaskTests(AgentTaskFixture):
    def test_proposal_is_inert_strict_and_snapshot_owned(self):
        row = self.draft()
        self.dispatch.assert_not_called()
        with self.assertRaises(LedgerConflict):
            self.tasks.run(self.owner, row['task_id'], self.approval(row))
        with self.assertRaises(LedgerConflict):
            self.tasks.approve(self.owner, row['task_id'], {'revision': 2, 'plan_hash': row['plan_hash']})
        with self.assertRaises((ValueError, LedgerNotFound)):
            self.tasks.get('story-aaaaaaaaaaaa', row['task_id'])
        snapshot = projects.sql_snapshot(projects.database_path(self.root, projects.DATABASES[0]), self.owner)
        self.assertIn('agent_tasks', str(snapshot))
        projects.assert_idle(self.root, self.owner)
        path = f'/api/agent/projects/{self.owner}/tasks/{row["task_id"]}'
        self.assertEqual(self.call('GET', path)[0], '200 OK')
        self.assertEqual(self.call('POST', path + '/unknown')[0], '404 Not Found')
        self.assertEqual(self.call('POST', path + '/cancel', {'unknown': True})[0], '400 Bad Request')
        self.assertEqual(self.call('POST', path + '/cancel', {})[1]['status'], 'cancelled')

    def test_http_runtime_unavailable_keeps_recoverable_task(self):
        row = self.ready()
        with patch.object(audio_utilities, 'capabilities', return_value={'operations': [{'id': 'extract_mp3', 'status': 'blocked', 'reason': 'Test runtime unavailable'}]}), patch('story_builder.services.agent_confirmation._desktop_confirm', return_value=True):
            status, result = self.call('POST', f'/api/agent/projects/{self.owner}/tasks/{row["task_id"]}/run', self.approval(row))
        self.assertEqual(status, '503 Service Unavailable')
        self.assertEqual(result['error']['code'], 'agent_runtime_unavailable')
        self.assertEqual(self.tasks.get(self.owner, row['task_id'])['status'], 'recovery_required')
        self.tasks.cancel(self.owner, row['task_id'])
        self.dispatch.assert_not_called()

    def test_parallel_run_allocates_once_and_dispatch_failure_recovers(self):
        row = self.ready()
        def run(_):
            return self.tasks.run(self.owner, row['task_id'], self.approval(row))
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(run, range(2)))
        self.assertEqual(results[0]['invocation']['job_id'], results[1]['invocation']['job_id'])
        self.assertEqual(self.dispatch.call_count, 1)
        with self.assertRaises(ValueError):
            projects.assert_idle(self.root, self.owner)
        other = self.ready()
        with patch.object(video_repertoire, 'start_job', side_effect=RuntimeError('dispatch lost')):
            with self.assertRaises(audio_utilities.WorkerUnavailable):
                self.tasks.run(self.owner, other['task_id'], self.approval(other))
        recovered = self.tasks.run(self.owner, other['task_id'], self.approval(other))
        self.assertEqual(recovered['job_status'], 'queued')
        self.assertEqual(len(list((self.root / 'services/media/jobs/audio-utilities').glob('*/job.json'))), 2)

    def test_lost_creation_ack_and_lost_mapping_reuse_frozen_identity(self):
        for boundary in ('create', 'map'):
            row = self.ready()
            create = video_repertoire.create_job
            def lost(kind, request):
                create(kind, request)
                raise RuntimeError('ack lost')
            target = patch.object(video_repertoire, 'create_job', side_effect=lost) if boundary == 'create' else patch.object(self.tasks, '_map_job', side_effect=RuntimeError('map lost'))
            with target, self.assertRaises(RuntimeError):
                self.tasks.run(self.owner, row['task_id'], self.approval(row))
            recovered = self.tasks.run(self.owner, row['task_id'], self.approval(row))
            self.assertEqual(recovered['job_status'], 'queued')
            self.assertIsNotNone(recovered['invocation']['job_id'])
        self.assertEqual(len(list((self.root / 'services/media/jobs/audio-utilities').glob('*/job.json'))), 2)

    def test_poll_recovers_abrupt_exit_at_each_submission_boundary_without_dispatch(self):
        for boundary in ('before_create', 'before_map', 'after_map'):
            row = self.ready()
            original_map = self.tasks._map_job
            def crash(*args):
                if boundary == 'after_map':
                    original_map(*args)
                raise KeyboardInterrupt('simulated process death')
            target = patch.object(video_repertoire, 'create_job', side_effect=crash) if boundary == 'before_create' else patch.object(self.tasks, '_map_job', side_effect=crash)
            with target, self.assertRaises(KeyboardInterrupt):
                self.tasks.run(self.owner, row['task_id'], self.approval(row))
            before = list((self.root / 'services/media/jobs/audio-utilities').glob('*/job.json'))
            recovered = self.tasks.poll(self.owner, row['task_id'])
            if boundary == 'before_create':
                self.assertEqual(recovered['status'], 'recovery_required')
                self.assertIsNone(recovered['invocation']['job_id'])
            else:
                self.assertEqual(recovered['status'], 'running')
                self.assertIsNotNone(recovered['invocation']['job_id'])
                self.assertEqual(self.tasks.poll(self.owner, row['task_id'])['invocation'], recovered['invocation'])
            self.assertEqual(list((self.root / 'services/media/jobs/audio-utilities').glob('*/job.json')), before)
        self.dispatch.assert_not_called()

    def test_poll_rejects_mismatched_or_duplicate_unmapped_jobs(self):
        row = self.ready()
        with patch.object(self.tasks, '_map_job', side_effect=KeyboardInterrupt), self.assertRaises(KeyboardInterrupt):
            self.tasks.run(self.owner, row['task_id'], self.approval(row))
        path = next((self.root / 'services/media/jobs/audio-utilities').glob('*/job.json'))
        job = json.loads(path.read_text())
        changed = json.loads(path.read_text())
        changed['request']['settings']['quality'] = 9
        path.write_text(json.dumps(changed))
        with self.assertRaises(LedgerConflict):
            self.tasks.poll(self.owner, row['task_id'])
        path.write_text(json.dumps(job))
        duplicate = path.parent.parent / 'duplicate' / 'job.json'
        duplicate.parent.mkdir()
        duplicate.write_text(json.dumps(job))
        with self.assertRaises(LedgerConflict):
            self.tasks.poll(self.owner, row['task_id'])
        self.assertIsNone(self.tasks.get(self.owner, row['task_id'])['invocation']['job_id'])
        self.dispatch.assert_not_called()

    def test_changed_input_and_changed_staged_bytes_never_dispatch(self):
        row = self.ready()
        self.original.write_bytes(self.before + b'changed')
        with self.assertRaises(LedgerConflict):
            self.tasks.run(self.owner, row['task_id'], self.approval(row))
        self.dispatch.assert_not_called()
        self.original.write_bytes(self.before)
        row = self.ready()
        stage = audio_utilities.stage_assets
        def changed(*args):
            inputs = stage(*args)
            (self.root / inputs[0]['relative_path']).write_bytes(b'changed')
            return inputs
        with patch.object(audio_utilities, 'stage_assets', side_effect=changed), self.assertRaises(ValueError):
            self.tasks.run(self.owner, row['task_id'], self.approval(row))
        self.dispatch.assert_not_called()
        self.assertEqual(list((self.root / 'services/media/jobs/audio-utilities').glob('*/job.json')), [])

    def test_worker_rejects_changed_frozen_inputs_and_recovery_rejects_changed_settings(self):
        row = self.ready()
        run = self.tasks.run(self.owner, row['task_id'], self.approval(row))
        job_id = run['invocation']['job_id']
        job = video_repertoire.read_job('audio-utilities', job_id)
        (self.root / job['request']['inputs'][0]['relative_path']).write_bytes(b'changed after submission')
        with self.assertRaises(audio_utilities.AudioUtilityError):
            audio_utilities.run_job(job, data_root=self.root, progress=lambda _: None)
        job['request']['settings']['quality'] = 9
        (self.root / 'services/media/jobs/audio-utilities' / job_id / 'job.json').write_text(json.dumps(job))
        with self.assertRaises(LedgerConflict):
            self.tasks.poll(self.owner, row['task_id'])

    def test_crash_after_staging_blocks_duplicate_allocation_but_can_cancel(self):
        row = self.ready()
        class Interrupted(BaseException):
            pass
        with patch.object(video_repertoire, 'create_job', side_effect=Interrupted), self.assertRaises(Interrupted):
            self.tasks.run(self.owner, row['task_id'], self.approval(row))
        with self.assertRaisesRegex(LedgerConflict, 'Unclaimed staged input'):
            self.tasks.run(self.owner, row['task_id'], self.approval(row))
        self.assertEqual(self.tasks.get(self.owner, row['task_id'])['status'], 'recovery_required')
        self.assertEqual(self.tasks.cancel(self.owner, row['task_id'])['status'], 'cancelled')
        self.dispatch.assert_not_called()
        self.assertEqual(self.original.read_bytes(), self.before)

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'CPU FFmpeg required')
    def test_cpu_output_is_verified_playable_and_original_preserved(self):
        row = self.ready()
        run = self.tasks.run(self.owner, row['task_id'], self.approval(row))
        job_id = run['invocation']['job_id']
        job = video_repertoire.read_job('audio-utilities', job_id)
        outputs = audio_utilities.run_job(job, data_root=self.root, progress=lambda _: None)
        job.update(status='completed', result={'workspace_id': self.owner, 'assets': outputs})
        (self.root / 'services/media/jobs/audio-utilities' / job_id / 'job.json').write_text(json.dumps(job))
        result = self.tasks.poll(self.owner, row['task_id'])
        self.assertEqual(result['status'], 'completed')
        self.assertTrue(result['outputs'][0]['content_url'].startswith('/api/media/tool-library/'))
        self.assertEqual(self.original.read_bytes(), self.before)
        output_path = media_library.asset_path(self.root, self.owner, outputs[0]['asset_id'])[0]
        import subprocess
        probe = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_name', '-of', 'json', str(output_path)], check=True, capture_output=True, text=True)
        self.assertEqual(json.loads(probe.stdout)['streams'][0]['codec_name'], 'mp3')
        output_path.write_bytes(b'corrupted')
        with self.assertRaises(LedgerConflict):
            self.tasks.poll(self.owner, row['task_id'])

    def test_new_revision_requires_fresh_approval_and_cancel_never_restarts(self):
        row = self.ready()
        revised = self.tasks.revise(self.owner, row['task_id'], {
            **self.approval(row), 'proposal': {'tool_id': 'audio.extract_mp3',
            'asset_ids': [self.asset['asset_id']], 'settings': {'quality': 7}}})
        self.assertEqual(revised['status'], 'draft')
        with self.assertRaises(LedgerConflict):
            self.tasks.run(self.owner, row['task_id'], self.approval(row))
        with self.assertRaises(LedgerConflict):
            self.tasks.run(self.owner, row['task_id'], self.approval(revised))
        self.tasks.approve(self.owner, row['task_id'], self.approval(revised))
        running = self.tasks.run(self.owner, row['task_id'], self.approval(revised))
        cancelled = self.tasks.cancel(self.owner, row['task_id'])
        self.assertEqual(cancelled['status'], 'cancelled')
        self.tasks.run(self.owner, row['task_id'], self.approval(revised))
        self.assertEqual(self.dispatch.call_count, 1)

    def test_draft_task_and_approval_survive_moved_project_checkpoint(self):
        from story_builder.services.story_authoring import StoryAuthoring
        story = StoryAuthoring(self.tasks.ledger, data_root=self.root)
        folder = Path(self.temp.name) / 'test-projects'
        folder.mkdir()
        project = projects.handle(self.root, story, {'REQUEST_METHOD': 'POST', 'PATH_INFO': '/api/projects/new'},
            None, lambda _: {'title': 'Task film', 'folder': str(folder)}, lambda _, status, data: data)
        owner = project['workspace_id']
        asset = media_library.register_upload(self.root, owner, filename='source.wav', content=self.before, role='project_audio')
        row = self.tasks.propose(owner, {'tool_id': 'audio.extract_mp3', 'asset_ids': [asset['asset_id']], 'settings': {}})
        self.tasks.approve(owner, row['task_id'], self.approval(row))
        from story_builder.services import agent_knowledge
        agent_knowledge.save(self.root, self.tasks.ledger, owner, {'revision': 0, 'content': 'Keep the base room layout.'})
        saved = Path(project['folder'])
        projects.save(self.root, owner, saved, {})
        moved = Path(self.temp.name) / 'moved-film'
        saved.rename(moved)
        fresh = Path(self.temp.name) / 'fresh-runtime'
        create_app(data_root=fresh)
        restored = projects.open_project(fresh, moved)
        tasks = AgentTasks(fresh, ProductionLedger(projects.database_path(fresh, projects.DATABASES[0])))
        recovered = tasks.get(owner, row['task_id'])
        self.assertEqual(restored['workspace_id'], owner)
        self.assertEqual(recovered['plan_hash'], row['plan_hash'])
        self.assertEqual(recovered['status'], 'approved')
        self.assertEqual(agent_knowledge.read(fresh, tasks.ledger, owner)['content'], 'Keep the base room layout.')
        self.assertEqual(tasks._assets(owner, [asset['asset_id']])[0]['sha256'], asset['sha256'])

class AgentAudioProcessingTests(AgentTaskFixture):
    def test_audio_adapters_freeze_settings_recover_and_verify_registered_wav(self):
        for operation, settings in [('noise_cleanup', {'model': 'dns64', 'dry': .25}),
                                    ('demucs_stems', {'stems': 2, 'device': 'cpu'})]:
            with self.subTest(operation=operation), patch.object(audio_utilities, 'capabilities', return_value={
                    'operations': [{'id': operation, 'status': 'available'}]}):
                row = self.tasks.propose(self.owner, {'tool_id': 'audio.' + operation,
                    'asset_ids': [self.asset['asset_id']], 'settings': settings})
                self.tasks.approve(self.owner, row['task_id'], self.approval(row))
                started = self.tasks.run(self.owner, row['task_id'], self.approval(row))
                self.assertEqual(started['invocation'], self.tasks.run(self.owner, row['task_id'], self.approval(row))['invocation'])
                job = video_repertoire.read_job('audio-utilities', started['invocation']['job_id'])
                self.assertEqual(job['request']['operation'], operation)
                self.assertEqual(job['request']['settings'], settings)
                # Mock worker completion with registered CPU fixture audio; never run a model.
                job.update(status='completed', result={'workspace_id': self.owner, 'assets': [self.asset]})
                video_repertoire.job_path('audio-utilities', job['job_id']).write_text(json.dumps(job))
                self.assertEqual(self.tasks.poll(self.owner, row['task_id'])['status'], 'completed')
                job['request']['operation'] = 'extract_mp3'
                video_repertoire.job_path('audio-utilities', job['job_id']).write_text(json.dumps(job))
                with self.assertRaises(LedgerConflict):
                    self.tasks.poll(self.owner, row['task_id'])
        self.assertEqual(self.original.read_bytes(), self.before)

    def test_director_stems_reject_gpu_and_unknown_settings(self):
        for settings in ({'device': 'cuda'}, {'command': 'anything'}):
            with self.assertRaises(ValueError):
                self.tasks.propose(self.owner, {'tool_id': 'audio.demucs_stems',
                    'asset_ids': [self.asset['asset_id']], 'settings': settings})
        self.dispatch.assert_not_called()
