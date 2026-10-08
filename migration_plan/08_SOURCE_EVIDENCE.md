# Source evidence and migration index

**Audit date:** 7 October 2026. Read-only filesystem/AST/JSON analysis. No application import, network health probe, test suite, training, model loading, provider call or GPU render was performed in this audit.

## Coverage and interpretation

The source indexes cover all top-level services and decorated API handlers, frontend page routing, all workflow JSON files, key implementation bodies/contract tests/release manifests, and standalone tool entry points. Installed engine inspection was limited to setup descriptions/configuration, custom-node/model layout and dependencies required by these capabilities. Vendored model implementation lines and model binaries were not exhaustively read.

The table below is a traceable index, not a readiness certificate. Hashes are file SHA-256 values at audit time; they allow a future migration manifest to detect intervening edits. Nested UI subgraph counts enumerate stored definitions, not expanded runtime instances. Duplicate hashes indicate exact byte duplicates only; semantically equivalent graphs may differ in metadata.

**Counts:** 71 top-level service modules; 224 HTTP method/path entries; two startup/shutdown handlers; 90 workflow-directory JSON files; 305 weight/checkpoint entries in inspected engine model roots. Backend main.py has 7167 lines.

## Release evidence

| File | Scope |
|---|---|
| [plan/new_complete_plan/12_CURRENT_STATUS.md](/home/riki/web_dev/story_builder/plan/new_complete_plan/12_CURRENT_STATUS.md) | Current source status, superseding older planning notes |
| [plan/new_complete_plan/25_PRODUCTION_OPERATOR_GUIDE.md](/home/riki/web_dev/story_builder/plan/new_complete_plan/25_PRODUCTION_OPERATOR_GUIDE.md) | Operator/recovery constraints and current runtime contract |
| [plan/new_complete_plan/27_FINAL_RELEASE_2026_10_07.md](/home/riki/web_dev/story_builder/plan/new_complete_plan/27_FINAL_RELEASE_2026_10_07.md) | Reported tests/runtime/native acceptance, limits and preserved temporary roots |
| [plan/new_complete_plan/evidence/FINAL_PLAN_ACCEPTANCE_20261007.json](/home/riki/web_dev/story_builder/plan/new_complete_plan/evidence/FINAL_PLAN_ACCEPTANCE_20261007.json) | Original required upgrade/representative acceptance; excludes optional unverified models and every-shot rendering |
| [plan/new_complete_plan/evidence/D5_RELEASE_20261006.json](/home/riki/web_dev/story_builder/plan/new_complete_plan/evidence/D5_RELEASE_20261006.json) | Three native clips, continuity and scene reset; no film stitching |
| [plan/new_complete_plan/evidence/FULL_DIRECT_ACCEPTANCE_20261006.json](/home/riki/web_dev/story_builder/plan/new_complete_plan/evidence/FULL_DIRECT_ACCEPTANCE_20261006.json) | Representative configured-provider Full Direct shot/continuation |
| [plan/new_complete_plan/evidence/FULL_REFERENCE_ACCEPTANCE_20261006.json](/home/riki/web_dev/story_builder/plan/new_complete_plan/evidence/FULL_REFERENCE_ACCEPTANCE_20261006.json) | Representative Full Reference accepted masters, native take and review/scene reset |

The source release describes a live launcher session `83317`. That is a **historical source-recorded handle**, not a process created, probed or managed by this audit. Current live state needs inspection before any implementation cutover.

## Service modules

Initial destination for every file in this table: `<Vibe Director>/app/story_builder/<source-relative path>`. Subsequent router boundaries are in document 04.

| Source | Lines | Purpose from module docstring | SHA-256 |
|---|---:|---|---|
| [services/__init__.py](/home/riki/web_dev/story_builder/services/__init__.py) | 1 | story_builder services. | `79e97abf1eb250ae2364ac1d06954aecfd69f44922e904fe819fe8c0b6b99382` |
| [services/audio_automation.py](/home/riki/web_dev/story_builder/services/audio_automation.py) | 151 | Typed, ordered audio automation registry and runner. | `55a4015095a002f9f124841874c56cf735471ac5ee1cc8b56697a15492ae8cbe` |
| [services/audio_catalog.py](/home/riki/web_dev/story_builder/services/audio_catalog.py) | 231 | Read-only audio capability, voice, and model discovery for the Audio Studio. | `f92b0c9bf2f2355a4ffcae07ac0047943c44dc5d9ef216b3e233fea9d7011feb` |
| [services/audio_effects.py](/home/riki/web_dev/story_builder/services/audio_effects.py) | 254 | Fixed ComfyUI audio-effect workflows for Audio Studio and Hermes. | `1ea966791e9295f4c236d6d36c0832b1bfab94655dd50eb2eeaab4b361459bd5` |
| [services/audio_finetune.py](/home/riki/web_dev/story_builder/services/audio_finetune.py) | 296 | Project-scoped F5-TTS dataset validation and preparation. | `ab8f4d8edb7f623e5273c9e75a8718bbb43ded9ce327642120615928cf5396cb` |
| [services/audio_reconstruct.py](/home/riki/web_dev/story_builder/services/audio_reconstruct.py) | 117 | Project-owned dialogue reconstruction maps, parts, and immutable takes. | `aac8549083b754743182ef286ff4d772e0308dac76a97daf964958544d33f0d7` |
| [services/audio_scene.py](/home/riki/web_dev/story_builder/services/audio_scene.py) | 162 | Project-scoped wrappers for TTS-Audio-Suite scene split/stitch tools. | `772c526b37e13bc1e2a004a36d826c59744e2fa141366d0433276676d1b1ee3c` |
| [services/audio_tts.py](/home/riki/web_dev/story_builder/services/audio_tts.py) | 218 | Prepared Phase 2 timed multi-character TTS execution. | `a977cd7a7ac04c5d5969b53c71b606e8153d5bb5fd3e332e6b143525fb3ec55e` |
| [services/audio_utilities.py](/home/riki/web_dev/story_builder/services/audio_utilities.py) | 253 | Managed audio library and deterministic batch utility jobs. | `a6cb4c11066cfe1f8bc42144ac60884ac8f3f5bb8461bc9a8d8832906a69ea5e` |
| [services/chunked_generation.py](/home/riki/web_dev/story_builder/services/chunked_generation.py) | 462 | Chunked, completeness-checked text generation for production V2. | `b7910ef04039c523730fcbceb8ed64977af8d106ab1b7166ddf84a28694782cb` |
| [services/control_foley.py](/home/riki/web_dev/story_builder/services/control_foley.py) | 157 | Typed Control-Foley jobs backed by fixed ComfyUI API workflows. | `8b6d556674fae27dc49acfd190a2193970869e3ce360007522112086b97fd1b9` |
| [services/director_contract.py](/home/riki/web_dev/story_builder/services/director_contract.py) | 709 | Versioned prompt-corpus access and deterministic H3 Director lint helpers. | `a6c51c884336382b5ff8289b78cc62effbf34b4ba8ad30cbd3e6b12b39e01b8f` |
| [services/director_pipeline.py](/home/riki/web_dev/story_builder/services/director_pipeline.py) | 33 | Director-level scene brief generation used by the production coordinator. | `cc89eba98a06a6b6d59bd87a86cfdf88ee3cbb1b198095b73e74b7461e03de0a` |
| [services/gpu_runtime.py](/home/riki/web_dev/story_builder/services/gpu_runtime.py) | 245 | Host-side GPU admission checks and durable telemetry for local ComfyUI work. | `1afb61596068b4594c3f9c5e555ed2476b5955c22ebec98a59a7aa8a78524d32` |
| [services/gpu_watchdog.py](/home/riki/web_dev/story_builder/services/gpu_watchdog.py) | 167 | Prompt-owned thermal supervision, independent of backend HTTP polling. | `f4f4ccfe5d148620456ca0d94f3903755867528a2980b843d9348d800c7ec7cc` |
| [services/image_detailer.py](/home/riki/web_dev/story_builder/services/image_detailer.py) | 174 | Evidence-based image detailer facade used by Story Builder. | `5fbc7a2f7ff8eee57db69ab010e4c9686f9f5283ab939c2cdd261e93d8c2fdd7` |
| [services/manual_director.py](/home/riki/web_dev/story_builder/services/manual_director.py) | 476 | Manual, workflow-aware ComfyUI runs stored in the shared video repertoire. | `f69f6fc8c80e6619ea6db873128dc6c451d3de3b402ca5e7da8aa60810abaa03` |
| [services/media_jobs.py](/home/riki/web_dev/story_builder/services/media_jobs.py) | 406 | Generic media job persistence and ComfyUI execution helpers. | `c76608d880d09f966e914ee283999f44d06905731332ebc7321cf0d9bb6a98e0` |
| [services/minimax_h3_graph_compiler.py](/home/riki/web_dev/story_builder/services/minimax_h3_graph_compiler.py) | 417 | Typed, deterministic compiler for local MiniMax H3 reference-to-video graphs. | `a1355882cf07f395a0ce5ba561c290e7e8e64e989d27ac4f59b0404e01cfaef3` |
| [services/minimax_h3_media.py](/home/riki/web_dev/story_builder/services/minimax_h3_media.py) | 446 | CPU-side media probing and job-owned video staging for local H3 R2V. | `a74fe5f93676062dcfb6aa0005297b0a813d7ffc5ea93ba60de12bf8367cd69e` |
| [services/minimax_h3_t2v.py](/home/riki/web_dev/story_builder/services/minimax_h3_t2v.py) | 47 | Deterministic compiler for the installed local MiniMax H3 text-to-video graph. | `c17ba00efb7b873bd256afa978d7b2eee13ac18395d92d48ee1e63151d88d712` |
| [services/music_sound.py](/home/riki/web_dev/story_builder/services/music_sound.py) | 103 | Fixed ACE-Step music jobs and fine-tuning capability contracts. | `0d2e7e4717f2ddef69dafafb7944f5729f3c109e7af2a3dfa719a1b33c034c13` |
| [services/narrative_style_library.py](/home/riki/web_dev/story_builder/services/narrative_style_library.py) | 403 | Validated, revisioned narrative style drafts and immutable published versions. | `9cd901aec8c78079e27177b868546c32bf82c70d5aa4541e7b6eeba6d89de700` |
| [services/narrative_style_sources.py](/home/riki/web_dev/story_builder/services/narrative_style_sources.py) | 166 | Safe text extraction with page/line evidence locators for style references. | `e67ace433c58b5e4d7a84d84ec698fad6a749b2f62e82d5b44fef52417d45019` |
| [services/ollama_client.py](/home/riki/web_dev/story_builder/services/ollama_client.py) | 230 | Minimal Ollama client for structured OpenClaw planning steps. | `18803cddac47a69b8351f09a4c3f26e76ecfd156e3b41a428b2f0edafd8d6952` |
| [services/production_assets.py](/home/riki/web_dev/story_builder/services/production_assets.py) | 474 | Project-scoped production asset registry with safe one-copy ownership. | `6b9c855fe804315479e8fd870bcdeb41739facb2c20204a4f090945e3158a0af` |
| [services/production_audio_sidecars.py](/home/riki/web_dev/story_builder/services/production_audio_sidecars.py) | 66 | Durable optional audio queue with idempotency and exact-prompt recovery. | `34d3bf8d4a2d5c069167f64b61731adef7eb76d5ff0a5ccd96d35cb7b054f733` |
| [services/production_authority.py](/home/riki/web_dev/story_builder/services/production_authority.py) | 12 | Resolve human/Director decision authority from immutable run configuration. | `e1f99ad3fe69a378d30d1f5cb61e8354510dd0e8a237955ef57458adfd31f71c` |
| [services/production_dialogue_tts.py](/home/riki/web_dev/story_builder/services/production_dialogue_tts.py) | 205 | Run-bound multi-speaker dialogue TTS over the durable production queue. | `6e109e412a3d56ed1a85cfbd7ea6dc1ee3cf29cf755be0fea0743d90cf4905a9` |
| [services/production_director_profiles.py](/home/riki/web_dev/story_builder/services/production_director_profiles.py) | 45 | Versioned Director behavior profiles, separate from narrative prompt styles. | `900b219345d87e20ff1e1a1e60bc9a76f98edd144efc645028702424b6316196` |
| [services/production_fl2va_capability.py](/home/riki/web_dev/story_builder/services/production_fl2va_capability.py) | 91 | Read-only preflight for the existing local H3 first/last-frame API graph. | `b59d8af4a3a7be2b71ca920cdbe4345591a71e53752975e408f8df130a0e3963` |
| [services/production_image_director.py](/home/riki/web_dev/story_builder/services/production_image_director.py) | 110 | Bounded, evidence-backed visual review for Full-mode image candidates. | `00997810e0ac02afe06523f736e0e203430a9e03cea9273e59f568c3e68d24f6` |
| [services/production_image_jobs.py](/home/riki/web_dev/story_builder/services/production_image_jobs.py) | 646 | Durable project-scoped queue records for production image candidates. | `51dae5f288953f0eee85270c84792d2d69dd46ebcf7de44ed1a77b1a35898d56` |
| [services/production_image_worker.py](/home/riki/web_dev/story_builder/services/production_image_worker.py) | 590 | Serialized ComfyUI worker for durable production image candidates. | `b05b695cf2de67f7b2da000c9b879e250df3ee1e8f45399d8bbe8b6ded5d5a11` |
| [services/production_image_workflows.py](/home/riki/web_dev/story_builder/services/production_image_workflows.py) | 269 | Typed, fail-closed adapters for the project's ComfyUI image workflows. | `2ba1fe16d74358cdcb01fa54209fd981eb113424ae4cd248b6a16a952315a602` |
| [services/production_job_worker.py](/home/riki/web_dev/story_builder/services/production_job_worker.py) | 637 | Serialized, durable, testable ComfyUI worker for production V2 H3 takes. | `f1da73d22e595868405e0ebddcf03e965453613a7c6d3da95c763dfef873228b` |
| [services/production_ledger.py](/home/riki/web_dev/story_builder/services/production_ledger.py) | 1256 | Durable, project-scoped ledger for the new production pipeline. | `39d2fc7eccd9fa288f5096a4cbbd13ab3c444396c0b911c8224f91905e510bab` |
| [services/production_reconciliation.py](/home/riki/web_dev/story_builder/services/production_reconciliation.py) | 88 | Read-only ComfyUI reconciliation for durable V2 take records. | `ee675285e93b18edd0157bae7360a8781f9c7daa9616fb7c40c4aa10a62bb20e` |
| [services/production_refine_store.py](/home/riki/web_dev/story_builder/services/production_refine_store.py) | 54 | Run-scoped, atomic storage for non-mutating H3 Refine proposals. | `2a9844bb0faa1b40f11e6721baf42c367947003cff1cc3521e2e93e65bca2859` |
| [services/production_route_assets.py](/home/riki/web_dev/story_builder/services/production_route_assets.py) | 92 | Making-route policy for required and accepted character/world image masters. | `de5e7155b3a4d7a9139c08a5cab0d08295f651877401551e9a031c995f392df0` |
| [services/production_runner.py](/home/riki/web_dev/story_builder/services/production_runner.py) | 137 | Dependency-ordered, two-scene production runner. | `1cae728d021594fa27f41a815680cae1d1c8335c00c87588781909af47b3c593` |
| [services/production_shot_plan.py](/home/riki/web_dev/story_builder/services/production_shot_plan.py) | 111 | Structured, immutable shot-plan revision helpers for production V2. | `4f6c507a25db2cfd85d185c59effecae4912e34cf8c494d5cc868f4ef256d344` |
| [services/production_shot_validation.py](/home/riki/web_dev/story_builder/services/production_shot_validation.py) | 186 | GPU-free, project-scoped validation and compilation of one H3 R2V shot. | `36626966f6da28be879c40a66639a53f91749b2b83fd5b6f137952785c8e86f2` |
| [services/production_stage_tasks.py](/home/riki/web_dev/story_builder/services/production_stage_tasks.py) | 278 | Durable, idempotent queue for text-stage work in Production V2. | `4f969f6f03fa9ab53ed6d0fd9e378af9735cf5d45c044df96f135885b8df3d98` |
| [services/production_story_revisions.py](/home/riki/web_dev/story_builder/services/production_story_revisions.py) | 139 | Atomic, run-scoped story canon revisions for production V2. | `86c3c3c11d18eee8c47ef475ecf6533f5b6194dc18102f8904a354d6a1689992` |
| [services/production_style_catalog.py](/home/riki/web_dev/story_builder/services/production_style_catalog.py) | 38 | Additive hierarchical catalog for the new production flow. | `005189c6fcf7515aab5963325e89e9b8ca987d9ab06eafa86b16eb00b64b6a47` |
| [services/production_t2v_capability.py](/home/riki/web_dev/story_builder/services/production_t2v_capability.py) | 90 | Fail-closed preflight for the separately tested H3 T2V production route. | `2637d6b4fc881596c5a0b0efdcab1b084da9a7bd2835e6cd732a14fa4404272e` |
| [services/production_take_runtime.py](/home/riki/web_dev/story_builder/services/production_take_runtime.py) | 172 | Project-scoped preparation and output collection for durable H3 takes. | `455a7e8d5c12d93d9f3a2e2caf41d86c96f9b918046a27a15208e1f55d596f66` |
| [services/production_temporal_video_evidence.py](/home/riki/web_dev/story_builder/services/production_temporal_video_evidence.py) | 97 | CPU-only, hash-bound timed-frame evidence; no acceptance or render authority. | `67572dd387e1880ae560fa2b09b4dafbaa1f4fcdebe3c87822f50ac0a894d282` |
| [services/production_text_controller.py](/home/riki/web_dev/story_builder/services/production_text_controller.py) | 469 | Narrative scene and shot outline planning for the durable text controller. | `6faf52538bc1df73f4ebfdd1c032fc3a73e8f047cb099322d55ed92d21408d9e` |
| [services/production_text_repair.py](/home/riki/web_dev/story_builder/services/production_text_repair.py) | 45 | Preserve approved units during an explicitly requested bounded text repair. | `87c6d93edf65b83e4a1c7fb0477988c5c8637544771171b25b20fce9250b2937` |
| [services/production_v2_capabilities.py](/home/riki/web_dev/story_builder/services/production_v2_capabilities.py) | 95 | Capability catalog for the opt-in dynamic H3 production path. | `5d50e542fad20df983edd7b4fbba4e1c36ef50a71dc3f71aca3a9b0e44cb6d20` |
| [services/production_video_director.py](/home/riki/web_dev/story_builder/services/production_video_director.py) | 352 | Bounded, CPU-evidence review for production H3 video takes. | `a5c9f2fa68f8d97b29c836d88087242f26b8da4a6f857a4f0b067b83998e5065` |
| [services/production_voice_binding.py](/home/riki/web_dev/story_builder/services/production_voice_binding.py) | 173 | Project-scoped voice selection and stable speaker binding (no cloning). | `ee9a20052783b7540388f154ba3f829e4d936c366fe883fae892fd777f95e8bc` |
| [services/production_voice_excerpt.py](/home/riki/web_dev/story_builder/services/production_voice_excerpt.py) | 84 | Create an explicit short H3 voice reference from a project voice master. | `b2da6c639aafbe4cfd9a6e5360f067842aee958badde80e4cb0ae449623d75a8` |
| [services/production_world_state.py](/home/riki/web_dev/story_builder/services/production_world_state.py) | 183 | Project-scoped, revisioned character and world canon for production V2. | `2e0512d0ac02b2d3e01e453624db197be642e0694458964de9464eec21b5da2c` |
| [services/project_graph.py](/home/riki/web_dev/story_builder/services/project_graph.py) | 87 | Small, project-local continuity graph. | `31d1acdb4903f89d6f1669e81d1daaec0ad297c6d7dd1370e9a4dd25c3ed2774` |
| [services/project_store.py](/home/riki/web_dev/story_builder/services/project_store.py) | 533 | Project storage and orchestration state for the website planning flow. | `8e4d797c9dfc594adaea522c14dc3e3c0ae8d6fbf3bbb637a5445b3fb3faad46` |
| [services/prompt_styles.py](/home/riki/web_dev/story_builder/services/prompt_styles.py) | 37 | Versioned production-style prompt packs used by automation runs. | `b36367f97747eb399cc082810b2635d9f63ce52ded6e2d34eca71eb7581968a7` |
| [services/provider_exec_guard.py](/home/riki/web_dev/story_builder/services/provider_exec_guard.py) | 37 | Arm Linux parent-death cleanup before replacing this process with a provider CLI. | `906de788ca22278f92b1c653a8a1873edd425e352db61a921453201cfd754ae0` |
| [services/reasoning_provider.py](/home/riki/web_dev/story_builder/services/reasoning_provider.py) | 275 | Provider-neutral JSON reasoning for Story Builder. | `135f4b63d2428898b74969ec9fd73adef4d1f7f54f6cc80d7d788e71c384b22a` |
| [services/story_pipeline.py](/home/riki/web_dev/story_builder/services/story_pipeline.py) | 268 | Prompt builders for the story -> image planning pipeline. | `413dca3db4d291a575fa47e808bce7c9c2dbd21c0e87f205c23db2703adae611` |
| [services/story_revisions.py](/home/riki/web_dev/story_builder/services/story_revisions.py) | 85 | Revision-backed story canvas persistence and screenplay planning. | `217559f8a22149f5a34a9b25ec052e8480dc43cf5936cc15f3ac16200389e3b1` |
| [services/video_audio_sam.py](/home/riki/web_dev/story_builder/services/video_audio_sam.py) | 218 | Story Builder integration for on-demand SAM Audio previews. | `0c134d4707a9965c09af3ce3daf475de0ec2b1846c1ab8d82d773ca98e3191f3` |
| [services/video_audio_search.py](/home/riki/web_dev/story_builder/services/video_audio_search.py) | 109 | Safe Story Builder adapter for the isolated video/audio analyzer corpus. | `4c7a37b8aae564e4a924b887e830d40e61e8a6143b3555c7f06c0016e396da68` |
| [services/video_references.py](/home/riki/web_dev/story_builder/services/video_references.py) | 458 | Curated clip retrieval for Media Composer. | `7e86718635382e451d52eb803b015a6c0cfd675d58ba64a33f8f847e0367b6f6` |
| [services/video_repertoire.py](/home/riki/web_dev/story_builder/services/video_repertoire.py) | 846 | Managed video repertoire assets and subprocess jobs. | `9417d89273e450108c5f11e80790882b6eda71676cb73754b8844f53b5e6339d` |
| [services/video_repertoire_worker.py](/home/riki/web_dev/story_builder/services/video_repertoire_worker.py) | 579 | Subprocess worker for Video Repertoire download and analysis jobs. | `09de78b0018e96213f7f4c7abc8d4cd37865c4e9b95dbb9020f9658233a65d0b` |
| [services/vision_contracts.py](/home/riki/web_dev/story_builder/services/vision_contracts.py) | 64 | Versioned contracts shared by image and video visual intelligence. | `06e38b323944d82c9e6b06f946977758924017fd2855e151945d95af1de46aaf` |
| [services/vision_runs.py](/home/riki/web_dev/story_builder/services/vision_runs.py) | 100 | Persistent, cancellable visual-analysis runs for Story Builder. | `80f648d20408b41f9fdb8742b867cd3015ced2cba8dad3dc08986f3099702b4e` |
| [services/workflow_catalog.py](/home/riki/web_dev/story_builder/services/workflow_catalog.py) | 268 | Workflow discovery and UI-friendly input inference for the media composer. | `592a8950a5cf8248a900cd3fbae0d82d096a56a9637981ccc14f79206725250c` |

