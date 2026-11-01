# Shared workflow status catalog

## Current implementation — 2026-10-12 (supersedes historical scope below)

P0 is complete for the local source tree. Status uses the existing T2V, FL2VA and R2V preflights and four image workflows, including Qwen multi-angle. Graph/model/node evidence is exposed when available. Verified render means the existing preflight validated its disposable output; it is separate from owner acceptance, which is not recorded here. Raw manifests and filesystem paths are not returned. Missing GPU telemetry, worker, feature, node/model/graph evidence or backend connection must not produce a usable status. Audio rows enumerate the actual ChatterBox, ACE-Step, audio-effect and three Control-Foley workflow files. The status endpoint now compares each graph's exact `class_type` values against one read-only ComfyUI `/object_info` snapshot. It reports the missing-node count but keeps every audio row `not_checked` because audio model availability, operation-specific safety, worker/dispatch and text limits are not fully preflighted; missing graph files remain `not_integrated`. Do not interpret installed node presence as runnable status.

The UI preserves `not_integrated` during runtime refresh, displays the source of a prompt cap, and labels unknown evidence honestly. It remains read-only. Browser tests prove draft preservation, unavailable/stale transitions and explicit recovery; they submit no media job.

### API origin

The API defaults to `127.0.0.1:3020` (`VIBE_DIRECTOR_PORT`). Vite proxies `/api` to that same origin unless `VIBE_DIRECTOR_API_PROXY` overrides it. If choosing another API port, set both values. Restart the API after backend code changes: Vite only reloads frontend code. A reachable stale/different server can produce Route not found even though the route exists here. SEO styles use `/api/media/{workspace_id}/assets/seo-styles`; asset lists use `/api/media/{workspace_id}/assets?kind=image|video|audio`.

Checks: 8 focused backend tests, including an 11-request mounted API catalog/library audit; one image capability regression; 2 Status browser regressions; TypeScript and production build. Fixtures use disposable data and injected capabilities. No live ComfyUI/model/provider test. Build output `/tmp/vibe-status-phase-build`; existing bundle-size warning remains. Later owner-clicked acceptance must establish actual generation.

## Scope

This slice adds a read-only `GET /api/status` projection and `#/status` UI route. The endpoint accepts the isolated backend's existing T2V `capability_snapshot()` result and does not independently inspect models, probe ComfyUI, check GPU safety, or dispatch a job. T2V readiness is combined with the existing runtime guard and explicit worker state. The UI refreshes the full snapshot only on page entry or explicit Refresh. While Status is mounted, it polls only the lightweight runtime and worker GET endpoints every five seconds. Status has no POST calls.

The usable T2V record states the product prompt rule (strictly below 7,000 Unicode code points, therefore maximum 6,999), 5–10 second duration, output presets 1344×768 / 864×480, fixed seed 1 and 20 steps, 16:9 aspect ratio, and zero references. FL2VA/R2V and all four image workflows use their own preflights. Audio rows inventory exact local graph files but make no runtime or prompt-limit claims without a workflow-specific check. Audio transforms without text prompts do not have a prompt limit.

## Provenance

- T2V workflow ID, version and live readiness evidence come from `backend/story_builder/services/production_t2v_capability.py` through the existing isolated server `capability_snapshot()`; no path values or `live_smoke` data are returned by the projection.
- The strict prompt rule, duration, output presets and fixed initial adapter values follow the isolated video generation contract and the existing Video UI implementation.
- Image workflow labels/IDs are the inspected `SPECS` entries in Story Builder `services/production_image_workflows.py`: Z-Image Turbo, Qwen Image 2512, and Qwen Image Edit 2511.
- Audio labels/IDs are derived from the actual Vibe workflow files in `backend/story_builder/workflows/api/audio/`: ACE-Step, timed ChatterBox TTS, RVC, voice changer/repair, emotion/style edit, noise cleanup and the three Control-Foley modes. A prior nonexistent VibeVoice row was removed. The catalog reports file presence only and does not claim live runtime readiness.
- The unavailable video rows represent requested future modes and do not claim backend workflows or verified limits.

The source Story Builder tree is read-only reference material. This implementation adds no provider or GPU calls and does not initiate generation. Backend reachability, ComfyUI node-catalog reachability, dispatch state and GPU telemetry are shown as separate facts; model/node evidence alone never marks generation usable.
