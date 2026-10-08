# [D3] Design optional character/world/frame creation and voice binding

Status: published as [GitHub issue #7](https://github.com/SaswataBhattacharyya/vibe-director/issues/7). Type: Design.

**Proposed lead/reviewer:** Ashu proposes; Saswata reviews. These are proposals, not an assignment already accepted by Ashu.
**Dependencies:** D1; G2 asset contracts.
**Read first:** [current plans](../README.md), [issue working rules](../issue_backlog.md), then char_world.md, video_gen.md, ux_shared.md in `plans/`. Paths below are relative to the named reference source, except explicitly absolute paths.

## Outcome and scope

Design clean character-image, world-image and clip-frame screens, followed by character-to-voice binding. Show prompts and exact references, editable with annotation/chat microedits. Assets can be skipped where optional. Frames carry scene/shot/clip and first/last roles. Voice rows show character image/description plus searchable voice dropdown; multiple characters may share one file.

Reference Story Builder `pages/ProductionWorkspace.tsx`, `pages/AudioStudio.tsx`, `components/FileUpload.tsx`, `services/production_assets.py`, `production_image_workflows.py`, `production_voice_binding.py`.

## Questions to resolve in this issue

- Should these be separate pages or focused views within one assets workspace while preserving the requested clean divisions?
- How do variant selection, skip, recommended refs and generation/retake states appear?
- How are reused voice files and missing bindings made clear without duplicating files?

## Acceptance evidence

- Prototype includes skip, first/last frame metadata, shared voice binding and prompt/reference annotation.
- Manual recommended image/voice refs are shown first but remain unselected until chosen.
- Model prompt budgets and unavailable workflows have explicit states.
- UI requirements/API needs feed bounded implementation tickets rather than recreating the old workspace wholesale.

## Handoff

Link the design/implementation PR, decisions, changed-file provenance and demonstrated evidence. Record unresolved dependencies explicitly. Follow the authoritative plans; ask about a real contradiction instead of reintroducing legacy pages or changing agreed mode policies.
