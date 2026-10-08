# [B3] Adapt image/voice assets and exact FFLF/R2V request compilation

Status: published as [GitHub issue #11](https://github.com/SaswataBhattacharyya/vibe-director/issues/11). Type: Implementation.

**Proposed lead/reviewer:** Backend implementer proposes; Ashu implements/reviews shared forms. These are proposals, not an assignment already accepted by Ashu.
**Dependencies:** G2; D3/D4 accepted; B1 durable execution boundary.
**Read first:** [current plans](../README.md), [issue working rules](../issue_backlog.md), then char_world.md, video_gen.md, integration.md in `plans/`. Paths below are relative to the named reference source, except explicitly absolute paths.

## Outcome and scope

Deliver bounded PRs for image jobs/bindings, FFLF requests and dynamic R2V manifests. Reuse Story Builder `services/production_assets.py`, `production_image_workflows.py`, `production_image_jobs.py`, `production_voice_binding.py`, `production_route_assets.py`, `production_fl2va_capability.py`, `minimax_h3_graph_compiler.py` and `workflows/api/minimax_h3_i2v_api.json`.

Adapt exact stable IDs and scene/shot/clip/frame roles. Deduplicate shared voice-file assets while preserving distinct character identities and compiler-local speaker labels. Collation compiles per-reference intent and main prompt into one reviewed prompt, with exact labels from the selected graph. Do not import cloud limits as local limits.

## Questions to resolve in this issue

- Which current image models/workflows are actually usable, and what are their prompt units/limits?
- What image/video/audio capacities, labels, durations and output settings does each local graph accept?
- Which existing compiler assumptions prevent two characters sharing one voice file?

## Acceptance evidence

- Each adapter validates the final exact request and rejects unsupported refs/roles before submission.
- FFLF requires two correct frame roles; voice-required generation routes to a compatible R2V graph.
- Shared voice binding works through the real manifest/compiler consumer, without duplicate files or lost identity.
- Collation/editing invalidates stale compiled prompts; saved take records preserve final prompt, refs, intent, workflow hash and parameters.

## Handoff

Link the design/implementation PR, decisions, changed-file provenance and demonstrated evidence. Record unresolved dependencies explicitly. Follow the authoritative plans; ask about a real contradiction instead of reintroducing legacy pages or changing agreed mode policies.
