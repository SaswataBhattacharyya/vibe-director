# [D4] Design three video forms, reference collation and take review

Status: local issue draft; not published. Type: Design.

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