## Frontend pages and support

| Source | Lines | Initial destination |
|---|---:|---|
| [frontend/app/src/pages/AgentStatus.tsx](/home/riki/web_dev/story_builder/frontend/app/src/pages/AgentStatus.tsx) | 254 | `app/story_builder/frontend/app/src/pages/AgentStatus.tsx` |
| [frontend/app/src/pages/AudioReconstruct.tsx](/home/riki/web_dev/story_builder/frontend/app/src/pages/AudioReconstruct.tsx) | 34 | `app/story_builder/frontend/app/src/pages/AudioReconstruct.tsx` |
| [frontend/app/src/pages/AudioStudio.tsx](/home/riki/web_dev/story_builder/frontend/app/src/pages/AudioStudio.tsx) | 567 | `app/story_builder/frontend/app/src/pages/AudioStudio.tsx` |
| [frontend/app/src/pages/AudioUtilities.tsx](/home/riki/web_dev/story_builder/frontend/app/src/pages/AudioUtilities.tsx) | 62 | `app/story_builder/frontend/app/src/pages/AudioUtilities.tsx` |
| [frontend/app/src/pages/AutomationStudio.tsx](/home/riki/web_dev/story_builder/frontend/app/src/pages/AutomationStudio.tsx) | 53 | `app/story_builder/frontend/app/src/pages/AutomationStudio.tsx` |
| [frontend/app/src/pages/Generate.tsx](/home/riki/web_dev/story_builder/frontend/app/src/pages/Generate.tsx) | 22 | `app/story_builder/frontend/app/src/pages/Generate.tsx` |
| [frontend/app/src/pages/Home.tsx](/home/riki/web_dev/story_builder/frontend/app/src/pages/Home.tsx) | 107 | `app/story_builder/frontend/app/src/pages/Home.tsx` |
| [frontend/app/src/pages/ImageDetailer.tsx](/home/riki/web_dev/story_builder/frontend/app/src/pages/ImageDetailer.tsx) | 19 | `app/story_builder/frontend/app/src/pages/ImageDetailer.tsx` |
| [frontend/app/src/pages/ManualDirector.tsx](/home/riki/web_dev/story_builder/frontend/app/src/pages/ManualDirector.tsx) | 188 | `app/story_builder/frontend/app/src/pages/ManualDirector.tsx` |
| [frontend/app/src/pages/MediaComposer.tsx](/home/riki/web_dev/story_builder/frontend/app/src/pages/MediaComposer.tsx) | 319 | `app/story_builder/frontend/app/src/pages/MediaComposer.tsx` |
| [frontend/app/src/pages/MusicSound.tsx](/home/riki/web_dev/story_builder/frontend/app/src/pages/MusicSound.tsx) | 30 | `app/story_builder/frontend/app/src/pages/MusicSound.tsx` |
| [frontend/app/src/pages/NotFound.tsx](/home/riki/web_dev/story_builder/frontend/app/src/pages/NotFound.tsx) | 24 | `app/story_builder/frontend/app/src/pages/NotFound.tsx` |
| [frontend/app/src/pages/ProductionWorkspace.tsx](/home/riki/web_dev/story_builder/frontend/app/src/pages/ProductionWorkspace.tsx) | 1346 | `app/story_builder/frontend/app/src/pages/ProductionWorkspace.tsx` |
| [frontend/app/src/pages/StoryBuilder.tsx](/home/riki/web_dev/story_builder/frontend/app/src/pages/StoryBuilder.tsx) | 393 | `app/story_builder/frontend/app/src/pages/StoryBuilder.tsx` |
| [frontend/app/src/pages/StoryCanvas.tsx](/home/riki/web_dev/story_builder/frontend/app/src/pages/StoryCanvas.tsx) | 66 | `app/story_builder/frontend/app/src/pages/StoryCanvas.tsx` |
| [frontend/app/src/pages/StyleLibrary.tsx](/home/riki/web_dev/story_builder/frontend/app/src/pages/StyleLibrary.tsx) | 135 | `app/story_builder/frontend/app/src/pages/StyleLibrary.tsx` |
| [frontend/app/src/pages/VideoRepertoire.tsx](/home/riki/web_dev/story_builder/frontend/app/src/pages/VideoRepertoire.tsx) | 473 | `app/story_builder/frontend/app/src/pages/VideoRepertoire.tsx` |
| [frontend/app/src/App.tsx](/home/riki/web_dev/story_builder/frontend/app/src/App.tsx) | 57 | `app/story_builder/frontend/app/src/App.tsx` |

Reuse the remaining frontend source recursively: components/ui, AppShell, FileUpload, ProductionStylePicker, hooks and lib clients/navigation/status helpers. Keep package-lock.json and build/test config. Do not copy node_modules or dist.

## Existing backend HTTP routes

These routes are the compatibility baseline, not a proposed new public API. Line links point to handlers in the current source.

