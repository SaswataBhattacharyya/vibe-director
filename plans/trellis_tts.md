# TRELLIS.2, Z-Image training and TTS integration plan

## 2026-10-29 audio/editor follow-up

Audio Reconstruct now keeps its existing calibration, dialogue preparation and take acceptance, with Record/Import voice and Change voice above those tools. Choose a source, then Simple/no AI presets or AI conversion using a target reference voice (Chatterbox) or installed RVC model/index. Processing uses the existing audio-effects service, original/result players and explicit Start. A result can become the selected dialogue-take source. Calibration is not automatic TTS voice enrollment; own reference voices still require explicit Audio Studio enrollment.

The owner's later request supersedes the shader/morph/speed-ramp deferral below: these are now implemented in Vibe Editor's approved timeline/render path, with cinematic/VHS filters. Morph is a warp/blend transition, not AI transformation. See `design/vibe-editor/PLAN.md` and its acquisition/security record. Synthetic CPU rendering and mocked UI checks pass; actual microphone and AI conversion acceptance remain owner-started.

Date: 2026-10-29. **Implemented locally; model acceptance pending.** See [implementation and verification](trellis_tts_implementation.md) for actual controls, copied artifacts, checks, limits and owner-started acceptance. The design below records the approved requirements; historical planning-only authorization language is superseded by the subsequent owner implementation request. No GPU render/training or real checkpoint deletion was started during implementation.

## 1. What the owner wants

Expose the existing ComfyUI setup through Vibe Director, reusing its runtime and model storage. Add a standalone Image to 3D studio with Single and Batch sections; launch existing AI Toolkit character/world training from the image pages; extend existing voice tools with recording and supported TTS operations. No TRELLIS fine-tuning tab or additional Z-Image training pages. Preserve image/video generation, H3/LTX chunking, screenplay, music training and their existing settings.

Use the same chat and collapsible/resizable panel experience as Video Create. Chat discusses and prepares changes; explicit Run/Start performs GPU work. Persist drafts, input/output choices, exact settings and job identity across refreshes.

Important capability distinction: the supplied TRELLIS graphs perform **image-to-mesh inference**. They do not provide a TRELLIS weight-training backend. Z-Image character/world LoRA training is a separate AI Toolkit service, and TTS training is engine-specific. The owner has dropped TRELLIS fine-tuning from scope.

## 2. Authoritative sources and copy list

Source checkout: `/home/riki/web_dev/setup_comfy_and-stuff` (abbreviated `SETUP` below). Read together:

- `SETUP/docs/VIBE_DIRECTOR_COMFY_INTEGRATION_PROMPT_2026-10-29.md`
- `SETUP/docs/vibe_director_comfy_handoff_2026-10-29/README.md`
- `SETUP/docs/vibe_director_comfy_handoff_2026-10-29/workflow-index.json`
- `SETUP/docs/vibe_director_comfy_handoff_2026-10-29/trellis-parameter-contract.json`
- `SETUP/docs/vibe_director_comfy_handoff_2026-10-29/tts-live-node-schema.json`
- `SETUP/docs/DEPENDENCY_FOLLOWUP_2026-10-29.md`

The source reports ComfyUI 0.36.0 and TTS Audio Suite 5.10.5. Its follow-up records clean AI Toolkit dependency checking, 2,760 baseline Comfy nodes and 40/46 saved API graphs passing CPU validation. These are setup evidence, **not GPU acceptance** of Vibe's adapters. Six unresolved graphs are not a reason to disable unrelated ready workflows.

