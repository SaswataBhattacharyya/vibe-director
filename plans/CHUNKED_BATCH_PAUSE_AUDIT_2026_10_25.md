# Chunked batch pause audit — 2026-10-25

## Scope and conclusion

Owner requested a strict audit of the renewed pause and comparison against the isolated `web_dev/setup_comfy_and-stuff` runner. This was a read-only runtime/source investigation, apart from this report and the handoff. No generation, resume, interrupt, service restart, dependency change or application code change was performed.

**The batch is paused. Both H3 originals succeeded. The first LTX chunk encountered contemporaneous NVIDIA allocation errors, but ComfyUI subsequently completed that chunk successfully and Vibe saved it. The batch remained paused because its GPU-fault pause is latched separately from take reconciliation.** No H3/LTX execution overlap is present in this incident.

The isolated and application supervisors are materially different. The isolated supervisor does not inspect kernel allocation errors. Therefore an isolated run finishing without a watchdog stop does not establish that it had no NVIDIA allocation warnings.

## Authoritative runtime identity

- Batch: `e92603ba-5450-4b95-9c79-55fc587613db`, state `paused`.
- Workspace: `media-49e2cabe-4ff4-416c-9b5d-edc7c758b0df`.
- Prompt 7 job: `b64cd6ef-f379-4e8d-a497-035346a66243`; take `a6bafdf8-fc55-55e2-9ad8-bdb1bb9d0c78`.
- Prompt 8 job: `819a97b0-0cb5-4586-a110-bc26335267ea`; take `2a24f326-0ef1-51a2-a392-b7aeb21f1bb0`.
- Ledger: `local_data/storage/production/ledger.sqlite3`; tables `t2v_batches`, `production_takes`, `production_events`.
- ComfyUI `http://127.0.0.1:3008`: queue empty at inspection, zero running and zero pending. No further LTX chunk had started.
- Existing worker PID reported by runtime status: `2007094`. Reconciliation events saying `recovered_after_restart` are generic recovery metadata, not evidence that the process restarted.

## Execution timeline

Times below are IST on October 25; Comfy history timestamps are UTC milliseconds converted to IST.

| Event | Time | Result |
|---|---|---|
| Prompt 7 H3 started | 16:23:20.421 | Original prompt ID `70870ece-7948-5f2e-9f13-b794e540a2e2` |
| Prompt 7 H3 finished | 16:25:58.246 | Success, **157.825 seconds** |
| Prompt 8 H3 started | 16:25:59.926 | Original prompt ID `faf12a5e-45aa-55a6-a4d9-68b2bdb41974` |
| Prompt 8 H3 finished | 16:28:24.091 | Success, **144.165 seconds** |
| First LTX chunk started, prompt 7 | 16:28:28.717 | Prompt ID `52d6e531-21c9-5297-8cc2-47b44320dd64` |
| NVIDIA allocation errors | 16:29:04 | Four `NV_ERR_NO_MEMORY` entries; further entries at 16:29:08 and 16:29:17 |
| Worker entered recovery | 16:29:07.974 | `gpu_monitor_failed`; batch subsequently latched paused |
| First LTX chunk finished | 16:30:07.794 | Comfy success, **99.077 seconds** |
| Chunk checkpoint saved | 16:30:08.935 | Index 0 preserved; next index is 1 |

The same Comfy prompt was reconciled and collected. It was not submitted twice. The monitoring exception path recorded recovery and returned; it did not send an interrupt for this exception. Comfy continued rendering. This explains the apparent contradiction between “paused” and a subsequently completed chunk.

Prompt 7 has **1 of 8 LTX chunks** saved, with seven remaining. Prompt 8 has its H3 original and no LTX chunks. Neither is a newly completed final video from this batch.

Checkpoint verified with ffprobe: `local_data/ltx_chunks/media-49e2cabe-4ff4-416c-9b5d-edc7c758b0df/b64cd6ef-f379-4e8d-a497-035346a66243/0000_138fdcb6756dda474c952ae14afb70df07cbe3beeeef9bf31bc517b3492baeb6.mp4`: 768×1344, 65 frames, 24 fps, 2.708333 seconds. This is an internal partial result, not the finished 15-second video.

## Memory evidence and its limits

NVIDIA reported `_memdescAllocInternal ... mem_desc.c:1359`, `NV_ERR_NO_MEMORY`. These entries are from the current workload window, not stale messages from an earlier batch. Comfy history nevertheless reports success; no Python execution failure is present in that history. These are real allocation failures, but they were not fatal to this particular chunk.

Recorded available host/shared memory:

| Observation | Available memory |
|---|---:|
| Before LTX admission, 16:28:27 | 67.1 GiB |
| Initial LTX monitor sample, same second | 70.3 GiB |
| 16:28:37 | 62.8 GiB |
| 16:28:47 | 36.8 GiB |
| 16:28:57 | 19.5 GiB |
| Fault sample, 16:29:07 | **7.3 GiB** |

