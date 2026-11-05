from __future__ import annotations

import tempfile
import subprocess
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from story_builder.services.reasoning_provider import ReasoningProviderError, _codex_json, _run_json_command


class ReasoningTimeoutTests(unittest.TestCase):
    def test_provider_call_allows_thirty_minutes(self):
        process = MagicMock(returncode=0)
        process.communicate.return_value = ('{"ok":true}', '')
        with patch('story_builder.services.reasoning_provider.subprocess.Popen', return_value=process):
            self.assertEqual(_run_json_command(['codex', 'exec'], 'test'), '{"ok":true}')
        process.communicate.assert_called_once_with(input='test', timeout=1800)

    def test_expired_call_still_terminates_process_group(self):
        process = MagicMock(pid=12345)
        process.communicate.side_effect = [subprocess.TimeoutExpired('codex', 1800), ('', '')]
        with patch('story_builder.services.reasoning_provider.subprocess.Popen', return_value=process), \
             patch('story_builder.services.reasoning_provider.os.killpg') as terminate:
            with self.assertRaisesRegex(ReasoningProviderError, '1800 seconds'):
                _run_json_command(['codex', 'exec'], 'test')
        terminate.assert_called_once()


class CodexImageInputTests(unittest.TestCase):
    def test_codex_json_attaches_supported_image_files_in_read_only_invocation(self):
        with tempfile.TemporaryDirectory() as temporary:
            image = Path(temporary) / "candidate.png"
            image.write_bytes(b"test")
            captured = {}

            def run(command, prompt):
                captured["command"] = command
                captured["prompt"] = prompt
                return '{"type":"item.completed","item":{"type":"agent_message","text":"{\\"ok\\":true}"}}'

            with patch("story_builder.services.reasoning_provider.shutil.which", return_value="/usr/bin/codex"), \
                 patch("story_builder.services.reasoning_provider._run_json_command", side_effect=run):
                result = _codex_json("Inspect candidate.", image_paths=[image])

            self.assertTrue(result["ok"])
            command = captured["command"]
            self.assertIn("--sandbox", command)
            self.assertEqual(command[command.index("--sandbox") + 1], "read-only")
            self.assertEqual(command[command.index("--image") + 1], str(image.resolve()))
            self.assertEqual(captured["prompt"], "Inspect candidate.")

    def test_codex_json_rejects_non_image_inputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            document = Path(temporary) / "candidate.txt"
            document.write_text("not an image", encoding="utf-8")
            with patch("story_builder.services.reasoning_provider.shutil.which", return_value="/usr/bin/codex"), \
                 patch("story_builder.services.reasoning_provider._run_json_command") as run:
                with self.assertRaisesRegex(ReasoningProviderError, "PNG, JPEG, WebP, or GIF"):
                    _codex_json("Inspect candidate.", image_paths=[document])
            run.assert_not_called()

    def test_codex_json_normalizes_missing_image_errors(self):
        with tempfile.TemporaryDirectory() as temporary:
            missing = Path(temporary) / "missing.png"
            with patch("story_builder.services.reasoning_provider.shutil.which", return_value="/usr/bin/codex"), \
                 patch("story_builder.services.reasoning_provider._run_json_command") as run:
                with self.assertRaisesRegex(ReasoningProviderError, "existing PNG, JPEG, WebP, or GIF"):
                    _codex_json("Inspect candidate.", image_paths=[missing])
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
