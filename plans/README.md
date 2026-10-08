# Current Story Builder product plans

**Authority:** These are the current product plans, updated from the user's decisions on 2026-10-08. Earlier `migration_plan/`, `PLAN.md`, `REUSE_AUDIT.md` and their journeys/route matrices are historical analysis and implementation reuse evidence. Their product flow, required stages, authority gates and UX choices are superseded where they differ from these plans. Existing source code is reusable material to adapt; it is not an alternative product specification.

## Reading order

1. `GLOSSARY.md` — scene, beat, shot, cut, clip, take, references and direction overrides.
2. `screenplay.md` — merged story/canvas authoring, knowledge graph, readable screenplay and derived production records.
3. `rectifications.md` — one preparation path using V2 source/revision principles, with no competing legacy pipeline.
4. `char_world.md` — optional character/world/clip-frame imagery, prompt annotation and voice bindings.
5. `video_gen.md` — three video workflows, references, prompt collation, settings, generation and retake review.
6. `automation.md` — post-screenplay Automation & Parameters, five Semi choices, fixed quality/dynamic duration, shared isolated entry and Status. `execution_modes.md` is a superseded compatibility pointer.
7. `media_prep.md` — separate Video/Audio/Images workspaces reusing existing tools and feeding the shared media library.
8. `ux_shared.md` — shared context, readable controls, conditional readiness, progress/review, recovery and mobile acceptance.
9. `integration.md` — source repositories, selective reuse, canonical contracts, dependencies/license decision and implementation sequence.
10. `issue_backlog.md` — collaborator/source setup, proposed UI/backend responsibilities, issue drafts, dependencies and first milestone; `issues/` contains unpublished issue bodies.

## Runtime and provider acceptance

[Runtime supervision and provider choices](runtime_and_providers.md) records GPU, acceptance and Codex-first provider boundaries. [OpenMontage licensing context](openmontage_licensing.md) records the pinned AGPL-3.0 terms relevant to proposed imports. These notes supplement the product plans; they do not change Manual/Semi/Full behavior, adopt OpenMontage code, or mark optional workflows ready.

## Proposed implementation details

The staged reuse map, CPU-only isolated T2V slice, and dependent work cards are proposed implementation details subordinate to the product requirements above: [`G2_isolated_video_reuse.md`](implementation/G2_isolated_video_reuse.md), [`LUNA_WORK_PACKAGES.md`](implementation/LUNA_WORK_PACKAGES.md). They do not change navigation, workflow policy, or authorize live generation.

## Accepted current direction

- One unified story workspace with real conversational editing, revision history and a source-linked knowledge graph; no arbitrary story-length cap and no silent truncation.
- One readable screenplay authoring surface. Camera, lighting, mood, action, dialogue, SFX and music are integrated at their relevant levels.
- Production JSON, visual briefs and model prompts derive from screenplay decisions. Prompt wording adapts to model/workflow, selected references, duration and output parameters as the user proceeds.
- Creative prompt changes offer **Update screenplay** or **This take only**.
- Scene → ordered shots → duration-bounded clips is the production hierarchy. Dramatic beats and dialogue link to appropriate spans; a cut is a transition between shots.
- Visual preparation is skippable. Clip frame pairs are optional; first/last-frame mode requires its inputs when used.
- Bound voice and character image assets appear as top recommendations in manual video reference selectors; a binding alone does not attach them. Confirmed Semi automated-video reference policy authorizes the Director to choose compatible assets.
- MiniMax's final submitted prompt is strictly below 7,000 characters. Image-model budgets are model-specific and must be verified/configured. No silent truncation.
- Regular path: screenplay → Automation & Parameters → prompt preparation. Manual clicks Generate/Next with editable/annotatable prompts. Semi has five checkboxes: character images, character-to-audio selection, world images, frame images and video generation; each checked stage confirms defaults/settings. Full skips images and starts each scene with T2V, then uses previous-clip R2V continuation. Semi automated video lets the Director choose FFLF or R2V with prepared frames/character/voice/world inputs, and optionally previous-video continuity in R2V. Automatic video fixes quality initially and allows either fixed duration or Director-selected duration per clip; retain every automatically generated clip.
- `media_prep.md` defines a separate Media Prep area: Video Repertoire & Summariser; Audio Studio, Audio Reconstruct, Music & Sound, Audio Utilities and Audio Repository; Image Detailer and Image Repository. All feed a shared media library with JSON metadata, readable descriptions and search. The main story journey consumes that library.

## What remains to be specified

Media Prep implementation details, final clip assembly/audio mixing, deployment, exact per-model image prompt budgets and graph-specific settings/capacity verification remain later planning or implementation tasks. The initial integrated application completion and acceptance baseline uses the configured Codex CLI. Only after the complete app works with Codex should OpenCode/direct API adapters, flexible model discovery or weaker Ollama/Qwen support be considered as a separate provider-expansion stage; existing Ollama may remain unchanged and need not be tested for Codex acceptance. Existing catalogued capabilities do not automatically become required stages in the new journey.

These are plans, not changes to the running Story Builder. Architecture and code reuse choices will follow these product contracts.

## Shared entry and navigation

The shared image/voice/video screens are directly accessible for isolated work without a story/screenplay. The main story journey supplies context to those same screens. Production V2, Generate, the old Automation Studio and Manual Director are retired as separate product pages; reusable backend logic may remain behind the new journey. Status remains a global page for connectivity, workflow usability, defaults and model prompt/parameter limits. `automation.md` specifies these behaviors.

Both routing decisions are confirmed: Full uses a T2V scene start followed by previous-clip R2V continuation; Semi lets the Director select FFLF or R2V using prepared resources and optional predecessor continuity. See `automation.md` for the authoritative policies and compatibility checks.


## Comparative assessments

`openmontage_comparison.md` compares current OpenMontage source with these plans and proposes selective reuse. It is an assessment, not an adopted change to the authoritative journey or automation policies.


## Integrated planning direction

Current product behavior is retained. StudioDirector's useful UX guidance is incorporated through `ux_shared.md` and the stage-plan additions. `integration.md` defines selective Story Builder/OpenMontage reuse without another controller or media store. Exact covered-source imports remain conditional on license compatibility and bounded technical verification. Final assembly still needs a separate user-approved journey.
