# Image to 3D: TRELLIS.2 and Pixal3D integration plan

Date: 2026-11-01. Status: implemented locally; CPU, mocked browser and live idle/schema checks pass. New multi-view GPU generation remains owner-clicked and untested. No model downloads or training performed. Extends `trellis_tts.md` and `trellis_tts_implementation.md`; preserves the current storage cleanup and existing single-image TRELLIS workflow.

## 1. Intended experience

Two backend pages under Generation Assets → Image to 3D:

- **TRELLIS.2**: existing page and route retained; add Single image / Multi-view toggle.
- **Pixal3D**: new sibling page, multi-view only. No single-image toggle or single-image graph preparation (owner correction).

Owner correction: only TRELLIS has the Single image / Multi-view toggle. Within either page, keep **Single item / Batch** separate from **Single image / Multi-view**. One multi-view set describes one object and produces one GLB. Batch means several objects processed sequentially. Switching toggles must not submit work or silently reinterpret existing selections.

Reuse the existing padded, resizable two-panel `EditorWorkspace`: Director conversation on one side, inputs/controls/results on the other, with independent Hide buttons and width slider. Preserve shared themes, model picker and /status. Chat offers suggestions for review; it does not start rendering. Preserve the current truthful attachment capability: filenames/settings are not visual analysis unless that capability is separately implemented.

Controls panel, in order:

1. Backend title, connection state, input-mode toggle and Single item / Batch tabs.
2. Image input or labelled view slots, each with thumbnail, replace/remove and drag/drop/file selection. View folders use the browser directory picker with recursive imports; custom output destinations use the existing native chooser/path grants.
3. Output destination: backend default or user-selected folder; workspace association is optional. Display the actual resolved destination.
4. Preset selector; collapsible Parameters; separate collapsible Workflow details with real backend, input requirements and qualification state.
5. Generate, progress/stage, elapsed time and actionable errors. Stop behavior must reflect the backend's actual capabilities.
6. Existing interactive GLB viewer, orbit/reset/lighting, Download GLB, Open output folder and **Open with Blender only for Single item**. Batch has per-object results and failures, but no automatic Blender opening.
7. Collapsible saved runs. Preserve existing TRELLIS history; isolate drafts and saved histories by backend; changing input/batch mode clears selections and approval.

No TRELLIS training tab. No text conditioning prompt where the selected graph/API has none. Resolution labels describe pipeline/texture settings rather than promising a mesh quality or memory footprint.

## 2. Inspected sources and current readiness

Donor root: `/home/riki/web_dev/setup_comfy_and-stuff`.

| Source | Use |
|---|---|
| `docs/MULTIVIEW_VIBE_DIRECTOR_HANDOFF_2026-11-01.md` | Integration contract and qualified/unqualified boundaries |
| `workflows/ricky/3d_stuff/pixal3d_multiview/README.md` | Native Comfy front/back and four-view API/UI graphs |
| Same folder `installation-manifest.json` | Source revisions, graph/model hashes and reused dependencies |
| `workflows/ricky/3d_stuff/trellis2_multiview/README.md` | Separate service, client, presets and preparation rules |
| Same folder `config/`, `generate_multiview.py`, `prepare_views.py` | Exact fields, client behavior and view preparation |
| `env_setup/trellis2_multiview/scripts/service.sh` and Compose file | Start/status/idle-only stop; isolated runtime |
| `third_party/trellis2-multiview/trellis2_api.py` plus deployment patch | Actual HTTP contract and recovery limitations |

Live read-only checks on 2026-11-01: TRELLIS `http://127.0.0.1:52070/health` reports healthy, models unloaded, no CUDA initialization, GPU idle. ComfyUI `3008/queue` is empty. AI Toolkit `8675/api/queue` returns no queues. These checks do not qualify rendering or training.

Copy only the required small graphs, presets, provenance and adapters into Vibe. Retain donor revision/hash records; verify copied artifacts against manifests. Reuse external model storage and prepared containers. Do not copy virtual environments, download duplicate models or mix the TRELLIS service dependencies into Vibe/Comfy Python.

**Owner correction:** Pixal is multi-view only; single-image API export is removed from scope. Existing Toolkit queue/training behavior is left unchanged.

## 3. Inputs and workflow-specific controls

### Common view selection

Owner-approved input choice: **Separate view images** or **Single multi-view sheet** on both multi-view backends. A sheet is not passed whole to the model. The user chooses rows/columns, adjusts crop rectangles, assigns direction labels and explicitly confirms the individual crop previews before submission. No silent direction inference. Preserve the original sheet; invalidate approval whenever crops/labels change. Apply the same review per object in batch mode.

