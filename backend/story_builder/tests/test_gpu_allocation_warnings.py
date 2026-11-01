"""Allocation monitoring policy only: no GPU work or external services."""
import unittest
from unittest.mock import patch

from story_builder.services import gpu_runtime


OLD_WARNING = "NVRM: nvCheckOkFailedNoLog: Out of memory [NV_ERR_NO_MEMORY] returned from _memdescAllocInternal(pMemDesc) @ mem_desc.c:1359"
CONTEXT_WARNING = "NVRM: nvCheckOkFailedNoLog: Out of memory [NV_ERR_NO_MEMORY] returned from kgrctxAllocCtxBuffers(pGpu, pGr) @ kernel_graphics_object.c:215"


class AllocationWarningTests(unittest.TestCase):
    def inspect(self, events):
        with patch.object(gpu_runtime, 'read_gpu_operating_point', return_value={'temperature_c':45., 'graphics_clock_mhz':2000.}), \
             patch.object(gpu_runtime, '_run', return_value='NVIDIA GB10, 45, 2, Not Active, Not Active'), \
             patch.object(gpu_runtime, '_json_url', return_value={
                 'devices':[{'name':'GB10', 'type':'cuda', 'vram_free':1024}],
                 'queue_running':[[0, 'same-owned-prompt']], 'queue_pending':[]}), \
             patch.object(gpu_runtime, '_kernel_errors', return_value=events), \
             patch.object(gpu_runtime, 'read_host_memory_diagnostic', return_value={}), \
             patch.object(gpu_runtime, 'record_gpu_telemetry') as telemetry:
            result = gpu_runtime.inspect_gpu_runtime(comfy_url='http://localhost:3008', check_queue=False,
                                                     expected_prompt_id='same-owned-prompt')
            return result, telemetry

    def test_known_allocations_are_recorded_as_warnings_for_same_prompt(self):
        events = [OLD_WARNING, CONTEXT_WARNING]
        result, telemetry = self.inspect(events)
        self.assertEqual(result['nvidia_kernel_warnings'], events)
        self.assertEqual(result['nvidia_kernel_errors'], [])
        self.assertEqual(telemetry.call_args.kwargs['phase'], 'runtime_warning')
        self.assertEqual(telemetry.call_args.kwargs['workload_id'], 'same-owned-prompt')
        self.assertEqual(telemetry.call_args.args[1]['nvidia_kernel_warnings'], events)

    def test_xid_and_other_allocations_still_block(self):
        for fault in (
            CONTEXT_WARNING + ' Xid 31',
            CONTEXT_WARNING + ' xid 31',
            CONTEXT_WARNING.replace(':215', ':216'),
            CONTEXT_WARNING.replace('kgrctxAllocCtxBuffers(', 'anotherAllocator('),
            'NVRM: Out of memory [NV_ERR_NO_MEMORY]',
            'NVRM: Xid 79 GPU has fallen off the bus',
        ):
            with self.subTest(fault=fault), self.assertRaises(gpu_runtime.GPUAdmissionError):
                self.inspect([CONTEXT_WARNING, fault])


if __name__ == '__main__':
    unittest.main()
