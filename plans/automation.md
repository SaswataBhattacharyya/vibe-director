## Mandatory T2V pipeline — owner correction 2026-10-24
All new T2V generation uses H3 Turbo (four steps at a smaller source canvas), followed by the pinned lower-noise LTX 2.3 refinement (three steps with installed Sol attention). This applies to standalone, batch and story T2V; FFLF/R2V remain unchanged. User quality, aspect ratio and duration specify the final output. Final landscape choices: Low1216×672, Standard1344×768, High1664×928, Max1920×1088. Existing numeric batch presets keep their original sizes. Pure-T2V automated stories make all originals first and then refine serially. Standalone batches also generate all validated H3 originals serially while retaining H3, confirm unloading, then refine all originals serially while retaining LTX, and confirm final unloading (latest owner correction 2026-10-25). After the initial 30-second unload window, supervised handoffs poll every 10 seconds until release is observed; elapsed time never authorizes loading. Original H3 audio is remuxed into the final video; source/stage IDs and hashes are durable. Pause prevents subsequent stages; Stop cancels pending refinement. Screenplay, authored prompts and frozen older jobs are preserved. See `plans/T2V_TURBO_LTX_INTEGRATION.md` for recipe, provenance and verification limits. This supersedes older “upscaling deferred” instructions for T2V only.

## Video reference policy — owner correction, 2026-10-22

Fully automated uses text to video for every clip, without image, video or audio references. Assisted manual defaults to text to video; the user may explicitly select a reference workflow and media for a clip. Never attach masters, voices, continuity frames or crops automatically. Explicit previous-frame continuity is optional in Assisted R2V only. Standalone manual reference workflows remain available.

Each T2V prompt independently describes the screenplay-supported background/location, lighting, named cast and appearance, action, camera, exact dialogue and who speaks it, delivery, ambience and sound balance. Progress the story with a clear new beat; avoid repeated establishment and padding. Use the shortest sufficient supported duration. T2V clips may be 5–30 seconds each; 30 seconds is a ceiling, not a target. The installed H3 node permits this frame count but describes lengths beyond its roughly 15-second trained range as untested. Preserve shorter clips when sufficient for brisk story progression. This is clip length, not a render-time guarantee. Upscaling and later character/audio replacement are deferred. Do not rewrite frozen submitted jobs.

## Owner-started Full run verification — 2026-10-22

## 2026-10-22 — Owner correction: last-frame continuity and run controls

This correction supersedes older automatic predecessor-video and inherited style-video rules below.

- Fully automated and Assisted manual continuation use the preceding completed/accepted clip's actual final decoded frame as an image reference. Preserve the world's layout, geometry, materials and identity; generate the next screenplay action and camera direction. Do not replay the preceding motion.
- Use an identity-verified crop from that same final frame for relevant characters when available and within image capacity; otherwise retain selected character masters. Never guess identity from an unverified crop. Optional derived crops yield to explicit image choices and the continuity frame. Continuity resets at scene boundaries; verified character identity may persist.
- No automatic video attachment for continuity or global style. Global style analysis may guide prompts. Explicit per-clip video references remain supported only for an intentional video copy/edit request, such as changing its characters or world.
- Current Take exposes Pause, Resume, Stop and Refresh before the clip list. Pause lets the current clip finish and prevents successors. Resume continues the same paused run. Stop durably prevents successors, cancels unsubmitted work and interrupts only its owned active Comfy prompt. Refresh in Automation and Current Take reads status only; it never pauses, stops, restarts or submits. Opening an active run routes to Current Take.
- Upscaling remains deferred until the owner supplies its model and workflow. Generate at the saved resolution for now. No new inference is authorized by this implementation; the owner starts the next run.
- Current Trial 1 run was stopped and its three completed clips removed from both Vibe and Comfy. Accepted screenplay, story and setup remain saved. Cleanup evidence: `local_data/current-run-cleanup-2026-10-22.json`; 42 protected files checked unchanged.


Start run uses saved duration and resolution, opens Current Take and continues without per-clip acceptance. A missing disposable smoke render does not block an owner-started Full run: its first live output passes the existing collected-file, hash and video/audio checks before progression. Failed/missing output pauses the run. Model/graph/node, worker/queue and GPU runtime admission remain enforced. Verified-render reporting remains evidence-based; no successful render is claimed before completion. Assisted workflow admission is unchanged.

# Automation & Parameters — one setup page and shared generation journey

## Assisted manual shot references — owner correction 2026-10-16

Video Create uses the accepted screenplay's shot design and saved asset selections. Director attaches current character masters for visible cast, current world masters for cited locations, and assigned voices only for speakers in that shot, preserving stable character–voice IDs in the request. Show action, dialogue, camera, lighting, mood and duration beside the reference controls; prepare an editable workflow-specific shot prompt automatically. Ambiguous cast/location/speaker matches or missing selected assets are explained rather than guessed. Standalone creation remains available.

