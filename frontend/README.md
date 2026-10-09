# Initial isolated T2V UI

A small React/Vite application for the isolated text-to-video workflow. Start with `npm run dev` (Vite binds to `127.0.0.1:8082` and proxies `/api` to the isolated backend at `127.0.0.1:3020`). The API is same-origin `/api/video/*`; configure the hosting proxy in the eventual integration environment. No external font or image service is needed.

## Scope

The usable screen supports editable prompt drafts, 5–10 second duration, the two agreed quality presets, explicit workflow/GPU/worker readiness checks, Generate, durable job polling, frozen request review, explicit acceptance, and draft-only retake review. First/last frame, reference-to-video, Story, Assets, Media and AI prompt editing are visibly unavailable. Retakes only record candidate-retention intent; the UI does not claim that any file was deleted. Job states follow the isolated API's `needs_review` and `accepted` states. No job is sent without clicking Generate, and no live provider or GPU run was performed as part of this UI work.

Global Status navigation is outside this initial slice. Drafts, idempotency keys, and the current job reference are stored in browser local storage. API request/response mapping is isolated in `src/lib/video-api.ts` and follows the backend agent's confirmed shape. Generation includes the exact workflow SHA and is gated on all three explicit readiness checks. After a transport loss, startup and explicit retry first use the read-only idempotency-key lookup; retry POST is allowed only after confirmed 404 and reuses the same key and frozen request. A saved active job that cannot be fetched remains a recovery-required active reference and blocks another generation. Startup itself never submits.

## Source reuse

Adapted visually from Story Builder `/home/riki/web_dev/story_builder/frontend/app/src/index.css` dark palette and its restrained card/button/input presentation. Used its pinned dependency versions for React 18, Vite 8, TypeScript, SWC React plugin and lucide-react. No source page, application shell, navigation, project API, or component files were copied. The shell, controls, workflow picker and responsive layout are new code for this screen. Source `node_modules` is linked for local verification only and is not part of product files.

## Focused browser checks

`npm run test:ui` runs eight mocked Playwright journeys with API calls intercepted: two video recovery/review flows, two Status checks, and four Story authoring/import/draft flows. Set `PLAYWRIGHT_CHROMIUM_EXECUTABLE` only when using a locally provisioned Chromium binary. These checks never call a live Generate endpoint.

## Shared Status page

The `#/status` page is a read-only overview of the established MiniMax H3 T2V capability, ComfyUI reachability, worker dispatch, and GPU safety telemetry. Opening/refreshing Status issues GET requests only. The full workflow evidence snapshot is requested on entry and by the Refresh status button; while open, only lightweight runtime and worker reads refresh every five seconds. Video remains mounted while navigating to Status so its draft and active job state survive the route change. The catalog lists first/last-frame and reference-to-video as not integrated. Image and audio rows are source-catalog labels only, also not integrated; their prompt limits are explicitly unknown. See `../plans/implementation/status_catalog.md` for provenance and scope.

## Provisional Story source editor

The `#/story` route adds explicit workspace create/select, editable source text, revision saves/history/restore, and TXT/Markdown/PDF extraction preview with an explicit apply action. Text drafts remain in local storage with their base revision; save/restore use expected-current-revision checks, and a conflict keeps the draft while requiring a deliberate reload. Upload alone does not create a workspace. Codex chat, story graph, screenplay fields, and style setup are clearly pending; this slice does not complete required production setup. See `../plans/implementation/story_ui.md` for the API and scope summary.
