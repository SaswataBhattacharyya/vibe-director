# Combined fixes and guide assessment

> **HISTORICAL REVIEW (prior to the 2026-11-06 agent implementation).** This document describes the old code baseline and should not be used as the current work queue. Start with [current code review](CODE_REVIEW_2026-11-06.md), [active fixes](ACTIVE_FIXES_2026-11-06.md) and [single-chat UI plan](UNIFIED_CHAT_AND_PANES.md). Keep this assessment only for provenance/regression context.

Base: `f48e99a43ff141239504e802dd416ac7c48a0f63`, `vibe-director-current`; clean before this documentation pass. The 12 additions since `d467dbb269312eabe1ee7afe0697de5187857f61` were docs/engineering skills, not runtime fixes. This pass edits guides only.

## Bird's-eye view

| System | Reuse / authority | Missing connection or limit |
| --- | --- | --- |
| Ownership | `ProjectController.tsx`, `projects.py`, production ledger/image DB | Agent state must checkpoint; Editor `edit-*` session differs from owner workspace |
| Manual tools | Existing clients and story/image/audio/video services | Keep independent entry points |
| Director | Story/prompt reasoning, fixed skill loader | No shared tool executor or dynamic registry |
| Editor | Saved sessions/ranges, brief/plan approvals, trusted renderer | Restricted JSON planner, not general tool agent |
| Media Prep audio | Utility route → staging → durable media job → worker → registered asset | Shared submission seam, staging visibility, durable invocation mapping |
| Generation | Exact T2V/R2V/FL2VA contracts, immutable jobs/recovery | Preserve request/version families; LTX-off is not a UI boolean |
| Film finishing | Continuity helper, take history, assembly/Editor export | General task graph/evidence-backed QA; inspect audio/timeline limits |
| Skills/computer | Three live app skill paths; global Codex skills separate | Shared resolver and actual authorized execution runtime |

## Guide assessment

| Guide | Assessment | Correction |
| --- | --- | --- |
| Master/matrix | Needs adaptation | Canonical numbering; minimal durability precedes autonomous submission |
| Backend | Exact routing pattern; storage needs adaptation | Pass configured dependencies; checkpoint/import tests required |
| Services | Exact audio/continuity seams; incomplete sketches | Remove drop-in appearance; strict schemas, grants, roots, cleanup and uncertainty explicit |
| Tests | Useful isolation; too broad per phase | Tests per card; baseline failure visible; cleanup on failure |
| Frontend | Valid target; shell stability unproven | Inspect App branch mounting; inspector first; no duplicate chats |
| Typed client | Useful proposed shapes | Types only for implemented routes; reuse ranges; casts do not validate responses |
| Editor | Exact planner restriction | Shared orchestration alongside retained approvals/renderer |
| Skills | Correct source layers | Preserve current context first; register approved blueprint root intentionally |
| Engineering skills | Useful method | Global blast-radius/ponytail now available here; older absence claim is historical |

## Confirmed baseline: staged inputs appear as media

`audio_utilities.stage_assets()` writes `generated_root(...)/utility_inputs/<staging_id>/001.wav`. `media_library.list_assets()` calls discovery; recursive scanning does not exclude that managed subtree. The copied input can become a new catalogue record even when the job stops before output publication.

The prior review ran six `AudioUtilitiesIntegrationTests`: five passed (including real CPU MP3); `test_gpu_safety_trip_does_not_publish_completed_audio_utility_output` failed. Diagnostic listing showed extra `001.wav` with `metadata.folder_discovery=True`. This is staged-input discovery, not evidence that GPU output published after the stop. Q01 fixes the root cause; do not weaken the assertion. Temporary storage removal was verified, including the failed run.

Other prior-review checks: frontend typecheck passed; V2 package validation passed (71 manifest files, 13 skills, five JSON contracts). These are baseline observations, not fresh proof of this documentation edit or comprehensive runtime acceptance. No GPU/provider generation or browser acceptance was performed.

## Implementation traps

- `list_assets()` writes discovery records. `video_repertoire.read_job()` may mark a dead-PID job interrupted. Do not call them blindly in a read-only projection.
- `create_job()` uses configured module roots, freezes destinations and creates a fresh ID; it is not an idempotency API. Passing `root` to a helper alone does not configure storage.
- `start_job()` can leave a persisted queued job when dispatch fails. A 503 does not prove nothing can run. Reconcile before replay; retain inputs needed by retryable jobs.
- `last_frame(root, workspace, output, create=True)` expects generated output fields `shared_asset_id`/`sha256`, not any uploaded video ID. `create=False` still reaches media discovery.
- Flat exact `ToolSpec.fields` is not a nested/optional/default schema. Audio capability returns an `operations` list, not a top-level tool status.
- A mutable task row is insufficient immutable plan history. Store revisions/approved hashes separately, claim calls transactionally, persist job identity before dispatch.
- Snapshot import checks exact columns/conflicts. New rows require owner columns/FKs and compatibility tests. Draft tasks should not block Save; paused tasks can still own active workers.
- Simplification examples are not automatic fixes: object→Map changes contract; removing async can change synchronous errors/promise behavior. Preserve actual behavior.