User may remove, replace or add image/audio/video references with separate identity, location, style, motion or sound instructions. These are per-shot overrides; global masters and voice assignments remain unchanged. Persist prompt, references and review decisions by workspace/revision/setup/workflow/shot; restore on switching/reloading. Rebuild Director choices is explicit and warns before replacing edits.

Automatic and extra references share workflow capacity (currently R2V: 9 images, 3 videos, 3 audio including paired soundtracks). Keep every proposal visible; when over capacity, ask which to retain and block submission until resolved. Never silently truncate. Show possible instruction conflicts near reference review, explain the affected identity/clothing/location scope and offer narrower instructions or a visible retained override. Do not claim visual/semantic inspection where only instruction scope was checked. Preparing a shot never queues generation; Assisted manual Generate remains owner-clicked.

This applies when video automation is unchecked in Assisted manual. If it is checked, Video Create offers an explicit “Use shot-by-shot manual R2V” action that saves manual video control and prepares the existing duration-bounded clip plan; it never submits a video. Otherwise checked video automation continues through the saved automated clip plan. This supersedes earlier recommendation-only wording for story-linked Assisted manual R2V. Optional style-library recommendations and isolated creation still require user selection. Fully automated behavior is unchanged.


### Sequential clip preparation — 2026-10-16

Reuse the existing clip planner and source-span coverage rules. Show Scene / Shot / Clip / seconds in the dropdown, splitting long material into clips within the saved duration policy and workflow’s 5–15 second limits. Show the clip’s action/dialogue and shot direction. Attach saved selected masters and assigned speaker voices automatically; continue a split utterance with its speaker identity. Planned duration is fixed in Create so it stays consistent with coverage.

Only clips whose predecessors have accepted videos are selectable. Retake revises the current clip. Accept & Next loads the following planned clip and prepares its prompt and references. Each subsequent clip in the same scene must include the preceding accepted video as a continuity reference (up to its final 15 seconds); new scenes do not inherit it. The backend checks plan freshness, clip identity/duration, preceding acceptance and continuity asset hash before admission. User edits and extra scoped references remain available. Do not overwrite edited prompts on reload; restoration is explicit.


## Notes-integrated correction — 2026-10-11

Automation selection comes after readable screenplay. Prompts are stage-local, prepared as work advances; retire the standalone Prompt Preparation destination while preserving its reusable backend records. All five Assisted boxes remain asset-based; Full skips separate image generation. Full may derive verified character frames from prior clips; registry persists across scenes, image-conditioned starts require R2V. Assisted automatic video uses the run-level FFLF/R2V choice and explicit frozen per-clip references described below. Preserve durable plans/recovery and resolve/freeze later reference-dependent requests before first submission.

Read [remaining_app.md](remaining_app.md) for task order/reuse and [OWNER_DUMMY_RUNS.md](OWNER_DUMMY_RUNS.md) for owner-clicked acceptance. This correction overrides conflicting older sections below; historical implementation checkpoints are not completion evidence.


**Status:** Current product plan. This describes intended behavior; it does not claim every part is implemented.

**Historical implementation checkpoint (2026-10-10; gaps superseded below):** Prompt Preparation links an Assisted manual workspace to Character images, World images, and Clip frames. Each Assets step requires the current accepted screenplay and exact saved setup; character/location targets come from the pinned graph, and frame targets use the revision-scoped `story_clip_id`. Frame Skip is durable per accepted screenplay shot. Checked character, world, and frame image stages use idempotent admission, durable queue progress/recovery and fail-closed Codex visual review. Character/location selections keep one current Director-selected master and retain alternates; frame first/last roles are selected independently per clip. The worker rechecks accepted revisions, graph/style lineage, saved settings and frame skip before review/selection. Frame prompts consume nested screenplay direction and reject over-limit prompts instead of truncating them. Manual image submission stays blocked for checked stages and in Fully automated mode; standalone generation remains available. Checked Character-to-audio selection runs deterministic matching against explicit character names or voice guidance in saved voice-asset metadata, assigns only a single clear match, records decisions, and pauses unmatched/ambiguous characters for a director choice. The image-reference and Assisted runner gaps stated in this historical checkpoint were superseded by the 2026-10-11 updates below.

**Historical setup checkpoint (2026-10-10; runner status superseded below):** Assisted manual saves one run-level automated-video workflow choice (FFLF or R2V); selecting Video Generation without choosing one is rejected. Every shot prompt is seeded from that selected workflow, and the prompt editor cannot switch individual shots to another workflow. The API rejects mixed-workflow drafts. The Director clarified that reference-to-video inputs must be mapped per clip before the run; the system must not guess which character, voice, world or style reference belongs to a shot, nor attach every asset to every clip. The implementation update below now freezes and executes the plan and reference map; live runtime and owner acceptance remain unverified.

