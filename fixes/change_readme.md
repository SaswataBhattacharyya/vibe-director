# Vibe Director — active implementation entry point

**Current review baseline:** `vibe-director-current` at `2d4878db60d6c8b5ffbcb3254dddc66d5db402ac` (2026-11-06). Inspect `git status` and current HEAD before continuing; these are source-linked guides, not application fixes.

## What Codex must read now
1. [Current code review](CODE_REVIEW_2026-11-06.md) — verified source findings, issues and limitations.
2. [Active fixes, in dependency order](ACTIVE_FIXES_2026-11-06.md) — **current to-do list**, superseding completed Q01–Q08 cards.
3. [One Director chat and three collapsible panes](UNIFIED_CHAT_AND_PANES.md) — exact UI state, Editor migration, older chat inventory, tests.
4. [File ownership matrix](FILE_CHANGE_MATRIX.md) and applicable directory `change_readme.md` — narrow change boundaries.
5. `AGENTS.md`, `full_review.md`, and tool glossary; older [V2 blueprint](vibe-director-codex-agent-blueprint-v2/vibe-director-codex-agent-blueprint/README.md) for product vision and the 13 filmmaking skills.

## Confirmed implemented foundation (do not rebuild)
Q01–Q08 are implemented bounded features with prior reported tests; see [Q01–Q06 results](Q01_Q06_RESULTS.md) and [Q07–Q08 results](Q07_Q08_RESULTS.md). Latest source contains real DirectorRuntime/DirectorConversation, shared tool/skill/context services, durable project tasks, notes, MP3 extraction, continuity PNG, scoped computer tasks, and existing Vibe Editor/HyperFrames render. **This is not yet an agent that can produce a complete film.** Prior test counts are historical claims and were not rerun during this documentation review.

## New correction: one chat, not one chat per page
The shared persistent Director chat is the single interactive conversational surface. The left sidebar remains as designed; the center chat and right real work page must be independently collapsible. All three panes can collapse/restore without unmounting unsaved work. `VibeEditorPage` currently renders a second Editor composer and nested `EditorWorkspace`, as confirmed in source and screenshot. Other embedded chats exist in screenplay, prompts, Video Create, image generation, TRELLIS/3D and parts of Media Prep. **Bridge their actual tools, proposals and approval behavior into the shared Director first, then remove duplicate chat UI.** Do not delete session history, revision checks or working manual controls.

## Immediate code review priorities
- **R01:** abrupt-exit submission mapping missing; `agent_tasks.poll` can leave an unmapped task stuck.
- **R02:** `agent_computer.run` blocking stdin write precedes supervision deadline.
- **UX01:** all three panes separately collapsible, restorable, keyboard and mobile safe.
- **UX02:** central chat can actually initiate existing Editor brief/plan workflow in the active Editor session, with exact owner/selection/revision.
- **UX03:** remove duplicate Editor chat and nested split **after UX02 works**; preserve preview/media/timeline/style/export and two clearances.
- **UX04:** remove other old chats one page at a time after their action/recovery features are available through the one Director.
- **AG01/AG02:** expand typed tool/action graph and durable filmmaking DAG; optional creative jackets, model-specific prompts, QA and editing follow.

## Source authority / approvals / safeguards
Existing code and its expected revision/ownership/contracts are authoritative over historical proposals. A skill does not grant tool execution. Review the current authorization before touching application code; this specific request authorizes code review/documentation updates. Scope permissions and exact approvals remain required for computer, paid-provider, GPU and destructive operations. No automatic Git reset/pull, broad refactor or renderer replacement.

**Preserve:** existing left sidebar, Media Prep operations/UX, all manual entry pages, true asset IDs/hashes, saved edits/history, project Save/Load, durable jobs/recovery, published output, destination grants, and GPU safety (90°C/2100 MHz policy). No screenplay, storyboard or style gate for standalone tools.

## Code quality and tests
Use blast-radius, ponytail and code-simplification methods: small readable modules, reuse existing services, avoid giant App.tsx/isolated_server.py rewrites or speculative frameworks. Test success/failure/ownership/stale revisions/recovery. Generate dummy TXT/PNG/WAV/MP4 only inside isolated test-owned directories; automatically clean after both success and failure and verify deletion. Never remove real user media or pretend mocked tests prove audiovisual quality. No new GPU/paid-provider jobs without explicit authorization.

## Historical documentation policy
Q01–Q08 implementation cards are complete as bounded slices; keep their results as evidence, not future tasks. Older `SOURCE_ASSESSMENT.md` is a historical pre-implementation snapshot. The 13 blueprint skill files and architecture remain useful vision/specification, but may describe not-yet-integrated features; the active task list wins for current code implementation.
