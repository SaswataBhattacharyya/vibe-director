# Music Jukebox — implementation and usage

2026-10-30. Implemented as a sibling of ACE-Step Music and Control-Foley under Media Prep → Audio tools → Music & Sound. It does not start AI generation or training. Existing music/voice/video engines remain separate.

## What is usable

1. Enter a project name and click **New named project**. Import audio files/a folder, choose shared media, record through the existing recorder, or bring an ACE-Step result using **Open in Music Jukebox**.
2. **Edit & Arrange** shows waveform clips with trim, move/drag, split at playhead, copy/cut/paste, duplicate, reverse, ripple delete, track mute/solo and gain. Originals remain intact. Track effects include pan, EQ, compression, echo, reverb, fades, independent granular time stretch/pitch, normalization and gain/pan automation.
3. **Compose & Beats** adds a house drum pattern, synth/bass/sampler tracks and a piano/step grid. Select notes to edit pitch, position, length and velocity; duplicate bars and quantize. MIDI imports reject unsupported changing tempo/time-signature maps rather than flattening them. Export MIDI separately from rendered audio.
4. **DJ Mix** loads A/B sources with cue, position, manual/tap BPM, rate, EQ, gain, beat-length loops, tempo sync and equal-power crossfader. Click **Capture mix performance**, operate decks, then **Finish capture**. Choose **Captured DJ performance** for common-transport replay/export. Stop live decks before using common playback. Live activity locks arrangement editing/export to avoid competing playback graphs.
5. Save/open/save-as, undo/redo, local draft recovery and 30 atomic server checkpoints preserve work. Export job progress is recovered when reopening the project. Project JSON can be downloaded/imported and copied to a chosen folder. Server project state remains the authoritative managed copy.
6. Prepare a rendered preview, check its peak, choose an output folder and export WAV/MP3/FLAC or a selected arrangement track stem. Existing files require explicit overwrite retry. Cancellation prevents publication of partial audio. Copying an export into the library and opening Vibe Editor is explicit; soundtrack replacement still needs editor approval.
7. Music Director uses the shared model picker and `/status`. It supports bounded tempo/gain/drum-pattern/crossfade proposals with brief approval followed by exact-change approval. Attach/drag sources into chat and remove attachment chips. These provide filenames/settings, not listening/transcription. Local video preview follows the common position with an editable offset; audio export does not embed video.

## Storage and limits

- `local_data/music_jukebox/projects/<id>/project.json` and `checkpoints/`: managed projects and revisions.
- `local_data/music_jukebox/cache/renders/`: temporary uploaded rendered WAV and one-use metadata, cleaned on staging after 24 hours.
- `local_data/music_jukebox/output/<id>/`: default exports; users can choose another folder.
- `local_data/music_jukebox/exports/`: small output manifests, not duplicate final audio.
- Recordings/imports reuse the shared media library; explicit imports can make library copies. Removing an unused Jukebox source does not delete its file.
- Stereo 44.1 kHz, maximum 10 minutes; 24 tracks, 32 sources, 64 MiB per decoded input file and 192 MiB decoded-source cache. Offline processing itself needs additional RAM, so these limits are safeguards, not a promise that every maximum-size arrangement fits every browser. Render upload cap 120 MiB.
- One tempo and 4/4; synth/bass/seeded drums and user samples. No realistic licensed piano/guitar bank downloaded.

## Practical boundaries

This is an initial music workstation, not full FL Studio/Ableton parity. DJ speed changes pitch; independent key-lock, separate headphone routing, automatic beat detection/grid alignment, per-deck waveform display and crossfader-curve choices remain future work. Deck sync matches rates from supplied BPM; it does not align downbeats automatically. Use position/cue to align them.

Track fades span the arrangement; silence is a track-level action (split/move to a separate track for an isolated region). Peak feedback reports the last render, not a continuous hardware meter. The visible master protection is a compressor, not a certified brick-wall limiter. Pre-roll waits one bar rather than generating an audible count. Pattern editing is note-based rather than a separate reusable pattern-clip engine. Keyboard editing shortcuts, independent effect bypass/A-B, arbitrary time signatures, portable collected-media packaging and direct shared multitrack video editing remain unimplemented. Export settings are session controls; only the project’s audio decisions are saved. Video selection must be reselected after reopening. Source media cannot be silently relinked to unrelated paths.

## Dependencies and provenance

Installed from npm, pinned with lifecycle scripts disabled:

| Package | Version | License | Use |
| --- | --- | --- | --- |
| tone | 15.1.22 | MIT | Offline instruments, stretch/pitch and effects |
| wavesurfer.js | 7.12.12 | BSD-3-Clause | Waveform display only |
| @tonejs/midi | 2.0.28 | MIT | MIDI notes import/export |

Primary docs: https://tonejs.github.io/docs/15.1.22/ and https://wavesurfer.xyz/docs/ and https://github.com/Tonejs/Midi . License notices are retained in `third_party_licenses/music-jukebox/` and exact dependency hashes in package-lock.json. No OpenStudio/Mixxx/LMMS source copied, no GPL DAW installed, no Rubber Band/Essentia dependency added. FFmpeg/ffprobe reuse the installed command-line tools. npm audit found three existing unrelated advisories in Vite/source-map-js/postcss-selector-parser; no automatic broad dependency upgrade was made. Existing large-bundle build advisory remains.

## Evidence

- Seven backend tests pass: revisions/checkpoints/workspace freeze, source identity, bounds, one-use project-bound render staging, actual FFmpeg WAV/MP3/FLAC encoding, collision/cancel protection, project-copy no-clobber and per-project job recovery.
- Three isolated Jukebox browser tests pass: real CPU offline synth/drum audio, deterministic replay, MIDI roundtrip, split sample continuity, +6 dB amplitude, stretch timing, DJ loop stop timing, project creation/save, browser draft recovery, piano grid and preview.
- Six existing ACE-Step/Control-Foley/Audio Studio browser regression tests pass (nine combined with Jukebox). Network APIs mocked for interaction tests; no provider/GPU calls.
- An actual shared CPU worker completed a temporary WAV export through the durable job path; the validated test output and temporary project were removed.
- TypeScript/production build passes. Desktop and narrow layouts inspected. Playwright MCP profile was occupied; isolated Playwright CLI browser used. Live UI at 8082 and `/api/jukebox/state` at 3020 verified, without creating real media or jobs.
- API reloaded from idle state with existing environment; PID 2559277, log `local_data/logs/studio-integration-reload.log`. ComfyUI queue verified idle; no GPU/AI generation/training started.

Owner testing: audition real imported tracks/DJ performance, grant microphone permission and record, export to the intended PC folder, reopen recovery, and approve an actual Director suggestion. Provider and microphone behavior were not represented as live acceptance by mocked checks.
