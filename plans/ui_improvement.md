# UI improvement plan

Status: shared visual refinement implemented and browser-checked on 2026-10-27. This covers presentation across existing pages; it does not claim that every populated, running or error state has been acceptance-tested.

## Objective and constraints

Make Vibe Director readable, calm and usable during long creative sessions. Preserve Ashu’s design foundation, all three themes, backend behavior, existing capabilities, saved drafts and selections. Improve composition and controls instead of replacing the application or its engines. `notes.md` and current stage plans remain authoritative for workflow requirements. No Git work, generation, provider calls or routine review agents.

The owner’s reported defects: cramped prompt boxes, dense or awkward messages, unclear buttons, weak spacing and page arrangements. The GPU notice demonstrated a concrete root cause: a generic flex notice placed several paragraphs and commands side by side, with tiny inherited type. Audit other notices for the same failure; do not assume every page is fixed by changing one global selector.

## Shared design rules

- Use existing theme tokens for surfaces, text, borders, focus, warnings and errors. No new palette. Maintain contrast in all three themes.
- Main form/message text defaults to 14–16 px with line height about 1.5; reserve smaller type for secondary metadata. Avoid tiny prose and dense all-caps technical labels.
- One clear page heading and one main action per task area. Put advanced settings and diagnostics in expandable sections; keep essential recovery instructions visible.
- Use consistent spacing: roughly 8 px between related controls, 16 px between field groups, 24–32 px between sections. Verify against actual content, not empty mockups.
- Commands get a full-width code row, wrapping or horizontal scrolling, and a copy icon button with an accessible label. Show Copied only after clipboard success; provide a manual-copy fallback on failure. Never execute a command by copying it.
- Messages stack a short title, what happened and what to do next. Keep tracebacks under details. Persistent problems use inline alerts; temporary confirmations use quiet status text. Do not erase useful errors before recovery.
- Buttons use plain verbs, consistent heights and visible focus/disabled/loading states. Explain why a necessary action is disabled and provide the next action. Icon buttons need labels/tooltips and comfortable targets (around 40–44 px).
- Prompt and chat fields need comfortable width and height, resize/expand support where appropriate, labeled inputs and a stable action row. Keep model selection, attachment and send controls grouped. Preserve selection-based micro-editing requirements from notes.
- Responsive panels must stack or collapse without squeezing prose into narrow strips. Long names wrap or truncate with full-name access. Preserve keyboard navigation and reduced-motion preferences.

## Execution batches

| Batch | Files / surfaces to inspect | Deliverable and acceptance |
| --- | --- | --- |
| 0 — Immediate warning | StatusPage.tsx, style.css | Stacked clock warning, readable command, copy feedback, expandable verification/undo. No hardware action. Implemented; focused browser verification required. |
| 1 — Shared controls | style.css, ModelSelector.tsx, MediaSourcePicker.tsx, SelectionToggle.tsx; existing message/button classes | Inventory actual selectors and consumers. Fix typography, spacing, buttons, file controls, messages and command rows at the smallest shared boundary. Preserve custom layouts; do not globally force every notice into flex or grid. Check themes and narrow widths. |
| 2 — Creative workspaces | StoryPage, ScreenplayPage, ProductionStylesPage, ProductionSetupPage, ImageAssetsPage, CharacterVoicesPage | Story has one main editor; graph/history secondary. Screenplay remains readable hierarchy. Assisted manual/Full setup remains after screenplay. Characters & Voices, Worlds, Frames retain separate tasks, large previews, adjacent prompts and clear generation controls. No standalone Prompts page reintroduced. |
| 3 — Chat and generation | App video-create/current-take surfaces, AceStudioPage, VibeEditorPage, MusicSoundPage | Consistent collapsible chat/right-panel arrangement; comfortable composers and readable replies; prompt/parameters grouped, progress visible, retake/next unambiguous. Preserve reference mapping, draft persistence, approvals, attachments and direct controls. |
| 4 — Media Prep and Search | MediaPrepPage, MediaLibraryPage and nested video/audio/image tools | Preserve nested tool pages; distinct voice/audio collections, search/sort/view controls, useful previews and clear import actions. Do not flatten tools into a generic asset grid. |
| 5 — Finish and recovery | StatusPage, DebugPanel, PerformancePanel, empty/error/loading states across pages | Diagnose in plain language; expandable technical detail; clear missing prerequisites and recovery action. Resolve overflow, inconsistent labels and keyboard/focus issues found in prior batches. |

## Low-token implementation packet for each batch

