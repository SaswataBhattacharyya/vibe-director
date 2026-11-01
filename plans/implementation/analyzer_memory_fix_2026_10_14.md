# Owner analysis failure — 2026-10-14

## Scope and confirmed cause

Bounded owner-requested repair only; broad completion goal remains paused. Existing writable checkout: `/home/riki/Documents/ChatGPT/Vibe Director`. No Git, bulk recopy, service restart, live retry or GPU/model inference.

Failed attempt: `analysis-557f22b1a89d`, source `pa-07740680760040e5`, workspace `media-49e2cabe-4ff4-416c-9b5d-edc7c758b0df`. Source is the 93.855-second imported YouTube video, AV1, 360×640. Saved failure and logs remain unchanged.

The NVIDIA driver recorded `NV_ERR_NO_MEMORY` at 06:36:09/11 UTC. `/tmp/vibe-director-gpu-telemetry.jsonl` records the monitor catching that driver error at 06:36:18. Docker events confirm the owned container was stopped at 06:36:18 and killed after its stop timeout, exiting 137 at 06:36:30. This is a watchdog stop following a real driver memory error; exit 137 alone was insufficient evidence. The first PE-AV CLI failed before the separate InternVideo3 stage began. AV1 decoding and SpeechBrain warnings in the tail were not the watchdog's stop reason.

Vibe already uses the **newer** `video_audio_analyzer` behind Story Builder's current Video Repertoire UI: PE-AV/audio/scenes → separate InternVideo3 summary → text embedding/index → director review. Before this repair, 31/32 top-level Python engine files were identical to that donor; the sole existing difference was a harmless parsed-URL adaptation in `peav_worker.py`. The additional Vibe frame-evidence pass is CPU OpenCV/numpy, not the causal GPU model pass.

The installed PE-AV video checkpoint defaults to `do_sample_frames: false`, `num_frames: null`. The copied adapter supplied no override, and the installed vision encoder flattens every decoded video frame into one GPU batch. This unbounded input is the identified memory-pressure defect. A completed donor attempt (`analysis-382950a35008`, October 4) reached 96,389 MiB peak, confirming that success in Story Builder does not imply a small memory footprint. The exact failed allocation is not instrumented.

## Minimal fixes

- Staged `peav_adapter.py`: explicitly use the existing processor's `do_sample_frames=True`, `num_frames=16` for video-containing HF inputs. Uniform sampling spans the scene's first to last frame. This follows the [PE Audio Video quickstart](https://huggingface.co/docs/transformers/model_doc/pe_audio_video). Scene/cut detection FPS, saved frames, audio options, original media and subsequent InternVideo3 stage remain intact. Audio/text-only and legacy processor dispatch are preserved.
- `backend/story_builder/services/media_jobs.py`: after verified owned-workload cancellation, retain the monitor failure as the visible exception if the process also reports an exit error; preserve that exit error through exception chaining. Cancellation still joins before releasing the shared lease; unknown termination still creates an admission hold. Keyboard interrupts/system exits retain their original handling.
- Added focused processor-call and error-propagation regression coverage. No fixed VRAM floor or parallel processing was added.

## Evidence and limits

- Eight focused CPU/mocked checks passed: video-only bound, joint AV bound/full audio, audio/text dispatch, legacy dispatch, monitor reason surviving exit137, ordinary body errors, cancellation, unknown-termination admission hold.
- Actual installed `video-audio-analyzer-peav:dev` processor tested against the owner's original video in a CPU-only, network-disabled container with 2 CPUs/4 GiB limit. No GPU device, model weights or neural inference. Real processor output: video `[1,16,3,336,336]`, audio `[1,1,4506240]`, finite pixels. The adapter's model call was a stub. Installed uniform sampler checked first/last coverage and valid indices for 1, 8 and 2,816 source frames. This proves preprocessing/dispatch, **not real inference or semantic quality**.
- Serving identities confirmed: API 3020 PID147809 cwd `.../Vibe Director/backend`; Vite8082 PID450396 cwd `.../Vibe Director/frontend`. API uses this checkout's data root and default staged analyzer; analysis spawns a new worker importing current source and mounts the staged engine read-only. These fixes take effect on the next owner-started worker without restarting the API.
- Read-only live preflight at 09:13:52 UTC: analyzer available; reported free96.14GiB informational; host available104.6/121.7GiB; swap free15.7GiB; no fixed minimum. Status: Comfy0/0, Vibe0 active/0 pending, two historical attention records, simultaneous runs OFF, no unknown-termination hold. Values expire and do not guarantee model fit.
- Full local Graphify refresh: 2,867 nodes / 9,041 edges. The initial incremental extraction wrote only a delta; a forced code-only scan restored full coverage. Staged engine files are not indexed by the main graph and were inspected directly.

## Provenance

No original donor/shared installation changed. Retain all previous resource checksum records. Selective adapter change only:

| File | SHA-256 |
|---|---|
| Donor / original copied `peav_adapter.py` | `765718a4178da4ddf9378341a18bd6aee54b3591cdb6b5623fb8a9ab5b310932` |
| Vibe adapted `peav_adapter.py` | `d248879b166bbcbcff4798841441320542f805f9acbbd54c5fc8e4fc56a91c02` |

Current top-level comparison: 30/32 identical; differences are this bounded-input adapter fix and the retained URL adaptation. The new sampling test's modality stubs were minimally adapted from donor `video_audio_analyzer/tests/test_peav_adapter.py`.

## Remaining acceptance

The C4/C10 concrete code defects are closed by the scoped evidence above. The earlier consolidated review predates this patch; no new consolidated review was requested. Real GPU completion, derived result playback, semantic indexing/relevance and optional audio-stage quality remain unverified. Do not claim that the previous failed attempt now succeeded. No analysis was retried. Before an owner-started retry, refresh idle/readiness/Debug/serial state; use the same selected video and settings so the real result is comparable.
