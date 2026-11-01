## Multi-view 3D integration — 2026-11-01

[TRELLIS.2 and Pixal3D integration](multiview_3d_integration.md): implemented TRELLIS Single image/Multi-view, Pixal multi-view only, and Single item/Batch on both. Separate images or explicitly split/reviewed sheets, labelled 2/4 views, padded panels, existing GLB viewer and Single-only Blender. Dedicated TRELLIS startup readiness and conservative lost-reply recovery; Toolkit unchanged. Build, 21 backend tests, three mocked browser tests and live idle/node-schema checks pass. Actual new GPU generation remains owner-clicked and untested.

## Local data cleanup and shared media — 2026-11-01

[Local data cleanup](local_data_cleanup.md) records the completed shared-root cutover and optional output destinations. Live browsing finds 68 YouTube downloads (65 baseline plus three retained legacy videos); 176 analyzed occurrences, 62 donor manifests and saved job/ACE paths resolve. Destination choices, verified publication and save-only recovery are wired. The reversible journal is `local_data/reports/storage-migration/applied-20261101/`. No media/checkpoints were permanently deleted. Focused checks pass (92 backend, five browser, frontend build); actual new GPU/provider output acceptance remains owner-clicked.

## Music Jukebox proposal — 2026-10-30

[Music Jukebox](music_jukebox.md): sibling of ACE-Step/Control-Foley, with waveform editing, composition/beat patterns, DJ decks, mixer, recording, project persistence and explicit Vibe Editor handoff. Planning only; no new packages or application changes.

## TRELLIS, image training and TTS plan — 2026-10-29

[trellis_tts.md](trellis_tts.md) records Image to 3D Single/Batch with Single-only Open with Blender; automatic startup/opening of the existing AI Toolkit from Characters/Worlds; Z-Image-only LoRA inference controls; and Audio Studio recording, speech and voice-processing organization. No new image-training pages or TRELLIS fine-tuning tab. Implemented locally: [verification and remaining model acceptance](trellis_tts_implementation.md). Backend/image worker reloaded while idle; no GPU generation/training started.

## ACE-Step dataset expansion planned — 2026-10-28

[Luna execution plan](ace_step_bgm_expansion.md): append eligible additional sources and unused master sections, preserve existing edits, reuse the downloader/extractor, validate and hand off for owner listening review. Planning only; no expansion downloads or training started.

## Text to Image folder references — 2026-10-29

[Text to Image and folder-based reference browser](text_to_image_folder_references.md) records the approved user-selected output folder, recursive reference gallery, explicit reference attachment, permanent deletion and Characters/Worlds/Frames integrations. Implemented locally; owner UI acceptance and a manually clicked generation remain pending.

## Media picker correction implemented — 2026-10-27

Source-first shared browsing, nested named Workspaces/folders, global download indexing without copying, selection controls and R2V limit warnings are implemented. See [handoff](HANDOFF.md) for checks and runtime handles. The historical planning-only entries below are superseded for this bounded change; wider UI redesign is still separate.

## Latest media browsing correction — 2026-10-27

[Media selection and storage](media_selection_storage.md) now separates completed physical migration from the pending source-first nested browser redesign. Downloads are global, workspaces are a named nested source, R2V keeps separate compatible media groups, and over-limit selections require a warning. [UI improvement](ui_improvement.md) records the shared layout repair. Earlier proposal/awaiting-confirmation entries below are historical; the migration is already recorded as implemented locally.

## UI improvement — 2026-10-27

[UI improvement plan](ui_improvement.md) covers readable prompts/messages, shared controls, page composition and all three existing themes. Only the immediate GPU warning repair is implemented; wider batches remain pending.

## Owner clarification — physical storage cleanup (2026-10-27)

`media_selection_storage.md` now requires actual repository/data folder reorganization with minimum necessary code disruption, not only a logical library UI. Revised root-entry audit and target layout await review and a concrete migration mapping. Select-all/deselect-all-shown behavior is accepted. No migration or code changes performed.

## Proposed media selection and storage audit — 2026-10-27

[Media inputs, selection and storage](media_selection_storage.md) records the current source/path audit, per-operation media compatibility table, cross-source dropdowns, select/deselect rules and minimal storage migration proposal. **Awaiting owner confirmation; not implemented.** No files or models are moved by this plan.

