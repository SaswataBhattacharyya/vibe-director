# Source-change matrix — only work still open after 603b1fcb

**Baseline:** latest [static review](REFRESH_REVIEW_2026-11-06_603b1fcb.md) and [active queue](ACTIVE_FIXES_2026-11-06.md). Previous R01/R02/UX01/UX02/UX03 work **implemented**, see [reported results](R01_UX03_RESULTS.md); do not list old source anchors as future changes. Confirm local git status before changes.

| Task | Core source anchors | Exact safe change / consumers |
| --- | --- | --- |
| UX04 screenplay | frontend/src/ScreenplayDirector.tsx, ScreenplayPage.tsx, backend story_authoring/field proposal services | Existing discuss/propose/Apply/CAS via typed agent action. Keep revision history; remove only old transcript+composer once equivalent available |
| UX04 prompts | PromptDirector.tsx, PromptPreparationPage.tsx and prompt director API/services | Reviewed per-shot diff and learned rules via central chat, keep approvals and source revisions |
| UX04 image | ImageAssetsPage.tsx ImageAssetsDirectorChat; TextToImagePage.tsx t2i-chat | Use existing prepareImagePrompt/field-edit adapters and exact source prompt snapshot; shared chat, right-side Apply; no automatic Generate |
| UX04 video | CreateWorkspace.tsx CreateChat, App.tsx/video field-edit proposals | Keep requestKey/recovery and prompt Apply, remove extra discussion composer after parity |
| UX04 3D | TrellisPage.tsx, StudioChat.tsx component | Central model settings suggestions; keep 3D config, batch jobs and explicit Apply |
| UX04 Media Prep | MediaPrepPage.tsx audio StudioChat, StudioChat.tsx export studioRequest | Preserve all processing, only replace AI assistant after parity. Keep fetch helper imported by many pages |
| MED01 browser | MediaSourcePicker.tsx, LocalImageFolderBrowser.tsx, EditorAssetBrowser.tsx, MediaLibraryPage.tsx, App.tsx R2V; lib/media-api.ts; DirectorConversation.tsx | Reuse browse UI with destination intent. Target-specific bind chat/model/Editor. Preserve folder OS consent, R2V role/slot caps and media library management |
| MED02 filters | services/media_library.py::browse_catalogue, media_discovery.py::discover, media_semantic_search.py, media-api.ts | New optional verified source/voice/analyzed/indexed/date/name filters with correct page counts. Bound scans; original endpoint compatible |
| MED03 cross-project | services/media_library.py::reuse_catalogue_asset/_link_shared_asset/_record_reuse/delete_media_file, storage_paths.py, projects.py and snapshots | Shared location + many project memberships/overlays without implicit copy; source availability/hash checks, migration and safe deletion tests |
| UX05 image layout | ImageAssetsPage.tsx imageSidePanel/EditorWorkspace, image-assets.css, OutputDestination.tsx, SceneBackgroundVariant.tsx | Replace inner split with one canvas, small disclosures, Media drawer and direct Generate/candidate controls |
| UX06 Current Take | TakeWorkspace.tsx, App.tsx VideoWorkspace take branch, video related CSS, TakeClipCard, T2VBatchPanel, AssemblyPreviewPanel | Remove nested EditorWorkspace ONLY for take view, preserve single player/job owner, live status, accept/retake/next and full-run controls |
| UX07 destinations | OutputDestination.tsx, output CSS; services/output_destinations.py preference/resolve/freeze only if needed | Collapsed badge + on-demand granted folder selection; no silent changes to historical output paths |
| UX08 general UX | StudioShell.tsx, page-specific headers/forms, existing CSS tokens, VibeEditorPage, ProductionStylesPage and other routes | Reusable small toolbar/disclosure/status primitives; don't rewrite stable sidebar or Media Prep processing |
| AG01/02 | services/agent_conversation.py, agent_tools.py, agent_tasks.py, agent_graph.py, existing story/image/video/editor workers | Typed action parity, durable film tasks and QA; always exact approval and media verification |
| CR01/VID01 | production style/storyboard sources and model-specific video contracts | Optional jackets, panels, exact upload manifests, LTX OFF new version without altering frozen old jobs |

**Never delete EditorWorkspace.tsx** merely because Take/Image stop using it; TRELLIS and Media Prep still call it. **Never delete StudioChat.tsx** while studioRequest is imported by many modules. Use small adapters, not new giant monolith or new unvalidated command endpoints.

See [unified media architecture](UNIFIED_MEDIA_AND_PROJECT_ASSETS.md), [UX spec](COMPACT_CREATIVE_WORKSPACE_UX.md), [route migration](PAGE_BY_PAGE_CHAT_AND_LAYOUT.md), and applicable colocated change_readme.md. Static docs review is not a new app test result.
