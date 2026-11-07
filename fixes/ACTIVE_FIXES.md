# Active fixes — source-audited at 9180a013 (2026-11-07)

This is the **only active implementation queue**. Previously completed foundation is summarized in [COMPLETED_BASELINE.md](COMPLETED_BASELINE.md). Progress means code+tests, not merely an existing service or a written plan. Codex should recheck actual HEAD before working.

| ID | Priority | Status | Next concrete result / acceptance |
| --- | --- | --- | --- |
| **CAP-01** | P0 | OPEN | Server-side capability catalogue returns real readiness, schemas, scopes and actionable reasons; Director chooses installed typed adapters, plans/approves/executes with evidence, not vague “cannot” or hallucinated capability. |
| **AUD-01** | P0 | OPEN | Full selected video/audio can be analyzed; actual transcript/diagnostics with exact source timestamps; reviewed edit ranges; no claims without running analyzer; no accidental 0–5s limit. |
| **HF-01** | P0 | OPEN | Isolated HyperFrames Studio UI spike, dependency/React/license/renderer compatibility documented; input from owned registered clip, save/edit/preview demonstrated; fallback decision if incompatible. |
| **HF-02** | P1 | BLOCKED by HF-01 | Right work pane AI Editor/Visual Editor modes + full-screen expansion; one persistent Director; timeline/properties/preview wired to same session/plan/assets, approval invalidated on edit, save/reload/export checks. |
| **MEDIA-01** | P1 | PARTIAL | One picker with typed chat/model/tool/Editor destinations; preserve existing R2V and Qwen reference constraints, in/out range, folder consent/import, deletion management and per-project identity. Consolidate duplicate Editor browse UI. |
| **OM-01** | P1 | RESEARCH GATE | OpenMontage/Backlot source/version/license/read-write/API feasibility report; prototype versioned adapter for Scene/Storyboard/Project assets; Production Board only after real path proven. |
| **UX-01** | P1 | PARTIAL | Route-by-route one-composer/compactness/accessibility regression; existing Story, Screenplay, Image, Take and output changes are foundations, not approval to redo or declare perfect. |
| **FILM-01** | P2 | BLOCKED | Multi-step durable film orchestration, output QA, retake, provenance and final assembly only after CAP/AUD/Editor adapters pass. |
| **MED-INDEX** | P2 | PARTIAL | Truthful cross-project membership + index freshness and pre-pagination filters; add schema only after storage/snapshot/delete impact proof. |
| **STYLE-VIDEO** | P2 | OPEN | Optional production style/storyboard-to-video wiring and model-specific frozen reference manifests; no automatic change to old jobs. |

## P0 failure that motivated these cards

Screenshot in Editor: user asks to locate gibberish. Existing assistant produces “I have not heard the audio”; `agent_tools.py`/`audio_utilities.py` already contain MP3 extraction, **but** `agent_conversation.py` only runs extraction when selected whole-asset inputs and intent align, and Editor bridge `agent_editor.py` currently prepares a brief, not complete transcription, exact spoken-error detection or trim/render. A happy-path “job completed” indicator is not evidence audio was analyzed. Implement tool routing and honest per-step evidence before another UI re-skin.

## Source-level acceptance gates

- Source: frontend is React 18.3.1 and currently has **no** `@hyperframes/studio` dependency. Backend `vibe_editor_render.py` already translates approved JSON plans into sandboxed HyperFrames CLI renders; this is **not** a visual Studio GUI.
- Source: `VibeEditorPage.tsx` supports `preview/media/timeline/style/export` and both `MediaSourcePicker` + `EditorAssetBrowser`. Editor attachment defaults to first 5 seconds for selection/preview; must not be mistaken for full-asset analysis.
- Source: `agent_tools.py` exposes MP3, continuity frame, Editor brief and Codex computer; `agent_conversation.py` also routes several **proposal/discussion** adapters. This does **not** mean automatic access to every generation, analyzer or renderer.
- OpenMontage/Backlot integration does not exist in current repo. Public upstream UI/license status requires live verification before implementation.

**Do not start by rewriting UX05/UX06/UX07, R01/R02, UX01–UX03 or Q01–Q08.** Those are source-implemented, with runtime quality/live provider gaps noted in baseline. Preserve assets/session revisions/frozen jobs/clearances in every slice.

Use [INTEGRATION_ARCHITECTURE.md](INTEGRATION_ARCHITECTURE.md) for contracts and [ACCEPTANCE_TESTS.md](ACCEPTANCE_TESTS.md) for focused checks.
