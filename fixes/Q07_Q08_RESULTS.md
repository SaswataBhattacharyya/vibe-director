# Shared Director implementation results — 2026-11-06

## What is working locally

Q01–Q08 have local implementations. This is a tested MP3/continuity slice, scoped computer adapter and shared workspace foundation, **not completion of the full filmmaking blueprint**. Implementation is now paused at the owner's request. Local review found two unresolved defects: abrupt-exit submission reconciliation and computer stdin timeout coverage. See repair cards R01/R02 in [QUICK_FIX_TASKS.md](QUICK_FIX_TASKS.md); existing passing tests do not cover those failures. No application fixes were applied during this review.

- Shared persistent project Director on Director and Editor routes; route changes/hide/reload retain drafts. The existing Editor specialist workflow and its brief/plan/render approvals remain independent.
- Both surfaces use the same typed discovery, selected-skill/context loader, conversation store and durable task gateway. Chat uses the existing structured reasoning provider only on Send; development/acceptance mocked reasoning. The host validates proposals; a model reply never dispatches tools directly.
- Exact plan approval binds owner, revision/hash, whole-asset IDs/hashes and quality. Run revalidates inputs, preserves original bytes, creates the existing audio-utilities job and maps it before dispatch. CPU FFmpeg produces registered, hash-checked playable MP3. Offers to Editor require the existing selection/approval flow; soundtrack is never silently replaced. Whole-asset extraction does not claim source-range trimming.
- Task events, invocation identity and job correlation survive acknowledgement loss. Concurrent/repeated Run does not allocate duplicate jobs. Missing/mutated jobs and uncertain staging require reconciliation, not blind replacement. A confirmed job-free orphan invocation can be cancelled; its historical staging is retained. Existing workers and recovery remain authoritative.
- Revisioned project notes are explicitly saved with compare-and-set. They enter both surfaces' reasoning context and project snapshots. Derived graph reads preserve source identities and avoid discovery/recovery writes.
- All 13 blueprint craft skills are explicitly registered in place alongside the three existing application skills. Selected craft context includes the shared contract. The launcher supplies global Codex/agents roots by default and respects an explicit override; no repeated export is needed. At most six selected skills enter a bounded context; discovery does not load the entire catalogue into the model.
- Live restarted app: 16 application skills available; 80 global skills available; 54 global symlink entries unavailable under the safe-root policy. This project has no local skills directory, honestly shown as unavailable. Skill availability grants no execution permission. The separate computer adapter requires explicit task approval and a selected access mode. Tools are shared across projects; selected media, tasks, conversation and notes remain project-owned.
- Scene Backgrounds replaces the displayed Worlds label without renaming internal asset roles/IDs. Choose a base location image, scene/shot and condition (e.g. damaged or slime-covered); Prepare creates an editable existing Qwen Image Edit request with the base reference. No generation occurs until the existing Generate action. Prompt/frozen-reference lineage preserves the connection. No new parallel location database was introduced.
- Desktop conversation width is resizable by pointer or keyboard and saved per project; mobile switches conversation/work surface without unmounting either. Shared chat/work surface uses existing appearance tokens, consistent spacing, responsive layout, visible focus and an unobstructed composer above the footer. Live screenshot review exposed a nested three-column squeeze on Create; its original prompt assistant is now a collapsible panel below full-width controls. Existing field-edit/Apply checks remain.
- Live debug journal was full (8 MiB); the recorder now pauses repeated permanent 4xx rejection rather than uploading the same batch every second. Existing log retained. An explicit recording stop/start controls recovery.

## Scoped computer and continuity additions

