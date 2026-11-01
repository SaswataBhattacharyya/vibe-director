"""Editor effect validation and actual FFmpeg producer/consumer checks (CPU only)."""
import copy
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from story_builder.services import editor_effects as effects, vibe_editor as editor

class EditorEffectsTests(unittest.TestCase):
    def clip(self, values=None, mime='video/mp4'):
        clip={'start':0,'end':3,'mime':mime,'fit':'contain'}
        effects.validate(clip, values or {})
        return clip

    def test_invalid_settings_and_image_ramp_rejected(self):
        for values in [{'effect':{'preset':'invented'}}, {'speed':{'start':float('nan')}}, {'speed':{'end':0}}, {'transition':{'kind':'invented'}}, {'effect':[]}, {'transition':{'kind':'glitch','duration':float('inf')}}]:
            with self.subTest(values=values), self.assertRaises(ValueError): self.clip(values)
        with self.assertRaisesRegex(ValueError,'video clips'): self.clip({'speed':{'start':2}},'image/png')
        with self.assertRaisesRegex(ValueError,'last clip'): effects.validate({'mime':'video/mp4'}, {'transition':{'kind':'glitch'}},last=True)

    def test_defaults_constant_and_ramp_duration(self):
        self.assertEqual(self.clip()['render_duration'],3)
        self.assertEqual(self.clip({'speed':{'start':2,'end':2}})['render_duration'],1.5)
        self.assertAlmostEqual(self.clip({'speed':{'start':1,'end':2}})['render_duration'],3*.69314718056)
        self.assertAlmostEqual(self.clip({'speed':{'start':2,'end':1}})['render_duration'],3*.69314718056)

    def test_neighbor_bounds_and_normalized_roundtrip(self):
        rows=[{'asset_id':'one','start':0,'end':3,'mime':'video/mp4'},{'asset_id':'two','start':0,'end':3,'mime':'video/mp4'}]
        plan={'clips':copy.deepcopy(rows)}
        with patch.object(editor,'validate_selection',return_value=rows):
            value=editor.validate_plan('/tmp','cpu',plan)
            self.assertEqual(value['clips'][0]['transition']['kind'],'cut')
            plan['clips'][0]['transition']={'kind':'glitch','duration':2}
            with self.assertRaisesRegex(ValueError,'half'): editor.validate_plan('/tmp','cpu',plan)

    def test_ffmpeg_filters_and_both_ramp_directions_preserve_audio_duration(self):
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder);source=folder/'source.mp4'
            subprocess.run(['ffmpeg','-nostdin','-v','error','-y','-f','lavfi','-i','testsrc2=s=160x128:r=24:d=3','-f','lavfi','-i','sine=duration=3','-c:v','libx264','-threads','1','-c:a','aac','-shortest',str(source)],check=True)
            for preset,a,b in [('cinematic',1,2),('vhs',2,1),('black-white',.5,.5)]:
                clip=self.clip({'effect':{'preset':preset,'strength':.7},'speed':{'start':a,'end':b}})
                destination=folder/(preset+'.mp4')
                effects.preprocess(source,destination,clip,{'width':160,'height':128,'fps':24},lambda args,*_:subprocess.run(args,check=True,capture_output=True),folder,{},lambda *_:None)
                probe=subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=codec_type,duration','-of','json',str(destination)],text=True)
                import json
                streams=json.loads(probe)['streams']
                self.assertEqual({s['codec_type'] for s in streams},{'audio','video'})
                for stream in streams:self.assertAlmostEqual(float(stream['duration']),clip['render_duration'],delta=.09)

if __name__=='__main__':unittest.main()
