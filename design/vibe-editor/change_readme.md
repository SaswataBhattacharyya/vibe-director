# Vibe Editor — active integration notes (2026-11-07)

Read `fixes/change_readme.md` and `fixes/INTEGRATION_ARCHITECTURE.md` before an Editor UI change; `fixes/ACTIVE_FIXES.md` cards AUD-01, HF-01, HF-02 and MEDIA-01 are current. Historical UX02/UX03 notes were completed as bounded source changes; **do not re-add an Editor chat box**.

**Today:** `frontend/src/VibeEditorPage.tsx` renders `preview/media/timeline/style/export` tabs, saved session/revision/style, selected ranges and a JSON plan; central Director bridge `DirectorEditor` prepares creative briefs. Its single `MediaSourcePicker` retains imports/folder consent, semantic/literal search, safe deletion, native drag and preview/attach destinations through `MediaPickerManagement`. Explicit in/out ranges remain separate from browsing. New attachments often default to 0–5s selection for **preview**; that is not a whole-clip audio scan.

**Engine:** `backend/story_builder/services/vibe_editor_render.py` is a sandboxed JSON-to-HyperFrames CLI/FFmpeg renderer, not HyperFrames Studio GUI. Renderer accepts trusted validated plans, stages registered approved inputs and verifies final outputs. Never run arbitrary model-authored HTML/JS/shell. Its runtime pin and frontend library compatibility must be tested independently; `frontend/package.json` currently uses React 18.3.1 and lacks `@hyperframes/studio`.

**Target:** two work modes `AI Editor | Visual Editor` with timeline/preview/properties plus full-workspace expansion and **the same** project media/Editor session/approval/chat; initially gate new integration on an isolated, licensed Studio component feasibility spike. Full-window tab is fallback with owner-scoped handoff, not separate chat. Plan edit invalidates clearance 2; generation/render remains explicit. Flattened MP4 is an editable *clip*, not automatically editable source layers.

Tests: `frontend/tests/editor-assets.spec.mjs`, `editor-effects.spec.mjs`, `director-runtime.spec.mjs`; backend `test_agent_editor.py`, `test_agent_editor_tool_handoff.py`, `test_audio_utilities_integration.py`, and new Studio mapping/asset-auth tests. Don't discard Editor history, selected range, style rules, pending clearances, job status or export grants.

## HF-01 compatibility result — 2026-11-07

**Spike complete; production integration remains HF-02.** The installed Apache-2.0 HyperFrames CLI/Studio is **0.8.199**, already separated from the application's React **18.3.1** runtime. Current upstream Studio package **0.9.19** uses React/ReactDOM **19**; its app relies on Studio server/context interfaces. Do not add it directly to the React 18 tree or upgrade the working renderer as a side effect. Decision: an isolated Studio workspace with a Vibe-owned, owner/revision-scoped adapter.

Repeatable local probe (requires the existing editor runtime, conda `react`, FFmpeg, Playwright and `/usr/bin/chromium-browser`):

```bash
node frontend/tests/hyperframes-studio.manual.mjs
```

Executed successfully: registered disposable MP4 and WAV through the real media library; staged only those registered sources into a disposable composition; decoded 320×180 H264 and two-second WAV; played, paused and sought preview; selected properties, changed caption text, dragged the timeline video end from 2s to 1.4s; saved and reloaded both edits. Its isolated database, fixture media and Studio server are removed in `finally`. No upstream source was copied into the app. The preview used hardware browser graphics, not model generation. Bundled Playwright Chromium failed H264 decoding; system Chromium passed, so codec readiness is an integration requirement.

**Still absent:** application Visual Editor mode, authenticated project-serving route, bidirectional validated JSON plan mapping, approval invalidation on visual changes, restrictions on upstream raw-code/AI/export surfaces, native composition import, final render/export acceptance. Preview success does not verify any of these. Existing renderer and both clearances remain authoritative; the spike's permissive local Studio must never be exposed as the production adapter.

Primary sources checked: [Studio package](https://github.com/heygen-com/hyperframes/blob/main/packages/studio/package.json), [Apache license](https://github.com/heygen-com/hyperframes/blob/main/LICENSE), [Studio integration documentation](https://github.com/heygen-com/hyperframes/blob/main/docs/packages/studio.mdx). Upstream `main` is a moving research reference, not a new dependency pin.

## Reviewed speech cuts and CPU output acceptance

`EditorSpeechReview.tsx` loads complete timed segments from the saved session’s selected sources. Play the original, mark segments, then save a cut proposal. The backend resolves the completed task, owner, invocation and current source checksum; it subtracts only the evidenced intervals from the latest pending/approved timeline (or current selection). All other clips, captions, filters and dimensions remain. This supports normal-speed hard cuts; replacement audio, transitions and retimed clips require manual alignment and are rejected. It never expands a five-second edit selection silently.

The pending proposal and approved render request retain task/job/hash/removed-segment provenance. Rendering rechecks the reviewed hash including the staged copy, existing file snapshots and revision/cancellation checks. Output cannot publish if expected sound is missing. Actual disposable CPU render: 3s H264/AAC source, remove 1–1.5s, 2.5s registered output at 320×180, decoded blue frames and non-silent original audio. This verifies the existing renderer, not Studio export or semantic speech accuracy. Repeat with `VIBE_TEST_CPU_RENDER=1 conda run -n react python -m unittest story_builder.tests.test_editor_speech` from `backend`; temporary records/media are removed and cleanup asserted.

### Current in-app visual slice

`EditorVisualTimeline.tsx` shares `VibeEditorPage`'s editable plan and existing clearance flow. `editor_preview.py` supplies a read-only validated preview using the installed HyperFrames runtime; `editor_composition.py` generates markup for both preview and CPU export. Do not replace this with the unrestricted CLI Studio server. Live filters/speed require preprocessing and currently report unsupported; rich layer editing and full Studio synchronization remain HF-02 work. See the active acceptance document for actual CPU/runtime and mocked browser evidence.
