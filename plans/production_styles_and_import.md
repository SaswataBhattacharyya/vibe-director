# Production type, style and story import

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
