import unittest

from story_builder.services.fully_automated_clip_plan import (
    ClipPlanError, clip_id, generate_clip_plan, validate_clip_plan,
)
from story_builder.services.isolated_video_contract import T2V_WORKFLOW_ID
from story_builder.services.isolated_r2v_contract import WORKFLOW_ID as R2V_WORKFLOW_ID
from story_builder.services.isolated_fl2va_contract import WORKFLOW_ID as FL2VA_WORKFLOW_ID

_UNSET = object()


class FullyAutomatedClipPlanTests(unittest.TestCase):
    def setUp(self):
        self.screenplay = {"scenes": [
            {"scene_number": 1, "shots": [
                {"shot_number": 1, "action": "Door opens.", "dialogue": "Mira: Come in.", "evidence_record_ids": ["event-a"]},
                {"shot_number": 2, "action": "Mira enters.", "dialogue": "", "evidence_record_ids": ["event-b"]},
            ]},
            {"scene_number": 2, "shots": [
                {"shot_number": 1, "action": "The train departs.", "dialogue": "", "evidence_record_ids": ["event-c"]},
            ]},
        ]}

    def valid_plan(self):
        return {"clips": [
            {"scene_number": 1, "shot_number": 1, "duration_seconds": 5,
             "duration_reason": "The action is a brief entrance.", "prompt": "Door opens, hold on Mira.",
             "source_spans": [{"field": "action", "start": 0, "end": 11}]},
            {"scene_number": 1, "shot_number": 1, "duration_seconds": 7,
             "duration_reason": "Dialogue needs a natural pause.", "prompt": "Mira invites the visitor inside.",
             "source_spans": [{"field": "dialogue", "start": 0, "end": 14}]},
            {"scene_number": 1, "shot_number": 2, "duration_seconds": 6,
             "duration_reason": "A short walk establishes her entrance.", "prompt": "Mira enters the room.",
             "source_spans": [{"field": "action", "start": 0, "end": 12}]},
            {"scene_number": 2, "shot_number": 1, "duration_seconds": 8,
             "duration_reason": "Departure needs room for the transition.", "prompt": "The train pulls away.",
             "source_spans": [{"field": "action", "start": 0, "end": 18}]},
        ]}

    def validate(self, plan=None, *, style=False, minimum=5, maximum=10,
                 screenplay=_UNSET):
        return validate_clip_plan(workspace_id="workspace-a", screenplay_revision_id="revision-a",
            screenplay=self.screenplay if screenplay is _UNSET else screenplay,
            proposed=self.valid_plan() if plan is None else plan,
            min_seconds=minimum, max_seconds=maximum, has_style_video=style)

    def test_splits_shot_into_stable_ordered_clips_and_restarts_t2v_at_scene(self):
        plan = self.validate()
        clips = plan["clips"]
        self.assertEqual([(item["scene_number"], item["shot_number"], item["clip_number"]) for item in clips],
            [(1, 1, 1), (1, 1, 2), (1, 2, 1), (2, 1, 1)])
        self.assertEqual([item["workflow_id"] for item in clips],
            [T2V_WORKFLOW_ID, R2V_WORKFLOW_ID, R2V_WORKFLOW_ID, T2V_WORKFLOW_ID])
        self.assertEqual(clips[0]["source_spans"][0]["text"], "Door opens.")
        self.assertEqual(clips[1]["source_spans"][0]["text"], "Mira: Come in.")
        self.assertEqual(clips[1]["evidence_record_ids"], ["event-a"])
        self.assertEqual(clips[0]["clip_id"], clip_id("workspace-a", "revision-a", 1, 1, 1))
        self.assertNotEqual(clips[0]["clip_id"], clips[1]["clip_id"])

    def test_selected_style_video_changes_each_scene_start_to_r2v(self):
        self.assertEqual([item["workflow_id"] for item in self.validate(style=True)["clips"]],
            [R2V_WORKFLOW_ID] * 4)

    def test_verified_character_reference_routes_only_reached_scene_start_to_r2v(self):
        first_scene = {"scenes": [self.screenplay["scenes"][1]]}
        first_scene["scenes"][0]["shots"][0]["character_record_ids"] = ["character-mira"]
        prompts = {"2.1": {"workflow_id": R2V_WORKFLOW_ID, "prompt": "Mira boards the train."}}
        scene_plan = {"clips": [{"scene_number": 2, "shot_number": 1,
            "duration_seconds": 8, "duration_reason": "A clear boarding beat.",
            "prompt": "Mira boards the train.",
            "source_spans": [{"field": "action", "start": 0, "end": 18}]}]}
        plan = validate_clip_plan(workspace_id="workspace-a", screenplay_revision_id="revision-a",
            screenplay=first_scene, proposed=scene_plan, min_seconds=5, max_seconds=10,
            scene_start_identity_refs=True)
        self.assertEqual(plan["clips"][0]["workflow_id"], R2V_WORKFLOW_ID)
        self.assertEqual(plan["clips"][0]["target_character_ids"], ["character-mira"])
        self.assertEqual(plan["clips"][0]["evidence_record_ids"], ["event-c"])
        self.assertTrue(plan["clips"][0]["character_refs_required"])
        without_reference = validate_clip_plan(workspace_id="workspace-a", screenplay_revision_id="revision-a",
            screenplay=first_scene, proposed=scene_plan, min_seconds=5, max_seconds=10)
        self.assertEqual(without_reference["clips"][0]["workflow_id"], T2V_WORKFLOW_ID)
        self.assertFalse(without_reference["clips"][0]["character_refs_required"])

    def test_rejects_gap_overlap_omitted_shot_and_invalid_duration_or_prompt(self):
        cases = []
        gap = self.valid_plan(); gap["clips"][0]["source_spans"][0]["end"] = 10; cases.append(gap)
        overlap = self.valid_plan(); overlap["clips"][1]["source_spans"] = [{"field": "action", "start": 10, "end": 11}]; cases.append(overlap)
        omitted = self.valid_plan(); omitted["clips"].pop(2); cases.append(omitted)
        duration = self.valid_plan(); duration["clips"][0]["duration_seconds"] = 11; cases.append(duration)
        prompt = self.valid_plan(); prompt["clips"][0]["prompt"] = "x" * 7000; cases.append(prompt)
        for case in cases:
            with self.subTest(case=case):
                with self.assertRaises(ClipPlanError):
                    self.validate(case)

    def test_rejects_dialogue_before_action_completion_and_out_of_order_clips(self):
        dialogue_early = self.valid_plan()
        dialogue_early["clips"][0]["source_spans"] = [{"field": "dialogue", "start": 0, "end": 14}]
        with self.assertRaisesRegex(ClipPlanError, "Dialogue coverage"):
            self.validate(dialogue_early)
        out_of_order = self.valid_plan()
        out_of_order["clips"][2], out_of_order["clips"][3] = out_of_order["clips"][3], out_of_order["clips"][2]
        with self.assertRaises(ClipPlanError):
            self.validate(out_of_order)

    def test_supports_splitting_action_and_combining_action_with_dialogue(self):
        self.screenplay["scenes"][0]["shots"][0]["action"] = "A door opens slowly."
        split = self.valid_plan()
        split["clips"][0]["source_spans"] = [{"field": "action", "start": 0, "end": 7}]
        split["clips"][1]["source_spans"] = [{"field": "action", "start": 7, "end": 20}]
        split["clips"][1]["prompt"] = "The door continues to open; Mira says come in."
        split["clips"][1]["duration_reason"] = "The continuing movement and line need a beat."
        split["clips"][1]["source_spans"].append({"field": "dialogue", "start": 0, "end": 14})
        self.assertEqual(self.validate(split)["clips"][1]["source_spans"], [
            {"field": "action", "start": 7, "end": 20, "text": "opens slowly."},
            {"field": "dialogue", "start": 0, "end": 14, "text": "Mira: Come in."},
        ])

    def test_direction_only_shot_allows_exactly_one_clip(self):
        screenplay = {"scenes": [{"scene_number": 1, "shots": [
            {"shot_number": 1, "action": "", "dialogue": "", "evidence_record_ids": ["event-a"]}
        ]}]}
        plan = {"clips": [{"scene_number": 1, "shot_number": 1, "duration_seconds": 5,
            "duration_reason": "A brief visual beat.", "prompt": "A quiet empty hallway.", "source_spans": []}]}
        self.assertEqual(len(self.validate(plan, screenplay=screenplay)["clips"]), 1)
        repeated = {"clips": [*plan["clips"], dict(plan["clips"][0]) ]}
        with self.assertRaisesRegex(ClipPlanError, "direction-only"):
            self.validate(repeated, screenplay=screenplay)

    def test_validates_duration_bounds_and_rejects_bool_duration(self):
        plan = self.valid_plan()
        plan["clips"][0]["duration_seconds"] = 6
        self.assertEqual(self.validate(plan, minimum=6, maximum=8)["clips"][0]["duration_seconds"], 6)
        plan["clips"][0]["duration_seconds"] = True
        with self.assertRaises(ClipPlanError):
            self.validate(plan)
        with self.assertRaises(ClipPlanError):
            self.validate(minimum=4, maximum=10)

    def test_accepts_unicode_prompt_just_below_limit_and_rejects_limit(self):
        plan = self.valid_plan()
        plan["clips"][0]["prompt"] = "界" * 6999
        self.validate(plan)
        plan["clips"][0]["prompt"] += "界"
        with self.assertRaisesRegex(ClipPlanError, "below 7000"):
            self.validate(plan)

    def test_rejects_malformed_screenplay_and_evidence_ids(self):
        with self.assertRaises(ClipPlanError):
            self.validate(screenplay=None)
        malformed = {"scenes": [{"scene_number": 1, "shots": [
            {"shot_number": 1, "action": 7, "dialogue": "", "evidence_record_ids": ["event-a"]}
        ]}]}
        with self.assertRaisesRegex(ClipPlanError, "must be text"):
            self.validate(screenplay=malformed)
        for bad_ids in (None, [], [""], [1]):
            malformed["scenes"][0]["shots"][0].update(
                action="A door opens.", evidence_record_ids=bad_ids)
            with self.subTest(evidence_ids=bad_ids), self.assertRaisesRegex(ClipPlanError, "evidence"):
                self.validate(screenplay=malformed)

    def test_rejects_duplicate_scene_numbers_and_ids_are_scoped(self):
        duplicate = {"scenes": [self.screenplay["scenes"][0], self.screenplay["scenes"][0]]}
        with self.assertRaisesRegex(ClipPlanError, "duplicate scene"):
            self.validate(screenplay=duplicate)
        current = clip_id("workspace-a", "revision-a", 1, 1, 1)
        self.assertNotEqual(current, clip_id("workspace-b", "revision-a", 1, 1, 1))
        self.assertNotEqual(current, clip_id("workspace-a", "revision-b", 1, 1, 1))

    def test_generates_each_scene_separately_and_validates_combined_plan(self):
        self.screenplay["scenes"][0]["shots"][0]["planned_duration_seconds"] = 12.5
        prompts = {
            "1.1": {"workflow_id": T2V_WORKFLOW_ID, "prompt": "A door opens; Mira invites someone in."},
            "1.2": {"workflow_id": R2V_WORKFLOW_ID, "prompt": "Mira enters."},
            "2.1": {"workflow_id": T2V_WORKFLOW_ID, "prompt": "The train departs."},
        }
        responses = self.valid_plan()["clips"]
        scene_responses = [
            {"clips": [item for item in responses if item["scene_number"] == 1]},
            {"clips": [item for item in responses if item["scene_number"] == 2]},
        ]
        calls = []

        def generator(**kwargs):
            calls.append(kwargs)
            return scene_responses[len(calls) - 1]

        plan = generate_clip_plan(workspace_id="workspace-a", screenplay_revision_id="revision-a",
            screenplay=self.screenplay, drafts=prompts, min_seconds=5, max_seconds=10,
            generate_json=generator)
        self.assertEqual(len(calls), 2)
        self.assertIn('"planned_duration_seconds":12.5', calls[0]["prompt"])
        self.assertIn("combined duration", calls[0]["prompt"])
        self.assertTrue(all("duration_reason" in call["prompt"] for call in calls))
        self.assertEqual(len(plan["clips"]), 4)

    def test_plan_generation_rejects_wrong_workflow_before_calling_provider(self):
        prompts = {
            "1.1": {"workflow_id": R2V_WORKFLOW_ID, "prompt": "Wrong workflow."},
            "1.2": {"workflow_id": R2V_WORKFLOW_ID, "prompt": "Mira enters."},
            "2.1": {"workflow_id": T2V_WORKFLOW_ID, "prompt": "The train departs."},
        }
        calls = []
        with self.assertRaisesRegex(ClipPlanError, "must use"):
            generate_clip_plan(workspace_id="workspace-a", screenplay_revision_id="revision-a",
                screenplay=self.screenplay, drafts=prompts, min_seconds=5, max_seconds=10,
                generate_json=lambda **kwargs: calls.append(kwargs))
        self.assertEqual(calls, [])

    def test_assisted_plan_locks_every_clip_to_one_director_selected_workflow(self):
        drafts = {key: {"workflow_id": R2V_WORKFLOW_ID, "prompt": "R2V shot prompt."}
            for key in ("1.1", "1.2", "2.1")}
        responses = self.valid_plan()["clips"]
        scene_responses = [
            {"clips": [item for item in responses if item["scene_number"] == 1]},
            {"clips": [item for item in responses if item["scene_number"] == 2]},
        ]
        calls = []
        def guided_generator(**kwargs):
            calls.append(kwargs["prompt"])
            return scene_responses.pop(0)
        plan = generate_clip_plan(workspace_id="workspace-a", screenplay_revision_id="revision-a",
            screenplay=self.screenplay, drafts=drafts, min_seconds=5, max_seconds=10,
            generate_json=guided_generator, fixed_workflow_id=R2V_WORKFLOW_ID,
            prompt_guidance="Approved rule: one concrete camera move per clip.")
        self.assertEqual([item["workflow_id"] for item in plan["clips"]], [R2V_WORKFLOW_ID] * 4)
        self.assertEqual(len(calls), 2)
        self.assertTrue(all("Approved rule: one concrete camera move per clip." in prompt for prompt in calls))

        for key in drafts:
            drafts[key]["workflow_id"] = FL2VA_WORKFLOW_ID
        plan = generate_clip_plan(workspace_id="workspace-a", screenplay_revision_id="revision-a",
            screenplay=self.screenplay, drafts=drafts, min_seconds=5, max_seconds=10,
            generate_json=lambda **kwargs: {"clips": [item for item in responses if item["scene_number"] == 1]}
                if '"scene_number":1' in kwargs["prompt"] else {"clips": [item for item in responses if item["scene_number"] == 2]},
            fixed_workflow_id=FL2VA_WORKFLOW_ID)
        self.assertEqual([item["workflow_id"] for item in plan["clips"]], [FL2VA_WORKFLOW_ID] * 4)

    def test_assisted_plan_rejects_prompt_draft_from_another_workflow_before_provider(self):
        drafts = {
            "1.1": {"workflow_id": FL2VA_WORKFLOW_ID, "prompt": "FFLF prompt."},
            "1.2": {"workflow_id": R2V_WORKFLOW_ID, "prompt": "Wrong workflow."},
            "2.1": {"workflow_id": FL2VA_WORKFLOW_ID, "prompt": "FFLF prompt."},
        }
        calls = []
        with self.assertRaisesRegex(ClipPlanError, "must use"):
            generate_clip_plan(workspace_id="workspace-a", screenplay_revision_id="revision-a",
                screenplay=self.screenplay, drafts=drafts, min_seconds=5, max_seconds=10,
                generate_json=lambda **kwargs: calls.append(kwargs), fixed_workflow_id=FL2VA_WORKFLOW_ID)
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
