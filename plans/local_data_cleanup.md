# Local data cleanup and shared media — 2026-10-31

Historical migration status (superseded by owner project pruning below): the physical shared-root cutover is applied and journaled at `local_data/reports/storage-migration/applied-20261101/`. No user media was permanently deleted. This plan supersedes conflicting storage-layout proposals in `media_selection_storage.md`; historical Oct 27 migration evidence remains valid history. The optional output-destination UI/API and producer publication/recovery wiring are implemented; live browsing and focused recovery checks passed. Actual new GPU/provider generation remains owner-clicked acceptance.

## Owner project pruning — 2026-11-01

Applied explicit owner deletion: keep only `trial 1 scar`, delete its generated/imported media and other projects. Named folder `projects/trial 1 scar/` preserves stable internal identity through `library/project-folders.json`; deleted project IDs cannot be recreated by stale writes. Source, graph, accepted storyboard/screenplay and written prompts retained; readable JSON export at `story/storyboard.json`. Cleared production jobs/assets/batches/automated run state; removed ~912 MiB of project files. Shared downloads/repertoire reassigned to tool-library, source files unchanged; training/models and standalone tool outputs untouched. Full audit `local_data/reports/project-cleanup-20261101.json`.

Migration rollback copies remain: automatic review rejected their deletion as beyond project scope, along with removal of shared workflow knowledge. The narrower cleanup retained both. Do not run the old rollback blindly; it would restore deleted project state. Removal of historical backup copies requires explicit additional authorization. Current service IDs and verification are at top of HANDOFF.md.

## Implemented storage cutover — 2026-11-01

The owner authorized proceeding with the proposed cleanup and optional workspace/folder destinations. The following reversible, same-filesystem directory moves and metadata changes are complete:

| Previous location | Current location | Result |
|---|---|---|
| `library/downloads/youtube/` | `youtube_downloads/files/` | 65 registered download records; original filenames retained. |
| `engines/youtube-import/out_videos/` | `youtube_downloads/files/legacy_import/` | Three legacy videos retained; donor manifests relinked and hash-verified. |
| `services/media/analyses/video_audio_analyzer/` | `video_repertoire/runs/` | Analysis run files now share the repertoire root. |
| `services/media/{analyses,uploads,clips,manifests,indexes,audio,temp}/` | `video_repertoire/` equivalents | Existing media and derived indexes moved; service job bookkeeping remains under `services/media/jobs/`. |
| `library/catalog/donor-video/` | `video_repertoire/legacy/donor-video/` | 62 donor video manifests remain discoverable; their media resolves under the approved shared roots. |
| `library/catalog/legacy-video/out_videos/` | `video_repertoire/legacy/out_videos/` | Legacy output path retained. |
| `services/music/{state.json,datasets,runs}/` | `ace_step/{state.json,datasets,runs}/` | ACE state, datasets, published LoRAs and full resume checkpoints moved without copying or pruning. Project documents are written under `projects/<workspace>/music/`. |
| `music_jukebox/projects/*/` | `projects/<workspace>/music/jukebox/` | Per-project music documents retain their workspace identity. No standalone project directory existed to migrate. |

The migration journal contains the exact move list, small metadata snapshots, publication rollback copies, and prior structured path records. Rollback command (after stopping affected Vibe services and confirming idle):

```bash
python tools/migrate_shared_media.py --root local_data \\
  --journal local_data/reports/storage-migration/applied-20261101 --rollback
```

The migration moved the 176 verified legacy project publication copies into the journal's `publications/` rollback area after resolving their shared repertoire files. The active `projects/*/media/generated/analysis/` trees now contain zero files; the canonical repertoire contains 639 files. This is reversible archival for rollback, not permanent deletion.

Read-only post-cutover checks on 2026-11-01: the YouTube Downloads catalogue query (`source=downloaded`, `kinds=video`) returns all 65 registered videos; analyzer publication discovery retains 176 occurrence records; 62 donor manifests and 32 saved jobs plus 10 ACE recovery requests resolve against the migrated roots. Re-running the migration without `--apply` reports zero pending moves/publications/job updates/ACE request updates. Focused checks recorded in `plans/HANDOFF.md` passed: migration 6/6, media library 25/25, repertoire adapter 48/48.

