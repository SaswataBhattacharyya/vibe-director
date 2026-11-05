# File-by-file implementation matrix — Codex handoff

**Basis:** latest read of the vibe-director-current GitHub application branch around 2026-11-05 plus the checked-in full_review.md. Every edit is PROPOSED; existing code may advance. Use target symbol names rather than assuming line numbers still match. The phase number is a code dependency, not a mandatory user creative flow. Follow fixes/change_readme.md and the colocated change_readme.md in each directory for more code sketches and safety requirements.

| Phase | Existing target file / planned new file | Precise proposed change | Upstream/downstream & acceptance |
|---|---|---|---|
| 0 | AGENTS.md, full_review.md, tool_glossary/** | READ current preservation rules, known tools and regression claims; do not rewrite historical review as if it were runtime proof | Compare git status/HEAD; no code modifications |
| 1 | NEW services/agent_tools.py | Define exact allowlisted ToolSpec + capability + owner + approval-scope adapter; metadata-only discovery first | media/audio/video/editor adapters; tests wrong-project, unknown field, blocked tool |
| 1 | NEW services/agent_skills.py | Shared global/app/project metadata search and selective safe SKILL.md loader; preserve hashes, versions, configured roots | director_skills.py and Editor new path; traversal, collision, missing-global tests |
| 1 | services/director_skills.py | Keep director_skill_context(video=...) compatibility while delegating selected context to new resolver after tests | current video/screenplay prompt callers must not regress |
| 1 | NEW services/agent_graph.py | Read-only project-scoped projection of current characters, worlds, story, screenplay, board, assets, jobs and Editor; provenance + hashes | do not invent scene nodes; test project A/B isolation |
| 1 | NEW services/agent_api.py | Exact routes /api/agent/... for tool metadata, task plans/status and skill metadata; safe error schema | isolated_server.py dispatcher routes to it; no arbitrary command execution |
| 1 | isolated_server.py | Add ONE narrow dispatch branch for /api/agent/ alongside existing /api/editor/ delegation | existing editor/audio/video route regression; no giant new request switch |
| 1 | NEW frontend/src/lib/agent-api.ts | Typed capability, skills, tasks, approvals, events client; no duplicate existing video/editor requests | backend agent_api validated contract |
| 1 | NEW frontend/src/lib/agent-context.ts | Typed workspace/surface/asset/range/task handoff; no path-only or filename-only identity | agent workspace UI, Editor, Storyboard, Video |
| 1 | NEW frontend/src/{AgentWorkspace,AgentChat,AgentTaskPanel,AgentSkillPicker}.tsx | Persistent center conversation, plan card, truthful progress, skill/tool badges, real right surface | StudioShell, project context, responsive and navigation tests |
| 1 | frontend/src/StudioShell.tsx | Keep sidebar; wrap chosen page + persistent chat; stage rail becomes optional shortcuts | App routing; independent Video/MediaPrep use |
| 1 | frontend/src/App.tsx | Pass actual project context into stable shared shell; avoid adding business logic to its ~1235 lines | route switching, unsaved forms, project switch |
| 1 | frontend/src/EditorWorkspace.tsx | Reuse existing resizable editor pane concept; prevent double nesting duplicate general chat | VibeEditorPage still functional |
| 2 | NEW services/agent_media_ops.py or audio_utilities.py | Extract existing server audio utility job setup into shared validated helper for both callers | isolated_server.py utility route and agent tool; real MP3 output; idempotency/recovery |
| 2 | services/audio_utilities.py | Preserve stage_assets, validation/capabilities; use shared helper only if factoring here is smaller | test_audio_utilities_integration.py; CPU-only worker |
| 2 | services/video_continuity.py | Reuse current verified last_frame() as tool, no new duplicate extractor | source hash + cache; test_video_continuity.py |
| 2 | services/media_library.py, media_discovery.py | Read/validate existing owner and hash API; avoid changes unless a concrete tool adapter requires a narrow new seam | preserve catalogue replacement fix and original assets |
| 3 | NEW services/agent_tasks.py / agent_plan.py | Plan revision+hash, approvals, DAG steps, events, job IDs, recovery/retry; task owner and typed tool calls | production_ledger.py, projects.py, agent_api; no execution during plan |
| 3 | services/production_ledger.py | Add agent_tasks/steps/events/(minimal graph edges or skill bindings) tables under existing project-owned DB and idempotency constraints | projects.sql_snapshot, existing worker jobs; versioned migration/rollback tests |
| 3 | services/projects.py | Verify new project tables, skill bindings and safe owned files save/load without altering historical snapshots | project isolation, idle active task behavior, moved projects |
| 3 | NEW services/agent_computer.py or separate sidecar | Optional scoped fs/Git/test/browser executor: explicit grants, sandbox, audit and runtime capability; blocked when absent | no raw user shell through API; never bypass GPU safety |
| 4 | frontend/src/ProductionStylesPage.tsx | Optional production type, visual style, directing jacket selectors; collapse advanced publishing; save versioned project choices | services/production_styles.py and production_director_profiles.py; no style gate for manual video |
| 4 | services/production_styles.py, production_director_profiles.py | Keep immutable published styles; add optional project visual treatment/jacket resolution only if existing schema lacks it | existing production style tests, original snapshots |
| 4 | frontend/src/ScreenplayPage.tsx | Use shared chat for scene/shot-specific proposals, apply only via existing revision/CAS | story_authoring.py/schema; standalone no-screenplay video unaffected |
| 4 | frontend/src/StoryboardPage.tsx | Comic panel cards for image+action+dialogue+duration; make automatic work resumable backend tasks later | storyboard.py, image jobs; keep current FFLF automation pause |
| 4 | services/storyboard.py | Reuse per-shot image/route/reference records and validated handoffs; minimal new optional association fields only | editor/video handoff tests, revision checks |
| 5 | NEW services/agent_video_prep.py | Model-aware structured reference manifest, dialogue timing and prompt; choose T2V/R2V/FL2VA route with exact schemas | all 3 contract validators, image/voice bindings, clip IDs |
| 5 | frontend/src/PromptPreparationPage.tsx | Present actual <Picture N>, <audioN>, video slots, real SHA and times, continuity semantics; no invented first-frame on R2V | model API serialization, PromptDirector guidance |
| 5 | frontend/src/lib/video-api.ts / Video Create | Reuse exact current request functions; only change after corresponding verified versioned backend contract | CPU exact-field tests, worker acceptance |
| 5 | services/isolated_{video,r2v,fl2va}_contract.py | LTX toggle must be a NEW versioned request/profile, not an unrecognized v2 field | graph digest pinning, old frozen jobs, validate_request |
| 5 | services/production_job_worker.py, production_ledger.py | If turbo_only selected under v3, original collection validates and publishes final directly; no LTX claim | save_turbo_original, promote_turbo_refinements, recovery |
| 5 | services/t2v_pipeline.py, ltx_chunks.py, minimax_h3_t2v.py | Versioned Turbo-only final validation (audio/fps/duration/hash) separate from existing LTX chunk/refinement path | video final collection, quality and restart tests |
| 6 | NEW services/agent_media_review.py | Evidence-backed timestamped visual/audio defect findings; mark unavailable analyzer honestly | image detailer/video summarizer/tool graph; tests avoid invented observations |
| 6 | services/vibe_editor.py | Add typed cross-tool Specialist agent binding ALONGSIDE old brief/plan/range-approved render; keep "do not run tools" for JSON renderer planner | Editor old sessions, learning, approval, exact selections |
| 6 | services/vibe_editor_api.py | Small adapter/handoff route only if necessary; preserve command/plan/export, no arbitrary execution | VibeEditorPage.tsx, persisted editor project |
| 6 | services/vibe_editor_render.py | **PRESERVE** trusted HyperFrames/FFmpeg render; extend only with verified requested support and regression tests | no LLM-authored executable code |
| 6 | frontend/src/VibeEditorPage.tsx | Show specialist shared chat and true tool outputs; keep Preview/Media/Timeline/Style/Export workflows | editor-api.ts and project context |
| 6 | services/assembly.py, assembly_renderer.py | Keep strict legacy accepted-take route; adopt freeform mixed timeline through Editor as separately validated finishing route | accepted history/output audio unaffected |
| 7 | optional OpenMontage, Backlot, HyperFrames Studio adapters | Feature-flag, verify install/license/auth; output asset handoff only after true capability check | external disabled means native pipeline still works |
| 0–7 | backend/story_builder/tests/change_readme.md | Add focused tests using isolated TemporaryDirectory for synthetic text/images/audio/video; cleanup and verify | never delete real media, no unapproved GPU/provider calls |

## Do not silently change
- MediaPrepPage.tsx and the existing Media Prep user interface.
- StudioShell left navigation links/theme.
- Existing Media Prep endpoints and stable media IDs/hashes.
- Historical model workflow versions, immutable accepted takes, ledger leases, recovery fences, GPU watchdog.
- Editor selected-media and approval validators.
- Existing stored project/skill/style history.
- The 13 blueprint skills are **guidance under fixes**, not automatically installed.
- The two custom engineering skills under fixes/skills are also **not installed globally**.

## Exact Codex procedure
1. Read fixes/CODEX_CHANGE_README_PROMPT.md.
2. Resolve discrepancies against current source and return a concrete Phase 1 mini-diff plan with file list, acceptance, blast radius.
3. Stop until explicit implementation approval.
4. When approved, implement only the agreed slice, run tests, prove disposable cleanup and report all results honestly.
