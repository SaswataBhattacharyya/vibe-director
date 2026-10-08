# [B5] Implement the three wrappers using the shared execution service

Status: local issue draft; not published. Type: Implementation.

**Proposed lead/reviewer:** Backend implementer proposes; both review journey behavior. These are proposals, not an assignment already accepted by Ashu.
**Dependencies:** B1/B3 contracts; B2 screenplay coverage; D5 accepted.
**Read first:** [current plans](../README.md), [issue working rules](../issue_backlog.md), then automation.md, integration.md, ux_shared.md in `plans/`. Paths below are relative to the named reference source, except explicitly absolute paths.

## Outcome and scope

Adapt Story Builder `services/production_stage_tasks.py`, `production_reconciliation.py`, `production_job_worker.py`, `production_take_runtime.py`, `production_video_director.py` and capability services, retaining only compatible logic. Implement policy-driven scheduling over the same jobs/forms used manually; no second controller. Freeze confirmed quality/non-duration settings and bounded duration policy.

Full: bypass images/binding, scene first clip T2V, later R2V with immediate predecessor, reset on each new scene, retain all clips. Semi: exactly five selections; unchecked used stages wait for manual action; selected video uses Director-chosen compatible FFLF/R2V and authorized refs. Required voice conditioning cannot use the current FFLF graph. No silent fallback.

## Questions to resolve in this issue

- What durable checkpoint identifies the next unfinished stage/clip and prevents duplicate advancement after restart?
- How does source coverage ensure the entire screenplay was scheduled, including gaps/failures?
- What authorized policy governs Director duration/ref decisions and failures?

## Acceptance evidence

- Demonstrate Manual and mixed Semi through the UI and a two-scene Full trace with reset and all retained outputs.
- Confirmed settings persist; duration decisions remain within selected workflow bounds.
- Pause/error/reconnect preserve pending manual tasks and existing jobs; uncertain jobs are reconciled.
- Distinguish auto-completed from human-reviewed; never synthesize approval to satisfy upstream checkpoints.
- Add focused policy/recovery checks and bounded real integration evidence after authorization.

## Handoff

Link the design/implementation PR, decisions, changed-file provenance and demonstrated evidence. Record unresolved dependencies explicitly. Follow the authoritative plans; ask about a real contradiction instead of reintroducing legacy pages or changing agreed mode policies.
