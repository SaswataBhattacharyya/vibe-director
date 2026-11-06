# Vibe Director code review — 2026-11-06

**Reviewed source:** `SaswataBhattacharyya/vibe-director`, branch `vibe-director-current`, Git SHA `2d4878db60d6c8b5ffbcb3254dddc66d5db402ac`. This document is a **static source review** against the user's current UI screenshot and the preceding `fixes` requirements. **No new application build, browser test, live Codex request, GPU run or media test was performed in this review.** Prior test totals are reported, not independently reproduced, in `Q07_Q08_RESULTS.md`.

## Executive assessment

**Already implemented / reuse:**
- Q01–Q08 have source implementations and previously reported focused regression evidence. Do not rebuild them. The current `agent_api.py`, `agent_tasks.py`, `agent_skills.py`, `agent_graph.py`, `agent_conversation.py`, `agent_computer.py` and `agent_continuity.py` are present.
- `main.tsx` mounts `ProjectController > DirectorRuntime > App`. `DirectorRuntime` portals one project-owned `DirectorConversation` into the `DirectorSlot` rendered by `StudioShell > DirectorWorkspace`. This is an appropriate basis for a persistent, route-independent agent.
- Existing Media Prep audio, video continuity, durable job validation, project save/load, HyperFrames renderer, Editor media selection/ranges and two clearances remain available.
- `ProjectController` remounts child UI when the active project/version changes (`key={workspace_id:version}`). Keep that ownership fence; do not assume editor session ID equals workspace owner.
- Left sidebar is already collapsible; preserve its links and palette. `DirectorWorkspace` has pointer/keyboard resize and project-scoped width; keep those features.
- Three tool execution routes in `agent_tools.py`: `audio.extract_mp3`, `video.continuity_last_frame`, `computer.execute`. Structured chat currently proposes only MP3/last-frame, while selected access mode can prepare a separate scoped computer task.

**Confirmed gaps / failures from source and screenshot:**

| Priority | Finding | Exact evidence and impact | Required repair |
|---|---|---|---|
| P0 | **Two chatboxes on Editor** | `DirectorConversation.tsx` shared composer plus `VibeEditorPage.tsx:138–153` `editor-messages` / `editor-composer` inside `EditorWorkspace`; screenshot visibly shows both. User enters the wrong conversation or thinks approval history is unified when it is not. | Consolidate interaction into the shared Director. Preserve editor session/history and manual clearance controls in right work surface; remove old edit composer **after** working bridge. |
| P0 | **Editor chat migration has a real dependency** | `VibeEditorPage.tsx:88–91` `submit` calls `POST /api/editor/projects/{id}/command` with `action:'chat'`, which creates the brief job; `approve` and `prepare_plan` also use that Editor command API. Removing the old form alone would make creating new briefs impossible. | Add typed agent-to-Editor session adapter/intent; make central composer able to prepare Editor brief and expose plan/approval/status on right; then retire old composer. |
| P0 | **No independent collapse of right work surface** | `DirectorWorkspace.tsx` saves chat width, mobile `surface` switch. `DirectorConversation.tsx:45–50` collapses itself. There is no independent desktop `workOpen` state or always-visible work restore control. | Add right-pane collapse and explicit restore controls, preserve left `StudioShell.navClosed` and center collapse; deterministic layouts for all combinations. |
| P1 | **Other legacy chats remain** | `ScreenplayDirector.tsx:68–113`, `PromptDirector.tsx:89–121`, `CreateWorkspace.tsx:17,23–76`, `ImageAssetsPage.tsx:39–67,699`, `TextToImagePage.tsx:265`, `TrellisPage.tsx:42` (`StudioChat`), `MediaPrepPage.tsx:819` (`StudioChat`); Storyboard has a separate production instruction/proposal form around line 85. | Inventory each; migrate review/apply and saved recovery state to typed central actions or right-hand proposal cards; remove extra conversational UIs, **not** manual prompt fields or useful buttons. Media Prep processing remains unchanged. |
| P1 | **Central chat is not yet general-purpose tool orchestration** | `agent_conversation.RESPONSE_SCHEMA` allows `discuss|extract_mp3|continuity_last_frame`; `agent_tools.tools()` returns two media submit tools + computer.execute. `surface:'editor'` only changes prompt context and carries **no** editor session, selected ranges or active timeline. | Build typed surface/handoff context and an expandable reviewed action registry; do not make a model reply execute arbitrary tools or bypass approval. |
| P1 | **Submission crash reconciliation gap (R01)** | `agent_tasks.poll` returns immediately when invocation has no `job_id`. Abrupt process termination between persisted submission intent and job mapping leaves `submitting` stuck. Already reproduced in `QUICK_FIX_TASKS.md`. | Reconcile frozen invocation identity on read, without submitting during GET; return explicit recoverable state if job absent, preserve no-replay semantics. |
| P1 | **Computer input timeout gap (R02)** | `agent_computer.run` does blocking `process.stdin.write(prompt.encode())` **before** setting deadline. A child that never reads stdin can hang. Already reproduced in `QUICK_FIX_TASKS.md`. | Bound stdin delivery along with process/output supervision, with no leaked writer/child. |
| P1 | **Editor agent state is not Editor session state** | `DirectorRuntime.send` sends `{text,asset_ids,skill_refs,surface}`; Editor still separately owns `project.id`, `project.selection`, `project.pending`, `project.messages`. No automatic bridge for creative briefs and clip-range semantics. | Bind owner `workspace_id`, optional `editor_session_id`, expected Editor revision, asset IDs + exact selected ranges and source SHA; server revalidates. |
| P2 | **Legacy chat archives must survive** | Old Editor session messages, ScreenplayDirector/PromptDirector proposals, and browser-local prompt-chat recovery keys still have useful revision provenance. | Keep historic sessions readable in an explicitly labeled History/Previous proposals panel; no second send box or competing agent authority. Do not delete DB rows, saved revisions, style rules or source localStorage keys without proven migration. |
| P2 | **No complete filmmaking task graph yet** | Current `agent_tasks.py` says “Approved one-operation tasks”; no screenplay→storyboard→generation→QA→retake→Editor DAG. `agent_graph.py` is a derived read-only context, not a complete editable project knowledge graph. | Build dependency DAG in separate tested phase, reuse existing jobs, preserve non-linear manual workflows. |
| P2 | **Creative jackets and full video prompt/model integration remain unfinished** | Existing production type/directing setup is rigid; full optional visual style selection, independent boards, exact prompt manifests, LTX off, quality-backed inspection/retakes are not shown as implemented. | Keep as future phases; do not treat new chat shell as final app. |
| P2 | **Computer access is real but not validated end-to-end** | `agent_computer.py` launches installed Codex CLI with permissions; `Q07_Q08_RESULTS.md` records offline sandbox/mock tests only. `full` allows host files/network. | Require conspicuous scope confirmation; test live runtime only with owner approval. Browser/desktop control not available yet. |

