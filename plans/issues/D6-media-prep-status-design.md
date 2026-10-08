# [D6] Arrange Media Prep libraries/tools and the Status catalog

Status: local issue draft; not published. Type: Design.

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
