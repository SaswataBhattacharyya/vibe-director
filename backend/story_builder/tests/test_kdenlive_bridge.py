"""Private client recovery never blindly replays uncertain external mutations."""
import json
import tempfile
import unittest
from pathlib import Path
from story_builder.services import kdenlive_mcp

@unittest.skipUnless(kdenlive_mcp.capability()['ready'],'Private MCP runtime required')
class BridgeTests(unittest.TestCase):
    def test_pending_operation_requires_reconciliation_and_cleans_up(self):
        with tempfile.TemporaryDirectory(prefix='vibe-kdenlive-recovery-') as temporary:
            folder=Path(temporary)
            (folder/'request.json').write_text('{}')
            (folder/'prepare.json').write_text(json.dumps({'stage':'pending','operation':'project_create'}))
            with self.assertRaisesRegex(ValueError,'Recovery required'):
                kdenlive_mcp.run(folder,'prepare',lambda *args:None)
            self.assertFalse((folder/'project').exists(),'Uncertain project_create was repeated')
            self.assertEqual(json.loads((folder/'prepare.json').read_text())['stage'],'pending')
        self.assertFalse(folder.exists(),'Recovery fixture survived cleanup')

    def test_malformed_private_result_is_rejected_without_mutation(self):
        with tempfile.TemporaryDirectory(prefix='vibe-kdenlive-recovery-') as temporary:
            folder=Path(temporary)
            (folder/'request.json').write_text('{}')
            (folder/'prepare.json').write_text('{broken')
            with self.assertRaises(ValueError):kdenlive_mcp.run(folder,'prepare',lambda *args:None)
            self.assertFalse((folder/'project').exists())
        self.assertFalse(folder.exists(),'Malformed recovery fixture survived cleanup')
