"""CPU-only layer validation, escaped markup and revisioned native import."""
import copy
import unittest
from story_builder.tests import test_native_interfaces as fixtures
from story_builder.services import editor_composition, editor_layers, editor_studio, vibe_editor


class EditorLayerTests(unittest.TestCase):
    setUp = fixtures.NativeInterfacesTests.setUp
    cleanup = fixtures.NativeInterfacesTests.cleanup
    save = fixtures.NativeInterfacesTests.save
    stage = fixtures.NativeInterfacesTests.stage

    def layers(self):
        self.plan['layers'] = [
            {'id': 'title', 'kind': 'text', 'at': 0, 'duration': 2, 'text': '<script>unsafe</script>',
             'x': 20, 'y': 10, 'width': 150, 'height': 60,
             'motion': [{'time': 0, 'opacity': 0}, {'time': 1, 'opacity': 1, 'x': 40}]},
            {'id': 'badge', 'kind': 'shape', 'duration': 2, 'shape': 'ellipse', 'color': '#cc8844'},
            {'id': 'inset', 'kind': 'image', 'duration': 2, **self.editor['selection'][0]}]

    def test_preview_and_studio_preserve_typed_motion_and_escape_text(self):
        self.layers()
        s = self.stage()
        normalized = s['plan']
        document, duration = editor_composition.document(normalized, s['sources'])
        self.assertEqual(duration, 2)
        self.assertIn('&lt;script&gt;unsafe&lt;/script&gt;', document)
        self.assertNotIn('<script>unsafe', document)
        self.assertIn('tl.to("#layer-title"', document)
        self.assertEqual(len(editor_layers.media_ranges(normalized)), 2)
        file = s['folder'] / 'index.html'
        file.write_text(file.read_text().replace('left:20px', 'left:35px').replace('&lt;script&gt;unsafe&lt;/script&gt;', 'Reviewed title'))
        result = editor_studio.operate(self.root, self.editor['id'], {'token': s['token'], 'action': 'import'})
        layer = result['pending']['value']['layers'][0]
        self.assertEqual(layer['x'], 35)
        self.assertEqual(layer['text'], 'Reviewed title')
        self.assertEqual(layer['motion'], normalized['layers'][0]['motion'])
        self.assertFalse(result.get('job_id'))

    def test_invalid_motion_source_and_duration_leave_session_unchanged(self):
        self.layers()
        before = vibe_editor.snapshot(self.root)
        cases = [dict(duration=3), dict(z=200.5), dict(motion=[{'time': 1}, {'time': 0}]),
                 dict(motion=[{'time': 0, 'opacity': float('nan')}]), dict(motion=[{'time': 0, 'script': 'x'}])]
        for change in cases:
            plan = copy.deepcopy(self.plan)
            plan['layers'][0].update(change)
            with self.assertRaises(ValueError):
                vibe_editor.propose_plan(self.root, self.editor['id'], {'revision': self.editor['revision'], 'plan': plan})
        plan = copy.deepcopy(self.plan)
        plan['layers'][2]['asset_id'] = 'foreign'
        with self.assertRaises((ValueError, FileNotFoundError)):
            vibe_editor.propose_plan(self.root, self.editor['id'], {'revision': self.editor['revision'], 'plan': plan})
        self.assertEqual(vibe_editor.snapshot(self.root), before)
