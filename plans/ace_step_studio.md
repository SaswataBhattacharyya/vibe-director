# ACE-Step Music Studio

## Execution update — direct controls and conversational preparation

**Status: implemented and activated; owner-clicked generation/training acceptance pending.** This section supersedes the earlier
four-tab layout and button placement where they conflict. Keep the existing
standalone engine, queue, saved projects, themes and GPU safeguards. Reuse the
copied ACE-Step reference/edit code rather than implementing a music engine.

### One request, two ways to prepare it

- Centre conversation and right-pane controls edit the same saved project draft:
  task, reference asset, prompt, lyrics, style/LoRA and parameters. A visible saved
  revision is the source of truth; no separate hidden chat request.
- Users can work entirely through direct controls, entirely through chat, or mix
  them. Direct generation/training must not require an LLM call.
- Chat supports audio attachment via chooser, drag/drop and clipboard files when
  the browser supplies actual files. Pasted lyrics remain visible in the chat;
  the assistant extracts them into the editable Lyrics field. Ambiguous quoted
  lyrics or multiple possible reference files require clarification rather than
  silently replacing a field. Plain attachment upload alone does not call an LLM.
- Direct controls are locked while a chat job runs, preventing concurrent field
  edits from being overwritten. Backend jobs remain revision-bound and reject
  stale results; unsent field edits and attachments persist across navigation. An attachment is not automatically a training
  example; training requires the dataset format below.
- Chat prepares and explains. The right-pane **Run** or **Start fine-tuning**
  button explicitly submits the displayed settings. These clicks are the final
  confirmation; do not require a separate conversation confirmation for a direct
  run. Never start generation/training from an ordinary chat message or upload.

### Right pane

Tabs: **Create**, **Fine-tune**, **Styles**, **Audio & models**, **Connection**.
Keep controls usable without creating a conversational brief. Create/open a
saved music project for persistent work; no model job starts when it is created.

**Create**

1. Compact capabilities/help area explains each mode, required inputs and what
   remains editable. Distinguish available engine features from wired features;
   label unsupported features honestly rather than displaying enabled controls.
2. Mode: Text to music; Reference music (audio-to-audio); Remix; Change lyrics.
   Text to music requires a description and song lyrics or Instrumental.
   Reference mode requires an uploaded/library recording, description and new
   lyrics or Instrumental; reference strength controls adherence.
   Remix/Change lyrics use the copied editing adapter's actual source/original
   lyrics, target lyrics/tags and parameter requirements. Inspect its signatures
   before wiring; lyric-only editing attempts to preserve melody and is not a
   guarantee of perfect preservation. Explain requirements beside each mode.
3. Reference audio dropzone + Choose file + library picker, filename, playback,
   replace/remove. Accept actual clipboard audio files where supported; do not
   promise arbitrary OS clipboard audio can always be read by a web page.
4. Style dropdown grouped as Built-in presets / Saved prompt presets / Trained
   LoRAs, with Base model available. Reuse the donor's ten genre presets.
   A preset fills editable tags; a trained style selects its adapter and can also
   supply saved descriptive tags. Explain which is selected. One LoRA per run
   initially; do not imply LoRA stacking is supported.
5. Editable music prompt and separate, generously sized Lyrics paste area;
   Instrumental makes the absence of sung lyrics explicit. Existing direct
   duration, seed, guidance, steps and scheduler remain. Reference/edit controls
   appear only for relevant modes. Chat can fill these exact fields.
6. **Run** saves/validates the displayed request and queues the exact revision.
   Incomplete inputs show field-specific explanations. Duplicate clicks cannot
   create duplicate jobs. Keep inputs intact after success/error/stop for retakes.

**Fine-tune**

1. Style name, short description and optional preview tags; explicit music LoRA
   explanation. Training produces an adapter, not another base model. A genre
   prompt does not need training. Multiple named training runs can produce
   multiple LoRA files; one LoRA may represent more than one musical trait.
2. Exact visible dataset format and example triplet from the section below.
   Every song needs MP3 **and both** prompt/tags and lyrics text. Instrumental
   recordings still need a lyrics file containing `[instrumental]`. Do not
   silently interpret the owner's “lyrics or tags” as permission to omit either
   file required by the copied converter.
