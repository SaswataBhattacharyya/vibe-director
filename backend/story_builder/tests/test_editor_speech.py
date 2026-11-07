"""Disposable CPU media, correlated evidence, retained cuts and render clearance."""
import io
import json
import os
import subprocess
import unittest
from unittest.mock import patch

from story_builder.services import agent_transcription, editor_speech, media_library, vibe_editor, vibe_editor_render, video_repertoire
from story_builder.services.production_ledger import LedgerConflict
from story_builder.tests.test_agent_tasks import AgentTaskFixture


class EditorSpeechTests(AgentTaskFixture):
    def setUp(self):
        super().setUp()
        path = self.root / 'fixture.mp4'
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'color=c=blue:s=320x180:r=24:d=3',
                        '-f', 'lavfi', '-i', 'sine=frequency=440:duration=3', '-c:v', 'libx264',
                        '-threads', '1', '-c:a', 'aac', '-shortest', str(path)], check=True)
        self.video = media_library.register_upload(self.root, self.owner, filename='speech.mp4',
                    content=path.read_bytes(), role='project_video')
        self.editor = vibe_editor.add_project(self.root, {'workspace_id': self.owner, 'name': 'Cuts'})
        self.editor = vibe_editor.update_project(self.root, self.editor['id'], {'selection': [
            {'asset_id': self.video['asset_id'], 'start': 0, 'end': 3}]})
        with vibe_editor.state(self.root) as data:
            p = vibe_editor.project(data, self.editor['id'])
            p['brief'] = {'summary': 'Remove reviewed speech only.', 'questions': []}
        self.task = self.tasks.propose(self.owner, {'tool_id': 'audio.transcribe',
                    'asset_ids': [self.video['asset_id']], 'settings': {}})
        self.tasks.approve(self.owner, self.task['task_id'], self.approval(self.task))
        with patch.object(agent_transcription, 'capability', return_value={'execution_enabled': True}):
            row = self.tasks.run(self.owner, self.task['task_id'], self.approval(self.task))
        self.job_path = video_repertoire.job_path(agent_transcription.KIND, row['invocation']['job_id'])
        job = json.loads(self.job_path.read_text())
        segments = [{'start': start, 'end': end, 'text': text, 'avg_logprob': -.2,
                     'no_speech_prob': .01, 'words': []} for start, end, text in
                    [(0, .5, 'keep intro'), (1, 1.5, 'review mistake'), (2, 2.5, 'keep ending')]]
        transcript = {'asset_id': self.video['asset_id'], 'sha256': self.video['sha256'],
            'scope': 'whole_source', 'device': 'cpu', 'model': 'faster-whisper-large-v3',
            'duration_seconds': 3, 'language': 'en', 'language_probability': .99, 'segments': segments}
        job.update(status='completed', result={'workspace_id': self.owner, 'transcript': transcript})
        self.job_path.write_text(json.dumps(job))

    def proposal(self, **changes):
        return {'revision': self.editor['revision'], 'task_id': self.task['task_id'],
                'segment_indices': [1], **changes}

    def test_review_creates_exact_retained_ranges_then_freezes_provenance_only_on_approval(self):
        evidence = editor_speech.evidence(self.root, self.tasks, self.editor['id'])
        self.assertEqual(len(evidence['sources'][0]['transcript']['segments']), 3)
        count = self.dispatch.call_count
        p = editor_speech.propose(self.root, self.tasks, self.editor['id'], self.proposal())
        self.assertEqual(self.dispatch.call_count, count, 'Saving cuts started rendering')
        self.assertEqual([(r['start'], r['end']) for r in p['pending']['value']['clips']], [(0, 1), (1.5, 3)])
        self.assertIsNone(p['pending']['value']['audio'], 'A replacement soundtrack would mute original speech')
        self.assertEqual(p['selection'], self.editor['selection'])
        self.assertEqual(p['pending']['evidence']['sha256'], self.video['sha256'])
        reloaded = vibe_editor.snapshot(self.root)['projects'][0]
        self.assertEqual(reloaded['pending'], p['pending'])
        with self.assertRaisesRegex(ValueError, 'revision changed'):
            editor_speech.propose(self.root, self.tasks, p['id'], self.proposal())
        vibe_editor.command(self.root, p['id'], {'action': 'approve', 'revision': p['revision']})
        reloaded = vibe_editor.snapshot(self.root)['projects'][0]
        job = video_repertoire.read_job('vibe-editor', reloaded['job_id'])
        self.assertEqual(job['request']['operation'], 'render')
        self.assertEqual(job['request']['review_evidence'], p['pending']['evidence'])
        self.assertEqual(reloaded['revisions'][-1]['evidence'], p['pending']['evidence'])

    def test_existing_effects_captions_and_dimensions_survive_source_cut(self):
        plan = {'width': 640, 'height': 360, 'fps': 30, 'audio': None, 'clips': [{
            **self.editor['selection'][0], 'caption': 'Preserve me', 'effect': {'preset': 'vhs', 'strength': .4}}]}
        p = vibe_editor.propose_plan(self.root, self.editor['id'], {'revision': self.editor['revision'], 'plan': plan})
        result = editor_speech.propose(self.root, self.tasks, p['id'], self.proposal(revision=p['revision']))
        proposed = result['pending']['value']
        self.assertEqual((proposed['width'], proposed['height'], proposed['fps']), (640, 360, 30))
        self.assertTrue(all(c['caption'] == 'Preserve me' and c['effect']['preset'] == 'vhs' for c in proposed['clips']))

    def test_retimed_or_replacement_soundtrack_plans_require_manual_alignment(self):
        self.editor = vibe_editor.update_project(self.root, self.editor['id'], {'selection': [
            *self.editor['selection'], {'asset_id': self.asset['asset_id'], 'start': 0, 'end': .2}]})
        for settings in ({'speed': {'start': 2, 'end': 2}}, {'soundtrack': True}):
            plan = {'clips': [{**self.editor['selection'][0], **({} if 'soundtrack' in settings else settings)}],
                    'audio': {'asset_id': self.asset['asset_id'], 'start': 0, 'end': .2} if 'soundtrack' in settings else None}
            current = vibe_editor.snapshot(self.root)['projects'][0]
            p = vibe_editor.propose_plan(self.root, current['id'], {'revision': current['revision'], 'plan': plan})
            with self.assertRaisesRegex(ValueError, 'realign|normal-speed'):
                editor_speech.propose(self.root, self.tasks, p['id'], self.proposal(revision=p['revision']))

    def test_corrupt_foreign_changed_or_unselected_evidence_and_invalid_cuts_rejected(self):
        for indices in ([], [True], [-1], [1, 1], [99]):
            with self.subTest(indices=indices), self.assertRaises(ValueError):
                editor_speech.propose(self.root, self.tasks, self.editor['id'], self.proposal(segment_indices=indices))
        with self.assertRaises((ValueError, LedgerConflict)):
            self.tasks.transcript('foreign-project', self.task['task_id'])
        original = self.job_path.read_text()
        job = json.loads(original); job['request']['agent_invocation_id'] = 'tampered'
        self.job_path.write_text(json.dumps(job))
        with self.assertRaises(LedgerConflict):
            editor_speech.evidence(self.root, self.tasks, self.editor['id'])
        self.job_path.write_text(original)
        self.editor = vibe_editor.update_project(self.root, self.editor['id'], {'selection': [
            {'asset_id': self.video['asset_id'], 'start': 0, 'end': .5}]})
        with self.assertRaisesRegex(ValueError, 'outside'):
            editor_speech.propose(self.root, self.tasks, self.editor['id'], self.proposal())
        source = media_library.asset_path(self.root, self.owner, self.video['asset_id'])[0]
        source.write_bytes(source.read_bytes() + b'changed')
        with self.assertRaises(LedgerConflict):
            self.tasks.transcript(self.owner, self.task['task_id'])
        self.assertEqual(self.original.read_bytes(), self.before, 'Unrelated original was modified')

    def test_interval_union_preserves_gaps_other_assets_and_repeated_occurrences(self):
        ranges = [{'asset_id': 'a', 'start': 0, 'end': 10}, {'asset_id': 'b', 'start': 2, 'end': 5},
                  {'asset_id': 'a', 'start': 2, 'end': 8}]
        result = editor_speech.retained_ranges(ranges, 'a', [(3, 4), (4, 5), (3.5, 6), (8, 9)])
        self.assertEqual([(r['asset_id'], r['start'], r['end']) for r in result],
            [('a', 0, 3), ('a', 6, 8), ('a', 9, 10), ('b', 2, 5), ('a', 2, 3), ('a', 6, 8)])

    def test_http_evidence_and_proposal_are_inert_and_require_json(self):
        prefix = f'/api/editor/projects/{self.editor["id"]}'
        self.assertEqual(self.call('GET', prefix + '/speech')[0], '200 OK')
        self.assertEqual(self.call('POST', prefix + '/speech-cuts', self.proposal())[0], '400 Bad Request')
        raw = json.dumps(self.proposal()).encode()
        env = {'PATH_INFO': prefix + '/speech-cuts', 'REQUEST_METHOD': 'POST', 'CONTENT_TYPE': 'application/json',
               'CONTENT_LENGTH': str(len(raw)), 'wsgi.input': io.BytesIO(raw)}
        status = []
        response = json.loads(b''.join(self.app(env, lambda s, h: status.append(s))))
        self.assertEqual(status, ['200 OK'], response)
        self.assertEqual(response['pending']['kind'], 'plan')

    def test_missing_render_audio_is_not_published(self):
        p = editor_speech.propose(self.root, self.tasks, self.editor['id'], self.proposal())
        vibe_editor.command(self.root, p['id'], {'action': 'approve', 'revision': p['revision']})
        p = vibe_editor.snapshot(self.root)['projects'][0]
        job = video_repertoire.read_job('vibe-editor', p['job_id'])
        probe = media_library._probe
        def missing_audio(path, kind):
            if path.name == 'final.mp4':
                return {'duration_seconds': 2.5, 'width': 1280, 'height': 720, 'streams': ['video']}
            return probe(path, kind)
        with patch.object(vibe_editor_render, 'capability', return_value={'ready': True}), \
             patch.object(vibe_editor_render, '_run'), patch.object(media_library, '_probe', side_effect=missing_audio), \
             patch.object(media_library, 'register_generated_video') as publish:
            with self.assertRaisesRegex(ValueError, 'lost the approved audio'):
                vibe_editor_render.render(self.root, p['job_id'], job['request'], lambda *_: None)
            publish.assert_not_called()
        self.assertNotIn('output', vibe_editor.snapshot(self.root)['projects'][0])

    @unittest.skipUnless(os.environ.get('VIBE_TEST_CPU_RENDER') == '1', 'Optional installed CPU renderer acceptance')
    def test_real_cpu_render_preserves_picture_and_original_sound(self):
        p = vibe_editor.propose_plan(self.root, self.editor['id'], {'revision': self.editor['revision'],
            'plan': {'width': 320, 'height': 180, 'fps': 24, 'audio': None, 'clips': self.editor['selection']}})
        p = editor_speech.propose(self.root, self.tasks, p['id'], self.proposal(revision=p['revision']))
        vibe_editor.command(self.root, p['id'], {'action': 'approve', 'revision': p['revision']})
        p = vibe_editor.snapshot(self.root)['projects'][0]
        job = video_repertoire.read_job('vibe-editor', p['job_id'])
        result = vibe_editor_render.render(self.root, p['job_id'], job['request'], lambda *_: None)
        output = media_library.asset_path(self.root, self.owner, result['asset']['asset_id'])[0]
        self.assertAlmostEqual(result['asset']['media']['duration_seconds'], 2.5, delta=.1)
        self.assertEqual(result['asset']['media']['streams'], ['audio', 'video'])
        for position in (.5, 1.5, 2.2):
            pixel = subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(position), '-i', str(output),
                '-frames:v', '1', '-vf', 'scale=1:1', '-pix_fmt', 'rgb24', '-f', 'rawvideo', '-'],
                check=True, capture_output=True).stdout
            self.assertEqual(len(pixel), 3)
            self.assertGreater(pixel[2], 200, 'Decoded output lost the blue source picture')
            self.assertLess(max(pixel[:2]), 30)
        audio = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(output), '-vn', '-ac', '1',
            '-ar', '8000', '-f', 's16le', '-'], check=True, capture_output=True).stdout
        import array
        samples = array.array('h', audio)
        self.assertGreater(sum(n*n for n in samples) / len(samples), 10000, 'Original sound became silent')
