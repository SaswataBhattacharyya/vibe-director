# ComfyUI / H3 Turbo readiness report

Audited 2026-10-23. Scope: actual Docker runtime, host files, live node/model catalog and published workflows. No installation, restart, model download or generation was performed. Screenplay and application state were not changed.

## Installation handoff for the setup-folder Codex

Use [the complete copy-ready H3 Turbo + LTX installation prompt](LTX_COMFYUI_INSTALLATION_PROMPT.md). It includes the required Turbo LoRA, reuse of all four existing H3 base components, ComfyUI upgrade, Turbo T2V UI/API workflows and node checks, followed by individual LTX Hugging Face downloads and model destinations, reuse of existing nodes/files, the official workflow download plus derived UI/API workflows, local encoding, source-audio preservation, Docker persistence, and `dep_solver` wheel/dependency requirements. Give that file to Codex opened in `/home/riki/web_dev/setup_comfy_and-stuff`. It is an installation task packet; this audit did not execute it.

## 1. Decision

**Evaluate H3 Turbo T2V in the existing ComfyUI first.** The four base components named by its published example are already installed. The initial additional model download is one approximately **1.82 GiB Turbo LoRA**. No additional Turbo custom-node repository is required by that graph.

The immediate prerequisite is a controlled ComfyUI upgrade: the running version is **0.30.0**, below the published **0.31.0+** requirement. Existing nodes being present does not qualify this older version. Keep the base T2V workflow as a fallback; do not replace its 20 steps with 4 without the Turbo LoRA and matching settings.

LTX upscaling is a separate follow-up. Its custom package exists but currently fails to import, and its required weights are missing. FastH3 outside ComfyUI is a larger alternative integration, not required for this first evaluation.

## 2. Actual local setup

| Item | Observed value |
|---|---|
| Host setup directory | `/home/riki/web_dev/setup_comfy_and-stuff` |
| Compose file | `/home/riki/web_dev/setup_comfy_and-stuff/docker-compose.yml` |
| Service / container | `comfyui` / `comfy-stack` |
| Image name | `setup_comfy_and-stuff-comfyui` |
| Running image ID | `sha256:0abd26ee91f2830f38d62d8b47594918dac7a9773503d523eedbf1b58de1ba1a` |
| Bind mount | Entire setup directory → `/workspace`, read/write |
| Host source directory | `/home/riki/web_dev/setup_comfy_and-stuff/ComfyUI` |
| Container source directory | `/workspace/ComfyUI` |
| Python executable | `/opt/comfy/bin/python` |
| Local API / browser | `http://127.0.0.1:3008` |
| ComfyUI version | **0.30.0**, confirmed by `/system_stats` and source |
| Source revision | `2eb609766a749e3104485979615e062e401bab97`; describe: `v0.30.0-17-g2eb60976` |
| Frontend / workflow templates | 1.48.6 / 0.11.31 |
| Platform | Linux aarch64, Python 3.12.3 |
| GPU / driver | NVIDIA GB10 / 580.178.04 |
| Torch family | torch 2.11.0+cu130, torchvision 0.26.0+cu130, torchaudio 2.11.0+cu130 |
| Transformers / Diffusers | 4.57.3 / 0.39.0 |
| Container configuration | GPU enabled, host IPC, 16 GB shm, restart unless stopped |
| Storage snapshot | About 2.3 TiB free; no immediate disk capacity blocker |
| Queue snapshot | No running or pending Comfy jobs at audit time |
| Live node catalog | 2,528 registered types |

The API reports about 121.7 GiB total unified memory. Its GPU and system totals describe shared memory; they must not be added together as independent RAM + VRAM. `nvidia-smi` does not report a conventional dedicated VRAM total here. Disk/model size is not a peak inference memory estimate.

The source checkout had no tracked changes at inspection; untracked `controlfoley/` and `custom_nodes_backups/` exist and must be preserved. No `extra_model_paths.yaml` was found in this source root; the live loader dropdowns corroborate the primary model files listed below.

