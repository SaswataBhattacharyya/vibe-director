# Bounded implementation cards

Q01–Q08 have local implementations; Q07/Q08 still have the two review defects below. See [Q01–Q06 results](Q01_Q06_RESULTS.md) and [Q07–Q08 results and remaining roadmap](Q07_Q08_RESULTS.md). **Implementation is paused at the owner's request on 2026-11-06.** The following cards guide future repairs; they do not authorize resuming work. GPU/paid-provider execution still requires explicit authorization.

Read [master scope](change_readme.md) and [assessment](SOURCE_ASSESSMENT.md). Current source supersedes historical proposed contracts. In particular, MP3 metadata now reports execution enabled through exact-plan approval; last-frame continuity now executes through the same approved CPU gateway. Persistent chat, project notes and the shared shell foundation have also been implemented; general film orchestration remains outstanding.

## Review repairs before expanding Q07/Q08

### R01 — Recover submission intent after process death (P2)

**Source anchors:** `backend/story_builder/services/agent_tasks.py::run/poll/_find_job/_validate_job/_map_job`; `frontend/src/DirectorConversation.tsx::TaskCard`; `frontend/src/DirectorRuntime.tsx::refresh`.

**Confirmed trigger:** process exits after committing `submitting` and creating job JSON but before mapping its ID. Unlike an ordinary caught exception, abrupt exit never sets `recovery_required`. GET polling returns the unmapped row unchanged; the UI offers Cancel but no Reconcile for `submitting`. The task stays stuck even though a durable job exists. A disposable CPU fixture reproduced this with `KeyboardInterrupt` at `_map_job`; an explicit service `run` recovered the original job without duplication.

**Small repair:** reconcile existing submission intent during polling under the existing project lock, using frozen invocation/owner/settings/input validation before mapping or observing. If no job exists, expose a deliberate recoverable state/action rather than silently creating a replacement during GET. Reuse existing recovery methods; do not create a second allocation path. Preserve uncertain staging and the no-replay computer journal guard.

**Focused acceptance:** abrupt exit before job creation, after creation/before mapping and after mapping; reload through GET plus browser UI; original job reused exactly once; mismatched/duplicate job rejected; no automatic replay of computer side effects. Keep the current caught-exception/concurrent-run regressions. Temporary fixture roots/DB/media must disappear even on injected failure.

**Rollback:** revert only reconciliation/UI changes, retain invocation/job/history records. No schema change expected.

### R02 — Bound computer input delivery as well as execution (P2)

**Source anchors:** `backend/story_builder/services/agent_computer.py::run` (stdin write precedes deadline); `backend/story_builder/tests/test_agent_computer.py`; existing process cancellation/guard code.

**Confirmed trigger:** an approved instruction plus skills/notes exceeds pipe capacity and the child stops before reading stdin. Synchronous `stdin.write` blocks before the timeout/journal-limit loop starts. A CPU-only child that sleeps without reading reproduced the blocked 100 KB write; the probe terminated/reaped its child and joined its writer. No Codex/model request was made.

**Small repair:** start the deadline before input delivery and use bounded input delivery that keeps timeout, log-limit and cancellation supervision active. Preserve streaming-to-private-journal behavior, process-group termination/reaping, report budgets and the exclusive execution marker. Avoid introducing an unbounded writer thread or buffering all child output in memory.

**Focused acceptance:** real disposable CPU child that never reads stdin, a slow reader, early exit/BrokenPipe, cancellation during delivery and normal report success. Use a short injectable test timeout; assert child/group cleanup, no live writer and no automatic replay. No provider/GPU required.

**Rollback:** revert only worker input-delivery changes; retain private journal/report/history. No API/schema change expected.

## Q01 — Hide managed audio staging from media discovery

**Outcome:** browsing does not add internal input copies as project assets. Existing originals and published derivatives remain usable. Separate preflight repair, not part of Phase 1. Small fix; shared catalogue regression risk.

**Read:** `services/audio_utilities.py::stage_assets/run_job`, `services/media_discovery.py::_discover_locked`, `services/media_library.py::list_assets`, `services/storage_paths.py::generated_root`, plus `test_audio_utilities_integration.py` and recursive discovery tests in `test_media_catalogue.py` (all backend paths below `backend/story_builder/`).

**Implement:** exclude the precise managed `generated_root(root, workspace)/utility_inputs` subtree when walking authorized project/tool-library sources. Prefer the discovery seam over relocating inputs: historical job JSON stores their paths, and retries must keep working. Derive the exclusion from storage helpers; do not skip every directory named `generated` or `utility_inputs` anywhere. Handle both canonical project storage and saved-project discovery locations deliberately; if mapping cannot be established, report the unsupported case rather than broadening exclusion.

