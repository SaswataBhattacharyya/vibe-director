# Optional storyboard-to-video pipeline

Status: storyboard preparation phase implemented and checked, 2026-11-04; complete autonomous film orchestration remains pending. Latest scene-based layout and manual-only FFLF policy govern implementation. Preserve existing Story/Screenplay, standalone Video Create, Media Prep and Vibe Editor workflows while adding this as an explicit user choice.

Prerequisite: preserve the implemented [Project Open/Save restoration fix](project_restore_fix_plan.md). Extend its checkpoint coverage for every new record and validate restoration before releasing the new pipeline.

## Product intent

Offer a complete path for users who want to plan a film shot by shot, find suitable footage in their own repertoire, generate missing images/video, review the storyboard, then assemble and render the result. A single project owns the screenplay/storyboard, source and generated assets, shot choices, prompts, edit decisions, music/audio choices, render and review history. The approved storyboard is the bridge between creative intent and production; the Backlot-inspired board exposes progress and review, and Vibe Editor remains the place to edit the assembled result.

“Storyboard” here means a production plan, not only a grid of pictures. Each shot carries a stable ID, story/scene context, visual intent, timing, continuity notes, candidate and selected media, generation mode (existing footage, image generation, text-to-video, reference-to-video, first/last-frame, or mixed), prompt/settings, audio/music intent, status and review decision. Keep source lineage and revisions so later edits do not silently rewrite a frozen generation request.

## Proposed user journey

1. **Choose a path at the project entry point.** On Home / New Project, after project selection, ask: “What are you making?” Offer “Create a storyboard and video” and “Create a video directly.” Keep Develop a Story available as a separate starting point. Do not bifurcate inside Video Create; it is already a direct generation page and should remain quick for users who do not want storyboard planning.

2. **Choose how to start.** In storyboard path, offer: start from a story/screenplay in the project; upload/import a script or screenplay; start from a brief/prompt; or start from existing footage/reference video. The user can enter directly at the Storyboard page from project navigation at any time. If there is no existing story, that page first asks for a brief/script or media; it must not require earlier Story pages.

3. **Prepare the script and scenes.** Reuse the current screenplay authoring and revision system. Turn accepted scenes/shots into stable storyboard cards, retaining source evidence, characters, locations, camera, lighting, mood, dialogue, sound and planned duration. Allow manual edits before searching or generation.

4. **Search existing media for each shot.** Search the project’s Video Repertoire and optionally Media Prep sources. Analyze newly added footage once: metadata and licensing/source details, duration and dimensions, sampled frames and visual embeddings; optionally speech transcript and audio cues. Search by a plain-language shot description, visual similarity/reference frame, transcript text, tags and filters. Show ranked candidates with contact sheets, preview, timestamps/usable ranges, source/provenance and confidence. User selects or rejects candidates per shot; weak matches allow query refinement or manual assignment. Do not silently treat a semantic match as approved.

5. **Choose what to generate for gaps.** For each shot, user can keep a sourced clip, generate a still, generate a T2V clip, use R2V with selected image/video references, use first/last frames, or leave unresolved. Provide shot-level generation controls that inherit project defaults but allow settings appropriate to that shot. Keep selected references attached to the shot. Include continuity checks for identity, wardrobe, location, visual style, aspect ratio and neighboring shots. Generation is explicit and submitted through existing engines/jobs with frozen inputs, durable progress, cancel/retry/recovery and normal GPU/provider guards.

6. **Review a complete storyboard.** Present ordered scene/shot cards and a compact timeline/filmstrip. Each card shows intended beat, chosen/generated media, prompt/mode, duration, audio/music cue, readiness/review state and any mismatch. Allow rearrangement, replacement, trims, regenerate, mark intentionally blank and approve. Changes create storyboard revisions; approval locks the exact shot/asset/prompt set for assembly. A Backlot-style production board is a view of these same saved records: stages, per-shot status, activity, decisions and eventual renders, not an independent database or a second source of truth.

7. **Assemble and finish the video.** Convert approved shot cards and selected media into an edit manifest (shot order, in/out ranges, transitions, overlays/titles, narration/dialogue, music/SFX, timing and output profile). Open that manifest in Vibe Editor for full manual editing. Use HyperFrames where its HTML/CSS/GSAP composition is suitable; preserve Vibe Editor’s existing native project/session/edit behavior and do not assume OpenMontage’s adapter is a drop-in. Render through the existing Vibe Director pipeline, then inspect final duration, streams, audio, black/frozen frames, shot coverage, and visual continuity. Show the final render and review results on the production board. The approved storyboard is an independent deliverable; video assembly is optional. For video delivery, publish the final approved/exported video; intermediate assets remain organized as project media.

## Page map and bifurcation

| Page / surface | Role in this pipeline | New or reuse |
| --- | --- | --- |
| Home / New Project | User choice: Storyboard → video, direct Video Create, or story development | Small entry choice; direct path remains unchanged |
| Story / Screenplay | Write/import story and create accepted screenplay revisions | Reuse existing pages and backend |
| Storyboard | Scene/shot cards, media search, generation choices, review and approval | New page; valid direct entry |
| Media Prep / Video Repertoire | Ingest, analyze and index local/source footage; search candidates from shot cards | Reuse and connect existing repertoire/media preparation capabilities |
| Backlot-style Production Board | Project overview: stages, each shot’s state, activity, decisions, outputs | New view or tab in storyboard/project; consumes same project records |
| Vibe Editor | Full timeline/composition editing of approved storyboard assets | Reuse; provide “Open in Vibe Editor” with edit manifest |
| Video Create / Current Take | Standalone prompt-first generation and job review | Keep independent; storyboard jobs can link to it internally |
| Project New/Open/Save | Persist all project content, choices, revisions and outputs | Reuse global project contract |

Earlier page-map proposal (superseded where amended by the 2026-11-04 extension below): use three main surfaces: (1) existing Home/project choice, (2) new Storyboard workspace with a stage strip and per-shot cards, and (3) existing Vibe Editor for detailed editing. Story/Screenplay and Media Prep remain optional supporting pages and are reachable when needed. The board can be the storyboard workspace’s overview tab rather than another separate app.

## Direct entry and required inputs

Users may open Storyboard directly. Required minimum to create a useful first board is **either** (a) a script/story file or existing project screenplay, **or** (b) a short brief describing topic, audience and intent. Existing footage is optional: without it, the user can still create a plan and generate media later. To search local repertoire, the user must choose an existing project/library folder or import footage into the project; no arbitrary filesystem scan without explicit selection. Reference videos, images, music, and character/voice references are optional. The storyboard page should explain which functions each supplied item enables.

For a user arriving with only footage: allow “Build a storyboard from these clips” by indexing/analyzing clips, surfacing candidate scenes and asking the user to confirm the resulting shot/story order. This is a distinct direction from script-first planning and should be explicit, not inferred.

## Data and handoff contracts

