# Initial isolated T2V UI

A small React/Vite application for the isolated text-to-video workflow. Start with `npm run dev` (Vite binds to `127.0.0.1:8082` and proxies `/api` to the isolated backend at `127.0.0.1:3020`). The API is same-origin `/api/video/*`; configure the hosting proxy in the eventual integration environment. No external font or image service is needed.

## Scope

The usable screen supports editable prompt drafts, 5–10 second duration, the two agreed quality presets, explicit workflow/GPU/worker readiness checks, Generate, durable job polling, frozen request review, explicit acceptance, and draft-only retake review. First/last frame, reference-to-video, Story, Assets, Media and AI prompt editing are visibly unavailable. Retakes only record candidate-retention intent; the UI does not claim that any file was deleted. Job states follow the isolated API's `needs_review` and `accepted` states. No job is sent without clicking Generate, and no live provider or GPU run was performed as part of this UI work.

Global Status navigation is outside this initial slice. Drafts, idempotency keys, and the current job reference are stored in browser local storage. API request/response mapping is isolated in `src/lib/video-api.ts` and follows the backend agent's confirmed shape. Generation includes the exact workflow SHA and is gated on all three explicit readiness checks. After a transport loss, startup and explicit retry first use the read-only idempotency-key lookup; retry POST is allowed only after confirmed 404 and reuses the same key and frozen request. A saved active job that cannot be fetched remains a recovery-required active reference and blocks another generation. Startup itself never submits.

## Source reuse

Adapted visually from Story Builder `/home/riki/web_dev/story_builder/frontend/app/src/index.css` dark palette and its restrained card/button/input presentation. Used its pinned dependency versions for React 18, Vite 8, TypeScript, SWC React plugin and lucide-react. No source page, application shell, navigation, project API, or component files were copied. The shell, controls, workflow picker and responsive layout are new code for this screen. Source `node_modules` is linked for local verification only and is not part of product files.

## Focused browser checks

`npm run test:ui` runs two Playwright journeys with every `/api/**` call intercepted: readiness gating through review/accept/draft-only retake, and a simulated lost create response followed by idempotency lookup after reload. Set `PLAYWRIGHT_CHROMIUM_EXECUTABLE` only when using a locally provisioned Chromium binary. These checks never call a live Generate endpoint.