### Docker persistence and update trap

The models and source persist through the `/workspace` bind mount. **The `/opt/comfy` Python environment is not that bind mount**: container-only pip changes are not a reproducible image update and can disappear on recreation.

`docker/comfy/entrypoint.sh` uses `/workspace/.docker-comfy-bootstrap-complete`. A forced bootstrap can pull multiple custom-node repositories and reinstall their requirements. It also manages protobuf/ONNX/audio/native compatibility. **Do not use `FORCE_BOOTSTRAP=1` as a Turbo installer.** Updating source alone may also leave new Python requirements unapplied because the bootstrap stamp remains.

The Dockerfile already handles CUDA 13, ARM64 and specialized native packages, including ONNX Runtime GPU and rasterizers. Preserve that working Torch/native stack. Review dependency changes explicitly; avoid a blanket Manager update or unconstrained pip upgrade of every package.

## 3. H3 downloads and paths

All model destinations below are beneath:

`/home/riki/web_dev/setup_comfy_and-stuff/ComfyUI/models`

| Component | Relative path | Local status / size |
|---|---|---|
| T2V base diffusion model | `diffusion_models/minimax_h3_fl2va_pruned_int8_convrot.safetensors` | Present, 19.53 GiB |
| Text encoder | `text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` | Present, 14.61 GiB |
| Video VAE | `vae/minimax_h3_video_vae_fp16.safetensors` | Present, 4.85 GiB |
| Audio VAE | `vae/minimax_h3_audio_vae_fp32.safetensors` | Present, 0.56 GiB |
| Initial Turbo LoRA | `loras/minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors` | **Missing**, 1,956,193,000 bytes / 1.82 GiB |
| Optional 768p alternative | `loras/minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors` | Missing; about 1.82 GiB; not needed initially |

The four existing base filenames exactly match the published Turbo T2V graph. Reuse them; about 39.55 GiB of base files need not be downloaded again. The separate existing `minimax_h3_ref2va_pruned_int8_convrot.safetensors` is for reference generation and is not required for the owner's automated T2V route.

