# Vibe Editor — integration plan

## 2026-10-29 owner-requested effects extension

Implemented per-clip **Filters, speed & transition** controls in the proposed timeline: cinematic/VHS/black-and-white grading with strength/reset; constant speed or smooth start-to-end speed ramps with matched pitch-preserving audio; cut/dissolve and 14 pinned official shader transitions, including warp/blend morph. These settings are included in clearance 2 and use the existing serial render job. Saving changed settings invalidates the previous approval. Preview uses the approved render path; there is no unapproved live render. Morph is not AI subject transformation.

Real synthetic CPU render acceptance passed for the filter/ramp/shader/audio path, plus focused mocked UI and backend checks. Owner media, microphone and AI voice-quality acceptance remain separate. See `ACQUISITION_AND_SECURITY.md` for provenance and limitations. The historical richer-transition deferral below is superseded for these explicit effects only; layered audio, automatic specialist execution and other open items remain open.

Date: 2026-10-26. Status: core implementation and pinned acquisition complete; live provider/render acceptance pending. Advanced operations remain explicitly open below. No generation or render was started during implementation.


## Implementation ledger — simplest steps

1. **Done:** inspect inventory; acquire one pinned official HyperFrames checkout and CLI package; copy its four official skills with license/provenance. Reuse existing browser, FFmpeg, media library and durable job queue. See [acquisition and security report](ACQUISITION_AND_SECURITY.md).
2. **Done:** Media Prep → Vibe Editor with named projects, saved stage, chat draft, shared search/import/preview/ranges, `/style` and `/addstyle`, confirmed style rules and project overrides. Independent collapsible navigation/written-work/preview panes also wrap Current Take without replacing its generation controls.
3. **Done in source:** two revision-bound chat approvals, trusted JSON composition, serial shared-queue render, stop, pause before publication, status refresh, saved approved revisions/restoration, final preview and export collision confirmation. Supported edits: reorder/trim selected clips, image holds, hard cuts, contain/cover, captions and source audio or one replacement soundtrack. Timeline controls and advanced JSON editing both require renewed plan approval.
4. **Pending owner acceptance:** send a brief using the selected Director model, approve it, select a few local media ranges, review/approve the exact tool plan, render, inspect sound/cuts/captions, reload/reopen and export. No provider request or render was initiated during implementation. Sandbox CLI startup, syntax/build and isolated idle UI checks are narrower evidence.
5. **Open:** richer transitions, animated graphics, J/L cuts and layered audio; automatic specialist execution adapters; portable project bundles; full undo/redo and preference export/history UI; confidence-based clarification reduction beyond retrieving confirmed rules. Current specialist requests report the missing adapter and use existing tools followed by import; a vocabulary entry is not an executable effect. These items are not declared complete.

### When chat passes work on

A normal chat message starts only interpretation. The assistant presents the creative brief (clearance 1); an explicit approval button or a standalone affirmative chat reply approves the displayed revision. Necessary unanswered questions prevent approval. If no media is selected, it asks for media first. After selecting ranges, **Prepare media and tool plan** obtains a concrete proposal. Clearance 2 approves those exact ranges, settings and tools together; only then is the render queued. A qualifying chat approval works like the button. Changed media, timeline or style invalidates approval. Learning proposals have their own confirmation and cannot be approved by approving an edit. Refresh never advances a clearance or queues a render.

### Source and data map

- `frontend/src/VibeEditorPage.tsx`, `EditorWorkspace.tsx`, `TakeWorkspace.tsx`: app UI and shared panes.
- `backend/story_builder/services/vibe_editor.py`, `vibe_editor_api.py`, `vibe_editor_render.py`: state, API, provider preparation, validated composition and sandboxed render.
- Existing `video_repertoire_worker.py`: shared execution route and GPU workload lock.
- `local_data/vibe_editor/`: ignored runtime, local profile/styles/projects/compositions. Shared asset IDs remain in the existing library. External reference checkout location and integrity are in `sources.lock.json`.

## 1. Objective and accepted decisions

Add prompt-driven editing under **Media Prep → Vibe Editor**, backed by HyperFrames composition/preview and existing Vibe Director assets, execution services and specialist tools. Support standalone editing projects and optional links to story projects. Preserve screenplay, Create functionality, generation modes and pipelines. Redesign Current Take presentation with the shared three-pane workspace described below; retain its jobs, controls and recovery behavior.

The owner confirmed:

