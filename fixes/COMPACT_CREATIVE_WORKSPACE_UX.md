# UX05–UX08 — Compact, functional filmmaking work surfaces

**Status at 603b1fcb (2026-11-06): planned, not implemented.** Review the user's Characters & Voices and Current Take screenshots, source app layouts, fixes/REFRESH_REVIEW_2026-11-06_603b1fcb.md and media architecture. Keep the existing dark palette and left sidebar, but establish a **visual hierarchy adapted to the narrower right-hand workspace**.

## North star

Vibe Director is a creative app with a Codex-like agent, not a dashboard with another dashboard inside it. A page should answer (1) *What am I making/reviewing?*, (2) *What action should I take now?*, (3) *Where do I find more options?*

One primary task on screen. Secondary metadata/features remain reachable through small controls, not removed. Avoid all-day form walls, forced steps, duplicate titles, nested three-column layouts, stacked full-size destination/configuration cards, repeated model pickers, and showing both a dense form and a giant inactive info panel as coequal content.

## Global layout and system design

Outer layout already provides Left Nav | Director | Right Work surface with independent collapse (UX01 implemented). That is the **only app-level multi-column system**. Within Right, default to **one responsive main canvas** (max readable width, centered task, no horizontal scrolling). A second inner column is acceptable only in an expanded/right-pane-full-width mode on wide screens where it genuinely helps side-by-side editing. Otherwise use toolbar-triggered drawer/overlay, tabs or collapsible section.

**Reusable toolbar system**, shared across pages:
- Upper-left page title + one-line context (e.g. “Lion_mouse / Scene 1 / Lion”); compact current asset/shot status.
- Primary action (Generate / Review / Apply / Accept), placed near relevant preview.
- Icon cluster with accessible labels/titles/keyboard shortcuts: Media, References (count), Workflow details, Output location, History, Settings, More. Text captions may display until breakpoint; never icon-only with no accessible name/tooltip.
- Optional status chip with actual workflow state (Ready / Queued / Rendering / Failed / Needs review), not a generic animated spinner.
- Right area uses consistent 4/8px spacing, min target 40–44px on touch, focus states, no overlaps/footer clipping and consistent cards.
- Desktop 1440×900, 1280×720, tablet ~900 and mobile 390 must remain usable. Distinguish collapsed panes from independent page tabs. Resizing chat should not reset page forms, media players, or job identity.
- Progressive disclosure: closed Advanced controls, technical JSON/logs, code workflow details, raw hashes/IDs and export folder permissions; error/recovery and missing prerequisites must always be visible. Empty/loading and permission-blocked states must be obvious.

## UX05: Characters & Voices / Scene Backgrounds / image generation

**Source:** ImageAssetsPage.tsx (~692 output, ~694 workflow, ~698 folder browser, ~699 old chat; ~717 EditorWorkspace) and its CSS. Both screenshot and current code show a double split: Director | “Generate an image” | another permanent panel with Output folder / Workflow details / references / old chat.

**Default desired hierarchy inside Right:**

    [Characters & Voices]             [Media] [Refs 0/3] [Output • project/…] [⚙]
    [Character target: Lion ▼]     [Image model: Z-Image ▼]
    [Prompt (editable; compact)]  [1 / 4 / 8 candidates]
    [Selected references chips / thumbnails]
    [Generate image]
    ──────────────────────────────────────────────────────────
    [Candidate gallery + preview, Accept/Use/Retake actions]
    [Advanced controls ▾] [Workflow details ▾] [History ▾]

For Scene Backgrounds, replace character target with base location and scene condition; no new separate generator. For first/last frames, preserve exact role and source scene/shot model. Keep character voice assignments reachable under their own task section; do not mix audio enrollment with the image prompt.

