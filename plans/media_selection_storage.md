## Latest implementation correction — 2026-10-27

R2V retains its existing categorized reference carousels. Do not add a separate
Browse media sources panel there. Put global repertoire, YouTube downloads,
generated/imported media and named workspace sources inside each existing
Images/Audio/Videos source dropdown, with strict media-kind filtering. Browsing
source is independent of saving destination. Copy foreign assets on explicit Add
through the existing reuse API; preserve reference limits, warnings and uploads.
FFLF and character/world/frame image browsers remain as before.
Character voice dropdowns offer ComfyUI voices directly: import and assign on
selection, refresh every character's choices immediately, allow voice reuse.
Fully automated continues to skip voice assignment; explain and link to settings.
The whole-app UI redesign is a separate pending milestone.

## Media source browser applied — 2026-10-27

Owner approved the source-first picker correction. Implemented locally in the shared
MediaSourcePicker, media catalogue service/API and Create R2V addition handlers.
Sources are global; Workspaces opens a nested named list, folders have breadcrumbs/
Back, and changing source clears the previous workspace filter. Compatible media
only; Downloads explicitly explains an image/audio-only empty result. Search,
newest/oldest, card/list/carousel, previews and select/deselect shown are retained.
Hidden selections survive filtering. Add remains explicit, preserving existing
reuse/dedup rules and destination workspace; it does not generate or attach refs.
Unnamed destinations prompt for a durable name before adding; existing page
workspace controls still choose the destination. Names persist in server metadata
and browser aliases. R2V's separate groups and existing paired audio handling stay;
over-limit Add warns before changing references (9 images, 3 videos, 3 audio).

Download refresh indexes only canonical local_data/library/downloads/youtube and
keeps original bytes/paths. It skips symlinks and already registered/archived paths.
Live refresh indexed 60 previously unregistered videos, no errors; global API now
returns 65 downloads even with an unrelated owner parameter. No physical migration
repeated; no donor files deleted. This completes this shared picker correction,
not the separate wider UI redesign.

Verification: TypeScript PASS; six focused media catalogue tests PASS (global
source/owner, folders, names, no-copy indexing/idempotence/archive preservation,
existing reuse and ACE behavior); three focused mocked Playwright checks PASS
(explicit Add/source navigation, durable name, R2V over-limit preservation).
Live Chromium shows 24 downloaded cards on first page, no JS errors; desktop
screenshot /tmp/vibe-media-source-desktop.png. No generation, training, Git or
hardware changes. Generation acceptance remains owner-run.

API reloaded idle with existing env/cwd: PID 1121468, port3020, log
/tmp/vibe-api-media-source.log. Frontend PID87762 remains port8082. Graphify code
map refreshed. Relevant files: frontend/src/MediaSourcePicker.tsx,
frontend/src/lib/media-api.ts, frontend/src/lib/media-workspace.ts,
frontend/src/media-library.css, frontend/src/App.tsx,
backend/story_builder/services/media_library.py and isolated_server.py.

# Media inputs, selection and storage

Date: 2026-10-27. **Status: physical migration implemented locally; source-browser redesign pending; owner UI acceptance pending.**

Owner authorized implementation and tests. Files and folders were physically moved, not just renamed in the UI. The original audit below records the previous arrangement; this implementation record and the migration journal take precedence over its proposed paths.

## Owner correction — source-first browsing and physical coherence (2026-10-27)

**Authoritative requirement; selector redesign pending.** The physical migration recorded below is completed locally; that does not mean the source browser is accepted or complete. These corrections supersede the flat source/workspace controls and ID-based display described below.