| Source | Proposed Vibe destination/use |
|---|---|
| `SETUP/workflows/ricky/3d_stuff/TRELLIS2_local_1024_bounded.api.json` and `.ui.json` | Versioned `backend/story_builder/workflows/api/three_d/` executable graph, with UI original/provenance alongside reference exports |
| `SETUP/workflows/ricky/3d_stuff/TRELLIS2_local_1536_detail.api.json` and `.ui.json` | Separate detail preset; keep bounded as default |
| Bundle's parameter contract, index and relevant schema entries | Store small contracts/hash provenance beside adapters; revalidate against live `/object_info` |
| `SETUP/workflows/ricky/zimage/ZImage_Turbo_baseline.{api,ui}.json` | Compare with existing image catalog first; copy only missing required baseline/adapter artifacts |
| `SETUP/workflows/ricky/zimage/ZImage_Turbo_character_world_TEMPLATE.ui.json`, `prepare_lora_workflow.py` and README | Reference for explicit publication and inference adaptation; bypassed placeholder LoRAs are not a ready inference profile |
| `SETUP/env_setup/zimage_training/presets/` and bundle `training_presets/` | Reuse existing stopped character/world jobs and presets; copy a small configuration only if missing, without duplicating jobs or installing another Toolkit |
| `SETUP/ComfyUI/custom_nodes/TTS-Audio-Suite/example_workflows/ricky/` and bundle `tts_upstream_ui_examples/` | Compare existing Vibe graphs; adapt only missing operations into configured executable API graphs |

Recheck source hashes against `workflow-index.json` when copying. Record local modifications and node IDs. Do not copy all 35 files indiscriminately, model weights, environments, databases or caches. No new model downloads until a selected operation identifies a genuinely missing dependency.

## 3. Existing TTS integration versus additions

“Wired” below means current product UI/service/graph coverage; it does not certify successful rendering after the Comfy upgrade. This is not a release-history claim that every unused node was introduced in 5.10.5.

| Capability | Current Vibe Director evidence | Proposed action |
|---|---|---|
| Voice reference discovery/import and character assignment | `audio_catalog.py`, `CharacterVoicesPage.tsx`; bundled, TTS-user and workspace voice references | Reuse catalog and assignment; distinguish reference WAVs from trained weights |
| Timed multi-character speech using reference voices | `audio_tts.py`, `tts_multichar_timed_chatterbox_api.json`: ChatterBoxEngineNode, CharacterVoicesNode, UnifiedTTSSRTNode, SaveAudioAdvanced | Preserve; revalidate live schema and supported languages/settings |
| Existing speech → target reference voice | `audio_effects.py`, `voice_changer_api.json`: ChatterBox + UnifiedVoiceChangerNode | Extend existing Voice Changer; do not build a duplicate page |
| RVC voice/pitch conversion | `rvc_voice_api.json`: RVCEngineNode, RVCPitchOptionsNode, LoadRVCModelNode, UnifiedVoiceChangerNode | Preserve model/index selection, pitch and chunk controls; add accepted trained models to catalog |
| Emotion/style editing | `emotion_edit_api.json`, `style_edit_api.json`: StepAudioEditX engine/editor | Revalidate and preserve transcript-based editing |
| Noise cleanup / voice repair | `noise_cleanup_api.json` uses VocalRemovalNode; `voice_repair_api.json` uses VoiceFixerNode | Preserve; setup CPU dependency fixes do not establish GPU acceptance |
| Scene splitting, concatenation and timed joining | `audio_scene.py` calls suite scripts | Reuse; these are audio preparation rather than voice training |
| Dialogue reconstruction/takes | `audio_reconstruct.py` and existing Reconstruct UI | Preserve; calibration and accepted recordings are not model training |
| F5 fine-tuning | `audio_finetune.py`, `audio_catalog.py`: dataset validation, Arrow/vocab preparation and command preview only; `training_enabled=False` | Keep labelled **F5 Dataset Preparation**. Do not claim training is implemented |
| Plain text standalone TTS across additional engines | New handoff has UnifiedTTSTextNode and additional engine schemas; current timed path is fixed to ChatterBox | Add engine-aware Speech section, only enable individually verified engines |
| Voice design + saved designed voices | UnifiedVoiceDesignerNode + SaveCharacterVoiceNode in handoff; not wired in current voice services | Add Voice Design, preview then explicit save; this is inference, not fine-tuning |
| Actual model training | UnifiedModelTrainingNode and registered RVC/MOSS/DramaBox handlers in handoff; no current Vibe adapter | New Voice Training section with backend-specific datasets/settings/artifacts |
| Unified ASR / sound-effects nodes | UnifiedASRTranscribeNode, UnifiedSoundEffectsNode and engine schemas in bundle | Available extension candidates, not needed to replace existing analyzers/Control-Foley now |

