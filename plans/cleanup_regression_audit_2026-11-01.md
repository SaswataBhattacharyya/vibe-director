# Cleanup regression audit — 2026-11-01

Follow-up: all five findings below were addressed by `cleanup_ui_repair_2026-11-01.md`. Retained evidence and practical acceptance limits are recorded there; the original audit is preserved below.

Scope: remaining storage/registry/browser-selection gaps after the shared-library and ACE/Editor recovery. This is an audit, not a claim of end-to-end generation acceptance. No product code, retained media, project registry or model was changed in this audit. No generation, provider request or training was run.

## Original findings (repaired in the authorized follow-up)

1. **High — shared-only assets display but several actions fail.** `backend/story_builder/services/media_library.py` merges shared records for `list_assets` and `asset_path`, but `update_annotations`, `set_asset_archived`, `assign_role` and `delete_extracted_asset` still search only the workspace manifest. Temporary migrated fixtures reproduce failures for tagging, hiding, reference-role assignment and extracted-asset removal after ownership moves to tool-library. Fix the shared-record-to-workspace-membership write boundary, including consistent archive/deletion semantics; do not bypass ownership checks or remove files used by other memberships.

2. **High — new analysis publication can fail for a shared-only source.** `register_derived_media` checks the source only in the workspace manifest. A temporary migrated fixture resolves/displays the source successfully but publication rejects it as missing or changed. `video_summarizer_results.publish_analyzer_outputs` calls this function, so running analysis on affected library sources risks completing expensive analysis without publishing its outputs. No GPU analysis was run to reproduce this; the failing publication boundary was exercised directly. Resolve the source using the same owned shared-record contract and retain hash/provenance validation.

3. **High — retained ACE LoRAs are absent from the adapter registry.** `local_data/ace_step/state.json` has no project documents; `ace_studio.snapshot` derives adapters exclusively from projects. There are 82 LoRA checkpoint files across nine training runs, plus 82 full training checkpoints, under `ace_step/runs`. These counts describe checkpoint versions, not 82 distinct trained styles or duplicates. Files are present, but the UI cannot select them through the cleared registry. Recover verified adapter metadata into a tool-level registry without restoring deleted projects. Do not retrain or delete checkpoints to repair registration.

4. **Medium — deleted browser selections remain in other pages.** Live isolated-browser checks reproduced rejected requests for a tombstoned workspace from Story, Screenplay, Setup, Characters, Worlds, Frames and Create. Music Jukebox also requests a removed cached project and shows “Music endpoint not found”; its new-project controls remain available. `preferredMediaWorkspaceId` now validates some cached selections, but explicitly requested IDs and cached drafts passed as requested IDs bypass that validation; several story pages read storage directly. Validate selections against current IDs and clear only stale pointers, preserving drafts and respecting an explicitly missing deep link with a clear recovery action.

5. **Low — tool-library is still queried as a story.** Characters/Worlds/Frames and Create/Current Take can request story endpoints using `tool-library`, producing HTTP 422 and misleading story-target warnings in standalone use. Audio Studio has the same unnecessary screenplay lookup. Separate optional story context from the media-library ID; standalone tools should not need a screenplay.

## Checks completed

- Resolved all **244 retained catalogue records** through the actual `asset_path` consumer: **68 YouTube downloads + 176 repertoire outputs**, all files present and recorded sizes matching. This audit did not rehash entire media files; the earlier cleanup recorded hash verification.
- Trial 1 Scar storyboard export exists at `local_data/projects/trial 1 scar/story/storyboard.json`.
- Browser sweep: 16 routes with valid selections and again with stale selections, plus the actual Music Jukebox tab. No uncaught page JavaScript exceptions were observed in the route sweep. Write requests were blocked; resulting “Failed to fetch” messages were excluded from findings. The invalid `tool=jukebox` shortcut did not exercise Jukebox; the separate real-tab check did.
- Playwright MCP could not initialize because its browser profile was already in use. Used a separate headless Chromium session through Playwright; the owner's browser was not closed or modified.
- Existing storage-migration/media-library tests: **32 passed**. The temporary fixture probes expose cases absent from those tests; passing tests do not close the findings above.

Raw local evidence: `/tmp/vibe-gap-audit.json`, `/tmp/vibe-gap-browser.json`, `/tmp/vibe-gap-jukebox.json`, `/tmp/vibe-gap-tests.log`. Reproduction scripts: `/tmp/vibe-gap-audit.py`, `/tmp/vibe-gap-browser.mjs`, `/tmp/vibe-gap-jukebox.mjs`.

Recommended repair order: shared read/write boundary and analysis publication; tool-level ACE adapter recovery; consistent stale-selection recovery; optional story-context guards. Verify producer-to-consumer actions in disposable data before any owner-clicked GPU acceptance. Do not restore pruned projects or blindly roll back the cleanup.
