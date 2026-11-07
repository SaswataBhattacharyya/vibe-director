# Acceptance checks — implementation evidence and remaining gates

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
- Playwright only against test fixtures with isolated API intercepts; screenshots at 1440/1280/900/390 widths. Test fail/retry/cleanup and verify no temporary artifacts left behind. The earlier documentation-only cleanup did not execute tests; implementation evidence below is separate.

## Executed for the 2026-11-07 capability/speech slice

- Backend all-agent discovery: `cd backend && conda run --no-capture-output -n react python -m unittest discover -s story_builder/tests -p 'test_agent_*.py'` — 74 tests OK, one skipped. After bounded evidence-to-brief changes, `test_agent_transcription test_agent_editor test_agent_editor_tool_handoff` — 19 tests OK.
- `test_agent_transcription test_audio_utilities_integration test_workload_policy` — 27 tests OK. These mock analyzer/job execution; they cover frozen hashes, repeat requests, blockers, cancellation, CPU dispatch, timing validation, output registration and failure cleanup. They do not prove real denoiser/Demucs generation.
- `cd frontend && npm run build` — TypeScript/build passed; existing bundle-size and SWC recommendations remain. No separate `typecheck` script was assumed.
- `npx playwright test tests/editor-assets.spec.mjs tests/director-runtime.spec.mjs` — 30 passed against isolated API mocks. Whole-source range selection, preserved ranges, one composer, truthful task settings/labels and restored timed reports are covered. Mock fixtures emitted expected unused-endpoint/proxy diagnostics; no live application backend was used.
- `npx playwright test tests/editor-effects.spec.mjs tests/storyboard.spec.mjs` — eight existing preservation regressions passed with isolated fixtures.
- **Real runtime:** disposable synthetic WAV and 9.85s H264/AAC MP4 processed by installed offline CPU Whisper. Speech evidence reached 8.98s and contained the fixture's post-five-second keyword. ASR was imperfect (not a truth oracle). This ran the real analyzer worker directly in isolated storage; durable dispatch/recovery was tested separately with mocks. Original test sources were preserved until fixture teardown, then all temporary media/database and worker staging were verified removed.
- **Real Studio:** `node frontend/tests/hyperframes-studio.manual.mjs` passed registered MP4/WAV decode, play/pause/seek, caption and timeline trim save/reload, and fixture cleanup. See the Editor guide for versions, licensing, browser codec limitation and the isolation decision. No Studio export acceptance or application Studio bridge is implied; the existing CPU renderer was accepted separately in the next slice.

Remaining owner acceptance: repeat analysis → playback review → cut proposal → clearance 2 → output inspection with real owner content; production Studio synchronization/export; real denoiser/stem execution only when explicitly authorized. Other cards retain their own gates above.

## Executed for reviewed cuts / shared browser / metadata export

- `VIBE_TEST_CPU_RENDER=1 conda run --no-capture-output -n react python -m unittest story_builder.tests.test_editor_speech story_builder.tests.test_production_manifest story_builder.tests.test_catalogue_filters` covers 14 focused cases. The optional CPU case uses the installed sandboxed HyperFrames renderer; the other cases use mocked analyzer/dispatch data and real disposable media/catalogues. Checks include exact retained ranges, interval union, source/invocation/hash ownership, invalid/stale cuts, revisioned save/reload, approval-only submission, preserved captions/effects/dimensions, explicit rejection of retiming/replacement audio, and refusal to publish output missing expected audio.
- Real render acceptance: remove 1.000–1.500s from a synthetic 3s blue H264/AAC source; final 2.5s at 320×180, audio+video streams, decoded source-colour frames at three positions and non-silent PCM samples. Output registered into the test library only. Synthetic speech timestamps are mocked in this test; actual ASR was independently verified in the preceding slice. This does not establish human speech judgment or exact real-content lip sync.
- `test_agent_editor test_agent_editor_tool_handoff test_media_catalogue`: 28 preservation cases passed in the combined run; the new metadata fixture's initial error expectations were corrected to the existing API/catalogue contracts and its three tests subsequently passed.
- Browser: `editor-assets ace-editor-ux media-source-picker` — eight passed; `storyboard editor-speech media-selection-scope editor-effects` — eleven passed. These use isolated API mocks, including partial folder import, range persistence, paste/drop, bulk attach, confirmed deletion/cancel/blockers, reference constraints, reviewed-cut save/reload, and saved-revision production-metadata download. Download is removed in `finally`. Build/TypeScript passed. Desktop/mobile Storyboard screenshots were inspected; not every route/viewport was visually accepted.
- Metadata adapter pins upstream `d21f5d4eaa08422b09c7091757a05affcbabb35b`. Tests verify version, owned IDs/hashes, planned timing, revision conflicts, changed/foreign sources, no local path leakage and no state mutation. No upstream runtime was installed; Backlot playability/round-trip/write-back remain unverified and unavailable.
- Fixture teardown verifies removal of test-owned directories, generated media and records on success/failure. No paid/provider/GPU generation ran, no application dependency/schema migration was added, and owner projects/history were not removed.

## In-app visual timeline and HyperFrames preview (2026-11-07)

- `cd backend && VIBE_TEST_CPU_RENDER=1 conda run --no-capture-output -n react python -m unittest story_builder.tests.test_editor_preview story_builder.tests.test_editor_speech`: 11 passed, including actual CPU export after extracting shared markup. Preview covers selected-range/owner/revision checks, strict keys, escaped captions, fixed runtime paths, no state writes and no job dispatch. Read-only refinement separately passed all 3 preview tests.
- `cd frontend && npx playwright test tests/editor-visual.spec.mjs tests/editor-effects.spec.mjs tests/editor-speech.spec.mjs tests/editor-assets.spec.mjs`: 4 passed with mocked application routes. Save/reload, approved-plan restoration, unsaved approval blocking, remote conflict preservation and existing effects/speech/attachments pass. Expanded mobile sizing was subsequently checked separately; screenshots inspected.
- `node frontend/tests/editor-preview.manual.mjs`: real installed HyperFrames runtime and system Chromium decoded synthetic H264, played/paused, selected the second caption and sought timeline 1.4s to source 1.9s. During playback, timeline 1.6621s corresponded to source 2.1621s. The fixture serves byte ranges like the real content endpoint; no mocked runtime/player. Test-owned server/browser/media/database are removed in `finally`, cleanup verified. This does not establish owner-content speech quality or every transition/filter.
- Frontend TypeScript/production build passed. Existing bundle-size warning remains. No paid/provider or GPU model generation, owner-content editing, production Studio embedding or OpenMontage write-back acceptance ran.
