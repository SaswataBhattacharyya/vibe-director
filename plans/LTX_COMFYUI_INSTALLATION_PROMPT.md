# Copy-ready prompt: install H3 Turbo T2V and LTX upscaling in the existing ComfyUI Docker

Copy the text below into Codex opened at `/home/riki/web_dev/setup_comfy_and-stuff`. This authorizes the receiving agent to perform the described setup; this document's author has not performed the installation. Live GPU acceptance remains owner-clicked.

---

Please install and configure **H3 Turbo text-to-video generation, followed by LTX 2.3 x4 pixel spatial upscaling for completed H3 videos**, inside my existing ComfyUI Docker setup. Complete the downloads, compatible custom-node/dependency setup, persistent Docker configuration and usable workflows. Keep originals and existing tools working.

## Scope and skills

- Work in `/home/riki/web_dev/setup_comfy_and-stuff`; reuse its existing Docker service and model storage. Do not create another ComfyUI installation or duplicate model trees.
- Read this folder's AGENTS.md and setup documentation first. Use the GNU/Linux/container skills and **`dep_solver`**, including its `references/wheel-workflow.md`, for platform diagnosis, wheel probing, focused dependency resolution, isolated builds and verification. If a named skill is unavailable, report that and locate it before doing native dependency work.
- Reference audit: `/home/riki/Documents/ChatGPT/Vibe Director/plans/COMFYUI_H3_TURBO_READINESS_REPORT_2026-10-23.md`. Recheck all snapshots before changing anything.
- Install **H3 Turbo T2V and LTX upscaling** as separate workflows. Keep the existing base H3 workflow as fallback. Do not install vLLM/FastH3, edit Vibe Director's screenplay/prompts or activate an automated runner. Prepare integration artifacts so Vibe Director can wire them later. Qualify Turbo first, then LTX separately.

## 1. Inventory, deduplication and maintenance

Audited container `comfy-stack`, Compose service `comfyui`; host Comfy root:

`/home/riki/web_dev/setup_comfy_and-stuff/ComfyUI`

Container root `/workspace/ComfyUI`, Python `/opt/comfy/bin/python`, API `http://127.0.0.1:3008`. Confirm these against Compose and the live container. Record versions/revisions, Python/ABI/architecture/libc, CUDA/driver, Torch family, GPU compute capability, available memory/disk, package constraints and active queue. Never print secrets.

Before model downloads, inspect primary model directories, `extra_model_paths.yaml`, live loader dropdowns, symlinks and existing Hugging Face caches. Reuse matching complete files via their configured path; if needed create a documented compatible link rather than copying tens of GB. Detect incomplete files and resume safely. Verify downloaded files against published metadata/checksums, not filenames alone. Do not download both alternative encoder formats by default.

Snapshot exact source/custom-node revisions, Docker image identity, requirements and configuration. Inspect existing local changes and preserve them. If jobs are active, prepare downloads/builds without interfering and wait for an idle maintenance window before restarting. Do not cancel someone else's jobs.

## 2A. H3 Turbo: required downloads, existing models and workflows

Official setup: https://github.com/ModelTC/Minimax-H3-Turbo/blob/main/COMFYUI_SETUP_AND_INFERENCE.md

### Required initial download

Download only this missing ComfyUI-format Turbo LoRA, approximately **1.82 GiB**, after the common deduplication checks:

- File: `minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors`
- Direct Hugging Face link: https://huggingface.co/lightx2v/Minimax-h3-Turbo/resolve/30f485ed874aa44c8183348ad361c5eabad318da/minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors
- Host destination: `/home/riki/web_dev/setup_comfy_and-stuff/ComfyUI/models/loras/minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors`
- Expected audited size: 1,956,193,000 bytes. Record the published hash and validate the actual file.

Reuse these four already-present base components under the same ComfyUI root; verify each actual loader selection and file integrity, **do not download again**:

| Component | Existing relative path |
|---|---|
| H3 diffusion model | `models/diffusion_models/minimax_h3_fl2va_pruned_int8_convrot.safetensors` |
| H3 text encoder | `models/text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` |
| H3 video VAE | `models/vae/minimax_h3_video_vae_fp16.safetensors` |
| H3 audio VAE | `models/vae/minimax_h3_audio_vae_fp32.safetensors` |

These filenames match the audited official example. If a file has disappeared, obtain its exact replacement link from the official setup/model provenance and record it before fetching; do not silently substitute a different quantization. The reference-video H3 model is not required for T2V.

### ComfyUI and nodes

The audit found **ComfyUI 0.30.0**; Turbo's published prerequisite is **0.31.0 or newer**. Select and pin a compatible core revision satisfying both Turbo and the LTX package, review dependency changes and persist them in Docker using section 4. Do not simply change a version string or force the broad bootstrap.

