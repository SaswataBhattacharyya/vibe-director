# Paste this prompt into Codex from the Vibe Director repository

You are the implementation engineer for **Vibe Director: a Codex-class, project-aware AI filmmaking workspace**. An attached blueprint ZIP named `vibe-director-codex-agent-blueprint-v2.zip` is the specification; unpack it to a temporary/reference location without overwriting repository files. Read `codex/CODEX_MASTER_VISION.md`, `03_SYSTEM_ARCHITECTURE.md`, `13_EXISTING_SOURCE_SKILL_MERGE.md`, `14_GLOBAL_AND_PROJECT_SKILL_ACCESS.md`, `15_COMPACT_CODE_AND_TEST_MEDIA_POLICY.md`, `08_EDITOR_HANDOFF_AND_DELEGATION.md`, `10_MIGRATION_IMPLEMENTATION_PHASES.md`, `11_ACCEPTANCE_TESTS.md`, plus the six foundational filmmaking skills, Production Style and relevant operating skills. Read the preserved source audit and glossary. Treat the current repository code as authority when it differs from documents.

## FIRST RESPONSE: PLAN ONLY — DO NOT IMPLEMENT YET

Inspect the checked-out Git branch, uncommitted changes, source files and tests. Pay special attention to `StudioShell`, `VibeEditorPage`, `EditorWorkspace`, `vibe_editor.py`, `vibe_editor_render.py`, `director_skills.py`, existing story/prompt/image/video/Media Prep APIs, project Save/Load and job ledgers. Preserve the existing left navigation and Media Prep. Identify which external global skill providers, local skill folders, computer/coding runtimes and tool adapters are actually installed; never pretend a capability is available merely because a skill mentions it.

Produce an **exact phased implementation proposal** with:
1. Current-state findings, concrete blockers and proof from source; no made-up implementations.
2. Proposed small component/module boundaries, typed APIs, data migration, project graph, global/bundled/project skill discovery, runtime permissions and Editor/Director tool parity.
3. How the Director independently operates Z-Image, MiniMax, Media Prep and HyperFrames to plan, create, inspect, retake and assemble a complete film, without locking manual users into any workflow.
4. Which existing files each stage changes, what new files are needed, a realistic order and rough engineering effort/risks, with feature flags and rollback.
5. Synthetic test fixtures for image/text/video/audio, explicit deletion/cleanup proof, and CPU/mocked tests before any live GPU work.
6. Quality constraints: compact readable maintainable code, no monolithic refactors or duplicate business logic, existing execution safety preserved.
7. Specific acceptance criteria for every stage and a proposed smallest **first approved vertical slice** (shared skill search and a real Editor/Director tool action, such as safe audio extraction).

**STOP after presenting the plan.** Do not edit code, install packages, run a GPU/provider generation, alter the user project, write permanent test media, or delete anything. Ask me to approve a specific phase or part of the plan.

## AFTER I EXPLICITLY SAY 'IMPLEMENT PHASE N' (or equivalent)

Implement only the approved scope, in small focused patches. If git changes already exist, preserve them and avoid destructive reset. Prefer safe branch/worktree isolation with approval when appropriate. Reuse current APIs, project-owned asset IDs, validators, durable job reconciliation, trusted HyperFrames renderer and GPU safeguards; do not bypass permissions. The Director and Editor must use **one shared runtime** for global and project-specific skills and for validated tool execution, plus optional computer/coding access. Skill discovery is not tool permission. Implement feature flags where relevant, and maintain legacy behavior until migration is proven.

Run automated tests using **only synthetic test-owned** text/PNG/short video/audio; create under a unique isolated test directory and optionally an isolated test project/DB. Remove the generated fixtures and their test-only catalogue/job entries after testing, including on failure; verify cleanup. NEVER delete user files or production assets. If a fixture cannot safely be cleaned, report the blocker and exact test-owned leftover. Do not run GPU/provider tests without separate authorization. Keep source tests, delete only temporary generated media.

For every finished phase provide: what changed, files/diff overview, tests with observed pass/fail, fixture cleanup confirmation, operational limits, and the next proposed phase. Do not treat a proposed or mocked capability as a completed working feature. Stop before widening scope; I will authorize the next phase.
