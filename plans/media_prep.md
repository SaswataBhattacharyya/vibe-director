## Owner correction — 2026-10-22 — one YouTube source store

YouTube originals live only in `local_data/donor_migration/video_repertoire/downloads`. Workspace libraries and analyzer source manifests link to that file, retaining their asset IDs; analysis outputs remain separate. Downloads do not trigger analysis. Selecting a completed analyzed source offers Yes/No to open its saved Results job; No stays on the current page. Delete analysis removes its derived outputs/result and analyzed relationship while retaining the original so it can be selected again. Workspace selection still determines library membership and analysis scope.

# Media Prep — video, audio and image workspaces

## Owner correction — 2026-10-14 — image assets and reference sources

Video Summariser now has Image Assets beside Video Assets and Audio Assets. All three extracted tabs provide item selection, Select all shown/Clear selection, Delete selected and Delete all. Delete all includes search-hidden assets of that tab in the current workspace; confirmation shows scope/count. Deletion uses the existing guarded asset API sequentially, reports failures, and removes successful items from catalog-backed Results. Per-extracted-image trash controls are also in Results and Search library. Deletion removes that published frame and its verified concrete run-local frame; original downloads, siblings and analysis metadata remain. Complete Delete analysis remains available for all run outputs.

Video Create keeps three reference sections (Images, Audio, Videos), each with one source dropdown and one visible carousel. Images: characters, worlds, first/last frames, extracted Image Assets, downloaded/imported images. Audio: voices, Audio Assets, downloaded/imported audio. Video: Video Assets, downloaded/imported videos. Existing generated audio/video references and pinned production-style recommendations remain usable; derived metadata distinguishes extracted assets, public origin distinguishes imported originals. Selected references/role instructions/paired soundtrack numbering remain intact while changing sources. Category uploads use the matching role. New originals use inputs/media/images, inputs/media/audio, inputs/media/videos within the existing workspace; prior files are not moved.

SAM Audio is separate from SAM/SAM2/SAM3 image-mask nodes. Actual ComfyUI node catalog has the latter, no SAM Audio nodes. Vibe reports checkpoint_present=false, worker_configured=false. UI explains this and the temporary preview/listen/save workflow. No install, model download or inference was performed.

## Owner correction — 2026-10-14 — extracted assets and search

Video Summariser includes **Video Assets** beside **Audio Assets**. Source downloads/uploads stay in Library; derived clips never enter the source analysis picker. Completed sources are marked analyzed and excluded from new analysis; deleting that analysis permits reanalysis. Results and both extracted tabs expose permanent per-video/audio deletion with confirmation, retaining original sources and sibling clips. Extracted frames are saved; no per-frame deletion requested here.

A source video's full summary describes its complete extracted video group; a semantic summary hit returns every surviving, nonarchived clip in that run, including through shared pickers. Rank/paginate semantic records before expanding groups, so a page limit does not silently cut a group in half. Audio uses its own event/clip/transcript semantics; only clips without meaningful local text inherit the video summary. Downloads retain title/metadata search and receive no automatic analyzer semantics. Explicit existing user indexing remains available.

## Notes-integrated correction — 2026-10-11

Media Prep & Library contains full Video Summariser nested views, four Audio tools, separate Image Detailer and separate Search. Search offers Videos, Images and Audio; Audio has Voice Files above Audio Clips, with independent name/semantic search, date sort and card/list/carousel views. Newest by default, explicit semantic fallback. Shared repertoire stores all annotated outputs. Reuse typed preview/search primitives in generation pickers; voice enrollment is explicit.

Read [remaining_app.md](remaining_app.md) for task order/reuse and [OWNER_DUMMY_RUNS.md](OWNER_DUMMY_RUNS.md) for owner-clicked acceptance. This correction overrides conflicting older sections below; historical implementation checkpoints are not completion evidence.


