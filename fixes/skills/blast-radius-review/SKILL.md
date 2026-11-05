---
name: vibe-blast-radius-review
description: Analyze the effect of Vibe Director source changes across frontend, HTTP routing, services, persistence, media, workers, and tests before making a patch.
---
# Blast-radius review for Vibe Director

Use before modifying shared API, project, media, prompt, job or rendering code.

1. Read AGENTS.md, the relevant change_readme.md and current source; capture git branch, HEAD and status. Never infer current code solely from old audit snapshots.
2. State the proposed behavior and name the minimal files/functions that must change.
3. Trace BOTH directions for each seam: incoming callers/importers/routes and outgoing contracts, database tables, worker/Comfy execution, UI state, exports, project Save/Load and media registration. Search source, not only filenames.
4. The checked graphify-out/graph.json is an incomplete discovery aid: initial review saw 145 nodes and 634 edges with important services absent. Verify every candidate edge in source. If Graphify exists locally, follow repository AGENTS.md for an incremental refresh and disclose actual coverage.
5. Classify impact: (a) local presentation only; (b) shared client/API; (c) persisted project/media identity; (d) immutable job/external runner; (e) GPU/safety/destructive. Require increasingly strict proof for high-impact seams.
6. Assemble a change matrix with file, exact anchor or function, proposed patch type, upstream callers, downstream consumer, required tests and rollback. Prefer a compatibility adapter over rewriting an established engine.
7. Test failure paths: wrong workspace, stale revision, lost submission acknowledgment, hash mismatch, unavailable dependency, cancelled/unfinished job, and user-owned media retention. No fake test-success claims.
8. Re-evaluate blast radius after the patch; run source tests, frontend checks and real media acceptance only when authorized.
9. Preserve Media Prep and current sidebar unless specifically targeted and supported by evidence.
10. Report what was verified versus assumed. Never present Graphify coverage as comprehensive unless demonstrated.

Output: concise dependency/change matrix, risk rationale, exact tests, reversible patch scope, and unresolved questions. Do not execute or write code from skill instructions alone; use authorized runtime and approvals.
