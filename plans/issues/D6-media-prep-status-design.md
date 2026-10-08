# [D6] Arrange Media Prep libraries/tools and the Status catalog

Status: published as [GitHub issue #9](https://github.com/SaswataBhattacharyya/vibe-director/issues/9). Type: Design.

**Proposed lead/reviewer:** Ashu proposes; Saswata reviews. These are proposals, not an assignment already accepted by Ashu.
**Dependencies:** D1; G2 library/capability contracts.
**Read first:** [current plans](../README.md), [issue working rules](../issue_backlog.md), then media_prep.md, ux_shared.md, integration.md in `plans/`. Paths below are relative to the named reference source, except explicitly absolute paths.

## Outcome and scope

Arrange Media Prep into Video, Audio and Images using existing tools. Preserve Video Repertoire & Summariser capabilities/tabs; place Audio Studio, Audio Reconstruct, Music & Sound, Audio Utilities and Audio Repository clearly; add Image Repository alongside Image Detailer. Libraries use common stable assets, readable descriptions, JSON metadata and search. Status shows backend connectivity, usable workflows, parameter/prompt limits and actual readiness.

Reference Story Builder `pages/VideoRepertoire.tsx`, `AudioStudio.tsx`, `AudioReconstruct.tsx`, `MusicSound.tsx`, `AudioUtilities.tsx`, `ImageDetailer.tsx`, `AgentStatus.tsx`.

## Questions to resolve in this issue

- Which tabs/subroutes avoid a large competing top navigation while preserving all existing utilities?
- How do tool outputs enter the same libraries consumed by video pickers?
- How will audio categories and image/video metadata filters work visually?
- How do available, configured, missing-node/model and verified workflow states differ?

## Acceptance evidence

- Inventory maps each existing tool to the new arrangement; none is silently removed.
- Mockups show library ingestion, readable metadata, category/search and reuse in a generation picker.
- Image Repository is identified as new UI/storage integration work, not claimed already complete.
- Status distinguishes reachable engine from usable exact workflow and shows limits with units.

## Handoff

Link the design/implementation PR, decisions, changed-file provenance and demonstrated evidence. Record unresolved dependencies explicitly. Follow the authoritative plans; ask about a real contradiction instead of reintroducing legacy pages or changing agreed mode policies.


## Current implementation and Ashu's next work — 2026-10-08

Ashu owns UI design; the current engineering UI is provisional. Saswata reviews. Design ownership changes only on Saswata's explicit instruction. The project goal is paused; this handoff publishes existing work and does not restart implementation.

Current implementation: Video has workflow/GPU/worker readiness displays, but Media Prep and global Status are not integrated in the published branch. A Status projection/page is locally staged only, with incomplete parent review/browser evidence; it is not an accepted design or published API. Ashu should design Media Prep subroutes and repositories, shared search/metadata/pickers, and the global connectivity/workflow/limits catalog. Distinguish configured/installed from usable/verified, and unknown budgets from confirmed limits.

Start from branch `issue-2-isolated-t2v-reuse` / [draft PR #15](https://github.com/SaswataBhattacharyya/vibe-director/pull/15), rather than assuming main has the implementation. Read [Ashu's UI handoff](https://github.com/SaswataBhattacharyya/vibe-director/blob/issue-2-isolated-t2v-reuse/plans/ASHU_UI_HANDOFF.md) for exact files, API behavior, preserved recovery/GPU invariants and focused evidence. This issue remains open; provisional code and passing mocks are not design acceptance.

For Codex/Claude: inspect those files and the linked stage plan; answer the issue's design questions, propose annotated layouts/states and API needs, then make bounded UI changes in a separate PR. Preserve saved requests, explicit generation and recovery behavior. Use mocked requests for UI verification; do not launch live generation or rerun the broad legacy test suite.