## Blast-radius evidence and limits

Local graph: 145 nodes/634 edges. `graphify affected stage_assets --depth 2` found no unique node. A bounded BFS query found 42 candidates across discovery/library/server; output was limited, not a complete caller census. Source traces cover two levels for the first slice: utility route → staging/job store → worker/publication; browse → discovery → manifest; Editor command → range validation → renderer. Checkpoint readers were inspected separately. No source changes means no graph regeneration in this docs pass.

[Source citation report](../.review/guide-assessment.json) records the explicitly assessed boundaries. Scores prioritize proposed future code changes, not the Markdown diff or defect probability. Unknown test-gap factors are retained; source searches are not coverage measurement. Highest proposed boundary score: 0.60, possible 1.00 with unknown test-gap/caller-count factors (high). Source-line verification does not verify dependency claims or test sufficiency. This is not a repository-wide correctness/security audit.

The V2 package/manifest and historical reviews remain unchanged. Broad refactors, SDKs, full DAGs, independent storyboard schema, multi-track rendering and computer/external integrations need later plans; they are not quick fixes hidden in these cards.

## Assessed source boundaries (proposed changes)

Sorted by lower-bound risk; unknown caller/test factors remain in the JSON. No executable nodes changed in this guide-only diff. Anchors below were verified against the assessment base; scoring is not source verification.

| Risk lower–upper | Source location | Verbatim anchor | Why inspect |
| --- | --- | --- | --- |
| 0.60–0.70 | [audio_utilities.py:134](../backend/story_builder/services/audio_utilities.py) | `def stage_assets(data_root: Path, workspace_id: str, job_id: str, asset_ids: list[str], operation: str) -> list[dict[str, str]]:` | isolated_server.py:910 calls stage_assets; run_job reads its relative_path inputs; tests call staging directly. |
| 0.60–0.70 | [audio_utilities.py:161](../backend/story_builder/services/audio_utilities.py) | `def run_job(job: dict[str, Any], *, data_root: Path, progress: Callable[[dict[str, Any]], None]) -> list[dict[str, Any]]:` | video_repertoire_worker dispatches audio-utilities to run_job; media_library.register_generated_audio publishes results. |
| 0.60–1.00 | [media_discovery.py:48](../backend/story_builder/services/media_discovery.py) | `def _discover_locked(root, workspace, *, shared=False, kinds=None):` | media_library.list_assets -> discover -> _discover_locked -> media_library._save; browse therefore writes. |
| 0.60–1.00 | [media_library.py:385](../backend/story_builder/services/media_library.py) | `def list_assets(root: Path, workspace_id: str, *, kind: str &#124; None = None, limit: int = 50,` | video_continuity.last_frame invokes list_assets; list_assets invokes media_discovery.discover before projecting manifest. |
| 0.60–1.00 | [video_repertoire.py:806](../backend/story_builder/services/video_repertoire.py) | `def create_job(kind: str, request: dict[str, Any]) -> dict[str, Any]:` | Utility POST calls create_job -> output_destinations.freeze + atomic job JSON under configured root -> start_job. |
| 0.60–1.00 | [video_repertoire.py:975](../backend/story_builder/services/video_repertoire.py) | `def start_job(kind: str, job_id: str) -> dict[str, Any]:` | Utility route calls start_job; it writes queued job state before media queue/dispatcher readiness. |
| 0.60–1.00 | [video_continuity.py:13](../backend/story_builder/services/video_continuity.py) | `def last_frame(root, workspace, output, *, create=True):` | isolated_video_jobs calls last_frame with owned generated output descriptor; helper verifies video bytes/hash. |
| 0.60–1.00 | [projects.py:102](../backend/story_builder/services/projects.py) | `def sql_snapshot(path, workspace):` | Project save calls sql_snapshot for configured production/image databases; load checks known table schemas, columns and conflicts. |
| 0.60–1.00 | [vibe_editor.py:231](../backend/story_builder/services/vibe_editor.py) | `def command(root, project_id, body):` | vibe_editor_api.handle routes command requests; command calls validate_selection before admitting approved brief/plan/render changes. |
| 0.60–1.00 | [vibe_editor.py:379](../backend/story_builder/services/vibe_editor.py) | `def run_job(root, job_id, request, progress):` | video_repertoire_worker dispatches vibe-editor jobs; render branch delegates vibe_editor_render.render. |
| 0.40–0.80 | [director_skills.py:10](../backend/story_builder/services/director_skills.py) | `def director_skill_context(*, video: bool = False) -> str:` | story_authoring, prompt_drafts and fully_automated_clip_plan call this helper; it reads fixed craft paths and hashes content. |
| 0.40–0.80 | [projects.py:135](../backend/story_builder/services/projects.py) | `def assert_idle(root, workspace):` | Project transitions call assert_idle; it examines snapshot status and persisted media job JSON. |

Verification command: `python3 /home/riki/.codex/skills/blast-radius/scripts/citation_verifier.py .review/guide-assessment.json --root .` returned 12 checked, zero rejected. It checks anchors only.
