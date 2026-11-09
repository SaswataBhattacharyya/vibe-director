import io
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from story_builder.isolated_server import create_app
from story_builder.services import agent_graph, projects, video_repertoire


class AgentApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='vibe-agent-test-')
        self.root = Path(self.temp.name)
        self.addCleanup(self.cleanup)
        self.app = create_app(data_root=self.root)
        self.a, self.b = 'story-aaaaaaaaaaaa', 'story-bbbbbbbbbbbb'
        with sqlite3.connect(projects.database_path(self.root, projects.DATABASES[0])) as db:
            for ident in (self.a, self.b):
                db.execute('INSERT INTO story_workspaces(workspace_id,title,authoring_uuid) VALUES (?,?,?)', (ident, ident, ident))

    def cleanup(self):
        video_repertoire.configure_roots(self.root / 'reset')
        self.temp.cleanup()
        self.assertFalse(self.root.exists(), 'Test-owned storage survived cleanup')

    def call(self, path, query='', method='GET'):
        response = []
        env = {'PATH_INFO': path, 'QUERY_STRING': query, 'REQUEST_METHOD': method,
            'CONTENT_LENGTH': '0', 'wsgi.input': io.BytesIO()}
        body = b''.join(self.app(env, lambda status, headers: response.append(status)))
        return response[0], json.loads(body)

    def activate(self, owner):
        path = self.root / 'library/projects/active.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({'workspace_id': owner}))

    def test_strict_routes_and_no_execution(self):
        with patch('subprocess.run', side_effect=AssertionError('Discovery launched a command')), \
             patch.object(video_repertoire, 'start_job', side_effect=AssertionError('Discovery dispatched work')), \
             patch('story_builder.services.agent_tools.shutil.which', return_value=None):
            status, value = self.call('/api/agent/tools', 'workspace_id=tool-library')
            self.assertEqual(status, '200 OK')
            self.assertEqual(len(value['tools']), len({t['id'] for t in value['tools']}))
            unavailable = {'audio.extract_mp3', 'video.continuity_last_frame', 'video.compare_clip_overlap', 'computer.execute'}
            self.assertTrue(all(t['status'] == 'blocked' and t['execution_enabled'] is False
                                for t in value['tools'] if t['id'] in unavailable))
            self.assertEqual(next(t['status'] for t in value['tools'] if t['id'] == 'editor.prepare_brief'), 'available')
            self.assertEqual(self.call('/api/agent/tools', 'workspace_id=tool-library', 'POST')[0], '405 Method Not Allowed')
            self.assertEqual(self.call('/api/agent/run')[0], '404 Not Found')
        for query in ('', 'workspace_id=', 'workspace_id=../x', 'workspace_id=tool-library&actor=x',
                      'workspace_id=tool-library&workspace_id=tool-library', 'workspace_id=' + self.a):
            with self.subTest(query=query):
                self.assertNotEqual(self.call('/api/agent/tools', query)[0], '200 OK')
        self.activate(self.a)
        self.assertEqual(self.call('/api/agent/tools', 'workspace_id=' + self.a)[0], '200 OK')
        self.assertNotEqual(self.call('/api/agent/tools', 'workspace_id=' + self.b)[0], '200 OK')
        self.assertNotEqual(self.call('/api/agent/projects/' + self.a + '/context', 'extra=x')[0], '200 OK')

    def test_context_has_source_ids_and_no_hidden_writes_or_cross_owner_data(self):
        from story_builder.services.storage_paths import media_root, project_root
        self.activate(self.a)
        with sqlite3.connect(projects.database_path(self.root, projects.DATABASES[0])) as db:
            db.execute("INSERT INTO story_revision_index(revision_id,workspace_id,revision_number,source_sha256,metadata_json) VALUES (?,?,?,?,?)", ('rev-a', self.a, 7, 'a'*64, '{}'))
            db.execute('UPDATE story_workspaces SET current_revision_id=? WHERE workspace_id=?', ('rev-a', self.a))
        manifest = media_root(self.root, self.a) / 'assets.json'
        manifest.parent.mkdir(parents=True)
        manifest.write_text(json.dumps({'schema_version': 1, 'assets': [
            {'asset_id': 'pa-a', 'workspace_id': self.a, 'sha256': 'b'*64, 'filename': 'owned.wav'},
            {'asset_id': 'pa-b', 'workspace_id': self.b, 'filename': 'secret.wav'}]}))
        session = project_root(self.root, self.a) / 'editor/editor/edit-a/project.json'
        session.parent.mkdir(parents=True)
        session.write_text(json.dumps({'id': 'edit-a', 'workspace_id': self.a, 'revision': 3, 'job_id': 'vibe-editor-abcdef'}))
        state = self.root / 'services/editor/state.json'
        state.parent.mkdir(parents=True, exist_ok=True)
        state.write_text(json.dumps({'project_files': [session.relative_to(self.root).as_posix()]}))
        job = self.root / 'services/media/jobs/vibe-editor/vibe-editor-abcdef/job.json'
        job.parent.mkdir(parents=True)
        job.write_text(json.dumps({'job_id': 'vibe-editor-abcdef', 'status': 'running', 'pid': 999999,
            'request': {'workspace_id': self.a, 'secret': 'must not leak'}}))
        def snapshot():
            return {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob('*') if p.is_file() and not p.name.endswith('-shm')}
        # SQLite read locks update volatile WAL shared-memory bookkeeping, never application records.
        before = snapshot()
        with patch('story_builder.services.media_library.list_assets', side_effect=AssertionError('Discovery write')), \
             patch.object(video_repertoire, 'read_job', side_effect=AssertionError('Recovery write')):
            status, result = self.call('/api/agent/projects/' + self.a + '/context')
            self.assertEqual(status, '200 OK', result)
        self.assertEqual(before, snapshot())
        nodes = {n['source_id']: n for n in result['nodes']}
        self.assertEqual(nodes['rev-a']['revision'], 7)
        self.assertEqual(nodes['pa-a']['sha256'], 'b'*64)
        self.assertEqual(nodes['edit-a']['owner'], self.a)
        self.assertEqual(nodes['vibe-editor-abcdef']['label'], 'running')
        self.assertNotIn('pa-b', nodes)
        self.assertNotIn('secret', json.dumps(result))
        self.assertNotIn(str(self.root), json.dumps(result))

    def test_empty_standalone_and_missing_project(self):
        status, value = self.call('/api/agent/projects/tool-library/context')
        self.assertEqual(status, '200 OK')
        self.assertEqual([n['kind'] for n in value['nodes']], ['workspace'])
        self.activate('story-cccccccccccc')
        self.assertNotEqual(self.call('/api/agent/tools', 'workspace_id=story-cccccccccccc')[0], '200 OK')
        self.activate(self.a)
        status, value = self.call('/api/agent/projects/' + self.a + '/context')
        self.assertEqual(status, '200 OK')
        self.assertEqual(len(value['nodes']), 1)