- Maintain one coherent physical layout, not just virtual labels. Downloads belong in `local_data/library/downloads/youtube/`; workspace media in `local_data/projects/<workspace>/media/`; repertoire analysis/indexes in `local_data/services/media/`. Reconcile any remaining misplaced files using explicit source-to-destination mapping, update stored paths and consumers, and verify file counts/integrity and playback before retiring old locations. Do not repeat completed moves or duplicate files to make category filters work. Analyzed clips, downloads and generated media retain provenance and discoverable identities; indexes may describe multiple views of the same file.
- Browse by **source first**: Workspaces, YouTube downloads, analyzed/repertoire clips, generated media (including ACE-generated audio), style references and imported media, as compatible. Workspaces opens a nested slide-in of named workspaces, then their media. Sources with folders/collections use the same nested navigation and breadcrumbs. Do not apply an active workspace filter to another source; reset stale nested scope on a source change. The target workspace identifies where work is saved, not a global discovery restriction.
- Use existing migrated directories and registries as the basis of discovery. Downloads must appear without requiring a manual import into the active workspace. Audit the downloader/repertoire registry-to-catalogue bridge: the current manifest-based catalogue is not proof that every physically present download is discoverable. Register/reconcile known files without recopying bytes or starting analysis. Distinguish no compatible files, no search matches, indexing gaps and loading failures.
- No anonymous generic or long-ID workspace names in normal UI. When saving/creating work needs a workspace and none is chosen, show a dialog: choose an existing named workspace or create one with a required human-readable name. Keep stable IDs internal. Existing unnamed workspaces need a naming action, without changing their identities or losing saved paths. Browsing global sources itself must not force workspace creation.
- Preserve R2V's separate **Images**, **Audio** and **Video** reference containers and existing preparation flow. Each browser lists only that slot's media kind: images for image selection, audio for audio selection, video for video selection. This change does **not** introduce Extract frames/Extract audio actions into those pickers or accept incompatible files. Explicit media preparation remains in its tool pages.
- Each multi-selection collection has Select all shown / Deselect all shown, preserving selections elsewhere. Single slots have Clear. Before committing additions, count already attached plus newly selected unique references across sources. Show a warning dialog if the selection exceeds the chosen workflow's image/audio/video capacity; explain allowed, selected and excess counts and let the user revise it. No silent truncation, replacement or generation. Submission remains blocked until valid. Enforce the same rules in the backend.
- Read actual limits from the selected workflow's versioned capability definition. The current installed H3 contract records 9 images, 3 videos and 3 standalone audio, with paired soundtrack handling and any verified combined/duration limits also respected; do not universalize these to other workflows or claim an unverified combined cap. Show counters beside each reference container.
- Repair the shared layout across every media selector: readable source names, full-width browser/drawer, grouped search/sort/view controls, generous previews, clear Add action and no squeezed duplicate workspace controls. Preserve all three themes, saved choices, source metadata and compatible-reference behavior.

Acceptance: a download outside the active workspace is browsable from Downloads; another workspace is reachable via Workspaces → name; nested Back/breadcrumb works; source changes clear stale scope; image/audio/video groups remain separate; limit warnings cover mixed-source and Select all additions; unnamed-workspace save prompts for a name/choice; migrated files and saved references still resolve. This is a planning correction, not a claim these interactions are implemented.

## Implemented layout

| Previously | Now, relative to repository root |
|---|---|
| `migration_plan/`, `My idea/`, root historical plans | `plans/migration/`, `plans/archive/ideas/`, `plans/archive/` |
| `Vibe Editor/`, `images.png` | `design/vibe-editor/`, `design/reference/images.png` |
| Runtime media in `media-projects/` and `assets/` | `local_data/projects/<workspace>/media/`: manifests, `imports/`, `generated/` |
| Chunk/original video intermediates | `local_data/projects/<workspace>/intermediates/{chunks,originals}/` |
| Story revision data | `local_data/projects/<workspace>/story/production_v2/` |
| Production queues and ledger | `local_data/services/production/` |
| Repertoire jobs, analysis and indexes | `local_data/services/media/` |
| Music/editor state | `local_data/services/{music,editor}/` |
| YouTube downloads | `local_data/library/downloads/youtube/` |
| Copied repertoire manifests | `local_data/library/catalog/{donor-video,legacy-video}/` |
| Copied analyzer, audio, TTS skills, YouTube code and resources | `local_data/engines/` with named subdirectories |
| Editor runtime | `local_data/runtimes/editor/` |
| Audits, exports of batch specifications, debug/performance output | `local_data/reports/` |
| Root test output | `local_data/test-results/` |

Exceptions are deliberate: the prefix-bound ACE Python environment remains `local_data/ace_step/runtime/`; music datasets/runs and editor project internals keep their adapter-owned organization inside services rather than undergoing an unrelated rewrite. Packaged image smoke evidence remains in backend source. `graphify-out/` remains the configured code graph. External `setup_comfy_and-stuff` and shared caches remain external. No model weights were downloaded or duplicated for these moves.

## Media selectors and selection behavior

The compatibility table below remains authoritative. A shared **Browse media sources** control now appears in style media, Video Create FFLF, image assets, editor attachments, ACE reference audio, Control-Foley, Video Summariser, Image Detailer, Audio Studio, Reconstruct, Utilities and Media Library. It offers current/all workspaces, generated project media, downloaded, extracted, imported, copied repertoire and style references. Project names appear when present in the story catalogue; otherwise stable IDs identify the workspace.

