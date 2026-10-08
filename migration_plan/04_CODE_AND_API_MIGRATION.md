# Code, file placement and API migration

**Status:** proposed implementation plan. No application files have been copied by this audit.

## 1. Preserve the source package layout in the first copy

Use one private repository rooted at `/home/riki/Documents/ChatGPT/Vibe Director`. Keep the Python package name `story_builder` initially, because existing imports, tests and workers use it. “Vibe Director” is the product name; renaming internal packages adds no immediate product value.

```text
Vibe Director/
  README.md, COLLABORATION.md, AGENTS.md
  migration_plan/                  this plan
  docs/                           future product glossary/decisions/operator docs
  app/
    story_builder/
      __init__.py
      api/main.py                 same API paths; split later
      services/                   preserve existing file names first
      config/
      prompts/
      workflows/                  all graphs, original paths first
      frontend/app/               existing Vite website and lockfile
      video_audio_analyzer/       source/config/services only, no models/runs/venvs
      runtimes/                   owned utility compatibility code
      scripts/, tests/, pytest.ini, requirements.txt
      run_story_builder.sh        adapted launcher
  integrations/                   selected optional standalone tools later
  runtime/                        ignored data; configured in later PR
    storage/, output/, video_repertoire/, legacy_video/
  .github/                        issue/PR templates and CPU CI later
```

This layout deliberately keeps `services/...` next to `workflows`, `prompts`, the frontend and analyzer. Current root-relative code continues to resolve after the initial copy. Run Python with `<repo>/app` on the import path, e.g. from that directory with `python -m uvicorn story_builder.api.main:app`. The existing launcher already computes the parent directory; adapt ports and optional service startup behavior in a small PR.

Until path configuration is introduced, a **disposable cloned data fixture** can live at the current package-relative storage/output locations. The eventual ignored `runtime/` roots require explicit configuration changes; do not assume today's backend supports every new variable below.

## 2. Exact copy/adapt rules

All source prefixes in this table are `/home/riki/web_dev/story_builder/` unless otherwise stated. Directory rules mean preserve every owned file recursively with exclusions listed below. The source appendix lists exact services, routes and graph files.

| Source | Proposed destination relative to Vibe Director | Action |
|---|---|---|
| `__init__.py`, `api/`, `services/`, `config/` | `app/story_builder/` with identical relative paths | Copy owned source first; keep request/response schemas and imports |
| `prompts/` | `app/story_builder/prompts/` | Copy all versioned packs/corpus/profile registry; retain hashes/version semantics |
| `workflows/` | `app/story_builder/workflows/` | Copy all 90 JSON files and accompanying source/docs first; deduplicate only with compatibility aliases after usage is traced |
| `frontend/app/src/`, `public/`, `index.html`, `package.json`, lockfile and build/typecheck/test/lint configs | `app/story_builder/frontend/app/` | Copy website source/config; retain exact resolved lockfile; rebuild dist later |
| `video_audio_analyzer/` owned source, service wrappers, configs, dependency/lock files and required package resources | `app/story_builder/video_audio_analyzer/` | Required even for root image analysis imports; retain package layout and subprocess isolation |
| `runtimes/` | `app/story_builder/runtimes/` | Copy owned audio-utilities compatibility source |
| `scripts/`, `tests/`, `pytest.ini`, `requirements.txt` | `app/story_builder/` with same paths | Copy current verification assets; no install/render on copy |
| `run_story_builder.sh` | `app/story_builder/run_story_builder.sh` | Adapt backend/frontend ports and service ownership; explicit non-production fixture start |
| `plan/new_complete_plan/12_CURRENT_STATUS.md`, `25_PRODUCTION_OPERATOR_GUIDE.md`, `27_FINAL_RELEASE_2026_10_07.md`, required evidence manifests | `docs/source-release/` preserving evidence file names | Keep historical release evidence with original scope; relocate referenced media separately |
| `docs/media-composer/` and relevant original README/AGENTS excerpts | `docs/source-reference/` | Preserve contracts; write a new concise project AGENTS rather than blindly importing all historical release constraints |
| `hermes_comfyui/runner/`, tests and operator references | `integrations/hermes_comfyui/` later | Optional CLI; adjust graph root to the migrated package; old H3 contracts remain labeled |
| `hermes_story_builder/runner/`, `TTS_skills/` | `integrations/agent_audio/` and `docs/agent-audio/` later | Reuse API client/operator guidance; no automatic agent installation |
| `Image_detailer/` | `integrations/image_detailer/` later | Preserve standalone iterative app separately; root facade already imports analyzer utilities |
| `audio/StyleTTS2_app/` and selected `audio/StyleTTS2/` source/config | `integrations/styletts2/` later | Keep app/source relationship through configured root; checkpoints remain external |
| `audio/song_gen/codes/` | `integrations/music_dataset/` later | Copy preparation source; label raga hook incomplete |
| Selected ACE-Step conversion/trainer source | `integrations/ace_step_training/` later | Reference pinned upstream/runtime; no automatic full-training enablement |
| `Art_ist_min/api_server/services/tts_assets.py`, relevant schema/alias/report logic and tests | `integrations/legacy_art_reference/` or adapted domain service later | Extract only unique utilities; do not copy its second website/backend/controller as production |
| `Art_ist_min` OpenClaw supervision/recovery source | `integrations/openclaw_reference/` later | Optional integration research; use production job ownership rather than adding competing workers |
| `app.py`, `_stages.py`, `pipeline/`, `engine/`, `utils/`, old `youtube_code/` | Historical reference initially | Legacy Streamlit/planning/generic engine utilities overlap current services; copy a helper only for a traced unique need |
| `storage/`, `output/`, `video_repertoire/`, analyzer runs, `video_summariser/out_videos/` | Ignored runtime roots via separate migration manifest | Data copy/attach, not Git source copy; preserve IDs/ownership/hashes |
| `/home/riki/web_dev/setup_comfy_and-stuff` | Remains in place | Engine/model installation is referenced, not copied into app Git |