| Method | Path | Handler / line |
|---|---|---|
| GET | `/api/health` | [health](/home/riki/web_dev/story_builder/api/main.py:2467) |
| GET | `/api/reasoning/provider` | [get_reasoning_provider](/home/riki/web_dev/story_builder/api/main.py:2483) |
| PUT | `/api/reasoning/provider` | [update_reasoning_provider](/home/riki/web_dev/story_builder/api/main.py:2489) |
| POST | `/api/reasoning/provider/test` | [test_reasoning_provider](/home/riki/web_dev/story_builder/api/main.py:2498) |
| POST | `/api/reasoning/provider/test-director` | [test_reasoning_provider_director](/home/riki/web_dev/story_builder/api/main.py:2506) |
| GET | `/api/projects` | [list_projects](/home/riki/web_dev/story_builder/api/main.py:2548) |
| POST | `/api/projects` | [create_project](/home/riki/web_dev/story_builder/api/main.py:2553) |
| GET | `/api/projects/{project_id}` | [fetch_project](/home/riki/web_dev/story_builder/api/main.py:2564) |
| PUT | `/api/projects/{project_id}/draft` | [update_project_draft](/home/riki/web_dev/story_builder/api/main.py:2572) |
| GET | `/api/automation/projects` | [list_automation_projects](/home/riki/web_dev/story_builder/api/main.py:2587) |
| DELETE | `/api/automation/projects` | [delete_automation_projects](/home/riki/web_dev/story_builder/api/main.py:2600) |
| POST | `/api/projects/{project_id}/automation/start` | [start_story_automation](/home/riki/web_dev/story_builder/api/main.py:2620) |
| POST | `/api/projects/{project_id}/automation/input` | [upload_automation_input](/home/riki/web_dev/story_builder/api/main.py:2660) |
| GET | `/api/projects/{project_id}/automation/run` | [get_story_automation](/home/riki/web_dev/story_builder/api/main.py:2692) |
| GET | `/api/projects/{project_id}/graph` | [get_project_graph](/home/riki/web_dev/story_builder/api/main.py:2701) |
| POST | `/api/projects/{project_id}/production/start` | [start_production](/home/riki/web_dev/story_builder/api/main.py:2735) |
| GET | `/api/projects/{project_id}/production/run` | [get_production_run](/home/riki/web_dev/story_builder/api/main.py:2752) |
| POST | `/api/projects/{project_id}/automation/{action}` | [action_story_automation](/home/riki/web_dev/story_builder/api/main.py:2761) |
| GET | `/api/projects/{project_id}/status` | [project_status](/home/riki/web_dev/story_builder/api/main.py:2785) |
| POST | `/api/projects/{project_id}/artifacts/{artifact_type}/generate` | [generate_artifact](/home/riki/web_dev/story_builder/api/main.py:2793) |
| POST | `/api/projects/{project_id}/artifacts/{artifact_type}/save` | [save_artifact](/home/riki/web_dev/story_builder/api/main.py:2825) |
| POST | `/api/story/assist` | [story_assist](/home/riki/web_dev/story_builder/api/main.py:2837) |
| GET | `/api/workflows` | [workflows](/home/riki/web_dev/story_builder/api/main.py:2863) |
| GET | `/api/production/v2/workflows` | [production_v2_workflows](/home/riki/web_dev/story_builder/api/main.py:2868) |
| GET | `/api/production/v2/image-workflows` | [production_v2_image_workflows](/home/riki/web_dev/story_builder/api/main.py:2874) |
| POST | `/api/projects/{project_id}/production/v2/runs/{run_id}/image-jobs` | [queue_production_image_job](/home/riki/web_dev/story_builder/api/main.py:2880) |
| GET | `/api/projects/{project_id}/production/v2/image-jobs/{batch_id}` | [get_production_image_job_batch](/home/riki/web_dev/story_builder/api/main.py:3025) |
| POST | `/api/projects/{project_id}/production/v2/runs/{run_id}/image-candidates/{asset_id}/accept` | [accept_production_image_candidate_route](/home/riki/web_dev/story_builder/api/main.py:3034) |
| GET | `/api/production/v2/h3-prompt-rules` | [production_v2_h3_prompt_rules](/home/riki/web_dev/story_builder/api/main.py:3063) |
| POST | `/api/projects/{project_id}/production/v2/runs` | [create_production_v2_run](/home/riki/web_dev/story_builder/api/main.py:3074) |
| GET | `/api/projects/{project_id}/production/v2/runs` | [list_production_v2_runs](/home/riki/web_dev/story_builder/api/main.py:3162) |
| GET | `/api/production/v2/director-profiles` | [production_v2_director_profiles](/home/riki/web_dev/story_builder/api/main.py:3174) |
| GET | `/api/production/v2/styles` | [production_v2_styles](/home/riki/web_dev/story_builder/api/main.py:3182) |
| GET | `/api/production/v2/style-sources` | [list_production_v2_style_sources](/home/riki/web_dev/story_builder/api/main.py:3191) |
| POST | `/api/production/v2/style-sources` | [upload_production_v2_style_source](/home/riki/web_dev/story_builder/api/main.py:3197) |
| GET | `/api/production/v2/styles/variants` | [list_production_v2_style_variants](/home/riki/web_dev/story_builder/api/main.py:3212) |
| GET | `/api/production/v2/styles/drafts` | [list_production_v2_style_drafts](/home/riki/web_dev/story_builder/api/main.py:3221) |
| GET | `/api/production/v2/styles/{variant_id}/versions` | [list_production_v2_style_versions](/home/riki/web_dev/story_builder/api/main.py:3229) |
| POST | `/api/production/v2/styles/analyze` | [analyze_production_v2_style_sources](/home/riki/web_dev/story_builder/api/main.py:3241) |
| POST | `/api/production/v2/styles/drafts` | [create_production_v2_style_draft](/home/riki/web_dev/story_builder/api/main.py:3255) |
| PUT | `/api/production/v2/styles/drafts/{variant_id}` | [update_production_v2_style_draft](/home/riki/web_dev/story_builder/api/main.py:3264) |
| POST | `/api/production/v2/styles/drafts/{variant_id}/publish` | [publish_production_v2_style_draft](/home/riki/web_dev/story_builder/api/main.py:3278) |
| POST | `/api/production/v2/styles/{variant_id}/fork` | [fork_production_v2_style_variant](/home/riki/web_dev/story_builder/api/main.py:3289) |
| POST | `/api/production/v2/styles/{variant_id}/archive` | [archive_production_v2_style_variant](/home/riki/web_dev/story_builder/api/main.py:3299) |
| GET | `/api/projects/{project_id}/production/v2/assets` | [list_project_production_assets](/home/riki/web_dev/story_builder/api/main.py:3308) |
| GET | `/api/projects/{project_id}/production/v2/canon` | [get_project_production_canon](/home/riki/web_dev/story_builder/api/main.py:3322) |
| PUT | `/api/projects/{project_id}/production/v2/canon` | [put_project_production_canon](/home/riki/web_dev/story_builder/api/main.py:3333) |
| POST | `/api/projects/{project_id}/production/v2/canon/characters` | [create_project_character_identity](/home/riki/web_dev/story_builder/api/main.py:3349) |
| POST | `/api/projects/{project_id}/production/v2/canon/worlds` | [create_project_world_identity](/home/riki/web_dev/story_builder/api/main.py:3370) |
| GET | `/api/projects/{project_id}/production/v2/runs/{run_id}/voice-bindings` | [get_production_voice_bindings](/home/riki/web_dev/story_builder/api/main.py:3386) |
| POST | `/api/projects/{project_id}/production/v2/runs/{run_id}/voices/bind` | [create_production_voice_binding](/home/riki/web_dev/story_builder/api/main.py:3395) |
| POST | `/api/projects/{project_id}/production/v2/runs/{run_id}/voices/{character_id}/excerpt` | [create_production_h3_voice_excerpt](/home/riki/web_dev/story_builder/api/main.py:3434) |
| POST | `/api/projects/{project_id}/production/v2/assets` | [upload_project_production_asset](/home/riki/web_dev/story_builder/api/main.py:3467) |
| POST | `/api/projects/{project_id}/production/v2/runs/{run_id}/dialogue-takes` | [upload_production_dialogue_take](/home/riki/web_dev/story_builder/api/main.py:3488) |
| POST | `/api/projects/{project_id}/production/v2/runs/{run_id}/dialogue-takes/{asset_id}/convert` | [convert_production_dialogue_take](/home/riki/web_dev/story_builder/api/main.py:3530) |
| POST | `/api/projects/{project_id}/production/v2/runs/{run_id}/audio-sidecars` | [create_production_audio_sidecar](/home/riki/web_dev/story_builder/api/main.py:3576) |
| POST | `/api/projects/{project_id}/production/v2/runs/{run_id}/dialogue-tts` | [create_production_dialogue_tts](/home/riki/web_dev/story_builder/api/main.py:3604) |
| GET | `/api/projects/{project_id}/production/v2/runs/{run_id}/audio-sidecars/{job_id}` | [get_production_audio_sidecar](/home/riki/web_dev/story_builder/api/main.py:3665) |
| POST | `/api/projects/{project_id}/production/v2/assets/{asset_id}/master-identity` | [assign_production_master_identity](/home/riki/web_dev/story_builder/api/main.py:3680) |
| POST | `/api/projects/{project_id}/production/v2/assets/links` | [link_project_repertoire_asset](/home/riki/web_dev/story_builder/api/main.py:3695) |
| GET | `/api/projects/{project_id}/production/v2/assets/{asset_id}/content` | [project_production_asset_content](/home/riki/web_dev/story_builder/api/main.py:3710) |
| GET | `/api/projects/{project_id}/production/v2/runs/{run_id}` | [get_production_v2_run](/home/riki/web_dev/story_builder/api/main.py:3724) |
| POST | `/api/projects/{project_id}/production/v2/runs/{run_id}/story/detail` | [detail_production_v2_story](/home/riki/web_dev/story_builder/api/main.py:3769) |
| POST | `/api/projects/{project_id}/production/v2/runs/{run_id}/story/manual-source` | [create_manual_production_v2_story_source](/home/riki/web_dev/story_builder/api/main.py:3878) |
| POST | `/api/projects/{project_id}/production/v2/runs/{run_id}/story/tasks` | [enqueue_production_v2_story_task](/home/riki/web_dev/story_builder/api/main.py:4006) |
| GET | `/api/projects/{project_id}/production/v2/runs/{run_id}/story/tasks/{task_id}` | [get_production_v2_story_task](/home/riki/web_dev/story_builder/api/main.py:4032) |
| POST | `/api/projects/{project_id}/production/v2/runs/{run_id}/text/{stage}/tasks` | [enqueue_production_v2_text_task](/home/riki/web_dev/story_builder/api/main.py:4053) |
| GET | `/api/projects/{project_id}/production/v2/runs/{run_id}/text/{stage}/tasks/{task_id}` | [get_production_v2_text_task](/home/riki/web_dev/story_builder/api/main.py:4076) |
| POST | `/api/projects/{project_id}/production/v2/runs/{run_id}/stage-tasks/{task_id}/resolve` | [resolve_production_v2_stage_task](/home/riki/web_dev/story_builder/api/main.py:4099) |
| GET | `/api/projects/{project_id}/production/v2/runs/{run_id}/story/revisions` | [list_production_v2_story_revisions](/home/riki/web_dev/story_builder/api/main.py:4123) |
| POST | `/api/projects/{project_id}/production/v2/runs/{run_id}/story/revisions/{revision_id}/manual` | [save_manual_production_v2_story_revision](/home/riki/web_dev/story_builder/api/main.py:4133) |
| GET | `/api/projects/{project_id}/production/v2/runs/{run_id}/text/{stage}/revisions` | [list_production_v2_text_revisions](/home/riki/web_dev/story_builder/api/main.py:4183) |
| POST | `/api/projects/{project_id}/production/v2/runs/{run_id}/story/revisions/{revision_id}/accept` | [accept_production_v2_story_revision](/home/riki/web_dev/story_builder/api/main.py:4195) |
| POST | `/api/projects/{project_id}/production/v2/runs/{run_id}/text/{stage}` | [generate_production_v2_text_stage](/home/riki/web_dev/story_builder/api/main.py:4230) |
| POST | `/api/projects/{project_id}/production/v2/runs/{run_id}/shots/{shot_id}/validate` | [validate_production_v2_shot](/home/riki/web_dev/story_builder/api/main.py:4520) |
| POST | `/api/projects/{project_id}/production/v2/runs/{run_id}/shots/{shot_id}/prompt-preparations` | [enqueue_production_v2_shot_prompt_preparation](/home/riki/web_dev/story_builder/api/main.py:4674) |
| GET | `/api/projects/{project_id}/production/v2/runs/{run_id}/shots/{shot_id}/prompt-preparations/{task_id}` | [get_production_v2_shot_prompt_preparation](/home/riki/web_dev/story_builder/api/main.py:4748) |
| POST | `/api/projects/{project_id}/production/v2/runs/{run_id}/shots/{shot_id}/takes` | [queue_production_v2_take](/home/riki/web_dev/story_builder/api/main.py:4917) |
| POST | `/api/projects/{project_id}/production/v2/runs/{run_id}/takes/{take_id}/accept` | [accept_production_v2_take](/home/riki/web_dev/story_builder/api/main.py:4924) |
| POST | `/api/projects/{project_id}/production/v2/runs/{run_id}/takes/{take_id}/cancel` | [cancel_production_v2_take](/home/riki/web_dev/story_builder/api/main.py:4947) |
| POST | `/api/projects/{project_id}/production/v2/runs/{run_id}/takes/{take_id}/retry` | [retry_production_v2_take](/home/riki/web_dev/story_builder/api/main.py:5023) |
| POST | `/api/projects/{project_id}/production/v2/runs/{run_id}/takes/{take_id}/reconcile-absent` | [reconcile_absent_production_v2_take](/home/riki/web_dev/story_builder/api/main.py:5045) |
| POST | `/api/projects/{project_id}/production/v2/runs/{run_id}/text/{stage}/manual` | [save_production_v2_manual_text](/home/riki/web_dev/story_builder/api/main.py:5104) |
| POST | `/api/projects/{project_id}/production/v2/runs/{run_id}/text/{stage}/revisions/{revision_id}/accept` | [accept_production_v2_text_revision](/home/riki/web_dev/story_builder/api/main.py:5174) |
| GET | `/api/projects/{project_id}/production/v2/runs/{run_id}/shots/{shot_id}` | [get_production_v2_shot](/home/riki/web_dev/story_builder/api/main.py:5245) |
| PUT | `/api/projects/{project_id}/production/v2/runs/{run_id}/shots/{shot_id}` | [put_production_v2_shot](/home/riki/web_dev/story_builder/api/main.py:5258) |
| GET | `/api/projects/{project_id}/production/v2/runs/{run_id}/shots/{shot_id}/draft` | [get_production_v2_shot_draft](/home/riki/web_dev/story_builder/api/main.py:5288) |
| PUT | `/api/projects/{project_id}/production/v2/runs/{run_id}/shots/{shot_id}/draft` | [save_production_v2_shot_draft](/home/riki/web_dev/story_builder/api/main.py:5310) |
| POST | `/api/projects/{project_id}/production/v2/runs/{run_id}/refine` | [propose_production_v2_refine](/home/riki/web_dev/story_builder/api/main.py:5332) |
| POST | `/api/projects/{project_id}/production/v2/runs/{run_id}/refine/{proposal_id}/accept` | [accept_production_v2_refine](/home/riki/web_dev/story_builder/api/main.py:5379) |
| GET | `/api/automation/styles` | [automation_styles](/home/riki/web_dev/story_builder/api/main.py:5434) |
| GET | `/api/automation/styles/{style_id}` | [automation_style](/home/riki/web_dev/story_builder/api/main.py:5439) |
| GET | `/api/audio/capabilities` | [audio_capabilities](/home/riki/web_dev/story_builder/api/main.py:5447) |
| GET | `/api/audio/voices` | [audio_voices](/home/riki/web_dev/story_builder/api/main.py:5461) |
| GET | `/api/audio/models` | [audio_models](/home/riki/web_dev/story_builder/api/main.py:5466) |
| GET | `/api/music/capabilities` | [get_music_capabilities](/home/riki/web_dev/story_builder/api/main.py:5471) |
| GET | `/api/music/ace/finetune/preflight` | [get_ace_finetune_preflight](/home/riki/web_dev/story_builder/api/main.py:5476) |
| GET | `/api/music/control-foley/capabilities` | [get_control_foley_capabilities](/home/riki/web_dev/story_builder/api/main.py:5481) |
| GET | `/api/music/control-foley/schema` | [get_control_foley_schema](/home/riki/web_dev/story_builder/api/main.py:5486) |
| POST | `/api/projects/{project_id}/music/ace/jobs` | [create_ace_music_job](/home/riki/web_dev/story_builder/api/main.py:5511) |
| GET | `/api/projects/{project_id}/music/jobs` | [list_music_jobs](/home/riki/web_dev/story_builder/api/main.py:5519) |
| GET | `/api/projects/{project_id}/music/jobs/{job_id}` | [get_music_job](/home/riki/web_dev/story_builder/api/main.py:5524) |
| POST | `/api/projects/{project_id}/music/control-foley/jobs` | [create_control_foley_job](/home/riki/web_dev/story_builder/api/main.py:5531) |
| GET | `/api/projects/{project_id}/music/control-foley/jobs` | [list_control_foley_jobs](/home/riki/web_dev/story_builder/api/main.py:5546) |
| GET | `/api/projects/{project_id}/music/control-foley/jobs/{job_id}` | [get_control_foley_job](/home/riki/web_dev/story_builder/api/main.py:5551) |
| GET | `/api/audio-library/assets` | [get_audio_library_assets](/home/riki/web_dev/story_builder/api/main.py:5558) |
| POST | `/api/audio-library/assets` | [create_audio_library_asset](/home/riki/web_dev/story_builder/api/main.py:5563) |
| PATCH | `/api/audio-library/assets/{asset_id}` | [patch_audio_library_asset](/home/riki/web_dev/story_builder/api/main.py:5569) |
| DELETE | `/api/audio-library/assets/{asset_id}` | [delete_audio_library_asset](/home/riki/web_dev/story_builder/api/main.py:5575) |
| GET | `/api/audio-library/files/{asset_id}` | [get_audio_library_file](/home/riki/web_dev/story_builder/api/main.py:5581) |
| GET | `/api/audio/utilities/capabilities` | [get_audio_utility_capabilities](/home/riki/web_dev/story_builder/api/main.py:5590) |
| POST | `/api/projects/{project_id}/audio/utilities/{operation}/jobs` | [create_audio_utility_job](/home/riki/web_dev/story_builder/api/main.py:5599) |
| GET | `/api/projects/{project_id}/audio/utilities/jobs` | [list_audio_utility_jobs](/home/riki/web_dev/story_builder/api/main.py:5612) |
| GET | `/api/projects/{project_id}/audio/utilities/jobs/{job_id}` | [get_audio_utility_job](/home/riki/web_dev/story_builder/api/main.py:5617) |
| POST | `/api/audio/voices` | [add_audio_voice](/home/riki/web_dev/story_builder/api/main.py:5624) |
| POST | `/api/audio/voices/refresh` | [refresh_audio_voices](/home/riki/web_dev/story_builder/api/main.py:5653) |
| GET | `/api/audio/finetune/f5/preflight` | [get_f5_preflight](/home/riki/web_dev/story_builder/api/main.py:5661) |
| GET | `/api/audio/effects/capabilities` | [get_audio_effect_capabilities](/home/riki/web_dev/story_builder/api/main.py:5666) |
| GET | `/api/audio/rvc/models` | [get_audio_rvc_models](/home/riki/web_dev/story_builder/api/main.py:5671) |
| GET | `/api/projects/{project_id}/audio/character-map` | [get_character_map](/home/riki/web_dev/story_builder/api/main.py:5676) |
| PUT | `/api/projects/{project_id}/audio/character-map` | [put_character_map](/home/riki/web_dev/story_builder/api/main.py:5685) |
| POST | `/api/projects/{project_id}/audio/tts/timed` | [create_timed_tts_job](/home/riki/web_dev/story_builder/api/main.py:5997) |
| GET | `/api/projects/{project_id}/audio/tts/jobs` | [list_timed_tts_jobs](/home/riki/web_dev/story_builder/api/main.py:6021) |
| GET | `/api/projects/{project_id}/audio/tts/jobs/{job_id}` | [get_timed_tts_job](/home/riki/web_dev/story_builder/api/main.py:6027) |
| POST | `/api/projects/{project_id}/audio/finetune/f5/prepare` | [create_f5_prepare_job](/home/riki/web_dev/story_builder/api/main.py:6036) |
| GET | `/api/projects/{project_id}/audio/finetune/f5/jobs` | [list_f5_prepare_jobs](/home/riki/web_dev/story_builder/api/main.py:6064) |
| GET | `/api/projects/{project_id}/audio/finetune/f5/jobs/{job_id}` | [get_f5_prepare_job](/home/riki/web_dev/story_builder/api/main.py:6070) |
| POST | `/api/projects/{project_id}/audio/effects/{operation}` | [create_audio_effect_job](/home/riki/web_dev/story_builder/api/main.py:6079) |
| GET | `/api/projects/{project_id}/audio/effects/jobs` | [list_audio_effect_jobs](/home/riki/web_dev/story_builder/api/main.py:6102) |
| GET | `/api/projects/{project_id}/audio/effects/jobs/{job_id}` | [get_audio_effect_job](/home/riki/web_dev/story_builder/api/main.py:6107) |
| POST | `/api/projects/{project_id}/audio/scenes/split` | [create_scene_split](/home/riki/web_dev/story_builder/api/main.py:6114) |
| POST | `/api/projects/{project_id}/audio/scenes/{split_job_id}/stitch` | [create_scene_stitch](/home/riki/web_dev/story_builder/api/main.py:6135) |
| GET | `/api/projects/{project_id}/audio/scenes/jobs` | [list_scene_jobs](/home/riki/web_dev/story_builder/api/main.py:6164) |
| GET | `/api/projects/{project_id}/audio/scenes/jobs/{job_id}` | [get_scene_job](/home/riki/web_dev/story_builder/api/main.py:6169) |
| GET | `/api/automation/blocks` | [get_automation_blocks](/home/riki/web_dev/story_builder/api/main.py:6176) |
| GET | `/api/automation/blocks/{operation_id}/schema` | [get_automation_block_schema](/home/riki/web_dev/story_builder/api/main.py:6181) |
| GET | `/api/projects/{project_id}/automation/pipelines` | [list_audio_pipelines](/home/riki/web_dev/story_builder/api/main.py:6212) |
| POST | `/api/projects/{project_id}/automation/pipelines` | [create_audio_pipeline](/home/riki/web_dev/story_builder/api/main.py:6217) |
| PUT | `/api/projects/{project_id}/automation/pipelines/{pipeline_id}` | [update_audio_pipeline](/home/riki/web_dev/story_builder/api/main.py:6222) |
| POST | `/api/projects/{project_id}/automation/pipelines/{pipeline_id}/validate` | [validate_saved_audio_pipeline](/home/riki/web_dev/story_builder/api/main.py:6231) |
| POST | `/api/projects/{project_id}/automation/pipelines/{pipeline_id}/runs` | [start_audio_pipeline_run](/home/riki/web_dev/story_builder/api/main.py:6238) |
| GET | `/api/projects/{project_id}/automation/runs` | [list_audio_pipeline_runs](/home/riki/web_dev/story_builder/api/main.py:6247) |
| GET | `/api/projects/{project_id}/automation/runs/{run_id}` | [get_audio_pipeline_run](/home/riki/web_dev/story_builder/api/main.py:6252) |
| POST | `/api/projects/{project_id}/automation/runs/{run_id}/steps/{step_id}/retry` | [retry_audio_pipeline_step](/home/riki/web_dev/story_builder/api/main.py:6259) |
| GET | `/api/workflows/{workflow_id:path}` | [workflow_detail](/home/riki/web_dev/story_builder/api/main.py:6270) |
| GET | `/api/video-repertoire/capabilities` | [video_repertoire_capabilities](/home/riki/web_dev/story_builder/api/main.py:6280) |
| POST | `/api/video-references/index` | [index_video_references](/home/riki/web_dev/story_builder/api/main.py:6285) |
| GET | `/api/video-references/index/status` | [video_reference_index_status](/home/riki/web_dev/story_builder/api/main.py:6290) |
| POST | `/api/video-references/search` | [search_video_references](/home/riki/web_dev/story_builder/api/main.py:6296) |
| GET | `/api/video-references/search/{search_id}/next` | [next_video_reference_page](/home/riki/web_dev/story_builder/api/main.py:6306) |
| POST | `/api/video-references/search/{search_id}/refine` | [refine_video_reference_search](/home/riki/web_dev/story_builder/api/main.py:6314) |
| GET | `/api/video-references/seo-styles` | [list_video_reference_styles](/home/riki/web_dev/story_builder/api/main.py:6322) |
| POST | `/api/video-references/seo-styles` | [create_video_reference_style](/home/riki/web_dev/story_builder/api/main.py:6327) |
| DELETE | `/api/video-references/seo-styles/{style_id}` | [delete_video_reference_style](/home/riki/web_dev/story_builder/api/main.py:6335) |
| GET | `/api/video-references/clips/{clip_id}` | [get_video_reference_clip](/home/riki/web_dev/story_builder/api/main.py:6342) |
| GET | `/api/video-references/clips/{clip_id}/content` | [video_reference_clip_content](/home/riki/web_dev/story_builder/api/main.py:6350) |
| GET | `/api/video-references/clips/{clip_id}/thumbnail` | [video_reference_clip_thumbnail](/home/riki/web_dev/story_builder/api/main.py:6361) |
| POST | `/api/video-references/automation/select` | [automate_video_reference_selection](/home/riki/web_dev/story_builder/api/main.py:6372) |
| POST | `/api/projects/{project_id}/video-references/select` | [select_video_references](/home/riki/web_dev/story_builder/api/main.py:6390) |
| POST | `/api/vision/images/analyze` | [analyze_image_detailer](/home/riki/web_dev/story_builder/api/main.py:6409) |
| POST | `/api/projects/{project_id}/vision/runs` | [create_project_vision_run](/home/riki/web_dev/story_builder/api/main.py:6445) |
| GET | `/api/vision/runs/{run_id}` | [get_vision_run](/home/riki/web_dev/story_builder/api/main.py:6461) |
| GET | `/api/vision/runs/{run_id}/events` | [get_vision_run_events](/home/riki/web_dev/story_builder/api/main.py:6469) |
| POST | `/api/vision/runs/{run_id}/cancel` | [cancel_vision_run](/home/riki/web_dev/story_builder/api/main.py:6478) |
| GET | `/api/vision/runs/{run_id}/artifacts/{artifact_path:path}` | [get_vision_run_artifact](/home/riki/web_dev/story_builder/api/main.py:6486) |
| GET | `/api/vision/runs/{run_id}/generation-brief` | [get_vision_generation_brief](/home/riki/web_dev/story_builder/api/main.py:6494) |
| POST | `/api/projects/{project_id}/canvas/revisions` | [create_canvas_revision](/home/riki/web_dev/story_builder/api/main.py:6503) |
| GET | `/api/projects/{project_id}/canvas/revisions` | [list_canvas_revisions](/home/riki/web_dev/story_builder/api/main.py:6515) |
| POST | `/api/projects/{project_id}/canvas/analysis` | [create_canvas_analysis](/home/riki/web_dev/story_builder/api/main.py:6524) |
| POST | `/api/projects/{project_id}/canvas/outline` | [create_canvas_outline](/home/riki/web_dev/story_builder/api/main.py:6543) |
| GET | `/api/projects/{project_id}/audio/reconstruct` | [get_reconstruction_session](/home/riki/web_dev/story_builder/api/main.py:6556) |
| POST | `/api/projects/{project_id}/audio/reconstruct/calibration` | [save_reconstruction_calibration](/home/riki/web_dev/story_builder/api/main.py:6565) |
| POST | `/api/projects/{project_id}/audio/reconstruct/parts` | [create_reconstruction_part](/home/riki/web_dev/story_builder/api/main.py:6576) |
| POST | `/api/projects/{project_id}/audio/reconstruct/parts/{part_id}/takes` | [upload_reconstruction_take](/home/riki/web_dev/story_builder/api/main.py:6587) |
| POST | `/api/projects/{project_id}/audio/reconstruct/parts/{part_id}/accept/{take_id}` | [accept_reconstruction_take](/home/riki/web_dev/story_builder/api/main.py:6598) |
| POST | `/api/video-repertoire/youtube/resolve` | [resolve_video_sources](/home/riki/web_dev/story_builder/api/main.py:6609) |
| POST | `/api/video-repertoire/youtube/jobs` | [create_video_download_job](/home/riki/web_dev/story_builder/api/main.py:6617) |
| GET | `/api/video-repertoire/youtube/jobs` | [list_video_download_jobs](/home/riki/web_dev/story_builder/api/main.py:6626) |
| GET | `/api/video-repertoire/youtube/jobs/{job_id}` | [get_video_download_job](/home/riki/web_dev/story_builder/api/main.py:6631) |
| POST | `/api/video-repertoire/youtube/jobs/{job_id}/cancel` | [cancel_video_download_job](/home/riki/web_dev/story_builder/api/main.py:6639) |
| POST | `/api/video-repertoire/youtube/jobs/{job_id}/retry` | [retry_video_download_job](/home/riki/web_dev/story_builder/api/main.py:6649) |
| GET | `/api/video-repertoire/assets` | [list_video_assets](/home/riki/web_dev/story_builder/api/main.py:6659) |
| POST | `/api/video-repertoire/assets/import-legacy` | [import_legacy_video_assets](/home/riki/web_dev/story_builder/api/main.py:6664) |
| POST | `/api/video-repertoire/assets/upload` | [upload_video_asset](/home/riki/web_dev/story_builder/api/main.py:6669) |
| DELETE | `/api/video-repertoire/assets` | [delete_video_assets](/home/riki/web_dev/story_builder/api/main.py:6677) |
| GET | `/api/video-repertoire/assets/{asset_id}` | [get_video_asset](/home/riki/web_dev/story_builder/api/main.py:6685) |
| GET | `/api/video-repertoire/assets/{asset_id}/content` | [video_asset_content](/home/riki/web_dev/story_builder/api/main.py:6693) |
| POST | `/api/video-repertoire/analysis/jobs` | [create_video_analysis_job](/home/riki/web_dev/story_builder/api/main.py:6705) |
| GET | `/api/video-repertoire/analysis/jobs` | [list_video_analysis_jobs](/home/riki/web_dev/story_builder/api/main.py:6718) |
| GET | `/api/video-repertoire/analysis/jobs/{job_id}` | [get_video_analysis_job](/home/riki/web_dev/story_builder/api/main.py:6723) |
| POST | `/api/video-repertoire/analysis/jobs/{job_id}/cancel` | [cancel_video_analysis_job](/home/riki/web_dev/story_builder/api/main.py:6731) |
| POST | `/api/video-repertoire/analysis/jobs/{job_id}/stop` | [stop_video_analysis_job](/home/riki/web_dev/story_builder/api/main.py:6743) |
| DELETE | `/api/video-repertoire/analysis/jobs/{job_id}` | [delete_video_analysis_job](/home/riki/web_dev/story_builder/api/main.py:6753) |
| POST | `/api/video-repertoire/analysis/jobs/{job_id}/retry` | [retry_video_analysis_job](/home/riki/web_dev/story_builder/api/main.py:6763) |
| GET | `/api/video-repertoire/search` | [search_video_repertoire](/home/riki/web_dev/story_builder/api/main.py:6773) |
| POST | `/api/video-repertoire/assets/{asset_id}/vision` | [analyze_video_repertoire_asset_vision](/home/riki/web_dev/story_builder/api/main.py:6778) |
| GET | `/api/vision/references/search` | [search_vision_references](/home/riki/web_dev/story_builder/api/main.py:6796) |
| POST | `/api/vision/references/{reference_id}/promote` | [promote_vision_reference](/home/riki/web_dev/story_builder/api/main.py:6803) |
| GET | `/api/video-repertoire/artifacts/{relative_path:path}` | [video_repertoire_artifact](/home/riki/web_dev/story_builder/api/main.py:6814) |
| GET | `/api/video-repertoire/audio-assets` | [list_video_repertoire_audio_assets](/home/riki/web_dev/story_builder/api/main.py:6825) |
| DELETE | `/api/video-repertoire/audio-assets` | [delete_video_repertoire_audio_assets](/home/riki/web_dev/story_builder/api/main.py:6833) |
| GET | `/api/video-repertoire/manual/workflows` | [manual_director_workflows](/home/riki/web_dev/story_builder/api/main.py:6842) |
| GET | `/api/video-repertoire/manual/assets` | [list_manual_director_assets](/home/riki/web_dev/story_builder/api/main.py:6848) |
| POST | `/api/video-repertoire/manual/assets` | [upload_manual_director_asset](/home/riki/web_dev/story_builder/api/main.py:6853) |
| GET | `/api/video-repertoire/manual/assets/content/{relative_path:path}` | [manual_director_asset_content](/home/riki/web_dev/story_builder/api/main.py:6864) |
| POST | `/api/video-repertoire/manual/jobs` | [create_manual_director_job](/home/riki/web_dev/story_builder/api/main.py:6872) |
| GET | `/api/video-repertoire/manual/jobs` | [list_manual_director_jobs](/home/riki/web_dev/story_builder/api/main.py:6884) |
| GET | `/api/video-repertoire/manual/jobs/{run_id}` | [get_manual_director_job](/home/riki/web_dev/story_builder/api/main.py:6889) |
| DELETE | `/api/video-repertoire/manual/jobs/{run_id}` | [delete_manual_director_job](/home/riki/web_dev/story_builder/api/main.py:6897) |
| GET | `/api/video-repertoire/manual/files/{run_id}/{filename}` | [manual_director_output](/home/riki/web_dev/story_builder/api/main.py:6907) |
| GET | `/api/video-repertoire/audio-assets/content/{relative_path:path}` | [video_repertoire_audio_asset_content](/home/riki/web_dev/story_builder/api/main.py:6916) |
| GET | `/api/video-audio-analyzer/runs/{run_id}/artifacts/{artifact_path:path}` | [video_audio_analyzer_artifact](/home/riki/web_dev/story_builder/api/main.py:6940) |
| POST | `/api/video-audio-analyzer/search` | [search_video_audio_analyzer](/home/riki/web_dev/story_builder/api/main.py:6962) |
| POST | `/api/video-audio-analyzer/runs/{run_id}/sam/isolate` | [isolate_video_audio_event](/home/riki/web_dev/story_builder/api/main.py:6975) |
| GET | `/api/video-audio-analyzer/sam/previews/{temporary_id}/audio` | [video_audio_sam_preview_audio](/home/riki/web_dev/story_builder/api/main.py:6992) |
| POST | `/api/video-audio-analyzer/sam/previews/{temporary_id}/director-review` | [video_audio_sam_director_review](/home/riki/web_dev/story_builder/api/main.py:7002) |
| DELETE | `/api/video-audio-analyzer/sam/previews/{temporary_id}` | [discard_video_audio_sam_preview](/home/riki/web_dev/story_builder/api/main.py:7013) |
| POST | `/api/media/upload` | [upload_media_asset](/home/riki/web_dev/story_builder/api/main.py:7022) |
| POST | `/api/projects/{project_id}/media/jobs` | [create_media_job](/home/riki/web_dev/story_builder/api/main.py:7032) |
| GET | `/api/projects/{project_id}/files/{relative_path:path}` | [project_file](/home/riki/web_dev/story_builder/api/main.py:7099) |
| GET | `/api/projects/{project_id}/media/jobs` | [list_media_jobs](/home/riki/web_dev/story_builder/api/main.py:7107) |
| POST | `/api/projects/{project_id}/output/finalize` | [finalize_project_output](/home/riki/web_dev/story_builder/api/main.py:7132) |
| POST | `/api/projects/{project_id}/output/compose` | [compose_project_output](/home/riki/web_dev/story_builder/api/main.py:7137) |
| GET | `/api/projects/{project_id}/output/manifest` | [get_project_output_manifest](/home/riki/web_dev/story_builder/api/main.py:7159) |

