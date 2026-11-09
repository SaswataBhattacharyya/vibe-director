"""Disposable CPU fixtures for actual multi-frame suffix/prefix analysis."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from story_builder.services import video_overlap


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg required')
class OverlapTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='vibe-overlap-test-')
        self.addCleanup(self.cleanup)
        self.folder = Path(self.temp.name)

    def cleanup(self):
        self.temp.cleanup()
        self.assertFalse(self.folder.exists(), 'Temporary overlap fixtures survived cleanup')

    def make(self, name, start=0, duration=3, fps=24, static=False, grade=False):
        path = self.folder / name
        source = 'color=blue:size=160x128:rate=24:duration=8' if static else 'testsrc2=size=160x128:rate=24:duration=8'
        filters = f'trim=start={start}:duration={duration},setpts=PTS-STARTPTS,fps={fps}'
        if grade:
            filters += ',eq=brightness=0.01:contrast=1.02'
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', source, '-vf', filters,
            '-c:v', 'libx264', '-crf', '23', str(path)], check=True, capture_output=True, timeout=30)
        return path

    def test_known_overlap_and_approximate_compression(self):
        a = self.make('a.mp4')
        for fps, grade in [(24, False), (30, True)]:
            b = self.make(f'b-{fps}.mp4', start=2, fps=fps, grade=grade)
            result = video_overlap.compare(a, b)
            self.assertEqual(result['status'], 'match', result)
            self.assertAlmostEqual(result['overlap_seconds'], 1, delta=2/fps)
            self.assertTrue(result['suggested_ranges'])
            self.assertGreaterEqual(len(result['evidence']), 2)

    def test_nonoverlap_and_static_never_recommend_trim(self):
        for static in (False, True):
            result = video_overlap.compare(self.make(f'a-{static}.mp4', static=static),
                                           self.make(f'b-{static}.mp4', start=4, static=static))
            self.assertNotEqual(result['status'], 'match', result)
            self.assertIsNone(result['suggested_ranges'])

    def test_invalid_settings(self):
        for value in ({'window_seconds': float('nan')}, {'window_seconds': True}, {'window_seconds': 99}, {'extra': 1}):
            with self.assertRaises(ValueError):
                video_overlap.settings(value)

    def test_short_and_periodic_motion_are_inconclusive(self):
        cycle=[bytes([(i*17+x*7)%256 for x in range(256)]) for i in range(12)]
        for rows in (cycle[:3],cycle*3):
            self.assertEqual(video_overlap.align(rows,rows,24)['status'],'inconclusive')

    def test_variable_frame_timing_is_reported_on_sampling_grid(self):
        a=self.make('vfr-a.mp4')
        raw=self.make('vfr-raw.mp4',start=2)
        b=self.folder/'vfr-b.mp4'
        subprocess.run(['ffmpeg','-v','error','-i',str(raw),'-vf','setpts=PTS+0.01*sin(N)/TB',
            '-fps_mode','vfr','-c:v','libx264',str(b)],check=True,capture_output=True,timeout=30)
        result=video_overlap.compare(a,b)
        self.assertIn(result['status'],('match','inconclusive'))
        self.assertGreater(result['timing_uncertainty_seconds'],0)
        if result['status']=='match':self.assertAlmostEqual(result['overlap_seconds'],1,delta=.1)
        else:self.assertIsNone(result['suggested_ranges'])