**Do not:** delete original files, staging directories of existing jobs, catalogue history, or rewrite frozen job requests. A discovery skip prevents new entries; already-indexed staging entries require an explicit separate decision. Do not claim this patch cleans historical memberships. That limitation is acceptable for this preventive card and must be reported.

**Accept/tests:** reproduce the existing safety-trip failure, fix it without changing its expected asset set; add discovery tests for `story-*` and `tool-library`, successful/failed staging, legitimate nested media and real published MP3. Confirm original bytes/hash retained. Use temporary roots. Run audio integration + media catalogue tests; GPU paths mocked. No worker launch needed. No schema/API change.

**Rollback:** revert only discovery exclusion/tests; media/job paths unchanged. Finish by reporting whether old indexed copies still appear.

## Q02 — Share audio utility submission without changing the API

**Depends:** Q01 for staging visibility; can be reviewed before agent work. Small service extraction, medium behavioral risk.

**Read:** `isolated_server.py` utility route (around 886), `audio_utilities.validate_settings/stage_assets`, `video_repertoire.configure_roots/create_job/start_job`, worker dispatch, output destination `freeze`, audio integration tests. Find every current caller of staging before editing.

**Implement:** move validation/capability selection/staging/job creation into one focused helper, preferably in `audio_utilities.py` unless imports justify a small module. Keep all three operations (`extract_mp3`, `noise_cleanup`, `demucs_stems`) supported by the same route. Keep HTTP/error mapping in the API layer. Preserve exact body keys, settings defaults, 202 public job projection, blocked-tool and worker-unavailable 503 codes. No backend HTTP call to itself.

**Failure ownership:**
- Partial staging before any durable job: clean only the new staging directory owned by this call, in a failure-safe path; preserve the original exception.
- Durable job created: inputs belong to that job. Dispatch failure may leave it queued; retain staging and job record. Do not delete/recreate/retry blindly. Q07 handles agent recovery.
- Test root configuration explicitly. A `root` helper argument does not override `video_repertoire` module configuration. Preserve destination freezing and existing recovery behavior.

**Accept/tests:** exact manual API parity for all operations; unknown field/quality/wrong-owner rejection; capability blocked; partial-stage failure cleanup; persisted-job dispatch failure retains inputs; CPU MP3 registered and playable. Mock containers/GPU/provider, never run them. No new DB.

**Rollback:** restore inline route logic and remove helper only after callers are restored; do not touch saved jobs or media.

## Q03 — Shared tool metadata API

**Depends:** none; Phase 1 starts here. Small/medium API task.

**Read:** `isolated_server.create_app`, Editor API delegation/error conventions, project ownership resolver, existing utility/video capability return shapes. See `backend/story_builder/change_readme.md`.

**Implement:** focused `services/agent_tools.py` and `services/agent_api.py`; one server dispatch branch with configured root/ledger/story dependencies as needed. Initial route: `GET /api/agent/tools?workspace_id=...`. Start with metadata for `audio.extract_mp3` and `video.continuity_last_frame`, mapped to the existing services; document generated-output prerequisites for continuity. Expand only for a requested, traced adapter. Register only concrete service-backed descriptions or explicitly blocked/navigation-only capabilities. Separate supported/installed/ready/executable facts; metadata availability is not permission to execute. Use explicit nested input schemas; do not implement a generic interpreter or execution endpoint.

**Contract:** `{tools:[{id,effect,input_schema,status,execution_enabled:false,reason?}]}`; effects `read|draft|submit|external|destructive`; statuses `available|blocked|unknown|navigation_only`. Schema and return types must match actual handlers. Resolve/validate owner context server-side including standalone tools; do not invent authentication merely by adding an actor field. Reject malformed/unknown query fields and unsupported methods. Keep existing error envelope.

**Accept/tests:** new `test_agent_tools.py`/`test_agent_api.py`: strict routing/fields, invalid/other-project context, blocked/unknown capability, no worker/provider/command launch. Capability mocks test actual operation-specific shapes. Existing Editor/audio/video routes unchanged. No DB or chat UI.

**Rollback:** remove new dispatch/metadata modules/tests. No persisted data.

## Q04 — Shared skill discovery and compatible context loading

**Depends:** Q03 API seam; Phase 1. Medium parser/ownership task.

**Read:** three existing live skill paths and supporting references, `director_skills.director_skill_context(video=...)`, its story/prompt callers, Editor `run_job` Markdown reader; `skills/change_readme.md`.