## Workflow JSON files

Initial destination: `app/story_builder/<same source-relative path>`. “API” denotes node-format JSON, not verified executor/readiness. Zero-node configs/presets are explicitly identified.

| Source | Format | Top-level nodes | Additional stored subgraph nodes | SHA-256 |
|---|---|---:|---:|---|
| [workflows/3d_stuff/blender_tools_config.example.json](/home/riki/web_dev/story_builder/workflows/3d_stuff/blender_tools_config.example.json) | Tools config | 0 | 0 | `1e05bb785d6f84d93c7d40b7b6807827d38857c081383104d90ae8fdb57a7d06` |
| [workflows/3d_stuff/blender_wrapper_TextToStatic3D.json](/home/riki/web_dev/story_builder/workflows/3d_stuff/blender_wrapper_TextToStatic3D.json) | UI | 79 | 0 | `95bd8c8bcea055728dbe82efa50c56e0cbaac4577229ca6f16eed1f932cde8c3` |
| [workflows/3d_stuff/pixal3d_example_workflow.json](/home/riki/web_dev/story_builder/workflows/3d_stuff/pixal3d_example_workflow.json) | UI | 9 | 0 | `aadb96c3a48b8e145e2bdc21c17292b9ba598b5bfea52b0415a674a62169e461` |
| [workflows/3d_stuff/pixal3d_low_vram_cam_control_example_workflow.json](/home/riki/web_dev/story_builder/workflows/3d_stuff/pixal3d_low_vram_cam_control_example_workflow.json) | UI | 10 | 0 | `095b73462a24cdd7198227276814b23603f947c4b61fc00533b3c8cfb3b24466` |
| [workflows/3d_stuff/ultrashape_workflow-low-vram.json](/home/riki/web_dev/story_builder/workflows/3d_stuff/ultrashape_workflow-low-vram.json) | UI | 7 | 0 | `eb25a095a01b673d5596fee4746be1e657a38d9e7ece320593f08a554ac3bafb` |
| [workflows/api/audio/ace_step_music_api.json](/home/riki/web_dev/story_builder/workflows/api/audio/ace_step_music_api.json) | API | 10 | 0 | `1baed6a3a4634cc0b549af876d5930cabf69d3c34ed9fe20302f609a77b85899` |
| [workflows/api/audio/control_foley/reference_video_audio_api.json](/home/riki/web_dev/story_builder/workflows/api/audio/control_foley/reference_video_audio_api.json) | API | 4 | 0 | `a368bc1e62903dd93c7419a447759084bdb6d71f50c743d27bf0d21ea91607d1` |
| [workflows/api/audio/control_foley/text_audio_api.json](/home/riki/web_dev/story_builder/workflows/api/audio/control_foley/text_audio_api.json) | API | 3 | 0 | `7b5d2ae1a70f3f63f070d11badf6f86894331062ce3268ec99491b63b192a820` |
| [workflows/api/audio/control_foley/text_video_audio_api.json](/home/riki/web_dev/story_builder/workflows/api/audio/control_foley/text_video_audio_api.json) | API | 4 | 0 | `bd5cda022ca30a1604edd137cebc2cdb413ea4744ba20295509ce4210b014e91` |
| [workflows/api/audio/emotion_edit_api.json](/home/riki/web_dev/story_builder/workflows/api/audio/emotion_edit_api.json) | API | 5 | 0 | `1da1500f4997839521c9c02cc9f8f680d67685dc743257dae56653106313d6af` |
| [workflows/api/audio/noise_cleanup_api.json](/home/riki/web_dev/story_builder/workflows/api/audio/noise_cleanup_api.json) | API | 4 | 0 | `f39af3406833393c83194ea00f6ffa02a869b2806a9adc9b44b3741854b11a01` |
| [workflows/api/audio/production_vibevoice_dialogue_api.json](/home/riki/web_dev/story_builder/workflows/api/audio/production_vibevoice_dialogue_api.json) | API | 8 | 0 | `0ac9016eb0dbd9b0a55ada3640ee95a4d2e7e4204225a15bbd7fcb89b5ee4975` |
| [workflows/api/audio/rvc_voice_api.json](/home/riki/web_dev/story_builder/workflows/api/audio/rvc_voice_api.json) | API | 8 | 0 | `ada34e38224376fc5df7d2440ac74ef869f9c0efb8b1501dff0364e19c261046` |
| [workflows/api/audio/style_edit_api.json](/home/riki/web_dev/story_builder/workflows/api/audio/style_edit_api.json) | API | 5 | 0 | `4211e1d30986655428e3af178a461c9e075bd82e4d4c3f0ec1b9eef5fe3ebaa3` |
| [workflows/api/audio/tts_multichar_timed_chatterbox_api.json](/home/riki/web_dev/story_builder/workflows/api/audio/tts_multichar_timed_chatterbox_api.json) | API | 7 | 0 | `3b1c28965a036b3de8aa91b0e3276c2977e1431d899ec173bd6cc8fc91eb8959` |
| [workflows/api/audio/voice_changer_api.json](/home/riki/web_dev/story_builder/workflows/api/audio/voice_changer_api.json) | API | 6 | 0 | `513de7b81fe2fef9b73a2251b82a6c1553a3628d74ccc7b2f997411d4d567075` |
| [workflows/api/audio/voice_repair_api.json](/home/riki/web_dev/story_builder/workflows/api/audio/voice_repair_api.json) | API | 4 | 0 | `6b2baaff7bba53c0d5e016b0aec2856efe7aa8bee8210c97a79a1d6b5ba3d1ba` |
| [workflows/api/gsl_starter_1_1_api.json](/home/riki/web_dev/story_builder/workflows/api/gsl_starter_1_1_api.json) | API | 10 | 0 | `d9ccfbdff52fca07264767da2b91e246c5c85a6310213f270cce2b0085485b6e` |
| [workflows/api/minimax_h3_i2v_api.json](/home/riki/web_dev/story_builder/workflows/api/minimax_h3_i2v_api.json) | API | 16 | 0 | `6c88479ce6f4ffad53b0a546bcf97de077b4ceb7affef2482d52d9455348271d` |
| [workflows/api/minimax_h3_r2v_api.json](/home/riki/web_dev/story_builder/workflows/api/minimax_h3_r2v_api.json) | API | 17 | 0 | `5ebac422ff9dd1eb467265d36610f10fa8744ff8c8d31262cd9bf871b814332d` |
| [workflows/api/minimax_h3_t2v_api.json](/home/riki/web_dev/story_builder/workflows/api/minimax_h3_t2v_api.json) | API | 14 | 0 | `4735e3662333493d488bc2ba6970810e620c13196ccac15b1155010e8cf3e1f9` |
| [workflows/api/qwen_2512_t2i_api.json](/home/riki/web_dev/story_builder/workflows/api/qwen_2512_t2i_api.json) | API | 10 | 0 | `724d04abd9303da761026b0966789c14d09b7848b07ed61ed2faca731a941927` |
| [workflows/api/qwen_2512_t2i_refine_api.json](/home/riki/web_dev/story_builder/workflows/api/qwen_2512_t2i_refine_api.json) | API | 23 | 0 | `dc0b53ff27bfdc91a4fe05c72f3bd1133c591cebea0e3f7ffe35dcd013ae55cb` |
| [workflows/api/qwen_edit_2511_api.json](/home/riki/web_dev/story_builder/workflows/api/qwen_edit_2511_api.json) | API | 18 | 0 | `49ee45e866e88c8c7cbb922cc913b3f115a1f524aa661535f6830e489a17b3e1` |
| [workflows/api/qwen_edit_api.json](/home/riki/web_dev/story_builder/workflows/api/qwen_edit_api.json) | API | 16 | 0 | `f2f40593a56942455a8b445936bf72dd180dce512cd7ed902a1ef32406f9c49f` |
| [workflows/api/wan2_2_flf2v_api.json](/home/riki/web_dev/story_builder/workflows/api/wan2_2_flf2v_api.json) | API | 16 | 0 | `d7ee42cf5251a0ffc21dba3713c517dd06d0a1defeec7844d7a1fda3bfd57eb3` |
| [workflows/audio/TTS_audio_multichar_timed_wf.json](/home/riki/web_dev/story_builder/workflows/audio/TTS_audio_multichar_timed_wf.json) | UI | 19 | 0 | `2e6ac8014879798b5ca643c3729da987d975a815b4b285143110e1865f5ca3b2` |
| [workflows/audio/audio_SRT_timing.json](/home/riki/web_dev/story_builder/workflows/audio/audio_SRT_timing.json) | UI | 9 | 0 | `676bc567a039e235ccc04764bcf235cb8616ef36768c80061b1aa825a0fffa35` |
| [workflows/audio/tts_multichar_timed_chatterbox_ui.json](/home/riki/web_dev/story_builder/workflows/audio/tts_multichar_timed_chatterbox_ui.json) | UI | 12 | 0 | `6b5e5a3be760cbf486321b210b3c7ba42e857bb56253e11981026b2d1ce2d864` |
| [workflows/image/02_qwen_Image_edit_subgraphed.json](/home/riki/web_dev/story_builder/workflows/image/02_qwen_Image_edit_subgraphed.json) | UI | 6 | 17 | `77725a6a6729f1f9952470afc82c9018818eb65d542e106ca19927efd2d060fb` |
| [workflows/image/image_qwen_Image_2512.json](/home/riki/web_dev/story_builder/workflows/image/image_qwen_Image_2512.json) | UI | 4 | 19 | `c66553d92beb7d85450e6b26a75c7658e6f988a0ec5a5ad41f90e8c75eed0d32` |
| [workflows/qwen_image/02_qwen_Image_edit_subgraphed.json](/home/riki/web_dev/story_builder/workflows/qwen_image/02_qwen_Image_edit_subgraphed.json) | UI | 6 | 17 | `77725a6a6729f1f9952470afc82c9018818eb65d542e106ca19927efd2d060fb` |
| [workflows/qwen_image/260330_MICKMUMPITZ_AI-VFX_1-0_SMPL.json](/home/riki/web_dev/story_builder/workflows/qwen_image/260330_MICKMUMPITZ_AI-VFX_1-0_SMPL.json) | UI | 72 | 15 | `3129bbb4409a41dd4a9d72f453d9275dfce2c3dab762cd092f06b9d3b35f43e3` |
| [workflows/qwen_image/260330_MICKMUMPITZ_AI-VFX_PREPROCESS_1-0.json](/home/riki/web_dev/story_builder/workflows/qwen_image/260330_MICKMUMPITZ_AI-VFX_PREPROCESS_1-0.json) | UI | 87 | 3 | `dac18fae51a0d9d353008585025a569294e3f0c1303a09a3e6022757dc3e3fe5` |
| [workflows/qwen_image/Benji modified - Multi-character dialogue ver 20260125.json](</home/riki/web_dev/story_builder/workflows/qwen_image/Benji modified - Multi-character dialogue ver 20260125.json>) | UI | 17 | 0 | `7e47a3a95c8918366b93ac5d89dc236ae833f3449e1edaff1f1b958804a4a13d` |
| [workflows/qwen_image/LTX_2_FirstLastFrame 20260112.json](</home/riki/web_dev/story_builder/workflows/qwen_image/LTX_2_FirstLastFrame 20260112.json>) | UI | 57 | 0 | `8e6c2cf03e614afc1f96de5b8c60bc2639c5a1a8f71541bcab06b77b27defb1e` |
| [workflows/qwen_image/Qwen 2511 multi angle (Single Sampler)+ZImageTurbo.json](</home/riki/web_dev/story_builder/workflows/qwen_image/Qwen 2511 multi angle (Single Sampler)+ZImageTurbo.json>) | UI | 26 | 10 | `5e61cdb8206d73f04943b8bb13a3c5b3e15134a6045f62de91a4d31c683e38b3` |
| [workflows/qwen_image/Qwen Image Edit -  Pose Studio + Camera Control 20260212.json](</home/riki/web_dev/story_builder/workflows/qwen_image/Qwen Image Edit -  Pose Studio + Camera Control 20260212.json>) | UI | 34 | 11 | `05a9c6aaae049a7b0109ceb80ba8a7c7694b7cedb0a04a5af2ae1dc5ea78fc0f` |
| [workflows/qwen_image/Qwen Image Edit -  Pose Studio With DWPOse + Camera Control 20260212.json](</home/riki/web_dev/story_builder/workflows/qwen_image/Qwen Image Edit -  Pose Studio With DWPOse + Camera Control 20260212.json>) | UI | 35 | 11 | `2559e3c5e2194b4e50e830c358e1b9cf8c88665534ec8a8989684da87d37ea28` |
| [workflows/qwen_image/TTS_audio_multichar_timed_wf.json](/home/riki/web_dev/story_builder/workflows/qwen_image/TTS_audio_multichar_timed_wf.json) | UI | 19 | 0 | `2e6ac8014879798b5ca643c3729da987d975a815b4b285143110e1865f5ca3b2` |
| [workflows/qwen_image/audio_SRT_timing.json](/home/riki/web_dev/story_builder/workflows/qwen_image/audio_SRT_timing.json) | UI | 9 | 0 | `676bc567a039e235ccc04764bcf235cb8616ef36768c80061b1aa825a0fffa35` |
| [workflows/qwen_image/audio_ace_step_1_t2a_instrumentals.json](/home/riki/web_dev/story_builder/workflows/qwen_image/audio_ace_step_1_t2a_instrumentals.json) | UI | 12 | 0 | `55263d4244838617fff6266c3f837683a9d5256aaa351053a782fbf4e1be8e1b` |
| [workflows/qwen_image/audio_ace_step_1_t2a_song.json](/home/riki/web_dev/story_builder/workflows/qwen_image/audio_ace_step_1_t2a_song.json) | UI | 11 | 0 | `0e29243e8884c93bda06baf88f21b12667345c581643849e159bd884996ebe11` |
| [workflows/qwen_image/audio_emotion.json](/home/riki/web_dev/story_builder/workflows/qwen_image/audio_emotion.json) | UI | 15 | 0 | `f05d2c1a0bd6000f47e13be4ead0de9684a8a9d950b34f49fe3601e883ef257a` |
| [workflows/qwen_image/gsc_creator_2_3.json](/home/riki/web_dev/story_builder/workflows/qwen_image/gsc_creator_2_3.json) | UI | 13 | 14 | `057cc3aeae1376093be6d6e94322c32bfac40d64cd3448fed35f4b76bd1b7581` |
| [workflows/qwen_image/gsl_starter_1_1.json](/home/riki/web_dev/story_builder/workflows/qwen_image/gsl_starter_1_1.json) | UI | 7 | 9 | `bb7cb26626e686643f4a0baf3de3bfa3ad9fe77ddc482ff4cb1eeaf48b3ecdd2` |
| [workflows/qwen_image/gsl_starter_1_2.json](/home/riki/web_dev/story_builder/workflows/qwen_image/gsl_starter_1_2.json) | UI | 11 | 69 | `d87bff78dfc6535df2c8d4324debf16994d92d9a32966294cbc12fc04d152b2a` |
| [workflows/qwen_image/hunyuan_foley.json](/home/riki/web_dev/story_builder/workflows/qwen_image/hunyuan_foley.json) | UI | 18 | 0 | `3bdd564211eaa00796bc501b1e922a423a7c51b3dfb9026630c59209d4095eaa` |
| [workflows/qwen_image/image_qwen_Image_2512.json](/home/riki/web_dev/story_builder/workflows/qwen_image/image_qwen_Image_2512.json) | UI | 4 | 19 | `c66553d92beb7d85450e6b26a75c7658e6f988a0ec5a5ad41f90e8c75eed0d32` |
| [workflows/qwen_image/ipadapter_controlnet_qwen.json](/home/riki/web_dev/story_builder/workflows/qwen_image/ipadapter_controlnet_qwen.json) | UI | 38 | 0 | `8b685ebc2bcdd1c6b2b43b6524eb1ccf21b4986e0c032e3c0cfd0a13c5bf49d7` |
| [workflows/qwen_image/ltx/1. LTX 2.3 All-In-One-1 260606-1.json](</home/riki/web_dev/story_builder/workflows/qwen_image/ltx/1. LTX 2.3 All-In-One-1 260606-1.json>) | UI | 175 | 214 | `213351876f45c96ee845970aa098b5022beabb3867c210b2077293cb76545492` |
| [workflows/qwen_image/qwen_multi_angle.json](/home/riki/web_dev/story_builder/workflows/qwen_image/qwen_multi_angle.json) | UI | 25 | 0 | `3305534f4176fcd0069a2fad2fa1dadaa885e7bdd43720f3d0029793a2a947d9` |
| [workflows/qwen_image/video_ltx2_3_flf2v.json](/home/riki/web_dev/story_builder/workflows/qwen_image/video_ltx2_3_flf2v.json) | UI | 35 | 0 | `91ec24821a403042098c1b857ea4b2165b6b2e3e50732116caea60794bc51087` |
| [workflows/qwen_image/video_ltx2_3_ia2v.json](/home/riki/web_dev/story_builder/workflows/qwen_image/video_ltx2_3_ia2v.json) | UI | 6 | 51 | `c180f41baa587b56d06fe27ab32447a6c19df97c7bf99a78fa81dc4da1335b12` |
| [workflows/qwen_image/video_ltx2_canny_to_video.json](/home/riki/web_dev/story_builder/workflows/qwen_image/video_ltx2_canny_to_video.json) | UI | 20 | 76 | `1fee558a77d8d9db9d56ae3623c207c04a63dc9f96737388a779e0960455cf8e` |
| [workflows/qwen_image/video_ltx2_depth_to_video.json](/home/riki/web_dev/story_builder/workflows/qwen_image/video_ltx2_depth_to_video.json) | UI | 20 | 88 | `62cc143ebee9d8cc583a325b11e0689bbbfcdc520d7a3576396dc394167a1323` |
| [workflows/qwen_image/video_wan2_2_14B_flf2v.json](/home/riki/web_dev/story_builder/workflows/qwen_image/video_wan2_2_14B_flf2v.json) | UI | 40 | 0 | `aa66baf93976a40ef58d327fc1ba0bf888788fad7550debba0a6ec9f876d0eb5` |
| [workflows/qwen_image/video_wan2_2_14B_fun_inpaint.json](/home/riki/web_dev/story_builder/workflows/qwen_image/video_wan2_2_14B_fun_inpaint.json) | UI | 38 | 0 | `84b7acb5dece15fab6b9b1e19f6fbd81599b4f703dbf9ed75154914f656e216b` |
| [workflows/qwen_image/video_wan2_2_14B_i2v.json](/home/riki/web_dev/story_builder/workflows/qwen_image/video_wan2_2_14B_i2v.json) | UI | 6 | 27 | `1f08affa9d9c1953a337bbcb8cdfc119d14116adf4bda575765323149b34fb61` |
| [workflows/qwen_image/video_wan2_2_14B_t2v.json](/home/riki/web_dev/story_builder/workflows/qwen_image/video_wan2_2_14B_t2v.json) | UI | 35 | 0 | `b0033344b43798fef61950813a503f6dc572040c3d2e0ae8954ee5110077bb48` |
| [workflows/qwen_image/wan2.1_fun_control.json](/home/riki/web_dev/story_builder/workflows/qwen_image/wan2.1_fun_control.json) | UI | 22 | 0 | `f7f88106f63234a246e463c97b22f04fe96ab5eb46a52587004ac1ec90621da2` |
| [workflows/ricky/02_qwen_Image_edit_subgraphed.json](/home/riki/web_dev/story_builder/workflows/ricky/02_qwen_Image_edit_subgraphed.json) | UI | 6 | 17 | `77725a6a6729f1f9952470afc82c9018818eb65d542e106ca19927efd2d060fb` |
| [workflows/ricky/Ideogram_4_Workflow11.json](/home/riki/web_dev/story_builder/workflows/ricky/Ideogram_4_Workflow11.json) | UI | 147 | 10 | `b02318a49743610a88005977adc94d5fc41d38bbc4d95b2925a103bdb47c8e38` |
| [workflows/ricky/Qwen 2511 multi angle (Single Sampler)+ZImageTurbo.json](</home/riki/web_dev/story_builder/workflows/ricky/Qwen 2511 multi angle (Single Sampler)+ZImageTurbo.json>) | UI | 26 | 10 | `c29ed5c36c2c1c46c1bb3843da73c760798038bea65efb4550f0aa30a6a711c0` |
| [workflows/ricky/TTS_audio_multichar_timed_wf.json](/home/riki/web_dev/story_builder/workflows/ricky/TTS_audio_multichar_timed_wf.json) | UI | 19 | 0 | `2e6ac8014879798b5ca643c3729da987d975a815b4b285143110e1865f5ca3b2` |
| [workflows/ricky/anima.json](/home/riki/web_dev/story_builder/workflows/ricky/anima.json) | Style preset | 0 | 0 | `8d0bf0625b8db06996e2cdc95824b1a863c0d51d404f9bc082619d8a2b9fe56a` |
| [workflows/ricky/audio_emotion.json](/home/riki/web_dev/story_builder/workflows/ricky/audio_emotion.json) | UI | 15 | 0 | `f05d2c1a0bd6000f47e13be4ead0de9684a8a9d950b34f49fe3601e883ef257a` |
| [workflows/ricky/control folley/02_tcv2a_text_controlled.json](</home/riki/web_dev/story_builder/workflows/ricky/control folley/02_tcv2a_text_controlled.json>) | UI | 5 | 0 | `17e09cd6238e31b2209b4fb5614684ee923bccd32314e049a9d547114a79b5fb` |
| [workflows/ricky/control folley/03_acv2a_audio_controlled.json](</home/riki/web_dev/story_builder/workflows/ricky/control folley/03_acv2a_audio_controlled.json>) | UI | 5 | 0 | `e52956857f160462f758013b604a7674b5f35b0af987e26b75ac914c2f1125ee` |
| [workflows/ricky/control folley/05_t2a_basic.json](</home/riki/web_dev/story_builder/workflows/ricky/control folley/05_t2a_basic.json>) | UI | 4 | 0 | `6d57ddc0751701064d32e08a7c59a1b8faf3d5e5b956cf9f93be840b7c6801c0` |
| [workflows/ricky/control folley/06_advanced_chain.json](</home/riki/web_dev/story_builder/workflows/ricky/control folley/06_advanced_chain.json>) | UI | 6 | 0 | `0f461cf5128ad5df927865d9d4fdd2c057cca38f8cf4d86cb902ccdb3a813abf` |
| [workflows/ricky/control folley/control_folley.json](</home/riki/web_dev/story_builder/workflows/ricky/control folley/control_folley.json>) | UI | 5 | 0 | `56095a138ef80e28cf5486f98f81ebb2f80d22c79f9e0ffc8692d3ea93f70bfe` |
| [workflows/ricky/control folley/control_folley_research.json](</home/riki/web_dev/story_builder/workflows/ricky/control folley/control_folley_research.json>) | UI | 5 | 0 | `4fb39bc8ae27b88d830f70fd2da769eb43709289d5d8be3be579dfe48c12d044` |
| [workflows/ricky/gsl_starter_1_1.json](/home/riki/web_dev/story_builder/workflows/ricky/gsl_starter_1_1.json) | UI | 7 | 9 | `bb7cb26626e686643f4a0baf3de3bfa3ad9fe77ddc482ff4cb1eeaf48b3ecdd2` |
| [workflows/ricky/hunyuan_foley.json](/home/riki/web_dev/story_builder/workflows/ricky/hunyuan_foley.json) | UI | 18 | 0 | `3bdd564211eaa00796bc501b1e922a423a7c51b3dfb9026630c59209d4095eaa` |
| [workflows/ricky/image_qwen_Image_2512.json](/home/riki/web_dev/story_builder/workflows/ricky/image_qwen_Image_2512.json) | UI | 4 | 19 | `8a7b238b79bfec5ea05148d365a5dacee912d7a49a2db5d682dd70edafd635e1` |
| [workflows/ricky/ltx/1. LTX 2.3 All-In-One-1 260606-1.json](</home/riki/web_dev/story_builder/workflows/ricky/ltx/1. LTX 2.3 All-In-One-1 260606-1.json>) | UI | 175 | 214 | `213351876f45c96ee845970aa098b5022beabb3867c210b2077293cb76545492` |
| [workflows/ricky/qwen_image_edit_2511.json](/home/riki/web_dev/story_builder/workflows/ricky/qwen_image_edit_2511.json) | UI | 6 | 23 | `6e687d4bfa65f0f77400c1206365f116e919f60519ac75e72569ec3e0e49f402` |
| [workflows/ricky/vid_minmax_h3_i2v.json](/home/riki/web_dev/story_builder/workflows/ricky/vid_minmax_h3_i2v.json) | UI | 9 | 15 | `bb71aecdd3c0b62e56eafe03acb14d1cfeabec7072eaed9cbdf473c2aaf73009` |
| [workflows/ricky/vid_minmax_h3_r2v.json](/home/riki/web_dev/story_builder/workflows/ricky/vid_minmax_h3_r2v.json) | UI | 23 | 0 | `099d24eda6263854818975c7209db6f29ebfd0339936c928f12293d5ab029ffb` |
| [workflows/ricky/vid_minmax_h3_r2v_crazy.json](/home/riki/web_dev/story_builder/workflows/ricky/vid_minmax_h3_r2v_crazy.json) | UI | 28 | 0 | `7cd08368bbcef64898232ec69d16452ea659bf4ff4b8d2de8453a0cc84ab3f80` |
| [workflows/ricky/vid_minmax_h3_t2v.json](/home/riki/web_dev/story_builder/workflows/ricky/vid_minmax_h3_t2v.json) | UI | 6 | 15 | `31ab33fdb053a7834cc866bd7aa08b887518fc656e4a796c89779c6b5e1786e6` |
| [workflows/ricky/video_ltx2_3_flf2v.json](/home/riki/web_dev/story_builder/workflows/ricky/video_ltx2_3_flf2v.json) | UI | 35 | 0 | `91ec24821a403042098c1b857ea4b2165b6b2e3e50732116caea60794bc51087` |
| [workflows/ricky/video_ltx2_3_ia2v.json](/home/riki/web_dev/story_builder/workflows/ricky/video_ltx2_3_ia2v.json) | UI | 6 | 50 | `d96b94f41e6aa09356c91e40da99f08f57add9969f44cb2826e9047ce2ed111d` |
| [workflows/ricky/video_wan2_2_14B_flf2v.json](/home/riki/web_dev/story_builder/workflows/ricky/video_wan2_2_14B_flf2v.json) | UI | 40 | 0 | `aa66baf93976a40ef58d327fc1ba0bf888788fad7550debba0a6ec9f876d0eb5` |
| [workflows/templates/gsl_starter_1_1_api.json](/home/riki/web_dev/story_builder/workflows/templates/gsl_starter_1_1_api.json) | API | 10 | 0 | `d9ccfbdff52fca07264767da2b91e246c5c85a6310213f270cce2b0085485b6e` |
| [workflows/video/video_ltx2_3_flf2v.json](/home/riki/web_dev/story_builder/workflows/video/video_ltx2_3_flf2v.json) | UI | 35 | 0 | `91ec24821a403042098c1b857ea4b2165b6b2e3e50732116caea60794bc51087` |
| [workflows/video/video_ltx2_3_ia2v.json](/home/riki/web_dev/story_builder/workflows/video/video_ltx2_3_ia2v.json) | UI | 6 | 51 | `c180f41baa587b56d06fe27ab32447a6c19df97c7bf99a78fa81dc4da1335b12` |
| [workflows/video/video_wan2_2_14B_i2v.json](/home/riki/web_dev/story_builder/workflows/video/video_wan2_2_14B_i2v.json) | UI | 6 | 27 | `1f08affa9d9c1953a337bbcb8cdfc119d14116adf4bda575765323149b34fb61` |
| [workflows/video/video_wan2_2_14B_t2v.json](/home/riki/web_dev/story_builder/workflows/video/video_wan2_2_14B_t2v.json) | UI | 35 | 0 | `b0033344b43798fef61950813a503f6dc572040c3d2e0ae8954ee5110077bb48` |