The handoff also contains engines such as Qwen3 TTS, HiggsAudio/V3, VibeVoice, F5, CosyVoice, IndexTTS, Echo, Dots, FishAudioS2, OmniVoice, ChatterBox Official 23-language, Granite ASR and MOSS sound effects. Schema presence alone does not establish local weights, operation support or a passing render. Existing model discovery is not equivalent to a generation adapter for each discovered family. VibeVoice has a separately documented Transformers-4 worker profile; do not route it blindly through the primary environment.

ACE-Step music generation/training is already a separate standalone service (`ace_studio.py`/`ace_studio_runner.py`), not TTS voice training. Control-Foley is likewise a separate sound-effect integration. Preserve both.

## 4. Navigation and page composition

### Image to 3D — new Generation Assets entry

Proposed route `#/image-to-3d`, title **Image to 3D · TRELLIS.2**. Standalone operation without screenplay/mode prerequisites; optional named project links metadata, not permission to change story assets.

Reuse `EditorWorkspace` for two longitudinal panels with Hide conversation, Hide creation controls and a width slider; both can be reopened, with keyboard-accessible controls and mobile stacking.

- **Conversation panel:** shared model dropdown, `/model`, `/status`, removable image attachment chips, chat history and explicit Apply proposed settings. Discuss geometry, reference suitability and generation parameters. Dragging an image into chat attaches context; it does not silently change the generation input. An explicit Use as input action does that.
- **Creation/results panel:** Single / Batch tabs, input/output paths and chooser buttons, image preview, collapsible Parameters and Workflow details, queue/progress/cancel, and a large interactive textured GLB viewer. Orbit, zoom, fit/reset and lighting controls; download/open output folder. The result is a 3D asset, not automatically a rendered video or rigged character. Reference image remains visible beside the result when space permits.

**Single:** choose/drop one local image, choose preset/output folder, inspect preview and parameters, Run. Save exact graph/settings and descriptor, collect/validate GLB, then show viewer. **Open with Blender** appears only in Single and is enabled after a validated result. A local backend action opens a new Blender session and explicitly imports the selected GLB using a trusted import script; passing a GLB as if it were a `.blend` file is insufficient. Preserve the GLB and existing Blender sessions. Show launch errors and retain Download/Open output folder alternatives. No required text prompt: these supplied TRELLIS graphs are image-conditioned and expose no text-conditioning input. Chat can help prepare a better image using existing image tools through a separate explicit action; never send invented prompt fields to TRELLIS.

**Batch:** choose/drop an input folder, enumerate supported images recursively, show thumbnails/relative paths and select/deselect controls. Default output folder is separate. Freeze an ordered manifest on Start; one owned Comfy prompt at a time. Each row shows queued/running/validating/completed/failed, output path and timings. Collect and validate item N before N+1; retain the model within the phase only as supported by runtime policy. Stop prevents new submissions; cancellation targets owned work. Failures preserve completed items and offer explicit retry failed/resume pending, without regenerating validated items. Nested input names map to safe relative output folders or stable item IDs to avoid collisions. Never rescan newly generated files into the running manifest. Do not show Open with Blender in Batch.

### Z-Image training — existing Characters and Worlds entry points

Do not add an Image Training navigation entry or duplicate dataset/training UI. Keep the Assisted manual generation journey through Characters and Worlds. Add a **LoRA Training** button there, with a short explanation that training opens in AI Toolkit. The button starts the existing local training studio when needed, waits for readiness, and opens it in another tab. The user does not need to host or start it separately. Opening the studio never starts training; dataset preparation, settings, review and explicit training Start/Stop stay in Toolkit.

Reuse existing character/world presets. Deep-link only if the installed Toolkit supports it; otherwise open its studio and identify the appropriate preset. Do not silently edit or restart existing jobs. Provide a compact connection state and Reopen training studio/Retry action instead of a second set of trainer controls.

For **Z-Image Turbo selection only**, enable a compatible LoRA dropdown, strength control, **Refresh LoRAs** and **Import trained LoRA** action. Other image workflows retain their current behavior. The import/publish action explicitly chooses a finished checkpoint and validates compatibility before making it available to ComfyUI; do not automatically publish every intermediate checkpoint. Show trigger-token guidance and an explicit insert action rather than silently changing the prompt. Freeze the selected checkpoint identity/hash and strength in the generation request. Share the catalog with other Z-Image generation forms where supported, without requiring a training project or changing their defaults.

