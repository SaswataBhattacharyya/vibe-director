> **Historical document — superseded for current migration direction on 7 October 2026.** The user chose to reuse and reorganize the working Story Builder app. Follow [migration_plan/00_READ_ME_FIRST.md](migration_plan/00_READ_ME_FIRST.md) for the current capability, UI, API and data plan. The original text below is retained for traceability.

# Story Builder reuse audit for Vibe Director

Date: 2026-10-03. Scope: read-only audit of `/home/riki/web_dev/story_builder` against the proposed first Vibe Director journey in [PLAN.md](PLAN.md). **No source code, workflows, models, media, or runtime state was copied or changed.** This is a reuse decision map, not acceptance of the old product.

## What was checked

The source tree is a broad local workspace, not a clean repository: its top-level `.git` is not usable as a Git repository, it has no top-level LICENSE file, and it includes generated output, storage, model files, nested third-party repositories and licenses. The FastAPI route file is 4,325 lines and the Production workspace page is 841 lines. Those sizes are not defects by themselves; they show that copying the whole app would carry many unrelated dependencies and product assumptions into a new start.

Read source and focused tests for the H3 graph compiler, media staging, project asset registry, durable ledger/worker, chunked story generation, Director contract, old production runner, API imports, and Production UI. Two read-only focused runs passed: **52 tests** for graph/media/assets/ledger/chunking and **34 tests** for worker/Director/shot validation/capability. They used the existing `react` Python environment with bytecode and pytest cache writes disabled; they did not contact ComfyUI, start a service, or inspect generated quality. Four warnings in the latter run concerned deprecated FastAPI `on_event` hooks.

## Reuse decisions

| Source | Assessment | What to bring into Vibe Director | Condition before copying/adapting |
| --- | --- | --- | --- |
| `services/minimax_h3_graph_compiler.py`, `workflows/api/minimax_h3_r2v_api.json`, matching tests | **Strong candidate, for a reference-based renderer** | Typed reference plan, deterministic graph compilation, same-loader video+paired-audio wiring, resolved tags, prompt-tag lint, node preflight. | Choose R2V for the first milestone or defer it. Recheck exact installed ComfyUI node/socket/model versions and run a disposable decoded video+audio smoke. The compiler explicitly rejects zero references and has Story Builder names/paths. |
| `services/minimax_h3_media.py`, matching tests | **Strong candidate when media references are selected** | FFprobe, bounded 24-fps conversion, synchronized paired audio, hash-owned temporary staging and cleanup. | Adapt ownership roots/names; verify errors and cleanup on the new filesystem. Do not stage at all for a text-only first shot. |
| `services/production_assets.py`, matching tests | **Adapt a small subset** | Asset IDs, MIME/probe/hash validation, path containment, one canonical output and safe content lookup. | Define Vibe Director's minimal asset roles first. Avoid importing the old 20-plus-role catalog and shared Video Repertoire semantics before needed. Review third-party media probing dependencies and upload size policy. |
| `services/production_ledger.py`, `services/production_job_worker.py`, `services/production_reconciliation.py`, matching tests | **Adapt a minimal durable job core** | Idempotent take creation, reserved Comfy prompt ID, explicit states, restart reconciliation, no blind retry after uncertain submit, one-GPU-job admission. | Specify the first job state machine and storage contract; port only required transitions. Integration-test against a disposable ComfyUI job and restart. Mocked tests do not establish live recovery. |
| `services/chunked_generation.py`, `services/director_contract.py`, `prompts/minimax_h3/`, matching tests | **Reuse design; code later** | Source-fact checks, stable IDs, bounded repair, provider-neutral calls, prompt rules and non-mutating Refine proposals. | Decide whether the first story is long enough to need chunking and define the new story/shot schema. Re-evaluate prompts on representative stories; deterministic checks are not proof of narrative quality. |
| `workflows/api/minimax_h3_t2v_api.json` and other versioned API graphs | **Reference fixtures, not ready-made capabilities** | A candidate graph to inspect for a no-reference first shot. | Inventory local models/nodes and decoded output. The T2V-named graph contains a `MiniMaxH3ImageToVideo` node; inspect its exact local contract before choosing it. Never expose a workflow only because JSON exists. |
| `tests/test_minimax_h3_*`, `test_production_assets.py`, `test_production_ledger.py`, `test_production_job_worker.py` | **Adapt high-value cases** | Boundary, ownership, pairing, idempotency, ambiguous-submit and restart scenarios. | Rewrite fixtures against the new contracts; retain tests that detect real failure modes, not old route shapes. |
| `frontend/app/src/pages/ProductionWorkspace.tsx`, `frontend/app/src/lib/project-api.ts`, `api/main.py` | **Study flows; rebuild boundaries** | Review the user states and DTO ideas for story, shot, queue and output review. | The page is a large stateful component with many `any` values and old endpoint/storage assumptions; the API file imports most subsystems. Build a small, typed frontend and modular API around the selected first journey. |
| `services/project_store.py`, `services/story_pipeline.py`, `services/production_runner.py`, `services/manual_director.py` | **Do not copy as the new foundation** | Use as historical examples only. | The old project shape expects six artifacts and broad app compatibility. The production runner uses fixed fixture images/music and picks two scenes, so it cannot establish a general story-to-video path. |
| `video_repertoire/`, `video_audio_analyzer/`, `video_summariser/`, `audio/`, `Art_ist_min/`, model files, generated `output/` and `storage/` | **Defer or exclude** | Specific capabilities only after a later product milestone asks for them. | Large generated/vendored trees have separate provenance and licenses. Never bulk-copy them into the new Git repository. |