### Exact-byte duplicate groups

Preserve paths first; change aliases after tracing code/script references. Different hashes are not assumed different user capabilities.

- [workflows/api/gsl_starter_1_1_api.json](/home/riki/web_dev/story_builder/workflows/api/gsl_starter_1_1_api.json); [workflows/templates/gsl_starter_1_1_api.json](/home/riki/web_dev/story_builder/workflows/templates/gsl_starter_1_1_api.json) — `d9ccfbdff52fca07264767da2b91e246c5c85a6310213f270cce2b0085485b6e`
- [workflows/audio/TTS_audio_multichar_timed_wf.json](/home/riki/web_dev/story_builder/workflows/audio/TTS_audio_multichar_timed_wf.json); [workflows/qwen_image/TTS_audio_multichar_timed_wf.json](/home/riki/web_dev/story_builder/workflows/qwen_image/TTS_audio_multichar_timed_wf.json); [workflows/ricky/TTS_audio_multichar_timed_wf.json](/home/riki/web_dev/story_builder/workflows/ricky/TTS_audio_multichar_timed_wf.json) — `2e6ac8014879798b5ca643c3729da987d975a815b4b285143110e1865f5ca3b2`
- [workflows/audio/audio_SRT_timing.json](/home/riki/web_dev/story_builder/workflows/audio/audio_SRT_timing.json); [workflows/qwen_image/audio_SRT_timing.json](/home/riki/web_dev/story_builder/workflows/qwen_image/audio_SRT_timing.json) — `676bc567a039e235ccc04764bcf235cb8616ef36768c80061b1aa825a0fffa35`
- [workflows/image/02_qwen_Image_edit_subgraphed.json](/home/riki/web_dev/story_builder/workflows/image/02_qwen_Image_edit_subgraphed.json); [workflows/qwen_image/02_qwen_Image_edit_subgraphed.json](/home/riki/web_dev/story_builder/workflows/qwen_image/02_qwen_Image_edit_subgraphed.json); [workflows/ricky/02_qwen_Image_edit_subgraphed.json](/home/riki/web_dev/story_builder/workflows/ricky/02_qwen_Image_edit_subgraphed.json) — `77725a6a6729f1f9952470afc82c9018818eb65d542e106ca19927efd2d060fb`
- [workflows/image/image_qwen_Image_2512.json](/home/riki/web_dev/story_builder/workflows/image/image_qwen_Image_2512.json); [workflows/qwen_image/image_qwen_Image_2512.json](/home/riki/web_dev/story_builder/workflows/qwen_image/image_qwen_Image_2512.json) — `c66553d92beb7d85450e6b26a75c7658e6f988a0ec5a5ad41f90e8c75eed0d32`
- [workflows/qwen_image/audio_emotion.json](/home/riki/web_dev/story_builder/workflows/qwen_image/audio_emotion.json); [workflows/ricky/audio_emotion.json](/home/riki/web_dev/story_builder/workflows/ricky/audio_emotion.json) — `f05d2c1a0bd6000f47e13be4ead0de9684a8a9d950b34f49fe3601e883ef257a`
- [workflows/qwen_image/gsl_starter_1_1.json](/home/riki/web_dev/story_builder/workflows/qwen_image/gsl_starter_1_1.json); [workflows/ricky/gsl_starter_1_1.json](/home/riki/web_dev/story_builder/workflows/ricky/gsl_starter_1_1.json) — `bb7cb26626e686643f4a0baf3de3bfa3ad9fe77ddc482ff4cb1eeaf48b3ecdd2`
- [workflows/qwen_image/hunyuan_foley.json](/home/riki/web_dev/story_builder/workflows/qwen_image/hunyuan_foley.json); [workflows/ricky/hunyuan_foley.json](/home/riki/web_dev/story_builder/workflows/ricky/hunyuan_foley.json) — `3bdd564211eaa00796bc501b1e922a423a7c51b3dfb9026630c59209d4095eaa`
- [workflows/qwen_image/ltx/1. LTX 2.3 All-In-One-1 260606-1.json](</home/riki/web_dev/story_builder/workflows/qwen_image/ltx/1. LTX 2.3 All-In-One-1 260606-1.json>); [workflows/ricky/ltx/1. LTX 2.3 All-In-One-1 260606-1.json](</home/riki/web_dev/story_builder/workflows/ricky/ltx/1. LTX 2.3 All-In-One-1 260606-1.json>) — `213351876f45c96ee845970aa098b5022beabb3867c210b2077293cb76545492`
- [workflows/qwen_image/video_ltx2_3_flf2v.json](/home/riki/web_dev/story_builder/workflows/qwen_image/video_ltx2_3_flf2v.json); [workflows/ricky/video_ltx2_3_flf2v.json](/home/riki/web_dev/story_builder/workflows/ricky/video_ltx2_3_flf2v.json); [workflows/video/video_ltx2_3_flf2v.json](/home/riki/web_dev/story_builder/workflows/video/video_ltx2_3_flf2v.json) — `91ec24821a403042098c1b857ea4b2165b6b2e3e50732116caea60794bc51087`
- [workflows/qwen_image/video_ltx2_3_ia2v.json](/home/riki/web_dev/story_builder/workflows/qwen_image/video_ltx2_3_ia2v.json); [workflows/video/video_ltx2_3_ia2v.json](/home/riki/web_dev/story_builder/workflows/video/video_ltx2_3_ia2v.json) — `c180f41baa587b56d06fe27ab32447a6c19df97c7bf99a78fa81dc4da1335b12`
- [workflows/qwen_image/video_wan2_2_14B_flf2v.json](/home/riki/web_dev/story_builder/workflows/qwen_image/video_wan2_2_14B_flf2v.json); [workflows/ricky/video_wan2_2_14B_flf2v.json](/home/riki/web_dev/story_builder/workflows/ricky/video_wan2_2_14B_flf2v.json) — `aa66baf93976a40ef58d327fc1ba0bf888788fad7550debba0a6ec9f876d0eb5`
- [workflows/qwen_image/video_wan2_2_14B_i2v.json](/home/riki/web_dev/story_builder/workflows/qwen_image/video_wan2_2_14B_i2v.json); [workflows/video/video_wan2_2_14B_i2v.json](/home/riki/web_dev/story_builder/workflows/video/video_wan2_2_14B_i2v.json) — `1f08affa9d9c1953a337bbcb8cdfc119d14116adf4bda575765323149b34fb61`
- [workflows/qwen_image/video_wan2_2_14B_t2v.json](/home/riki/web_dev/story_builder/workflows/qwen_image/video_wan2_2_14B_t2v.json); [workflows/video/video_wan2_2_14B_t2v.json](/home/riki/web_dev/story_builder/workflows/video/video_wan2_2_14B_t2v.json) — `b0033344b43798fef61950813a503f6dc572040c3d2e0ae8954ee5110077bb48`