Initial multi-view profiles: **Front + Back** and **Front + Left + Back + Right**. Require every slot in the selected profile, with explicit direction labels and no duplicate file assigned twice. Front is canonical. Do not infer camera direction from an unordered upload. A mixed folder of unrelated images is not a multi-view object.

Show a prepared-input preview before Generate. Validate supported image types, decoding, EXIF orientation, dimensions and size bounds; retain original aspect/relative subject scale and alpha until preparation. Same subject, pose, lighting and scale; consistent canvas; genuine side images rather than three-quarter views. Pad rather than stretch. Composite transparency onto the required black background after preparation; do not silently independently crop each view. Opaque background removal needs an explicit preparation choice and review, not an unsupported automatic promise. Existing single-image RGB upload cannot simply be reused unchanged for alpha-sensitive multi-view preparation.

### Pixal3D through ComfyUI

- Front/back API: `Pixal3D_MV_front_back_bounded.api.json`: LoadImage nodes **400 front, 401 back**.
- Four-view API: `Pixal3D_MV_four_views_bounded.api.json`: **400 front, 401 left, 402 back, 403 right**.
- Model node319 uses `pixal3d_multiview_int8_convrot.safetensors`; preserve its compatible VAEs/vision encoder. Camera node324 starts at **20° FOV**, horizontal views at the native orbit assumptions.
- Bounded profile retains stage94=1024, texture288=1024, normal bake224=1024, remesh241=256/UDF with bounded precluster, decimate186=100,000 faces. Keep sampler/scheduler/CFG defaults intact initially.
- Expose seed and supported FOV/texture/mesh controls in Parameters with validated bounds. Preserve all sampler seed mappings (nodes3/12/18/23) and record the compiled graph.
- Upload to Comfy using returned filename/subfolder; bind slots explicitly. Use one `/prompt` submission and the existing durable Comfy history/prompt-ID recovery. Output372 gets a unique job prefix. Read actual GLB history descriptors; never guess filename counters.

### TRELLIS.2 multi-view through separate API

Use `POST /generate-multiview` multipart with named `front`, `back`, `left`, `right` files. Keep existing TRELLIS **single-image Comfy graph** for Single image mode: the separate deployment disables its other GPU routes, so switching to single mode must not call `/generate`.

Use checked-in service presets, not guessed defaults:

- Start with saved `front_back_512.json`: pipeline512, seed42, structure guidance7.5/30 steps, SLAT guidance3.0/12 steps, front axis z, blend temperature2, Euler, texture1024, decimation100,000, remesh on, quad off.
- Saved two/four-view 1024-cascade and direct1024 presets are advanced profiles pending GPU acceptance. Cascade uses front-only sparse structure and multiple views later; label this limitation. Direct1024 uses multiple views throughout and needs separate memory/quality qualification.
- A four-view512 profile is not supplied as a saved preset; derive and schema-check it explicitly if offered, then qualify separately.
- Expose supported fields in collapsible Parameters, using preset values and server-side range/enum checks. Quad remains unavailable; no synthetic progress percentages or invented prompt controls.
- Response provides request ID, GLB URL and texture URLs. Fetch only allowed same-service output paths through the backend. Validate a real, nonempty mesh before publishing or displaying success.

## 4. Batch grouping and destinations

Single-image batch retains existing sequential image-folder behavior. Multi-view batch uses one subject subfolder per object, for example:

```text
chosen-input/
  statue-a/front.png
  statue-a/back.png
  statue-b/front.png
  statue-b/left.png
  statue-b/back.png
  statue-b/right.png
```

Folder scan produces editable object cards with named direction slots and missing-view feedback. Recognize case-insensitive exact view basenames with supported extensions; duplicate basenames are rejected. Replace/remove a slot manually to resolve assignments. Batch objects can be removed or added; only a complete, explicitly reviewed set can start. Limit: 500 objects / 2000 images. Freeze mappings and hashes at submission. One object at a time; no parallel model loads.

Actual storage reuses the existing durable adapter: imported images, batch manifests and run/recovery metadata for both backends remain under `local_data/trellis.2/{input,batches,runs}`. Defaults for final assets are `local_data/trellis.2/output/<job-id>/<index>.glb` and `local_data/pixal3d/output/<job-id>/<index>.glb`. Custom output folders replace that final destination. Existing TRELLIS history remains compatible; no unrelated media is migrated.

