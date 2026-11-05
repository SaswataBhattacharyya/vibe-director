"""CPU-only checks for project prompt discussions, approval and portable guidance."""
import json
import io
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import Mock, patch

from story_builder.services.production_ledger import ProductionLedger, LedgerConflict
from story_builder.services.story_authoring import StoryAuthoring
from story_builder.services.prompt_director import PromptDirector, read_guidance, image_brief
from story_builder.services import projects


class PromptDirectorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'runtime'
        self.ledger = ProductionLedger(self.root / projects.DATABASES[0])
        self.story = StoryAuthoring(self.ledger, data_root=self.root)
        item = self.story.create_workspace(title='The key', source_text='Mira holds a key in a room.')
        self.w = item['workspace_id']; source = item['current_revision']['revision_id']
        def graph(**_):
            return {'records': [
                {'kind':'entity','type':'character','name':'Mira','detail':'','start':0,'end':4,'quote':'Mira','status':'source_supported'},
                {'kind':'entity','type':'location','name':'Room','detail':'','start':22,'end':26,'quote':'room','status':'source_supported'},
                {'kind':'event','type':'action','name':'Mira holds a key','detail':'','start':0,'end':16,'quote':'Mira holds a key','status':'source_supported'}]}
        g = self.story.build_story_graph(workspace_id=self.w, source_revision_id=source, idempotency_key=str(uuid.uuid4()), provider_call=graph)
        def draft(**kw):
            records = json.loads(kw['prompt'].split('GRAPH RECORDS (JSON):\n')[1])
            return {'scenes':[{'slugline':'INT. ROOM - DAY','summary':'Mira holds a key.','shots':[
                {'action':'Mira holds a key.','dialogue':'','camera':'Static','lighting':'Day','mood':'Quiet','sfx':'','music':'',
                 'evidence_record_ids':[item['record_id'] for item in records]}]}]}
        screenplay = self.story.draft_screenplay(workspace_id=self.w, source_revision_id=source, graph_snapshot_id=g['snapshot_id'], idempotency_key=str(uuid.uuid4()), provider_call=draft)
        self.r = screenplay['screenplay_revision_id']
        self.story.accept_screenplay(workspace_id=self.w, screenplay_revision_id=self.r)
        self.service = PromptDirector(self.ledger, self.story)
        self.state = self.service.get(self.w, self.r)
        self.target = next(iter(self.state['targets']))

    def save(self, lessons=None, assets=None, version=0):
        return self.service.save(self.w, self.r, {'expected_revision':version,'lessons':lessons or [],'assets':assets or {}})

    def payload(self, instruction='Discuss the prompts.', key='chat'):
        return {'instruction':instruction, 'idempotency_key':key, 'prompts':{'shot:1.1':'Mira holds a key.'}}

    def test_chat_is_durable_contextual_idempotent_and_never_applies(self):
        original = self.story.get_screenplay_revision(self.w, self.r)
        provider = Mock(return_value={'replacement':'We can simplify camera direction.','explanation':'Discussion only'})
        self.service.discuss(self.w, self.r, 'chat', self.payload(), provider)
        self.service.discuss(self.w, self.r, 'chat', self.payload(), provider)
        self.assertEqual(provider.call_count, 1)
        self.service.discuss(self.w, self.r, 'chat', self.payload('Keep the action.', 'second'), provider)
        self.assertIn('We can simplify camera direction.', provider.call_args.kwargs['prompt'])
        self.assertEqual(self.service.get(self.w, self.r)['revision'], 0)
        self.assertEqual(self.story.get_screenplay_revision(self.w, self.r), original)
        self.assertEqual(len(PromptDirector(self.ledger, self.story).get(self.w, self.r)['items']), 2)

    def test_learning_requires_review_is_scoped_removable_and_exports_skill(self):
        lesson = {'scope':'character','rule':'Use concrete visible clothing rather than occupation labels.'}
        provider = Mock(return_value={'replacement':json.dumps({'lessons':[lesson]}),'explanation':'An appearance rule.'})
        turn = self.service.discuss(self.w,self.r,'learn',self.payload('Remember how to describe clothing.'),provider)
        self.assertEqual(read_guidance(self.ledger,self.w,'character'), '')
        self.save(lessons=turn['proposal']['lessons'])
        self.assertIn(lesson['rule'],read_guidance(self.ledger,self.w,'character'))
        self.assertEqual(read_guidance(self.ledger,self.w,'video'), '')
        self.assertEqual(read_guidance(self.ledger,'unrelated-project','character'), '')
        exported = self.service.export(self.w,self.r)
        self.assertTrue(exported.startswith('---\nname: project-prompting\n'))
        self.assertIn(lesson['rule'],exported)
        self.save(version=1)
        self.assertEqual(read_guidance(self.ledger,self.w,'character'), '')

    def test_image_briefs_keep_revision_ownership_and_cas(self):
        self.assertEqual({t['scope'] for t in self.state['targets'].values()},{'character','world'})
        self.save(assets={self.target:'An established appearance brief.'})
        self.assertEqual(image_brief(self.ledger,self.w,self.r,self.target),'An established appearance brief.')
        self.assertEqual(image_brief(self.ledger,self.w,'another-revision',self.target),'')
        with self.assertRaises(LedgerConflict):self.save(assets={self.target:'Stale edit.'})
        with self.assertRaises(ValueError):self.save(assets={'foreign-target':'Invalid.'},version=1)
        self.assertEqual(image_brief(self.ledger,self.w,self.r,self.target),'An established appearance brief.')

    def test_proposals_reject_unknown_stale_and_oversized_changes_without_applying(self):
        for key, before, value in [('shot:99.1','Mira holds a key.','New'),('shot:1.1','Incorrect before','New'),('shot:1.1','Mira holds a key.','x'*7000)]:
            provider = Mock(return_value={'replacement':json.dumps({'changes':[{'key':key,'before':before,'value':value}]}),'explanation':'Change'})
            with self.assertRaises(ValueError):self.service.discuss(self.w,self.r,'propose',self.payload(key=str(uuid.uuid4())),provider)
        change = {'key':'shot:1.1','before':'Mira holds a key.','value':'Mira holds a key. Static framing.'}
        turn = self.service.discuss(self.w,self.r,'propose',self.payload(key='valid'),Mock(return_value={'replacement':json.dumps({'changes':[change]}),'explanation':'The agreed change.'}))
        self.assertEqual(turn['proposal']['changes'],[change])
        self.assertEqual(self.service.get(self.w,self.r)['revision'],0)

    def test_failed_request_is_not_silently_resubmitted(self):
        provider = Mock(side_effect=RuntimeError('Provider interrupted.'))
        with self.assertRaises(RuntimeError):self.service.discuss(self.w,self.r,'chat',self.payload(),provider)
        with self.assertRaises(LedgerConflict):self.service.discuss(self.w,self.r,'chat',self.payload(),provider)
        self.assertEqual(provider.call_count,1)

    def test_project_checkpoint_restores_lessons_briefs_and_conversation(self):
        self.save(lessons=[{'scope':'all','rule':'Keep prompts concise.'}], assets={self.target:'A retained brief.'})
        self.service.discuss(self.w,self.r,'chat',self.payload(),Mock(return_value={'replacement':'Agreed.','explanation':'Discussion'}))
        folder = Path(self.temp.name)/'project'; folder.mkdir()
        projects.save(self.root,self.w,folder,{})
        fresh = Path(self.temp.name)/'fresh'
        restored_story = StoryAuthoring(ProductionLedger(fresh/projects.DATABASES[0]),data_root=fresh)
        restored = PromptDirector(restored_story.ledger,restored_story)
        projects.open_project(fresh,folder)
        value = restored.get(self.w,self.r)
        self.assertEqual(value['assets'][self.target],'A retained brief.')
        self.assertEqual(value['lessons'][0]['rule'],'Keep prompts concise.')
        self.assertEqual(value['items'][0]['reply'],'Agreed.')

    def test_http_image_preparation_consumes_saved_brief_and_scoped_rule(self):
        from story_builder.isolated_server import create_app
        char = next(key for key, target in self.state['targets'].items() if target['scope'] == 'character')
        self.save(lessons=[{'scope':'character','rule':'Keep the white studio background.'},
                           {'scope':'world','rule':'Keep the building geometry.'}], assets={char:'Owner-approved clothing brief.'})
        provider = Mock(return_value={'prompt':'Mira alone against white.'})
        app = create_app(data_root=self.root, reasoning_json_provider=provider)
        def request(path, method='GET', payload=None):
            statuses=[]; body=json.dumps(payload).encode() if payload is not None else b''
            response=json.loads(b''.join(app({'REQUEST_METHOD':method,'PATH_INFO':path,'QUERY_STRING':'',
                'CONTENT_TYPE':'application/json','CONTENT_LENGTH':str(len(body)),'wsgi.input':io.BytesIO(body)},lambda status, headers:statuses.append(status))))
            self.assertEqual(statuses,['200 OK'],response)
            return response
        self.assertEqual(request(f'/api/story/workspaces/{self.w}/prompt-director/{self.r}')['assets'][char],'Owner-approved clothing brief.')
        result = request('/api/images/prompts/prepare','POST',{'workspace_id':self.w,'screenplay_revision_id':self.r,
            'target_record_id':char,'asset_role':'character_master','workflow_id':'qwen_image_2512','prompt':''})
        self.assertEqual(result['prompt'],'Mira alone against white.')
        context=provider.call_args.kwargs['prompt']
        self.assertIn('Owner-approved clothing brief.',context)
        self.assertIn('Keep the white studio background.',context)
        self.assertNotIn('Keep the building geometry.',context)
        self.assertIn('WORKFLOW GUIDANCE:',context)


if __name__ == '__main__':unittest.main()
