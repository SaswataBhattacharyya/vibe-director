# UI action and state audit — 2026-10-22

Use the installed diagnosing-bugs skill with state-transition tests in Playwright and backend prerequisite tests. A skill guides investigation; executable assertions detect regressions.

For each button record: workspace/revision, prerequisites, enabled/disabled reason, request, saved result, destination, retry behavior and stale response handling. Cover boundaries and interacting pairs. Do not promise every theoretical combination.

| Area | States | Expected behavior | Evidence / remaining work |
|---|---|---|---|
| Full entry | Assisted/Full; missing, unaccepted, stale screenplay | Start only for current accepted Full context | Existing full-run-video-entry tests |
| Start | Ready, missing model, unsafe GPU, absent worker, busy queue | One explicit submission or clear disabled reason and Status route | Mock browser matrix |
| Refresh | Running unchanged/changed, completed, slow, failed, retry | Preserve pinned run; visible check/error/busy state; no POST | New browser tests |
| Poll | Active run, pending identity review, slow request | Read only; one in-flight check; visible failure | Existing identity test + slow refresh test |
| Pause / Stop | Failed clip; planning pause; owner request | Plan: Pause prevents new tasks, preserves current job; Stop boundary unspecified | Existing failure/planning resume tests only. Owner Pause/Stop controls are missing; clarification pending on Refresh menu and Stop cancellation semantics |
| Files | Missing, deleted, unreadable, unsupported, preserved | No false playback or endless deleted-job recovery | Earlier deleted-job checks; extend per tool |
| Settings | Saved/unsaved model; supported effort; frozen run | Persist validated choices; preserve frozen run inputs | Separate Director settings checks |
| Isolated | T2V/R2V/first-last; prompt/reference boundaries | Mode-specific prerequisite reasons and correct job/workspace | Existing video-ui suite; wider rerun pending |
| Assisted | Fresh plan, accept, retake, Next, continuity | No unresolved advancement; correct next prompt/reference | Existing assisted tests; live acceptance separate |
| Navigation | Active or waiting Full run; workspace/revision changes; late old response | Existing active run opens Current Take without submitting; ignore stale results | Two new return/navigation browser tests; delayed context-switch test still pending |
| Other tools | Analyzer, detailer, TTS, audio utilities, images | Same prerequisite/request/result/destination contract | Per-tool audit required |

Browser responses are mocked. This matrix does not certify inference, output quality or all application buttons. Keep active owner runs uninterrupted; live submissions remain owner-clicked.

Latest evidence: full-run-video-entry.spec.mjs 18/18 mocked browser tests and TypeScript pass. Playwright MCP failed with its shared browser profile already in use; isolated CLI Playwright used.
