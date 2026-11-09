# Active roadmap — test-first, evidence-gated (2026-11-09)

This is the **only current task/status queue**. Snapshot is `vibe-director-current` at `6db612357f6c`. All statuses below are **planning states**, not newly run verification. Implement against current HEAD. Each task has a stop/go gate in [ACCEPTANCE_TESTS.md](ACCEPTANCE_TESTS.md).

## Required sequence

| Order | ID | Priority | Status | Deliverable / gate |
| --- | --- | --- | --- | --- |
| 0 | **T0-BASELINE** | P0 | NEXT — NOT RUN IN THIS DOC UPDATE | Reconcile branch/dirtiness, inventory tests and installed prerequisites, run safe static and representative CPU/mock suites, record precise pass/fail/skip/time and reproducible logs. No product changes. |
| 1 | **T1-TRIAGE** | P0 | BLOCKED on T0 | Classify each failure as pre-existing, environment, flaky, new regression, unsupported runtime or missing coverage; reproduce, locate owner/caller and prioritize corruption/security/data loss first. |
| 2 | **T2-REGRESSIONS** | P0 | BLOCKED on T1 | Fix confirmed failures in small isolated changes, with targeted and neighboring tests, no generated/provider job side effects. Green tests or explicit documented exceptions required before feature expansion. |
| 3 | **S1-CAPABILITY-TRUTH** | P1 | QUEUED | Catalogue distinguishes adapter registered, runtime ready, input actionable and approval needed. Remove unconditional readiness claims; verify blocked and missing-runtime behavior without generation. |
| 4 | **S2-MCP-ISOLATION** | P1 | QUEUED | Stop passing the full parent environment into Kdenlive MCP, validate workspace/output paths and subprocess lifetime, preserve journals; demonstrate denial of unrelated secrets/files with focused tests. |
| 5 | **S3-CI** | P1 | QUEUED | Add reliable non-GPU CI checks for Python tests, TS typecheck/build, a selected browser smoke suite, lint/security; native ARM64/MLT and GPU suites remain opt-in runners. |
| 6 | **S4-STORAGE** | P1 | QUEUED | Measure project checkpoints, copied media, Kdenlive staging and model checkpoints. Implement **read-only** storage report and retention proposal first. No deletion until a separate reversible, reference-aware policy and owner confirmation exist. |
| 7 | **M1-REPO-HYGIENE** | P1 | QUEUED | Audit consumer references for committed `graphify-out/` AST caches (~138 MB at snapshot), propose ignore/untrack plan in a separate code change, preserve minimal reports and any required runtime graph. Never delete local caches/media as a side effect. |
| 8 | **M2-MODULE-SEAMS** | P1 | QUEUED | Extract low-risk HTTP/routes and UI responsibilities from oversized modules *incrementally* after characterization tests; avoid rewrites, changing URL contracts or global dependency updates. |
| 9 | **O1-DIRECTOR-ORCHESTRATION** | P1 | BLOCKED on baseline + S1 | Typed persisted multi-step plans with dependency graph, per-step grants, user approval, pause/reconcile/compensation, idempotent submission and evidence-gated transitions. One synthetic workflow first. |
| 10 | **E1-KDENLIVE** | P2 | BLOCKED on T0 + owner GUI test | Verify Flatpak can open exported .kdenlive project and managed media; expand beyond two clips/1080p30 only with versioned format and audio/frame correctness tests. |
| 11 | **E2-NATIVE-EDITORS** | P2 | BLOCKED on baseline | Extend supported Studio/Backlot round-trip only after exact upstream-version/API checks; unsupported controls stay visibly unsupported. |
| 12 | **E3-MEDIA-INDEX** | P2 | QUEUED | Cross-project membership/index freshness and pre-pagination filtering with migration/snapshot/delete impact proof. |
| 13 | **F1-OWNER-FILM** | P2 | BLOCKED on orchestration + editor acceptance | Opt-in end-to-end owner-material film run with QA, retakes, soundtrack, provenance, restart recovery and final export; no “fully autonomous” claim from isolated tool tests. |
| later | **STYLE-VIDEO / UX / advanced speech** | P2 | DEFERRED | Frozen style references; compact/accessibility review; audio retime/replacement and real gibberish judgment, each gated by tested core workflows. |

## Current implemented baseline — preserve, do not reimplement

- **CAP-01:** shared Director/Editor task gateway, approvals and 37 registered operations; catalogue truth and multi-step orchestration are incomplete.
- **AUD-01:** complete-source CPU speech evidence and reviewed, normal-speed hard-cut proposals exist; owner-content speech judgment and retimed/replacement audio alignment not validated.
- **HF-01 / HF-02:** actual isolated HyperFrames 0.8.199 Studio, bounded trim/order/caption/framing round-trip to a Vibe approval; arbitrary native layers/history/audio are unsupported.
- **OM-01:** pinned Backlot mirrors playable saved storyboard media, supports a **Vibe extension** staging typed prompt/duration/note edits for review, and displays registered final outputs; upstream general write-back/generation is not implemented. Older claims that it is strictly “read-only” refer to upstream API, not the extension.
- **MEDIA-01:** shared typed media picker consolidated; cross-project indexing is separate.
- **KDENLIVE:** actual two-clip moving-overlap analysis and MCP hard-cut preview/render/export implementation with synthetic CPU test evidence. Flatpak desktop opening and creative continuity on owner media remain owner acceptance.
- **FRAMES:** reviewed keyframe takes and FILM/RIFE interpolation/export code; live model inference and visual quality unverified.
- **FILM-01:** general multi-stage autonomous filmmaking remains incomplete.

These statuses are based on inspected source and prior reports, not a new test run. Do not mark them DONE for live owner projects solely from old test notes.

## Task execution policy

For **each** task: (1) inspect actual current source and clients, (2) write a small change/rollback map, (3) reproduce a concrete baseline or missing acceptance case, (4) implement one vertical slice, (5) run focused tests and neighbors, (6) review artifact bytes and authorization/security, (7) record exact results and update this table. Preserve original media, IDs/hashes, two Editor clearances, database/job schema compatibility, active grants, external outputs and user-local modifications.

**P0 immediately:** confirmed data loss, inaccessible previously saved projects, bypass of tool approval/ownership, unsafe file deletion, unauthenticated remote exposure, broken supported primary export, and regression in durable recovery. Stop adding features until fixed.

**Testing modes:** MOCKED (contract/UI only), CPU (actual synthetic media processing), NATIVE (pinned desktop/MCP real runtime), GPU/PROVIDER (explicit opt-in), OWNER (human artistic acceptance). A pass in one mode never substitutes for another.