### Exclude from source copying

Nested `.git`, `.agents`, `.codex`, credentials and raw `.env*`; node_modules; built dist; venv/.venv/conda/site-packages; Python/test caches; logs; downloaded model weights/checkpoints; output/input/staging/media/datasets; temporary acceptance data; vendor caches; duplicate vendored runtime trees such as `Art_ist_min/TTS-Audio-Suite` when the installed engine is authoritative. Retain required small package resources and LICENSE/NOTICE files for selected dependencies.

Create a file manifest before copying, with source path, destination, SHA-256, category and exclusions. Compare source/destination bytes for unchanged files. Use a filtered copy; do not copy the whole giant tree and clean it afterward. Keep original source untouched and record its current revision/dirty-file state; filesystem source is authoritative when its Git history is incomplete.

## 3. Backend: one modular API application first

Keep FastAPI and current services. Split `api/main.py` (about 7,168 lines) into domain routers and shared dependencies **after** the copied app works with a fixture. These are code modules, not separate network services. Existing analyzer auxiliary services remain isolated because their dependencies are already different.

Proposed router files under `app/story_builder/api/routers/`:

| Router | Existing ownership | Existing service files to reuse |
|---|---|---|
| `projects.py` | Projects, drafts, legacy artifacts and canvas revisions | project_store, story_pipeline, story_revisions, project_graph |
| `styles.py` | Production types, profiles, source references and style drafts/versions | prompt_styles, production_style_catalog, production_director_profiles, narrative_style_sources/library |
| `production_runs.py` | Run config, stages, task state, canon revisions and controller actions | production_authority, production_text_controller, production_story_revisions, production_stage_tasks, chunked_generation |
| `canon_assets.py` | Characters/worlds, accepted masters, voice bindings, content resolution | production_assets, production_world_state, production_route_assets, production_voice_binding/excerpt |
| `shots.py` | Shot plans, validation, prompt draft/refine and exact reference ordering | production_shot_plan/validation, director_contract, production_refine_store, minimax_h3_graph_compiler/t2v/media |
| `takes.py` | Queue/status/accept/cancel/retry/reconcile and review | production_ledger, production_take_runtime, production_job_worker, production_video_director, production_temporal_video_evidence |
| `images.py` | Candidate batches/jobs/acceptance and image recipe capabilities | production_image_workflows/jobs/worker/director |
| `audio.py` | Voices, timed TTS, effects, scenes, production dialogue and reconstruction | audio_catalog/tts/effects/scene/reconstruct, production_dialogue_tts/audio_sidecars |
| `audio_library.py` | Curated audio and batch utility jobs | audio_utilities |
| `music_foley.py` | Music and validated Foley recipes/jobs | music_sound, control_foley |
| `automation.py` | Pipeline definitions, validation, runs and step retry | audio_automation |
| `repertoire.py` | Videos, YouTube jobs, analysis, reference search and selection | video_repertoire/worker, video_references, video_audio_search/sam |
| `vision.py` | Image analysis, visual runs, events, briefs and promotion | image_detailer, vision_runs/contracts |
| `workflows.py` | Generic catalog/details, upload and supported API-graph jobs | workflow_catalog, media_jobs, production_*_capability |
| `training.py` | Dataset preflight/preparation; no full-training switch | audio_finetune, music_sound preflight |
| `delivery.py` | Output manifest and legacy one-video/one-audio compose | existing API implementation initially |
| `operations.py` | Health/provider settings/status and aggregate job reads | reasoning_provider, existing status helpers |