- Keep one stable project ID and stable scene/shot IDs across storyboard revisions where the creative entity remains the same.
- Store media as project asset records with content hash, source path/copy, provenance/license, analysis status and reusable transcript/frame indexes.
- Store per-shot candidate references separately from the chosen asset. Candidate search must never silently change an approved choice.
- A generated asset links to its shot, storyboard revision, prompt/settings hash and frozen job. Failed or retried jobs preserve history and do not duplicate or corrupt prior results.
- An approved storyboard revision generates an immutable edit manifest. Vibe Editor may create newer editable revisions; it must retain links back to originating shot IDs and assets.
- Save board activity from actual job/revision/approval events. The board derives stage status from authoritative job and revision records rather than maintaining shadow progress.
- Keep OpenMontage code as a reference/inspiration until a compatibility, license and dependency review proves selective reuse is appropriate. Prefer adapters around Vibe Director’s current Media Prep, repertoire, generation, project and editor services over importing its entire agent-first runtime.

## Decisions to settle during design

1. Does storyboard entry begin at Home/New Project only, or also become a first-class global navigation item? Proposal: both; project choice at Home and direct entry from navigation.
2. Which sources can be searched initially? Proposal: user-selected project/repertoire media first; add stock/open-web connectors only after provenance, licensing, download and folder-storage UX are agreed.
3. What does analysis include? Proposal: visual frame embeddings and metadata by default, transcript/audio indexing as an optional analysis pass; make coverage visible per asset.
4. Should every proposed shot require approval before generation? Proposal: user chooses per-shot or approves a batch; no automatic paid/provider/GPU work without the existing explicit action.
5. Does “first storyboard” generate images automatically? Proposal: no; first produce the plan and search results, then offer explicit image/video generation per shot or selected batch.
6. How do timeline edits flow back? Proposal: Vibe Editor owns detailed edit revisions; it can report timing/order changes to the board while preserving the approved storyboard as the source creative plan.

## Risks and safeguards

- Search quality depends on frame sampling, embeddings, transcripts, clip variety and query fit; show why a result matched and permit manual choice.
- Visual embeddings alone do not find spoken content. Transcript search must be separately indexed and labeled.
- Huge libraries need incremental analysis, deduplication by content hash, background indexing, cancellation and resumable progress.
- Sourced media needs provenance and license metadata surfaced before export.
- Scene-to-shot links, generated job lineage, original media, sessions, revisions and output-folder/project ownership must survive edits and project moves.
- Avoid rebuilding OpenMontage’s whole pipeline or replacing proven Vibe Director engines. Add a thin storyboard orchestration layer and reuse current services.
- Verify each stage end-to-end: ingest → analysis/index → candidate search → user selection → shot generation (existing footage/T2V/R2V/image) → approval → editor handoff → render → playback. Unit tests and mocked UI do not substitute for owner-approved real generation acceptance.

## Recommended first release scope

1. New optional storyboard path and direct Storyboard entry.
2. Brief/script/manual scene editing using current screenplay data.
3. Index and semantic-search user-selected Video Repertoire clips using sampled frames, with transcript indexing clearly optional.
4. Per-shot candidate selection and continuity/reference links.
5. Automated and assisted manual image/T2V/R2V generation through existing job services, with per-shot prompt editing and mode selection.
6. Ordered approval board and a stable edit manifest handoff to Vibe Editor.
7. One verified rendered output with visible provenance and recoverable job state.

Defer stock-provider expansion, automatic story inference from arbitrary footage and broad OpenMontage code import until this first vertical path is proven. Bounded Director automation is part of the requested pipeline; implement it incrementally against the same editable records as manual operations.

## UI, project setup and generation routes (2026-11-04)

These requirements extend the seven-step journey above. This remains a planning document; features described here are proposed behavior, not claims of current implementation.

### Visual consistency and layout

Reuse Vibe Director's current palette, typography, spacing, sidebar, cards, buttons, icons, status badges and focus/hover treatments. Use existing theme tokens and controls. The storyboard and production board must feel like part of the same application. Before implementation, identify the exact reusable components and theme files and prepare reviewable desktop and narrow-screen layouts using those components.

The initial page design is:

| Surface | Layout and controls |
| --- | --- |
| Home / New Project | Add **Storyboard to video** beside direct Video Create and story development. Keep New/Open/Save and the active project visible. |
| Storyboard header | Project title, saved/unsaved state, production type and style summary, storyboard revision and output-folder control. |
| Storyboard workspace | Compact stage strip: **Plan → Find media → Generate → Review & assemble**. Scene groups and ordered shot cards occupy the main area; selected-shot details and Director chat use a resizable side panel. Search/settings open in a drawer or popover without pushing the whole page down. |
| Production board | Overview tab in the same Storyboard workspace: stage progress, shot readiness, waiting decisions, active/failed jobs and final outputs. Selecting a status opens the affected shot or job. |
| Vibe Editor | Existing editor page receives the selected storyboard revision and edit manifest; retains its own editable revisions, sessions and approvals. |

This adds one main Storyboard page with a production-board tab, plus entry controls and connections to existing pages. It does not require one new page for every stage. The route names and component boundaries are to be confirmed against the current app shell before implementation.

### Project, production type and style connectivity

- Reuse the global New/Open/Save project flow. Save storyboard drafts, prompt revisions, selected references/ranges, job links, audio choices, board activity and editor handoffs with the project. Reopening restores the same state and pending review position.
- Direct Storyboard entry works from navigation. If there is no active project, offer New/Open project using the existing folder controls; if the project has no script, accept a brief or import on that page. Earlier Story pages are optional entry routes.
- Reuse **Production Type & Style**, including production type, visual style, directing style, reference media and the existing saved selection snapshot. Show a compact summary and **Review/change type & style** action with a return to the same storyboard.
- Feed the chosen production type/style into scene breakdown, shot suggestions, search intent, image/video prompts, pacing, audio direction and editor brief. Preserve factual content and explicit user direction when applying style.
- Freeze the selected setup with approved storyboard/generation revisions. Changing type/style shows the affected prompts and choices and offers an explicit revision/review action. Completed media and submitted jobs retain their original settings and lineage.
- Project-wide settings supply defaults; scene/shot overrides are visible and reversible. The UI must show whether a value is inherited or overridden.
- Output folder defaults inside the project with the existing editable path plus Choose folder override. Keep source folders, project storage and output destination clearly labeled.

### Shot cards, prompts and required actions

Each shot shows its scene/shot number, purpose, action, duration, selected media, generation mode, continuity notes, audio cue and current review/job state. Detailed camera, lighting and settings can live in the selected-shot panel to keep the board readable.

Provide controls to add, duplicate, reorder and remove scenes/shots; search or attach media; preview and trim candidate ranges; select/deselect references; edit prompt; ask Director to refine it; restore a suggested prompt; inspect prompt history; generate/regenerate; compare takes; accept/reject a take; approve selected shots; and open the assembled sequence in Vibe Editor. Removing an attachment or shot reference must not delete the source file. Actual file deletion uses the existing explicit deletion flow.

