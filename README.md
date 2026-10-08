# Vibe Director

Plan and reorganize the working Story Builder into one coherent product, reusing verified source capabilities. An initial isolated text-to-video implementation now reuses the verified production ledger, worker, compiler and GPU guards. The full planned application is still in development.

Start with [current product plans](plans/README.md), then [collaboration and issue backlog](plans/issue_backlog.md). These govern the new product. [COLLABORATION.md](COLLABORATION.md) records the proposed working agreement for owner `SaswataBhattacharyya` and collaborator `ashucodesbio`.

Local reference sources: Story Builder at `/home/riki/web_dev/story_builder`, OpenMontage at `/home/riki/web_dev/OpenMontage`; ComfyUI/model setup at `/home/riki/web_dev/setup_comfy_and-stuff`. Reference sources and model storage remain outside the product repository. Story Builder is the existing [`mooV_E_maker`](https://github.com/SaswataBhattacharyya/mooV_E_maker) repository; Ashu should clone `https://github.com/SaswataBhattacharyya/mooV_E_maker.git`. Verify source commit/local-file correspondence before reuse.

Older `migration_plan/`, `PLAN.md`, `REUSE_AUDIT.md` and `My idea/` retain historical analysis and reuse evidence; their conflicting product journeys are superseded by the current plans. The public product repository is `https://github.com/SaswataBhattacharyya/vibe-director`. Visibility was changed from the earlier private preference by the owner's explicit instruction. All 14 issues are published; start with [the issue backlog](plans/issue_backlog.md) and [GitHub issues](https://github.com/SaswataBhattacharyya/vibe-director/issues).

## Local development

Set a product-owned `VIBE_DIRECTOR_DATA_DIR`, then start the API from `backend/` with `PYTHONPATH=. python -m story_builder.isolated_server`. From `frontend/`, install the pinned dependencies with `npm ci` and run `npm run dev`; the UI is at `http://127.0.0.1:8082/`, with API proxy to port 3020. See [backend runtime configuration](backend/README.md) and [UI scope](frontend/README.md).

The API starts no render worker. A separate explicitly enabled worker, external ComfyUI/models, verified readiness and GPU admission are required for generation. Uncovered live acceptance waits for the user's Generate click. FFLF, R2V, story editing, asset preparation and Media Prep are not yet integrated.

## UI design handoff

Ashu retains UI design ownership. See [the current implementation and UI handoff](plans/ASHU_UI_HANDOFF.md) and draft PR #15; its engineering UI is provisional. Implementation is paused pending the owner’s explicit resume.
