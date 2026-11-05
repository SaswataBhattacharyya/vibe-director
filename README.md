# Vibe Director

Local creative tools for story/screenplay development, video and image generation, characters/voices, media search and analysis, audio/music, 3D preparation, editing and assembly. Implemented routes and services do not guarantee an installed model or ready runtime.

## Run locally

Run `./start_vibe_director.sh` from this checkout. It uses the `react` Conda environment, starts or reuses the backend at `http://127.0.0.1:3020` and frontend at `http://127.0.0.1:8082`, and starts missing image/video workers. Ctrl+C stops processes started by that invocation. Install frontend dependencies with `npm ci` in `frontend/` if needed. Runtime data is under `local_data/`; ComfyUI and specialized model services have separate lifecycles. Starting services is distinct from submitting generation.

## Functionality and current changes

Use **New / Open project** in the top bar to choose an existing folder, then create or open a project. **Save project** checkpoints its story, sessions, media and tool memory there. Outputs default to `outputs/` inside that folder; each tool's output path and **Choose folder** can override the destination. **Use standalone tools** leaves project mode without requiring a workspace.

The application keeps its operational working copy in `local_data/`; the chosen folder holds `vibe-project.json`, versioned `project-data/` checkpoints and outputs. Reopening preserves newer local edits. Models, secrets and runtime installations remain application-wide. On another runtime, external output overrides require Choose/Locate again. Save retains full checkpoints and media copies, so repeated saves increase disk use. See the [project storage review](audit/PROJECT_STORAGE_REVIEW.md) for validation and recovery limits.

- [Functionality audit and code review](audit/FUNCTIONALITY_AUDIT.md): component source map, preserved contracts, findings and bounded validation.
- [Latest Editor and ACE-Step changes](plans/editor_media_output_ace_plan.md): current requested behavior.
- [General design foundation](design/VIBE_DIRECTOR_FOUNDATION.md): visual guidance; current user requests govern redesign.
- [Project directing skill](skills/vibe-director/SKILL.md) and [video-prompting skill](skills/video-prompting/SKILL.md): runtime craft guidance.

Read the relevant section for a task rather than loading all documentation. Retain third-party notices in `third_party_licenses/` and bundled skill/runtime license files.

## Focused checks

From `frontend/`, use `npm run typecheck` or `npm run build`; run relevant browser specs with `npx --no-install playwright test tests/<name>.spec.mjs`. The test configuration starts a local frontend and specs may intercept API calls; consult each spec before treating it as a mocked check.

From `backend/`, run targeted modules with `python3 -m unittest story_builder.tests.<module>`. Use the project's configured environment for dependencies. Mocked/CPU tests do not establish model compatibility or generated-media quality. Preserve runtime admission, saved-job recovery, original assets and output-folder collision handling.
