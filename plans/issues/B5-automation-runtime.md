> Updated owner decision: only **Assisted manual** and **Fully automated** appear as modes. No checks means manual operation; all five checks means automatic asset preparation and video. The separate Fully automated preset skips images and keeps its T2V/R2V chain. Read `../automation.md` and `../development_workflow.md`; previous Manual/Semi labels are retired.

# [B5] Implement the two modes using the shared execution service

Status: published as [GitHub issue #13](https://github.com/SaswataBhattacharyya/vibe-director/issues/13). Type: Implementation.

**Proposed lead/reviewer:** Backend implementer proposes; both review journey behavior. These are proposals, not an assignment already accepted by Ashu.
**Dependencies:** B1/B3 contracts; B2 screenplay coverage; D5 accepted.
**Read first:** [current plans](../README.md), [issue working rules](../issue_backlog.md), then automation.md, integration.md, ux_shared.md in `plans/`. Paths below are relative to the named reference source, except explicitly absolute paths.

## Outcome and scope

Adapt Story Builder `services/production_stage_tasks.py`, `production_reconciliation.py`, `production_job_worker.py`, `production_take_runtime.py`, `production_video_director.py` and capability services, retaining only compatible logic. Implement policy-driven scheduling over the same jobs/forms used manually; no second controller. Freeze confirmed quality/non-duration settings and bounded duration policy.

Fully automated: bypass image generation/required voice binding. Without a selected direct style video, each scene starts T2V; later clips use predecessor R2V. With a confirmed selected style video, the first clip uses R2V style video + text and later clips retain style plus predecessor continuity. Reset predecessor per scene, retain style and every generated clip. Validate combined reference counts/durations first; conflicts block without silent reference dropping or T2V fallback. Zero exported style frames still allows the original video. Read production_styles.md. Assisted manual: exactly five selections; unchecked used stages wait for manual action; selected video uses Director-chosen compatible FFLF/R2V and authorized refs. Required voice conditioning cannot use the current FFLF graph. No silent fallback.

## Questions to resolve in this issue

- What durable checkpoint identifies the next unfinished stage/clip and prevents duplicate advancement after restart?
- How does source coverage ensure the entire screenplay was scheduled, including gaps/failures?
- What authorized policy governs Director duration/ref decisions and failures?

## Acceptance evidence

- Demonstrate Assisted manual with none/some/all checked through the UI and a two-scene Fully automated trace with reset and all retained outputs.
- Confirmed settings persist; duration decisions remain within selected workflow bounds.
- Pause/error/reconnect preserve pending manual tasks and existing jobs; uncertain jobs are reconciled.
- Distinguish auto-completed from human-reviewed; never synthesize approval to satisfy upstream checkpoints.
- Add focused policy/recovery checks and bounded real integration evidence after authorization.

## Handoff

Link the design/implementation PR, decisions, changed-file provenance and demonstrated evidence. Record unresolved dependencies explicitly. Follow the authoritative plans; ask about a real contradiction instead of reintroducing legacy pages or changing agreed mode policies.
