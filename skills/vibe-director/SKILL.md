---
name: vibe-director
description: Direct Vibe Director screenplays and video runs from approved story facts, with coherent staging, camera, lighting, pacing, dialogue and sound; use video-prompting for model-specific rendering prompts.
---
# Director

Treat source story, approved screenplay, owner style and saved settings as authority. Skills guide craft; they never authorize new story events or generation. Preserve uncertainty rather than inventing facts.

## Direct each scene
- Identify the dramatic purpose, emotional turn, visible action, location and participating characters. Keep action, dialogue and sound in their screenplay shot fields.
- Establish geography and screen direction. Preserve spatial relationships, costume, props and lighting motivation across adjacent shots. Change angle or shot size for a story reason.
- Choose one legible composition and compatible camera movement per shot. Specify subject, framing, viewpoint and movement speed. Avoid contradictory camera instructions.
- Motivate key/fill/backlight from the scene; describe direction, softness, contrast and palette. Keep faces readable when dialogue matters. Mood is expressed through staging, light and performance, not adjective piles.
- Allow time for the actual spoken words, breathing, reactions and action. Split at complete thoughts or action beats within the selected workflow bounds. Do not accelerate speech to force excessive text into a short clip.
- Cut on motivated action, attention or an emotional change. Maintain the axis of action unless a deliberate re-establishing shot makes a change understandable. Avoid unrequested cuts inside a continuous shot.
- Give each visible speaker a stable identity, exact supported words, language and delivery. Distinguish on-screen speech, off-screen dialogue and narration. Do not invent dialogue.
- Plan sound in layers: intelligible foreground speech, physical effects, quiet ambience, then optional score. Do not stack competing foreground sounds under dialogue. Use the approved music direction; never add score by default.

## Written text
Default generated footage to unlettered, unbranded surfaces without titles, captions or subtitles. Preserve any screenplay requirement for readable text as a later editing task. Review the video-prompting rooftop example for text-free imagery and non-overlapping beat timing; never copy its action, music or pacing into unrelated scenes.

## Prepare and inspect
Use [video-prompting](../video-prompting/SKILL.md) before writing a generation prompt. Its model adapter controls syntax; the screenplay controls content. Check source coverage, timing, references, sound and workflow limits before freezing a request.

Fully automated uses text to video for every clip, without image, video or audio references. Assisted manual defaults to text to video; the user may explicitly select a reference workflow and media for a clip. Never attach masters, voices, continuity frames or crops automatically. Explicit previous-frame continuity is optional in Assisted R2V only. Standalone manual reference workflows remain available.

Each T2V prompt independently describes the screenplay-supported background/location, lighting, named cast and appearance, action, camera, exact dialogue and who speaks it, delivery, ambience and sound balance. Progress the story with a clear new beat; avoid repeated establishment and padding. Use the shortest sufficient supported duration. T2V clips may be 5–30 seconds each; 30 seconds is a ceiling, not a target. The installed H3 node permits this frame count but describes lengths beyond its roughly 15-second trained range as untested. Preserve shorter clips when sufficient for brisk story progression. This is clip length, not a render-time guarantee. Upscaling and later character/audio replacement are deferred. Do not rewrite frozen submitted jobs.

After rendering distinguish file validation from creative review. Report unclear speech, continuity drift or unexpected cuts as observations; do not claim a good result solely because a file exists. Owner lessons are editable persistent guidance, not model retraining. Changing this skill affects future preparation, not frozen prompts already running.

## Concise rendering direction — owner correction, 2026-10-23
Write short, crisp production prompts: concrete subject and essential setting/light, one observable event or tightly linked action, at most one camera move, and a clear endpoint. Aim for 60–120 words of visual direction, fewer when sufficient; this is a soft target excluding exact dialogue and required workflow fields. Never pad to the target or truncate source action or speech. Remove repeated instructions, decorative adjective/lens lists, reasoning and story summaries. Keep mandatory model section names, exact speaker-labelled dialogue and essential sound balance. 

Keep the screenplay as the full narrative authority. A rendering prompt is a compact translation of its assigned beat, not a rewritten screenplay. Prefer one coherent event per clip; split only through the existing source-span planner so dialogue/action coverage survives. Each T2V clip repeats only the essential appearance and location facts it needs to stand alone. Put sound and music in their designated model fields; use N/A when absent. A short prompt may improve compliance and text-encoding cost, but does not guarantee shorter GPU denoising. Do not alter existing screenplay revisions or frozen requests.

## Vibe Editor handoff
For prompt-driven editing, use the project-local [Vibe Editor director](../../Vibe%20Editor/skills/vibe-editor-director/SKILL.md), its isolated style-learning rules and tool-routing skill. The editor requires creative-brief approval followed by approval of selected media/ranges and tool plan. Consult the implementation ledger in `Vibe Editor/PLAN.md` before claiming an operation is executable. This handoff does not change generation prompting or authorize a render.
