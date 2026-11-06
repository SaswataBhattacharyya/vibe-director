# Remaining test work — after Q01–Q08

Current [review](../../../fixes/CODE_REVIEW_2026-11-06.md) and [active tasks](../../../fixes/ACTIVE_FIXES_2026-11-06.md) supersede completed foundation cards. Previous reported 75/76 backend and 18 browser tests were **not rerun** in this doc update.

## R01 recovery
Extend `test_agent_tasks.py` to simulate abrupt process death in three windows: after storing `submitting` before job, after job creation before `_map_job`, after mapping. GET polling discovers and verifies existing job with no new dispatch; no-job state signals deliberate recovery; wrong job/mismatched hash/duplicate raises conflict. Verify same invocation identity and no duplicate effects; human-visible task state should allow reconciliation.

## R02 bounded input
Extend `test_agent_computer.py`: CPU child never reads stdin, slow read, early exit/BrokenPipe, cancellation during delivery; short test timeout. Assert process group and writer fully reaped, no unbounded allocation, private journal remains within budget; no live Codex/provider required.

## UX01/UX02/UX03
Add `frontend/tests/three-pane-collapse.spec.mjs` and `single-director-chat.spec.mjs` (or extend `director-runtime.spec.mjs` and `create-panes.spec.mjs`). Check every left/center/right visibility combination, restore when all closed, pointer/keyboard resize, browser refresh, mobile tabs, independent project switching, unsaved Editor/timeline/media and Video Create input preservation. Assert **only one active conversational composer** on Editor while retaining tool prompt fields.
Add Editor integration with mocked reasoning: central chat, correct edit-session/range context, brief/clarification/clearance1, media-plan/clearance2 and trusted render *submission only after explicit approval*. Old Editor session messages/read-only history unchanged, wrong session/owner/old revision rejected, no hidden render from opening page. Verify old MP3 asset offer still works.

## UX04 other chat retirements
For Screenplay/Prompt/Video/Image/3D and Media Prep, compare existing proposal/recovery/apply outputs before/after migration. Do not treat a useful manual prompt textarea as a chat to remove. `MediaPrepPage` tools and EditorWorkspace shared layout must remain functional. `StudioChat.studioRequest` callers must pass after any extraction.

## Disposable fixtures and static acceptance
Use `tempfile.TemporaryDirectory`, Playwright fixture folders, test-owned project/database for TXT/PNG/WAV/MP4, and cleanup in `finally`. Assert fixtures removed even when tests fail. Never delete actual user assets or production history. Mock/CPU tests first; paid providers and GPU require separate consent. Report commands, counts, failures and cleanup honestly. No massive unrelated lint/simplification to disguise behavior changes.