Only registered, non-archived compatible kinds are listed. Search here matches names, descriptions and tags; existing semantic search stays in the dedicated search tools. Browsing does not start inference or generation. **Add selected** validates and copies media into the target workspace, preserves source provenance, and does not select workflow reference slots automatically. Same-workspace reuse and target hash matches avoid duplicate bytes. Cross-workspace files over 512 MiB require the existing dedicated import/registration route; large selections show a disk/time warning. Unregistered copied videos remain under Video Summariser → Import copied videos.

Multi-select collections use **Select all shown / Deselect all shown**, preserving hidden selections and enforcing workflow limits. Single frame/master slots have Clear. File/folder imports have separate labels and hover/focus help; the import list supports removing individual items and clearing it. Enrolled voices remain distinct from ordinary audio; changing an asset source never enrolls a voice automatically.

## Verification and recovery

- Migration journal: `local_data/reports/layout-migration-20261027/`, including preview, move list, consistent database/manifest backups and original changed source files.
- 110 registered media files retained identical SHA-256 and inode; no new broken paths. Nine already unresolved/archived records were recorded before migration and remain listed in `verification.json`.
- Both service databases passed integrity checks; 76 immutable submitted snapshots were left unchanged.
- Focused migration tests cover rename, manifest/SQLite path rewrite, rollback, collision refusal and active-job refusal. Catalogue tests cover compatible filters, independent reuse, tampering, archive behavior, role validation and provenance deduplication.
- Mocked browser tests cover compatible source discovery, explicit Add without generation, project labels, operation filtering and hidden selection preservation. TypeScript and launcher syntax checks pass. Analyzer/extracted-media tests use the new paths.
- Apply must never run again against this completed migration. Rollback requires stopped writers, the journal and backups, followed by restoring changed source files from `code-before/` according to `code-changed.json` (the tool rolls back data/moves, not source edits). Refuses occupied destinations rather than deleting user files. Do not roll back a live working installation for a test.

Owner acceptance: refresh the running UI on port 8082; check Audio Utilities → MP3 extraction → Browse media sources; filter a project/source, Add a video, then select/deselect shown items while searching. Verify saved media playback and open a saved story. Actual generation, extraction, training and provider calls remain owner-clicked; this change did not run those jobs. No Git work was performed.

## Original audit and proposed design

## 1. Original audit and design rationale (before implementation)

The application has useful media adapters, validation, manifests and job tracking. Reuse them. The weakness is inconsistent discovery and presentation, compounded by historical storage names. A file existing on disk is not proof it is registered, searchable, compatible, or safe for a particular job.

| Finding | Evidence in current code | Consequence / proposed correction |
|---|---|---|
| “Shared library” is primarily workspace-scoped | `frontend/src/lib/media-api.ts:listMediaAssets` calls `/api/media/{workspace}/assets`; Audio Utilities, Audio Studio, Reconstruct, ACE-Step, Image Detailer and Editor use workspace lists | Existing media elsewhere disappears from a picker. Add cross-source browsing, then explicitly make selected media usable by the target workspace. |
| Select-all behavior is inconsistent | `MediaPrepPage.tsx` Audio Utilities replaces selection with visible IDs; extracted assets have separate select/clear controls; `CharacterVoicesPage.tsx` has Select all + Clear | One toggle with a clear scope; preserve hidden selections; explicit workflow limits. |
| Source information is too coarse | `media_library.py:_public` labels project_upload/youtube_download as imported and everything else generated | That binary label cannot populate accurate Downloaded / Extracted / Generated filters. Preserve/normalize actual provenance, not filename guesses. |
| “Project”, workspace, repertoire, and source are mixed | Editor and ACE projects link to a media workspace; a story has its own identity and revision records | Display project names but retain stable workspace IDs and origins. Do not infer associations from matching titles. |
| YouTube storage name is misleading | `video_repertoire.py:youtube_downloads_root()` returns `local_data/donor_migration/video_repertoire/downloads` | New downloads are written into a historical transfer folder. Consolidate to the active repertoire downloads directory after a verified migration. |
| Two directory trees can look authoritative | `ensure_layout()` creates `storage/video_repertoire/downloads`, while the downloader uses the donor path | Choose one physical downloads store and update every consumer; an empty directory is not evidence of lost downloads. |
| Media and metadata are split | Upload bytes in `media-projects/<id>/inputs/media`; manifests in `production/assets.json`; generated bytes in `assets/<id>` | Keep these established paths initially; document ownership and expose a unified logical library instead of rewriting all workers. |
| Source and output format lists differ | Library upload accepts PNG/JPEG/WebP; MP4/MOV/MKV/WebM; WAV/MP3/M4A/OGG/FLAC/AAC. Some utility/repertoire code also recognizes AVI/M4V | Browser `accept` is not backend support. Align each picker with the complete active adapter path; unsupported files need an explicit conversion/error. |
| Reusable engines/models remain under transfer-era names | Roughly 47 GiB in `local_data/donor_migration`, about 46 GiB within analyzer; overall `local_data` about 49 GiB (`du`, rounded allocated sizes) | Do not recopy/reorganize large engines merely for appearance. Keep configured locations; optional renaming is a later, separately checked migration. These totals are not duplicate-byte measurements. |
| Import labels depend on native browser text | Audio Utilities has regular file input and `webkitdirectory` folder input, both rendered “Choose Files” | Distinct visible Import files / Import folder controls, short descriptions and hover/focus help. |