### Nested recipe discovery

| Graph | Named stored subgraphs |
|---|---|
| [workflows/image/02_qwen_Image_edit_subgraphed.json](/home/riki/web_dev/story_builder/workflows/image/02_qwen_Image_edit_subgraphed.json) | Qwen Image Edit 2509 (Simplified) |
| [workflows/image/image_qwen_Image_2512.json](/home/riki/web_dev/story_builder/workflows/image/image_qwen_Image_2512.json) | Text to Image (Qwen-Image 2512) |
| [workflows/qwen_image/02_qwen_Image_edit_subgraphed.json](/home/riki/web_dev/story_builder/workflows/qwen_image/02_qwen_Image_edit_subgraphed.json) | Qwen Image Edit 2509 (Simplified) |
| [workflows/qwen_image/260330_MICKMUMPITZ_AI-VFX_1-0_SMPL.json](/home/riki/web_dev/story_builder/workflows/qwen_image/260330_MICKMUMPITZ_AI-VFX_1-0_SMPL.json) | SETTINGS; Sampler |
| [workflows/qwen_image/260330_MICKMUMPITZ_AI-VFX_PREPROCESS_1-0.json](/home/riki/web_dev/story_builder/workflows/qwen_image/260330_MICKMUMPITZ_AI-VFX_PREPROCESS_1-0.json) | SETTINGS |
| [workflows/qwen_image/Qwen 2511 multi angle (Single Sampler)+ZImageTurbo.json](</home/riki/web_dev/story_builder/workflows/qwen_image/Qwen 2511 multi angle (Single Sampler)+ZImageTurbo.json>) | Image to Image (Z-Image-Turbo) |
| [workflows/qwen_image/Qwen Image Edit -  Pose Studio + Camera Control 20260212.json](</home/riki/web_dev/story_builder/workflows/qwen_image/Qwen Image Edit -  Pose Studio + Camera Control 20260212.json>) | Image to Image (Z-Image-Turbo) |
| [workflows/qwen_image/Qwen Image Edit -  Pose Studio With DWPOse + Camera Control 20260212.json](</home/riki/web_dev/story_builder/workflows/qwen_image/Qwen Image Edit -  Pose Studio With DWPOse + Camera Control 20260212.json>) | Image to Image (Z-Image-Turbo) |
| [workflows/qwen_image/gsc_creator_2_3.json](/home/riki/web_dev/story_builder/workflows/qwen_image/gsc_creator_2_3.json) | Image Upscale (Z-image-Turbo) |
| [workflows/qwen_image/gsl_starter_1_1.json](/home/riki/web_dev/story_builder/workflows/qwen_image/gsl_starter_1_1.json) | Z-Image-Turbo |
| [workflows/qwen_image/gsl_starter_1_2.json](/home/riki/web_dev/story_builder/workflows/qwen_image/gsl_starter_1_2.json) | 4 Frame Animation; First-Last-Frame  to Video (Wan 2.2); First-Last-Frame  to Video (Wan 2.2); First-Last-Frame  to Video (Wan 2.2); First-Last-Frame  to Video (Wan 2.2) |
| [workflows/qwen_image/image_qwen_Image_2512.json](/home/riki/web_dev/story_builder/workflows/qwen_image/image_qwen_Image_2512.json) | Text to Image (Qwen-Image 2512) |
| [workflows/qwen_image/ltx/1. LTX 2.3 All-In-One-1 260606-1.json](</home/riki/web_dev/story_builder/workflows/qwen_image/ltx/1. LTX 2.3 All-In-One-1 260606-1.json>) | New Subgraph; New Subgraph; New Subgraph; New Subgraph; New Subgraph; New Subgraph |
| [workflows/qwen_image/video_ltx2_3_ia2v.json](/home/riki/web_dev/story_builder/workflows/qwen_image/video_ltx2_3_ia2v.json) | Video Generation (LTX-2.3) |
| [workflows/qwen_image/video_ltx2_canny_to_video.json](/home/riki/web_dev/story_builder/workflows/qwen_image/video_ltx2_canny_to_video.json) | Canny to Video (LTX 2.0); Canny to Video (LTX 2.0 Distilled) |
| [workflows/qwen_image/video_ltx2_depth_to_video.json](/home/riki/web_dev/story_builder/workflows/qwen_image/video_ltx2_depth_to_video.json) | Depth to Video (LTX 2.0); Canny to Video (LTX 2.0 Distilled); Image to Depth Map (Lotus) |
| [workflows/qwen_image/video_wan2_2_14B_i2v.json](/home/riki/web_dev/story_builder/workflows/qwen_image/video_wan2_2_14B_i2v.json) | Image to Video (Wan2.2) |
| [workflows/ricky/02_qwen_Image_edit_subgraphed.json](/home/riki/web_dev/story_builder/workflows/ricky/02_qwen_Image_edit_subgraphed.json) | Qwen Image Edit 2509 (Simplified) |
| [workflows/ricky/Ideogram_4_Workflow11.json](/home/riki/web_dev/story_builder/workflows/ricky/Ideogram_4_Workflow11.json) | JSON Prompt Builder (Gemma4); Image To JSON Prompt Builder (Gemma4) |
| [workflows/ricky/Qwen 2511 multi angle (Single Sampler)+ZImageTurbo.json](</home/riki/web_dev/story_builder/workflows/ricky/Qwen 2511 multi angle (Single Sampler)+ZImageTurbo.json>) | Image to Image (Z-Image-Turbo) |
| [workflows/ricky/gsl_starter_1_1.json](/home/riki/web_dev/story_builder/workflows/ricky/gsl_starter_1_1.json) | Z-Image-Turbo |
| [workflows/ricky/image_qwen_Image_2512.json](/home/riki/web_dev/story_builder/workflows/ricky/image_qwen_Image_2512.json) | Text to Image (Qwen-Image 2512) |
| [workflows/ricky/ltx/1. LTX 2.3 All-In-One-1 260606-1.json](</home/riki/web_dev/story_builder/workflows/ricky/ltx/1. LTX 2.3 All-In-One-1 260606-1.json>) | New Subgraph; New Subgraph; New Subgraph; New Subgraph; New Subgraph; New Subgraph |
| [workflows/ricky/qwen_image_edit_2511.json](/home/riki/web_dev/story_builder/workflows/ricky/qwen_image_edit_2511.json) | Image Edit (Qwen-Image 2511) |
| [workflows/ricky/vid_minmax_h3_i2v.json](/home/riki/web_dev/story_builder/workflows/ricky/vid_minmax_h3_i2v.json) | Image to Video (MiniMax H3) |
| [workflows/ricky/vid_minmax_h3_t2v.json](/home/riki/web_dev/story_builder/workflows/ricky/vid_minmax_h3_t2v.json) | Image to Video (MiniMax H3) |
| [workflows/ricky/video_ltx2_3_ia2v.json](/home/riki/web_dev/story_builder/workflows/ricky/video_ltx2_3_ia2v.json) | Video Generation (LTX-2.3) |
| [workflows/video/video_ltx2_3_ia2v.json](/home/riki/web_dev/story_builder/workflows/video/video_ltx2_3_ia2v.json) | Video Generation (LTX-2.3) |
| [workflows/video/video_wan2_2_14B_i2v.json](/home/riki/web_dev/story_builder/workflows/video/video_wan2_2_14B_i2v.json) | Image to Video (Wan2.2) |