Total measured physical memory is 121.7 GiB. At the fault sample approximately 114.4 GiB was **not available system-wide**. This is not a measurement of exclusive LTX VRAM use: GB10 shares memory across the OS, applications, model storage, driver and tensor allocations. Swap free was 7.6 of 16 GiB. Monitoring's full memory samples stopped on this exception, so the true subsequent minimum/peak is unknown.

At the fault, Comfy's reported Torch reservation was about 3.19 GiB while system memory was heavily occupied. This demonstrates why Torch allocator counters alone cannot prove all dynamic/offloaded allocations have disappeared. Model logs showed approximately 25,440 MB of staged LTX text-encoder weights and 40,050 MB of staged LTX model weights, in addition to VAE and temporary work. Staged sizes are not additive peak GPU residency measurements.

The recorded operating points in this batch reached 75°C and 2099 MHz. The pause was not attributed to a temperature or clock limit. Source currently contains a 90°C cutoff while AGENTS guidance says 83°C; this pre-existing policy discrepancy needs explicit resolution separately. No limits were changed during this audit.

## Comparison with the isolated runner

Inspected donor files under `/home/riki/web_dev/setup_comfy_and-stuff/`:

- `workflows/ricky/h3_ltx/run_chunked_flow.py`
- `workflows/ricky/h3_ltx/t2v_20s/LTX23_1344x768_3step_Sol_chunk_template.api.json`
- `workflows/ricky/h3_ltx/t2v_20s/test-result.json`
- `env_setup/h3_ltx_20261023/scripts/run_authorized_test.py`
- `env_setup/h3_ltx_20261023/scripts/gpu_test_watchdog.py`
- `env_setup/h3_20s_20261025/RESULTS.md`

### Same core refinement, different supervision and inputs

| Item | Isolated 20-second test | Current Vibe batch |
|---|---|---|
| LTX graph | 24 nodes | Same 24 node IDs; same model/sampler/Sol settings |
| Window / overlap | 65 / 16 frames | 65 / 16 frames, cut-aware |
| First chunk backend time | 97.877 s | 99.077 s |
| Final dimensions | 1344×768 landscape | 768×1344 portrait |
| H3 input size | 896×512 | 320×576 |
| Positive LTX text | 204 characters in donor template | 4,138 characters, including approved preservation suffix |
| Negative LTX text | 58 characters | Empty, existing product behavior |
| Scaling node | ResizeImageMaskNode, ×1.5 | ImageScale to requested absolute final dimensions |
| Unload | Idle check, POST `/free` | Idle check, POST `/free`, repeated low-Torch-allocator observations |
| Fault monitoring | Temperature ≥80°C; RAM <1 GiB for 3 samples; telemetry errors logged | Separate operating-point watchdog plus kernel-error inspection that raises on matched errors |
| Kernel journal inspection | None in this supervisor | Yes |

Output/input filenames also differ by design. All graph differences were inspected from the exact submitted Comfy history against the donor template, not just the current template on disk. H3 still uses four steps; LTX still uses three steps per window. No full 15-second LTX tensor was submitted for this chunk.

The donor's first chunk had a sampled minimum of **7.34 GiB** available RAM; its full test minimum was **6.86 GiB**. Thus the successful isolated qualification was already close to memory pressure. Its watchdog would not stop at 7.3 GiB and does not read the kernel journal. Its success report alone cannot rule out kernel allocation warnings. Conversely, the current allocation failure's exact requester/byte size cannot be determined from these logs; prompt length, orientation, retained caches and other processes must not be asserted as the sole cause without controlled measurements.

The lower H3 source speeds H3 but does not lower LTX's requested final spatial size: product scales to 768×1344 before LTX processing. LTX still pays for a full final-size 65-frame window.

## Source findings

### 1. Recovery state and batch state diverge — confirmed

`gpu_runtime.inspect_gpu_runtime` raises for any matched kernel entries. `production_job_worker._poll` translates this to `recovery_required` with `gpu_monitor_failed` and returns. `t2v_batches.advance_active` auto-waits only for `comfy_status_unavailable`; this GPU reason becomes `paused`. Its active query excludes paused batches. Later reconciliation saves the successful chunk, but `production_ledger._group_allows_refinement` correctly refuses further work in a paused group.

Consequently, a valid checkpoint does not clear the batch's earlier fault reason. This is a genuine recovery/control-state gap, not evidence that chunk generation failed or that the owner pressed Pause. A deliberate GPU safety hold must remain distinct from a transport wait; it should show both fault and recovered-output facts and define a supervised recovery action.

### 2. Successful chunk save preserves the old current error — confirmed

`production_ledger.save_ltx_chunk` updates pipeline/index/status but does not clear or resolve `error_json`. The job moves to `refinement_pending` while retaining `gpu_monitor_failed`. Historical errors belong in events; current unresolved safety holds need an explicit representation. Simply hiding the message would conceal the real fault.

### 3. Retention checks pending stage without checking paused batch eligibility — confirmed

