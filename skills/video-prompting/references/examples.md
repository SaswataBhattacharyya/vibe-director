# Original screenplay-to-prompt examples

## Video reference policy — owner correction, 2026-10-22

Fully automated uses text to video for every clip, without image, video or audio references. Assisted manual defaults to text to video; the user may explicitly select a reference workflow and media for a clip. Never attach masters, voices, continuity frames or crops automatically. Explicit previous-frame continuity is optional in Assisted R2V only. Standalone manual reference workflows remain available.

Each T2V prompt independently describes the screenplay-supported background/location, lighting, named cast and appearance, action, camera, exact dialogue and who speaks it, delivery, ambience and sound balance. Progress the story with a clear new beat; avoid repeated establishment and padding. Use the shortest sufficient supported duration. T2V clips may be 5–30 seconds each; 30 seconds is a ceiling, not a target. The installed H3 node permits this frame count but describes lengths beyond its roughly 15-second trained range as untested. Preserve shorter clips when sufficient for brisk story progression. This is clip length, not a render-time guarantee. Upscaling and later character/audio replacement are deferred. Do not rewrite frozen submitted jobs.


These fictional examples are not facts to inject into an owner's story. Durations are illustrative and must fit the selected graph.

## T2V: a quiet ten-second courtroom line
Screenplay: Wide courthouse interior. A clerk stands and says, “The court is now in session.” Locked camera, soft window light, restrained room ambience, no score.

```
integrated_multimodal_description: [Shot 1] A locked wide view establishes the courthouse interior in soft lateral window light. The clerk (S1) stands calmly, pauses, then says clearly at a natural pace, <d>[English] The court is now in session.</d> Hold long enough for the complete line and a short reaction beat. Keep the other people quiet and the geography stable; no cut.
overall_soundscape: A subdued room tone and a brief chair movement precede the line. Speech is the clear foreground; ambience stays soft underneath it.
non_diegetic_music: N/A
```

## R2V: next courtroom shot, continuity image plus verified crop
Screenplay: Medium shot of the same clerk looking toward the entrance. No dialogue or score. Attached Picture 1 is the previous clip's decoded last frame; Picture 2 is a verified crop of this clerk. If that crop is unavailable, omit Picture 2 and its identity claim.

```
subject_definitions: <Subject 1> is the clerk shown in <Picture 2>.
summary: [reference generation] A new medium shot of <Subject 1> turning toward the entrance in the courthouse established by <Picture 1>.
retention_analysis: Partially preserve <Picture 1>: room geometry, materials, window-light direction and palette remain consistent; framing and action change. Preserve <Subject 1>'s visible appearance from <Picture 2>, not the old pose. No video or audio reference is attached.
detailed_description: [Shot 1] At eye level, hold a steady medium composition of <Subject 1>. The clerk turns toward the entrance and settles into an attentive stillness. Match the soft side light and the established screen direction. Progress this new action rather than replaying the previous clip. No dialogue, no cut.
overall_soundscape: Quiet room tone with a subtle clothing rustle as the clerk turns.
non_diegetic_music: N/A
```

## Silent exercise scene
For an approved eight-second continuous bench-press demonstration, describe the starting posture, controlled lowering, complete press and return posture in visual order. Specify the locked viewpoint and stable anatomy. If the screenplay requests complete silence, set both sound fields to `N/A`; omit vocal tags. A matching start/end posture is a request, not proof of a seamless loop. Check the rendered endpoints before export.

## Failure checks
- Long dialogue in five seconds: split at a complete sentence or extend within approved bounds; do not request rushed speech.
- Loud storm plus quiet speech: prioritize speech intelligibility and subordinate the storm during the line, preserving the scene's atmosphere.
- No music direction: do not add cinematic score to fill silence.
- Missing crop: show that no crop was attached; never label the full world frame as a verified close-up.

## Owner rooftop example: concise one-event adaptation
The owner's dense five-second trailer prompt demonstrates a look, not an instruction to copy multiple leaps and cuts into every clip. This fictional example is usable only if the approved screenplay assigns this leap and landing to one clip. Never drop other assigned source events to shorten the prompt; split through source spans instead.

```
integrated_multimodal_description: [Shot 1] Rain-wet rooftops at dusk, city towers behind. Arun, a lean man in a dark coat, leaps across a narrow gap and lands on the opposite roof. Track sideways through the jump, ending as he regains his footing. Realistic live action, cool side light. Unlettered buildings; no overlays. No dialogue.
overall_soundscape: Wind, coat rustle, one landing impact. No voices.
non_diegetic_music: N/A
```

The invented name and costume demonstrate concreteness; replace them with approved screenplay facts. Do not copy this example's action into another story. If readable text is essential, retain it as an editing requirement.
