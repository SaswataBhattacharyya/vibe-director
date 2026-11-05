"""CPU preparation across the durable job/public workflow boundary; no engine POST."""
import copy
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from story_builder.services import isolated_video_jobs as jobs
from story_builder.services import isolated_video_contract as t2v
from story_builder.services import isolated_fl2va_contract as fl2va
from story_builder.services import isolated_r2v_contract as r2v
from story_builder.services.minimax_h3_graph_compiler import ResolvedAsset
from story_builder.services.production_ledger import ProductionLedger, stable_hash
from story_builder.tests.test_isolated_video_jobs import request as t2v_request
from story_builder.tests.test_isolated_fl2va_contract import request as fl2va_request
from story_builder.tests.test_isolated_r2v_contract import request as r2v_request


class VideoWorkerDestinationTests(TestCase):
    def requests(self):
        yield t2v, t2v_request(workflow_version=2, steps=4)
        yield fl2va, fl2va_request(workflow_version=2)
        yield r2v, r2v_request(workflow_version=2, steps=4,
            prompt="Use <Picture 1> for identity, <Picture 2> for setting and <Video 1> for motion.",
            images=[dict(asset_id="image-one", sha256="a" * 64, role="character_identity", intent="Match identity"),
                    dict(asset_id="image-two", sha256="b" * 64, role="background", intent="Match setting")],
            videos=[dict(asset_id="video-one", sha256="c" * 64, role="motion", intent="Match motion",
                         start_sec=0, end_sec=2, include_paired_soundtrack=False, audio_intent="")])

    def take(self, request):
        return dict(input_snapshot=request, input_hash=stable_hash(request),
                    project_id="workspace", run_id="run", shot_id="clip",
                    take_id="take", job_id="job")

    def test_all_workflows_prepare_with_frozen_destination_and_preserve_snapshot(self):
        for contract, payload in self.requests():
            for with_destination in (False, True):
                with self.subTest(workflow=payload["workflow_id"], destination=with_destination):
                    request = contract.normalize_request(payload)
                    if with_destination:
                        request["output_destination"] = dict(mode="folder", path="/chosen/output", grant="saved-grant")
                    take = self.take(request)
                    original = copy.deepcopy(take)
                    staged = {asset["asset_id"]: ResolvedAsset(asset["asset_id"], kind,
                              asset["asset_id"] + suffix, asset["sha256"],
                              0 if kind == "video" else None, 2 if kind == "video" else None)
                              for group, kind, suffix in (("images", "image", ".png"), ("videos", "video", ".mp4"))
                              for asset in request.get(group, [])}
                    with tempfile.TemporaryDirectory() as tmp, patch.object(jobs, "stage_fl2va_frames",
                            return_value=({"first_frame": "first.png", "last_frame": "last.png"}, lambda: None)), patch.object(
                            jobs, "stage_r2v_references", return_value=staged):
                        prepared = jobs.prepare_isolated_take(take, media_root=Path(tmp),
                            comfy_input_root=Path(tmp), r2v_owner_root=Path(tmp),
                            r2v_capability_provider=lambda: {"available": True},
                            fl2va_capability_provider=lambda: {"available": True})
                    saves = [node for node in prepared.graph.values() if node.get("class_type") == "SaveVideo"]
                    self.assertEqual(len(saves), 1)
                    self.assertEqual(saves[0]["inputs"]["filename_prefix"], "isolated/workspace/clip/take")
                    self.assertEqual(take, original)

    def test_destination_tampering_is_rejected_before_compilation(self):
        for contract, payload in self.requests():
            with self.subTest(workflow=payload["workflow_id"]):
                request = contract.normalize_request(payload)
                request["output_destination"] = {"path": "/original"}
                take = self.take(request)
                request["output_destination"]["path"] = "/tampered"
                with self.assertRaisesRegex(t2v.IsolatedVideoContractError, "ledger hash"):
                    jobs.prepare_isolated_take(take)

    def test_other_unknown_fields_and_client_metadata_remain_rejected(self):
        for contract, payload in self.requests():
            with self.subTest(workflow=payload["workflow_id"]):
                request = contract.normalize_request(payload)
                with self.assertRaises(ValueError):
                    contract.normalize_request(dict(request, output_destination={"path": "/untrusted"}))
                request.update(output_destination={"path": "/saved"}, unexpected_field=True)
                with self.assertRaises(ValueError):
                    jobs.prepare_isolated_take(self.take(request))

    def test_job_creation_idempotency_and_retake_keep_metadata_outside_workflow(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = ProductionLedger(root / "ledger.sqlite3")
            facade = jobs.IsolatedVideoJobs(ledger, media_root=root)
            payload = t2v_request(workflow_version=2, steps=4)
            original = facade.create_job(workspace_id="tool-library", clip_id="clip",
                                         idempotency_key="first", request=payload)
            self.assertIn("output_destination", original["request"])
            replay = facade.create_job(workspace_id="tool-library", clip_id="clip",
                                       idempotency_key="first", request=payload)
            self.assertEqual(replay["job_id"], original["job_id"])
            take = facade._take_and_meta(original["job_id"])[0]
            jobs.prepare_isolated_take(take)
            with ledger._connect() as db:
                db.execute("UPDATE production_takes SET status='failed' WHERE job_id=?", (original["job_id"],))
            draft = facade.retake_draft(original["job_id"], keep_original=True)
            self.assertNotIn("output_destination", draft["request"])
            t2v.normalize_request(draft["request"])
            retake = facade.create_retake(original["job_id"], idempotency_key="second", keep_original=True)
            jobs.prepare_isolated_take(facade._take_and_meta(retake["job_id"])[0])
            self.assertIn("output_destination", retake["request"])
            self.assertEqual(facade.get_job(original["job_id"])["request"], original["request"])
