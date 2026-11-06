# Vibe Director — CURRENT active fixes after 603b1fcb push (2026-11-06)

**Use this as the only active task queue.** Baseline HEAD inspected: 603b1fcb0a3eedbcb32154f3599e419ffef05a15. Confirm checkout/dirty changes before implementation. The previous tasks R01, R02, UX01, UX02, UX03 are **implemented as bounded fixes**, with prior Codex test evidence in [R01_UX03_RESULTS.md](R01_UX03_RESULTS.md). Do not redo them. Q01–Q08 similarly completed as foundation. The agent cannot yet autonomously produce an end-to-end film.

**Read first:** [latest source review](REFRESH_REVIEW_2026-11-06_603b1fcb.md), [one media browser & memberships](UNIFIED_MEDIA_AND_PROJECT_ASSETS.md), [compact filmmaking UX](COMPACT_CREATIVE_WORKSPACE_UX.md), [route-by-route plan](PAGE_BY_PAGE_CHAT_AND_LAYOUT.md), and the existing [single-chat principle](UNIFIED_CHAT_AND_PANES.md).

## Prioritized open work

| Card | Priority | Dependencies | Verified status at reviewed HEAD | Acceptance |
| --- | --- | --- | --- | --- |
| UX04 | P0 | existing DirectorRuntime and typed agent tool services | **OPEN**: old chats remain outside Editor | Each page's AI message composer removed only after shared Director can perform/review the old specific action; read-only history preserved |
| MED01 | P0 | current MediaSourcePicker, R2V, Editor, image/voice validators | **OPEN**: multiple browsers, search controls and reference handlers | One reusable media selector, distinct destinations chat/model/tool/Editor, selected chips and exact workflow role/slot validations |
| UX05 | P0 | UX04 image adapter, MED01 basic picker | **OPEN**: ImageAssetsPage nested inner split | Image workflow is one main canvas; primary Generate/candidate actions first; Output/Workflow/Media in compact drawer; no new chat |
| UX06 | P0 | current TakeWorkspace/VideoWorkspace handlers | **OPEN**: Current Take nested two-column layout | One major player + real status + Accept/Retake/Next; metadata in details; retains jobs, history, automation and playback |
| UX07 | P1 | OutputDestination existing mode/grant API | **OPEN**: verbose output card | Project-aware short destination badge, optional Change drawer, unchanged frozen output destinations, relink warnings visible |
| UX08 | P1 | UX05/06/07 primitives | **OPEN**: disparate clutter across pages | Consistent compact toolbars and progressive disclosure, accessible responsive pages without functional loss |
| MED02 | P1 | MED01 UI contract; media_library, content index and semantic search | **PARTLY PRESENT; NEW FILTERS OPEN** | Truthful voice/analyzed/YouTube/other project/folder/date/name/semantic indexed filters, bounded incremental indexing, correct paging/permissions |
| MED03 | P2 high persistence risk | confirmed source/storage grant review, MED01/02 | **PARTLY PRESENT; MANY-PROJECT MEMBERSHIPS OPEN** | One physical source, many project memberships, no implicit copies, protected delete, stable pa-* IDs/hashes and saved jobs |
| AG01 | P1 engine | current Editor bridge, validated services | **OPEN except Editor brief** | Add typed shared action adapters for screenplay/prompt/image/video/QA; no generic unsafe execution |
| AG02 | P2 engine | AG01 | **OPEN** | Durable multi-step film plan/task graph, inspect media, retakes, edit handoff and validated output |
| CR01 | P2 creative | AG01 and versioned style/story services | **OPEN** | Optional film type/visual style/directing jacket and comic panels, no mandatory manual flow |
| VID01 | P2 video | frozen route contracts, ledger, workers | **OPEN** | Actual hash-bound reference manifests, model-specific limits, separately versioned LTX OFF |