The prompt panel must show the exact editable generation text, selected image/video/audio inputs and their roles, shot mode, supported model settings and inherited style context. Director suggestions are reviewable changes with Apply/Discard. A changed prompt creates a new draft; it cannot rewrite a submitted job's frozen request. Mode changes validate the required inputs and explain missing references beside the relevant control.

Support multi-selection and clear selected counts for batch actions. Use labeled actions and accessible keyboard/touch equivalents. Preserve loading, empty, partial-analysis, failed-search, missing-file, save-conflict and unavailable-engine states, including a clear reason and recovery action when generation is disabled. Asset selection or drag/drop alone must not submit chat or start generation.

### After storyboard approval: choose how to generate

Offer two explicit options on the **Generate** stage. Both consume the same versioned storyboard and per-shot records, and both support a mixture of existing clips, T2V, R2V, first/last-frame generation and image-based shots. There is no requirement to use one generation mode for the whole film; a majority-R2V plan with a few T2V shots is valid.

| Route | User experience |
| --- | --- |
| **Automated clip generation** | Director prepares a run plan from approved shot content, chosen references, production type/style and settings. Show a reviewable summary of modes, inputs, missing assets and execution limits before **Generate approved shots**. The batch proceeds through supported dependency steps, using existing footage directly where selected and generating missing assets/clips where specified. Show per-shot progress, pause/stop behavior, retries and review results. |
| **Assisted manual clip generation** | User works shot by shot with Director help. Edit or refine prompts, choose media/reference roles and generation mode, review settings, then click **Generate this shot**. Compare takes and accept one, upload an alternative, or return to planning. Provide **Next unresolved shot** and preserve progress on navigation/reload. |

Allow switching routes for remaining work while retaining completed shots and their accepted takes. A batch must pin its exact storyboard revision, prompts and input hashes. Later edits mark affected pending work as needing review; they do not alter running jobs. Do not silently substitute engines, modes or missing references. Reuse durable jobs, retry/cancel/recovery, GPU admission/watchdog and provider execution guards.

Define automated run bounds visibly: selected shots, planned dependencies, retry limit, whether generated takes may be automatically selected under existing review rules, and where the run pauses for the user. Stop at unresolved choices or unavailable capabilities. Storyboard approval authorizes the creative plan; the explicit Generate action authorizes execution. Users may generate an approved subset while other shots remain drafts; final full assembly requires every required shot to be resolved or deliberately omitted.

### Audio, assembly and final editing

Keep dialogue/source audio, narration, sound effects and music as distinct creative roles in the plan. Let users import or generate suitable assets through existing audio tools and assign cues to shots or the whole film. Layered sound is required for this pipeline. Current Vibe Editor accepts source audio or one replacement soundtrack; the separate assembly service already validates and mixes timed audio tracks. Reuse and adapt that mixing logic into a shared composition contract rather than introducing an unrelated mixer. Richer fades, repeated cues, automation and shot-relative timing require explicit validator/renderer/UI extensions. The detailed specification below governs this integration.

After required shots are ready, present **Assemble preview** and **Open in Vibe Editor**. Automated assembly can prepare the ordered sequence, but detailed editing and render approvals must honor Vibe Editor's current brief and exact-plan clearances. The generated edit manifest retains shot IDs, selected takes/ranges, timing, transitions, titles and audio references. Changes in Vibe Editor create edit revisions; the original approved storyboard remains inspectable, with differences visible on return.

### Feasibility and implementation gates

The requested flow is coherent. Its difficult seams are project restoration, style changes, shot-to-job lineage, shared media search indexes, automated run recovery, mixed audio and editor import. A matching UI alone does not establish these capabilities. Before coding, trace these seams in the functionality audit and current source, perform a scoped blast-radius analysis, and identify reuse versus required extensions. Verify design interactions with browser tooling and verify the complete generated-media path through owner-authorized acceptance.

No clarification blocks this plan update. Design defaults are: one Storyboard page with tabs, direct entry through New/Open project, per-shot or batch approval, route switching for unfinished shots, and initial search of user-selected project/repertoire media. External stock search remains a later extension unless the user expands that scope.

## Comprehensive editing and Director integration specification (2026-11-04)

This section extends and resolves the earlier proposal. All stages remain accessible and editable. Stage labels describe progress, not locked wizard pages. Approval freezes a revision for execution; it never makes the creative project permanently read-only. Backend/frontend names below are proposed seams to confirm during implementation, not existing endpoints or verified runtime capabilities.

### One editable production, from brief to final film

Use the same project, shot identities and composition records throughout. The user can write directly, manipulate cards/timeline, or ask Director to make an equivalent change. Director must use the same validated operations as the UI, with no hidden alternative project or timeline.

| Stage | Editable content and controls | What Director can do when authorized |
| --- | --- | --- |
| Brief and setup | Story, audience, intended length, production type/style, references, format and constraints | Propose or revise the brief and suggest a breakdown |
| Screenplay and storyboard | Scenes, beats, dialogue, shot order, framing, camera, lighting, continuity, duration and notes | Draft scenes/shots, improve pacing and propose continuity fixes |
| Media discovery | Queries, filters, candidate ranges, reference roles, selections and exclusions | Search selected libraries, rank candidate ranges and explain choices |
| Storyboard preview / animatic | Still holds, rough clips, order, timing, temporary narration/music/SFX, captions and transitions | Assemble a rough timed preview and propose edits before expensive generation |
| Shot production | Exact prompts, mode, inputs, settings, selected takes and local clip edits | Generate approved dependencies, compare results and select within explicit run rules |
| Assembly and sound | Clip trims/order, speed, framing, supported effects, titles, transitions and layered audio | Prepare the cut, place cues, propose sound levels and resolve supported timing issues |
| Review and export | All edit decisions, output profile/folder, review notes and revision selection | Apply scoped feedback, render approved revisions and prepare a final review |

Each stage has Save, revision history and contextual Undo/Redo for committed editing actions. Undo creates/restores a draft revision; it cannot undo an external execution, delete original media or erase job history. Support autosaved drafts with a visible save state and explicit retry on failure. Do not overwrite unsaved edits during background job updates.

### Director control: assist or automate, changeable at any stage

Provide a persistent **Assist / Automate** control with scope **selected shots / scene / whole film**. Assist offers reviewable suggestions. Automate delegates the defined work within a visible run policy. Switching back to manual pauses future scheduling and preserves completed work. The user can keep editing drafts while a frozen run executes.

An automation brief records the objective, allowed operations, eligible shots, locked choices, search folders, permitted engines, output settings, retry/time/cost limits where measurable, automatic take-selection rules and pause conditions. Provide **Plan only**, **Run approved plan**, **Pause after current task**, **Cancel active work** and **Take over editing**, with precise explanations of what each stops. Resume reconciles completed jobs before scheduling anything again.