## Engine model inventory summary

305 filename/size entries were recorded under `ComfyUI/models` and setup `models`. Shards, auxiliaries and duplicate resources are counted separately. No binary was read or loaded. This inventory does not include every model stored outside those roots or behind unvisited directory symlinks.

| Directory family | Weight entries | Recorded bytes | Examples |
|---|---:|---:|---|
| `ComfyUI/models/MoGe` | 1 | 1,305,030,700 | `ComfyUI/models/MoGe/moge-2-vitl/model.pt` |
| `ComfyUI/models/NAF` | 1 | 2,664,431 | `ComfyUI/models/NAF/naf_release.pth` |
| `ComfyUI/models/Pixal3D` | 8 | 25,257,412,422 | `ComfyUI/models/Pixal3D/camenduru_dinov3-vitl16-pretrain-lvd1689m/model.safetensors`<br>`ComfyUI/models/Pixal3D/ckpts/slat_flow_img2shape_dit_1_3B_1024_bf16.safetensors`<br>`ComfyUI/models/Pixal3D/ckpts/ss_flow_img_dit_1_3B_64_bf16.safetensors` |
| `ComfyUI/models/TTS` | 208 | 269,162,519,967 | `ComfyUI/models/TTS/content-vec-best.safetensors`<br>`ComfyUI/models/TTS/rmvpe.pt`<br>`ComfyUI/models/TTS/qwen3_tts/Qwen3-TTS-12Hz-0.6B-Base/model.safetensors` |
| `ComfyUI/models/UltraShape` | 1 | 7,366,231,254 | `ComfyUI/models/UltraShape/ultrashape_v1.pt` |
| `ComfyUI/models/checkpoints` | 6 | 35,187,626,255 | `ComfyUI/models/checkpoints/zavychromaxl_v80.safetensors`<br>`ComfyUI/models/checkpoints/ace_step_v1_3.5b.safetensors`<br>`ComfyUI/models/checkpoints/sd_xl_base_1.0.safetensors` |
| `ComfyUI/models/clip_vision` | 3 | 7,482,505,508 | `ComfyUI/models/clip_vision/clip-vision_vit-h.safetensors`<br>`ComfyUI/models/clip_vision/clip_vision_h.safetensors`<br>`ComfyUI/models/clip_vision/clip-vision_vit-g.safetensors` |
| `ComfyUI/models/controlfoley` | 5 | 16,578,896,893 | `ComfyUI/models/controlfoley/weights/controlfoley.pth`<br>`ComfyUI/models/controlfoley/ext_weights/cav_mae_st.pth`<br>`ComfyUI/models/controlfoley/ext_weights/v1-44.pth` |
| `ComfyUI/models/controlnet` | 8 | 23,975,470,197 | `ComfyUI/models/controlnet/noobaiXLControlnet_openposeModel.safetensors`<br>`ComfyUI/models/controlnet/controlnet-depth-sdxl-1.0.safetensors`<br>`ComfyUI/models/controlnet/noob-sdxl-controlnet-scribble_pidinet.fp16.safetensors` |
| `ComfyUI/models/detection` | 2 | 1,296,238,505 | `ComfyUI/models/detection/yolov10m.onnx`<br>`ComfyUI/models/detection/vitpose-l-wholebody.onnx` |
| `ComfyUI/models/diffusion_models` | 17 | 232,949,566,414 | `ComfyUI/models/diffusion_models/anima-preview.safetensors`<br>`ComfyUI/models/diffusion_models/hunyuan_3d_v2.1.safetensors`<br>`ComfyUI/models/diffusion_models/seedvr2_3b_int8_convrot.safetensors` |
| `ComfyUI/models/dwpose` | 2 | 351,805,857 | `ComfyUI/models/dwpose/yolox_l.onnx`<br>`ComfyUI/models/dwpose/dw-ll_ucoco_384_bs5.torchscript.pt` |
| `ComfyUI/models/inpaint` | 2 | 125,332,880 | `ComfyUI/models/inpaint/fooocus_inpaint_head.pth`<br>`ComfyUI/models/inpaint/MAT_Places512_G_fp16.safetensors` |
| `ComfyUI/models/ipadapter` | 2 | 2,103,563,120 | `ComfyUI/models/ipadapter/noobIPAMARK1_mark1.safetensors`<br>`ComfyUI/models/ipadapter/ip-adapter_sdxl_vit-h.safetensors` |
| `ComfyUI/models/loras` | 17 | 14,637,960,299 | `ComfyUI/models/loras/lightx2v_I2V_14B_480p_cfg_step_distill_rank64_bf16.safetensors`<br>`ComfyUI/models/loras/low_noise_model.safetensors`<br>`ComfyUI/models/loras/wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors` |
| `ComfyUI/models/text_encoders` | 7 | 60,691,256,978 | `ComfyUI/models/text_encoders/gemma4_e4b_it_fp8_scaled.safetensors`<br>`ComfyUI/models/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors`<br>`ComfyUI/models/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors` |
| `ComfyUI/models/unet` | 1 | 11,627,589,408 | `ComfyUI/models/unet/gguf/wan-14B_vace_skyreels_v3_R2V_e4m3fn_v1-Q4_K_M.gguf` |
| `ComfyUI/models/upscale_models` | 6 | 327,400,055 | `ComfyUI/models/upscale_models/OmniSR_X4_DIV2K.safetensors`<br>`ComfyUI/models/upscale_models/OmniSR_X2_DIV2K.safetensors`<br>`ComfyUI/models/upscale_models/4x_NMKD-Superscale-SP_178000_G.pth` |
| `ComfyUI/models/vae` | 8 | 7,747,342,944 | `ComfyUI/models/vae/flux2-vae.safetensors`<br>`ComfyUI/models/vae/Wan2.1_VAE.safetensors`<br>`ComfyUI/models/vae/seedvr2_ema_vae_fp16.safetensors` |