# Vibe Editor — 2026-10-26

[Vibe Editor integration plan](../Vibe%20Editor/PLAN.md): prompt editing under Media Prep, pinned HyperFrames acquisition, two chat/button approvals, shared media selection, project persistence and isolated learned styles. Core implementation is in place; provider/render acceptance and advanced editing adapters remain open in the plan ledger. Existing generation pipelines remain unchanged.

## Completion gate — owner correction, 2026-10-13

[CODING_COMPLETION_GATE.md](CODING_COMPLETION_GATE.md) is the finite copying/coding exit ledger: Luna closes required implementation and configuration, then consolidated Sol 6.1 medium review/fixes, then manual acceptance with Debug ON. This supersedes older review timing for the current completion handoff. Reuse existing evidence and code; do not restart completed work.

**Current decision:** the ledger records C1–C12 and the consolidated Sol medium review as PASS. Therefore Luna's copy/code stage and Sol review are complete; the next gate is owner-run acceptance, starting with the prepared Video Summariser Analyze session. Historical P2–P7 “open/in progress” entries are runtime/acceptance status or earlier checkpoints, not an instruction to redo coding. Reopen a coding row only for a specific reproduced required behavior defect.

## Current execution status — 2026-10-11

The owner resumed the goal. Continue implementation locally; Git hosting operations remain deferred until explicitly requested. Keep `setup_comfy_and-stuff`; use [donor_independence.md](donor_independence.md) for the selective Story Builder/OpenMontage asset transfer and independence audit. The corrected copy pass completed; the selected files already existed in ignored `local_data/donor_migration`, so it transferred 0 new bytes. The staged tree still requires an inventory before cleanup or donor retirement. No donor checkout has been deleted. Do not let old pause wording in historical notes stop implementation.

> Active completion scope: [GOAL.md](GOAL.md). Backend wiring and the full usable UI are in scope now. Build locally on the agreed Ashu foundation; Git hosting work and Ashu's fine design/detail refinement wait until the owner explicitly asks to resume them.

## Owner correction — 2026-10-11 (authoritative)

Luna implements, checks and fixes each part directly; no Luna workers. The next planned GPT-6.1 Sol medium review is after P2–P6 are complete, followed by a final review after P7 and remaining integration fixes. Do not invoke Sol per helper, copied tool, issue, slice or individual stage. Earlier Sol help is only when Luna is genuinely stuck on a specific issue after focused investigation; a potentially risky change alone is not a trigger. Pass relevant files, evidence and one concrete question. Sol may make bounded fixes without spawning workers; Luna verifies them itself. Do not request an automatic follow-up Sol review. This replaces all older R1/R2/R3 and three-milestone review triggers.

Reuse Story Builder’s video_audio_analyzer, Video Repertoire/Summariser, audio tools and Image Detailer as the main implementation. Copy/adapt the smallest working file set and existing Vibe adapters; change only necessary imports, paths, API/UI seams, shared asset metadata and job/GPU safeguards. Do not rewrite engines or build speculative frameworks. Implement notes.md’s nested pages, search, carousels, previews and saved selections alongside wiring; current UI shells are not completion evidence.

Implementation is active when the runtime goal is active. Git coordination remains deferred; live acceptance is owner-clicked. Older runtime-status prose is historical; use the goal tool for actual status.


## Notes-integrated implementation order — 2026-10-11

Read [remaining_app.md](remaining_app.md) before older stage details. It applies the latest notes, removes the global Prompts destination, combines Characters & Voices, defines nested Media Prep/Search and correct Retake/Next, and plans derived character references. [OWNER_DUMMY_RUNS.md](OWNER_DUMMY_RUNS.md) specifies mock versus real owner-clicked acceptance. Older conflicting flow text is superseded.


> Current development instructions: [development_workflow.md](development_workflow.md). Luna implements from existing sources; GPT-6.1 Sol reviews at bounded milestones. Product modes are **Assisted manual** (none/some/all checkboxes) and **Fully automated** (image-free video chain). All checked remains the asset-based route, as confirmed by the owner.

