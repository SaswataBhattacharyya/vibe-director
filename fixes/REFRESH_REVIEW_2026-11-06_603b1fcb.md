# Latest push review — shared UX and source re-evaluation

**Read at branch vibe-director-current commit 603b1fcb0a3eedbcb32154f3599e419ffef05a15, 2026-11-06.** Compared to the previous fixes HEAD 39680fa382698890542f0751613f33c36fe15241. This is a **static GitHub code review plus the user's Characters & Voices and Current Take screenshots**. I did not run current tests, launch app, run Codex, change application code, or validate the UI in a live browser. Existing test numbers in fixes/R01_UX03_RESULTS.md are Codex's claims for its previous local run, not fresh test results.

## Current-state correction: don't redo finished work
- R01 task submission recovery: new code in services/agent_tasks.py; the previous results report source/mock tests. Treat implemented pending regression verification.
- R02 computer stdin supervision: new code in services/agent_computer.py; treat implemented pending regression verification, with live Codex still untested.
- UX01 independent sidebar/Director/work-pane controls: DirectorWorkspace.tsx + DirectorRuntime.tsx now manage center/right state, keeping panes mounted. Source supports the prior implementation report. Do not reopen as a from-scratch fix.
- UX02 Editor bridge: agent_editor.py + agent_conversation.py + agent_tasks.py + DirectorEditor.tsx; a typed versioned Editor session target can prepare the existing creative brief and still requires the original two clearances.
- UX03 Editor secondary chat: current VibeEditorPage.tsx no longer imports EditorWorkspace nor renders the prior editor-composer; preserved tools/history. This is complete as a bounded migration, not as a fully autonomous Editor agent.
- **OPEN:** UX04 all other legacy chats; AG01/AG02 full agent action graph; creative jackets/storyboard; model-aware video prompts; audiovisual QA, retakes and final assembly.

## Newly confirmed design/engineering problems

| Priority | Current code & screenshot | Diagnosis | Repair route |
|---|---|---|---|
| P0 | ImageAssetsPage.tsx lines ~692–721 uses OutputDestination, Workflow details, LocalImageFolderBrowser, ImageAssetsDirectorChat in imageSidePanel, then EditorWorkspace with creation controls and that side panel. Screenshot shows 3 app-level panes and *another* inner split. | Unnecessary internal column compression and duplicate chat. It hides primary image workflow below the fold. | UX04 image chat action parity first; UX05 flatten the right work pane and move advanced options into compact drawer/details. |
| P0 | TakeWorkspace.tsx wraps content with EditorWorkspace name=take and uses ReviewDock/TakeReviewSection and portal-based DockedVideo. App.tsx Current Take has review status at left and generated-player dock at right, plus saved snapshot/workflow info, complete-run section and history. | A second right-side split inside already narrowed workspace; media/player/actions should lead, metadata should be subordinate. | UX06 single responsive Current Take canvas, one player/status/actions priority; preserve portal owner while migrating. |
| P1 | MediaSourcePicker.tsx has global media, current/all projects, shared downloads, extracted, repertoire, generated, import, source folder, query, sort and cards/list/carousel. | Already a good shared catalogue **foundation**; don't rebuild search. However its Add does not assign exact target model slot/chat attachment. | MED01 use one picker/surface with typed target roles and adapters; retain existing specialized model constraints. |
| P1 | LocalImageFolderBrowser.tsx separately reads browser directory handles, offers reference and chat callbacks and **permanent deletion**. EditorAssetBrowser.tsx has another importer/search/grid/delete. TextToImagePage.tsx uses LocalImageFolderBrowser and a separate t2i chat. | Duplicated UI and inconsistent semantics; removing without migration would discard OS folder use and dangerous delete confirmation. | MED01 migrate folder/drop/import as browse adapters; keep deletion in explicit Media Library management, never universal attach dialog. |
| P1 | App.tsx VideoWorkspace ~1080–1160 has rich R2V image/audio/video reference group browsing, metadata, voice filters, semantic retrieval, style rankings and per-kind limits. | Valuable mature logic but partly duplicates MediaSourcePicker and lives in a ~1235-line parent. | MED01 preserve the R2V model-specific binding/tray; extract reusable media browsing, not its schema, matching, reference slot numbering or exact validators. |
| P1 | MediaSourcePicker currently shows source categories; MediaLibraryPage has 'voice-files', 'audio-clips', role filters, annotation and content index controls. | Filter vocabulary is fragmented. No one picker exposes voice-only, YouTube-only, analyzed-only, use-in-project and audio category uniformly. | MED02 shared query filter contract; each filter must be real backed by source metadata, not a decorative button. |
| P1 | media_library.browse_catalogue() loops source project manifests and calls media_discovery.discover() on browse, which may index newly seen files. The query searches filename/description/tags; semantic search is separate and workspace-scoped. | Existing catalogue is useful but not a single precomputed global index of every path with analyzed/voice metadata. Source traversals may be costly; don't promise search completeness or global semantic search without backend work. | MED02 incremental metadata index/search adapter with explicit source grants, stable old API compatibility and measured performance. |
| P1 | media_library.reuse_catalogue_asset() links records with storage_location; otherwise falls back to file read/upload/dedupe even in reference mode. Cross-project ordinary source folders may be copied. | User's desired many-projects-one-file membership is not fully represented by current behavior. Treat content hash, source location and membership as different identities. | MED03 additive project membership and canonical asset locator/overlay while retaining existing pa-* IDs, hashes and frozen jobs. |
| P1 | OutputDestination.tsx always displays heading, path input, choose folder button, Use this folder, repeated full path, a footnote; screenshot shows already configured project image output. | Excessive always-on configuration. Backend output_destinations already has modes default/workspace/folder, grant validation, freeze and relink; must not hide missing-grant errors. | UX07 compact destination summary/chip, recommended project output location, Change drawer on click, full path tooltip/copy, no silent migration of existing choice. |
| P1 | Many older conversations remain: ScreenplayDirector, PromptDirector, CreateWorkspace.CreateChat, ImageAssetsDirectorChat, TextToImagePage t2i-chat, TrellisPage.StudioChat, MediaPrepPage.StudioChat. Storyboard production instruction is a proposal editor, not necessarily a duplicate chat. | One Director composer still is not true across *all routes*. | UX04 per-page typed action migration then delete composer, not review/Apply/history. |
| P2 | Right-hand work pages include full card headings, large panels, duplicate resource pickers, settings on first view. | The new persistent Director reduces work-surface width; old full-page information hierarchy no longer fits. | UX05/UX06/UX07 + UX08 cross-page design language/compact controls based on task priority, not blanket hiding. |

