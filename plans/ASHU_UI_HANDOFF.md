# Ashu UI handoff — 2026-10-08

## Ownership and starting point

Ashu owns UI design. The current screen is a provisional engineering interface, not an accepted product design. Saswata reviews the designs; UI ownership changes only if he explicitly says he is taking care of it. Project implementation resumed on 2026-10-09 at Saswata’s request. UI design ownership remains with Ashu. Live uncovered render acceptance still requires Saswata to click Generate.

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

Status/catalog and the B2 source revision foundation are now reviewed and included in this draft branch; see the 2026-10-09 checkpoint below. No OpenMontage source has been imported. Do not claim these additions, the full app, or any design issue is resolved.

## Ongoing collaboration workflow (owner instruction, 2026-10-09)

Prepare working provisional UI with each backend slice and publish completed, reviewed work in issue-linked PRs. Ashu retains UI design ownership and can refine/replace provisional layouts and interactions within agreed contracts. Provisional implementation can resolve a bounded implementation issue once its criteria are demonstrated; it does not automatically resolve Ashu's design issue. Close design issues only when the design is accepted. Push resolved work and update the issue with files, behavior, evidence, limitations and Ashu's remaining task.

Fetch Ashu's branches/PRs for local review before merging. Compare against the actual PR base/common ancestor to avoid treating existing backend code as his new changes. Inspect product alignment, contracts, preserved state/recovery and visual interaction, then recommend merge or concrete fixes. Never automatically merge on fetch, green tests or authorship. Preserve his branch; use a separate review checkout when needed.

New requirement: read `production_styles.md` before design work; production type/style precedes story and story accepts TXT/PDF uploads.


## Active checkpoint — 2026-10-09

Goal active. At meaningful completed slices: fetch collaborator branches/PRs, compare actual base, review requirements and focused evidence, publish reviewed implementation with issue updates, and record next work. Fetch does not authorize automatic merge.

Ashu PR #16 was fetched and reviewed as a design-only prototype against its actual base. Simulated T2V generation/completion/acceptance survived reload; 10 sample routes at 390px had no horizontal overflow or browser errors. Review comment requests the newer production style/import/style-video rules. PR #16 remains unmerged; #3/#4 remain open and palette acceptance is pending. Review export/server: `/tmp/vibe-ashu-review`, local port 8093 (temporary review only).

Published additions: read-only `/api/status`, `frontend/src/StatusPage.tsx` and `#/status` with model/workflow catalog, prompt limits and GPU/worker telemetry. Failed refresh withdraws readiness and marks cached readings stale. Video draft stays mounted/preserved. Two fully intercepted Status browser checks passed; one focused backend catalog test passed, plus typecheck/build. Cataloged image/audio/FFLF/R2V rows are explicitly not integrated, with unknown unverified budgets.

B2 foundation: `services/story_authoring.py` uses the existing ledger DB plus unchanged V2 revision writer and extracted exact source chunk utilities. Exact Unicode edits, hash/chunk integrity, revision history/restore, concurrency checks, monotonic revision order, collision reservations and interrupted initialization recovery have seven focused CPU tests. This is a service foundation, not an exposed authoring page/API, AI editing, knowledge graph or screenplay generator. B2 stays open.

Ashu can design Status presentation against the read-only contract and continue story/screenplay design against the plans; do not invent functional graph/edit endpoints from these foundations. Next backend work is bounded story authoring API/import integration, followed by grounded Codex editing/graph/screenplay contracts. Native output playback, FFLF/R2V generation and full automation remain pending. No live rendering was started.
