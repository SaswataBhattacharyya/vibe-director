# MED01–MED03 — One media browser, typed bindings, project memberships

**Status at 603b1fcb (2026-11-06): proposed; not implemented.**
Basis: MediaSourcePicker.tsx, LocalImageFolderBrowser.tsx, EditorAssetBrowser.tsx, MediaLibraryPage.tsx, App.tsx R2V code, lib/media-api.ts, services/media_library.py and media_discovery.py, output_destinations.py, storage_paths.py. Read latest code before editing. The user wants a single elegant source selector across pages, not loss of R2V/reference, voice, YouTube, scene, Editor or Media Prep capabilities.

## Product UX: one universal selection surface

On every content-generating page and inside the Director composer, provide a small stable **Media** trigger/icon with selected-chip count. Opening it displays one roomy modal/drawer/pane anchored to the right-hand work surface; it must not force a third permanently visible subcolumn.

**Header:** Search media… | media type chips All / Images / Audio / Video (available kinds restricted by the caller) | project scope Current / Other projects / All / Shared | source folder breadcrumbs.

**Filters (progressive disclosure):** source Imported / Generated / YouTube downloads / Extracted / Repertoire / Style references / ACE audio; audio category Voice only / Dialogue / Music / SFX; Indexed/Analyzed only; date Newest/Oldest, name A–Z; optional source-specific character, scene/shot, selected workflow, version; keyword vs semantic only when indexed embeddings are actually available. A filter must be accurate, combinable, countable and clearable, and display 'not indexed/unavailable' rather than pretend search succeeded. The current backend browse_catalogue supports newest/oldest only; name sort and analyzed/voice category filters need backend or bounded client support with correct pagination totals.

**Body:** Grid (default), list, carousel; high-quality thumbnails, audio waveform/player where available, lightweight MP4 hover/keyboard preview, filename/size/duration/dimensions, source and project chips, indexed badge and safe missing/offline status. Multi-select with selected count and clearly available quota. Empty/error/reload states and keyboard navigation. Current selected items remain stable while changing folder/filters where permitted.

**Footer:** Target-aware action, e.g. "Attach 2 to chat", "Use 2 as image references", "Add 3 clips to Editor", "Use as first frame", "Add selected to project". Inapplicable actions disabled with explanation. A quick action to upload files, choose local folder, browse existing project, or import a shareable source. Choosing a File System Access folder requires the user's browser consent; it is not automatically indexed outside approved roots.

The library UI should not show permanent delete buttons in its generic selection mode. Put deleting, relinking, archive and destructive bulk management in an explicit Library management surface with current confirmations and dependency previews.

## Separate media ownership vs intended use

Define/keep four distinct layers:

A. **Physical asset occurrence:** verified storage locator + digest/size/media metadata, optional analyzer provenance, folder registration; never expose server-absolute path as trust grant to the frontend. Same SHA does not prove it is the same physical occurrence/permissions.
B. **Project membership:** a project may *refer* to the same verified occurrence as other projects; a project uses stable project-scoped pa-* IDs or an additive join mapping, roles/annotations/preview state, provenance and availability. Do not rewrite existing pa-* identities. Membership changes must not silently move bytes.
C. **Selection intent:** an ephemeral or saved browser selection with owning workspace + current route/session + actual destination. Browsing does not imply applying. Chat attachment, model reference, Editor media range and project membership are **different** actions.
D. **Immutable job/model binding:** once a request starts, freeze exact project, selected occurrence, asset ID/SHA, reference role/slot, model workflow/validator, output destination and permissions. Project membership edits may not change a frozen job.

**Suggested typed boundary (conceptual only):**

    MediaPickerRequest = {
      workspace_id, allowed_kinds: [image|audio|video],
      destination: chat_attachment|model_reference|editor_range|tool_asset|project_membership,
      model_profile?, permitted_roles?, max_items?, current_selection?
    }
    MediaChoice = {
      source_workspace_id, asset_id, expected_sha256,
      destination, target_role?, target_slot?, intent?, editor_range?
    }

Do not send arbitrary filenames/paths to execution services. Server resolves ID -> current authorized occurrence, checks digest, selected owner/target/project, validates exact workflow caps and role, then returns *registered* target IDs/revision as appropriate. Preserve existing API response shapes for old callers; add adapter routes/types only after tests.

