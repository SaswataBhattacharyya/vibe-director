from __future__ import annotations

import tempfile
import unittest
import sqlite3
from pathlib import Path

from story_builder.services.production_ledger import ProductionLedger
from story_builder.services.production_styles import ProductionStyleError, ProductionStyleService


class ProductionStyleTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.service = ProductionStyleService(ProductionLedger(Path(self.temporary.name) / "ledger.sqlite3"))

    @staticmethod
    def custom_payload():
        return {
            "story": "Protect author intent and causal continuity.",
            "scene_direction": "Use clear blocking and motivated camera choices.",
            "image": "Use a restrained palette and readable composition.",
            "audio": "Keep dialogue clear and music subordinate.",
            "video": "Use purposeful camera movement and coherent pacing.",
            "review": "Check continuity, clarity, and factual support.",
        }, {
            "display_name": "Field Journal",
            "purpose": "Document field observations clearly.",
            "behavior": ["Keep observations distinct from interpretation."],
            "review_priorities": ["source fidelity", "readability"],
        }

    def test_bundled_catalog_has_six_valid_pinned_types(self):
        rows = self.service.list_catalog()["production_types"]
        self.assertEqual(len(rows), 6)
        self.assertEqual({row["production_type"] for row in rows}, {
            "story_film", "social_profile", "corporate_pitch", "informative", "news_report", "advertisement"
        })
        self.assertTrue(all(row["narrative_hash"] and row["director_profile_hash"] and
                            len(row["narrative_guidance"]) == 6 for row in rows))

    def test_types_and_directing_styles_are_separate_catalogs(self):
        catalog = self.service.list_catalog()
        self.assertEqual({row["style_id"] for row in catalog["directing_styles"]},
                         {"cinematic", "horror", "romance", "action", "mixed"})
        self.assertTrue(all(row["style_hash"] and row["guidance"] for row in catalog["directing_styles"]))

    def test_custom_directing_style_versions_are_immutable_and_selections_pin_exact_version(self):
        first = self.service.publish_custom_directing_style(
            "neo_noir", "Neo-noir", "Use motivated shadows and restrained camera movement.",
            evidence=[{"asset_id": "pa-0123456789abcdef", "kind": "image", "intent": "lighting"}])
        self.assertEqual(first["version"], 1)
        second = self.service.publish_custom_directing_style(
            "neo_noir", "Neo-noir", "Use motivated shadows, restrained movement and practical color.")
        self.assertEqual(second["version"], 2)
        self.assertNotEqual(first["style_hash"], second["style_hash"])
        catalog = {item.get("style_version_id"): item for item in self.service.list_catalog()["directing_styles"]}
        self.assertIn(second["style_version_id"], catalog)
        selected_old = self.service.select(isolated_context_id="isolated-style", production_type="story_film",
            directing_style_id="neo_noir", directing_style_version_id=first["style_version_id"])
        selected_latest = self.service.select(isolated_context_id="isolated-style", production_type="story_film",
            directing_style_id="neo_noir")
        self.assertEqual(selected_old["directing_style"]["version"], 1)
        self.assertEqual(selected_old["directing_style"]["evidence"][0]["kind"], "image")
        self.assertEqual(selected_latest["directing_style"]["version"], 2)

    def test_custom_directing_style_cannot_overwrite_builtins_or_accept_bad_rules(self):
        with self.assertRaisesRegex(ProductionStyleError, "cannot be replaced"):
            self.service.publish_custom_directing_style("horror", "Mine", "Different rules")
        with self.assertRaisesRegex(ProductionStyleError, "guidance"):
            self.service.publish_custom_directing_style("neo_noir", "Neo-noir", " ")

    def test_custom_directing_style_scope_is_persisted_and_enforced(self):
        scoped = self.service.publish_custom_directing_style(
            "news_look", "News look", "Keep reporting direct and legible.",
            scope_type="production_type", production_type_scope="news_report")
        catalog_style = next(style for style in self.service.list_catalog()["directing_styles"]
                             if style["style_id"] == "news_look")
        self.assertEqual(catalog_style["scope_type"], "production_type")
        self.assertEqual(catalog_style["production_type_scope"], "news_report")
        selected = self.service.select(isolated_context_id="scoped-style", production_type="news_report",
            directing_style_id="news_look", directing_style_version_id=scoped["style_version_id"])
        self.assertEqual(selected["directing_style"]["production_type_scope"], "news_report")
        with self.assertRaisesRegex(ProductionStyleError, "only available"):
            self.service.select(isolated_context_id="wrong-style", production_type="story_film",
                                directing_style_id="news_look")
        with self.assertRaisesRegex(ProductionStyleError, "scope_type"):
            self.service.publish_custom_directing_style("bad_scope", "Bad scope", "Rules", scope_type=[])
        with self.assertRaisesRegex(ProductionStyleError, "cannot be bound"):
            self.service.publish_custom_directing_style("bad_binding", "Bad binding", "Rules",
                production_type_scope="news_report")

    def test_existing_custom_styles_migrate_as_cross_type(self):
        self.service.publish_custom_directing_style("legacy_look", "Legacy look", "Keep the visual style coherent.")
        with sqlite3.connect(self.service.ledger.path) as db:
            db.execute("ALTER TABLE directing_style_versions DROP COLUMN production_type_scope")
            db.execute("ALTER TABLE directing_style_versions DROP COLUMN scope_type")
        migrated = ProductionStyleService(self.service.ledger)
        style = next(item for item in migrated.list_catalog()["directing_styles"]
                     if item["style_id"] == "legacy_look")
        self.assertEqual(style["scope_type"], "cross_type")
        self.assertIsNone(style["production_type_scope"])

    def test_document_style_evidence_has_a_strict_schema(self):
        valid = {"kind": "document", "source_id": "style-source-0123456789abcdef",
            "source_sha256": "a" * 64, "filename": "rules.txt", "locator": "line:1-1",
            "quote": "Use a quiet palette.", "intent": "Keep the palette restrained."}
        record = self.service.publish_custom_directing_style("document_style", "Document Style",
            "Use restrained palettes.", evidence=[valid])
        self.assertEqual(record["evidence"], [valid])
        invalid = {**valid, "source_sha256": "not-a-hash"}
        with self.assertRaisesRegex(ProductionStyleError, "SHA-256"):
            self.service.publish_custom_directing_style("bad_document_style", "Bad Document Style",
                "Use restrained palettes.", evidence=[invalid])

    def test_selection_freezes_independent_directing_style_and_keeps_legacy_default(self):
        action = self.service.select(isolated_context_id="isolated-a", production_type="story_film",
                                     directing_style_id="action")
        legacy = self.service.select(isolated_context_id="isolated-b", production_type="story_film")
        self.assertEqual(action["production_type"], "story_film")
        self.assertEqual(action["directing_style"]["style_id"], "action")
        self.assertTrue(action["directing_style"]["style_hash"])
        self.assertEqual(legacy["directing_style"]["style_id"], "cinematic")
        with self.assertRaisesRegex(ProductionStyleError, "Unknown directing style"):
            self.service.select(isolated_context_id="isolated-c", production_type="story_film",
                                 directing_style_id="made_up")
        with self.assertRaisesRegex(ProductionStyleError, "Unknown directing style"):
            self.service.select(isolated_context_id="isolated-d", production_type="story_film",
                                 directing_style_id="")

    def test_custom_type_validation_requires_all_guidance_and_profile_fields(self):
        stages, profile = self.custom_payload()
        with self.assertRaisesRegex(ProductionStyleError, "six stages"):
            self.service.publish_custom_type("field_journal", {"story": "only"}, profile)
        with self.assertRaisesRegex(ProductionStyleError, "review_priorities"):
            self.service.publish_custom_type("field_journal", stages, {**profile, "review_priorities": []})

    def test_published_versions_and_selections_are_immutable(self):
        stages, profile = self.custom_payload()
        v1 = self.service.publish_custom_type("field_journal", stages, profile)
        first = self.service.select(workspace_id="workspace-a", production_type="field_journal",
                                    style_version_id=v1["style_version_id"])
        v2 = self.service.publish_custom_type("field_journal", stages,
                                              {**profile, "purpose": "Document field observations for review."})
        second = self.service.select(workspace_id="workspace-a", production_type="field_journal",
                                     style_version_id=v2["style_version_id"])
        self.assertEqual(v2["style_version"], 2)
        self.assertNotEqual(first["snapshot_id"], second["snapshot_id"])
        self.assertNotEqual(first["director_profile_hash"], second["director_profile_hash"])
        self.assertEqual(self.service.get_selection(first["snapshot_id"]), first)
        self.assertEqual([s["snapshot_id"] for s in self.service.list_selections(workspace_id="workspace-a")],
                         [first["snapshot_id"], second["snapshot_id"]])
        self.assertEqual(self.service.list_selections(isolated_context_id="isolated-a"), [])
        with self.assertRaisesRegex(ProductionStyleError, "Unknown or mismatched custom"):
            self.service.select(workspace_id="workspace-a", production_type="field_journal", style_version_id="")

    def test_base_selection_pins_hashes_and_requires_one_context(self):
        with self.assertRaisesRegex(ProductionStyleError, "exactly one"):
            self.service.select(production_type="story_film")
        selected = self.service.select(isolated_context_id="isolated-a", production_type="story_film")
        self.assertEqual(selected["style_version_id"], "base:story_film:v1")
        self.assertTrue(selected["narrative_hash"])
        self.assertTrue(selected["director_profile_hash"])


if __name__ == "__main__":
    unittest.main()