Post-cutover checks: downloaded catalogue 65/65; analyzed/extracted catalogue 176/176; repertoire browse 178 total (the 176 analyzed occurrences plus two existing donor-linked records); all 62 donor manifests resolve and match SHA-256; 32 saved jobs load with no old operational download paths; ACE state lists two project documents. A second dry-run reports zero pending moves, publications or job/request path updates. Six focused migration tests, 25 media-library tests and 48 repertoire adapter tests pass. The migration's preflight refused active service/job state if present; apply completed.

No model/runtime directories were moved. `trellis.2/` remains the TRELLIS input/output/runs root. ACE checkpoints (about 1.3 TiB including resumable training state) were renamed on the same filesystem, not copied or removed. Audio recordings/conversion outputs remain in `audio_studio/`; ACE generated audio remains under `ace_step/output/`; Music Jukebox project documents belong to a workspace and exports remain user-selected/browser outputs. The root `music_jukebox/` is currently empty.

### Completed destination integration and verification — 2026-11-01

Shared destination controls now offer **Tool default / Selected workspace / Choose folder** on direct image/video/export, analysis, recording, voice/audio utilities, Foley and ACE producer screens. Existing Text to Image folder-only behavior and TRELLIS/Jukebox/editor output controls remain intact. Browsing sources is independent of the selected workspace; standalone tools can use `tool-library`. Workspace inclusion references shared media unless the user explicitly requests a separate copy.

A chosen folder is granted explicitly and frozen into each new job before execution. Final publication verifies bytes, retains shared IDs/content URLs and removes transient staging only after successful publication. It does not copy intermediate H3 originals into the selected final-output folder. Missing destinations do not silently fall back; completed shared jobs and assembly exports retain a publication checkpoint so saving can be retried without rendering again. Relinking a moved folder verifies registered file hashes. Analysis run mappings preserve frame/clip/audio URLs when a complete run is stored externally. Existing frozen requests keep their original destination.

| Output | Tool default under `local_data/` |
|---|---|
| YouTube downloads | `youtube_downloads/files/` |
| Analyzed media, frames, clips, indexes | `video_repertoire/` (runs under `runs/`) |
| Workspace/project documents | `projects/<workspace>/` |
| TRELLIS inputs, GLB outputs and run state | `trellis.2/{input,output,runs}/` |
| User microphone recordings | `audio_studio/recordings/` |
| Voice transformations | `audio_studio/voice_changes/` |
| Other speech/audio outputs | `audio_studio/output/` |
| ACE datasets, checkpoints, generated music | `ace_step/{datasets,runs,output}/` |
| Music Jukebox documents | `projects/<workspace>/music/jukebox/` |
| Music Jukebox final exports | Existing user-selected export folder/browser download |

The explicit folder choice overrides supported defaults; workspace mode uses that workspace's generated-media area. Image/video/export defaults preserve their existing workspace behavior while allowing standalone library operation. Output grants and run mappings are metadata in `library/output_destinations/`, not additional permanent media copies. No model/checkpoint retention policy was changed.

Final live catalogue: **68 YouTube videos**, consisting of the 65 baseline downloads plus three retained legacy-import videos indexed by the normal picker refresh. Analysis remains 176 occurrences; repertoire browsing includes two additional donor-linked records. The live YouTube picker displays playable media and the migrated preview endpoint returns video bytes. Final migration dry-run reports **zero** pending moves/publications/job updates/ACE request updates, with all 68 downloads registered.

Evidence:

