from __future__ import annotations

import tempfile
import unittest
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
