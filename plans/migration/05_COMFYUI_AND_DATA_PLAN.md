# ComfyUI dependencies and data preservation

## 1. Runtime arrangement

Retain `/home/riki/web_dev/setup_comfy_and-stuff/ComfyUI` as the local generation engine. Preserve installed node versions, models, auxiliary runtimes and working startup configuration. The app should talk to the current endpoint through configuration. Source release records use backend 3010, production website 8081, ComfyUI 3008 and Ollama 11434; this audit did not probe whether they are running now. The root launcher defaults its frontend to 8080, so do not equate launcher defaults with the recorded release port.

| Dependency group | What is reused | Migration treatment |
|---|---|---|
| H3 | Ref2VA/FL2VA weights, Qwen3-VL encoder, separate video/audio VAEs and H3 nodes | Keep exact paths/versions; retain separate T2V/R2V/FL2VA adapters and readiness evidence |
| Image generation | Qwen Image/Edit, Lightning/LoRA resources, Z-Image and their encoders/VAEs | Copy graphs, not weights; retain recipe-specific defaults |
| Additional video | Wan/LTX models and control/preprocessor nodes | Expert recipes until typed adapter and specific acceptance |
| Speech/audio | Installed TTS-Audio-Suite, voice references/transcripts, Chatterbox/VibeVoice/Qwen/F5/RVC/StepAudioEditX/repair/removal resources | Engine is authoritative; preserve language and reference contracts |
| Music/Foley | ACE-Step and Control-Foley resources; other graph-specific sound models | Integrated fixed graphs first; training gates unchanged |
| 3D/VFX | Hunyuan/Pixal/UltraShape/Blender and SAM/tracking/depth dependencies | Optional expert runtime; no main-app readiness assumption |
| Video analysis | Analyzer source plus isolated InternVideo/ASR/diarization/PE-AV/TalkNet/SAM dependencies | Keep heavy inference subprocess/services isolated |
| Reasoning | Existing provider configuration and guarded execution | Preserve saved run provider; no inference during navigation/readiness inventory |

The audit found **305 weight/checkpoint entries** under the inspected engine model roots. This is a filename/size inventory, not 305 distinct models or a guarantee they load. The same repository also contains standalone checkpoints such as StyleTTS2, outside that count. Do not place weights or datasets in the new Git repository.

## 2. Configuration work

Some paths are configurable now; other roots are hardcoded/package-relative. Introduce a single path resolver and keep compatibility defaults until cutover:

| Concern | Current evidence | Planned handling |
|---|---|---|
| Comfy root | `COMFYUI_ROOT` in audio/model discovery, defaults to existing engine directory | Retain variable; standardize all adapter reads |
| Comfy endpoint | config default 3008; launcher has `COMFYUI_URL` | Retain one explicit endpoint setting and validate callers agree |
| Project/upload/output roots | main.py derives storage/output from package root | Add explicit runtime-root configuration; map legacy defaults |
| Production ledger/stage/image queue | `storage/production/v2_ledger.sqlite3` | Keep schema/store implementations and one writer owner |
| Audio sidecar queue | `storage/production_audio_sidecars.sqlite3` | Preserve separately, with job/prompt IDs |
| Repertoire | `VIDEO_REPERTOIRE_ROOT`; legacy video/analyzer roots partly package-relative | Extend root resolver to legacy clips/runs/corpus paths |
| Legacy output base | config/settings.py points at `/home/riki/web_dev/story_projects` convention | Trace legacy consumers before migration; distinguish from website project storage |
| Provider/model | provider adapter/launcher settings and saved run metadata | Document only safe setting names; do not copy credentials |
| Workflow readiness | smoke files under storage and output | Preserve verified evidence with matching graph/model/compiler scope |
| GPU locks/telemetry | shared guards and prompt-owned watchdog | Retain host-shared admission; two checkouts must not use isolated locks against one GPU |
| Optional analyzer services | existing optional endpoints (TalkNet 8032, SAM Audio 8033, PE-AV query 8034 in source guidance) | Preserve configured service boundaries; do not start/download optional services on app startup |

Proposed new variables such as a unified `VIBE_DIRECTOR_RUNTIME_ROOT` are **to be implemented**. Merely writing them in an env file would not redirect today's package-relative paths.

Create a safe `.env.example` with documented non-secret paths/ports and existing flags only. `VITE_STORY_BUILDER_NEW_PRODUCTION_NAV` and `STORY_BUILDER_ENABLE_DYNAMIC_H3` belong in an explicit configuration manifest. H3 FL2VA remains disabled until its own acceptance exists. Never bulk-copy `.env.local` or shell history into Git.

## 3. Workflow registry and evidence

Copy original graph paths first because adapters, tests and scripts refer to them. Add registry metadata gradually:

`recipe_id`, display name/category, source path, graph format, graph hash, compiler/schema version, required nodes/models, input/output roles, bounds, supported authority/routes, adapter reference, readiness state, evidence reference and original-path aliases.