**Implement:** `services/agent_skills.py`; metadata-first discovery from explicitly configured installed global roots/providers, existing bundled roots, and approved project-owned roots. No full-home scan or recursive scan of all fixes. Namespace identity by provider/scope/id, preserve collisions explicitly. Content read uses canonical safe roots, bounded files/context, hash/version and approved relative references. Missing source stays unavailable. Blueprint skills become available only through an explicitly approved package-root registration; preserve current craft defaults.

**Contract:** `GET /api/agent/skills?workspace_id=...` metadata with stable ref, scope, description, hash/version, availability/reason. Selected context loading is a server service; add a narrow inspect endpoint only if Q06 needs it, with the same ownership and size rules. Never expose arbitrary filesystem reads. Skills grant no permissions.

**Compatibility:** first capture existing `director_skill_context(video=False/True)` content/ordering/hash labels/budget behavior. Adapt its loader only with parity tests. Editor's existing planner context must remain equivalent; sharing resolver does not make it tool-executable. No automatic addition of every skill to model context.

**Accept/tests:** `test_agent_skills.py`: disposable global/project roots, missing source/update/removal, duplicate IDs, traversal/symlink, reference escape, content limits, project isolation, legacy Director/Editor parity. No changes to global installed skills or blueprint package. No persistent bindings DB yet.

**Rollback:** restore original readers and remove resolver route; original skill files/references intact.

## Q05 — Derived project context without hidden writes

**Depends:** Q03; Phase 1. Medium ownership/projection task.

**Read:** story/board read services and revisions, `projects.sql_snapshot`, media manifests, durable job JSON, Editor state/document readers. Source facts and IDs are authoritative.

**Implement:** `services/agent_graph.py`, `GET /api/agent/projects/{workspace_id}/context`. Return bounded nodes/relations with kind, source ID, owner, revision/hash and provenance. Start with current workspace, assets, available story revision and relevant Editor session/job references. Missing story/board is normal. Do not invent scene/shot nodes or a parallel story store. Keep workspace IDs distinct from Editor session IDs. Do not dump unrelated rows, raw paths, secrets or all job requests.

**Read-only trap:** `list_assets` can register discovered files; `read_job` can change interrupted status. Use non-mutating projections of current registered state, or a narrowly reviewed read-only accessor if necessary. Avoid a broad media-library rewrite. “No data yet” is preferable to fabricating readiness.

**Accept/tests:** `test_agent_project_graph.py`: two projects + standalone; real source IDs/hash/revisions; missing/empty sources; no file/manifest/job/DB mutation while querying; no late ownership crossover. Snapshot/knowledge editing is Phase 3, not this card. No migration.

**Rollback:** remove context route/projection; no data written.

## Q06 — Compact shared discovery inspector

**Depends:** Q03–Q05; completes Phase 1. Medium UI task.

**Read:** `App.tsx` route return branches and kept-mounted video workspace; `StudioShell.tsx`; `ProjectController.tsx` owner/remount behavior; `EditorWorkspace.tsx`; `lib/editor-api.ts` ranges.

**Implement:** `lib/agent-api.ts`, `lib/agent-context.ts`, one focused `AgentInspector.tsx` and scoped styles, with narrow shell wiring. Share tool/skill/context display on Director and Editor. Reuse existing fetch/error conventions. Add only types for implemented endpoints. Requests bind owner; abort/discard stale responses on project switch. Handoff IDs/ranges use existing types; URL strings and filenames do not establish ownership.

**Do not:** build persistent chat/task panels yet, add execution buttons, duplicate Editor chat, alter Media Prep/sidebar, force an accepted screenplay, or restructure App to satisfy a speculative shell. If a later persistent chat must survive changing App branches, design its stable mounting separately; putting JSX in StudioShell alone does not prove stability.

**Accept/tests:** frontend typecheck; focused browser tests with stubbed discovery responses for both surfaces, project switching/late response, collapsed/mobile/keyboard use, direct Video Create without screenplay, and no submission calls on mount. Preserve unsaved forms and existing Editor panels. Test screenshots/output only in temporary test-owned directories; report if browser tooling unavailable.

**Rollback:** remove inspector wiring/components/types/styles; no app persistence changes.

## Q07 — Minimal durable approved one-operation task

**Depends:** Q02–Q05 and Q01; Phase 2. High-risk persistence/recovery task, not a quick unreviewed patch. Schema and transitions are implemented in `agent_task_schema.py` and `agent_tasks.py`; see the results for verified crash boundaries.

**Read:** configured `ProductionLedger` initialization/transaction patterns, `projects.DATABASES/sql_snapshot/assert_idle` and import schema checks; media `create_job/start_job`/queue recovery; Q02 helper. Do not add a third DB.