Inspection is static source plus directory/size inspection. It is not a full file hash/duplicate audit, a live API inventory, or proof every saved path resolves. No user files were moved or deleted.

## 2. Input compatibility table — what each screen should offer

I = image, V = video, A = audio. “None” means no media input, not missing functionality. Text, lyrics, transcripts and training sidecars are separate inputs. The selected backend workflow is authoritative: the UI must not show all three media kinds everywhere simply because the library stores them.

| Screen / operation | Expected media | Cardinality / additional rules | Existing backend contract to reuse |
|---|---|---|---|
| Production style references | I, V, A, independently or combined as a reference collection | Documents are a separate PDF/TXT/Markdown evidence path. Video frame extraction is an explicit separate action/count. | `production_styles.py`, `media_library.py` |
| Story import | None of I/V/A | TXT/Markdown/text PDF; scanned PDF needs OCR/fallback. Do not turn it into an arbitrary media picker. | `story_imports.py` |
| Character/world base image — Z-Image or Qwen T2I | None | Prompt/settings only. Style image recommendations require an image-edit route to be attached as actual images. | `production_image_workflows.py` |
| Character/world/frame image — Qwen Edit | I | Existing edit adapter supports 1–3 references; enforce active workflow/role restrictions. | `isolated_image_references.py`, image workflow adapter |
| World directional views — Qwen multi-angle | I | One selected world master; requested directional outputs are not extra input references. | Image workflow adapter |
| First/last frame preparation | I if using Qwen Edit | Separate first and last outputs; references allowed by workflow. Four candidates per frame in manual selection, one for automatic, per existing plan. | Image pages/jobs and frame lineage |
| Character voice binding | A from enrolled voice catalogue | One assigned voice per character; same voice may serve multiple characters. Ordinary music/audio is not automatically a voice. | `character_voice_bindings.py`, `audio_catalog.py` |
| Text-to-video | None | Prompt/settings. No media picker unless user changes workflow. | T2V contract |
| First/last-frame video | I + I | One first image and one last image in distinct slots; optional inputs only if the selected adapter explicitly supports them. | `isolated_fl2va_contract.py`, assets adapter |
| Reference-to-video | I, V, A or compatible combinations | Local H3 compiler currently caps 9 images / 3 videos / 3 standalone audio refs. Other constraints, durations and combined rules still apply. Do not hard-code these counts as universal model rules. | `isolated_r2v_contract.py`, `minimax_h3_graph_compiler.py`, `minimax_h3_media.py` |
| Video Summariser / analysis | V | Bulk library selection; selected job settings and backend batch rules apply. Outputs may include I/V/A. | `video_repertoire.py`, worker/results adapters |
| Image Detailer | I | One image per analysis request; selectable repository images. No raw video/audio here. | `image_detailer.py` |
| Timed TTS / dialogue generation | Enrolled A voice reference where engine requires it | Dialogue text/transcript/timing tags; engine-specific voice requirements. | `audio_tts.py`, `audio_catalog.py` |
| Audio Studio — voice/effect processing | A | Source audio plus selected effect's voice/model inputs; not arbitrary video. | `audio_effects.py` |
| Voice enrollment | A + exact spoken transcript | Explicit enrollment into ComfyUI voice catalogue. Never auto-label an extracted music clip as a voice. | `audio_catalog.py:install_reference_voice` |
| Audio Reconstruct | A | One source recording for the selected dialogue take; character/transcript/part metadata retained. | `audio_reconstruct.py` |
| Audio Utilities — MP3 extraction | A or V | 1–100 compatible assets in existing staging contract; video must contain usable audio. Images excluded. | `audio_utilities.py:stage_assets` |
| Audio Utilities — noise cleanup / Demucs | A | Existing extension/settings validation; video requires a prior explicit audio extraction step. | `audio_utilities.py` |
| ACE-Step — text music | None | Tags, lyrics or instrumental mode, parameters, optional trained adapter. | Standalone `ace_studio.py`, runner |
| ACE-Step — reference/edit task | A | One reference, currently up to 240 sec; task-specific settings. No fake acceptance of video/image. | ACE settings/validation/runner |
| ACE-Step — LoRA training | A + paired text files | Matching MP3 + `_prompt.txt` + `_lyrics.txt` triplets; folder or multi-file import. Separate from reference music picker. | ACE dataset validation |
| Control-Foley — text audio | None | Sound prompt. | `control_foley.py:schema` |
| Control-Foley — text + video | V | One video + sound prompt. | Same schema |
| Control-Foley — reference audio + video | A + V | Separate audio and video slots. | Same schema |
| Vibe Editor chat / asset selection | I, V, A as contextual attachments | The executable edit plan is narrower than attachment support. Preserve current renderer validation; an attached image does not imply a supported image-edit operation. | `vibe_editor.py:validate_selection`, `validate_plan`, renderer |
| Assembly/export | V + optional A | Accepted ordered clips and supported optional audio tracks; not arbitrary image export. | Assembly contracts/renderer |
| Media Search | I, V, A browsing | Separate type views; audio voices and general clips retain separate sections and controls. | Media library + semantic search |

