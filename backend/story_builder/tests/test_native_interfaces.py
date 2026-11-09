"""Disposable native workspace mapping, ownership, stale revisions and mirror cleanup."""
import json
import io
import unittest
from unittest.mock import patch
from pathlib import Path

from story_builder.services import editor_studio, interface_sessions, production_board, vibe_editor
from story_builder.tests import test_storyboard as fixtures


class NativeInterfacesTests(unittest.TestCase):
    save = fixtures.StoryboardTests.save

    def setUp(self):
        fixtures.StoryboardTests.setUp(self)
        self.addCleanup(self.cleanup)
        self.sessions = []
        body = self.board.get(self.w, self.r)['body']
        body['shots']['1.1']['image_asset_id'] = self.asset['asset_id']
        self.saved = self.save(body)
        self.editor = self.board.editor_handoff(self.w, self.r)
        with vibe_editor.state(self.root) as data:
            vibe_editor.project(data, self.editor['id'])['brief'] = {'summary': 'Fixture edit', 'questions': []}
        self.plan = {'width': 320, 'height': 180, 'fps': 24, 'audio': None,
                     'clips': [{**self.editor['selection'][0], 'caption': 'Original'}]}

    def cleanup(self):
        for s in self.sessions:
            if s['folder'].exists():
                interface_sessions.close(s)
            self.assertFalse(s['folder'].exists())
        self.temp.cleanup()
        self.assertFalse(Path(self.temp.name).exists())

    def stage(self):
        s = editor_studio.stage(self.root, self.editor['id'], {'revision': self.editor['revision'], 'plan': self.plan})
        self.sessions.append(s)
        return s

    def test_native_edits_become_pending_proposal_and_stale_import_is_rejected(self):
        s = self.stage()
        file = s['folder'] / 'index.html'
        file.write_text(file.read_text().replace('>Original</div>', '>Native caption</div>').replace('data-duration="2.0"', 'data-duration="1.4"'))
        value = editor_studio.operate(self.root, self.editor['id'], {'token': s['token'], 'action': 'import'})
        self.assertEqual(value['pending']['value']['clips'][0]['caption'], 'Native caption')
        self.assertAlmostEqual(value['pending']['value']['clips'][0]['end'], 1.4)
        self.assertEqual(value['pending']['kind'], 'plan')
        self.assertFalse(value.get('job_id'))
        self.assertFalse(s['folder'].exists())
        self.editor = value
        s = self.stage()
        vibe_editor.propose_plan(self.root, self.editor['id'], {'revision': value['revision'], 'plan': self.plan})
        with self.assertRaisesRegex(ValueError, 'Stale'):
            editor_studio.operate(self.root, self.editor['id'], {'token': s['token'], 'action': 'import'})

    def test_ownership_ranges_unknown_layers_and_invalid_timing_fail_without_mutation(self):
        before = vibe_editor.snapshot(self.root)
        s = self.stage()
        with self.assertRaises(ValueError):
            interface_sessions.get(self.root, s['token'], 'studio', 'foreign')
        file = s['folder'] / 'index.html'
        original = file.read_text()
        for text in (original.replace('data-media-start="0.0"', 'data-media-start="100"'),
                     original.replace('data-duration="2.0"', 'data-duration="NaN"'),
                     original.replace('</body>', '<div id="unsupported-layer"></div></body>')):
            file.write_text(text)
            with self.assertRaises(ValueError):
                editor_studio.operate(self.root, self.editor['id'], {'token': s['token'], 'action': 'import'})
        self.assertEqual(vibe_editor.snapshot(self.root), before)

    def test_backlot_mirror_is_playable_refreshes_and_preserves_original(self):
        s = interface_sessions.create(self.root, 'backlot', (self.w, self.r))
        self.sessions.append(s)
        first = production_board.sync(self.board, s, self.saved['revision'])
        folder = s['folder'] / 'projects/production'
        manifest = json.loads((folder / 'artifacts/asset_manifest.json').read_text())
        asset, = manifest['assets']
        self.assertEqual((folder / asset['path']).read_bytes(), self.png)
        self.assertNotIn('content_url', asset)
        body = self.saved['body']
        body['shots']['1.1']['prompt'] = 'Updated saved prompt'
        saved = self.save(body)
        result = production_board.operate(self.board, self.w, self.r, {'token': s['token'], 'action': 'sync'})
        self.assertGreater(result['revision'], first['revision'])
        scene = json.loads((folder / 'artifacts/scene_plan.json').read_text())['scenes'][0]
        self.assertEqual(scene['description'], 'Updated saved prompt')
        self.assertFalse(result['write_back'])
        self.assertEqual(self.board.get(self.w, self.r), saved)
        with self.assertRaises(ValueError):
            production_board.operate(self.board, 'foreign', self.r, {'token': s['token'], 'action': 'sync'})

    def test_failed_launch_cleans_owned_folder_and_close_is_idempotent(self):
        s = self.stage()
        with self.assertRaises(FileNotFoundError):
            interface_sessions.launch(s, ['/nonexistent/vibe-test-owned-executable'])
        self.assertFalse(s['folder'].exists())
        interface_sessions.close(s)
        with self.assertRaises(ValueError):
            interface_sessions.get(self.root, [], 'studio', self.editor['id'])

    def test_http_routes_reach_owned_interface_adapters(self):
        from story_builder.isolated_server import create_app
        app = create_app(data_root=self.root)
        for path, module, body in [
            (f'/api/editor/projects/{self.editor["id"]}/studio', editor_studio,
             {'revision': self.editor['revision'], 'plan': self.plan}),
            (f'/api/story/workspaces/{self.w}/storyboard/{self.r}/backlot', production_board,
             {'expected_revision': self.saved['revision']})]:
            raw = json.dumps(body).encode()
            response = []
            with patch.object(module, 'open_workspace', return_value={'token': 'fixture', 'revision': 1}) as call:
                result = b''.join(app({'PATH_INFO': path, 'QUERY_STRING': '', 'REQUEST_METHOD': 'POST',
                    'CONTENT_TYPE': 'application/json', 'CONTENT_LENGTH': str(len(raw)), 'wsgi.input': io.BytesIO(raw)},
                    lambda status, headers: response.append(status)))
                self.assertEqual(response, ['200 OK'])
                self.assertEqual(json.loads(result)['token'], 'fixture')
                self.assertEqual(call.call_args.args[-1], body)

    def test_changed_registered_bytes_cannot_open_studio(self):
        path = editor_studio.media_library.asset_path(self.root, self.w, self.asset['asset_id'])[0]
        path.write_bytes(self.png + b'changed')
        with self.assertRaisesRegex(ValueError, 'source bytes changed'):
            self.stage()
