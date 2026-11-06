# Skills — current implementation vs remaining work (2026-11-06)

Current source review: [code review](../fixes/CODE_REVIEW_2026-11-06.md) and [active work](../fixes/ACTIVE_FIXES_2026-11-06.md).

**Done as bounded foundation:** `agent_skills.py` provides one metadata/selected-context resolver for Director/Editor; the 13 blueprint craft skills are registered alongside existing app craft roots; launcher configures global Codex skill roots (see historical `Q07_Q08_RESULTS.md`). Respect availability/blocked entries and safe-root rules; no implicit skill activation or permission grant.

**Still incomplete:** project-owned custom skills/bindings with versioned portability, optional type/visual/directing “jackets” at project scope, rule/learning revisions across scenes, ability to use a newly installed global skill when its configured provider becomes available, and actual runtime adapters for skills' suggested tools. Avoid silently assuming every global skill supports the app's filesystem sandbox or that loaded SKILL.md grants computer use.

**For UX migration:** central Director and Editor must use the same resolver; old page-specific agents should contribute narrowly selected craft guidance, not spawn new chat stores. Preserve screenplay and prompt revision/proposal data, source hashes and already accepted skill references.

**Tests:** global/bundled/project discovery, unsafe symlinks/root absence, hash drift and invalidation, project A/B isolation, bounded context, duplicate names, Editor/Director parity, save/reload. Cleanup only synthetic test skill roots. Do not delete or alter global installations during tests.
