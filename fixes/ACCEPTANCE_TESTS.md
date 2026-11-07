# Acceptance checks — future code slices (not tests run for this docs commit)

Run focused tests in disposable test-owned projects. Mock UI/provider where appropriate, but distinguish mock/CPU evidence from verified real source audio or actual HyperFrames Studio functionality. Report real commands, exit codes, media outputs and blockers. Do not trigger paid/GPU generation or full-access Codex incidentally.

## CAP-01 / AUD-01

- Discovery truth: FFmpeg installed vs missing; transcription service present vs absent; image/video/render worker ready vs not. Correct `ready`, `reason`, valid schema. A skill/glossary entry never grants tool runtime.
- Select a **7+ second** synthetic video with a spoken fixture and a designed error at >5s: analysis requests the whole asset or explicitly selected interval, not preview range. Extraction of MP3 alone does NOT satisfy time-coded error detection.
- Test two cases: actual timed analyzer runs and returns source-aligned timestamps/confidence; analyzer unavailable produces precise blocker and no invented words/times. Editing only after reviewed ranges and two existing clearances. Preserve the non-target soundtrack/pacing if requested; if removing duration changes, tell user and require confirmation.
- Wrong project, stale sha, selection revision changed, aborted job, repeated request key, missing artifact, deleted source and concurrent chat interactions cannot apply edits or duplicate jobs. Inspect logs/output hashes and registered derived media before reporting success.
- Focused backend candidates: `test_agent_tools.py`, `test_agent_tasks.py`, `test_agent_editor.py`, `test_audio_utilities_integration.py` plus new timed-analysis tests. Frontend `director-runtime.spec.mjs` and Editor tests.

## HF-01 / HF-02

- Disposable Studio compatibility smoke test: React/Studio peer dependencies, CSS isolation, license notices, runtime version, imported MP4 + WAV from verified project ID, actual preview/play/scrub/trim, timeline/properties, save/reload.
- No source files exposed by arbitrary path; no cross-project asset leak; browser refresh/closed tab keeps revisioned draft. Native composition import and flattened-video fallback behave differently and are labelled correctly.
- Visual move/trim/transition/caption change updates an approved-plan **proposal**, invalidates old clearance, requires new approval and uses the existing trusted renderer. Visual output inspected for duration, FPS, dimensions, audio and exact event positions. Unsupported features are blocked visibly, not silently discarded.
- Collapse central/right pane and enter/exit full-screen at desktop/tablet/mobile; no duplicate chat, no lost draft/selected media, no double job submit. Keyboard shortcuts, labels, focus, scroll and reduced-motion checks.

## MEDIA-01 / MED-INDEX

- Same registered video/audio/image appears in chat and Editor after explicit binding, no extra upload. Chat attachment alone never binds a model reference or a render track.
- Validate audio/video/image filters before pagination, selected source roles, R2V separate caps/voice, Qwen 1–3 image references, FFLF first/last roles, Editor exact start/end, wrong-owner/expired grant and deletion protections.
- Two project IDs can reference same occurrence without changing old IDs; unlink from one does not delete the other or corrupt immutable approved jobs. Reopen project checkpoints; check stale and missing media clearly. Never delete through generic picker.
- Focused tests: `test_media_library.py`, `test_media_catalogue.py`, `frontend/tests/media-source-picker.spec.mjs`, `editor-assets.spec.mjs`, `media-selection-scope.spec.mjs`.

## OM-01

- Capture upstream commit/license/API readme and compatibility decision before coding. Without a supported Studio API, mark the GUI “not integrable yet” rather than implementing fake UI.
- Round-trip at least one existing story scene/shot/asset to a separately staged OpenMontage/Backlot fixture and back; preserve IDs, revision and job provenance; never overwrite source Storyboard.
- Verify available/unavailable runtime UI and optional feature flag; no side effects in read-only dashboard; an external tab carries an authenticated/owner-scoped project handoff or is clearly just a documentation link.

## General preservation / run guidance

- Existing `frontend/tests/storyboard.spec.mjs`, `editor-assets.spec.mjs`, `editor-effects.spec.mjs`, `director-runtime.spec.mjs` and focused backend Editor/storyboard tests remain green.
- `cd frontend && npm run typecheck && npm run build`; `cd backend && python3 -m unittest story_builder.tests.test_agent_tools story_builder.tests.test_agent_editor story_builder.tests.test_audio_utilities_integration`, with actual project environment as needed.
- Playwright only against test fixtures with isolated API intercepts; screenshots at 1440/1280/900/390 widths. Test fail/retry/cleanup and verify no temporary artifacts left behind. No tests were executed by the docs cleanup commit.