- 92 focused backend tests pass: output destinations, assembly worker/API, media library, repertoire adapter and migration. Includes real synthetic WAV publication, verified folder relink, no-clobber/symlink checks and save-only recovery without GPU admission/rendering.
- Five isolated Playwright checks pass for source browsing/selection and destination/missing-folder recovery. Frontend production build passes; its existing bundle-size advisory remains.
- Live browser on port 8082 verified YouTube downloads in Media Prep and the output controls. Screenshots: `/tmp/vibe-storage-live-downloads.png`, `/tmp/vibe-storage-live-output.png`. Playwright MCP could not use its occupied profile; isolated Playwright CLI was used without closing the owner's browser.
- Graphify refreshed. Final logs: `/tmp/vibe-storage-final-build.log`, `/tmp/vibe-storage-final-browser.log`, `/tmp/vibe-storage-final-dryrun.log`; focused backend log `/tmp/vibe-storage-checks.log`.
- Broader video/production-image suites still fail in legacy workflow/setup/provider fixtures; this is not a full-suite pass. Those failures do not establish live GPU generation behavior and unrelated workflows were not rewritten to satisfy them.

After checking Vibe jobs and ComfyUI's queue were idle, the existing API and image worker were reloaded with their prior arguments/environment. API PID 1161970, image worker PID 1161944; frontend 8082 was left running. Logs: `local_data/logs/storage-api-reload.log` and `storage-image-worker-reload.log`. No GPU/provider generation or training was submitted. Owner acceptance of a new generated output, native folder dialog and real removable-folder recovery remains; keep the rollback journal until that acceptance. If an interrupted analysis copy leaves an unregistered destination directory, retry reports the collision and retains the source rather than overwriting it; inspect/reconcile that directory before retrying.

## Owner's requested outcome

- One shared Video Repertoire folder for analysed video, frames, extracted audio, annotations and indexes; these are reusable beyond the project that requested analysis.
- One shared YouTube downloads folder.
- One `projects/` root for workspaces and their project documents.
- Individual tool folders such as ACE-Step, TRELLIS.2 and Music Jukebox.
- Browse sources independently of the selected workspace. Saving to a workspace is optional; users can choose another output folder.
- Preserve working generation, analysis/search, voices, training, editing, recovery and references.

## Audit evidence

Read current plans, B4 media-library scope, storage helpers, downloader, analysis publisher, asset resolver/catalogue, shared picker, R2V picker and tool stores. Graphify query for `publish_analyzer_outputs` returned no matching nodes; relationships below were confirmed directly in source instead.

| Observation | Evidence and interpretation |
|---|---|
| Downloads exist and are indexed | `local_data/library/downloads/youtube/` contains 65 MP4s. Workspace manifests contain 65 download records: 60 in `shared-downloads`, three in the standalone media workspace and two in the story workspace. None archived, none unindexed and no registered download file missing. These records point at the shared physical folder. |
| Live download endpoint works | GET `/api/media/media-49e2cabe-4ff4-416c-9b5d-edc7c758b0df/assets/catalogue?source=downloaded&kinds=video&limit=1` returned HTTP 200, total 65. Combined kinds also returned 65; image-only and audio-only returned zero. This does NOT establish that the owner's particular UI screen works. Page/context clarification is pending. |
| Definite R2V category mismatch | `App.tsx` labels `global:repertoire` “Analysed repertoire”. `media_library.catalogue_source()` categorizes current analyzer outputs as `extracted`, while `repertoire` means legacy donor records. Live totals: extracted 176 versus repertoire 2. This explains missing analysed content in that specific option, independently of the reported download symptom. |
| Analysed media is physically duplicated into projects | `video_summarizer_results.publish_analyzer_outputs()` calls `shutil.copyfile()` into `projects/<workspace>/media/generated/analysis/...` then registers a workspace output. Private originals live under `services/media/analyses/video_audio_analyzer/<run-id>/`. |
| Analysis publication inventory | 176 registered publications: 60 video clips, 95 frames, 21 audio clips, across two workspaces; recorded size 76,116,900 bytes. SHA-256 comparison proved 169 publications identical to corresponding run files. Seven older publications exist but lack `analyzer_relative_path`; their private counterparts have NOT been resolved or declared missing. Recover mappings through run manifests/occurrence IDs/hashes before deduplication. |
| Global catalogue remains workspace-backed | `browse_catalogue()` enumerates `projects/*/media/assets.json`; even global downloads need an owning workspace manifest. `MediaSourcePicker` requires `workspaceId` before browsing, requires a workspace name before Add, and `reuse_catalogue_asset()` copies foreign assets (512 MiB bound). Discovery, ownership and destination are still coupled. |
| Current disk allocation | Approximately 814 MiB projects, 342 MiB downloads, 358 MiB media service (351 MiB analysis runs), 270 MiB TRELLIS.2, 4.3 GiB `ace_step`, 47 GiB engines, and about 1.2 TiB `services/music`. Rounded `du` figures, not a deduplication estimate. |
| Main disk consumer is training history | ACE-Step has 72 `.ckpt` files totaling 1,240,372,293,408 bytes (about 1.13 TiB), each approximately 17.2 GB. Separate 72 adapter `.bin`/`.safetensors` files total 4,717,544,832 bytes. Full resumable checkpoints and inference LoRAs are different artifacts: do not delete either automatically or promise that every checkpoint is redundant. |
| ACE-Step storage is split | `ace_step/` contains runtime/datasets; `services/music/` contains state, copied datasets and training runs. Jukebox documents also use a separate `music_jukebox/projects/` root; editor projects are embedded in `services/editor/state.json`. These need explicit mappings, not a blanket directory rename. |