**Image-reference gap superseded (2026-10-11):** Automated First/Last Frame jobs now attach only selected, hash-validated character/location images explicitly cited by that screenplay shot; a last-frame job may also use that clip's selected first frame. The same selected frame assets can be mapped to FFLF video clips through the existing role-validated video-reference path. This closes the older claim that safe staging and image-reference wiring were missing. It does not claim live Qwen/MiniMax node compatibility or visual-quality acceptance. See `remaining_app.md` and the latest `HANDOFF.md` checkpoint.

**Current implementation update (2026-10-11):** The Assisted runner now freezes the saved clip plan and per-clip references, then queues one clip at a time through the durable video-job ledger. R2V can optionally include the immediately preceding completed clip from the same scene; this is an explicit per-clip Director choice, off by default, unavailable on the first clip of a scene, saved with the plan, frozen into the run manifest and counted against the workflow's video-reference limit. The focused backend tests cover frozen-input rejection and inclusion/exclusion of that predecessor. This closes the earlier “runner not complete” checkpoint for the implemented path; live ComfyUI/model compatibility and owner-clicked generation acceptance remain unverified. Do not treat that checkpoint as proof the complete automation phase is done.

The planned clip prompt remains editable after clip planning. Use the shared selected-text micro-edit interaction, let the Director review the proposed replacement, then save the changed prompt to that exact planned clip. Saving is separate from the source screenplay-shot prompt draft, checks that the accepted screenplay/setup/source prompts still match the plan, enforces the 6,999-character ceiling, and is blocked after run freeze. Unsaved clip prompt edits block Start; replanning warns before discarding them. This prompt-edit path is implemented; see the latest `HANDOFF.md` checkpoint for verification limits.

## Rules to follow

- There are exactly two choices: **Assisted manual** and **Fully automated**. Do not show a separate Manual or Semi mode.
- Assisted manual has five `Automate this step` checkboxes. None checked means the user runs each step; some checked means a mix; all checked automates the asset-based route.
- Fully automated skips the separate character/world/frame generation pages. At a scene start it uses R2V if a selected style video or usable verified character frame is attached; otherwise it uses T2V. Later clips use the immediately preceding clip as an R2V continuity reference. Character references persist across scenes, while predecessor-video continuity resets at each scene boundary. A candidate identity observation alone is not a verified image reference and must not change routing.
- Both choices use shared generation screens. Confirm settings before an automated run; do not ask again for every clip.
- `Manual` can describe a user action or an old saved value. It is never a mode in the new UI. Translate old saved values using the compatibility rule at the end of this plan.

## Quick pathway

```text
Screenplay → Automation & Parameters
  ├─ Assisted manual
  │   ├─ None checked → user runs each step: edit → Generate → review → Next
  │   ├─ Some checked → selected steps run automatically; others wait for user
  │   └─ All checked → assets/voices and video run automatically
  │       Video automated → compatible FFLF or R2V, chosen by Director
  └─ Fully automated
      Skip image preparation and manual voice matching
      Each scene: first clip R2V with selected style video or usable verified character image; otherwise T2V
      Later clips: R2V with previous clip; keep character references across scenes
Both → saved clips/history → ordered assembly/export in assembly.md
```

Character, world and frame image stages each have a saved **Skip / Undo skip** choice in Automation & Parameters and their manual stage page. Checked = automatic, unchecked = manual, Skip = bypass; choosing Skip turns that stage's automatic checkbox off. Next bypasses skipped stages while keeping minimum selections for stages used. Skipping character images does not waive required voice choices. All three image stages may be skipped in Assisted manual with no forced switch to Fully automated; manual Video Create supports T2V without these references. Saved assets remain available. For filmmaking, frame preparation is currently experimental/unreliable: skip Frames to go from Worlds to Video Create, defaulting to R2V. First/last-frame tools remain available for explicit use and other production types.

Optional image steps may be skipped. Automatic settings are confirmed before starting; missing inputs or technical failures pause. Quality stays fixed; duration may be fixed or Director-selected. Isolated tools use the same screens without a screenplay or this mandatory setup.

## 1. Where the page belongs

For the regular story journey:

```text
Story workspace + knowledge graph
  → readable screenplay with integrated direction
  → Automation & Parameters
  → workflow-specific prompt preparation
  → optional asset preparation / voice binding
  → video generation and ordered clip results
```

Place this page **after the screenplay is generated and before any production model prompts are prepared**. Scene/shot/source records can already exist, but do not finalize image/video prompts or queue generation before the execution policy and parameters are confirmed.

