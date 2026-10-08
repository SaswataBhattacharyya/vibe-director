# Automation & Parameters — one setup page and shared generation journey

**Status:** Current product plan based on the user's clarification. It supersedes the broader checkbox proposals in `execution_modes.md`. This is planned UI behavior, not a claim that it is implemented.

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

The page defines Manual, Semi or Full behavior for the same underlying generation screens. It is part of the regular production journey, not the old global Automation Studio/pipeline-builder page. The older separate Production V2, Generate, Automation and Manual Director pages are removed from the intended product navigation. Reusable backend/compiler/job logic from those pages may support the new journey without retaining them as competing user destinations.

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

Mode:  [ Manual ] [ Semi ] [ Full ]

Semi:  Automated?          Stage                          Parameters / policy
       [ ]                Character image generation    Defaults / Configure
       [ ]                Character-to-audio selection  Voice-selection defaults / Configure
       [ ]                World-building image gen      Defaults / Configure
       [ ]                Frame image generation        Defaults / Configure
       [ ]                Video generation              Quality + Duration / Configure

Video quality/output: [saved/default preset] [Configure]
Duration policy:       ( ) Fixed seconds    ( ) Director chooses per clip

Summary: automated stages / manual stages / skipped optional stages / settings
[Save setup]  [Continue in Manual OR Start configured production]
```

Show only controls relevant to the chosen mode. Presets have concrete values inspectable by the user, not an opaque “default” label. Every stage selected for automation opens its parameter/policy confirmation and is marked Confirmed only after the user accepts defaults or saves changes. The page can summarize and start after all selected stages have confirmed valid settings; no repeated per-clip confirmation is required.

A checkbox means **automate**, not **include**. An unchecked stage remains manual if used. Optional image stages still have a distinct Skip action; automatic completion, manual completion and skipped state are visibly different.

## 4. Manual

Manual means the user works through the shared screens, clicks Generate for each required item, inspects the result and clicks Next when ready. Unused image/frame stages can be skipped. The user chooses video workflow and references and may generate isolated assets directly.

Show the exact prompt before generation on every applicable screen. Allow direct editing, selected-text annotation and Codex/LLM microediting. A contextual chat instruction changes the selected passage in context; provide a reviewable change and undo/history. Do not replace the entire prompt with an unrelated rewrite.

Manual settings are visible/editable per generation. Parameter defaults are available but are not a commitment to an automated run. Generation completion does not launch the next item automatically. Generate/Next remains the simple primary flow; avoid additional mandatory acceptance screens duplicating those actions.

## 5. Semi — exactly five automation choices

Use these five checkboxes, matching the user's specified stages:

| Checkbox | If checked | Parameters or policy to confirm |
|---|---|---|
| Character image generation | Build images for applicable screenplay characters automatically | Image model/workflow, supported quality/output settings, defaults and candidate handling |
| Character-to-audio selection | Choose and save character voice bindings automatically | Eligible voice library/filter, language/style matching criteria, existing-binding reuse and unresolved-match behavior |
| World-building image generation | Build applicable reusable location/world images automatically | Image model/workflow, supported quality/output settings and defaults |
| Frame image generation | Generate required clip first/last frame pairs automatically | Frame model/workflow, supported output settings and which planned clips need frames |
| Video generation | Director chooses FFLF or R2V from available assets; optional previous-clip reference for R2V | Fixed initial quality/output/settings, duration policy, allowed FFLF/R2V workflows and automatic reference-selection policy |

Character-to-audio selection means choosing a voice asset/binding, not generating a voice file or training a model. Selecting its checkbox expressly authorizes automated binding according to the confirmed policy. Use the existing library; if a usable match is unavailable, pause at that binding with a clear choice rather than fabricate an asset. Shared voice files may bind to multiple characters, consistent with `char_world.md`.

An unchecked step pauses for manual action when reached. Checked steps execute when their inputs/dependencies are ready and advance without compulsory human result acceptance. The user may inspect, pause, revise or retake. Automatic prompt assembly and parameter validation are subordinate work within the selected stages; do not add story/graph/screenplay checkboxes to this post-screenplay page.

The displayed checkbox list does not prescribe an invalid dependency order. Required frame inputs wait for the selected character/world references; selected generation waits for its inputs. Independent selections can use supplied/library assets if an earlier optional stage was skipped.

Checking Video Generation authorizes the Director to choose **first/last-frame (FFLF)** or **reference-to-video (R2V)** per planned clip, using available manually or automatically prepared assets. If Video Generation is unchecked, the user chooses any supported video mode manually. Semi automatic video is resource-aware rather than forced to follow Full's image-free route.

### Director-selected workflow and references in Semi

- **FFLF:** choose when the current clip has usable first/last frames and their boundary control suits the action. Character/world images guide frame preparation; the final video request receives its two frame inputs. Select only additional direct reference inputs supported by that graph.
- **R2V:** select relevant character images and bound voices, plus world/background images where useful, according to the confirmed automatic reference policy. For later clips within a scene, the Director may also select the preceding generated video as a continuity reference. It is an optional, recorded choice rather than a mandatory previous-video input for every R2V request.
- The first clip of a scene can be FFLF or R2V with prepared image/voice/world references; it does not require a previous generated clip. Reset default predecessor selection at scene boundaries.
- Confirm the allowed workflows and reference policy upfront. The Director records its workflow/input choice and reason per clip; only supported combinations are submitted. Enforce role/capacity/prompt limits after building the manifest.
- If neither workflow has its required inputs, pause at the missing frame/reference preparation step. Do not silently fall back to T2V or change quality. The user can explicitly change the mode/setup if they want a different route.
- Existing voice binding remains a top recommendation in manual pickers. Semi's checked automated Video stage plus confirmed reference policy authorizes the Director to attach the appropriate prepared voice/image assets. A binding alone outside that policy does not authorize attachment.

**FFLF compatibility detail:** the inspected current local FFLF graph exposes two image inputs and a prompt, not a direct voice-reference slot. Character/world identity can be carried through prepared frames, but a bound voice file cannot be claimed as an input when the graph cannot accept it. If voice-reference conditioning is required, the Director chooses compatible R2V (or a future verified FFLF adapter explicitly supporting it). Required intent takes priority over guessing support.

## 6. Full — configure once, then generate the story's clips

Full skips character/world/frame image generation and does not require manual voice assignment. The user explicitly reconfirmed the original continuation loop: **the first clip of each scene is T2V; later clips are R2V using the immediately preceding video**. Configure quality and duration policy once, then retain every generated clip. Full does not use FFLF or require prepared character/world/voice assets.

Confirmed Full sequence:

1. Start the first planned clip of each scene with text-to-video.
2. Use the immediately preceding completed clip as the video reference for each following clip in that scene's R2V request.
3. Derive each continuation prompt from the next screenplay action/dialogue, shot/camera direction and predecessor continuity state. Include the actual reference label matching the selected previous clip.
4. Retain every generated clip and its exact request/history. A replacement never automatically deletes the old output.
5. Reset the chain at the next scene and start again with text-to-video.
6. Finish with ordered scene/clip results and source coverage. Film assembly/audio mixing remains a later step.

When entering Full through the regular path, confirm setup once on this page after screenplay generation. If a future story-only start uses an already confirmed saved Full preset, it may pass through this same setup state without another stop. “Fully automatic” describes execution after configuration; it does not authorize guessing unconfirmed quality settings.

## 7. Video quality and parameters: fixed upfront

Before starting automatic video generation (Full or Semi with Video checked), confirm the allowed workflows and all non-duration generation settings. **Quality is fixed initially.** The Director can choose duration if authorized, but cannot silently vary quality between clips.

Quality/output configuration includes the actual supported resolution/scale preset, aspect ratio/dimensions, frame rate and applicable model/sampling settings. Expose supported defaults with readable labels and an expandable exact-value panel. A seed or seed policy, if supported, is also confirmed upfront; it is not a new free parameter for the Director to change per clip.

Validate one compatible configuration for every workflow allowed by the selected wrapper (Semi: FFLF/R2V; Full: T2V/R2V). Backend-specific fields may differ, but their mapping to the fixed output quality must be explicit and validated. Do not silently downgrade quality when changing workflow. If the pair cannot support the selected preset, show the incompatibility before starting.

Changing fixed settings later pauses at a safe boundary and creates a new explicitly confirmed run-policy revision for future work. Existing clips keep their original parameters. Normal automatic execution may vary only duration among generation parameters under the selected policy. Semi also authorizes workflow/reference selection by the Director; that selection must preserve the fixed quality configuration. It is not permission to vary resolution or sampling quality per clip.

## 8. Duration: fixed or Director-selected per clip

Offer two policies for automatic video:

- **Fixed:** use the confirmed target duration for clips and divide longer scene/shot coverage into enough clips. If the remaining action is shorter, use permitted hold/pacing according to screenplay direction or expose an infeasible timing issue; do not silently switch to dynamic timing.
- **Director-selected:** the Director chooses a supported duration for each clip based on its action, dialogue, pauses and transition. The user confirms allowed minimum/maximum (and default target where useful), constrained by the installed workflows. Duration may differ between clips. All quality and other fixed parameters remain unchanged.

Choose duration before finalizing the clip prompt and job request. Long action/dialogue is divided at sensible boundaries into additional clips. Maintain a ledger of source action/dialogue spans covered and remaining, so dynamic timing cannot omit or repeat story content merely to fit a request.

The current inspected local H3 contracts support 5–15-second outputs; the UI reads actual supported values/increments from verified capability configuration. Show actual selected seconds with every queued/result clip. The duration decision and its reason are inspectable, not a new modal requiring human confirmation on every automatic clip.

## 9. Prompt preparation after setup

Only after mode/stage settings are confirmed, assemble prompts using:

```text
screenplay direction or standalone user intent
  + current scene/shot/clip coverage and duration
  + selected workflow/model and fixed parameters
  + actual selected references and per-reference instructions
  → model-specific final prompt
