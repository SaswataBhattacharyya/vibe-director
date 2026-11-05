# Codex instruction — Phase 0 ONLY (no source edits)

Audit the currently opened Vibe Director repository. DO NOT implement in this task. Produce `docs/agent-rebuild/LOCAL_RECONCILIATION_PLAN.md` only if user expressly permits writing a planning document; otherwise print the plan in chat.

1. Print current branch, HEAD SHA and `git status --short` (never overwrite local changes). Compare with uploaded Nov 5 `full_review.md` and `vibe-director-current` Nov 1 GitHub source. Review Vibe Editor files (`frontend/src/VibeEditorPage.tsx`, `EditorWorkspace.tsx`, `backend/story_builder/services/vibe_editor.py`, `vibe_editor_api.py`, `vibe_editor_render.py`) and backend skill/runtime/worker modules.
2. Inventory all actual public tool endpoints and their readiness/security/execution semantics using `tool_glossary/catalog.json` as leads. Describe which 44 groups are actionable vs navigation-only. Note missing computer runtime and its OS/dependency options.
3. Inspect test baseline, migration/dependency risks, app Save/Load semantics and current GPU/ComfyUI capabilities WITHOUT submitting generation.
4. Produce a concrete phase-by-phase file-level plan, source-linked evidence and acceptance criteria: chat/tool gateway/graph first, Media Prep Extract MP3 vertical slice, agent/computer runtime, skills/style/screenplay/board, video/QA/Editor, external optional adapters. Include permission approval gates and LTX design.
5. STOP. Ask "Approve Phase 1 implementation?" and wait. No code changes, package installs, GPU/paid calls or destructive cleanup.
