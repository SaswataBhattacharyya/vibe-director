# [D3] Design optional character/world/frame creation and voice binding

Status: published as [GitHub issue #7](https://github.com/SaswataBhattacharyya/vibe-director/issues/7). Type: Design.

**Proposed lead/reviewer:** Ashu proposes; Saswata reviews. These are proposals, not an assignment already accepted by Ashu.
**Dependencies:** D1; G2 asset contracts.
**Read first:** [current plans](../README.md), [issue working rules](../issue_backlog.md), then char_world.md, video_gen.md, ux_shared.md in `plans/`. Paths below are relative to the named reference source, except explicitly absolute paths.

## Outcome and scope

Design clean character-image, world-image and clip-frame screens, followed by character-to-voice binding. Show prompts and exact references, editable with annotation/chat microedits. Assets can be skipped where optional. Frames carry scene/shot/clip and first/last roles. Voice rows show character image/description plus searchable voice dropdown; multiple characters may share one file.

Reference Story Builder `pages/ProductionWorkspace.tsx`, `pages/AudioStudio.tsx`, `components/FileUpload.tsx`, `services/production_assets.py`, `production_image_workflows.py`, `production_voice_binding.py`.

## Questions to resolve in this issue

- Should these be separate pages or focused views within one assets workspace while preserving the requested clean divisions?
- How do variant selection, skip, recommended refs and generation/retake states appear?
- How are reused voice files and missing bindings made clear without duplicating files?

## Acceptance evidence

- Prototype includes skip, first/last frame metadata, shared voice binding and prompt/reference annotation.
- Assisted manual recommended image/voice refs are shown first but remain unselected until chosen.
- Model prompt budgets and unavailable workflows have explicit states.
- UI requirements/API needs feed bounded implementation tickets rather than recreating the old workspace wholesale.

## Handoff

Link the design/implementation PR, decisions, changed-file provenance and demonstrated evidence. Record unresolved dependencies explicitly. Follow the authoritative plans; ask about a real contradiction instead of reintroducing legacy pages or changing agreed mode policies.


## Current implementation and Ashu's next work — 2026-10-08

Ashu owns UI design; the current engineering UI is provisional. Saswata reviews. Design ownership changes only on Saswata's explicit instruction. The project goal is paused; this handoff publishes existing work and does not restart implementation.

Current implementation: no character/world/frame generation or voice-binding UI/API is integrated; Assets is a disabled placeholder. Ashu should design the clean asset views, optional Skip, visible editable prompt/reference snapshots, variant review and searchable voice rows with shared files. Preserve role-filtered first/last frames and recommended-but-unselected character/voice references. Record proposed API contracts as proposals until backend issue #11 provides them.

Start from branch `issue-2-isolated-t2v-reuse` / [draft PR #15](https://github.com/SaswataBhattacharyya/vibe-director/pull/15), rather than assuming main has the implementation. Read [Ashu's UI handoff](https://github.com/SaswataBhattacharyya/vibe-director/blob/issue-2-isolated-t2v-reuse/plans/ASHU_UI_HANDOFF.md) for exact files, API behavior, preserved recovery/GPU invariants and focused evidence. This issue remains open; provisional code and passing mocks are not design acceptance.

For Codex/Claude: inspect those files and the linked stage plan; answer the issue's design questions, propose annotated layouts/states and API needs, then make bounded UI changes in a separate PR. Preserve saved requests, explicit generation and recovery behavior. Use mocked requests for UI verification; do not launch live generation or rerun the broad legacy test suite.