"""Regression: an approval question must not deadlock its own clearance."""
import tempfile
import unittest
from story_builder.services import vibe_editor as editor


class ClearanceTests(unittest.TestCase):
    def seed(self, root, questions):
        p = editor.add_project(root, {"name": "Edit", "workspace_id": "workspace"})
        with editor.state(root) as data:
            item = editor.project(data, p["id"])
            item["pending"] = {"kind": "brief", "revision": 0,
                "value": {"summary": "Replace the soundtrack", "questions": questions},
                "style_snapshot": {"id": None, "version": 0, "rules": []}}
        return p["id"]

    def test_saved_approval_question_allows_button_and_chat(self):
        for action, text in [("approve", None), ("chat", "yes, apply")]:
            with self.subTest(action=action), tempfile.TemporaryDirectory() as root:
                pid = self.seed(root, ["Do you approve the revision 4 creative brief?"])
                shown = editor.snapshot(root)["projects"][0]
                self.assertEqual(shown["pending"]["value"]["questions"], [])
                result = editor.command(root, pid, {"action": action, "text": text, "revision": 0})
                self.assertNotIn("pending", result)
                self.assertEqual(result["brief"]["questions"], [])
                self.assertEqual(len(result["revisions"]), 1)
                self.assertIsNone(result["job_id"])  # No media: no render or provider call.

    def test_real_and_mixed_questions_still_block(self):
        for question in ["Should the music be orchestral or electronic?",
                         "Do you approve this brief, and should the audio fade out?",
                         "Do you approve the export folder?"]:
            with self.subTest(question=question), tempfile.TemporaryDirectory() as root:
                pid = self.seed(root, ["Do you approve this brief?", question])
                self.assertEqual(editor.snapshot(root)["projects"][0]["pending"]["value"]["questions"], [question])
                with self.assertRaisesRegex(ValueError, "clarification"):
                    editor.command(root, pid, {"action": "approve", "revision": 0})
                unchanged = editor.snapshot(root)["projects"][0]
                self.assertIn("pending", unchanged)
                self.assertEqual(unchanged["revisions"], [])


if __name__ == "__main__":
    unittest.main()