Create `api/dependencies.py` for stores, configured roots and ownership resolvers; `api/schemas/` for extracted Pydantic models; `api/lifecycle.py` for existing worker construction/start/stop. Extract one router at a time, retaining URLs and schemas exactly. Keep `api/main.py` as assembly and temporary compatibility re-exports where tests/importers require them.

**Critical dependency:** worker-construction closures and controller helpers in main.py share project stores/output collectors/stage helpers. Extract those together into injected runtime/controller dependencies before moving handlers that use them; copying only decorators would break behavior.

## 4. Module and job contracts

Small APIs should represent domain actions, not expose arbitrary filesystem paths or graph-node edits. Keep current project/run-scoped endpoints and known asset IDs. Each route delegates to a domain service; ComfyUI submission occurs only through its guarded worker/adapter.

- Project/canon service owns identity and revisions.
- Workflow adapter owns recipe schema, graph/model version and validation.
- Job/take owner owns idempotency, status, prompt ID and recovery.
- Media owner resolves authorized bytes; caller references IDs and roles.
- Director proposes/reviews; saved authority policy controls acceptance/continuation.
- Analyzer owns its heavy inference/runtime and produces immutable evidence.

Existing queues are intentionally different. Do not replace ledger, image queue, sidecar queue, project JSON jobs and repertoire subprocess records with a new job system during migration. A proposed read-only `/api/jobs` projection may aggregate `{kind, owner, native_id, project_id, run_id, native_status, display_status, actions}`. Actions still call the owning API and use native ID/idempotency rules. This endpoint is **new work**, not an existing source endpoint.

Lifecycle currently starts production text/audio/image/video consumers on application startup. A copied app pointed at live data can resume work immediately. Fixture mode must disable consumers or use isolated stores before any parity startup. Do not import/start the app against production just to generate documentation.

## 5. Frontend/API compatibility

Keep current `project-api.ts`, `tts-api.ts` and `agent-api.ts` client signatures first. Later introduce domain client files with re-exports to reduce simultaneous churn. Preserve polling/invalidation rules and exact gate/run status interpretation. Generated schemas/OpenAPI client generation is optional after the existing contract is stable, not prerequisite work.

Backend endpoint names still say `production/v2`; that is a compatibility namespace. Product branding and scoped frontend URLs can change independently. The full existing route inventory is the baseline in [08_SOURCE_EVIDENCE.md](08_SOURCE_EVIDENCE.md).

## 6. Sequence and acceptance

1. Manifest and selective source copy; paths/imports untouched.
2. Configuration/root overrides and fixture-only launch. No shared live writers.
3. Existing CPU contract/frontend checks against migrated copy.
4. Safe live-data preservation/cutover as described in the data plan.
5. Navigation/header/URL context, then one workspace panel at a time.
6. Domain router extraction, one domain per PR, with response/ownership/recovery compatibility checks.
7. Unique optional adapters only when their customer journey is ready.

No mass package rename, database replacement, new queue infrastructure, full UI rebuild or model redownload is needed to achieve this migration.
