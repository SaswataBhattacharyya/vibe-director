# Screenplay-first story workspace for Story Builder

**Status:** Current product plan; planned behavior, not a claim of implementation. The decisions in `README.md`, `GLOSSARY.md`, and `automation.md` govern this document.  
**Decision:** Merge the current Story Builder and Story Canvas into one story workspace. Use Production V2's source tracking, revision, chunking, and validation principles. Make the human-readable screenplay the canonical authored plan. Only after screenplay approval should the system compile it into scene, cut/shot, dialogue, and generation JSON for production prompts.

## 1. Product problem and direction

The current Story Builder and Story Canvas divide writing, revision, analysis, and production planning across two pages. Story Builder is centered on a pasted story and machine-oriented JSON artifact cards. Story Canvas is a separate novel editor with revision history, analysis, and a basic screenplay outline. Keeping both as separate destinations risks confusion and diverging copies of the story.

Story Builder should present one continuous story-making experience:

- Write or paste the story, of any practical length.
- Develop it through a Codex-powered conversational collaborator that makes requested edits to the actual story, with review and revision history.
- Maintain a knowledge graph of story facts, entities, relationships, events, time, and continuity, linked to the text that supports them.
- Turn the accepted story into a readable screenplay with numbered scenes, action, dialogue, and nested beats/cuts.
- After screenplay approval, compile its content into validated structured records and stage-specific JSON/prompts for production.

The user should not have to edit JSON to create or understand the story, screenplay, scenes, cuts, or dialogue. JSON is an internal interface between validated stages and generation systems, with an optional technical/debug view for inspection.

## 2. One merged customer journey

```text
Story workspace
  ├─ write / paste / import story (no arbitrary product length limit)
  ├─ Codex collaborator chat: discuss, propose, and apply requested story edits
  ├─ versioned story revisions + source-linked knowledge graph
  └─ story analysis and continuity review
          ↓
Accepted story revision and graph snapshot
          ↓
Readable, editable screenplay: scenes with beats, ordered shots, dialogue/action, and direction attached inline; clips are duration-bounded render units linked to shots
          ↓
Human or configured Director review and acceptance
          ↓
Validated scene / shot / dialogue / audio records
          ↓
Automation & Parameters (Assisted manual / Fully automated; confirm settings)
          ↓
Workflow-specific prompt preparation and generation
```

Assisted manual and Fully automated use this same journey; see `automation.md`. Assisted manual exposes five automation checkboxes: none means manual Generate/Next, some means mixed operation, and all means automatic asset preparation plus video. Fully automated skips image preparation and uses the style-aware T2V/R2V continuation route. Both record the same screenplay context; no extra Manual mode is shown.

## 3. Unified story workspace

Merge the useful roles of the two existing pages instead of keeping two separate products:

- One editor for writing, pasting, and importing story text, with project title and autosaved draft state.
- Revision history with compare, restore, and clear parent/child lineage.
- Analysis for loose ends, contradictions, chronology, character motivation, and continuity, shown as actionable findings linked to relevant passages. These are suggestions, not automatic changes.
- A Codex collaborator chat for natural-language instructions such as “make the sister’s motive clearer in the station scene, but preserve the reveal.” The collaborator should inspect relevant story and graph context, show the proposed change/diff, and apply it as a new revision only after the user accepts it. It should also be able to make a direct edit when the user's instruction is explicit, with a visible undo/revision path.
- Users can select a passage or refer to characters, scenes, or events in chat. The assistant should preserve unrelated text, explain conflicts with established facts, and ask only when a material ambiguity cannot be resolved safely.
- Remove the current fake focused-edit behavior that inserts `[Requested edit: …]` into the story. An edit action must change the story text itself or remain a clearly labeled unapplied suggestion.
- Retain narrator, style, and directing preferences as project settings that guide the screenplay and production stages. Do not confuse these preferences with story facts.

### Long-story handling

