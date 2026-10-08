# Ashu UI handoff — 2026-10-08

## Ownership and starting point

Ashu owns UI design. The current screen is a provisional engineering interface, not an accepted product design. Saswata reviews the designs; UI ownership changes only if he explicitly says he is taking care of it. Project implementation is paused; this publication does not resume the goal or authorize new generation.

Completed implementation is on branch `issue-2-isolated-t2v-reuse`, draft [PR #15](https://github.com/SaswataBhattacharyya/vibe-director/pull/15). Clone Vibe Director and check out that branch to inspect code; cloning main alone will not include the draft implementation. Keep design changes in your own branch/PR and link the relevant D issue. Read `plans/README.md`, the stage plan and the issue before implementation. This handoff is usable by Codex or Claude; give the agent the relevant issue plus these repository paths.

## What exists and how

- `frontend/src/App.tsx`: provisional isolated T2V screen, prompt/settings, readiness, explicit Generate, durable polling, frozen request review, acceptance, history and preserved retake. Browser storage retains draft, pending idempotency key and active job; reload performs read-only recovery.
- `frontend/src/lib/video-api.ts`: existing `/api/video/*` request/response client. `frontend/src/style.css`: provisional dark responsive styling. `frontend/tests/video-ui.spec.mjs`: two fully mocked browser journeys.
- `backend/story_builder/isolated_server.py`: localhost API; `services/isolated_video_contract.py` validates/compiles requests; `services/isolated_video_jobs.py` adapts the reused ProductionLedger/worker. Existing source compiler, graph, media helpers and GPU safeguards are reused; the frontend screen is new code adapted visually from Story Builder, not a copied legacy page.
- Prompt budget is strictly below 7,000 Unicode code points. Current T2V accepts 5–10 seconds, two fixed quality presets, and no references. Only exact pinned workflow readiness plus safe GPU telemetry and an explicitly enabled healthy worker permit admission.
- Start instructions are in root, frontend and backend READMEs. Ashu can install frontend dependencies and use mocked API responses without ComfyUI/models. Local `127.0.0.1` addresses point to his own machine, not Saswata's backend.

## Preserve when redesigning

Retain explicit Generate, immutable submitted snapshots, saved unresolved-job context, same-key recovery and no startup/reload submission. Preserve exact workflow/model validation and fail-closed GPU/worker admission. Retake prepares a draft; it submits only on a later Generate. Keep/delete records retention intent; actual reference-aware deletion is pending. Separate these invariants from presentation: layout, typography, components, navigation, labels and interaction can be redesigned. If an API/state change is needed, document it and coordinate the backend adapter instead of silently inventing endpoints.

## Design work remaining

All six D issues remain open: #3 navigation/context; #4 three video forms and reference collation; #6 merged authoring/readable screenplay; #7 assets/voices; #8 Automation & Parameters; #9 Media Prep/Status. Story, Assets and Media are currently disabled. FFLF/R2V, real Codex microedits, asset selectors and automation wrappers do not work yet. Ask design questions and produce annotated layouts/prototypes, states, route/context map and bounded implementation PRs. Preserve the settled product journey and mode rules in the plans; no legacy competing pages.

## Evidence and limits

20 focused backend tests, typecheck/build and two intercepted browser journeys passed for the published T2V slice. Real UI rendering was inspected; these checks do not prove a successful new live render. No live generation/provider call was performed. FFLF live acceptance is deferred to final implementation acceptance. Existing Story Builder release evidence is retained; do not rerun the broad legacy suites just to redesign UI. New live acceptance is prepared in the UI using suitable existing Story Builder media, with monitoring, and Saswata clicks Generate.

Status/catalog and a B2 revision foundation are only locally staged in `/tmp/vibe-director-implementation`, unpublished with incomplete parent review. They are outside this published baseline. No OpenMontage source has been imported. Do not claim these additions, the full app, or any design issue is resolved.
