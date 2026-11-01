# TRELLIS, Z-Image LoRA and Audio Studio implementation

Date: 2026-10-29. Implements the owner-approved `trellis_tts.md` scope locally. Actual model rendering/training acceptance remains owner-started; no GPU render, training run, checkpoint deletion, Toolkit startup or Blender launch was performed in this implementation turn.

## Where to use it

| Entry | Available controls |
|---|---|
| Generation Assets → Image to 3D (`#/image-to-3d`) | Single/Batch, image or recursive folder upload/drop, selection, output folder, bounded/detail presets, collapsed parameters/workflow, durable progress/reconciliation, textured GLB preview/download, Single-only Open with Blender |
| Characters / Worlds → Z-Image LoRA | LoRA Training starts the existing AI Toolkit service if needed and opens a ready tab; refresh/import accepted checkpoint, compatible LoRA picker, strength and explicit trigger insertion |
| Text to Image → Z Image | Same compatible published LoRA selection; Qwen profiles do not receive a Z-Image LoRA |
| Media Prep → Audio → Audio Studio | Shared collapsible/resizable conversation and controls; microphone/import/trim, standalone ChatterBox speech, Qwen3 voice design, existing timed dialogue and conversion, Simple/AI voice processing, RVC training, checkpoint manager |

The primary training button opens a placeholder tab immediately and navigates after service readiness. Opening the training website never queues or starts a training job. Dataset editing and explicit training Start/Stop remain in the installed AI Toolkit. The Reopen link is a convenience for an already running studio. No additional image-training pages were added.

The default TRELLIS directory is `local_data/trellis.2/`: `input/` contains normalized uploaded copies; `output/<job-id>/<item>.glb` contains validated finals; `batches/<job-id>.json` freezes item order/state; `runs/<job-id>/` contains exact per-item graphs and Blender scripts; `projects/` stores chosen output-folder grants; `staging/` holds temporary collection files. Originals in user folders are preserved. An external output folder is used after explicit confirmation. Browser drafts/chat use local storage; durable job state uses the existing execution service. Inputs are browser-selected/uploaded rather than arbitrary backend folder scans.

## Execution and integrity

- Both TRELLIS API graphs, their UI originals and parameter contract were copied unchanged from the setup checkout, with source paths and SHA256 recorded in `backend/story_builder/workflows/api/three_d/provenance.json`. Runtime mutates only the configured inputs; no model/environment copy.
- TRELLIS and new voice jobs reuse the shared durable dispatcher, GPU workload guard and owned cancellation/recovery. Batch item N+1 cannot submit until N has a collected, validated GLB. Prompt identity and executable graph are persisted before submission. Uncertain submission reconciles existing history rather than blindly resubmitting.
- GLBs are checked for version/structure, contained resources and content hash before preview/download/Blender. Collected finals are saved atomically. An owned Comfy result is removed only after a verified final copy; cleanup failures remain visible. Other user outputs are not removed.
- Z-Image publication reads real stopped/completed Toolkit job configuration and checkpoint files. Only proven Turbo character/world LoRAs are accepted. Publication copies the selected file and provenance to the existing Comfy catalog; inference freezes identity/hash/strength and revalidates before use.
- Voice training is explicit, dataset-selected and confirmed. RVC uses the suite's returned artifact paths rather than invented filenames. MOSS/DramaBox training stays disabled pending qualification. F5 remains dataset preparation, not claimed training.
- Simple voice effects execute through existing FFmpeg on CPU. Short preview and full application remain distinct. Source recordings are preserved, and recording/import never enrolls a training dataset automatically.
- Checkpoint deletion requires confirmation, current ownership/hash and idle workload checks. Published copies and training checkpoints are separate entries. ACE adapter registration/selection is cleared under its state lock; datasets and base weights are excluded. Historical deletions are recorded. Stale Z-Image selections fail hash/catalog validation and require refreshing the picker.

## Actual storage