1. Read the relevant notes and page source. List actual defects with screenshot evidence, affected shared selectors and required preserved actions. Avoid a speculative rewrite.
2. Reuse existing components and tokens. Implement one coherent batch directly. No Luna workers. Sol review only at the previously agreed substantial milestone or a specific genuine blocker.
3. Verify changed interactions with focused mocked browser tests. Test copy success/failure, disabled/loading states or persistence only where touched. Reuse unchanged passing checks.
4. Inspect rendered output at desktop and a narrow width, with long realistic text and each theme. Check no clipping/horizontal page overflow, legible labels, message hierarchy, keyboard focus and touch targets. A test passing is not proof of attractive layout.
5. Save before/after evidence and a concise handoff listing what changed and what is still pending. Present one representative usable journey to the owner before propagating a contentious layout change widely. Continue independent work while awaiting feedback.

## Verification boundaries

Use screenshots and mocked UI flows without starting generation. The owner clicks generation/training for acceptance. Do not rerun the legacy hundreds of tests. Affected typecheck and focused UI checks are sufficient unless a changed producer/consumer requires another test. Final UI sign-off requires owner inspection of actual rendered screens; do not mark the whole app improved based on component tests alone.

## Current evidence

GPU notice repair: dedicated stacked layout, 14 px body, command row with Copy icon and feedback, secondary help/undo collapsed. Existing 2100 MHz policy and backend checks remain unchanged. Other batches are pending.

## Source browser correction — 2026-10-27 (pending)

Apply `media_selection_storage.md`'s owner correction to shared controls before judging this batch complete. The Characters & Voices screenshot shows truncated source labels, broken narrow toolbar text, a tiny search box, duplicated workspace controls and an empty result with no useful explanation. Replace that composition with source-first nested browsing: Workspaces → named workspace, Downloads → folders, repertoire/other collections → folders where present. Global sources must not inherit the active workspace filter. This is backed by the actual migrated file layout and registry reconciliation, not cosmetic category labels.

Preserve separate image/audio/video R2V containers; improve their browsers rather than merging them or adding extraction to incompatible slots. Add selection toggles and workflow-capacity warning dialogs/counters across consumers. Require a named workspace choice/create dialog where saving needs one. Verify desktop/narrow layouts, long names, keyboard navigation and all three themes. Implementation and focused browser tests remain pending; no code or data moves were made for this clarification.


## Implementation — 2026-10-27

`frontend/src/ui-refinement.css`, imported after the existing stylesheet by `main.tsx`, now provides the shared finishing layer. It uses Ashu’s existing quiet/grit/mixtape tokens. No engine, job, data, routing or selection logic was changed for this visual pass.

- Readable form and message typography, consistent controls, stronger focus outlines, themed file inputs and comfortable prompt/composer space.
- Consistent panel gaps and padding; workspace fields no longer stretch vertically beside the media browser. Controls wrap in narrow panes, including video workflow choices.
- Notices stack readable prose and keep their dismiss button separate. Menu containment was attempted; the owner’s populated-page screenshot on 2026-10-28 shows the profile panel still escapes the viewport, so that fix is incomplete. Main content clears the fixed bottom bar.
- Media Prep utility forms receive proper panel padding and field spacing; image-stage tabs wrap. Hidden upload inputs no longer force invisible horizontal page overflow.
- Restrained button hover/press feedback, panel reveal and media preview hover effects. Reduced-motion users get no added animation. CSS handles these simple effects; no GSAP dependency was added.

Verification: TypeScript passed. Three focused mocked Chromium tests passed for voice import/assignment/reuse, native dropdown opening, Full-mode assignment lock, R2V limits/draft retention and global download selection with explicit Add. Desktop/narrow route audits checked Story, Screenplay, production styles/setup, image stages, video, editor, music, Media Prep and Status. Final narrow checks at 390 px found no document-width overflow on Characters, Frames, Setup, Current Take, Utilities, Search and Status. Desktop top/middle/bottom scroll screenshots checked Home, Setup, Current Take, Utilities, Search and Status; all three palettes and reduced motion were checked.

Evidence stays in `/tmp/ui-before-*.png`, `/tmp/ui-after-*.png`, `/tmp/ui-final-*.png`; representative corrected video screenshot: `/tmp/ui-final-video-corrected.png`. These are temporary local evidence, not committed assets. Browser runs used separate contexts and did not change the owner’s palette or saved drafts. No generation, training or provider request was submitted.

Remaining: implement the owner corrections below, then obtain owner visual feedback and user-driven generation acceptance checks. Populated libraries, long model conversations and running jobs still need their normal real-world acceptance review; empty-state screenshots do not establish those states. The existing standalone Prompts route was preserved in this presentation-only pass; any removal remains a separate workflow change, as required by the stage plans.


## Owner corrections — 2026-10-28 (pending implementation)

The earlier finishing pass is incomplete. These requirements extend batches 1–5; they are not claims of completed fixes. Preserve all page contents, saved selections, clips and generation behavior.

