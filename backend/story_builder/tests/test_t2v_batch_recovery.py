"""CPU-only regression checks: no provider or ComfyUI submissions."""
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from story_builder.services.gpu_runtime import GPUAdmissionError, ComfyRuntimeUnavailable, _json_url
from story_builder.services.production_ledger import ProductionLedger, LedgerNotFound
from story_builder.services.production_job_worker import ProductionJobWorker
from story_builder.services.t2v_batches import T2VBatches


class BatchRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ledger = ProductionLedger(Path(self.tmp.name) / 'ledger.sqlite3')
        self.job = {'status': 'recovery_required', 'error': {'code': 'comfy_status_unavailable'}, 'outputs': []}
        self.jobs = SimpleNamespace(ledger=self.ledger, get_job=lambda _: self.job)
        self.batches = T2VBatches(self.jobs)
        with self.ledger._connect() as db:
            db.execute("INSERT INTO t2v_batches(batch_id,workspace_id,idempotency_key,manifest_hash,entries_json,state) VALUES(?,?,?,?,?,?)",
                       ('batch-a', 'workspace-a', 'key-a', 'hash', json.dumps([{'number':'7','job_id':'job-a'}]), 'running'))

    def test_transient_recovers_same_job_and_completes(self):
        self.batches.advance_active(lambda: self.fail('Must not submit a new job'))
        self.assertEqual(self.batches.get('batch-a')['state'], 'waiting_for_recovery')
        self.job = {'status': 'running', 'outputs': []}
        self.batches.advance_active(lambda: self.fail('Must not submit a new job'))
        self.assertEqual(self.batches.get('batch-a')['state'], 'running')
        self.job = {'status':'needs_review', 'outputs':[{'kind':'video','playback_url':'/7.mp4'}]}
        self.batches.advance_active(lambda: self.fail('Must not submit a new job'))
        self.assertEqual(self.batches.get('batch-a')['state'], 'completed')

    def test_gpu_fault_pauses_with_actual_reason(self):
        self.job['error'] = {'code':'gpu_monitor_failed','message':'NVIDIA out of memory'}
        self.batches.advance_active(lambda: {})
        batch = self.batches.get('batch-a')
        self.assertEqual(batch['state'], 'paused')
        self.assertIn('NVIDIA out of memory', batch['reason'])
        self.job['status'] = 'needs_review'
        self.batches.advance_active(lambda: self.fail('Safety pause must persist'))
        self.assertEqual(self.batches.get('batch-a')['state'], 'paused')

    def test_owner_pause_never_auto_resumes(self):
        self.batches.control('batch-a', 'pause')
        self.batches.advance_active(lambda: self.fail('Owner pause must persist'))
        self.assertEqual(self.batches.get('batch-a')['state'], 'paused')

    def test_missing_video_is_not_complete(self):
        self.job = {'status':'needs_review','outputs':[{'kind':'video','available':False,'playback_url':'/7.mp4'}]}
        self.batches.advance_active(lambda: {})
        self.assertEqual(self.batches.get('batch-a')['state'], 'paused')

    def test_next_h3_admitted_after_validated_original(self):
        entries = [{'number':'7','job_id':'job-a'},
                   {'number':'8','job_id':None,'request':{'prompt':'Second prompt'}}]
        with self.ledger._connect() as db:
            db.execute('UPDATE t2v_batches SET entries_json=?', (json.dumps(entries),))
        self.jobs.get_by_idempotency_key = Mock(side_effect=LedgerNotFound('not admitted'))
        self.jobs.create_job = Mock(return_value={'job_id':'job-b'})
        self.job = {'status':'running','outputs':[]}
        self.batches.advance_active(lambda: {'available':True})
        self.jobs.create_job.assert_not_called()
        self.job = {'status':'refinement_pending','outputs':[]}
        self.batches.advance_active(lambda: {'available':True})
        self.jobs.create_job.assert_called_once()
        self.assertEqual(self.batches.get('batch-a')['entries'][1]['job_id'], 'job-b')

    def test_transport_classification(self):
        with patch('urllib.request.urlopen', side_effect=TimeoutError('timed out')):
            with self.assertRaises(ComfyRuntimeUnavailable):
                _json_url('http://localhost/system_stats')
        with patch('urllib.request.urlopen', side_effect=urllib.error.HTTPError('url',500,'bad',{},None)):
            with self.assertRaises(GPUAdmissionError) as caught:
                _json_url('http://localhost/system_stats')
            self.assertNotIsInstance(caught.exception, ComfyRuntimeUnavailable)

    def worker(self, inspector, history):
        ledger = Mock()
        ledger.belongs_to_t2v_batch.return_value = False
        return ProductionJobWorker(ledger, comfy_url='http://localhost', prepare=Mock(),
            collect=Mock(return_value=[{'kind':'video'}]), cleanup=Mock(), release_idle=Mock(),
            gpu_inspector=inspector, operating_point_reader=lambda: {'temperature_c':40,'graphics_clock_mhz':1000},
            request_json=Mock(return_value=history), sleep=lambda _: None)

    @patch('story_builder.services.production_job_worker.record_gpu_telemetry')
    @patch('story_builder.services.production_job_worker.ensure_prompt_watchdog')
    def test_worker_retries_transport_but_not_gpu_fault(self, watchdog, telemetry):
        take = {'project_id':'p','take_id':'t','job_id':'j'}
        # Deterministic clock advances past telemetry interval each loop.
        for fault, count, code in [(ComfyRuntimeUnavailable('timeout'),3,'comfy_status_unavailable'),
                                    (GPUAdmissionError('NVIDIA OOM'),1,'gpu_monitor_failed')]:
            inspector = Mock(side_effect=fault)
            worker = self.worker(inspector, {})
            worker._finish_owner_cancellation = Mock(return_value=False)
            ticks = iter(range(1000,100000,11))
            with patch('story_builder.services.production_job_worker.time.monotonic', side_effect=lambda: next(ticks)):
                result = worker._wait_collect_impl(take, 'same-prompt', None)
            self.assertEqual(result['status'], 'recovery_required')
            self.assertEqual(inspector.call_count, count)
            self.assertEqual(worker.ledger.transition_take.call_args.kwargs['payload']['code'], code)
            self.assertFalse(worker.request_json.called)  # no POST or replacement

    @patch('story_builder.services.production_job_worker.record_gpu_telemetry')
    @patch('story_builder.services.production_job_worker.ensure_prompt_watchdog')
    def test_worker_continues_after_one_timeout(self, watchdog, telemetry):
        inspector = Mock(side_effect=[ComfyRuntimeUnavailable('timeout'), {}])
        worker = self.worker(inspector, {'same-prompt':{'status':{'status_str':'success'}}})
        worker._finish_owner_cancellation = Mock(return_value=False)
        worker._commit_collected_stage = Mock(return_value='refinement_pending')
        ticks = iter(range(1000,100000,11))
        with patch('story_builder.services.production_job_worker.time.monotonic', side_effect=lambda: next(ticks)):
            result = worker._wait_collect_impl({'project_id':'p','take_id':'t','job_id':'j'}, 'same-prompt', None)
        self.assertEqual(result['status'], 'refinement_pending')
        worker.ledger.transition_take.assert_not_called()
        worker.release_idle.assert_not_called()
        self.assertEqual(worker.request_json.call_args.args[0], 'http://localhost/history/same-prompt')

    def test_recovery_keeps_models_within_stage(self):
        worker = self.worker(Mock(), {})
        worker._release_after_stage({'job_id':'j'}, 'refinement_pending')
        worker.ledger.has_ready_refinement.return_value = True
        worker._release_after_stage({'job_id':'j','pipeline':{'stage':'ltx_refinement'}}, 'needs_review')
        worker.release_idle.assert_not_called()
        worker.ledger.has_ready_refinement.return_value = False
        worker._release_after_stage({'job_id':'j','pipeline':{'stage':'ltx_refinement'}}, 'needs_review')
        worker.release_idle.assert_called_once()

    def test_batch_retains_models_within_phase_and_releases_at_end(self):
        worker = self.worker(Mock(), {})
        worker.ledger.belongs_to_t2v_batch.return_value = True
        worker._release_after_stage({'job_id':'j'}, 'refinement_pending')
        worker.ledger.has_ready_refinement.return_value = True
        worker._release_after_stage({'job_id':'j','pipeline':{'stage':'ltx_refinement'}}, 'needs_review')
        worker.release_idle.assert_not_called()
        worker.ledger.has_ready_refinement.return_value = False
        worker._release_after_stage({'job_id':'j','pipeline':{'stage':'ltx_refinement'}}, 'needs_review')
        worker.release_idle.assert_called_once()
        self.assertTrue(worker.release_idle.call_args.kwargs['wait_for_memory_release'])


if __name__ == '__main__':
    unittest.main()
