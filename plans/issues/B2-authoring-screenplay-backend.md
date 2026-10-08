# [B2] Adapt V2 revisions and build real story edits/graph/screenplay derivation

Status: local issue draft; not published. Type: Implementation.

**Proposed lead/reviewer:** Backend implementer proposes; both review creative semantics. These are proposals, not an assignment already accepted by Ashu.
**Dependencies:** G2; D2 accepted; deliver in separate bounded PRs.
**Read first:** [current plans](../README.md), [issue working rules](../issue_backlog.md), then screenplay.md, rectifications.md, GLOSSARY.md in `plans/`. Paths below are relative to the named reference source, except explicitly absolute paths.

## Outcome and scope

Use Story Builder `services/production_story_revisions.py`, `chunked_generation.py`, `production_world_state.py`, `production_shot_plan.py`, `production_authority.py` as reuse candidates. Build actual selected-text LLM revision handling, source-linked graph facts and readable integrated screenplay records. This includes new implementation; copying old prompts alone is insufficient. Use only the V2 preparation lineage, not legacy `story_pipeline.py` as a parallel controller.

Split implementation into revision/edit round-trip, graph/source linking and screenplay derivation PRs with producer-to-consumer verification. Reconcile legacy context/row caps with long-story requirements; bounded requests and paginated storage are valid, silently losing source facts is not.

## Questions to resolve in this issue

- Which graph storage and span/revision model preserve provenance and conflicting facts?
- How will chunk context cover the whole story and expose missing coverage?
- How do screenplay edits invalidate only dependent prompts/assets, while take-only overrides stay local?

## Acceptance evidence

- An actual selected edit creates a reversible persisted revision rather than an inserted note.
- A multi-chunk story produces numbered scenes/shots/dialogue with linked source coverage and holistic direction.
- Reload preserves graph/revision links; changed screenplay identifies stale derived work.
- Final prompts are derived after mode/settings choice, and model budgets never truncate the story silently.

## Handoff

Link the design/implementation PR, decisions, changed-file provenance and demonstrated evidence. Record unresolved dependencies explicitly. Follow the authoritative plans; ask about a real contradiction instead of reintroducing legacy pages or changing agreed mode policies.