The run preview lists its dependencies: for example reference still → R2V → required enhancement/stitch → review → assembly → sound mix → final render. A task is complete only after its required output is verified and registered. Intermediate base/enhancement chunks do not count as final delivered clips. Existing clips skip generation; an image-only shot can remain a deliberate still hold.

Automation may choose and edit within approved scope, but must pause on unsupported tools, missing references, failed validation, exhausted retries, material scope changes or conflicting locked decisions. Explain the issue in the affected shot and offer an actionable fix. Search scores and automated quality checks are evidence, not guarantees of narrative or visual correctness. Do not silently replace a rejected take, change engine, broaden source folders or change approved output settings.

Preserve the Editor's current brief and exact-plan clearances in the initial integration. A single automation scope must not silently bypass them. An optional consolidated approval may be introduced only as an explicit, reviewed extension of the approval contract, with exact revision/tool/media coverage and tests; generation, editing and export authorization must remain attributable. Do not force repeated creative questions where the user already supplied the answer.

### Changes and downstream impact

Show a short impact preview for edits that invalidate later work, with **Apply to draft**, **Keep current take** and **Rebuild affected work** where applicable. Never regenerate the entire film by default.

| Change | Required response |
| --- | --- |
| Correct title, note or non-rendered label | Save draft metadata; no media regeneration |
| Change cut, trim, transition, caption or framing | Invalidate affected preview/render; keep generated source clips |
| Change duration or speed | Recalculate sequence timing and attached audio anchors; show collisions, insufficient handles and neighboring transition impact |
| Change prompt, reference, character identity or generation mode | Preserve current take; mark its compatibility for review; regenerate only explicitly selected affected shots |
| Change project style or recurring character/location | Preview dependent scenes, prompts and takes; allow scoped propagation and visible overrides |
| Replace a take | Preserve existing trim if valid; otherwise request range adjustment; retain old take/history |
| Edit storyboard after opening Editor | Offer explicit import/reconcile with a field-level difference preview; never overwrite manual Editor edits automatically |
| Edit timeline order/timing in Editor | Save edit revision and show board differences; apply selected changes back to storyboard only on user action |
| Change media on disk or move project | Verify identity/hash, offer relink, invalidate incompatible approved inputs; never silently substitute a same-named file |

Pin jobs to immutable input revisions and asset hashes. A pending task whose dependencies changed pauses or is superseded before submission. Running jobs may finish against their old revision; results remain available but are visibly associated with that revision. Prevent duplicate task creation with idempotent submission keys. Use expected-revision checks for conflicting saves and publish revisions atomically.

### HyperFrames during planning and after generation

Use a shared validated composition description for the storyboard animatic, individual-shot edit and finished sequence. Reuse the existing trusted JSON-to-HyperFrames adapter and FFmpeg preprocessing where supported. HyperFrames supplies timed visual composition; it does not perform semantic footage search, maintain story coherence or generate missing footage by itself.

Before generation, render a quick animatic from selected stills, candidate clips and temporary audio. Clearly label placeholders and temporary assets. After generation, replace placeholders with accepted takes while retaining shot IDs, composition timing and deliberate user edits; prompt for resolution when durations differ. Provide **Edit this shot** from each card, opening Vibe Editor with the shot context and a clear **Return to storyboard** action. A local edit produces a derivative linked to the original take; it never overwrites the source. Whole-film editing opens the same composition at sequence scope.

A shot may therefore have a generated/sourced original, an optional edited derivative and a selected version for the film. Avoid double-applying an effect when an edited derivative is reused: the manifest states whether operations are live or baked. Preserve source time versus sequence time, playback speed and transition overlap. Keep visual preview and final render driven by the same validated timing/effects data.

Extend supported operations deliberately. The current Editor supports sequential image/video ranges, captions, contain/cover, selected filters, speed/ramp and bounded transitions. Arbitrary multitrack visuals, keyframed overlays or new animation templates require actual schema, validation, adapter and UI work before appearing as usable controls. Director proposes supported edits or identifies the missing capability; provider-authored HTML/JavaScript must not become executable project content.

### Music, dialogue, ambience and SFX as editable timeline elements

Add a sound panel and timeline lanes for source/dialogue, narration, music, ambience and SFX. Lanes express creative roles; independently placed clip instances refer to original audio assets. The same sound asset can be used for several cues without copying its source file. Each instance stores a unique ID, asset identity/hash, source in/out, placement, gain, fades, mute, role and anchor. Optional loop and ducking settings are validated, visible edit decisions.

Support three anchor modes: linked to a shot offset, linked to an event/marker within a shot, or fixed to sequence time. Reordering a shot moves its linked cues; fixed film-level music remains fixed. A trim/speed edit remaps anchors through the source-to-sequence timing map and flags anchors that fall outside retained footage. Show the result before accepting ripple changes. A source-video speed change preserves the existing pitch-handling behavior; separate music does not change speed implicitly.

Provide import/search, preview, trim, move, duplicate, split, replace, mute/solo, gain, fade-in/out and loop-to-range where supported. Show waveforms with lazy loading, snapping and numeric alternatives. Avoid silent musical cuts: expose loop boundaries/crossfades and allow manual adjustment. Offer dialogue-aware music ducking as an explicit setting with editable amount/attack/release; retain manual gain overrides. Prevent clipping with a validated mix policy and report peak/loudness measurements; loudness targets depend on the chosen output profile rather than one universal preset.

Director can suggest music/SFX from the approved brief, use selected library material, or request generation through existing ACE/music/voice/Foley tools. An audio task retains its prompt/settings, model/source, output identity and review state. Missing sounds remain visible unresolved cues or intentional silence; never invent an asset or present text cues as mixed sound. Generated speech timing and lip synchronization are separate capabilities; do not imply automatic lip sync from adding narration.

Implementation reuse: `assembly.py::validate_assembly_audio_tracks` and `assembly_renderer.py::render_manifest` already support timed trim/gain mixing with source-preservation policies. Current constraints include at most 20 optional tracks and one use per audio asset. `vibe_editor.py::validate_plan`, `frontend/src/lib/editor-api.ts::EditorPlan` and `vibe_editor_render.py` currently expose a single optional soundtrack. Reconcile these contracts into versioned audio instances; do not remove limits without measured justification. Add fades, repeated instances, ducking and anchor mapping through focused extensions. Keep existing manifests readable and migrate only when explicitly saved as a new revision.

Use HyperFrames for timed visuals and the shared FFmpeg mix path for final sound. Preserve unmixed cue/track decisions alongside a derived mix so later edits remain possible. Previews may cache a low-cost mix; final export rebuilds or verifies the mix for the exact composition revision. Preview and export must agree on duration, overlap, mute policies and cue timing. Layered sound and editability are required acceptance criteria, not deferred merely because one existing Editor field is limited.