### Audio — extend the existing Audio Studio

Keep **Media Prep → Audio → Audio Studio** as the entry point. Preserve working forms, timed dialogue, character maps, Reconstruct, Music & Sound and Utilities. Organize new controls around three user activities rather than separate engine pages:

| Activity | User-facing controls and behavior |
|---|---|
| **Create speech** | Text or existing timed-dialogue mode; compatible engine/voice picker; Generate speech. Voice Design is a subtool with preview and explicit Save voice, not a training action. |
| **Record / Import audio** | Choose file or microphone; input meter; Record, Pause/Resume, Stop and elapsed time; playback, trim, Record again, Save/Keep and Use for… actions. Use for… offers reference voice, voice change or editor as compatible. Request microphone permission only after an explicit click. Never silently add recordings to training datasets. |
| **Change / Process audio** | One source player and Voice Change tool, with **Simple effects / AI conversion** toggle. Keep cleanup, repair and existing emotion/style tools discoverable beside it, reusing working forms. |

**Voice Change:** Simple effects shows a preset dropdown (for example deep, cartoon, robot, telephone) and only relevant pitch/strength controls; preserve duration when changing pitch where supported. AI conversion offers **Reference voice / Trained model**, with the appropriate reference attachment or model/index picker. Preserve existing RVC pitch/chunk controls and ChatterBox reference conversion. A reference WAV is not an RVC checkpoint. Each mode has Preview, Apply effect/Convert voice and Reset; changing a toggle or preset never starts processing. Short preview and full processing are distinct actions. Show original/result players with before/after comparison and Save/Send to editor; keep the source intact.

**Voice Training** remains a distinct section within Audio Studio, not another full page or a conversion mode. Use backend-specific prerequisites, dataset validation, settings review, Start/Stop, actual progress/logs/checkpoints, manually started audition and explicit publication. Start with compatible RVC; enable MOSS/DramaBox only when qualified. Their metadata formats differ; do not accept an arbitrary audio folder as universally trainable. Keep F5 Dataset Preparation honestly labelled. A **Voices & Models** section distinguishes reference recordings, designed voices and trained models, with compatible use/delete actions.

**Layout and aesthetics:** reuse Vibe Editor's two longitudinal panels, width slider and Hide/Reopen controls. Put shared chat with model picker, `/model` and `/status` in one panel; source, controls and preview in the other. Keep primary action and current state visible; collapse Advanced parameters, Workflow details and training logs independently. Avoid nested collapsibles around everyday controls. Keep result playback visible, attachments removable, selections preserved across activity switches, and record/processing states clearly labelled. Align controls, stack on narrow screens and support keyboard navigation. Reuse Record audio as a small action in editor/reference pickers rather than making users navigate away.

For editor effects, reuse installed FFmpeg filters and existing TTS conversion first; no initial Applio/Seed-VC installation or replacement of working audio controls. Proposed traditional effects attach to a selected clip with preview/apply/reset and relevant parameters, using the existing editor render path. Shader-transition integration, morphing and speed ramps are explicitly deferred to a later plan.

## 5. Storage design and present ACE-Step locations

Proposed TRELLIS defaults, created only when feature implementation needs them:

```text
local_data/trellis.2/
  input/                         # default images; originals are never modified
  output/<project-or-batch>/      # final GLB/assets; user may choose another folder
  projects/<project-id>/          # draft, selected paths, revisions and results index
  runs/<job-id>/                  # graph, input manifest, descriptors, logs, timings
  batches/<batch-id>/             # frozen ordered manifest and per-item checkpoints
  staging/<job-id>/               # temporary Comfy upload/collection, not a second library
```

External input/output folders are first-class choices. Store user-granted paths/handles and re-request access if permission expires. Browser folder drops do not provide trustworthy absolute paths: use the existing chooser/backend path-grant mechanism or explicitly upload files and record that staging location. Validate traversal/symlinks, supported extensions and output containment. Do not mirror whole external folders into a workspace. Final output has one user-chosen location; an asset record may point to it without making another permanent copy. Cleanup temporary Comfy output only after successful final copy and hash/parse validation; failed collection retains a recoverable staging result. Never delete user inputs during cleanup.

