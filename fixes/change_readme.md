# Vibe Director — current Codex entry (2026-11-09)

**Single current implementation entrypoint.** First read this file, then [ACTIVE_FIXES.md](ACTIVE_FIXES.md), [ACCEPTANCE_TESTS.md](ACCEPTANCE_TESTS.md), and only the relevant portion of [INTEGRATION_ARCHITECTURE.md](INTEGRATION_ARCHITECTURE.md). Read root [AGENTS.md](../AGENTS.md) for preservation rules. The earlier CODEX_START_HERE and COMPLETED_BASELINE guides were consolidated into these current documents; retrieve historic wording from Git history only for a specific regression.

## Source of truth and safe starting protocol

Target branch: `vibe-director-current`. Planning snapshot: `6db612357f6ccdd351b5d91e48b5d1ffd408e57a` (2026-11-09), **not a frozen implementation target**.

1. At the beginning of each implementation session run `git branch --show-current`, `git rev-parse HEAD`, `git status --short`, and inspect the relevant source/tests. If HEAD has moved, source wins over this planning snapshot; refresh references before editing.
2. Preserve user-local dirty changes. Do not reset, clean, overwrite, or revert unrelated files. Never discard local media, models, journals, job state, checkpoint history, approved plans, or external outputs.
3. **TEST FIRST.** Phase T0 records the baseline without application changes. No feature work, broad refactor, dependency upgrade, mass deletion, or code cleanup until the baseline and failures are classified.
4. After T0, fix only demonstrated failures in the smallest vertical slice. Re-run focused tests, then neighboring regressions; require a changed-file map and a rollback plan before shared-seam modifications.
5. Separate observed execution from documentation and mocks. An available tool, successful import or completed job does not establish creative quality or live provider/model readiness.
6. No paid-provider, model inference, GPU-intensive generation, checkpoint deletion, production rendering, or full-access computer tasks as incidental tests. Real owner-media acceptance is opt-in and separately recorded.

## Current product boundary

Vibe Director owns project/workspace IDs, media registry and hashes, Director/Editor session state, two edit clearances, durable jobs, output registration, and provenance. HyperFrames Studio, OpenMontage Backlot, and Kdenlive MCP are specialist workspaces/engines, not additional project owners or independent chatbot sessions.

The current branch includes a shared Director with **37 registered operations** (availability is not always runtime-probed); a bounded two-clip overlap analyzer; Kdenlive MCP preview/render with a narrow 1080p/30 hard-cut adapter; isolated native HyperFrames Studio; and an OpenMontage Backlot mirror with limited reviewable edit extension. These are real implemented paths but **not** full GUI parity, universally ready runtimes, or complete autonomous film direction. See [Director tool contract](../docs/DIRECTOR_TOOL_ACCESS.md), [Kdenlive acceptance](../plans/kdenlive_clip_continuity_usage.md), [native workspaces](../design/vibe-editor/native-interfaces.md), and [frame pipeline usage](../docs/FRAME_PIPELINE_USAGE.md).

## Implementation order / stop conditions

**T0** reproducible test inventory and baseline → **T1** failure triage, fixes and green focused checks → **S1** security/readiness/CI and storage audit → **M1** incremental maintainability work → **O1** reviewable multi-step Director orchestration → **E1** richer editing and native acceptance → **F1** whole-film quality acceptance.

Do not advance to the next stage on documentation alone. If the test environment is unavailable, report **BLOCKED with cause and executable next step**, not PASS. Never silently change supported workflows or replace an unavailable backend with another renderer.

## How Codex must report a completed slice

Report the current HEAD and dirty state, exact files changed, reason, dependency/caller trace, tests executed with real counts and pass/fail/skip, mock vs CPU vs native vs GPU evidence, artifact validation, remaining limitations, any storage/runtime effects, and rollback path. Mark a task DONE in ACTIVE_FIXES only after its acceptance criteria were actually met.

**Deletion boundary:** The nested `fixes/vibe-director-codex-agent-blueprint-v2/vibe-director-codex-agent-blueprint/` is a live skill/reference source. `agent_skills.py` reads its `skills/*/SKILL.md` and `shared/CONTRACT.md`; leave it intact. Do not delete its Markdown as “old notes” without an explicit runtime dependency migration and test. `fixes/skills/` also contains development skills, not disposable handoff prose.