`production_job_worker._release_after_stage` keeps models whenever returned status is `refinement_pending`. On this recovered first chunk that is true even though the batch is paused and no successor is eligible. Thus the code skips final idle release on this path. The exact current model residency cannot be established from small Torch counters, but the release omission is directly visible in source. Pausing should preserve checkpoint files while releasing idle model/cache resources after remote completion, subject to queue ownership.

### 4. “Memory release observed” is narrower than the wording suggests — confirmed limitation

`media_jobs.release_comfyui_models_if_idle` requires two idle low-Torch-allocator samples, never authorizes a stage merely because a timeout elapsed, and polls every ten seconds after the initial observation window. The requested wait/poll mechanism exists. However this proves allocator observations, not full dynamic/CPU model eviction or next-stage fit. H3 finished before LTX; the records do not support concurrent execution. Nor do these observations prove every H3-related CPU/cache allocation was gone.

### 5. Fault provenance and peak diagnostics are incomplete — confirmed limitation

Kernel matches are host-wide within the workload interval; matching a line does not identify its allocating process. The matching pattern also includes general thermal/watchdog text. A single broad GPUAdmissionError mixes faults with observation failures. Once polling exits, detailed memory sampling ceases even though the remote prompt may still run. Handoff samples lack timestamps/job IDs, making exact retrospective association weaker than it should be.

## No two-prompt parsing limit

The current exported Markdown is 8,163 bytes and contains only headers 7 and 8. The saved batch likewise has exactly two entries. Parser limits are 1 MB aggregate and 1–100 prompts, with per-prompt validation. This pause is an explicit GPU-monitor event during LTX, not exhaustion/truncation of the prompt text field. It occurred after two H3 originals because that is the complete saved H3 phase.

## Recommended correction sequence

1. Preserve both originals, the completed chunk, IDs and checkpoint index. Never regenerate or double-submit them during recovery.
2. Separate user pause, actual remote execution failure, telemetry outage and kernel-allocation safety hold. Keep observing the same remote prompt to terminal state without admitting successors during a hold.
3. On recovered success, validate and record the chunk; explicitly resolve current job error versus retained safety hold. Show “chunk recovered; batch held after NVIDIA allocation error” rather than implying missing output. Allow continuation only through defined health/recovery checks; do not blindly ignore allocation errors.
4. Release models once remote work is idle and the owning group is paused/stopped/failed, instead of retaining solely on `refinement_pending`. Preserve one shared queue owner.
5. Persist timestamped, job/stage/chunk-associated unload observations and memory sampling through terminal reconciliation, including host/swap and available allocator diagnostics. This is necessary to measure actual peaks rather than infer them.
6. Reproduce on owner-authorized identical input/orientation/prompt/window in donor and app, observing kernel logs in both. If pressure remains, qualify smaller LTX windows and/or lower-memory text-encoding/decoding settings. Do not promise that chunking alone guarantees fit or change prompt/final resolution without agreement.

These are recommendations, not changes applied in this audit. The batch remains paused and its checkpoint is preserved.

## Follow-up fix — owner-authorized allocation warning policy

After this audit, the owner requested that the recurring allocation log no longer pause rendering. The GPU inspector now treats the exact NVRM `NV_ERR_NO_MEMORY` + `_memdescAllocInternal(pMemDesc)` + `mem_desc.c:1359` message as a recorded diagnostic warning, excluding Xid lines. Other faults remain blocking. Comfy execution/history and final output validation still determine render success. This is a monitoring-policy correction, not a memory-capacity fix or a guarantee of completion.

Syntax inspection and code graph refresh completed; idle worker reloaded as PID2323970. No live generation was submitted. Latest batch was already stopped by the owner and remains stopped. Earlier sections describe the original audited snapshot.

### 2026-10-26 — Context buffer allocation diagnostic

The owner reported another allocation diagnostic from `kgrctxAllocCtxBuffers(...) @ kernel_graphics_object.c:215`. The warning exception now covers this specific source/function combination only when the line also contains `NVRM:` and `[NV_ERR_NO_MEMORY]` and contains no Xid (case-insensitive). It remains in `nvidia_kernel_warnings` and durable `runtime_warning` telemetry. Other allocation errors, Xid faults, execution/history failures and invalid outputs remain blocking; normal GPU admission and independent thermal/clock supervision are unchanged. No general automatic unpause was added: owner pauses and genuine safety holds must persist.

Focused CPU-only verification: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend python -m unittest story_builder.tests.test_gpu_allocation_warnings -v` passed both methods, including six negative cases. The initial test fixture lacked queue fields and was corrected before the passing run; no GPU test generation was submitted.

Runtime activation: latest owner-started batch `e4e78618-e5c8-4293-881b-a3a7c56aed0a` was already running with a healthy detached watchdog. Reloaded the existing worker with preserved configuration (2728143 →2934517), leaving ComfyUI and its owned prompt untouched. That prompt, `23eb4a41-87a0-5257-8143-a38001ba6446`, completed successfully and was collected through existing recovery. API reload2728140 →2934883 activates the policy for readiness checks too. Batch now reports completed; both jobs for IDs7/8 are ready for review with no error. This establishes completion of this batch, not immunity to future genuine allocation/execution failures.
