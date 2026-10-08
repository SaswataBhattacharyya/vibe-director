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
