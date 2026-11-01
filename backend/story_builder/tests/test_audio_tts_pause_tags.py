import unittest

from story_builder.services.audio_tts import TimedTTSError, build_workflow, prepare_srt


class TimedTTSPauseTagTests(unittest.TestCase):
    def setUp(self):
        self.characters = [{"name": "Arjun", "reference_voice_id": "voice-arjun", "language": "en"}]
        self.voices = [{"id": "voice-arjun", "name": "Arjun", "source": "user",
            "relative_path": "Arjun.wav", "discoverable": True}]

    def test_pause_tags_survive_speaker_rewrite(self):
        srt = "1\n00:00:00,000 --> 00:00:02,000\n[pause:1s] [Arjun] Wait here. [pause:250ms]\n"
        rewritten, _ = prepare_srt(srt, self.characters, self.voices)
        self.assertIn("[pause:1s] [English:Arjun] Wait here. [pause:250ms]", rewritten)

    def test_pause_then_speaker_is_not_mistaken_for_narration(self):
        srt = "1\n00:00:00,000 --> 00:00:02,000\n[pause:1s] [Arjun] Wait here.\n"
        rewritten, resolved = prepare_srt(srt, self.characters, self.voices)
        self.assertIn("[pause:1s] [English:Arjun]", rewritten)
        self.assertEqual(resolved["used_characters"], ["arjun"])

    def test_plain_untagged_dialogue_still_requires_narrator(self):
        srt = "1\n00:00:00,000 --> 00:00:02,000\nWait here.\n"
        with self.assertRaisesRegex(TimedTTSError, "Narrator"):
            prepare_srt(srt, self.characters, self.voices)

    def test_donor_workflow_is_available_for_prompt_compilation(self):
        rewritten, resolved = prepare_srt(
            "1\n00:00:00,000 --> 00:00:02,000\n[Arjun] Wait.\n", self.characters, self.voices)
        workflow = build_workflow(rewritten_srt=rewritten, narrator=resolved["narrator"],
            settings={"language": "English"}, filename_prefix="vibe/test")
        self.assertEqual(workflow["3"]["inputs"]["srt_content"], rewritten)
        self.assertEqual(workflow["4"]["inputs"]["filename_prefix"], "vibe/test")


if __name__ == "__main__":
    unittest.main()
