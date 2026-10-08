# [D4] Design three video forms, reference collation and take review

Status: published as [GitHub issue #4](https://github.com/SaswataBhattacharyya/vibe-director/issues/4). Type: Design.

**Proposed lead/reviewer:** Ashu proposes; Saswata reviews. These are proposals, not an assignment already accepted by Ashu.
**Dependencies:** D1; G2 workflow contracts.
**Read first:** [current plans](../README.md), [issue working rules](../issue_backlog.md), then video_gen.md, char_world.md, ux_shared.md in `plans/`. Paths below are relative to the named reference source, except explicitly absolute paths.

## Outcome and scope

Design workflow selection → correct input form → job progress → clip and full submitted request → Next/Retake. T2V has prompt/settings. FFLF has role-filtered first and last frame selectors plus upload/drop/paste. R2V has multiple image/video/audio selectors with graph-backed limits, exact labels, per-reference user intent, search/sort/category controls and prompt Collate with clarifying chat. Prompts support precise passage annotation.

Inspect Story Builder `pages/MediaComposer.tsx`, `pages/Generate.tsx`, `pages/VideoRepertoire.tsx`, `services/minimax_h3_graph_compiler.py`. OpenMontage Backlot is a visibility reference, not an interactive replacement.

## Questions to resolve in this issue

- How can users understand reference numbering, intent and the final combined prompt without visual overload?
- How does collation flag ambiguity and invalid or over-budget requests before generation?
- How do the keep/delete question, preserved inputs and alternate takes appear during retake?
- How are duration, quality and workflow-specific parameters presented?

## Acceptance evidence

- Prototype covers all three forms, multiple refs, clipboard image input, clarification and exact request review.
- Final MiniMax prompt is strictly below 7,000 characters with visible validation; model-specific image limits use declared units.
- Retake retains every input; keep/delete is explicit. Offline/failed/uncertain jobs retain context.
- Frame pickers exclude character/world assets; R2V image pickers can show all eligible imagery.

## Handoff

Link the design/implementation PR, decisions, changed-file provenance and demonstrated evidence. Record unresolved dependencies explicitly. Follow the authoritative plans; ask about a real contradiction instead of reintroducing legacy pages or changing agreed mode policies.


## Current implementation and Ashu's next work — 2026-10-08

Ashu owns UI design; the current engineering UI is provisional. Saswata reviews. Design ownership changes only on Saswata's explicit instruction. The project goal is paused; this handoff publishes existing work and does not restart implementation.

Current implementation: editable T2V prompt, duration/quality, readiness, Generate, progress, frozen submitted request, review/accept, history and draft-only retake exist in `frontend/src/App.tsx`; API mapping is in `frontend/src/lib/video-api.ts`. FFLF/R2V, reference selectors/collation, real AI microedit and reference-aware deletion remain unimplemented. Ashu should redesign the existing T2V interaction and design the two additional forms, precise annotation, reference intent/collation chat, review, mobile and error states. Do not imply that candidate files are already deleted or unavailable workflows work.

Start from branch `issue-2-isolated-t2v-reuse` / [draft PR #15](https://github.com/SaswataBhattacharyya/vibe-director/pull/15), rather than assuming main has the implementation. Read [Ashu's UI handoff](https://github.com/SaswataBhattacharyya/vibe-director/blob/issue-2-isolated-t2v-reuse/plans/ASHU_UI_HANDOFF.md) for exact files, API behavior, preserved recovery/GPU invariants and focused evidence. This issue remains open; provisional code and passing mocks are not design acceptance.

For Codex/Claude: inspect those files and the linked stage plan; answer the issue's design questions, propose annotated layouts/states and API needs, then make bounded UI changes in a separate PR. Preserve saved requests, explicit generation and recovery behavior. Use mocked requests for UI verification; do not launch live generation or rerun the broad legacy test suite.