Browser limitation: Playwright MCP could not attach: “Browser is already in use for /home/riki/.cache/ms-playwright-mcp/mcp-chrome-c9ae093”. No browser reproduction is claimed. Sandbox localhost access was denied; the read-only live GET checks used approved host execution. No runtime reload occurred.

## Proposed physical layout

“One folder” means one authoritative root with organized subfolders, not all assets flattened into one directory. Run IDs/source IDs prevent collisions and preserve timestamps and lineage.

```text
local_data/
  youtube_downloads/                   # one canonical original-video store
    files/                            # retain existing filenames during migration
    catalog.json                      # global records, provenance, stable asset IDs
  video_repertoire/                   # one canonical analysis/repertoire root
    runs/<run-id>/                    # frames, clips, audio, manifests, summaries
    legacy/                           # retained donor material when still needed
    indexes/                          # semantic indexes, versioned/rebuildable
    catalog.json                      # occurrences link to exact run artifacts
  projects/<workspace-id>/
    workspace.json                    # name/context; stable workspace identity
    media/                            # explicit imports/project-exclusive output
    selections/                       # shared asset IDs, roles, ranges, annotations
    editor/                           # workspace-owned editor project documents
    music/                            # workspace-owned ACE/Jukebox project documents
    exports/                          # only when chosen as output destination
    intermediates/                    # private temporary production files
  ace_step/
    datasets/                         # approved training sets, not unrelated media
    runs/<job-id>/                    # training history, logs, resumable checkpoints
    loras/<adapter-id>/                # published inference adapter + metadata
    output/                           # standalone generated audio default
    runtime/                          # preserve existing environment in place
  music_jukebox/                       # standalone output/cache; project docs above
  trellis.2/                          # preserve input/output/runs/batches layout
  library/                            # other shared imports/catalogue as needed
  services/                           # durable queues, locks, service registries
  engines/                            # existing code/models, preserve locations
  runtimes/ runtime/ logs/ reports/     # existing operational data; separate retention
```

Root names above are proposed defaults. Downloads currently already have a single physical root; moving it to `youtube_downloads/` improves visibility but does not fix the selector by itself. Do not create a second active downloads tree during migration. Do not relocate installed Python environments, model weights or third-party engines merely for naming consistency.

Tool project documents should live under their associated workspace; standalone projects receive a named workspace identity without imposing screenplay/story prerequisites. Tool registries hold IDs and locations, not a second authoritative project document. Existing global style profiles remain global; project overrides stay with the project.

## Ownership and output choices

Separate **where to find inputs**, **where bytes are saved**, and **which workspace uses them**:

1. Source browser works without a selected project. Sources: YouTube downloads, Video Repertoire, other shared media, Workspaces, Choose folder. Enforce the input's supported media types and explain empty incompatible sources.
2. Each producing tool shows **Save output to: Tool default / Workspace / Choose folder on this PC**. Show the resolved path before Start and remember the choice per tool/project. Text to Image keeps its approved user-folder-only permanent-save behavior.
3. Selecting Workspace enables the workspace chooser. Choosing a folder opens the existing desktop folder picker, with an editable validated path fallback; no forced workspace creation/naming for folder-only work.
4. Analysis defaults to `video_repertoire/runs/<run-id>/`. A custom folder becomes the authoritative run location, indexed by reference in the same repertoire catalogue. It must not cause an invisible permanent second copy. Workspace linkage remains optional.
5. Shared downloads and analysed outputs have stable identities independent of workspace ownership. Proposed default Add-to-workspace links the existing file; **Make a separate copy** is explicit. This default is awaiting owner confirmation. Changing project notes/roles must not change another project's annotations.
6. Distinct occurrences at different source timestamps retain separate occurrence IDs even if their bytes match. Sharing physical files does not merge their semantic identities.
7. External folders use explicit folder grants and validated paths, following existing folder services. Temporary processing/staging may be necessary and must be labelled, bounded and cleaned after successful publication. User originals are never deleted as staging.
8. Missing external storage shows **Unavailable → Locate/relink**; it must not silently create an empty replacement or fall back to another output folder.
9. Remove from workspace unlinks only. Permanent library deletion is a separate confirmed operation displaying affected projects. Do not reuse today's analyzer delete routine unchanged: it currently removes both publication and private output.

## Required implementation seams

Reuse existing services; do not introduce a parallel media engine, queue or search implementation.

| Files | Bounded change |
|---|---|
| `services/storage_paths.py`, `video_repertoire.py` | Canonical root helpers; explicit storage locations; no stale hard-coded root or silent fallback. Separate job bookkeeping from media ownership. |
| `video_repertoire_worker.py`, `video_summarizer_results.py` | Publish/register exact run artifacts once; keep workspace association as metadata/reference. Preserve partial output/recovery behavior and source lineage. |
| `media_library.py` | Global asset ownership/location lookup with stable legacy-ID aliases; keep existing API consumers working. Separate project membership from ownership; resolve content, reuse, archive/delete and external availability consistently. |
| `media_semantic_search.py`, analyzer/index adapters | Resolve global and external locations; migrate/rebuild path-bearing indexes without losing annotations. Preserve semantic group expansion. |
| `isolated_server.py`, `lib/media-api.ts` | Project-independent catalogue access and output destination contract; existing routes may delegate through compatible adapters during transition. |
| `MediaSourcePicker.tsx`, R2V in `App.tsx` | Same source taxonomy and kind-aware results. Correct repertoire/extracted mismatch. Remove mandatory project/name gate for global discovery; preserve selections/paging/errors. |
| `MediaPrepPage.tsx`, `MediaLibraryPage.tsx`, image/audio tools | Optional destination/workspace association, actual resolved output path, folder-only workflow and relinking. Preserve existing controls and source restrictions. |
| `ace_studio.py`, `ace_studio_runner.py`, `vibe_editor.py`, `music_jukebox.py` | Consolidate project documents and tool paths only after dependency mapping. Published LoRAs remain usable; move/update adapter paths atomically. No broad training rewrite. |

## Impact on Vibe Director and every path-dependent integration

This is an application storage migration, not a file-manager cleanup. Moving directories without the corresponding reader, writer and saved-reference changes can break previews, search, references, training selection, rendering and resume. The following is the required impact checklist; the implementation dry run must extend it with every actual reference discovered. File names below are under `backend/story_builder/` unless a frontend/tool path is given.

### Physical paths and saved data that need migration

