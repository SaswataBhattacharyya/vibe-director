---
name: screenplay-writer
description: Write or revise film stories, screenplays, dialogue, scene breakdowns, emotional beats, and generation-sized clip plans with realistic time budgets. Use when a Vibe Director user brings an idea, fable, outline, script, or requests screenplay/scene planning. Works without requiring characters, storyboard, or media assets first.
metadata:
  version: "1.0.0"
  product: "Vibe Director"
---

# Screenplay Writer

## Mission
Turn a concept into filmable action and dialogue **without imposing a compulsory workflow**. Distinguish an overall story, a screenplay **scene** (time/place/dramatic event), a **shot** (camera setup), a **storyboard panel** (visual beat), and a **generation clip** (one output constrained by a model). Do not conflate these units.

## Runtime integration
Before reading or changing project state, follow `../../shared/CONTRACT.md` and the Director's capability registry. Read current story, characters, locations, accepted dialogue, clips, and model profile when available. Use registered create/update actions rather than merely describing UI changes. If no app tool exists, produce a portable draft and mark it `uncommitted`; never pretend it was saved. Users may invoke this skill directly from any page.

## Procedure
1. **Identify intent.** Is the user asking for a logline, full screenplay, single scene, rewritten dialogue, alternate ending, or timed clip breakdown? Reuse what already exists rather than regenerating approved work.
2. **Extract the story spine:** protagonist, goal, obstacles, turning points, cause-and-effect, resolution and emotional arc. Preserve user's plot and tone; do not add characters or new story beats without reason.
3. **Write screenable actions.** State what appears on camera; replace unfilmable abstractions with visible behavior. Include physical blocking and essential props. Dialogue belongs to named speakers, not narration unless requested.
4. **Handle time deliberately.** Give `estimated_story_duration_s`, scene duration ranges, and per-line speech time estimates. Use a configurable speaking-rate assumption, typically ~2.0–2.5 spoken words/second plus pauses and reactions. Do not guarantee voice timing. Account for movement, expression changes, and camera travel.
5. **Split into model-sized clips only if needed.** The current user profile uses a **15-second maximum** and **7,000-character prompt maximum** for MiniMax H3. These are *generation constraints*, not a screenplay length limit. If a 35-second scene is requested, produce multiple clips (e.g., 12 + 12 + 11 seconds) with valid end/start bridges. Other models use their own profile.
6. **Plan transitions.** For each clip, identify starting state, final frame, whether a time/location jump occurs, and whether next generation should reuse the preceding clip's final image.
7. **Persist structured edits** through available project capabilities only after honoring user intent and permissions. Retain previous versions and stable IDs.

## Screenplay output contract
Return human-readable screenplay plus structured entities suitable for storyboard and prompting:

- `story_id`, `title`, `genre`, `style_goal`, `estimated_story_duration_s`
- `scene_id`, `slugline` (`EXT. FOREST - DAY`), `dramatic_purpose`, `location_id`, `time_of_day`, `characters`, `action`, `emotion`, `dialogue[]`, `duration_estimate_s`
- `clip_plan[]`: `clip_id`, `scene_id`, `max_duration_s`, `target_duration_s`, `start_state`, `end_state`, `beats[]` with `[start_s,end_s]`, `continuation_policy` (`last_frame` / `new_first_frame` / `none` / `decide_later`)
- For dialogue: `speaker_character_id`, `text`, `delivery`, `voice_asset_id` if already assigned, `estimated_spoken_s`; **a voice sample is not the dialogue recording**.
- `open_questions[]` only for materially blocked details. Otherwise make reversible creative defaults.

## Quality gate
- Every important event has cause, readable action, reaction, and consequence.
- Voices are never assigned by guessed file names; use actual project assets.
- Dialogue fits the assigned time with breathing space; never force two long lines into three seconds.
- A clip's total beat durations equal its intended running time and respect selected model's max duration.
- Preserve user-approved canonical story details and continuity.
- A screenplay draft can be used immediately, even if no storyboard, image, or model is selected.

## Example: The Lion and the Mouse
Scene `forest_rescue`: mouse finds trapped lion, chews through the binding rope, lion escapes. Proposed 15-second clip: 0–2 inspect knot; 2–6 chew; 6–9 rope frays and snaps; 9–12 net slackens, lion steps free; 12–15 lion says a **brief** grateful line. End with lion's head beside mouse for a possible final-scene first frame.
