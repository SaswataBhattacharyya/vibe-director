# Consolidated coding gate review — 2026-10-13

## Verdict

Required coding is **not complete**. C8 and C10 reopen for the two concrete defects below. C4's dispatcher race was fixed in this review. Manual acceptance remains unreleased; do not ask the owner to run generation yet.

Reviewed current source and retained evidence against AGENTS, README/development workflow, GOAL, progress review, remaining estimate, 2026-10-12 review, top HANDOFF, completion gate, remaining_app, notes and automation. Used the local Graphify graph to locate workload relationships, then confirmed them in source. No Git operation, workers, live provider/GPU/media/generation/export or acceptance run. Retained mock/CPU checks remain their original evidence; no unchanged legacy suite repeated.

## Required findings

### R1 / C8 — Checked Assisted stages depend on mounted browser pages

`frontend/src/ImageAssetsPage.tsx:256` admits a checked image stage in a React effect. Its effect at 264 admits directional world views only after polling sees accepted world masters. `backend/story_builder/isolated_server.py:2515` implements the POST and saves image batches, including views only when selected masters already exist. `isolated_image_worker.py` reviews/selects admitted candidates; it does not admit dependent views or advance the post-screenplay stage. `isolated_worker.py:72` advances durable **video** runs, not character → voice → world → frame → video stages. Voice matching is also initiated on Characters page refresh (`CharacterVoicesPage.tsx:72`). Continuation between checked image stages is an unconditional user link at `ImageAssetsPage.tsx:343`.

Consequences: leave Worlds while masters run and successful master selection does not enqueue directional views; all five boxes checked still requires page navigation to initiate later stages. This contradicts `automation.md:132`: checked stages execute when dependencies are ready and advance without compulsory human acceptance. Existing batch idempotency, review, video runner and manual world/frame selection work are reusable; add progression to the existing durable owner, not another browser controller. Freeze revision/setup/style lineage, advance views after master selection, match voices, proceed through checked stages, stop at unchecked/manual or actionable failure, and recover after reload/restart without duplicate admission. Focused checks must remove the browser after admission and still observe saved progression, including late world-master completion and stale/retry cases. C6's manual asset contracts remain closed; its automatic world-view continuation is covered by this reopened C8 finding.

### R2 / C10 — Non-Comfy monitor does not abort work at safety failure

`backend/story_builder/services/media_jobs.py:156` starts a monitor in `gpu_workload_guard`. At a failing sample it records `monitor_failure`, writes telemetry and sets the stop event, but the guarded body keeps running. `MediaJobError` is raised only after that body returns. The actual analyzer uses blocking `subprocess.run` with a 24-hour timeout (`video_repertoire_worker.py:342`), and GPU analyzer/audio/Image Detailer/SAM paths use this guard. Copied Comfy prompt watchdog interruption does not stop these non-Comfy processes/containers. Thus the 83°C/2100MHz failure can leave the active costly workload running beyond the cutoff.

Connect the monitor trip to cancellation of the verified owned workload immediately, using existing process identity and analyzer container labels where applicable. Preserve unrelated services; keep the shared lease until termination is proven, and retain explicit recovery when remote ownership/termination is unknown. Do not alter clocks. A focused injected monitor failure should prove cancellation occurs while the body is still active, no result is committed, and no unrelated workload is stopped. This crosses several adapter cancellation seams and is returned to Luna rather than patched with an unsafe generic kill.

## Bounded fix completed

`video_repertoire.start_job` previously started `_ensure_media_dispatcher()` before persisting the reset queued record. Startup scans queued records and starts the dispatcher thread; that thread could complete or save its PID before `start_job` overwrote the record with queued/PID-null state. Moved dispatcher initialization after atomic persistence. Added `test_dispatcher_startup_cannot_be_overwritten_by_queue_reset` to `test_workload_policy.py`, simulating immediate startup completion without any subprocess/media action.

Focused check: startup-race regression, shared-slot wait and one-worker-process policy tests **3/3 pass**. The race test verifies completed state, PID and result survive startup. No live work ran.

## Other row dispositions and source contracts

| Rows | Reviewed contract / disposition |
|---|---|
| C1 | Retained staging/checksum and donor-hidden evidence, maintained package resources and shared Comfy workflow paths. No new required copying defect identified; donors preserved. |
| C2–C3 | Saved style/source/screenplay lineage through setup and stage-local prompt admission in isolated_server; existing fresh mocked entry/revision evidence retained. Entry controls exist, but checked stage progression is R1. |
| C4–C5 | Video Repertoire durable queue → worker adapters → shared result registration/search; media_semantic_search/library indexing and explicit preview consumers. Race fixed above. Installed execution and semantic quality remain unproven runtime evidence; monitor defect tracked in R2. |
| C6–C7 | Production image admission/jobs/selection → shared roles and pickers; accepted revision voice bindings; isolated video jobs freeze role-ordered references and save results for Current Take. Preserve punctuation-safe/long voice bindings and paired-video audio numbering. No bounded defect found in those retained contracts; automatic world continuation is R1. |
| C8 | Durable video clip advancement/retry/identity is implemented. Required post-screenplay checked-stage progression is missing, R1. |
| C9 | Assembly saved selections → snapshot/manifest → durable export job → leased FFmpeg renderer → registered output/player. Retained CPU playable MP4 and mocked UI evidence unchanged. |
| C10 | Shared serial lease/default-off opt-in, queue admission and capability/parameter gates implemented. Non-Comfy cutoff is R2. Capability reports are not proof of installed operation; SAM checkpoint/endpoint/auth setup must be reconciled before its owner session. |
| C11–C12 | Debug bounded journal, default-off setting, existing three-theme/focus checks and ordered bounded acceptance packet retained. Corrected packet's Next wording to next prepared prompt or empty standalone draft. Packet remains unreleased. |

Graphify refreshed after source fix; see top HANDOFF for final extraction result. No UI implementation change or browser verification was claimed by this review. Runtime/creative quality remains separate from these required coding findings.
