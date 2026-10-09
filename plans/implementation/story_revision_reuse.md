# Story revision foundation reuse map

Status: a bounded CPU revision foundation is implemented in the draft branch. It does not complete B2: there is no Codex editor integration, story graph, screenplay derivation, HTTP route, or provider call in this slice.

## Reuse and dependency boundary

Reference is the read-only Story Builder tree `/home/riki/web_dev/story_builder`, matched by parent to `mooV_E_maker` commit `2023bf5bce1a808b2624fb5789b4b2a1e8b7b8db`.

| Source | Provenance | Draft use |
|---|---|---|
| `services/production_story_revisions.py` | Git blob `010d761f62546acde197bf477c72702e1daac6c9`; staged SHA256 `86c3c3c11d18eee8c47ef475ecf6533f5b6194dc18102f8904a354d6a1689992` | Copied byte-for-byte. Reuses atomic, fsynced temp-write + replace, canonical UUID ownership folder and `story-canon-<12 hex>` validation. Story workspace ID is passed as `project_id`; a generated `authoring_uuid` is passed as `run_id` only to identify the storage folder. No production run or take is created. |
| `services/chunked_generation.py` | Git blob `c06f73971ecb6b77ac789fad71d89363478a8c58` | `SourceChunk` and `split_source_text` were extracted to `backend/story_builder/services/source_chunks.py`. Other code from this provider-dependent module is not imported. The extractor preserves contiguous Python Unicode-codepoint slices and checks complete coverage. |

`StoryAuthoring` depends on those revision/chunk utilities and the existing `ProductionLedger._connect()` for a shared SQLite database. It adds story-domain tables but no execution controller and does not alter production run/take state. Use an explicitly product-owned data root. Revision files live under `<data-root>/<workspace>/production_v2/runs/<authoring_uuid>/story/revisions/` according to the unchanged writer. The DB index/current pointer is authoritative; a file written by an optimistic writer that loses its DB transaction can remain as an unindexed orphan and is not exposed by revision listing.

## Contract and methods

- `create_workspace(title, source_text)` creates a generated `story-<12 hex>` workspace, a fresh authoring UUID and the first immutable source revision. It imposes no arbitrary source-length limit or truncation.
- `write_revision(workspace_id, source_text, expected_current_revision_id, metadata=None)` checks the current pointer optimistically, writes the immutable revision file first, and atomically inserts the revision index/chunk rows and changes the pointer. Concurrent writers from the same base produce one current revision; stale writers receive `LedgerConflict`.
- `get_workspace(..., include_source=True)` reloads the DB pointer and verifies the current revision file/source hash/chunk coverage. `get_revision()` verifies the indexed file, full source SHA256 and each chunk range/hash. `list_revisions(limit, offset)` is paginated; `restore_revision()` writes a new child revision from prior full text rather than rewinding the pointer.
- `propose_selected_edit(...)` stores an explicit human edit proposal only. It validates integer Unicode codepoint offsets (rejects booleans), exact expected quote and replacement text. It does not pretend that a model produced the edit. `accept_selected_edit()` requires the proposal base to remain current, performs normal exact-string replacement, and commits the new revision/pointer plus proposal status atomically. Concurrent/stale acceptance conflicts. Text outside the selected range stays byte-for-byte/codepoint-for-codepoint the same.

The SQLite additions are `story_workspaces`, `story_revision_index`, `story_revision_reservations`, `story_source_chunks`, and `story_edit_proposals`. Full source text is stored in each immutable JSON revision file; the chunk index stores contiguous start/end codepoint offsets and SHA256. Stable `story-canon-<12 hex>` IDs retain V2 writer compatibility. A reservation row and destination-file check prevent a generated ID collision from overwriting an existing immutable file. Revisions have a per-workspace monotonic sequence used for listing; timestamp precision and random IDs do not determine order. The chunker’s 2400-character default controls partitioning only and is not a story-length maximum.

Workspace creation stores its row before its first revision. If interrupted in that interval, `get_workspace()` and `list_workspaces()` expose `status: "initializing"`; `initialize_workspace()` accepts source text to recover the workspace once, and refuses reinitialization after a revision is indexed. A null current pointer is therefore detectable and recoverable rather than reported as initialized.

## Focused evidence and limits

Run from `backend/`: `PYTHONPATH=. python -m unittest story_builder.tests.test_story_authoring -v` (stdlib tests only). Seven cases cover multi-chunk Unicode source persistence/restart, exact selected edit and restore lineage, stale/concurrent optimistic conflict, workspace/offset/quote validation, monotonic revision ordering under equal timestamps, revision-ID collision without file overwrite, and interrupted workspace initialization recovery. No HTTP, Codex provider, graph, GPU, runtime, or user story is involved.

## Selected-text Codex editing slice (issue #20)

Outcome: the Story workspace can select one exact passage, send only that passage and the user's instruction to Codex, persist a keyed AI proposal with provider/model provenance, and review Accept/Discard. Accept reuses the exact-span CAS writer to create a normal immutable revision; proposal recovery and the revised story survive reload. The prompt explicitly discloses selected-only context and forbids whole-story claims.

Reuse provenance: `/home/riki/web_dev/story_builder/services/reasoning_provider.py` from selected Story Builder commit `2023bf5bce1a808b2624fb5789b4b2a1e8b7b8db` (verified blob prefix `00bcd7d`, source SHA-256 `135f4b63d2428898b74969ec9fd73adef4d1f7f54f6cc80d7d788e71c384b22a`), adapted to Codex-only and Vibe Director's provider setting (adapted file SHA-256 `4a629336b60a5066a3df7f89ab5f18e1f07076b4622ba520a193108e1917835d`); `/home/riki/web_dev/story_builder/services/provider_exec_guard.py` (verified blob prefix `c1f1a39`, source SHA-256 `906de788ca22278f92b1c653a8a1873edd425e352db61a921453201cfd754ae0`) copied unchanged. The read-only local reference folder has no `.git`; provenance uses the previously verified commit/blob record. No dependency was added.

Focused evidence: fake-provider API checks prove exact Unicode span validation, selected-only prompt input, one keyed provider call, durable proposal lookup after restart, CAS acceptance and story reload. Proposal insertion and the keyed request's complete/proposal pointer now commit in one SQLite transaction; a trigger-induced completion failure proves neither proposal nor pointer is partially committed. An ambiguous fake timeout remains failed/uncertain and the same key cannot submit again. UI edit request/proposal state carries its workspace ID, reload restores that workspace, and switching or creating another workspace is blocked until the edit is resolved. A mocked Playwright journey passed earlier; a repeat run was blocked before test startup by Chromium's sandbox-host `Operation not permitted` failure. Typecheck passed. No live Codex/provider/media calls were made.

Remaining: graph/source coverage, screenplay derivation and invalidation are later B2 slices. Provider context is the selected passage only; no whole-story consistency claim is made. An ambiguous keyed request is intentionally not resubmitted; the user must review status and create a distinct request if they choose to continue.
