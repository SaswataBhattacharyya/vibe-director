# Active roadmap — test-first, evidence-gated (2026-11-09)

This is the **only current task/status queue**. Snapshot is `vibe-director-current` at `6db612357f6c`. All statuses below are **planning states**, not newly run verification. Implement against current HEAD. Each task has a stop/go gate in [ACCEPTANCE_TESTS.md](ACCEPTANCE_TESTS.md).

## Required sequence — user-confirmed P0 harness recovery

**Core regression to fix first:** Vibe makes one `codex exec --ephemeral` reasoning call, proposes one tool (often `media.list`), and stops. User requested ordered clips **2→3→4→5→6** and a playable video; discovered media is not a completed user goal. The one-shot response-schema bug may have been patched separately but is not a harness. Follow **[DIRECTOR_HARNESS_P0.md](DIRECTOR_HARNESS_P0.md)** as the exact primary implementation specification. Current source diagnosis: `05508145fe049214f0f83ac45b1164748920dd4d` (2026-11-09).

| Order | ID | Priority | Status | Required concrete outcome |
| --- | --- | --- | --- | --- |
| 0 | **T0-BASELINE** | **P0** | **NEXT — not executed in documentation** | Run safe focused unit/type/browser baseline; log existing dirty paths, test counts, exact failures and runtime versions. No production code or owner media edits. |
| 1 | **H0-REPRO** | **P0** | **OPEN** | Reproduce one-shot `media.list` dead end as a failing goal-level test, independently verify fixed schema with mocks and optionally a user-authorized real Codex call. |
| 2 | **H1-CODEX-HARNESS** | **P0** | **BLOCKED on H0** | Spike official `codex app-server` in disposable ARM64 workspace: real 2+ tool calls in one turn, stream, restart/resume, MCP, approval events, and denied shell/files. Choose Agents SDK only if Codex fails a recorded requirement. |
| 3 | **H2-TOOL-GATEWAY** | **P0** | **BLOCKED on H1** | Durable project-owned goal/step ledger; model sees allowlisted Vibe/MCP functions, existing task service remains authority; tool-result continuation, source hashes and compact chat. |
| 4 | **H3-APPROVAL-RECOVERY** | **P0** | **BLOCKED on H2** | Human-only exact-plan approval, two Editor clearances, cancel/restart/idempotence/stale revisions, no model/Playwright authorization bypass. |
| 5 | **H4-FIVE-CLIP-EDIT** | **P0** | **BLOCKED on H3** | Resolve true project order (not media-list date order), build 2→3→4→5→6 timeline, use permitted editor, real synthetic CPU render with A/V boundary/hash checks, verify and register video. |
| 6 | **H5-EDITOR-PLAYBACK** | **P0** | **BLOCKED on H4** | Source video/audio immediately playable in Vibe Editor; user-approved stitched artifact opens without extra prompt; real Playwright frontend/host acceptance; raw metadata collapsed. |
| 7 | **H6-OWNER-ACCEPTANCE** | **P0** | **OPT-IN after H5** | Actual owner project, manual sequence/audio quality check, no owner-file corruption and truthful completion only after playback. |
| 8 | **T1/T2-REMAINING-REGRESSIONS** | P1 | QUEUED | Reproduce and repair other confirmed baseline failures in small changes with neighbors and rollback proof. |
| 9 | **S1–S4** | P1 | QUEUED | Capability-ready truth, MCP minimal-env isolation, non-GPU CI, read-only storage audit/retention proposal. |
| 10 | **M1–M2** | P1 | QUEUED | Generated Graphify cache tracking audit and small safe refactors of oversized modules. |
| 11 | **E1–E3** | P2 | QUEUED | Native Kdenlive desktop acceptance / multi-clip backend parity, HyperFrames/Backlot richer round-trip, media indexing. |
| 12 | **F1-FULL-FILM** | P2 | BLOCKED | Creative QA, multi-stage filmmaking, retakes, soundtrack, verification and opt-in owner acceptance after harness works. |
| later | STYLE-VIDEO / UX / advanced speech | P2 | DEFERRED | Do not distract from the P0 user-visible goal failure. |

**First mandatory test:** A user request that needs 5–8 verified steps must not report success after one read-only `media.list`; verify full goal state, specific approval and output playback. **No feature is DONE based on tests that were not run.**

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
