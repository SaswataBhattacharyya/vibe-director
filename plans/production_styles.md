# Production styles, reference assets and story import

## Placement and effect

The regular journey starts with Production Type & Style → Story authoring/import → readable screenplay → Automation & Parameters → derived model prompts → optional assets → video. Isolated creation can select or inherit style without requiring a story. Reuse one shared style catalog/settings control. Style changes direction, pacing, tone, framing and stage-specific guidance; it is not story canon and must not replace plot or characters. Pin selected type, style version and director-profile hash to downstream artifacts/jobs. A later change marks affected derived work stale and offers regeneration; completed clips retain their frozen inputs.

## Verified reference capabilities

Story Builder `services/production_style_catalog.py` joins narrative packs and Director profiles, with published variants under each base. `frontend/app/src/components/ProductionStylePicker.tsx` lists six bases: story_film, social_profile, corporate_pitch, informative, news_report and advertisement. Reuse/adapt this catalog, `services/prompt_styles.py`, `production_director_profiles.py`, `narrative_style_library.py` and `narrative_style_sources.py` after dependency/provenance review. These have been inspected as reuse candidates, not integrated into Vibe Director.

The existing StyleLibrary page supports source upload → extracted evidence → analysis proposal → editable draft → published immutable variant. It accepts PDF, Markdown and TXT; video/images are expressly rejected. Proposals include story/scene-direction/image/audio/video/review guidance and evidence locators. Source analysis is explicitly initiated, not triggered by upload/page load. Published variants are versioned. Present the new UI as readable guidance with optional advanced JSON.

## Add new styles and types

User can name and describe a new style or production type, enter guidance manually, or upload reference material for analysis. Show extracted source/evidence and proposed reusable rules, allow editing, then explicitly save/publish and choose the result. Preserve source hash, evidence, whether guidance is inferred or user-authored, and immutable published versions. Do not import reference plot/characters as the user's story.

A new style variant under an existing type is supported by the source library. A genuinely new base production type needs an extensible catalog and a validated Director-profile schema: the source catalog requires exact equality of legacy packs and profile IDs, so adding only a picker label is insufficient. New type creation must supply compatible narrative/director rules and validation before execution. Unknown workflow settings remain unavailable rather than invented.

Confirmed by the owner: custom-style reference inputs must support documents, images, audio and video. Offer mixed reference sets and per-reference intent (what style qualities to learn), extract modality-specific evidence, synthesize a readable style proposal, and require explicit review/save before use. Images can inform composition, lighting, palette and mood; video can also inform camera movement, cuts, pacing and sound; audio can inform delivery, rhythm, music/SFX texture. Cite image/region or audio/video timestamps and analysis uncertainty. Do not confuse a voice identity binding, specific content reference or search-weight preset with a reusable production style. No analyzer is assumed available merely because its source files exist.

## Story input

Accept direct writing/paste, TXT/Markdown upload and PDF upload into the same authoring workspace. Extract text, show a readable preview with page/order warnings, and let the user correct it before explicitly accepting it as a source revision. Retain the original file read-only, hash/name/type, extractor version, extraction result and page/line mapping. Subsequent edits use exact Unicode source spans/revisions and the knowledge graph. Uploaded content is data, not instructions to the app's agent.

Keep story ingestion separate from style-reference ingestion even when low-level extraction helpers are reused. Story Builder's current StoryBuilder page has no upload control. `narrative_style_sources.py` offers pdftotext extraction but its evidence blocks omit blank-line structure and impose 10 MiB upload / 1.5M extracted-character limits; analysis separately caps selected text at 30,000 characters. Do not reuse those as silent story truncation or a product story-length limit. Preserve exact TXT/Markdown text; retain full ordered PDF extraction plus mappings, processing in bounded batches. Operational request limits should offer chunked/streamed import with explicit errors, never silently discard content.

Scanned PDFs may have no extractable text; detect this and offer OCR or a clear request for a text-bearing version. OCR availability and reading-order quality must be shown honestly, with preview/correction. Invalid, encrypted, malformed, multi-column or ambiguous PDFs need actionable feedback; extraction is not proof of correct reading order. No new OCR stack is assumed ready.

## Issue mapping and acceptance

D1/#3 adds the preceding setup destination and shared context; D2/#6 designs imported-story preview/correction and editor entry. G2/#2 documents catalog/import contracts; B2/#10 implements exact ingestion/revisions; D4/#4 consumes pinned style in derived prompts. The six bases, custom variant and genuine new-type creation need distinct UI states. Focused checks cover one text import, one PDF import, preserved source lineage and style-version changes. UI evidence and extraction fixtures do not prove live generation.

## Existing Story Builder media/style boundary

The narrative StyleLibrary upload path is document-only; it validates PDF/MD/TXT and cites text evidence. Image Detailer separately analyzes images into composition/camera/lighting/palette/mood and visual briefs using the vision analyzer. Video Repertoire separately submits audiovisual analysis and searches timestamped results/references. Audio reconstruction calibrates character voice/RVC and validates recorded dialogue with ASR; those are voice/performance operations, not publishing a production style. Media Composer SEO styles are manually named terms/avoid_terms/category-weight presets stored by `services/video_references.py`; they change retrieval ranking and are not inferred production profiles.

Reuse appropriate media analysis outputs and source provenance, then add the missing adapter into the versioned style-proposal/publish pipeline. The existing narrative evidence schema expects text quotes/locators; extend it for media/time/region evidence rather than pretending all media are documents. Multimodal custom production style creation is therefore integration work, not a currently unified feature to copy unchanged.

