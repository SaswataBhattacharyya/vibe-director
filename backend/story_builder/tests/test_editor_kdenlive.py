"""Disposable real CPU acceptance through Vibe task/Editor approvals and MCP."""
import copy
import json
import subprocess
from pathlib import Path
from unittest import skipUnless
from unittest.mock import patch
from story_builder.tests.test_agent_tasks import AgentTaskFixture
from story_builder.services import agent_editor, agent_overlap, editor_kdenlive, kdenlive_mcp, media_library, projects, vibe_editor, video_repertoire

class KdenliveTests(AgentTaskFixture):
    def setUp(self):
        super().setUp()
        self.videos=[]
        for i in range(2):
            path=Path(self.temp.name)/f'clip-{i}.mp4'
            subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','testsrc2=size=160x128:rate=30:duration=6',
                '-f','lavfi','-i','sine=frequency=440:sample_rate=48000:duration=6','-ss',str(i*2),'-t','3',
                '-c:v','libx264','-c:a','aac',str(path)],check=True,capture_output=True,timeout=30)
            self.videos.append(media_library.register_upload(self.root,self.owner,filename=path.name,content=path.read_bytes(),role='project_video'))
        self.hashes=[projects.digest(media_library.asset_path(self.root,self.owner,a['asset_id'])[0]) for a in self.videos]
        self.p=vibe_editor.add_project(self.root,{'name':'CPU join acceptance','workspace_id':self.owner})
        self.p=vibe_editor.update_project(self.root,self.p['id'],{'selection':[{'asset_id':a['asset_id'],'start':0,'end':3} for a in self.videos]})

    def complete(self,kind,ident,result):
        job=video_repertoire.read_job(kind,ident);job.update(status='completed',result=result)
        video_repertoire.job_path(kind,ident).write_text(json.dumps(job))

    def compare(self):
        row=self.tasks.propose(self.owner,{'tool_id':'video.compare_clip_overlap','asset_ids':[a['asset_id'] for a in self.videos],'settings':{}})
        self.tasks.approve(self.owner,row['task_id'],self.approval(row))
        row=self.tasks.run(self.owner,row['task_id'],self.approval(row));ident=row['invocation']['job_id']
        result=agent_overlap.run(self.root,video_repertoire.read_job('video-overlap',ident)['request'])
        self.complete('video-overlap',ident,result)
        self.assertEqual(self.tasks.poll(self.owner,row['task_id'])['status'],'completed')
        return row,self.tasks.overlap(self.owner,row['task_id'])

    def execute(self,p):
        ident=p['job_id'];job=video_repertoire.read_job('vibe-editor',ident)
        result=vibe_editor.run_job(self.root,ident,job['request'],lambda *args:None)
        self.complete('vibe-editor',ident,result)
        return next(p for p in vibe_editor.snapshot(self.root)['projects'] if p['id']==self.p['id'])

    def test_comparison_source_identity_and_reject(self):
        row,evidence=self.compare();self.assertEqual(evidence['comparison']['status'],'match')
        with patch.object(kdenlive_mcp,'capability',return_value={'ready':True}):
            p=editor_kdenlive.propose(self.root,self.tasks,self.p['id'],{'revision':self.p['revision'],'task_id':row['task_id']})
        self.assertEqual(p['pending']['kind'],'brief');self.assertIsNone(p['job_id'])
        p=vibe_editor.command(self.root,p['id'],{'action':'reject','revision':p['revision']});self.assertNotIn('pending',p)
        media_library.asset_path(self.root,self.owner,self.videos[0]['asset_id'])[0].write_bytes(b'changed source')
        with self.assertRaisesRegex(Exception,'changed'):self.tasks.overlap(self.owner,row['task_id'])

    @skipUnless(kdenlive_mcp.capability()['ready'],'Private Kdenlive runtime required')
    def test_real_mcp_agent_to_preview_approval_render_and_export(self):
        row,evidence=self.compare()
        target={'version':1,'editor_session_id':self.p['id'],'expected_revision':self.p['revision'],'selected_ranges':agent_editor.ranges(self.p['selection'])}
        draft=self.tasks.propose(self.owner,{'tool_id':'editor.prepare_clip_join','asset_ids':[a['asset_id'] for a in self.videos],
            'settings':{'target':target,'comparison_task_id':row['task_id']}})
        self.tasks.approve(self.owner,draft['task_id'],self.approval(draft))
        running=self.tasks.run(self.owner,draft['task_id'],self.approval(draft))
        p=self.execute({'job_id':running['invocation']['job_id']})
        self.assertEqual(self.tasks.poll(self.owner,draft['task_id'])['status'],'completed');self.assertEqual(p['pending']['kind'],'brief')
        p=vibe_editor.command(self.root,p['id'],{'action':'approve','revision':p['revision']})
        self.assertEqual(video_repertoire.read_job('vibe-editor',p['job_id'])['request']['operation'],'kdenlive_prepare')
        p=self.execute(p);self.assertEqual(p['pending']['value']['backend'],'kdenlive')
        self.assertTrue(media_library.asset_path(self.root,self.owner,p['join_preview']['asset']['asset_id'])[0].is_file())
        with self.assertRaisesRegex(ValueError,'stale'):vibe_editor.command(self.root,p['id'],{'action':'approve','revision':p['revision']-1})
        bad=copy.deepcopy(p['pending']['value']);bad['clips'][0]['effect']={'preset':'vhs','strength':.5}
        with self.assertRaises(ValueError):vibe_editor.validate_plan(self.root,self.owner,bad)
        p=vibe_editor.command(self.root,p['id'],{'action':'approve','revision':p['revision']});p=self.execute(p)
        self.assertEqual(p['output']['backend'],'kdenlive')
        output=media_library.asset_path(self.root,self.owner,p['output']['asset']['asset_id'])[0];probe=media_library._probe(output,'video')
        self.assertAlmostEqual(probe['duration_seconds'],5,delta=2/30);self.assertIn('audio',probe['streams'])
        self.assertTrue(Path(p['output']['editable_project']).is_file())
        folder=editor_kdenlive.execution_folder(self.root,self.owner,p['id'],p['output']['execution_id'])
        cached=kdenlive_mcp.run(folder,'render',lambda *args:None)
        self.assertEqual(cached['outputSha256'],projects.digest(Path(cached['outputPath'])))
        Path(cached['outputPath']).write_bytes(b'changed cached render')
        with self.assertRaisesRegex(ValueError,'output changed'):
            kdenlive_mcp.run(folder,'render',lambda *args:None)
        self.assertEqual(self.hashes,[projects.digest(media_library.asset_path(self.root,self.owner,a['asset_id'])[0]) for a in self.videos])

    def test_chat_proposes_analysis_then_uses_measured_evidence_for_join(self):
        import uuid
        from unittest.mock import Mock
        from story_builder.services.agent_conversation import AgentConversation
        target={'version':1,'editor_session_id':self.p['id'],'expected_revision':self.p['revision'],'selected_ranges':agent_editor.ranges(self.p['selection'])}
        request={'request_id':str(uuid.uuid4()),'text':'Compare end A to start B','asset_ids':[], 'skill_refs':[], 'surface':'editor','target':target}
        reason=Mock(return_value={'reply':'Compare these sources.','intent':'compare_clip_overlap','quality':2})
        message=AgentConversation(self.tasks,reason).send(self.owner,request)['messages'][-1]
        draft=self.tasks.get(self.owner,message['task_id'])
        self.assertEqual(draft['plan']['tool_id'],'video.compare_clip_overlap')
        self.dispatch.assert_not_called()
        self.tasks.cancel(self.owner,draft['task_id'])
        row,evidence=self.compare()
        reason.return_value={'reply':'Prepare measured join.','intent':'editor.prepare_clip_join','quality':2}
        request.update(request_id=str(uuid.uuid4()),text='Prepare the join using this overlap')
        message=AgentConversation(self.tasks,reason).send(self.owner,request)['messages'][-1]
        join=self.tasks.get(self.owner,message['task_id'])
        self.assertEqual(join['plan']['settings']['comparison_task_id'],row['task_id'])
        self.assertEqual(join['status'],'draft')
        self.assertIn('overlap_evidence',reason.call_args.kwargs['prompt'])

    def test_selection_change_invalidates_join_brief_and_unavailable_has_no_fallback(self):
        row,_=self.compare()
        body={'revision':self.p['revision'],'task_id':row['task_id']}
        with patch.object(kdenlive_mcp,'capability',return_value={'ready':False,'message':'Unavailable'}), patch.object(kdenlive_mcp,'run') as execute:
            with self.assertRaisesRegex(ValueError,'Unavailable'):editor_kdenlive.propose(self.root,self.tasks,self.p['id'],body)
            execute.assert_not_called()
        with patch.object(kdenlive_mcp,'capability',return_value={'ready':True}):
            p=editor_kdenlive.propose(self.root,self.tasks,self.p['id'],body)
        p=vibe_editor.update_project(self.root,p['id'],{'selection':p['selection'][::-1]})
        self.assertNotIn('pending',p)

    def test_cancelled_or_superseded_execution_cannot_publish(self):
        request={'project_id':self.p['id'],'revision':self.p['revision'],'workspace_id':self.owner}
        job=video_repertoire.create_job('vibe-editor',{**request,'operation':'kdenlive_prepare'})
        with vibe_editor.state(self.root) as data:vibe_editor.project(data,self.p['id'])['job_id']=job['job_id']
        video_repertoire.cancel_job('vibe-editor',job['job_id'])
        with patch.object(kdenlive_mcp,'run') as execute:
            with self.assertRaisesRegex(ValueError,'stopped'):editor_kdenlive.prepare(self.root,job['job_id'],request,lambda *args:None)
            execute.assert_not_called()

    @skipUnless(kdenlive_mcp.capability()['ready'],'Private Kdenlive runtime required')
    def test_silent_sources_prepare_without_synthetic_audio(self):
        silent=[]
        for i,asset in enumerate(self.videos):
            source=media_library.asset_path(self.root,self.owner,asset['asset_id'])[0]
            target=Path(self.temp.name)/f'silent-{i}.mp4'
            subprocess.run(['ffmpeg','-v','error','-i',str(source),'-an','-c:v','copy',str(target)],check=True,capture_output=True,timeout=30)
            silent.append(media_library.register_upload(self.root,self.owner,filename=target.name,content=target.read_bytes(),role='project_video'))
        self.videos=silent
        self.p=vibe_editor.update_project(self.root,self.p['id'],{'selection':[{'asset_id':a['asset_id'],'start':0,'end':3} for a in silent]})
        row,_=self.compare()
        p=editor_kdenlive.propose(self.root,self.tasks,self.p['id'],{'revision':self.p['revision'],'task_id':row['task_id']})
        p=vibe_editor.command(self.root,p['id'],{'action':'approve','revision':p['revision']});p=self.execute(p)
        self.assertEqual(p['pending']['value']['backend'],'kdenlive')
        p=vibe_editor.command(self.root,p['id'],{'action':'approve','revision':p['revision']});p=self.execute(p)
        output=media_library.asset_path(self.root,self.owner,p['output']['asset']['asset_id'])[0]
        self.assertAlmostEqual(media_library._probe(output,'video')['duration_seconds'],5,delta=2/30)

    def test_mcp_preview_escape_is_not_registered(self):
        row,_=self.compare()
        with patch.object(kdenlive_mcp,'capability',return_value={'ready':True}):
            p=editor_kdenlive.propose(self.root,self.tasks,self.p['id'],{'revision':self.p['revision'],'task_id':row['task_id']})
        p=vibe_editor.command(self.root,p['id'],{'action':'approve','revision':p['revision']})
        outside=media_library.asset_path(self.root,self.owner,self.videos[0]['asset_id'])[0]
        with patch.object(kdenlive_mcp,'run',return_value={'outputPath':str(outside)}):
            with self.assertRaisesRegex(ValueError,'invalid preview'):self.execute(p)
        current=next(p for p in vibe_editor.snapshot(self.root)['projects'] if p['id']==self.p['id'])
        self.assertNotIn('join_preview',current)
        self.assertNotIn('output',current)
