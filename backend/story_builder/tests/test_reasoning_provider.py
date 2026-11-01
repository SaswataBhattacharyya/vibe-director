from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from story_builder.services.reasoning_provider import ReasoningProviderError, _codex_json


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