Do not impose an arbitrary maximum story length as a product rule. Support stories that grow over time, subject to transparent technical and operational limits where storage or a particular provider requires them. Do not silently truncate.

Use V2-style exact, contiguous source chunking for ingestion and analysis. Track chunk boundaries and hashes, process in bounded batches, and maintain a complete ordered source index. For chat and generation, retrieve the relevant passages, graph neighborhood, accepted canon, and continuity summaries; fetch additional chunks when the requested edit or scene needs broader context. For operations that must consider the whole story, run chunked/map-reduce analysis with a final synthesis pass. Always show when a task used selected context rather than the whole story, and allow the user to request a full-story pass.

A story edit creates a new revision and refreshes only affected graph facts plus dependent summaries, while retaining a way to rebuild and verify the full graph against the full revision. The system must not represent a partial-context answer as if it considered every part of a very long story.

## 4. Story knowledge graph

Maintain a project knowledge graph as a living, queryable model of the complete story. It complements the screenplay and source text; it does not replace either one.

### Core node types

- Characters, aliases, groups, creatures, and roles.
- Locations, organizations, objects, and other important entities.
- Events and actions, including goals, outcomes, and causal dependencies.
- Time points, durations, ordering constraints, and flashback/flash-forward relations.
- Story revisions, source chunks, screenplay scenes, beats, shots, clip plans, and dialogue lines.
- Open questions, mysteries, inferred details, and unresolved continuity issues.

### Core relationships

Examples include `knows`, `related_to`, `wants`, `opposes`, `located_at`, `owns`, `participates_in`, `causes`, `before/after`, `reveals`, `contradicts`, `appears_in`, and `supported_by_source`. Relations should be typed, directional where appropriate, and have confidence/status when uncertain.

### Provenance and update rules

- Every asserted fact or relation links to exact source text spans/chunk IDs and the story revision where it was found.
- Mark claims as source-supported, inferred, user-authored, or unresolved; never silently promote an inference to a source fact.
- Keep aliases and identity resolution explicit so a renamed character does not create accidental duplicates.
- Record changes by revision. A graph snapshot used to create a screenplay must be identifiable and reproducible.
- On edits, detect likely affected facts and relationships, update them, and re-run relevant contradiction and continuity checks. Preserve the prior graph snapshot for comparison and rollback.
- Let users inspect, correct, merge, or split graph entities and see the supporting passages. Avoid forcing users to work in a graph visualization; provide it as a navigable story bible and relationship/timeline view.

The graph gives chat and screenplay planning a compact way to retrieve connected context across a long story, while source links let users verify why the system believes a fact.

## 5. Human-readable screenplay hierarchy

The screenplay is the canonical, writer-facing plan between story development and production JSON. It should be editable as readable structured content, not a single opaque text blob and not a JSON textarea.

### Suggested structure

- **Project header:** title, screenplay revision, source story revision, selected style/narrator settings, and graph snapshot.
- **Scene 1 — The Case Against Arjun**
  - Slugline, for example `INT. KOLKATA SESSIONS COURT — DAY`.
  - Optional planning note: purpose and dramatic turn.
  - Readable present-tense action.
  - Dialogue blocks: character cue, optional parenthetical/delivery, line, and timing/pause cues where needed.
  - Sound/music cues attached to the relevant beat.
  - Optional **Beat** and **Shot** details for dramatic progression, camera, blocking, and visual action; these can be collapsed while writing. A cut is a transition between shots. A render clip is a duration-bounded part of a shot, not another dramatic scene.
  - **Direction fields integrated in the relevant screenplay content**, rather than a separate directing stage:
    - Project-level defaults (visual language, palette, camera approach, sound identity, music direction) appear as screenplay settings and can be overridden in a scene.
    - Scene-level fields hold dramatic mood arc, lighting/time/weather continuity, ambience, and music cues/transitions.
    - Beat fields hold performance intention, blocking/action, and sound effects tied to that moment; beats can span shots and shots can span beats.
    - Shot fields hold framing, lens or equivalent camera intent, angle, movement, focus, composition, shot-specific lighting, and transition to the next shot.
    - Dialogue blocks hold speaker, line, delivery/performance notes, timing, pauses, and relevant sound/music cues.
  - Source/graph references and inferred-detail markers available on demand.