## How each target behaves

**Chat attachment:** attach an existing registered image/audio/video asset to the one Director conversation. Chat can show thumbnail/player and ask questions; attaching does NOT mean the model received or analyzed raw bytes unless an actual authorized analyzer is invoked. The current DirectorConversation 'Context & skills' whole-asset checkbox selector should be replaced by/launch the shared picker, while context and skill selection remain available. Project/session ownership is checked; don't attach another workspace's path without explicitly bringing it into this project using existing verified reuse APIs.

**Image model reference:** choose 1–3 compatible images for Qwen Edit or exact model caps. After choice, display compact reference chips with role, intended effect and remove button in creation form. Reuse verified image registration and current image workflow validators; do not interpret attaching to chat as a generation reference.

**Video model reference:** preserve R2V's existing rich typed experience (App.tsx ~1080–1165). Images, audio and video are three **type filters in one source browser** but become separate role-specific **binding trays** only for workflows supporting multiple modalities. Preserve current R2V distinct limits (images up to 9; videos up to 3; audio references up to 3 subject to existing paired-soundtrack accounting), duplicate refs checks, speaker mapping, intent, model slot order and source constraints. FL2VA first/last frame are conditioning endpoints, not the same thing as an R2V general visual reference. T2V without references needs no reference tray. Never manufacture unsupported fields or bypass R2V exact char/duration restrictions.

**Editor:** picker can add owned assets, then exact in/out ranges and expected Editor revision are chosen/validated in Editor controls. Avoid implicit 0–5 s trim when the user explicitly selected another range. Attachment to Director and adding to Editor selection are separate actions. Existing edit session/approval flow remains authoritative.

**Audio:** voice-only filters must combine audio_category, roles (voice_master), comfyui_voice_catalog, transcript/enrollment metadata where available. A voice file is not automatically a dialogue sound track; identity reference and synthesized spoken text are different. Preserve Media Prep audio handling and own voice-library discoverability.

**Folder / imported files:** unregistered local file is not a fully recognized project asset until registration; fingerprint, validate supported format, size and permission with existing upload/discovery infrastructure. LocalImageFolderBrowser uses browser DirectoryHandle and currently can permanently delete; retain trusted explicit folder reading/upload behavior but do not import deletion into universal picker. No uncontrolled host drive scans.

## Source reality: reuse today's code

- MediaSourcePicker.tsx **already** implements global/current/all projects, source categories, folder navigation, query, paging, card/list/carousel, newest/oldest, verified reuse and 'make a copy'. Refactor as a core browser with a thin target-aware adapter, not a second new catalogue.
- MediaLibraryPage.tsx already has voice-files/audio-clips filtering, per-kind search and content-index/annotation management; extract shared controls/metadata interpretation, retain its management functionality.
- App.tsx R2V already has model-specific classification, speaker refs, semantic searches, style rankings and reference editing. Retain this **engine binding** while moving its browse logic out of the large parent to reusable picker/search hooks. Do not flatten reference-specific validation.
- LocalImageFolderBrowser.tsx already has actual browser directory access; use as an import source adapter only after preserving its consent, relative paths and error behavior. Keep its delete flow in management if still required.
- EditorAssetBrowser.tsx has selection, preview, import and explicit deletion. Share browse/view components, retain current Editor exact selection/range APIs and deletion checks.
- Other call sites: ImageAssetsPage, TextToImagePage, Video Create, VibeEditorPage, MediaPrepPage, MediaLibraryPage, TrellisPage, PromptPreparationPage and the Director conversation. Inventory imports before deleting wrappers.

## MED02: stable indexing, richer filters, fast search

Current services/media_library.py::browse_catalogue calls media_discovery.discover() when browsing broad scopes, then loops tool and project assets manifests. Its keyword query searches filename/description/tags; source/extracted classification is not equivalent to 'analyzed successfully'. media_semantic_search.py search_workspace is **workspace-scoped**, not proven global semantic retrieval.

