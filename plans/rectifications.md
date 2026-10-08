# Rectification: use one story-to-screenplay preparation path

**Decision:** The current screenplay-first plans are authoritative. Reuse Production V2 source chunking, stable identities, validation and revision principles for one preparation path; adapt existing code to these product decisions. The earlier migration plan is historical evidence, not a competing product specification.

## Why this rectification is needed

Story Builder contains two ways to turn story material into production plans. Presenting both as active ways to create scenes, sub-scenes/shots, and dialogue would make the product harder to understand and create competing records. We should retain one user journey, one set of concepts, and one source of truth.

## Difference between the two existing methods

| Area | Legacy `/story` flow | Production V2 flow | Product decision |
|---|---|---|---|
| **Preparation sequence** | Generates separate artifacts in order: story → characters → scenes → sub-scenes → dialogue → image jobs. Each stage consumes earlier JSON artifacts. | Builds a versioned story canon, then creates linked production text stages such as scenes, dialogue, visual briefs, and shot plans. | Reuse V2 lineage and validation principles; adapt the sequence/contracts to the current screenplay-first product plan. |
| **Use of original story** | Original input is embedded in the story artifact, which is forwarded to later stages. There is no explicit source-chunk coverage proof at each legacy stage. | Splits the exact source into contiguous chunks, tracks source facts and inferred additions, and uses an accepted story revision as the basis for downstream work. Scene outlines link back to source chunks. | Preserve V2 source lineage, accepted revisions, and coverage validation. |
| **Scene planning** | Scene plan is generated as a JSON artifact with a title, summary, location, time, continuity notes, characters, and background prompt. | Scene outline is planned from the expanded story and chunk index. Chunks are context windows, not scene boundaries; scene boundaries follow dramatic action and location/time changes. Stable IDs and source links are validated. | Plan scenes using V2’s story-aware, source-linked approach. |
| **Sub-scenes and cuts/shots** | “Sub-scenes” are separate cut-level objects with camera, blocking, action, image prompts, and frame briefs. The label can be confused with a dramatic scene. | Uses production units and shot plans linked to scenes and story chunks. Shot planning is a downstream stage. | Use **scene → ordered shots → duration-bounded clips**, with dramatic beats and dialogue linked where relevant. A cut is a transition between shots; beats may span shots. See `GLOSSARY.md` for legacy sub-scene interpretation. |
| **Dialogue** | A dialogue artifact is generated after sub-scenes, while sub-scenes can already carry dialogue text. This can duplicate dialogue and allow records to drift. | Dialogue is its own linked production stage, generated from accepted story canon and explicit units/character identities. | Keep one canonical dialogue record authored in the readable screenplay; derive downstream dialogue plans from it using adapted V2 lineage contracts. |
| **Review and revisions** | The legacy page presents generate/edit/save JSON cards, without the same accepted-canon revision gate described in V2. | Story canon has reviewable revisions; downstream text generation requires an accepted revision and checks source freshness. Stage revisions preserve lineage. | Reuse lineage/revision tracking; user-visible advancement follows the Manual/Semi/Full policy in `automation.md`. |
| **User-facing representation** | Exposes machine-oriented JSON text areas for scenes, sub-scenes, and dialogue. | Has structured, revisioned production stages, but still needs the planned human-readable screenplay view. | Make readable structured screenplay authoring authoritative; derive/adapt V2 records from it. JSON remains an optional technical/debug view. |

## Canonical Vibe Director journey

```text
Original story
  → source chunks and story canon
  → story review and acceptance
  → readable screenplay draft and revision
  → accepted screenplay records
  → compiled scenes, authored shots, linked beats and canonical dialogue
  → derived visual briefs and duration-bounded clip plans
  → image, video, and audio generation
```

The screenplay layer described in `screenplay.md` is part of the V2 journey. It is not a separate legacy path. It should use V2 story revisions, source chunk references, stable IDs, and revision lineage. Users should read and edit the screenplay in normal hierarchical text; the system should store and validate structured records behind that view.

