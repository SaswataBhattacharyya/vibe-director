# FFLF and dynamic R2V: Turbo → LTX — 2026-10-24

## Implemented route

All new first/last-frame and reference-to-video requests use version 2: H3 Turbo (4 steps) → shared LTX 2.3 + Sol-Attn refinement (3 steps) → original H3 audio remux and final validation. Separate Create modes, aspect-ratio controls and guided duration range (5–15 seconds) remain. User quality specifies the **final** canvas; H3 runs at approximately two thirds per axis, rounded to the 32-pixel grid.

| Quality | Landscape final | Numeric preset |
|---|---|---|
| Low | 1216 × 672 | 0.8 |
| Standard | 1344 × 768 | 0.98 |
| High | 1664 × 928 | 1.5 |
| Max | 1920 × 1088 | 2.0 |

Portrait swaps axes. Existing square/tablet aspect calculations remain. Older numeric presets remain accepted for saved drafts. No screenplay, prompt or media cleanup is part of this change.

## Source and adaptations

Source folder: `/home/riki/web_dev/setup_comfy_and-stuff/workflows/ricky/h3_ltx/`.

- Copied generic `H3_Turbo_FFLF_896x512_4step.api.json` to `backend/story_builder/workflows/api/minimax_h3_turbo_fl2va_api.json`; replace example prompt/output prefix. Uses the tested cabinet recipe, including the FL2V Turbo LoRA named `minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors` at **4 steps**, matching the tested graph despite its filename.
- Copied generic `H3_Turbo_R2V_896x512_4step.api.json` to `backend/story_builder/workflows/api/minimax_h3_turbo_r2v_api.json`; replace example prompt/output prefix. Uses `minimax_h3_ref2v_turbo_4step_v0.1_comfyui_bf16.safetensors`.
- Existing dynamic compiler still injects up to 9 images, 3 videos and 3 audio references with roles, tags, intents, excerpts and paired audio. The example dragon image is not a fixed product input. FFLF continues to stage ordered first and last images.
- Compared source `FFLF_to_LTX23_1344x768_3step_Sol_cabinet.api.json` and `R2V_to_LTX23_1344x768_3step_Sol_dragon.api.json` to the existing shared `minimax_h3_ltx_refine_api.json`. Reuse the shared computation; retain exact user-size ImageScale rather than fixed 1.5 scaling, dynamic prompt/input/output and style-neutral negative prompt. Preserve original H3 audio without reencoding, trimming aligned tails to the requested final duration.
- Existing shared Docker model/node installations are reused; no model copies, downloads or environment changes.

## Persistence and readiness

New guided requests use combined generator+refiner hashes:

- FFLF: `575afcdef3a80e52828bdb4df07c0c5b27939d4dbc44d074aef665f3bad18fb0`
- R2V: `7c9f2ec6bed283f0b0b761370e7798fe155ee1b1e04feb12a0d91a05c516a6b4`

Version 1 graph files and request dispatch remain for saved legacy jobs. New submissions require version 2. The existing worker/ledger owns both stages and their Comfy prompt IDs, originals, recovery, cancellation and model release. No additional controller is introduced. Pure T2V batching remains originals-first, refinements-afterward.

Manual readiness checks both H3 and LTX graphs, required node types and weight files. First manual generation does not require an earlier render. Automated guided use still requires a successful current-version output with verified file hash, video and audio. Successful owner-started standalone outputs record that evidence separately for each mode.

## Evidence and remaining acceptance

- Python syntax and graph JSON parsing passed; TypeScript/Vite production build passed (existing bundle-size warning).
- Read-only live ComfyUI preflight: FFLF and R2V available with their feature flags enabled, no missing models/nodes; queue empty. No generation performed.
- API and video worker reloaded while idle, retaining environment and enabling FFLF/R2V. API PID 3147924; worker PID 3147943. Logs: `local_data/logs/guided-turbo-ltx-{api,worker}.log`.
- Graphify code-only refreshed; workflow JSON produces no AST nodes, so inspect those graphs directly.
- Playwright browser verification blocked by profile already in use: `/home/riki/.cache/ms-playwright-mcp/mcp-chrome-c9ae093`. UI interactions are not claimed verified.
- No tests added/run, and no GPU/provider generation submitted. Owner acceptance remains: reload Create, choose FFLF with two images or R2V with chosen dynamic references, select quality/aspect/duration, Preview then Generate. Confirm Turbo → LTX → playable final with expected canvas, duration and H3 soundtrack. Other aspect ratios, long clips and larger final sizes still need live acceptance; setup trial timings do not guarantee these configurations.
