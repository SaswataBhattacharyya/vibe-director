# Active fixes — latest source continuation (2026-11-06)

**Read first:** [code review](CODE_REVIEW_2026-11-06.md), [unified chat/three-pane design](UNIFIED_CHAT_AND_PANES.md), `AGENTS.md`, the active Git HEAD, and relevant directory `change_readme.md`. This supersedes Q01–Q08 as a **to-do list**; earlier [Q01–Q06](Q01_Q06_RESULTS.md) and [Q07–Q08](Q07_Q08_RESULTS.md) are implementation history and regression baselines, not tasks to repeat.

**Authorization:** This review request authorizes documentation/code review changes. It is **not** a new blanket authorization for application-code changes, live Codex sidecar execution, GPU/paid provider generation or deleting project data. On continuing implementation, follow the owner's currently explicit approval; plan each affected slice and report tests and cleanup. No user-facing workflow stage is mandatory.

## Priority and task dependencies

| Card | Priority | Depends on | Status at reviewed SHA | Goal |
|---|---|---|---|---|
| R01 | P1 reliability | Q07 | **Open, source-confirmed** | Recover unmapped submitted job after abrupt exit |
| R02 | P1 reliability | computer adapter | **Open, source-confirmed** | Supervise blocking computer stdin delivery |
| UX01 | P0 UI | shared DirectorRuntime | **Open** | All three panes independently collapsible |
| UX02 | P0 function | Q07/Q08, Editor service | **Open** | Central chat can initiate existing Editor brief/plan workflow |
| UX03 | P0 UI | UX02 | **Open** | Remove old Vibe Editor chat without losing approvals/tools |
| UX04 | P1 UX | UX02/UX03 pattern | **Open** | Consolidate older screenplay/prompt/video/image/3D chats |
| AG01 | P1 agent | existing tool/task services | **Open** | Extend action registry + verified surface-specific context |
| AG02 | P2 film | AG01, generation/Editor services | **Open** | Multi-step film DAG, evidence-backed QA, retakes/finishing |
| CR01 | P2 creative | AG01 | **Open** | Optional type/visual/directing jackets; independent storyboard |
| VID01 | P2 video | versioned validator/worker review | **Open** | Reference manifest and separately-versioned LTX OFF |

**Implementation scheduling note:** Fix crash/timeout regressions before relying on uncontrolled long-running agent work; UI-only UX01 can be independently staged if approved. UX03 must **never** precede UX02. Migration UX04 is incremental by tool; no mass deletion.

## R01 — Recover submission intent after process death
**Anchors:** `agent_tasks.py::poll, _find_job, _validate_job, _map_job, run`; `DirectorConversation.tsx::TaskCard`. Current `poll` returns an unbound `submitting` row if `invocation.job_id` is empty, and UI lacks a reconcile action for that state. Under the project lock, find the job by frozen `agent_invocation_id`/owner/tool, validate its exact request and bind when found; **GET must not create a new job**. If no job exists, expose precise recoverable status/action, not silent resubmission. Preserve no-replay computer journal safeguards. Tests: three crash windows, duplicate/mismatch, original reused exactly once, UI reload, disposable state cleanup.

## R02 — Bound computer stdin delivery
**Anchors:** `agent_computer.py::run`. It writes input to a pipe before establishing its deadline. Implement nonblocking/bounded delivery or a supervised stdin writer with a real bounded lifecycle, while still watching process termination and journal bytes. A child that never reads stdin must be terminated and reaped with no orphan thread; slow reader and BrokenPipe are controlled failures; no automatic retry of uncertain work. CPU-only fixture with short injected timeout; report journal/proc cleanup, no external Codex call.

