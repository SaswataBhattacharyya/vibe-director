# UI structure and frontend routing

**Proposal:** reorganize existing React pages incrementally. Retain React/Vite, React Router, TanStack Query, Tailwind and the existing UI primitive library. No design-system replacement is required.

## Navigation

| Global area | Purpose | Main content |
|---|---|---|
| Projects | Resume/create work | Project cards; stage/status; latest run; recent accepted output |
| Create | One-off creation | Image, Video, Dialogue/Voice, Music/Foley, Expert workflows |
| Library | Find and reuse assets | Images, videos/clips, voices/audio, music/sounds; search and provenance |
| Automations | Reusable execution recipes | Audio pipeline editor, saved pipelines, run history |
| Jobs | Follow current/recent work | Production/text/image/audio/download/analysis job projections |
| Settings | Configuration and optional resources | Provider/engine readiness, styles, expert training resources |

Within a project, use **Story · Bible · Shots · Audio · Review · Delivery**. Persistent header shows project title, run selector, production type, authority mode, making route and current stage. The same library picker can be opened from Bible, Shots and Audio.

## Primary shot workspace

```text
PROJECT / RUN                          Mode · Route · Stage · Jobs
Story | Bible | Shots | Audio | Review | Delivery
┌───────────────────┬────────────────────────────────┬───────────────────┐
│ Scenes and shots  │ Selected shot                   │ Inspector         │
│ status badges     │ Story/dialogue context          │ Recipe inputs     │
│ shot order        │ Prompt + ordered references     │ Timing/settings   │
│ selected take     │ Validate / Render               │ Readiness/blockers│
│ dependency hints  │ Native player + take comparison │ Provenance/review │
└───────────────────┴────────────────────────────────┴───────────────────┘
```

Use existing resizable-panel primitives on desktop. On smaller screens collapse the list and inspector into drawers; keep the selected shot/player and primary action visible. Respect keyboard focus, labeled fields, readable contrast and a textual equivalent of status color.

### Progressive disclosure

Default fields are intent, required inputs, preview and primary action. Put seed/steps/model details in **Advanced**. Put raw graph JSON, prompt corpus/debug traces and dependency checks in **Expert / Diagnostics**. Expose timing and identity settings whenever they affect an actual creative choice.

Do not stack every audio, workflow and reference form in one production page. The shot's recipe determines its form. The tool's output can be attached to the current project through the shared asset picker.

## Canonical proposed routes

All routes below are frontend routes. Backend paths remain compatible during the first UI migration.

| Route | Surface |
|---|---|
| `/projects` | Project home |
| `/projects/new` | Setup/import |
| `/projects/:projectId` | Resume last saved run/stage with validated fallback |
| `/projects/:projectId/runs/:runId/story` | Story desk |
| `/projects/:projectId/runs/:runId/bible` | Characters/worlds/masters/voices |
| `/projects/:projectId/runs/:runId/shots` | Scene/shot overview |
| `/projects/:projectId/runs/:runId/shots/:shotId` | Selected shot desk |
| `/projects/:projectId/runs/:runId/audio` | Project dialogue/music/Foley |
| `/projects/:projectId/runs/:runId/review` | Gates, takes and evidence |
| `/projects/:projectId/runs/:runId/delivery` | Accepted outputs and legacy composition |
| `/create/:tool` | Supported image/video/dialogue/voice/music/Foley recipes |
| `/create/expert` | Workflow library and optional 3D/VFX tools |
| `/library/:kind` | Managed assets and existing indexes through adapters |
| `/automations` and `/automations/:pipelineId` | Saved pipelines/editor |
| `/jobs` | Read-only aggregate job status; actions use owning APIs |
| `/settings` and `/settings/styles` | Settings/readiness and style library |

**URL project/run/shot IDs are authoritative.** Verify the run belongs to the project and the shot belongs to the run before fetching/mutating. Existing `CURRENT_PROJECT_KEY` and `story-builder.production.project` / `.run` values can provide an initial navigation fallback once. Do not let stale localStorage change a scoped URL's project. Project switching clears incompatible run/shot selection using existing navigation helpers.

## Existing pages: reuse and destination

