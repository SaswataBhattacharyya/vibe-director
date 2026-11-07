import unittest
from unittest.mock import patch
from story_builder.services.agent_tools import tools


class AgentToolsTests(unittest.TestCase):
    def test_installed_tools_describe_real_inputs_without_execution(self):
        with patch('story_builder.services.agent_tools.shutil.which', return_value='/test/ffmpeg'), \
             patch('story_builder.services.agent_transcription.capability', return_value={'status': 'blocked', 'execution_enabled': False, 'reason': 'Missing analyzer image.'}), \
             patch('story_builder.services.audio_utilities.capabilities', return_value={'operations': []}), \
             patch('subprocess.run', side_effect=AssertionError('Passive discovery must not launch commands')):
            rows = {row['id']: row for row in tools()['tools']}
        self.assertEqual(set(rows), {'audio.extract_mp3', 'video.continuity_last_frame', 'computer.execute', 'editor.prepare_brief',
                                     'audio.transcribe', 'audio.noise_cleanup', 'audio.demucs_stems'})
        self.assertFalse(rows['audio.transcribe']['execution_enabled'])
        self.assertIn('Missing analyzer image', rows['audio.transcribe']['reason'])
        self.assertEqual(rows['audio.extract_mp3']['scope'], 'whole_source')
        self.assertEqual(rows['audio.demucs_stems']['accepted_media'], ['audio'])
        self.assertTrue(rows['audio.extract_mp3']['execution_enabled'])
        self.assertTrue(rows['video.continuity_last_frame']['execution_enabled'])
        audio = rows['audio.extract_mp3']['input_schema']
        quality = audio['properties']['settings']['properties']['quality']
        self.assertEqual((quality['default'], quality['minimum'], quality['maximum']), (2, 0, 9))
        self.assertFalse(audio['additionalProperties'])
        inputs = rows['video.continuity_last_frame']['input_schema']['properties']['asset_ids']
        self.assertEqual(inputs['maxItems'], 1)
