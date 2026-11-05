# Integrating the Chat-Based Director into Vibe Director

## Objective
The Director chat is the **universal control surface** for Vibe Director and Vibe Editor. It can see project state, reason about creative choices, and **invoke every supported, authorized component** through a tool registry. The user can also work manually anywhere in the application; neither path requires a rigid sequence of screens.

## Two layers (keep separate)

**Skills** = film expertise: screenplay, characters, environments, storyboard, prompts, continuity. Stored as Agent Skills `SKILL.md` and loaded on demand.

**Tools** = actual application actions: create reference image, extract frame, upload asset, generate video, switch off upscaling, place clip in editor. Skills never make a component callable on their own. A runtime bridge must expose its code as safe, typed actions.

## Desired architecture
```text
Director Chat UI
      │  natural-language requests + page/selection context
      ▼
Director Orchestrator (loads relevant SKILL.md on demand)
      ├─ Project State Reader (story, assets, scenes, clips, settings)
      ├─ Capability Registry + Permissions + Model Profiles
      ├─ Tool Execution Layer (validated schemas, job state, errors)
      └─ Skill Router (six creative skills; can combine)
              │
              ├─ Story & screenplay    ├─ Z-Image characters & backgrounds
              ├─ Comic storyboard     ├─ MiniMax H3 and other video models
              ├─ Media Prep            ├─ Frame/audio utilities
              ├─ LTX upscale settings └─ Vibe Editor timeline/export
```

## Tool bridge requirements
1. On each chat turn, pass current `project_id`, active page, selected scene/clip/asset IDs and compact recent state to the orchestrator.
2. Provide a **live** registry of available actions with strict input JSON schema, descriptions, return types, permission requirements, billing/side effect class and availability.
3. Give tool executor read/write access to permitted components, with audited changes and app-side permission enforcement. The assistant can request actions but cannot bypass authorization.
4. Return canonical asset/clip/job IDs after actions. Refresh UI and project state from successful results; do not trust optimistic assistant prose.
5. Support long-running generations with `job_id`, progress/status and completion handling through app jobs. Don't promise background work unless there is an actual job service.
6. Track model profiles and feature flags. Validate whether requested first frame, reference images, motion reference and voice samples can be combined. Block incompatible tool payloads before submitting.
7. Persist preview/editable prompts and human-approved references; do not irreversibly overwrite previous versions.
8. Support `ltx_upscaling_enabled` as a visible generation setting with a **hard skip** for upscale nodes/jobs when false. Setting must be read from real app state.
9. Make existing Media Prep audio extraction callable via the registry; add last-frame and first-frame extraction utilities using verified app code paths.
10. Allow routes like "jump to prompts" or "send this clip to editor" directly. Navigation is a tool action, not a prerequisite-locked wizard.

## Avoid these implementation errors
- A chat assistant that only explains where to click but cannot invoke app actions.
- A fixed pipeline requiring screenwriting before character creation or video generation.
- Duplicating existing TTS/audio/editing utilities instead of exposing them.
- Treating voice-clone source sample as a prerecorded dialogue track.
- Treating arbitrary reference-image attachment as a guaranteed video first-frame lock.
- Hardcoding MiniMax prompt limits for other video generators.
- Allowing hidden/upscale-off jobs to continue consuming resources.
- Losing asset identity when prompt aliases are reassigned per generation.

## Needed from upcoming app audit
- Frontend routes/components and component tree.
- Backend endpoints/tool services/jobs, auth and file storage.
- Exact model integration contracts (Z-Image, MiniMax H3, LTX, other models).
- Current Media Prep audio and image utilities.
- Vibe Editor timeline state and actions.
- Existing flow/wizard constraints, state stores, database schema, logs/tests.

Only **after** inspecting the app review Markdown and source ZIP should these abstract tools be mapped to concrete code, priorities, migration plan and implementation patches. Nothing in this starter pack assumes that integrations have already been installed.
