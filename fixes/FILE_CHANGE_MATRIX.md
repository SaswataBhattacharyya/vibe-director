# Source/change routing matrix

Current implementation: [Q07–Q08 results](Q07_Q08_RESULTS.md), including persistent conversation, notes and shell foundation. Remaining phase rows are future work.

Canonical scope: [master](change_readme.md). Detailed instructions: [task cards](QUICK_FIX_TASKS.md). Evidence: [assessment](SOURCE_ASSESSMENT.md). Service names below live in `backend/story_builder/services/`.

| Card / phase | Inspect existing anchors | Proposed edit boundary | Consumers / acceptance |
| --- | --- | --- | --- |
| Q01 / preflight | `audio_utilities.stage_assets/run_job`, `media_discovery._discover_locked`, `media_library.list_assets` | Managed staging discovery exclusion; preserve job path compatibility | Audio utility and recursive discovery regressions; originals/legitimate outputs retained |
| Q02 / 2 | Utility route in `isolated_server.py`, `video_repertoire.create_job/start_job` | One shared submission helper; manual route delegates | All three operations, 202/503 errors, configured roots, frozen destinations, uncertain dispatch |
| Q03 / 1 | `isolated_server.create_app`, capability adapters | New `agent_tools.py`, `agent_api.py`, narrow dispatch seam | Metadata only; strict routes, owner checks, no execution |
| Q04 / 1 | `director_skills.director_skill_context`, Editor `run_job` skill reader | New `agent_skills.py`; compatibility facade after parity test | Story/video/Editor context, global/app/project isolation, budgets |
| Q05 / 1 | Story/board records, manifests, job JSON, Editor state | New `agent_graph.py`, owned context endpoint | Derived IDs/hashes; no mutating browse/recovery calls under read-only label |
| Q06 / 1 | `StudioShell.tsx`, `App.tsx`, `ProjectController.tsx`, `lib/editor-api.ts` | `AgentInspector.tsx`, `lib/agent-api.ts`, `lib/agent-context.ts`, narrow shell wiring | Same discovery on Director/Editor; project switch/direct routes/mobile; no submit |
| Q07 / 2 | `production_ledger.py`, `projects.sql_snapshot/assert_idle`, media job store | Small `agent_tasks.py`, immutable plan/call/event tables, lifecycle API | Stale approval, crash/reconcile, duplicate request, Save/Load |
| Q08 / 2 | Director/Editor chat entry points, Q02/Q07 | One-operation chat bridge; registered result/attachment proposal | Real CPU MP3, session/workspace/ranges, late responses; no soundtrack replacement |
| Phase 3 | Q07, checkpoints and shell | Persistent chat, multistep execution, reviewed knowledge/skill bindings | New schema/transition plan; no parallel story authority/task engine |
| Phase 4 | Style/screenplay/storyboard pages and services | Optional jackets, scene proposals, comic panels; independent board schema separate | Published history, revision/CAS, panel/shot/clip distinctions, no manual gates |
| Phase 5 | Prompt/video clients, continuity, exact video contracts | Reference manifests/adapters; separately version LTX-off | Route fields/durations, hashes, voice vs dialogue, frozen jobs |
| Phase 6 | Editor/render/assembly services | Verified QA/retakes/handoff/export; extend renderer for proven gaps only | Actual observations, immutable takes, ranges, audio/timeline limits |
| Phase 7 | Real installed runtime/license/auth interfaces | Optional scoped computer/browser/coding/external adapters | Permissions/audit/output registration; native workflow independent |

Large files are not rewrite targets. Extract only the approved seam; do not append a second business implementation to the dispatcher or App.

Current continuation: approved CPU last-frame PNG and scoped Codex computer tasks are implemented alongside MP3. Both surfaces offer Application tools, Project only and Full access; each computer task freezes scope and requires exact approval. Offline sandbox and mocked worker tests differ from unperformed live model acceptance. Browser/desktop automation and general film orchestration remain incomplete. See `Q07_Q08_RESULTS.md` for evidence and changed files.
