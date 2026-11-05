# Plan first → Approve → Execute → Review

## Required interaction
1. **DISCOVER**: inspect active project graph, actual assets/hashes, existing output/takes, tool registry, runtime status, user goal and selected creative jackets. Read-only operations are allowed to make an accurate plan.
2. **PLAN**: produce concrete numbered work items, inputs, dependencies, expected artifacts, selected tools/models, duration budget, estimated compute/resource demand (uncertainty disclosed), required references and specific permission gates. Indicate what's already done and what is missing. Plan is editable/branchable and revisioned.
3. **AWAIT_APPROVAL**: show the full plan in middle chat and a structured plan viewer in right pane. **Do not dispatch GPU jobs, modify source code, install dependencies, generate assets, publish outputs or make external changes until authorized.** User may say "implement", "approve steps 1-3", "change this first" or "manual only".
4. **EXECUTE**: pin approved plan revision, project ID, style/skills versions and tool graph snapshot. Persist every task event before invoking tools; use idempotency or reconciliation for uncertain operations. Show task list, inputs/outputs, logs, blockers and current step in UI. The user can redirect or pause.
5. **VERIFY/REPAIR**: probe output metadata, run media inspection, flag suspected defects, choose local edit or retake. Safe automatic retry must not resubmit a possibly active external job. If plan needs significant change, present a plan delta for approval.
6. **DELIVER**: compose/edit/export, verify playable final output, save all provenance, return direct asset and project links. Persist unfinished work if interrupted.

## Permission tiers (proposed; adapt to user's installed runtime)
- **R0 read-only:** local project lookups, source inspect, capability check, software logs, media probing, Git status/diff. These can run to build a plan.
- **R1 reversible/local edits:** create draft screenplay, write working files, perform sandboxed code edits, create draft timeline and previews. Requires *plan approval* unless user directly requested that one action; never overwrite original assets.
- **R2 substantial compute:** GPU/video/music/TTS jobs, installers, network downloads, third-party services. Require approved execution scope and show budgets/settings; optionally checkpoint at defined resource threshold.
- **R3 high impact:** destructive cleanup, overwrites/exports beyond project workspace, credential use, external uploads/publication, account actions, code affecting safety/ownership. Always require a specific confirmation; block if tool policy prohibits.

## Plan example contract
```
Plan ID / revision / project / target film / estimated final runtime
Available characters / locations / voices / existing media
Tool choices and live readiness
Proposed scenes, shots, generate-sized clips, optional images/existing footage
Per-clip reference manifest and duration (MiniMax R2V <= 15 seconds, prompt <7000 code points)
Task DAG: create refs → generate candidates → inspect → selected take/retake → edit → export
Quality checks and acceptance thresholds
Expected outputs and user approval gates
Risks/unknowns, budget ceiling, resumability and rollback strategy
```

## Exact agent language
- Before approval: "Here's my proposed plan; no generation or source modifications have been performed."
- After approval: "Implementing approved plan revision N. Tool job J queued/running ..."
- On uncertainty: "The response is inconclusive. I am reconciling the existing job ID before attempting another submission."
- On blocker: "Stage X is blocked by Y. Here's the safe adjustment; approve the change if you'd like me to proceed."
- Never promise background execution without a persistent actual worker runtime and a registered task handle.

## Code-writing / computer-use permissions
A Codex-like agent is a **host process capability** that must be installed and authorized. Its coding layer can use a sandboxed terminal, file editing/diffs, tests, Git worktrees/branches, and narrowly authorized Playwright/desktop controls. Tool-call schemas + capabilities + owner permission enforcement are essential. Screen-driving is for GUI-only features, not for bypassing application security/admission. No unrestricted shell from a model-generated string. Explicitly show commands and file diffs for consequential operations. No direct writes to production SQLite ledgers or frozen request files.
