# Projects tool guide

Source-backed usage map, 2026-11-05. IDs below are glossary IDs for future routing, not currently registered model functions. Consult [API helpers](API_HELPERS.md) and [HTTP routes](HTTP_ROUTES.md) for exact source locations. Live readiness has not been exercised by this documentation task.

## project.manage — New / Load / Save project

**Choose when:** Create a project, reopen its work, save or switch to standalone tools.

**UI:** Global project bar

**Inputs:** New: title and parent folder; open: project folder; save: current project and browser memory.

**Outputs:** Project identity/folder, restored scoped state and saved project records.

**How to use:** Use ProjectController sequence: persist outgoing memory, save outgoing project where applicable, then new/open/select. Read current project before choosing ownership. Use /api/projects/current, /new, /open, /save, /select, /memory; check projects.py for exact body and validation.

**Source:** [ProjectController.tsx](../frontend/src/ProjectController.tsx), [projects.py](../backend/story_builder/services/projects.py)

## output.destination — Output folder selection and relink

**Choose when:** Choose where a tool publishes its results.

**UI:** Output folder controls in tools

**Inputs:** Tool ID, project/workspace ID, entered path or native folder selection, saved choice/grant.

**Outputs:** Validated output grant/preference; recovery location if previous folder disappeared.

**How to use:** POST /api/studio-tools/output-folder; /output-destination; /output-relink. Freeze destination into submitted jobs. Do not assume editing a path in chat has granted it.

**Source:** [OutputDestination.tsx](../frontend/src/OutputDestination.tsx), [output_destinations.py](../backend/story_builder/services/output_destinations.py), [studio_tools_api.py](../backend/story_builder/services/studio_tools_api.py)