- Both Director and Editor expose Application tools (default), Project only and Full access. Project/full messages prepare an inert computer task; review shows the frozen instruction, mode, project folder and model. Approve then Run is explicit. Changing access scope creates a new plan revision and invalidates approval.
- Project only invokes installed Codex CLI with a named filesystem profile: project write, minimal system read, unrelated files and network denied, minimal environment. The installed Codex binary directory is readable for sandbox startup. User configuration, project trust, hooks, apps/plugins, web search and multi-agent execution cannot silently expand the grant. Full access deliberately permits host filesystem/network; prompt restrictions are not an OS security guarantee.
- Computer mutations require a local Host/same-origin check and a process-session nonce. No CORS grant or generic shell endpoint. Durable job correlation, exact approval, bounded private journals/reports, process-group cancellation and a start marker prevent automatic replay after uncertain filesystem effects. A returned report is not a registered, inspected media output. Interactive browser/desktop control is explicitly unavailable.
- Continuity uses the existing last-frame extractor in a CPU durable job. A single approved registered video is hash-checked; successful output is an owned registered PNG preview. Original media remains unchanged. No replacement generation engine or GPU admission bypass.
- Real Codex/provider execution has **not** been exercised. Worker tests mock the provider; the installed Linux sandbox itself was tested offline without a model call. Unsupported CLI/config versions fail closed. Owner authentication/model availability and a live execution remain acceptance gaps.

## APIs and persistence

Computer capability: `GET /api/agent/computer-access` (local browser session grant; never log its token).
Read discovery: `GET /api/agent/tools?workspace_id=...`, `/skills?workspace_id=...`, `/projects/{owner}/context`.
Shared state: `GET|POST /api/agent/projects/{owner}/conversation` and `/knowledge`.
Tasks: `GET|POST /api/agent/projects/{owner}/tasks`, `GET /tasks/{task}` and `POST /tasks/{task}/{approve,run,revise,cancel}`. Strict fields, owner checks and error envelopes; unavailable runtime returns 503 with recoverable persisted task.

`agent_task_schema.py` adds tables in the existing production ledger: `agent_tasks`, immutable `agent_task_plans`, exact `agent_task_approvals`, correlated `agent_invocations`, ordered `agent_task_events`, idempotent `agent_messages`, immutable `agent_knowledge`. Owner-consistent foreign keys and uniqueness constraints supplement service checks. No third DB or media bytes in SQL. Existing snapshots include owned rows; moved-project tests restore approvals and notes. Live/recovery invocations block Save; draft/approved-only tasks do not. Project SQLite context managers now close connections while preserving transaction behavior; other test/service connection warnings remain.

## Evidence

- Backend: **76 tests ran: 75 passed, 1 opt-in sandbox test skipped** across `test_agent_computer`, `test_agent_continuity`, `test_agent_tasks`, `test_agent_editor_tool_handoff`, `test_agent_skills`, `test_agent_api`, `test_agent_tools`, `test_projects`, `test_audio_utilities_integration`, `test_media_catalogue`. Includes CPU FFmpeg MP3/PNG output, unchanged original digest, injected failure, stale approvals, duplicate submission, recovery, cancellation and moved project. After final permission/config changes the focused ten-test subset passed (nine passed, one opt-in skip).
- Offline installed sandbox: `VIBE_TEST_CODEX_SANDBOX=1 python -m unittest story_builder.tests.test_agent_computer.AgentComputerTests.test_real_project_sandbox_hides_sibling_and_blocks_network`: one test passed. Project write succeeds; sibling read, symlink escape, outside write and socket creation are denied; outside original bytes unchanged. This is OS permission evidence, not live model acceptance.
- Browser: **18 passed** in the final isolated run of `agent-inspector.spec.mjs`, `director-runtime.spec.mjs`, `create-panes.spec.mjs`, `debug-recording.spec.mjs`. Both routes exercise computer mode freezing/approval/report display, continuity PNG, MP3/handoff, skills/context, notes, scene variation, retained prompts, keyboard resizing/reload/mobile and footer bounds. The new selector initially pushed Send below the footer when context opened; fixed composer height/scrolling and reran all 18.
- Browser isolation: pagehide keepalive autosaves escaped Playwright routes during teardown. The test Vite proxy now points to closed loopback port 1 instead of production. Rerun logs confirm escaped requests are refused at port 1. Three verified fixture-owned browser-memory JSON files (`story-aaaaaaaaaaaa`, `story-bbbbbbbbbbbb`, `workspace-a`) were removed after checking fixture source, contents, absence of owner rows in both production databases and absence from the folder registry; no user project was removed. Tests using an explicitly supplied live UI URL are intentionally outside this mock-server guarantee.
- `npm run build`: TypeScript and production build passed; existing large-bundle warning remains.
- Restarted the actual app only after zero active/unresolved jobs were found in local job/ledger records and backed up both ledgers using SQLite backup to `local_data/backups/before-agent-runtime-20261106-102119/`. Verified live discovery/skill lists in browser and read-only HTTP. Did not send a live prompt or generation request. User project shot-preparation reports a stale saved T2V prompt; no silent regeneration/rewrite was attempted.
- Graphify code-only full refresh: 5,135 nodes / 15,540 edges at this check. 89 zero-node inputs (largely JSON/config) and skipped unsupported files mean incomplete coverage. Depth-2 results were discovery candidates; listed relationships manually confirmed. Source-anchor artifacts: `.review/q01-q06-impact.json`, `.review/q07-q08-impact.json`; risk remains high at persistence/recovery boundaries. No exhaustive caller/branch coverage claimed.
- Existing prior baseline browser issues/limitations are recorded in Q01_Q06_RESULTS.md. The stale Create fixture is now corrected and the unchanged Apply safety behavior passes; unrelated voice-selector fixture issue remains outside these focused checks.