**Status:** Current product plan based on the user's request and source inspection on 2026-10-08. This is planning only; it does not claim the reorganized UI is implemented.  
**Name:** Use **Media Prep** for the top-level area. It includes preparation, analysis, generation/repair tools and repositories. Keep the existing tool names inside it so familiar capabilities remain easy to find.

## 1. Purpose and scope

Create one separate Media Prep destination containing three areas: **Video**, **Audio** and **Images**. Reuse the existing Story Builder tool pages and their working backend operations, and improve navigation, layout, repository access and saved-output metadata.

Media Prep is an auxiliary workspace. It is not a required page in the main Story → Screenplay → optional visual preparation → Video Generation journey. A user can prepare reusable assets before, during or independently of a story project, and then select them from the story's compatible reference pickers.

The main work is arranging the existing UI and connecting its outputs consistently to the shared media library. The requested image repository and common asset/search integration are additions where the existing pages lack them; reuse current storage/analysis services wherever possible rather than rebuilding engines.

## 2. Navigation and page arrangement

```text
Media Prep
  ├─ Video
  │    └─ Video Repertoire & Summariser
  │         Library | YouTube Download | Analyze | Results | Audio Assets
  ├─ Audio
  │    ├─ Audio Repository
  │    ├─ Audio Studio
  │    ├─ Audio Reconstruct
  │    ├─ Music & Sound
  │    └─ Audio Utilities
  └─ Images
       ├─ Image Repository
       └─ Image Detailer
```

The top-level page provides the Video/Audio/Images selector and remembers the last active tool. Each area owns focused tool pages or tabs rather than placing all forms on one long screen. The screenshots show the existing tool contents to preserve; their current crowded global navigation is reorganized into this hierarchy.

“Audio Reconstruct” was listed twice in the request. Treat that as one existing tool/page, without creating a duplicate destination.

Keep project selection visible for tools whose existing backend needs a project. Repository browsing remains separate from project assignment. Retain context when moving between tools, and provide a return link when Media Prep was opened from a story's reference picker.

## 3. Video — preserve Video Repertoire & Summariser

Use the existing **Video Repertoire & Summariser** page as shown in the first screenshot. Both the old Video Repertoire and Video Summariser navigation entries resolve to this one tool rather than becoming competing libraries.

Preserve its internal workflow and tab names:

- **Library:** upload/register videos, import existing sources, browse previews and source details, select items and perform supported library actions.
- **YouTube Download:** existing source lookup, review and download controls, task state and history.
- **Analyze:** existing scene/cut detection settings, direct video analysis, optional audio-analysis switches and job controls.
- **Results:** existing timestamped summaries, scene/clip information, transcript/audio evidence, analysis runs and searchable reference results.
- **Audio Assets:** existing derived audio collection, playback, grouping, source timestamps and supported sound-isolation/review actions.

Preserve capability/readiness indicators and existing progress, cancellation/retry and saved-job behavior. Moving this tool into Media Prep must not alter its analysis meaning, rerun completed analysis or remove its controls. Existing detection and summary data remain linked to source media and timestamps.

Video search continues to reuse the current keyword/semantic and curated reference functionality. Show genuine semantic readiness; existing word search remains available when embeddings are unavailable. The generation-page picker consumes these saved annotations/search results rather than inventing a separate video catalogue.

Existing “Send to Manual Director” hand-off controls are adapted to **Use as reference** or **Add to current clip** in the new journey. This transfers an asset selection/context link; it does not start a generation or choose a reference's creative role silently. Maintain compatibility links only where needed during UI migration.

## 4. Audio — preserve four tools and provide one repository entry

The Audio area contains **Audio Studio**, **Audio Reconstruct**, **Music & Sound**, and **Audio Utilities**, plus a common **Audio Repository** view. The repository consolidates access to curated audio, voice references and reusable audio extracted/generated by the tools. Existing stores can be exposed through shared asset records; displaying them in one repository does not require copying every file.

### Audio Studio