| Current location or record | Proposed location/change | Consequence if missed |
|---|---|---|
| `library/downloads/youtube/<file>` | `youtube_downloads/files/<file>`; update downloader, reconciler, resolver and global catalogue together | New downloads land in the old folder, existing thumbnails/video streams fail, or refresh scans an empty directory. |
| `services/media/analyses/video_audio_analyzer/<run>` | `video_repertoire/runs/<run>` or an explicitly selected external run location | Results, clips, SAM Audio source lookup and semantic searches lose their run files. |
| `projects/*/media/generated/analysis/...` | Global repertoire occurrence points at the verified canonical artifact; workspace stores membership/annotations | Frozen references stop resolving, or old copies are recreated on the next publication. Seven legacy mappings must be recovered first. |
| `library/catalog/donor-video` and `library/catalog/legacy-video/out_videos` | Audit and map referenced donor media under `video_repertoire/legacy/`; preserve unrelated catalogue material | Legacy repertoire entries and legacy source-resolution paths break. |
| `services/media/analyses/corpus_index_v2`, other path-bearing indexes/manifests | Repertoire indexes plus run-location mappings; translate paths or rebuild only derived indexes | Semantic hits may exist but point to missing media. Changing vector/index paths does not justify dropping summaries or manual annotations. |
| `projects/*/media/assets.json` | Preserve legacy asset/workspace aliases; introduce global ownership/location records and project membership | Existing asset IDs in prompts, roles, accepted takes and editor timelines become orphaned. |
| `services/music/state.json`, datasets and runs | Tool state under `ace_step/`, project documents under `projects/<workspace>/music/`; update all recorded dataset/checkpoint/adapter locations | Training resume, logs, dataset preview and generation with trained LoRAs fail. |
| `music_jukebox/projects/*/project.json` and checkpoints | Workspace music documents with stable Jukebox project IDs; update project registry and recovery paths | Saved arrangements, sample references and autosave recovery disappear from the UI. |
| Editor projects inside `services/editor/state.json` | Workspace editor documents; retain global styles/profile separately | Editor project chooser, saved selections, composition paths and previous exports become inaccessible. |
| Production DB fields, batch entry JSON, job request/result JSON, analyzer manifests, composition records and cached output grants containing old paths | Inventory exact fields; migrate explicit locations or resolve stable IDs through a location mapping | Resume can repeatedly pause on a missing output, render can read stale paths, or a job can incorrectly regenerate existing work. |

Do not perform unrestricted string replacement across JSON/SQLite/source files. Distinguish operational file locations from historical log text, source provenance, immutable request content and signed/hashed manifests. Keep frozen content and its recorded hash intact where ID/location indirection suffices; any necessary schema migration must version records and preserve original audit evidence. Do not hand-edit a frozen manifest and leave its old hash.

### Feature-by-feature application impact

