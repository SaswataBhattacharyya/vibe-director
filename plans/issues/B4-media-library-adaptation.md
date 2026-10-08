# [B4] Reuse Media Prep services behind one searchable asset library

Status: local issue draft; not published. Type: Implementation.

**Proposed lead/reviewer:** Backend implementer proposes; Ashu implements/reviews D6 UI. These are proposals, not an assignment already accepted by Ashu.
**Dependencies:** G2; D6 accepted.
**Read first:** [current plans](../README.md), [issue working rules](../issue_backlog.md), then media_prep.md, integration.md in `plans/`. Paths below are relative to the named reference source, except explicitly absolute paths.

## Outcome and scope

Map existing Media Prep endpoints and adapt them behind stable shared asset/search contracts. Sources: Story Builder `services/video_repertoire.py`, `video_repertoire_worker.py`, `video_audio_search.py`, `audio_catalog.py`, `audio_reconstruct.py`, `audio_tts.py`, `audio_utilities.py`, `music_sound.py`, `image_detailer.py` and current page API clients. Preserve working utility behavior, dependencies and original files.

Add image-repository registration/indexing and audio category/search gaps only where absent. OpenMontage `lib/corpus.py` is an optional image/video retrieval candidate after license decision; it does not supply a complete audio repository. Split video/audio/image adapters into reviewable PRs.

## Questions to resolve in this issue

- Which metadata/search fields exist now, and which require extraction/indexing rather than only UI rearrangement?
- How will imports and tool outputs deduplicate and become searchable without moving originals?
- What processing state/provenance explains incomplete analysis results?

## Acceptance evidence

- Prepared/imported video, audio and image assets appear through the same generation selectors with stable IDs.
- JSON metadata and readable descriptions persist; video SEO and audio category/search work on representative records.
- Library/tool failure does not destroy original media or block unrelated story editing.
- Existing utilities are accounted for; dependency-heavy execution remains separate from lightweight UI setup.

## Handoff

Link the design/implementation PR, decisions, changed-file provenance and demonstrated evidence. Record unresolved dependencies explicitly. Follow the authoritative plans; ask about a real contradiction instead of reintroducing legacy pages or changing agreed mode policies.