The registry must distinguish API graphs, UI graphs with nested subgraphs, non-graph presets and configuration JSON. Exact-byte duplicates can be represented by one recipe plus aliases after callers are verified; similarly named graphs with different hashes remain separate versions until reviewed.

### A subtle migration dependency

`production_v2_capabilities.py` locates its last H3 live smoke under `output/disposable-h3-reference-smoke/runs/phase-a-*/manifest.json`. Image readiness looks under `storage/production/image_workflow_smokes`. T2V and FL2VA have their own smoke locations. A source-only copy that excludes all output/storage can disable previously tested recipes.

Preserve the original compact manifests and the referenced verification media/hash scope. In the first compatibility stage preserve the expected layout or attach an isolated copy of evidence. Later introduce a configured evidence root and update capability readers together. Do not fabricate a successful smoke or mark another graph version ready based on the old record. Offline/file presence and source-recorded acceptance remain distinguishable from current engine readiness.

## 4. Data inventory and copy manifest

Before implementation, enumerate these sources without changing them:

- `storage/projects` project JSON, uploads/linked assets, audio scenes, reconstruction, pipeline runs and reference selections.
- `storage/uploads`, `storage/audio_library`, production canon/style/image-smoke/staging metadata.
- `storage/production/v2_ledger.sqlite3` plus sidecar SQLite and any other actual databases discovered in the source walk.
- `output` run/canon/shot/take revisions, original media, review evidence, prompt/refine proposals and manifests.
- `video_repertoire` source assets, clips, audio, jobs/manifests, analysis/corpus/index records and temporary isolation state.
- `video_audio_analyzer/runs` legacy analysis runs and any auxiliary service indexes required by current lookup adapters.
- `video_summariser/out_videos` curated clips/thumbnails used by legacy reference endpoints.
- ComfyUI voice directories and `.reference.txt`/alias files; preserve IDs, not just filenames.
- Standalone training preparation datasets/checkpoints, kept external unless specifically selected.
- Temporary release acceptance media, particularly `/tmp/storybuilder-full-controller-acceptance-20261006-nlmgwm4y`, which is referenced by the Full Reference release record. Preserve required evidence outside `/tmp` before a future cleanup.

A migration manifest records source, intended owner, destination/attachment, size, hash for selected media, referenced IDs and disposition. Do not hash every huge model during a planning-only audit. Preserve original IDs; path relocation should not mint replacement project/asset/take IDs.

## 5. Safe data cutover sequence

1. Create a small representative fixture with copied project metadata, accepted assets, revisions and review evidence. Disable render/text/audio consumers or use completely isolated stores. Read-only views must not resume source queued jobs.
2. Validate every fixture asset reference resolves to the same bytes/MIME/probe and role. Verify project → run → shot → take ancestry and voice/identity bindings.
3. Record active/submitted/held jobs and actual engine prompt IDs before live cutover. Drain or transfer ownership explicitly. Preserve source acceptance checkpoint holds.
4. Stop the old app's writers/consumers before taking a consistent final data snapshot. Account for analyzer/downloader writers too. Keep the engine independently owned; stopping an app is not permission to interrupt an unrelated render.
5. Use SQLite backup/checkpoint tooling or a quiesced consistent snapshot. Never copy only a live `.sqlite3` while ignoring WAL/SHM. Keep JSON/media snapshot consistent with database references.
6. Copy/attach data using the manifest. Rewrite stored absolute paths only through a versioned, reversible migration with old→new path mapping; preserve hashes/provenance/original evidence paths.
7. Start one migrated consumer owner. Reconcile submitted jobs before resuming. Unknown outcomes stay held. Confirm existing locks/watchdog ownership work across the transition.
8. Validate accepted media playback, gate state, run recovery and selected outputs. A representative render is only needed to resolve an actual adapter/runtime change, with saved evidence and existing GPU policy.
9. Switch entry point after parity. Keep original source and snapshot available for rollback. Rollback stops new writers first and restores the coherent snapshot; do not merge two diverged live stores by copying newer filenames.

### Ownership invariants

Project-owned uploads remain project-owned. Shared repertoire links remain shared and should not be duplicated unnecessarily. Deleting a project must not delete a shared library source. No client-supplied path escapes the configured allowed roots. Transient Comfy staging belongs to its exact job and can be cleaned only after that job's ownership/outcome is established.

## 6. Application hosting boundary

First target is the existing local working website for you and Ashu. Private GitHub collaboration does not itself supply application login/access control. If a public/remote customer website is selected later, project authorization, upload isolation, authenticated media access, engine access and deployment topology need a separate concrete plan. Do not expose local ComfyUI ports to customers or add a full SaaS architecture to this migration by default.

The immediate runtime decision to confirm at implementation kickoff is whether Ashu runs CPU/mock fixtures locally, connects to the owner's shared engine, or has another engine. Source changes remain portable while local model weights and secrets stay machine-specific.