All 18 example node types were already registered: `BasicGuider`, `BasicScheduler`, `CLIPLoader`, `ComfyMathExpression`, `CreateVideo`, `KSamplerSelect`, `LoraLoaderModelOnly`, `MiniMaxH3ImageToVideo`, `MiniMaxH3SigmaShift`, `PrimitiveFloat`, `RandomNoise`, `ResolutionSelector`, `SamplerCustomAdvanced`, `SaveVideo`, `UNETLoader`, `VAEDecode`, `VAEDecodeAudio`, `VAELoader`. **No additional Turbo custom-node repository is required by this graph.** Recheck after the upgrade; repair the responsible core/package only if a required type is actually absent. `MiniMaxH3ImageToVideo` supports this T2V workflow with image inputs unconnected. Keep all image/video/audio reference inputs absent.

### Download and adapt the Turbo workflow

Official workflow page:
https://github.com/ModelTC/Minimax-H3-Turbo/blob/main/example_workflows/video_minimax_h3_t2v_lightx2v_turbo.json

Raw download:
https://raw.githubusercontent.com/ModelTC/Minimax-H3-Turbo/main/example_workflows/video_minimax_h3_t2v_lightx2v_turbo.json

Download the untouched original to:
`/home/riki/web_dev/setup_comfy_and-stuff/ComfyUI/user/default/workflows/h3_turbo/video_minimax_h3_t2v_lightx2v_turbo.upstream.json`

Use the actual configured workflow directory if different. Resolve and record upstream commit/hash. Alongside it save:

- `H3_Turbo_T2V_8step_local.ui.json`
- `H3_Turbo_T2V_8step_local.api.json`
- `H3_Turbo_T2V_4step_lowres_local.ui.json`
- `H3_Turbo_T2V_4step_lowres_local.api.json`
- `H3_Turbo_T2V_README.md` and an installation manifest with provenance and resolved settings.

Initial recipe: the v1.0 low-resolution LoRA above, **8 steps, Euler, video/audio sigma shifts 12/3**, and the official matching scheduler. Start at the example's **0.5 MP / 960×544 / 24 fps / 5 seconds** for owner-clicked acceptance. A later 4-step low-resolution comparison can use this same LoRA and 12/3 shifts; save its graph but mark it unqualified until actually run. Retain every other matching upstream setting. Do not reduce steps on the base graph without its Turbo LoRA stage.

The upstream uses subgraph proxy-widget overrides: inner stale defaults include 20 steps and an unrelated LoRA. Inspect the resolved executable graph and export API JSON from the actual selected configuration; do not copy stale inner defaults. Validate graph/model selections without submitting GPU work. Use unique outputs such as `video/vibe_h3_turbo/<source-or-job-id>`; never overwrite existing files.

**Optional later 768p profile, not an initial required download:**
https://huggingface.co/lightx2v/Minimax-h3-Turbo/resolve/30f485ed874aa44c8183348ad361c5eabad318da/minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors

If separately requested, put it under `models/loras/` using that exact filename and use its matching 4-step **6/3** shift recipe. Do not substitute it into the low-resolution recipe or fetch every LoRA variant. Newer versions need their own matching recipe review.

Keep the existing 24 fps / `17k+5` frame grid and application ceiling of 719 frames (29.958 seconds); initial qualification is short, since longer Turbo clips require separate quality/memory evaluation. Preserve concise prompts and exact speaker dialogue; no screenplay rewrite.

**Vibe integration handoff:** installation alone does not switch the app to Turbo. Its current compiler accepts 8–40 steps and rejects 4; its base API graph lacks a Turbo LoRA. Provide resolved UI/API graphs, settings, hashes and node/model manifest for a later versioned app profile with existing queue/watchdog/stop/recovery safeguards. Do not claim acceleration is active in Vibe merely because ComfyUI setup finished.

## 2B. LTX exact model manifest

Use `C = /home/riki/web_dev/setup_comfy_and-stuff/ComfyUI` below. These links refer to individual files, **not whole repositories to download**. Resolve/record immutable repository revisions and file hashes. Download through Hugging Face tooling or authenticated requests without exposing tokens. If gated access is needed, give me the exact access page and continue independent preparation; do not bypass access conditions.