## Migration and reuse direction

- Reuse Production V2 source/revision principles and useful implementation logic behind the current canonical journey; its separate page and prior controller UX are retired.
- Do not build a second set of legacy-style scene/sub-scene/dialogue generators or a second product journey.
- Reuse legacy artifacts only as migration inputs, compatibility data, or examples where useful. They must be translated into V2-linked records before entering the canonical workflow, with any missing source links or ambiguous dialogue clearly marked.
- Prefer a read-only legacy screenplay renderer during transition if old projects need to be inspected. Do not let legacy artifacts become an alternative authoring path.
- Use one vocabulary in the product: **story canon → screenplay → scenes / ordered shots / duration-bounded clips**, with linked beats, dialogue and direction. Avoid “sub-scene” in new UX unless a precise product definition is adopted.
- Keep generation prompts and JSON schemas behind the screenplay experience. Provide technical inspection only as an optional advanced view.

## Acceptance criteria for this decision

1. A new project has one story-to-production journey based on V2.
2. Downstream records identify the current story/screenplay revisions used. Wrapper policy controls acceptance and advancement; subsequent planners derive rather than independently reinvent authored scenes, shots and dialogue.
3. Screenplay scenes and beats retain source chunk references, stable identities, and revision history.
4. Scene/shot/clip numbering is for display; stable IDs remain valid through edits and reordering.
5. Dialogue has one canonical editable source and does not drift between scene/shot and dialogue artifacts.
6. Users can inspect the complete screenplay in a readable hierarchy before approving detailed production plans.
7. Legacy data can be migrated or viewed without creating a competing V1 authoring flow.

## Existing source references

This decision is based on the two code paths reviewed in Story Builder:

- Legacy prompt contracts: `/home/riki/web_dev/story_builder/services/story_pipeline.py`
- Legacy page and artifact order: `/home/riki/web_dev/story_builder/frontend/app/src/pages/StoryBuilder.tsx`
- V2 source chunking/canon: `/home/riki/web_dev/story_builder/services/chunked_generation.py`
- V2 scene outline and production text planning: `/home/riki/web_dev/story_builder/services/production_text_controller.py`
- V2 routes and revision gates: `/home/riki/web_dev/story_builder/api/main.py`

This is a product direction for future work, not a claim that the V2 user interface or screenplay editor is already complete.

## Current decisions that supersede earlier planning

- `README.md` identifies the authoritative current plans; older `migration_plan/` UX, stage order, mode/route matrix and controller policies do not govern new behavior.
- `GLOSSARY.md` defines scene, beat, shot, cut, clip, take and override terminology.
- `screenplay.md` governs authoring, compilation and screenplay-versus-take direction changes.
- `char_world.md` makes visual preparation skippable and makes character/voice bindings recommended video references rather than automatic selections.
- `video_gen.md` governs model-specific prompt adaptation, duration/output controls, limits, reference preparation and review.
- `automation.md` defines the wrappers, including story-only Full mode with a new T2V start for each scene and previous-clip R2V continuation within it.

## New navigation and scheduling rectification

Remove separate Production V2, Generate, old Automation Studio and Manual Director pages from the new product. Shared generation screens support direct isolated entry with no story requirement. In the regular path, Automation & Parameters sits after the readable screenplay and before workflow/model prompt preparation. Semi exposes exactly the five specified downstream stage checkboxes; automatic video has fixed initial quality and optional Director-selected duration. Retain Status as the backend/workflow/prompt-limit catalogue.


## Integration and shared UX amendments

Use `ux_shared.md` for persistent context/next task, conditional readiness, prose-first creative controls, offline editing/save and native review/recovery. Preserve data compatibility, validation, lineage and job recovery while adapting historical human-approval gates to the explicitly agreed wrapper policies.

`integration.md` defines selective extraction from existing Story Builder and evaluation of OpenMontage components. One screenplay authority, asset store, capability contract and durable execution service govern the product. OpenMontage's file-based pipelines and the StudioDirector mockup do not reinstate retired pages or override isolated entry.
