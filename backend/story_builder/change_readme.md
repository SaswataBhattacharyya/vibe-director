# Backend implementation boundaries

Read [master scope](../../fixes/change_readme.md), then the approved [task card](../../fixes/QUICK_FIX_TASKS.md). These are proposals. Current source/owner instructions win. Do not implement every route below in one patch.

## Q03–Q05: narrow discovery seam (Phase 1)

Follow `create_app`'s existing `/api/editor/` delegation pattern for `/api/agent/`. Pass configured root/ledger/story dependencies that the services actually need; do not instantiate a second default ledger in the handler. Keep exact route/method/query/body validation and existing JSON errors. The server's `workspace_id` validation/lookup must enforce owner context, including standalone `tool-library`; browser IDs are not authorization. Local-owner profile/session identity is not a new authentication scheme.

Only initial routes:
- `GET /api/agent/tools?workspace_id=...`
- `GET /api/agent/skills?workspace_id=...`
- `GET /api/agent/projects/{workspace_id}/context`

No task tables, execution routes or persistent chat in Phase 1. No broad dispatcher rewrite. Q05 must not mutate manifests/job state merely to describe them.

## Q02/Q07/Q08: shared operation and lifecycle (Phase 2)

Q02 factors existing utility submission without altering manual API contracts. Q07 introduces proposed tasks, immutable plan revisions, approvals, invocation/job mapping and events in the configured production ledger. Q08 connects both chat surfaces. Inspect final SQL/transitions/crash handling before implementing Q07.

Proposed task routes are added only with their service/tests: propose, inspect, approve, run, and supported control operations under `/api/agent/projects/{workspace_id}/tasks`. Plan POST never executes. Approval binds exact project, revision/hash, assets+hashes, settings and tool. Run rechecks ownership/capability. No generic `/exec`.

`projects.sql_snapshot()` selects owner rows and related records; import checks exact columns and newer/conflicting records. This is not proof that new tables automatically roundtrip correctly. Test old/new checkpoints, fresh configured root and moved projects. `assert_idle()` must follow actual in-flight jobs; draft tasks do not block Save, paused tasks can still own live work.

Keep new tables additive, with explicit owner columns, consistent FKs, immutable plan history and unique invocation constraints. Avoid new columns in historical tables unless necessary. Retain records on rollback; stop new execution and reconcile live work first. Older binaries may reject new snapshots.

Trace at least route → service → persistence/worker → result consumer for each changed flow. Test only affected contracts; see [test guide](tests/change_readme.md). Preserve original/frozen jobs, grants, identities and manual workflows.
