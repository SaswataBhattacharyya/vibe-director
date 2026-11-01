# TRELLIS.2 community multi-view service

Separate Docker image/interpreter; current Comfy environment and launchers are unchanged. Source pinned in `third_party/trellis2-multiview`; local patch and dependency evidence under `env_setup/trellis2_multiview/`.

From repository root:

```bash
env_setup/trellis2_multiview/scripts/service.sh start
env_setup/trellis2_multiview/scripts/service.sh status
env_setup/trellis2_multiview/scripts/service.sh stop
```

Local API `http://127.0.0.1:52070`. Health separates process availability, generation model loaded and worker busy. Startup does not load weights, initialize CUDA or render; native imports are deferred until the generation request. Stop refuses while worker reports busy; stopping an idle container releases retained models. Comfy start/stop and local-AI-stack scripts do not manage this new service.

Owner-triggered first test (GPU work):

```bash
python3 workflows/ricky/3d_stuff/trellis2_multiview/scripts/generate_multiview.py \
 --front /ABSOLUTE/prepared/front.png --back /ABSOLUTE/prepared/back.png \
 --preset workflows/ricky/3d_stuff/trellis2_multiview/config/front_back_512.json
```

Add `--prepare-only` to validate/save settings without contacting any service. Requires Python requests/Pillow. Client defaults output to this folder's `outputs/<timestamp-uuid>/`; original GLB, request/response/hashes/time remain together. Server originals persist separately at repository `outputs/trellis2-multiview/<request-id>/output.glb`, mounted as `/outputs`. Output files belong to the host user.

API: multipart `POST /generate-multiview`, required `front`, optional `back,left,right`; fields come from JSON presets. Response contains relative `glb_url`, request ID and textures/topology metadata. Client resolves URLs to the same origin, validates GLB header/JSON framing, and downloads original. Browser disconnected/client timeout does not stop server work. Do not retry automatically; inspect health and logs. API processes one job at a time; local busy submissions return409. Vibe must also reserve GPU across other applications—checking Comfy's queue alone is not atomic scheduling and does not unload models.

First profile: seed42,512,Euler,blend temperature2,1024 textures,100k triangle faces. Higher1024_cascade and additional views are separately unqualified presets. Separate generation/texturing pipeline was made lazy. Only multi-view triangle generation is enabled here; quad and other POST routes explicitly return422. Avoid retaining two large stacks. Low-VRAM pipeline mode is enabled; this is no memory guarantee on shared GB10 RAM.

Original model paths/configs are pinned under `models/3d-workers/trellis2-multiview/`; verified existing decoder/DINO/BiRefNet files use read-only links/mounts. Background remover is the compatible original ZhengPeng7/BiRefNet, replacing gated RMBG2 in the config; its segmentation behavior may differ and needs visual acceptance. Native Comfy checkpoints are not renamed into original format.

Prepare same-dimension aligned canvases with `scripts/prepare_views.py`. Never label three-quarter as90-degree side. Actual anatomy images still needed. View labels are semantic assumptions; no guaranteed anatomically accurate reconstruction or rig-ready topology.

Blender handoff: explicitly invoke installed Blender with `--background --python scripts/import_to_blender.py -- <original.glb> <NEW_DIR> [--render]`. It preserves source, saves a fresh inspection blend/report and optional five CPU comparison renders; axes are provisional and require visual review. No rigging or geometry cleanup is automatic. Script syntax is checked; actual generated GLB import/render remains owner acceptance.

Rollback: stop this Compose project only. Keep outputs/caches; previous Comfy image/source need no changes to roll back. Rebuilding uses `docker build -f docker/trellis2-multiview/Dockerfile -t trellis2-multiview:20261101 .`; follow recorded dependency locks/wheel hashes. Do not run the fork's original CUDA12.8/Python3.10 Dockerfile on this target.

Source limitation found during implementation: in this fork, `1024_cascade` uses only front conditioning for the shape cascade, although structure and texture use multiple views. The512 profile uses multi-view conditioning throughout. Added `front_back_1024_direct.json` and `four_views_1024_direct.json` (`pipeline_type=1024`) for the genuine multi-view higher-resolution shape path; these are unqualified and may use more memory. Do not label cascade as all-stage multi-view geometry.


Preparation completed 2026-11-01: locked image rebuild, actual HTTP health/rejection tests, container recreation, dependency checks, native imports/linkage and offline CPU auxiliary-model loading passed. Final idle health includes `cuda_initialized=false`. Model manifests contain the published revisions/checksums and reused files. Native import diagnostics briefly initialize CUDA for FlexGEMM device detection in a separate process; they do not render. Owner GPU generation, model quality, timing and actual Blender import/render remain untested.

For Vibe integration and input/output bindings see [the integration handoff](../../../../docs/MULTIVIEW_VIBE_DIRECTOR_HANDOFF_2026-11-01.md). Keep the separate service lifecycle; existing Comfy/local-AI-stack launchers are unchanged.
