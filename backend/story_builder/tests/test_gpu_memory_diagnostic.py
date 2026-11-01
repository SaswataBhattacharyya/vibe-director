import tempfile
import unittest
from pathlib import Path

from story_builder.services.gpu_runtime import read_host_memory_diagnostic


class HostMemoryDiagnosticTests(unittest.TestCase):
    def test_reports_mem_available_and_swap_as_diagnostic_values(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "meminfo"
            path.write_text(
                "MemTotal:       104857600 kB\n"
                "MemAvailable:    83886080 kB\n"
                "SwapTotal:        8388608 kB\n"
                "SwapFree:         7340032 kB\n",
                encoding="ascii",
            )
            self.assertEqual(read_host_memory_diagnostic(path), {
                "total_gib": 100.0,
                "available_gib": 80.0,
                "swap_total_gib": 8.0,
                "swap_free_gib": 7.0,
            })

    def test_returns_none_when_proc_memory_data_is_unavailable_or_incomplete(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "meminfo"
            self.assertIsNone(read_host_memory_diagnostic(path))
            path.write_text("MemTotal: 100 kB\n", encoding="ascii")
            self.assertIsNone(read_host_memory_diagnostic(path))


if __name__ == "__main__":
    unittest.main()
