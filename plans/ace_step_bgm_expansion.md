# ACE-Step BGM dataset expansion — Luna execution plan

Status: download/preparation runner launched; inspect live progress and final report. Training has not been started.

## Owner update — continuous preparation

Process both the original 41 and additional 23 source pages. Append usable clips directly to `local_data/ace_step/datasets/ACE_STEP_READY/<style>/`; do not quarantine material for a review gate. Preserve existing audio, tag edits and lyrics. Keep complete originals in `_download_cache`, split uncovered sections into clips up to 235 seconds, and record source metadata and individual download failures. Tags are source-description suggestions, not claims of having listened. The owner edits tags and manually starts each style’s training. No training is started by this runner.

Live runner: `tools/prepare_ace_bgm_dataset.py`; PID, log, progress and final report: `local_data/ace_step/datasets/download_preparation/`. Verified original audio downloads take precedence over duplicate YouTube copies.



## Objective and boundaries

Extend the existing ACE-Step dataset using eligible additional recordings and previously unused sections of original recordings. Preserve existing audio, manually edited tags and lyrics. Reuse Vibe Director's downloader and audio extraction utilities. Prepare files for the owner to review and upload; do not start LoRA training or change the training UI.

Luna implements this directly, without Luna workers or routine Sol reviews. Ask for help only when genuinely stuck or when a substantial completed milestone needs review. No Git work, new model weights, environment rebuilds or app-wide test runs.

## Read first

- Package: `local_data/ace_step/ACE_STEP_BGM_ADDITIONS_FOR_CODEX/`. Read `CODEX_PROMPT.md`, `README_FIRST.md`, `SOURCES_READABLE.md` and `ADDITIONAL_BGM_SOURCES.json`; use the CSV for editable suggestions. Treat source lists and license claims as inputs to verify, not proof.
- Existing dataset: `local_data/ace_step/datasets/ACE_STEP_READY/`.
- Previous plan: [Dataset and LoRA pilot](ace_step_bgm_dataset.md).
- Original builder and validator: `local_data/ace_step/ACE_STEP_BGM_Builder/`.

Use the actual checkout `/home/riki/Documents/ChatGPT/Vibe Director`. The injected `Vibe Director 2` path is obsolete; do not recreate it.

## Current evidence; do not redo unchanged checks

The previous pilot produced eight complete 235-second triplets from five Carnatic recordings. Three recordings supplied two excerpts and two supplied one. Full originals are cached under the dataset's `_download_cache`. The other nine style folders are not prepared datasets. Previous structural validation passed; vocal absence and musical tags were not verified. Preserve those eight triplets and report their pending owner review rather than silently relabeling or moving them.

The additional package has **23 candidate source entries**, not 23 guaranteed usable tracks:

| Existing style key | Additional entries |
| --- | ---: |
| indian_carnatic | 3 |
| indian_hindustani | 5 |
| cosmic_cinematic | 2 |
| epic_orchestral | 3 |
| action_battle | 4 |
| emotional_piano | 2 |
| peaceful_ambient | 2 |
| dark_suspense | 1 |
| modern_chill | 1 |
| indian_fusion | 0 |

The original 41-source catalog remains a reference. Do not rebuild or replace it. This request authorizes expanding dataset preparation before the pilot training completes; owner review and manual training remain required.

## Reuse map

| Need | Existing implementation | Adaptation |
| --- | --- | --- |
| YouTube resolution and download | `backend/story_builder/services/video_repertoire.py`: `resolve_youtube_sources`, `youtube_downloads_root`; `video_repertoire_worker.py`: `run_youtube`, `_download_with_cli` | Reuse the existing downloader, source metadata and global `library/downloads/youtube` location. Inspect the current signatures before calling. Do not submit analyzer/GPU jobs. |
| Audio extraction | `backend/story_builder/services/audio_utilities.py`: `extract_mp3` operation | Reuse its FFmpeg extraction settings; segment full masters with FFmpeg. |
| Triplet structure and manifest | `local_data/ace_step/ACE_STEP_BGM_Builder/build_ace_step_dataset.py` | Reuse compatible helpers; replace old start/end-only excerpt selection in an expansion wrapper, not by blindly rerunning the old builder. |
| Validation | `local_data/ace_step/ACE_STEP_BGM_Builder/validate_ace_step_dataset.py`; `backend/story_builder/services/ace_studio.py` | Check new triplets against the installed uploader/converter contract. Do not change training endpoints. |