- **Scene 2**, etc., in dramatic order.

Illustrative format:

```text
SCENE 1 — THE COURTROOM
INT. SESSIONS COURT — DAY

Arjun stands before the bench. The prosecution lays out the case against him.

SHOT 1.1 — WIDE ESTABLISHING SHOT
The judge sits above the crowded courtroom. Arjun stands in the accused area.

KABIR
(low, to Arjun)
We challenge the timeline first.

[PAUSE: 1s]

CUT TO:
SHOT 1.2 — CLOSE ON ARJUN
He notices the prosecutor watching him.
```

Use the vocabulary in `GLOSSARY.md`: a scene is a dramatic/location/time unit; a beat is a meaningful action or dialogue moment; a shot is a planned continuous camera view; a cut is a transition between shots; a clip is one duration-bounded generation unit; a take is one generated attempt at that clip. Beats and shots overlap rather than forming a rigid beat → shot tree. Display Scene 1 / Shot 1.1 / Clip 1.1.1, with stable IDs underneath. Interpret legacy “sub-scene” labels during migration rather than creating a second authoring object. Changing camera angle creates a new shot where appropriate, not a new scene. Dialogue has one canonical record and appears wherever relevant in the screenplay; it must not be duplicated as separately editable conflicting text in a shot and a dialogue artifact. Mood can evolve across a scene; lighting can be set at scene level with shot-level changes; camera action is attached to shots; and sound effects/music are attached to the beat, shot, or dialogue cue where they occur. These are all edited in context as part of the screenplay hierarchy, not in a separate pass or detached set of cards.

Visible numbering is for readers. Internal scene, beat, shot, character, dialogue, and location IDs remain stable through edits and reordering.

## 6. From screenplay to production JSON

The approved/current screenplay is the canonical source for production breakdown. Wrapper policy determines when a draft becomes the usable production revision. Scene, shot, dialogue and direction records are compiled from it. Visual briefs and clip plans derive from those decisions; any missing creative decision is completed in the readable screenplay before use. Downstream planners may split an existing shot into duration-bounded clips, with source coverage retained, but cannot independently rewrite dialogue, reorder story events or invent a competing shot plan.

1. The writer/Director edits direction in context inside the screenplay: project defaults, scene mood and lighting, shot camera/action, dialogue delivery, and beat/shot sound and music cues. Each field belongs to its scene, shot, dialogue block, or cue and is visible while reading that content.
2. Compile the accepted screenplay revision and graph snapshot into normalized internal records: scenes, beats, shots, clip plans, dialogue, visual direction, sound/music cues, character/location references, and source links.
3. Validate hierarchy, stable identities, scene order, dialogue speakers, timing values, continuity, source coverage, graph conflicts, and all references.
4. Report omissions, inferred content, unresolved graph facts, unsupported locations/characters, and compilation warnings in human language. Let the user correct the screenplay or use chat to make an edit, then recompile.
5. Create stage-specific JSON payloads and prompts from the validated records. Scene JSON comes from screenplay scenes; shot JSON includes inline camera/action/lighting/mood; dialogue and audio JSON derive from canonical dialogue and cues. Visual briefs and render prompts are derived from the accepted screenplay and its inline direction, plus approved references and style settings.
6. Store each compiled artifact with screenplay revision ID, graph snapshot ID, source hash, compiler/schema version, and parent stage IDs. Recompiling after an edit produces a new revision and marks dependent plans stale; it must not overwrite approved prior outputs silently.
7. Provide an optional technical view to inspect generated JSON and prompt inputs for debugging. Normal users stay in the readable screenplay/workspace view.