Before implementation, confirm each row against its exact current request validator and enabled workflow. Derive format/count help from existing backend capability/schema responses where available; add only the missing contract fields. Do not create a parallel catalogue of guessed limits. In particular, native file chooser filters are hints, not validation.

## 3. Source dropdowns and shared picker behavior

Use compact dropdowns above the existing previews/carousels, not a new navigation system:

1. **Location:** Current project; Another project… (searchable project selector); Shared repertoire; All available. On isolated screens, show Current workspace instead of inventing a project.
2. **Source:** All sources; Generated; Uploaded; YouTube downloads; Extracted/analyzed; Copied Story Builder media; Style references; ComfyUI voice library (audio/voice contexts only). Show only applicable values that can be discovered; distinguish empty from unavailable.
3. **Media category:** Only relevant role filters: characters, world masters/views, first frames, last frames; voices, dialogue, music, SFX, other audio. Analyzed is also a processing state: an uploaded or downloaded file can be analyzed without losing its original source.

Project is ownership/context; downloaded/uploaded/generated is origin; analyzed is processing state; style/character/music is usage/category. Keep these fields distinct even when the compact Source dropdown combines useful views. Downloaded items may already be in a project: union results without duplicate cards, retaining all origins.

Keep filename/semantic search, newest/oldest icon, card/list/carousel switch and previews from `notes.md`. Semantic unavailability must be explicit; filename search still works. Pinned style refs rank first in compatible categories but remain unselected. Cross-source search needs bounded/paginated results, not downloading every project's complete assets on each keystroke.

### Browse → select → use

- Existing project assets: browse read-only by `(source_workspace_id, asset_id)` and preview through the existing content endpoint.
- Repertoire/download/copied media not yet registered for the target: offer **Add to this project** / **Use selected** with source provenance and an import/link result. Reuse staged donor import, YouTube registration, and Comfy voice import paths.
- Execution currently resolves assets within a target workspace. Do not send a foreign ID alone and hope it works. Add one narrow server-side import/reuse operation for ordinary cross-workspace assets if none exists; return target asset IDs before updating the job form.
- First implementation may make a validated owned copy using existing registration code where zero-copy reuse is unsupported. Report a large copy before starting it; do not claim global deduplication. Reusing the existing YouTube shared-path registration avoids copying that source per project.
- Do not introduce generic filesystem links to bypass current anti-symlink/path checks. Shared-byte links require explicit asset resolver and deletion ownership support.
- Stable IDs, hash, source workspace/asset, original display name, timestamps, analysis references and role metadata survive imports. Keep occurrence-level annotations: two excerpts with identical bytes may have different source times/context.
- No directory walking or byte-copying on every render. Enumerate registered catalogues; explicit one-time registration for unindexed legacy files. Shared repertoire is a catalogue/view, not another automatic copy of every output.
- Cross-project deletion is never implied by selection. Archive/delete remains a separate explicit action and must honor references from other projects.

## 4. Select/deselect contract — every selectable collection

One control toggles **Select all shown** ↔ **Deselect all shown**, based on whether every currently shown eligible ID is selected. Add missing shown IDs, or remove shown IDs; retain selections outside the current filter. Show `N selected · M shown` and, if needed, how many selections are hidden. Empty views disable the control. “Shown” means the displayed page, not thousands of unseen search results.

For capped workflows, display remaining slots. If Select all shown would exceed the cap, disable it with a clear limit explanation; keep individual selection usable. Never silently select an arbitrary subset or auto-attach refs. Selection into a pending carousel list is separate from **Add selected** into the reference tray; final tray capacity is checked too. Per-reference instructions remain attached to the item, not its transient position.

