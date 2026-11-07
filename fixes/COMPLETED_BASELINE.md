# Source-completed baseline — not a task queue

**Audited:** `vibe-director-current` commit `9180a01376a6eb254ef6c171f9d3977e4d388dfb`, 2026-11-07. This is static GitHub inspection and earlier reported test evidence; **not** a live user-project or current CI acceptance. Historical dated results were removed from the active docs tree; recover them via Git history if genuinely needed for debugging.

| Former cards | Source-level state | Do not confuse with |
| --- | --- | --- |
| Q01–Q08, R01/R02 | Implemented foundation: private media staging exclusion, approved MP3 + last-frame task jobs, safe skills/context discovery, shared chat, computer scope, task reconciliation/input supervision. | Full tool graph, real timed audio understanding or autonomous editing. |
| UX01–UX03 | Independently collapsible nav/Director/work panes; one persistent Director chat; Editor bridge and removal of duplicate Editor chat. | A native HyperFrames Studio editing GUI. |
| UX04 (parts) | Shared Director adapters for Story, Screenplay, prompt changes/learning, image prompt preparation, Video Create prompt, studio settings, ACE discussion; preserve accepted revisions and old history. | Every manual creator tool callable, or parity across all storyboard/3D/Media Prep routes. |
| UX05–UX08 (parts) | Flattened Image/Take canvases, compact output and shared work-surface improvements documented in latest active notes and source. | Perfect visual acceptance on every viewport or workflow. |
| MED01/02/03 (parts) | MediaSourcePicker typed destinations; several filters/date/name sorting; linked reuse and protection for existing shareable storage, project checkpoint handling. | A universal no-copy membership model, fully indexed cross-project search, or zero duplication of browsers. |
| Vibe Editor | Saved Editor project, ranges, revisions, style/clearance, plan JSON, FFmpeg/HyperFrames CPU renderer, output checks and export. | HyperFrames Studio GUI; transcript extraction/real gibberish detection; arbitrary AI edits of clip layers. |

Known source links: `backend/story_builder/services/agent_skills.py`; `agent_tools.py`; `agent_tasks.py`; `agent_conversation.py`; `agent_editor.py`; `vibe_editor_render.py`; `frontend/src/VibeEditorPage.tsx`; `MediaSourcePicker.tsx`. Use current tests/source rather than blanket “done” assumptions.

### Package deliberately retained

`fixes/vibe-director-codex-agent-blueprint-v2/vibe-director-codex-agent-blueprint/` looks archival but is **still a runtime source**: `agent_skills.py` resolves `skills/<name>/SKILL.md` and `shared/CONTRACT.md` there. Its older strategy, glossary, references and packaged assets are *not* the active task list. Do not delete/move the package without first changing and testing the registry and every affected skill.