**Implementation:**
1. UX04 image prompt proposal parity: wire central Director chat to existing prepareImagePrompt and review/Apply, while retaining prompt snapshot/knowledge; then remove ImageAssetsDirectorChat's secondary transcript/form. Do not simply hide it in CSS.
2. Flatten image-assets-specific EditorWorkspace wrapping. Existing image creation and candidate controls should remain mounted. Replace permanent imageSidePanel with a single toolbar Settings/Output/Media popover/drawer or accordion; leave a lightweight media/reference chip tray in the main canvas. EditorWorkspace.tsx is still used by TRELLIS and parts of Media Prep: **do not delete or globally change its behavior** to fix Image Assets.
3. OutputDestination becomes compact default summary (UX07). Workflow details use a small info icon/button with a description popover, version/readiness and full technical details under Advanced. Accessibility: aria-label and keyboard close/focus return.
4. Unify media and local folder pickers via MED01, but keep actual generation form, candidate management, prompt editor, scene background variant workflow, saved references and selected-image acceptance. Do not remove workflow readiness checks or "assisted manual/automation" indicators where they affect action.

**Acceptance:** screenshots at target widths show main image task without lateral squeeze and generation/selection accessible without navigating a second sidebar. Current project/character/shot lineage and manual page entry remain. No silent Generate on attaching chat/media.

## UX06: Current Take — a first-class playback and retake surface

**Source:** TakeWorkspace.tsx uses nested EditorWorkspace(name=take) and portals TakeReviewSection/DockedVideo into right subpane. App.tsx VideoWorkspace shows status, T2VBatchPanel, full-run run state, selected take prompt, previous take details, saved request and workflow readiness alongside the gallery/player. Screenshot shows two large columns inside the already narrowed right pane.

**Default hierarchy (single responsive main canvas):**

    [Current Take • Scene 1 / Clip 1]   [History] [Details ⋯]
    [Job state: Generating 62% / Queued / Ready to review / Error]
    [Video player: large, retains playback position]
    [thumbnail strip to choose generated clip or take]
    [Accept Take]  [Retake]  [Next Clip/Video]
    [Reasoning / director defects or retake suggestion when AVAILABLE]
    ──────────────────────────────────────────────────────────
    [Technical details ▾] [Submitted prompt ▾] [Run history ▾]

**Behavioral requirements:**
- While generation is active: show **actual job state/progress/stage**, busy/ETA only if measured, correct pause/cancel/recovery controls and log summary. Do not invent generation percent or render fake placeholder clip.
- When complete: prioritize selected playable video, clip/take selector and three decision buttons; show accepted state and accurate reasons for disabled controls. Retake dialog must keep original unless the user chooses a supported non-destructive option; preserve frozen prompt, retake idempotency, take history, job IDs and source-lineage association.
- When in fully automated run: keep run Pause/Resume/Stop and per-clip errors readily visible; **do not** hide a required safety decision or recovery action in ⋯. Automatically continuing is a separate authorized run mode; manual Accept/Next semantics must not be changed.
- The player is a single mount at a time; do not duplicate video elements or get portal cycles. Retain saved playback position and selection when layout changes. Avoid gallery auto-playing multiple videos in background.
- Hide low-priority request snapshots, raw model settings, JSON IDs, old prompts and detailed worker telemetry under “More details” or a small ⋯ menu. Failed job/recovery warnings remain prominent.
- Optional inspector shows timestamped clip defects **only with real observations**; otherwise label “Not analyzed” and offer an authorized analysis path. Do not claim bad lip-sync/voices from unexamined media.

**Implementation outline:**
1. Map references to TakeReviewSection/ReviewDock/DockedVideo and keep job/selection/preview in VideoWorkspace while restructuring JSX. Do not copy state, requeue jobs or unmount the running VideoWorkspace during layout toggles. Extract view-only TakeReviewSurface.tsx (or similar focused component) if helpful.
2. Replace only the Take route's nested EditorWorkspace split with a single responsive gallery/player/main review actions. Keep EditorWorkspace for TRELLIS/Media Prep.
3. Keep T2VBatchPanel and AssemblyPreviewPanel available as a compact tab/accordion; do not bury actual selected run controls.
4. Test manually submitted clip, running job, failed job, accepted and retake, full-run pause/recover, multiple clips, Next video with/without screenplay, keyboard carousel and mobile.

