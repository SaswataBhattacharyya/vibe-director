# Production V2 graph and screenplay reuse audit

This read-only assessment compares `/home/riki/web_dev/story_builder` with the current Vibe Director plans. Target one story-to-screenplay path: exact source tracking, complete source-linked graph, readable editable screenplay. Legacy Canvas and V2 UI are reuse references, not alternate flows. See `/home/riki/Documents/ChatGPT/Vibe Director/plans/screenplay.md`, `rectifications.md`, and `GLOSSARY.md`.

## Reusable source and revision foundations

`/home/riki/web_dev/story_builder/services/chunked_generation.py` contains the strongest long-source processing primitives:

- `split_source_text` creates exact contiguous chunks with source offsets and stable per-input IDs, checking for gaps and overlaps.
- `_validate_story_chunk` verifies the returned source excerpt exactly against the chunk, derives fact offsets from exact quoted substrings, and separates inferred details. Its current `.find(quote)` chooses the first occurrence if a quote repeats; adapt this to require a validated occurrence/span or flag ambiguity for review, rather than arbitrarily assigning provenance.
- `generate_story_canon` processes chunks in order with bounded retries and continuity handoff; it verifies the complete ordered chunk ID list and fact spans before assembling a canon revision.
- `chunk_units` and `generate_chunked_units` batch stable downstream units under a character budget, validate returned IDs/order, and retry missing units.

Adapt these algorithms to the current workspace/revision contract. Chunk coverage does not prove every story fact, event, or relationship was extracted.

`/home/riki/web_dev/story_builder/services/production_story_revisions.py` provides `write_revision`, `load_revision`, and `list_revisions` for atomic immutable JSON files under validated project/run paths. It also has matching stage-revision helpers. `/home/riki/web_dev/story_builder/services/production_world_state.py` provides `read_project_canon` and `save_project_canon`, with schema validation, optimistic revision checks, append-preserving identity rules, atomic writes, revision copies, and content hashes.

In the current canonical backend, build on `/home/riki/Documents/ChatGPT/Vibe Director/backend/story_builder/services/source_chunks.py`, `services/story_authoring.py` (`StoryAuthoring`), `services/production_story_revisions.py`, and `services/production_ledger.py`. The authoring service persists immutable story revisions and exact source chunk ranges/hashes in the existing SQLite ledger, verifies complete coverage and hashes on read, and uses the current workspace pointer/revision model. Keep graph and screenplay lineage in this same story-authoring domain; do not create a second controller or ledger.

## What the existing graph stores

`production_world_state.py` persists versioned character and world/location records. `production_text_controller.py:reconcile_outline_identities` resolves names in candidate scenes to those stable IDs and stores evidence containing the story revision, scene, source-context and matched chunk IDs, and matched text. It attaches `character_ids` and `world_id` to scene/shot outline units.

This entity canon is not the planned knowledge graph. Missing: event/time nodes, typed relationship edges, exact evidence offsets, confidence/unresolved states, screenplay-linked graph snapshots, graph queries, and incremental consistency checks. Source-derived aliases also need careful reconciliation: text-name equality cannot itself establish a stable identity, and renames must not silently create duplicates or merge different characters.

The older `/home/riki/web_dev/story_builder/services/project_graph.py:update_artifact` is even narrower: it writes project JSON artifact nodes, a selected set of entity nodes, and generic `mentions` edges. Its text-derived IDs and sparse extracted fields are not evidence-backed story graph records. Neither implementation should be presented as complete graph coverage.

## Screenplay and whole-source limits

`/home/riki/web_dev/story_builder/services/production_text_controller.py:plan_scene_outline` plans dramatic scenes independently of chunk boundaries and requires each known source chunk to appear in at least one scene reference. It also places the full expanded story into one prompt and currently rejects inputs above 100,000 characters. That is not map-reduce and chunk-level coverage does not prove semantic coverage of every story fact. Do not adopt a silent 100,000-character truncation or a product-level story cap; if a particular provider or operation has a transparent technical limit, surface it and preserve the complete source.

