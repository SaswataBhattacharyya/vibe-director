"""CPU continuity acceptance; fixture cleanup owns every record and media file."""
import json
import shutil
import subprocess
import uuid
from unittest.mock import patch

from story_builder.services import agent_continuity, media_library, video_repertoire
from story_builder.services.production_ledger import LedgerConflict
from story_builder.tests.test_agent_tasks import AgentTaskFixture


class AgentContinuityTests(AgentTaskFixture):
    def setUp(self):
        super().setUp()
        if not shutil.which('ffmpeg'):
            self.skipTest('CPU FFmpeg unavailable')
        clip = self.root / 'fixture.mp4'
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-f', 'lavfi',
                        '-i', 'color=blue:s=32x32:r=5:d=0.4', '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                        str(clip)], check=True, capture_output=True, timeout=20)
        self.video = media_library.register_upload(self.root, self.owner, filename='fixture.mp4',
                                                   content=clip.read_bytes(), role='project_video')

    def draft(self):
        return self.tasks.propose(self.owner, {'tool_id': 'video.continuity_last_frame',
            'asset_ids': [self.video['asset_id']], 'settings': {}})

    def test_worker_publishes_verified_frame_and_reuses_it(self):
        from story_builder.services import video_repertoire_worker as worker
        row = self.ready()
        running = self.tasks.run(self.owner, row['task_id'], self.approval(row))
        job_id = running['invocation']['job_id']
        with patch('sys.argv', ['worker', agent_continuity.KIND, job_id]), \
                patch.object(worker.signal, 'signal'), \
                patch.object(worker, 'gpu_workload_lock', side_effect=AssertionError('CPU operation requested GPU')):
            self.assertEqual(worker.main(), 0)
        result = self.tasks.poll(self.owner, row['task_id'])
        self.assertEqual(result['status'], 'completed')
        image = result['outputs'][0]
        path, media_type, _ = media_library.asset_path(self.root, self.owner, image['asset_id'])
        self.assertEqual(media_type, 'image/png')
        self.assertTrue(path.read_bytes().startswith(b'\x89PNG'))
        job = video_repertoire.read_job(agent_continuity.KIND, job_id)
        repeated = agent_continuity.run(self.root, job['request'])
        self.assertEqual(repeated['assets'][0]['asset_id'], image['asset_id'])
        self.tasks.run(self.owner, row['task_id'], self.approval(row))
        self.dispatch.assert_called_once()
        source, _, _ = media_library.asset_path(self.root, self.owner, self.video['asset_id'])
        from story_builder.services.projects import digest
        self.assertEqual(self.video['sha256'], digest(source))

    def test_lost_mapping_recovers_once_and_cancel_uses_correct_kind(self):
        row = self.ready()
        with patch.object(self.tasks, '_map_job', side_effect=RuntimeError('lost mapping')), self.assertRaises(RuntimeError):
            self.tasks.run(self.owner, row['task_id'], self.approval(row))
        recovered = self.tasks.run(self.owner, row['task_id'], self.approval(row))
        self.assertEqual(recovered['job_status'], 'queued')
        self.assertEqual(len(list((self.root / 'services/media/jobs/continuity-frame').glob('*/job.json'))), 1)
        self.assertEqual(self.tasks.cancel(self.owner, row['task_id'])['status'], 'cancelled')

    def test_strict_video_input_and_frozen_hash(self):
        for ids, settings in ((None, {}), ([], {}), ([self.asset['asset_id']], {}),
                              ([self.video['asset_id']], {'quality': 2})):
            with self.assertRaises(ValueError):
                self.tasks.propose(self.owner, {'tool_id': 'video.continuity_last_frame', 'asset_ids': ids, 'settings': settings})
        row = self.ready()
        running = self.tasks.run(self.owner, row['task_id'], self.approval(row))
        job = video_repertoire.read_job(agent_continuity.KIND, running['invocation']['job_id'])
        path, _, _ = media_library.asset_path(self.root, self.owner, self.video['asset_id'])
        path.write_bytes(b'changed')
        with self.assertRaises(ValueError):
            agent_continuity.run(self.root, job['request'])
        job['request']['operation'] = 'extract_mp3'
        stored = self.root / 'services/media/jobs/continuity-frame' / job['job_id'] / 'job.json'
        stored.write_text(json.dumps(job))
        with self.assertRaises(LedgerConflict):
            self.tasks.poll(self.owner, row['task_id'])

    def test_both_chat_surfaces_propose_without_execution(self):
        from unittest.mock import Mock
        from story_builder.services.agent_conversation import AgentConversation
        reason = Mock(return_value={'reply': 'Review the last-frame plan.', 'intent': 'continuity_last_frame', 'quality': 2})
        chat = AgentConversation(self.tasks, reason)
        for surface in ('director', 'editor'):
            result = chat.send(self.owner, {'request_id': str(uuid.uuid4()), 'text': 'Extract its last frame',
                'surface': surface, 'asset_ids': [self.video['asset_id']], 'skill_refs': []})
            row = self.tasks.get(self.owner, result['messages'][-1]['task_id'])
            self.assertEqual(row['plan']['tool_id'], 'video.continuity_last_frame')
            self.assertEqual(row['status'], 'draft')
        self.dispatch.assert_not_called()