## Additional source areas and disposition

| Area | Evidence inspected | Disposition |
|---|---|---|
| Root Streamlit app, pipeline, engine, utils | Entry points, stage methods and generic workflow builders | Historical overlap; current service adapters remain primary |
| Art_ist_min | README, API declarations and current generation/status paths, supervision/recovery and TTS utility source | README is stale; preserve unique utility/agent integration references, not a second production website |
| Hermes media/audio and TTS skills | Request schemas, allowlist, CLI/API clients and dialogue/voice contracts | Optional integration/operator guidance; old reference bounds labeled |
| Image_detailer | Standalone README/entry point/iterative flow plus root facade imports | Standalone iteration capabilities; core facade imports current analyzer package |
| video_audio_analyzer | README, worker/adapters/package layout and optional service contracts | Required current source; isolated inference preserved |
| video_summariser | Legacy README/path/index uses | Preserve curated media and legacy namespaces until compatibility adapter covers them |
| StyleTTS2 / app / finetune_model | App/inference/preparation/training entry points, config/checkpoint presence | Standalone; root website training not established |
| ACE-Step and song_gen/codes | Generation adapter, preflight, trainer/conversion paths, dataset pipeline and raga placeholder | Reuse generation/preparation; full training remains gated |
| youtube_code | Historical helper layout | Reference; prefer current managed adapters |
| setup_comfy_and-stuff | Root setup guidance, Docker configs, Comfy custom-node/model layout and installed pause parser | External installed engine; no copy/reinstallation |

## Traced gaps affecting migration

1. `services/audio_tts.py` applies its speaker-tag regex to every bracket tag. Normal `[pause:1s]` becomes an unknown character. The installed suite has `utils/text/pause_processor.py` with pause/wait/stop parsing. Fix the adapter and preserve the engine behavior.
2. `services/audio_automation.py` lists twelve blocks but dispatches no noise-cleanup/Demucs adapter; input-bearing Foley modes reject bindings. Early executable-support validation is needed.
3. StoryCanvas selected-passage “edit” adds a request marker locally; it does not call a provider to rewrite the selection.
4. Reconstruction “calibrate” stores sentence/settings metadata. Current frontend uploads supplied audio/transcript and lacks automatic recording/ASR/accept action.
5. Capability readers require existing smoke manifests under output/storage. A code-only copy loses that evidence unless explicitly preserved/relocated.
6. `_build_output_manifest` scans all files under project output; it does not select only accepted takes. Its docstring overstates acceptance filtering.
7. Main application startup starts durable consumers. Pointing the migrated copy at source data without isolating ownership may resume jobs.
8. `image_detailer.py` imports `video_audio_analyzer/src/video_scene_summarizer` utilities. Omitting analyzer source breaks even root image analysis.
9. Legacy and current analyzer packages use overlapping namespaces. Do not combine them by indiscriminate directory merging.
10. Source checkpoints and UI graphs do not establish that optional FL2VA, training, raga or every auxiliary analyzer path is ready.
