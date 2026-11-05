# Video tool guide

Source-backed usage map, 2026-11-05. IDs below are glossary IDs for future routing, not currently registered model functions. Consult [API helpers](API_HELPERS.md) and [HTTP routes](HTTP_ROUTES.md) for exact source locations. Live readiness has not been exercised by this documentation task.

## video.t2v — Text to video

**Choose when:** Generate directly from the user final prompt without reference media.

**UI:** #/video → Text to video

**Inputs:** Workflow-specific request including prompt, duration/frames, dimensions, seed, output and idempotency key; optional story linkage.

**Outputs:** Durable job, progress, final verified video and take status.

**How to use:** video-api.ts getCapability → validateRequest → createJob → getJob/listJobs. Use current T2V contract, not a fabricated request. Manual generation does not require accepting a screenplay recommendation. LTX refinement is part of the configured pipeline, not a separate arbitrary edit.

**Source:** [video-api.ts](../frontend/src/lib/video-api.ts), [isolated_video_contract.py](../backend/story_builder/services/isolated_video_contract.py), [isolated_video_jobs.py](../backend/story_builder/services/isolated_video_jobs.py), [t2v_pipeline.py](../backend/story_builder/services/t2v_pipeline.py)

## video.r2v — Reference to video

**Choose when:** Generate using selected image/video/audio references and user prompt.

**UI:** #/video → Reference to video

**Inputs:** Current reference asset identities/hashes, role/intent/order and workflow-specific prompt/settings.

**Outputs:** Durable generation job and final video.

**How to use:** Use video-api and isolated_r2v_contract.py/isolated_r2v_assets.py. Read workflow guidance for Picture/Video/Audio tags. Collation helps preparation; do not assume it is mandatory for a manually supplied valid final prompt. Re-read replaced media identities before submission.

**Source:** [video-api.ts](../frontend/src/lib/video-api.ts), [isolated_r2v_contract.py](../backend/story_builder/services/isolated_r2v_contract.py), [isolated_r2v_assets.py](../backend/story_builder/services/isolated_r2v_assets.py)

## video.fflf — First + last frame video

**Choose when:** User explicitly chooses video generation between two prepared endpoint images.

**UI:** #/video → First + last frame

**Inputs:** Supported first/last asset roles and identities plus FFLF prompt/settings.

**Outputs:** Job and final video matching the selected workflow.

**How to use:** Use FL2VA capability and contract/assets validators through video-api. User states image quality is why automatic FFLF is paused; runtime readiness and automation policy are separate checks. Do not use automatically while disabled.

**Source:** [video-api.ts](../frontend/src/lib/video-api.ts), [isolated_fl2va_contract.py](../backend/story_builder/services/isolated_fl2va_contract.py), [isolated_fl2va_assets.py](../backend/story_builder/services/isolated_fl2va_assets.py), [storyboard.py](../backend/story_builder/services/storyboard.py)

## video.review — Take review, accept, retake and continuity

**Choose when:** Review a generated clip, accept it, prepare another take or explicitly reuse its final frame.

**UI:** #/take

**Inputs:** Job ID, acceptance/retake choice, keep-original choice; explicit continuity request.

**Outputs:** Accepted take, editable retake draft or extracted continuity asset.

**How to use:** getJob/acceptJob/prepareRetake/prepareContinuityFrame. Preserve original media and frozen requests. If submission reply is uncertain, find by idempotency key before retry; release only through supported reconciliation.

**Source:** [video-api.ts](../frontend/src/lib/video-api.ts), [TakeWorkspace.tsx](../frontend/src/TakeWorkspace.tsx), [video_continuity.py](../backend/story_builder/services/video_continuity.py)

## video.runs — Assisted and fully automated production runs / batches

**Choose when:** Run multiple planned clips or resume controlled production.

**UI:** #/setup, #/prompts and #/video production controls

**Inputs:** Saved screenplay/setup and prepared clip prompts, mode-compatible reference choices, batch settings.

**Outputs:** Clip plan, run state, jobs, retries and pause/resume/stop status.

**How to use:** Use story-api assisted-video and automated-run helpers plus t2v_batches/t2v_pipeline entrypoints. Read setup and exact pipeline policy first; full auto currently uses image-free T2V. Recover existing jobs instead of resubmitting blindly.

**Source:** [story-api.ts](../frontend/src/lib/story-api.ts), [T2VBatchPanel.tsx](../frontend/src/T2VBatchPanel.tsx), [t2v_batches.py](../backend/story_builder/services/t2v_batches.py), [production_job_worker.py](../backend/story_builder/services/production_job_worker.py)

## video.assembly — Accepted clip assembly and final export

**Choose when:** Combine reviewed production takes with configured audio.

**UI:** Assembly panel in production review

**Inputs:** Exact required take selections, assembly settings and selected audio tracks.

**Outputs:** Assembly snapshot, preview and durable export.

**How to use:** Use AssemblyPreviewPanel and assembly.py/assembly_renderer.py. Existing assembly validates selection completeness; do not describe it as an arbitrary free-form timeline tool. Use Editor for a freely selected edit.

**Source:** [AssemblyPreviewPanel.tsx](../frontend/src/AssemblyPreviewPanel.tsx), [assembly.py](../backend/story_builder/services/assembly.py), [assembly_renderer.py](../backend/story_builder/services/assembly_renderer.py)
