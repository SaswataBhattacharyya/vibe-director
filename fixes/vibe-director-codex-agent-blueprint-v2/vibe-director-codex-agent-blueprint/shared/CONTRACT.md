# Vibe Director — Shared Skill Contract (v1.0)

This document applies to ALL six skills. It is a **design contract**, not evidence that integrations already exist. The supplied app review and source ZIP will determine actual tool names, routes, available models and limits.

## Operating principles

1. **One chat Director; six optional skills.** User may start from any page, asset, story, prompt, storyboard, audio clip or video. No rigid wizard. The Director can use multiple skills for one request, but calls only what's needed.
2. **Every app component is potentially reachable from chat**, subject to actual registered tools, user permissions and capabilities. A UI button alone is not a callable tool; it needs a backend action/adapter and readable state.
3. **Inspect before operating.** Use `capability.list`/catalog (or the actual mapped equivalent) to discover actions with schema, allowed modes, side effects, cost and availability. `capability.invoke` is an *illustrative contract name*, not a real API until mapped.
4. **Single project truth.** Store canonical IDs in project state; never assume `<Picture 1>` is permanently the mouse. Asset IDs are stable, prompt slot labels are regenerated per request.
5. **Idempotent editing.** Prefer upsert by stable entity ID, version checks and append-only generation records. Avoid overwriting an approved clip or reference. User changes must update project context/UI when tools return success.
6. **Skip-friendly.** Missing screenplay, character sheet or storyboard is not a blocker if the user has sufficient assets to perform requested generation. Supply minimal defaults and ask only about indispensable missing information.
7. **Model-specific validation.** Selected model profile governs input modes, resolution, aspect ratio, max duration, prompt budget, reference count/combinations and audio behaviors. This user's current MiniMax H3 settings: 15 seconds maximum and 7,000 characters maximum for the final generation prompt.
8. **Voice sample ≠ spoken recording.** `female_01.wav` is the mouse identity sample and `Morgan_Freeman CC3.wav` is the lion identity sample in the current example, but resolve **actual** project records. Text of new dialogue is provided separately. Check whether model supports referenced speech generation and lip-sync; otherwise use TTS/lip-sync components only when available.
9. **First-frame semantics.** The last frame from a prior clip is an image asset to assign to the next clip's true `first_frame` slot (when supported), not just a generic image reference. Reuse it only when story/camera continuity warrants it.
10. **Tool-result honesty.** `planned`, `ready`, `submitted`, `running`, `completed`, `failed` are distinct states. Never claim to have invoked an unavailable tool or generated a video when only a prompt was authored.
11. **Side effects.** Creating media may incur time/cost; changing files or settings is persistent. Honor app consent, permissions, budget controls and user confirmation policies; never bypass access control or launch unrequested generations. `LTX Upscaling: OFF` must skip any upscale job, not merely hide its result.
12. **Estimated runtime.** Report planned *on-screen duration* exactly. Report expected render/wall-clock time only when data is available from actual tool/provider; avoid invented ETAs.

## Logical capabilities the Director should be able to use (once mapped)

Discovery/context: `capabilities.list`, `project.read`, `project.update`, `assets.list`, `assets.get`, `assets.import`, `assets.link`, `models.list`, `models.get_profile`, `settings.read`, `settings.update`, `jobs.read`.

Creative: `screenplay.save`, `characters.save`, `images.generate`, `environments.save`, `storyboard.panels.save`, `storyboard.render`, `video.prompts.save`, `video.generate`, `video.preview`, `voice.generate`, `video.lipsync`.

Utilities/editor: `frames.extract_first`, `frames.extract_last`, `frames.extract_at`, `audio.extract`, `audio.transcode`, `video.upscale`, `video.upscale.set_enabled`, `editor.add_clip`, `editor.trim`, `editor.reorder`, `editor.set_audio`, `editor.preview`, `export.render`.

**These are names for mapping only.** The real app may expose different, fewer, more or richer actions. Register *all* safely exposable functions from the supplied source after review, not only this list.

## Capability descriptor (illustrative)
```json
{
  "id": "frames.extract_last",
  "display_name": "Extract Last Frame",
  "description": "Create a new PNG asset from the last visible frame of a video",
  "input_schema": {"type":"object", "properties":{"video_asset_id":{"type":"string"}}},
  "returns": ["asset_id", "source_video_asset_id", "source_time_s"],
  "available": false,
  "permission": "write_asset",
  "side_effect": "creates_asset",
  "cost_hint": "local",
  "adapter": null
}
```
`available:false` and `adapter:null` explicitly indicate **not connected yet**. App's real registry must be populated from verified code/runtime.

## Recommended project record shape
- `project`: id, title, style bible, selected model/profile, output defaults, optional settings (e.g. `ltx_upscaling_enabled`).
- `assets`: stable ID, media type, origin, filepath/URL in app, upload metadata, approved status, role(s), derived-from links, version.
- `characters`: stable ID, physical/visual identity, approved reference asset IDs, voice sample IDs, relative scale.
- `locations`: stable ID, spatial/layout bible, style, image asset IDs.
- `scenes`: slugline, dramatic purpose, script/dialogue, location, story time.
- `clips`: scene links, running time, generation mode, model, timecoded beats, start/end state, prompt ID, reference manifest, generation IDs.
- `storyboard_panels`: sequence/time/shot/comic image/dialogue/camera notes; panel can share `clip_id` with adjacent panels.
- `continuity`: source end frame, camera/character/prop positions and state, chosen continuation mode.

See `project.schema.json` for a portable starting structure (extensible, not yet mapped to current app DB).

## Multi-skill routing examples
- "Write me a fable" → Screenplay Writer.
- "Make my mouse image" → Character Designer (+ `images.generate` if available).
- "Make matching forest background" → Environment Designer.
- "Show whole story like comic" → Storyboard Director; optionally Character/Environment Designers if no reference assets.
- "Generate the next 15-second H3 prompt" → Continuity Director → Cinematic Prompt Director, consulting Screenplay if timing needs revision.
- "Turn off LTX upscaling" → Director queries settings capability; invokes mapped setting toggle if authorized; confirms actual returned state. No forced skill stage.
- "Extract last frame and use it" → Director invokes media extraction and maps returned image to first-frame slot if supported.
- "Open this shot in Vibe Editor" → Director invokes registered editor navigation/action, preserving `clip_id` and assets.

## Prompt reference manifest contract
The video prompt response should show a human-readable manifest **outside** the prompt and structured assignment inside project:
```json
{
  "generator_mode": "image_to_video_first_frame",
  "duration_s": 15,
  "references": [
    {"slot":"<Picture 1>", "asset_id":"mouse-ref-v1", "role":"character"},
    {"slot":"<Picture 2>", "asset_id":"lion-ref-v1", "role":"character"},
    {"slot":"<Picture 3>", "asset_id":"scene4-lastframe", "role":"first_frame"},
    {"slot":"<audio1>", "asset_id":"lion-voice", "role":"voice_sample", "character_id":"lion"}
  ]
}
```
The sample is **illustrative**: actual slot syntax and supported asset combinations must be validated for the selected model and UI.
