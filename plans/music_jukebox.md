# Music Jukebox — implementation plan and scope

Date: 2026-10-30. Status: initial workstation implemented. Owner authorized implementation and required dependencies. See [implementation, usage, checks and remaining boundaries](music_jukebox_implementation.md). The design below remains the broader roadmap; unimplemented refinements are explicitly listed in the implementation report.

## 1. Placement and user journey

Media Prep → Audio tools → Music & Sound has sibling tabs:
**ACE-Step Music | Music Jukebox | Control-Foley**.
Keep ACE-Step generation, training, styles and saved projects unchanged. Music Jukebox is a separate named editing/composition project, optionally linked to a workspace or Vibe Editor project; it requires neither a screenplay nor AI generation.

1. Create/open a named Jukebox project; choose project and export folders.
2. Import files/folders, select existing media, record audio, bring in an ACE-Step result, or start with an empty beat/melody.
3. Edit/arrange, compose patterns, or mix two decks. These are views of one project rather than disconnected tools.
4. Audition, undo changes, save/reopen, then export the mix or individual track stems. Send an explicitly chosen rendered result to Vibe Editor.

Add **Open in Music Jukebox** to an ACE-Step result without moving/deleting it. The reverse shortcut **Generate with ACE-Step** opens the existing generator; it never silently queues a GPU job. Returning lets the user choose the generated result for import.

## 2. Layout and controls

Reuse the app themes, spacing, shared Director model picker, `/status`, media picker and collapsible pane/width controls. Avoid six permanently open panels.

- **Left pane:** collapsible Director conversation and media/sample browser. Drag media onto tracks or attach it to chat; attachments are removable.
- **Main pane:** Edit & Arrange / Compose & Beats / DJ Mix views.
- **Bottom/side inspector:** selected clip, instrument or channel settings; Mixer and optional video preview collapse independently.
- **Shared transport:** play/pause, stop, seek, loop range, elapsed/bar position, BPM, time signature, metronome, count-in, snap and zoom. Microphone recording and DJ-performance capture have distinct labelled buttons.
- **Project toolbar:** new/open/save/save as, unsaved indicator, undo/redo and export. Export opens a folder picker and format/options dialog; collisions need overwrite confirmation or a new name.
- Hover help explains musical terms in plain language. Controls have accessible labels and keyboard equivalents, not hover-only instructions.

### Edit & Arrange — Audacity-style work

Stacked waveform tracks with a time/bar ruler, playhead, horizontal/vertical scrolling and adjustable track heights. Waveform rows never shrink into overlapping cards. Select a time range or clip, then:

- Split at playhead, trim edges, cut/copy/paste, duplicate, move and delete selected content.
- Explicit **Ripple delete / Leave gap**; paste at the playhead or chosen track; grid snap can be disabled for precise speech edits.
- Increase/decrease amplitude with a gain control in dB, channel volume/pan, mute/solo and peak/clipping meters.
- Fade in/out, silence selected range, reverse, normalize, EQ, compression, limiter, echo/reverb, tempo and pitch controls. Destructive-sounding commands create editable operations/derived clips; originals remain intact.
- Preview selected range, bypass/reset an effect, compare before/after; selected-channel effects and master effects are clearly distinguished.
- Adjustable volume/pan automation points; repeated loops can be placed and resized without copying the source file repeatedly.
- Reuse the existing microphone recorder and imports. Browser recording needs permission and must never start by opening the page.

Normalize raises the level to a chosen target; it cannot recover clipped audio. Gain can clip: show meters and offer a visible limiter option rather than silently changing the sound.

### Compose & Beats

- Beat maker: kick/snare/hat/sample lanes, step grid, pattern length, swing, per-step velocity and pattern duplication.
- Piano roll: add/move/resize/delete notes, velocity, keyboard audition, quantize, copy/paste and loop. MIDI import/export carries notes, tempo and supported controls; MIDI does not contain instrument audio.
- Instruments: synth/bass/drums first, plus sampler slots for user-chosen sounds. Piano/guitar presets require suitable licensed sample banks; do not label a generic synth as a realistic guitar or download sample packs without review.
- Patterns become clips on the shared arrangement timeline. Instrument/effect choices are saved with the project and included when rendering stems.

### DJ Mix

