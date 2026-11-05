# Audio tool guide

Source-backed usage map, 2026-11-05. IDs below are glossary IDs for future routing, not currently registered model functions. Consult [API helpers](API_HELPERS.md) and [HTTP routes](HTTP_ROUTES.md) for exact source locations. Live readiness has not been exercised by this documentation task.

## audio.extract — Extract MP3 from video/audio

**Choose when:** Extract a soundtrack for listening, analysis or subsequent audio work.

**UI:** #/media-prep → Audio → Utilities → Extract MP3

**Inputs:** Project/workspace ID, source asset_ids and operation extract_mp3; settings quality 0–9.

**Outputs:** Audio utility job and registered extracted audio assets.

**How to use:** getAudioUtilityCapabilities; createAudioUtilityJob(w,"extract_mp3",ids,{quality:2}); poll getAudioUtilityJob. ffmpeg is required. API accepts audio/video; UI output destination is configured separately. Extraction alone neither analyses speech nor proves a requested interval was isolated.

**Source:** [media-api.ts](../frontend/src/lib/media-api.ts), [audio_utilities.py](../backend/story_builder/services/audio_utilities.py)

## audio.utilities — Noise cleanup and stem separation

**Choose when:** Clean a recording or separate soundtrack components.

**UI:** #/media-prep → Audio → Utilities

**Inputs:** Audio asset_ids, noise_cleanup or demucs_stems and supported settings.

**Outputs:** Utility job and cleaned audio/stems.

**How to use:** Check utility capabilities; createAudioUtilityJob then poll results. Cleanup uses the denoiser runtime; stems uses Demucs. Operation readiness is separate from ffmpeg extraction readiness.

**Source:** [media-api.ts](../frontend/src/lib/media-api.ts), [audio_utilities.py](../backend/story_builder/services/audio_utilities.py)

## audio.isolate — SAM audio event isolation

**Choose when:** Isolate a specific event already identified in analysed video audio.

**UI:** #/media-prep → Video Summariser results/audio events

**Inputs:** Analysis run/event IDs, prompt; temporary preview identity for save/discard.

**Outputs:** Isolation preview and explicitly saved or discarded asset.

**How to use:** getSamAudioCapability → isolateVideoAudioEvent → saveSamAudioPreview/discardSamAudioPreview. Requires compatible analysis context; not a universal timestamp cutter or an automatic promise of perfect speech removal.

**Source:** [media-api.ts](../frontend/src/lib/media-api.ts), [sam_audio_vibe.py](../backend/story_builder/services/sam_audio_vibe.py)

## audio.speech — Timed TTS / dialogue generation

**Choose when:** Generate spoken character dialogue or narration with timed text.

**UI:** #/media-prep → Audio → Studio

**Inputs:** SRT content, characters with name/reference_voice_id/language and supported settings.

**Outputs:** Timed TTS job and generated speech assets.

**How to use:** listAudioVoices/listAudioModels/getAudioCapabilities then createTimedTTSJob/getTimedTTSJob. Preserve exact requested words and speaker assignments; generated speech is distinct from source analysis.

**Source:** [media-api.ts](../frontend/src/lib/media-api.ts), [audio_tts.py](../backend/story_builder/services/audio_tts.py)

## audio.voices — Record, enrol and bind character voices

**Choose when:** Record/import a voice or associate a chosen voice with a character.

**UI:** #/characters and Audio Studio

**Inputs:** Recording/import asset, name/transcript; character and screenplay identity for binding.

**Outputs:** Voice reference/catalogue asset and explicit character-voice association.

**How to use:** uploadMediaAsset with recording storage where appropriate; enrollAudioVoice/importComfyVoiceToWorkspace/refreshAudioVoices; story-api setCharacterVoice/auto-match. Browser recording needs user microphone access; matching proposes/selects voices, not actor consent.

**Source:** [VoiceRecorder.tsx](../frontend/src/VoiceRecorder.tsx), [media-api.ts](../frontend/src/lib/media-api.ts), [story-api.ts](../frontend/src/lib/story-api.ts), [character_voice_bindings.py](../backend/story_builder/services/character_voice_bindings.py)

## audio.effects — Voice effects, repair, conversion and simple CPU effects

**Choose when:** Alter existing audio with a supported effect.

**UI:** #/media-prep → Audio → Studio effects/conversion

**Inputs:** Audio asset ID, operation simple/noise_cleanup/voice_repair/voice_changer/rvc/emotion/style and validated settings.

**Outputs:** Effect job and output audio.

**How to use:** getAudioEffectCapabilities → createAudioEffectJob → getAudioEffectJob. Inspect operation schema/models. Workflow file existence does not establish verified runtime nodes. Do not confuse audio-effects cleanup with utility cleanup; select the ready appropriate service.

**Source:** [media-api.ts](../frontend/src/lib/media-api.ts), [audio_effects.py](../backend/story_builder/services/audio_effects.py)

## audio.voice_studio — Specialist voice studio and RVC training

**Choose when:** Explicit specialist voice workflow, model training or conversion.

**UI:** Audio Studio → specialist voice tools

**Inputs:** Operation-specific source assets, reference/model/training settings and project identity.

**Outputs:** Voice-studio job, logs/progress and resulting audio/model where supported.

