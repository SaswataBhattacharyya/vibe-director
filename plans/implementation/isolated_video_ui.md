# Isolated video UI slice

The initial React screen lives in `frontend/` and is intentionally limited to the first local text-to-video workflow. Story, Assets, Media, first/last-frame, reference-video, and AI prompt editing remain clearly unavailable. It does not add a placeholder Status page or pretend an absent integration exists.

The browser checks workflow capability, GPU safety telemetry, and explicit worker dispatch only after a user action. Generate checks all three again and is the only action that can create a job. The prompt and native settings are snapshotted and stored with a stable idempotency key before that POST. Reload only uses GET recovery. Job lifecycle uses `needs_review`, `accepted`, and explicit failure/recovery states. Only reviewable outputs with a playback URL expose the native video player.

Retake preparation returns a draft to the editor without creating a job. `keep_original` is described as retention intent; candidate deletion is not claimed. The follow-up Generate is a separate explicit operation that includes the source job and retention intent.

## Verification

- `npm run typecheck`
- `npm run build`
- `npm run test:ui` (two Playwright journeys, all API routes mocked)

No live Generate/provider call or GPU change is part of browser testing. Chromium launch may require the host-provisioned executable through `PLAYWRIGHT_CHROMIUM_EXECUTABLE`.
