# Shared Director and Editor tool access

Both chat surfaces use the live `/api/agent/tools` catalogue and the same `tool.call` router. The former fixed intent list no longer limits which registered operation the model can propose. There are currently 37 registered operations. Discovery and conversation do not dispatch work: the owner reviews exact settings, approves the saved task, then chooses Run. Missing native runtimes remain blockers.

| Area | Registered operations |
| --- | --- |
| Sources and evidence | `media.list`, `media.inspect`, `media.index_content`, `media.download_youtube`, `image.analyze`, `video.analyze`, `video.sample_frames`, `video.extract_style_frames` |
| Clip comparison and editing | `video.compare_clip_overlap`, `video.continuity_last_frame`, `editor.create_session`, `editor.select_media`, `editor.prepare_brief`, `editor.prepare_timeline`, `editor.prepare_clip_join`, `editor.render` |
| Images and reviewed frames | `image.generate`, `frame.create_take`, `image.generate_next_keyframe`, `video.interpolate_keyframes`, `video.export_frame_sequence` |
| Video generation | `video.generate` using existing T2V, R2V or first/last-frame requests |
| Audio and music | `audio.extract_mp3`, `audio.transcribe`, `audio.noise_cleanup`, `audio.demucs_stems`, `audio.effects`, `audio.foley`, `audio.split_scene`, `audio.stitch_scene`, `music.generate`, `voice.speak`, `voice.design`, `voice.timed_speech` |
| 3D | `3d.generate`, `3d.generate_multiview` |
| Computer | `computer.execute` with explicit project/full access through the existing grant and approval path |

## Example: compare, cut and join two clips

1. Attach the two clips in intended order, or ask the Director to find project media. Approve source discovery/inspection when proposed.
2. Ask it to compare the first clip's tail with the second clip's head. `video.compare_clip_overlap` produces measured evidence. Similarity is not proof of a seamless cut.
3. Ask for specific sampled frames if visual review is needed. `video.sample_frames` extracts up to six explicitly timestamped images on CPU. With the source still selected, the next chat message receives these verified images as vision input, along with timestamp lineage. Extraction alone is not visual interpretation. Explicit image attachments take precedence.
4. Use an existing Editor session or ask to create one. Ask to select explicit in/out ranges using `editor.select_media`; initial five-second UI previews do not impose a whole-source analysis limit.
5. Prepare and approve the creative brief through the existing Editor clearance. Ask for the exact cuts/order through `editor.prepare_timeline`, or for a supported Kdenlive join through `editor.prepare_clip_join` with the completed comparison task ID.
6. Review the pending plan and render through existing clearance controls, or review and run an `editor.render` task bound to the pending revision. Originals remain unchanged. New edits invalidate old plans.

Completed tool reports and owned session IDs/revisions are available to follow-up messages. Tool/media content is untrusted evidence, not permission or instruction. The model never approves its own tasks or frames. Processing beyond a saved selection requires changing that selection explicitly.

## Execution boundaries

All catalogue tools are reachable; this does not expose arbitrary HTTP endpoints, grant every permission, or implement every upstream feature. Existing native tools enforce readiness, ownership, immutable inputs, job correlation and GPU/provider guards. The router does not automatically execute chains of proposed tasks or retry generation after a lost acknowledgement.

HyperFrames and Kdenlive use the existing supported Editor plan/render adapters. Native Studio/Backlot GUI launching, arbitrary native GUI actions/history, upstream OpenMontage generation, fine-tuning/training, F5 dataset preparation, Jukebox browser-performance capture/export and SAM Audio's separate preview/save workflow are not new chat adapters in this change. Interactive browser control remains unavailable. Approved computer tasks provide terminal/coding/filesystem access, not automatic native GUI parity. Do not describe these exclusions as completed integrations.

## Implementation and verification

- `agent_tool_routing.py`: validates live catalogue requests; supplies bounded completed evidence and verified sampled images to follow-up chat.
- `agent_analysis_tools.py`: typed bindings to existing Media Prep job routes.
- `agent_workspace_tools.py`: bounded CPU media discovery/probing/frame sampling, Editor session/range/plan actions and candidate frame takes.
- `agent_native_tools.py`, `agent_tasks.py`: preserve exact plans, input identities, native dispatch correlation, durable job mapping, polling and cancellation. No database migration.
- `vibe_editor.update_project(..., expected_revision=...)`: optional internal atomic revision guard; existing manual callers retain their interface.
- `DirectorConversation.tsx`: exact settings disclosure and media-kind-specific output previews.

Focused mock and CPU tests cover both chat surfaces, invalid/blocked/foreign requests, computer routing, existing Media Prep route contracts, completed evidence, real FFmpeg samples, extraction-failure cleanup, Editor revisions/selections/plans and existing native generation/render/task recovery. Browser tests check sampled-image display, settings, reload and existing speech/audio cards. These checks do not establish real model/provider quality or full native-GUI acceptance.

Tests own temporary roots and assert their deletion, including on failure. Successful user frame samples are intentional registered outputs, not disposable test files. No owner media or production history is removed.

Rollback: revert only this tool-access change set, preserving unrelated working changes. Stop new task submissions first and allow active jobs to finish; older code cannot process the new `agent-workspace` kind. Keep completed media and task history. No database rollback is required.

Current verification: 67 focused backend tests passed; one opt-in offline Codex sandbox test was skipped. Two focused Playwright tests passed. TypeScript typechecking and `git diff --check` passed. Test fixtures assert removal of their temporary media/database roots. No GPU generation or paid provider requests ran.

Files changed for this tool-access work (some already contained unrelated local changes):

- `backend/story_builder/services/agent_tool_routing.py`
- `backend/story_builder/services/agent_analysis_tools.py`
- `backend/story_builder/services/agent_workspace_tools.py`
- `backend/story_builder/services/agent_native_tools.py`
- `backend/story_builder/services/agent_conversation.py`
- `backend/story_builder/services/agent_tasks.py`
- `backend/story_builder/services/vibe_editor.py`
- `backend/story_builder/services/video_repertoire.py`
- `backend/story_builder/services/video_repertoire_worker.py`
- `backend/story_builder/tests/test_agent_tool_access.py`
- `backend/story_builder/tests/test_agent_tools.py`
- `backend/story_builder/tests/test_agent_api.py`
- `frontend/src/DirectorConversation.tsx`
- `frontend/tests/director-runtime.spec.mjs`
- `skills/vibe-director/SKILL.md`
- `fixes/INTEGRATION_ARCHITECTURE.md`
- `docs/DIRECTOR_TOOL_ACCESS.md`
- `.review/director-tool-access-impact.json`
- Generated Graphify graph, manifest, stat index and AST cache entries from the required code-only refresh. The latest incremental extraction has 97 nodes/304 edges for ten changed files; it is not a complete repository call graph. Manual dispatch tracing supplements it.

The blast-radius report verifies 29 current source anchors and rates the shared dispatch/ownership seams high impact (0.60–0.70 heuristic range). This is a review-priority score, not a defect probability. It excludes unrelated dirty work and does not assert measured test coverage.
