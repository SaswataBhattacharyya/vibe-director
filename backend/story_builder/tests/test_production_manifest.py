"""Versioned metadata export uses real saved boards and disposable media only."""
import io
import json
import unittest
from pathlib import Path

from story_builder.isolated_server import create_app
from story_builder.services import media_library, production_manifest
from story_builder.services.production_ledger import LedgerConflict, LedgerNotFound
from story_builder.tests import test_storyboard as fixtures


class ProductionManifestTests(unittest.TestCase):
    save = fixtures.StoryboardTests.save

    def setUp(self):
        fixtures.StoryboardTests.setUp(self)
        self.addCleanup(self.verify_cleanup)

    def verify_cleanup(self):
        self.temp.cleanup()
        self.assertFalse(Path(self.temp.name).exists())

    def export(self, revision):
        return production_manifest.export(self.board, self.w, self.r, revision)

    def test_exact_identity_timing_owned_hashes_and_no_state_change(self):
        body = self.board.get(self.w, self.r)['body']
        body['shots']['1.1'].update(image_asset_id=self.asset['asset_id'],
                                  reference_ids=[self.asset['asset_id']], notes='Keep this take.')
        saved = self.save(body)
        value = self.export(saved['revision'])
        self.assertEqual(value['version'], 1)
        self.assertEqual(value['project']['storyboard_revision'], saved['revision'])
        self.assertEqual(value['upstream']['revision'], production_manifest.UPSTREAM_REVISION)
        self.assertEqual(value['shot_mapping'][0]['shot_key'], '1.1')
        self.assertEqual(value['shot_mapping'][0]['notes'], 'Keep this take.')
        plan = value['artifacts']['scene_plan']
        self.assertEqual(plan['metadata']['total_duration_seconds'], 2)
        self.assertEqual((plan['scenes'][0]['start_seconds'], plan['scenes'][0]['end_seconds']), (0, 2))
        asset, = value['artifacts']['asset_manifest']['assets']
        self.assertEqual(asset['vibe_asset_id'], self.asset['asset_id'])
        self.assertEqual(asset['sha256'], self.asset['sha256'])
        self.assertEqual(asset['scene_id'], plan['scenes'][0]['id'])
        self.assertEqual(asset['path'], '')
        self.assertNotIn(str(self.root), json.dumps(value))
        self.assertEqual(value['capabilities']['write_back'], False)
        self.assertEqual(self.board.get(self.w, self.r), saved)
        with self.assertRaises(LedgerConflict):
            self.export(saved['revision'] - 1)
        with self.assertRaises(LedgerConflict):
            self.export(True)

    def test_changed_bytes_foreign_owner_and_concurrent_save_are_rejected(self):
        body = self.board.get(self.w, self.r)['body']
        body['shots']['1.1']['image_asset_id'] = self.asset['asset_id']
        saved = self.save(body)
        from unittest.mock import patch
        original = self.board.get
        calls = 0
        def changed(*args):
            nonlocal calls
            calls += 1
            result = original(*args)
            return {**result, 'revision': result['revision'] + 1} if calls > 2 else result
        with patch.object(self.board, 'get', side_effect=changed), self.assertRaises(LedgerConflict):
            self.export(saved['revision'])
        with self.assertRaises((ValueError, LedgerNotFound)):
            production_manifest.export(self.board, 'foreign', self.r, saved['revision'])
        source = media_library.asset_path(self.root, self.w, self.asset['asset_id'])[0]
        source.write_bytes(source.read_bytes() + b'changed')
        with self.assertRaises((ValueError, LedgerConflict)):
            self.export(saved['revision'])

    def test_json_api_requires_exact_saved_revision(self):
        saved = self.save()
        app = create_app(data_root=self.root)
        def call(payload):
            content = json.dumps(payload).encode()
            status = []
            response = b''.join(app({'REQUEST_METHOD': 'POST',
                'PATH_INFO': f'/api/story/workspaces/{self.w}/storyboard/{self.r}/production-manifest',
                'CONTENT_TYPE': 'application/json', 'CONTENT_LENGTH': str(len(content)),
                'wsgi.input': io.BytesIO(content)}, lambda s, h: status.append(s)))
            return status[0], json.loads(response)
        status, value = call({'expected_revision': saved['revision']})
        self.assertEqual(status, '200 OK', value)
        self.assertEqual(value['schema'], 'vibe-director.production-manifest')
        self.assertEqual(call({'expected_revision': 0})[0], '409 Conflict')
        self.assertEqual(call({'expected_revision': 1, 'path': '/tmp/anything'})[0], '422 Unprocessable Entity')
