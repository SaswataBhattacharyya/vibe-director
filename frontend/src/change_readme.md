# Frontend source — current remaining changes after 603b1fcb (2026-11-06)

R01/R02, UX01 three outer collapsible panes, UX02 shared Editor creative brief and UX03 removal of the Editor's duplicate composer are **implemented as bounded slices** (reported checks in fixes/R01_UX03_RESULTS.md). Do not rebuild them.

**Read:** fixes/REFRESH_REVIEW_2026-11-06_603b1fcb.md, fixes/ACTIVE_FIXES_2026-11-06.md, fixes/UNIFIED_MEDIA_AND_PROJECT_ASSETS.md, fixes/COMPACT_CREATIVE_WORKSPACE_UX.md and fixes/PAGE_BY_PAGE_CHAT_AND_LAYOUT.md.

## UX04: one Director chat on *every* page

Remove these legacy AI composers **after** their typed existing tool action and review/Apply parity works:
- ScreenplayDirector.tsx (called in ScreenplayPage): whole screenplay instructions, proposal diff and CAS Apply.
- PromptDirector.tsx (called in PromptPreparationPage): selected shot/target, prompt edits, learning rules, CAS.
- CreateWorkspace.tsx (CreateChat): Video Create prompt field-edit and saved requestKey recovery.
- ImageAssetsPage.tsx (ImageAssetsDirectorChat): exact image prompt/source refs and Apply.
- TextToImagePage.tsx (t2i-chat): image suggestion, saved prompt snapshot, Use suggested prompt.
- TrellisPage.tsx (StudioChat component): assisted tool settings Apply.
- MediaPrepPage.tsx (audio StudioChat): optional chat guidance only; preserve every actual Media Prep processing tool.
- StoryboardPage.tsx Production instruction/shot proposal: review classification; not every textarea is an AI chat.
No second model selector/Send/history transcript per route after parity. Preserve old messages read-only and page input fields (image prompt, screenplay text, shot/video prompt, SRT editor, search, output folder).

## MED01: shared browse/pick interface, not a second catalogue

Actual reusable foundation MediaSourcePicker.tsx already has current/all projects, folders and source types. LocalImageFolderBrowser.tsx has real client folder consent + deletion; EditorAssetBrowser.tsx has import/select/deletion; MediaLibraryPage has voice-only and indexing UI; App.tsx R2V has rich modality role/slot matching. Make a reusable media search/display + typed destination adapter. On selection, perform one of Attach to Director, bind exact model image/audio/video reference, choose Editor range, or add project membership. These are different operations and must not silently coincide. Preserve slot limits, R2V source matching, source SHA and selected asset ownership.

Do not globally replace LocalImageFolderBrowser/EditorAssetBrowser before their download/import/deletion features can be reached in appropriate controls. Generic picker is safe browse/select; destructive delete remains in library management.

## UX05: Image Assets/Scene Backgrounds

ImageAssetsPage.tsx (~804 lines): current imageSidePanel includes OutputDestination, Workflow details, LocalImageFolderBrowser, and old chat, then the page wraps another EditorWorkspace(name=image-assets) split inside the outer app. Restructure as a single right pane main canvas: target→model→editable prompt→refs→Generate→candidate review. Output, workflow details, advanced image controls and source folder selection are compact buttons/drawers. Keep voice assignment, scene variation, image candidates, frozen job requests and producer validation. Don't modify generic EditorWorkspace globally.

## UX06: Current Take

TakeWorkspace.tsx currently uses EditorWorkspace(name=take), ReviewDock portal and DockedVideo. App.tsx VideoWorkspace take branch has rich selected job/take/full-run state and Accept/Retake/Next handlers plus saved request/technical panels. Use one responsive right-side review canvas: genuine progress/status, playable selected video and thumbnail strip, decisions. Keep T2VBatchPanel, full-run Pause/Stop/Retry, AssemblyPreviewPanel, frozen prompts and raw job details accessible through details or More. Avoid double video mount, unmount of active VideoWorkspace, or changing retention/retry semantics.

## UX07/UX08: compact destinations and consistent visual hierarchy

OutputDestination.tsx always renders long editable path and duplicate actions. Collapse by default to short project folder badge with current backend effective mode and optional Change/Relink; preserve choice/freeze/grants. Details accessible, error/unavailable visible. Apply small reusable toolbar/StatusChip/Disclosure patterns only after 2+ real uses. Keep existing left sidebar, Director and work pane collapse, project toolbar and Media Prep functionality.

## Code quality, tests

App.tsx ~1235 lines, ImageAssetsPage.tsx ~804 lines. Extract display-only child components/hooks and explicit typed contracts; avoid moving request ownership without tests. EditorWorkspace.tsx is still consumed by TRELLIS and Media Prep; StudioChat.tsx exports widely imported studioRequest. Do NOT delete either module during one page's layout/chat cleanup.

Verify source consumers; isolated test output and source files only under disposable directories. Run Playwright at wide/1280/tablet/mobile and focused backend tests. No GPU/provider execution without permission. Never strip relevant plan approvals, user media or frozen refs.