Prefer a verified licensed original audio download when supplied. Use the existing Video Summariser downloader for permitted YouTube sources; it currently caps video at 720p and extracts from the downloaded audio stream. Do not claim lossless source quality or change global download presets. Reuse downloads by source URL/video ID; avoid title-based collisions. Keep dataset-specific logic in a small wrapper under `scripts/datasets/` following local conventions.

## Implementation sequence

### 1. Inventory and protect existing work

Locate the actual existing files and masters. Save a timestamped manifest backup and SHA-256 baseline of every existing MP3, prompt and lyrics file outside the style folders. Record existing manifest schema/rows and source intervals (`clip_start`, `clip_seconds`). Validate interval metadata before trusting it; an unknown interval is a review item, not permission to recut it.

Do not overwrite, rename, regenerate or retag old triplets. Do not delete originals or cached masters. Keep download cache, staging, quarantine and operational manifests outside triplet-only style folders.

### 2. Resolve sources and permissions

For each candidate, record the exact recording, original source page, direct/download URL, artist, title, license evidence and attribution. Verify the actual recording and version; package claims alone are insufficient. Follow the package's eligibility policy: skip unclear permission, ND and NC-only candidates, recording the reason. Do not bypass access restrictions. Missing or rejected sources remain visible in the report.

Handle compilation entries as multiple recordings when appropriate. In particular, honor the Ramani compilation's `section_boundaries_or_cues` and composition titles. For Scott Buckley's Sleep choose **Piano Only**; for Red choose **No Vocals**. Flag a missing or wrong mix rather than treating it as equivalent.

### 3. Download/reuse full masters, then plan intervals

Use original full recordings, not previously trimmed MP3 excerpts. For each original, calculate the union of already-used intervals and subtract that union from eligible clean musical sections. Cover the remaining usable sections consecutively, including middle sections missed by the old builder.

- New clips must be at most **235 seconds**, preferably 160–235 seconds where sensible, normally at least 45 seconds.
- Do not cross known composition boundaries just to fill a clip. Prefer sensible musical boundaries when they can actually be established.
- Redistribute a short tail within uncovered material if possible; otherwise log the omitted seconds and reason. Never modify old clips to absorb it.
- Avoid overlapping intervals and excessive near-duplicates. Detect the same performance arriving through alternate URLs/encodings using audio fingerprints where available; hold uncertain matches for review. File hashes alone do not detect re-encoded duplicates.
- Produce a dry-run interval manifest before cutting. One source entry may produce several clips or none.

### 4. Prepare new triplets with truthful metadata

Use deterministic safe stems, for example `song_add_<source_id>_<start_ms>_<end_ms>`, within the uploader's 80-character stem limit and `[A-Za-z0-9][A-Za-z0-9_-]{0,79}` rule. Each published stem needs:

```text
song_add_example_0_235000.mp3
song_add_example_0_235000_prompt.txt
song_add_example_0_235000_lyrics.txt
```

Prompt files contain UTF-8, comma-space separated musical tags. Candidate tags are suggestions: preserve their provenance and refine from actual recording metadata and audible evidence. Do not invent instruments, BPM, raga, language or time signatures. Different excerpts can require different tags.

Use `[instrumental]` only for excerpts checked to contain no singing, speech, chants, wordless choir or spoken percussion syllables. VAD alone cannot establish that. Do not run blanket source separation. If content cannot be verified, put the **new** triplet in a separate review/quarantine area, not the ready upload folder; explain what the owner needs to listen for. Do not claim automatic listening occurred without an actual supported analysis/review method.

Stage all three files, validate them, and publish using a resumable journal. Three file renames are not an atomic transaction: recover interrupted groups on rerun so a ready folder is never left with unnoticed partial triplets. Existing stems must never be overwritten.

