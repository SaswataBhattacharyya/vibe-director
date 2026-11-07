# Backend services — active capability / Editor / production integration (2026-11-07)

Current implementation guides: `fixes/ACTIVE_FIXES.md`, `fixes/INTEGRATION_ARCHITECTURE.md`, `fixes/ACCEPTANCE_TESTS.md`. Old R01/R02 crash-recovery and Editor brief bridge are **already source-implemented**; don't replay them.

- `agent_tools.py`: passive metadata + readiness for currently allowlisted MP3, last-frame, Editor brief and Codex computer actions. Not a comprehensive app tool registry.
- `agent_conversation.py`: shared Director with finite intent schema and existing bounded Story/Screenplay/Image/Prompt/Video/Studio/ACE proposal/discussion adapters. It does **not** autonomously dispatch every app feature or deeply inspect video audio.
- `agent_tasks.py` / `agent_editor.py`: durable approved operations and revision-scoped brief preparation. Add additional narrow typed validators only for real installed capabilities; retain actual job state, approve/review steps, owner/hash and repeated-request recovery. Never add generic arbitrary command endpoints.
- `audio_utilities.py`: FFmpeg MP3 extraction; extraction alone is **not** timed transcription/gibberish identification. Implement AUD-01 only after examining real ASR/timing service outputs and projecting timestamps back onto the source media.
- `vibe_editor.py` / `vibe_editor_api.py` / `vibe_editor_render.py`: saved Editor session, ranges, plan revisions, two clearances and trusted JSON→HyperFrames renderer; visual Studio UI must translate into this format or a separately validated, versioned adapter. No arbitrary provider-authored HTML/JS.
- `media_library.py` / `storage_paths.py` / `projects.py`: preserve existing project-scoped IDs, linked storage, source hashes, explicit import, deletion checks, output grants and checkpoint recovery. Index/membership migrations require separate schema impact proof.
- `storyboard.py`: preserve native storyboard source as truth; optional OpenMontage manifest adapters need validated install/license/API and revisioned mappings, not a parallel project database.
- **Runtime skill dependency:** `agent_skills.py` points into `fixes/vibe-director-codex-agent-blueprint-v2/...`. Do not delete or move that package as part of documentation cleanup.

Test only with test-owned sources and bounded workers; don't run paid/GPU generations or unrestricted host tool execution without explicit authorization.
