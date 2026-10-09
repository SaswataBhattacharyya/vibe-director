# [F1] Define final clip assembly, sound and export before selecting tools

Status: published as [GitHub issue #14](https://github.com/SaswataBhattacharyya/vibe-director/issues/14). Type: Design.

**Proposed lead/reviewer:** Both; proposed later milestone. These are proposals, not an assignment already accepted by Ashu.
**Dependencies:** Generation/take journey stable; user supplies assembly intent.
**Read first:** [current plans](../README.md), [issue working rules](../issue_backlog.md), then integration.md, openmontage_comparison.md in `plans/`. Paths below are relative to the named reference source, except explicitly absolute paths.

## Outcome and scope

Final assembly has not been specified by the user. Gather the editing/export journey after generation is usable. Evaluate existing Story Builder capabilities and OpenMontage `tools/video/video_stitch.py`, `video_compose.py`, `tools/audio/audio_mixer.py` as candidates only after desired behavior and licensing are known. Keep this issue in Later; do not add an inferred editor to the current scope.

## Questions to resolve in this issue

- Is the first deliverable ordered clip export, automatic assembly or an editable timeline?
- How should dialogue, SFX, music, subtitles, transitions and alternative takes synchronize?
- What exports, revisions and error/recovery behavior are required?

## Acceptance evidence

- An agreed assembly journey defines inputs, editing controls, audio timing and export acceptance.
- A bounded reuse assessment identifies dependencies/licenses and UI/backend follow-ups.
- No implementation or tool import is claimed from this design record alone.

## Handoff

Link the design/implementation PR, decisions, changed-file provenance and demonstrated evidence. Record unresolved dependencies explicitly. Follow the authoritative plans; ask about a real contradiction instead of reintroducing legacy pages or changing agreed mode policies.

## Owner decision — 2026-10-09

First target: accepted clips ordered by screenplay, exported as one video, with optional audio tracks. See ../assembly.md. Do not reopen ordered export vs full timeline. Exact export settings, audio timing/mix and reuse/license decisions remain to be finalized before implementation.