The page defines Assisted manual or Fully automated behavior for the same underlying generation screens. It is part of the regular production journey, not the old global Automation Studio/pipeline-builder page. The older separate Production V2, Generate, Automation and Manual Director pages are removed from the intended product navigation. Reusable backend/compiler/job logic from those pages may support the new journey without retaining them as competing user destinations.

## 2. Two entry paths into the same generation screens

### Regular story production

The screenplay supplies scene/shot/clip context, character/world identities, dialogue and integrated direction. After Automation & Parameters, the shared generation screens prepare prompts for the selected workflow and actual settings, then execute according to the chosen wrapper.

### Isolated generation

Anyone can start directly at character image generation, world/background image generation, clip/frame image generation, compatible voice binding, or any of the three video modes. A story, screenplay, knowledge graph and previous production stages are optional for this path.

Each screen accepts its own required description, prompt and assets. A first/last-frame video requires its two images, but these may be uploaded or selected from the library without going through frame generation. R2V accepts library/uploaded references and their intent. T2V accepts text without story setup.

Use the same controls, prompt annotation/microediting, limits, generation jobs, review/retake and shared asset storage as the regular path. Do not build a separate isolated-generation implementation or a new Generate landing page reproducing the old one. Direct links and stage navigation enter the actual shared tool. Prompt preparation follows local settings on isolated entry; the post-screenplay setup page is not mandatory there.

If existing backend services require a project/workspace identifier, allocate or select a lightweight saved workspace behind these screens. Do not require a fabricated story/scene or send the user through story authoring just to generate one asset. Standalone outputs have asset/take IDs; source screenplay/scene/shot links are optional, not invented.

## 3. Setup page layout

```text
Automation & Parameters                 Screenplay revision / scenes / status

Mode:  [ Assisted manual ] [ Fully automated ]

Assisted manual:  Automated?          Stage                          Parameters / policy
       [ ]                Character image generation    Defaults / Configure
       [ ]                Character-to-audio selection  Voice-selection defaults / Configure
       [ ]                World-building image gen      Defaults / Configure
       [ ]                Frame image generation        Defaults / Configure
       [ ]                Video generation              Quality + Duration / Configure

Video quality/output: [saved/default preset] [Configure]
Duration policy:       ( ) Fixed seconds    ( ) Director chooses per clip

Summary: automated stages / manual stages / skipped optional stages / settings
[Save setup]  [Continue / Start production]
```

Show only controls relevant to the chosen mode. Presets have concrete values inspectable by the user, not an opaque “default” label. Every stage selected for automation opens its parameter/policy confirmation and is marked Confirmed only after the user accepts defaults or saves changes. The page can summarize and start after all selected stages have confirmed valid settings; no repeated per-clip confirmation is required.

A checkbox means **automate**, not **include**. An unchecked stage remains manual if used. Optional image stages still have a distinct Skip action; automatic completion, manual completion and skipped state are visibly different.

## 4. Assisted manual — none, some or all stages automated

There are two mode choices: **Assisted manual** and **Fully automated**. Never add separate Manual or Semi buttons. In Assisted manual, checkbox selection alone determines how much the system does.

- **None checked:** every used stage waits for the user. Show the prompt, allow editing/selected-text AI changes, then Generate → review/retake → Next. Optional image stages have Skip. This remains Assisted manual, not a third mode.
- **Some checked:** checked stages run when their inputs are ready; unchecked used stages wait for manual action. Skip is separate from an unchecked box.
- **All five checked:** character/world/frame generation, voice matching and video run automatically using confirmed policies. This is automation with prepared assets; it does not switch to the image-free Fully automated preset.

The owner confirmed that both all-checked and the separate Fully automated route remain. They differ in which assets are prepared and how video workflows are chosen, not in whether the user must click each Generate button.

Manual steps show editable settings and the exact prompt before generation. Selected-text AI edits produce a reviewable change with undo/history. Completion does not start the next manual item; the user clicks Next. Do not add a second mandatory acceptance screen after review.

## 5. The five Assisted manual checkboxes

Use these five checkboxes, matching the user's specified stages:

| Checkbox | If checked | Parameters or policy to confirm |
|---|---|---|
| Character image generation | Build images for applicable screenplay characters automatically | Image model/workflow, supported quality/output settings, defaults and candidate handling |
| Character-to-audio selection | Match and save voice bindings automatically for speaking characters | Same-workspace voice-master library; exact character name or explicit voice guidance in saved filename/description/tags; reuse existing bindings; pause ambiguous or missing matches for the Director |
| World-building image generation | Build applicable reusable location/world images automatically | Image model/workflow, supported quality/output settings and defaults |
| Frame image generation | Generate required clip first/last frame pairs automatically | Frame model/workflow, supported output settings and which planned clips need frames |
| Video generation | Director chooses one workflow for the whole run: FFLF or R2V | Fixed initial quality/output/settings, duration policy, selected FFLF/R2V workflow; FFLF frame-pair validation or a Director-authored per-clip R2V reference map |