| File and approximate size | Direct download | Required host destination |
|---|---|---|
| LTX 2.3 dev checkpoint, 42.98 GiB | https://huggingface.co/Lightricks/LTX-2.3/resolve/main/ltx-2.3-22b-dev.safetensors | `C/models/checkpoints/ltx-2.3-22b-dev.safetensors` |
| Distilled sampling LoRA, 7.08 GiB | https://huggingface.co/Lightricks/LTX-2.3/resolve/main/ltx-2.3-22b-distilled-lora-384-1.1.safetensors | `C/models/loras/ltxv/ltx2/ltx-2.3-22b-distilled-lora-384-1.1.safetensors` |
| Pixel x4 upscale IC-LoRA, 0.61 GiB | https://huggingface.co/Lightricks/LTX-2.3-22b-IC-LoRA-Pixel-Spatial-Upscaler/resolve/main/ltx-2.3-22b-ic-lora-pixel-spatial-upscaler-x4-0.9.safetensors | `C/models/loras/ltxv/ltx2/ltx-2.3-22b-ic-lora-pixel-spatial-upscaler-x4-0.9.safetensors` |
| Packaged Gemma 3 12B text encoder, 22.71 GiB | https://huggingface.co/Comfy-Org/ltx-2/resolve/main/split_files/text_encoders/gemma_3_12B_it.safetensors | `C/models/text_encoders/gemma_3_12B_it.safetensors` |

The checkpoint and LoRAs are from Lightricks; the packaged encoder is from Comfy-Org. Rough total is 73.4 GiB before cache/temporary/output space. Do not fetch a second full distilled checkpoint: this selected workflow uses the **dev checkpoint + distilled LoRA**. Do not substitute a latent upscaler weight for the pixel IC-LoRA or download unrelated controls/camera LoRAs.

**Encoder compatibility prerequisite:** inspect the exact loader after resolving package versions, before the large encoder download. The upstream example selects `comfy_gemma_3_12B_it.safetensors`; use the actual packaged `gemma_3_12B_it.safetensors` in its compatible loader and verify format support. Renaming a file is not a compatibility fix. Existing Gemma 4 is not a substitute. If the resolved loader genuinely requires the directory-format Google encoder instead, document why and download only that format from https://huggingface.co/google/gemma-3-12b-it-qat-q4_0-unquantized into `C/models/text_encoders/gemma-3-12b-it-qat-q4_0-unquantized`, including all required tokenizer/config/shards. Do not fetch both formats speculatively.

## 3. Custom nodes: reuse and repair

Required package: **ComfyUI-LTXVideo**, official repository:

https://github.com/Lightricks/ComfyUI-LTXVideo

It already exists at `C/custom_nodes/ComfyUI-LTXVideo`; audited revision `aceeae9635f6d493f2893ba3c411a1c36031788a`. **Do not clone a second copy.** Inspect its state, preserve changes and select a compatible released/pinned core + package pair.

Known actual failure: `cannot import name 'interleaved_freqs_cis' from 'comfy.ldm.lightricks.model'`. Fix this API mismatch through compatible versions; do not stub the missing function or assume pip alone fixes it. Git also reported an LFS temp/filter error: inspect and repair without destructive reset/reclone.

The audit had ComfyUI 0.30.0. H3 Turbo separately requires >=0.31.0; meeting that minimum alone does not establish LTX compatibility. Pin and record the version actually verified for both the existing H3 base nodes and the selected LTX package.

Required LTX example types missing from the live catalog included `LTXAddVideoICLoRAGuide`, `LTXICLoRALoaderModelOnly`, `LTXVSetAudioRefTokens`, `LTXVTiledVAEDecode`. Verify the **complete chosen graph**, including core video/audio/text/sampling nodes, against `/object_info` after setup. `Note` is a UI annotation, not a backend package to install.

`GemmaAPITextEncode` is also absent, but its upstream nodes are bypassed. Keep local encoding and remove bypassed API nodes from the adapted/API graph; do not add external credentials or calls. Do not install unrelated node packs just to satisfy unused annotations or bypassed branches. Core `LoadVideo`/`GetVideoComponents`/`CreateVideo`/`SaveVideo` already existed; VideoHelperSuite was installed too. Reuse existing working nodes if needed rather than duplicating them.

## 4. Dependencies and wheels

Audited platform anchors: ARM64, Python 3.12.3, NVIDIA GB10, driver 580.178.04, Torch 2.11.0+cu130 / torchvision 0.26.0+cu130 / torchaudio 2.11.0+cu130. Reinspect current state. Preserve native ONNX GPU/rasterizer and other tool compatibility.

Read the selected LTX package's exact requirements and consuming imports. Existing local requirements included Diffusers, Einops, Hugging Face Hub >=0.25.2, Kornia, Ninja ~=1.11.1.4 and Transformers[timm] >=4.50.0. Installed Ninja was 1.13.2, outside that constraint. Resolve actual version intersections; do not silently weaken metadata or use `--no-deps` to conceal conflicts.

Prefer matching ARM64 wheels from trusted indexes. Distinguish missing wheel, resolver conflict, native ABI/linkage and Python API mismatch. Only build a native wheel if actually necessary. Build in an isolated target-matched environment with bounded parallelism, the measured GPU architecture and the package's supported build flags. Retain wheel, SHA256, source commit/patch, toolchain, constraints and logs. Do not overwrite the live environment while experimenting.

