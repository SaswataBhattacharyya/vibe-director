import hashlib
import io
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from story_builder.isolated_server import create_app
from story_builder.services.production_ledger import ProductionLedger
from story_builder.services.workflow_knowledge import WorkflowKnowledge, WorkflowKnowledgeError
from story_builder.services.workflow_knowledge_catalog import (seed_audio_workflow_knowledge,
    seed_image_workflow_knowledge, seed_minimax_h3_workflow_knowledge)


def evidence_graph(text="Keep camera motion explicit."):
    excerpt_hash = hashlib.sha256(text.encode()).hexdigest()
    return {"sources": [{"source_id": "local_contract", "uri": "backend/contracts/video.json",
        "version": "1", "section": "prompt rules", "sha256": excerpt_hash}],
        "nodes": [{"node_id": "camera_motion", "kind": "prompt_rule", "text": text,
            "source_ids": ["local_contract"]}], "edges": []}


class WorkflowKnowledgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.ledger = ProductionLedger(self.root / "services/production/ledger.sqlite3")
        self.knowledge = WorkflowKnowledge(self.ledger)

    def publish(self, text="Keep camera motion explicit.", *, model="minimax_h3", version="1", graph_hash="b" * 64):
        graph = evidence_graph(text)
        return self.knowledge.publish(model_id=model, workflow_id="minimax_h3_t2v_v1",
            workflow_version=version, workflow_sha256=graph_hash, graph=graph)

    def test_every_copied_api_workflow_graph_has_source_linked_knowledge(self):
        seeded = (
            seed_minimax_h3_workflow_knowledge(self.knowledge)
            + seed_image_workflow_knowledge(self.knowledge)
            + seed_audio_workflow_knowledge(self.knowledge)
        )
        source_root = Path(__file__).resolve().parents[1]
        indexed_graphs = {
            source["uri"]
            for item in seeded
            for source in self.knowledge.get(item["workflow_id"], model_id=item["model_id"])["sources"]
            if source["uri"].startswith("workflows/api/")
        }
        api_graphs = {
            path.relative_to(source_root).as_posix()
            for path in (source_root / "workflows" / "api").rglob("*.json")
        }
        self.assertEqual(indexed_graphs, api_graphs)
        for item in seeded:
            guidance = self.knowledge.get(item["workflow_id"], model_id=item["model_id"])
            graph_sources = [source for source in guidance["sources"]
                if source["uri"].startswith("workflows/api/")]
            self.assertTrue(graph_sources, item["workflow_id"])
            graph_digests = set()
            for source in graph_sources:
                graph_path = source_root / source["uri"]
                digest = hashlib.sha256(graph_path.read_bytes()).hexdigest()
                self.assertEqual(source["version"], digest, item["workflow_id"])
                graph_digests.add(digest)
            self.assertEqual(graph_digests, {guidance["workflow_sha256"]}, item["workflow_id"])

    def test_publish_is_versioned_immutable_and_idempotent(self):
        first = self.publish()
        same = self.publish()
        second = self.publish("Name camera movement and speed.")
        self.assertEqual(first["guidance_version"], 1)
        self.assertEqual(same["guidance_version"], 1)
        self.assertEqual(second["guidance_version"], 2)
        self.assertEqual(len(self.knowledge.list_versions("minimax_h3_t2v_v1")), 2)
        with self.assertRaises(sqlite3.IntegrityError):
            with self.ledger._connect() as db:
                db.execute("UPDATE workflow_knowledge_snapshots SET graph_json='{}' WHERE knowledge_id=?",
                    (first["knowledge_id"],))
        with self.assertRaisesRegex(sqlite3.IntegrityError, "immutable"):
            with self.ledger._connect() as db:
                db.execute("INSERT OR REPLACE INTO workflow_knowledge_snapshots SELECT * FROM workflow_knowledge_snapshots WHERE knowledge_id=?",
                    (first["knowledge_id"],))
        versions = self.knowledge.list_versions("minimax_h3_t2v_v1")
        self.assertEqual([row["knowledge_id"] for row in versions],
            [first["knowledge_id"], second["knowledge_id"]])

    def test_workflow_and_model_are_both_required_for_exact_retrieval(self):
        self.publish()
        self.publish("Separate model guidance.", model="other_model")
        found = self.knowledge.get("minimax_h3_t2v_v1", model_id="minimax_h3")
        other = self.knowledge.get("minimax_h3_t2v_v1", model_id="other_model")
        missing = self.knowledge.get("minimax_h3_r2v_v1", model_id="minimax_h3")
        self.assertEqual(found["nodes"][0]["text"], "Keep camera motion explicit.")
        self.assertEqual(other["nodes"][0]["text"], "Separate model guidance.")
        self.assertEqual(missing["retrieval_status"], "not_curated")
        self.assertEqual(missing["nodes"], [])

    def test_rejects_unlinked_or_malformed_evidence(self):
        graph = evidence_graph()
        graph["nodes"][0]["source_ids"] = ["missing"]
        with self.assertRaises(WorkflowKnowledgeError):
            self.knowledge.publish(model_id="minimax_h3", workflow_id="minimax_h3_t2v_v1",
                workflow_version="1", workflow_sha256="b" * 64, graph=graph)

    def test_rejects_changed_captured_evidence(self):
        graph = evidence_graph()
        graph["nodes"][0]["text"] = "Altered after its evidence digest was captured."
        with self.assertRaisesRegex(WorkflowKnowledgeError, "digest"):
            self.knowledge.publish(model_id="minimax_h3", workflow_id="minimax_h3_t2v_v1",
                workflow_version="1", workflow_sha256="b" * 64, graph=graph)

    def test_catalog_seeds_exact_workflow_hashes_idempotently(self):
        first = seed_minimax_h3_workflow_knowledge(self.knowledge)
        second = seed_minimax_h3_workflow_knowledge(self.knowledge)
        expected = {"minimax_h3_t2v_local_v1", "minimax_h3_fl2va_first_last_v1", "minimax_h3_r2v_dynamic_v1"}
        self.assertEqual({entry["workflow_id"] for entry in first}, expected)
        self.assertEqual([entry["knowledge_id"] for entry in first], [entry["knowledge_id"] for entry in second])
        for workflow_id in expected:
            result = self.knowledge.get(workflow_id, model_id="minimax_h3")
            self.assertEqual(result["retrieval_status"], "matched")
            self.assertTrue(result["sources"])
            self.assertTrue(result["nodes"])
            self.assertTrue(all(node["source_ids"] for node in result["nodes"]))
            contract = next(node for node in result["nodes"] if node["kind"] == "parameter_contract")
            self.assertTrue(any(source_id.startswith("contract_")
                for source_id in contract["source_ids"]))
            self.assertTrue(any(source_id == "local_graph_contract"
                for source_id in contract["source_ids"]))
        expected_contracts = {
            "minimax_h3_t2v_local_v1": ("5–10 seconds", "steps fixed at 20", "no references"),
            "minimax_h3_fl2va_first_last_v1": ("5–15 seconds", "both first_frame and last_frame", "24 fps"),
            "minimax_h3_r2v_dynamic_v1": ("5–15 seconds", "steps 8–40", "at most 9 images, 3 videos and 3 standalone audio refs"),
        }
        for workflow_id, phrases in expected_contracts.items():
            result = self.knowledge.get(workflow_id, model_id="minimax_h3")
            contract = next(node for node in result["nodes"] if node["kind"] == "parameter_contract")
            for phrase in phrases:
                self.assertIn(phrase, contract["text"])

    def test_api_returns_exact_guidance_or_explicit_not_curated(self):
        self.publish()
        app = create_app(data_root=self.root)

        def get(query):
            status = []
            body = b"".join(app({"REQUEST_METHOD": "GET", "PATH_INFO": "/api/workflow-guidance",
                "QUERY_STRING": query}, lambda code, _headers: status.append(code)))
            return status[0], json.loads(body)

        status, result = get("model_id=minimax_h3&workflow_id=minimax_h3_t2v_v1")
        self.assertEqual(status, "200 OK")
        self.assertEqual(result["retrieval_status"], "matched")
        self.assertEqual(result["nodes"][0]["text"], "Keep camera motion explicit.")
        status, missing = get("model_id=minimax_h3&workflow_id=minimax_h3_r2v_v1")
        self.assertEqual(status, "200 OK")
        self.assertEqual(missing["retrieval_status"], "not_curated")
        status, invalid = get("model_id=minimax_h3")
        self.assertEqual(status, "400 Bad Request")
        self.assertIn("workflow_id", invalid["error"]["message"])

    def test_image_catalog_pins_graph_and_adapter_contracts(self):
        first = seed_image_workflow_knowledge(self.knowledge)
        second = seed_image_workflow_knowledge(self.knowledge)
        expected = {"qwen_image_2512", "z_image_turbo", "qwen_image_edit_2511", "qwen_image_multi_angle_2511"}
        self.assertEqual({item["workflow_id"] for item in first}, expected)
        self.assertEqual([item["knowledge_id"] for item in first], [item["knowledge_id"] for item in second])
        for workflow_id in expected:
            result = self.knowledge.get(workflow_id, model_id=workflow_id if workflow_id != "qwen_image_multi_angle_2511" else "qwen_image_edit_2511")
            self.assertEqual(result["retrieval_status"], "matched")
            self.assertGreaterEqual(len(result["nodes"]), 2)
            self.assertTrue(all(node["source_ids"] for node in result["nodes"]))
            local_sources = [source for source in result["sources"]
                if source["source_id"].startswith(("graph_", "adapter_"))]
            self.assertTrue(local_sources)
            self.assertTrue(all(len(source["version"]) == 64 for source in local_sources))
            self.assertTrue(all(len(source["sha256"]) == 64 for source in result["sources"]))
            self.assertTrue(any(node["kind"] == "parameter_contract" for node in result["nodes"]))
            self.assertTrue(any(node["kind"] == "prompt_limit_contract" and "6,999" in node["text"]
                for node in result["nodes"]))
        edit = self.knowledge.get("qwen_image_edit_2511", model_id="qwen_image_edit_2511")
        self.assertIn("one to three", edit["nodes"][1]["text"])

    def test_image_vendor_guidance_is_source_linked_and_separate_from_local_contract(self):
        seed_image_workflow_knowledge(self.knowledge)
        qwen = self.knowledge.get("qwen_image_2512", model_id="qwen_image_2512")
        qwen_vendor = [node for node in qwen["nodes"] if node["kind"] == "vendor_prompt_example"]
        self.assertEqual(len(qwen_vendor), 1)
        self.assertTrue(any("QwenLM/Qwen-Image/blob/6b5e1f5" in source["uri"]
            for source in qwen["sources"] if source["source_id"] in qwen_vendor[0]["source_ids"]))
        self.assertIn("not required model syntax", qwen_vendor[0]["text"])

        z_image = self.knowledge.get("z_image_turbo", model_id="z_image_turbo")
        parameter_note = next(node for node in z_image["nodes"]
            if node["kind"] == "parameter_compatibility_note")
        self.assertIn("CFG 1.0", parameter_note["text"])
        self.assertIn("guidance_scale 0.0", parameter_note["text"])
        z_contract = next(node for node in z_image["nodes"] if node["kind"] == "parameter_contract")
        self.assertIn("steps 4 to 16", z_contract["text"])
        self.assertIn("CFG 0.1 to 2", z_contract["text"])

        edit = self.knowledge.get("qwen_image_edit_2511", model_id="qwen_image_edit_2511")
        edit_parameter_note = next(node for node in edit["nodes"]
            if node["kind"] == "parameter_compatibility_note")
        self.assertIn("4-step Lightning LoRA", edit_parameter_note["text"])

    def test_audio_catalog_pins_local_generation_inputs_idempotently(self):
        first = seed_audio_workflow_knowledge(self.knowledge)
        second = seed_audio_workflow_knowledge(self.knowledge)
        expected = {
            "ace_step_music_v1", "control_foley_text_audio_v1",
            "control_foley_text_video_audio_v1", "control_foley_reference_video_audio_v1",
            "chatterbox_timed_multichar_v1",
            "audio_effects_noise_cleanup_v1", "audio_effects_voice_repair_v1",
            "audio_effects_voice_changer_v1", "audio_effects_rvc_v1",
            "audio_effects_emotion_v1", "audio_effects_style_v1",
        }
        self.assertEqual({item["workflow_id"] for item in first}, expected)
        self.assertEqual([item["knowledge_id"] for item in first], [item["knowledge_id"] for item in second])
        audio_root = Path(__file__).resolve().parents[1] / "workflows" / "api" / "audio"
        catalog_graphs = {
            source["uri"]
            for item in first
            for source in self.knowledge.get(item["workflow_id"], model_id=item["model_id"])["sources"]
            if source["source_id"] == "local_graph"
        }
        supported_graphs = {
            path.relative_to(Path(__file__).resolve().parents[1]).as_posix()
            for path in audio_root.rglob("*.json")
        }
        self.assertEqual(catalog_graphs, supported_graphs)
        for item in first:
            result = self.knowledge.get(item["workflow_id"], model_id=item["model_id"])
            self.assertEqual(result["retrieval_status"], "matched")
            self.assertEqual({node["kind"] for node in result["nodes"]},
                {"prompt_contract", "reference_contract", "parameter_contract"})
            self.assertTrue(all(set(node["source_ids"]) == {"local_graph", "local_adapter"}
                for node in result["nodes"]))
            self.assertTrue(all(len(source["version"]) == 64 and len(source["sha256"]) == 64
                for source in result["sources"]))
        ace = self.knowledge.get("ace_step_music_v1", model_id="ace_step_1_3_5b")
        ace_prompt = next(node for node in ace["nodes"] if node["kind"] == "prompt_contract")
        self.assertIn("separate tags and lyrics inputs", ace_prompt["text"])
        self.assertIn("not a claim about undocumented vendor prompt syntax", ace_prompt["text"])
        ace_parameters = next(node for node in ace["nodes"] if node["kind"] == "parameter_contract")
        self.assertIn("song mode requires lyrics", ace_parameters["text"])
        self.assertIn("lyrics_strength to 0–1", ace_parameters["text"])
        ace_refs = next(node for node in ace["nodes"] if node["kind"] == "reference_contract")
        self.assertIn("does not accept image, video or reference-audio", ace_refs["text"])
        text_video = self.knowledge.get("control_foley_text_video_audio_v1", model_id="control_foley")
        self.assertIn("requires one video and accepts no reference audio",
            next(node for node in text_video["nodes"] if node["kind"] == "reference_contract")["text"])
        reference = self.knowledge.get("control_foley_reference_video_audio_v1", model_id="control_foley")
        self.assertIn("requires both reference audio and video",
            next(node for node in reference["nodes"] if node["kind"] == "parameter_contract")["text"])
        self.assertIn("requires both one video and one reference-audio input",
            next(node for node in reference["nodes"] if node["kind"] == "reference_contract")["text"])
        timed_tts = self.knowledge.get("chatterbox_timed_multichar_v1", model_id="chatterbox_timed_multichar")
        tts_prompt = next(node for node in timed_tts["nodes"] if node["kind"] == "prompt_contract")
        self.assertIn("Pause tags", tts_prompt["text"])
        self.assertIn("not vendor documentation", tts_prompt["text"])
        tts_references = next(node for node in timed_tts["nodes"] if node["kind"] == "reference_contract")
        self.assertIn("discoverable voice file", tts_references["text"])
        tts_parameters = next(node for node in timed_tts["nodes"] if node["kind"] == "parameter_contract")
        self.assertIn("stretch_to_fit", tts_parameters["text"])
        self.assertIn("batch_size 0–32", tts_parameters["text"])
        rvc = self.knowledge.get("audio_effects_rvc_v1", model_id="audio_effects_local")
        self.assertIn("downloads are disabled", next(node for node in rvc["nodes"]
            if node["kind"] == "parameter_contract")["text"])
        voice_changer = self.knowledge.get("audio_effects_voice_changer_v1", model_id="audio_effects_local")
        self.assertIn("discoverable reference voice", next(node for node in voice_changer["nodes"]
            if node["kind"] == "reference_contract")["text"])
        emotion = self.knowledge.get("audio_effects_emotion_v1", model_id="audio_effects_local")
        self.assertIn("exact transcript", next(node for node in emotion["nodes"]
            if node["kind"] == "parameter_contract")["text"])


if __name__ == "__main__":
    unittest.main()
