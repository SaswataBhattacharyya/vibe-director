# Backend services — active UI/media contracts after 603b1fcb

R01 and R02 are now implemented as bounded fixes; UX02 Editor brief adapter exists. See fixes/R01_UX03_RESULTS.md for prior reported checks. Do **not** redo R01/R02 or re-add Editor APIs. Current work is UX04/AG01 and MED02/MED03. Read fixes/REFRESH_REVIEW_2026-11-06_603b1fcb.md, fixes/UNIFIED_MEDIA_AND_PROJECT_ASSETS.md and fixes/ACTIVE_FIXES_2026-11-06.md.

## UX04/AG01 — real typed agent actions across pages
Keep existing agent_conversation, agent_tools, agent_tasks, agent_editor, vibe_editor permissions/ledger and Editor revision-bound target. New actions should call old validated story/screenplay/prompt/image/video/3D/Media Prep services as allowlisted thin adapters. User message alone never dispatches new paid/GPU/renderer action. For each route first prove proposal/review/Apply parity, including idempotency/recovery and old history, then frontend removes legacy composer. No generic shell/function-call endpoint or separate project chat DB. Skills are instructions, not permission.

## MED02 — existing catalogue, truthful filters
media_library.py::browse_catalogue currently discovers approved source folders and iterates shared/tool/project manifests. It matches query on filename/description/tags and sorts newest/oldest, returning paged results and folder names. media_semantic_search.py::search_workspace is workspace scoped. Add optional backward-compatible filter contract if needed: audio voice category/roles, analyzer/index status and content SHA freshness, source/year/date/name sort, project/folder, tag/role. Apply filters before pagination; avoid discovering every large source tree during every keystroke. Bound indexing tasks and report stale/unindexed. No spontaneous model analysis or whole-disk scans.

## MED03 — multi-project membership without hidden copies
media_library.py::reuse_catalogue_asset links a source with reusable storage_location; otherwise it reads the source and registers/copies even when mode=reference. _link_shared_asset and _record_reuse carry provenance as existing mechanisms. Investigate source path authorization, project snapshots, data root relocations and deletion_preview/delete_media_file before changing persistence. Propose an additive verified physical occurrence + per-project membership/overlay adapter that retains old pa-* IDs/SHA, grant/lifetime, archived status and source project association. Cross-project use must never silently copy nor delete shared bytes when one membership is removed. Missing source should be shown/relinked explicitly.

Before adding a central database or moving files, demonstrate why existing project assets.json manifests/shared storage overlays cannot support the needed membership mapping. Preserve frozen admitted requests, original media, Editor selections, saved accepted takes, project Save/Load and cleanup/retry. No broad refactor of 1600-line media_library.py: extract a narrow validated helper and migrate with tests.

## UX07 output folder
output_destinations.py already supports default/workspace/folder, grant, relink and freeze. First improve OutputDestination.tsx display only; backend changes only if explicit project-specific recommendation or relink semantics require it. Existing chosen target is frozen per job. Never silently redirect published outputs or overwrite on label change.

## Acceptance and blast radius
Trace media_library.py -> media_discovery.py/storage_paths.py/output_destinations.py -> projects.py snapshots -> editor/job/agent consumers; inspect server route validators and existing tests. Verify 2 projects / same source, created_at sorting and pagination, filter truth, unsafe paths, external folder unavailable, deletion protection, project checkpoints, source moved, stale hash, recovery idempotency. Test synthetic assets under test-owned temporary workspaces; no user media deletion. No GPU/paid/provider activation without authorization.
