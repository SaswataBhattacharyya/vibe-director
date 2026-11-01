# Cleanup and media UX repair plan — 2026-11-01

Status: implemented and checked after owner authorization to restore the broken parts. Real provider/GPU generation remains owner-clicked acceptance. This extends `cleanup_regression_audit_2026-11-01.md`, with the current screenshots and source inspection. Follow the existing B4/D6 media-library reuse boundaries. No blanket rollback, restoration of deleted projects, new media copies, training or generation is needed for these repairs.

## What the controls actually do

- Editor and ACE projects hold tool sessions: conversation, settings, selected assets and edit/music state. They are distinct from story workspaces and must remain saveable/openable. Their current UI unnecessarily requires project creation before showing chat.
- “Media library / Tool library · no workspace” selects a backend ownership context. It is neither a folder browser nor an attachment picker. `tool-library` is the internal standalone-media namespace; it must not be sent to story endpoints or exposed as a prerequisite for using tools.
- Image Detailer already implements “Analyze selected image”, readiness, progress, results, cancellation/retry and saving search details. Its action toolbar follows the entire gallery, so 95 images bury the main action. It auto-selects the first image; clicking the selection again does not deselect. No bulk management exists there.
- Search library provides individual archive/restore and limited extracted-asset deletion, but no general multi-selection toolbar. Archive keeps files; it is not permanent deletion.
- Images home’s “Image Repository” opens Search library. It is a navigation shortcut, not another repository or storage root.

Authoritative source seams: `frontend/src/VibeEditorPage.tsx`, `AceStudioPage.tsx`, `MediaPrepPage.tsx` (ImageDetailer/ImageHome), `MediaLibraryPage.tsx`, `lib/media-workspace.ts`; backend `media_library.py`, `video_summarizer_results.py` and `ace_studio.py` under `backend/story_builder/services/`. Confirm callers with Graphify and current source before implementation.

## Intended user experience

### Editor, ACE and other tool sessions

Show the existing Director conversation and appropriate controls immediately. Replace the prominent project/library setup block with a compact session toolbar: **New**, **Open**, editable session name and save status. Keep existing sessions accessible. Create the durable tool session at the first action that needs persistence, before sending a message or saving settings; reuse existing project APIs and prevent duplicate creation on repeated clicks. An empty session must not launch providers, generation or training. If creation fails, retain the draft and show Retry.

Use **Browse media sources** for attachments, with previews and removable selection chips. Preserve the Editor’s clip ranges, saved selections, style commands, approval/revision checks and render/export sequence; preserve ACE’s Create/Fine-tune/Styles/Audio & models/Connection controls. A session’s optional story link belongs in collapsed session details, independent of input sources and output location. Do not merely rename the ownership dropdown and leave its coupling in place.

Add **Back to Media Prep** above Vibe Editor. Retain panel hide buttons, width sliders, spacing and responsive behavior. Use Audio tools as the immediate parent for audio subpages.

### One library with clear sources

Keep one shared catalogue. Media Prep → Images should open the existing library with Images active; remove the extra landing-page choice between two apparent repositories. Keep a clear **Image Detailer** action on image cards/selection. Preserve old image-home and repository links by routing them to the same Images view; no data migration is involved.

Replace user-facing “Tool library” wording with **Shared media** where a collection scope is useful. Use the source browser for **Video repertoire**, **YouTube downloads**, **Folders on this PC** and named **Workspaces**. Scope filtering is optional; attaching an item must not require moving it into a story. Present a workspace choice only when linking to that workspace is the actual operation. Keep custom output-folder selection separate.

### Image Detailer

Use a bounded, scrollable gallery beside a selected-image preview and analysis/report area. Keep **Start analysis**, depth and readiness visible above the gallery or in a persistent action bar, with an explanation when disabled. Start analyzes exactly one explicitly selected image; no silent first-image selection. Provide visible selection state and **Deselect**. Show progress, Cancel/Retry and the resulting report beside the selection. Retain saving analysis/tags and semantic indexing; none runs automatically on selection.

Use consistent image management controls: checkbox selection, selected count, Select all shown, Deselect all and Delete selected. Separate the single active image for analysis from bulk management selection; enable Start only for one analysis target. Clear deleted targets and stale reports correctly. Do not imply batch analysis is supported.

### Search/library management

Add the same visible multi-selection controls for images, videos and audio, including list/card/carousel views. “Select all shown” means the current filtered results, with its count; changing scope clears selection. Attach/use-selected actions appear in a picker; the standalone library offers the relevant analyze/open actions. Card preview and checkbox selection must be distinct interactions.

Keep **Archive** explicitly reversible. **Delete files permanently** requires a confirmation showing file paths, item count and affected workspace/session references. Resolve all references before deletion; do not silently leave broken saved selections or silently substitute archive for deletion. Treat removing a workspace membership as a separate action. Keep original source videos when deleting only extracted frames/clips. External folders and shared records must use their appropriate validated deletion APIs; no broad folder deletion or arbitrary-path endpoint.

## Repair order and boundaries

