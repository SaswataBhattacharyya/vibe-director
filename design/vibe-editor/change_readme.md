# Vibe Editor — current change guide (2026-11-09)

**Start with [test-first active plan](../../fixes/change_readme.md), [queue](../../fixes/ACTIVE_FIXES.md) and [runbook](../../fixes/ACCEPTANCE_TESTS.md).** This file is a component map, **not** a second task queue. Check actual branch, HEAD, dirty state and source before changing Editor behavior.

## Current implementation, not future speculation

- `frontend/src/VibeEditorPage.tsx` contains preview/media/visual/timeline/style/export views with one central Director chat and saved Editor session. `EditorVisualTimeline.tsx` edits typed plans; unsaved or stale plans block approval.
- `MediaSourcePicker.tsx` and `MediaPickerManagement.tsx` support typed attachment vs reference vs Editor selection, import/folder consent, filtering, preview and safe management. Initial selected ranges may default to five seconds; full-source analysis must not be truncated to five seconds.
- `vibe_editor.py`, `vibe_editor_api.py`, `vibe_editor_render.py`, `editor_composition.py` and `editor_preview.py` retain two clearances, saved revisions, verified owned media, CPU HyperFrames/FFmpeg rendering and export.
- `editor_studio.py`, `native_studio.mjs` launch isolated **installed HyperFrames Studio 0.8.199**. Supported caption, order, trim and framing edits return as a pending JSON proposal; arbitrary Studio layers, native history, unrestricted AI/export and soundtrack edits do not round-trip. Do not upgrade the React 18 app to upstream React 19 as a side effect.
- `ClipJoinReview.tsx`, `editor_kdenlive.py`, `kdenlive_mcp_client.mjs` use real overlap evidence plus a narrow Kdenlive MCP join: two videos, normal speed, linked audio, hard cut, 1080p/30. Desktop `.kdenlive` interchange in the owner's Flatpak GUI is still manual acceptance. It is not general Kdenlive GUI control.
- `EditorSpeechReview.tsx` prepares reviewed CPU speech cuts using actual source-correlated evidence. Do not infer creative speech understanding or audio-retiming support from transcripts.

## Test and change policy

**First T0:** do not touch Editor code. Run/review the designated static, CPU and mocked browser suites in `fixes/ACCEPTANCE_TESTS.md`. Preserve user media, selected ranges, approved history and pending jobs. For later fixes use `test_editor_preview.py`, `test_editor_speech.py`, `test_editor_kdenlive.py`, `test_video_overlap.py`, `frontend/tests/editor-visual.spec.mjs`, `editor-effects.spec.mjs`, `clip-join.spec.mjs` as appropriate.

Any Editor change must trace project revision, both clearances, owner/source hashes, all plan consumers, job recovery and output registration. A specialty backend must not silently fall back to a different renderer. Test exact stale-revision/cancel paths. Never run owner-media render, paid provider or GPU inference for routine regression work.

For detailed pinned native behavior and limitations see [native interfaces](native-interfaces.md), [Kdenlive usage](../../plans/kdenlive_clip_continuity_usage.md), [tool-access contract](../../docs/DIRECTOR_TOOL_ACCESS.md) and [shared architecture](../../fixes/INTEGRATION_ARCHITECTURE.md). Older implementation narratives remain accessible in Git history.
