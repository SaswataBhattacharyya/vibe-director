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

## Card 2 — isolated job adapter on durable execution service

**Depends on Card 1 and accepted architecture decision.** Add a story-free durable owner/job mapping, idempotent create/get/progress/reconcile/retake endpoints and immutable request/take snapshots over the reviewed SQLite ledger/worker. If the existing project-keyed schema cannot safely support isolated identity, propose a narrow migration rather than fabricating scenes. Reserve/bind exact Comfy `prompt_id`; unknown submission remains recovery-required; reconnect is read/reconcile only. Keep Comfy and output dependencies injected in CPU tests. Meaningful check: restart ledger/worker simulation, duplicate idempotency key, ambiguous POST outcome, reconciliation, exact full-snapshot retake preservation and keep/delete candidate choice without deleting shared assets. Live runtime remains separate.

## Card 3 — connect approved UI to API and supervised runtime

**Depends on Card 2 plus Ashu's accepted screen/API field contract and operator/runtime readiness.** Connect shared video screen entry for isolated T2V, validation, submission, progress/reconnect, playable output and preserved-input retake. Verify exact graph/model/node readiness and output playback in a supervised ComfyUI session only under separately approved generation authorization. CPU fixtures/mock browser behavior must be labeled separately from real render evidence. Stop on missing runtime readiness or uncertain submission; reconcile exact prompt before any retry.
