# Post-transfer code audit — 2026-10-22

## Scope and outcome

Owner requested code checks across readiness, preserved media, analyzer, Image Detailer, audio, standalone generation and Assisted manual. No real provider/GPU generation or media deletion was performed during this audit. Passing mocked tests does not establish successful inference.

Found and fixed one production recovery bug: the bench-press job `ef63725f-c7fe-455d-95a5-c0929310d6b4` returns HTTP 404 after cleanup, but the browser retried it indefinitely as a connection failure. `frontend/src/App.tsx` now clears that missing job's active/history pointers on confirmed 404, keeps the draft prompt, and stops polling. Transport/service failures still retain recovery. Standalone Current Take also no longer renders story assembly or queries a deleted story merely because it remains selected elsewhere.

## Results by requested area

| Area | Evidence | Result / remaining limitation |
| --- | --- | --- |
| Status and paths | Live capabilities; all 666 transfer manifest entries have existing sources/targets and matching target sizes; 64 protected files rehashed unchanged | No broken transferred paths found. Manual T2V/R2V available; all four required video models present. Z-Image and Qwen image workflows usable. FL2VA remains intentionally disabled. Full automation needs fresh verified renders because cleanup removed smoke outputs. |
| Existing media | Preserved downloaded video and voice content URLs each returned HTTP 206 with correct media types; saved analysis `video-1376e2fcd013` returned readable structured content | Media serving and saved analysis retrieval work. Audible playback/visual decoding was not manually assessed. |
| Video analyzer | Live capabilities report source, six model groups, container images and adapter ready; focused capability, sampling, launcher and result tests | Code checks pass; no new inference run. |
| Image Detailer | Integration tests plus source-to-adapter path review | Code checks pass; no new model description generated. |
| Audio | TTS/F5 preflight, voice enrollment, pause tags, scene/effects adapters and utility integration tests; live F5 dependencies/checkpoints ready | Code checks pass. MP3 extraction available. Noise cleanup and Demucs currently need their existing containers started; this is a runtime dependency. Other audio catalog entries marked Not Checked do not claim model/runtime verification. |
| Standalone | Mocked T2V readiness, preview, submit, acceptance and retake; R2V collation, preview and frozen reference IDs; backend image/video admission and contract checks | Code checks pass; no actual Low image/video rendered. |
| Assisted manual | Reviewed Director's shot prompt, selected masters, speaker voice bindings, capacity/issue handling and preceding accepted same-scene clip reference; mocked Next prompt preparation and removed-shot refusal; backend clip-plan/skip/admission tests | No regression found in inspected paths. A fresh complete two-shot real generation/acceptance journey remains owner acceptance; not performed by this audit. |

## Verification

- 209 focused backend CPU/mocked tests passed across analyzer, Image Detailer, audio, shared media, image/video contracts, capabilities, admission and clip planning.
- Eight focused mocked Playwright browser tests passed: three new missing-job/connection recovery cases, assembly optional audio/export, standalone T2V flow, next prompt preparation, removed-shot refusal and R2V reference flow.
- TypeScript check passed.
- Updated stale browser fixtures to account for automatic readiness requests, the collapsed optional audio picker, and pinned screenplay revision URLs. Updated one backend skipped-shot fixture to mock the newer stage-skip prerequisite. These were fixture corrections, not additional product fixes.
- Playwright MCP could not initialize because its shared Chrome profile was already in use. Browser tests used an isolated Playwright CLI browser with all relevant API routes mocked; no actual generation submitted.
- Graphify refreshed after code changes.

## Owner action

Refresh Vibe Director once to load the recovery fix. The absent bench-press job will be released automatically; its prompt remains editable. No need to regenerate it merely to stop recovery.

Keep real render verification separate from this code audit. Starting missing audio service containers and completing fresh owner-clicked render acceptance are the remaining runtime checks; this audit does not mark the whole application inference-verified.