Generation models may help draft or enrich the screenplay and fill defined production fields, but they must work within the accepted screenplay structure, cite their source/graph context, and pass validators. They should not independently reinterpret the entire story to create a competing scene order after screenplay approval.

## 7. Revision, source, and quality rules

- Keep the original imported/pasted story intact as a source revision. Editing produces a new revision; do not overwrite source evidence.
- Every screenplay revision identifies its parent story revision and graph snapshot. Every production JSON artifact identifies its screenplay parent.
- Preserve major source events, causal order, motivations, and ending unless the user explicitly requests a rewrite. Show proposed omissions/additions and their evidence.
- Divide the story into chunks for processing only; chunks are not scenes. Determine scene boundaries by dramatic action, location, and time changes.
- Maintain source-to-screenplay coverage at event/beat level: represented, intentionally omitted, inferred, or unresolved. A coverage score alone does not establish faithfulness.
- Allow scene-level edits and bind generation to a clearly identified usable screenplay revision. In Assisted manual, advancement follows the configured manual/automatic step; Fully automated records the revision it automatically used without waiting for a separate human acceptance click.
- If story source changes after a screenplay is accepted, flag the screenplay and dependent production plans as stale; offer reconciliation rather than silently reusing mismatched outputs.
- Make revision diffs, undo/restore, validation findings, and approval status easy to find.

## 8. Suggested implementation boundaries

These are product responsibilities, not endpoint names already present:

- **Unified story workspace:** replaces separate Story Builder and Story Canvas navigation; owns story text, settings, chat, revision history, analysis, graph exploration, and screenplay authoring.
- **Story collaborator service:** chat interface with access to authorized project revisions and graph context; produces grounded edit proposals/diffs and applies accepted changes as new revisions.
- **Long-story ingestion/context service:** exact chunk index, source span map, hashes, retrieval, bounded full-story operations, and no silent truncation.
- **Knowledge graph service:** versioned entities/relations, provenance, identity resolution, graph snapshotting, and incremental plus full consistency checks.
- **Screenplay authoring service:** drafts and revisions the readable hierarchical screenplay from an accepted story revision and graph snapshot.
- **Screenplay editor:** presents scene, beat, shot, clip, dialogue, and inline direction together; stores structured fields and stable IDs without exposing JSON as the writing surface.
- **Screenplay compiler/validator:** translates the approved screenplay and its inline direction into stage-specific JSON and checks lineage, schemas, graph/source links, and continuity.
- **Production planners and generators:** consume compiled records with V2 source/revision principles; derive visual briefs, duration-bounded clip plans, model/workflow-specific prompts and media jobs. Existing V2 code is a reuse source; the current screenplay contract determines behavior.

Use a structured internal screenplay model that can render as normal text and preserve IDs/provenance through edits. Offer screenplay text export/import only after round-trip behavior is specified; do not make unstructured Markdown the sole source of truth.

## 9. Recommended delivery order

1. Define the unified story, revision, graph, screenplay, and production-record vocabulary and how each retains source provenance.
2. Merge the Story Builder and Story Canvas entry experience into one workspace; make story text and revision history the single source of truth for new projects.
3. Implement the long-story chunk/source index and versioned knowledge graph, including entity and fact provenance.
4. Replace the fake focused-edit placeholder with a conversational collaborator that proposes real diffs, applies accepted edits as revisions, and preserves unrelated text.
5. Add story analysis and graph-backed continuity checks with passage links; make findings actionable through chat or direct edit.
6. Draft and edit the readable screenplay from accepted story and graph revisions; use the same path for Assisted manual and Fully automated; execution settings come after the screenplay.
7. Add inline direction fields at project, scene, beat, shot, and dialogue levels; keep each decision readable and editable in the screenplay before compilation.
8. Build the screenplay compiler and validators; generate scene/cut/shot/dialogue/audio JSON after the applicable revision/readiness checks and approvals required by the configured execution policy.
9. Connect compiled records to existing V2 visual/audio/video production stages, retaining lineage and invalidation on edits.
10. Migrate old project data as needed. Keep legacy JSON artifacts available only for compatibility, migration, or optional read-only inspection—not as a second authoring workflow.