**Suggested short engineering slices:** (1) inspect old image chat → adapt via central Director, (2) MED01 shared picker with only existing catalogue backend first, (3) UX05 image layout cleanup, (4) UX06 take canvas and (5) UX07 compact output. UX04 screenplay/prompt/video/3D and global UX08 follow one route at a time. MED02/MED03 require their own reviewed backend plan and migration tests; do not assume cosmetic UI reuse solves indexing or identity.

## UX04 — Remove ALL redundant assistant chats

Old standalone AI composers remain in ScreenplayDirector.tsx, PromptDirector.tsx, CreateWorkspace.tsx/CreateChat, ImageAssetsPage.tsx/ImageAssetsDirectorChat, TextToImagePage.tsx/t2i-chat, TrellisPage.tsx/StudioChat and MediaPrepPage.tsx/audio StudioChat. StoryboardPage's instruction/proposal form is primarily a manual planning control: only retire it after typed parity. StoryPage needs route-level audit to separate story editing from assistant discussion.

For each: identify actual endpoint/persistence/revision checks → share typed page context/action → show review/Apply in right work canvas → preserve existing conversation and pending proposals read-only → **then** remove legacy textarea/Send/log, not manual text prompts. The Vibe Editor composer was already removed; preserve it as success pattern. See [per-route inventory](PAGE_BY_PAGE_CHAT_AND_LAYOUT.md).

## MED01/MED02 — Reuse media browser rather than adding one more

MediaSourcePicker.tsx is **already** a strong source browser (all/current projects, YouTube, extracted, generated, source folder, keyword, chronological sort, cards/list/carousel). App.tsx R2V already has rich reference-specific image/audio/video UI, voice, semantic and style ranking. MediaLibraryPage has index/voice fields; LocalImageFolderBrowser and EditorAssetBrowser independently browse/import. Combine their **browsing/display architecture**, keep specialized R2V model binding and independent Chat vs model reference selection; do not degrade existing semantics. Add truthful missing filters and persisted asset membership in separate phases. See [media plan](UNIFIED_MEDIA_AND_PROJECT_ASSETS.md).

## UX05/UX06/UX07 — User's screenshot fixes

- **Images:** flatten ImageAssetsPage internal EditorWorkspace split (right surface is already narrow); main image prompt/generation/candidates first, old chat migrated, compact Output/Workflow details/reference picker.
- **Current Take:** remove TakeWorkspace's nested EditorWorkspace for this route after transferring working portals/state to one view. Real progress/player/thumbnails/Accept/Retake/Next dominant. Frozen prompt/recovery/history/worker details remain accessible under details; automated-run controls visible.
- **Output:** reuse OutputDestination existing preference/grants/freeze; display the project path compactly and make Change optional. Project folder recommended only if it can be resolved and safely selected, without silently moving frozen jobs.

## AG01/AG02/CR01/VID01 — long-term agent filmmaking

Full agent action graph and state-aware non-linear film orchestration remain future scope, as do true media-backed defect detection and output verification. Preserve skills/global/project layers, project knowledge lineage and manual access. No prompt claims without real registered output, no GPU/paid runs without separate owner approval.

## Source, test, preservation rules

Use existing AGENTS.md, caller trace, Git status/HEAD and currently applicable directory change_readme.md. Preserve project snapshots, media originals/hashes, local source paths/grants, Editor sessions/ranges, prompt CAS, frozen jobs, audio voices, takes/retakes, GPU guards and all Media Prep processing. Keep external automation/third-party integrations behind real capability detection.

Small typed view/adapters, no giant rewrite of App.tsx or media_library.py. One route per slice; run existing and new Playwright/unittest/build tests. Synthetic PNG/WAV/MP4/TXT only under isolated test-owned temp roots and cleanup assertions on success/failure. No destructive deletion of project data. **This guide documents planned app work; do not treat it as automatic permission to run external code, provider/GPU jobs, remove user media, or publish.**
