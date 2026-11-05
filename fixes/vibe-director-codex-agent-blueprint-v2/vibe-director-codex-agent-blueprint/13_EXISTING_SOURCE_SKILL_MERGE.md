# Merging new skills with the existing repository

This package supplies **13 new/updated skills**. The actual application already has `skills/vibe-director/SKILL.md`, `skills/video-prompting/SKILL.md` and `design/vibe-editor/skills/vibe-editor-director/SKILL.md`; **do not delete or override these blindly**. Inspect local versions, compare relevant craft/validation boundaries, and introduce a versioned on-demand skill index. The new skill files include the previous six standalone craft skills, the production-style skill, and six new agent-execution skills. Their `../../shared/CONTRACT.md` relative links are supplied in `shared/` in this package.

The folder `legacy_skill_pack_docs/` preserves prior integration proposals for context; `codex/CODEX_MASTER_VISION.md` and the new numbered architecture files are the updated authoritative vision. `glossary/catalog.json` inventories groups but does not register callable tools.

**Deployment is not simply copying all Markdown into live instructions.** Codex must implement explicit skill retrieval, tool executor schemas, permissions, project/task persistence and stateful UI integration; after testing, install individual skills in the app repo.


## Mandatory shared global + project skill resolution

The new skills are **not** a closed list, and must never shadow the user's installed global skills merely because this package includes local `SKILL.md` files. Both Vibe Director and Vibe Editor must query the **same** registered skill resolver for global installed skills, bundled skills, and enabled project-specific skills. Global paths/providers are runtime configuration or supported plugin/agent interfaces, not hardcoded assumptions. Skill registration/discovery can refresh without rebuilding the UI. Projects must preserve skill bindings, hashes, versions and owner-scoped custom guidance on save/load. Keep global skill installations external and avoid duplicating their contents in each saved project.

When two skills collide, show both provenance/scope and resolve by explicit user selection or a documented priority rule (current request > project creative jacket > global/bundled creative defaults). No precedence rule can bypass policy, tools' JSON schemas, user permissions or provenance validation. Skill discovery and Markdown context loading are read-only; tool invocation needs independent authorization. Existing `director_skills.py` and Vibe Editor local skill paths must be adapted to use this resolver *without breaking legacy loads*. See `14_GLOBAL_AND_PROJECT_SKILL_ACCESS.md` for schemas, tests and rollout.
