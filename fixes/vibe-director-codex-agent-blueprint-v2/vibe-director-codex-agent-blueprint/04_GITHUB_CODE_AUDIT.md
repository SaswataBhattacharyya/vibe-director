# GitHub code inspection — source-confirmed findings

**Repository:** `SaswataBhattacharyya/vibe-director` — code on branch **`vibe-director-current`**, initially inspected at SHA `65e9717932547cad2ef8b55e9beb2c83f7686b05` (2026-11-01), and rechecked after the push at `3b9db20304c1073c674271c8f60fc66859a7a044`. `main` still contains primarily planning documents; the application source and this `fixes/` package are on `vibe-director-current`. **The 2026-11-05 `full_review.md` and `tool_glossary/` are now in that branch. A developer's local checkout can still differ.** Reconciling actual workspace before modification is mandatory.

## Actual source inspected (via GitHub connector)
- `frontend/src/StudioShell.tsx` lines ~52–79: existing left nav and sequential stage rail; keep sidebar, de-emphasize mandatory-looking stage rail, mount center chat and right workspace.
- `frontend/src/VibeEditorPage.tsx` lines ~12–133: project/session state, chat, media attach/search, selected ranges, preview/timeline/style/export tabs. UI can be reused as right pane; `EditorWorkspace.tsx` currently provides editor conversation/preview resizing only, not universal chat.
- `frontend/src/StudioChat.tsx`: settings chat uses `/api/studio-tools/chat`; it discusses settings, does not run filmmaker tools.
- `frontend/src/ProductionStylesPage.tsx`: versioned production types/directing styles and selected snapshots, but heavy publishing/setup forms. Recast as optional production brief and advanced editor while retaining versioned storage.
- `backend/story_builder/services/vibe_editor.py` lines ~231–375: command dispatcher supports chat→brief→approval→plan→approval→render, selected asset ranges and strict validators.
- `backend/story_builder/services/vibe_editor.py` lines ~375–462: `_conversation` only returns messages for selected project/style; `run_job()` reads editor skill, gives model explicit **"Do not run tools or create files"** and either brief JSON or validated timeline-plan JSON. This IS the capability bottleneck. Add a tool-execution agent service *alongside* supported editor-plan path; don't simply delete validator instructions and give model arbitrary shell.
- `backend/story_builder/services/vibe_editor_api.py`: editor routes use narrow handler and `command|plan|export`; attach a typed cross-tool orchestrator adapter rather than turning this into an arbitrary request dispatcher.
- `backend/story_builder/services/vibe_editor_render.py`: trusted JSON → HyperFrames/FFmpeg; staged selected ranges, validation and published output. Preserve as stable rendering backend.
- `backend/story_builder/services/director_skills.py`: loads a **fixed** set of skills from `skills/vibe-director` and optionally `skills/video-prompting`; does not discover new skills or enable tool execution.
- `backend/story_builder/services/production_director_profiles.py`: versioned production type behavior profiles exist; layer visual art/style guidance, and do not confuse type with style.
- `design/vibe-editor/skills/vibe-editor-director/SKILL.md`: editor-specific craft and approval rules; it asks user to create specialist assets elsewhere. Updating skill text alone cannot grant operational access.
- `backend/story_builder/services/production_setup.py` around validation: current `fully_automated` requires `automate_steps` all false and chooses image-free route. This conflicts with intended mixed R2V/image/existing-media agent graph. Build a new unified task planner, preserve existing historical run mode.

## Updated branch reconciliation (2026-11-05)

Comparison of the previous inspected SHA with the new `vibe-director-current` head shows one large follow-up commit adding/updating substantial project, storyboard, prompt, catalogue and audit content. In particular, the checked branch now has `backend/story_builder/services/projects.py`, `storyboard.py`, `prompt_director.py`, `media_discovery.py`, `full_review.md`, `tool_glossary/` and `fixes/`. These are **current source**, not merely proposed designs.

The directly rechecked Vibe Editor files `vibe_editor.py` (Git blob `806019b4c27fd44a78ad534c2fb54c0a543b0c78`) and `vibe_editor_render.py` (Git blob `1a07845b8c43a007dbd7ea2a14a06a75c20f729c`) are unchanged from the initial inspection. The fixed skill loader `director_skills.py` (Git blob `51eb979839dce480abca48512ee9d21bb5fae9a9`) is likewise unchanged. The Editor's narrow planner and lack of a shared tool-executing agent therefore remain confirmed gaps in the pushed branch.

Project/media infrastructure has changed since the first inspection; **reuse and verify these newer modules rather than adding redundant project/catalogue systems**. The newly pushed review describes code state and prior focused tests, not proof of live GPU, computer-control or end-to-end automated filmmaking. Consult `16_UPDATED_GITHUB_RECONCILIATION.md` for precise next inspection tasks.

## Implications for implementation
1. The Editor currently has **an LLM as a constrained planner**, not an agent with tools. Extend via one shared agent runtime, used by Director and Editor, not two unrelated chatbot implementations.
2. Preserve the existing `Editor` two-approval render process as a specialized *render approval* surface; new overarching plan approval should avoid redundant per-subtask prompts without bypassing high-impact approvals.
3. The production stage rail/accepted screenplay/frozen full-run pipeline should no longer define access to unrelated manual operations. DO NOT remove admission protections.
4. The new skill files can sit under `skills/`, but update `director_skills.py` to load a versioned skill index dynamically and provide skill context on demand, not concatenate all skills on every request.
5. Preserve the local changes reported by the review, especially media-discovery replacement fingerprint fix; snapshot old behavior and run tests before touching shared components.

## References
- `https://github.com/SaswataBhattacharyya/vibe-director/tree/vibe-director-current`
- `https://github.com/SaswataBhattacharyya/vibe-director/blob/vibe-director-current/backend/story_builder/services/vibe_editor.py`
- `https://github.com/SaswataBhattacharyya/vibe-director/blob/vibe-director-current/frontend/src/VibeEditorPage.tsx`
- `https://github.com/SaswataBhattacharyya/vibe-director/blob/vibe-director-current/frontend/src/StudioShell.tsx`
- `https://github.com/SaswataBhattacharyya/vibe-director/blob/vibe-director-current/backend/story_builder/services/director_skills.py`

## Unverified matters
No new runtime or browser acceptance tests were run during this GitHub recheck; no remote shell/computer access was verified; no model-generated media was tested. Third-party GUI/licensing/versions must be checked in a separate integration spike. Follow `full_review.md` for stronger local checkout observations, but don't assume its uncommitted changes are pushed to GitHub.
