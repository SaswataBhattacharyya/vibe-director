"""Preview crosses the same selected-plan seam as export, without jobs or writes."""
import io
import json
import subprocess
from unittest.mock import patch
from story_builder.services import editor_composition, editor_preview, media_library, vibe_editor
from story_builder.tests.test_agent_tasks import AgentTaskFixture


class EditorPreviewTests(AgentTaskFixture):
    def setUp(self):
        super().setUp()
        source = self.root / 'preview.mp4'
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'color=c=blue:s=320x180:d=2',
                        '-c:v', 'libx264', '-threads', '1', '-pix_fmt', 'yuv420p', str(source)], check=True)
        self.video = media_library.register_upload(self.root, self.owner, filename='preview.mp4',
            content=source.read_bytes(), role='project_video')
        p = vibe_editor.add_project(self.root, {'workspace_id': self.owner, 'name': 'Preview'})
        self.p = vibe_editor.update_project(self.root, p['id'], {'selection': [
            {'asset_id': self.video['asset_id'], 'start': .25, 'end': 1.75}]})
        self.plan = {'width': 320, 'height': 180, 'fps': 24, 'clips': [
            {**self.p['selection'][0], 'caption': '<script>bad()</script>'}], 'audio': None}

    def preview(self, **changes):
        return editor_preview.prepare(self.root, self.p['id'],
            {'revision': self.p['revision'], 'plan': self.plan, **changes})

    def test_preview_is_readonly_escaped_owned_and_uses_export_markup(self):
        before = vibe_editor.snapshot(self.root)
        with patch.object(vibe_editor, 'write', side_effect=AssertionError('Preview wrote Editor state')):
            result = self.preview()
        self.assertEqual(result['duration'], 1.5)
        self.assertEqual(result['revision'], self.p['revision'])
        self.assertNotIn('<script>bad()', result['document'])
        self.assertIn('&lt;script&gt;bad()', result['document'])
        self.assertIn(f'/api/media/{self.owner}/assets/{self.video["asset_id"]}/content', result['document'])
        validated = vibe_editor.selected_plan(self.root, self.p, self.plan)
        document, duration = editor_composition.document(validated, {self.video['asset_id']: 'owned.mp4'})
        self.assertEqual(duration, result['duration'])
        self.assertIn('data-media-start="0.25"', document)
        self.assertEqual(vibe_editor.snapshot(self.root), before)
        self.dispatch.assert_not_called()

    def test_revision_ownership_range_and_preprocessing_guards(self):
        for revision in (True, -1, self.p['revision']+1):
            with self.assertRaisesRegex(ValueError, 'Stale'):
                self.preview(revision=revision)
        for patch in ({'start': 0}, {'asset_id': self.asset['asset_id']},
                      {'effect': {'preset': 'vhs', 'strength': .5}}, {'speed': {'start': 2, 'end': 2}}):
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                self.preview(plan={**self.plan, 'clips': [{**self.plan['clips'][0], **patch}]})
        with self.assertRaisesRegex(ValueError, 'exactly'):
            self.preview(html='<script>bad()</script>')
        with self.assertRaises(ValueError):
            editor_preview.prepare(self.root, 'other', {'revision': 1, 'plan': self.plan})
        for name in ('../../package.json', 'package.json', 'studio/index.html'):
            with self.assertRaises(ValueError):
                editor_preview.runtime_file(name)

    def test_http_preview_and_allowlisted_runtime(self):
        path=f'/api/editor/projects/{self.p["id"]}/preview'
        raw=json.dumps({'revision': self.p['revision'], 'plan': self.plan}).encode()
        response=[]
        result=b''.join(self.app({'PATH_INFO':path,'QUERY_STRING':'','REQUEST_METHOD':'POST',
            'CONTENT_TYPE':'application/json','CONTENT_LENGTH':str(len(raw)),'wsgi.input':io.BytesIO(raw)},
            lambda status,headers:response.append((status,headers))))
        self.assertEqual(response[0][0],'200 OK')
        self.assertEqual(json.loads(result)['duration'],1.5)
        response=[]
        content=b''.join(self.app({'PATH_INFO':'/api/editor/runtime/runtime.js','REQUEST_METHOD':'GET',
            'QUERY_STRING':'','wsgi.input':io.BytesIO()},lambda status,headers:response.append((status,dict(headers)))))
        self.assertEqual(response[0][1]['Content-Type'],'application/javascript; charset=utf-8')
        self.assertGreater(len(content),10000)
