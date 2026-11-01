"""CPU-only proof of final-frame extraction, caching and source integrity."""
import hashlib
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from story_builder.services.video_continuity import last_frame
from story_builder.services.media_library import asset_path, register_upload

@unittest.skipUnless(shutil.which('ffmpeg'), 'FFmpeg required')
class LastFrameTests(unittest.TestCase):
    def test_actual_final_frame_cache_and_changed_source(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'source.mp4'
            subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=red:s=128x96:r=2:d=1',
                '-f','lavfi','-i','color=c=blue:s=128x96:r=2:d=1','-filter_complex','[0:v][1:v]concat=n=2:v=1:a=0',
                '-c:v','libx264','-y',str(source)],check=True,capture_output=True)
            asset = register_upload(root, 'workspace-a', filename='source.mp4',content=source.read_bytes(),role='project_video')
            output = {'shared_asset_id':asset['asset_id'],'sha256':asset['sha256']}
            frame = last_frame(root,'workspace-a',output)
            path, _, _ = asset_path(root,'workspace-a',frame['asset_id'])
            rgb = subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-vf','scale=1:1','-f','rawvideo','-pix_fmt','rgb24','-'])
            self.assertGreater(rgb[2],200)
            self.assertLess(rgb[0],30)
            with patch('story_builder.services.video_continuity.subprocess.run',side_effect=AssertionError('cache miss')):
                self.assertEqual(last_frame(root,'workspace-a',output,create=False),frame)
            video, _, _ = asset_path(root,'workspace-a',asset['asset_id'])
            video.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'missing or changed'):
                last_frame(root,'workspace-a',output)