- Two decks A/B with waveform, load track, play/pause, cue, seek, gain, three-band EQ, pitch/tempo, key-lock where supported, and beat-length loop controls.
- Crossfader with clear A/B endpoints and curve selection; channel/master meters, master limiter and headphones/cue preview where the browser/audio device supports routing. Show routing limits instead of pretending a single output is independent headphone cueing.
- Manual BPM, tap tempo and beat-grid adjustment first; optional analysis suggests BPM/first beat and remains editable. Sync needs a valid grid and user choice of master deck; variable-tempo songs may need manual correction.
- **Capture mix performance** records deck/crossfader/EQ/loop events into the project, rather than recording low-quality system sound. Replay and export the same saved performance. Distinguish track trim, deck tempo and key/pitch changes.

## 3. Prompt editing and approvals

Examples: “Make an eight-bar house beat at 124 BPM”, “Cut the silence and raise this voice by 3 dB”, “Crossfade into track B over eight bars”. The Director explains its proposed instruments, regions, tempo and changes using familiar editing terms.

Reuse Vibe Editor's interpretation → explicit brief approval → concrete media/tool approval for chat-driven edits. A proposal names the tracks/ranges, effects and generated patterns; questions/unsupported operations cannot masquerade as completed edits. Apply creates one undoable project revision. Direct manual controls are immediately auditionable/undoable and do not need two confirmations for every fader movement. A prompt cannot delete source files, overwrite an export, launch ACE-Step or train a model without the existing explicit action/approval.

## 4. Existing services and actual gaps

Inspected: `frontend/src/MusicSoundPage.tsx` (currently ACE-Step/Control-Foley tabs), `AceStudioPage.tsx`, `VoiceRecorder.tsx`, `VoiceConversion.tsx`, `MediaSourcePicker.tsx`; backend `audio_effects.py`, `audio_utilities.py`, `ace_studio.py`, `vibe_editor.py`, `vibe_editor_render.py` and `editor_effects.py`.

Reuse media identity, project persistence conventions, directory chooser/export collision behavior, durable job execution, cancellation and recording. Existing simple voice effects and editor speed preprocessing provide bounded operations, not a ready multitrack mixer. The current Vibe Editor adapter renders sequential video clips/source audio or a replacement soundtrack; it does not expose an instrument, MIDI or DJ engine. Do not infer installed capabilities from upstream HyperFrames weekly announcements.

| Component | Planned role | Acquisition rule |
|---|---|---|
| Tone.js | Instruments, timed notes/patterns, common audio transport, effects and offline synthesis | Add one pinned compatible package after dependency/source/license review |
| WaveSurfer.js | Waveforms, region selection and visual timeline interaction | UI/visualization role; it is not the destructive editor or authoritative audio clock |
| @tonejs/midi | Read/write MIDI and convert supported notes/events | Add with piano-roll slice; file parsing is not a ready piano-roll UI |
| WaveSurfer Multitrack | Evaluate synchronized track display/dragging | Use only if it fits our common transport; avoid a second independent playback engine |
| FFmpeg/ffprobe | Existing decode, processing, encoding and validated final export | Reuse installed tools; never concatenate user input into shell commands |
| HyperFrames | Existing video composition/render integration | Hand off a rendered mix/stems first; qualify deeper track APIs against installed version |
| Essentia.js | Optional beat/tempo analysis beyond existing tools | Defer until a demonstrated analysis gap and license/runtime review |
| Rubber Band | Optional high-quality independent tempo/pitch processing | Check installed FFmpeg build/support and distribution obligations before enabling |
| OpenStudio, LMMS, Mixxx | Workflow/interaction references | No whole-DAW installation or source/component copying without an explicit compatible license decision |

Initial code should fit the existing frontend/backend structure: one Jukebox page plus focused timeline/beat/piano/deck components as needed; one validated project API and render service through the current job execution route. Do not create another worker controller or modify ACE-Step's internal project format.

## 5. Project model, timing and files

Use versioned JSON with tracks, source asset references, clip input/output positions, patterns/notes, instrument/sample configuration, effects, automation, tempo/time signature, loop markers, deck performance, export settings and revision. IDs remain stable. Source ranges are bounds-checked and imported files are probed; changed/missing sources require relink/review. Store undo history/checkpoints within a bounded policy and autosave atomically. Warn before leaving with unsaved changes and recover the last complete revision.

Musical notes/patterns use ticks/beats; audio trims use sample frames; one explicit tempo map converts both into arrangement seconds. Long audio stays at its chosen absolute time unless the user enables musical stretching. All views share the same playback position. Timing calculations cannot drift through repeated rounded seconds. Version 1 can have one project tempo; imported MIDI tempo maps must be supported explicitly or rejected with an explained conversion choice, never silently flattened.

Default local structure (separate from ACE-Step training/datasets):

