# ACE-Step BGM dataset and LoRA pilot

Status: Carnatic download pilot completed 2026-10-28. No training started.

New preparation priority: [BGM dataset expansion for Luna](ace_step_bgm_expansion.md). The owner now requests additional recordings and recovery of unused master sections before training. That supersedes the earlier preparation order below; listening review and owner-started training remain required. Preserve existing edited triplets.

## Inspected package and compatibility

Package: `local_data/ace_step/ACE_STEP_BGM_Builder/`.
It contains 41 source entries across 10 style categories and currently contains no audio recordings. Categories are dataset labels, not existing trained LoRAs.

The builder outputs MP3 recordings with matching `_prompt.txt` and `_lyrics.txt` files. This matches the installed standalone ACE-Step converter at `local_data/engines/audio/song_gen/ACE-Step/convert2hf_dataset.py` and Vibe Director's dataset upload in `backend/story_builder/services/ace_studio.py`. Tags must be comma-space separated; instrumental recordings use `[instrumental]`. Builder excerpts are capped at 235 seconds, below Vibe's 240-second upload limit. Upload one completed style folder through Fine-tune, not its ZIP: the current interface accepts matching files/folders.

This establishes file-format compatibility, not successful training or music quality. Use the installed engine and existing base weights; this plan does not require upgrading ACE-Step or downloading replacement weights. Training additionally needs the runtime dependencies and cached MERT/mHuBERT encoders reported by the existing training-readiness check.

## Builder safeguards and pilot results

The donor builder/validator changes are in place: partial download failures are reported as a failing exit; expected style folders can be checked; and the manifest records license evidence, source URLs, attribution, durations, tags, and MP3 checksums. The validator reports structural/audio-duration status, not musical content.

The `indian_carnatic` pilot was downloaded with the existing `react` Conda environment and FFmpeg. It produced **8 MP3 + prompt + lyrics triplets from 5 source recordings**, all 235 seconds, with 0 reported builder errors. Three source recordings each contributed two non-overlapping excerpts; these are examples, not independent recordings. `FAILED_DOWNLOADS.csv` contains only its header. The triplet validator passed with 8 recordings and 0 structural errors. MP3 checksums differ, and `ffprobe` can read all durations.

Prompt tags are copied from the package's prewritten catalog descriptions. The downloader retrieves source/license metadata but does not automatically extract musical tags or analyze the recordings. It writes `[instrumental]` for every excerpt without verifying absence of vocals. The owner must audition each excerpt, correct tags/lyrics, and remove any unsuitable track. This pilot is **not approved for training yet** and does not establish that a Carnatic LoRA will train well.

## Review checkpoint — 2026-10-28

Only the Carnatic pilot has prepared recordings; the other nine categories are not downloaded datasets. The current Fine-tune interface submits one dataset as one training job. A serial queue of separately named style-training jobs is still missing. Uploading several styles together would combine them into one dataset, not create separate LoRAs. Upload only a completed style folder containing matching triplets; the output root also contains manifests/cache files rejected by the uploader. No successful training run or resulting adapter has been verified.

## Execution sequence

1. Owner reviews all 8 pilot excerpts by listening. Update each `_prompt.txt` and `_lyrics.txt` based on what is actually audible; remove unwanted, vocal, silent, damaged, or mismatched excerpts. The generated `[instrumental]` label must not be trusted until listened to.
2. Keep excerpts grouped by original recording and do not treat two excerpts from one performance as independent recordings. Decide which source recordings to retain for later comparison rather than training.
3. When the owner approves the pilot tags and chosen triplets, run the validator again and upload only the approved folder/files through ACE-Step Fine-tune. Review the song count/durations and choose a distinct adapter name. Confirm training readiness and GPU admission using existing safeguards.
4. Prepare a bounded pilot training request with visible rank, learning rate, steps, and checkpoint interval. The owner manually clicks Start fine-tuning. No training was started by this task.
5. Compare base-model output and the resulting LoRA using matched prompts/seeds, including unfamiliar prompts. Check style improvement, diversity, artifacts, and resemblance to training tracks. Pilot parameters and dataset size are experimental; do not promise quality or a training time.
6. Register only a successfully completed, loadable adapter as a named Trained LoRA in Styles. Each separately trained style has its own adapter; dataset folders do not become styles merely by being downloaded. Additional dataset preparation can proceed now under the expansion plan; further training remains owner-controlled.

## Additional audio priorities

Hindustani has only one default modern bansuri source plus an optional historical sitar source. Carnatic has five pages with artist concentration. These are starter collections, not evidence of broad genre coverage. Dark suspense, Indian fusion and modern chill are also sparse by source-page count; actual usable track counts remain unknown until download and review.

Ask the owner for more independent, clearly licensed recordings matching a narrow intended style, preferably from varied performances/artists. Provide a URL, recording-level license/attribution, audible instrument/mood notes and confirmation whether vocals occur. More excerpts of the same performance do not replace more diverse recordings. Do not set an invented universal minimum number of songs.

## Acceptance and boundaries

Dataset-preparation pilot success means validated triplets and complete source provenance; that portion is complete. A training milestone still requires the owner-reviewed triplets, an owner-started training job, a saved loadable LoRA, and owner-reviewed comparison output. File checks alone are not acceptance. No model weights were downloaded, no base weights were changed, and no training job was submitted.