3. Drag/drop a folder, Choose folder and Choose files fallback. Traverse folder
   contents, pair triplets by relative directory plus stem, and preserve that
   identity while copying into an owned safe dataset. The browser supplies files,
   not host filesystem paths; the backend never follows uploaded folder paths. Reject path escape,
   duplicate identities, missing partners and unsupported recordings; never
   flatten two same-named songs into one. Show a review table, song count,
   durations and per-file errors before permitting training. Source folder is
   never modified. Explain browser folder-drop support/fallback locally.
4. Existing rank, learning rate, steps and checkpoint cadence remain directly
   editable, with defaults and clear compute/time guidance without invented ETA.
5. **Start fine-tuning** validates the named style, dataset and parameters, then
   explicitly starts that exact revision. No LLM call is required.
6. On successful validated training, register the chosen completed adapter as a
   named **Trained LoRA** in the shared studio Styles catalogue and dropdowns,
   available across music projects. Keep stable IDs/version, base-model identity,
   dataset/training provenance and weight path. Internal checkpoint files do not
   each become separate catalogue styles. Failed/stopped runs cannot publish an
   unfinished style as ready. Preserve earlier style versions and recordings.

**Styles** displays the ten built-in presets (Modern Pop, Rock, Hip Hop, Country,
EDM, Reggae, Classical, Jazz, Metal, R&B), saved editable prompt presets, and
trained LoRAs with name/description/readiness. Select applies to the current
draft without starting a job. No fixed list limits what the base model can be
asked to generate. Existing project-local LoRAs need catalogue migration without
moving/deleting their weight files.

### Feedback and persistence

Buttons show immediate pressed/pending feedback, disable duplicate submission
and retain readable text/focus. Respect reduced-motion preferences. Use durable
job status for Waiting for GPU / Preparing / Generating or Training / Saving /
Complete / Failed / Stopped. Show progress bar and actual inference/training step
counts when supplied by the reused engine; otherwise an indeterminate bar with
the actual stage. Elapsed-time display is not implemented. Do not simulate percentage or claim a queued job is
generating. Stop, errors and retry remain accessible. Persist request, reference
IDs, lyrics, style selection and job identity across navigation/reload. Completed
audio has playback/download and shared-library identity in Audio & models.

### Implementation order and bounded verification

1. Add shared preset/LoRA catalogue and direct Create controls; retain current
   text generation. Add reference upload/library attachment and wire the copied
   audio-to-audio/edit paths with validated, revision-frozen asset IDs.
2. Connect chat audio/lyrics to the same fields, including stale-response safety.
3. Add folder ingestion/review, named training and successful catalogue publish.
4. Connect real progress events and small button feedback; inspect the composed
   page once. Update capability/help text to match actual working modes.

Reuse `AceStudioPage`, studio API/runner, shared uploads/library/queue and donor
components. No new model downloads, backend controller, Git or subagents for this
slice. Focused checks only for new branches: attachment/task requirements,
revision/duplicate protection, folder collisions, successful-only publication,
mode argument mapping and chat/direct synchronization. Owner clicks real Run
and Start fine-tuning acceptance tests; prepare short inputs and visible GPU
monitoring first. Do not rerun unchanged passing suites or invoke routine Sol
reviews for each small change. Detailed implementation is pending owner approval
of this plan; no generation or training is authorized by this planning request.

## Owner journey

Open **Media Prep → Audio tools → Music & Sound → ACE-Step Music**.

The existing navigation is the left pane. The centre is the conversation. The
right pane uses Vibe Editor's layout and the current theme, with four tabs:

- **Settings:** song/instrumental, editable prompt and lyrics, duration, seed,
  inference steps, guidance, scheduler and a previously trained music LoRA.
  Switch Task to training to see training steps, learning rate, save interval
  and LoRA rank.
- **Training files:** the exact dataset format, multi-file upload and validated
  song list.
- **Audio & models:** generated recordings with playback/download, and saved
  music LoRAs. Songs also enter the shared Audio Clips library. LoRAs are
  selectable in subsequent generation requests.
- **Connection:** standalone engine requirements, installed locations and logs.