Training weights remain in existing services. Suggested Vibe metadata locations are `local_data/services/image_training/` and `local_data/services/voice_training/` (service connection/publication metadata for image training; manifests/jobs for voice training), with links to actual trainer artifact paths. Toolkit remains the owner of image datasets and training jobs; do not create a duplicate dataset store. Do not duplicate base weights into these folders.

**ACE-Step currently implemented storage**, relative to Vibe Director root:

| Location | Meaning |
|---|---|
| `local_data/services/music/state.json` | Music projects, settings, registered adapter paths and preset metadata |
| `local_data/services/music/datasets/<project-id>/...` | Validated training-song triplets |
| `local_data/services/music/runs/<job-id>/runtime.log` | Actual run log |
| `local_data/services/music/runs/<job-id>/hf_dataset/` | Converted training dataset |
| `local_data/services/music/runs/<job-id>/training/lightning_logs/<run>/checkpoints/*_lora/` | Trained LoRA checkpoint directories; adapter config and weights belong together |
| `local_data/services/music/runs/<job-id>/checkpoints/` | Links to base checkpoints, not another trained LoRA library |
| `local_data/projects/<workspace-id>/media/generated/ace_studio/<job-id>.wav` | Registered generated music |
| `local_data/ace_step/runtime/`, `local_data/engines/audio/song_gen/ACE-Step/` | Existing owned Python runtime and engine source |

Base checkpoints default to `~/.cache/ace-step/checkpoints`, overridden by `ACE_STEP_CHECKPOINTS`. Auxiliary MERT/mHuBERT snapshots use the configured Hugging Face cache. Do not treat these shared base/encoder folders as unwanted LoRAs.

Current music state registers five adapters: Action battle, Cosmic cinematic BGM, dark suspence BGM, emotional piano BGM and epic orchestral BGM. For example Action battle is registered at:

`local_data/services/music/runs/ace-studio-730c178ae2cb/training/lightning_logs/2026-10-28_20-49-00music_adapter/checkpoints/epoch=76-step=1000_lora/`

The ACE runner currently registers the latest saved `*_lora` directory after successful training; earlier checkpoint directories can remain on disk. Style description is optional metadata; training consumes each song's `_prompt.txt` tags and `_lyrics.txt`. A style name is required before starting training.

**Deleting wrong LoRAs:** there is no current ACE API/UI delete action. Do not advise deleting a directory while leaving `state.json` unchanged. Plan a Models/Checkpoints manager shared in behavior across music/image/voice training: show exact path, size, backend, current selections and running-job references. Confirm permanent deletion; block active/in-use jobs, clear affected draft selections atomically, remove registration, and delete only the confirmed owned adapter/checkpoint files. Preserve source recordings, base-model links/targets and other checkpoints. Show earlier unregistered checkpoints separately for cleanup. External/published copies must be listed explicitly; removing registration alone does not reclaim their space. Keep historical job metadata marked deleted, and report partial failures honestly. No deletion is authorized by this planning request.

**New Z-Image LoRAs:** existing AI Toolkit output root is `SETUP/env_setup/zimage_training/output/` (`/training/output` in its container). Read each job's actual files/config; never guess a checkpoint filename. Explicit publication copies a validated accepted `.safetensors` plus provenance into `SETUP/ComfyUI/models/loras/zimage/`. Its training container sees Comfy models read-only, so publication belongs to the host-side adapter. Track both paths so deleting a training checkpoint is not confused with deleting its published copy.

**New TTS trained models:** the suite writes engine-specific artifacts/progress under Comfy output `tts_audio_suite_training/<engine>/jobs/...`. Read returned training artifacts (`model_path`, RVC `index_path`, summary) as truth; publish into the compatible loader's actual catalog. Current Vibe RVC discovery expects `.pth` files in `ComfyUI/models/TTS/RVC/` and indexes in its `.index/` subdirectory. Do not put every voice checkpoint in a LoRA folder; some are full models, not LoRAs.

## 6. Backend contracts and execution

