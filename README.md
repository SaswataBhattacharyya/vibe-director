# Vibe Director

Vibe Director is being built by reusing and adapting verified Story Builder capabilities. The local app now includes story and screenplay workspaces, production setup, image/voice tools, video creation, and nested Media Prep tools. Backend and UI integration remains in active development; consult [the current handoff](plans/HANDOFF.md) for verified progress and open work. A copied module, mock test, or configured workflow alone does not prove that a live generation path works.

Start with [current product plans](plans/README.md), then [collaboration and issue backlog](plans/issue_backlog.md). These govern the new product. [COLLABORATION.md](COLLABORATION.md) records the proposed working agreement for owner `SaswataBhattacharyya` and collaborator `ashucodesbio`.

Local reference sources: Story Builder at `/home/riki/web_dev/story_builder`, OpenMontage at `/home/riki/web_dev/OpenMontage`; ComfyUI/model setup at `/home/riki/web_dev/setup_comfy_and-stuff`. Reference sources and model storage remain outside the product repository. Story Builder is the existing [`mooV_E_maker`](https://github.com/SaswataBhattacharyya/mooV_E_maker) repository; Ashu should clone `https://github.com/SaswataBhattacharyya/mooV_E_maker.git`. Verify source commit/local-file correspondence before reuse.

Older `plans/migration/`, `plans/archive/PLAN.md`, `plans/archive/REUSE_AUDIT.md` and `plans/archive/ideas/` retain historical analysis and reuse evidence; their conflicting product journeys are superseded by the current plans. The public product repository is `https://github.com/SaswataBhattacharyya/vibe-director`. Visibility was changed from the earlier private preference by the owner's explicit instruction. All 14 issues are published; start with [the issue backlog](plans/issue_backlog.md) and [GitHub issues](https://github.com/SaswataBhattacharyya/vibe-director/issues).

## Local development

Run `./start_vibe_director.sh` from this checkout to start the backend and frontend together and open the UI at `http://127.0.0.1:8082/`. It reuses Vibe Director services already responding on ports 3020/8082, starts only missing services, and stops only services it started when you press Ctrl+C. It uses the `react` Conda environment and this checkout's `local_data`. On first use, install frontend dependencies once with `npm ci` from `frontend/`. ComfyUI remains a separate shared service; start it with its existing setup script when needed. See [backend runtime configuration](backend/README.md) and [UI scope](frontend/README.md).

The API starts no render worker. A separate explicitly enabled worker, ComfyUI/models, verified readiness and GPU admission are required for generation. Live acceptance is prepared for the owner's Generate click. Media Prep tools are connected to Vibe's workspace library; the current handoff distinguishes completed local parity work from owner import and installed-runtime acceptance still to be done.

## UI design handoff

Ashu retains UI design ownership. See [the current implementation and UI handoff](plans/ASHU_UI_HANDOFF.md) and draft PR #15; its engineering UI is provisional. Local implementation continues; Git coordination remains deferred until the owner asks for it.