## Media semantics: do not conflate browsing with binding

One visual browser may deliver:
1. **Chat attachment**: a project/surface-owned reference to the Director conversation, not silently a MiniMax/model input. Validate access and limits; do not upload bytes in the chat prompt.
2. **Model reference**: an explicit engine/workflow-specific binding with model slot/role/intent, source ID/hash and validation; R2V has independent image/audio/video limits and paired sound semantics; FL2VA has true first/last.
3. **Tool input or Editor range**: selected media and actual start/end range or task source, not either of the above.
4. **Browse-only**: preview, inspect, index or search with **no** automatic binding.

One picker, distinct actions. Never silently treat adding to a project catalogue as attaching to a prompt or chat. Preserve 'reference' versus 'copy' as a consented storage action, separate from selection destination.

## State and blast radius

Current branch contains old assets/manifests, test fixtures and audited APIs. Cross-project identity touches services/media_library.py, media_discovery.py, storage_paths.py, projects.py, output_destinations.py, production_ledger.py, MediaSourcePicker.tsx, lib/media-api.ts, MediaLibraryPage.tsx, selected media state in R2V/App.tsx, editor-api ranges, snapshot/delete utilities and existing tests. Do not eagerly replace media IDs or rewrite stored request references.

Nested layout cleanup touches StudioShell/DirectorWorkspace (already working), ImageAssetsPage, TakeWorkspace, App VideoWorkspace, EditorWorkspace (reused by TRELLIS/Media Prep), VibeEditorPage, output CSS and per-route screenshot tests. Do not delete shared components while callers remain.

The current code review has **not** proven runtime layout across every viewport or any true media quality outcome. Before implementation: inspect clean git status, source APIs/worker contracts, source-wide callers, project snapshots, media path/grant checks, and historical regressions.

## See also
- fixes/UNIFIED_MEDIA_AND_PROJECT_ASSETS.md — shared picker, indexing, memberships, typed binding and source security.
- fixes/COMPACT_CREATIVE_WORKSPACE_UX.md — page hierarchy and exact Current Take/image/output redesign.
- fixes/PAGE_BY_PAGE_CHAT_AND_LAYOUT.md — migration matrix for every older chat and nested layout.
- fixes/ACTIVE_FIXES_2026-11-06.md — prioritized remaining task cards.
