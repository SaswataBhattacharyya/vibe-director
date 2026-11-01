"""Focused deletion and publication checks; temporary assets only."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from story_builder.services import media_library as library, video_repertoire as store
from story_builder.services.video_repertoire_worker import _publication_rows, _materialize_cut_clips

class AnalysisQualityCleanupTests(unittest.TestCase):
    def test_owned_assets_only_including_archived(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root/'projects'/'ws'/'media'
            project.mkdir(parents=True)
            output = root/'projects'/'ws'/'media'/'generated'/'analysis'/'analysis-test_run-a'
            output.mkdir(parents=True)
            (output/'frame.jpg').write_bytes(b'frame')
            source = root/'projects'/'ws'/'media'/'inputs'/'source.mp4'
            source.parent.mkdir(); source.write_bytes(b'original')
            rows = [{'asset_id':'source','source':'project_upload','relative_path':'inputs/source.mp4'},
                {'asset_id':'derived','source':'project_output','relative_path':'analysis/analysis-test_run-a/frame.jpg',
                 'archived':True,'metadata':{'derivation_id':'analysis-test_run-a'}},
                {'asset_id':'other','source':'project_output','relative_path':'other.jpg','metadata':{'derivation_id':'analysis-other_run-b'}}]
            (project/'assets.json').write_text(json.dumps({'schema_version':1,'assets':rows}))
            self.assertEqual(library.delete_analysis_assets(root,'ws','analysis-test',{'run-a'}),1)
            self.assertTrue(source.exists()); self.assertFalse((output/'frame.jpg').exists())
            self.assertEqual([r['asset_id'] for r in json.loads((project/'assets.json').read_text())['assets']],['source','other'])

    def test_terminal_delete_never_signals_stale_pid_and_active_rejected(self):
        with patch.object(store,'read_job',return_value={'status':'completed','pid':1234}), patch.object(store,'_remove_analysis_job_outputs') as cleanup, patch.object(store.os,'killpg') as kill:
            store.delete_analysis_job('analysis-test'); cleanup.assert_called_once(); kill.assert_not_called()
        with patch.object(store,'read_job',return_value={'status':'running'}), patch.object(store,'_remove_analysis_job_outputs') as cleanup:
            with self.assertRaises(ValueError): store.delete_analysis_job('analysis-test')
            cleanup.assert_not_called()

    def test_cut_publication_skips_full_length_duplicate(self):
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory); (run/'cuts').mkdir(); (run/'cuts'/'c1.mp4').write_bytes(b'cut')
            (run/'embeddings').mkdir(); (run/'embeddings'/'s1.mp4').write_bytes(b'full')
            manifest={'run_id':'r1','source':{'duration_sec':10},'scenes':[{'scene_id':'s1','start_time_sec':0,'end_time_sec':10,'cuts':[{'cut_id':'c1','start_time_sec':0,'end_time_sec':5,'clip_path':'cuts/c1.mp4'}]}]}
            rows=_publication_rows(manifest,run)
            self.assertEqual(len(rows),1); self.assertEqual(rows[0]['timestamp_end_seconds'],5)
            manifest['scenes'][0]['cuts']=[]
            self.assertEqual(_publication_rows(manifest,run),[])

    def test_cut_encoder_serial_bounded_and_whole_source_skipped(self):
        with tempfile.TemporaryDirectory() as directory, patch('story_builder.services.video_repertoire_worker.subprocess.run') as run:
            manifest={'source':{'duration_sec':10},'scenes':[{'cuts':[{'cut_id':'whole','start_time_sec':0,'end_time_sec':10},{'cut_id':'half','start_time_sec':2,'end_time_sec':5}]}]}
            _materialize_cut_clips(manifest,Path(directory),Path('source.mp4'))
            run.assert_called_once(); self.assertIn('1',run.call_args.args[0]); self.assertEqual(manifest['scenes'][0]['cuts'][1]['clip_path'],'cuts/half.mp4')
