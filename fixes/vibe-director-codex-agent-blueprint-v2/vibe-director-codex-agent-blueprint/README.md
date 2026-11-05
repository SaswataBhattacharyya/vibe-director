# Vibe Director — Codex-Class Filmmaking Agent Blueprint

**Status: architecture and implementation instructions, NOT an app patch, working computer-control integration, or proven media render.** The repository `fixes/` directory is the in-repo source of this blueprint; Codex should read it directly, not require a separate ZIP upload.

## One-sentence vision
Vibe Director is a project-aware Codex-like filmmaking workstation: a user may operate any existing filmmaking page manually, or ask the persistent Director agent to plan and—AFTER user approval—use software tools, computer/browser automation, coding, and specialist agents to make, inspect, repair, edit and deliver an entire film.

## Read in this order
1. `01_VISION_AND_BEHAVIOR.md` — product meaning and corrected autonomous behavior.
2. `02_PLAN_APPROVE_EXECUTE.md` — plan-first contract, execution and authority policy.
3. `03_SYSTEM_ARCHITECTURE.md` — agent runtime, tools, projects, skills, UI.
4. `04_GITHUB_CODE_AUDIT.md` — live GitHub branch findings for Vibe Editor and gaps.
5. `05_PROJECT_KNOWLEDGE_GRAPH.md` — persistence and relationships.
6. `06_TOOL_GRAPH_AND_COMPUTER_ACCESS.md` — typed app tools plus genuine computer/coding access.
7. `07_END_TO_END_FILM_LOOP.md` — production, QA, retakes, edit, export.
8. `08_EDITOR_HANDOFF_AND_DELEGATION.md` — Editor, HyperFrames, OpenMontage, Backlot.
9. `09_UI_CREATIVE_WORKFLOWS.md` — keep sidebar and Media Prep intact, redesign production.
10. `10_MIGRATION_IMPLEMENTATION_PHASES.md` and `11_ACCEPTANCE_TESTS.md` — incremental work.
11. `codex/START_HERE_PLAN_THEN_IMPLEMENT.md`, `codex/CODEX_MASTER_VISION.md`, `codex/PHASE_0_REPO_RECONCILIATION.md`, `codex/PHASE_1_IMPLEMENT_ON_APPROVAL.md` — in-repository Codex instructions; planning first, implementation only after approval.
12. `16_UPDATED_GITHUB_RECONCILIATION.md` — what the newly pushed 2026-11-05 source does and does not establish.
13. `skills/` — 13 `SKILL.md` files. Original six plus Production Style plus six operating skills.
14. `contracts/` — example JSON machine-readable structures and schemas. Must be reconciled with actual app before use.
15. `source_materials/` — original provided review, glossary ZIP, and original skill package; docs also unzipped in `glossary/`.

## Non-negotiables
- Preserve current left navigation and all Media Prep tools/UI and runtime services.
- All pages independently usable. No mandatory story → screenplay → storyboard → video pipeline.
- One persistent center Director chat, resizable/collapsible, real right pane tool workspace.
- Plan is always reviewable BEFORE an autonomous implementation run. A user can request a draft-only action explicitly.
- Computer access is REAL runtime adapter(s), not a prompt assertion. Code execution is sandboxed, permissioned, logged and testable.
- Both Director and Editor use the same project-aware, typed tool gateway, not uncontrolled direct engine access.
- Immutable admitted jobs, idempotency, media identity/hash, owner boundaries, safety guards and existing approval/export policies are preserved.
- No claim of success without verified registered outputs; creative quality evaluation is different from file validation.
- Project graph records film state, provenance and execution; tool graph records capabilities and current availability; skill graph records advice and constraints.
- Production-type, visual-style and directing-language profiles are independent, optional, versioned creative jackets.

## Provenance
The uploaded `full_review.md` documents a **local checkout with uncommitted changes on 2026-11-05**. The initial GitHub inspection was at `65e9717932547cad2ef8b55e9beb2c83f7686b05` (2026-11-01). The `vibe-director-current` branch was then updated to `3b9db20304c1073c674271c8f60fc66859a7a044`, which includes `full_review.md`, `tool_glossary/`, and the `fixes/` package. The supplied review still describes a local checkout at its review time, so Codex must check the actual current working tree before implementation. This blueprint modifies documentation only; it does not implement agent/runtime changes.