`generate_chunked_units` is bounded batching for already-defined scene/shot units. It lacks a final cross-batch synthesis/reconciliation pass. Any whole-story graph or screenplay operation needs map-reduce across every chunk and then a bounded final synthesis that can retrieve/reconcile all chunk outputs, not just an excerpt or the last chunk’s continuity summary. Capacity and completeness of that final retrieval are key risks.

Legacy Canvas is not an adequate screenplay foundation: `/home/riki/web_dev/story_builder/services/story_revisions.py:outline` sends the entire novel to one provider call and requests generic JSON scene records; `/home/riki/web_dev/story_builder/api/main.py:create_canvas_outline` stores that as a screenplay revision with only a parent ID and narrator metadata. It has no accepted V2 story/graph lineage, editable structured hierarchy, or complete source coverage. The screenplay-first requirements in `screenplay.md` define the target instead.

V2 story revisions do preserve source evidence, but `api/main.py:save_manual_production_v2_story_revision` copies the parent revision’s chunks/facts while changing `expanded_story`; that can leave evidence stale relative to edited text. A source-story change currently requires a new V2 run, but there is no targeted graph/screenplay dependent invalidation for edits.

## Smallest aligned implementation sequence

1. Reuse the canonical workspace, immutable revision, source-chunk, and shared-ledger foundations. Add graph snapshots scoped to an exact story revision, with stable entity/fact/event/time/relation IDs, exact source offsets and chunk IDs, and explicit source-supported/inferred/user-authored/unresolved status.
2. Build bounded per-chunk extraction and identity reconciliation, followed by cross-chunk synthesis for aliases, chronology, relationships, contradictions, and open questions. Validate exact quotations and require an explicit disposition for extracted facts; chunk references alone are insufficient.
3. Add resumable map-reduce operations over all source chunks and all chunk outputs, with immutable task/revision identity, visible completeness/context status, and a final synthesis that verifies complete input coverage.
4. Draft the readable structured screenplay only from an accepted story revision and identifiable graph snapshot. Preserve source links and stable scene/beat/shot/dialogue IDs, and measure source-to-screenplay event coverage rather than only chunk coverage.
5. Add screenplay revision, edit, acceptance, render/round-trip validation, and dependency staleness tracking. Edits should refresh affected graph facts and dependent screenplay summaries while retaining the prior snapshot and a full rebuild/compare path.

Relevant inspected V2 entry points include `api/main.py:detail_production_v2_story`, `_process_claimed_story_stage_task`, `enqueue_production_v2_text_task`, and `generate_production_v2_text_stage`. Reuse their validation and lineage patterns selectively; retain one current screenplay-first user journey.

## 2026-10-09 implemented graph increment

The first graph producer-consumer increment now lives inside the existing `StoryAuthoring` service and production ledger. A snapshot is keyed to one immutable source revision ID and SHA256. Processing uses the existing exact contiguous `source_chunks` partition and makes one provider call per chunk; no whole-story prompt, story-length cap, or silent truncation is introduced. Each returned record carries chunk-local code-point start/end and quote; the backend rejects mismatched or invalid spans before persisting absolute source offsets, chunk ID, revision ID/hash, status, confidence, and typed fields. Supported record kinds are entity, fact, event, time, relation and open question. Entity/relation identities are stable within one snapshot; repeated semantic records accumulate evidence from multiple chunks.

Snapshot/chunk state and records are persisted incrementally. Same-key replay returns completed results, retries only explicitly requested `failed` chunks, and preserves `uncertain` calls without resubmitting them. A duplicate request leaves a recent `processing` claim alone; claims older than ten minutes become `uncertain` before pending work continues. The Story UI can generate/continue extraction, inspect source evidence and chunk states, edit a record, set its review status, and reload the saved snapshot. The API remains in the shared local Story route and SQLite ledger; no second controller or database was added.

