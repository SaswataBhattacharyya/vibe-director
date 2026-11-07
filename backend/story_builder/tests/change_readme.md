# Backend tests — active implementation checks (2026-11-07)

Read `fixes/ACCEPTANCE_TESTS.md`. Historical completed tasks Q01–Q08, R01/R02, UX01–UX03 and partial cross-page adapters do not need new implementation; re-run their tests only where touched code could regress them.

Prioritize:
1. CAP-01 typed tool discovery/authorization: `test_agent_tools.py`, `test_agent_tasks.py`, `test_agent_skills.py` and `test_agent_editor_tool_handoff.py`. Mock blocked/unavailable runtime honestly; skill text is not executable permission.
2. AUD-01 whole-asset vs five-second preview and truthful timed-ASR analysis: extend `test_audio_utilities_integration.py` and add a source-aligned transcript/range proposal test. Assert MP3 extraction alone doesn't claim the spoken error was located.
3. HF-01/HF-02 approved JSON plan and Studio bridge: `test_agent_editor.py`, `test_editor_effects.py`, media checks and new composition serialization/revision/approval tests. No user-edited JS execution, unsafe path, source hash bypass or stale clearance.
4. MEDIA-01 membership/browse/reuse `test_media_library.py`, `test_media_catalogue.py` with two fixture projects and Save/Load/rollback; delete one membership must not delete the other's source.
5. OM-01 storyboard roundtrip with optional/unavailable upstream handled without data loss: `test_storyboard.py` + new adapter fixture tests.

Use `tempfile.TemporaryDirectory`, dummy PNG/WAV/MP4, no real user projects; assert cleanup on success AND error. Mocked/CPU tests are not proof of actual Studio preview, audio transcription quality or paid/GPU output. Record commands and failures accurately.