### 5. Preserve provenance and produce review material

Append compatible rows to `SOURCE_MANIFEST.csv`, retaining its schema and old rows. Store additional fields in `ADDITIONS_MANIFEST.csv`: source ID and recording identity, source URLs, master hash, clip interval, output hash, tag provenance, vocal-review status, license evidence and attribution. Preserve the original manifest as the baseline backup.

Also write outside style folders:

- `ADDITIONS_FAILED.csv`: download/conversion/validation failures.
- `PENDING_RIGHTS_REVIEW.csv`: excluded or unresolved permissions and reasons.
- A content-review list linking uncertain clips to their proposed tags and source intervals.
- `ATTRIBUTIONS.md` and `LICENSES.csv` retaining recording-level obligations.
- `EXPANSION_REPORT.md`: per-style before/after clips, usable duration, unique performances/artists, sources reused/downloaded/skipped/failed/pending, and omitted seconds/reasons.

Flag any single recording contributing over 35% of a style's duration for owner review; do not automatically discard it. More cuts from one performance do not create source diversity. Future training/evaluation splits should separate original recordings, not neighboring excerpts.

### 6. Execute and verify in bounded stages

1. Implement dry-run planning and preservation checks. Test interval subtraction, short tails, existing overlap, conflicting stems and interrupted rerun recovery using small local fixtures.
2. Prepare one eligible source as a smoke check. Validate duration, playback readability, triplet matching, manifest links and unchanged baseline files.
3. Process eligible Indian additions first, then remaining styles and uncovered sections of old masters. Reuse cached sources. Save progress after each source; resume without duplicate cutting or downloads.
4. Validate all new triplets and ready folders. Compare all old file hashes and old manifest rows against baseline. A metadata/content/rights-pending clip is not ready merely because it passes structural validation.
5. Rerun the expansion in dry-run/resume mode: it should propose no duplicate completed intervals and should preserve tags edited after the first run. Run only relevant changed checks; no unchanged full-app suite.

Do not wait for a training run to prepare the next independent source. Do not start training to validate the dataset.

## Completion and owner handoff

Report exact prepared folders and counts, pending/skipped/failed entries and reasons, and whether every existing triplet remained unchanged. Do not call all 23 entries successfully processed if any eligible entry failed. Separate **structurally valid**, **content reviewed**, **rights verified** and **owner approved** statuses.

The owner listens, edits tags and approves material. Then upload **one approved style folder at a time** through ACE-Step Fine-tune and manually start its LoRA. The current UI submits one dataset/job; multiple styles uploaded together pool into one dataset and do not create separate adapters. A serial multi-LoRA training queue is outside this task. Dataset preparation alone does not create a trained style.

## Paste-ready instruction for Luna

Read `plans/ace_step_bgm_expansion.md` and the linked expansion package. Execute dataset preparation only, reusing Vibe Director's existing Video Summariser downloader and audio extraction utilities. Append eligible additional recordings and uncovered sections of cached originals; preserve existing MP3s, tags and lyrics byte-for-byte. Build resumable, nonduplicating triplets of at most 235 seconds with source/interval/license provenance. Quarantine new clips with uncertain vocal content or tags for owner review. Validate changed behavior and preservation, then report exact ready and pending folders. Do not train, change the UI, download model weights, do Git work, spawn workers or request routine Sol reviews.


## Dataset completion — 2026-10-28

Prepared 172 MP3/prompt/lyrics triplets across 10 style folders in `local_data/ace_step/datasets/ACE_STEP_READY`. All 64 catalog source pages processed; no pending sources. Fixed Last Journey's changed attachment filename. All styles passed format/duration validation; only the changed epic_orchestral folder was revalidated during the final repair. Existing clips and text edits preserved. Tags are source-description suggestions, not an audio listening assessment. Training has not been started. Owner may edit each `_prompt.txt`, then import one style folder at a time in ACE-Step Fine-tune. Complete originals remain in `_download_cache`; exclude that cache and the manifest when uploading training triplets.