Single-target slots use **Clear selection** / **Replace**, not select-all. Required slots can be cleared while editing; Generate stays unavailable with an explanation until valid. Changes of operation/workflow must identify incompatible selections rather than silently submit them. Persist chosen assets, instructions, source/filter settings and drafts across page navigation, scoped to the correct workspace/project/clip.

| Area to audit/update | Selection behavior / scope |
|---|---|
| Audio Utilities | Visible compatible audio/video batch toggle; cross-source picker |
| Video Summariser library, copied-video import, copied-analysis audio, extracted I/V/A results | Toggle on each independently selectable collection; preserve batch/delete boundaries |
| YouTube download search candidates | Toggle eligible candidates only, with existing job limits; download is a separate action |
| Media Search / repository selection where present | Same toggle if multi-select; pure browsing does not gain pointless checkboxes |
| R2V image/voice/audio/video carousels | Per-carousel pending toggle, category limits, Add selected; preserve user reference instructions and deterministic tags |
| Characters & Voices — enrolled voice import list | One toggle instead of competing Select all/Clear buttons; per-character assignment remains single-select |
| Characters/worlds/frames — reference lists and candidate choices | Toggle only for compatible multi-ref lists; one chosen candidate per target remains single-select |
| Audio Studio, Reconstruct, ACE reference, Image Detailer | Single-slot Clear/Replace and source dropdowns; batch only if backend already supports batch |
| Vibe Editor asset selection | Multi-asset selection consistent with actual editor plan/attachment contract; preserve clip ranges |
| Production Styles — documents and media evidence | Toggle per independent evidence collection; preserve instructions and version bindings |
| ACE training files | Show selected file/folder list with Remove and Clear all; no “all library media” because training needs validated matching triplets |
| Assembly clip/audio choices | Respect one accepted take per clip and ordered sequence; no bulk control that violates those invariants |
| Non-media selections | Automation stage checkboxes remain settings. Any bulk toggle must retain validation/parameter confirmation; do not treat them as media IDs. |

### Understandable imports and help

Audio Utilities currently has two inputs: individual files versus a whole folder. Replace browser-dependent visible labels with **Import files…** and **Import folder…** and a selected-file count/list. Folder import needs a browser capability fallback. Filter/validate folder contents with an explicit unsupported-file report, never silently skip training triplet members. Prevent double imports while busy; clear only after successful registration.

Provide short hover help after about two seconds, also available on keyboard focus; touch users get a small info control. Use shared themed tooltip behavior where it exists. Keep essential labels and restrictions visible; tooltips supplement them. Apply this audit to upload, Add, Run, reference-slot, sorting and view icons throughout the listed screens. Preserve browser file/folder permission boundaries and all three themes.

## 5. Storage audit — where things go today

Data root from launcher: `VIBE_DIRECTOR_DATA_DIR=<checkout>/local_data`. The API requires this configured root. Stable IDs, not editable story titles, identify folders.

| Data | Current authoritative path relative to `local_data/` | Notes |
|---|---|---|
| Story/workspace records, screenplay and many job relations | `storage/production/ledger.sqlite3` | Not just folders. Back up the database and corresponding files consistently. |
| Image job/selection state | `storage/production/image-jobs.sqlite3` | Preserve it when reorganizing files. |
| Saved story canon revision files | `<story-id>/production_v2/runs/<uuid>/story/revisions/` | Legacy path is actively read/written. Other authoring data also lives in ledger. |
| Uploaded story documents/previews | `story_imports/<import-id>/` | Separate from audio/image/video. |
| Workspace media manifests and imported bytes | `media-projects/<workspace-id>/production/assets.json`; `inputs/media/{images,videos,audio}/` | Per-workspace hash dedup for uploads; not a global object store. |
| Generated/derived media | `assets/<workspace-id>/...` | Images, video, generated audio, analyzer outputs and utility results use adapter subdirectories; manifests resolve them. |
| New and migrated YouTube download bytes | `donor_migration/video_repertoire/downloads/` | Existing shared physical store; target below fixes its misleading location. |
| Repertoire analysis, manifests, indexes, jobs, upload staging, clips | `storage/video_repertoire/` | Queue serves more than video; do not rename queue roots just for terminology. |
| Music project chat/settings | `ace_studio/state.json`; datasets/runs under `ace_studio/` | Independent music project links to media workspace. |
| Music engine Python environment | `ace_step/runtime/` | Source defaults into donor_migration/audio/song_gen/ACE-Step; checkpoints default to external cache unless overridden. |
| Editor chat/projects/style state and render intermediates | `vibe_editor/state.json`, `vibe_editor/projects/...`; runtime under `vibe_editor/runtime/` | Approved renders are registered under assets; staging is not automatically disposable. |
| Video pipeline intermediate/original files | `ltx_chunks/<workspace>/`, `t2v_originals/<workspace>/` | Originals may be needed for recovery/retakes. Do not blanket-delete. |
| Worker ownership/readiness and journals | `runtime/`, `logs/`, `storage/debug`, `storage/performance` | Preserve active ownership/leases; bounded log retention later. |
| Exports / operator reports | `exports/`; numerous audit JSON/JSONL files currently at root | Root clutter can be moved to reports only after checking references. Exports also include batch specifications, not just finished movies. |
| Migrated engines, weights, clips, skills | `donor_migration/`, `story_builder_resources/` | Mixed categories; not automatically rubbish or safe to delete. |
| Shared installed ComfyUI models/voices | External `setup_comfy_and-stuff/ComfyUI/` | Voices: `models/voices`, `models/TTS/voices`, suite `voices_examples`. Retain installed model/node setup. |

