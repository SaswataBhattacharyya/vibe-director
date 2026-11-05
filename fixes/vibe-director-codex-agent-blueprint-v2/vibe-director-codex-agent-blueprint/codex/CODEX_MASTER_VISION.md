# Give this to Codex in the Vibe Director repository

You are the implementation engineer for **Vibe Director: Codex-Class Filmmaking Agent**. The owner wants to turn the existing app into an AI filmmaking environment with a persistent chat that can plan, use local computer/code tools and all existing media capabilities, inspect results, retake bad clips, delegate editing, and produce an entire final film. A user may also use EVERY existing page manually and out of order. You MUST KEEP the existing left navigation and Media Prep intact.

Read all planning files in this bundle, especially `README.md`, `02_PLAN_APPROVE_EXECUTE.md`, `03_SYSTEM_ARCHITECTURE.md`, `04_GITHUB_CODE_AUDIT.md`, `05_PROJECT_KNOWLEDGE_GRAPH.md`, `06_TOOL_GRAPH_AND_COMPUTER_ACCESS.md`, `07_END_TO_END_FILM_LOOP.md`, `08_EDITOR_HANDOFF_AND_DELEGATION.md`, `10_MIGRATION_IMPLEMENTATION_PHASES.md`, `11_ACCEPTANCE_TESTS.md` and every relevant skill.

**Two-pass contract:** First do read-only repo investigation (git branch, working tree, source files, tests, runtime capability), reconcile the owner's Nov 5 local review with GitHub `vibe-director-current`, present a concrete exact implementation plan (affected paths, schema/API plan, migration, feature flags, testing/rollback, estimated engineering effort and risks). STOP and ask the user to authorize implementation. NEVER patch source, install packages, trigger GPU jobs or delete outputs during planning unless specifically requested as part of an approved investigation.

**Only after user says implement/approve:** create a safe branch/worktree if appropriate, patch incrementally, validate and test after each slice, report exactly which files changed and evidence of working behavior, and stop before any non-authorized destructive or external operation. No giant rewrite. No suppression of job hash/owner/recovery/GPUs safety checks.

## Reference reality
GitHub source inspection saw `SaswataBhattacharyya/vibe-director` code on branch `vibe-director-current`, SHA `65e9717932547cad2ef8b55e9beb2c83f7686b05` (Nov 1). Uploaded review describes Nov 5 local uncommitted changes. TRUST ACTUAL local checkout after inspection; do not assume branch equals local.

## Task deliverables
1. A coherent project-aware 3-pane Codex shell with the existing sidebar untouched; center persistent chat; right existing tool surfaces, including Editor.
2. Shared typed tool registry, dynamic skill loader, computer/coding runtime with auditable permissions and project/task orchestration.
3. Optional creative jackets and seven craft skills; full operating skill set in package.
4. Persistent versioned project knowledge graph and normalized task/edit handoffs.
5. Independent manual screenplay, comic storyboard, images, prompts, video and editor pathways.
6. Actual end-to-end filmmaking with QA, retakes, Editor handoff and final export.
7. Correct H3 prompt refs/timing, first-frame semantics and LTX on/off.
8. Optional external delegates HyperFrames Studio/OpenMontage/Backlot after proof-of-concept, security/license checks.

Check real tools, exact request schemas and available workers rather than inferring capabilities from prompts. When implementing, use existing APIs/ledgers first. User must be able to interrupt and direct the agent just like Codex.


## NON-NEGOTIABLE: global + project skills for BOTH agents

Vibe Director **and** Vibe Editor are equal clients of one **shared, runtime-discoverable skill service**. Each can discover, inspect, selectively load, and use (a) globally installed agent skills, (b) application/bundled skills, and (c) project-owned skills, including the 13 skills in this package. Do not hardcode a list of global skill directories or equate a skill Markdown file with an executable tool. Discover actual global sources/interfaces from the live agent/runtime; if absent, report the unavailable source and support configuration. Skills added/updated/disabled during app usage must become discoverable after cache refresh without changing application source.

Treat project-owned skills as versioned project knowledge: persist stable skill ID, source, content hash/version, enabled state, provenance, scope, and references in Save/Load; prevent cross-project leakage. For competing creative guidance, explicit current user request outranks project-specific guidance, then global/app defaults. **Safety, runtime capabilities, authorization and tool schemas outrank ALL skill text**, regardless of source. Untrusted skill content is never permission to execute shell/browser/network/GPU commands. Load relevant skill content on demand, with size/version/provenance shown; never dump every global skill into model context.

A skill can tell the agent HOW to approach a task; only a separately authorized tool adapter or connected computer runtime can DO the task. Both agents must share the same tool discovery, execution, permission, audit and recovery layers while retaining specialist editing/directing behavior. See `14_GLOBAL_AND_PROJECT_SKILL_ACCESS.md`, `13_EXISTING_SOURCE_SKILL_MERGE.md` and `08_EDITOR_HANDOFF_AND_DELEGATION.md`.

## Engineering quality and disposable testing

Favor small, cohesive, typed modules over extensions to monolithic components or giant dispatcher files. Reuse existing validated APIs and state services; avoid duplicated UI/business logic, speculative frameworks, magical path guessing, broad exception swallowing, and unnecessary dependencies. Add focused contracts, regression tests, and an explicit test cleanup plan for each phase. Synthetic test images, text, audio and video MUST be created only inside isolated test-owned locations; clean them and their test-owned media/project records using `try/finally` and safe ownership checks, even when a test fails. **Never delete user data or pre-existing test assets to achieve cleanup.** Preserve reusable test code, but remove temporary generated fixture media after use. See `15_COMPACT_CODE_AND_TEST_MEDIA_POLICY.md`.
