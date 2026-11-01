"""CPU-only publication and recovery checks; never submits a render."""
import json
import tempfile
import unittest
import wave
from unittest.mock import patch
from pathlib import Path
from story_builder.services import output_destinations as out, media_library as library, video_repertoire
from story_builder.services.storage_paths import generated_root, shared_file


class OutputDestinationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'data'
        self.root.mkdir()
        self.folder = Path(self.temp.name) / 'chosen folder'
        self.folder.mkdir()
        self.choice = {'mode': 'folder', **out.grant(self.root, str(self.folder))}

    def test_job_freezes_choice_and_missing_folder_never_falls_back(self):
        out.preference(self.root, 'audio-effects', 'tool-library', self.choice)
        request = out.freeze(self.root, 'audio-effects', {'workspace_id': 'tool-library'})
        out.preference(self.root, 'audio-effects', 'tool-library', {'mode': 'default'})
        self.assertEqual(request['output_destination']['path'], str(self.folder))
        self.folder.rmdir()
        with self.assertRaises(ValueError): out.target_root(self.root, request['output_destination'])
        self.assertFalse((self.root / 'audio_studio').exists())

    def test_no_clobber_and_symlink_preserve_source(self):
        source = self.root / 'source'; source.write_bytes(b'original')
        target = self.folder / 'same'; target.write_bytes(b'other')
        with self.assertRaises(ValueError): out.copy_verified(source, target)
        self.assertEqual(source.read_bytes(), b'original')
        self.assertEqual(target.read_bytes(), b'other')
        (self.folder / 'link').symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError): out.copy_verified(source, self.folder / 'link' / 'new' / 'bad')
        self.assertFalse((self.root / 'new').exists())

    def test_audio_publication_preserves_id_preview_and_one_copy(self):
        source = generated_root(self.root, 'tool-library') / 'record.wav'
        source.parent.mkdir(parents=True)
        with wave.open(str(source), 'wb') as stream:
            stream.setparams((1, 2, 8000, 0, 'NONE', 'not compressed'))
            stream.writeframes(b'\0\0' * 800)
        asset = library.register_generated_audio(self.root, 'tool-library', 'record.wav', {'job_id': 'job-one'})
        job = {'kind': 'audio-effects', 'job_id': 'job-one', 'request': {'output_destination': self.choice}}
        saved = out.finalize(self.root, job, {'asset': asset})['asset']
        self.assertEqual(saved['asset_id'], asset['asset_id'])
        self.assertEqual(saved['content_url'], asset['content_url'])
        path, _, _ = library.asset_path(self.root, 'tool-library', asset['asset_id'])
        self.assertTrue(path.is_relative_to(self.folder))
        self.assertTrue(path.is_file())
        self.assertFalse(source.exists())
        self.assertEqual(out.finalize(self.root, job, {'asset': saved})['asset']['asset_id'], saved['asset_id'])
        self.assertFalse((self.root / 'projects').exists())
        self.assertEqual(library.browse_catalogue(self.root, 'tool-library', kinds='audio')['total'], 1)

    def test_run_publication_resolves_artifacts_and_keeps_original_on_collision(self):
        video_repertoire.configure_roots(self.root)
        run = self.root / 'video_repertoire/runs/run-one'
        (run / 'frames').mkdir(parents=True)
        (run / 'manifest.json').write_text('{}')
        (run / 'frames/one.png').write_bytes(b'frame')
        job = {'kind': 'analysis', 'job_id': 'job-analysis', 'request': {'output_destination': self.choice}}
        out.finalize(self.root, job, {'audio_analysis': [{'run_id': 'run-one'}]})
        self.assertFalse(run.exists())
        logical = run / 'frames/one.png'
        resolved = video_repertoire.safe_path(logical, self.root / 'video_repertoire')
        self.assertEqual(resolved.read_bytes(), b'frame')
        self.assertEqual(shared_file(self.root, {'store':'repertoire','path':'runs/run-one/frames/one.png'}), resolved)
        with self.assertRaises(ValueError): out.resolve_run_path(self.root, run / '../elsewhere')
        (run / 'frames').mkdir(parents=True)
        (run / 'manifest.json').write_text('{}')
        with self.assertRaises(ValueError): out.finalize(self.root, job, {'audio_analysis':[{'run_id':'run-one'}]})
        self.assertTrue(run.is_dir())

    def test_symlinked_generated_directory_rejected(self):
        parent = generated_root(self.root, 'tool-library').parent
        parent.mkdir(parents=True)
        (parent/'generated').symlink_to(self.folder, target_is_directory=True)
        with self.assertRaises(ValueError): generated_root(self.root, 'tool-library')

    def test_missing_folder_can_be_relocated_only_with_matching_registered_content(self):
        out.preference(self.root, 'analysis', 'tool-library', self.choice)
        video_repertoire.configure_roots(self.root)
        run = self.root / 'video_repertoire/runs/run-relink'
        run.mkdir(parents=True)
        (run / 'manifest.json').write_text('{"kept":true}')
        job = {'kind':'analysis', 'job_id':'job-relink', 'request':{'output_destination':self.choice}}
        out.finalize(self.root, job, {'audio_analysis':[{'run_id':'run-relink'}]})
        moved = self.folder.with_name('moved folder')
        self.folder.rename(moved)
        self.assertFalse(out.preference(self.root, 'analysis', 'tool-library', allow_unavailable=True)['available'])
        wrong = self.root / 'wrong'; wrong.mkdir()
        with self.assertRaisesRegex(ValueError, 'matching content'):
            out.locate_saved_folder(self.root, 'analysis', 'tool-library', out.grant(self.root, str(wrong))['grant'])
        with self.assertRaises(ValueError): out.resolve_run_path(self.root, run / 'manifest.json')
        restored = out.locate_saved_folder(self.root, 'analysis', 'tool-library', out.grant(self.root, str(moved))['grant'])
        self.assertEqual(restored['grant'], self.choice['grant'])
        self.assertEqual(out.resolve_run_path(self.root, run / 'manifest.json').read_text(), '{"kept":true}')

    def test_publication_retry_skips_the_workload_and_operation(self):
        from story_builder.services import video_repertoire_worker as worker
        job = {'status':'queued', 'publication_pending':True, 'result':{'completed':'render'}, 'request':{}}
        with patch.object(worker.sys, 'argv', ['worker','audio-effects','job-retry']), \
             patch.object(worker.store, 'read_job', return_value=job), \
             patch.object(worker, 'publish_completed_result') as publish, \
             patch.object(worker, 'gpu_workload_lock') as lock, \
             patch.object(worker.signal, 'signal'):
            self.assertEqual(worker.main(), 0)
        publish.assert_called_once_with('audio-effects','job-retry',job,job['result'])
        lock.assert_not_called()


if __name__ == '__main__': unittest.main()
