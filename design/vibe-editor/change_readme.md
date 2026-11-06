# Vibe Editor — remaining integration, not a renderer rewrite

Read [current code review](../../fixes/CODE_REVIEW_2026-11-06.md), [UX migration spec](../../fixes/UNIFIED_CHAT_AND_PANES.md), [active UX02/UX03 tasks](../../fixes/ACTIVE_FIXES_2026-11-06.md). **Q08 MP3-to-Editor handoff is implemented and reported tested.** Do not repeat it.

## Confirmed defect
`frontend/src/VibeEditorPage.tsx:138–153` renders a second Editor chat log/composer and an `EditorWorkspace` nested split in the **right** work area. The new persistent `DirectorConversation` already occupies the middle column; screenshot confirms redundancy.

## Exact safe migration order
1. `VibeEditorPage.submit` currently calls `POST /api/editor/projects/{id}/command` with `action:'chat'`, `revision`, `text`. **This is the only current route to initiate an Editor creative brief from its UI.** Do not simply delete it.
2. Add a shared tool/action adapter `editor.prepare_brief` that resolves real `workspace_id`, separate `editor_session_id`, selected in/out ranges, expected Editor revision and text; validates session ownership and selection; invokes existing `vibe_editor.command`. The center chat becomes the authorizing/request surface.
3. Keep `editor.command` transitions: brief → clearance 1 → selected media/plan → clearance 2 → trusted HyperFrames/FFmpeg render. Proposal/clearance action cards may live in the right Editor work area while central chat is the only freeform composer. One approval must not silently substitute for another.
4. Preserve `project.messages` as **read-only legacy session history** (collapsed details), `project.revisions`, `pending`, style rules, saved selections and exact media ranges.
5. After real central-chat Editor requests succeed, remove old `editor-messages` as primary chat, old `editor-composer`, second model picker/send and nested `<EditorWorkspace name="editor">`. Move attach/browse/style/session operations into existing right tabs. Do **not** remove `EditorWorkspace.tsx` (used elsewhere) or Editor backend services.
6. Add persistent session context to `DirectorRuntime`; current `surface:'editor'` has no session ID/selected ranges. Server must reject wrong project, stale session/revision and unselected media.
7. Regression: new edit → brief → clarification/clearance → media plan → final clearance → trusted render; saved sessions, pause/stop/retry and output/export preserved. No automatic render from asking in chat.

## Later
Evidence-backed QA, retakes, project graph, multi-clip assembly and optional HyperFrames Studio/OpenMontage/Backlot adapters remain separate phases. Model text alone is not audiovisual inspection. The old `vibe_editor.run_job` JSON planner's “Do not run tools” protects the renderer; do not remove it to enable the new agent, which operates through shared typed gateway.

No editing engine or Media Prep rewrites are authorized by this guide.
