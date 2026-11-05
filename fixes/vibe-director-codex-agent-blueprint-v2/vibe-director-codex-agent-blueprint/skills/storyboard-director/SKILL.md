---
name: storyboard-director
description: Make a fast, comic-book-style visual storyboard from a story, screenplay, selected clip, or user-supplied image. Use when users want panels with one image per shot/beat, dialogue captions, timing, camera framing and simple editable shot planning; support generation and selective regeneration without forcing preceding steps.
metadata:
  version: "1.0.0"
  product: "Vibe Director"
---

# Storyboard Director (Visual Comic Book)

## Mission
Produce a readable, fast-to-review **comic-book presentation of the film**: images per shot or meaningful visual beat, with dialogue, action, camera and duration shown in editable panel cards **outside** the generated image. Storyboard frames are storytelling tools, not necessarily one video generation each.

## Runtime integration
Follow `../../shared/CONTRACT.md`. Read selected story/scene/clip, approved character and location references, current storyboard panels and image generation capabilities. Use registered `storyboard`, `image.generate`, `asset`, `editor` components if exposed; otherwise return a complete panel plan and image prompts. Never claim an image exists until an asset ID was returned.

## Panel design
Each card should present, in this order:
- Large visual panel image (generated or placeholder clearly marked).
- `Scene 2 / Panel 03`, start/end time, duration, and clip grouping.
- Dialogue bubble/strip in UI (`speaker`, actual words, `voice_id` if known). **Don't bake dialogue or lettering into AI panel images.**
- One-line visible action and emotional beat.
- Camera framing/movement indicator (wide/medium/close, low/high angle, track/pan/crane) with optional shot notes.
- References used (characters, location, optional starting frame), editable link to video prompt.

## Procedure
1. Accept *any* starting point: short story, screenplay, an existing image, isolated scene, last frame, or an existing clip. Infer missing information conservatively; do not demand screenplay completion first.
2. Split into visually meaningful panels based on changes in action/angle/emotion. Avoid a panel for every second; 3–6 panels per 15-second clip is a useful default, not a rule.
3. **Separate panels from clips.** Several panels may communicate one moving 15-second continuous camera shot. Group under `clip_id`, with `shot_continuity` = `one_take` when appropriate. If an actual cut is planned, record it explicitly.
4. Calculate timestamps. Panel time ranges within a clip must be non-overlapping, contiguous unless holds are intentional, and stay inside the target duration. Dialogue must realistically fit its assigned panel(s).
5. Generate **frame prompts** for each panel using approved character and environment references, matching camera, composition, action and location. Prioritize quick concept/storyboard rendering over final-polish detail when speed matters.
6. Generate panels in batches if a supported image component permits; preserve previous approved frames and regenerate only selected panel IDs. Save image asset IDs after successful generation.
7. Present a comic-page grid with image, readable text and interactive reorder/edit/replace/regenerate commands where the application supports them. Use text plan fallback when UI rendering is absent.
8. Let the user jump from any panel to `Create First Frame`, `Generate Video Prompt`, `Generate Video`, or `Open Editor` based on available capabilities; skip all irrelevant stages.

## Structured panel schema (minimum)
`panel_id`, `scene_id`, `clip_id`, `order`, `start_s`, `end_s`, `shot_type`, `camera_angle`, `camera_action`, `on_screen_action`, `emotion`, `dialogue[]`, `character_ids[]`, `location_id`, `reference_asset_ids[]`, `image_prompt`, `image_asset_id|null`, `approved`, `continuity_notes`.

## Mini example — lion wakes (15s / one continuous take)
- Panel 1 [0–3s] low mouse-eye view pushing through grass, no dialogue.
- Panel 2 [3–7s] camera reveals mouse, hops onto low tree branch, no dialogue.
- Panel 3 [7–10s] mouse leaps from branch to lion's rounded back, wide framing; no dialogue.
- Panel 4 [10–13s] lion's ear twitches, eyes open, head lifts; mouse running across back.
- Panel 5 [13–15s] mouse hops off front shoulder, lion watches in surprise.
These are **five panels in ONE video shot**, not five required separate AI videos.

## Quality gate
- User can understand story without reading a screenplay.
- Panels are visual and dialogue-rich but do not contain accidental image-generated text.
- Storyboard and screenplay dialogue remain aligned (edits propagate or mark a conflict).
- Reference IDs point to actual project assets; no invented images.
- No rigid dependency on prior workflow stage. Selective edits preserve other panels.
