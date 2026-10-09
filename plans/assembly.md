# First final assembly and export

## Accepted direction — 2026-10-09

Owner chooses: order accepted clips by screenplay and export one video, with optional audio tracks. This is the first delivery target. No full editing timeline has been requested.

## Proposed review and export surface

Show ordered Scene → Shot → Clip entries from the selected screenplay revision, each with its accepted take, preview, duration and gaps. Explicitly choose one accepted take per clip; preserve all original takes. Show missing/unaccepted clips and stale source relationships before export; do not silently omit them. Let the user review the resulting ordered list and start Export explicitly. For isolated clips, an explicit user-created ordered selection supplies the equivalent manifest without requiring a story.

Optional audio is selected from the shared library using stable IDs, category, description and preview. Show start time, trim range, level and the treatment of generated clip audio. Proposed safe default: preserve the existing audio on clips; adding a track mixes it only after an explicit selection. Replacement/muting must be explicit. Track timing and mix parameters require visible review, rather than assuming a selected voice file is final dialogue audio. These proposed controls remain subject to UI/contract review.

Store an immutable export manifest: screenplay/style versions, ordered clip/take/asset IDs and hashes, audio placement/mix settings, exact tool/configuration and target format. Report progress/failure, preserve inputs, allow retry without overwriting originals and expose a playable/downloadable result. Output goes into the shared managed library with readable description, JSON metadata and provenance. Reference-aware deletion must retain assets used by exports.

## Implementation/reuse assessment

Existing installed FFmpeg/ffprobe and owner-owned Story Builder assembly/audio helpers are candidates. OpenMontage stitch/compose/mixer can be assessed for behavior, but copying covered implementation still requires the license decision recorded in openmontage_licensing.md. This scope does not require choosing OpenMontage as the production app. Prefer the smallest compatible reusable tool chain that supports the agreed manifest and safeguards.

Verify source compatibility, differing codec/resolution/frame-rate/audio streams, explicit conversion policy and output format before implementation. Do not invent an automatic quality change. Propose concrete export presets in issue #14; screenplay ordering is settled, exact codec/resolution/fps and audio-overlap policy still need contract review.

## Acceptance

Focused tests use existing Story Builder media, preserve originals and establish clip order, optional audio placement, output playback/ffprobe, immutable manifest, retry and missing-input errors. Prepare any new media generation separately for the owner to click. Export tests need no new model generation and no broad legacy suite rerun. Issue #14 remains open until remaining settings/contracts and implementation evidence are accepted.