## Cleanup and live state

Backend test-owned temporary media/databases/projects are guarded by fixture teardown, including injected failure; removal is asserted. Earlier eight named browser roots and two pointers were removed. The two additional continuity/computer browser roots and two pointers, including failed runs, were also removed with absence asserted. Screenshots were inspected before removal. Review probes also verified disposable task/database/media cleanup and terminated/reaped the non-reading CPU child. No existing user project/media/history was deleted. Production ledger backups and existing debug logs are deliberately retained, including the additional `before-computer-runtime-20261106-105735/` backup. The old idle image worker ignored TERM during shutdown; only that confirmed worker was forcibly stopped before restarting the normal launcher. The normal launcher remains running for the owner; image/video workers are idle unless the owner explicitly submits work.

## Remaining blueprint work

1. General approved multistep task graph, pause/stage budgeting/replanning and skill bindings. Current notes/derived graph are not a complete editable film knowledge graph.
2. Connect more concrete adapters: screenplay/shot proposals, image/video/audio repair, take inspection, Editor and export. Current approved application execution supports whole-asset MP3 and last-frame PNG; computer reports do not substitute for registered media adapters.
3. Optional composable creative profiles, independent editable comic storyboard/panels and scene backfill without screenplay prerequisites.
4. Exact model-aware generation manifests and versioned LTX-off. Existing pipeline remains unchanged; no fake toggle or readiness claim.
5. Evidence-based audiovisual QA, selective retakes and complete reviewed mixed-media film assembly/export through existing renderer. Real generated-media acceptance requires owner-started runs or explicit authorization.
6. Complete live acceptance of the scoped Codex computer adapter, add an explicitly authorized browser/desktop adapter, and validate external HyperFrames Studio/OpenMontage/Backlot installation, license and authentication. Installed skills alone do not provide these tools.

These are remaining implementation work under the latest authorization, not a claim that Q01–Q08 solve the complete product. Do not launch paid/GPU workloads to accelerate them. New sensitive runtime grants must be explicitly approved. UI screenshots/mocks cannot establish actual generated-film quality.

## Rollback

Disable the new chat/task entry points first; let identified owned jobs settle or cancel through their existing services. Retain task/job/media history. Revert only this reviewed patch, preserving prior local changes; never reset the checkout. Additive tables can remain unused; do not DROP them. Pre-change ledger backups are evidence/recovery inputs, not files to overwrite onto a running service. Old binaries may reject snapshots containing new tables; downgrade compatibility is not promised. Preserve the shared audio submission contract until both manual and agent callers have been restored. Generation engines, GPU policy, output destinations and original media are not rollback targets.

## Changed files in the combined local patch