1. Learned preferences apply across projects, with project-specific overrides.
2. Clearance 2 reviews **selected media/ranges and the tool plan together**, before asset creation or editing begins.
3. Confirmation remains required later, even when the system learns enough to ask fewer questions.
4. Editing terminology is the assistant's responsibility: translate everyday intent into appropriate editing techniques, explain unfamiliar terms in plain language, and show the concrete effect in the brief.
5. Learning is scoped to Vibe Director only, with user-owned named styles and project overrides. It must not modify global Codex skills or affect unrelated applications/users.
6. `/style` opens an inline searchable style picker in the composer. Current Take and Vibe Editor share a Codex-like three-pane, independently collapsible layout.
7. `/addstyle` asks for a unique style name inside the composer dropdown; Enter saves a new empty learning profile. Each style learns independently from scratch. Only verified factual context may be shared between styles; learned preferences, principles, examples and interpretations do not cross style boundaries.

The owner authorized implementation and necessary acquisition. Real provider/render acceptance remains owner-started. The older assembly plan's limited timeline scope predates this explicit editor request; this plan extends that scope without replacing existing assembly.

## 2. Acquisition: what to clone or install

Inspect local inventory and pin versions/licenses before acquiring anything. Existing reference material is not automatically an installed or runtime-accessible skill.