## Code-quality / blast-radius review

- **Do not patch a CSS symptom only.** Hiding `editor-composer` in CSS would make the UI appear fixed while breaking the only Editor brief submission action. Must migrate intent before removal.
- **Do not delete `vibe_editor.py`, `vibe_editor_api.py`, `vibe_editor_render.py`, `ScreenplayDirector` proposal APIs or `PromptDirector` approved rules.** These own history, selected ranges, revision/CAS and trusted execution. Remove only duplicate **chat presentation**, then simplify orphaned client code with behavior tests.
- **Do not give every old chat a separate agent store.** The shared `agent_messages` is the conversation authority going forward; legacy messages stay historical, with link/import provenance if displayed.
- **Do not put orchestration in `App.tsx` or `isolated_server.py`.** Current `App.tsx` is >1200 lines and dispatcher >3700; use small React work-pane components, a typed shared frontend context, and narrow backend adapters.
- **Blast radius:** `StudioShell, DirectorWorkspace, DirectorRuntime, VibeEditorPage, EditorWorkspace, ProjectController, frontend/src/lib/agent-*, frontend/src/lib/editor-api.ts, agent_conversation, agent_api, agent_tasks, vibe_editor, vibe_editor_api, production ledger/projects` plus older embedded chat components and Playwright suites. The Graphify index is a discovery aid, not a proof that all consumers were reviewed.
- **Preserve** Media Prep tools/UI, originals/assets/hashes, saved project and Editor sessions, style learning, manual entry, frozen prompts/retakes, project recovery, output grants, GPU safety and separate approvals.
- **Approval models:** project tool task approval and Editor creative/render clearance are different; present them coherently, never silently treat one as the other.

## Suggested implementation order

1. **R01/R02 reliability** (or first if live agent is in use; failures are confirmed).
2. **UX01 shell**: independent, accessible three-pane collapse with no page remount; test before Editor migration.
3. **UX02 Editor bridge**: shared chat invokes existing Editor brief/plan workflow and shows exact editor session; preserve controls and old history.
4. **UX03 Editor duplicate removal**: retire composer and nested conversation split, keep right-side tabs and clearances, update the frontend tests.
5. **UX04 other page chat migrations**: screenplay/prompt/video/image/Trellis and Media Prep conversational widgets, one at a time; preserve their proposal/apply/recovery work.
6. **AG01 expanded tool/film DAG**: creative action catalogue, knowledge links, QA/retake/Editor delegation; only then make “produce a full film” execution promises.

See [the active tasks](ACTIVE_FIXES_2026-11-06.md) and [three-pane migration guide](UNIFIED_CHAT_AND_PANES.md) for precise changes and acceptance criteria.

## Testing evidence qualification

Previously reported in `Q07_Q08_RESULTS.md`: 76 backend tests (75 passed, 1 skipped); isolated browser tests (18 passed), production build passed, sandbox offline test. These are **historical Codex claims**, not results from this review. None of those tests prove that a single composer exists across all routes or that independent right-pane collapse works. Re-run against the exact checkout and add the new UX/agent tests before claiming completion.

No source files, user media or existing project records were modified by this review.
