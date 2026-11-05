# Vibe Director — Codex-Class Filmmaking Agent Blueprint

**Status: architecture and implementation instructions, NOT an app patch, working computer-control integration, or proven media render.**

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
11. `codex/CODEX_MASTER_VISION.md`, `codex/PHASE_0_REPO_RECONCILIATION.md`, `codex/PHASE_1_IMPLEMENT_ON_APPROVAL.md` — give directly to Codex.
12. `skills/` — 13 `SKILL.md` files. Original six plus Production Style plus six operating skills.
13. `contracts/` — example JSON machine-readable structures and schemas. Must be reconciled with actual app before use.
14. `source_materials/` — original provided review, glossary ZIP, and original skill package; docs also unzipped in `glossary/`.

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
The uploaded `full_review.md` documents a **local checkout with uncommitted changes on 2026-11-05**. GitHub inspection was of `SaswataBhattacharyya/vibe-director`, **`vibe-director-current` at `65e9717932547cad2ef8b55e9beb2c83f7686b05`** (GitHub commit 2026-11-01). These are not necessarily identical. Before modifying any source, Codex must inspect the user's actual working tree and reconcile differences. No source files in the user's repository are modified by this blueprint.