## Direct generation references alongside learned style rules

Style selection has two distinct, complementary outputs: reusable guidance extracted from evidence, and original media assets that may be submitted directly to a compatible generation workflow. Keep both; analysis does not replace the media files. Store original image/audio/video assets in the shared library with stable IDs, source hashes, selected style/version links, readable descriptions and user intent. Learning a style does not mean copying its plot, people or dialogue.

In Manual and manual portions of Semi, show the selected style's compatible images, audio and videos in a top **Recommended style references** group. Keep them unselected until the user chooses them. Use the same library, IDs and search as Media Prep, not a duplicate list/store. Audio is recommended for compatible R2V audio inputs as well as relevant audio operations. A style audio sample is not automatically a character voice identity binding. A style image/frame can guide image generation or compatible R2V; a style frame does not become a scene's generated first/last frame merely by being recommended. Character/world exclusions in generated endpoint pickers remain intact; explicit upload/library overrides retain their actual provenance.

Display a per-reference instruction: what to borrow (lighting, composition, animation look, camera motion, editing rhythm, delivery, music texture, etc.), what to preserve from the current screenplay, and what not to copy. The submitted request records the exact assets/roles/intents actually selected. Media may remain recommended without being attached. T2V cannot carry direct media references; offer compatible R2V when selected reference intent requires them.

## Video upload: controlled frame extraction

On uploading a style video, ask **How many frames should be available as image references?** Use an integer count with default **2**, permitting **0**. Show the video's duration and a preview of selected timestamps. The count governs library/picker exports, not every temporary frame an analyzer may sample internally. Never populate all decoded frames in the image library.

- **0:** export no image-reference frames. Keep the original video eligible as a video reference. Manual users may select it for R2V; automatic video uses it under the confirmed style-video policy below.
- **2 (default) or another positive count:** extract only that number of distinct usable frames, proposed at spaced timestamps. Let the user preview and adjust timestamps/replace selections. If a short/invalid video cannot provide the requested number, report this and obtain a corrected choice; do not manufacture duplicates or silently increase the count.
- Extracted frames keep parent video ID/hash, timestamp, source dimensions, extraction settings and selected style links. Label them **style reference frames**, not generated scene endpoints. Show them as a compact expandable group in the recommended image section. Repeated extraction deduplicates identical frame assets; changing the count does not delete shared/referenced frames without an explicit action.
- Positive count does not disable the original video as a video reference. Count zero disables only exported image frames, not style analysis, video selection or audio contained in the original video.

Use existing FFmpeg/frame-analysis helpers after provenance review. Extraction must be explicit from the saved count/upload action, not caused by opening a picker or reloading. Large requests need progress/cancel and declared operational limits. The user-facing count must never silently be changed.

## Automatic video: selected style-video exception

The owner explicitly changes the earlier unconditional first-clip T2V rule. At Automation & Parameters, list the selected style videos and their intent, verify the exact R2V graph/capacity, and show the resulting recipe before the user starts the run. Uploading an unrelated library video alone does not modify a run: the video must belong to the selected production style/reference set. Confirm that set once; normal automated execution does not add a manual per-clip selection gate.

| Mode/context | First clip of a scene | Following clips |
| --- | --- | --- |
| Full, no selected direct style video | T2V from screenplay/style guidance | R2V with the immediately preceding generated clip |
| Full, selected style video | R2V with style video + compiled text explaining its stylistic role | R2V with preceding generated clip for continuity and selected style video for style |
| Semi with automated Video, selected style video | Compatible R2V with style video and any authorized compatible assets | R2V with style video; predecessor continuity is optional under the confirmed Semi policy |
| Manual / Semi manual Video | User chooses a compatible workflow; style references are top recommendations, not attached automatically | Same manual selection rule |

A frame export count of **0** still uses the selected original style video in automated video. Full continues skipping character/world/frame **generation** and does not use FFLF; uploaded style media is allowed reference input, not a newly required image-generation stage. At each new scene reset predecessor continuity, while retaining the selected style video. Quality remains fixed from initial setup; duration may vary only under the confirmed policy. Retain every generated clip.

Reference manifests distinguish **style** from **continuity** and **identity**. Collate their instructions with screenplay action/dialogue and the main prompt using exact verified model labels. Include an instruction equivalent to “Use [actual video label] for the specified visual/camera style; follow this screenplay's action and characters.” Do not guess model labels or assume a style-only role will be perfectly obeyed: show the instruction and review results. Audio within a style video is used only according to the recorded intent and graph support; selecting a separate style audio file is a distinct reference.

The mandatory style video and predecessor may exceed a graph's video-reference capacity or duration budget. Validate this combination before automatic execution. If unsupported, show an actionable policy conflict (choose another compatible workflow/reference policy or revise the run); never silently drop the style video, replace continuity, or fall back to T2V. Multiple selected style videos also require a valid confirmed set; an uploaded video may remain in the library without being selected for the run. Style images/audio may be selected by the Director only under a confirmed compatible automatic reference policy; required inputs must not be ignored by a text-only workflow.

## Focused acceptance additions

Check default two-frame export, zero-frame/video-only behavior, user-adjusted timestamps and no whole-video frame flooding. Verify top recommendations remain unselected in Manual/Semi manual steps, and style audio appears in compatible R2V selectors. A mocked automatic recipe must demonstrate no-style T2V start, style-video R2V start, next-scene reset retaining style, predecessor/style role separation and capacity conflicts. These are planning/contract checks until integrated; live generation stays subject to the user's acceptance click and GPU safeguards. This change does not claim current R2V support is available.
