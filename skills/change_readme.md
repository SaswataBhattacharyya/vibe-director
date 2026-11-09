# Skills — current guidance (2026-11-09)

Follow [test-first Codex entry](../fixes/change_readme.md), [current task queue](../fixes/ACTIVE_FIXES.md) and [acceptance gates](../fixes/ACCEPTANCE_TESTS.md). Prior links to deleted dated fix guides were obsolete.

`backend/story_builder/services/agent_skills.py` registers bundled application skills, configured global skill roots and project-local selected guidance. It also loads skill packages and `shared/CONTRACT.md` from `fixes/vibe-director-codex-agent-blueprint-v2/vibe-director-codex-agent-blueprint/`. **Never delete this nested package or its SKILL.md/reference files in a documentation cleanup.** Preserve all runtime `skills/**/SKILL.md` and references.

Skills are guidance, **not execution grants**. The shared Director accepts selected skill hashes and uses the live typed tool gateway with separate owner/revision/source/approval checks. A global Codex MCP registration does not automatically expose an operation inside Vibe Director. The built-in `kdenlive-clip-continuity-and-stitching` skill directs real video analysis and pinned MCP join tools; it does not bypass user clearances.

**T0:** test skill discovery and bounded context against existing test fixtures, with no global skill install, edit or delete. Later work may improve project-owned versioning, optional specialist skills and richer tool adapters, but only after baseline/triage. Test symlinks, absent roots, source drift, duplicate IDs, per-project isolation, session recovery and approval boundaries. Keep history and accepted skill references immutable.