1. **Snapshot and inventory.** Record current registries/catalogues, relevant hashes/counts, two retained analysis jobs, nine ACE training runs and Trial 1 Scar storyboard. Save bounded metadata backups and a repair journal. Do not restore owner-deleted media/projects. Preserve the dirty working tree.
2. **Shared data actions first.** Repair owned shared-record resolution for annotations, roles, archive, analysis saving/indexing and source publication. Keep stable IDs, path resolution, source hash validation and per-workspace overrides. Establish deletion/reference behavior before exposing bulk deletion. A readable thumbnail is not proof its actions work.
3. **Recover retained ACE adapters.** Reconstruct verified adapter metadata from retained run/checkpoint evidence into tool-level registration. Group checkpoint versions by training run; do not treat 82 versions as 82 styles. Do not resurrect deleted sessions or retrain. Flag ambiguous checkpoints instead of guessing model compatibility.
4. **Fix context recovery.** Validate cached story/tool/session IDs against available records; remove stale pointers while preserving recoverable text drafts. An explicitly missing deep link needs a recovery choice, not a silent switch to a different story. Separate optional story context from shared media ownership across Story, Screenplay, Setup, Characters, Worlds, Frames, Create, Take, Audio Studio and Jukebox.
5. **Repair session entry.** Make Editor/ACE usable without forced project setup, using the existing APIs and saved-state formats. Add the parent navigation button and consistent media attachments. Verify existing session reload before proceeding.
6. **Repair library/Detailer UX.** Reuse existing gallery, picker and analyzer services; add the explicit actions and consolidate navigation above. No analyzer, editor or execution-service rewrite.

## Finite verification and release gates

- Use disposable data to verify shared-only and workspace-owned assets through list → preview → select → annotate/use → analyze publication/save → reload. Cover ownership isolation, missing files, duplicate catalogue membership and partial deletion failure.
- Confirm the two retained analysis histories and their outputs remain available; all 244 retained catalogue records still resolve. Verify recovered ACE adapter paths without loading models.
- Test Editor/ACE fresh entry, first-message session creation (mock provider), rapid repeated actions, saved-session reopening, deleted cached IDs and failed persistence. Ensure conversation and controls remain visible.
- Browser-check Image Detailer with a large gallery: Start visible, explicit select/deselect, report tied to the right image, disabled reason, bulk selection and confirmation. Mock analysis; owner clicks any real GPU acceptance later.
- Browser-check library filters, all view modes, attachment chips, deletion cancel/failure and old navigation links. Audit touched pages for parent navigation, meaningful labels, visible primary action, usable empty/error states, padding and narrow layouts.
- Run focused regression tests and production build; refresh Graphify after code changes. Use Playwright MCP when available; if its profile remains busy, report that error and use an isolated browser without disturbing the owner’s session.
- Ship in the bounded steps above, verify each producer-to-consumer path, and record actual evidence in `HANDOFF.md`. Do not declare completion from test counts, thumbnails or page shells. No unrelated feature additions, dependency upgrades or storage cleanup during this repair.


## Implemented result and evidence — 2026-11-01

- Editor and ACE show chat and controls immediately, save a tool session lazily on the first durable action, preserve failed-message drafts, and reopen saved conversations. New/Open/name and optional story context stay in the compact session toolbar. Editor has Back to Media Prep; attachments use media browsing with removable selections.
- Shared-only media now support owned metadata writes and derived-analysis publication through the existing library. IDs, physical paths and ownership checks remain intact. Permanent deletion has preflight reference/path/hash checks, explicit confirmation and partial-failure reporting. Files with detected saved references are blocked; this repair does not rewrite those saved uses automatically. Removing an analysis does not silently delete or archive retained shared outputs.
- Recovered eight complete ACE trained styles in a global adapter registry, grouping checkpoint versions; verified paths, safetensors headers and retained hashes. Incomplete runs were excluded. No deleted project/session was resurrected. Journal: `local_data/reports/cleanup-ui-repair-20261101/adapter-recovery.json`.
- Cached removed workspace/session IDs recover without treating the shared library as a story. Explicit missing story deep links retain their error. Story, Screenplay, Setup, generation assets, Create/Take, Audio Studio and Jukebox received focused context checks.
- Images navigation uses the existing shared library. Image Detailer has explicit analysis selection/deselection, visible depth/Start/readiness controls, a bounded gallery and adjacent preview/report. Library and Detailer expose management selection, select-all-shown, deselect and confirmed permanent deletion. Scope/filter changes clear management selection.
- Live retained state: **244 files** resolve with matching recorded sizes (95 images, 128 videos, 21 audio; 68 YouTube downloads + 176 repertoire outputs). Both completed analysis histories are visible. Trial 1 Scar storyboard SHA256 remains `3f9b73c0b3c5440dba00380e9af189ad1f07920db1062d8963da2d36efbcafd3`.

Verification: 59 focused backend tests, six isolated mocked browser tests (including saved-session reload, failed first save/retry, Detailer admission and deletion cancel/failure), production build, 32 read-only route visits with fresh/stale caches and no API/uncaught-JS errors. Live image/video/audio previews return HTTP200. Desktop and narrow screenshots confirm no horizontal overflow; selected Detailer preview and visible Start were inspected. Graphify refreshed. Build retains the existing large-chunk advisory.

Evidence retained under `local_data/reports/cleanup-ui-repair-20261101/evidence/`. Playwright MCP could not initialize because its browser profile was already in use; isolated Playwright Chromium was used without touching the owner's browser. UI interactions that would call providers, generate/analyze media, or delete real files were mocked or blocked. No GPU/training/provider acceptance or live media deletion occurred. API was reloaded idle preserving args/environment (PID2095492, port3020); log `local_data/logs/shared-library-repair-reload.log`. Frontend8082 remains running.

Remaining acceptance: owner refresh and normal use, including explicitly owner-started provider/GPU work. This is bounded regression repair evidence, not certification of every unrelated feature. Previous deleted conversations/projects are not restored because their deletion was explicitly requested. Historical backup rollback would undo that request and must not be applied blindly.