Character-to-audio selection means choosing a voice asset/binding, not generating a voice file or training a model. Selecting its checkbox expressly authorizes automatic matching. Match only a single direct metadata hit for a character name or explicit voice-guidance phrase; do not infer a voice from appearance or general personality prose. Preserve existing bindings. Do not assign voices to characters without labeled dialogue in the screenplay. When speaker labels cannot be mapped, or no unique asset matches, pause that character and let the Director choose a voice or update its metadata. Shared voice files may bind to multiple characters, consistent with `char_world.md`.

An unchecked step pauses for manual action when reached. Checked steps execute when their inputs/dependencies are ready and advance without compulsory human result acceptance. The user may inspect, pause, revise or retake. Automatic prompt assembly and parameter validation are subordinate work within the selected stages; do not add story/graph/screenplay checkboxes to this post-screenplay page.

The displayed checkbox list does not prescribe an invalid dependency order. Required frame inputs wait for the selected character/world references; selected generation waits for its inputs. Independent selections can use supplied/library assets if an earlier optional stage was skipped.

Checking Video Generation asks the Director to choose one workflow for the whole Assisted manual run: **first/last-frame (FFLF)** or **reference-to-video (R2V)**. The chosen workflow is confirmed once with its run settings and applies to every planned clip; do not ask for a workflow again per clip or silently switch workflows. FFLF requires usable selected first/last frames for each generated clip; skipped or missing frames pause that clip for a Director decision. R2V requires an explicit per-clip reference map authored by the Director before the run. The map may include compatible selected character, voice, world or video references; it is frozen with the run. A Director may separately select up to two recommended style videos for the automated stage in setup; these are explicitly selected run-level R2V references attached to every clip, with their saved intents. Selecting them requires R2V; FFLF is unavailable until they are removed. Per-clip mappings remain explicit and cannot duplicate an inherited run-level style video. Never infer cast/location from prose or attach all workspace assets to every clip. A previous clip is included only where the Director maps it as a reference. If Video Generation is unchecked, the user chooses any supported video mode manually. Assisted manual automatic video is resource-aware rather than forced to follow Fully automated's image-free route.

### Director-selected workflow and references in Assisted manual

- **FFLF:** choose when the current clip has usable first/last frames and their boundary control suits the action. Character/world images guide frame preparation; the final video request receives its two frame inputs. Select only additional direct reference inputs supported by that graph.
- **R2V:** the Director maps compatible character images, bound voices, world/background images and optional video continuity references to each clip before starting. Up to two style videos explicitly selected in setup are inherited as run-level style refs with their saved instructions. Mapping is explicit; no automatic relevance guess and no blanket attach-all behavior. A selected style video requires R2V and consumes the shared per-clip video-reference capacity.
- The first clip of a scene can be FFLF or R2V with prepared image/voice/world references; it does not require a previous generated clip. Reset default predecessor selection at scene boundaries.
- Confirm one workflow upfront for the whole run. Before admission, show the Director's per-clip reference mapping for review and freeze compatible asset IDs, hashes, roles and intent. Enforce workflow role/capacity/prompt limits after building the manifest. Never switch workflows between clips.
- If neither workflow has its required inputs, pause at the missing frame/reference preparation step. Do not silently fall back to T2V or change quality. The user can explicitly change the mode/setup if they want a different route.
- Existing voice binding remains a top recommendation in manual pickers. Assisted manual's checked automated Video stage plus confirmed reference policy authorizes the Director to attach the appropriate prepared voice/image assets. A binding alone outside that policy does not authorize attachment.

**FFLF compatibility detail:** the inspected current local FFLF graph exposes two image inputs and a prompt, not a direct voice-reference slot. Character/world identity can be carried through prepared frames, but a bound voice file cannot be claimed as an input when the graph cannot accept it. If voice-reference conditioning is required, the Director chooses compatible R2V (or a future verified FFLF adapter explicitly supporting it). Required intent takes priority over guessing support.

## 6. Fully automated — configure once, then generate the story's clips

Fully automated skips the separate character/world/frame image-generation stages and does not require manual voice assignment. Configure quality and duration policy once, then retain every generated clip. At a scene start, use R2V when a selected style video or a usable verified character reference is available for that scene; otherwise use T2V. Within a scene, use the immediately preceding clip as the R2V continuity reference. Starting a new scene clears predecessor-video continuity but preserves the per-character reference registry. A candidate identity observation alone is not a verified image reference and must not change routing. Fully automated does not use FFLF.

Confirmed Fully automated sequence:

