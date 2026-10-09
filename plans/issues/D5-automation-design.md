> Updated owner decision: only **Assisted manual** and **Fully automated** appear as modes. No checks means manual operation; all five checks means automatic asset preparation and video. The separate Fully automated preset skips images and keeps its T2V/R2V chain. Read `../automation.md` and `../development_workflow.md`; previous Manual/Semi labels are retired.

# [D5] Design Automation & Parameters and shared run monitoring

Status: published as [GitHub issue #8](https://github.com/SaswataBhattacharyya/vibe-director/issues/8). Type: Design.

**Proposed lead/reviewer:** Ashu proposes; Saswata reviews. These are proposals, not an assignment already accepted by Ashu.
**Dependencies:** D1; G2 run-policy draft.
**Read first:** [current plans](../README.md), [issue working rules](../issue_backlog.md), then automation.md, ux_shared.md in `plans/`. Paths below are relative to the named reference source, except explicitly absolute paths.

## Outcome and scope

Design the setup page after screenplay and before model prompts. Assisted manual requires Generate/Next only for unchecked used stages and shows exactly five automation choices: character images, character-to-audio binding, world images, frame images, video. Each checked stage confirms defaults/settings. Fully automated skips images/binding and uses first clip T2V then predecessor-video R2V within each scene. Quality/non-duration settings are confirmed initially; duration may be fixed or Director-selected.

Assisted manual automated video lets the Director select compatible FFLF/R2V with prepared assets and optional previous-video continuity. Existing FFLF has no direct voice input: never depict unsupported voice conditioning.

## Questions to resolve in this issue

- How are checked automation, unchecked manual work and optional Skip visibly different?
- How is the confirmed policy summarized so users understand what runs without further clicks?
- What run view lets users inspect outcomes/errors and revise future work without adding per-clip Fully automated approval gates?
- How are incompatible/missing assets resolved before execution?

## Acceptance evidence

- Prototype demonstrates Assisted manual with none/some/all checked and a two-scene Fully automated chain with a visible scene reset.
- Automated settings include duration policy and bounded choices; quality stays fixed through the run.
- No silent fallback or pretend human approval; technical holds are actionable.
- Design states separate generated, retained and user-reviewed results. Backend policy execution belongs to B5.

## Handoff

Link the design/implementation PR, decisions, changed-file provenance and demonstrated evidence. Record unresolved dependencies explicitly. Follow the authoritative plans; ask about a real contradiction instead of reintroducing legacy pages or changing agreed mode policies.


## Current implementation and Ashu's next work — 2026-10-08

Ashu owns UI design; the current engineering UI is provisional. Saswata reviews. Design ownership changes only on Saswata's explicit instruction. The project goal is paused; this handoff publishes existing work and does not restart implementation.

Current implementation: the isolated T2V screen has one manually triggered Generate and durable job review, but no screenplay setup, Assisted manual checkboxes, Fully automated chain, Director policy or run-monitoring wrapper exists. Ashu should design Automation & Parameters after screenplay and before derived prompts, confirm exactly five Assisted manual choices and initial parameters, and design scene-reset/continuity, progress and actionable technical holds. Existing isolated Assisted manual behavior is not evidence that the wrappers are implemented.

Start from branch `issue-2-isolated-t2v-reuse` / [draft PR #15](https://github.com/SaswataBhattacharyya/vibe-director/pull/15), rather than assuming main has the implementation. Read [Ashu's UI handoff](https://github.com/SaswataBhattacharyya/vibe-director/blob/issue-2-isolated-t2v-reuse/plans/ASHU_UI_HANDOFF.md) for exact files, API behavior, preserved recovery/GPU invariants and focused evidence. This issue remains open; provisional code and passing mocks are not design acceptance.

For Codex/Claude: inspect those files and the linked stage plan; answer the issue's design questions, propose annotated layouts/states and API needs, then make bounded UI changes in a separate PR. Preserve saved requests, explicit generation and recovery behavior. Use mocked requests for UI verification; do not launch live generation or rerun the broad legacy test suite.