Keep configurable Comfy URL (current setup `http://127.0.0.1:3008`) and AI Toolkit URL (`http://127.0.0.1:8675`) behind backend adapters. Reuse existing durable jobs, media identities, provider guard, GPU runtime and monitoring. Do not add another controller that can bypass shared ownership.

### TRELLIS adapter

Validate required node classes/models via live `/object_info`; stage uniquely named input through `/upload/image`; submit executable API graph through `/prompt`; save prompt ID before polling history/websocket. Collect output from node **322** `Save3DAdvanced`: its history `3d` descriptor array, with filename/subfolder/type. The `result` path is not base64. Validate the generated GLB and any companion assets before marking completed. Serve it through a bounded content endpoint; avoid arbitrary filesystem reads or remote GLB dependencies.

Expose only supported controls, preserving graph wiring:

| Input | Node/input | Bounded default / detail default |
|---|---|---|
| Input image | `122.image` | unique staged filename |
| Structure seed/steps/CFG | `3.seed/steps/cfg` | 56 / 12 / 7.5 |
| Shape seed/steps/CFG | `18.seed/steps/cfg` | 42 / 20 / 7.5 |
| Upsample seed/steps/CFG | `23.seed/steps/cfg` | 42 / 12 / 7.5 |
| Texture seed/steps/CFG | `12.seed/steps/cfg` | 43 / 12 / 1 |
| Voxel target | `94.target_resolution` | 1024 / 1536 |
| Texture pixels | `288.value` | 1024 / 4096 |
| Face target | `186.target_face_count` | 100000 / 700000 |
| Remesh | `241.resolution` | 256 / 768 |
| Save prefix | `322.filename_prefix` | unique job/item prefix |

`322.width/height` are viewer dimensions (1024), not mesh resolution. Parameter validation must follow the copied contract and live schema. Detail remains explicitly unaccepted until an owner-run test establishes memory/time/quality.

### AI Toolkit launcher and LoRA publication adapter

Reuse `SETUP/env_setup/zimage_training/README.md` and the existing installation/container. The fixed launch command, run from the configured SETUP checkout, is:

```bash
docker compose -f docker-compose.yml -f docker-compose.training.yml --profile training up -d --no-build zimage-training
```

The existing service has restart policy `no`; Comfy startup alone does not start it. A narrow backend POST launch action checks current health, starts that fixed service only if necessary, then polls the configured studio URL for readiness. Serialize concurrent launch requests, use bounded startup/retry status, and do not report ready merely because the launch command returned. Never accept shell commands, arbitrary Compose files or service names from browser input. Reuse an authorized host launcher; lack of Docker access must produce an actionable error, not silent privilege changes or dependency installation.

On the user click, synchronously open a placeholder tab to avoid popup blocking, then navigate it when ready. Show **Starting training studio…**, progress/error and Retry in Vibe. Repeated clicks reuse the pending launch/tab where possible; an already healthy service opens immediately. If browser policy blocks opening, show an explicit Open training studio link. This starts the service on Vibe's configured local host; it does not install or start software on an unrelated browser computer.

Opening the web UI must not queue, resume or start training, including existing stopped character/world jobs. Confirm that startup leaves training queues stopped before qualifying this integration. Do not stop the service when its tab closes: training may still be active. Any future Stop studio action requires explicit intent and verified idle queues/processes. No runtime/service action is authorized by this plan update.

Toolkit owns dataset/caption editing, jobs, losses, previews and training controls. Its `/api/jobs/<id>/start` and `/api/queue/0/start` are distinct; account for both when inspecting active work, but do not rebuild those controls in Vibe. Monitor upstream state read-only as needed for shared GPU preflight. Opening an idle studio does not require claiming the GPU. Direct training from its UI can bypass Vibe's lock: qualify shared scheduling or add an upstream launch guard before claiming global enforcement. Never stop unrelated work to open the studio.

Vibe's publication action reads actual completed checkpoints, translates `/training/output` to the configured host output root, validates Z-Image compatibility and explicitly publishes the selected file to the existing Comfy catalog. Record original/published paths and hashes; refresh the LoRA picker without resubmitting training. Mutation endpoints must be explicit POST actions and cannot be prefetched. No duplicate installation, model download, preset job or automatic training on click.

