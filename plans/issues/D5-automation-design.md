# [D5] Design Automation & Parameters and shared run monitoring

Status: local issue draft; not published. Type: Design.

**Proposed lead/reviewer:** Ashu proposes; Saswata reviews. These are proposals, not an assignment already accepted by Ashu.
**Dependencies:** D1; G2 run-policy draft.
**Read first:** [current plans](../README.md), [issue working rules](../issue_backlog.md), then automation.md, ux_shared.md in `plans/`. Paths below are relative to the named reference source, except explicitly absolute paths.

## Outcome and scope

Design the setup page after screenplay and before model prompts. Manual requires Generate/Next at each used stage. Semi shows exactly five automation choices: character images, character-to-audio binding, world images, frame images, video. Each checked stage confirms defaults/settings. Full skips images/binding and uses first clip T2V then predecessor-video R2V within each scene. Quality/non-duration settings are confirmed initially; duration may be fixed or Director-selected.

Semi automated video lets the Director select compatible FFLF/R2V with prepared assets and optional previous-video continuity. Existing FFLF has no direct voice input: never depict unsupported voice conditioning.

## Questions to resolve in this issue

- How are checked automation, unchecked manual work and optional Skip visibly different?
- How is the confirmed policy summarized so users understand what runs without further clicks?
- What run view lets users inspect outcomes/errors and revise future work without adding per-clip Full approval gates?
- How are incompatible/missing assets resolved before execution?

## Acceptance evidence

- Prototype demonstrates Manual, mixed Semi and a two-scene Full chain with a visible scene reset.
- Automated settings include duration policy and bounded choices; quality stays fixed through the run.
- No silent fallback or pretend human approval; technical holds are actionable.
- Design states separate generated, retained and user-reviewed results. Backend policy execution belongs to B5.

## Handoff

Link the design/implementation PR, decisions, changed-file provenance and demonstrated evidence. Record unresolved dependencies explicitly. Follow the authoritative plans; ask about a real contradiction instead of reintroducing legacy pages or changing agreed mode policies.
