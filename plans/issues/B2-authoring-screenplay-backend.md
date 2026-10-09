# [B2] Adapt V2 revisions and build real story edits/graph/screenplay derivation

Status: published as [GitHub issue #10](https://github.com/SaswataBhattacharyya/vibe-director/issues/10). Type: Implementation.

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

## 2026-10-09 implementation checkpoint

Issue #10 is in progress on the B2 graph/source-linking increment after the published #20 selected-edit commit. The current graph producer maps every exact source chunk independently into validated entity/fact/event/time/relation/open-question records, stores immutable revision/hash-bound snapshots and exact code-point evidence in the existing StoryAuthoring ledger, and exposes keyed replay/recovery plus inspect/review/edit/reload UI. This is a usable first producer-consumer slice, not a complete graph: chunk processing is not semantic coverage; cross-chunk alias/identity reconciliation and contradiction analysis remain unimplemented, and snapshot contradiction state is explicitly `not_assessed`. Screenplay derivation and dependent invalidation are still pending.

Parent review added duplicate-request claim safety and explicit recovery semantics: same-key concurrent requests preserve recent processing claims; claims older than the five-minute Codex timeout plus a recovery margin become uncertain; the explicit UI retry reruns only validated-response failures, retaining complete chunks and never resubmitting uncertain calls. Regression checks cover duplicate POST, failed-chunk-only retry, and uncertain-call replay. Typecheck and production build pass. Mocked browser execution is still pending because Chromium launch was denied by the sandbox; backend journey checks use the fake provider only.

2026-10-09 screenplay V2 increment: drafting now maps over every exact source chunk, passes prior chunk continuity context, validates every shot against graph evidence from its own chunk, and persists resumable task/chunk state and immutable screenplay revisions in the same ledger. A screenplay replay now stops at the first incomplete chunk, including uncertain provider outcomes, so later scenes cannot be generated without the missing continuity context. Focused fake-provider tests cover lineage, recovery, idempotency, invalid evidence and stale edits. Remaining: graph reconciliation and semantic coverage, source-edit invalidation, screenplay history/acceptance, and live-provider acceptance. See the current milestone entry in `HANDOFF.md`.