## Architecture implication

For a first single-shot slice, define **Project → StoryRevision → ShotPlan → RenderTake → OutputAsset** and the statuses/ownership between them. A ShotPlan is an editable intention; a RenderTake is one immutable submission/result; an OutputAsset is a canonical file with provenance. A selected reference is an approved asset plus use intent, not a raw path. These definitions are proposed and should be reviewed with the first user journey.

Build the smallest frontend and API around that model. Port the asset and job invariants first. Choose text-only or reference-based H3 after a local capability spike; the current R2V compiler is valuable only if that route is selected. Keep reasoning/prompt work behind a provider interface so it cannot submit arbitrary Comfy graphs or silently mutate user-approved facts.

## Evidence gaps and next gate

1. **Ownership/provenance:** establish which first-party source files may be moved into a private repository and record their original paths and hashes. Root code lacks usable Git history/license metadata; nested third-party packages, models, and sample media have separate terms.
2. **First-result choice:** decide whether the MVP promises a plan or a playable clip. A playable clip makes the renderer spike and durable job core prerequisites.
3. **Local capability:** inspect the exact current ComfyUI `object_info`, model availability, GPU admission, and one disposable video **with audio**. Prior Story Builder logs are leads, not current acceptance.
4. **Migration slice:** after the product brief, select one module at a time, adapt its interfaces, port meaningful tests, and record source hash, changes, and new acceptance evidence. Avoid a wholesale tree copy.

## Source fingerprints for future provenance

| File | SHA-256 |
| --- | --- |
| `services/minimax_h3_graph_compiler.py` | `a9837a7cb28802e48c3a3235a48c9cad020b0efe3ba1960b31d7ffecce934c07` |
| `services/minimax_h3_media.py` | `2d76ae7a4f0c6853ba03330dc6cb0f76132d679c17d2c32fce5faf8eea3782e0` |
| `services/production_assets.py` | `39a32df36d50e0d220f8b66cfdec689d8dad164bc5b752b6cc136a200f19303f` |
| `services/production_ledger.py` | `2d94538605518bd1b5cd194e07804467d3a520b6ee2227625db6eeb5f86f3ea8` |
| `services/production_job_worker.py` | `5330ed304f53878f7ea4b677a41013076f790880588b36261c44096d9b2d5c4c` |
| `workflows/api/minimax_h3_r2v_api.json` | `5ebac422ff9dd1eb467265d36610f10fa8744ff8c8d31262cd9bf871b814332d` |
