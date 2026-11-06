# Paste into Codex — Vibe Director cross-app UX and media cleanup

Read the CURRENT repository code and do not redo implemented R01/R02/UX01/UX02/UX03. On current reviewed commit 603b1fcb the Editor-specific duplicate chat is already removed, the three outer panes can collapse, and the Editor brief adapter exists. This new request is **a whole-app cohesion project**, not a second Editor fix.

Before planning/editing, read:
1. AGENTS.md and current git branch/HEAD/status; keep all uncommitted changes.
2. fixes/REFRESH_REVIEW_2026-11-06_603b1fcb.md
3. fixes/ACTIVE_FIXES_2026-11-06.md
4. fixes/UNIFIED_MEDIA_AND_PROJECT_ASSETS.md
5. fixes/COMPACT_CREATIVE_WORKSPACE_UX.md
6. fixes/PAGE_BY_PAGE_CHAT_AND_LAYOUT.md
7. fixes/FILE_CHANGE_MATRIX.md and appropriate frontend/src, frontend/src/lib, backend/story_builder/services, tests change_readme.md
8. fixes/R01_UX03_RESULTS.md for what is done; 13 skills and glossary when the current task needs them.

## The desired end result
The persistent middle Director is the only live AI chat. Every other older screenplay/prompt/image/T2I/Create/3D/Media Prep AI chat must be carefully migrated and retired, keeping its real propose/review/apply/draft/recovery behavior. The right work area is one elegant main task surface, not a stack of nested side panels; all three outer panes independently collapse and restore. Leave sidebar and Media Prep processing intact.

Build on existing MediaSourcePicker/catalogue and R2V per-kind reference binding: a common all-image/audio/video picker with real filters for project(s), authorized folder, YouTube, generated, voice-only, analyzed/semantic only when indexed, sorting and preview modes. The *same browser* can choose "Attach to Director" OR "Use as model reference" OR "Add to Editor" but those are separate typed actions; no unreviewed model reference from a chat attachment. Do not make a second asset registry unless the existing storage/membership graph demonstrably requires a small additive schema.

Current Take should prioritize live generation progress, large actual playable video, selected clip gallery and Accept/Retake/Next; put long frozen prompt/job/workflow details in an accessible overflow/Details panel. Image Assets/Scene Backgrounds should prioritize target, editable prompt, selected refs, Generate, candidate gallery; move verbose Output/Workflow metadata behind compact controls. Output location defaults should recommend project folder when safely available but must not silently change prior choice/frozen jobs.

## IMPLEMENTATION PROCEDURE — plan first, one slice at a time
1. Reconcile actual latest HEAD and implementations; identify duplicate chats, nested EditorWorkspace wrappers, media browser copies and output path ownership from current source. Separate completed from open work.
2. Produce a concise exact file-level plan with dependencies, blast radius, typed API shapes and edge cases; don't attempt all pages in one patch. Priority first small safe slice: image Director action parity, then MED01 picker adapter and UX05 image panel; UX06 Current Take can be an independent slice; UX07 output badge; UX04 remaining routes then MED02/MED03.
3. Verify all major API and role semantics from source before coding. For media, distinguish actual registered source, project membership, chat attachment, model reference slot and Editor range. Existing R2V has distinct image/video/audio caps and separate paired sound; FL2VA true first/last. Don't reduce to unsafe generic references.
4. Show the mini-plan and obtain explicit current authorization to implement the selected slice. Don't assume this docs review grants permission to run paid/GPU/provider work or unrestricted host tools.
5. Then implement small readable modules using code-simplification, ponytail and blast-radius. Preserve user project state, assets/hashes, saved Editor revisions and jobs, retries, workflow versions, media outputs and Media Prep behavior.
6. Test relevant existing and new Playwright/unittest/build in test-only temp workspaces with dummy PNG/WAV/MP4/TXT; assert no leftovers even on failures. No real GPU/paid generation unless separately approved. Visually verify compact layout at 1440, 1280, tablet, mobile with expanded Director/sidebar and no clipped controls.
7. Report actual changes/tests/cleanup/rollback and next small slice; never claim a complete film or analyzed media from only mocked success.

START with a source-specific implementation plan for the first slice, not a giant new framework.
