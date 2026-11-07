"""Mocked CPU analyzer contract; fixtures clean media and records even on failure."""
import json
import uuid
from pathlib import Path
from unittest.mock import Mock, patch

from story_builder.services import agent_transcription as speech, video_repertoire
from story_builder.services import projects, video_repertoire_worker as worker, vibe_editor, agent_editor
from story_builder.services.agent_conversation import AgentConversation, editor_instruction
from story_builder.tests.test_agent_tasks import AgentTaskFixture


class TranscriptionTests(AgentTaskFixture):
    def evidence(self):
        return {'asset_id': self.asset['asset_id'], 'sha256': self.asset['sha256'], 'scope': 'whole_source',
                'device': 'cpu', 'model': 'faster-whisper-large-v3', 'duration_seconds': 12,
                'language': 'en', 'language_probability': .98,
                'segments': [{'start': 6.5, 'end': 8, 'text': 'review this speech', 'avg_logprob': -.4,
                    'no_speech_prob': .05, 'words': [{'start': 6.5, 'end': 7, 'text': 'review', 'probability': .9}]}]}

    def draft_transcript(self):
        return self.tasks.propose(self.owner, {'tool_id': 'audio.transcribe',
            'asset_ids': [self.asset['asset_id']], 'settings': {}})

    def test_approved_job_recovers_and_exposes_verified_source_timestamps(self):
        row = self.draft_transcript()
        self.tasks.approve(self.owner, row['task_id'], self.approval(row))
        with patch.object(speech, 'capability', return_value={'execution_enabled': True}):
            started = self.tasks.run(self.owner, row['task_id'], self.approval(row))
            again = self.tasks.run(self.owner, row['task_id'], self.approval(row))
        self.assertEqual(started['invocation'], again['invocation'])
        self.assertEqual(self.dispatch.call_count, 1)
        job = video_repertoire.read_job(speech.KIND, started['invocation']['job_id'])
        job.update(status='completed', result={'workspace_id': self.owner, 'transcript': self.evidence()})
        video_repertoire.job_path(speech.KIND, job['job_id']).write_text(json.dumps(job))
        done = self.tasks.poll(self.owner, row['task_id'])
        self.assertIn('6.500–8.000s', done['report'])
        self.assertIn('No cuts or render have been approved', done['report'])
        self.assertEqual(done['outputs'], [])
        reason = Mock(return_value={'reply': 'Review the timed speech before cutting.', 'intent': 'discuss', 'quality': 2})
        chat = AgentConversation(self.tasks, reason)
        with patch('story_builder.services.agent_tools.tools', return_value={'tools': []}):
            chat.send(self.owner, {'request_id': str(uuid.uuid4()), 'text': 'Where should I review?',
                'asset_ids': [self.asset['asset_id']], 'skill_refs': [], 'surface': 'director'})
        prompt = reason.call_args.kwargs['prompt']
        context = json.loads(prompt[prompt.index('\n{') + 1:])['context']
        self.assertIn('6.500–8.000s', context['speech_evidence'][0]['report'])
        self.assertEqual(context['speech_evidence'][0]['job_id'], job['job_id'])
        self.assertEqual(self.tasks.speech_evidence(self.owner, [{**self.asset, 'sha256': 'new bytes'}]), [])
        self.assertEqual(self.tasks.speech_evidence(self.owner, []), [])
        editor = vibe_editor.add_project(self.root, {'workspace_id': self.owner, 'name': 'Speech review'})
        editor = vibe_editor.update_project(self.root, editor['id'], {'selection': [
            {'asset_id': self.asset['asset_id'], 'start': 0, 'end': .3}]})
        reason.return_value = {'reply': 'I already cut it.', 'intent': 'editor.prepare_brief', 'quality': 2}
        with patch('story_builder.services.agent_tools.tools', return_value={'tools': []}):
            message = chat.send(self.owner, {'request_id': str(uuid.uuid4()), 'text': 'Prepare a reviewed edit.',
                'asset_ids': [], 'skill_refs': [], 'surface': 'editor', 'target': {'version': 1,
                    'editor_session_id': editor['id'], 'expected_revision': editor['revision'],
                    'selected_ranges': agent_editor.ranges(editor['selection'])}})['messages'][-1]
        brief = self.tasks.get(self.owner, message['task_id'])
        self.assertIn('6.500–8.000s', brief['plan']['settings']['instruction'])
        self.assertIn(job['job_id'], brief['plan']['settings']['instruction'])
        self.assertIn('No cuts or render', message['reply'])
        self.assertEqual(brief['plan']['settings']['target']['selected_ranges'][0]['end'], .3)
        self.assertEqual(self.dispatch.call_count, 1, 'Brief proposal started work without approval')
        job['result']['transcript']['sha256'] = '0' * 64
        video_repertoire.job_path(speech.KIND, job['job_id']).write_text(json.dumps(job))
        with self.assertRaises(ValueError):
            self.tasks.poll(self.owner, row['task_id'])
        with self.assertRaises(ValueError):
            self.tasks.speech_evidence(self.owner, [self.asset])

    def test_bad_evidence_and_nonempty_settings_rejected(self):
        for update in ({'duration_seconds': float('nan')}, {'scope': 'preview'}, {'sha256': 'changed'},
                       {'segments': [{'start': 0, 'end': 99, 'text': 'invented'}]}):
            with self.subTest(update=update), self.assertRaises(ValueError):
                speech.validate({**self.evidence(), **update}, self.asset)
        with self.assertRaises(ValueError):
            self.tasks.propose(self.owner, {'tool_id': 'audio.transcribe',
                'asset_ids': [self.asset['asset_id']], 'settings': {'command': 'anything'}})
        self.dispatch.assert_not_called()
        excerpt = {'task_id': 'test', 'report': 'x' * 16000, 'truncated': False}
        instruction = editor_instruction('Preserve the good speech.', [excerpt] * 3)
        self.assertLessEqual(len(instruction), 12000)
        self.assertIn('"truncated": true', instruction)
        with self.assertRaisesRegex(ValueError, 'Shorten'):
            editor_instruction('x' * 11990, [excerpt])

    def test_worker_dispatch_persists_result_without_gpu_admission(self):
        request = {'workspace_id': self.owner, 'operation': 'transcribe', 'settings': {}, 'inputs': [self.asset]}
        job = video_repertoire.create_job(speech.KIND, request)
        with self.assertRaisesRegex(ValueError, 'active media job'):
            projects.assert_idle(self.root, self.owner)
        with patch.object(worker.sys, 'argv', ['worker', speech.KIND, job['job_id']]), \
             patch.object(worker.signal, 'signal'), \
             patch.object(worker, 'gpu_workload_lock', side_effect=AssertionError('CPU job requested GPU admission')), \
             patch.object(speech, 'run', return_value={'workspace_id': self.owner, 'transcript': self.evidence()}) as run:
            self.assertEqual(worker.main(), 0)
        run.assert_called_once_with(self.root, job['job_id'], request)
        saved = video_repertoire.read_job(speech.KIND, job['job_id'])
        self.assertEqual(saved['status'], 'completed')
        self.assertEqual(saved['result']['transcript'], self.evidence())

    def test_worker_uses_whole_source_offline_cpu_and_cleans_staging_on_failure(self):
        request = {'workspace_id': self.owner, 'operation': 'transcribe', 'settings': {},
                   'inputs': [self.asset]}
        folders = []
        def command(args, **kwargs):
            if args[0] == 'ffmpeg':
                target = Path(args[-1]); folders.append(target.parent); target.write_bytes(b'test wav')
                self.assertNotIn('-t', args)
                self.assertNotEqual(args[args.index('-i') + 1], args[-1])
                return Mock(returncode=0)
            if args[0] == 'ffprobe':
                return Mock(stdout='12')
            self.assertNotIn('--gpus', args)
            self.assertIn('none', args)
            self.assertIn('--read-only', args)
            self.assertIn('HF_HUB_OFFLINE=1', args)
            return Mock(returncode=1, stderr='test analyzer failure')
        with patch.object(speech, 'capability', return_value={'execution_enabled': True}), \
             patch.object(speech.subprocess, 'run', side_effect=command), \
             patch.object(video_repertoire, '_stop_job_containers') as stop:
            with self.assertRaisesRegex(RuntimeError, 'test analyzer failure'):
                speech.run(self.root, 'agent-transcription-test', request)
        stop.assert_called_once_with('agent-transcription-test', speech.LABEL)
        self.assertTrue(folders)
        self.assertTrue(all(not folder.exists() for folder in folders), 'Analyzer staging survived failure')
        self.assertEqual(self.original.read_bytes(), self.before)

    def test_unavailable_runtime_never_dispatches_and_cancel_checks_owned_containers(self):
        row = self.draft_transcript()
        self.tasks.approve(self.owner, row['task_id'], self.approval(row))
        with patch.object(speech, 'capability', return_value={'execution_enabled': False, 'reason': 'missing image'}):
            with self.assertRaisesRegex(RuntimeError, 'missing image'):
                self.tasks.run(self.owner, row['task_id'], self.approval(row))
        self.dispatch.assert_not_called()
        self.assertEqual(self.tasks.get(self.owner, row['task_id'])['status'], 'recovery_required')
        job = video_repertoire.create_job(speech.KIND, {'workspace_id': self.owner})
        job.update(status='running', pid=999999999)
        video_repertoire.job_path(speech.KIND, job['job_id']).write_text(json.dumps(job))
        with patch.object(video_repertoire, '_stop_job_containers') as stop, \
             patch.object(video_repertoire, 'read_job', return_value=job), \
             patch.object(video_repertoire, '_pid_alive', return_value=False):
            self.assertEqual(video_repertoire.cancel_job(speech.KIND, job['job_id'])['status'], 'cancelled')
        self.assertEqual(stop.call_count, 2)
        for call in stop.call_args_list:
            self.assertEqual(call.args, (job['job_id'], speech.LABEL))
