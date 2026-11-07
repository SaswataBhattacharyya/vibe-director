# Active fixes — updated against local changes over f89b758 (2026-11-07)

This is the **only active implementation queue**. Previously completed foundation is summarized in [COMPLETED_BASELINE.md](COMPLETED_BASELINE.md). Progress means code+tests, not merely an existing service or a written plan. Codex should recheck actual HEAD before working.

| ID | Priority | Status | Next concrete result / acceptance |
| --- | --- | --- | --- |
| **CAP-01** | P0 | PARTIAL | Seven typed tools now expose live readiness, schemas, scope, runtime and exact-plan approval; speech, denoise and CPU stems reuse durable jobs. Remaining: broader generation/render adapters and approved multi-step planning; Director chooses installed typed adapters, plans/approves/executes with evidence, not vague “cannot” or hallucinated capability. |
| **AUD-01** | P0 | PARTIAL | Complete-source offline CPU ASR now works for selected Editor sources or explicit chat attachments; source/hash-correlated timed evidence survives jobs/reload and informs follow-up chat/briefs. Real 9.85s MP4 analyzed beyond 5s. Reviewed transcript segments now create a revisioned normal-speed hard-cut proposal, retain unaffected footage/original sound and require clearance 2. Real synthetic CPU render passed picture/audio/duration checks. Remaining: owner-content speech judgments and retimed/replacement-soundtrack alignment; actual transcript/diagnostics with exact source timestamps; reviewed edit ranges; no claims without running analyzer; no accidental 0–5s limit. |
| **HF-01** | P0 | DONE (spike only) | Installed Apache-2.0 CLI/Studio 0.8.199 tested in isolation with owned MP4/WAV, actual decode/play/seek, timeline trim and caption save/reload. Use isolated Studio, avoiding React 18→19 upgrade; preserve existing renderer. Repeatable probe and limitations in `design/vibe-editor/change_readme.md`. |
| **HF-02** | P1 | PARTIAL | Visual timeline now edits the shared session plan (trim/order/caption/framing), expands, restores approved plans and saves as a new clearance-2 proposal. Unsaved or remotely stale drafts block approval. Sandboxed installed HyperFrames preview shares export markup and reads owned assets only; real synthetic H264 playback/pause/source-offset seeking passed. Filters/speed previews and rich Studio layer editing remain. |
| **MEDIA-01** | P1 | DONE (browser consolidation) | One picker with typed chat/model/tool/Editor destinations; preserve existing R2V and Qwen reference constraints, in/out range, folder consent/import, deletion management and per-project identity. Editor now uses the shared picker plus management actions; duplicate browser removed. Focused folder/import/delete/drop/range/reference regressions pass. Membership/index migration remains MED-INDEX. |
| **OM-01** | P1 | PARTIAL (metadata adapter) | Verified public Backlot is a read-only loopback dashboard, OpenMontage AGPL-3.0; no supported write-back interface demonstrated. Pinned d21f5d4eaa08; version-1 saved-revision metadata export maps existing scene/shot/owned asset IDs and verified hashes. Media is not bundled, upstream runtime/write-back/round-trip are not connected; Production Board only after real path proven. |
| **UX-01** | P1 | PARTIAL | Route-by-route one-composer/compactness/accessibility regression; existing Story, Screenplay, Image, Take and output changes are foundations, not approval to redo or declare perfect. |
| **FILM-01** | P2 | BLOCKED | Multi-step durable film orchestration, output QA, retake, provenance and final assembly only after CAP/AUD/Editor adapters pass. |
| **MED-INDEX** | P2 | PARTIAL | Truthful cross-project membership + index freshness and pre-pagination filters; add schema only after storage/snapshot/delete impact proof. |
| **STYLE-VIDEO** | P2 | OPEN | Optional production style/storyboard-to-video wiring and model-specific frozen reference manifests; no automatic change to old jobs. |

## Original P0 failure (now partly repaired)

Screenshot in Editor: user asks to locate gibberish. Existing assistant produces “I have not heard the audio”; `agent_tools.py`/`audio_utilities.py` already contain MP3 extraction, **but** `agent_conversation.py` only runs extraction when selected whole-asset inputs and intent align, and the Editor bridge only prepared a brief. The new separate `audio.transcribe` adapter addresses real timed analysis; the brief still cannot approve cuts or render. A happy-path “job completed” indicator is not evidence audio was analyzed. Implement tool routing and honest per-step evidence before another UI re-skin.

## Source-level acceptance gates

- Source: frontend is React 18.3.1 and currently has **no** `@hyperframes/studio` dependency. Backend `vibe_editor_render.py` already translates approved JSON plans into sandboxed HyperFrames CLI renders; this is **not** a visual Studio GUI.
- Source: `VibeEditorPage.tsx` supports `preview/media/visual/timeline/style/export` and `MediaSourcePicker` with `MediaPickerManagement`. Editor attachment defaults to first 5 seconds for selection/preview; must not be mistaken for full-asset analysis.
- Source: `agent_tools.py` exposes MP3, continuity frame, Editor brief, Codex computer, complete-source transcription, denoising and CPU stems; `agent_conversation.py` also routes several **proposal/discussion** adapters. This does **not** mean automatic access to every generation, analyzer or renderer.
- OpenMontage/Backlot live integration remains absent. A bounded metadata-only adapter/export is implemented; playable project staging, round-trip synchronization and distribution decisions remain prerequisites for Production Board.

**Do not start by rewriting UX05/UX06/UX07, R01/R02, UX01–UX03 or Q01–Q08.** Those are source-implemented, with runtime quality/live provider gaps noted in baseline. Preserve assets/session revisions/frozen jobs/clearances in every slice.

Use [INTEGRATION_ARCHITECTURE.md](INTEGRATION_ARCHITECTURE.md) for contracts and [ACCEPTANCE_TESTS.md](ACCEPTANCE_TESTS.md) for focused checks.