### Detailed UI and aesthetics

Use the current application theme, not a separate imported app shell. Before coding, inventory reusable cards, buttons, fields, media browsers, drawers, split panes and theme tokens from `frontend/src/style.css`, `vibe-editor.css`, `screenplay.css` and current pages. Preserve contrast, typography hierarchy and spacing; status must have text/icon meaning beyond color. Build desktop and narrow-screen mockups for the owner to review.

| Area | Specification |
| --- | --- |
| Project header | Title, save state, revision, style/type summary, output-folder summary and Assist/Automate scope. Overflow menu holds less frequent actions. |
| Navigation | Tabs **Storyboard**, **Timeline**, **Production**. Compact stage strip remains navigable; show blocked work without preventing draft edits elsewhere. |
| Storyboard canvas | Scene groups; shot cards with thumbnail/contact sheet, duration, selected take, mode and status. Add/reorder/duplicate controls, multi-select and keyboard equivalents. Grid/list view, sorting for discovery and explicit authored shot order for playback. |
| Inspector | Contextual tabs for Intent, Media, Prompt, Edit and Sound. Inherited settings are distinct from overrides. Advanced settings collapse without hiding errors. |
| Preview | Selected shot/scene/film playback, scrubbing, timecode, markers, preview-quality label and compare version. Range loops support checking cuts and sound cues. |
| Timeline | Compact animatic on Storyboard; detailed timeline on the existing Editor surface. Video/overlay/audio lanes, zoom, snapping, playhead and readable selection. Same revisions and operations across both. |
| Director | Resizable/collapsible panel, explicit selected scope, attachments and hover/focus removal, proposed changes with before/after and Apply/Discard, run activity and takeover controls. |
| Media search | Drawer using existing Search selection/view conventions; visual/transcript coverage, match range, source, preview, attach/select and rejected-candidate history. No toolbar expansion pushing the whole canvas down. |
| Production tab | Draft → needs media → ready → queued/running → needs review → accepted/exported, derived from actual records. Separate stale/blocked/failed indicators and relevant recovery actions. |
| Review | Comments attached to shot/timecode/revision; compare takes, accept/reject, resolve notes and inspect differences before propagating changes. |
| Export | Exact revision, profile, required-media readiness, sound policy, output path/Choose folder, collision behavior and explicit render/export action. Final playback/download plus optional project-save action. |

Keep one dominant contextual action: e.g. Find media, Generate selected, Review takes or Assemble preview. Batch actions show scope/count and eligible versus blocked items. Do not label an automation button merely “Go.” Make Pause/Cancel available without making destructive actions visually dominant.

On narrow screens, switch the inspector/Director to sheets or tabs and preserve the preview/editing context; avoid compressing all panes into unusable columns. Support keyboard reordering, accessible form labels, focus management, reduced motion and touch-accessible removal controls. Show skeleton/loading/empty states, partial search results, offline/reconnecting state and save failures. Preserve focused text inputs and scroll/selection when job progress refreshes.

### Backend/frontend connection and persistent model

Reuse the existing HTTP dispatcher, service layout, asset registry and durable jobs. Add a scoped storyboard orchestration service rather than replacing engines or adding a separate application/database. Determine exact storage placement from current project APIs before implementing; save/open must include all new records and handle externally referenced media explicitly.

| Record | Authoritative content / relationship |
| --- | --- |
| Project | Existing identity, folder, settings, production style snapshots and project-specific Director/Editor memory |
| Storyboard revision | Scene/shot IDs, creative intent, inherited setup and per-shot overrides; links to accepted screenplay revision |
| Shot media selection | Candidates, ranges, reference roles, accepted take/edited derivative and approval provenance |
| Composition revision | Ordered clip instances, source/sequence timing, transitions, effects, titles, audio instances and output profile |
| Director proposal | Scoped operation list, base revision, explanations, validation and apply/discard status |
| Production run | Frozen plan, policy/authorization, dependency tasks, existing job IDs, attempts and recovery state |
| Analysis record | Asset hash, analyzer/model version, coverage, timestamped search ranges and index version |
| Render/export record | Frozen composition, input hashes, job, verified output identity and publication/review state |

Use independent clip/audio instance IDs so the same asset can appear repeatedly. Do not confuse application project identity with an Editor session or legacy internal workspace ownership. Keep those relationships explicit internally while presenting the user with Project and Output folder.

Proposed operations: read/update storyboard with expected revision; create/apply Director proposal; search candidate ranges; select media; create/update composition; preview impact; approve exact revision; plan/start/pause/cancel/resume run; inspect task/job progress; render/export verified revision. Use the existing API conventions for errors and progress rather than inventing a second transport. Frontend typed contracts must match backend validation, including capability and missing-input reasons. Show server-authoritative save/run states; optimistic UI must roll back or surface conflicts.

Current integration points to trace before coding:

- `frontend/src/App.tsx`, `ProductionStylesPage.tsx`, `StoryPage.tsx`, `ScreenplayPage.tsx`: routes, entry points, setup and screenplay lineage.
- `frontend/src/MediaPrepPage.tsx` and `backend/story_builder/services/video_repertoire.py`: ingestion, analysis jobs, searchable records and asset registration; confirm actual semantic-index coverage and timestamp accuracy before adding search promises.
- `frontend/src/VibeEditorPage.tsx`, `EditorWorkspace.tsx`, `frontend/src/lib/editor-api.ts` and Editor CSS: composition editing, session restore, approvals and shared media selection.
- `backend/story_builder/services/vibe_editor_api.py`, `vibe_editor.py`, `vibe_editor_render.py`, `editor_effects.py`: validated operations, trusted rendering and capability reporting.
- `backend/story_builder/services/assembly.py`, `assembly_renderer.py`, `frontend/src/AssemblyPreviewPanel.tsx`: accepted-take selection, snapshots, layered audio and verified publication.
- `backend/story_builder/services/projects.py`, `output_destinations.py`, `frontend/src/lib/project-state.ts`: project persistence, browser state, source relinking, destination freezing and export.
- Existing video/image/audio generation adapters, ledgers and worker guards: confirm exact functions during blast-radius analysis; retain current request normalization, required enhancement/stitch stages, cancellation and retry behavior.

### Delivery sequence and acceptance

Build one complete editable vertical path first, then expand it. A phase is complete only when frontend actions reach backend persistence/execution and survive reopen; a mock UI alone does not finish a phase.

