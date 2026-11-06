import unittest
from unittest.mock import patch
from story_builder.services.agent_tools import tools


class AgentToolsTests(unittest.TestCase):
    def test_installed_tools_describe_real_inputs_without_execution(self):
        with patch('story_builder.services.agent_tools.shutil.which', return_value='/test/ffmpeg'), \
             patch('subprocess.run', side_effect=AssertionError('Passive discovery must not launch commands')):
            rows = {row['id']: row for row in tools()['tools']}
        self.assertEqual(set(rows), {'audio.extract_mp3', 'video.continuity_last_frame', 'computer.execute'})
        self.assertTrue(all(row['status'] == 'available' for row in rows.values()))
        self.assertTrue(rows['audio.extract_mp3']['execution_enabled'])
        self.assertTrue(rows['video.continuity_last_frame']['execution_enabled'])
        audio = rows['audio.extract_mp3']['input_schema']
        quality = audio['properties']['settings']['properties']['quality']
        self.assertEqual((quality['default'], quality['minimum'], quality['maximum']), (2, 0, 9))
        self.assertFalse(audio['additionalProperties'])
        inputs = rows['video.continuity_last_frame']['input_schema']['properties']['asset_ids']
        self.assertEqual(inputs['maxItems'], 1)
