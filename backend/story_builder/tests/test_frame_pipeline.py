"""Reviewed take and export acceptance with disposable records and CPU images."""
import contextlib
import io
import json
import struct
import zlib
from unittest.mock import Mock, patch
from story_builder.tests.test_agent_tasks import AgentTaskFixture
from story_builder.services import frame_pipeline as frames, frame_interpolation as interp, frame_pipeline_jobs, media_library, projects, video_repertoire
from story_builder.services.production_ledger import LedgerConflict
from story_builder.services.storage_paths import generated_root


def png(color, width=32, height=32):
    def chunk(kind, data):
        return struct.pack('!I',len(data))+kind+data+struct.pack('!I',zlib.crc32(kind+data)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!2I5B',width,height,8,2,0,0,0))+chunk(b'IDAT',zlib.compress((b'\0'+bytes(color)*width)*height))+chunk(b'IEND',b'')


class FrameTests(AgentTaskFixture):
    def setUp(self):
        super().setUp()
        self.images=[media_library.register_upload(self.root,self.owner,filename=f'key-{i}.png',content=png(c),role='project_image') for i,c in enumerate([(255,0,0),(0,0,255)])]

    def take(self, two=False):
        take=frames.create(self.root,self.owner,self.images[0]['asset_id'])
        take=self.review(take)
        if two:
            take=frames.change(self.root,self.owner,take['take_id'],{'operation':'append','revision':take['revision'],'asset_id':self.images[1]['asset_id']})
            take=self.review(take)
        return take

    def review(self,take,decision='approved'):
        return frames.change(self.root,self.owner,take['take_id'],{'operation':'review','revision':take['revision'],'key_id':take['keys'][-1]['key_id'],'decision':decision})

    def settings(self,take,**extra):
        return {'take_id':take['take_id'],'revision':take['revision'],**extra}

    def test_explicit_canvas_preparation_preserves_original_and_endpoint_handoff_is_read_only(self):
        source=media_library.asset_path(self.root,self.owner,self.images[0]['asset_id'])[0]
        before=source.read_bytes()
        take=frames.create(self.root,self.owner,self.images[0]['asset_id'],normalize=True)
        self.assertEqual((take['keys'][0]['image']['width'],take['keys'][0]['image']['height']),(1024,1024))
        self.assertNotEqual(take['keys'][0]['image']['asset_id'],self.images[0]['asset_id'])
        self.assertEqual(source.read_bytes(),before)
        pair=self.take(two=True)
        endpoints=frames.endpoints(self.root,self.owner,pair['take_id'],pair['revision'])
        self.assertEqual(endpoints['first_frame'],pair['keys'][0]['image'])
        self.assertEqual(endpoints['last_frame'],pair['keys'][-1]['image'])
        self.assertEqual(frames.get(self.root,self.owner,pair['take_id']),pair)
        with self.assertRaises(LedgerConflict):frames.endpoints(self.root,self.owner,pair['take_id'],1)

    def test_node_schema_and_model_choices_are_checked_without_inference(self):
        from story_builder.services.production_image_workflows import graph_input_errors, input_choices
        graph={'1':{'class_type':'UNETLoader','inputs':{'unet_name':'kontext.safetensors'}}}
        self.assertTrue(graph_input_errors(graph,{'UNETLoader':{}}))
        schema={'UNETLoader':{'input':{'required':{'unet_name':[['other.safetensors']]}}}}
        self.assertIn('does not offer',graph_input_errors(graph,schema)[0])
        schema['UNETLoader']['input']['required']['unet_name'][0].append('kontext.safetensors')
        self.assertEqual(graph_input_errors(graph,schema),[])
        schema['UNETLoader']['input']['required']['unet_name']=['COMBO',{'options':['kontext.safetensors']}]
        self.assertEqual(graph_input_errors(graph,schema),[])
        self.assertEqual(input_choices(schema['UNETLoader']['input']['required']['unet_name']),['kontext.safetensors'])
        schema['UNETLoader']['input']['required']['unet_name'][1]['options']=[]
        self.assertTrue(graph_input_errors(graph,schema))
        for model in ('film','rife'):
            graph=interp.compile_graph(['a.png','b.png'],model,2,'check')
            info={n['class_type']:{'input':{'required':{f:['ANY'] for f in n['inputs']}}} for n in graph.values()}
            info['FrameInterpolationModelLoader']['input']['required']['model_name']=['COMBO',{'options':[interp.MODELS[model]]}]
            with patch.object(interp,'_request_json',return_value=info):self.assertEqual(interp.capability()['models'],[model])

    def test_completed_interpolation_download_order_and_key_preservation(self):
        take=self.take(two=True);sources=[k['image'] for k in take['keys']]
        settings={'model':'rife','multiplier':2,'fps':24,'hold':0}
        job=video_repertoire.create_job('frame-pipeline',{'workspace_id':self.owner})
        folder=generated_root(self.root,self.owner)/'frame-pipeline'/job['job_id'];folder.mkdir(parents=True)
        video_repertoire._atomic_json(folder/'interpolation.json',{'config':{'sources':sources,'settings':settings},'prompt_id':'saved-prompt'})
        history={'status':{'completed':True},'outputs':{'6':{'images':[{'filename':f'{i}.png','subfolder':'owned','type':'output'} for i in range(3)]}}}
        content=[png((255,0,0)),png((127,0,127)),png((0,0,255))]
        with patch.object(interp,'_request_json',return_value={'saved-prompt':history}) as request,patch.object(interp.urllib.request,'urlopen',side_effect=lambda *a,**kw:io.BytesIO(content.pop(0))),patch.object(interp,'finish_prompt_watchdog'),patch.object(interp,'cleanup_staging') as cleanup:
            result=interp.interpolate(self.root,self.owner,job['job_id'],sources,settings)
            self.assertEqual(result['frame_count'],3)
            cleanup.assert_called_once_with(self.root,job['job_id'])
            self.assertNotIn('method',request.call_args.kwargs)
        manifest=json.loads((folder/'sequence.json').read_text())
        self.assertEqual(manifest['sources'],sources)
        self.assertEqual(manifest['frames'][0]['sha256'],sources[0]['sha256'])

    def test_cpu_cancellation_reaps_owned_process(self):
        import subprocess
        processes=[];popen=subprocess.Popen
        def start(*args,**kwargs):
            process=popen(*args,**kwargs);processes.append(process);return process
        with patch.object(interp.subprocess,'Popen',side_effect=start),patch.object(interp,'check_cancel',side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):interp.run_cpu(['python3','-c','import time; time.sleep(30)'],'test-owned')
        self.assertIsNotNone(processes[0].poll())

    def test_failed_staging_removes_only_the_owned_staging_set(self):
        from story_builder.services import minimax_h3_media
        with patch.object(minimax_h3_media,'stage_image_reference',side_effect=ValueError('bad input')),patch.object(interp,'cleanup_staging') as cleanup:
            with self.assertRaises(ValueError):interp.stage(self.root,'owned-job',['source.png'],[{'asset_id':'a','sha256':'a'*64}])
            cleanup.assert_called_once_with(self.root,'owned-job')

    def test_review_branch_rejection_revision_and_snapshot(self):
        take=frames.create(self.root,self.owner,self.images[0]['asset_id'])
        with self.assertRaises(ValueError):frames.prepare(self.root,self.owner,'image.generate_next_keyframe',self.settings(take,prompt='Turn left',seed=1))
        take=self.review(take)
        with self.assertRaises(LedgerConflict):frames.change(self.root,self.owner,take['take_id'],{'operation':'append','revision':1,'asset_id':self.images[1]['asset_id']})
        take=frames.change(self.root,self.owner,take['take_id'],{'operation':'append','revision':take['revision'],'asset_id':self.images[1]['asset_id']})
        take=self.review(take,'rejected')
        branch=frames.change(self.root,self.owner,take['take_id'],{'operation':'branch','revision':take['revision'],'key_id':take['keys'][0]['key_id']})
        self.assertNotEqual(branch['take_id'],take['take_id']);self.assertEqual(len(branch['keys']),1)
        self.assertEqual(len(frames.get(self.root,self.owner,take['take_id'])['keys']),2)
        self.assertIn('frame_pipeline_takes',projects.sql_snapshot(projects.database_path(self.root,projects.DATABASES[1]),self.owner))
        self.dispatch.assert_not_called()

    def test_next_candidate_is_idempotent_and_never_auto_approved(self):
        take=self.take();settings=self.settings(take,prompt='Turn the camera slightly; preserve identity.',seed=41)
        result=frames.next_key(self.root,self.owner,settings)
        replay=frames.next_key(self.root,self.owner,settings)
        self.assertEqual(result['key_id'],replay['key_id'])
        current=frames.get(self.root,self.owner,take['take_id'])
        self.assertEqual(current['keys'][-1]['review'],'candidate')
        job=frames.store(self.root).get_job(project_id=self.owner,job_id=result['image_job_id'])
        self.assertEqual(job['workflow_id'],'flux_kontext_dev');self.assertEqual(job['seed'],41)
        self.assertEqual(job['settings']['image_references'],[{k:take['keys'][0]['image'][k] for k in ('asset_id','sha256')}])
        with self.assertRaises(ValueError):frames.prepare(self.root,self.owner,'image.generate_next_keyframe',self.settings(current,prompt='Next',seed=2))

    def test_shared_task_approval_and_chat_proposal_are_inert(self):
        take=self.take();settings=self.settings(take,prompt='Shift the light left.',seed=1)
        row=self.tasks.propose(self.owner,{'tool_id':'image.generate_next_keyframe','asset_ids':[self.images[0]['asset_id']],'settings':settings})
        with self.assertRaises(LedgerConflict):self.tasks.run(self.owner,row['task_id'],self.approval(row))
        self.tasks.approve(self.owner,row['task_id'],self.approval(row))
        row=self.tasks.run(self.owner,row['task_id'],self.approval(row))
        self.assertEqual(video_repertoire.read_job('frame-pipeline',row['invocation']['job_id'])['request']['operation'],'next')
        from story_builder.services.agent_conversation import AgentConversation
        import uuid
        chat=AgentConversation(self.tasks,Mock(return_value={'reply':'Review this candidate task.','intent':'image.generate_next_keyframe','quality':2,'frame_settings':settings}))
        result=chat.send(self.owner,{'request_id':str(uuid.uuid4()),'text':'Prepare next key','asset_ids':[],'skill_refs':[],'surface':'director'})
        self.assertTrue(result['messages'][-1]['task_id'])

    def test_changed_approved_image_and_dimensions_rejected(self):
        take=self.take();path=media_library.asset_path(self.root,self.owner,self.images[0]['asset_id'])[0]
        path.write_bytes(png((1,2,3)))
        with self.assertRaises(LedgerConflict):frames.prepare(self.root,self.owner,'image.generate_next_keyframe',self.settings(take,prompt='Next',seed=1))
        # Original WAV fixture remains unchanged; no production data is involved.
        self.assertEqual(self.original.read_bytes(),self.before)

    def test_compiled_interpolation_batches_all_keys_and_rejects_invalid_settings(self):
        graph=interp.compile_graph(['a.png','b.png','c.png'],'film',4,'test/frame')
        self.assertEqual(graph['5']['inputs']['images'],['batch_0',0])
        self.assertEqual(graph['batch_0']['inputs']['image2'],['key_0',0])
        for extra in ({'multiplier':True},{'fps':float('nan')},{'model':'unknown'},{'hold':11}):
            with self.assertRaises(ValueError):interp.validate_settings({'model':'film','multiplier':2,'fps':24,'hold':0,**extra})

    def test_cpu_export_verifies_count_silence_and_detects_modified_sequence(self):
        take=self.take(two=True);settings=self.settings(take,model='rife',multiplier=2,fps=6,hold=.5)
        sources=frames.prepare(self.root,self.owner,'video.interpolate_keyframes',settings)
        job=video_repertoire.create_job('frame-pipeline',{'workspace_id':self.owner,'operation':'interpolate','settings':settings,'inputs':sources})
        folder=generated_root(self.root,self.owner)/'frame-pipeline'/job['job_id'];(folder/'sequence').mkdir(parents=True)
        records=[]
        for i,c in enumerate([(255,0,0),(127,0,127),(0,0,255)]):
            path=folder/'sequence'/f'frame_{i:04d}.png';path.write_bytes(png(c));records.append({'path':path.name,'sha256':projects.digest(path)})
        video_repertoire._atomic_json(folder/'sequence.json',{'sources':sources,'settings':{k:settings[k] for k in ('model','multiplier','fps','hold')},'frames':records,'dimensions':[32,32]})
        # Keep test mutation within its own job JSON; worker publication is tested separately.
        job['status']='completed';video_repertoire._atomic_json(video_repertoire.job_path('frame-pipeline',job['job_id']),job)
        export_job=video_repertoire.create_job('frame-pipeline',{'workspace_id':self.owner})
        result=interp.export(self.root,self.owner,export_job['job_id'],job['job_id'])
        self.assertEqual(result['frame_count'],9);self.assertEqual(len(result['assets']),1)
        self.assertTrue((generated_root(self.root,self.owner)/'frame-pipeline'/export_job['job_id']/'lossless.mkv').is_file())
        (folder/'sequence/frame_0001.png').write_bytes(png((0,255,0)))
        with self.assertRaises(ValueError):interp.export(self.root,self.owner,export_job['job_id'],job['job_id'])
        self.assertFalse(list(generated_root(self.root,self.owner).rglob('encoding-*')))

    def test_uncertain_submission_is_never_posted_twice(self):
        take=self.take(two=True);settings={'model':'rife','multiplier':2,'fps':24,'hold':0}
        sources=[k['image'] for k in take['keys']]
        job=video_repertoire.create_job('frame-pipeline',{'workspace_id':self.owner})
        with patch.object(interp,'capability',return_value={'models':['rife']}),patch('story_builder.services.media_jobs.gpu_workload_guard',return_value=contextlib.nullcontext()),patch.object(interp,'stage',return_value=['a.png','b.png']),patch.object(interp,'ensure_prompt_watchdog',return_value=Mock()),patch.object(interp,'_request_json',side_effect=OSError('lost reply')) as request:
            self.assertEqual(interp.interpolate(self.root,self.owner,job['job_id'],sources,settings)['job_status'],'recovery_required')
            self.assertEqual(request.call_count,1)
        with patch.object(interp,'_request_json',return_value={}) as request:
            self.assertEqual(interp.interpolate(self.root,self.owner,job['job_id'],sources,settings)['job_status'],'recovery_required')
            self.assertEqual(request.call_count,1);self.assertNotIn('method',request.call_args.kwargs)

    def test_generated_approved_key_hash_stays_pinned_and_failed_candidate_can_be_rejected(self):
        take=self.take();queued=frames.next_key(self.root,self.owner,self.settings(take,prompt='Next lighting',seed=4))
        current=frames.get(self.root,self.owner,take['take_id'])
        store=frames.store(self.root)
        store.transition(queued['image_job_id'],'cancelled')
        current=frames.get(self.root,self.owner,take['take_id'])
        self.assertEqual(self.review(current,'rejected')['keys'][-1]['review'],'rejected')
        # A generated output must retain the exact hash the owner approved.
        take=frames.get(self.root,self.owner,take['take_id'])
        key={'key_id':'generated','review':'approved','job_id':'fake','image':take['keys'][0]['image']}
        take['keys']=[key];frames.save(self.root,take,take['revision'])
        media_library.asset_path(self.root,self.owner,key['image']['asset_id'])[0].write_bytes(png((3,4,5)))
        with patch.object(frames,'store') as mocked:
            mocked.return_value._connect=store._connect
            mocked.return_value.get_job.return_value={'status':'completed','output_asset_id':key['image']['asset_id']}
            with self.assertRaises(LedgerConflict):frames.get(self.root,self.owner,take['take_id'])

    def test_mismatched_canvas_and_stale_export_rejected(self):
        take=self.take()
        wide=media_library.register_upload(self.root,self.owner,filename='wide.png',content=png((0,2,3),64,32),role='project_image')
        take=frames.change(self.root,self.owner,take['take_id'],{'operation':'append','revision':take['revision'],'asset_id':wide['asset_id']})
        with self.assertRaises(ValueError):self.review(take)
        take=self.review(take,'rejected');take=frames.change(self.root,self.owner,take['take_id'],{'operation':'append','revision':take['revision'],'asset_id':self.images[1]['asset_id']});take=self.review(take)
        job=video_repertoire.create_job('frame-pipeline',{'workspace_id':'other','operation':'interpolate'})
        with self.assertRaises(LedgerConflict):frames.prepare(self.root,self.owner,'video.export_frame_sequence',self.settings(take,sequence_job_id=job['job_id']))

    def test_http_review_routes_and_owned_reconciliation_guard(self):
        from story_builder.services.frame_pipeline_api import handle
        def call(path,body=None):
            raw=json.dumps(body or {}).encode();statuses=[]
            env={'PATH_INFO':path,'REQUEST_METHOD':'POST' if body is not None else 'GET','CONTENT_TYPE':'application/json','wsgi.input':io.BytesIO(raw),'CONTENT_LENGTH':str(len(raw))}
            def respond(start,status,result):start(status,[]);return [json.dumps(result).encode()]
            return json.loads(b''.join(handle(self.root,env,lambda s,h:statuses.append(s),lambda e:json.load(e['wsgi.input']),respond,tasks=self.tasks)))
        result=call('/api/frame-pipeline/tool-library/takes',{'asset_id':self.images[0]['asset_id']})
        with patch.object(interp,'capability',return_value={'models':[],'available':False}):
            self.assertEqual(len(call('/api/frame-pipeline/tool-library')['takes']),1)
        reviewed=call('/api/frame-pipeline/tool-library/takes/'+result['take_id'],{'operation':'review','revision':1,'key_id':result['keys'][0]['key_id'],'decision':'approved'})
        task=call('/api/frame-pipeline/tool-library/propose',{'tool_id':'image.generate_next_keyframe','settings':self.settings(reviewed,prompt='Next',seed=1)})
        self.assertEqual(task['status'],'draft');self.dispatch.assert_not_called()
        job=video_repertoire.create_job('frame-pipeline',{'workspace_id':'other'})
        with self.assertRaises(ValueError):call(f"/api/frame-pipeline/tool-library/jobs/{job['job_id']}/reconcile",{})