ACE checkpoints default to `~/.cache/ace-step/checkpoints`; auxiliary training encoders may be in Hugging Face cache. Respect configured overrides. Do not move these into every project or re-download them. A separate backend source `storage/production/image_workflow_smokes` contains small readiness evidence: do not confuse it with live data-root storage or move it indiscriminately.

## 6. Physical filesystem reorganization — revised owner requirement

**A logical library view alone does not satisfy this requirement.** Reorganize actual files and folders in the repository and its `local_data` tree. Minimize disruption, not the number of moves at the expense of a confusing final layout. Reuse application code; make the necessary narrow path/configuration changes. Do not preserve a bad permanent layout simply because existing code assumes it.

### Repository root audit and proposed destinations

The current root contains active source directories alongside `My idea`, `Vibe Editor`, `migration_plan`, `plans`, `PLAN.md`, `REUSE_AUDIT.md`, `images.png`, `graphify-out`, and `test-results`. These names indicate mixed concerns, but names alone do not establish ownership or whether a folder is obsolete. Inventory contents and references before deciding individual moves.

| Current root entry | Proposed physical organization | Required check |
|---|---|---|
| `frontend`, `backend`, `contracts`, `skills`, `tools`, `design` | Keep these clear functional source roots | Avoid pointless module/package renames. Audit misplaced files within them separately. |
| `plans`, `migration_plan`, root `PLAN.md` / `REUSE_AUDIT.md` | `plans/` with active plan index, `plans/migration/`, `plans/archive/` where appropriate | Retain decision history; distinguish current authority from superseded plans; fix links and agent instructions. |
| `Vibe Editor`, `My idea`, `images.png` | Classify contents into existing source roots, `design/`, or `plans/` | Never move runnable code as if it were a document. Determine what these contain first. |
| `graphify-out`, `test-results`, `.pytest_cache` | Generated artifacts under `local_data/reports/`, `local_data/test-results/`, or configured tool cache locations | Check Graphify/test runner output options and links. Keep required configured output paths if the tool cannot relocate them safely; document a justified exception. |
| `README.md`, `AGENTS.md`, `COLLABORATION.md`, launcher, `.gitignore`, license notices | Retain essential root entry points | Update references to reorganized files; no Git operations as part of this task. |
| `local_data` | Keep one configured data root; physically reorganize contents as below | Preserve database relations, media IDs and job recovery. |

### Proposed physical target

```text
Vibe Director/
  README.md  AGENTS.md  COLLABORATION.md  start_vibe_director.sh
  frontend/  backend/  contracts/  skills/  tools/  design/
  plans/                         # indexed active plans, migration plans and historical decisions
  third_party_licenses/
  local_data/
    projects/<workspace-id>/
      project.json               # optional small identity/title mapping if existing records need it
      story/                     # story imports/revisions, mapped from existing story identities
      media/
        assets.json              # existing asset manifest schema, relocated
        imports/{images,audio,videos}/
        generated/{images,audio,videos}/
      music/                     # workspace-owned datasets, generated adapters and run records
      editor/                    # workspace-owned editor projects/intermediates
      exports/                   # finished exports and associated job specifications
      intermediates/             # retained chunks/originals, clearly marked recovery data
    library/
      downloads/youtube/         # one authoritative YouTube download store
      images/  audio/  videos/   # shared owned media only, not copies of all project assets
      catalog/                   # existing shared manifests/indexes, adapted rather than replaced
    services/
      production/                # existing ledger and image-job databases
      media/                     # shared worker queue/jobs, analysis staging and service indexes
      music/                     # global music project registry/configuration
      editor/                    # global editor registry/configuration
    engines/                     # copied analyzer/music code and required bundled resources
    models/                      # only repo-owned model assets that need a canonical home
    runtimes/                    # relocatable environments, or documented fixed-path exceptions
    runtime/  logs/
    reports/  test-results/
```

