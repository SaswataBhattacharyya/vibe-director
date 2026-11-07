# Vibe Editor — active integration notes (2026-11-07)

Read `fixes/change_readme.md` and `fixes/INTEGRATION_ARCHITECTURE.md` before an Editor UI change; `fixes/ACTIVE_FIXES.md` cards AUD-01, HF-01, HF-02 and MEDIA-01 are current. Historical UX02/UX03 notes were completed as bounded source changes; **do not re-add an Editor chat box**.

**Today:** `frontend/src/VibeEditorPage.tsx` renders `preview/media/timeline/style/export` tabs, saved session/revision/style, selected ranges and a JSON plan; central Director bridge `DirectorEditor` prepares creative briefs. Its internal asset browser duplicates part of `MediaSourcePicker`; preserve import/folder controls, safe delete/relink and explicit in/out ranges before consolidating. New attachments often default to 0–5s selection for **preview**; that is not a whole-clip audio scan.

**Engine:** `backend/story_builder/services/vibe_editor_render.py` is a sandboxed JSON-to-HyperFrames CLI/FFmpeg renderer, not HyperFrames Studio GUI. Renderer accepts trusted validated plans, stages registered approved inputs and verifies final outputs. Never run arbitrary model-authored HTML/JS/shell. Its runtime pin and frontend library compatibility must be tested independently; `frontend/package.json` currently uses React 18.3.1 and lacks `@hyperframes/studio`.

**Target:** two work modes `AI Editor | Visual Editor` with timeline/preview/properties plus full-workspace expansion and **the same** project media/Editor session/approval/chat; initially gate new integration on an isolated, licensed Studio component feasibility spike. Full-window tab is fallback with owner-scoped handoff, not separate chat. Plan edit invalidates clearance 2; generation/render remains explicit. Flattened MP4 is an editable *clip*, not automatically editable source layers.

Tests: `frontend/tests/editor-assets.spec.mjs`, `editor-effects.spec.mjs`, `director-runtime.spec.mjs`; backend `test_agent_editor.py`, `test_agent_editor_tool_handoff.py`, `test_audio_utilities_integration.py`, and new Studio mapping/asset-auth tests. Don't discard Editor history, selected range, style rules, pending clearances, job status or export grants.