## UX07: default compact output destination

**Current:** OutputDestination.tsx has existing API to read/save mode default/workspace/folder, grants, relinks and frozen target. Screenshot shows long displayed path plus multiple buttons even when output is already valid.

**Collapsed state (normal):**

    Saved to   [Project / outputs / images] ✓    [Change] [ⓘ]

Show a concise label, **last 1–2 path segments**, project badge and full path via tooltip/Copy. For output type distinguish images/videos/audio/edits and stay truthful about actual saved backend preference (not pretend default mode is project mode). If location is external, badge “Custom folder”. If unavailable, show warning and Relink action without silently choosing another.

**Expanded state:** existing picker/absolute path, mode selection “Project folder (recommended)” / “App default” / “Other folder…”, exact current path, permissions and resolve/relink. Default recommendation: within the current project folder when it is valid/registered; when current data was saved elsewhere **do not silently migrate it**. New jobs use the newly saved choice, existing frozen jobs retain their target and file provenance. If project folder not writable show explicit validation/alternative. Preview of final destination location before Generate. Preserve window/system folder picker and owner grant, non-overwrite output publication, chosen project checkpoint portability and failure/recovery.

**Source:** frontend/src/OutputDestination.tsx; backend services/output_destinations.py::preference,resolve,freeze,granted,target_root,finalize and API dispatcher. Do not change backend just to hide form; UI-only chip is first safe slice. Dedicated output controls in TextToImagePage and VibeEditorPage/export need adapter support; don't blindly force same path semantics.

## UX08: cross-app aesthetics, shared primitive reuse

Target routes: Home, Production Styles, Story, Screenplay, Frame per Shot, Storyboard, Automation & Parameters, Prompt Prep, Video Create, Current Take, Characters & Voices, Scene Backgrounds, First/Last Frames, Text to Image, TRELLIS/Pixal, Media Library, Vibe Editor, Media Prep (business logic unchanged), Status.

Keep the preserved navigation. Apply **semantic visual patterns** rather than generic component rewriting:
- Media-first: preview/generation result primary, controls secondary (image/video/Editor).
- Text-first: screenplay/story/prompt diff primary, review/Apply visible, metadata expandable.
- Timeline-first: Editor editing timeline and review cards; media selection one shared drawer.
- Automation-first: status, authorized plan and progress primary, settings secondary.
- Library-first: search/filter/sort/result grid primary; file management in dedicated safe panel.

Common tokens/components: CompactToolbar, IconAction, DisclosurePanel, StatusChip, DestinationBadge, AssetTray, ReviewActions. Start by composing existing buttons/dialogs; create a shared component only when two real pages need the same behavior. No giant design-system migration or dense one-line code optimization. Styling must use existing token variables and maintain keyboard, reduced-motion and ARIA behavior.

**Compact ≠ hiding requirements:** output destination grant blocked, missing/expired references, unsafe GPU readiness, stale revision, selected work not saved, and destructive actions are high-priority indicators and must not disappear into More.

## Test & acceptance strategy

- Visual regression for 1440×900, 1280×720 (user's screenshots have lower effective right width), 900×768, 390×844; Director expanded/collapsed and sidebar expanded/collapsed. No horizontal overflow, overlapping sticky toolbars, clipped composer/footer, or 4-column squeeze.
- Interaction: all primary and advanced controls available via mouse/keyboard/touch; focus restored after dialog; exact current project and route state retained; no duplicate conversation composer.
- Safety: synthetic image/video/audio assets in isolated test root, mocked jobs and output grants, no real files deleted, no GPU/paid calls. Verify cleanup in failure path.
- Cross-page: output badge changes for new jobs only; old frozen job retains original output; saved output grant not lost; Current Take accepts/retakes/navigates without dropping saved work; Media Prep tests remain unchanged.

**Implementation order:** UX04 migration on images → UX05 image layout; MED01 reusable media view early; UX06 take single canvas can run independently after focused tests; UX07 compact destination UI; UX08 across pages in small route-specific changes. The existing left sidebar and Media Prep processing are preservation boundaries.