1. **Source and design validation:** scoped blast radius, relevant audit checks, graph coverage, exact API/record map, existing-license review, and desktop/narrow layouts. Identify migrations and consumer compatibility before changing shared schemas.
2. **Editable project/storyboard:** direct entry, setup inheritance, shot IDs, draft history, autosave/conflicts and folder restoration. Existing workflows remain usable.
3. **Discovery and animatic:** local search, explicit ranges and references, still/clip placeholders and shared timing model. Preview with temporary sound; no unnecessary regeneration.
4. **Shot production:** mixed modes and assisted manual generation, edited derivatives, accepted-take lineage; then bounded Director orchestration over those same operations with durable pause/resume/takeover.
5. **Connected Editor and audio:** versioned composition import/reconcile, shot editing and full sequence editing, repeated timed sound instances, mixing/fades/ducking, reversible choices and consistent preview/export timing.
6. **Final production:** dependencies and review gates, verified enhancement/stitch completion, scoped regeneration, final assembly/export, project reopen and revision comparison.

Focused acceptance scenarios:

- Start from a brief, script or existing project; direct Storyboard entry restores the same project/style/memory.
- Create a board containing sourced footage, an image hold, R2V, T2V and first/last-frame shots; select timestamped media and verify required inputs at the control that needs them.
- Edit at every stage, including after approval/export; retain old revision/takes and rebuild only affected work.
- Preview an animatic, edit a shot through HyperFrames, replace it with generated media and return without losing timeline decisions.
- Reorder/trim/speed-change a shot with dialogue, music and repeated SFX; verify shot-linked versus fixed cues, transitions and final audio timing.
- Compare manual and Director-applied equivalent operations; both create valid revisions using the same backend checks.
- Pause/take over/resume automation; simulate restart, lost progress connection and duplicate submission; no duplicate jobs or hidden repeated generation.
- Edit a draft while a job runs; the job keeps its frozen inputs and its result is correctly labeled against the older revision.
- Fail a generation/enhancement/mix/render step; recover with retained successful dependencies and no early publication of intermediate clips.
- Save/open or move a project, relink missing assets, preserve original files and restore composition/audio/run state.
- Verify browser interactions, keyboard/touch controls, compact popovers, disabled-action reasons and narrow layouts.
- Run schema/service tests, CPU synthetic-media tests for timing/mixing/stitching, and separate owner-authorized real generation/render acceptance. Report which evidence actually ran; do not equate mocks with generated-media readiness.

No implementation or media generation is authorized by this planning document alone. No blocking clarification is required to update the plan: the governing defaults are editable stages, bounded automation with takeover, shared validated records, shot-scoped rebuilds, existing aesthetics, project ownership and a fully editable sound/composition path.


## Approved planning extension: screenplay direction, shot frames and standalone storyboard — 2026-11-04

This section incorporates the latest user request and supersedes conflicting earlier page-count, deliverable and stage-order proposals. It authorizes planning only. Existing working tools remain available; implementation must use a scoped blast-radius review before changing shared contracts.

### Outcomes and navigation

Provide two new, distinct pages: **Frame per shot**, followed by **Storyboard**. Retain **First & Last Frames** as an optional supporting page and **Worlds** as an optional preparation stage. A storyboard is a finished comic-like product containing ordered images, shot descriptions, dialogue and optional narration/captions. It can be saved/exported without generating video. Continuing into video is a separate action.

Suggested navigation: Production Type & Style → Story / Screenplay → Production Setup → optional preparation pages → Frame per shot → Storyboard → optional Video Production → Vibe Editor / final output. This is navigable progress, not a mandatory wizard: direct entry, existing media, existing accepted project work and skipped stages remain supported. Keep Frame per shot immediately before Storyboard in navigation; selected first/last preparation is a supporting dependency before a shot's FFLF video job, not a mandatory interruption between those two pages.

| Surface | Planned behavior |
| --- | --- |
| Screenplay | Whole-screenplay Director chat plus existing specific field/shot edits; editable Image/Video classification, duration, continuity and production intent |
| Production Setup | Deliverable choice, stage inclusion, manual/auto ownership, readiness, per-shot routing preview and dependency explanations |
| Worlds (optional) | Approved location references, variations and continuity anchors; skipping it permits supplied/per-shot backgrounds |
| Frame per shot (new) | One editable representative composition per included shot; character/background references, prompt, candidate versions, reuse/upload/generate, approval and scoped batch actions |
| First & Last Frames (optional, existing) | Explicit ordered endpoint roles for selected FFLF shots; reuse an approved representative image as first frame where appropriate, with an independently prepared last frame |
| Storyboard (new) | Scene groups and ordered comic panels with approved image, description, dialogue, captions, shot number and timing; editable layout/text, revision history, preview, standalone export and Continue to video |
| Video production / Current Take | Per-shot T2V/FFLF/R2V execution or still-image preparation, durable progress and accepted outputs |
| Vibe Editor | Existing shot/sequence editing plus planned composition and sound extensions; assembly consumes selected stills and accepted clips |

The storyboard representative image is not automatically both endpoints of a video. A two-frame pair is not automatically a storyboard panel. Both may reference the same underlying asset with distinct roles, avoiding duplicated files and lost lineage.

### Optional stages and control ownership

In **both Fully automated and Assisted manual**, expose independent inclusion toggles for World building, Frame per shot, Storyboard and First & last frames. Offer an explicit **Storyboard only**, **Storyboard + video**, or **Video only** deliverable choice. Selecting a storyboard deliverable enables the storyboard stage and requires a usable image per included panel; it may come from existing media, upload, an extracted source frame or generation. Skipping frame generation must not mean skipping panel images.

In Assisted manual, each enabled stage has **Manual / Director auto** controls, separate from Enabled/Skipped. Manual allows direct prompt edits, Director suggestions, media selection and user-triggered generation; it does not mean editing without assistance. Auto delegates decisions/execution within the approved scope. Disabled stages have neither pending work nor automation obligations. Fully automated defaults enabled stages to Director auto; choosing manual takeover exposes a visible pause/review checkpoint and makes the remaining run visibly mixed-control, rather than claiming it remains unattended.

Persist stage choices, inherited defaults and shot overrides per project/setup revision. Show effective settings and reasons on each shot. Stage switches do not delete approved assets or historical results. Per-shot overrides may reuse/supply required references even when a project-wide preparation stage is skipped.

Dependency rules must be explicit:

- Skip Worlds: use supplied references or shot-specific backgrounds; do not require a world master solely to unblock a job.
- Skip storyboard: direct video production still works and does not create a hidden storyboard approval gate.
- Skip first/last preparation: T2V/R2V/image routes still work. FFLF is valid only if both endpoint images are supplied/reused; otherwise offer enable preparation, supply images or change route. Never silently turn the stage back on.
- Storyboard only: generate/prepare necessary stills and export the board; do not enqueue video, LTX or final film rendering.
- Video only: generated references are prepared only where the selected route needs them; no mandatory panel generation for T2V.
- Required selected workflow unavailable: retain the creative plan but mark execution blocked with the actual reason. No silent route/model substitution.

### Screenplay-wide direction and classification

Add a project-persisted common Director chat on Screenplay, scoped to the whole screenplay by default, with optional scene/shot selection. Keep specific edit chats separate. A request such as “classify suitable shots as images and make those still holds two seconds” produces a validated change proposal showing affected shots and before/after fields. Apply all/selected or discard; create a new saved revision, preserve evidence and prior acceptance history, and require acceptance of the changed revision before production. Explicitly authorized automation may apply proposals within scope, using the same validation and revision APIs.

