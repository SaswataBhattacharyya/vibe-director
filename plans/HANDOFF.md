# Current planning handoff — 2026-10-08

## Objective and authority

Prepare Vibe Director collaboratively with Ashu by selectively reusing Story Builder services. `plans/README.md` and linked stage plans govern product behavior; earlier plans/source journeys are historical reuse evidence. Product requirements are frozen for this bounded slice. The public repository is `SaswataBhattacharyya/vibe-director`, baseline `main` `0b7d4ddd9526e586b16e495b7e0455c07a20cd94`; it has 66 plans/guidance files and 14 open issues. GitHub #2 and #5 remain open.

## Current implementation and evidence

The CPU-only isolated H3 T2V preview slice is implemented in the draft package: exact copies of the upstream T2V compiler, graph compiler dependency and workflow JSON, plus strict request validation, canonical request hashing, preview compilation and eight focused standard-library tests. Source baseline is `mooV_E_maker` commit `2023bf5bce1a808b2624fb5789b4b2a1e8b7b8db`; provenance and local hashes are in `backend/README.md`.

From `backend/`, run `PYTHONPATH=. python -m unittest discover -s story_builder/tests -v`. The suite validates prompt/duration/preset boundaries, fixed steps=20 and seed=1, graph hash drift and single-read pinning, references/unknown fields, hash normalization, and preview compilation (6 seconds requested → 158 frames, 6.583333 seconds predicted). No HTTP routes, readiness adapter, durable job integration, UI, or live render are included. Existing `production_t2v_capability.t2v_capability()` remains the readiness source to reuse later. Proposed APIs/examples are not live endpoints.

## Pending work and decisions

An issue-linked draft PR is prepared for review; do not merge it or close #2/#5. The canonical repository is `/home/riki/Documents/ChatGPT/Vibe Director`; planning files were backed up on branch `planning-pre-publication`. Next, architecture/Ashu review should settle the isolated job owner and API/UI shape, then a small durable job/reconciliation slice can reuse the existing production worker/ledger with appropriate isolation. A later UI/runtime card needs Ashu's accepted screen/API field contract and separately supervised ComfyUI/GPU readiness. Keep generated duration distinct from frame-derived prediction; never resubmit automatically on reconnect or uncertain submission. Retake must preserve the complete input snapshot and ask whether to retain the prior candidate; shared/referenced assets are not deleted by that choice.

## Access, permissions and external runtime

User delegated coding/file creation/copying to Luna; parent handles reasoning/review and publication. Ashu currently has read access; arrange write access with the repository owner if needed, without sending an invitation from this task. Canonical project root is `/home/riki/Documents/ChatGPT/Vibe Director`. Reference trees and runtimes remain external: Story Builder source is at `/home/riki/web_dev/story_builder`; OpenMontage reviewed SHA is `9327439db69021ab4b0e2776729bf3b58fdb5a87`; ComfyUI/model setup remains external. No OpenMontage/AGPL code, model weights, app runtime, dependencies, secrets, or media were copied. No paid provider or GPU job was run; there are no live process/job handles.