| Current route/page | Plan | Destination / reusable parts |
|---|---|---|
| `/` — Home | Adapt | `/projects`; retain existing working entry points during compatibility |
| `/story` — StoryBuilder | Reuse | Story/source/artifact forms and legacy project editing |
| `/canvas` — StoryCanvas | Reuse with gap labeled | Story revisions/analysis/outline; passage-edit placeholder stays visibly incomplete |
| `/production` — ProductionWorkspace | Main reuse target | Extract stage panels into scoped workspace; preserve API calls, gate semantics and take review |
| `/manual-director` — ManualDirector | Preserve | `/create/video` expert/legacy adapter; contracts remain distinct |
| `/media` — MediaComposer | Preserve and narrow | Expert workflow explorer, reference selection and API-graph execution |
| `/generate` — Generate | Adapt | Creation landing page; current page is mostly a gateway |
| `/image-detailer` — ImageDetailer | Reuse | `/create/image` Analyze tab / library inspector |
| `/audio` — AudioStudio | Reuse | Timed TTS, voice effects, voice library and F5 preparation subpanels |
| `/audio-reconstruct` — AudioReconstruct | Preserve as partial | Project Audio → Reconstruction; add missing accept/record/ASR only in explicit later PRs |
| `/music-sound` — MusicSound | Reuse | Project Audio and one-off Music/Foley forms |
| `/audio-tools` — AudioUtilities | Reuse | Batch utilities and audio library |
| `/automation` — AutomationStudio | Reuse | Pipeline editor/history; distinguish executable blocks |
| `/status` — AgentStatus | Reuse | Jobs/diagnostics and existing orchestration views |
| `/video-repertoire` — VideoRepertoire | Reuse | Library → Video research, search/download/analysis |
| `/video-summariser` | Preserve alias | Redirect only after equivalent research screen exists |
| `/style-library` — StyleLibrary | Reuse | Settings → Styles and project style picker |

Keep old pages/routes operational until the new destination handles their equivalent actions. Where a legacy route lacks an explicit project/run, resolve validated saved context or show a selection screen; never guess an ID.

## Component extraction order

ProductionWorkspace is roughly 1,346 source lines and AudioStudio roughly 567. Extract one behavior at a time without changing contracts:

1. `ProjectRunHeader` and `RunConfigurationSummary`.
2. `StoryReviewPanel` and `TextStagePanel`.
3. `CharacterWorldPanel`, `ImageCandidatePanel`, `VoiceBindingPanel`.
4. `SceneShotList` and `ShotPlanPanel`.
5. `ShotComposer`, `OrderedReferencePicker`, `ShotValidationPanel`, `PromptRefinePanel`.
6. `TakePlayer`, `TakeHistory`, `TakeReviewPanel`, `JobStatusPanel`.
7. `TimedDialogueForm`, `AudioEffectForm`, `MusicForm`, `FoleyForm` extracted from their current pages.
8. `AssetPicker` and `AssetInspector` backed by existing owner APIs.

Reuse AppShell, FileUpload, ProductionStylePicker, navigation/status helpers and current primitive components. Retain current form validation and mutation/invalidation behavior when extracting. Split client functions by domain through re-exports before changing callers; avoid a simultaneous file move/API rename/UI redesign.

## Presentation rules

- Label results **Draft**, **Generated**, **Reviewed**, **Accepted**, **Superseded** only where the owning store supports that interpretation.
- Render thumbnails/player immediately for existing artifacts; no provider call to “refresh” an accepted take.
- For a blocked operation, show missing input/dependency and the relevant action, not a generic failure toast alone.
- Display voice identity and reference order beside generation controls.
- Compare original audio/video with derivatives; default playback keeps native audio intact.
- Use separate style labels: narrative writing style, voice delivery style and visual recipe.
- Unsupported expert recipes can be viewed/saved/exported; their disabled Generate action names the missing adapter/readiness condition.
- Training resources use **Prepare dataset** until a supported trainer is implemented and validated.

## Small browser acceptance set

Project A → run A → shot A deep link; switching to Project B; refresh/back restoration; existing legacy routes; one story gate; reference reorder invalidation; candidate/voice selection; native take playback and acceptance; unsupported recipe disabled state; pipeline missing-adapter state; Delivery acceptance filtering. Mock inference/provider calls for layout tests. Reuse existing source tests for controller semantics.
