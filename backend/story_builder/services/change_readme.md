# Backend services — only unfinished work

Read [current static review](../../../fixes/CODE_REVIEW_2026-11-06.md) and [active tasks](../../../fixes/ACTIVE_FIXES_2026-11-06.md). Q01–Q08 and CPU MP3/continuity/computer task foundations are implemented; old speculative sketches are obsolete. Preserve current owner-scoped gateway, graph projection, skill resolver, and ledger.

## Immediate R01 and R02
- **R01 `agent_tasks.py::poll`:** if an invocation is `submitting` with no `job_id`, GET presently returns the row and does not reconcile. Under existing project lock, find job by frozen invocation ID and correct kind, validate complete frozen settings/inputs/owner/tool and map if found; GET must not enqueue a new job. If none, return explicit recoverable state and deliberate action. Reconcile after abrupt process death; do not replay uncertain computer effects.
- **R02 `agent_computer.py::run`:** blocking `process.stdin.write` occurs before `deadline = time.monotonic() + 1800`. Supervise stdin nonblocking/bounded along with child, timeout, log quota and process group shutdown; prove no leaked child/thread after non-reading stdin. Do not weaken per-plan Full/Project grants or run paid/provider acceptance automatically.

## UX02: typed Editor action through the existing service
- `agent_conversation.RESPONSE_SCHEMA` supports only `discuss/extract_mp3/continuity_last_frame`. Add a *versioned* typed `editor.prepare_brief` proposal/action on current Editor session with real selected ranges, expected revision and owner. Validate server-side using Editor's existing project and session lookup, not user-provided names/paths.
- Use existing `vibe_editor.command` for brief/plan. No direct model execution of HyperFrames or unselected media. Preserve Editor's two clearances as distinct approvals. A typed agent task is not automatically clearance 1 or 2.
- `agent_api` and `agent_tools` should register one scoped action at a time and fail closed when not available. No generic text-based executor or duplicate persistence. `agent_messages` is new conversation authority; historical Editor `project.messages` remain valid read-only legacy history.
- General screenplay/prompt/image/video/QA adapters and multi-step DAG are later AG01/AG02; maintain exact T2V/R2V/FL2VA contracts, review-mode and GPU guards.

## Blast radius
`agent_task_schema` + `projects.sql_snapshot/save/open`, `audio_utilities`, `video_repertoire` and Editor projects all matter when altering execution. Check existing `test_agent_tasks`, `test_agent_computer`, `test_agent_editor_tool_handoff`, `test_agent_api`, `test_projects`, `test_audio_utilities_integration`, and relevant Editor tests; extend targeted coverage. Preserve ownership, idempotency, frozen media, recovery and no repeat shell side effects.

Keep modules small; do not append agent business logic to `isolated_server.py` or weaken `vibe_editor_render.py` trust boundary.
