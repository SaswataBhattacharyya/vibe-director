> 2026-10-13 correction: the fixed 20 GiB GPU admission threshold has been removed. Default-off serial scheduling now protects shared workload execution; memory reports are informational. Real model/workflow fit still needs acceptance. See `implementation/review_2026_10_13.md` for current remaining gates. Resource checksums below are unchanged.

# Remaining work and copy verification — updated 2026-10-13

## Live Status integration update (2026-10-12)

The audio node-catalog addition is now live in the verified app: after refreshing only the API serving this checkout, the API and visible Status page show all 11 audio graphs have all required node types installed. Audio remains explicitly unverified for models/runtime/prompt limits, so this closes only node-evidence visibility. The running API is PID `3203544` on port 3020; the Vite UI remains on 8082. See the top of `HANDOFF.md` for identity and no-job safeguards.

## Current completion yardstick and remaining effort

**Copying/coding: PASS.** The finite implementation gate is [CODING_COMPLETION_GATE.md](CODING_COMPLETION_GATE.md): C1–C12 are CLOSED, with focused evidence and real UI → service/adapter → saved result → consumer paths recorded. The consolidated GPT-6.1 Sol medium review and its required bounded fixes are also complete. The prior **15–33 hour implementation estimate is obsolete**; it must not be used to imply that another coding phase remains. Do not recopy resources or repeat unchanged suites. Reopen only a named C row when a concrete required defect is reproduced.

**Manual acceptance: RELEASED, not complete.** It is a separate owner-run phase. Historical copied-video import, title search and playback are accepted; real analysis, semantic quality, generation, durable-run output, and final export playback still require workflow-specific acceptance. `plans/MANUAL_ACCEPTANCE.md` contains the prepared sessions. Before each live click, refresh the serving UI/API identity, workflow readiness, queue, serial-workload setting and independent GPU monitor; enable Debug. The owner starts Analyze/Generate/Export. A software pass is not runtime readiness, and a ready status is not successful output acceptance.

| Acceptance area | What remains to observe | Evidence boundary |
| --- | --- | --- |
| Media Prep analysis and search | Owner starts the prepared one-video analysis; inspect saved summary/derived assets, then test content indexing and a media-grounded semantic query. | Real analyzer/runtime and retrieval quality; title search/playback already owner-confirmed. |
| Image, voice, world and frame workflows | Run only currently enabled, prepared workflows; inspect and select usable outputs and confirm they reach downstream pickers. | Installed workflow compatibility and real output quality. |
| T2V, FFLF, R2V and Current Take | Exercise supported prepared inputs, review real clips, then verify Retake/Next and persisted references. | Real generation, continuity and output quality. |
| Assisted and Fully automated runs | Complete one bounded run; inspect stage/clip order, pause/recovery behavior and continuity. | Real runner progression and generated results. |
| Assembly/export | Export accepted takes with selected audio/settings; play the produced file and verify retry/recovery if needed. | Real FFmpeg render and final playback. |
| Audio/SAM and other opt-in tools | Accept only after Status identifies the exact worker/model/credential prerequisite and the workflow is enabled. | Their readiness is currently separate; graphs/nodes alone do not prove runtime. |

There is no single reliable wall-clock completion estimate: GPU/model waiting and the number of enabled workflows vary. Run the prepared sessions one at a time, record each result in Debug and the acceptance packet, and reopen only the affected coding row if a live failure demonstrates a product defect. No Git work, deferred provider expansion, donor deletion or bulk recopy is part of this yardstick.

## Copy verification performed now

**Donor checkout runtime-reference audit (2026-10-12):** A targeted scan of backend/frontend runtime sources found no imports or configured file paths into the Story Builder or OpenMontage checkout. Python imports named `story_builder` resolve to Vibe's copied package in this repository. The only direct checkout path is visual-design provenance in `frontend/README.md`; it is documentation, not a runtime dependency. OpenMontage is absent from runtime imports. This does not validate the retained ComfyUI setup, third-party model/runtime dependencies, or real execution; keep both donor checkouts until owner runtime acceptance is complete.

Compared the copy script's selected source set to `local_data/donor_migration` using rsync checksum dry-run with `--ignore-existing` removed. No copy or overwrite occurred. Log: `/tmp/vibe-copy-verification.log` (temporary diagnostic, may be removed later). The selected set totals **51,031,107,445 bytes**, about 51.0 GB decimal/47.5 GiB; this sum can count overlapping selections more than once and is not the total destination-tree size.

- Selected model weights, skills and media produced no checksum differences or missing-file transfers.
- All **62** staged video manifests resolve to files inside Vibe staging; every media SHA-256 matches its manifest. Each donor/staged manifest differs only in `path`, as intended.
- Three analyzer code files differ: two staged launchers were intentionally adapted for input paths; `peav_worker.py` merely stores the parsed URL before checking its path. These are adaptations, not damaged media. Maintained Vibe launchers, not staged launcher copies, are now used by app execution.
- Two staged notices are absent: `audio/StyleTTS2/LICENSE` and `audio/denoiser/LICENSE`. Identical notices already exist at `third_party_licenses/StyleTTS2/LICENSE` and `third_party_licenses/denoiser/LICENSE`; byte equality to donors was verified. Preserve these in packaging; no bulk recopy is required.
- No `copy.log` or `copy.pid` was found at the plan's suggested destination. The verified destination state establishes preservation; it does not establish how/when the user's shell invocation ended.

**Legacy staging follow-up (2026-10-12):** `local_data/donor_migration/storage/projects` and `storage/production` had 286 legacy donor files totaling about 31 MB, although the current copy script excludes these trees and no Vibe runtime code reads the staged copies. Each staged file was SHA-256/size checked against its still-present donor original. The two staged trees have now been removed; the donor originals were confirmed intact. The user may import specific donor media intentionally for acceptance tests. The separately staged `input/Trial-I` is a sample story source, not a runtime dependency. Do not rerun the large copy.

Conclusion: the selected resource/media copy is present and checksum-consistent, with intentional adaptations and the two notices preserved outside staging. Combined with the donor-hidden startup and route checks recorded in `plans/donor_independence.md`, this supports the C1 coding closure; it does not prove that installed models/workflows run. Keep both donor checkouts and the retained ComfyUI setup through runtime acceptance. No donor removal is required for coding completion.