Reuse its existing sections, retaining available controls and results:

- Voice/model/system catalogues and runtime discovery.
- Reference-voice import with name, source audio and exact transcript.
- Character–voice mapping.
- Timed multi-character text-to-speech and existing timing/voice settings.
- Audio effects such as supported repair, cleanup, voice conversion, emotion/style operations.
- Split, replace and stitch audio.
- Existing F5-TTS dataset preparation controls and their current availability status.

Arrange these as focused subsections within Audio Studio, preserving the existing generation pipelines. Character mapping must share the same canonical bindings used by `char_world.md`; a second tool view must not create a separately editable conflicting map. Shared voice files remain assignable to multiple characters.

Voice Files combines workspace-enrolled voice assets with the configured ComfyUI voice catalog without relocating catalogue originals. Catalogue entries are read-only previews streamed by validated voice ID; never accept a filesystem path from the browser. They support name/metadata search, date order and Template/List/Carousel views. A Director can explicitly copy a selected catalogue voice into the current workspace; it then becomes a normal `voice_master` asset for character assignment, annotations and optional semantic indexing. Browsing alone never copies files or changes bindings. Unimported ComfyUI catalogue entries remain keyword-searchable only.

### Audio Reconstruct

Reuse the existing character calibration, dialogue-part preparation and raw-take upload/history UI. Preserve project/character/part identities and immutable take behavior.

Keep currently available reconstruction controls; do not promise unsupported recording, recognition, processing or acceptance actions solely because the page is being rearranged. Backend gaps found during reuse are implementation tasks recorded separately from layout changes.

### Music & Sound

Reuse ACE-Step music generation (instrumental/song, prompt/tags, lyrics where appropriate, duration and settings), Control-Foley sound-effects modes, result playback and job state. Keep existing dataset/fine-tune preparation controls and their current readiness; navigation changes do not turn preparation into supported full training.

Save music as music assets and Foley as SFX assets, with prompts/settings and source references retained for search and later generation use.

### Audio Utilities

Reuse the `/audio-tools` interface and current operation contracts:

- Curated audio import, hash-based duplicate detection, playback and filename/tag search.
- Batch speech-noise cleanup.
- Video-to-MP3 extraction.
- Demucs stem separation.
- Existing file/folder selection, output collection, quality/model/stem/device controls, capability state, progress and output listing.

Expose curated audio through the common Audio Repository as well as the Utilities context, using the same assets. Preserve originals and save transformed outputs as linked derivatives.

### Audio Repository

Show playable audio entries with names, descriptions, duration, category, source and tags. Include generated/imported voice-only audio, dialogue, music, SFX, ambience and other/mixed audio without forcing incorrect classification. Multi-label categories are allowed when content is mixed.

Provide search over readable descriptions, filenames, tags, transcript and available annotations; support newest/oldest ordering and type filters. Integrate existing audio search/indexes where present and add missing metadata/search adapters as necessary. Do not label filename-only filtering as full SEO/content search.

Reference-voice transcript and speaker identity remain distinct from a general descriptive annotation. Extracted video audio retains its parent video and source interval. Audio assets created in the Video tool appear in the same Audio Repository through shared IDs/links rather than duplicate imports.

## 5. Images — Image Repository and Image Detailer

Provide a persistent **Image Repository** with the same browse → inspect/analyze → search → select/use pattern as Video and Audio.

### Image Repository

- Import/upload images; support file selection, drag-and-drop and image clipboard paste.
- Display thumbnail cards with title, readable description, dimensions, tags, source and analysis state.
- Include uploaded images, saved Image Detailer inputs/results, and generated character/world/clip-frame images from the main story journey via their existing asset links.
- Filter by useful roles: character, world/location/background, first frame, last frame and other. Display scene/shot/clip/character associations where present.
- Search descriptions, filenames, tags and saved analysis; sort recent/old with a reversible control.
- Open an image for full preview, metadata, analysis and reference use. Unanalyzed images remain browsable and usable; mark missing descriptions/analysis honestly.
- Preserve asset IDs, role and source links when selecting an image for a generation task; the repository does not silently make an unrelated image a first/last-frame asset.

