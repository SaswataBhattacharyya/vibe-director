# Codex start prompt — implement source-linked change_readme guides, phase by phase

Read the current Vibe Director repository on the checked-out branch. Start with AGENTS.md and fixes/change_readme.md, then read EACH change_readme.md in:
- backend/story_builder/
- backend/story_builder/services/
- backend/story_builder/tests/
- frontend/src/
- frontend/src/lib/
- design/vibe-editor/
- skills/

Read fixes/vibe-director-codex-agent-blueprint-v2/vibe-director-codex-agent-blueprint/ in parallel for product requirements, original review, 13 skills and the tool glossary. Also read fixes/skills/blast-radius-review/SKILL.md and fixes/skills/compact-code-craft/SKILL.md if present. The files in fixes are specifications and code proposals, not live implementation; inspect current source before treating a snippet as drop-in code.

The product is a Codex-class filmmaking Director and specialist Vibe Editor sharing one tool gateway, global/bundled/project skill resolver and project knowledge graph. Manual pages remain independent; agent plan is reviewed before the agent implements. The agent can later use real authorized computer/coding, terminal, browser, Git and optional external specialists. Skills do not grant permissions. Preserve left sidebar, Media Prep UI/functionality, HyperFrames renderer, versioned production jobs, project snapshots and GPU safety.

FIRST TASK: PLAN ONLY
1. Show current git branch, HEAD, status, and existing uncommitted changes. Do not reset, switch branches or overwrite work.
2. For each change_readme.md, verify every source anchor and existing API signature against local checkout. Label each proposal as exact, needs-adaptation, or blocked. Identify already implemented parts and omit duplicate work.
3. Trace BLAST RADIUS using source-wide callers, API consumers, persistence, tests and actual Graphify index (known partial) before proposing a shared-file edit.
4. Prepare a short phased plan, exact files to create/change, typed inputs/outputs, schema migrations, permission/approval semantics, testing, rollback and estimated engineering effort. Prefer one vertical slice: shared tool/skill discovery + Editor/Director calling existing Extract MP3 and receiving a real registered asset.
5. STOP. Request my explicit approval of Phase 1. Do not modify application code or run paid/GPU jobs.

AFTER APPROVAL OF ONE PHASE
- Implement only that approved phase. Use compact, readable, modular code; keep new modules focused. Do not add another giant dispatcher/React page or duplicate services.
- Run relevant existing tests and add narrow regression tests. Use disposable synthetic TXT/PNG/WAV/MP4 only in test-owned TemporaryDirectory and isolated DB/project; clean on normal/failing runs and verify cleanup. Never erase user media.
- Preserve exact current T2V/R2V/FFLF versioned contracts and durable job idempotency. A working LTX OFF toggle is a separate cross-layer change, not a UI-only switch.
- Report actual file diff, commands/tests and results, created assets and their cleanup proof, remaining limitations, blast radius and rollback.
- Stop and request approval before next phase.

No claim that a generated film is complete without verifying its actual output media and, where supported, providing truthful observed quality checks and Editor handoff.
