"""Host consent invariants; native user input mocked, existing task storage real."""
import copy
import time
from unittest.mock import patch

from story_builder.services import agent_confirmation as consent
from story_builder.services.production_ledger import LedgerConflict
from story_builder.tests.test_director_harness import DirectorHarnessFixture
class ConsentTests(DirectorHarnessFixture):
    def row(self):
        return self.tasks.propose(self.owner, {'tool_id': 'editor.create_session', 'asset_ids': [],
                                             'settings': {'name': 'untrusted <b>review</b>'}})

    def test_one_use_exact_binding_and_expiration(self):
        row = self.row()
        with patch.object(consent, '_desktop_confirm', return_value=True):
            for change in ('owner', 'root', 'task', 'action', 'revision', 'hash', 'settings', 'status', 'expiry'):
                receipt = consent.confirm(self.root, self.owner, row, 'approve')
                current, owner, root, action = copy.deepcopy(row), self.owner, self.root, 'approve'
                if change == 'owner': owner = 'other'
                if change == 'root': root = self.root / 'other'
                if change == 'task': current['task_id'] = 'other'
                if change == 'action': action = 'run'
                if change == 'revision': current['current_revision'] += 1
                if change == 'hash': current['plan_hash'] = '0' * 64
                if change == 'settings': current['plan']['settings']['name'] = 'changed'
                if change == 'status': current['status'] = 'approved'
                if change == 'expiry': receipt.expires = time.monotonic() - 1
                with self.subTest(change=change), self.assertRaises(LedgerConflict):
                    consent.consume(receipt, root, owner, current, action)
                self.assertTrue(receipt.used)
            receipt = consent.confirm(self.root, self.owner, row, 'approve')
            consent.consume(receipt, self.root, self.owner, row, 'approve')
            with self.assertRaises(LedgerConflict):
                consent.consume(receipt, self.root, self.owner, row, 'approve')
        with self.assertRaises(LedgerConflict):
            consent.consume({'approved': True}, self.root, self.owner, row, 'approve')

    def test_changes_during_native_review_rejected_inside_task_lock(self):
        row = self.row()
        def change_plan(text, action):
            self.tasks.revise(self.owner, row['task_id'], {**self.approval(row), 'proposal': {
                'tool_id': 'editor.create_session', 'asset_ids': [], 'settings': {'name': 'swapped'}}})
            return True
        with patch.object(consent, '_desktop_confirm', side_effect=change_plan):
            receipt = consent.confirm(self.root, self.owner, row, 'approve')
        with self.assertRaises(LedgerConflict):
            self.tasks.approve(self.owner, row['task_id'], self.approval(row), authorization=receipt)
        self.assertEqual(self.tasks.get(self.owner, row['task_id'])['status'], 'draft')
        self.dispatch.assert_not_called()

    def test_native_rejection_unavailable_timeout_and_concurrency_fail_closed(self):
        row = self.row()
        with patch.object(consent, '_desktop_confirm', return_value=False), self.assertRaises(ValueError):
            consent.confirm(self.root, self.owner, row, 'approve')
        with patch.dict('os.environ', {}, clear=True), self.assertRaises(ValueError):
            consent.confirm(self.root, self.owner, row, 'approve')
        import subprocess
        with patch.dict('os.environ', {'DISPLAY': ':test'}), patch.object(consent.subprocess, 'run', side_effect=subprocess.TimeoutExpired('zenity', 1)), self.assertRaises(ValueError):
            consent.confirm(self.root, self.owner, row, 'run')
        consent._LOCK.acquire()
        try:
            with self.assertRaises(ValueError):
                consent.confirm(self.root, self.owner, row, 'approve')
        finally:
            consent._LOCK.release()
        self.dispatch.assert_not_called()

    def test_revised_read_task_cannot_launder_protected_host_approval(self):
        gateway = self.new_goal()
        args = {'kind': 'all', 'offset': 0, 'limit': 2}
        step, _ = self.goals.step(self.owner, self.request, 'media_list', args)
        row = self.tasks.propose(self.owner, {'tool_id': 'media.list', 'asset_ids': [], 'settings': args})
        self.goals.receipt(self.owner, self.request, step['step_key'], task_id=row['task_id'])
        self.tasks.revise(self.owner, row['task_id'], {**self.approval(row), 'proposal': {
            'tool_id': 'editor.create_session', 'asset_ids': [], 'settings': {'name': 'swapped protected operation'}}})
        with self.assertRaisesRegex(LedgerConflict, 'revised or substituted'):
            gateway.call('media_list', args)
        self.assertEqual(self.tasks.get(self.owner, row['task_id'])['status'], 'draft')
        self.dispatch.assert_not_called()
