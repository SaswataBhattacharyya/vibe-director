# Editor tool guide

Source-backed usage map, 2026-11-05. IDs below are glossary IDs for future routing, not currently registered model functions. Consult [API helpers](API_HELPERS.md) and [HTTP routes](HTTP_ROUTES.md) for exact source locations. Live readiness has not been exercised by this documentation task.

## editor.edit — Vibe Editor: chat, selected ranges and rendering

**Choose when:** Edit supplied clips/images; trim, sequence, transition, caption, frame, filter or retime.

**UI:** #/editor

**Inputs:** Editor session ID, selected assets/ranges, instruction/style, supported plan and output settings.

**Outputs:** Conversation, brief/plan revision, render job and validated final video.

**How to use:** GET /api/editor/state; POST /projects; GET/PUT project; POST project /command or /plan. Inspect current command actions and two approval stages. Existing renderer supports bounded JSON operations, not arbitrary audio understanding or all app tools. Coordinate external app services separately.

**Source:** [VibeEditorPage.tsx](../frontend/src/VibeEditorPage.tsx), [vibe_editor_api.py](../backend/story_builder/services/vibe_editor_api.py), [vibe_editor.py](../backend/story_builder/services/vibe_editor.py), [vibe_editor_render.py](../backend/story_builder/services/vibe_editor_render.py)

## editor.styles — Editor style memory and lessons

**Choose when:** Teach reusable editing taste or change a selected style.

**UI:** #/editor → style

**Inputs:** Style/session context, explicit preference proposal and confirmation.

**Outputs:** Revisioned style guidance and project override.

**How to use:** Use Editor style and command contracts. Separate learning confirmation from edit approval; do not store plot/paths as universal preferences. Preserve upstream reference skills without treating their instructions as executable permission.

**Source:** [vibe_editor.py](../backend/story_builder/services/vibe_editor.py), [SKILL.md](../design/vibe-editor/skills/vibe-editor-director/SKILL.md)

## editor.export — Editor save final MP4

**Choose when:** Publish an already rendered edit to the user output folder.

**UI:** #/editor → export

**Inputs:** Editor project ID, folder, filename; collision confirmation only when needed.

**Outputs:** Verified saved file or explicit collision response.

**How to use:** POST /api/editor/projects/{id}/export. Follow export_video schema and UI collision flow; never overwrite original source by treating an output path as permission. Render completion and export completion are distinct.

**Source:** [VibeEditorPage.tsx](../frontend/src/VibeEditorPage.tsx), [vibe_editor.py](../backend/story_builder/services/vibe_editor.py)