The inspected `ImageDetailer.tsx` contains analysis/result UI but not this repository interface. Add the repository around the existing detailer and shared asset services rather than pretending it is already present.

### Image Detailer

Reuse the current image upload/selection, quick/balanced/deep analysis modes, Qwen-based analysis, optional vision evidence, progress/cancel and result display. Allow input from the Image Repository as well as local files and supported saved frames.

Save the input asset, analysis result JSON, readable description, extracted searchable tags/attributes and analysis provenance together. Link each analysis run to the existing image ID; repeated analysis produces a new analysis revision, not another copy of the image.

Present readable findings with an optional structured JSON/evidence view. Keep the current available evidence and model warnings visible. Descriptions are model interpretations; dimensions and technical properties are measured metadata. User corrections remain traceable and can improve searchable descriptions.

## 6. Shared media storage, JSON and readable descriptions

"One place" means one coherent media catalogue/storage interface with typed Video/Audio/Image collections. Existing physical files can stay in their working locations during migration and be registered through adapters, but Vibe Director must not depend on files inside the Story Builder or OpenMontage checkouts at completion. Copy only the runtime assets Vibe actually needs—such as required model weights, TTS voice/skill assets, workflows, and selected downloaded reference videos—into Vibe Director's managed asset area or the retained `setup_comfy_and-stuff` installation. Keep that ComfyUI/model installation; do not copy its whole environment into Vibe Director. Use hashes and an inventory to avoid duplicate transfers, preserve provenance, and exclude accumulated project databases/cache/output unrelated to runtime. Donor checkouts may be removed only after a path/import/script audit and a successful verification with both donor directories unavailable; this is a later owner-authorized cleanup step, not part of ordinary migration.

Every reusable asset exposes:

- Stable `asset_id`, media type, title/filename and preview/file locator.
- Content hash, creation/import timestamps and technical metadata (duration for audio/video, dimensions for images/video, and formats where relevant).
- Readable description and searchable tags/categories/annotations.
- JSON metadata containing structured analysis and provenance, including source asset ID/interval for derivatives and analyzer/model/version/run IDs when applicable.
- Generation prompt, references, workflow/settings and project/scene/shot/clip links when the asset was generated from a story task.
- Appropriate voice transcript/speaker or character/location/frame-role mappings where available.

Metadata may live in records or JSON sidecars; preserve existing stores and outputs through a common contract. Missing values remain unknown rather than being fabricated. Assets do not need analysis before storage or preview; richer analysis can be added later.

SEO here means descriptive/searchable content metadata used to find reference material, not a requirement to publish media to web search engines. User-edited descriptions/tags update the searchable index without changing original media bytes or wiping analysis history.

## 7. Connection to the main Story Builder journey

All image/video/audio reference pickers consume this same asset catalogue. A video-generation page can search prepared video/audio descriptions and use images from the repository; its selected manifest still defines intended roles and reference-specific instructions.

An annotation describes what an asset contains. A reference instruction describes what the Director wants the current generation to use from it. Keep those separate so reuse does not overwrite repository descriptions with one task's directions.

Bound character images and voices appear as top recommendations in compatible selectors, without automatic selection. Frame selectors use first/last role and scene/shot/clip links to filter eligible images; R2V can browse the wider image catalogue. These rules remain those of `char_world.md` and `video_gen.md`.

Preparing media does not run the story pipeline. Generated story clips/images and auxiliary outputs can register in the shared library with provenance and appropriate retention; the Fully automated wrapper continues to retain all generated clips.

## 8. UI and routing plan

Proposed new frontend routes:

