"""CPU-only analyzer quality checks; no model load or owner media changes."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[3]/'local_data/engines/video-analyzer/src'))
from video_audio_analyzer.pipeline import AnalyzerOptions, _cut_interval_records, _collect_audio_event_clips
from video_audio_analyzer.voice_embeddings import speaker_passages

class ExtractionQualityTests(unittest.TestCase):
    def test_cut_in_bottom_panel_is_not_diluted_by_stationary_reactor(self):
        first=np.zeros((90,160,3),dtype=np.uint8)
        second=first.copy(); second[45:]=80
        samples=[(0,first,0),(1,second,80/255/2)]
        cuts=_cut_interval_records('s1',0,3,samples,AnalyzerOptions())
        self.assertEqual([(c['start_time_sec'],c['end_time_sec']) for c in cuts],[(0,1),(1,3)])

    def test_cut_toggle_disabled(self):
        self.assertEqual(_cut_interval_records('s1',0,3,[],AnalyzerOptions(extract_cut_clips=False)),[])

    def test_mixed_music_and_sfx_are_not_saved_as_isolated_clips(self):
        events=[{'event_id':'music','event_type':'music','start_time_sec':0,'end_time_sec':3},
                {'event_id':'sfx','event_type':'sfx','start_time_sec':1,'end_time_sec':2}]
        with tempfile.TemporaryDirectory() as directory, patch('video_audio_analyzer.pipeline._run') as run:
            root=Path(directory)
            self.assertEqual(_collect_audio_event_clips(root/'mix.wav',events,root,collect_music=True,collect_sfx=True),[])
            run.assert_not_called()
            collected=_collect_audio_event_clips(root/'no_vocals.wav',events,root,collect_music=True,collect_sfx=True,isolation_status='demucs_accompaniment')
            self.assertEqual(len(collected),1); self.assertEqual(collected[0]['source'],'no_vocals.wav')
            self.assertEqual(collected[0]['isolation_status'],'demucs_accompaniment')
            self.assertIn(str(root/'no_vocals.wav'),run.call_args.args[0])

    def test_other_speaker_inside_passage_prevents_voice_reference(self):
        segments=[{'speaker_id':'reactor','start_time_sec':0,'end_time_sec':40},
                  {'speaker_id':'source','start_time_sec':15,'end_time_sec':20}]
        self.assertEqual(speaker_passages(segments),[])
        self.assertEqual(len(speaker_passages(segments[:1])),1)