Implementation handoff: Luna works directly from the relevant plan and local implementation slice using Ponytail full. Sol reviews once after substantial P2–P6 completion and once at final P7 completion; earlier only if genuinely stuck after focused investigation. Luna verifies any bounded fixes. Reuse Story Builder first and OpenMontage only within the recorded license boundary. Git/GitHub coordination is deferred until the owner asks. See `development_workflow.md` for source locations and task rules.

# Current Story Builder product plans

**Authority:** These are the current product plans, updated from the user's decisions on 2026-10-08. Earlier `migration_plan/`, `PLAN.md`, `REUSE_AUDIT.md` and their journeys/route matrices are historical analysis and implementation reuse evidence. Their product flow, required stages, authority gates and UX choices are superseded where they differ from these plans. Existing source code is reusable material to adapt; it is not an alternative product specification.

## Reading order

Start with `production_styles.md`: Production Type & Style precedes story authoring/import; direct generation may select style without a story. Then follow the stage references below.

1. `GLOSSARY.md` — scene, beat, shot, cut, clip, take, references and direction overrides.
2. `screenplay.md` — merged story/canvas authoring, knowledge graph, readable screenplay and derived production records.
3. `rectifications.md` — one preparation path using V2 source/revision principles, with no competing legacy pipeline.
4. `char_world.md` — optional character/world/clip-frame imagery, prompt annotation and voice bindings.
5. `video_gen.md` — three video workflows, references, prompt collation, settings, generation and retake review.
6. `automation.md` — post-screenplay Automation & Parameters, five Assisted manual choices, fixed quality/dynamic duration, shared isolated entry and Status. `execution_modes.md` is a superseded compatibility pointer.
7. `media_prep.md` — separate Video/Audio/Images workspaces reusing existing tools and feeding the shared media library.
8. `ux_shared.md` — shared context, readable controls, conditional readiness, progress/review, recovery and mobile acceptance.
9. `integration.md` — source repositories, selective reuse, canonical contracts, dependencies/license decision and implementation sequence.
10. `issue_backlog.md` — collaborator/source setup, proposed UI/backend responsibilities, issue drafts, dependencies and first milestone; `issues/` contains unpublished issue bodies.

## Runtime and provider acceptance

[Runtime supervision and provider choices](runtime_and_providers.md) records GPU, acceptance and Codex-first provider boundaries. [OpenMontage licensing context](openmontage_licensing.md) records the pinned AGPL-3.0 terms relevant to proposed imports. These notes supplement the product plans; they do not change Assisted manual/Fully automated behavior, adopt OpenMontage code, or mark optional workflows ready.

## Proposed implementation details

The staged reuse map, CPU-only isolated T2V slice, and dependent work cards are proposed implementation details subordinate to the product requirements above: [`G2_isolated_video_reuse.md`](implementation/G2_isolated_video_reuse.md), [`LUNA_WORK_PACKAGES.md`](implementation/LUNA_WORK_PACKAGES.md). They do not change navigation, workflow policy, or authorize live generation.

## Accepted current direction

- One unified story workspace with real conversational editing, revision history and a source-linked knowledge graph; no arbitrary story-length cap and no silent truncation.
- One readable screenplay authoring surface. Camera, lighting, mood, action, dialogue, SFX and music are integrated at their relevant levels.
- Production JSON, visual briefs and model prompts derive from screenplay decisions. Prompt wording adapts to model/workflow, selected references, duration and output parameters as the user proceeds.
- Creative prompt changes offer **Update screenplay** or **This take only**.
- Scene → ordered shots → duration-bounded clips is the production hierarchy. Dramatic beats and dialogue link to appropriate spans; a cut is a transition between shots.
- Visual preparation is skippable. Clip frame pairs are optional; first/last-frame mode requires its inputs when used.
- Story-linked Assisted manual R2V attaches shot-relevant selected character/world masters and assigned speaker voices automatically, with editable per-shot overrides, capacity choices and instruction-scope review. See the 2026-10-16 correction in video_gen.md. Isolated reference creation remains user-selected.
- MiniMax's final submitted prompt is strictly below 7,000 characters. Image-model budgets are model-specific and must be verified/configured. No silent truncation.
- Regular path: screenplay → Automation & Parameters → prompt preparation. Assisted manual with no checks uses Generate/Next with editable/annotatable prompts. Its five checkboxes are: character images, character-to-audio selection, world images, frame images and video generation; each checked stage confirms defaults/settings. Fully automated skips image generation and starts each scene with T2V when no direct style video is selected; a selected style video changes the first clip to R2V. Later clips use previous-clip R2V continuation and retain selected style-video conditioning subject to verified reference capacity. Assisted manual automated video lets the Director choose FFLF or R2V with prepared frames/character/voice/world inputs, and optionally previous-video continuity in R2V. Automatic video fixes quality initially and allows either fixed duration or Director-selected duration per clip; retain every automatically generated clip.
- `media_prep.md` defines a separate Media Prep area: Video Repertoire & Summariser; Audio Studio, Audio Reconstruct, Music & Sound, Audio Utilities and Audio Repository; Image Detailer and Image Repository. All feed a shared media library with JSON metadata, readable descriptions and search. The main story journey consumes that library.