This increment does not complete graph semantics. `all_chunks_processed_semantic_coverage_unverified` means every chunk returned a validated response; it is not proof that all meaningful facts were extracted. Cross-chunk identity/alias reconciliation, chronology synthesis, contradiction detection, graph queries/neighborhoods, rollback/merge/split, incremental refresh after story edits, and screenplay consumers are still pending. Contradiction state remains `not_assessed`; there is no whole-story consistency or coverage claim. A claim older than ten minutes is treated as uncertain (the Codex CLI timeout is five minutes); uncertain calls are never silently retried under the same key.

## 2026-10-09 screenplay projection slice

The graph now feeds an immutable screenplay revision in the same StoryAuthoring ledger. Drafting requires a complete graph snapshot for the exact source revision, projects ordered event records (or facts when events are absent) into numbered readable scenes and shots, carries exact graph evidence links, and exposes action, dialogue, camera, lighting, mood, sound and music fields in a UI at `#/screenplay`. Saving edits creates a child screenplay revision; the API validates sequential numbering and preserves the exact evidence-link set. Reload selects the latest durable revision. The backend and mocked UI journey cover draft, edit, reload and lineage without a live provider or media request.

This is deliberately a projection scaffold, not semantic screenplay generation: it creates one shot per graph event/fact and does not expand scenes or reconcile events across chunks. Direction fields and dialogue are initially empty unless present in graph properties; current graph extraction does not yet establish a dependable dialogue contract. There is no screenplay deletion or history picker, scene/shot add/remove editor, cross-chunk synthesis, semantic completeness claim, or targeted invalidation after source/graph edits. Next issue-sized step: add bounded provider-backed per-chunk screenplay planning against all graph/source chunks with explicit coverage and recovery, then reconcile the outputs before presenting a draft.

## 2026-10-09 provider-backed screenplay draft increment

The screenplay projection scaffold is replaced in the current working tree by a bounded provider-backed map over every exact chunk of the immutable source revision. Each prompt receives that full chunk, its source-linked graph records/evidence from the exact snapshot, and the previous chunk's concise planned scene/action/dialogue context. Prior continuity is context only; every nonempty shot still needs exact graph record IDs whose spans belong to the current source chunk. Output is validated into the existing scene → shot hierarchy with action, dialogue, camera, lighting, mood, SFX and music together. No per-story cap or live provider/media call was added.

Task and chunk state are stored with screenplay revisions in the existing StoryAuthoring SQLite ledger. Calls proceed in source order and stop at the first failed/uncertain chunk. Explicit same-key recovery retries failed chunks only and retains completed chunks; expired claims are not blindly resubmitted. Final screenplay writes preserve exact source revision and graph snapshot lineage. The Story→Screenplay UI resumes the same task key and displays chunk progress and honest semantic-coverage limits. Same-key content collisions and edits from stale screenplay parents are rejected; StoryAuthoring connections now close after preserving transaction semantics.

Provenance: inspected Story Builder `services/chunked_generation.py` (SHA256 `b7910ef04039c523730fcbceb8ed64977af8d106ab1b7166ddf84a28694782cb`) and `services/production_shot_plan.py` (SHA256 `4f6c507a25db2cfd85d185c59effecae4912e34cf8c494d5cc868f4ef256d344`). Reused concepts: exact source chunking, continuity handoff, structured shot validation and immutable revisions. No source code copied; backend contracts remain the current Vibe Director source chunks, StoryAuthoring and production ledger. Source clone had no usable Git metadata in this environment, so file hashes are recorded instead of a commit.

Focused graph/screenplay fake-provider checks: six pass (multi-chunk source/evidence, recovery, replay, rejected evidence, exact lineage, stale-parent conflict). Frontend production build and `git diff --check` pass. No broad suite or live calls. Semantic event coverage remains unverified by design; cross-chunk graph reconciliation, acceptance/history UI, and source-edit invalidation remain open.