This is a proposed destination taxonomy, not a claim that every folder exists or must be created empty. Use existing workspace IDs as the default project storage key; retain story/editor/music IDs as children or explicit mappings. Establish relationships from records, never title matching. Preserve current manifest schemas, URL contracts and asset identities where possible. Consolidate duplicated top-level stores rather than creating a second decorative tree.

There is real path-adaptation work: current imports and generated files resolve through different roots, story revision paths embed legacy structure, and music/editor have global state plus project-owned data. Inventory those relationships before assigning exact file destinations. Introduce or extend one shared path resolver/configuration layer, and adjust the affected consumers; do not rewrite the engines, create a new database architecture, or scatter replacement path literals across workers. Shared media keeps a single owner and references; project folders must not duplicate the entire repertoire.

Copied engines/resources under `donor_migration` and `story_builder_resources` must be classified into engines, repo-owned models, shared library, skills, or reports. Remove the transfer-era directory as an active permanent destination after migration coverage is verified. Required code/data must remain available without Story Builder or OpenMontage checkouts. Nothing is deleted merely because it was copied from a donor.

The retained external `setup_comfy_and-stuff` installation remains external. Do not move its models/voices or re-download weights. Python environments may embed absolute prefixes: inspect before relocation, and use supported environment relocation/recreation only if needed. Retain a documented fixed-path exception when relocation would impose unnecessary risk; do not blindly rename an environment or symlink around anti-symlink validation.

Readable names, scene/shot/clip/take/direction/seed labels and original filenames stay in metadata; stable IDs prevent unsafe paths and rename churn. No automatic cleanup of originals, weights, training sets, accepted takes or referenced clips.

## 7. Implementation packets — only after owner confirmation

**A — Catalogue and picker contracts.** Reuse media_library/media-api and existing dropdown/carousel controls. Normalize source/processing/category metadata, enumerate projects/repertoire and compatible kinds, add bounded cross-source listing/search and narrow target-workspace import. Retain existing content URLs and validate paths/hashes/roles server-side. Start with Audio Utilities and R2V; then apply the surface inventory above, including voice and training exceptions.

**B — Selection and labels.** One small shared toggle helper/control using stable IDs, then wire each listed multi-select collection. Single targets get Clear/Replace. Add import labels/help and accurate per-workflow counts/format messages. Do not restyle/rebuild completed pages.

**C — Physical layout and migration.** Inventory root files and data: owner, current readers/writers, embedded paths, destination and retained external dependencies. Produce a complete old→new dry-run manifest, including sizes, hashes, reference counts, collisions, free-space requirements, required code/config/link changes and exceptions. Include source/docs/tool-output reorganization, project media/story/editor/music data, shared downloads/catalogues, service databases and copied engines/resources—not only YouTube downloads. Owner reviews this concrete mapping before moves. Quiesce affected jobs/writers; back up consistent databases/manifests. Implement narrow shared path resolution, migrate one dependency group at a time, and update database fields, manifests, indexes, queued job specs, launcher/env defaults, recovery code, tests and documentation together. Prefer same-filesystem rename; verify hashes when copying across filesystems. Do not overwrite collisions. No symlink bypasses or silent fallback writes into retired directories. Preserve a reversible mapping/backups; do not duplicate large trees merely for rollback. Verify old projects and shared references after restart before retiring old paths. Final acceptance must show physically changed directories and no new writes to retired roots.

**D — Focused acceptance and handoff.** Test select/deselect with hidden selections/empty views/caps, workspace isolation and source reuse, same asset in multiple projects, content preview, accurate incompatible-media messages, persisted form selections, and delayed hover/keyboard help. For migration, verify old project open/restart, download playback, provenance/index resolution, job recovery, and one newly mocked download registration into the new store. Check delete/archive cannot remove a shared file still used elsewhere. No repeated 600-test suite and no provider/GPU/training job for planning. Prepare owner-clicked real examples later.

### What confirmation will approve

1. The input compatibility/source-dropdown rules and screen inventory above.
2. **Accepted by owner:** select-all/deselect-all-shown semantics; hidden selections retained; single slots use Clear/Replace. Capacity constraints remain enforced.
3. Physical repository/data reorganization with minimum necessary code disruption. Owner has required the physical cleanup; the revised destination map and migration preview still require review before actual moves.

No new implementation agents or routine Sol reviews. No Git work. The existing global goal is not resumed by this planning task.