## What remains to be specified

Media Prep implementation details, exact export/audio settings, deployment, exact per-model image prompt budgets and graph-specific settings/capacity verification remain later planning or implementation tasks. The initial integrated application completion and acceptance baseline uses the configured Codex CLI. Only after the complete app works with Codex should OpenCode/direct API adapters, flexible model discovery or weaker Ollama/Qwen support be considered as a separate provider-expansion stage; existing Ollama may remain unchanged and need not be tested for Codex acceptance. Existing catalogued capabilities do not automatically become required stages in the new journey.

These are plans, not changes to the running Story Builder. Architecture and code reuse choices will follow these product contracts.

## Shared entry and navigation

The shared image/voice/video screens are directly accessible for isolated work without a story/screenplay. The main story journey supplies context to those same screens. Production V2, Generate, the old Automation Studio and Manual Director are retired as separate product pages; reusable backend logic may remain behind the new journey. Status remains a global page for connectivity, workflow usability, defaults and model prompt/parameter limits. `automation.md` specifies these behaviors.

Both routing decisions are confirmed: Fully automated uses a T2V scene start followed by previous-clip R2V continuation; Assisted manual lets the Director select FFLF or R2V using prepared resources and optional predecessor continuity. See `automation.md` for the authoritative policies and compatibility checks.


## Comparative assessments

`openmontage_comparison.md` compares current OpenMontage source with these plans and proposes selective reuse. It is an assessment, not an adopted change to the authoritative journey or automation policies.


## Integrated planning direction

Current product behavior is retained. StudioDirector's useful UX guidance is incorporated through `ux_shared.md` and the stage-plan additions. `integration.md` defines selective Story Builder/OpenMontage reuse without another controller or media store. Exact covered-source imports remain conditional on license compatibility and bounded technical verification. The approved first export is ordered accepted clips with optional audio tracks; see `assembly.md`.

## Production setup before authoring

[Production type, style and story import](production_styles.md) precedes the story/screenplay journey and specifies custom style/type creation and TXT/PDF ingestion. [Ashu handoff](ASHU_UI_HANDOFF.md) also records provisional implementation, publication and review-before-merge rules.

## First assembly target

Owner selected screenplay-ordered accepted clips → one exported video with optional audio tracks. See [assembly.md](assembly.md) for the accepted target and proposed contracts; a full timeline is not part of this first target. Exact export/audio settings and implementation remain pending in #14.

## Accepted UI implementation baseline

Ashu’s PR #16 structure/flow and all three palettes are approved and adopted. Future pages use the shared StudioShell and theme tokens; Ashu retains design ownership. See [adaptation evidence and remaining gaps](implementation/ashu_ui_adaptation.md). Navigation design #3 is accepted; task/context implementation is tracked separately in #18. Exact FFLF/R2V collation/annotation design #4 remains open.

## PR #22 design foundation

Ashu’s [design foundation](../design/VIBE_DIRECTOR_FOUNDATION.md), pinned to d7bf40489eefe377a1cec01d04def0ed04177c23, supersedes the PR #16 visual shell reference. Adapt its typography, palette roles, profile settings, navigation, Clapper and contextual taskbar to real functionality. Retain Quiet comic alongside Concrete & ink and Midnight mixtape under the owner’s explicit three-theme requirement. Prototype simulations do not replace production behavior; unavailable project/workflow features must remain honest. Ashu retains design ownership.
