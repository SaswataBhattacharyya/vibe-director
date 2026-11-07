# Codex — implement the remaining integrations, one vertical slice at a time

Current audit: `vibe-director-current` at `9180a01376a6eb254ef6c171f9d3977e4d388dfb` (2026-11-07). This is the **active** instruction; ignore historical prompt packages in `fixes/`. Start with `git branch --show-current`, `git rev-parse HEAD` and `git status --short`. Never discard user edits; if branch moved, reconcile against live source first.

## Order (do not skip the foundation)

1. **CAP-01 capability truth and routing:** inventory existing media/audio/video/image/3D services and their readiness. Keep `agent_tools.py` GET discovery as description, not permission. Add small allowlisted, typed adapters to `agent_tasks.py` / `agent_conversation.py` for genuinely supported actions, with exact owner/revision/hash/approval checks. Refuse unavailable capabilities truthfully; do not invent a generic shell endpoint or rely on a Markdown glossary as execution proof.
2. **AUD-01 full-asset audio edit:** in `VibeEditorPage.tsx`, distinguish 5-second **preview defaults** from full-asset analysis; use registered Editor inputs, create an extraction→transcription/inspection→timestamped proposal pipeline only where corresponding real analyzer services exist; exact source timestamp and confidence (with review) precede any destructive cut. Preserve soundtrack, video format/length unless user approves edits.
3. **HF-01 proof:** inspect actual installed versions, licenses and `@hyperframes/studio` dependencies (React peer compatibility versus frontend React 18.3.1). Build an **isolated disposable spike** demonstrating editable preview/timeline/properties on one registered MP4 + optional audio. Do not mutate frontend dependencies globally until the compatibility, security and render/save plan are written down and verified.
4. **HF-02 integration:** add `AI Editor | Visual Editor` modes in the Vibe Editor work pane and full-workspace expansion. Reuse Editor session, selected assets, approved versioned edit plan and rendering path; add a strictly typed composition bridge. Persist manual timeline changes as proposals, invalidate clearance 2 on mutation, preserve style/history/export grants. Use a dedicated editor tab/window as fallback only with an explicit saved-session handshake; do not clone the central chat.
5. **MEDIA-01 consistency:** consolidate redundant browse/select surfaces only after preserving Editor Asset Browser folder/drop/import and safe deletion flows. Shared `MediaSourcePicker` is the starting point; typed destination decides chat attachment vs tool input vs model refs vs Editor range. No implicit asset cloning or 0–5 second analysis truncation. Full-selected-range and whole-asset analysis are separate choices.
6. **OM-01 feasibility, then optional production board:** verify actual OpenMontage project/version, install, licensing (including AGPL obligations), APIs and Backlot semantics before integration. First ingest/publish **versioned** storyboard/scene/asset/job manifests through narrow adapters; don't embed unverified private-alpha Studio UI or replace the existing Storyboard page. An external tab can be a fallback if authenticated handoff is sound.
7. **FILM-01 later:** project-owned multi-step Director orchestration, QA, retake and final assembly after individual tools are reliable. Never declare end-to-end autonomy based only on prepared prompts or MP3 extraction.

For each slice: trace existing callers/persisted state, supply a mini file plan, implement only that slice, add focused tests per `ACCEPTANCE_TESTS.md`, run them in isolated fixtures, write observed results, then mark only genuinely accepted cards done. Do not use a stale dated guide to roll back implementation already on the current branch.

## Read code here, not the historical notes

- Shared Director: `frontend/src/DirectorRuntime.tsx`, `DirectorConversation.tsx`; `backend/story_builder/services/agent_conversation.py`, `agent_tools.py`, `agent_tasks.py`, `agent_skills.py`, `agent_graph.py`.
- Editor: `frontend/src/VibeEditorPage.tsx`, `DirectorEditor.tsx`; `backend/story_builder/services/agent_editor.py`, `vibe_editor.py`, `vibe_editor_api.py`, `vibe_editor_render.py`, `editor_effects.py`.
- Media/audio: `MediaSourcePicker.tsx`, `lib/media-api.ts`, `EditorAssetBrowser.tsx`, `services/media_library.py`, `audio_utilities.py`, and existing voice/analysis adapters.
- Storyboard: `frontend/src/StoryboardPage.tsx`, `backend/story_builder/services/storyboard.py`.
- Tests: `backend/story_builder/tests/test_agent_*.py`, `test_audio_utilities_integration.py`, `test_media_library.py`, `test_storyboard.py`, `frontend/tests/editor-assets.spec.mjs`, `director-runtime.spec.mjs`, `storyboard.spec.mjs`.

**Default next code slice: CAP-01 plus one honest audio-analysis vertical path.** Keep Visual Editor/production-board implementation behind verified upstream compatibility and source/permission checks. Do not launch GPU/paid models as part of discovery.
