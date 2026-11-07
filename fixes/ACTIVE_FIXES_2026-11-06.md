# Vibe Director — CURRENT active fixes after 603b1fcb push (2026-11-06)

**Use this as the only active task queue.** Baseline HEAD inspected: 603b1fcb0a3eedbcb32154f3599e419ffef05a15. Confirm checkout/dirty changes before implementation. The previous tasks R01, R02, UX01, UX02, UX03 are **implemented as bounded fixes**, with prior Codex test evidence in [R01_UX03_RESULTS.md](R01_UX03_RESULTS.md). Do not redo them. Q01–Q08 similarly completed as foundation. The agent cannot yet autonomously produce an end-to-end film.

**Read first:** [latest source review](REFRESH_REVIEW_2026-11-06_603b1fcb.md), [one media browser & memberships](UNIFIED_MEDIA_AND_PROJECT_ASSETS.md), [compact filmmaking UX](COMPACT_CREATIVE_WORKSPACE_UX.md), [route-by-route plan](PAGE_BY_PAGE_CHAT_AND_LAYOUT.md), and the existing [single-chat principle](UNIFIED_CHAT_AND_PANES.md).

## Working-tree progress after b1c0f17d (2026-11-06)

The table below records the earlier reviewed HEAD, not the current uncommitted implementation. Inspect the working tree before repeating a card. Current bounded progress:

- **UX04 / AG01:** Shared Director adapters now cover images, screenplay, prompt proposals/learning, Video Create prompts, studio settings, ACE music discussion and Story passage proposals. Story manual edits and shared requests reuse `services/agent_story.py`; proposals retain explicit review, revision checks and request-key recovery. Old assistant history and unsent Story instructions remain readable. Storyboard planning controls still need their own parity audit. Media analysis/QA and autonomous execution are not implemented by these adapters.
- **UX05 / UX06 / UX07:** Image and Current Take inner layouts have been flattened; output selection uses the existing grants/preferences through compact controls. Existing generation, retake, history and frozen requests remain authoritative. These are bounded layout fixes, not whole-application completion.
- **UX08:** Studio shells, pane controls and several creative pages use compact disclosure/layouts. Story now uses one full-width source column beside the shared chat, with import below the editor. Continue route-by-route review; do not declare every route visually accepted.
- **MED01:** `MediaSourcePicker` has explicit chat attachment, model reference, tool input and Editor preview destinations. Editor preview preserves unfinished ranges, audio utilities select inputs without running, and first/last-frame slots register and bind the matching role separately. R2V's specialized selector and remaining local-folder browser consolidation are still open.
- **MED02 / MED03:** The shared browser now offers audio categories, inclusive added-date ranges, name sorting and current-content-index filters before pagination. Extracted media is labelled as extracted, rather than claiming analysis. Registered images can bind directly to Qwen references on both image surfaces. Reference reuse now links ordinary uploads through existing storage locations instead of silently copying; explicit copy remains available. Linked originals retain deletion protection, and project checkpoints restore linked bytes without the source workspace. No membership schema or indexing migration was introduced. Incremental indexing and broader membership management remain open.
- **AG02 / CR01 / VID01:** Durable full-film orchestration, optional production-style/comic extensions and model-specific frozen reference manifests remain open. Do not label these as completed by the shared-chat adapters.

Evidence for the Story/frame slice: `test_agent_story.py`, existing selected-edit/authoring regressions, `director-story.spec.mjs`, the frame-slot case in `video-ui.spec.mjs`, and existing shared-media cases in `director-runtime.spec.mjs`. Tests use mock/CPU execution and isolated test-owned storage; they do not establish live provider/GPU output acceptance. Existing engine confirmation controls remain in place.

Validation of this slice: 17 Story/selected-edit/authoring backend tests and 18 other creative-adapter backend tests passed. The final browser runs passed five Story/shared-media cases and five model/frame cases; the preceding broader run passed 14 regressions, with its two fixture/selector failures corrected and rerun successfully. Production build and `git diff --check` pass. Browser screenshots at 1280/900/390 px show no horizontal overflow; desktop layout was visually inspected. Temporary Playwright output was removed and absence verified; backend fixtures assert cleanup. Graphify refreshed to 5,299 nodes / 16,031 edges; 34 blast-radius citations verify. Build still reports the existing large-bundle advisory.

Files changed for the Story/frame slice (in addition to earlier uncommitted work):

