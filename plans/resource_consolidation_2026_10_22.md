# Story Builder resource consolidation — 2026-10-22

## Owner request and outcome

Owner authorized moving required models/resources into Vibe Director, retaining a lighter Story Builder source folder, removing generated tests, and checking affected consumers. Harbor Light was already deleted; the live workspace API still returns zero story workspaces.

- Consolidated **666 files / 54,566,092,419 bytes**: analyzer and summarizer model trees, audio checkpoints/media, downloaded video/audio and preserved analyses. SHA-256 compared each file before changing its source entry.
- **54,488,575,439 duplicate bytes removed**. **77,516,980 unique bytes relocated** into `local_data/story_builder_resources/`. Existing canonical copies remain under `local_data/donor_migration/`.
- Story Builder retains compatibility symlinks, with **666/666 resolving**. 627 targets are in Vibe; 39 reuse the retained shared ComfyUI TTS installation. No standalone weight files remain in Story Builder outside dependency environments. No Vibe resource links point back into Story Builder.
- Story Builder decreased from approximately **62 GiB to 8.1 GiB**. Its retained `video_summariser/.venv` accounts for **6.3 GiB**; source, frontend dependencies, documentation and ancillary data account for most of the balance. The environment was intentionally retained, not moved or claimed as a Vibe runtime. Vibe continues using its existing supported environment.
- **64/64 protected files unchanged**: existing voices, downloaded/analysed assets, Comfy output/video(s), and retained originals. ComfyUI models/runtime were not relocated. No provider/GPU generation or clock changes.

## Test cleanup

Identified 27 disposable/validation projects, their generated output folders, and image smoke staging. Deleted writable test material; **two root-owned remnants remain** below. Preserved eight original uploaded inputs under `local_data/story_builder_resources/preserved_validation_inputs/`. Trial story source and the Util project's downloaded/extracted audio remain.

Removed **3,946,354 disposable production events**, 13 takes, 9 runs and related test records. Compacted donor ledger from 2,468,171,776 to **167,936 bytes**. Integrity check `ok`; foreign-key check empty; the non-disposable trial run remains. This ledger is Story Builder's historical database, not Vibe's live ledger.

Blocked roots (sudo requires owner password):

- `/home/riki/web_dev/story_builder/storage/projects/demucslive-7da28818`
- `/home/riki/web_dev/story_builder/storage/projects/audio-phases-2-4-live-validation-b47f4bb7`

Owner can restore ownership only for these test remnants, then the agent can finish deleting them:

```bash
sudo chown -R "$(id -un):$(id -gn)" -- \
  /home/riki/web_dev/story_builder/storage/projects/demucslive-7da28818 \
  /home/riki/web_dev/story_builder/storage/projects/audio-phases-2-4-live-validation-b47f4bb7
```

## Path impact and checks

No installed skill named “blast radius” was found. Used Graphify plus source/config and filesystem consumer searches. Graphify query found no matching analyzer nodes; its incremental output is not a complete dependency proof. Refreshed the graph after the copy-helper change.

- Vibe analyzer, repertoire, Image Detailer and audio services already consume Vibe staging or shared Comfy resources; no hard-coded Story Builder checkout dependency found in those runtime consumers. Preserved modified Vibe analyzer code; did not overwrite it with donor source.
- Old Story Builder relative/absolute file paths still resolve via compatibility links. Files relocated individually, so retained source modules and parent-relative imports remain in place.
- Updated `tools/copy_donor_resources.sh` to dereference compatibility links when copying, avoiding staged self-links; added previously omitted `.t7` checkpoints and `.aup3` projects. Shell syntax and dry-run completed successfully; no copy pass rerun.
- SHA-256 verified before each transfer; final path/size checks passed for all 666 links. Protected-media hashes rechecked. Live workspace GET succeeded with no Harbor Light project.
- This is filesystem/path verification, **not full model inference or UI acceptance**. Existing full-automation smoke evidence still requires fresh owner-generated renders following the earlier test-output deletion.

## Local evidence

Ignored JSON/JSONL under `local_data/`:

- `resource-transfer-preview-2026-10-22.json`
- `resource-transfer-2026-10-22.jsonl` — exact source, destination, bytes, SHA-256, deduplication decision
- `resource-transfer-verification-2026-10-22.json`
- `story-builder-test-cleanup-2026-10-22.json`

No workers, Git operations, services restarted, or UI code changes in this consolidation.
