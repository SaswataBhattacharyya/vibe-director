# Text to Video batch files

Open Create → Text to video → Batch prompts. Upload Markdown, plain text or JSON, or paste its contents. Validate batch previews every entry. Start batch is owner-clicked and opens Current Take. Screenplays and story automation are independent of this standalone batch.

## Markdown / text

```text
#prompt 1: time=15sec, AR=9:16, Q1=0.6 Q2=0.98
"Your complete MiniMax H3 prompt."

#prompt 2: time=15sec, AR=16:9, Q1=0.6 Q2=0.98
"Your next complete prompt."
```

Only prompt-ID headers and quoted prompts; no introductions or code fences in the uploaded file. Prompt bodies may span lines. Spaces after parameter equals signs are accepted. IDs can be nonconsecutive numbers or names such as temple-reveal. Use 1–64 ASCII letters, digits, hyphens or underscores, beginning with a letter or digit. IDs are case-insensitively unique within a file; generation follows file order. The project reserves their video filenames across batches. Limits: 1–100 prompts, 1 MB total, current H3 contract duration 5–30 seconds and prompt length limit. Final quality: 0.8 Low, 0.98 Standard, 1.5 High, 2 Max. Legacy 0.4 and 0.6 retain their smaller dimensions. Aspect ratios use the existing video contract options.

## Independent H3 / LTX quality — 2026-10-26

Q1 selects the native H3 source canvas; Q2 independently selects the final LTX canvas. For example, Q1=0.6 uses 1056×608 landscape or 608×1056 portrait, and Q2=0.98 finishes at 1344×768 landscape or 768×1344 portrait. Other aspect ratios use the existing 32-pixel grid fitting. A comma between Q1 and Q2 is optional. Accepted preset keys for each: 0.4, 0.6, 0.8, 0.98, 1.5, 2. Explicit Q1 bypasses automatic source downsizing; it may cost more memory/time than the previous small-source default.

Existing `Quality=...` Markdown and JSON remain accepted, retaining automatic H3 source sizing and using Quality for the final LTX output. Saved jobs and batches are not changed. The owner Markdown headers now specify Q1=0.6 Q2=0.98; prompt bodies, IDs, durations and aspect ratios are preserved.

## JSON

```json
{"prompts":[{"id":1,"time":10,"AR":"9:16","Q1":0.6,"Q2":0.98,"prompt":"Your complete prompt."}]}
```

A top-level array of the same objects is also accepted. No extra keys. Time is numeric seconds; Q1 and Q2 are numeric resolution presets, not text labels. Both are required in the new format; do not mix them with legacy Quality.

## Execution and recovery

The existing supervised video worker admits one job per batch at a time. It generates and validates every H3 Turbo original in file order, retaining H3 between originals. Only when all originals are validated may LTX promotion begin: confirm unloading, refine each original in file order while retaining LTX, validate each final with original audio, then confirm final unloading. Unknown allocator observations block loading; after the initial 30-second window, supervised handoffs poll every 10 seconds until release is observed. Existing saved originals are reused during recovery. Each stage waits for its outstanding job to finish before advancing. No references are attached. GPU/model/queue guards apply to each job. Completed jobs remain reviewable without requiring per-clip acceptance to advance.

Pause finishes the current clip and prevents the next admission. Resume continues a paused batch. Stop requests cancellation of this batch's owned active job and prevents later prompts. Refresh reads progress only. Reload restores project-scoped batches from the ledger. Stable admission keys prevent duplicate jobs after a lost response or process restart. Missing/failed/uncertain outputs pause progression rather than automatically resubmitting. Fixing an error and pressing Resume rechecks the outstanding job; it does not retry failed generation. Stop and start a corrected manifest if a new render is needed.

## Rewritten owner file

These exports originally contained the source entries; they are editable user files. At the latest audit the Markdown contains only IDs 7/8, whereas JSON contains IDs 1–8. The filename is not a promise of the current entry count. They follow the official H3 prompt structure: integrated_multimodal_description, overall_soundscape, non_diegetic_music; timestamp later shots and avoid rendered text. Source: https://github.com/MiniMax-AI/MiniMax-H3/tree/main/skills/h3-prompt-writing

Extended-duration generation quality still needs owner-clicked live acceptance. Validation confirms request compatibility, not visual fidelity or render speed. No GPU batch was started during implementation.

## Named outputs and regeneration — 2026-10-24

`#prompt temple-reveal: time=18sec, AR=9:16, Quality=0.98` (or JSON `"id":"temple-reveal"`) produces `local_data/assets/<workspace_id>/temple-reveal.mp4`. Numeric IDs work too; they need not start at 1 or be consecutive.

Start revalidates the manifest and asks about each existing project ID: OK overwrites the named final only after successful collection/validation, Cancel keeps it and allocates the next free `temple-reveal_take-2.mp4`, `_take-3`, etc. Choices and filename reservations are durable with the batch start key. Lost-response recovery reuses the same choices and filenames. Duplicate IDs in one file are rejected. Unmanaged existing files cannot be overwritten through this flow; choose a new take. Old job/library records are retained, with overwritten outputs unavailable rather than playing replacement bytes. ComfyUI intermediates are not deleted by final-output overwrite.

All H3 originals precede all LTX refinements (latest owner correction, 2026-10-25). Filenames affect final outputs only; screenplay and other generation modes are unchanged.

## Transport recovery — 2026-10-25

Brief ComfyUI runtime connection failures are retried with GPU safeguards active. Sustained transport-only failures wait for reconciliation of the same saved prompt, without resubmission. GPU faults, invalid/missing outputs and explicit user pauses remain paused. New pause reasons include the underlying error. See `plans/BATCH_PIPELINE_AUDIT_2026_10_25.md` for incident evidence and focused verification.
