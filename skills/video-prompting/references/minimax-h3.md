# MiniMax H3 adapter

## Video reference policy — owner correction, 2026-10-22

Fully automated uses text to video for every clip, without image, video or audio references. Assisted manual defaults to text to video; the user may explicitly select a reference workflow and media for a clip. Never attach masters, voices, continuity frames or crops automatically. Explicit previous-frame continuity is optional in Assisted R2V only. Standalone manual reference workflows remain available.

Each T2V prompt independently describes the screenplay-supported background/location, lighting, named cast and appearance, action, camera, exact dialogue and who speaks it, delivery, ambience and sound balance. Progress the story with a clear new beat; avoid repeated establishment and padding. Use the shortest sufficient supported duration. T2V clips may be 5–30 seconds each; 30 seconds is a ceiling, not a target. The installed H3 node permits this frame count but describes lengths beyond its roughly 15-second trained range as untested. Preserve shorter clips when sufficient for brisk story progression. This is clip length, not a render-time guarantee. Upscaling and later character/audio replacement are deferred. Do not rewrite frozen submitted jobs.


Source checked 2026-10-22: [official portable skill](https://github.com/MiniMax-AI/MiniMax-H3/tree/main/skills/h3-prompt-writing), [base guide](https://github.com/MiniMax-AI/MiniMax-H3/blob/main/skills/h3-prompt-writing/references/base-en.txt), [reference guide](https://github.com/MiniMax-AI/MiniMax-H3/blob/main/skills/h3-prompt-writing/references/ref-en.txt). This project summary and examples are original; upstream skill code is not installed.

## Base workflows (T2V / first-and-last frame)
Use fields in order: `integrated_multimodal_description`, `overall_soundscape`, `non_diegetic_music`. Put `[Shot 1]` first; timestamp later cuts against the actual clip timeline. Describe camera behavior in readable prose. Keep stable speaker IDs such as `(S1)`; put exact speech inside `<d>[English] words</d>` and delivery outside. Identify narration explicitly as off-screen voiceover. Reserve `<scenetrans>` for speech crossing a cut and `<cutoff>` for interrupted speech.

For image-conditioned base workflows, describe the real starting-image alignment; for first/last conditioning describe both actual endpoint times. T2V has no image-alignment claim.

Describe ambience and physical nonverbal effects in `overall_soundscape`, independently of dialogue. Put only non-diegetic score in `non_diegetic_music`; use `N/A` when none is intended. Use soundscape `N/A` only for complete silence.

## Reference workflow (R2V)
Order six sections: `subject_definitions`, `summary`, `retention_analysis`, `detailed_description`, `overall_soundscape`, `non_diegetic_music`.

Bind real inputs with `<Picture N>`, `<Video N>`, `<Audio N>`; each media type numbers independently. Define reusable visible identities with `<Subject N>`. Summary starts `[reference generation]` for new action guided by images. State precisely which appearance/world attributes remain and which action changes; never imply video editing when no video is attached. Retention can be fully/partially preserved, attribute transfer or weak reference. Audio copying and voice-style reference are different intentions. Reuse the base guide's speaker, dialogue and timing conventions.

## Local application rules
Before references are attached, prepare content without guessed labels; the request builder supplies the actual ordered bindings. Do not invent cropped subjects. Use continuity images to preserve the world while progressing screenplay action. Explicitly prioritize clear foreground speech, subdued ambience and no competing score unless the scene requires it. Prompting can improve intent, not guarantee audible quality; listen during owner acceptance.

## Written text and beat timing — owner example, 2026-10-22
The owner reports garbled lettering in generated video. Default to an explicitly text-free image: no titles, subtitles, captions, signs, labels, logos or watermarks; prefer unlettered architecture and unbranded costumes/props. Add required readable text during editing. This is project guidance from observed output, not a claim of guaranteed model behavior or an official limitation. Dialogue tags request spoken sound, not visible words.

The owner's rooftop trailer example illustrates useful location, action, camera and sound detail, but its first two intervals overlap (0–1.5s and 1–2.5s). Normalize beat timing to the selected clip length before submission. Four complete sprint/leap/land/roll/leap actions may be too dense for five seconds: simplify to the approved essential beat or split/extend within saved duration settings. Do not invent new action to copy this example. Use the corrected example in [examples.md](examples.md) as a structure, not story canon.

## Concise Base composition
Use the required Base fields even for short prompts. Inside integrated_multimodal_description, use [Shot 1], concrete opening state, one event, optional compatible camera movement and endpoint. Avoid repeated prose already represented by overall_soundscape and non_diegetic_music. Preserve exact speech tags and every assigned source span; brevity never authorizes losing dialogue. Prefer a short unlettered/no-overlay instruction over a long negative list.