Plan:
1. Preserve current browse endpoint/metadata, add an optional v2 query/filter contract that merges actual parsed metadata filters: kinds, source, source workspace(s), source folder, audio_category/voice markers, analyzer run/status/index freshness, tags/role, created-at date, name sort, paged results. Filter BEFORE paging and return trustworthy total.
2. Separate **registered** source occurrences from approved **discoverable** roots. Sync/index on controlled import, job completion, user-requested folder refresh, or bounded background jobs. Do not assume OS filesystem event watching or full-home indexing. Track freshness, last indexed timestamp, original path locator only server-side, stale/missing state, source SHA, analyzer version and derived embedding provenance.
3. Reuse existing annotation/content index workflows and link searchable embeddings to asset digest; no invented 'analyzed' badges when no validated result. Global semantic search is a separate verified capability: consider per-workspace federated searching with owner permissions before building a new global vector index.
4. Security: root grants, non-symlink verified paths, no ../../../ traversal, do not index hidden temporary/utility_inputs, no leakage of other projects' private storage from unauthorized contexts. Bound scanning budget and file count, don't hash huge files on every render. Cache invalidation on refresh/change, no automatic paid analysis.
5. Performance acceptance: fixture with multiple projects and 1k registered mixed assets, repeat query/pagination/sort tests; verify no missing/duplicate rows across pages and source switch, index staleness accurate, scope checks on every asset. Measure browse latency before declaring fast.

## MED03: one asset, multiple project memberships **without destroying legacy identity**

The existing backend has shared storage_location reuse via _link_shared_asset, preserving SHA and a source link for shared occurrences. But in media_library.reuse_catalogue_asset(), ordinary project files without reusable storage_location fall into copy/deduplication; therefore "reference, never copy" is **NOT** uniformly implemented.

Propose a compatible overlay/join (JSON or SQL only after actual project-snapshot review):
- One immutable physical occurrence identity/verified locator; source owner/permission, SHA, current availability.
- Many per-project memberships with their own stable pa-* asset ID, role, tags/description override, added_at, source project link, and reference/copy mode. UI shows all membership project names and the origin project; renaming a project must not alter IDs or physical locator.
- Reference reuse must not copy bytes but must verify source location access, hash and lifetime. If source storage is unportable/ephemeral, offer an **explicit copy/import** fallback; do not pretend a reference is safe. No silent cross-project sharing for private projects without local authorization.
- Deletion from one project should usually unlink only that membership, not delete shared bytes. Source-owner deletion must check current members, frozen job dependencies, Editor sessions and published output. Protect source and require explicit elevated confirmation before removing final physical bytes.
- Preserve previous project per-workspace assets.json manifests, pa-* IDs, SHA indexes and project Save/Load: migration additive and reversible; old jobs must continue resolving. Saved/moved project import may require relinking missing external source or explicit verified copy. Do not pin private absolute paths inside portable snapshots.
- Avoid duplicate semantic/content analysis on shared bytes when safe to share: immutable digest-qualified analysis may be referenced across memberships; project-specific tags and permissions stay separate. Never mix analysis revisions from different content hashes.

**First vertical slice:** two fixture projects, one PNG/WAV/MP4, add to second by reference without writing a second media file, distinct project-scoped identity/annotations, browsing shows both project chips and correct origin, delete one membership leaves original and other usable; Save/Load and a frozen job still resolve. Only after passing add cross-project UI affordances.

## MED acceptance checklist
1. Source → picker → select → target role/slot → Save/Apply uses the **correct old validator** for each app surface.
2. Chat attachment does not alter R2V refs or Editor ranges. Switching target preserves valid selection and clearly resets invalid roles.
3. Current/all projects, imported/generated/YouTube/analyzed/voice sources, folders, chronological sort, name sort, grid/list/carousel, pagination, indexed status and unavailable file handling are truthful.
4. Changing selected workspace/session during a pending reuse cannot apply a result into another project; frozen hashes validated server-side.
5. No duplicate media files unless explicit copy; no dangling references when source removed; no filename-only join; no surprise deletion.
6. Media Prep and all existing voice/video/image engines still work. GPU/paid analysis is never triggered by opening a picker.
7. Tests use disposable isolated TXT/PNG/WAV/MP4, project manifests and database; assert cleanup even on injected error. Preserve real media.

**Dependencies:** MED01 (UI reuse) can precede MED02/03 as long as it reuses truthful existing API scope. MED03 is higher persistence blast radius and should be separately approved after impact/schema/backups. No whole-app rewrite or new mega-library monolith.