Separate **presentation: Image / Video** from **production route: existing media / image preparation / T2V / FFLF / R2V**. A fixed camera with moving people is Video; do not equate static camera with still image. Keep an explanation for Director suggestions and manual overrides. Image shots have an editable still-hold duration; support the user's requested two-second policy without imposing it retroactively on every existing project. Video duration must respect actual workflow capabilities. Dialogue that exceeds the proposed hold requires an explicit timing choice or split; do not truncate speech automatically.

Backend schema, provider output schema, frontend types, local recovery, revision validation, prompt generation, setup, planners, scheduling and assembly all need compatible changes. Legacy shots remain readable with their prior behavior; do not silently reclassify or rewrite accepted historical screenplays.

### Characters, backgrounds and composition

Reuse approved character references across shots; create them once per deliberate identity/wardrobe variation, not once per panel. Use an existing source image or current text-to-image workflow to create the initial reference; Qwen Edit requires valid image input(s) for editing/composition.

For every shot, resolve a suitable background. Reuse an approved background when unchanged; create a Qwen Edit variation for a changed viewpoint, framing, lighting or scene state. Where supported, reference the approved location master alongside the relevant prior background to limit drift. Link continuity dependencies by stable identity and asset hash, not simply the previous array position. Skipping the Worlds page does not forbid continuity; it means there is no mandatory separate master-building stage.

Compose approved character/background references into the representative shot image using supported Qwen Edit inputs. Separate editable prompts for character reference, background variation, shot composition, endpoint preparation and video motion. Preview input roles, inherited production style, source media and missing references. Preserve original/reference images and derivative ancestry. A changed upstream reference marks only dependent outputs for review; it never silently regenerates a whole sequence.

### Per-shot route decisions and prompt contracts

| Route | Inputs and output | Prompt focus |
| --- | --- | --- |
| Image preparation | Suitable existing/sourced still or generated composition → still panel/sequence hold | Appearance, composition, identity, background, lighting; no invented motion requirement |
| T2V | Text and supported settings → video | Self-contained appearance/location, action, timing, camera and supported audio |
| FFLF | Explicit first + last images, text and supported settings → video | Transition/action between endpoints, continuity and timing |
| R2V | Valid role-labelled references and text → video | Reference purpose, identity/location continuity, intended motion and camera |
| Existing media | Approved image or timestamped clip range → panel/sequence selection | Search/selection intent and edit instructions, rather than unnecessary generation |

Assisted users select routes per shot or apply a batch default, then override. In auto, Director proposes/chooses per shot from classified intent, available assets, continuity, readiness and approved scope. Freeze resolved routes, prompts, references, settings and dependencies in the run plan before scheduling. Storyboard images can guide an R2V job or become FFLF first frames when explicitly assigned. Keep video-motion prompts distinct from panel/comic text; spoken dialogue is an explicit audio decision, not an instruction to paint text into a generated image.

### First/last-frame gating: current source evidence

`backend/story_builder/services/production_fl2va_capability.py` gates manual FFLF availability on local files, graph validity, ComfyUI nodes/connectivity and an opt-in feature flag. Automatic execution additionally requires a successful exact-contract, hash-verified video+audio smoke artifact. This is separate from preparing two still images. This planning pass did not query live capability or start a render, so it does not claim the workflow is currently available or blocked.

`production_setup.py` currently restricts workflow choice and stage skipping by mode; `production_image_workflows.py` contains full-mode image-generation restrictions. Audit the entire scheduler/admission path before extending automation: the requested stage controls cannot be implemented by frontend toggles alone. Preserve real readiness checks, GPU/provider guards, endpoint ordering, verified final publication and enhancement/stitch requirements. Unsupported/missing evidence must be shown at the affected route, rather than disabling unrelated storyboard or image preparation.

### Storyboard UI, export and project persistence

Use the existing purple palette, gold primary actions, typography, cards and compact controls. Frame page: scene/shot list or grid, large selected image, reference/prompt inspector, generation history and scope-aware Director panel. Storyboard page: comic/page preview, ordered panels, editable description/dialogue/captions rendered as layout text rather than baked into generated images, optional timing labels and scene breaks. Support reordering, panel image replacement, per-panel edits and whole-board suggestions. Provide accessible controls, narrow-screen layouts and precise disabled-action reasons.

Planned standalone exports: printable PDF and image pages from the same validated layout, plus project-linked editable storyboard data. Implement export renderer and publication verification explicitly; these are new capabilities, not assumed current support. Comic dialogue placement, typography, page size and text overflow need preview and validation. Video continuation consumes the saved shot/media records, not exported comic pages or flattened text overlays.

Save/Open includes global chat/proposals, classifications, stable shot IDs, setup toggles/ownership, routes, continuity links, frames/endpoints, storyboard layouts/text/revisions, selected assets, run history and export references. Extend project snapshot table/media enumeration and restore tests. Fresh-browser reopening restores both new pages and their respective project data. Shared repertoire indexing remains separate from the project's owned checkpoint content.

### Implementation sequence and acceptance additions

1. Trace schema/ledger, UI, generation admission, automated scheduler, prompts, assets, Editor/assembly and project-save consumers. Refresh/check graph coverage; save verified scoped blast-radius findings. Check relevant audit contracts and licenses before reusing outside code.
2. Add compatible shot classification and whole-screenplay proposal/revision flow, with project restore coverage.
3. Extend setup with deliverables, enabled stages, independent control ownership and per-shot route/dependency validation. Retain legacy setups; version new behavior rather than reinterpreting old flags.
4. Implement Frame per shot and optional endpoint/world connections through existing jobs, reference lineage and prompts.
5. Implement independent comic Storyboard page, editable layout, approval and verified standalone exports.
6. Connect mixed still/video execution and assembly, followed by scoped auto orchestration, pause/takeover/recovery and sound/timing behavior from earlier sections.

Acceptance must include: storyboard-only never queues video; skipping Worlds still permits suitable shot backgrounds; skipping generated frames with supplied panel images succeeds; missing panel images explain required input; FFLF without supplied endpoints is blocked only for that shot; auto never bypasses capability/smoke checks; still images hold for two seconds when requested and skip video/LTX; mixed routes use correct prompt/input contracts; manual controls and Director changes produce the same validated revisions; long dialogue timing conflicts are visible; upstream edits preserve old takes and flag only dependents; all new records/media restore through project Save/Open; legacy accepted screenplays and unrelated standalone tools remain unchanged.

No blocking clarification is needed for this plan. Governing interpretation: a storyboard is an optional independent deliverable; selected outputs imply required assets but never imply mandatory generation; Director chooses only supported routes within authorized scope; optional preparation and runtime capability are separate concepts.