Includes earlier guide/Q01–Q06 work and this continuation; not every file was authored in this continuation.

- `.review/guide-assessment.json`
- `.review/q01-q06-impact.json`
- `.review/q07-q08-impact.json`
- `backend/story_builder/change_readme.md`
- `backend/story_builder/isolated_server.py`
- `backend/story_builder/services/agent_access.py`
- `backend/story_builder/services/agent_api.py`
- `backend/story_builder/services/agent_computer.py`
- `backend/story_builder/services/agent_continuity.py`
- `backend/story_builder/services/agent_conversation.py`
- `backend/story_builder/services/agent_graph.py`
- `backend/story_builder/services/agent_knowledge.py`
- `backend/story_builder/services/agent_permissions.py`
- `backend/story_builder/services/agent_skills.py`
- `backend/story_builder/services/agent_task_schema.py`
- `backend/story_builder/services/agent_tasks.py`
- `backend/story_builder/services/agent_tools.py`
- `backend/story_builder/services/audio_utilities.py`
- `backend/story_builder/services/change_readme.md`
- `backend/story_builder/services/director_skills.py`
- `backend/story_builder/services/media_discovery.py`
- `backend/story_builder/services/projects.py`
- `backend/story_builder/services/vibe_editor.py`
- `backend/story_builder/services/video_repertoire.py`
- `backend/story_builder/services/video_repertoire_worker.py`
- `backend/story_builder/tests/change_readme.md`
- `backend/story_builder/tests/test_agent_api.py`
- `backend/story_builder/tests/test_agent_computer.py`
- `backend/story_builder/tests/test_agent_continuity.py`
- `backend/story_builder/tests/test_agent_editor_tool_handoff.py`
- `backend/story_builder/tests/test_agent_skills.py`
- `backend/story_builder/tests/test_agent_tasks.py`
- `backend/story_builder/tests/test_agent_tools.py`
- `backend/story_builder/tests/test_audio_utilities_integration.py`
- `backend/story_builder/tests/test_media_catalogue.py`
- `design/vibe-editor/change_readme.md`
- `fixes/CODEX_CHANGE_README_PROMPT.md`
- `fixes/FILE_CHANGE_MATRIX.md`
- `fixes/Q01_Q06_RESULTS.md`
- `fixes/Q07_Q08_RESULTS.md`
- `fixes/QUICK_FIX_TASKS.md`
- `fixes/SOURCE_ASSESSMENT.md`
- `fixes/change_readme.md`
- `frontend/playwright.config.mjs`
- `frontend/src/AgentInspector.tsx`
- `frontend/src/CreateWorkspace.tsx`
- `frontend/src/DirectorConversation.tsx`
- `frontend/src/DirectorRuntime.tsx`
- `frontend/src/DirectorWorkspace.tsx`
- `frontend/src/ImageAssetsPage.tsx`
- `frontend/src/ProjectKnowledge.tsx`
- `frontend/src/SceneBackgroundVariant.tsx`
- `frontend/src/StudioShell.tsx`
- `frontend/src/VibeEditorPage.tsx`
- `frontend/src/agent-inspector.css`
- `frontend/src/change_readme.md`
- `frontend/src/director-runtime.css`
- `frontend/src/lib/agent-api.ts`
- `frontend/src/lib/agent-context.ts`
- `frontend/src/lib/agent-tasks.ts`
- `frontend/src/lib/change_readme.md`
- `frontend/src/lib/debug-recorder.ts`
- `frontend/src/main.tsx`
- `frontend/tests/agent-inspector.spec.mjs`
- `frontend/tests/create-panes.spec.mjs`
- `frontend/tests/debug-recording.spec.mjs`
- `frontend/tests/director-runtime.spec.mjs`
- `graphify-out/cache/stat-index.json`
- `graphify-out/graph.json`
- `graphify-out/manifest.json`
- `skills/change_readme.md`
- `start_vibe_director.sh`
- `graphify-out/cache/ast/v0.9.17/*.json` (50 generated extraction-cache files at this check).
