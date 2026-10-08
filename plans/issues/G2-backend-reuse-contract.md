# [G2] Map reusable services and define the UI/API boundary

Status: published as [GitHub issue #2](https://github.com/SaswataBhattacharyya/vibe-director/issues/2). Type: Groundwork.

**Proposed lead/reviewer:** Saswata/backend implementer proposes; Ashu co-designs. These are proposals, not an assignment already accepted by Ashu.
**Dependencies:** G1 source access; can begin locally now.
**Read first:** [current plans](../README.md), [issue working rules](../issue_backlog.md), then integration.md, GLOSSARY.md, ux_shared.md in `plans/`. Paths below are relative to the named reference source, except explicitly absolute paths.

## Outcome and scope

Create a bounded extraction manifest and API contract before copying application code. For each selected file record source hash, dependencies, destination chosen during architecture, keep/adapt/new decision, affected callers and acceptance evidence. Audit Story Builder and any copied dependencies for license compatibility; OpenMontage covered-source adoption requires an explicit compatible license decision before import.

Candidate groups: Story Builder `services/production_story_revisions.py`, `chunked_generation.py`, `production_world_state.py`, `production_assets.py`, `production_voice_binding.py`, `production_take_runtime.py`, `production_job_worker.py`, `media_jobs.py`, local capability services and `minimax_h3_graph_compiler.py`. OpenMontage `tools/_comfyui/client.py`, `lib/checkpoint.py`, `tools/video/video_selector.py`, `lib/corpus.py`, `tools/cost_tracker.py` are candidates, not a wholesale framework import. Use one durable execution authority and shared asset identity.

## Questions to resolve in this issue

- Which existing persistence/worker boundary can be retained with the fewest safe changes?
- Which existing endpoints already fit the new screens, and which need thin adapters?
- How will source revisions, run policies, assets, clips/takes, jobs and reference manifests be represented and versioned?
- Does copying AGPL code fit the intended product, or should those particular helpers be implemented independently?

## Acceptance evidence

- Versioned request/response examples cover validation, start, progress, reconnect, outputs and retake, plus offline UI fixtures.
- A file-level extraction map records provenance and dependencies; invented target paths are marked proposed until architecture agrees.
- Workflow readiness/limits come from actual graphs, not hard-coded UI guesses.
- Gaps needing new code are identified explicitly. Existing green tests are not treated as proof of the new UI journey.

## Handoff

Link the design/implementation PR, decisions, changed-file provenance and demonstrated evidence. Record unresolved dependencies explicitly. Follow the authoritative plans; ask about a real contradiction instead of reintroducing legacy pages or changing agreed mode policies.
