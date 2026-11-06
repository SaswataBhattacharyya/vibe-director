# Active source change matrix — 2026-11-06

**Current:** [review](CODE_REVIEW_2026-11-06.md), [active tasks](ACTIVE_FIXES_2026-11-06.md), [single-chat UI spec](UNIFIED_CHAT_AND_PANES.md). **Completed** Q01–Q08 are archived as [results](Q01_Q06_RESULTS.md) and [results](Q07_Q08_RESULTS.md); do not reimplement.

| Task | Files / symbols needing review | Actual change needed | Critical consumers and tests |
|---|---|---|---|
| R01 | `backend/story_builder/services/agent_tasks.py::poll,_find_job,_validate_job,_map_job`; `frontend/src/DirectorConversation.tsx::TaskCard` | Map frozen job after crash; do not create on GET; show recoverable state | task store, audio/continuity/computer jobs; no duplicate side effects |
| R02 | `backend/story_builder/services/agent_computer.py::run` | Bound stdin delivery along with runtime/journal, child cancellation | Linux sandbox, process-group kill, mock non-reading child; no real model call |
| UX01 | `frontend/src/{StudioShell,DirectorWorkspace,DirectorRuntime,DirectorConversation}.tsx`, `director-runtime.css` | Controlled chat/work visible state + always-visible restore; keep nav existing and all panes mounted | Playwright: each pane alone/collapsed; mobile, resize, project A/B, drafts |
| UX02 | `frontend/src/{VibeEditorPage,DirectorRuntime}.tsx`, `lib/agent-context.ts`, `backend/story_builder/services/{agent_conversation,agent_tools,agent_tasks,vibe_editor}.py` | Editor session/selection context and existing brief/plan command as typed shared action | old Editor range/CAS, exact approvals, no render on draft chat |
| UX03 | `frontend/src/{VibeEditorPage,EditorWorkspace}.tsx`, `vibe-editor.css` | Remove old Editor composer/log and nested two-pane only after UX02; keep right-hand controls and history | existing Editor session, two clearances, timeline/export, H3 source unaffected |
| UX04a | `ScreenplayDirector.tsx`, `ScreenplayPage.tsx`, story revision services | Replace secondary conversation with central scene/shot proposal; keep Apply selector | revision/CAS, transcript history |
| UX04b | `PromptDirector.tsx`, `PromptPreparationPage.tsx` | Central prompt/rule chat with work-surface diff+apply, preserve learning | exact prompt fields, saved lessons, stale revision |
| UX04c | `CreateWorkspace.tsx`, `TextToImagePage.tsx`, `ImageAssetsPage.tsx` | Remove old prompts chats after central typed refine+apply/field recovery parity | freeze base prompt, idempotency, reference/order, manual generation |
| UX04d | `TrellisPage.tsx`, `MediaPrepPage.tsx`, `StudioChat.tsx` | Retire only redundant chat component after settings Apply parity; **keep Media Prep processing intact** | `studioRequest` imports, EditorWorkspace reusable layout, tool APIs |
| AG01 | `agent_conversation,agent_api,agent_tools,agent_skills,agent_graph,agent_tasks` + typed frontend clients | Expand tool registry, pass real page/session/ranges, never generic unsafe executor | each new tool from Director and Editor, strict validation, project graph |
| AG02 | NEW small agent planning/QA/handoff modules + existing workers/Editor | Durable film step DAG, real media defect evidence and retakes, verified final assembly | existing jobs/ledger/save-load, Editor selected media, no fake completed film |
| CR01 | `ProductionStylesPage,ScreenplayPage,StoryboardPage` + style/story services | Optional production type, visual/directing jackets and comic panels | historical style snapshots, manual paths, scene/shot/clip identities |
| VID01 | `PromptPreparationPage,video-api.ts,isolated_*_contract.py,production_job_worker.py,production_ledger.py,t2v_pipeline.py` | Actual upload manifest; new separately versioned LTX-off route | exact H3 request schemas/digests, never alter old v2 jobs |

**Implemented first milestone:** R01/R02 and UX01 → UX02 → UX03; see [evidence and rollback](R01_UX03_RESULTS.md). Next remove old chats progressively under UX04, after each typed bridge reaches parity. These are engineering phases, not a mandatory user filmmaking wizard.

**Code review rule:** do not delete `EditorWorkspace.tsx` or `StudioChat.tsx` until every remaining import is migrated; the latter exports `studioRequest` used across pages. Do not touch `MediaPrepPage` business logic or replace `vibe_editor_render.py` to solve UI duplication. Preserve project state and legacy message history. Original generation and editor services remain the source of truth.
