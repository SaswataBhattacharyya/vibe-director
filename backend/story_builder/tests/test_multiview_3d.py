"""CPU-only view bindings, review gates and uncertain-request contracts."""
import io, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from story_builder.services import multiview_3d as multi, trellis_studio as studio, video_repertoire as jobs
from story_builder.tests.test_studio_tools import glb

class MultiViewContracts(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);jobs.configure_roots(self.root)
        self.addCleanup(jobs.configure_roots,self.root/'reset')
    def image(self,size=(80,100)):
        data=io.BytesIO();Image.new('RGBA',size,(255,0,0,128)).save(data,format='PNG')
        return studio.upload(self.root,data.getvalue())['id']
    def body(self,backend='pixal'):
        front,back=self.image(),self.image()
        return {'backend':backend,'input_mode':'multiview','view_profile':'two','mode':'single',
                'preset':'pixalbounded' if backend=='pixal' else 'mv512','settings':{},'views_confirmed':True,
                'items':[{'id':front,'name':'Subject','views':{'front':front,'back':back}}]}
    def test_bind_exact_two_and_four_pixal_views(self):
        for profile in multi.VIEWS:
            graph=multi.pixal_graph(profile,{'seed':7,'fov':30,'faces':10000},{v:v+'.png' for v in multi.VIEWS[profile]},'owned')
            for i,v in enumerate(multi.VIEWS[profile]):self.assertEqual(graph[str(400+i)]['inputs']['image'],v+'.png')
            self.assertEqual(graph['372']['inputs']['filename_prefix'],'owned')
            for n in ('3','12','18','23'):self.assertEqual(graph[n]['inputs']['seed'],7)
    def test_input_review_dimensions_distinct_and_pixal_mode_gates(self):
        with patch.object(jobs,'start_job',side_effect=lambda kind,identity:jobs.read_job(kind,identity)):
            body=self.body();body['views_confirmed']=False
            with self.assertRaisesRegex(ValueError,'confirm'):studio.create(self.root,body)
            body['views_confirmed']=True;body['items'][0]['views']['back']=body['items'][0]['id']
            with self.assertRaisesRegex(ValueError,'distinct'):studio.create(self.root,body)
            body=self.body();body['items'][0]['views']['back']=self.image((90,100))
            with self.assertRaisesRegex(ValueError,'dimensions'):studio.create(self.root,body)
            body=self.body();job=studio.create(self.root,body)
            self.assertEqual(job['request']['items'][0]['views'],body['items'][0]['views'])
            self.assertEqual(len(job['request']['items'][0]['hashes']),2)
            body['input_mode']='single'
            with self.assertRaisesRegex(ValueError,'Pixal3D'):studio.create(self.root,body)
    def test_alpha_upload_and_common_padding_preserve_scale(self):
        token=self.image();run=self.root/'prepared';run.mkdir()
        with Image.open(studio.image_path(self.root,token)) as im:self.assertEqual(im.mode,'RGBA');self.assertEqual(im.getpixel((0,0))[3],128)
        files=multi.prepare_views(self.root,{'front':token,'back':self.image()},run)
        with Image.open(files['front']) as im:
            self.assertEqual(im.size,(100,100));self.assertEqual(im.getpixel((0,0)),(0,0,0));self.assertEqual(im.getpixel((10,0)),(128,0,0))
    def test_remote_presets_are_bounded(self):
        self.assertEqual(multi.remote_settings('mv512',{})['ss_sampling_steps'],30)
        for values in ({'texture_size':513},{'seed':1.5},{'slat_sampling_steps':101},{'fake':1}):
            with self.assertRaises(ValueError):multi.remote_settings('mv512',values)
    def test_uncertain_submission_is_never_posted_again(self):
        run=self.root/'run';run.mkdir();studio.write(run/'remote-request.json',{'state':'submission_started'})
        with patch('requests.post') as post:
            with self.assertRaisesRegex(ValueError,'uncertain'):multi.remote_render(self.root,'test',{'index':1},{},run,lambda *args:None)
            post.assert_not_called()
    def test_saved_remote_receipt_downloads_without_another_generation(self):
        import uuid
        identity=str(uuid.uuid4());run=self.root/'run';run.mkdir()
        studio.write(run/'remote-response.json',{'request_id':identity,'glb_url':f'/download/{identity}/output.glb'})
        with patch('requests.post') as post,patch.object(multi,'ensure_ready'),patch.object(multi,'release_service_if_idle') as release,patch.object(multi,'urlopen',return_value=io.BytesIO(glb())),patch('story_builder.services.media_jobs.get_gpu_safety_hold',return_value={}):
            target=multi.remote_render(self.root,'test',{'index':1},{},run,lambda *a:None)
            self.assertEqual(target.read_bytes(),glb());post.assert_not_called();release.assert_called_once()
    def test_backend_default_destinations_are_separate(self):
        self.assertEqual(studio.output_folder(self.root,None,'pixal'),self.root/'pixal3d/output')
        self.assertEqual(studio.output_folder(self.root,None),self.root/'trellis.2/output')
    def test_health_reuses_service_without_starting_or_warming_models(self):
        with patch.object(multi,'health',return_value={'ready':True,'gpu_busy':False,'model_loaded':False}),patch.object(multi.subprocess,'run') as run:
            self.assertTrue(multi.ensure_ready(self.root)['ready']);multi.release_service_if_idle();run.assert_not_called()
    def test_recovery_cannot_attach_to_unsubmitted_object(self):
        job=jobs.create_job('trellis',{'backend':'trellis','input_mode':'multiview','items':[{}]})
        job['status']='recovery_required';jobs._atomic_json(jobs.job_path('trellis',job['job_id']),job)
        with self.assertRaisesRegex(ValueError,'number'):multi.reconcile(self.root,job['job_id'],'id',-1)
        with self.assertRaisesRegex(ValueError,'no submitted'):multi.reconcile(self.root,job['job_id'],'id',1)
    def test_remote_batch_publishes_before_next_object(self):
        body=self.body('trellis');body['mode']='batch';body['items'].append(self.body('trellis')['items'][0])
        with patch.object(jobs,'start_job',side_effect=lambda kind,identity:jobs.read_job(kind,identity)):job=studio.create(self.root,body)
        seen=[]
        def render(root,identity,row,request,run,progress):
            if seen:self.assertTrue((studio.output_folder(root,None)/identity/'0001.glb').exists())
            seen.append(row['index']);target=run/'collecting.glb';target.write_bytes(glb());return target
        with patch('story_builder.services.image_training.ensure_idle'),patch.object(multi,'remote_render',side_effect=render):
            result=studio.run_job(self.root,job['job_id'],job['request'],lambda *a:None)
        self.assertEqual(seen,[1,2]);self.assertTrue(all(r['status']=='completed' for r in result['items']))

if __name__=='__main__':unittest.main()