1. At each scene start, use R2V if a compatible selected style video or usable verified character image is attached; otherwise use T2V. Include explicit instructions for each attached reference.
2. Use the immediately preceding completed clip as the continuity reference for following R2V clips; retain selected style videos as distinct style references. Validate combined reference capacity before starting.
3. Derive each continuation prompt from the next screenplay action/dialogue, shot/camera direction and predecessor continuity state. Include the actual reference label matching the selected previous clip.
4. Retain every generated clip and its exact request/history. A replacement never automatically deletes the old output.
5. Reset predecessor-video continuity at each new scene, but keep the per-character reference registry. Use character-reference R2V only when its reference was safely derived and frozen into that clip; otherwise use the style-video R2V or T2V route above.
6. Finish with ordered scene/clip results and source coverage. Film assembly/audio mixing remains a later step.

When entering Fully automated through the regular path, confirm setup once on this page after screenplay generation. If a future story-only start uses an already confirmed saved Fully automated preset, it may pass through this same setup state without another stop. “Fully automatic” describes execution after configuration; it does not authorize guessing unconfirmed quality settings.

## 7. Video quality and parameters: fixed upfront

Before starting automatic video generation (Fully automated or Assisted manual with Video checked), confirm the allowed workflows and all non-duration generation settings. **Quality is fixed initially.** The Director can choose duration if authorized, but cannot silently vary quality between clips.

Quality/output configuration includes the actual supported resolution/scale preset, aspect ratio/dimensions, frame rate and applicable model/sampling settings. Expose supported defaults with readable labels and an expandable exact-value panel. A seed or seed policy, if supported, is also confirmed upfront; it is not a new free parameter for the Director to change per clip.

Validate one compatible configuration for every workflow allowed by the selected wrapper (Assisted manual: FFLF/R2V; Fully automated: T2V/R2V). Backend-specific fields may differ, but their mapping to the fixed output quality must be explicit and validated. Do not silently downgrade quality when changing workflow. If the pair cannot support the selected preset, show the incompatibility before starting.

Changing fixed settings later pauses at a safe boundary and creates a new explicitly confirmed run-policy revision for future work. Existing clips keep their original parameters. Normal automatic execution may vary only duration among generation parameters under the selected policy. Assisted manual also authorizes workflow/reference selection by the Director; that selection must preserve the fixed quality configuration. It is not permission to vary resolution or sampling quality per clip.

## 8. Duration: fixed or Director-selected per clip

Offer two policies for automatic video:

- **Fixed:** use the confirmed target duration for clips and divide longer scene/shot coverage into enough clips. If the remaining action is shorter, use permitted hold/pacing according to screenplay direction or expose an infeasible timing issue; do not silently switch to dynamic timing.
- **Director-selected:** the Director chooses a supported duration for each clip based on its action, dialogue, pauses and transition. The user confirms allowed minimum/maximum (and default target where useful), constrained by the installed workflows. Duration may differ between clips. All quality and other fixed parameters remain unchanged.

Choose duration before finalizing the clip prompt and job request. Long action/dialogue is divided at sensible boundaries into additional clips. Maintain a ledger of source action/dialogue spans covered and remaining, so dynamic timing cannot omit or repeat story content merely to fit a request.

The current inspected local H3 contracts support 5–15-second outputs; the UI reads actual supported values/increments from verified capability configuration. Show actual selected seconds with every queued/result clip. The duration decision and its reason are inspectable, not a new modal requiring human confirmation on every automatic clip.

**Initial setup-page scope:** the first persisted setup UI may offer the conservative shared 5–10-second subset for fixed and Director-selected duration, labelled as a shared range rather than a workflow maximum. Workflow-specific upper bounds and increments (including 5–15-second H3 modes) remain a later capability-driven refinement; never validate or dispatch using the shared subset alone once workflow-aware generation is wired.

## 9. Prompt preparation after setup

Only after mode/stage settings are confirmed, assemble prompts using:

```text
screenplay direction or standalone user intent
  + current scene/shot/clip coverage and duration
  + selected workflow/model and fixed parameters
  + actual selected references and per-reference instructions
  → model-specific final prompt
```

Manual steps in Assisted manual expose the editable prompt before Generate. Automatic steps prepare/refine/validate internally and record the exact prompt alongside the result, without a compulsory prompt-review gate.