- Backend: `backend/story_builder/services/agent_story.py` (new), `backend/story_builder/services/agent_conversation.py`, `backend/story_builder/isolated_server.py`, `backend/story_builder/tests/test_agent_story.py` (new).
- Frontend: `frontend/src/DirectorStory.ts` (new), `frontend/src/DirectorRuntime.tsx`, `frontend/src/DirectorConversation.tsx`, `frontend/src/StoryPage.tsx`, `frontend/src/lib/agent-tasks.ts`, `frontend/src/App.tsx`, `frontend/src/ui-refinement.css`.
- Browser regressions: `frontend/tests/director-story.spec.mjs` (new), `frontend/tests/model-selection.spec.mjs`, `frontend/tests/p1-progress.spec.mjs`, `frontend/tests/video-ui.spec.mjs`.
- Review/generated documentation: this guide, `.review/director-image-ui-impact.json`, `graphify-out/graph.json`, `graphify-out/manifest.json`, `graphify-out/cache/stat-index.json` and content-addressed AST cache entries generated by Graphify. Earlier worktree changes were preserved.


## Latest media continuation — owner acceptance pending

Implemented metadata filtering in a small shared module, bound library selection directly to Qwen image references, and removed silent copies for ordinary upload references. Reference removal cleans only owned temporary staging, never registered library media. The picker explains reference versus copy and keeps generation explicit.

Focused checks: 15 catalogue/filter backend regressions passed, plus one new checkpoint recovery regression. Four mocked browser regressions passed (prompt review/stale protection, persistent Qwen references with safe removal, catalogue filters, utility input selection); the filter case passed again after the checkbox spacing correction. Production build passes with the existing large-chunk advisory. Screenshots at 1280 and 390 pixels were inspected. These checks do not establish live model output quality. Temporary backend roots have cleanup/absence assertions; test browser output is removed after inspection. No provider or GPU job was started. Graphify refresh: 5,319 nodes / 16,087 edges; 41 exact source citations checked.

Files changed in this continuation (existing unrelated working-tree changes are preserved):

- Backend: `backend/story_builder/isolated_server.py`, `backend/story_builder/services/media_library.py`, new `backend/story_builder/services/catalogue_filters.py`, `backend/story_builder/tests/test_media_catalogue.py`, new `backend/story_builder/tests/test_catalogue_filters.py`.
- Frontend: `frontend/src/MediaSourcePicker.tsx`, new `frontend/src/MediaCatalogueFilters.tsx`, `frontend/src/TextToImagePage.tsx`, `frontend/src/ImageAssetsPage.tsx`, `frontend/src/lib/media-api.ts`, `frontend/src/media-library.css`, `frontend/src/ui-refinement.css`, `frontend/tests/director-runtime.spec.mjs`.
- Evidence/guidance: this document, `.review/director-image-ui-impact.json` and generated Graphify graph/manifest/cache artifacts.

### Your manual acceptance

1. Stop and restart the app with its launcher to load backend changes. Open a disposable project; keep existing production media untouched.
2. On Story, Screenplay, Prompt Preparation, image pages, Video Create, TRELLIS/audio and ACE, confirm one shared Director composer, readable old history, and explicit proposal review/Apply where supported. Type a manual prompt, open/close the inspector and switch panes; the prompt must survive.
3. Open Context & skills in Director and Editor. Confirm application/global/project skills and shared tools. Check application/project-only/full-access modes against the configured runtime's actual capabilities; labels alone do not establish terminal/browser execution.
4. In a media picker, try source/project/folder selection, voice/music/dialogue filters, dates, name sorting, paging and clear filters. “Content indexed” requires a saved current embedding; it does not automatically run indexing or certify analysis quality.
5. On Text to Image, choose Qwen Image Edit, browse registered images and select up to three references. Reload; references should remain. Remove one; its original library entry/file should remain. Repeat on an independent character/background editing flow. First/last-frame lineage keeps its dedicated binding controls.
6. Reuse a disposable source in a second project with separate-copy unchecked; both memberships should resolve the same bytes. Permanent deletion must report the other use. With separate-copy checked, the copy should be independent. Save/reopen the target project and confirm media remains available.
7. In Editor, browse/select a source, preview a range, then add it explicitly; unfinished range selections must survive browsing. In Media Prep, selection must not run a utility until you click Run.
8. When ready, use your own Generate/Run buttons to accept image/video/audio/ACE outputs, cancellation/retry and retakes. Confirm saved output playback and project reopen. No live generation acceptance was performed automatically.

Rollback: restore only the specific UI/filter/reference changes from your saved patch or Git review; do not reset the entire dirty checkout. Filters add optional query fields and no database migration. New linked memberships use the existing `storage_location` format and remain readable by the previous resolver; do not delete their source media when reverting. Existing copies, IDs, frozen jobs and saved checkpoints are not migrated or rewritten.


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
