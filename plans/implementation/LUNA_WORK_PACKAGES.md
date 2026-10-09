> These cards record the initial isolated T2V slice. They are evidence and specific contracts, not the whole-project task order. Current Luna leadership, reuse instructions and Sol review points are in `../development_workflow.md`; check the current branch and handoff before treating old “Next”/readiness statements as current.

# Luna implementation work packages: isolated T2V

These cards implement the accepted isolated-video contract after architecture/Ashu UI review. Product requirements are frozen by `plans/README.md`, `plans/video_gen.md`, `plans/ux_shared.md` and the published G2/B1 issues; these cards add no navigation choice. No live generation is authorized here.

## Card 1 — CPU-only isolated request contract and compiler preview

**Implemented in this draft branch; no Ashu layout or GPU was required.** D4 screen layout is not a prerequisite for CPU request-contract work. Product fields follow current agreed video plan; adapter/endpoint layout remains proposed.

- **Copied unchanged:** `backend/story_builder/services/minimax_h3_t2v.py`, `backend/story_builder/services/minimax_h3_graph_compiler.py`, `backend/story_builder/workflows/api/minimax_h3_t2v_api.json`; provenance and matched Git blob/SHA256 hashes are in `backend/README.md`.
- **Added:** `backend/story_builder/services/isolated_video_contract.py` and `backend/story_builder/tests/test_isolated_video_contract.py`.
- **Behavior:** strict unknown/missing field rejection; exact graph hash/workflow check; MiniMax prompt below 7000 Python Unicode code points while preserving authored prompt exactly; finite T2V 5–10 second, 16:9 and preset validation; empty references only; fixed first-slice `steps=20` and `seed=1`. Editable steps/seed are deferred pending a reviewed T2V capability contract. Preview uses compatibility-only internal compiler IDs, rewrites SaveVideo prefix to `isolated_preview/preview_only`, returns no submit operation, and labels frame-derived duration as predicted. No persistence, readiness probe, Comfy call, or provider call.
- **Run:** from `backend/`, `PYTHONPATH=. python -m unittest discover -s story_builder/tests -v` (standard library only).
- **Verified:** eight focused cases cover 6999/7000 prompt boundary, whitespace retention, 5/10 duration endpoints and invalid/nonfinite/bool values, both presets, adapter settings checks, graph drift, refs/unknown fields, canonical hash order/numeric equivalence/settings sensitivity, source graph/input immutability and 6-second compile result of 158 frames at 1344×768 with 158/24 seconds predicted.
- **Evidence/limits:** this CPU result proves deterministic contract/compile behavior only. It does not prove workflow readiness, output duration, durable recovery, playback, or usable video. Live T2V capability should call the existing `production_t2v_capability.t2v_capability()` after a safe adapter seam is reviewed; no duplicate readiness module is added here.

## Card 2 — isolated durable backend

**Implemented in this draft branch; the UI remains separate.** Added the story-free job facade and metadata on the same production ledger; product identity is aliased to ledger project/shot fields, with one narrow atomic `queue_take(on_create=...)` hook. Added CPU localhost API routes and an explicitly started worker process. The API never auto-starts dispatch; worker status is surfaced and create POST fails closed without a fresh, healthy explicitly enabled consumer. Readiness is rechecked before claiming queued work and again in prepare. The existing worker owns exact prompt reservation, one-submit handling, watchdog, and ambiguous-result reconciliation. Output collection stores ffprobe-confirmed audio+video assets under the product data root. GET idempotency recovery never repairs/mutates state. Retakes first return a read-only full-request draft and require a separate explicit Generate request; `recovery_required` jobs cannot be drafted/retried. Keep/delete is explicit, and delete only sets a candidate flag after accepted replacement; actual reference-aware GC is deferred.

- **Main files:** `backend/story_builder/services/isolated_video_jobs.py`, `backend/story_builder/isolated_server.py`, `backend/story_builder/isolated_worker.py`; modified source adaptations are the ledger transaction hook and T2V graph node catalog comparison.
- **Focused check:** `cd backend && PYTHONPATH=. python -m unittest discover -s story_builder/tests -v` (20 tests, stdlib-only, injected fake Comfy responses; no live API/GPU/provider/render).
- **Remaining evidence:** no real Comfy rendering, live output collection/playback, browser integration, or restart recovery has been established. Current host GPU clock snapshot exceeds preserved 2100 MHz ceiling. Do not start worker/runtime until safe conditions and explicit supervised generation acceptance.

## Card 3 — connect approved UI to API and supervised runtime

**Next:** connect the accepted product screen to the staged API fields (including `playback_url`, worker dispatch availability and idempotency recovery). Verify browser usability, reconnection, and retake form behavior without automatic submission. Separately, when live GPU/runtime readiness permits, perform a user-clicked supervised Generate test; prove exact graph/model/node readiness, native media output/playback, restart reconciliation and preserved-input retake. Keep CPU fixtures visibly distinct from real renders. Stop on missing readiness or uncertain submission; reconcile the exact prompt before any retry.
