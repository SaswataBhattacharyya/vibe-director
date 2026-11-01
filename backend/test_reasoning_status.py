import unittest
from unittest.mock import patch
from story_builder.services import reasoning_status as status

class StatusTests(unittest.TestCase):
    def setUp(self):
        status._cached = None
        status._usage.clear()

    def test_windows_are_separate_and_unknown_is_not_zero(self):
        windows = status.normalize_limits({"rateLimitsByLimitId": {"codex": {"limitId": "codex", "primary": {"usedPercent": 23, "windowDurationMins": 300}, "secondary": {"usedPercent": None}}}})
        self.assertEqual(len(windows), 1)
        self.assertEqual(windows[0]["remaining_percent"], 77)
        self.assertEqual(status.normalize_limits({"rateLimits": {"primary": {"usedPercent": True}}}), [])

    @patch('story_builder.services.reasoning_provider.get_settings', return_value={"provider":"codex","model":"test"})
    @patch.object(status, '_rpc_limits', return_value={"rateLimits":{"primary":{"usedPercent":12}}})
    def test_read_only_cache_and_last_request(self, rpc, settings):
        status.record_usage('codex', 'test', 120, 40)
        first = status.provider_status()
        self.assertEqual(first['windows'][0]['remaining_percent'], 88)
        self.assertIsNone(first['context_remaining_percent'])
        self.assertEqual(first['last_request']['input_tokens'], 120)
        status.provider_status()
        rpc.assert_called_once()

    @patch('story_builder.services.reasoning_provider.get_settings', return_value={"provider":"ollama","model":"local"})
    @patch.object(status, '_rpc_limits')
    def test_local_has_no_quota_but_finite_unknown_context(self, rpc, settings):
        value = status.provider_status()
        self.assertEqual(value['quota'], 'unmetered')
        self.assertIsNone(value['context_remaining_percent'])
        rpc.assert_not_called()

    @patch('story_builder.services.reasoning_provider.get_settings', return_value={"provider":"codex","model":"test"})
    @patch.object(status, '_rpc_limits', side_effect=RuntimeError('secret-provider-body'))
    def test_failure_is_sanitized(self, rpc, settings):
        value = status.provider_status()
        self.assertEqual(value['quota'], 'unavailable')
        self.assertNotIn('secret', str(value))

if __name__ == '__main__':
    unittest.main()