### Storyboard layout clarification — scene-based reading view

The user's storyboard is a scene-based two-column reading view, not a requirement for comic speech bubbles or a separate text panel per shot. Each scene forms one section. The **left column** contains a coherent combined description of the scene, its action across all shots, and ordered speaker-labelled dialogue/narration. Retain shot markers where useful to associate text with images. The **right column** contains the corresponding shot images in authored order, labelled by shot number. For a four-shot scene, show one combined scene text section on the left and all four corresponding images on the right; do not merge the images into one generated picture or discard shot identities. On narrow screens, stack that scene's text and images while preserving associations. Editing the scene summary must not silently rewrite the underlying shot action or dialogue; offer explicit propagation when requested.

Earlier references to “comic panels”, “panel images”, “comic dialogue placement” or “comic/page preview” mean these scene-associated shot images and the scene text/image layout. Speech bubbles and text over images are not required. Printable/PDF/image-page exports must preserve this scene grouping, text/image association and readable overflow/pagination; the editable project retains individual shots and image assets.

FFLF has two separate prerequisites: (1) creative inputs—one assigned first frame and one assigned last frame for each FFLF video shot; (2) runtime readiness—the actual engine, nodes, models, feature flag and, for automatic execution, verified exact-workflow render evidence. The optional First & Last Frames preparation stage may be skipped if the two images already exist and are explicitly assigned. A storyboard's single representative shot image can supply one endpoint; it does not supply the other endpoint automatically. Missing endpoint inputs or runtime capability block only the affected FFLF execution, not storyboard preparation or independent image/T2V/R2V work. Current live FFLF readiness remains unverified in this planning pass.


### Authoritative FFLF policy correction — user clarification

This policy supersedes earlier ambiguity about whether Director auto may choose FFLF. The owner confirms models/nodes are ready. The reason for pausing FFLF automation is the current quality of FFLF image preparation, not missing infrastructure. This planning pass did not independently retest runtime readiness.

- Keep existing FFLF image preparation and video generation available for explicit manual user choice. Do not remove the page, engine, assets or saved endpoint assignments.
- For now, exclude BOTH FFLF endpoint-image generation and FFLF video generation from every Director-auto scope, including Fully automated and automatically controlled stages/shots in Assisted manual. Existing endpoint images do not override this temporary policy.
- Director auto routes eligible work through image preparation/still output, T2V, R2V or existing media, according to the shot and approved scope. Ordinary Frame per shot images and storyboard preparation remain available; they are not FFLF endpoint preparation.
- Explicitly selected manual FFLF work remains manual. An auto run encountering a manually assigned FFLF shot must show a manual checkpoint or ask for an explicit alternative; never silently submit it or replace its route.
- UI explanation: “FFLF automation is paused while endpoint-image quality is improved. Available manually.” This is a quality policy, separate from ordinary execution validation.
- Implement a single shared orchestration/admission policy for FFLF automation, so route planning, setup eligibility and resumed runs agree. Preserve historical records and frozen requests; do not reinterpret completed jobs. Do not cancel or mutate existing active work incidentally.
- Re-enable FFLF automation only after an explicit future policy change following image-quality improvement and appropriate acceptance. Do not automatically re-enable it merely because models/nodes are present or a readiness check passes.

Acceptance additions: auto planners never choose FFLF; auto submission/resume cannot execute FFLF endpoint or video tasks while paused; manually requested FFLF remains usable; non-FFLF shot-image preparation still works; the later enablement switch can restore automatic eligibility without rewriting legacy project data. No blocking clarification remains.


## Implementation checkpoint — 2026-11-04

Implemented: whole-screenplay Director proposals with selective review/apply; Image/Video classification and duration; project-linked Frame per shot and scene-based Storyboard pages; explicit optional stages and Manual/Director ownership; per-shot character/background/image preparation through existing image jobs; automatic missing-frame preparation with saved request recovery; manual-only FFLF quality policy shared with legacy automatic admission; project checkpoint/restore; embedded-image HTML export and browser PDF printing; saved-shot Video handoff; ordered existing-media handoff into Vibe Editor without overwriting existing edits.

The new UI inherits the studio palette and uses spaced cards, responsive columns, labelled controls and recoverable unsaved edits. Live trial 1 scar reads its accepted screenplay and 22 scenes without rewriting the owner's project. Existing screenplays remain compatible.

Validation and bounded blast-radius/code review are recorded in [STORYBOARD_IMPLEMENTATION_REVIEW.md](../audit/STORYBOARD_IMPLEMENTATION_REVIEW.md). Focused backend, image workflow/admission, build and six browser interaction checks passed. Thirty source citations passed the bundled verifier. No provider/GPU generation was run. Real output quality is still owner acceptance work.

Remaining implementation from this larger plan: brief/media entry without a saved screenplay, semantic candidate search, durable server-side mixed still/video orchestration and automatic video adoption, complete character/background dependency tracking, timestamped clip ranges, music/SFX/dialogue scheduling, and autonomous final assembly/publication. Current Fully automated controls govern frame preparation and Director planning; they do not yet run a complete film automatically. Per-shot Video continues through the existing owner's Generate action. Standalone raster-page export is pending; native PDF rendering is not implemented.

A broader R2V suite is not green (6 failures/4 errors). The captured baseline reports the same ten failing test names, but this does not prove all unrelated workflows ready. Preserve workflow/version/hash/smoke guards and resolve those tests separately; never loosen acceptance to hide them.


### Conversational screenplay Director — implemented follow-up

Send message now provides ordinary discussion with earlier user/Director turns as context. Discuss and refine understanding first, then choose Prepare agreed changes and Apply selected changes. Project save/open retains the discussion across screenplay revisions. Thinking/loading/preparing/saving states show a small animated icon; shared tool Director chat also has a thinking indicator. Preserve source evidence and per-field edit chats. Existing shot fields can change; automatic insertion/splitting of shots still requires a separate schema/lineage extension.

Verification: 12 backend checks, seven browser interaction checks and production build passed. Live chat loading was checked without a provider call; model response quality remains untested.


### Prompt Preparation conversation and teachable guidance — implemented

The Prompt page now supports project-owned chat with history and thinking animation, explicit Prepare agreed changes, selective review/apply, and the existing Save shot prompt drafts boundary. Character and background briefs are visible and editable beside the discussion, linked to canonical source targets and adapted on the image pages. Teaching is explicit: Draft learning rules → review → Save selected rules. Saved scoped rules guide future shot/image drafting and assisted clip planning with the configured provider; SKILL.md export makes them portable. Project checkpoints preserve rules, briefs and history. Older frozen work remains unchanged.

Focused checks and bounded code/impact review are in `audit/STORYBOARD_IMPLEMENTATION_REVIEW.md` under Prompt Director. Whole-app regression health and real model/media quality remain distinct from these checks. Per-shot background dependencies and complete automated assembly remain pending as stated above.
