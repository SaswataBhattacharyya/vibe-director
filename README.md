# Vibe Director

Local creative tools for story/screenplay development, video and image generation, characters/voices, media search and analysis, audio/music, 3D preparation, editing and assembly. Implemented routes and services do not guarantee an installed model or ready runtime.

## Run locally

Run `./start_vibe_director.sh` from this checkout. It uses the `react` Conda environment, starts or reuses the backend at `http://127.0.0.1:3020` and frontend at `http://127.0.0.1:8082`, and starts missing image/video workers. Ctrl+C stops processes started by that invocation. Install frontend dependencies with `npm ci` in `frontend/` if needed. Runtime data is under `local_data/`; ComfyUI and specialized model services have separate lifecycles. Starting services is distinct from submitting generation.

## Functionality and current changes

Use **New / Open project** in the top bar to choose an existing folder, then create or open a project. **Save project** checkpoints its story, sessions, media and tool memory there. Outputs default to `outputs/` inside that folder; each tool's output path and **Choose folder** can override the destination. **Use standalone tools** leaves project mode without requiring a workspace.

The application keeps its operational working copy in `local_data/`; the chosen folder holds `vibe-project.json`, versioned `project-data/` checkpoints and outputs. Reopening preserves newer local edits. Models, secrets and runtime installations remain application-wide. On another runtime, external output overrides require Choose/Locate again. Save retains full checkpoints and media copies, so repeated saves increase disk use. See the [project storage review](audit/PROJECT_STORAGE_REVIEW.md) for validation and recovery limits.

- **P0: Fix the Director agent harness first.** [Current Codex entry](fixes/change_readme.md) → **[Codex-like harness plan](fixes/DIRECTOR_HARNESS_P0.md)** → [active task queue](fixes/ACTIVE_FIXES.md) → [test baseline / acceptance](fixes/ACCEPTANCE_TESTS.md). Reproduce one-shot media discovery, prove real multi-step Codex/MCP/approval workflow, render five ordered clips and play verified output before unrelated new features.
- [Integration and preservation architecture](fixes/INTEGRATION_ARCHITECTURE.md): existing Director, Editor, HyperFrames, OpenMontage, Kdenlive MCP, media and jobs; not a separate implementation queue.
- [Functionality audit and code review](audit/FUNCTIONALITY_AUDIT.md): component source map, preserved contracts, findings and bounded validation.
- [Older Editor and ACE-Step requirements](plans/editor_media_output_ace_plan.md): historical feature context; current user decisions govern.
- [General design foundation](design/VIBE_DIRECTOR_FOUNDATION.md): visual guidance.
- [Project directing skill](skills/vibe-director/SKILL.md) and [video-prompting skill](skills/video-prompting/SKILL.md): runtime craft guidance.

Read only the guide relevant to the current task. Retain third-party notices in `third_party_licenses/` and bundled skill/runtime license files. The nested blueprint under `fixes/` is also a **runtime skill source**, not an active task queue.

## Native filmmaking interfaces

Vibe Editor → **Open Visual Editor → Open HyperFrames Studio** opens the native Studio. Storyboard → **Open OpenMontage Backlot** opens the native production board mirror. Studio imports supported edits as approval-required Vibe proposals; Backlot follows saved storyboard changes with playable media, and a Vibe-owned extension stages limited typed edits for review (not general upstream write-back). Setup, limits, licenses and the verified synthetic workflow are in [Native Studio and Backlot](design/vibe-editor/native-interfaces.md). Restart the backend to load these changes.

## Focused checks

FLUX Kontext editing and **Reviewed keyframes → silent video** are available in
First & Last Frames and Vibe Editor. Review, branch, FILM/RIFE interpolation and
silent MP4/FFV1 export share the Director task system. See
[frame pipeline usage and limitations](docs/FRAME_PIPELINE_USAGE.md). Restart the
backend using the normal launcher when active jobs have finished to load new code.

Follow the [T0 test runbook](fixes/ACCEPTANCE_TESTS.md) for exact preflight, typecheck/build, focused Python suites, mocked Playwright suites, optional native CPU checks, cleanup assertions and evidence reporting. Do not run production GPU/provider workloads as part of a baseline. Keep the project environment and original media unchanged.

## Kdenlive clip continuity

Compare two clips, inspect repeated footage, and approve a real Kdenlive MCP join through the existing Director and Editor. See [setup, usage, verification and remaining desktop check](plans/kdenlive_clip_continuity_usage.md).