```text
local_data/music_jukebox/
  projects/<project-id>/project.json
  projects/<project-id>/checkpoints/
  projects/<project-id>/recordings/
  cache/waveforms/<source-hash>/
  cache/renders/<job-id>/
  output/<project-id>/
```

User can choose a project/output folder. External media is referenced without an unnecessary permanent second copy; offer **Collect project media** for an explicitly requested portable project. Explain which generated recordings/stems belong to the project. A library entry may index the chosen output path; it must not secretly create a second final file. Cleaning cache never deletes sources, recordings or saved exports.

## 6. Preview, export and video synchronization

One audio scheduling/processing graph owns playback; WaveSurfer follows it. Pause/seek/loop affects all tracks/decks. Browsers require a user gesture to unlock audio. Do not use separate unsynchronized HTML players as a mixer.

Use Tone/Web Audio offline rendering for the same supported instrument/effect/automation graph and fixed sample rate/seed, then FFmpeg for file encoding. For operations not faithfully reproducible in realtime, preview the rendered range through the same processing path. Compensate known processing latency and filter tails. Do not promise bit-identical output across devices or between lossy MP3 and live playback: verify musical timing and processing against a lossless reference, and let the user audition the actual export.

Export stereo WAV first, then MP3/FLAC and optional per-track stems/MIDI. Validate duration/sample rate/channels, clipping, silence and file integrity before publishing. Cancellation must not publish a partial export. DJ performance recording must include automation and repeatable source timing.

Video preview follows the same project position with a saved offset. First integration sends the approved rendered soundtrack to Vibe Editor using existing asset selection, replacing audio only on user request. The current editor cannot be described as a fully shared multitrack DAW until deeper timeline support is implemented and tested. Preserve source dialogue by choosing mix/replace explicitly; do not automatically erase it.

Long recordings need cached/downsampled waveform peaks and bounded decoding; Web Audio buffers can consume much more RAM than compressed files. Before accepting large projects, measure memory and export limits, show usable bounds, and process work off the UI thread. Add no GPU dependency for ordinary composition/editing.

## 7. Build sequence and acceptance

1. **Edit foundation:** sibling tab, named project/folders, media/ACE-Step handoff, waveform tracks, recording, split/trim/cut/copy/paste, gain/fades/mute/solo, undo/reopen, shared playback and WAV export. Prove an actual cut/boost/fade matches playback before continuing.
2. **Mixer and effects:** pan/EQ/compression/limiter/reverb/tempo/pitch, automation, processed preview, clipping feedback and stems. Keep unsupported controls unavailable with a reason.
3. **Compose:** pinned Tone.js/MIDI integration, beat patterns, piano roll, synth/sample instruments, pattern arrangement and deterministic offline synthesis. Prove notes/patterns survive reload and export at the right bar boundaries.
4. **DJ:** two decks, cues/loops/EQ/crossfader, tap/grid/sync, performance capture/replay/export. Prove both deck audio and recorded controls survive seek and project reopen.
5. **Director/video:** validated prompt proposals/undo and optional linked video preview; explicit Jukebox → Vibe Editor soundtrack handoff. Verify revisions and approval cancellation, without duplicating the existing provider/controller.

Focused tests: sample-accurate splits/paste/ripple, silence/missing-source recovery, undo/reload, tempo conversion, loops/automation/fades, clipping, source preservation, export collision/cancel, identical project graphs for offline/live paths, audio/video offset and long-file memory limits. Use synthetic audio for automated CPU checks; actual microphone/device routing and subjective music quality require owner listening. Regression-check ACE-Step generation/training/result selection and Control-Foley remain unchanged.

Completion means usable music editing, composition and DJ output—not six empty panels or a claim of full FL Studio/Ableton feature parity. VST hosting, external MIDI hardware, advanced live time warping and AI stem separation are separate scope, not silently implied requirements.

## 8. Primary references checked

- https://github.com/Tonejs/Tone.js — Web Audio instruments, scheduling and effects.
- https://github.com/katspaugh/wavesurfer.js — waveform/regions/recording; visualization is distinct from signal processing.
- https://github.com/katspaugh/wavesurfer-multitrack — candidate multitrack UI, subject to transport compatibility.
- https://github.com/Tonejs/Midi — MIDI parsing/writing; piano-roll editing must be provided by the app.
- https://github.com/heygen-com/hyperframes/blob/main/docs/weekly-updates.mdx — upstream reference, not proof of our installed adapter's coverage.
- https://github.com/808StaN/OpenStudio — workflow reference only; no source copied.

No dependency acquisition, downloads, generation or application implementation is authorized by this planning artifact alone. The owner has asked to plan this addition; implementation requires the next instruction to proceed.
