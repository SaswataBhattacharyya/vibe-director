"""Real temporary-file project/export contracts. No GPU or provider calls."""
import io
import json
from pathlib import Path
import tempfile
import unittest
import wave
from unittest.mock import patch
from story_builder.services import music_jukebox as music, media_library


def wav():
    stream=io.BytesIO()
    with wave.open(stream,'wb') as out:
        out.setnchannels(2);out.setsampwidth(2);out.setframerate(44100);out.writeframes(b'\x00\x00\x00\x00'*4410)
    return stream.getvalue()


def project():
    return dict(version=1,name='Beat',revision=0,bpm=120,bars=1,master=-3,limiter=True,swing=0,sources=[],tracks=[],dj={'cross':0,'events':[]},mode='arrange')


class JukeboxContracts(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.p=music.save(self.root,{'project':project()},True)

    def test_save_revision_conflict_and_checkpoint(self):
        p=music.save(self.root,{'project':self.p,'revision':1})
        self.assertEqual(p['revision'],2)
        self.assertEqual(json.loads((music.project_path(self.root,p['id']).parent/'checkpoints'/'000001.json').read_text())['revision'],1)
        with self.assertRaisesRegex(ValueError,'another tab'): music.save(self.root,{'project':self.p,'revision':1})
        with self.assertRaisesRegex(ValueError,'workspace'): music.save(self.root,{'project':{**p,'workspace_id':'other'},'revision':2})

    def test_asset_identity_and_duration_gate(self):
        a=media_library.register_upload(self.root,self.p['workspace_id'],filename='test.wav',content=wav(),role='project_audio')
        source=dict(id=a['asset_id'],workspace_id=a['workspace_id'],asset_id=a['asset_id'],name='test',duration=.1,url=a['content_url'])
        music.validate(self.root,{**self.p,'sources':[source]})
        with self.assertRaisesRegex(ValueError,'URL'): music.validate(self.root,{**self.p,'sources':[{**source,'url':'/etc/passwd'}]})
        with self.assertRaisesRegex(ValueError,'10 minutes'): music.validate(self.root,{**self.p,'bars':128,'bpm':30})
        with self.assertRaises(ValueError): music.validate(self.root,{**self.p,'bpm':float('nan')})

    def test_render_claim_is_project_bound_and_single_use(self):
        data=wav();stage=music.stage_export(self.root,self.p['id'],{'CONTENT_LENGTH':str(len(data)),'wsgi.input':io.BytesIO(data)})
        other=music.save(self.root,{'project':project()},True)
        with self.assertRaisesRegex(ValueError,'another export'): music.claim_export(self.root,other['id'],stage)
        music.claim_export(self.root,self.p['id'],stage)
        with self.assertRaisesRegex(ValueError,'another export'): music.claim_export(self.root,self.p['id'],stage)

    def test_real_codec_exports_and_collision_protection(self):
        for fmt in ['wav','mp3','flac']:
            data=wav();stage=music.stage_export(self.root,self.p['id'],{'CONTENT_LENGTH':str(len(data)),'wsgi.input':io.BytesIO(data)})
            music.claim_export(self.root,self.p['id'],stage)
            with patch.object(music.jobs,'read_job',return_value={'status':'running'}):
                result=music.encode(self.root,'music-jukebox-123456789abc',{**stage,'project_id':self.p['id'],'format':fmt,'name':'mix'})
            self.assertTrue(Path(result['path']).is_file());self.assertGreater(result['duration'],0)
            with self.assertRaisesRegex(ValueError,'exists'): music.encode(self.root,'music-jukebox-123456789abc',{**stage,'project_id':self.p['id'],'format':fmt,'name':'mix'})

    def test_chosen_folder_and_cancel_do_not_publish(self):
        dest=self.root/'chosen';dest.mkdir();grant=music.folder(self.root,{'path':str(dest)})
        data=wav();stage=music.stage_export(self.root,self.p['id'],{'CONTENT_LENGTH':str(len(data)),'wsgi.input':io.BytesIO(data)})
        with patch.object(music.jobs,'read_job',return_value={'status':'cancel_requested'}):
            with self.assertRaisesRegex(ValueError,'cancelled'): music.encode(self.root,'music-jukebox-123456789abc',{**stage,'project_id':self.p['id'],'name':'cancel','folder':grant['grant']})
        self.assertFalse((dest/'cancel.wav').exists())


    def test_jobs_recover_only_for_requested_project(self):
        from story_builder.services import music_jukebox_api as api
        captured=[]
        def respond(start,status,value): captured.append(value);return []
        with patch.object(api.jobs,'list_jobs',return_value=[{'job_id':'mine','request':{'project_id':self.p['id']}},{'job_id':'other','request':{'project_id':'jukebox-000000000000'}}]):
            api.handle(self.root,{'REQUEST_METHOD':'GET','PATH_INFO':'/api/jukebox/projects/'+self.p['id']+'/jobs'},lambda *a:None,lambda e:{},respond)
        self.assertEqual([j['job_id'] for j in captured[0]['jobs']],['mine'])

    def test_project_copy_does_not_replace_without_permission(self):
        path=self.root/'copy.json'
        music.write(path,{'version':1},overwrite=False)
        with self.assertRaises(FileExistsError):music.write(path,{'version':2},overwrite=False)
        self.assertEqual(json.loads(path.read_text()),{'version':1})
        music.write(path,{'version':2},overwrite=True)
        self.assertEqual(json.loads(path.read_text()),{'version':2})

if __name__=='__main__': unittest.main()
