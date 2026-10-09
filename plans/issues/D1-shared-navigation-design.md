# [D1] Design shared navigation for story-led and isolated creation

Status: published as [GitHub issue #3](https://github.com/SaswataBhattacharyya/vibe-director/issues/3). Type: Design.

**Proposed lead/reviewer:** Ashu proposes; Saswata reviews. These are proposals, not an assignment already accepted by Ashu.
**Dependencies:** Read G2 draft contracts; can design before backend exists.
**Read first:** [current plans](../README.md), [issue working rules](../issue_backlog.md), then ux_shared.md, automation.md, integration.md in `plans/`. Paths below are relative to the named reference source, except explicitly absolute paths.

## Outcome and scope

Design the shell, route map and saved-context behavior for one product. Regular creation uses story → readable screenplay → Automation & Parameters → shared asset/video screens. Isolated creation enters those same screens directly without inventing a story or screenplay. Media Prep is a separate auxiliary area and Status remains global. Production V2, Generate, old Automation and Manual Director cease to be separate destinations.

Reference Story Builder `frontend/app/src/App.tsx`, `components/AppShell.tsx`, `pages/ProductionWorkspace.tsx`, `lib/production-navigation.ts`. Reuse useful components; older page topology is not the specification.

## Questions to resolve in this issue

- What navigation names and grouping make regular creation, isolated creation and Media Prep immediately discoverable?
- How does a user switch project/task, resume unfinished work and see unsaved changes?
- What appears on mobile, and what happens to context when an isolated asset is later linked to a story?

## Acceptance evidence

- Wireframes or a clickable prototype show regular entry, isolated video/image entry, saved context and recovery after reload.
- Route map identifies shared screens and required/optional context; no duplicate generation implementation.
- Loading, empty, unavailable and failure states are designed.
- Design PR records decisions, API needs and bounded UI implementation follow-ups. This design issue does not claim the app is implemented.

## Handoff

Link the design/implementation PR, decisions, changed-file provenance and demonstrated evidence. Record unresolved dependencies explicitly. Follow the authoritative plans; ask about a real contradiction instead of reintroducing legacy pages or changing agreed mode policies.


## Current implementation and Ashu's next work — 2026-10-08

Ashu owns UI design; the current engineering UI is provisional. Saswata reviews. Design ownership changes only on Saswata's explicit instruction. The project goal is paused; this handoff publishes existing work and does not restart implementation.

Current implementation: a provisional single-screen sidebar and isolated Video form exist in `frontend/src/App.tsx` and `frontend/src/style.css`; Story, Assets and Media are disabled placeholders. There is no regular journey, project switcher, or accepted routing design yet. Ashu should propose navigation, route/context mapping, responsive shell, unsaved-state and resume behavior; then reshape the provisional shell without losing the saved job/draft behavior.

Start from branch `issue-2-isolated-t2v-reuse` / [draft PR #15](https://github.com/SaswataBhattacharyya/vibe-director/pull/15), rather than assuming main has the implementation. Read [Ashu's UI handoff](https://github.com/SaswataBhattacharyya/vibe-director/blob/issue-2-isolated-t2v-reuse/plans/ASHU_UI_HANDOFF.md) for exact files, API behavior, preserved recovery/GPU invariants and focused evidence. This issue remains open; provisional code and passing mocks are not design acceptance.

For Codex/Claude: inspect those files and the linked stage plan; answer the issue's design questions, propose annotated layouts/states and API needs, then make bounded UI changes in a separate PR. Preserve saved requests, explicit generation and recovery behavior. Use mocked requests for UI verification; do not launch live generation or rerun the broad legacy test suite.

## Owner-approved Ashu UI adaptation — 2026-10-09

Accepted and adapted: shared shell, route map, mobile navigation and all three themes. Design issue #3 can close; real task-scoped drafts, context switching, resume and explicit linking are tracked in #18. This does not claim whole-product implementation. Read plans/implementation/ashu_ui_adaptation.md for changed files and focused evidence. Future UI work uses the shared shell and all three themes; earlier pending acceptance/provisional-shell notes are historical.
