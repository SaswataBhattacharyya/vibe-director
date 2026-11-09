---
name: video-prompting
description: Translate approved screenplay shots into precise model-specific video prompts, including actual reference roles, achievable timing, camera, action and intelligible sound; called by vibe-director.
---
# Video prompting

## Video reference policy — owner correction, 2026-10-22

Fully automated uses text to video for every clip, without image, video or audio references. Assisted manual defaults to text to video; the user may explicitly select a reference workflow and media for a clip. Never attach masters, voices, continuity frames or crops automatically. Explicit previous-frame continuity is optional in Assisted R2V only. Standalone manual reference workflows remain available.

Each T2V prompt independently describes the screenplay-supported background/location, lighting, named cast and appearance, action, camera, exact dialogue and who speaks it, delivery, ambience and sound balance. Progress the story with a clear new beat; avoid repeated establishment and padding. Use the shortest sufficient supported duration. T2V clips may be 5–30 seconds each; 30 seconds is a ceiling, not a target. The installed H3 node permits this frame count but describes lengths beyond its roughly 15-second trained range as untested. Preserve shorter clips when sufficient for brisk story progression. This is clip length, not a render-time guarantee. Upscaling and later character/audio replacement are deferred. Do not rewrite frozen submitted jobs.


## Shared procedure
1. Read the accepted shot, scene context, saved style, duration and workflow. Preserve assigned source spans and exact dialogue. No new canon.
2. State what is visible: subject, setting, composition, light, ordered action, camera behavior, ending state. Separate identity/world continuity from motion to generate now.
3. Inventory only attached references in request order. Explain what to retain and what changes. An earlier clip's last frame is a continuity image, not the requested final frame of the new clip. Character crops preserve appearance, not pose or old action.
4. Specify the audio foreground and background separately. Exact words, identified speaker, language, natural delivery and enough time come first. Keep ambience/effects subordinate during speech; use music only if approved. For silent scenes explicitly request silence. Do not promise that negative instructions guarantee silence or clarity.
5. Apply the selected model's official adapter. Keep graph duration, resolution, reference and prompt limits authoritative. Never transfer cloud capabilities to a local graph without support. If no adapter exists, flag that gap rather than applying another model's syntax.
6. Keep generated frames free of written text by default: no titles, captions, subtitles, signs, labels, logos or watermarks. Describe unlettered surfaces and unbranded props where relevant. Required readable text belongs in later editing; do not silently omit a screenplay text requirement. Spoken dialogue remains audio, never a subtitle instruction. Negative wording reduces ambiguity but does not guarantee artifact-free output.
7. Review for contradictory camera moves, impossible timing, duplicated dialogue, invented reference labels, unsupported cuts and source omissions. For timed beats, use ordered, non-overlapping intervals within the actual clip duration; keep timing labels as prompt metadata, never visible overlays. Keep the result under the local prompt limit. Preserve structure when splitting into clips.

## MiniMax H3
Use [the H3 adapter](references/minimax-h3.md), based on MiniMax's official open prompt-writing skill. [Worked screenplay examples](references/examples.md) illustrate T2V and image continuity. Use examples as craft demonstrations, never as story facts.

Other models need their own cited adapter. These general principles are reusable; H3 field names and tags are not universal.

Use the shared [visual craft glossary](../prompt-craft/references/visual-glossary.md) when choosing cinematic vocabulary. The owner's [frost-glider example](references/owner-frost-glider.md) demonstrates continuous chase choreography, speed ramps, atmosphere and light separation. Preserve its craft as a reference, not its story facts or an unverified promise of five-second execution.

## Concise rendering direction — owner correction, 2026-10-23
Write short, crisp production prompts: concrete subject and essential setting/light, one observable event or tightly linked action, at most one camera move, and a clear endpoint. Aim for 60–120 words of visual direction, fewer when sufficient; this is a soft target excluding exact dialogue and required workflow fields. Never pad to the target or truncate source action or speech. Remove repeated instructions, decorative adjective/lens lists, reasoning and story summaries. Keep mandatory model section names, exact speaker-labelled dialogue and essential sound balance. 

Keep the screenplay as the full narrative authority. A rendering prompt is a compact translation of its assigned beat, not a rewritten screenplay. Prefer one coherent event per clip; split only through the existing source-span planner so dialogue/action coverage survives. Each T2V clip repeats only the essential appearance and location facts it needs to stand alone. Put sound and music in their designated model fields; use N/A when absent. A short prompt may improve compliance and text-encoding cost, but does not guarantee shorter GPU denoising. Do not alter existing screenplay revisions or frozen requests.

## Owner-approved detailed examples — 2026-10-23
The owner reverted the plain-prose simplification. Use [the supplied cinematic prompts](references/owner-cinematic-examples.md) as approved examples of detailed H3 composition: shot-specific staging, camera, lighting, ordered cuts, continuity, soundscape and music. Preserve that detail when requested; the earlier 60–120-word suggestion is not a hard cap and must not force these examples into generic summaries. Batch headers are an outer file format, independent of the full structured prompt inside quotes. Adapt example craft to the actual screenplay rather than copying its story facts.