```

Manual and manual Semi steps expose the editable prompt before Generate. Automatic steps prepare/refine/validate internally and record the exact prompt alongside the result, without a compulsory prompt-review gate.

Keep MiniMax prompts strictly below 7,000 characters, counting compiled tags and adapter text. Enforce each image model's verified prompt/token/encoder budget. Preserve meaning during shortening and never truncate silently. Workflow/parameter/reference changes invalidate stale prompt validation and generate a traceable revised draft.

Creative microedits retain **Update screenplay** versus **This take only** in story-linked work. Isolated work has no screenplay to update; save the change to its local task brief/prompt revision. Automatically rephrasing for a model must preserve the screenplay's creative intent.

## 10. Progress, pause, resume and results

Present the policy summary and one readable progress view: stage/item, scene/clip position, task state, selected duration/quality and latest available outputs. Show which manual step is awaiting action in Semi.

Pause prevents new tasks from starting, while showing the current job's actual backend state. Resume continues from saved completed work. Refresh or navigation does not restart generation or resubmit an ambiguously queued job. Changing automation choices/settings applies at the next safe boundary to future work.

Generation completion is separate from human quality approval. Automatic steps advance on successful completion; outputs stay available for later review and retakes. A technical failure pauses with an actionable reason. Do not introduce unlimited hidden retries or automatic deletion of failed-quality clips.

Manual/Semi manual retakes use Keep/Discard from `video_gen.md`; automatic video retains every generated clip. Replacing a predecessor marks dependent continuations stale and offers an explicit regeneration path while preserving all old media.

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

1. **Manual regular path:** screenplay → setup Manual → edit/annotate a prompt → Generate → review → Next; no next generation starts before the user's action.
2. **Semi mixed path:** check character images and video only → confirm their settings/reference policy → automatic characters → manual remaining steps or explicit skips → Director selects viable FFLF/R2V and compatible refs; the page clearly explains each upcoming stop.
3. **Semi defaults:** check each of the five stages → each opens its appropriate settings/policy → accept defaults → summary accurately lists what will run; no extra repeated parameter gates.
4. **Full fixed duration:** confirm quality/duration → skip images → first scene starts T2V, later clips use predecessor R2V → second scene resets to T2V → retain all clips; no human generation/acceptance clicks mid-run.
5. **Full dynamic duration:** confirm quality and allowed duration range → differing clip durations appear with recorded decisions → quality stays fixed and complete story coverage remains visible.
6. **Isolated FLF:** directly open the video form → supply two uploaded/library images and prompt → generate/review without a story or screenplay.
7. **Isolated image/R2V:** directly open a shared stage → edit/annotate prompt, choose compatible references/settings → save results with no fabricated scene links.
8. **Return/recovery:** refresh/pause/resume across manual and automatic steps → inputs/results survive and no duplicate job starts.
9. **Status:** limits/defaults/usable workflows agree with the setup and generation forms; unavailable capabilities have an actionable explanation.
10. **Semi FFLF:** Director selects FFLF with two usable frames → character/world continuity comes through those frames → no voice file is presented as directly submitted to the current graph. A required voice-reference intent selects compatible R2V instead.
11. **Semi R2V:** Director selects relevant prepared character/voice/world assets and optionally the preceding clip → manifest, reference labels and prompt reflect exactly those inputs → clip uses the confirmed quality and a permitted duration. Missing inputs pause clearly; no implicit T2V fallback.

Use wireframes or a clickable prototype of these journeys before claiming the UI is usable. Automated checks support the chosen behavior but do not substitute for seeing the real screens and completing these flows.


## 14. Unified production visibility and durable execution

Apply `ux_shared.md` for saved context, clear next actions, mobile arrangement and offline recovery. Show a single production overview with current item/scene/clip, exact prompt/ref manifest, duration, fixed quality, coverage, take history and job state. A checked stage completes automatically under its confirmed policy; completion must not be represented as human acceptance.

One durable application service owns state transitions, submission identity, job IDs and resume; the LLM supplies authorized creative/workflow/duration decisions. Do not depend on an active coding-agent chat alone to keep background production alive. Upstream creative gates/selectors are adapted to this policy rather than copied as a competing controller. See `integration.md`.

Known-cost estimates may be displayed before starting a configured run, identifying uncertain/local/LLM costs separately. Do not import repeated per-clip approval thresholds as new mandatory gates. Any future budget policy requires an explicit run-level contract.