| Vibe Director feature | Path users / required adaptation | Required regression evidence |
|---|---|---|
| Startup and worker configuration | `isolated_server.py`, `storage_paths.py`, `video_repertoire.configure_roots()` and worker launch configuration. Audit `VIBE_DIRECTOR_DATA_DIR`, `VIDEO_REPERTOIRE_ROOT` and absolute dataset/output settings. Keep the data root unchanged; update only relocated subroots. `VIDEO_REPERTOIRE_ROOT` currently also owns jobs, so separate job bookkeeping deliberately rather than moving its whole tree accidentally. | API and workers agree on roots after restart; no split queues, second catalogue or empty replacement folder. |
| YouTube download, history and discovery | `video_repertoire.youtube_downloads_root()`, worker download/publication, `media_library._youtube_download_base()`, registration, reconciliation and content resolver | Download records, streaming, refresh and history all resolve the same canonical store. |
| Video Summariser Library / Analyze / Results / extracted assets | `video_repertoire.py`, `video_repertoire_worker.py`, `video_summarizer_results.py`, `media_library.py`, `sam_audio_vibe.py` | Existing results and previews load, new publications use the new root once, delete/unlink follows shared ownership, interrupted analysis resumes. |
| Name and semantic search | `media_semantic_search.py`, repertoire corpus/run-index locations and analyzer adapters | Existing queries return playable/image-previewable hits and preserve timestamp/group semantics across workspaces. |
| Browse media, R2V and FFLF reference selection | Shared `MediaSourcePicker.tsx`, catalogue API/client, R2V source controls in `frontend/src/App.tsx`; content requests resolve old IDs through new locations | Correct source/category and media type; references survive source/project switching and reload. R2V analysed-source bug corrected separately from path migration. |
| Characters, Worlds, Frames and standalone Text to Image | `frontend/src/ImageAssetsPage.tsx`, folder-reference/image studio components, `isolated_image_worker.py` and asset resolution/publication | Existing masters/views/roles still resolve. User-selected external input/output folders remain unchanged. Workspace output helpers change only when their destination policy changes. |
| T2V / FFLF / R2V generation and batches | `services/isolated_video_jobs.py`, `services/t2v_batches.py`, production stores and generated/intermediate path helpers | Old jobs/takes retain playback and overwrite naming; source/reference hashes match; batch resume finds existing H3/final artifacts. H3/LTX chunking, unload order and generation parameters are outside this cleanup and must remain unchanged. |
| Audio tools, voice recording/conversion and saved voices | `audio_utilities.py`, `voice_studio.py`, repertoire worker audio publication, media resolver and Reconstruct/TTS consumers | Audio previews, enrolled references, calibration and saved takes work. RVC artifacts under ComfyUI model storage are not moved; only relocated local-data references change. |
| ACE-Step projects/training/LoRA generation and management | `ace_studio.py`, `ace_studio_runner.py`, `ace_studio_api.py`, `studio_checkpoints.py` | Load projects and dataset rows, show logs, resume training, select existing adapter for generation and preview deletion candidates. Checkpoint catalogue IDs are currently derived from absolute paths: preserve aliases or migrate identities, invalidate stale confirmations, and never let an old deletion selection target a different artifact. |
| Music Jukebox and Vibe Editor | `music_jukebox.py`, `vibe_editor.py`, `vibe_editor_render.py`, saved source selections and output/composition locations | Open/recover old projects, resolve shared media, export and hand off between tools. External exports stay where the user chose them. |
| Assembly / final export | `assembly_export_worker.py`, `services/assembly_renderer.py`, source resolver and registration | Frozen export inputs still validate. Current assembly renderer explicitly restricts output to workspace exports: adding custom destinations requires an approved-folder-aware contract change, not merely changing a displayed path. |
| TRELLIS.2 and AI Toolkit links | Keep current tool/runtime/model roots. Inspect saved input/output grants and launch configuration for any path included in the move manifest | Open saved GLBs/Blender and existing trainer links. No reinstall or model relocation as an incidental cleanup. |
| Cleanup, diagnostics and maintenance | Existing `tools/migrate_local_layout.py` describes the Oct 27 layout; do not rerun it as the new migration. Update current health/cleanup scripts, fixtures and documentation that enforce relocated roots | A new dry run reports only intended moves; retention tools cannot mistake shared or external originals for disposable copies. |

### UI and API contract implications

The frontend should normally receive stable asset IDs and backend-generated content URLs, not construct new filesystem paths. Keep those IDs/URLs usable while the backend location changes. New UI work is needed for optional workspace association, explicit destination choices, resolved-path display, missing-file relinking and shared-file deletion warnings. Existing folder-only pages must keep their chosen locations. Preserve generation controls, chat panels, style choices and automation semantics.

Existing content-resolution rules currently accept only known workspace/download roots. Global repertoire and granted external locations require explicit resolver support with the same traversal/symlink and authorization checks; simply widening the allowed filesystem root is not an acceptable shortcut. Internal tool Docker/subprocess mounts and generated HTML/FFmpeg inputs must receive the resolved new location, including paths containing spaces.

### Cutover and rollback rule

Treat the root mapping, metadata migration, service configuration and compatible reader/writer release as one coordinated cutover. Pause only affected writes during migration; leave generation settings and unrelated services alone. Restart affected backend/workers against the same mapping, verify consumer paths and recovery, then re-enable writes. Rollback restores code/configuration, metadata and moved files together. Do not delete the old verified copies until all affected consumers pass and the retention review approves their removal.

## Migration sequence and safeguards

