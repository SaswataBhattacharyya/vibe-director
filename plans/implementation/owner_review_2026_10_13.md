# Owner-requested Luna review — 2026-10-13 16:13 UTC

Reviewed the finite C1–C12 gate, final consolidated Sol report and retained evidence, then inspected current Search loading/upload/import paths, Debug recorder/journal, shared workload lease/policy, GPU admission and Media Prep dispatch source. This is a targeted follow-up, not fresh runtime certification of every workflow. The checkout and write capability are verified at `/home/riki/Documents/ChatGPT/Vibe Director`. No Git, donor copy, external provider, live generation, analysis, export or runtime-setting change occurred.

## Required fix — C5 workspace isolation

Trigger: start uploading a file or copying a catalog voice in Search, then change workspace before its response arrives. Previously upload completion changed the selected media kind and published a second, unguarded library response from the old workspace; voice completion inserted its old-workspace asset into the current list. A successful new-workspace load did not protect against these later mutation responses.

`frontend/src/MediaLibraryPage.tsx` now checks the library request generation and current workspace before applying either completion. Stale upload errors/settlement and voice errors also cannot overwrite the new view. Upload success uses the returned durable asset instead of an extra unguarded fetch; switching media kind retains the existing guarded load, and archived assets respect Show archived.

Verification: `frontend/tests/media-upload-navigation.spec.mjs` passes four mocked browser cases: ordinary upload, delayed upload across workspace navigation, ordinary catalog voice import, delayed voice import across navigation. `npm run build` passes TypeScript and Vite (existing >500 kB chunk warning). These checks use the project's isolated Playwright CLI frontend with mocked APIs and do not modify user media. Playwright MCP could not attach: `Browser is already in use for /home/riki/.cache/ms-playwright-mcp/mcp-chrome-c9ae093`. No live UI/API process identity or fresh readiness is claimed by this review.

Graphify full code-only extraction refreshed successfully: 2,849 nodes / 9,012 edges. The incremental extractor initially wrote only the changed-file graph; the full scan restored whole-project coverage.

## Remaining to the yardstick

C5 is closed after this fix; C1–C12 have no identified open coding task. Existing consolidated Sol review remains evidence for unchanged code; this bounded follow-up is the owner's requested review/fix. No additional helper review is required. Current source retains Cards/List/Carousel, separate keyword/semantic modes, playback, opt-in Debug and default-off simultaneous workload policy. GPU free memory is informational (`MIN_FREE_BYTES=0`); thermal/clock, queue and unknown-cancellation holds remain active. The queue persists waiting work and launches Media Prep workers sequentially.

| Area | Remaining evidence before application completion |
| --- | --- |
| Fresh story/screenplay | Real configured-provider authoring, exact edit/save/reload and downstream setup. |
| Video analysis and semantic search | One owner-started analysis; inspect derived assets, content indexing and relevant semantic result/timestamp. Imported-video title search/playback has already been accepted. |
| Images, characters, voices, worlds, frames | Enable the intended worker/model, generate/select real outputs, confirm saved bindings and downstream pickers. |
| Video and Current Take | Enable each supported workflow; real T2V/FFLF/R2V output, references, Retake/Next and playback. |
| Assisted/Fully automated | Bounded real progression, continuity, pause/recovery and saved results. |
| Audio/SAM | Exact model/worker prerequisites and real preview/listening/save outcomes for supported tools. |
| Assembly/export | Accepted production takes through real export and final playback. |

Manual acceptance packets remain in `plans/MANUAL_ACCEPTANCE.md`. Before each owner click: verify the serving UI/API, refresh selected-workflow readiness and idle queues, Debug ON, simultaneous workloads OFF, independent monitoring. Historical disabled workers/opt-ins and Not Checked audio are prerequisites to refresh, not current readiness measurements or completed acceptance. Remaining duration depends on runtime prerequisites, serial render times and findings; no defensible hours/percentage is available.