**Current implementation boundary:** Prompt Preparation creates one readable, editable base prompt per accepted screenplay shot and offers the three workflow-specific prompt forms. Drafts are durably saved under the exact accepted screenplay revision and a hash of the saved setup. **Open in Video** loads a saved shot into the shared Video form, where normal one-shot submission remains available. On Full start, the backend asks the configured reasoning provider for a per-scene clip plan, validates exact ordered action/dialogue source-span coverage, then freezes the accepted screenplay, setup, saved prompts, durations, plan and hash before admitting the first clip. Fixed and Director-selected duration policies are supported within the configured range. Status reads only recover persisted state and do not call the model. Full routing uses R2V at a scene start when a selected style video or a usable verified character crop for that scene is available; otherwise it uses T2V. Later clips use R2V with the immediately previous clip, resetting that video chain at each scene boundary. Screenplay cast targets (`character_record_ids`) are separate from source-evidence citations (`evidence_record_ids`) and drive character-crop lookup. The durable identity queue exposes candidate observations; only validated, registered crops from prior clips can become references. Workflow-specific prompts are re-prepared when newly available scene-start crops change T2V to R2V, retaining prior prompt prose as context. Frozen request validation and retry reconstruct the same refs. Assisted runs likewise freeze their clip plan and mapped references and queue clips through the durable video-job ledger, with pause/retry behavior. Focused mocked backend tests cover these paths, but identity matching quality, live provider planning, R2V/T2V/FFLF generation, GPU acceptance, assisted/full end-to-end behavior and export remain unverified. Do not imply runtime acceptance is complete.

Keep MiniMax prompts strictly below 7,000 characters, counting compiled tags and adapter text. Image prompts also have a shared product input cap of 6,999 Unicode code points; any workflow-specific lower technical limit must also be enforced once verified. Preserve meaning during shortening and never truncate silently. Workflow/parameter/reference changes invalidate stale prompt validation and generate a traceable revised draft.

Creative microedits retain **Update screenplay** versus **This take only** in story-linked work. Isolated work has no screenplay to update; save the change to its local task brief/prompt revision. Automatically rephrasing for a model must preserve the screenplay's creative intent.

## 10. Progress, pause, resume and results

Present the policy summary and one readable progress view: stage/item, scene/clip position, task state, selected duration/quality and latest available outputs. Show which manual step is awaiting action in Assisted manual.

Pause prevents new tasks from starting, while showing the current job's actual backend state. Resume continues from saved completed work. Refresh or navigation does not restart generation or resubmit an ambiguously queued job. Changing automation choices/settings applies at the next safe boundary to future work.

Generation completion is separate from human quality approval. Automatic steps advance on successful completion; outputs stay available for later review and retakes. A technical failure pauses with an actionable reason. Do not introduce unlimited hidden retries or automatic deletion of failed-quality clips.

Assisted manual manual retakes use Keep/Discard from `video_gen.md`; automatic video retains every generated clip. Replacing a predecessor marks dependent continuations stale and offers an explicit regeneration path while preserving all old media.

## 11. Status remains a global page

Retain **Status** as the place to inspect backend connectivity and website-usable workflows. It displays:

- Backend/ComfyUI and selected reasoning/analysis engine connectivity/readiness.
- Workflow catalogue with name, type, version, input roles and the shared screen that can use it.
- Supported duration/output parameters and defaults, including incompatible presets.
- Prompt limits, with units (characters/tokens/encoder constraints), for each workflow/model; unknown or unverified values are labeled and investigated rather than invented.
- Installed/readiness versus usable-through-this-UI state, with missing nodes/models/adapters or unavailable connection reasons where relevant.

Use the same verified capability data for Status, setup parameter panels and generation validation. A workflow being stored on disk does not mean the website can execute it. Status is informative and does not create a competing generation entry point or require a visit before normal work.

## 12. Retired pages and shared navigation

Remove Production V2, Generate, the old Automation Studio and Manual Director as distinct user-facing pages. Retain reusable operations behind the shared forms and policy runner where useful. This Automation & Parameters page is reached in the regular journey, not added as a second global automation workbench.

The product navigation exposes the story/screenplay journey, actual shared image/voice/video stage screens accessible directly, Media Prep and Status. Do not make users choose between multiple controllers that all claim to generate the same clip.

Proposed shared frontend routes (the same forms may carry optional story/project/clip context):

| Route | Surface |
|---|---|
| `/assets/characters` | Character image generation, story-linked or isolated |
| `/assets/worlds` | World/background image generation, story-linked or isolated |
| `/assets/frames` | First/last image generation, story-linked or isolated |
| `/assets/voices` | Character voice binding when characters exist; otherwise voice-library selection |
| `/video` | Three-mode selector |
| `/video/text`, `/video/frames`, `/video/reference` | Matching shared video forms |
| `/stories/:storyId/automation` | Post-screenplay Automation & Parameters |
| `/status` | Connections, usable workflows and limits |

These are proposed UI routes, not a backend rename. Story-linked navigation supplies validated source context; isolated entry leaves it absent. Old links may redirect to an equivalent shared tool with valid asset/task context. A redirect must not start generation or invent missing story IDs. Replace Media Prep's legacy hand-off actions with selection into these shared tools.

