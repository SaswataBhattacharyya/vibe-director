from __future__ import annotations

import io
import json
import tempfile
import unittest
import uuid
from pathlib import Path

from story_builder.isolated_server import create_app
from story_builder.services.production_ledger import ProductionLedger
from story_builder.services.field_edit_proposals import FieldEditProposals
from story_builder.services.story_authoring import StoryAuthoring


class FieldEditProposalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "data"
        self.ledger = ProductionLedger(self.root / "services/production/ledger.sqlite3")
        story = StoryAuthoring(self.ledger, data_root=self.root)
        self.workspace = story.create_workspace(title="Test",source_text="Story text.")["workspace_id"]
        self.calls = []
        def provider(*, prompt, provider, temperature):
            self.calls.append((prompt, provider, temperature))
            return {"replacement": "Mira crosses the quiet room.", "explanation": "Reduced urgency."}
        self.app = create_app(data_root=self.root, reasoning_json_provider=provider,
            capability_provider=lambda: {}, gpu_reader=lambda: {})

    def call(self, method, path, payload=None):
        raw=json.dumps(payload or {}).encode(); statuses=[]
        env={"REQUEST_METHOD":method,"PATH_INFO":path.partition("?")[0],"QUERY_STRING":path.partition("?")[2],
             "CONTENT_TYPE":"application/json","CONTENT_LENGTH":str(len(raw)),"wsgi.input":io.BytesIO(raw)}
        body=b"".join(self.app(env,lambda status,headers:statuses.append(status)))
        return statuses[0],json.loads(body)

    def payload(self, key=None):
        text="Mira hurries across the room."
        return {"surface":"prompt","revision_id":"revision-1","field_key":"1.1",
            "field_text":text,"start_codepoint":5,"end_codepoint":12,"expected_text":"hurries",
            "instruction":"Make the movement calmer.","idempotency_key":key or str(uuid.uuid4())}

    def test_proposal_is_preview_only_and_keyed_replay_does_not_repeat_provider(self):
        key=str(uuid.uuid4()); payload=self.payload(key)
        status,proposal=self.call("POST",f"/api/story/workspaces/{self.workspace}/field-edit-proposals",payload)
        self.assertEqual(status,"201 Created"); self.assertEqual(proposal["replacement"],"Mira crosses the quiet room.")
        self.assertEqual(proposal["expected_text"],"hurries"); self.assertEqual(proposal["status"],"pending")
        replay=self.call("POST",f"/api/story/workspaces/{self.workspace}/field-edit-proposals",payload)
        self.assertEqual(replay[1]["proposal_id"],proposal["proposal_id"]); self.assertEqual(len(self.calls),1)
        recovered=self.call("GET",f"/api/story/field-edit-requests/by-key/{key}")
        self.assertEqual(recovered[1]["proposal"]["replacement"],proposal["replacement"])

    def test_stale_quote_rejected_before_provider(self):
        payload=self.payload(); payload["expected_text"]="hurries!"
        status,_=self.call("POST",f"/api/story/workspaces/{self.workspace}/field-edit-proposals",payload)
        self.assertEqual(status,"409 Conflict"); self.assertEqual(self.calls,[])

    def test_idempotency_key_cannot_be_reused_for_different_selection(self):
        key=str(uuid.uuid4()); self.call("POST",f"/api/story/workspaces/{self.workspace}/field-edit-proposals",self.payload(key))
        changed=self.payload(key); changed["instruction"]="Different edit."
        status,_=self.call("POST",f"/api/story/workspaces/{self.workspace}/field-edit-proposals",changed)
        self.assertEqual(status,"409 Conflict"); self.assertEqual(len(self.calls),1)


if __name__ == "__main__": unittest.main()
