"""Chat attachments are owned inputs to reasoning, never generation references."""
import binascii
import json
import struct
import uuid
import zlib
from unittest.mock import Mock

from story_builder.services import media_library
from story_builder.services.agent_conversation import AgentConversation
from story_builder.services.production_ledger import LedgerConflict
from story_builder.tests.test_agent_tasks import AgentTaskFixture


def png(pixel=0):
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', binascii.crc32(kind + data) & 0xffffffff)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>2I5B', 1, 1, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(bytes([0, pixel, 0, 0]))) + chunk(b'IEND', b''))


class ChatAttachmentTests(AgentTaskFixture):
    def setUp(self):
        super().setUp()
        self.reason = Mock(return_value={'reply': 'The attached image has a red field.', 'intent': 'discuss', 'quality': 2})
        self.chat = AgentConversation(self.tasks, self.reason)

    def image(self, pixel=0):
        return media_library.register_upload(self.root, self.owner, filename=f'chat-{pixel}.png', content=png(pixel), role='project_image')

    def payload(self, *assets):
        return {'request_id': str(uuid.uuid4()), 'text': 'Describe this image.', 'asset_ids': list(assets), 'skill_refs': [], 'surface': 'director'}

    def test_actual_images_are_forwarded_and_saved_history_keeps_attachment_identity(self):
        asset = self.image()
        payload = self.payload(asset['asset_id'])
        result = self.chat.send(self.owner, payload)
        call = self.reason.call_args.kwargs
        self.assertEqual(len(call['image_paths']), 1)
        self.assertEqual(call['image_paths'][0].read_bytes(), png())
        context = json.loads(call['prompt'].split('\n', 1)[1])['context']
        self.assertEqual(context['image_inputs'][0]['asset_id'], asset['asset_id'])
        self.assertEqual(result['messages'][-1]['attachments'][0]['asset_id'], asset['asset_id'])
        self.assertEqual(self.chat.send(self.owner, payload), result)
        self.reason.assert_called_once()
        self.assertEqual(self.tasks.list(self.owner)['tasks'], [])
        self.dispatch.assert_not_called()
        self.assertEqual(self.original.read_bytes(), self.before)

    def test_foreign_missing_and_changed_images_never_reach_reasoning(self):
        with self.assertRaises(ValueError):
            self.chat.send(self.owner, self.payload('pa-not-owned'))
        asset = self.image()
        path = media_library.asset_path(self.root, self.owner, asset['asset_id'])[0]
        path.write_bytes(png(2))
        with self.assertRaises(LedgerConflict):
            self.chat.send(self.owner, self.payload(asset['asset_id']))
        self.reason.assert_not_called()

    def test_image_count_and_invalid_request_fail_before_reasoning(self):
        assets = [self.image(pixel)['asset_id'] for pixel in range(7)]
        with self.assertRaisesRegex(ValueError, 'up to six images'):
            self.chat.send(self.owner, self.payload(*assets))
        with self.assertRaisesRegex(ValueError, 'Missing fields: request_id'):
            payload = self.payload()
            del payload['request_id']
            self.chat.send(self.owner, payload)
        self.reason.assert_not_called()