## UX01 — Independently collapsible LEFT / CENTER / RIGHT
**Anchors:** `StudioShell.navClosed`, `DirectorWorkspace`, `DirectorConversation.open`, `DirectorRuntime` portal and `director-runtime.css`. Keep sidebar design. Lift center/right open states to a shared project-scoped controller; add always-visible restore controls and proper grid/resizer states, responsive rules. Do not unmount children or chat, throw away form drafts or hide focusable elements incorrectly. Test every pane combination, refresh, keyboard, mobile, route and project switches. Use [exact design](UNIFIED_CHAT_AND_PANES.md#change-a--one-state-authority-for-the-centerright-pane).

## UX02 — Editor bridge BEFORE removing the old composer
**Anchors:** `VibeEditorPage.submit/command/ensureProject`, `vibe_editor.command`, `agent_conversation.RESPONSE_SCHEMA`, `agent_tools`, `agent_tasks`. New shared Director chat currently cannot start an Editor brief; old Editor composer is sole path. Provide typed project+Editor-session+selection/revision context and `editor.prepare_brief` action that calls the existing trusted command (after validation), not the renderer. Proposed edit plan and creative brief remain editable/reviewable. The second Editor clearance remains explicitly required. Accept: user makes new edit from central chat with real selected assets, brief and plan arrive in correct saved session, no hidden render. Test wrong owner, wrong edit session, stale revision, selected range, refresh, retry.

## UX03 — Remove duplicate Editor chat + nested two-pane
**Anchors:** `VibeEditorPage.tsx:138–153`, `EditorWorkspace.tsx`, `vibe-editor.css`. AFTER UX02 tests pass, remove `editor-composer`, message-send controls, second model selector, old chat transcripts as primary UI and Editor's nested two-column `<EditorWorkspace>`. Keep session picker, output preview, asset selection, exact in/out ranges, timeline JSON/UI, style history, brief+plan clearances, job status, pause/cancel/retry, export, legacy **read-only session history**. Preserve all Editor backend tables/sessions and unchanged renderer. Do not delete `EditorWorkspace.tsx`: TRELLIS and Media Prep use it. A screenshot must show just the shared Director conversation and right Editor tabs.

## UX04 — Remove other redundant chats incrementally
**Anchors:** `ScreenplayDirector`, `PromptDirector`, `CreateWorkspace.CreateChat`, `ImageAssetsDirectorChat`, `TextToImagePage.t2i-chat`, `TrellisPage.StudioChat`, `MediaPrepPage.StudioChat`. For each, first add a typed shared-chat action with actual selected page context and surviving Review/Apply controls, idempotency/recovery, then remove the extra composer and chat log. Keep the image/video prompt fields and storyboard proposal controls because these are work-surface **tools**, not chat duplicates. Preserve Media Prep itself entirely; consider its legacy chat UI only after parity without processing changes. `StudioChat.tsx` exports the unrelated `studioRequest` helper; do not remove the module until its other call sites migrate safely. Cover one route at a time with tests.

## AG01 — Real shared action/context bridge
**Anchors:** `agent_conversation`, `agent_tools`, `agent_api`, `agent_skills`, `agent_tasks`, `frontend/src/lib/agent-context.ts` and `DirectorRuntime`. Current explicit intents are discuss, whole-asset MP3, last-frame. Expand through typed allowlisted adapters, with scene/shot/prompt/editor session IDs, selected ranges, frozen hashes and expected revisions; show unsupported capabilities honestly. Do not open a generic unvalidated command endpoint. Preserve skill source/permission separation, global/project skill resolver, project knowledge, trusted render/worker boundary. Start with Editor action (UX02), then screenplay/prompt proposals, image drafting, video generation job submission, analysis and export. Test each tool from both Director and Editor contexts.

## AG02 — Verified multi-step filmmaking
Add a durable *dependency* graph for plan→approval→create/inspect/retake/edit/export without imposing a *manual page* wizard. Task steps have stable identity, output refs, errors, budgets and idempotency; a model-generated sequence is not proof that tools ran. Preserve source clip history. Quality inspection requires actual frame/audio evidence and timestamped defects; unsupported analysis must say blocked. Editor handoff carries real registered clips/ranges; complete only after validating finished media. No paid/GPU in ordinary regression tests.

## CR01 — Creative profiles and storyboard, separate from chat migration
Optional production type + visual style + directing style; versioned creative jackets only, never prerequisites for manual create. Storyboard comic panels with image/action/dialogue/duration; panel != render job and multiple panels may share one clip. Preserve current source/shot revision ownership, FFLF automation pause, Media Prep and fast manual routes.

## VID01 — Video reference prep / LTX OFF
Build exact reference manifest with image/video/audio slot mapping and actual hash-bound asset IDs. R2V image reference is not guaranteed first-frame conditioning; only FL2VA binds true first/last inputs. Preserve distinct prompt caps and durations from each actual validator. LTX ON/OFF needs a separate frozen workflow/versioned request, output validity and no-refinement worker tests; do not add fake boolean to existing v2.

## Code simplicity / test hygiene
Use code-simplification + ponytail + blast-radius practices: smallest **readable** complete patch, no unnecessary new framework, behavior-changing code separated from pure refactors, no giant `App.tsx` or `isolated_server.py` additions. Use isolated dummy PNG/TXT/WAV/MP4 and DB/project IDs, clean after success/failure, verify no leftovers. Never delete real project media. Run focused Playwright + unittest + build and describe actual results, not a promise.

## Cleanup of previous guides
Q01–Q08 are **done as bounded implementations** per source and historical test reports; completed feature cards should not be used as future work. Keep result/evidence files for regression and audit. Directory `change_readme.md` files should point at these *active* tasks only where code is actually unfinished. Do not delete a reference file merely because one small feature shipped if it still contains instructions for unresolved integrations.