### TTS adapters

Reference speech cloning, voice design, speech conversion and weight training are distinct operations. Configure a real engine-specific API graph, not an upstream UI JSON. UnifiedModelTrainingNode must connect to a registered output sink or Comfy may not execute it. Poll suite `/api/tts-audio-suite/training-progress?node_id=...` alongside owned Comfy history; handle returned `nodes` map and persisted progress files. Respect resume/warm-start semantics and explicit overwrite choice. No assumed per-job suite stop API: verify cancellation support in the selected handler; global Comfy interrupt is allowed only for owned running work.

### Shared scheduling/recovery

One heavy owned job across Comfy video/image/3D/audio and external AI Toolkit training. External direct UI submissions can bypass Vibe's lock, so preflight live queues/processes and show a conflict rather than claim absolute exclusivity. Never clear or stop unrelated work. On phase change release models only while owned queue is idle; confirm actual completion/memory state with bounded polling and visible recovery instead of treating one timeout as successful unloading. A monitoring read timeout is not proof of OOM; genuine workload failures remain visible. Maintain current 90°C cutoff and 2100 MHz policy; do not alter clocks or modify the H3 pipeline in this work.

## 7. Smallest implementation sequence and acceptance

1. Inventory/hash selected artifacts and current live schemas; trace shared layout/jobs/catalog seams in source and Graphify. Record per-operation installed/registered/graph-valid/GPU-accepted states. No installation by default.
2. Implement Image to 3D Single, folder paths, durable job and GLB viewer with existing shared controls. CPU/API fixtures cover input staging → graph mutation → output descriptor → validated collected asset, and reconnect without duplicate submission.
3. Add frozen-manifest sequential Batch, stop/resume/failed-item recovery and collision-safe paths. Verify two mock items cannot submit concurrently or advance before validated output.
4. Add the fixed AI Toolkit service launcher and Characters/Worlds training links. Test stopped/starting/healthy/failed service states, repeated clicks, popup blocking and stopped queues without starting training. Add explicit checkpoint publication and Z-Image-only LoRA selection; test compatibility, path mapping and frozen generation settings.
5. Add Single-only Open with Blender using validated owned results and a trusted GLB import script. Test disabled/no-result and launch-error states without modifying existing scenes.
6. Preserve existing Audio Studio behavior while grouping activities. Add microphone recording/import, removable source, playback/trim and use/save actions; verify permission denial, stop/re-record and source preservation. Revalidate TTS graphs; add qualified standalone speech/design/training incrementally, retaining F5 preparation scope.
7. Add checkpoint management/delete confirmation and active-job dependency checks for ACE, Toolkit and voice artifacts. Show real disk paths and training vs published copies; never delete originals/base models.
8. Type/build checks, focused mocked producer-to-consumer/recovery checks, then live browser layout/interaction inspection. Check aligned controls, nonoverlapping galleries, both collapsed panels reopening, keyboard navigation and narrow screens. Refresh Graphify after meaningful code changes.
9. Prepare owner-clicked GPU acceptance separately: one bounded TRELLIS image/view/download/Blender import, two-image batch and reconnect, short Toolkit training/checkpoint publication and Z-Image audition, short voice conversion and backend-specific training/audition. Record actual memory/timing/output quality; CPU graph validation is not successful inference or training. Opening the training studio is not permission to start these tests.

### Settled scope and deferred work

- TRELLIS is Single/Batch image-to-3D only; Open with Blender is Single-only. No Fine-tuning tab.
- Training uses the existing AI Toolkit website, automatically started/opened from Characters/Worlds; no new Vibe training pages. LoRA inference controls are enabled only for compatible Z-Image workflows.
- Initial 3D output is textured GLB. Rendered turntables, rigging and animation remain later features.
- Shader transitions, morphing and speed ramps remain deferred; no packages are installed for them in this scope.
- Folder structure above is proposed; existing ACE/trainer data stays in place. No migration or deletion is implied.

No outstanding product clarification blocks this plan. Launcher permissions, startup queue behavior, Blender import and per-engine support are implementation checks, not assumed successes. Existing runtimes and saved workflows remain unchanged.
