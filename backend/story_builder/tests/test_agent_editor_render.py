"""Exact task approval renders only the current prepared Editor plan."""
import base64
from story_builder.services import media_library
from story_builder.services import vibe_editor, video_repertoire
from story_builder.services.production_ledger import LedgerConflict
from story_builder.tests.test_agent_tasks import AgentTaskFixture


class EditorRenderTaskTests(AgentTaskFixture):
    def setUp(self):
        super().setUp()
        png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aD1cAAAAASUVORK5CYII=')
        self.image = media_library.register_upload(self.root, self.owner, filename='frame.png', content=png, role='project_image')
        self.editor = vibe_editor.add_project(self.root, {'name': 'Test render', 'workspace_id': self.owner})
        self.editor = vibe_editor.update_project(self.root, self.editor['id'], {'selection': [
            {'asset_id': self.image['asset_id'], 'start': 1, 'end': 2}]})

    def prepared(self):
        with vibe_editor.state(self.root) as data:
            vibe_editor.project(data, self.editor['id'])['brief'] = {'summary': 'Test edit', 'questions': []}
        self.editor = vibe_editor.propose_plan(self.root, self.editor['id'], {'revision': self.editor['revision'],
            'plan': {'width': 320, 'height': 180, 'fps': 24, 'clips': self.editor['selection'], 'audio': None}})
        return self.tasks.propose(self.owner, {'tool_id': 'editor.render', 'asset_ids': [self.image['asset_id']],
            'settings': {'project_id': self.editor['id'], 'revision': self.editor['revision']}})

    def test_exact_approval_uses_native_render_and_duplicate_run_does_not_dispatch(self):
        row = self.prepared()
        self.dispatch.assert_not_called()
        with self.assertRaises(LedgerConflict):
            self.tasks.run(self.owner, row['task_id'], self.approval(row))
        self.tasks.approve(self.owner, row['task_id'], self.approval(row))
        first = self.tasks.run(self.owner, row['task_id'], self.approval(row))
        job = video_repertoire.read_job('vibe-editor', first['invocation']['job_id'])
        self.assertEqual(job['request']['operation'], 'render')
        self.assertEqual(job['request']['agent_plan'], row['plan'])
        self.assertEqual(job['request']['plan'], row['plan']['settings']['snapshot']['value'])
        self.assertEqual(self.tasks.run(self.owner, row['task_id'], self.approval(row))['invocation'], first['invocation'])
        self.dispatch.assert_called_once()

    def test_changed_editor_revision_cannot_be_approved_or_rendered(self):
        row = self.prepared()
        vibe_editor.propose_plan(self.root, self.editor['id'], {'revision': self.editor['revision'],
            'plan': self.editor['pending']['value']})
        with self.assertRaises((ValueError, LedgerConflict)):
            self.tasks.approve(self.owner, row['task_id'], self.approval(row))
        self.dispatch.assert_not_called()