**Implement:** focused `agent_tasks.py` plus additive project-owned ledger tables: task identity/state; immutable plan revisions (`task_id,revision`, unique hash); approval bound to exact revision/hash/project/tool/input assets+hashes/settings; invocation row with unique owner/task-step/idempotency identity and stored job ID; ordered events. Declare owner-consistent FKs/indexes and enforce them in service checks/transactions. Do not put media bytes in DB. Keep claims/leases simple for one operation; no generic DAG engine yet.

**API:** under `/api/agent/projects/{workspace_id}/tasks`: POST proposes only; approve binds expected revision/hash/scope; run claims the invocation; GET polls; control only for operations actually supported. Unknown controls fail. Inputs changing after approval require a new revision/approval.

**Critical crash windows:** intent before creation; persist created job identity before dispatch; recover a crash between job creation and mapping without making a second job (use durable correlation in the frozen request and lookup or another reviewed atomic allocation design); persist/result reconciliation on acknowledgment loss. A unique DB key alone does not solve cross-store atomicity. Never retry an uncertain call by creating another job. Mark recovery-required until identity is resolved.

**Checkpoint/rollback:** test old snapshots, new row inclusion and load into a fresh configured root, conflicts/newer local records, moved folders and missing-global refs. Draft/approved-only tasks do not block Save; any owned live job does, even if task says paused. Additive schema rollback disables new execution/readers while retaining records; older binaries may reject new snapshots, so do not claim downgrades work automatically. Never drop history.

**Accept/tests:** `test_agent_tasks.py`, `test_projects.py` and named-project storage tests: propose never submits; stale/wrong-owner approval; mutated source; parallel duplicate run; crash at each boundary; queued-job dispatch failure; cancellation/retry semantics; registered/hash-verified output required for completion. Mock all workers first. No GPU/provider authorization implied.

## Q08 — Both chats complete the MP3 vertical slice

**Depends:** Q01–Q07; completes Phase 2. Medium/high integration task.

**Read:** Director chat entry points and Editor sessions/selection/command approvals, Q07 lifecycle client, existing media/audio preview and Editor selection APIs. Before implementation identify the exact Director chat surface; do not invent a second independent conversation store.

**Implement:** a narrow typed orchestration bridge using shared Q04 skills, Q05 context, Q07 approval/call lifecycle and Q02 submission. Natural-language reasoning proposes only the supported tool intent through the existing reasoning provider's structured JSON path. Keep the provider sandbox read-only; host code validates/executes approved calls. No assumed native tool-call SDK, raw shell, brittle phrase-matching-only demo, or fake completed progress. Mock reasoning during development.

**Flow on BOTH surfaces:** actual selected owned video/audio asset → proposed extraction plan/settings → exact approval → run/poll durable job → verified registered playable audio → offer attachment to Editor. Preserve original and selected video ranges. MP3 extraction currently operates on the whole selected asset; do not claim range trimming without a separately specified adapter. Never silently replace soundtrack or bypass Editor brief/plan/render clearances.

**Accept/tests:** `test_agent_editor_tool_handoff.py` plus Director route/client coverage; same gateway called by both; wrong workspace/session rejected; refresh/retry reuses job; late project response discarded; real CPU FFmpeg synthetic input produces a probed MP3 whose registered asset/hash is returned. No model/provider/GPU needed for acceptance tests. Verify original hash and temporary cleanup, including injected failure. Existing Editor manual workflow and Media Prep remain functional.

**Rollback:** disable/remove chat bridge first, keep in-flight task/job recovery available, retain task history/outputs. Never roll back by deleting user media or job rows.

## Later work and simplification

The remaining Phases 3–7 need source-traced cards. Persistent chat and revisioned project notes now exist. General task loops, independent storyboard drafts, LTX-off, additional execution adapters, film QA/assembly orchestration and browser/desktop access remain larger implementation work; scoped Codex computer tasks now exist, with live provider acceptance outstanding. The overall vision remains in the blueprint.

For a requested readability cleanup: choose one named function, trace callers/side effects, capture behavior tests, then make one equivalent refactor separately from a feature/bug fix. Large file size alone is not evidence. No unsolicited global rename/format/rewrite. Preserve asynchronous errors, exceptions, API shape, state timing, cancellation and recovery. Baseline failures stay recorded; tests may broaden only for an observed risk/failure.

Current continuation: approved CPU last-frame PNG and scoped Codex computer tasks are implemented alongside MP3. Both surfaces offer Application tools, Project only and Full access; each computer task freezes scope and requires exact approval. Offline sandbox and mocked worker tests differ from unperformed live model acceptance. Browser/desktop automation and general film orchestration remain incomplete. See `Q07_Q08_RESULTS.md` for evidence and changed files.
