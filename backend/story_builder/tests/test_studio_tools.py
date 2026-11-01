"""CPU contracts for studio adapters. No real Comfy submission or artifact deletion."""
import contextlib
import hashlib
import io
import json
import struct
import tempfile
import unittest
import wave
from story_builder.services import studio_checkpoints
from pathlib import Path
from unittest.mock import patch
from story_builder.services import trellis_studio as trellis, voice_studio as voice, image_training as training
from story_builder.services import video_repertoire as jobs, audio_effects


def glb():
    scene=json.dumps({'asset':{'version':'2.0'},'meshes':[{'primitives':[]}]}).encode()
    scene+=b' ' * (-len(scene)%4)
    return struct.pack('<4sII',b'glTF',2,20+len(scene))+struct.pack('<II',len(scene),0x4e4f534a)+scene


class StudioContracts(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);jobs.configure_roots(self.root)
        self.addCleanup(jobs.configure_roots,Path(self.temp.name)/'reset')

    def test_blender_appimage_launch_and_early_failure(self):
        import subprocess
        trellis.layout(self.root)
        run=trellis.home(self.root)/'runs'/'test-job';run.mkdir()
        app=self.root/'Applications'/'Blender-5.2.AppImage'
        app.parent.mkdir();app.write_text('');app.chmod(0o755)
        model=self.root/'result.glb';model.write_bytes(glb())
        with patch.object(trellis.jobs,'read_job',return_value={'request':{'mode':'single','items':[{}]}}), \
             patch.object(trellis,'result_path',return_value=model), \
             patch.object(trellis.shutil,'which',return_value=None), \
             patch.object(trellis.Path,'home',return_value=self.root), \
             patch.dict(trellis.os.environ,{'BLENDER_EXECUTABLE':''}), \
             patch.object(trellis.subprocess,'Popen') as launch:
            launch.return_value.wait.side_effect=subprocess.TimeoutExpired('blender',2)
            launch.return_value.pid=123
            self.assertTrue(trellis.open_blender(self.root,'test-job',1)['opened'])
            self.assertEqual(launch.call_args.args[0][0],str(app))
            self.assertEqual(launch.call_args.kwargs['env']['APPIMAGE_EXTRACT_AND_RUN'],'1')
            self.assertIn(str(model), (run/'open_blender.py').read_text())
            launch.return_value.wait.side_effect=None
            launch.return_value.wait.return_value=1
            with self.assertRaisesRegex(ValueError,'exited during startup'):
                trellis.open_blender(self.root,'test-job',1)

    def test_batch_waits_for_validation_and_recovery_never_resubmits(self):
        trellis.layout(self.root)
        rows=[]
        for index in (1,2):
            token=str(index)*32;trellis.image_path(self.root,token).write_bytes(b'image')
            rows.append({'index':index,'id':token,'name':str(index),'status':'queued'})
        job=jobs.create_job('trellis',{'mode':'batch','preset':'bounded','settings':{},'items':rows})
        identity=job['job_id'];manifest=trellis.home(self.root)/'batches'/f'{identity}.json'
        trellis.write(manifest,{'items':rows});calls=[]
        def submit(graph,**kwargs):
            index=len(calls)+1
            if index==2:self.assertTrue((trellis.home(self.root)/'output'/identity/'0001.glb').is_file())
            calls.append(kwargs['prompt_id'])
            return kwargs['prompt_id'],{'status':{'completed':True},'outputs':{'322':{'3d':[{'filename':'result.glb','subfolder':'','type':'output'}]}}}
        def get(url,**kwargs):return io.BytesIO(b'{}' if url.endswith('object_info') else glb())
        with patch.object(trellis,'urlopen',side_effect=get),patch.object(trellis,'validate_graph'),patch.object(trellis,'submit_and_wait',side_effect=submit),patch.object(training,'ensure_idle'),patch.dict('os.environ',{'COMFYUI_ROOT':str(self.root/'comfy')}):
            result=trellis.run_job(self.root,identity,job['request'],lambda *args:None)
        self.assertEqual([r['status'] for r in result['items']],['completed','completed']);self.assertEqual(len(calls),2)
        # A persisted uncertain prompt is reconciled, never sent again.
        result['items'][0].update(status='recovery_required',prompt_id='owned')
        trellis.write(manifest,result)
        with patch.object(trellis,'urlopen',return_value=io.BytesIO(b'{}')),patch.object(trellis,'validate_graph'),patch.object(trellis,'submit_and_wait') as submit,patch.object(training,'ensure_idle'):
            result=trellis.run_job(self.root,identity,job['request'],lambda *args:None)
        self.assertEqual(result['job_status'],'recovery_required');submit.assert_not_called()

    def test_invalid_first_result_blocks_second_prompt(self):
        trellis.layout(self.root);token='a'*32;trellis.image_path(self.root,token).write_bytes(b'image')
        rows=[{'index':i,'id':token,'name':str(i),'status':'queued'} for i in (1,2)]
        job=jobs.create_job('trellis',{'mode':'batch','preset':'bounded','settings':{},'items':rows})
        trellis.write(trellis.home(self.root)/'batches'/f"{job['job_id']}.json",{'items':rows})
        history={'status':{'completed':True},'outputs':{'322':{'3d':[{'filename':'result.glb','type':'output'}]}}}
        with patch.object(trellis,'urlopen',return_value=io.BytesIO(b'{}')),patch.object(trellis,'validate_graph'),patch.object(trellis,'submit_and_wait',return_value=('owned',history)) as submit,patch.object(training,'ensure_idle'),patch.dict('os.environ',{'COMFYUI_ROOT':str(self.root/'comfy')}):
            with self.assertRaises(ValueError):trellis.run_job(self.root,job['job_id'],job['request'],lambda *args:None)
        self.assertEqual(submit.call_count,1)

    def test_glb_validation_and_bounds(self):
        file=self.root/'test.glb';file.write_bytes(glb());self.assertEqual(len(trellis.validate_glb(file)),64)
        file.write_bytes(b'bad')
        with self.assertRaises(ValueError):trellis.validate_glb(file)
        with self.assertRaises(ValueError):trellis.compile_graph('bounded',{'shape_steps':float('nan')},'test','test')
        with self.assertRaises(ValueError):trellis.compile_graph('bounded',{'shell':'bad'},'test','test')

    def test_voice_recovery_preserves_submission_and_staging_on_network_failure(self):
        job=jobs.create_job('voice-studio',{'operation':'design','workspace_id':'workspace-a','text':'Hello','description':'Calm'})
        folder=jobs.job_path('voice-studio',job['job_id']).parent
        jobs._atomic_json(folder/'submission.json',{'prompt_id':'owned'})
        with patch.object(training,'ensure_idle'),patch.object(voice,'live_ready'),patch.object(voice,'urlopen',side_effect=OSError('offline')),patch.object(voice,'submit_and_wait') as submit:
            result=voice.run(self.root,job['job_id'],job['request'],lambda *args:None)
        self.assertEqual(result['job_status'],'recovery_required');self.assertEqual(result['prompt_id'],'owned');submit.assert_not_called()

    def test_training_freezes_safe_config_and_accepts_only_owned_artifacts(self):
        graph=voice.compile_graph({'operation':'training','name':'voice','epochs':40,'batch_size':1},'test','dataset')
        self.assertFalse(graph['4']['inputs']['overwrite']);self.assertFalse(graph['3']['inputs']['cache_data_in_gpu'])
        with self.assertRaises(ValueError):voice.compile_graph({'operation':'training','name':'../bad'},'test')
        comfy=self.root/'comfy';file=comfy/'models/TTS/RVC/voice.pth';file.parent.mkdir(parents=True);file.write_bytes(b'weights')
        history={'outputs':{'5':{'text':[json.dumps({'engine_type':'rvc','model_path':'/container/ComfyUI/models/TTS/RVC/voice.pth'})]}}}
        with patch.object(voice,'COMFY',comfy):
            self.assertEqual(voice.training_artifacts(history)['artifact_paths'],[str(file)])
            history['outputs']['5']['text']=[json.dumps({'engine_type':'rvc','model_path':'/etc/passwd'})]
            with self.assertRaises(ValueError):voice.training_artifacts(history)

    def test_lora_hash_revalidation_blocks_changed_weights(self):
        file=self.root/'test.safetensors';header=json.dumps({'lora_A.weight':{'dtype':'F32','shape':[1],'data_offsets':[0,4]}}).encode()
        file.write_bytes(struct.pack('<Q',len(header))+header+b'1234')
        metadata={'base_model_variant':'z-image-turbo','training_type':'character','sha256':hashlib.sha256(file.read_bytes()).hexdigest()}
        training.checked(file,metadata);file.write_bytes(file.read_bytes()+b'changed')
        with self.assertRaises(ValueError):training.checked(file,metadata)

    def test_training_launcher_reuses_healthy_service_without_starting_jobs(self):
        state={'ready':True,'url':training.URL,'active':False,'queues':[]}
        with patch.object(training,'health',return_value=state),patch.object(training.subprocess,'run') as run:
            self.assertEqual(training.launch(self.root),state)
        run.assert_not_called()

    def test_saved_active_training_queue_blocks_service_start(self):
        import sqlite3
        database=self.root/'env_setup/zimage_training/ai-toolkit/aitk_db.db'
        database.parent.mkdir(parents=True)
        with sqlite3.connect(database) as connection:
            connection.execute('CREATE TABLE Queue (is_running INTEGER)')
            connection.execute('INSERT INTO Queue VALUES (1)')
        with patch.object(training,'SETUP',self.root),patch.object(training,'health',return_value={'ready':False,'active':False}),patch.object(training.subprocess,'run') as run:
            with self.assertRaisesRegex(ValueError,'saved an active queue'): training.launch(self.root)
        run.assert_not_called()

    def test_checkpoint_delete_requires_confirmation_and_matching_current_hash(self):
        artifact=self.root/'checkpoint.safetensors';artifact.write_bytes(b'test weights')
        with patch.object(studio_checkpoints,'assert_idle'),patch.object(studio_checkpoints,'catalog',return_value=[{'id':'owned','sha256':'current','path':str(artifact)}]):
            with self.assertRaisesRegex(ValueError,'confirmation'):studio_checkpoints.delete(self.root,{'id':'owned','sha256':'current'})
            with self.assertRaisesRegex(ValueError,'changed'):studio_checkpoints.delete(self.root,{'id':'owned','sha256':'old','confirmed':True})
        self.assertEqual(artifact.read_bytes(),b'test weights')

    def test_simple_effect_runs_on_cpu_and_updates_the_local_job(self):
        source=self.root/'source.wav'
        with wave.open(str(source),'wb') as writer:
            writer.setnchannels(1);writer.setsampwidth(2);writer.setframerate(8000);writer.writeframes(b'\0\0'*8000)
        job={'job_id':'cpu-test','operation':'simple','settings':{'preset':'deep','strength':.5,'preview':True}}
        events=[]
        with patch.object(audio_effects,'submit_and_wait') as submit:
            audio_effects.run_effect_job(project_id='w',project_dir=self.root,output_root=self.root/'out',comfy_input_dir=self.root/'input',comfy_url='unused',job=job,source=source,update=events.append)
        submit.assert_not_called();self.assertEqual(job['status'],'completed');self.assertTrue(Path(job['export_path']).is_file())
        self.assertAlmostEqual(audio_effects.validate_duration('simple',Path(job['export_path']))['duration'],1,delta=.1)

if __name__=='__main__':unittest.main()