| Route | Page |
|---|---|
| `/media-prep` | Last-used area or Video/Audio/Images overview |
| `/media-prep/video` | Existing Video Repertoire & Summariser, preserving its internal tabs |
| `/media-prep/audio/library` | Common Audio Repository |
| `/media-prep/audio/studio` | Existing Audio Studio |
| `/media-prep/audio/reconstruct` | Existing Audio Reconstruct |
| `/media-prep/audio/music-sound` | Existing Music & Sound |
| `/media-prep/audio/utilities` | Existing Audio Utilities |
| `/media-prep/images/library` | Image Repository |
| `/media-prep/images/detailer` | Existing Image Detailer, with saved-library input/results |

Adapt existing routes `/video-repertoire`, `/video-summariser`, `/audio`, `/audio-reconstruct`, `/music-sound`, `/audio-tools` and `/image-detailer` to the matching destination once equivalent actions are available. Preserve project/asset/job context in redirects and deep links. These are UI routes; they do not require renaming backend APIs or workflows.

Keep selected tool, draft inputs, current job/result and relevant project context across navigation. Share repository pickers/previews and asset metadata controls between tools rather than creating separate libraries per page.

## 9. Implementation order and acceptance

1. Add the Media Prep shell and Video/Audio/Images navigation around the existing components.
2. Embed the current Video Repertoire & Summariser with its five tabs and capabilities intact.
3. Arrange the four audio tools and expose the shared Audio Repository.
4. Add Image Repository browsing/storage/search and connect the existing Image Detailer.
5. Normalize asset registration, readable descriptions, JSON provenance and search adapters across outputs without replacing working generation/analysis engines.
6. Connect repository assets to the main story generation/reference pickers; verify route/context restoration and existing tool operations.

Acceptance requires all named tools to remain reachable and retain their supported inputs, settings, playback/results and task behavior; video keeps the screenshot's tab structure; Audio Reconstruct appears once; all three repositories expose searchable metadata and stable reusable assets; Image Detailer saves linked analysis; and selection in Media Prep transfers a reference without launching generation or silently selecting additional assets.

## 10. Inspection basis and remaining detail

Reviewed the supplied screenshots and the existing frontend pages:

- `/home/riki/web_dev/story_builder/frontend/app/src/pages/VideoRepertoire.tsx`
- `/home/riki/web_dev/story_builder/frontend/app/src/pages/AudioStudio.tsx`
- `/home/riki/web_dev/story_builder/frontend/app/src/pages/AudioReconstruct.tsx`
- `/home/riki/web_dev/story_builder/frontend/app/src/pages/MusicSound.tsx`
- `/home/riki/web_dev/story_builder/frontend/app/src/pages/AudioUtilities.tsx`
- `/home/riki/web_dev/story_builder/frontend/app/src/pages/ImageDetailer.tsx`

`http://localhost:8080/audio-tools` was not reachable from the planning session. Tool behavior above is based on source inspection and screenshots, not a successful live browser check. Backend availability remains whatever the existing capability checks report. No application, engine, workflow or model has been rebuilt by this plan.

## 11. Shared generation entry and retired navigation

Media Prep is reusable without story authoring and links into the same isolated/story-linked generation forms. Remove the separate Production V2, Generate, old Automation Studio and Manual Director destinations from the intended navigation; legacy hand-offs select assets into compatible shared forms. No hand-off automatically renders media or invents missing screenplay context. Status remains global with connection/workflow/limit information as defined in `automation.md`.


## 12. Shared UI and selective reuse

Apply `ux_shared.md`: one saved workspace/asset context, readable results with optional JSON, clear processing/offline/empty/error states and direct recovery. Existing specialist capabilities remain accessible through this area rather than restored competing production pages. Shared voice bindings and stable asset IDs remain canonical.

`integration.md` governs reuse of the current tool services and selected retrieval helpers. A visual embedding corpus may augment image/video SEO; it does not replace audio transcripts/categories or introduce a second media repository. Add only dependencies needed by selected tools, keeping them separate from the working generation environment.
