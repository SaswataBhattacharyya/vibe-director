# [D2] Design merged story authoring and the readable screenplay

Status: published as [GitHub issue #6](https://github.com/SaswataBhattacharyya/vibe-director/issues/6). Type: Design.

**Proposed lead/reviewer:** Ashu proposes; Saswata reviews. These are proposals, not an assignment already accepted by Ashu.
**Dependencies:** D1; G2 revision contract draft.
**Read first:** [current plans](../README.md), [issue working rules](../issue_backlog.md), then screenplay.md, rectifications.md, GLOSSARY.md in `plans/`. Paths below are relative to the named reference source, except explicitly absolute paths.

## Outcome and scope

Design one merged story/canvas workspace with real chat edits and passage annotation, revision visibility and access to source-linked graph facts. Design readable scene/shot/dialogue hierarchy before JSON/model prompts, with camera/action/lighting/mood/SFX/music integrated into the screenplay. No arbitrary story-length cap; backend processing may chunk safely.

Inspect Story Builder `frontend/app/src/pages/StoryBuilder.tsx`, `StoryCanvas.tsx`, `ProductionWorkspace.tsx` and the V2 revision/chunking services. The old Focused edit placeholder is not acceptable reuse.

## Questions to resolve in this issue

- How do scene/shot numbers, dialogue and direction appear together while remaining readable?
- How are selected passage edits previewed, accepted and undone, and their scope shown?
- How can users inspect conflicting graph facts or stale downstream work without technical JSON?
- What long-story navigation/search is useful without loading every section into the editor at once?

## Acceptance evidence

- Prototype covers a long story section, one integrated scene, an actual proposed edit/diff and its downstream stale notice.
- Editing states distinguish suggestion, saved revision and generation; no fake AI edit note.
- Technical data is optional advanced detail; the main screenplay is ordinary readable text.
- Produce design decisions and UI implementation tickets; backend graph/editor implementation is B2.

## Handoff

Link the design/implementation PR, decisions, changed-file provenance and demonstrated evidence. Record unresolved dependencies explicitly. Follow the authoritative plans; ask about a real contradiction instead of reintroducing legacy pages or changing agreed mode policies.


## Current implementation and Ashu's next work — 2026-10-08

Ashu owns UI design; the current engineering UI is provisional. Saswata reviews. Design ownership changes only on Saswata's explicit instruction. The project goal is paused; this handoff publishes existing work and does not restart implementation.

Current implementation: no story, graph, or screenplay UI/API is integrated. Story navigation is disabled. A revision/chunking foundation exists only in a local unpublished staging area and has incomplete parent review; do not depend on it as a published API. Ashu should design the merged story/canvas editor, real conversational edit/diff/revision states, graph fact inspection and human-readable holistic screenplay; propose the UI/state contracts for backend issue #10.

Start from branch `issue-2-isolated-t2v-reuse` / [draft PR #15](https://github.com/SaswataBhattacharyya/vibe-director/pull/15), rather than assuming main has the implementation. Read [Ashu's UI handoff](https://github.com/SaswataBhattacharyya/vibe-director/blob/issue-2-isolated-t2v-reuse/plans/ASHU_UI_HANDOFF.md) for exact files, API behavior, preserved recovery/GPU invariants and focused evidence. This issue remains open; provisional code and passing mocks are not design acceptance.

For Codex/Claude: inspect those files and the linked stage plan; answer the issue's design questions, propose annotated layouts/states and API needs, then make bounded UI changes in a separate PR. Preserve saved requests, explicit generation and recovery behavior. Use mocked requests for UI verification; do not launch live generation or rerun the broad legacy test suite.