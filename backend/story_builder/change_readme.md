# Backend boundary change README — current application

**Edit targets:** `isolated_server.py`, `services/production_ledger.py`, `services/projects.py`; NEW small `services/agent_api.py` and related services described in `services/change_readme.md`. **Proposal only; no implementation in this document.**

## 1. Add ONE agent API dispatch seam
`isolated_server.py` currently enters `app(environ,start_response)` around line 480 and delegates `/api/editor/` to `vibe_editor_api.handle`. Following the same adapter pattern, add **before generic route matching**:

```python
if path.startswith("/api/agent/"):
    from story_builder.services.agent_api import handle
    return handle(root, environ, start_response, _read_json, _json_response)
```

Use the existing WSGI envelope and error policy; **do not** make the HTTP dispatcher itself perform agent work, shell commands, or input staging. `agent_api.handle` must restrict methods, match routes exactly, validate `workspace_id` ownership (do not trust supplied IDs), and return the same error envelope as existing APIs.

Proposed v1 routes; create only when service contract and tests are ready:
- `GET /api/agent/tools?workspace_id=...` — metadata/capabilities only.
- `GET /api/agent/skills?workspace_id=...` — global/app/project metadata only; no secret skill payload.
- `GET /api/agent/projects/{workspace_id}/context` — scene/asset/task graph projection with provenance.
- `GET/POST /api/agent/projects/{workspace_id}/tasks` — inspect or propose a `draft` plan; **no execution from plan POST**.
- `POST /api/agent/projects/{workspace_id}/tasks/{task_id}/approve` — explicit owner approval of the exact immutable plan revision/scope.
- `POST /api/agent/projects/{workspace_id}/tasks/{task_id}/run` — only after approval, runtime permission and capability recheck.
- `GET /api/agent/projects/{workspace_id}/tasks/{task_id}` — durable events, errors and progress.
- `POST /api/agent/projects/{workspace_id}/tasks/{task_id}/control` — pause/stop/resume via task controller, never blind replay.

Never mirror the complete existing `/api/video/jobs`, `/api/images/jobs`, `/api/editor/projects` or `/api/audio/*` implementation inside this API. Call the same trusted backend service methods through thin adapters.

## 2. Persist resumable task/graph state *with* project Save/Load
The current `projects.DATABASES` snapshots the production SQLite ledger and image-jobs DB. Prefer adding project-owned agent tables to the **existing configured production ledger** in `ProductionLedger._initialize()` (after inspecting migrations and tests), rather than introducing a third source-of-truth DB that the project checkpoint cannot see.

Minimal table outlines (final SQL, indexes and foreign keys require a reviewed migration):

```sql
CREATE TABLE IF NOT EXISTS agent_tasks (
 task_id TEXT PRIMARY KEY, project_id TEXT NOT NULL,
 plan_revision INTEGER NOT NULL, status TEXT NOT NULL,
 plan_json TEXT NOT NULL, plan_sha256 TEXT NOT NULL,
 approved_sha256 TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_agent_tasks_project
 ON agent_tasks(project_id, updated_at);
CREATE TABLE IF NOT EXISTS agent_steps (
 step_id TEXT PRIMARY KEY, task_id TEXT NOT NULL REFERENCES agent_tasks(task_id),
 project_id TEXT NOT NULL, tool_id TEXT NOT NULL,
 status TEXT NOT NULL, input_json TEXT NOT NULL,
 output_json TEXT, job_id TEXT, idempotency_key TEXT
);
CREATE TABLE IF NOT EXISTS agent_events (
 event_id TEXT PRIMARY KEY, project_id TEXT NOT NULL,
 task_id TEXT NOT NULL, event_json TEXT NOT NULL, created_at TEXT NOT NULL
);
```

Include **unique idempotency per project/tool invocation** and foreign-key relationship ownership. Start with `draft → awaiting_approval → approved → running/blocked/paused → verifying → completed/failed/cancelled`. Only reviewed transitions may admit execution. A step is complete only after its registered output or explicit terminal no-output result has been verified.

`projects.sql_snapshot()` filters by `workspace_id` or `project_id` and follows some child FKs; give each new row `project_id` and declared relationships so Save/Load is safe. `projects.assert_idle()` currently scans status/state fields: ensure new agent task statuses reflect **actual in-flight work**; avoid indefinite blocks for a draft or approved-but-not-running task. Confirm old project snapshots still load and new ones preserve tasks/graph/skill bindings.

## 3. Project graph
Start with a **read-only derived graph** of current story/source/graph/shot/asset/job IDs; do not create a second story authority. Store only missing edges and reviewed project-specific creative decisions in new project-owned records when needed. Every node/edge has provenance, source revision or content hash and owner ID; never invent file paths or asset identifiers.

## 4. Blast-radius acceptance
Inspect callers of `ProductionLedger`, `projects.sql_snapshot`, `projects.open_project/save`, and `create_app` before patching. Verify:
- legacy opening/saving; two projects never swap editor sessions, chats, skills or jobs;
- new project accepted but no screenplay still permits manual Video Create;
- approved task cannot run after changing its plan hash or project context;
- reconnect/recovery never submits the same GPU/CPU job twice;
- all legacy editor/audio/video paths still work; generic status API unaffected.

Avoid broad refactors of the 3,700+ line dispatcher. Its new branch should be a few lines; service logic lives in small modules.
