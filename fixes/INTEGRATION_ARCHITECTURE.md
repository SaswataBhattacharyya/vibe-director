# Integration architecture — one Director, two optional specialist engines

## 0. Terms / ownership

**Vibe Director owns project and authority**: source media IDs, membership, editor sessions, render approval, style, history, chat and jobs. HyperFrames and OpenMontage are **engines or specialized views**, not new owners of the project. The central `DirectorConversation` is the **only active AI composer** across pages. Timeline labels/prompt fields are not extra AI chat.

Current known source:
- `frontend/src/VibeEditorPage.tsx` has five subpanels and a draft JSON timeline, plus the reusable media picker and an independent Editor asset browser. `frontend/package.json` has React 18.3.1 and no Studio package.
- `backend/story_builder/services/vibe_editor_render.py` is a trusted JSON-to-HTML HyperFrames **CLI renderer** with sandbox, FFmpeg, fixed local runtime checks; it does **not** expose a HyperFrames Studio GUI.
- `agent_conversation.py` has finite intent schemas and `agent_tasks.py` a small executable allowlist; `agent_tools.py` advertises only four executable types. Other APIs in the app aren't automatically callable by the Director.
- `agent_skills.py` loads bundled and configured skills, including runtime `fixes/vibe-director-codex-agent-blueprint-v2/.../skills` plus `shared/CONTRACT.md`. **Do not delete that package just because it lives under fixes.**

## 1. Proposed visual layout

Main Vibe Editor work pane: `[AI Editor] [Visual Editor] [Expand workspace]`. AI Editor keeps current clearance, session/media/style and jobs. Visual Editor gives a real playable composition, timeline, source selection, effects/properties and export controls. Center Director chat stays mounted and retains context. Full workspace hides/collapses panels reversibly without losing chat draft, editor draft, playback or jobs; on mobile choose one surface at a time without unmounting state. If upstream Studio can't coexist with React/runtime safely, isolate it in a same-origin hosted route or explicit new tab; establish a signed/session-scoped handoff, not browser storage hacks.

Do **not** copy an external app's sidebar or its own chat into our main navigation. Do not assume it exposes a usable component library until tested.

## 2. Shared media, not shared arbitrary filesystem paths

Conceptual adapter (exact API shape only after source validation):

`MediaRef = { workspace_id, asset_id, sha256, kind, duration?, authorized_locator_id? }`
`EditSelection = { editor_session_id, expected_revision, asset_id, start, end, intended_use }`
`StudioComposition = { composition_id, editor_session_id, source_plan_revision, tracks, assets: MediaRef[], timeline_revision }`

The server resolves a MediaRef through current owned records, verifies availability/grant/hash, and stages or serves only approved bytes. Browser `File`/folder picker can require user consent and registration once; composing later must reuse that record, not silently re-upload it. Whole-asset analysis is a separate explicit action from the existing 0–5-second initial **preview range**.

Separate purposes: chat attachments supply context refs; model references bind to exact supported slots/roles; Editor selections are versioned in/out; tool inputs are task-bound; project memberships may share a verified occurrence. Do not bind one merely because another is present. Never hand the renderer a client-provided local absolute path.

## 3. One truthful capability router

`Capability = { id, ready, reason, accepted_media, input_schema, result_schema, runtime, effect, auth_scope, approval_class }`

Discovery must be live, not invented from a Markdown glossary. Skills teach selection/recipes; tools supply callable adapters; glossary documents UI semantics. Adapter flow:

1. Discover actual installed service/worker readiness without side effects.
2. Model proposes a typed intent and exact registered inputs.
3. Host validates ownership, input media kind, revision/hash, runtime limits and permission; if unavailable, explain precisely.
4. Host records a recoverable proposal, asks for necessary approval and submits to existing durable job gateway.
5. Poll actual status, verify output metadata/digest, register output, expose provenance. Never infer successful inspection from “job completed” alone.

Keep computer tool permission scopes and no generic “execute shell” loophole. An analyzer used for speech must **actually process audio and return time alignment**, not merely convert WAV/MP3. Routes and adapters should reuse `audio_utilities.py`, existing analyzer/transcription capabilities where verified, `vibe_editor.py` and `vibe_editor_render.py`. If no timed speech analyzer is installed, mark that step unavailable and offer only legitimate extraction/manual review.

## 4. HyperFrames adapter: editable source vs flattened video

**Gate HF-01**: verify official version, Studio export surface, React peer requirements, ffmpeg/browser dependencies, licensing and safe input API. Spike in disposable project first. Existing CLI render is pinned to its own runtime, so upgrading Studio need not require upgrading the existing renderer. Do not mix incompatible versions without tests.

A source MP4 becomes a **clip element in a composition** (trim/order/effects/overlays editable). It cannot magically recover separate original text, layers, 3D objects or effects from already flattened pixels. A native HyperFrames composition, if present and safely importable, may expose more layers.

Draft timeline mapper: Editor approved-plan JSON → view-model → visual controls → validated proposed JSON. Preserve resolution/FPS, source ranges, transition lengths, caption text, speed/effect whitelist, soundtrack/audio policy and style snapshot. Unknown edit features must show unsupported rather than be dropped. Client changes increment revision and invalidate clearance 2; render still occurs via trusted host adapter, **never model-authored arbitrary HTML/JS/shell**. Visual preview is not final export verification.

## 5. OpenMontage / Backlot: optional production adapter

**Gate OM-01**: verify actual upstream repository/branch/licence, API, install, authentication, commercial/distribution obligations and which dashboard is read-only. OpenMontage “Backlot” concepts may fit a production board; don't assume private/unreleased Studio GUI can be embedded. Prefer import/export of versioned story/scene/shot/asset/job manifests with exact mapping to existing Storyboard IDs. The normal storyboard remains functional if OpenMontage is absent. Link to external Backlot or use an isolated route only when session/source synchronization is verified. No parallel “truth” for story revisions or approved outputs.

## 6. Persistence and regression boundaries

Preserve `pa-*` project asset identities, source checksums/locations, approved Editor selected ranges and two clearances, prior plans, style memories, durable task correlation, checkpoint reload, output grants and frozen job configs. A user switching project while Studio is open must not leak media across owners. Cross-project reuse requires an explicit binding with deletion protection. Always show unsupported/missing/transcript-not-reviewed states rather than fabricate evidence.

Order: `CAP-01 → AUD-01 → HF-01 → HF-02 + MEDIA-01 → OM-01 → FILM-01`. Source-specific tests and consent gates: [ACCEPTANCE_TESTS.md](ACCEPTANCE_TESTS.md).
