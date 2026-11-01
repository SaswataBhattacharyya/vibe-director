"""CPU-only checks of batch phase barriers and asynchronous memory release."""
import io
import json
import sqlite3
import unittest
from unittest.mock import patch

from story_builder.services.media_jobs import release_comfyui_models_if_idle
from story_builder.services.production_ledger import ProductionLedger
from story_builder.services.t2v_batches import parse_batch


class PhaseBarrierTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.db.row_factory = sqlite3.Row
        self.addCleanup(self.db.close)
        self.db.executescript('CREATE TABLE t2v_batches(state TEXT, entries_json TEXT);'
                              'CREATE TABLE production_takes(job_id TEXT, status TEXT);')
        self.db.execute('INSERT INTO t2v_batches VALUES(?,?)', ('running', json.dumps([
            {'job_id': '7'}, {'job_id': '8'}, {'job_id': '9'}])))
        self.db.executemany('INSERT INTO production_takes VALUES(?,?)',
                           [('7','refinement_pending'), ('8','refinement_pending'), ('9','running')])

    def allowed(self, job):
        return ProductionLedger._group_allows_refinement(self.db, {'job_id':job})

    def test_all_originals_required_then_serial_refinement(self):
        self.assertFalse(self.allowed('7'))  # H3 9 still rendering
        self.db.execute("UPDATE production_takes SET status='refinement_pending' WHERE job_id='9'")
        self.assertTrue(self.allowed('7'))
        self.assertFalse(self.allowed('8'))
        for status in ('queued', 'running', 'collecting', 'recovery_required', 'failed'):
            self.db.execute('UPDATE production_takes SET status=? WHERE job_id=?', (status,'7'))
            self.assertFalse(self.allowed('8'), status)
        self.db.execute("UPDATE production_takes SET status='needs_review' WHERE job_id='7'")
        self.assertTrue(self.allowed('8'))
        self.assertFalse(self.allowed('9'))
        self.db.execute("UPDATE t2v_batches SET state='paused'")
        self.assertFalse(self.allowed('8'))

    def test_missing_original_blocks_refinement(self):
        self.db.execute("DELETE FROM production_takes WHERE job_id='9'")
        self.assertFalse(self.allowed('7'))

    def test_large_aggregate_is_not_truncated(self):
        source = '\n\n'.join(f'#prompt {i}: time=18sec, AR=9:16, Quality=0.98\n"' + 'a'*4000 + '"'
                             for i in range(7,15))
        self.assertGreater(len(source), 6999)
        entries = parse_batch(source)
        self.assertEqual([e['id'] for e in entries], [str(i) for i in range(7,15)])
        self.assertTrue(all(len(e['prompt']) == 4000 for e in entries))


class ReleaseTests(unittest.TestCase):
    def run_release(self, *, release_at=45, cancel_at=1000, invalid_until=0):
        clock = [0.0]
        sleeps = []
        requests = []
        def sleep(seconds):
            sleeps.append(seconds)
            clock[0] += seconds
        def urlopen(request, **kwargs):
            url = request if isinstance(request,str) else request.full_url
            requests.append(url)
            if url.endswith('/queue'):
                value = {'queue_running':[], 'queue_pending':[]}
            elif url.endswith('/free'):
                value = {}
            else:
                if clock[0] < invalid_until:
                    raise TimeoutError('temporary stats timeout')
                reserved = 0 if clock[0] >= release_at else 10 * 1024**3
                value = {'devices':[{'torch_vram_total':reserved, 'torch_vram_free':0}]}
            return io.BytesIO(json.dumps(value).encode())
        with patch('story_builder.services.media_jobs.time.monotonic', side_effect=lambda:clock[0]), \
             patch('story_builder.services.media_jobs.time.sleep', side_effect=sleep), \
             patch('story_builder.services.media_jobs.urllib.request.urlopen', side_effect=urlopen), \
             patch('story_builder.services.media_jobs.record_gpu_telemetry'):
            result = release_comfyui_models_if_idle(comfy_url='http://mock', wait_for_memory_release=True,
                                                    keep_waiting=lambda:clock[0]<cancel_at)
        return result, sleeps, requests

    def test_slow_release_waits_beyond_timeout_and_requires_two_samples(self):
        result, sleeps, requests = self.run_release(release_at=45)
        self.assertTrue(result['memory_release_observed'])
        self.assertEqual(result['elapsed_seconds'], 60)
        self.assertEqual(sleeps[-3:], [10,10,10])
        self.assertEqual(requests.count('http://mock/free'), 1)
        self.assertFalse(any(url.endswith('/prompt') for url in requests))

    def test_unavailable_stats_never_allow_loading(self):
        result, _, _ = self.run_release(release_at=0, invalid_until=1000, cancel_at=55)
        self.assertEqual(result['status'], 'cancelled')
        self.assertFalse(result['memory_release_observed'])

    def test_stop_during_unload_wait(self):
        result, _, _ = self.run_release(release_at=1000, cancel_at=45)
        self.assertEqual(result['status'], 'cancelled')
        self.assertFalse(result['memory_release_observed'])


if __name__ == '__main__':
    unittest.main()