Create/open a music project, describe the request, answer any questions, review
the draft and settings, then click **Confirm & generate music** or
**Confirm & train LoRA**. Chat prepares the request and never starts either job.
The app's selected Director provider/model is used; initial acceptance is Codex.
It can draft/change lyrics and parameters. Direct manual parameter entry is also
supported without a chat call. Settings have a Save button; messages, settings,
datasets, output identities and confirmations persist locally. Unsent composer
text is not a saved message.

After submission, the same revision cannot be submitted twice. **Prepare another
take** preserves its settings and requires another explicit confirmation. Stop
cancels the owned worker process group. A changed revision or cancelled job cannot
attach a late response/output to the current project.

## Exact training format

Select every matching triplet together (flat filenames):

```text
song_001.mp3
song_001_prompt.txt
song_001_lyrics.txt
song_002.mp3
song_002_prompt.txt
song_002_lyrics.txt
```

Example `song_001_prompt.txt`, UTF-8:

```text
acoustic pop, warm, fingerpicked guitar, gentle percussion, 90 bpm, soft vocals
```

Example `song_001_lyrics.txt`, UTF-8, containing the actual sung words:

```text
[verse]
Morning light across the floor
I hear your footsteps at the door
[chorus]
Stay until the daylight fades
```

For an instrumental recording, use `[instrumental]` in its lyrics file.
Stems use letters/numbers/underscore/hyphen, maximum 80 characters. Prompts are
limited to 4,000 characters and lyrics to 10,000. Recordings must be decodable,
nonempty MP3 audio up to 240 seconds. Convert WAV/FLAC using Audio Utilities first.
Each upload accepts 1–500 triplets. Files without partners, duplicate/invalid
stems, unsupported recordings and empty text are rejected. Backend validates
every song before making its owned dataset copy. Original uploads remain in the
library if later validation fails, so no source media is deleted.

This trains a **music LoRA**, not a TTS voice model. The base model is retained.
Use recordings you have permission to train on. This does not guarantee the
quality or identity accuracy of the resulting adapter.

## Reuse and execution

Donor: `mooV_E_maker` / Story Builder's `audio/song_gen/ACE-Step`, copied into
ignored `local_data/donor_migration/audio/song_gen/ACE-Step`.

Reused engine: `acestep/pipeline_ace_step.py`; dataset converter:
`convert2hf_dataset.py`; training: `trainer.py`; LoRA target configuration:
`config/zh_rap_lora_config.json`. No new music model/training algorithm.

Vibe adapters: `ace_studio.py`, `ace_studio_api.py`, `ace_studio_runner.py`.
Jobs use the existing `video_repertoire` queue under kind `ace-studio`. Chat and
dataset conversion are CPU/provider operations. Model execution alone owns the
shared GPU guard, waits for ComfyUI to be idle and releases its idle models.
Existing temperature/clock/fault monitoring remains in force. ACE-Step submits
no ComfyUI graph. Control-Foley remains its existing ComfyUI tool.

Generation maps standalone `prompt`, `lyrics`, `audio_duration`, `infer_step`,
`guidance_scale`, `scheduler_type`, `manual_seeds`, `lora_name_or_path` and
`save_path`. These are not the old Comfy graph's shift/lyrics-strength controls.
Training uses one GPU/process, batch size 1, BF16, no loader subprocesses,
configured max steps and checkpoint interval. The converter runs once per song;
the trainer repeats epochs until max steps. Preview generation during training
is disabled for this initial adapter. The copied trainer is adapted in its
job-local directory: use single-process Lightning and remove the donor fallback
which edits a shared Hugging Face cache blob. Its MERT compatibility correction
is applied to the in-memory config instead. Donor source is preserved.

Legacy ACE Comfy POSTs return a migration message requiring standalone studio
confirmation. Historical job records remain readable. A missing standalone
bundle must never be described as a missing Comfy workflow.

## Runtime setup and reproducibility

The separate ignored Python environment is
`local_data/ace_step/runtime/bin/python`. It inherits CUDA PyTorch from the
existing `react` environment; dependency overrides stay in the owned environment.
It does not modify shared `react` packages or the ComfyUI installation.

