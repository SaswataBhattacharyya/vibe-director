"""CPU-only contracts for storyboard revisions, ownership and screenplay edits."""
import copy
import io
import json
import tempfile
import unittest
import uuid
from pathlib import Path
from PIL import Image
from story_builder.services.production_ledger import ProductionLedger, LedgerConflict
from story_builder.services.story_authoring import StoryAuthoring
from story_builder.services.storyboard import Storyboard, automatic_route_allowed
from story_builder.services.media_library import register_upload
from story_builder.services import projects
from story_builder.services.isolated_video_jobs import _validate_story_source_lineage, StoryHandoffRejected

class StoryboardTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'runtime'
        self.ledger=ProductionLedger(self.root/projects.DATABASES[0]);self.story=StoryAuthoring(self.ledger,data_root=self.root)
        item=self.story.create_workspace(title='Storyboard test',source_text='Mira holds a key.')
        self.w=item['workspace_id'];source=item['current_revision']['revision_id']
        def graph(**kw):
            return {'records':[{'kind':'event','type':'action','name':'Mira holds a key','detail':'','start':0,'end':17,'quote':'Mira holds a key.','status':'source_supported'}]}
        g=self.story.build_story_graph(workspace_id=self.w,source_revision_id=source,idempotency_key=str(uuid.uuid4()),provider_call=graph)
        def draft(**kw):
            records=json.loads(kw['prompt'].split('GRAPH RECORDS (JSON):\n')[1])
            return {'scenes':[{'slugline':'INT. ROOM - DAY','summary':'Mira holds a key.','shots':[{'presentation':'image','planned_duration_seconds':2,'action':'Mira holds a key.','dialogue':'MIRA: Here it is.','camera':'Static','lighting':'Daylight','mood':'Quiet','sfx':'','music':'','evidence_record_ids':[records[0]['record_id']]}]}]}
        self.screenplay=self.story.draft_screenplay(workspace_id=self.w,source_revision_id=source,graph_snapshot_id=g['snapshot_id'],idempotency_key=str(uuid.uuid4()),provider_call=draft)
        self.r=self.screenplay['screenplay_revision_id'];self.story.accept_screenplay(workspace_id=self.w,screenplay_revision_id=self.r)
        self.board=Storyboard(self.ledger,self.story,self.root)
        image=Image.new('RGB',(32,32),(22,80,130));stream=io.BytesIO();image.save(stream,format='PNG')
        self.png=stream.getvalue()
        self.asset=register_upload(self.root,self.w,filename='frame.png',content=self.png,role='image_candidate')

    def save(self,body=None):
        state=self.board.get(self.w,self.r)
        return self.board.save(self.w,self.r,{'expected_revision':state['revision'],'body':body or state['body']})

    def test_saved_board_cas_and_manual_fflf_policy(self):
        state=self.board.get(self.w,self.r);body=state['body'];self.assertEqual(body['shots']['1.1']['presentation'],'image')
        self.assertEqual(body['shots']['1.1']['duration'],2)
        self.save(body)
        with self.assertRaises(LedgerConflict):self.board.save(self.w,self.r,{'expected_revision':0,'body':body})
        body['shots']['1.1'].update(presentation='video',route='fflf',control='manual',duration=6)
        self.save(body)
        body['shots']['1.1']['control']='auto'
        with self.assertRaisesRegex(ValueError,'paused'):self.save(body)
        with self.assertRaisesRegex(ValueError,'paused'):automatic_route_allowed('fflf')
        body['shots']['1.1']['control']='manual';body['stages']['first_last']={'enabled':True,'control':'auto'}
        with self.assertRaisesRegex(ValueError,'paused'):self.save(body)

    def test_cross_project_references_and_bad_inputs_rejected(self):
        body=self.board.get(self.w,self.r)['body'];body['shots']['1.1']['reference_ids']=[{}]
        with self.assertRaises(ValueError):self.save(body)
        foreign=register_upload(self.root,'other-project',filename='foreign.png',content=self.png,role='image_candidate')
        body['shots']['1.1']['reference_ids']=[foreign['asset_id']]
        with self.assertRaisesRegex(ValueError,'unavailable'):self.save(body)
        body['shots']['1.1']['reference_ids']=[];body['shots']['1.1']['duration']=float('nan')
        with self.assertRaises(ValueError):self.save(body)
        body['shots']['1.1'].update(duration=6,presentation='video',route='image')
        with self.assertRaisesRegex(ValueError,'video route'):self.save(body)
        body['shots']['1.1'].update(route='t2v',media_asset_id=self.asset['asset_id'])
        with self.assertRaisesRegex(ValueError,'must match'):self.save(body)

    def test_global_proposal_selective_apply_keeps_evidence_and_idempotency(self):
        calls=[]
        def provider(prompt):
            calls.append(prompt);return {'replacement':json.dumps({'changes':[{'scene_number':1,'shot_number':1,'field':'planned_duration_seconds','value':3},{'scene_number':1,'shot_number':1,'field':'action','value':'Mira displays the key.'}]}),'explanation':'Adjust timing and action.'}
        proposal=self.board.propose(self.w,self.r,{'instruction':'Change timing and action','idempotency_key':'global-test'},provider)
        self.board.propose(self.w,self.r,{'instruction':'Change timing and action','idempotency_key':'global-test'},provider)
        self.assertEqual(len(calls),1);self.assertEqual(len(proposal['changes']),2)
        saved=self.board.apply(self.w,self.r,{'request_key':'global-test','selected':[0],'idempotency_key':str(uuid.uuid4())})
        shot=saved['screenplay']['scenes'][0]['shots'][0]
        self.assertEqual(shot['planned_duration_seconds'],3);self.assertEqual(shot['action'],'Mira holds a key.')
        self.assertEqual(shot['evidence'],self.screenplay['screenplay']['scenes'][0]['shots'][0]['evidence'])
        self.assertEqual(len(self.board.conversations(self.w,self.r)),1)
        with self.assertRaises(LedgerConflict):self.board.apply(self.w,self.r,{'request_key':'global-test','selected':[1],'idempotency_key':str(uuid.uuid4())})

    def test_discussion_is_saved_contextual_and_never_edits_screenplay(self):
        original=self.story.get_screenplay_revision(self.w,self.r)
        prompts=[]
        def provider(prompt):
            prompts.append(prompt)
            return {'replacement':'I suggest character dialogue for Mira, with narration for context.', 'explanation':'Discussion only'}
        first={'instruction':'Can Mira speak instead of the narrator?', 'idempotency_key':'chat-first'}
        reply=self.board.chat(self.w,self.r,first,provider)
        self.assertIn('Mira',reply['reply'])
        self.board.chat(self.w,self.r,first,provider)
        self.assertEqual(len(prompts),1)
        self.board.chat(self.w,self.r,{'instruction':'Keep narration where useful.', 'idempotency_key':'chat-second'},provider)
        self.assertIn(first['instruction'],prompts[-1])
        self.assertIn(reply['reply'],prompts[-1])
        self.assertEqual(self.story.get_screenplay_revision(self.w,self.r),original)
        self.assertEqual(len(self.board.conversations(self.w,self.r)),2)
        def propose(prompt):
            self.assertIn('Keep narration where useful.',prompt)
            return {'replacement':json.dumps({'changes':[{'scene_number':1,'shot_number':1,'field':'dialogue','value':'MIRA: I found the key.'}]}),'explanation':'The agreed dialogue adjustment.'}
        self.board.propose(self.w,self.r,{'instruction':'Prepare our agreed changes.', 'idempotency_key':'chat-agreed'},propose)
        saved=self.board.apply(self.w,self.r,{'request_key':'chat-agreed','selected':[0],'idempotency_key':str(uuid.uuid4())})
        history=self.board.conversations(self.w,saved['screenplay_revision_id'])
        self.assertEqual(len(history),3)
        self.assertEqual(history[0]['reply'],reply['reply'])
        with self.assertRaisesRegex(ValueError,'different screenplay'):
            self.board.apply(self.w,self.r,{'request_key':'chat-first','selected':[0],'idempotency_key':str(uuid.uuid4())})

    def test_director_cannot_replace_media_and_auto_fflf_is_rejected(self):
        body=self.board.get(self.w,self.r)['body'];body['shots']['1.1']['image_asset_id']=self.asset['asset_id']
        with self.assertRaisesRegex(ValueError,'replace generated media'):
            self.board.direct(self.w,self.r,{'instruction':'Plan','idempotency_key':'invalid-media'},lambda p:{'replacement':json.dumps(body),'explanation':'Invalid'})
        body['shots']['1.1'].update(image_asset_id='',presentation='video',route='fflf',control='auto')
        with self.assertRaisesRegex(ValueError,'paused'):
            self.board.direct(self.w,self.r,{'instruction':'Plan','idempotency_key':'invalid-route'},lambda p:{'replacement':json.dumps(body),'explanation':'Invalid'})

    def test_export_embeds_images_escapes_text_and_requires_complete_board(self):
        with self.assertRaisesRegex(ValueError,'every shot'):self.board.export(self.w,self.r)
        body=self.board.get(self.w,self.r)['body'];body['shots']['1.1']['image_asset_id']=self.asset['asset_id'];body['scenes']['1']['description']='<script>alert(1)</script>'
        self.save(body);export=self.board.export(self.w,self.r)
        self.assertIn('data:image/png;base64,',export['html']);self.assertIn('&lt;script&gt;',export['html']);self.assertNotIn('<script>',export['html'])
        self.assertIn('MIRA: Here it is.',export['html'])

    def test_video_handoff_binds_saved_board_and_stale_changes_block_submission(self):
        body=self.board.get(self.w,self.r)['body'];body['shots']['1.1'].update(presentation='video',route='t2v',duration=6)
        self.save(body);handoff=self.board.video_handoff(self.w,self.r,'1.1')
        lineage={k:handoff[k] for k in ('screenplay_revision_id','setup_hash','scene_number','shot_number','source_prompt_sha256','board_revision')}
        request={'workflow_id':handoff['workflow_id'],'duration_seconds':6}
        with self.ledger._connect() as db:
            result=_validate_story_source_lineage(db,self.story,self.w,handoff['clip_id'],request,lineage,self.root)
        self.assertEqual(result['board_revision'],1)
        body['shots']['1.1']['video_prompt']='Changed shot prompt';self.save(body)
        with self.ledger._connect() as db:
            with self.assertRaisesRegex(StoryHandoffRejected,'changed'):_validate_story_source_lineage(db,self.story,self.w,handoff['clip_id'],request,lineage,self.root)

    def test_project_save_and_fresh_root_restore_include_board_and_media(self):
        body=self.board.get(self.w,self.r)['body'];body['shots']['1.1']['image_asset_id']=self.asset['asset_id'];self.save(body)
        self.board.chat(self.w,self.r,{'instruction':'Keep this discussion with the project.','idempotency_key':'portable-chat'},lambda p:{'replacement':'I will keep the agreed pacing in mind.','explanation':'Discussion only'})
        folder=Path(self.temp.name)/'project';folder.mkdir()
        projects.save(self.root,self.w,folder,{})
        fresh=Path(self.temp.name)/'fresh';story=StoryAuthoring(ProductionLedger(fresh/projects.DATABASES[0]),data_root=fresh)
        board=Storyboard(story.ledger,story,fresh)
        projects.open_project(fresh,folder)
        restored=board.get(self.w,self.r)
        self.assertEqual(restored['body'],body);self.assertIn('data:image/png;base64,',board.export(self.w,self.r)['html'])
        self.assertEqual(board.conversations(self.w,self.r)[0]['reply'],'I will keep the agreed pacing in mind.')

    def test_editor_import_is_ordered_and_reopening_preserves_edits(self):
        body=self.board.get(self.w,self.r)['body'];body['shots']['1.1']['image_asset_id']=self.asset['asset_id'];self.save(body)
        item=self.board.editor_handoff(self.w,self.r)
        self.assertEqual(item['selection'][0]['asset_id'],self.asset['asset_id'])
        self.assertEqual(item['selection'][0]['end'],2)
        from story_builder.services import vibe_editor
        vibe_editor.update_project(self.root,item['id'],{'override':'My new editing instructions'})
        self.assertEqual(self.board.editor_handoff(self.w,self.r)['overrides']['default'],'My new editing instructions')
        body['shots']['1.1'].update(presentation='video',route='existing');self.save(body)
        with self.assertRaisesRegex(ValueError,'final video'):self.board.editor_handoff(self.w,self.r)

    def test_unsaved_board_cannot_open_video_and_r2v_uses_pinned_aspect(self):
        with self.assertRaisesRegex(ValueError, 'Save the storyboard'):
            self.board.video_handoff(self.w, self.r, '1.1')
        from story_builder.services.isolated_video_jobs import IsolatedVideoJobs
        request = IsolatedVideoJobs._full_r2v_request(setup={
            'video_quality':'standard','aspect_ratio':'9:16',
            'duration_policy':{'seconds':6}}, prompt='A bird takes flight.')
        self.assertEqual(request['aspect_ratio'], '9:16')
        self.assertEqual(request['duration_seconds'], 6)

    def test_storyboard_auto_images_require_smoke_before_admission(self):
        from unittest.mock import patch
        from story_builder.isolated_server import create_app
        app = create_app(data_root=self.root)
        payload = {'workflow_id':'z_image_turbo', 'initial_candidate_count':1,
            'prompt':'A mountain.', 'control_mode':'assisted_manual', 'seed':1,
            'output_prefix':'storyboard/shot_1_1_image', 'workspace_id':self.w,
            'idempotency_key':'automatic-smoke-test','asset_role':'image_candidate',
            'storyboard_automatic':True}
        raw = json.dumps(payload).encode(); statuses=[]
        with patch('story_builder.isolated_server.image_workflow_catalog', return_value={
                'workflows':[{'workflow_id':'z_image_turbo', 'available':True,
                    'automation_available':False, 'automation_disabled_reason':'Manual review required.'}]}), \
             patch('story_builder.isolated_server._runtime_guard') as gpu:
            response = json.loads(b''.join(app({'REQUEST_METHOD':'POST', 'PATH_INFO':'/api/images/jobs',
                'QUERY_STRING':'', 'CONTENT_TYPE':'application/json','CONTENT_LENGTH':str(len(raw)),
                'wsgi.input':io.BytesIO(raw)}, lambda status, headers:statuses.append(status))))
        self.assertEqual(statuses, ['409 Conflict'])
        self.assertEqual(response['error']['code'], 'image_automation_not_ready')
        gpu.assert_not_called()

    def test_editor_uses_screenplay_order_even_if_saved_json_keys_are_reversed(self):
        from unittest.mock import patch
        envelope=copy.deepcopy(self.screenplay)
        second=copy.deepcopy(envelope['screenplay']['scenes'][0]['shots'][0]);second['shot_number']=2
        envelope['screenplay']['scenes'][0]['shots'].append(second)
        with patch.object(self.story, 'get_screenplay_revision', return_value=envelope):
            body=self.board.get(self.w,self.r)['body']
            for row in body['shots'].values():row['image_asset_id']=self.asset['asset_id']
            body['shots']['1.2']['duration']=3
            body['shots']=dict(reversed(list(body['shots'].items())))
            self.save(body)
            item=self.board.editor_handoff(self.w,self.r)
        self.assertEqual([row['end'] for row in item['selection']], [2,3])
