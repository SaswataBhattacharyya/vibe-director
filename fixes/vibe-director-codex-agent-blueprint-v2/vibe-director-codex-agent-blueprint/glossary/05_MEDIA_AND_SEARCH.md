# Media tool guide

Source-backed usage map, 2026-11-05. IDs below are glossary IDs for future routing, not currently registered model functions. Consult [API helpers](API_HELPERS.md) and [HTTP routes](HTTP_ROUTES.md) for exact source locations. Live readiness has not been exercised by this documentation task.

## media.browse — Library, source catalogue and imports

**Choose when:** Find/select local media by project, repertoire, folder or category; import external files.

**UI:** #/media or media source pickers

**Inputs:** Current project, kind, source/owner scope, query/order/pagination/folder; file and intended role for upload.

**Outputs:** Catalogue rows with identities and content URLs, reused/copied assets or imports.

**How to use:** browseMediaCatalogue/listMediaAssets/uploadMediaAsset/reuseCatalogueAsset/refreshDownloadCatalogue. Read media_discovery.py for actual filesystem coverage. Broad scopes include discovered supported files; character/world roles are narrower semantic filters. Never assume the whole disk or Downloads is searched without a configured scope.

**Source:** [media-api.ts](../frontend/src/lib/media-api.ts), [MediaSourcePicker.tsx](../frontend/src/MediaSourcePicker.tsx), [media_discovery.py](../backend/story_builder/services/media_discovery.py), [media_library.py](../backend/story_builder/services/media_library.py)

## media.semantic — Semantic search, indexing and annotations

**Choose when:** Find content by meaning rather than filename.

**UI:** #/media → Search

**Inputs:** Media kind, scoped assets, natural-language query; annotations or indexing request.

**Outputs:** Ranked hits, evidence/descriptions and indexing job status.

**How to use:** searchMediaSemantically; updateMediaAnnotations/indexMediaAssetAnnotations; createMediaContentIndexJob and read/retry/cancel helpers. Unanalysed media is not automatically semantically understood. Report actual indexing/search coverage.

**Source:** [media-api.ts](../frontend/src/lib/media-api.ts), [media_semantic_search.py](../backend/story_builder/services/media_semantic_search.py)

## media.download — YouTube search/URL resolution and download

**Choose when:** User requests online source discovery or imports an online video.

**UI:** #/media-prep → Video Summariser → YouTube Download

**Inputs:** Search query/count or pasted URLs, selected candidates and project.

**Outputs:** Resolved candidates, download job and saved source assets.

**How to use:** resolveYoutubeSources → startYoutubeDownload → getYoutubeJob; cancel when supported. Search resolution is not a completed download or content analysis. Preserve source provenance.

**Source:** [media-api.ts](../frontend/src/lib/media-api.ts), [video_repertoire.py](../backend/story_builder/services/video_repertoire.py)

## media.analyse_video — Video Summariser / audio-video analysis

**Choose when:** Understand source clips, locate described actions or inspect recorded audio events.

**UI:** #/media-prep → Video Summariser → Analyze / Results / Audio Assets

**Inputs:** Selected video IDs and analysis settings.

**Outputs:** Analysis jobs, result records, extracted artifacts and searchable evidence as produced by the pipeline.

**How to use:** startVideoAnalysis/getVideoAnalysisJob with cancel/retry/delete helpers; staged donor analysis/import helpers. Inspect video_summarizer_results.py for real artifacts/timestamps. Do not claim every file has been analysed or every model understands speech.

**Source:** [media-api.ts](../frontend/src/lib/media-api.ts), [video_summarizer_results.py](../backend/story_builder/services/video_summarizer_results.py), [video_repertoire_worker.py](../backend/story_builder/services/video_repertoire_worker.py)

## media.style_frames — Style reference frames and associations

**Choose when:** Use selected video frames/images as evidence for a directing style.

**UI:** #/media and style-reference controls

**Inputs:** Asset ID, style ID, selected timestamps or linked image.

**Outputs:** Frame-extraction job and linked style-reference assets.

**How to use:** linkMediaAssetToStyle/extractMediaStyleFrames/getStyleFrameJob/cancelStyleFrameJob. This is not generic per-shot video generation.

**Source:** [media-api.ts](../frontend/src/lib/media-api.ts), [style_sources.py](../backend/story_builder/services/style_sources.py)

## media.delete — Archive and permanent media deletion

**Choose when:** User explicitly requests hiding or deleting selected media.

**UI:** Search/library selection actions

**Inputs:** Asset identity, archive flag or deletion preview/token.

**Outputs:** Archive update or confirmed deletion result.

**How to use:** setMediaAssetArchived; previewMediaDeletion then permanentlyDeleteMedia. Removing an attachment is a different operation and must not delete the original.

**Source:** [media-api.ts](../frontend/src/lib/media-api.ts), [media-deletion.ts](../frontend/src/lib/media-deletion.ts), [media_library.py](../backend/story_builder/services/media_library.py)
