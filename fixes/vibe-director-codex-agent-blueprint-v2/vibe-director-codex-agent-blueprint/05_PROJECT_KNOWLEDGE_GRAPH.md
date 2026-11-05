# Project-specific knowledge graph and memory

## Goal
A loaded project should let the Director answer: What story are we telling? Which character image/voice is canonical? What was decided? Which clips exist and what defects remain? What tool work is in progress? What is safe to do next? This knowledge survives restarts, project switches and editor handoffs.

## Implement as a projection, not a second authority
Use the existing project-owned SQLite ledger + media catalogue + versioned story/source/editor records as truth. Create graph tables or materialized adjacency/projection keyed to existing asset/revision/job IDs. Include an event log and explicit rebuild/reconcile path. **Don't invent a new autonomous graph that silently overwrites existing records.** Text/vector retrieval may help recall; it must link back to provenance and current hashes.

## Node types
`Project`, `Conversation`, `Message`, `TaskPlan`, `Task`, `SkillVersion`, `CreativeBriefVersion`, `StoryRevision`, `Scene`, `Shot`, `StoryboardPanel`, `GenerationClip`, `Character`, `CharacterImage`, `VoiceSample`, `VoiceBinding`, `Location`, `WorldReference`, `Asset`, `PromptVersion`, `ReferenceManifest`, `Attempt`, `RenderJob`, `Take`, `QualityFinding`, `RetakeDecision`, `EditorSession`, `EditPlan`, `TimelineItem`, `Export`, `ExternalDelegation`, `ToolCapabilitySnapshot`, `UserDecision`.

## Edges
`PROJECT_HAS`, `BASED_ON`, `PART_OF`, `APPEARS_IN`, `LOCATED_IN`, `USES_VOICE`, `STYLED_BY`, `REFERENCE_FOR`, `GENERATED_BY`, `OUTPUT_OF`, `PRECEDES`, `CONTINUES_FROM`, `LAST_FRAME_OF`, `SELECTED_TAKE_FOR`, `DEFECT_IN`, `RETAKE_OF`, `REPAIRS`, `IN_EDITOR_SESSION`, `ASSEMBLED_AS`, `APPROVED_BY`, `BLOCKED_BY`, `DELEGATED_TO`, `REQUIRES_TOOL`, `SUPERSEDES`.

## Graph record invariants
- All graph nodes are owned by one project/workspace; cross-project reuse is an explicit referenced or copied asset with permission and provenance.
- Every graph fact carries `source_id`, `source_kind`, `created_at`, `observed_at`, `confidence` if inferred, and `valid_for_hash/version` where applicable.
- User-approved canonical facts outrank automatic inference. Conflicts are represented, not silently resolved.
- Stable `character_id`, `location_id`, `clip_id`, `asset_id`. `<Picture 1>` and `<audio1>` are **transient per-render labels**, not permanent IDs.
- Project changes use revision/expected-version CAS and event history; snapshots/portable saves contain or can regenerate the graph projection, chat, task logs and links to owned files.
- Don't store unbounded raw video bytes or credentials in graph; reference verified library assets. Indexed text is untrusted data, not commands.

## Context assembly before every agent step
Fetch (1) latest user intent and active task plan, (2) canonical story entities/visual refs, (3) relevant clip/end-state/source hashes, (4) selected creative brief/jackets, (5) recent decisions/defects, (6) tool and approval state. Summarize with citations/provenance IDs. Do **not** dump all history into every model call. Retrieve by graph neighborhood, version and recency; use semantic text retrieval as supplement.

## Tasks and snapshots
A plan may refer to a graph snapshot but must revalidate source hashes and tool capability before submitting each task. On restart, reconcile job IDs from existing ledgers; never mark a render done because a chat message said so. A failed QA finding and human rejection remain recoverable as versioned entities.

## Example continuity query
For `Scene5`, get `previous Scene4 selected take → verified last frame asset → mouse/lion master IDs → lion_voice_sample → net arrangement → required R2V reference manifest`. Validate model supports actual selected reference mode. If first-frame conditioning is only supported in a separate FFLF workflow, do not mislabel a normal R2V image as hard first-frame constraint.

## Migration strategy
Begin with projection tables + read API, not replacing underlying authored story graph. Backfill from recent project assets/jobs; graph status `unknown/unindexed` when provenance is incomplete. Dual-read and verify, preserve project Save/Load semantics. Project-specific event sourcing should be additive and reversible.