Installed adapter compatibility versions: diffusers 0.33.1, transformers 4.50.0,
Lightning 2.5.1, py3langid 0.3.0, num2words 0.5.14, hangul-romanize 0.1.0,
plus cutlet/fugashi/unidic-lite and their dependencies. This environment still
depends on the retained `react` CUDA installation; it is not a portable bundle.

Base bundle: `ACE-Step/ACE-Step-v1-3.5B`, revision
`82cd0d7b6322bd28cd4e830fe675ddb6180ce36c`, approximately 8.28 GB for the required
four component directories. Default location: `~/.cache/ace-step/checkpoints`.
The existing single ComfyUI checkpoint is a different format.

Training additionally caches `m-a-p/MERT-v1-330M` and
`utter-project/mHuBERT-147` in the Hugging Face hub cache. Training uses those
encoders as well as the base bundle; it does not train TTS voices. Inference
and training run offline after setup, so missing models produce a failure rather
than downloading unpredictably inside a GPU job.

Pinned training encoder revisions are `5240c2708a5acaee1007f43fb9735c7dcd0b78c9`
(MERT) and `7ad3fc0bc5106c58c9c13526abccad527150d135` (mHuBERT). The trainer
loads those local snapshots directly. Only required weights/configuration/code
are downloaded; fairseq archives, FAISS indexes and duplicate weights are excluded.
The two encoder weights total approximately 1.64 GB.

Resume/reproduce the model downloads, without running generation or training:

```bash
cd '/home/riki/Documents/ChatGPT/Vibe Director'
/home/riki/miniforge3/envs/react/bin/python -u tools/download_ace_models.py
```

To recreate the isolated runtime, use the existing CUDA Python with
`python -m venv --system-site-packages local_data/ace_step/runtime`, then run
its `bin/python -m pip install` for `diffusers==0.33.1 transformers==4.50.0
pytorch-lightning==2.5.1 py3langid==0.3.0 num2words==0.5.14
hangul-romanize==0.1.0 cutlet==0.5.2 fugashi==1.5.2 unidic-lite==1.0.8
mojimoji==0.0.13`. The retained CUDA environment supplies the other packages;
Connection lists missing requirements if that environment differs.

Optional launcher overrides, exported before starting the website:

```bash
export ACE_STEP_SOURCE="/absolute/path/to/ACE-Step"
export ACE_STEP_PYTHON="/absolute/path/to/runtime/bin/python"
export ACE_STEP_CHECKPOINTS="$HOME/.cache/ace-step/checkpoints"
```

Restart the API after changing its environment. The shared dispatcher must
inherit the same overrides; defaults are automatically detected in this checkout.
Connection checks prove file/dependency presence, not model quality or a completed
GPU render. Logs and actual job outcomes remain authoritative.

## Acceptance

CPU/mock checks cover revision-bound confirmation, no generation from chat,
strict datasets, parameters, standalone inference argument mapping, job-local
trainer adaptation, audio registration and HTTP routing. Mocked UI checks must
be recorded separately from actual output acceptance.

Owner clicks Send for a real Codex conversation, reviews a short 5–10 second
instrumental, then explicitly confirms generation. Inspect playback and shared
Audio Clips. For training, upload a small valid dataset and explicitly confirm a
small step count, then select the resulting LoRA in a later generation. Real
training/inference, quality and cancellation during a GPU job are pending owner
acceptance until those runs happen. No synthetic passing test replaces them.


## Generated audio collection — 2026-10-27

Audio & models lists all registered standalone ACE-Step audio across music projects,
not just the latest job. Newest-first pages, search, playback, downloads and explicit
refresh reuse the shared catalogue. Select/Deselect all affects only shown items;
other page/filter selections remain selected. Delete selected always asks for
confirmation and identifies known music projects which generated/selected the audio.
It also warns that other saved projects may use it. Deletion uses the existing
archive operation: hide from pickers, retain original bytes and saved playback,
and provide Undo. It is not disk cleanup; archived entries can also be restored
from the media library. Other project usage is not exhaustively enumerated.

Compatible shared source pickers include **ACE-Step generated audio** (audio only),
identified by saved engine provenance, across workspace boundaries. The broader
Generated/projects source still includes these tracks. Add remains explicit;
no generation or voice enrollment starts from browsing/selection.