The `/workspace` source/models bind persists; `/opt/comfy` belongs to the container/image environment. Persist accepted dependency changes in the Dockerfile/build recipe and persistent wheelhouse/constraints. Do not rely on one-off container pip installs. Do not force the broad bootstrap or blanket-update all custom nodes. Snapshot and retain a rollback path for both source and image/dependencies.

Run appropriate dependency/import checks, `pip check` and CPU graph validation. Mark preexisting unrelated conflicts explicitly. After controlled recreation verify installed module origins and node registration again. Do not claim GPU behavior from imports alone.

## 5. Download the official workflow and save usable variants

Official workflow page:

https://github.com/Lightricks/ComfyUI-LTXVideo/blob/master/example_workflows/2.3/LTX-2.3_ICLoRA_Pixel_Spatial_Upscaler_Distilled.json

Raw download:

https://raw.githubusercontent.com/Lightricks/ComfyUI-LTXVideo/master/example_workflows/2.3/LTX-2.3_ICLoRA_Pixel_Spatial_Upscaler_Distilled.json

Download the original to:

`C/user/default/workflows/ltx_upscale/LTX-2.3_ICLoRA_Pixel_Spatial_Upscaler_Distilled.upstream.json`

If the configured Comfy user directory differs, use its real workflow directory and report the exact host/container paths. Record upstream commit + SHA256, keep the original unchanged and avoid overwriting existing user workflows.

Create and save these **derived artifacts** alongside it:

1. `H3_to_LTX23_x4_local.ui.json` — importable Comfy workflow with real model selections, local text conditioning, H3 input-video path and a unique output prefix.
2. `H3_to_LTX23_x4_local.api.json` — resolved API graph, with only executable nodes, no UI subgraphs/proxy defaults or bypassed API calls.
3. `H3_to_LTX23_x4_README.md` — exact loading procedure, input/output node IDs, model locations, settings, memory strategy, audio mux procedure and known limitations.
4. `installation-manifest.json` — source/image revisions, dependencies/wheels/hashes, model provenance/hashes, reusable existing files, workflows and check results.

Do not present an unmodified example containing its sample hamster prompt/input as our finished workflow. Replace the sample with a concise configurable description of the actual source clip; refinement must preserve its scene/action rather than introduce unrelated content.

Retain the published matching sampler/sigma/LoRA recipe initially (audited eight intervals, Euler CFG++, distilled LoRA 0.5, x4 IC-LoRA 1.0). Resolve links and widget overrides rather than guessing defaults.

## 6. H3 → upscale behavior

- Operate on an existing completed H3 video, after the H3 generation batch. No image/video/audio references are added to H3's text-only generation. The completed clip is the LTX upscale input.
- Unload H3 weights before loading LTX; avoid retaining both large stacks. Prepare tiled decoding and bounded/chunked processing only as supported by this workflow, with overlap/seam/duration handling documented.
- Preserve original H3 files. Write new outputs to `C/output/ltx_upscaled/`, using unique source-linked filenames; never overwrite existing preserved `output/video` or `output/videos` content.
- Preserve the original H3 soundtrack with explicit FFmpeg remuxing if the graph generates or alters audio; preserve sync, clip duration and intended FPS. Handle silent inputs too. Do not mistake audio generation from the example for a requirement to replace the soundtrack.
- x4 is large: 864×480 becomes 3456×1920. Document a separate optional final resize to the desired delivery dimensions without pretending the model natively targets 1080p.
- Keep all inference local. Do not promise exact face/text reconstruction or a total speedup from adding refinement. This is LTX 2.3 pixel upscaling, not NVIDIA's custom three-step LTX 2.5 GB200 demonstration.

## 7. Acceptance and final handoff

Prepare the exact short Turbo T2V settings first, then a separate LTX upscale of a short existing H3 input, with queue and independent GPU supervision ready. **Have me click Run for GPU acceptance**; do not auto-submit a render or start a batch. Preserve current owner GPU operating policy and never alter clocks.

Before that click, installation/dependency/CPU graph checks should be complete. Distinguish “downloaded”, “loads/registers”, “graph validates” and “GPU render accepted”. If acceptance is not run, say so clearly.

Finish with: exact downloaded/reused files and paths; installed/reused node repositories and commits; Docker/dependency/wheel changes; workflow paths; model access or compatibility blockers; rollback procedure; and a concise integration note for Vibe Director describing the API graph inputs/outputs, model unloading, audio preservation and runtime limits. Keep an execution log in this setup folder so another agent can resume without redownloading or rebuilding completed work.

---

End of copy-ready prompt. Installation has not been executed by the reporting agent.
