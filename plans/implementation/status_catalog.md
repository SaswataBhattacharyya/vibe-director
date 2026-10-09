# Shared workflow status catalog

## Scope

This slice adds a read-only `GET /api/status` projection and `#/status` UI route. The endpoint accepts the isolated backend's existing T2V `capability_snapshot()` result and does not independently inspect models, probe ComfyUI, check GPU safety, or dispatch a job. T2V readiness is combined with the existing runtime guard and explicit worker state. The UI refreshes the full snapshot only on page entry or explicit Refresh. While Status is mounted, it polls only the lightweight runtime and worker GET endpoints every five seconds. Status has no POST calls.

The usable T2V record states the product prompt rule (strictly below 7,000 Unicode code points, therefore maximum 6,999), 5–10 second duration, output presets 1344×768 / 864×480, fixed seed 1 and 20 steps, 16:9 aspect ratio, and zero references. First + last frame and reference-to-video are unavailable in this application. Image/audio rows are informational source-catalog entries, not integrated workflows; their prompt limits remain unknown.

## Provenance

- T2V workflow ID, version and live readiness evidence come from `backend/story_builder/services/production_t2v_capability.py` through the existing isolated server `capability_snapshot()`; no path values or `live_smoke` data are returned by the projection.
- The strict prompt rule, duration, output presets and fixed initial adapter values follow the isolated video generation contract and the existing Video UI implementation.
- Image workflow labels/IDs are the inspected `SPECS` entries in Story Builder `services/production_image_workflows.py`: Z-Image Turbo, Qwen Image 2512, and Qwen Image Edit 2511.
- Audio labels/IDs are a compact catalog derived from filenames inspected under Story Builder `workflows/api/audio/` (ACE-Step, VibeVoice dialogue, timed multi-character ChatterBox TTS, RVC, voice changer/repair, emotion/style edit, noise cleanup). This does not import or copy those workflow files.
- The unavailable video rows represent requested future modes and do not claim backend workflows or verified limits.

The source Story Builder tree is read-only reference material. This implementation adds no provider or GPU calls and does not initiate generation. Backend reachability, ComfyUI node-catalog reachability, dispatch state and GPU telemetry are shown as separate facts; model/node evidence alone never marks generation usable.
