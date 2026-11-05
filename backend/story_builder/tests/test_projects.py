"""Project ownership/checkpoint recovery without providers or generation."""
import json
import sqlite3
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from story_builder.services import projects, vibe_editor, output_destinations as out
from story_builder.services.production_ledger import ProductionLedger
from story_builder.services.story_authoring import StoryAuthoring

class ProjectTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name); self.root = self.base / 'runtime'
        self.story = self.initialize(self.root); self.folder = self.base / 'my project'; self.folder.mkdir()

    def initialize(self, root):
        return StoryAuthoring(ProductionLedger(root / projects.DATABASES[0]), data_root=root)

    def call(self, operation, **body):
        return projects.handle(self.root, self.story, {'REQUEST_METHOD': 'POST', 'PATH_INFO': '/api/projects/' + operation},
            None, lambda _: body, lambda _, status, data: data)

    def test_open_named_legacy_folder_preserves_identity_and_source(self):
        from story_builder.services.storage_paths import project_root
        item = self.story.create_workspace(title='Existing story', source_text='Already saved source')
        workspace = item['workspace_id']
        original = project_root(self.root, workspace)
        original.mkdir(parents=True, exist_ok=True)
        named = original.with_name('Existing story'); original.rename(named)
        (self.root / 'library').mkdir(exist_ok=True)
        (self.root / 'library/project-folders.json').write_text(json.dumps({workspace: named.name}))
        opened = self.call('open', folder=str(named))
        self.assertEqual(opened['workspace_id'], workspace)
        self.assertEqual(opened['folder'], str(named))
        self.assertEqual(self.story.get_workspace(workspace)['current_revision']['source_text'], 'Already saved source')
        self.call('save', workspace_id=workspace, folder=str(named))
        self.call('save', workspace_id=workspace, folder=str(named))
        manifest = json.loads((named / 'vibe-project.json').read_text())
        state = json.loads((named / manifest['state_path']).read_text())
        self.assertFalse(any('project-data' in Path(entry['path']).parts for entry in state['files']))
        fresh = self.base / 'fresh-legacy'; fresh_story = self.initialize(fresh)
        restored = projects.open_project(fresh, named)
        self.assertEqual(restored['workspace_id'], workspace)
        self.assertEqual(fresh_story.get_workspace(workspace)['current_revision']['source_text'], 'Already saved source')

    def test_new_named_child_defaults_to_projects_and_reopens_with_same_identity(self):
        created = self.call('new', title='Lion and Mouse', parent_folder='')
        folder = self.root / 'projects/Lion and Mouse'
        self.assertEqual(created['folder'], str(folder))
        self.assertTrue((folder / 'vibe-project.json').is_file())
        self.assertTrue((folder / 'outputs').is_dir())
        self.assertEqual(projects.project_root(self.root, created['workspace_id']), folder)
        self.assertEqual(projects.current(self.root)['folder'], str(folder))
        self.assertEqual(projects.current(self.root)['projects_folder'], str(self.root / 'projects'))
        source = self.story.write_revision(workspace_id=created['workspace_id'], source_text='The lion frees the mouse.', expected_current_revision_id=None)
        self.call('save', workspace_id=created['workspace_id'])
        self.call('select', workspace_id='tool-library')
        opened = self.call('open', folder=str(folder))
        self.assertEqual(opened['workspace_id'], created['workspace_id'])
        self.assertEqual(self.story.get_workspace(created['workspace_id'])['current_revision_id'], source['revision_id'])
        with self.assertRaisesRegex(ValueError, 'already exists'):
            self.call('new', title='Lion and Mouse', parent_folder='')
        self.assertEqual(projects.current(self.root)['workspace_id'], created['workspace_id'])

    def test_new_child_supports_external_parent_and_cannot_escape_or_use_runtime(self):
        created = self.call('new', title='../../A story', parent_folder=str(self.folder))
        self.assertEqual(created['folder'], str(self.folder / 'A story'))
        with self.assertRaisesRegex(ValueError, 'outside source'):
            self.call('new', title='Forbidden', parent_folder=str(self.root))
        with self.assertRaisesRegex(ValueError, 'already exists'):
            self.call('new', title='A story', parent_folder=str(self.folder))
        self.assertEqual(projects.current(self.root)['workspace_id'], created['workspace_id'])

    def test_unregistered_and_forged_internal_folders_cannot_open(self):
        unknown = self.root / 'projects/unknown'; unknown.mkdir(parents=True)
        (unknown / 'vibe-project.json').write_text(json.dumps({'workspace_id':'story-aaaaaaaaaaaa'}))
        with self.assertRaisesRegex(ValueError, 'outside source'):
            self.call('open', folder=str(unknown))
        item = self.story.create_workspace(title='Existing', source_text='Source')
        from story_builder.services.storage_paths import project_root
        folder = project_root(self.root, item['workspace_id']); (folder / 'media').mkdir(parents=True, exist_ok=True)
        (folder / 'media/workspace.json').write_text(json.dumps({'workspace_id':'story-aaaaaaaaaaaa'}))
        with self.assertRaisesRegex(ValueError, 'ownership'):
            self.call('open', folder=str(folder))
        with self.assertRaisesRegex(ValueError, 'outside source'):
            self.call('new', title='Wrong destination', folder=str(folder))

    def test_new_save_open_round_trip_scopes_story_and_editor_memory(self):
        a = self.call('new', title='Project A', folder=str(self.folder)); workspace = a['workspace_id']
        revision = self.story.write_revision(workspace_id=workspace, source_text='Storyboard A', expected_current_revision_id=None)
        # Persist a synthetic accepted screenplay to exercise the exact restore contract.
        screenplay = {'title': 'Already prepared', 'scenes': [{'scene_number': 1, 'shots': []}]}
        with sqlite3.connect(self.root / projects.DATABASES[0]) as db:
            db.execute("INSERT INTO story_graph_snapshots(snapshot_id,workspace_id,source_revision_id,source_sha256,idempotency_key,request_hash,status,chunk_total,coverage_state,provider) VALUES(?,?,?,?,?,?,?,?,?,?)",
                       ('graph-fixture', workspace, revision['revision_id'], '0'*64, 'graph-key', 'request', 'complete', 0, 'complete', 'fixture'))
            db.execute("INSERT INTO story_screenplay_revisions(screenplay_revision_id,workspace_id,source_revision_id,graph_snapshot_id,screenplay_json,idempotency_key,accepted_at) VALUES(?,?,?,?,?,?,?)",
                       ('screenplay-fixture', workspace, revision['revision_id'], 'graph-fixture', json.dumps(screenplay), 'screenplay-key', '2026-11-04'))
        session = vibe_editor.add_project(self.root, {'workspace_id': workspace, 'name': 'Edit A'})
        b = self.story.create_workspace(title='Unrelated B', source_text='Private B')
        memory = {'vibe-create-chat:' + workspace + ':clip': '[{"text":"Remember A"}]'}
        self.call('save', workspace_id=workspace, folder=str(self.folder), browser_state=memory)
        manifest = json.loads((self.folder / 'vibe-project.json').read_text())
        state = json.loads((self.folder / 'project-data' / manifest['checkpoint'] / 'state.json').read_text())
        self.assertNotIn(b['workspace_id'], json.dumps(state)); self.assertNotIn('Private B', json.dumps(state))
        fresh = self.base / 'new-runtime'; fresh_story = self.initialize(fresh)
        restored = projects.open_project(fresh, self.folder)
        self.assertEqual(restored['browser_state'], memory)
        self.assertEqual(fresh_story.get_workspace(workspace)['current_revision']['source_text'], 'Storyboard A')
        self.assertEqual(fresh_story.get_workspace(workspace)['current_revision_id'], revision['revision_id'])
        self.assertEqual(vibe_editor.snapshot(fresh)['projects'][0]['id'], session['id'])
        recovered = fresh_story.get_screenplay(workspace_id=workspace, source_revision_id=revision['revision_id'])
        self.assertEqual(recovered['screenplay'], screenplay)
        self.assertTrue(recovered['accepted'])
        self.assertEqual(len(fresh_story.list_workspaces()['items']), 1)

    def test_reopen_preserves_newer_local_memory_and_story(self):
        a = self.call('new', title='A', folder=str(self.folder)); workspace = a['workspace_id']
        self.story.write_revision(workspace_id=workspace, source_text='New work after Save', expected_current_revision_id=None)
        self.call('memory', workspace_id=workspace, browser_state={'vibe-studio-chat-test': 'new conversation'})
        self.call('select', workspace_id='tool-library')
        reopened = self.call('open', folder=str(self.folder))
        self.assertIn('new conversation', json.dumps(reopened['browser_state']))
        self.assertEqual(self.story.get_workspace(workspace)['current_revision']['source_text'], 'New work after Save')

    def test_deleted_project_is_not_resurrected(self):
        a = self.call('new', title='A', folder=str(self.folder))
        (self.root / 'library/deleted-projects.json').write_text(json.dumps([a['workspace_id']]))
        self.assertEqual(projects.current(self.root)['workspace_id'], 'tool-library')
        with self.assertRaises(ValueError): projects.open_project(self.root, self.folder)

    def test_moved_folder_preserves_newer_local_work_and_rebases_output(self):
        a = self.call('new', title='A', folder=str(self.folder)); workspace = a['workspace_id']
        self.story.write_revision(workspace_id=workspace, source_text='Newer unsaved story', expected_current_revision_id=None)
        moved = self.base / 'moved'; self.folder.rename(moved)
        reopened = self.call('open', folder=str(moved))
        self.assertEqual(reopened['folder'], str(moved))
        self.assertEqual(self.story.get_workspace(workspace)['current_revision']['source_text'], 'Newer unsaved story')
        self.assertEqual(out.preference(self.root, 'video-generation', workspace)['path'], str(moved / 'outputs/videos'))

    def test_completed_3d_result_travels_without_its_external_destination(self):
        from story_builder.services import trellis_studio as studio, video_repertoire as jobs
        from story_builder.tests.test_studio_tools import glb
        a = self.call('new', title='A', folder=str(self.folder)); workspace = a['workspace_id']
        jobs.configure_roots(self.root); self.addCleanup(jobs.configure_roots, self.root)
        job = jobs.create_job('trellis', {'workspace_id':workspace,'items':[]})
        path = studio.output_folder(self.root, None) / job['job_id'] / '0001.glb'
        path.parent.mkdir(parents=True); path.write_bytes(glb())
        studio.write(studio.home(self.root)/'batches'/f"{job['job_id']}.json", {'items':[{'index':1,'status':'completed','sha256':studio.validate_glb(path)}]})
        job_path = self.root/'services/media/jobs/trellis'/job['job_id']/'job.json'
        value = json.loads(job_path.read_text()); value['status']='completed'; studio.write(job_path,value)
        self.call('save', workspace_id=workspace, folder=str(self.folder))
        fresh = self.base/'fresh'; self.initialize(fresh); projects.open_project(fresh,self.folder)
        jobs.configure_roots(fresh)
        recovered = studio.result_path(fresh,job['job_id'],1)
        self.assertEqual(recovered.read_bytes(),glb())
        recovered.write_bytes(b'changed')
        with self.assertRaises(ValueError): studio.result_path(fresh,job['job_id'],1)

    def test_failed_save_keeps_last_good_checkpoint(self):
        a = self.call('new', title='A', folder=str(self.folder)); before = (self.folder / 'vibe-project.json').read_bytes()
        with patch.object(projects, 'owned_files', side_effect=OSError('disk failure')):
            with self.assertRaises(OSError): projects.save(self.root, a['workspace_id'], self.folder, {})
        self.assertEqual((self.folder / 'vibe-project.json').read_bytes(), before)
        self.assertEqual(len(list((self.folder / 'project-data').iterdir())), 1)

    def test_edit_during_save_keeps_the_previous_manifest(self):
        a = self.call('new', title='A', folder=str(self.folder)); workspace = a['workspace_id']
        original = (self.folder / 'vibe-project.json').read_bytes()
        document = projects.project_root(self.root, workspace) / 'draft.json'
        document.parent.mkdir(parents=True, exist_ok=True)
        document.write_text('before')
        copy = projects.shutil.copy2
        def mutate(source, target):
            result = copy(source, target)
            if source == document: document.write_text('newer edit')
            return result
        with patch.object(projects.shutil, 'copy2', side_effect=mutate):
            with self.assertRaisesRegex(ValueError, 'Project changed while saving'):
                self.call('save', workspace_id=workspace, folder=str(self.folder))
        self.assertEqual((self.folder / 'vibe-project.json').read_bytes(), original)
        self.assertEqual(document.read_text(), 'newer edit')

    def test_open_rejects_an_imported_job_that_could_replay(self):
        a = self.call('new', title='A', folder=str(self.folder)); workspace = a['workspace_id']
        path = self.root / 'services/media/jobs/analysis/saved/job.json'; path.parent.mkdir(parents=True)
        projects.write(path, {'status':'completed','request':{'workspace_id':workspace}})
        self.call('save', workspace_id=workspace, folder=str(self.folder))
        manifest = projects.read(self.folder / 'vibe-project.json')
        base = self.folder / 'project-data' / manifest['checkpoint']; state = projects.read(base / 'state.json')
        item = next(item for item in state['files'] if item['path'].endswith('/job.json'))
        projects.write(base / item['path'], {'status':'queued','request':{'workspace_id':workspace}})
        item['sha256'] = projects.digest(base / item['path']); projects.write(base / 'state.json',state)
        manifest['state_sha256'] = projects.digest(base / 'state.json'); projects.write(self.folder / 'vibe-project.json',manifest)
        fresh = self.base / 'fresh'; story = self.initialize(fresh)
        with self.assertRaisesRegex(ValueError, 'must be settled'): projects.open_project(fresh,self.folder)
        self.assertEqual(story.list_workspaces()['items'],[])
        self.assertFalse((fresh / 'services/media/jobs/analysis/saved/job.json').exists())

    def test_tampering_symlinks_and_secrets_rejected(self):
        self.call('new', title='A', folder=str(self.folder))
        manifest = json.loads((self.folder / 'vibe-project.json').read_text())
        (self.folder / 'project-data' / manifest['checkpoint'] / 'state.json').write_text('{}')
        with self.assertRaises(ValueError): projects.open_project(self.root, self.folder)
        linked = self.base / 'link'; linked.symlink_to(self.folder, target_is_directory=True)
        with self.assertRaises(ValueError): projects.folder_path(linked)
        with self.assertRaises(ValueError): projects.browser_state({'vibe-provider-token': 'secret'})

    def test_output_default_and_override_do_not_change_project(self):
        a = self.call('new', title='A', folder=str(self.folder)); workspace = a['workspace_id']
        self.assertEqual(out.preference(self.root, 'video-generation', workspace)['path'], str(self.folder / 'outputs/videos'))
        other = self.base / 'external output'; other.mkdir(); selected = out.grant(self.root, str(other))
        out.preference(self.root, 'video-generation', workspace, {'mode': 'folder', 'grant': selected['grant']})
        self.assertEqual(projects.current(self.root)['workspace_id'], workspace)
        self.assertEqual(out.preference(self.root, 'video-generation', workspace)['path'], str(other))

    def test_active_job_blocks_switch(self):
        a = self.call('new', title='A', folder=str(self.folder))
        job = self.root / 'services/media/jobs/analysis/job-one/job.json'; job.parent.mkdir(parents=True)
        job.write_text(json.dumps({'status': 'running', 'request': {'workspace_id': a['workspace_id']}}))
        with self.assertRaisesRegex(ValueError, 'active media job'): self.call('select', workspace_id='tool-library')
        self.assertEqual(projects.current(self.root)['workspace_id'], a['workspace_id'])

    def test_checkpoint_media_survives_missing_external_output(self):
        from story_builder.services import media_library
        from story_builder.tests.test_music_jukebox import wav
        a = self.call('new', title='A', folder=str(self.folder)); workspace = a['workspace_id']
        asset = media_library.register_upload(self.root, workspace, filename='tone.wav', content=wav(), role='project_audio')
        external = self.base / 'external'; external.mkdir()
        selected = out.grant(self.root, str(external))
        media_library.relocate_output(self.root, workspace, asset['asset_id'], {'mode':'folder', **selected}, 'job-one')
        self.call('save', workspace_id=workspace, folder=str(self.folder))
        fresh = self.base / 'fresh'; self.initialize(fresh)
        for file in external.rglob('*'):
            if file.is_file(): file.unlink()
        projects.open_project(fresh, self.folder)
        path, _, filename = media_library.asset_path(fresh, workspace, asset['asset_id'])
        self.assertEqual(filename, 'tone.wav'); self.assertEqual(path.read_bytes(), wav())

    def test_second_database_conflict_rolls_back_first(self):
        import sqlite3
        a = self.call('new', title='A', folder=str(self.folder)); workspace = a['workspace_id']
        with sqlite3.connect(self.root / projects.DATABASES[1]) as db:
            db.execute('CREATE TABLE sample(id TEXT PRIMARY KEY, workspace_id TEXT, value TEXT)')
            db.execute('INSERT INTO sample VALUES(?,?,?)', ('same', workspace, 'saved'))
        self.call('save', workspace_id=workspace, folder=str(self.folder))
        fresh = self.base / 'fresh'; story = self.initialize(fresh)
        with sqlite3.connect(fresh / projects.DATABASES[1]) as db:
            db.execute('CREATE TABLE sample(id TEXT PRIMARY KEY, workspace_id TEXT, value TEXT)')
            db.execute('INSERT INTO sample VALUES(?,?,?)', ('same', workspace, 'newer'))
        with self.assertRaisesRegex(ValueError, 'Newer local project records'): projects.open_project(fresh, self.folder)
        self.assertEqual(story.list_workspaces()['items'], [])
        self.assertFalse((fresh / 'library/projects/active.json').exists())

    def test_failed_new_project_leaves_no_story_row(self):
        with patch.object(projects, 'save', side_effect=OSError('disk full')):
            with self.assertRaises(OSError): self.call('new', title='A', folder=str(self.folder))
        self.assertEqual(self.story.list_workspaces()['items'], [])

    def test_custom_database_path_and_3d_inputs_jukebox_restore(self):
        from story_builder.services import music_jukebox as music
        from story_builder.tests.test_music_jukebox import project
        a = self.call('new', title='A', folder=str(self.folder)); workspace = a['workspace_id']
        session = music.save(self.root, {'project': {**project(), 'workspace_id': workspace}}, True)
        token = 'a' * 32
        path = self.root / 'trellis.2/input' / (token + '.png'); path.parent.mkdir(parents=True); path.write_bytes(b'input')
        memory = {'vibe-trellis-draft': json.dumps({'inputs':[{'id': token}]})}
        self.call('save', workspace_id=workspace, folder=str(self.folder), browser_state=memory)
        fresh = self.base / 'fresh'; custom = fresh / 'alternate/ledger.sqlite3'
        story = StoryAuthoring(ProductionLedger(custom), data_root=fresh)
        projects.configure(fresh, custom, fresh / 'alternate/images.sqlite3')
        projects.open_project(fresh, self.folder)
        self.assertEqual(story.get_workspace(workspace)['title'], 'A')
        self.assertEqual((fresh / 'trellis.2/input' / (token + '.png')).read_bytes(), b'input')
        self.assertEqual(music.snapshot(fresh, workspace)['projects'][0]['id'], session['id'])
        self.assertEqual(json.loads(music.project_path(fresh, session['id']).read_text())['workspace_id'], workspace)

    def test_moved_folder_restores_ace_dataset_adapter_and_output(self):
        import shutil
        from story_builder.services import ace_studio
        a = self.call('new', title='A', folder=str(self.folder)); workspace=a['workspace_id']
        session=ace_studio.add_project(self.root, {'workspace_id':workspace,'name':'Music'})
        dataset=self.root/'ace_step/datasets'/session['id']/'prepared';dataset.mkdir(parents=True);(dataset/'song.wav').write_bytes(b'dataset')
        adapter=self.root/'ace_step/runs/ace-123456789abc/training/saved_lora';adapter.mkdir(parents=True);(adapter/'model.safetensors').write_bytes(b'weights')
        with ace_studio.state(self.root) as data:
            value=ace_studio.project(data,session['id']);value['dataset']={'path':str(dataset),'count':1};value['adapters']=[{'id':'trained','path':str(adapter)}]
        self.call('save',workspace_id=workspace,folder=str(self.folder))
        moved=self.base/'moved project';shutil.move(self.folder,moved)
        fresh=self.base/'fresh';self.initialize(fresh);projects.open_project(fresh,moved)
        restored=ace_studio.snapshot(fresh)['projects'][0]
        self.assertEqual((Path(restored['dataset']['path'])/'song.wav').read_bytes(),b'dataset')
        self.assertEqual((Path(restored['adapters'][0]['path'])/'model.safetensors').read_bytes(),b'weights')
        self.assertEqual(out.preference(fresh,'video-generation',workspace)['path'],str(moved/'outputs/videos'))

    def test_invalid_preference_rejected_before_importing_story(self):
        import hashlib
        self.call('new',title='A',folder=str(self.folder))
        manifest_path=self.folder/'vibe-project.json';manifest=json.loads(manifest_path.read_text());state_path=self.folder/'project-data'/manifest['checkpoint']/'state.json'
        state=json.loads(state_path.read_text());state['preferences']={'../../bad':{'choice':{'grant':'a'*32},'path':'/tmp'}};state_path.write_text(json.dumps(state));manifest['state_sha256']=hashlib.sha256(state_path.read_bytes()).hexdigest();manifest_path.write_text(json.dumps(manifest))
        fresh=self.base/'fresh';story=self.initialize(fresh)
        with self.assertRaisesRegex(ValueError,'Invalid output preference'):projects.open_project(fresh,self.folder)
        self.assertEqual(story.list_workspaces()['items'],[])

    def test_checkpoint_preserves_music_export_even_without_library_registration(self):
        from story_builder.services import music_jukebox as music
        from story_builder.tests.test_music_jukebox import project,wav
        a=self.call('new',title='A',folder=str(self.folder));workspace=a['workspace_id']
        session=music.save(self.root,{'project':{**project(),'workspace_id':workspace}},True)
        job_id='music-jukebox-123456789abc';job=self.root/'services/media/jobs/music-jukebox'/job_id/'job.json';job.parent.mkdir(parents=True)
        job.write_text(json.dumps({'job_id':job_id,'status':'completed','request':{'workspace_id':workspace,'project_id':session['id']}}))
        audio=self.base/'mix.wav';audio.write_bytes(wav());record=music.home(self.root)/'exports'/f'{job_id}.json';record.parent.mkdir(parents=True);record.write_text(json.dumps({'path':str(audio),'name':audio.name,'project_id':session['id']}))
        self.call('save',workspace_id=workspace,folder=str(self.folder));audio.unlink()
        fresh=self.base/'fresh';self.initialize(fresh);projects.open_project(fresh,self.folder)
        self.assertEqual(music.export_path(fresh,job_id).read_bytes(),wav())