Official [Turbo setup](https://github.com/ModelTC/Minimax-H3-Turbo/blob/main/COMFYUI_SETUP_AND_INFERENCE.md), [repository/settings](https://github.com/ModelTC/Minimax-H3-Turbo) and [LoRA files](https://huggingface.co/lightx2v/Minimax-h3-Turbo/tree/main).

### Example download command for the later installation

This is a prepared command, **not executed**. Run with an account allowed to write the models directory, using an available Hugging Face CLI; check permissions before downloading rather than using world-writable permissions.

```bash
hf download lightx2v/Minimax-h3-Turbo \
  minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors \
  --revision 30f485ed874aa44c8183348ad361c5eabad318da \
  --local-dir '/home/riki/web_dev/setup_comfy_and-stuff/ComfyUI/models/loras'
```

Use the **ComfyUI BF16 LoRA**, not a similarly named Diffusers training package. Repository revision above was resolved during this audit. Newer v1.1/v1.2/v1.3 variants are not interchangeable with the v1.0 example without reviewing their recipes.

## 4. Turbo nodes and workflow settings

Use the official [Turbo T2V workflow](https://github.com/ModelTC/Minimax-H3-Turbo/blob/main/example_workflows/video_minimax_h3_t2v_lightx2v_turbo.json).

All 18 node types used by this graph are already registered in the live server:

`BasicGuider`, `BasicScheduler`, `CLIPLoader`, `ComfyMathExpression`, `CreateVideo`, `KSamplerSelect`, `LoraLoaderModelOnly`, `MiniMaxH3ImageToVideo`, `MiniMaxH3SigmaShift`, `PrimitiveFloat`, `RandomNoise`, `ResolutionSelector`, `SamplerCustomAdvanced`, `SaveVideo`, `UNETLoader`, `VAEDecode`, `VAEDecodeAudio`, `VAELoader`.

The node called `MiniMaxH3ImageToVideo` also supports the published T2V graph with its image inputs unconnected. Its name does not mean that automated generation must attach an image.

| Profile to qualify | Steps | Video/audio sigma shift | Starting resolution |
|---|---:|---|---|
| Initial low-resolution Turbo v1.0 | 8 | 12 / 3 | Official example: 0.5 MP, 16:9 → 960×544 |
| Later comparison using that low-resolution LoRA | 4 | 12 / 3 | Same dimensions for a fair comparison |
| Optional dedicated 768p 4-step LoRA | 4 | 6 / 3 | Matching 768p recipe; separate qualification |

Start with Euler and the graph's corresponding scheduler. The low-resolution v1.0 LoRA documentation supports both 8 and 4 NFE. Reducing 20 to 8/4 steps reduces denoising work, but cannot promise proportional total latency because loading, encoding, decoding and validation remain.

**Subgraph import caution:** the downloaded JSON contains subgraph proxy-widget overrides. Inner widgets include stale 20-step and unrelated LoRA defaults; the exposed T2V instance overrides them. Import, select the exact model/settings, inspect the resolved graph and export an API graph before app adaptation. Do not construct the app graph by copying inner widget defaults alone.

For initial qualification use 5 seconds, then 10 seconds. FPS is 24 and frame counts follow the model's `17k+5` grid. Existing Vibe code caps a nominal 30-second clip at 719 frames / 24 fps (29.958 seconds); retain this. The node describes training lengths around 5–15 seconds, so a 30-second application ceiling is not evidence that long Turbo clips are good or economical. Qualify longer durations separately.

Use a distinct output prefix, e.g. `video/vibe_h3_turbo`, and preserve existing original videos. Keep concise visual direction plus H3 soundscape/music fields and exact speaker-labelled dialogue. Do not add image/video/audio references to Full mode.

## 5. Controlled installation sequence for the next change

1. Wait for an idle queue and stop app successors before maintenance. Record the current source commit, image ID, custom-node revisions and pip inventory; retain existing source/config/model paths and screenplay.
2. Select a released ComfyUI revision **at least 0.31.0** compatible with this CUDA/ARM64 stack. Fetch and verify its exact tag/commit before checkout. Review its requirements against the existing Torch pins; do not blindly update every custom node.
3. Apply required Python dependency changes specifically in `/opt/comfy`, with constraints preserving the proven CUDA stack. Persist the same changes in the Docker build recipe. A source bind update does not update the image's Python packages automatically.
4. Download the single initial Turbo LoRA above. Import the official T2V workflow, resolve model selections and export the actual API graph. Keep base and Turbo graphs separate.
5. Restart the intended service only after the maintenance changes are ready. Read `/system_stats`, `/object_info` and filtered startup logs. Confirm the new version, all graph node types and every loader option. An installed folder alone is insufficient.
6. Prepare the exact 5-second prompt, seed and resolution with queue/watchdog checks. Owner clicks Generate for a bounded first render. Inspect video, audio, timing and GPU behavior before app rollout.
7. Compare warm runs at the same duration/resolution/seed/prompt across base, Turbo 8 and Turbo 4. Record cold-load runs separately. Do not run expensive benchmark batches automatically.
8. After acceptable output, add the versioned app profile described below. Roll back source **and** matching dependency image if qualification fails; restoring only source is insufficient after pip changes. Retain Turbo model files harmlessly on disk rather than deleting preserved media.

No restart/update commands were executed during this report. Future maintenance can use `docker compose ... restart comfyui` for an existing compatible image or a controlled rebuild/recreate when the image recipe changes; choose based on the actual dependency delta, not as a blanket instruction.

## 6. Vibe Director adaptation work

Current implementation still uses the base T2V graph. In `backend/story_builder/services/minimax_h3_graph_compiler.py`, the default is 20 steps and validation permits 8–40: **4-step Turbo is currently rejected**. The `minimax_h3_t2v.py` adapter loads `backend/story_builder/workflows/api/minimax_h3_t2v_api.json`; the base graph has no Turbo LoRA stage.

Required bounded changes after Comfy qualification:

- Add an explicit versioned Turbo T2V API graph with LoRA between base loader and guider, correct sigma shifts, sampler and 4/8-step profile validation. Keep base fallback.
- Extend workflow catalog/preflight to require the exact LoRA, resolved nodes and compatible version. Freeze profile, LoRA identity, graph hash, steps, shifts and resolution in each job so recovery cannot silently switch recipes.
- Pass the chosen profile consistently through isolated T2V, Assisted manual and Full worker paths. Preserve the text-only Full rule and user-selected references in Assisted; do not rewrite the three standalone Create forms.
- Keep saved screenplay and exact reviewed prompts intact. Existing stop/pause/recovery, admission/queue checks and independent GPU monitoring must also wrap Turbo.
- Include profile/steps/LoRA identity in timing records. Current inclusive timing stages overlap; **do not sum them** or call inclusive Comfy time denoising time. They are enough for end-to-end comparison, not a kernel profiler or live ETA.

This report does not implement those changes or mark Turbo usable in the product.

## 7. Later LTX 2.3 x4 option: actual blockers and downloads

Installed package: `ComfyUI/custom_nodes/ComfyUI-LTXVideo`, revision `aceeae9635f6d493f2893ba3c411a1c36031788a`.

**Confirmed startup error:** `cannot import name 'interleaved_freqs_cis' from 'comfy.ldm.lightricks.model'`. This is a core/custom-package API mismatch. Update or pin a mutually compatible pair; adding weights or reinstalling Torch alone will not fix it.

Five types used by the published x4 example are absent from the live catalog: `GemmaAPITextEncode`, `LTXAddVideoICLoRAGuide`, `LTXICLoRALoaderModelOnly`, `LTXVSetAudioRefTokens`, `LTXVTiledVAEDecode`. Existing core LTX nodes do not establish that this package imports successfully.

Its local Git status also encountered an LFS temporary-directory/filter error. Repair/inspect that checkout before updating it; do not reset or delete it blindly. Requirements include `ninja~=1.11.1.4`, while installed Ninja is 1.13.2; resolve this constraint deliberately alongside existing packages.

Official [node package](https://github.com/Lightricks/ComfyUI-LTXVideo) and [x4 example](https://github.com/Lightricks/ComfyUI-LTXVideo/blob/master/example_workflows/2.3/LTX-2.3_ICLoRA_Pixel_Spatial_Upscaler_Distilled.json).

| Required asset | Destination under models | Download / size |
|---|---|---|
| `ltx-2.3-22b-dev.safetensors` | `checkpoints/` | [Lightricks LTX-2.3](https://huggingface.co/Lightricks/LTX-2.3/blob/main/ltx-2.3-22b-dev.safetensors), 42.98 GiB |
| `ltx-2.3-22b-distilled-lora-384-1.1.safetensors` | `loras/ltxv/ltx2/` to match example | [Distilled LoRA](https://huggingface.co/Lightricks/LTX-2.3/blob/main/ltx-2.3-22b-distilled-lora-384-1.1.safetensors), 7.08 GiB |
| `ltx-2.3-22b-ic-lora-pixel-spatial-upscaler-x4-0.9.safetensors` | `loras/ltxv/ltx2/` | [Pixel upscaler](https://huggingface.co/Lightricks/LTX-2.3-22b-IC-LoRA-Pixel-Spatial-Upscaler/blob/main/ltx-2.3-22b-ic-lora-pixel-spatial-upscaler-x4-0.9.safetensors), 0.61 GiB |
| Gemma 3 12B encoder | `text_encoders/`, selected in loader | See compatibility note below |

All four are missing from the inspected live model catalogs. Existing Gemma **4** is not the required Gemma **3**.

**Encoder naming discrepancy:** the example selects `comfy_gemma_3_12B_it.safetensors`; the official [Comfy-Org packaged encoder](https://huggingface.co/Comfy-Org/ltx-2/tree/main/split_files/text_encoders) is named `gemma_3_12B_it.safetensors` (22.71 GiB). The node README also documents a [Google Gemma directory-format download](https://huggingface.co/google/gemma-3-12b-it-qat-q4_0-unquantized). Choose the format supported by the resolved loader after fixing the package; select its actual filename rather than assuming a rename makes formats equivalent. License/access acceptance may be required. Approximate total with the packaged BF16 encoder is **73.4 GiB**, excluding caches, temporary files and outputs; format choice changes this.

The example includes external `GemmaAPITextEncode` nodes, but both are **mode 4 (bypassed)** in the inspected JSON; active local `CLIPTextEncode` nodes use the encoder. Preserve local conditioning in the exported API graph, prune bypassed external API nodes and verify routing. No API key is required for the intended local path.

The example uses eight sampling intervals, Euler CFG++, distilled LoRA strength 0.5 and upscaler LoRA strength 1.0. Retain its schedule when qualifying. This is generative refinement: it may change faces/details and is not guaranteed to restore exact original detail.

For our workflow, finish H3 generation first, unload its models, then run a separate queued upscale pass. Preserve original H3 audio explicitly during muxing, duration and FPS. x4 takes 864×480 to 3456×1920, or 960×544 to 3840×2176; that can be excessive for a 1080p target. Benchmark target-appropriate refinement later rather than promising faster overall production from adding another large model.

## 8. Other installed-node problems observed

Filtered startup logs also show ComfyUI-Manager failing on missing Python `git` (GitPython) and `ncnodes` failing on missing Python `ffmpeg`. These are package imports, distinct from the shell Git/FFmpeg binaries. Impact Pack/Subpack and tensorops also have import failures. They are **not dependencies of the audited Turbo graph**; do not expand the Turbo change into a blanket repair. If Manager is needed later, repair its specific dependencies in the reproducible image first; do not assume it currently works because its directory exists.

## 9. FastH3 and NVIDIA refinement are different projects

The [vLLM FastH3 recipe](https://recipes.vllm.ai/MiniMaxAI/MiniMax-H3) has a Spark image-conditioned example and different prompt-only hardware assumptions. It would need its own environment/service and Vibe adapter. Do not install vLLM into `/opt/comfy` or replace the current Torch stack to try it. Running outside ComfyUI alone does not establish a speed improvement.

The [NVIDIA H3 → LTX demonstration](https://nvlabs.github.io/Sana/Sol-Engine/H3-Super-Acceleration/) uses specialized H3/LTX 2.5 acceleration on GB200. Its latency and custom three-step refinement are not evidence for this GB10 or the released LTX 2.3 eight-interval Comfy workflow.

## 10. Evidence and next acceptance record

Read-only sources: Docker inspect/compose/Dockerfile/entrypoint, host source revisions and model files, container Python package versions, `/system_stats`, `/object_info`, `/queue`, filtered startup errors, official workflow JSON and Hugging Face file metadata. Temporary raw audit files: `/tmp/h3-turbo-audit/` (not durable production state).

Downloaded workflow JSON SHA-256 snapshots:

- Turbo T2V: `aacfc7e7627ef72c95fdc0baaf7f3f39fa8944c37bf6427b3d3a6a7a28eec817`
- LTX x4: `c4acc08def6656316b44f838bac4fca23d5a75a3690c30344df2a2f99be21ba9`

For each owner-generated comparison retain: profile/graph hash, model/LoRA identity, prompt identity, seed, seconds, exact dimensions/frame count, cold/warm state, elapsed stages, output validity, audio clarity, visible motion and peak memory/thermal observations. No local Turbo speed estimate or successful render is claimed yet.

**Next smallest implementation:** controlled Comfy upgrade + the one Turbo LoRA + published 8-step T2V qualification; then 4-step comparison; then Vibe integration. Defer LTX until that provides a measured baseline. Related notes: [H3 speed options](H3_SPEED_OPTIONS.md).
