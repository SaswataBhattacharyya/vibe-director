# Chunked LTX integration — 2026-10-25

## Applied scope

T2V, first/last-frame and dynamic R2V now share bounded LTX refinement in the existing durable production worker. H3 Turbo graph compilers, dynamic reference insertion, UI controls, small-source policy, exact H3 prompt and approved LTX preservation suffix remain unchanged. No new model, node, dependency or Docker installation is required.

For a batch: serial validated H3 originals (retain H3) → confirmed model release → serial LTX finals (retain LTX across windows and ready clips) → final release. Each clip is refined through sequential windows; the next window is admitted only after the previous ComfyUI submission completes and its output validates. Existing queue lock, independent watchdog, memory-release observation and paused-group gating remain authoritative. ComfyUI may still offload weights under pressure.

## Donor and adaptation

Source directory: `/home/riki/web_dev/setup_comfy_and-stuff/workflows/ricky/h3_ltx/`.

- `run_chunked_flow.py`, SHA256 `409d1bcee0b50618ba91bb1c12325956493fcb995b9838d9270b8201cecfa7c8`: adapted window planning, lossless staging and streamed overlap joining into `backend/story_builder/services/ltx_chunks.py`.
- `t2v_20s/LTX23_1344x768_3step_Sol_chunk_template.api.json`, SHA256 `bc5cd06ebbafdc560131f26a106d50a4709189e253dd0409881c11d9c0dae2dd`: compared with the existing product LTX API graph. Same model, sampler, three-step/Sol recipe. Retained product graph with explicit final width/height instead of fixed 1.5× resize, existing negative prompt and parameter binding. Donor test prompts, example references and fixed output paths were not imported.
- Donor evidence: `CHUNKED_REFINEMENT_README.md`, `t2v_20s/README.md` and the resolved `chunked_runs/20261025T085805Z-t2v-54a4af` graphs. Donor 20-second qualification is T2V only; FFLF/R2V have shorter donor trials.

## Refinement and recovery

- Maximum 65 source frames per window, 16-frame overlap within continuous shots, 24 fps. FFmpeg scene score >0.35 proposes hard cuts; windows do not blend across detected cuts.
- Lossless FFV1/PCM staging pads to 8n+1. Very short shots are extended with their last frame to at least17 frames, then trimmed to the original frame range on joining. This short-shot adaptation needs owner visual acceptance.
- The ledger pins the window plan before submission and checkpoints each completed window. Each window has a distinct deterministic ComfyUI prompt ID. Recovery reconciles that ID before any resubmission.
- Already submitted legacy whole-clip LTX jobs retain their original reconciliation path. Unsubmitted originals can use the chunked path on owner resume. No saved batch was resumed or rewritten during integration.
- Joining streams decoded frames and holds only overlap frames; same-shot overlaps blend linearly, hard cuts concatenate. H.264 CRF18 output is remuxed with the original compressed H3 audio. Final dimensions, 24fps and requested frame count are validated before normal asset publication.
- Originals and chunk checkpoints remain internal recovery files under `local_data/t2v_originals` and `local_data/ltx_chunks`; intermediate ComfyUI files are not registered as user-facing takes. Existing final naming/overwrite behavior is preserved.

## Changed source

`ltx_chunks.py`, `t2v_pipeline.py`, `production_ledger.py`, `production_job_worker.py`, `isolated_video_jobs.py` under `backend/story_builder/services/`.

## Evidence and limits

Python syntax and imports checked in the existing react environment. No GPU generation, batch resume, model download or new automated test was performed. Queue and active-take checks were idle before graceful worker reload. Updated video worker PID2007094 confirmed running. Each window uses a distinct loader input path to prevent reuse of cached frames. Graphify refreshed after source changes.

Chunking reduces frame-dependent allocations, not model-weight memory. It adds repeated overlap work and can take longer. Scene-cut detection is heuristic and overlap blending can ghost during large changes. It does not guarantee that every requested resolution/duration fits memory. Owner acceptance should inspect the final video, audio and overlap boundaries in the next manually started run.
