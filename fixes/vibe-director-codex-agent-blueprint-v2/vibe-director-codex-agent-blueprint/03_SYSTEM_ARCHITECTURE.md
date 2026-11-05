# Target architecture — one filmmaking workspace, multiple tool surfaces

```
┌ Left nav (EXISTING) ┐ ┌ Middle: persistent Director/Editor chat ┐ ┌ Right: live tool/work surface ┐
│ Projects & tools   │ │ planning | tasks | logs | approvals    │ │ screenplay / images / board │
│ keep Media Prep   │ │ real progress and artifacts           │ │ video / Editor / Run Board  │
└───────────────────┘ └──────────────────────────────────────┘ └──────────────────────────────┘
                             │
                 PROJECT CONTEXT + TASK CONTROLLER
                 PLAN / APPROVE / EXECUTE / VERIFY
                             │
           ┌─────────────────┼──────────────────┐
      SKILL REGISTRY      TOOL GRAPH          PROJECT GRAPH
       craft guidance     typed operation     canonical facts
       style jackets      capability/live     assets & lineage
                         permission gates      jobs & decisions
                             │
       ┌─────────────────────┴──────────────────────┐
    Tool gateway          Computer/Coding runtime       Delegation adapters
  existing app APIs      sandboxed shell, Git, tests,   Editor, OpenMontage,
  Z-Image MiniMax etc    browser/desktop, FFmpeg,       Backlot, Blender,
                        code patch, verified files      HyperFrames Studio
       └─────────────────────┬──────────────────────┘
                      existing durable ledgers
                      GPU guards / idempotency
                      media library / output grants
```

## Agent engine
A stateful orchestrator runs a resumable plan with statuses `planning`, `awaiting_approval`, `approved`, `running`, `awaiting_resource_approval`, `blocked`, `paused`, `verifying`, `completed`, `failed`, `cancelled`. Each task has `task_id`, kind, input refs, dependencies, tool operation ID, approval scope, idempotency key/lookup, owner session, output asset IDs, event log and retry policy. **Model reasoning is not a durable task runner**; task/job state is stored in the existing project-owned database/service.

## Shared tool gateway (both agents)
Tool routing: `discover → capability → validate → authorize → submit → observe/reconcile → collect/register → update project graph`. Expose trusted high-level operations with concrete schemas. The 44 glossary groups are only discovery domains: split them into specific actions and mark `wired | navigation_only | unavailable | unverified`. Bind tools to the current owner/project server-side. Reuse existing service endpoints and safety protections.

## Computer/Coding sidecar
Add a separate **opt-in local Agent Runtime** capable of sandboxed command execution, Git, file reads/patches, test runners, browser/desktop automation and specialized binaries. Restrict filesystem roots, worktree, environment, network egress and secrets; log commands/artifacts. Use the same plan approval and permissions. Prefer existing app APIs for media operations. Use GUI automation only when no typed adapter exists and it is allowed. It cannot claim remote browser or computer control just because the UI resembles Codex.

## Persistent UI and context
Keep `StudioShell.tsx` left sidebar. In center, mount project-scoped, reloadable conversation with task operations. Right pane holds interactive mounted app surfaces; populate via typed `{route, project_id, selection_ids, ranges, draft_id, job_id, tool_id}` context. Navigation changes should not lose chat or unsaved drafts. Editor can switch to specialist chat context while sharing graph and tools. Third-party GUIs run in controlled route/sidecar, not an iframe assumption.

## Source-of-truth boundaries
- Existing immutable video job requests, hashes, leases, reconciliation and media library **remain authoritative** for execution.
- Project graph indexes/references the originals; it does not replace them or rewrite submitted jobs.
- Screenplay, storyboard and creative brief are editable graph material; clip render plans are derived documents, not permanent global locks.
- Manual operations can remain unlinked to a screenplay and be linked to timeline later.
- Stage authority is per-task (human vs agent), not a universal five-checkbox pipeline.

## LTX off semantics
Two real postprocessing profiles: `turbo_only` and `turbo_plus_ltx`. The user can toggle *before* admission. The request snapshot must include the postprocess profile and relevant workflow version; update the compiler/worker/collector/final publication path consistently. Turbo-only still validates duration/frame count/audio, registers final asset and has a distinct reviewable status. Never treat old jobs as Turbo-only by changing a preference later. Legacy jobs retain their frozen LTX plan and recovery semantics. Design migration/contract tests first; don't merely hide LTX UI.


## Global / app / project skill service (shared by Director and Editor)

Place a `SkillDiscovery + SkillResolver + SkillContextLoader` service next to the typed tool gateway, not inside a page component or a separate private Editor prompt. Skill sources are **configured global agent providers/installed skill directories**, existing bundled app skills, and **project-scoped, portable/versioned skill records**. Discover provider capabilities at runtime; never assume a particular global directory exists. Present a single `list/search/inspect/load/refresh` contract to both Director and Editor, returning IDs, source/scope, provenance, version/hash, description and availability. Cache by hash/version with invalidation; load only selected relevant `SKILL.md` and allowed local references under bounded context budgets. Apply scope-specific creative precedence while enforcing immutable security and task permissions. Skill content does not create tool access; tool graph capabilities remain validated and permission-gated.

Project Save/Load includes *references and snapshots* necessary to restore project-owned skill bindings and resolved creative choices without copying global installation payloads into each project. Missing/changed global skills are flagged, not silently replaced. No project may load or modify another project's private skills. The two agents use the **same runtime resolver**; editorial/directorial specializations are activation context, not separate permission systems. Acceptance checks and API design are in `14_GLOBAL_AND_PROJECT_SKILL_ACCESS.md`.

## Compact implementation rule

Build thin adapters near the existing services, typed contracts and small reusable view components. Do not broaden `App.tsx`, `StudioShell.tsx`, the main HTTP dispatcher, or existing Editor single-file logic unnecessarily. Insert vertical slices with tests and compatibility wrappers. Keep the left navigation and Media Prep implementation unchanged unless a concrete bug fix is independently approved. Cleanup semantics for synthetic test media follow `15_COMPACT_CODE_AND_TEST_MEDIA_POLICY.md`.
