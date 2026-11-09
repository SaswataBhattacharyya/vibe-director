"""Offline boundary tests for the opt-in H1 experiment, not the production harness."""
import tempfile
import unittest
from pathlib import Path

from jsonschema import ValidationError
from story_builder.tests.harness_probe import fixture
from story_builder.tests.harness_probe_mcp import Gateway
from story_builder.services import video_repertoire
from story_builder.services import media_library
from story_builder.services.production_ledger import LedgerConflict


class ProbeBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='vibe-h1-boundary-')
        self.base = Path(self.temp.name)
        self.addCleanup(self.cleanup)
        (self.base / 'H1_TEST_ONLY').touch()
        self.asset = fixture(self.base)
        self.gateway = Gateway(self.base / 'data')

    def cleanup(self):
        video_repertoire.configure_roots(self.base / 'reset')
        self.temp.cleanup()
        self.assertFalse(self.base.exists())

    def test_unknown_tools_and_extra_owner_path_or_command_arguments_are_denied(self):
        for name in ('shell', 'approve', 'grant', 'delete', 'full_access', 'run_without_approval', 'fetch'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.gateway.call(name, {})
        for extra in ({'owner': 'story-foreign'}, {'path': '/etc/passwd'},
                      {'command': 'id'}, {'url': 'https://example.com'}, {'approve': True}):
            with self.subTest(extra=extra), self.assertRaises(ValidationError):
                self.gateway.call('media_inspect', {'asset_id': self.asset['asset_id'], **extra})
        with self.assertRaises(ValueError):
            self.gateway.call('media_inspect', {'asset_id': 'pa-foreign-unowned'})

    def test_changed_source_hash_is_denied_before_read_dispatch(self):
        path = media_library.asset_path(self.base / 'data', self.gateway.owner, self.asset['asset_id'])[0]
        path.write_bytes(b'changed disposable media')
        with self.assertRaises(LedgerConflict):
            self.gateway.call('media_inspect', {'asset_id': self.asset['asset_id']})

    def test_protected_proposal_is_durable_and_cannot_run_or_use_stale_approval(self):
        result = self.gateway.call('editor_propose_session', {'name': 'H1 pending review'})
        task_id = result['task_id']
        tasks, owner = self.gateway.tasks, self.gateway.owner
        approval = {'revision': result['revision'], 'plan_hash': result['plan_hash']}
        with self.assertRaises(LedgerConflict):
            tasks.run(owner, task_id, approval)
        with self.assertRaises(LedgerConflict):
            tasks.approve(owner, task_id, {**approval, 'plan_hash': 'tampered'})
        reopened = Gateway(self.base / 'data').tasks.get(owner, task_id)
        self.assertEqual(reopened['status'], 'draft')
        self.assertIsNone(reopened['invocation'])
        with tasks.ledger._connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM agent_task_approvals').fetchone()[0], 0)


if __name__ == '__main__':
    unittest.main()