| Source | Proposed action | Purpose / duplication boundary |
| --- | --- | --- |
| [heygen-com/hyperframes](https://github.com/heygen-com/hyperframes) | Primary new source: one pinned reference checkout; install only required pinned runtime/Studio packages into a local project environment | Composition engine, embedded preview/timeline, agent authoring and render. Do not vendor the whole monorepo into product source. |
| Official HyperFrames skills | Acquire missing `hyperframes`, `hyperframes-cli`, `hyperframes-registry`, `media-use` from the pinned source | Four core skills. Compare existing on-disk copies first; register/adapt one authoritative copy. Avoid blanket `skills add --all`. |
| [HKUDS/CLI-Anything](https://github.com/HKUDS/CLI-Anything) | Conditional reference checkout, after an identified missing application adapter | Evaluate selected GIMP/Inkscape/Audacity harnesses with actual installed application versions. Existing Blender/FreeCAD integrations take precedence. Not required to open the first editor. |
| [kajisho5/ffmpeg-skill](https://github.com/kajisho5/ffmpeg-skill) | Optional selective skill/reference acquisition | Fill demonstrated instruction gaps; retain existing FFmpeg execution services. Do not install a second job controller or duplicate media tooling. |
| [showheyohtaki/motion-prompt](https://github.com/showheyohtaki/motion-prompt) | Optional curated reference snapshot | Vocabulary/examples for the Vibe Lexicon; reference material, not an editing engine or mandatory executable skill. Preserve applicable attribution. |
| [alchaincyf/huashu-art-motion](https://github.com/alchaincyf/huashu-art-motion) | Optional curated reference snapshot | Selected art/motion recipes. Check separate font, stroke-data and example-media permissions; do not assume the code license covers those assets. |
| [LottieFiles/motion-design-skill](https://github.com/LottieFiles/motion-design-skill) | Defer unless it fills a measured gap | UI-motion principles overlap installed GSAP/emotional-design skills. Not a replacement for filmmaking direction. |
| [HyperFrames community skills](https://github.com/heygen-com/hyperframes-community-skills) | Browse individually when needed | Review provenance/instructions and installed equivalents before adding; no bulk installation. |

Do **not** acquire duplicate Blender Superskill, FreeCAD skill collections, GSAP skills, a second grilling skill, or Remotion as another initial rendering framework. Existing `grill-with-docs` supplies focused clarification. Remotion conversion, Figma and slideshow HyperFrames skills are on-demand additions only.

### Existing reuse found

- Global Blender, FreeCAD, GSAP, GNU/Linux, emotional-design and `grill-with-docs` skills are already present. GNU/Linux administration skills do not prove GUI application editing adapters exist.
- Project `skills/vibe-director` and `skills/video-prompting` remain authoritative for existing direction/generation behavior.
- Media Prep and shared media library already support asset identity, analysis and search; semantic search has real index prerequisites.
- `/home/riki/web_dev/OpenMontage` already contains a HyperFrames adapter, style bridge and instructions. Inspect those references before designing seams, but do not copy covered implementation without the compatibility decision recorded in `plans/openmontage_licensing.md`. Existing instructions may describe an older upstream skill layout.
- HyperFrames 0.8.199 is installed in the isolated local editor runtime; the backend adapter invokes its CLI. The app retains React 18 and uses its native editing controls rather than upgrading React for upstream Studio.

Official HyperFrames [quickstart](https://hyperframes.app/docs/1-startup/2-quickstart) and [Studio documentation](https://hyperframes.app/docs/5-packages/studio) are implementation references. At research time upstream requires Node 22+ and offers React Studio components. Confirm pinned package peer dependencies against the existing React 18/Vite environment before changing dependencies.

## 3. One Vibe Editor home, no duplicate media store

Use this `Vibe Editor/` directory as the central hub for editor documentation, project-local skill sources, recipes and future editor-specific integration files. Keep frontend/backend entry points in the app's existing source layout and link them here; do not create another application server.

Proposed hub structure, created only as the relevant phase is implemented:

```text
Vibe Editor/
  PLAN.md
  sources.lock.json       # source URL, commit/version, license, local reference path
  skills/                 # editor-specific skills, registered with the existing loader
  recipes/                # curated Vibe Lexicon entries and examples
  docs/                   # contracts, acceptance evidence and operator notes
```

Reference clones stay outside product Git, proposed at `/home/riki/web_dev/vibe_editor_sources/`, with their locations recorded in the hub. Saved project data, preferences, revisions and intermediates use ignored `local_data/vibe_editor/`; original media and models stay in their existing locations. The UI presents this as one Vibe Editor workspace. Export goes to the user's chosen folder.

## 4. User journey and approvals

1. **New / Open project:** enter a name or choose a saved editor project. Optionally link a story; standalone editing requires no screenplay. Restore timeline, current selection, brief, revisions and jobs.
2. **Describe the edit:** prompt may apply to the whole composition, selected clips, audio track or time range. Show that scope before submitting.
3. **Clearance 1 — creative brief:** ask a few consequential questions, then show duration, format, audience/tone, narrative beats, audio/text intentions and things to preserve. User approves or corrects this interpretation.
4. **Find media:** search repertoire or import files. Preview suggested candidates and exact ranges, identify missing assets, and pin a shortlist. No silent analysis or generation simply because a search returned no match.
5. **Clearance 2 — media and execution plan:** show selected clips/images/audio, in/out points, proposed generated assets, assigned tools, dependencies, expected transformations and output settings. User approves this concrete plan together.
6. **Execute approved revision:** use existing durable jobs; show stages, actual tool, source assets and live preview where supported. New scope, media substitutions or tool changes requiring a different plan return for approval.
7. **Review:** play/scrub video, listen to audio, inspect captions and compare revisions. A correction such as “less dramatic” creates a proposed edit and a visible change summary; do not overwrite manual edits silently.
8. **Save / Export:** saving retains the editable project even without exporting. Choose output folder, filename, dimensions, aspect ratio, frame rate and audio settings. Prompt on collision. Register the final as a shared asset with provenance.

Two clearances approve an editing plan; they do not introduce acceptance prompts for every clip in an already approved automated generation run. A reliable match may make a clearance a short summary with Approve/Edit buttons, but learned confidence never supplies consent.

### Example

“Make this punchier, spiritual rather than dramatic, and keep the spoken words.”

- Clearance 1: propose shorter pauses, earlier visual beats, quiet spiritual instrumentation and no dialogue rewrite; ask about target duration if unknown.
- Clearance 2: show the exact selected ranges; HyperFrames for composition, existing audio tools for music balance, FFmpeg for delivery. Blender appears only if a new 3D element is actually requested.
- After review, offer to remember the confirmed meaning of “spiritual” for this user, with project override available.

## 5. Shared workspace: Current Take and Vibe Editor

Owner UI correction, 2026-10-26: use the supplied Codex screenshot as the interaction/layout reference. This replaces the earlier proposal that put the preview in the center and conversation on the right.

```text
[ Left: navigation / projects ] [ Center: conversation / written work ] [ Right: preview / artifacts ]
```

All three panes collapse and reopen independently. Provide visible restore controls even when a pane is closed, resizable boundaries, retained pane widths/open state and an expanded preview mode. At narrow widths use one active pane with accessible switches instead of compressing three columns.

- **Left:** retain existing application navigation and project context; expose editor projects/history and media browsing without duplicating the shared library.
- **Center:** written direction, prompts, approvals, selected-media/tool-plan summaries and truthful progress. Anchor a multiline composer at the bottom, with attachments, slash-command suggestions, selected style and send/stop state. Preserve draft text when opening panels or switching styles.
- **Right:** generated video, image, audio preview or a selected artifact opens in a docked panel, like the document panel in the reference screenshot. Additional artifacts use tabs within this panel rather than creating more full-width columns. Collapsing or changing tabs never cancels a job or loses position/state.
- **Current Take:** written prompt/settings/status and run controls in the center; selected generated clip/player on the right. Show a useful waiting/generating state until a validated playable file is ready. Keep pause/stop/refresh behavior and project-scoped saved progress; the new layout does not add chat-driven prompt rewriting or replace generation controls.
- **Vibe Editor:** conversation/approvals in the center; HyperFrames preview and a collapsible timeline area in the right workspace. Media search, properties, source and exports open as appropriate panel tabs/drawers. Save timeline position, selection and revision independently of collapsed panels.
- Keep the existing Vibe Director themes and visual identity. The screenshot supplies layout and interaction behavior; it does not require replacing the app's theme with Codex branding.

Media Prep → Vibe Editor remains the editing entry. Shared project header exposes name/selector, save state and revision. Current Take remains the generation monitor. Validate embedded Studio component support before committing to detailed timeline controls.

### Composer `/style` interaction

1. Typing `/` offers commands; typing `/style` filters to Style. Clicking it or pressing Enter opens the style list inside the composer popover.
2. Search by name/description; use Up/Down and Enter or pointer selection. Escape closes the picker without submitting the prompt. Enter while the picker is active selects the highlighted style, not Send.
3. Show the selected style as a removable chip, with description/inspection available. Include No style, project default, personal saved styles and explicit Create/Edit style actions. Create opens the same `/addstyle` interaction below. No style uses an isolated default learning context, not a blend of named styles; shared factual context remains available.
4. Selecting a style influences the proposed interpretation/plan. It does not immediately apply edits, launch generation, replace written prompt text or rewrite an existing approved revision.
5. Make the chosen style and resolved project overrides visible in the brief. A change affecting an approved plan creates a proposed revision for confirmation.

### Composer `/addstyle` interaction

1. Type `/addstyle` and select it or press Enter. Open an inline dropdown/popover containing a style-name input and a brief explanation: “Starts fresh; learns only from this style’s confirmed conversations and corrections.”
2. Enter a name unique within the current user's Vibe Director styles. Trim surrounding whitespace and compare normalized, case-insensitive names for uniqueness. Reject empty/duplicate names with an inline message; never overwrite an existing style. An existing match may offer Switch to this style explicitly.
3. Enter in the name input saves the new style and selects its chip for subsequent prompting. It does not submit the composer draft or execute an edit. Escape cancels without creating a style; preserve the draft. Use a stable internal style ID independent of its display name and enforce uniqueness atomically in persistence.
4. Create an empty learned-memory context: no inherited taste, prompting interpretations, examples, confidence, principles or rules from any other style. Begin focused clarification and the same two approvals. A style can contain that user's own principles and rules, proposed or entered explicitly and confirmed in that style.
5. Save before showing success; on persistence failure retain the entered name and show Retry. No ghost style or silent fallback. Renaming later preserves the style ID and its learning while enforcing the same uniqueness rule.

### HyperFrames integration boundary

Style creation, intent learning, factual memory and approvals belong to Vibe Director, above the rendering engine. After the user approves a plan, translate that revision into HyperFrames composition instructions and any approved specialist tasks. Bind each revision/job to its style ID and memory version: switching styles must not mutate an already running or approved revision. HyperFrames does not need to learn the user's style or implement these slash commands itself. This keeps the proposed architecture compatible with an embedded engine; exact Studio/persistence seams still require the Phase 1 integration proof.

HyperFrames handles authored composition and motion; it is not assumed to perform arbitrary character replacement, relighting or novel 3D camera moves inside existing footage. Such requests require an explicit capable specialist step, or an explanation that no adapter exists.

## 6. Media discovery and choosing clips

Reuse `MediaPrepPage`, `MediaLibraryPage`, `media_library.py` and `media_semantic_search.py`, not a new repertoire database.

- **Text match:** filename/title, tags, description, analysis text and indexed transcript where available.
- **Semantic:** indexed visual/audio content, with index readiness displayed. If unavailable, offer text search or explicit indexing; do not label literal matches semantic.
- Filters: video/audio/image, project/shared library, duration, orientation, source and analysis state.
- Results: thumbnail/keyframes or waveform, duration, source, match explanation and preview. Searchable transcript hits open the corresponding time range where timestamped data exists.
- Choose whole assets or in/out ranges; audition audio and compare alternatives before approval. Preserve one asset ID and source lineage.
- Upload/import supports user files as well as library assets. Missing external files offer Relink, Remove or Replace rather than a broken player marked ready.
- Deleting analysis retains the original; deleting an asset used by an editor revision warns about those references. Existing YouTube download storage stays authoritative.

## 7. Tool orchestration

| Need | Preferred route |
| --- | --- |
| Cuts, layout, captions, overlays, transitions, timing and motion graphics | HyperFrames composition, existing GSAP knowledge |
| Trim/conform/remux, loudness, codecs and delivery validation | Existing FFmpeg services |
| Select existing footage/music/images | Shared Media Prep/repertoire search and selection |
| New generated clips/images/audio | Existing Vibe generation/asset services, explicit approved request |
| Animated 3D scene, object or camera | Existing Blender bridge/skills; render an asset for the composition |
| Dimensionally accurate CAD/product asset | Existing FreeCAD bridge/skills, then an appropriate render/export step |
| Image/vector/audio application editing not covered above | Add a verified specific adapter only when required; CLI-Anything is one candidate |

Compile the approved plan into dependent work items handled through the existing durable execution authority. Reuse unchanged assets by identity/content hash. GPU jobs use the same queue/memory/runtime safeguards as current production. No new parallel generation controller.

Before reusing an output, check its file and revision dependencies. A tool name in a skill is not proof that its binary, bridge, fonts, models or runtime are available. Show a recoverable unmet prerequisite rather than silently selecting a different engine.

## 8. Skills and adaptive interpretation

Proposed **project-specific** additions, implemented later using the skill-creator workflow:

1. **Vibe Editor director:** connects existing direction craft to editing briefs, scope, two clearances, media choice, tool assignment, reversible revisions and review.
2. **Vibe intent learning:** uses existing `grill-with-docs` for focused questions and a structured confirmed-preference store. It proposes memory updates rather than silently rewriting skill instructions.
3. **Vibe media selection:** shared search, candidate comparison, precise ranges and missing-media handling.

The four official HyperFrames skills supply engine-specific authoring. Link the editor director from the existing Director skill when implemented; do not rewrite H3 prompting as part of this work.

Keep the learning skill's instructions and records inside Vibe Director. Store user-owned styles/preferences in app-local data, keyed by user/profile identity; do not expose or learn another user's preferences implicitly. A local single-user installation still records an explicit profile identity. Each named style starts with no learned preferences and can accumulate a description and confirmed rules for pacing, cuts, camera/motion, color/light, typography, sound/music and preservation constraints as applicable. Avoid treating a style as a single preset that overrides every task.

### Strict style isolation and shared factual context

- **Style memory:** key every learned interpretation, preference, principle, rule, example, correction and confidence value by user ID and style ID. Retrieve only the active style's records. Do not use another style's conversation, embedding matches or summaries to infer taste. Project overrides are keyed to the active style too; choosing a project must not import a different style's rules.
- **Shared facts:** a separate, provenance-bearing store for objective context such as asset IDs, accessible file paths, file metadata and verified tool availability. Facts retain user/project access boundaries and must be revalidated when stale. A path saved as a fact is not proof that the file still exists or that it is authorized for every project.
- Do not promote “I like rapid cuts,” “use this music,” a favorite asset/path selection or “cinematic means X to me” to shared facts. File location can be shared; the preference for using that file remains style-specific.
- Shared editing vocabulary and verified tool capabilities remain general knowledge, distinct from any user's learned meanings. If a style uses a term differently, its confirmed interpretation applies only there.
- Resolution order: **current explicit request → active-style project override → active style's confirmed rules → general editing knowledge/default behavior**. Shared facts inform available inputs and feasibility, not taste. No fallback to another style's preferences. Material conflicts return for clarification.
- Memory records user/style IDs, interpreted meaning, scope, confirmed example/correction, provenance, confidence and version. Never infer a preference merely because a render completed. Export/delete/forget style learning independently of shared facts.

This supersedes the earlier proposal for general cross-style user-preference fallback. Cross-project learning remains enabled **within each style**, for that user only.

During learning, ask about uncertain or consequential choices. With consistent approved examples, prefill the brief and ask fewer questions. Conflicts, unfamiliar contexts and rejected interpretations increase clarification. Both approvals remain. Provide Inspect, Edit, Forget and Reset controls, with revision history; forgetting excludes the preference from future interpretation. This is preference memory, not model weight training.

The Lexicon translates terms such as J-cut, L-cut, match cut, cut on action, montage, restrained camera movement or “punchy” into definitions, examples and supported edit recipes. The assistant should select the appropriate terminology/technique from ordinary user language; users are never required to know the jargon. For example, “let us hear the next person before we see them” can become a proposed J-cut, with a short explanation and timing preview. It must distinguish a vocabulary example from a tested executable operation.

## 9. Persistence and recovery contracts

An editor project owns revision IDs, composition source/timeline, asset IDs and ranges, brief, approvals tied to revision/hash, execution plan, job/result references, output profile and chosen export destination. Existing shared assets and jobs remain authoritative.

- Save source before execution; store draft and approved revision separately. Undo/redo and manual changes survive reload.
- Refresh reads/reconciles status only. It never starts another render.
- Resume reconciles existing job IDs and files before resubmission; completion requires valid output.
- Distinguish user pause, awaiting approval, queued, running, recovery needed, failed, stopped and completed. Show the reason and next action; avoid indefinite spinners or stale ready banners.
- Pause takes effect at the next safe boundary and says whether the active step continues. Stop prevents downstream work and cancels the owned active job where supported, without clearing unrelated ComfyUI jobs.
- Reopen restores project stage and preview. A failed step does not erase successful upstream assets.
- Generated composition code runs in a restricted render workspace: no arbitrary host file/network access. Resolve approved asset handles, validate export paths and use existing provider/process guards.
- Portable project export is a separate explicit action: manifest-only or copy selected media after showing size; never duplicate the repertoire implicitly.

## 10. Implementation phases and acceptance

1. **Inventory and compatibility:** pin HyperFrames, licenses and core skill revisions; check Node/Chromium/FFmpeg and React peers. Use Graphify plus source to map existing service seams. Prove a small local composition can embed, save/reopen, preview and export; no GPU/provider generation.
2. **Projects and media:** persist revisions/selection, add shared picker, text search, semantic readiness, range preview/import and missing-file recovery.
3. **Prompt editing:** implement both clearances, revision change summaries, basic cuts/audio/captions/graphics, progress and chosen-folder export.
4. **Specialist routing:** connect existing Blender/FreeCAD/generation/audio adapters one useful end-to-end task at a time. Add application harnesses only for uncovered operations.
5. **Learning and Lexicon:** Vibe Director-only user profiles/named styles, `/style` and `/addstyle` pickers, fresh independent learning per style across projects, style-specific overrides, correction/forget behavior and curated examples. Measure fewer unnecessary questions without reducing approval requirements.

Acceptance cases include empty project, existing project, unavailable semantic index, missing source, no search match, wrong candidate, absent tool, changed prompt invalidating approval, tool failure, browser reload during render, duplicate submit, pause/stop, invalid output, unavailable output folder, filename collision and saved-project restore, all three panes collapsing/restoring, panel tabs retaining playback/selection, `/style` keyboard versus send behavior, user profile/style isolation, `/addstyle` duplicate/case/empty-name and save-failure handling, fresh style with zero inherited rules, cross-project same-style learning, shared-fact access/staleness and selected-style conflicts. Verify UI interactions with Playwright when available; owner starts authorized GPU/provider acceptance. Do not claim success from mocks or compilation alone.

## 11. Current outcome / next decision

The full plan and the two owner-confirmed policies are recorded. No remaining contradiction blocks planning. The next implementation action, if approved, is Phase 1 inventory and a minimal embedded HyperFrames composition—not installing every suggested skill/tool. Runtime integration remains unverified until that phase.

### Current Take layout clarification — implemented 2026-10-26

The complete generated clips gallery, selected video, assembly preview and Accept/Retake/Next controls occupy the right pane. Prompt/history text, frozen requests, project/run status and readiness remain in the middle. Both desktop panes scroll independently and remain collapsible; narrow screens use Written/Preview tabs. Existing generation handlers are retained.


## Asset selection and chat attachments — 2026-10-26

The right pane's **Asset selection** tab replaces the plain media filename list with thumbnail browsing, video hover, recent-first/oldest-first ordering, existing literal/semantic search and preview/range controls. Pick an asset then **Add to chat selection**. Chat displays saved attachments and accepts file selection, drop and clipboard media. Uploads reuse the same project workspace/library and validated range API; no duplicate storage engine or automatic render. Existing saved `media` tabs remain compatible. Selection is project-persistent and shared with the creative brief/tool plan; changing it still follows existing revision and clearance rules. This is editing source selection, not an independent inspiration-only collection. Chat receives metadata/ranges; watching/analyzing uploaded media is not implied. No acceptance render has been run.
