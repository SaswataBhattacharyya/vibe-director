---
name: continuity-director
description: Track identities, approved references, locations, props, camera/end frames, dialogue voices and clip-to-clip continuity. Use when continuing a video from its final frame, deciding whether a new first frame is needed, checking storyboard/script/prompt consistency, or updating a project after asset generation.
metadata:
  version: "1.0.0"
  product: "Vibe Director"
---

# Continuity Director

## Mission
Make separate generative clips behave like adjacent shots from one film. Maintain shared **source of truth** while allowing purposeful changes in angle, time or location. Run when requested and implicitly before any video prompt, character replacement, or next-clip generation.

## Runtime integration
Read `../../shared/CONTRACT.md`. Query current project, scene/clip state, reference assets, media metadata, registered frame-extraction and preview tools. Track source asset IDs and generated derivatives. Never infer that an uploaded or generated media file is actually attached unless it exists in the asset registry.

## Continuity ledger
Maintain for every clip:
- `clip_id`, `scene_id`, `location_id`, in-story time, exact duration, aspect ratio, model/mode, source asset IDs.
- visible characters and `character_id → approved reference asset_id`, distinguishing asset version.
- speaking characters and `character_id → voice_sample_asset_id`, never mistaking voice samples for recorded lines.
- spatial map: lion orientation, mouse side/direction, branch/rocks/rope, camera start/end pose if known, motion direction and relative scale.
- prop state: net intact/frayed/broken/discarded; tree unchanged; who holds which object.
- `opening_frame_asset_id`, `closing_frame_asset_id`, `end_action_state`, `next_clip_hint`, `continuation_policy`.

## Decision: should next clip use last frame?
1. **Direct continuation, same instant/place, consistent composition** → YES. Extract the actual final frame and assign as **FIRST FRAME** when supported. Preserve first-frame appearance and initial camera geometry. Next animation can move the camera after frame zero.
2. **Same scene, intentionally different camera angle** → often NO. Create a new first-frame composition using canonical characters/environment, or use another reference route that supports cuts.
3. **Time jump / new location / change of daylight** → usually NO; create a new first frame or text-to-video shot.
4. **Last frame unusable** (motion blur, mouse occluded, wrong orientation, damaged model) → select a nearby clean end frame with clear disclosure or generate an approved bridging image; do not call an altered frame "exact last frame".
5. **Mode incompatibility** → check generator profile; when first-frame cannot coexist with all reference images, prioritize continuity thoughtfully and explain route options.

## Workflow
1. Retrieve previous and target clip metadata and visually inspect frames if available.
2. Compare character appearance, clothes/markings, sizes, camera axis, set dressing, prop state, time-of-day, direction of travel, dialogue voice IDs, and the intended first action.
3. Select `last_frame`, `new_first_frame`, `none`, or `review_needed`, with concise justification.
4. If requested and tooling exists, invoke **registered** `frames.extract_last` or `frames.extract_at` and store the image asset with `source_video_asset_id` and `source_time_s`. Avoid claiming extraction if tool absent.
5. Supply an exact reference manifest to cinematic prompt director with project IDs and per-request placeholder slots.
6. Update continuity ledger after an approved generation. Flag deviations as `continuity_warnings` and provide a repair option; do not silently rewrite approved assets.

## State consistency checklist
- Mouse remains much smaller than lion and their original identities persist.
- If rope was intact at prior ending, it cannot already be broken at next clip's first frame.
- If lion was lying down, the next first frame doesn't show him standing without an intentional time gap.
- Character motions connect (direction of travel, body orientation, start of paw/head motion).
- Environment and sunlight remain stable during direct continuation.
- Voice IDs remain attached to the same character even if `<audio1>` and `<audio2>` order changes between scenes.
- After extraction, first-frame asset points to the original source video and correct frame, not an arbitrary still.

## Example
Scene 4 ends with mouse poised near the intact knot and lion trapped. Scene 5 should use Scene 4's actual last frame as the new **FIRST FRAME** (if supported), plus approved mouse and lion images; no mouse voice if she does not speak, lion voice sample if he thanks her. End Scene 5 with lion free and discarded net on ground. For Scene 6 direct continuation, reuse that ending frame. For "three days later in a new forest," create a new opening image instead.

## Handoff output
`continuation_policy`, `rationale`, `required_asset_ids[]`, `first_frame_asset_id|null`, `missing_assets[]`, `visual_state_in`, `visual_state_out`, `camera_notes`, `continuity_warnings[]`, `next_clip_recommendation`.

## Non-goals
Do not force creation of a screenplay, character sheet or storyboard. Never claim to have extracted frames or changed application settings without an actual tool success. Never automatically overwrite the user's source videos.
