# Production UI — preserve working areas, modernize the flow

> **CURRENT IMPLEMENTATION OVERRIDE (2026-11-06):** Q01–Q08, shared skill/tool discovery, project chat, MP3 and last-frame tools are already implemented as bounded foundation work. Start with `fixes/CODE_REVIEW_2026-11-06.md`, `fixes/ACTIVE_FIXES_2026-11-06.md`, `fixes/UNIFIED_CHAT_AND_PANES.md`, and `fixes/CODEX_CHANGE_README_PROMPT.md` at the repository root. Do **not** rebuild the old first vertical slice. New requirement: only ONE persistent Director chat composer, including inside Vibe Editor; all THREE panes independently collapse and restore. Before deleting embedded page chats, migrate their actual tool/proposal/approval/recovery actions. Existing Media Prep operations and left navigation remain intact. The remainder of this blueprint is the long-term product vision; the new active guides take precedence for current implementation.

## Preserve exactly what the owner approved
Existing left sidebar categories/navigation and Media Prep pages/behavior are good. Preserve styling, palette, Media Prep audio tools and server APIs; avoid gratuitous refactoring. User can open any route directly. Home/project bar remains.

## New universal layout
- Left fixed/collapsible current navigation.
- Middle resizable project-scoped Director chat: conversation, plan cards, approvals, progress list, tool calls, artifacts, error/recovery. Users can switch to Editor specialist context without losing underlying project task.
- Right resizable interactive work surface: existing actual page (not screenshot), asset/library chooser, comic board, prompts, video create/take, editor/timeline, logs, optional third-party GUI. Work surface tracks context and reuses existing components.
- Small screens: conversation/work-surface switcher; retain unsaved drafts. Transparent state if no computer runtime connected.

## Production Type & Style becomes optional Creative Brief
Independent selectors: `Production Type` (movie/film/short/advertisement/educational...), `Visual Style` (anime, realistic, stylized 3D...), `Directing Language` (cinematic, static, handheld, energetic...). Add mood/tone/aspect/runtime and reference media. These choices add versioned *jacket guidance* applied selectively to skills. Film can be anime with cinematic camera: not competing options. Advanced custom type/style publishing is hidden behind an expand/control; defaults are skippable and never gate manual generation.

## Screenplay
Editable screenplay structured by scenes with dialogue and action. Right pane highlights scene; chat commands like "shorten the mouse dialogue" propose patches and apply after user says so. Show total runtime estimate and preview plan; can split into model-sized clips without changing source scene count. A new version does not mutate submitted jobs.

## Storyboard
Comic book page per scene: each visual panel shows generated/uploaded image plus dialogue and small action/timing. Scene description, character/location references and panel numbering. User can drag reorder, change text, regenerate one panel, choose frame from clip or create image. Panels are beats, not forced one-to-one clips. Export HTML/PDF if supported; no invented available PDF button. Prompt route can consume panel/clip selections. Fast default generates only needed representative images.

## Video Prompt Preparation (first-class screen)
At top: model/route/duration and explicit "Assets to attach" manifest with correct per-route roles and per-asset UI field instructions. Under it: timecoded action beats, physical motion/camera instructions, dialogue voice samples, soundscape, strict char count (<7000 for reviewed H3 contracts). Show what previous last frame means: true FFLF input vs *ordinary* R2V reference image. Show conflict before user submits. End-state/next-clip planning and "Extract last frame" button (existing `/api/video/jobs/{id}/continuity-frame`). User can edit prompt directly and skip prior stages.

## Generation and take review
Existing Generate and Current Take remain. Surface explicit blockers and recovery without disabling everything for stale screenplay advice; show job ID, capability checks, actual reference order, original/final quality. Toggle `LTX Refinement ON/OFF` implemented in backend (not visual-only). Result review includes visual/audio defect annotation and ``Retake / Edit this take / Accept``.

## Editor
Right pane mounts current Editor with real preview/media/timeline/style/export. Its chat has Director tool access and quality findings. Eventually optional HyperFrames Studio tab if validated. Unselected assets never silently enter an approved timeline.
