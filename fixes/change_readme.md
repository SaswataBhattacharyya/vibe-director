# Vibe Director — CURRENT Codex entry after latest push

**Current inspected source:** vibe-director-current at 603b1fcb0a3eedbcb32154f3599e419ffef05a15 (2026-11-06). Before implementing, inspect local git HEAD/status and reconcile any newer source; this document is a fix guide, not a working code patch.

## Read first — source-linked ACTIVE guides
1. [Fresh source review & observed UI issues](REFRESH_REVIEW_2026-11-06_603b1fcb.md).
2. [Current open-task list](ACTIVE_FIXES_2026-11-06.md).
3. [Unified media browser, indexing and multi-project memberships](UNIFIED_MEDIA_AND_PROJECT_ASSETS.md).
4. [Compact filmmaking UI, image and Current Take redesign](COMPACT_CREATIVE_WORKSPACE_UX.md).
5. [Page-by-page chat removal and layout instructions](PAGE_BY_PAGE_CHAT_AND_LAYOUT.md).
6. [Source-change matrix](FILE_CHANGE_MATRIX.md), appropriate frontend/backend/test directory change_readme.md, repository AGENTS.md.
7. [Single Director/three-pane original design](UNIFIED_CHAT_AND_PANES.md) as background; [R01–UX03 results](R01_UX03_RESULTS.md) for completed work. The older six foundational and 13 package skills remain creative guidance, not evidence that all runtime adapters are implemented.

## Done — DON'T REDO

Q01–Q08 foundations and R01/R02 crash/input repairs, UX01 three-pane collapse, UX02 Editor brief bridge, UX03 Editor chat removal now have source implementations. The previous result files report mock/CPU/browser test evidence; this documentation review has not rerun tests or exercised a paid provider/real Codex sidecar. Check actual source before assuming each claim is fully accepted. The agent is NOT yet end-to-end film capable.

## Owner's new whole-app design correction

- **One persistent center Director chat** for Story, Screenplay, Storyboard, prompts, images, Video Create, TRELLIS, Media Prep and Editor. Other old chatboxes are redundant, not just Editor's. Migrate each chat's *actual* proposal/diff/Apply and history to typed shared tools BEFORE deleting its composer.
- **One clean right-hand working canvas** instead of nested EditorWorkspace-style internal two-column areas inside the already split outer app. Prioritize creation/review; reduce visual noise with compact icons, tooltips, drawers and expandable technical details. Preserve accessibility, responsive layouts, all keyboard actions and real error/recovery.
- **One unified media discovery/selection surface** using EXISTING MediaSourcePicker and mature R2V/library capabilities. Support image/audio/video, current/all projects, authorized folders, YouTube downloads, generated, analyzed, voice-only, chronology, indexed search, grid/list/carousel; do not fake unsupported filters. **Selecting for chat, binding to model references, Editor ranges and linking to project are distinct explicit actions**.
- **Multiple project memberships** for same verified asset without implicit file copies, while maintaining old project-scoped pa-* IDs, SHA, lineage and deletion rules. Existing shared-record mechanism is partial; design/data migration and tests before changing persistence.
- **Output folder compact by default**, show effective project-preferred path with optional Change/Relink and unchanged frozen outputs/grants.
- **Current Take = progress + prominent video player + thumbnails + Accept/Retake/Next.** Other saved request and workflow details remain accessible in details, not preempting video. Keep full-run safety and recovery visible.
- Keep **existing left navigation** unchanged and all three outer panes independently collapsible. Keep Media Prep's working processing controls and don't lock users into a stage sequence.

## Engineering policy

Use blast-radius + ponytail + code-simplification: patch the smallest verified source seam; simplify semantics and duplicate presentation, not compact code into unreadable lines. Do not replace existing engines, trusted HyperFrames renderer or video validators. Avoid adding more code to App.tsx (~1235 lines), ImageAssetsPage.tsx (~804) or isolated_server.py beyond tested thin seams; extract only cohesive view/adapters after tracing callers. Keep future AG01/AG02/CR01/VID01 roadmap but avoid premature huge migrations.

Current task is a source review and documentation update, **not** permission to execute GPU/paid/model jobs, delete user data, or start arbitrary host computer tasks. Codex should first report a source-level mini-plan for the next implementation slice and request/observe specific authorization.

Testing: each route in isolated fixture workspace plus tool-library, image/audio/video/TXT synthetic assets only under disposable directories; verify cleanup after success/failure; frontend/browser/build and backend contract tests, real provider/render acceptance only after owner approval. Current review made doc edits only.

**History:** Old Q01_Q06_RESULTS.md, Q07_Q08_RESULTS.md and SOURCE_ASSESSMENT.md are provenance; R01_UX03_RESULTS.md documents the latest implemented patch. No completed feature cards should be replayed.