1. **Finish diagnosis:** reproduce the owner's exact empty YouTube picker with its page/kinds/query/folder/workspace/request/response. Fix measured source/filter/refresh errors rather than assuming that moving files fixes discovery. Include an accessible mismatch explanation for image/audio-only consumers.
2. **Dry-run manifest:** enumerate every existing file/record to be affected: old/new path, size, hash where relevant, asset/occurrence/run IDs, project memberships, referring DB/manifests/indexes and action (retain/move/link/deduplicate/manual review). Check available disk, cross-filesystem behavior, destination collisions, active jobs and unresolved external locations. Keep a separate protected inventory of models, adapters, full checkpoints, datasets and runtime environments.
3. **Adapt readers/writers first and test on temporary fixtures:** preserve IDs/API contracts and references from frozen production requests, takes, editor timelines, semantic results and job recovery. A versioned migration state must prevent reading half-migrated records. Do not simply rename folders with old code running.
4. **Quiesce affected jobs:** prevent new affected writes, wait for or explicitly defer active work. Snapshot small metadata/DBs/index configuration and produce a reversible move journal. Same-filesystem atomic renames where practical; cross-filesystem copy → hash verify → switch references → later retire old files. No overwrites or symlink-based compatibility bypass.
5. **Migrate downloads and analysis:** move the one download store; preserve all 65 records/identities. Relocate analysis runs, register 176 publications globally, resolve seven legacy mappings; deduplicate only verified identical bytes while retaining all occurrence identities. Preserve unmatched workspace copies until resolved. Move donor catalogue media into repertoire only after auditing actual file references.
6. **Migrate project/tool metadata:** consolidate project documents and update explicit paths/IDs. Move ACE runs/datasets only with published adapter/resume/UI paths updated; do not copy 1.2 TiB needlessly or prune training files as part of the rename. Leave environments where installed.
7. **Verify before cleanup:** compare manifest totals/hashes and all referenced paths; run focused consumer/recovery checks below. Keep unresolved cases visible. Roll back paths and metadata together if validation fails.
8. **Separate retention review:** present reclaimable verified duplicate/temp/checkpoint candidates with references, bytes and consequences. Agree training resume retention versus inference-only LoRA retention before pruning. No deletion of “bad LoRAs”, `.ckpt`, datasets, backups or external originals based only on age/name.

## Acceptance checks

- Downloads source shows the 65 baseline videos from multiple workspaces and folder-only mode; no duplicates introduced by refresh. Kind-specific empty states are truthful. Verify content previews, not only record counts.
- Repertoire shows all 176 baseline analysed occurrences across media kinds and both existing workspaces; all 169 verified copies retain exact identity/hash mappings and seven legacy cases are resolved or retained explicitly.
- Download → analyze → repertoire → select in R2V/editor works through one shared asset identity. CPU fixtures cover publication; any new GPU analysis/generation remains owner-clicked under existing runtime safeguards.
- Adding shared media to two projects under the proposed link policy makes no extra permanent copy. Roles/ranges/notes remain project-specific. Explicit copy makes a separate owned file.
- Choose folder works without a story/workspace; selected output exists only at the chosen permanent location, aside from bounded labelled temporary data. Existing Text to Image folder behavior remains intact.
- Search/group results, waveform/video/image previews, frozen requests, accepted takes, ACE adapters, editor projects and resume/recovery still resolve after restart.
- Removing a project selection cannot delete shared files. Confirmed permanent deletion reports dependencies. Disconnect/relink external folders and test missing/collision/failure recovery.
- Migration is restartable and reversible; repeated execution neither duplicates files nor restores archived assets. Tool settings, runtimes and trained models survive unchanged.

## Decisions and remaining acceptance

Implementation and the reversible storage cutover are complete. Shared files remain in their canonical root; workspace inclusion is optional linkage, and a separate copy is explicit. The live YouTube source browser now finds all 68 registered files. Focused storage/recovery tests and idle-service reload checks passed as recorded above. The owner still performs actual GPU/provider generation acceptance; synthetic and mocked tests do not replace it. Preserve the migration journal and resumable checkpoints until owner acceptance. No permanent media/checkpoint deletion or retention cleanup was performed.