- Toolkit training checkpoints: `/home/riki/web_dev/setup_comfy_and-stuff/env_setup/zimage_training/output/`, selected using the real job configuration.
- Published Z-Image LoRAs: `/home/riki/web_dev/setup_comfy_and-stuff/ComfyUI/models/loras/zimage/`.
- RVC: actual returned `.pth`/`.index` artifacts in the installed `ComfyUI/models/TTS/RVC/` catalog; voice job metadata under the existing shared jobs root.
- ACE-Step: existing `local_data/services/music/runs/ace-studio-*/training/lightning_logs/*/checkpoints/*_lora` directories and music state remain in place. No migration.

## Verification

- Frontend TypeScript/Vite production build: PASS. Existing large-bundle advisory remains.
- 68 focused backend tests: PASS, including sequential batch gating, invalid-output blocking, uncertain-job reconciliation, GLB/parameter validation, LoRA hash changes, safe training configuration/artifacts, CPU effect duration/state, healthy Toolkit reuse, saved active-queue launch rejection and checkpoint confirmation/hash rejection. Fake media/artifacts only.
- Isolated Playwright: 2 tests PASS. Checked recursive folder selection, explicit batch start, recovery controls without duplicate submission, removable chat attachments, both panel collapse/reopen controls, narrow-screen overflow, explicit microphone permission failure, disabled training with no selected dataset and disabled unavailable voice design.
- Desktop/narrow TRELLIS screenshots and Audio Studio screenshot visually inspected. Mocked browser tests establish interaction behavior, not successful model execution or real microphone hardware capture.
- Live read-only checks after reload: TRELLIS state and training/LoRA/checkpoint/voice capability endpoints respond. Both TRELLIS graph presets and new voice graph shapes were checked against installed Comfy schemas. Five copied graph/contract hashes match their source.
- Graphify code-only refresh: PASS (576 nodes / 1,837 edges at the recorded refresh). It indexes code rather than plans/workflow JSON.
- Playwright MCP could not initialize because its browser profile was already in use. Isolated Playwright CLI supplied the browser checks without closing the owner's browser.

The existing backend and image worker were reloaded only after confirming queues were idle. Backend PID 2085461; image worker PID 2085513. Video worker PID 905650 was left untouched. Reload log: `local_data/logs/studio-integration-reload.log`. No H3 pipeline change or job submission.

## Remaining qualification and limits

1. Owner-started bounded TRELLIS render/view/download and Single Blender import, followed by two-image batch/reload acceptance. The detail preset needs separate memory/time/quality qualification.
2. Click LoRA Training to qualify stopped-service startup/popup behavior; explicitly start a small training job in Toolkit, publish its checkpoint, then manually generate a Z-Image audition. No existing training job was started or modified for these checks.
3. Record real microphone audio, trim/save/use it; manually audition speech, voice design and conversion. Run a small confirmed RVC training/audition before considering it model-qualified. Available capabilities mean installed schema/config support, not a passing render.
4. Exercise checkpoint deletion on a deliberately disposable trained artifact. Current verification covers rejection/ownership paths without deleting real models.
5. AI Toolkit's direct website has its own scheduler. Vibe checks active Toolkit work before the new GPU operations and image inference, but a user can still start Toolkit training after Vibe's preflight. Global enforcement against that external race is not qualified. Do not start direct Toolkit training during another render.
6. Studio chat receives filenames/settings and conversation text, not image pixels; its UI states this. Chat does not start generation and settings suggestions require Apply. Visual reference analysis through this chat is not claimed.
7. Microphone capture requires browser permission and a supported secure browser context. Native folder opening and Blender require a desktop session and the installed executables; failures retain download/manual-path alternatives.
8. Dependency audit reports three existing frontend toolchain advisories (postcss-selector-parser, source-map-js and Vite). No broad toolchain upgrade or new AI runtime/model installation was included.

Deferred by agreement: TRELLIS fine-tuning, additional Z-Image training pages, Applio/Seed-VC, shader transitions, morphing and speed ramps. Working story/video/music paths were preserved.
