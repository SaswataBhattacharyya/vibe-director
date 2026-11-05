# Vibe Editor — code-level specialist handoff change README

Files to inspect: design/vibe-editor/skills/vibe-editor-director/SKILL.md, backend/story_builder/services/vibe_editor.py, vibe_editor_api.py, vibe_editor_render.py, frontend/src/VibeEditorPage.tsx, EditorWorkspace.tsx, lib/editor-api.ts.

## What exists, so preserve it
The current Editor has project/session messages and style rules, media selection with explicit ranges, creative brief and timeline-plan approvals, and a trusted JSON→HyperFrames/FFmpeg renderer. In vibe_editor.run_job(), the existing model instruction literally says "Do not run tools or create files." It is a restricted *render planner*, not a general tool-executing assistant. Never remove its validator or give its LLM output arbitrary executable HTML/Python/shell.

## Exact proposed change
1. Add shared agent task/chat mode (Director and Editor both call same server tool gateway/skill registry/project graph). Editor switches its specialist skill context, not its permission system or project identity.
2. Keep old vibe_editor.command actions and approved render adapter as existing supported actions. Expose only typed wrappers, e.g. editor.prepare_brief, editor.prepare_plan, editor.render_approved; never bypass selected asset+range validation.
3. For user request "extract MP3 from this selected video": resolve currently selected real asset ID and project, invoke shared audio.extract_mp3 using the *existing* audio utility service, follow durable job, display playable output and offer to attach it to Editor. Do not treat extractor completion as entire edit completion or silently replace soundtrack.
4. A Director full-film task hands Editor a plan proposal and approved source media *references*, not a secretly rendered edit. Handoff includes real workspace_id, editor_session_id, exact selected asset_id/start/end, target sequence, task_id, creative style version, expected revision. Recheck ownership/ranges when opening the work surface.
5. Keep old Editor project sessions/approved revisions. Store the new agent task ID, status and output references in shared project context so project save/load and switching remain consistent. No late result may land in another project's Editor.
6. Only after verifying actual media-analysis capability should Editor report frame defects, dialogue/lip sync or audio gibberish with evidence/timestamps. If a requested analyzer cannot inspect the content, mark blocked instead of claiming to have listened.
7. HyperFrames Studio, Backlot and OpenMontage are **optional** agents/tools behind adapters, not replacements for the trusted native renderer. Check their actual installed versions, license/auth, supported interfaces, output registration and sidecar security; no assumption that third-party GUI can be embedded in an iframe.

## Short change to Editor craft SKILL.md (after agent runtime exists)
Append:

    ## Tool-using specialist handoffs
    This skill provides creative editing guidance. For actual cross-tool tasks,
    the Editor requests typed authorized operations from the same shared Agent
    gateway used by Vibe Director. The old render-only JSON planning prompt
    remains non-executable and cannot invoke arbitrary commands or add
    unselected media. Keep explicit approvals and input/range validation.

This text is advice; it does not itself make the Editor capable of executing tools. Reuse backend/story_builder/services/agent_skills.py to load global/app/project skills selectively, rather than introducing separate Editor-only discovery.

## Blast-radius & tests
- vibe_editor_api.handle routes /api/editor/projects/{id} with command/plan/export and old state shapes: preserve.
- Existing style learning remains explicit/confirmed, not automatically cross-project.
- Editor job status and result collection remain truthful, including cancellation/paused export.
- Wrong-project, stale-revision and unselected-range plans must fail.
- CPU vertical slice must return real extracted audio asset and preserve original source bytes.
- Confirm edits/exports use trusted HyperFrames adapter and project output grants. Temporary synthetic test media must be removed afterward.