Use existing `output_destinations.py`, folder grants and verified atomic publication for custom destinations. Final assets go to the chosen output location; avoid an additional hidden final copy. Keep references in catalogues, rather than duplicating files into workspaces. External selected source images remain untouched. Owned Pixal Comfy staging inputs and hash-identical GLB intermediates are removed after verified publication. TRELLIS service originals remain in the donor `outputs/trellis2-multiview/<request-id>/` for recovery; this integration does not prune that external folder. Prepared local views and recovery receipts are retained. Never broad output-folder pruning. Preserve failed/uncertain outputs for recovery; record any retained intermediate location. User cleanup of Trial/projects is unrelated and must remain intact.

## 5. Startup and GPU ownership

`start_vibe_director.sh` now starts/reuses TRELLIS multi-view through a locked, bounded health bootstrap. Existing Toolkit startup/launch behavior is unchanged by owner instruction.

At normal Vibe startup, a single idempotent service bootstrap should:

1. Start/reuse Vibe's existing services; check configured Comfy availability through its established lifecycle, without creating a second Comfy instance.
2. Start/reuse the prepared TRELLIS multi-view container with `--no-build`; poll health with bounded waits. Healthy here means HTTP ready, with models loaded only on an explicit GPU job.
3. Preserve the existing AI Toolkit behavior; no new Toolkit queue/admission work in this task.
4. Multi-view controls show service readiness and a Check / start service button. Startup failure logs to `local_data/logs/trellis-service.log` without blocking unrelated tools. The existing training website launch remains separate.


Use process/file locking so refreshes, multiple tabs and repeated boot calls reuse services. Preserve ownership: Vibe shutdown does not kill externally started or busy services. No Docker rebuilds, environment migration, model downloads, preset rewrites or inference warm-up in startup.

Extend existing `media_jobs.gpu_workload_lock/gpu_workload_guard` and shared dispatcher to cover both 3D adapters. API readiness is not permission to infer. Hold ownership until remote inference is confirmed stopped/completed, output recovery resolved and model memory released; check-then-submit queue polling alone is not an atomic lease.

Before moving between Comfy and the separate TRELLIS process, verify the other GPU workload is idle and release its resident model allocation through the existing supported runtime lifecycle. The dedicated TRELLIS service has no unload endpoint: use its **idle-only stop**, confirm exit/release, and auto-restart lazily for its next job. A stopped service after intentional memory release should say so; users never need to host it again. Do not claim that `torch.cuda.empty_cache()` unloads live model weights. If keeping it continuously HTTP-ready is later required, add and qualify an explicit idle-only unload operation rather than pretending one exists.

Owner correction: do not modify Toolkit queues/scheduling or add a training admission bridge in this task. AI Toolkit's own website can schedule work outside Vibe. Retain current idle preflight and document this existing boundary; do not claim complete mutual exclusion. A one-time queue-idle check or merely opening Toolkit safely does not prevent a later training/render race. Until that bridge is verified, block conflicting Vibe work and make the limitation explicit. Preserve temperature90°C/clock2100MHz safeguards and independent monitoring; do not change clocks or ignore genuine OOM faults.

## 6. Durable execution and recovery

Reuse `trellis_studio.py`, `video_repertoire.py` and `video_repertoire_worker.py`; keep one durable dispatcher and existing asset identity. Add a small backend-specific adapter for Pixal graph compilation and TRELLIS multipart requests rather than a second queue/controller. Existing route behavior and old saved runs must remain readable.

Important TRELLIS limitation: its POST is long-running and synchronous; request ID is currently server-generated, returned only after completion. There is no supported cancellation/status/idempotency API. A browser disconnect/HTTP timeout does not mean inference stopped. No automatic retry and no release of the GPU lease merely because the HTTP client stopped waiting. Stop initially means “stop after current object”; never advertise immediate cancellation.

Before robust automatic restart recovery is enabled, add a minimal, bounded service contract for a caller-owned request token, persisted state/result lookup and duplicate prevention, preserving the prepared generation pipeline. This also requires updating the deployment's strict route allowlist. If that extension cannot be made, use explicit `recovery_required` with server health/output reconciliation; do not guess which output belongs to a job or resend uncertain work. Persist request intent, input hashes, settings, output destination and state before dispatch; fail closed across Vibe worker restart while the remote service remains busy. Completion requires validated, published output, not just HTTP200.

## 7. Implementation sequence and acceptance

