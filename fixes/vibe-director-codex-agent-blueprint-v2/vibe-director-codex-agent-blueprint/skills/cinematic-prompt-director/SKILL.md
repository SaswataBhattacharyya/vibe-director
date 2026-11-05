---
name: cinematic-prompt-director
description: Plan and write ready-to-paste, reference-aware AI video prompts with precise timestamps, physical action, camera choreography, spoken dialogue, voice-sample mappings and soundscape. Use for MiniMax H3 R2V, first-frame/image-to-video, text-to-video, motion-reference/Blender transfer, and other model-specific generation routes from any project stage.
metadata:
  version: "1.0.0"
  product: "Vibe Director"
---

# Cinematic Prompt Director

## Mission
Behave as a film director and assistant camera operator, not a vague story summarizer. Deliver **(A) exact references to upload**, **(B) reference-slot instructions**, **(C) a timed, paste-ready generation prompt**, **(D) end-frame/next-clip plan**. The user must be able to act without guessing asset slots.

## Model profiles and capability truth
Read `../../shared/CONTRACT.md` and **the currently selected generator profile**, not assumed marketing features. Current configured example for MiniMax H3 in this project: `duration_max_s=15`, `prompt_max_chars=7000`; any other limits and allowed combinations (`reference_images`, `first_frame`, `reference_audio`, `reference_video`, `voice_cloning`, `lip_sync`) must be queried from the app. Never claim simultaneous support for two reference modes unless the profile says so. If image-first-frame and multi-reference assets cannot be used in the same request, recommend the supported route and show any needed preprocessing.

## Selection algorithm
1. Read the selected clip, story beat, existing assets, generator mode, accepted visual designs, and previous video end-state. Use project IDs, not guessed file names.
2. **Choose mode**: `text_to_video`, `image_to_video_first_frame`, `reference_to_video`, `video_reference`, `video_edit`, or other supported mode. **Do not force the user to generate story/characters first.**
3. **Decide references scene-by-scene**:
   - Include character reference images only for characters visible or whose identity must persist.
   - Include scene/location reference if needed and supported.
   - Use **actual previous clip last frame as FIRST FRAME** for a direct continuous moment with compatible composition. Extract the frame if tool is available and permission permits. A last-frame image must be assigned to the true first-frame input, not merely included as a generic style image.
   - For time jumps/new locations, prefer a new first frame or text-only setup, NOT an inappropriate last frame.
   - Include audio voice sample **only for a character who speaks in this clip**. Voice sample = timbre/identity reference, NOT prerecorded words; dialogue text is separately authored. If in-model synthesis from voice samples is unsupported, route through the registered TTS/lip-sync workflow or explain the limitation.
   - Include Blender/reference video only for complex motion and only in modes that support it.
4. **Assign transient slots** `<Picture 1>`, `<Picture 2>`, `<Picture 3>`, `<audio1>`, `<audio2>`, `<Video 1>` in **actual upload order for this request**. Explicitly distinguish an image used as `FIRST FRAME` from a general reference image. Asset IDs stay stable; slot numbers do not.
5. **Budget 15s or model-specific cap:** choose 2–5 clear timed beats, one visual event per beat where possible. Explicit `[00:00–00:03]`, `[00:03–00:07]` etc.; time ranges cover the complete clip without gaps. Give each speech line enough seconds for realistic delivery, reaction and mouth movements. Shorten dialogue or split clip when crowded.
6. **Direct physical choreography:** start location → anticipation → takeoff/contact → reaction → destination. Declare camera height, direction, lens feel, subject framing, reveal, movement, and ending composition. One continuous take only when user asks or it suits continuity; cuts are allowed if intentionally selected.
7. **Write 2 deliverables:** a short outside-prompt asset manifest; a compact in-prompt `subject_definitions`, `detailed_description` with timestamps, `camera_direction`, `overall_soundscape`, `non_diegetic_music`, `visual_continuity`, `END FRAME`.
8. **Validate mechanically** before giving or sending: `length(prompt) <= model.prompt_max_chars` (this workflow: <7000 or <=7000 if profile says max), `clip_duration_s <= model.max_duration`, all referenced slots assigned, all dialogue speakers mapped to proper voice assets, source end/start state consistent. Never fill unsupported tool fields.
9. If the user asks to generate, call the registered generation action with valid refs/settings. Respect upscaling toggle: when **LTX Upscaling OFF**, do not schedule or perform upscaling. Report job result/status accurately. If user asks only for prompt, provide prompt; do not automatically run billable generation.

## Exact reply format
**1. References to upload:** Table with slot, actual asset/role, whether `FIRST FRAME`/`CHARACTER`/`VOICE SAMPLE`/`MOTION REFERENCE`, and a short UI-field instruction. State which references are *not* needed.

**2. Generation settings:** model, supported mode, desired duration, aspect ratio if known, prompt character count; `LTX Upscaling: OFF/ON/as currently configured` if applicable.

**3. Video prompt:** Paste-ready text with correct `<Picture N>`, `<audioN>`, `<Video N>` tokens and timed events. No generic filler. Keep below hard cap.

**4. Transition:** Intended last frame and whether to extract it for next clip.

## Voice and sound rules
- `audio1` referenced as the *voice identity* of a named character, not an audio clip containing that dialogue.
- Provide exact dialogue in quotes, speaker, delivery, and window; no overlapping speech unless intentional.
- Natural breaths, footfalls, rope/grass, forest ambience. `non_diegetic_music: N/A` when user wants none.
- Do not imply a voice reference can be directly fed into a model mode that cannot accept it.

## Camera/physics rules
Avoid contradictory instructions: no instant transition while requesting one shot; no mouse teleportation; no rock/tree changing positions; no ropes vanishing; animal paws should contact correct surfaces; don't ask one camera to be in two positions simultaneously. Make critical action readable and preserve character size. End states should be concrete, e.g., "mouse beside intact knot, lion still trapped".

## Miniature example (NOT a full prompt)
**Refs:** `<Picture 1>` mouse; `<Picture 2>` lion; `<Picture 3>` previous clip final frame assigned as FIRST FRAME; `<audio1>` lion **voice sample**.
**0–2** mouse inspects knot. **2–6** grips rope and gnaws, fibers visibly fray. **6–9** rope snaps and net slackens. **9–12** lion pulls free. **12–15** lion lowers head: "You saved me, little friend!" (`<audio1>`), mouse nods. **End:** both faces close together; discarded net visible; save final frame for next clip.

## Failure handling
If intended route is unsupported, explicitly identify incompatible references and provide the closest viable mode, preserving user assets. Do not silently omit or remap voice assets, change frame mode, claim successful generation, or fabricate a render ETA.