### Spacing and containment audit

| Surface | Confirmed defect | Required correction |
| --- | --- | --- |
| Create Video | Linked-story title (`Trial 1 - The Scar · Fully automated`) and actions touch their card edges and the following section. | Pad the story card and separate its heading, description, action and next section. Let the card grow with wrapped text. |
| Current Take | Full-run information card has no internal padding. | Give run information and actions comfortable padding and spacing. |
| Characters & Voices, Worlds, Frames | Image-preparation status appears as a thin border hugging its text. | Use a padded, content-sized notice. Keep stage tabs separate. |
| Frames | Selected shot/frame description card lacks padding. | Keep description and controls inside a growing padded card. |
| Video Summariser → YouTube Download | Workspace/search labels touch controls; radio labels are detached; URL field is narrow; Find videos touches the next result panel. | Stack labels above full-width fields with about 8 px gap. Group each radio with its label. Make URL textarea use the available horizontal width. Separate actions and result cards by 12–16 px or more. |
| Screenplay | Director/model/reasoning/lessons card lacks padding. | Pad the card and group related controls. |
| Media Prep → Search | Upload card lacks padding. | Pad upload fields and separate their action row. |
| Status | Manual-result labels sit inline against selects/textareas. | Stack labels and controls with consistent gaps. |

Inspect other nested forms and populated states for the same defects. Prefer a shared component or narrowly scoped class correction; do not force every generic card into a new layout. Check top, middle and bottom scroll positions, long names, narrow panes and all three themes.

### Profile panel

- Opening Profile must keep the entire panel inside the browser viewport. The screenshot shows it clipped off the left edge inside the sidebar.
- Anchor it to the profile button, clamp its position and width to viewport margins, and avoid sidebar overflow clipping (use the existing overlay/portal approach where appropriate).
- Long content scrolls inside a bounded panel. Preserve existing profile controls, keyboard focus, Escape and outside-click dismissal. Opening it must not navigate away.

### Current Take: one large player

- Show one large video player. Remove the repeated full-size `Batch prompt … video` players underneath; retain every clip and its metadata.
- Put previous/next arrow buttons on the left and right sides of the main player frame. They browse all available generated clips, including batch outputs. Show the selected clip name and position/count; disable an arrow at the collection boundary.
- Browsing is independent of the existing **Next video** production action: arrows do not accept a take, advance the screenplay, submit a job or delete anything. Preserve Retake, acceptance, download and other existing actions for the selected clip.
- Pause the old clip when switching. Keep arrows accessible by keyboard, with descriptive labels and visible focus.
- The player must resize with the preview pane, its width control and the hidden-conversation state. Use available pane space and preserve the video aspect ratio with contain sizing. Portrait and landscape videos must remain fully visible, including playback controls, without being cut off midway. Verify native fullscreen as well.

### Batch details

- Put the batch prompt list and execution logs inside a disclosure, collapsed by default.
- Keep a concise batch status/progress summary visible. Required stop, pause, resume, retry or recovery controls must remain discoverable; collapsing logs must not remove those capabilities.
- Keep prompt text, per-item outcomes and diagnostics available when expanded. Do not mount an additional large video player per log item.

### Focused acceptance

Use existing saved clips and the populated batch shown by the owner; no new GPU generation is needed for these layout checks. Check zero, one and many clips; portrait/landscape playback; arrow navigation and selected-clip actions; pane width extremes; conversation hidden/shown; fullscreen; collapsed/expanded batch details; profile on multiple routes; desktop/narrow widths; all three themes. Record visual evidence in addition to interaction checks. Do not declare the whole UI finished solely because an overflow test passes.


### Consistent page gutters — owner approval, 2026-10-28

Use Create/Current Take as the spacing reference: one shared outer horizontal gutter for every page. Embedded tools (especially ACE-Step inside Media Prep) must not add another page gutter. Preserve comfortable internal card padding. Apply this across the three themes and when navigation or editor panes are collapsed. Implementation includes full-width YouTube fields, padded story/status cards, a viewport-contained Profile overlay, one Current Take player with viewing arrows, and collapsed batch prompt logs. Verification results are recorded in HANDOFF.md; generation behavior is outside this presentation change.

### Applied and checked — 2026-10-28

Implemented the gutter, card spacing, YouTube form, Profile overlay and single-player changes above. Batch logs start collapsed; viewing arrows are separate from production Next. Removed duplicate hidden batch rendering on Current Take. Final frontend build passed. Browser checks covered desktop/narrow layouts, all three themes, saved playable clips, arrow navigation, expanded preview and native fullscreen. No new media was generated. Evidence and the existing missing-story-media limitation are recorded at the top of HANDOFF.md. Further owner feedback on populated tool states remains welcome; this milestone does not mark the entire project complete.