## 13. Concrete UI walkthroughs before implementation acceptance

Validate the intended behavior through a small set of end-to-end UI walkthroughs, not a large passing test count alone:

1. **Assisted manual, none checked:** screenplay → setup Assisted manual with no checks → edit/annotate a prompt → Generate → review → Next; no next generation starts before the user's action.
2. **Assisted manual mixed path:** check character images and video only → confirm their settings/reference policy → automatic characters → manual remaining steps or explicit skips → Director selects viable FFLF/R2V and compatible refs; the page clearly explains each upcoming stop.
3. **Assisted manual, all checked:** check each of the five stages → each opens its appropriate settings/policy → accept defaults → summary accurately lists what will run; no extra repeated parameter gates.
4. **Fully automated fixed duration:** confirm quality/duration → skip separate image generation → at each scene start use R2V when a selected style video or safely derived character reference is attached, otherwise T2V → later same-scene clips use predecessor R2V → retain clips in plan order; no human generation/acceptance clicks mid-run.
5. **Fully automated dynamic duration:** confirm quality and allowed duration range → the provider proposes per-clip durations and reasons within that range → quality stays fixed and complete source-span coverage is validated before any job starts. The frozen duration plan is shown as clips run.
6. **Isolated FLF:** directly open the video form → supply two uploaded/library images and prompt → generate/review without a story or screenplay.
7. **Isolated image/R2V:** directly open a shared stage → edit/annotate prompt, choose compatible references/settings → save results with no fabricated scene links.
8. **Return/recovery:** refresh/pause/resume across manual and automatic steps → inputs/results survive and no duplicate job starts.
9. **Status:** limits/defaults/usable workflows agree with the setup and generation forms; unavailable capabilities have an actionable explanation.
10. **Assisted manual FFLF:** Director selects FFLF with two usable frames → character/world continuity comes through those frames → no voice file is presented as directly submitted to the current graph. A required voice-reference intent selects compatible R2V instead.
11. **Assisted manual R2V:** Director selects relevant prepared character/voice/world assets and optionally the preceding clip → manifest, reference labels and prompt reflect exactly those inputs → clip uses the confirmed quality and a permitted duration. Missing inputs pause clearly; no implicit T2V fallback.

Use wireframes or a clickable prototype of these journeys before claiming the UI is usable. Automated checks support the chosen behavior but do not substitute for seeing the real screens and completing these flows.


## 14. Unified production visibility and durable execution

Apply `ux_shared.md` for saved context, clear next actions, mobile arrangement and offline recovery. Show a single production overview with current item/scene/clip, exact prompt/ref manifest, duration, fixed quality, coverage, take history and job state. A checked stage completes automatically under its confirmed policy; completion must not be represented as human acceptance.

One durable application service owns state transitions, submission identity, job IDs and resume; the LLM supplies authorized creative/workflow/duration decisions. Do not depend on an active coding-agent chat alone to keep background production alive. Upstream creative gates/selectors are adapted to this policy rather than copied as a competing controller. See `integration.md`.

Known-cost estimates may be displayed before starting a configured run, identifying uncertain/local/LLM costs separately. Do not import repeated per-clip approval thresholds as new mandatory gates. Any future budget policy requires an explicit run-level contract.

## Selected production-style references

`production_styles.md` defines the selected style-video exception for automated video: Fully automated starts a scene with R2V when a direct style video is selected, even when its frame-export count is zero. Assisted manual automated Video also uses compatible R2V with the selected style video. The policy includes explicit style intent, selected assets and graph-capacity validation; subsequent style/continuity references remain distinct. In manual steps of Assisted manual images/audio/video are top recommendations and remain unselected. Default video frame export is two; never export all frames into image pickers.

## Existing saved policies

When the mode implementation is added, preserve existing drafts, jobs and history. If saved legacy labels exist, interpret Manual as Assisted manual with no checks, Semi as Assisted manual preserving its five checks, and Full as Fully automated preserving its recipe/settings. Do not rewrite active submitted requests or turn a restored draft into an automatic run. Display the new labels; resume only under the saved confirmed policy. This is a required compatibility rule, not a claim that these policies already exist in the current backend.

### Video quality correction — 2026-10-21
All video workflows and Automation & Parameters expose Low (864 × 480, 0.4), Standard (1056 × 608, 0.6), Medium (1216 × 672, 0.8), and High (1344 × 768, 0.98). Existing saved `standard` setup keys retain the former 0.4 resolution and display as Low; the new Standard uses `standard_608`, preserving saved setup hashes/manifests. Quality changes invalidate the settings preview, not the collated reference instructions. Next-clip R2V prompts include reference labels and explicit assigned-speaker bindings automatically; readiness is checked on opening/resetting Create and again on Generate.