1. Inventory/hash exact donor multi-view artifacts; preserve provenance. Pixal single-image generation is out of scope. No duplicate weights.
2. Add idempotent startup/lifecycle adapters for the dedicated TRELLIS service; preserve Toolkit behavior. Check healthy-service reuse without model loading.
3. Extend shared durable 3D jobs, GPU ownership, service recovery contract, bindings and verified publication. Preserve existing single-image routes/history.
4. Reuse/refactor the smallest existing page/viewer pieces; add the Pixal sibling page, input toggle, labelled view slots and batch group review. Retain established padding, collapsible sections, hide controls and sliders.
5. CPU/schema and mocked protocol checks: input mappings, ambiguity rejection, alpha/scale preparation, preset bounds, exact graph bindings, path grants, output validation, save-only recovery, uncertain POST/no replay, busy contention and old-run compatibility.
6. Browser checks: both backends/modes, resize/collapse/theme, upload/remove, folder grouping, clear disabled reasons, output selection, progress/history and single-only Blender behavior. Use Playwright MCP when available; report its actual error if unavailable and label any fallback honestly.
7. Prepare aligned front/back inputs, exact graph/settings, idle queues and monitor for **owner-clicked GPU acceptance**. Measure peak memory, time, actual GLB geometry/textures and orientation; inspect in viewer/Blender. Qualify two-view then four-view and advanced profiles separately. Do not enable untested high-resolution defaults based only on successful health/schema checks. No background render/training acceptance.
8. Update plan/hand-off with measured results, supported controls and remaining limits. Rollback restores existing single-image route/graph and removes new routing/bootstrap hooks without deleting source images, meshes, projects, environments or models.

## 8. Affected files and boundaries

Expected seams, confirmed against current source and the code graph: `frontend/src/TrellisPage.tsx`, shared `EditorWorkspace`/StudioChat/viewer controls, `App.tsx` routing and `StudioShell.tsx` navigation; `backend/story_builder/services/trellis_studio.py`, `video_repertoire.py`, `video_repertoire_worker.py`, `media_jobs.py`, `image_training.py`, `isolated_server.py`; launcher `start_vibe_director.sh`; small new API graph/preset/provenance files and backend-specific service adapter. Confirm exact changes at implementation, then refresh Graphify after meaningful code edits.

Existing character/world Z-Image LoRA selection, training publication/deletion, audio, H3/LTX and editor behavior are outside this change except for shared startup/admission regression checks. No new training pages. No changes to the accepted Trial storyboard or cleanup. Pixal single-image is excluded. Explicit manual remote recovery is implemented; automatic lost-reply correlation and external Toolkit admission remain unsupported rather than assumed complete.

## 9. Implementation evidence — 2026-11-01

Implemented `MultiViewInputs.tsx`, extended `TrellisPage.tsx`, Pixal navigation/routing and scoped padded CSS; adapted existing durable jobs with `multiview_3d.py`, `trellis_studio.py`, `studio_tools_api.py` and shared worker handling. Ten small donor artifacts are copied with matching SHA256 in `backend/story_builder/workflows/api/three_d/multiview/provenance.json`; no weights/environments copied.

- 21 focused backend tests pass: bindings, seed propagation, confirmation/dimensions/distinctness, alpha/common padding, preset limits, uncertain POST never replayed, service reuse, invalid recovery rejection, sequential validate/publish before next object, existing studio contracts.
- Three isolated Playwright CLI tests pass: separate view upload and review gating; sheet preview/apply/review; four-view reset; collapse/desktop non-overlap/mobile overflow; existing single-image batch with simulated recursive directory selection, output grant and recovery. OS folder dialog itself is not automated. Playwright MCP could not initialize because its Chrome profile was already in use; CLI fallback used.
- Frontend production build and shell syntax pass; Graphify refreshed (workflow/config JSON files produce no AST nodes, expected).
- Live Comfy node/model-choice schema checks pass for both Pixal graphs. TRELLIS health/repeated readiness reports models unloaded/no CUDA/GPU idle. Live pages load without JavaScript errors. API reloaded idle with its original environment; no GPU/provider generation submitted.
- Timeout recovery persists intent before dispatch and never automatically resends an uncertain POST. Stop means after current object. If a reply is lost, owner must match the completed request UUID from service logs and recover the existing result; an aborted request with no recoverable GLB requires operator investigation. No unsupported automatic status/cancellation/idempotency contract is claimed.

Pending: owner-clicked actual aligned 2-view generation, then 4-view/profile qualification, memory/timing/mesh inspection. New workflow readiness is not evidence of successful GPU rendering.
