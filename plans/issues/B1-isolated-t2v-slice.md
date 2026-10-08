# [B1] Connect isolated T2V from edited prompt to durable job and retake

Status: local issue draft; not published. Type: Implementation.

**Proposed lead/reviewer:** Backend implementer proposes; Ashu integrates/reviews UI. These are proposals, not an assignment already accepted by Ashu.
**Dependencies:** G2; D1/D4 accepted for this slice.
**Read first:** [current plans](../README.md), [issue working rules](../issue_backlog.md), then integration.md, video_gen.md, ux_shared.md in `plans/`. Paths below are relative to the named reference source, except explicitly absolute paths.

## Outcome and scope

Extract only the services needed for the first end-to-end slice: isolated prompt/settings → exact locally ready T2V graph → durable job/progress → playable output → preserved-request retake. Candidates: Story Builder `services/minimax_h3_t2v.py`, `production_t2v_capability.py`, `production_take_runtime.py`, `production_job_worker.py`, `media_jobs.py`. Preserve supervised GPU admission and prompt IDs. Implement against G2 contracts and shared D4 form.

OpenMontage generic Comfy client is only a candidate if a concrete existing gap justifies it. No live generation is authorized merely by drafting this issue.

## Questions to resolve in this issue

- Which existing durable job path can support a story-free request without fabricating project/scene canon?
- How does reconnection distinguish unsubmitted, submitted, failed and uncertain work to avoid duplicate renders?

## Acceptance evidence

- Browser demo shows validation, submission, progress, playback and retake preserving prompt/settings/refs.
- Reload resumes the same job/result; ambiguous submission is reconciled before retry.
- Missing engine/workflow is actionable and leaves prompt editable.
- Verify relevant persistence/restart contracts; an authorized supervised real render is the integration gate, not a test-count target.

## Handoff

Link the design/implementation PR, decisions, changed-file provenance and demonstrated evidence. Record unresolved dependencies explicitly. Follow the authoritative plans; ask about a real contradiction instead of reintroducing legacy pages or changing agreed mode policies.
