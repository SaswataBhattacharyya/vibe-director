# H3 prompting, timing and acceleration — 2026-10-23

## Actual Docker audit

See [ComfyUI H3 Turbo readiness report](COMFYUI_H3_TURBO_READINESS_REPORT_2026-10-23.md) for the verified version, existing weights, exact missing LoRA, node import failures, Docker persistence, workflow settings and staged integration plan. Running ComfyUI is 0.30.0; published Turbo requires 0.31.0+. All four Turbo-example base files are present. Initial extra weight: one 1.82 GiB LoRA; no extra Turbo custom-node repository is required by that graph. No installation or generation performed.

## Implemented now

- Director and H3 composer: short concrete visual direction; soft 60–120-word target excluding exact dialogue and required model fields. Fewer words are preferred when sufficient. Preserve source actions, speaker identities and exact dialogue; no hard truncation. Use essential setting, subject, action, camera, light and endpoint. Keep the H3 soundscape/music sections, with N/A when appropriate. No automatic rewrite of saved prompts or screenplay.
- Status → Generation timing → Record generation timing. Enable before an owner-started run. Records completed preparation, inclusive ComfyUI execution, collection/validation and inclusive post-submission worker time. Rows overlap: do not sum them. Logs are local, bounded to 8 MiB/session, downloadable, with job/settings metadata and no prompt/media contents. Not a separate denoising profiler or live ETA. Compare like-for-like duration, resolution, graph and warm/cold state before estimating future runs.
- No acceleration package, weights or workflow installed or activated. Current H3 sampling remains unchanged.

## Recommended first acceleration candidate: H3 Turbo inside ComfyUI

Source: https://github.com/ModelTC/Minimax-H3-Turbo
Setup: https://github.com/ModelTC/Minimax-H3-Turbo/blob/main/COMFYUI_SETUP_AND_INFERENCE.md
T2V graph: https://github.com/ModelTC/Minimax-H3-Turbo/blob/main/example_workflows/video_minimax_h3_t2v_lightx2v_turbo.json

Install procedure for a later bounded change: verify ComfyUI >=0.31.0 and the compatible base H3 components, download the task-matched ComfyUI Turbo LoRA into models/loras, import the official T2V graph, and retain its matching sampler/shift settings. This graph uses core nodes including MiniMaxH3ImageToVideo; no image input is required for T2V. Start with the 8-step T2V example. Optional 768p 4-step variant needs its corresponding LoRA/settings. Do not simply reduce steps on the existing base graph. Verify quantized-base compatibility and GB10 memory use before replacing the app graph.

Models from lightx2v/Minimax-h3-Turbo:
- minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors
- Optional alternative: minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors

## FastH3 / vLLM-Omni alternative

Source and exact current commands: https://recipes.vllm.ai/MiniMaxAI/MiniMax-H3

FastH3 uses distilled few-step weights plus optimized inference. The documented single-card Spark example uses FastVideo/FastH3-Omni-NVFP4-QAD with an image; prompt-only FastH3V2 examples have different hardware assumptions. This is not yet a qualified replacement for this app's text-only GB10 workflow.

The Spark recipe uses native ARM64, Python 3.12, CUDA 13-compatible drivers, vLLM 0.32.0/cu130 and the documented vLLM-Omni FastH3 branch/config. Install in a separate environment, follow the recipe's Spark residency/offload instructions, then expose a local service and add an app adapter with existing admission/watchdog safeguards. Retain ComfyUI until equivalent T2V capability and output quality are established. Moving the same model out of ComfyUI alone does not establish a speed gain.

## LTX refinement/upscaling: two different options

### NVIDIA demonstration

https://nvlabs.github.io/Sana/Sol-Engine/H3-Super-Acceleration/

This uses a four-step low-resolution H3 draft followed by three LTX 2.5 refinement steps with Sol-Attn and fast VAE components. Reported latencies are on GB200, not GB10, exclude warmup/loading, and do not establish local runtime. The linked LTX-2.5 pre-trained model is not by itself the exact custom three-step refiner checkpoint. No complete equivalent public ComfyUI graph/custom refiner package was established in this inspection.

### Released ComfyUI alternative: LTX 2.3 x4 pixel upscaler

Nodes/install: https://github.com/Lightricks/ComfyUI-LTXVideo
Workflow: https://github.com/Lightricks/ComfyUI-LTXVideo/blob/master/example_workflows/2.3/LTX-2.3_ICLoRA_Pixel_Spatial_Upscaler_Distilled.json

Required weights named by that workflow:
- ltx-2.3-22b-dev.safetensors — checkpoint, includes VAE/audio components
- comfy_gemma_3_12B_it.safetensors — text encoder
- ltx-2.3-22b-distilled-lora-384-1.1.safetensors — sampling LoRA
- ltx-2.3-22b-ic-lora-pixel-spatial-upscaler-x4-0.9.safetensors — upscaler LoRA

Use the matching ComfyUI-LTXVideo node package and compatible ComfyUI. The Docker audit now confirms its installed package fails on missing `interleaved_freqs_cis` in the core; five example node types and the required weights are absent from the live catalog. Resolve that core/package mismatch first. The example encoder filename differs from the published Comfy-Org filename: use the compatible loader format and actual selection, as detailed in the report. The external Gemma API nodes are bypassed in the inspected example; retain its active local conditioning. This is a separate alternative to NVIDIA's custom LTX 2.5 refiner. Preserve original H3 audio, inspect faces/motion and schedule refinement after the generation batch. It adds processing time and cannot guarantee recovery of missing detail.

## Verification limits

Python AST and frontend build passed; Status timing switch enabled/disabled through the browser and returned off. No test suite or GPU/provider render. Actual timing rows and Turbo/upscale speed/quality remain owner-run acceptance work. Screenshot: /tmp/vibe-generation-timing.png. ComfyUI/node/model upgrades need a separate implementation step; this note is not installation evidence.
