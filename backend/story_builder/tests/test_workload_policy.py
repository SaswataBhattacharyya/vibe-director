import io
import json
import os
import queue
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

from story_builder.services import media_jobs, gpu_runtime, video_repertoire
from story_builder.isolated_server import create_app
from story_builder.services.production_job_worker import ProductionJobWorker
from story_builder.services.production_image_worker import ProductionImageWorker


class WorkloadPolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        env = patch.dict(os.environ, {
            'VIBE_DIRECTOR_GPU_WORKLOAD_LOCK': str(self.root / 'work.lock'),
            'VIBE_DIRECTOR_WORKLOAD_POLICY_PATH': str(self.root / 'policy.json'),
            'VIBE_DIRECTOR_GPU_SAFETY_HOLD_PATH': str(self.root / 'gpu-safety-hold.json')})
        env.start()
        self.addCleanup(env.stop)

    def test_serial_waiter_does_not_enter_until_current_work_finishes(self):
        acquired = threading.Event()
        attempting = threading.Event()
        def other():
            attempting.set()
            with media_jobs.gpu_workload_lock():
                acquired.set()
        with media_jobs.gpu_workload_lock():
            thread = threading.Thread(target=other)
            thread.start()
            self.assertTrue(attempting.wait(2))
            self.assertFalse(acquired.wait(.1))
        self.assertTrue(acquired.wait(2))
        thread.join(2)
        self.assertFalse(thread.is_alive())

    def test_safety_cancellation_retains_lease_until_verification_returns(self):
        cancelling = threading.Event()
        verified = threading.Event()
        finished = threading.Event()
        admitted = threading.Event()
        errors = []
        monitor_join_timeouts = []
        original_join = threading.Thread.join

        def observed_join(thread, timeout=None):
            if thread.name == 'story-builder-gpu-monitor':
                monitor_join_timeouts.append(timeout)
            return original_join(thread, timeout)

        def cancel(_reason):
            cancelling.set()
            verified.wait(2)

        def run():
            try:
                with media_jobs.gpu_workload_guard(comfy_url='http://mock',
                        on_safety_trip=cancel, monitor_interval_seconds=.001):
                    self.assertTrue(cancelling.wait(2))
            except media_jobs.MediaJobError as exc:
                errors.append(str(exc))
            finally:
                finished.set()

        def waiter():
            with media_jobs.gpu_workload_lock():
                admitted.set()

        with patch.object(media_jobs, 'wait_for_comfyui_idle'), \
             patch.object(media_jobs, 'inspect_gpu_runtime', side_effect=RuntimeError('cutoff')), \
             patch.object(media_jobs, 'record_gpu_telemetry'), \
             patch.object(threading.Thread, 'join', observed_join):
            worker = threading.Thread(target=run)
            worker.start()
            self.assertTrue(cancelling.wait(2))
            queued = threading.Thread(target=waiter)
            queued.start()
            self.assertFalse(finished.wait(.05))
            self.assertFalse(admitted.is_set())
            verified.set()
            worker.join(2)
            queued.join(2)
        self.assertFalse(worker.is_alive())
        self.assertFalse(queued.is_alive())
        self.assertTrue(admitted.is_set())
        self.assertEqual(len(errors), 1)
        self.assertEqual(monitor_join_timeouts, [None])

    def test_second_analysis_can_wait_for_the_shared_slot(self):
        job = {'job_id':'second', 'status':'queued'}
        with patch.object(video_repertoire, 'read_job', return_value=job), \
             patch.object(video_repertoire, 'job_path', return_value=self.root / 'job.json'), \
             patch.object(video_repertoire, '_atomic_json'), \
             patch.object(video_repertoire, '_ensure_media_dispatcher') as ensure_dispatcher, \
             patch.object(video_repertoire._MEDIA_DISPATCH_QUEUE, 'put') as enqueue, \
             patch.object(video_repertoire.subprocess, 'Popen') as spawn:
            result = video_repertoire.start_job('analysis', 'second')
        self.assertEqual(result['status'], 'queued')
        self.assertIsNone(result['pid'])
        ensure_dispatcher.assert_called_once()
        enqueue.assert_called_once_with(('analysis', 'second'))
        spawn.assert_not_called()

    def test_media_dispatcher_never_runs_two_worker_processes_at_once(self):
        pending = queue.Queue()
        pending.put(('analysis', 'first'))
        pending.put(('audio-utilities', 'second'))
        pending.put(None)
        active = 0
        maximum_active = 0
        observed = []
        state_lock = threading.Lock()

        def fake_worker(kind, job_id):
            nonlocal active, maximum_active
            with state_lock:
                active += 1
                maximum_active = max(maximum_active, active)
                observed.append((kind, job_id))
            threading.Event().wait(.01)
            with state_lock:
                active -= 1

        with patch.object(video_repertoire, '_launch_media_worker', side_effect=fake_worker):
            video_repertoire._media_dispatch_loop(pending)
        self.assertEqual(maximum_active, 1)
        self.assertEqual(observed, [('analysis', 'first'), ('audio-utilities', 'second')])

    def test_dispatcher_startup_cannot_be_overwritten_by_queue_reset(self):
        path = self.root / 'job.json'
        path.write_text(json.dumps({'job_id': 'first', 'status': 'queued'}))

        def launch_during_startup():
            current = json.loads(path.read_text())
            current.update(status='completed', pid=123, result={'asset_id': 'saved-output'})
            path.write_text(json.dumps(current))

        with patch.object(video_repertoire, 'read_job', side_effect=lambda *_: json.loads(path.read_text())), \
             patch.object(video_repertoire, 'job_path', return_value=path), \
             patch.object(video_repertoire, '_ensure_media_dispatcher', side_effect=launch_during_startup), \
             patch.object(video_repertoire._MEDIA_DISPATCH_QUEUE, 'put'):
            video_repertoire.start_job('analysis', 'first')
        saved = json.loads(path.read_text())
        self.assertEqual(saved['status'], 'completed')
        self.assertEqual(saved['pid'], 123)
        self.assertEqual(saved['result'], {'asset_id': 'saved-output'})

    def test_cancelled_queued_worker_exits_before_taking_shared_slot(self):
        from story_builder.services import video_repertoire_worker
        with patch.object(video_repertoire_worker.store, 'read_job', return_value={'status':'cancelled'}), \
             patch.object(video_repertoire_worker, 'gpu_workload_lock') as workload_lock, \
             patch('story_builder.services.video_repertoire_worker.sys.argv',
                   ['worker', 'analysis', 'analysis-cancelled']):
            self.assertEqual(video_repertoire_worker.main(), 130)
        workload_lock.assert_not_called()

    def test_cancel_during_dispatch_waits_for_the_worker_pid(self):
        job = {'job_id':'analysis-waiting', 'status':'running', 'pid':None}
        with patch.object(video_repertoire, 'read_job', return_value=job), \
             patch.object(video_repertoire, 'job_path', return_value=self.root / 'job.json'), \
             patch.object(video_repertoire, '_atomic_json') as save:
            result = video_repertoire.cancel_job('audio-utilities', 'analysis-waiting')
        self.assertEqual(result['status'], 'cancel_requested')
        save.assert_called_once()

    def test_model_unload_acknowledgement_is_not_memory_fit_evidence(self):
        responses = [{'queue_running':[], 'queue_pending':[]}, {},
                     {'devices':[{'vram_free':1024}]}]
        def response(*args, **kwargs):
            return io.BytesIO(json.dumps(responses.pop(0)).encode())
        with patch.object(media_jobs.urllib.request, 'urlopen', side_effect=response):
            result = media_jobs.release_comfyui_models_if_idle(comfy_url='http://localhost:3008')
        self.assertEqual(result['status'], 'unload_requested')
        self.assertEqual(result['vram_free_bytes'], 1024)

    def test_generation_workers_respect_parallel_opt_in(self):
        worker = SimpleNamespace(comfy_url='http://localhost:3008',
            request_json=lambda *args, **kwargs: {'queue_running':[[0,'other']], 'queue_pending':[]})
        for inspect in (ProductionJobWorker._comfy_queue_busy_reason,
                        ProductionImageWorker._comfy_busy_reason):
            self.assertIsNotNone(inspect(worker))
        media_jobs.set_workload_policy(True)
        for inspect in (ProductionJobWorker._comfy_queue_busy_reason,
                        ProductionImageWorker._comfy_busy_reason):
            self.assertIsNone(inspect(worker))

    def test_serial_default_parallel_opt_in_and_busy_setting_rejected(self):
        self.assertFalse(media_jobs.get_workload_policy()['allow_simultaneous_runs'])
        media_jobs.set_workload_policy(True)
        acquired = threading.Event()
        release = threading.Event()
        def other():
            with media_jobs.gpu_workload_lock():
                acquired.set()
                release.wait(3)
        with media_jobs.gpu_workload_lock():
            thread = threading.Thread(target=other)
            thread.start()
            self.assertTrue(acquired.wait(2))
            with self.assertRaisesRegex(media_jobs.MediaJobError, 'active workloads'):
                media_jobs.set_workload_policy(False)
            release.set()
            thread.join(3)
        self.assertFalse(thread.is_alive())
        media_jobs.set_workload_policy(False)
        self.assertFalse(media_jobs.get_workload_policy()['allow_simultaneous_runs'])

    def test_policy_api_validates_and_persists(self):
        app = create_app(data_root=self.root / 'data')
        def call(payload):
            body = json.dumps(payload).encode()
            statuses = []
            raw = b''.join(app({'REQUEST_METHOD':'PUT','PATH_INFO':'/api/runtime/workload-policy',
                'CONTENT_LENGTH':str(len(body)), 'wsgi.input':io.BytesIO(body)},
                lambda status, headers: statuses.append(status)))
            return statuses[0], json.loads(raw)
        self.assertEqual(call({'allow_simultaneous_runs':'false'})[0], '400 Bad Request')
        self.assertEqual(call({'allow_simultaneous_runs':True}),
                         ('200 OK', {'allow_simultaneous_runs':True}))
        with media_jobs.gpu_workload_lock():
            self.assertEqual(call({'allow_simultaneous_runs':False})[0], '409 Conflict')

    def test_safety_hold_api_requires_explicit_idle_verification(self):
        app = create_app(data_root=self.root / 'data')
        media_jobs._set_gpu_safety_hold('adapter stop could not be confirmed', 'pid:123')
        def call(method, payload=None):
            body = json.dumps(payload or {}).encode()
            statuses = []
            raw = b''.join(app({'REQUEST_METHOD':method,'PATH_INFO':'/api/runtime/safety-hold',
                'CONTENT_LENGTH':str(len(body)), 'CONTENT_TYPE':'application/json', 'wsgi.input':io.BytesIO(body)},
                lambda status, headers: statuses.append(status)))
            return statuses[0], json.loads(raw)
        status, held = call('GET')
        self.assertEqual(status, '200 OK')
        self.assertTrue(held['termination_unknown'])
        self.assertEqual(call('POST', {'verified_idle':False})[0], '409 Conflict')
        self.assertEqual(call('POST', {'verified_idle':True}), ('200 OK', {'cleared':True}))

    def test_low_cuda_memory_is_diagnostic_and_queue_wait_happens_in_dispatch(self):
        device = {'name':'cuda:0 GB10','type':'cuda','vram_free':1024}
        def url(address):
            if address.endswith('/system_stats'):
                return {'devices':[device]}
            return {'queue_running':[[0,'other']], 'queue_pending':[]}
        with patch.object(gpu_runtime, 'read_gpu_operating_point', return_value={'temperature_c':45., 'graphics_clock_mhz':2000.}), \
             patch.object(gpu_runtime, '_run', return_value='NVIDIA GB10, 45, 2, Not Active, Not Active'), \
             patch.object(gpu_runtime, '_json_url', side_effect=url), \
             patch.object(gpu_runtime, '_kernel_errors', return_value=[]):
            result = gpu_runtime.inspect_gpu_runtime(comfy_url='http://localhost:3008', check_queue=False)
            self.assertEqual(result['comfyui']['free_bytes'], 1024)
            for unavailable in (None, 'N/A', -1):
                device['vram_free'] = unavailable
                result = gpu_runtime.inspect_gpu_runtime(comfy_url='http://localhost:3008', check_queue=False)
                self.assertIsNone(result['comfyui']['free_bytes'])
                self.assertIsNone(result['comfyui']['free_gib'])
            device['vram_free'] = 1024
            with self.assertRaisesRegex(gpu_runtime.GPUAdmissionError, 'unowned prompt'):
                gpu_runtime.inspect_gpu_runtime(comfy_url='http://localhost:3008')
            media_jobs.set_workload_policy(True)
            gpu_runtime.inspect_gpu_runtime(comfy_url='http://localhost:3008')

    def test_render_monitor_allows_own_pending_prompt_but_blocks_other_work(self):
        pending = [[0, 'owned']]
        def url(address):
            if address.endswith('/system_stats'):
                return {'devices': [{'name': 'cuda:0 GB10', 'type': 'cuda', 'vram_free': 1024}]}
            return {'queue_running': [], 'queue_pending': pending}
        with patch.object(gpu_runtime, 'read_gpu_operating_point', return_value={'temperature_c':45., 'graphics_clock_mhz':2000.}), \
             patch.object(gpu_runtime, '_run', return_value='NVIDIA GB10, 45, 2, Not Active, Not Active'), \
             patch.object(gpu_runtime, '_json_url', side_effect=url), \
             patch.object(gpu_runtime, '_kernel_errors', return_value=[]):
            gpu_runtime.inspect_gpu_runtime(comfy_url='http://localhost:3008', expected_prompt_id='owned')
            with self.assertRaisesRegex(gpu_runtime.GPUAdmissionError, 'pending prompt'):
                gpu_runtime.inspect_gpu_runtime(comfy_url='http://localhost:3008')
            pending.append([1, 'foreign'])
            with self.assertRaisesRegex(gpu_runtime.GPUAdmissionError, 'pending prompt'):
                gpu_runtime.inspect_gpu_runtime(comfy_url='http://localhost:3008', expected_prompt_id='owned')