**How to use:** GET /api/studio-tools/voice/capabilities; POST /voice/jobs; GET job and POST cancel/resume supported routes. Inspect voice_studio.create and UI payload before submission. Training is expensive, separate from preference learning.

**Source:** [VoiceStudioTools.tsx](../frontend/src/VoiceStudioTools.tsx), [voice_studio.py](../backend/story_builder/services/voice_studio.py), [studio_tools_api.py](../backend/story_builder/services/studio_tools_api.py)

## audio.scene — Audio scene surgery: split and stitch

**Choose when:** Cut specific audio intervals, replace passages and reconstruct a scene.

**UI:** Audio Studio → scene surgery

**Inputs:** Audio source, edits with start/end/text; split job ID, simple/timed stitch mode, replacement IDs and gaps.

**Outputs:** Split/stitch jobs and resulting audio assets.

**How to use:** getAudioSceneCapabilities → createAudioSceneSplit → getAudioSceneSplit; createAudioSceneStitch → getAudioSceneStitch. Validate current source/range/format requirements. This is the first candidate for excerpt operations; inspect actual split outputs before claiming an exact requested export.

**Source:** [AudioSceneSurgery.tsx](../frontend/src/AudioSceneSurgery.tsx), [media-api.ts](../frontend/src/lib/media-api.ts), [audio_scene.py](../backend/story_builder/services/audio_scene.py)

## audio.reconstruct — Dialogue reconstruction and take selection

**Choose when:** Prepare character speech in parts and choose approved replacement takes.

**UI:** #/media-prep → Audio → Reconstruct

**Inputs:** Character/sentence calibration, ordered parts with expected_text, take audio and transcript.

**Outputs:** Reconstruction session/parts/takes and accepted audio association.

**How to use:** getReconstructionSession/saveReconstructionCalibration/createReconstructionPart/addReconstructionTake/acceptReconstructionTake. Accepting a take does not automatically replace video sound; route it into a reviewed edit/stitch.

**Source:** [media-api.ts](../frontend/src/lib/media-api.ts), [audio_reconstruct.py](../backend/story_builder/services/audio_reconstruct.py)

## audio.finetune — F5 dataset preparation

**Choose when:** Prepare an explicitly requested speech fine-tuning dataset.

**UI:** Audio Studio → fine-tune preparation

**Inputs:** Dataset name/base model, samples with audio asset_id and text.

**Outputs:** Preparation job/dataset artifacts.

**How to use:** createF5PreparationJob/getF5PreparationJob. Dataset preparation is not proof model training completed. Use only explicit training intent.

**Source:** [media-api.ts](../frontend/src/lib/media-api.ts), [audio_finetune.py](../backend/story_builder/services/audio_finetune.py)

## music.generate — Music and Foley generation

**Choose when:** Generate music or sound effects, including supported reference-conditioned Foley.

**UI:** #/media-prep → Audio → Music & Sound

**Inputs:** Kind ace-music/control-foley, settings, prompt knowledge reference and optional video/audio reference IDs.

**Outputs:** Music/Foley jobs and audio outputs.

**How to use:** getMusicCapabilities/getWorkflowGuidance; createMusicJob/listMusicJobs/getMusicJob. Follow the selected operation schema and reference support. Do not claim generated SFX are automatically placed in an edit.

**Source:** [MusicSoundPage.tsx](../frontend/src/MusicSoundPage.tsx), [media-api.ts](../frontend/src/lib/media-api.ts), [music_sound.py](../backend/story_builder/services/music_sound.py), [control_foley.py](../backend/story_builder/services/control_foley.py)

## music.ace — ACE-Step studio, generation and fine-tuning

**Choose when:** Use ACE creation modes or explicitly prepare/train adapters.

**UI:** Music & Sound → ACE-Step studio; nested view, not a guaranteed top-level hash route

**Inputs:** ACE session/project, create settings/reference mode; training dataset and configuration for fine-tuning.

**Outputs:** Saved ACE session/revisions, runtime job and generated audio or training artifacts.

**How to use:** GET /api/ace/state; POST /api/ace/projects; project /command and /dataset; GET /log. Read AceStudioPage and ace_studio.command for valid commands. New visits should use Create; Fine-tune is a distinct intent.

**Source:** [AceStudioPage.tsx](../frontend/src/AceStudioPage.tsx), [ace_studio_api.py](../backend/story_builder/services/ace_studio_api.py), [ace_studio.py](../backend/story_builder/services/ace_studio.py)

## music.jukebox — Music Jukebox / composition / DJ / export

**Choose when:** Arrange/play/edit music or export a composition.

**UI:** Music & Sound → Music Jukebox

**Inputs:** Project, tracks/patterns, tempo/gain/deck/crossfade settings and output selection.

**Outputs:** Saved composition, playback state, staged WAV and export job/output.

**How to use:** /api/jukebox/state/projects; project save/render/export/copy; jobs and exports. Browser Tone/MIDI playback/render is part of this path. /api/jukebox/chat proposes supported changes; it does not run arbitrary tools.

**Source:** [MusicJukebox.tsx](../frontend/src/MusicJukebox.tsx), [JukeboxDJ.tsx](../frontend/src/JukeboxDJ.tsx), [music_jukebox_api.py](../backend/story_builder/services/music_jukebox_api.py), [music_jukebox.py](../backend/story_builder/services/music_jukebox.py)
