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
