# Media Prep donor parity

Audit date: 2026-10-12  
Compared the Story Builder `VideoRepertoire.tsx` / repertoire APIs with Vibe Director's Media Prep pages, shared library, and routes. This is a source review; it does not claim live model or browser acceptance.

## Donor feature mapping

| Story Builder capability | Vibe Director destination | Status |
| --- | --- | --- |
| Add local video; register existing media | Media Prep → Video → Library; upload and explicit copied-Story-Builder import | Implemented. Import preserves donor originals and source lineage. |
| Select videos and run direct video/audio analysis | Video → Analyze; workspace-scoped analysis jobs with settings, progress, cancellation and retry | Implemented. Existing focused adapter coverage applies; live analyzer runtime remains unverified. |
| Review summaries, scenes and derived clips/frames | Video → Results; job summaries and published shared-library assets | Implemented. |
| Inspect collected audio and isolate detected events | Video → Audio Assets; shared audio assets and optional SAM Audio preview/save/discard | Implemented. SAM inference/checkpoint readiness still needs owner runtime acceptance. |
| Search video and analyzer corpus | Media Prep → Search; image/video/audio search, keyword/semantic mode, sorting and template/list/carousel views | Implemented in the new shared-library workflow. The old “send selected result to Manual Director” destination is intentionally removed. |
| Browse and manage audio categories | Search → Voice Files / Audio Clips; separate filters and searches; voice import is explicit | Implemented. |
| Run Audio Studio, Audio Reconstruct, Music & Sound, Audio Utilities | Media Prep → Audio tool pages | Implemented as workspace-aware adapters/jobs; actual workflow/model availability is shown per capability and needs runtime acceptance. |
| Analyze a saved image | Media Prep → Images → Image Detailer; saved analysis is linked to the image asset | Implemented; live image analyzer compatibility remains unverified. |
| Keep analysis, media and provenance linked | Shared workspace library and donor-lineage metadata | Implemented for copied videos and explicitly imported analyzed audio. |
| Delete selected repertoire videos/audio | Media Prep → Search → Archive / Restore | Implemented as reversible archive: archived media is hidden from normal library/search/picker results, but its file and manifest record remain intact so existing story, prompt and job references continue to resolve. It can be shown and restored in the library. |

## Deliberate replacements

- The donor's “Send to Manual Director” button targets a page the Vibe plan removed. Vibe uses the shared Media Prep library and Video Create reference picker instead.
- Donor video assets import into a chosen Vibe workspace; they do not remain dependent on the Story Builder checkout.
- Donor hard deletion is replaced with archive/restore to protect linked project records and preserve a recovery path.
- Archiving a setup-owned style reference removes it from future pinned-style recommendations. Saved R2V/FFLF references still validate and stage from the intact source file; archive changes visibility, not file identity or bytes.
- Donor-specific curated SEO/corpus search is replaced by the planned unified image/video/audio Search page. Search can still report when content embeddings or workers are unavailable; keyword search remains available.

## Acceptance still needed

1. Owner creates/opens a story and imports one copied Story Builder video into its workspace. **Owner-confirmed (2026-10-12):** the imported video appears in Search → Videos.
2. Owner verifies the imported video opens and plays from the library. **Owner-confirmed (2026-10-12):** playback works.
3. Reversible archive/restore functional check: **agent-run on 2026-10-12** with one staged video imported into the current standalone workspace. Normal listing hid it after archive; Show archived exposed it; restore returned it; playback still worked. This is separate from the owner's earlier copied-video asset and does not claim owner acceptance of that asset's archive state.
4. Owner later clicks analysis/generation actions only when ready; this source audit did not start them.
5. Confirm the supported local analyzer/audio/image workflow readiness against the retained ComfyUI and copied resources.

The copied-video import and Search → Videos playback checks are owner-confirmed. Archive/restore behavior has an agent-run current-instance check; owner-specific archive acceptance is not required to establish the reversible feature after this user's autonomous-test authorization. Analyzer/audio/image workflow readiness and quality remain open.
