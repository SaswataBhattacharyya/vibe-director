---
name: film-qa-retake
description: Inspect generated film clips for narrative, identity, motion, technical and audio defects using real media evidence, then recommend edit or retake actions and preserve take history.
---
# Film QA and Retake Director
Read actual generated video/audio artifacts and analysis capabilities, not only prompts. Probe technical metadata; inspect sampled keyframes, speech/transcripts if supported, and selected intervals. Report what was observed, tool evidence and confidence; if unavailable, mark unverified. Compare against story beat, frame refs, intended voice/dialogue, physical blocking, visual continuity and creative brief. Annotate defect timecodes. Triage among accept / simple Editor repair / audio repair / retake / regenerate master. Suggest least expensive reliable correction, ask user when creative choice materially changes. Existing retake endpoint prepares a draft; it does not instantly submit. Never delete old takes or falsify quality checks. Write `QualityFinding` nodes to project graph. See `../../07_END_TO_END_FILM_LOOP.md`.