## 10. Decisions to settle before implementation

- **Chat provider and permissions:** “Codex collaborator” should mean a project-scoped assistant that can read the selected story revision and relevant graph/source passages, propose/apply user-directed edits, and cannot silently rewrite unrelated material. Decide the provider/runtime integration and tool permissions during architecture work.
- **Graph technology:** choose an implementation based on query, versioning, provenance, and deployment needs; the product requirement is the versioned graph model, not a particular database vendor.
- **Screenplay conventions:** choose the default display/export conventions and whether users can configure slugline and dialogue formatting.
- **Technical limits:** define transparent per-request/provider limits and chunking behavior without imposing an arbitrary maximum story length or silently dropping text.
- **Revision granularity:** allow scene-level revisions and preserve unaffected clip work. Generation must name the source revision it used. Assisted manual and Fully automated advancement follow `automation.md`; a whole-story human approval is not an unconditional gate for all modes.

## 11. Planning boundary

This plan specifies the desired merged, screenplay-first product and its migration direction. It does not claim that the current Story Builder or Story Canvas already implements these behaviors. Production V2 is the architectural basis for source lineage, chunking, revisions, and validation; the merged workspace and screenplay-to-JSON compiler remain planned work.

## 12. Direction changes and evolving generation prompts

The screenplay holds story and creative intent. A generation prompt is adapted to the selected model, workflow, clip duration, output parameters and currently selected references; it is not a frozen copy of screenplay text. Rebuild or refine prompt drafts as the user proceeds through preparation, while retaining accepted manual edits and displaying differences.

When a prompt change alters screenplay direction (camera, lighting, mood, action, dialogue, sound or music), offer:

- **Update screenplay:** apply the reviewed change to its scene/shot/dialogue field as a new revision, then mark dependent prompt/media records stale and offer targeted reconciliation.
- **This take only:** retain the screenplay and record an explicit override on this attempt. Show the difference beside the result.

Wording changes needed to suit a model do not require a screenplay edit when the intended direction is preserved. Fully automatic prompt adaptation preserves the story/creative intent and records technical adaptation and take overrides without silently rewriting canon.

Clip planning must account for dialogue, pauses, actions and the selected workflow's duration bounds. If a shot is too long, split it into ordered clips with explicit continuation state. Do not shorten or omit story content merely to fit one request. Assisted manual show these divisions in the readable screenplay/production view; Fully automated derives them automatically with source coverage recorded.

## 13. Setup placement and standalone scope

After screenplay generation, enter `automation.md` before preparing production model prompts. Capture stage automation choices and confirm their defaults/settings there. This page controls the downstream runner; it does not send the user to legacy Production V2, Manual Director or Automation Studio.

The canonical screenplay/source rules in this document apply to story-linked production. Isolated work can enter the same image/voice/video stage screens without any screenplay. Its task brief and prompt revisions provide local intent, with source screenplay/scene links left optional.


## 14. Shared workspace presentation and integration

Apply `ux_shared.md`: show saved source/screenplay revision and the next unfinished action; use readable direction/prose with optional technical disclosure. Direct editing and saving remain usable when generation is offline. Creative changes flag only affected downstream work; retain history and outputs. The story-linked journey and isolated generation use the same downstream forms.

`integration.md` defines source reuse. V2 lineage/chunking and selected direction-vocabulary helpers support this screenplay authority; neither a legacy JSON editor nor an upstream script display becomes a second authoring surface.

## Preceding production setup and file import

Regular authoring follows Production Type & Style, with pinned direction/style guidance. The same story workspace accepts writing/paste, TXT/Markdown and PDF extraction with readable preview/correction and exact revision provenance. See [production style and story import plan](production_styles.md); imported story is distinct from style-reference material.
