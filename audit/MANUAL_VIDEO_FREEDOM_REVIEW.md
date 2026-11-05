# Manual Video freedom: scoped impact review

Overall impact risk: **high (0.70)** because admission shares the durable SQL job ledger. This is a change-impact score, not a defect probability. No measured test coverage is claimed.

Scope: manual Video Create, retake provenance, recovery, and advisory planned duration. Existing unrelated working-tree changes excluded. Graph discovery found 21 edges incident to `create_job`; current source remains authoritative.

| Risk | Node | File | Anchor | Reason |
| --- | --- | --- | --- | --- |
| 0.70 | def create_job( | backend/story_builder/services/isolated_video_jobs.py:2177 | `    def create_job(self, *, workspace_id: str, clip_id: str, idempotency_key: str,` | Direct: HTTP manual admission; Full/Assisted run callers and internal retakes retain strict default. New CPU tests exercise manual, stale, retake, replay and incompatible mode branches. |
| 0.60 | def app(environ, start_response): | backend/story_builder/isolated_server.py:480 | `    def app(environ, start_response):` | Direct: POST jobs opts into manual admission; definite pre-admission rejection marked. CPU HTTP tests, capability guard remains. |
| 0.60 | def queue_take( | backend/story_builder/services/production_ledger.py:232 | `    def queue_take(self, *, project_id: str, run_id: str, shot_id: str, take_id: str,` | Indirect: durable identity and request snapshot still reject changed-payload replay; CPU regression asserts it. |
| 0.40 | def _validate_story_source_lineage( | backend/story_builder/services/isolated_video_jobs.py:146 | `def _validate_story_source_lineage(db, story, workspace, clip, request, supplied, media_root=None):` | Indirect: valid metadata retained; stale manual recommendations become unlinked. Default strict rejection asserted. |
| 0.40 | const generate = async () => { | frontend/src/App.tsx:826 | `  const generate = async () => {` | Direct: definite rejection returns editable prompt; pending network ambiguity retains immutable snapshot. Browser lost response and rejection tests pass. |
| 0.40 | lineage = take.get("source_lineage") | backend/story_builder/services/assembly.py:146 | `        lineage = take.get("source_lineage")` | Indirect: manual media remains project-owned; stale/unverified shot link omitted rather than claiming screenplay conformance. Assembly permits null lineage; automatic screenplay candidate matching requires valid source lineage. |
| 0.40 | const formLocked = | frontend/src/App.tsx:457 | `  const formLocked = busy \|\| uploadingRefs \|\| uploadingFrameRole !== null \|\| hasPendingAttempt \|\| capState === 'loading' \|\| preparingShotPrompt;` | Consumer: planned duration restriction removed separately; in-flight/recovery protections remain. Browser planned-duration edits and final-only prompt checks. Nested callbacks absent from graph. |

Validation: 8 CPU tests (4 new manual-admission tests plus 4 worker-destination tests); 8 focused Playwright tests; production build passed (existing bundle warning). All 7 source citations verified by the skill verifier. No GPU generation.

Preservation: automation retains its explicit frozen-run checks; request-hash/idempotency conflicts remain; retakes retain original provenance. Unlinked free manual clips remain project media but do not automatically claim a screenplay slot. Unknown network outcomes retain recovery; definite non-admission releases the editable form.

High-impact follow-up: owner Generate-click render acceptance. No new dependencies, engines, storage migration, or screenplay regeneration.

Live browser inspection after idle-service reload: restored Lion_mouse draft still has a pre-existing pending attempt and an enabled Recover saved attempt button. No recovery/render POST was clicked. Therefore a clean live Generate submission is not claimed; current-request admission is covered by CPU HTTP tests and mocked browser tests.

## Recovery lock follow-up

The first fix left all workflow choices disabled on an existing pending attempt. Added a safe return-to-editing route: atomically recover the admitted job, or fence its old key before releasing an unsubmitted draft. The fence is checked inside the same ledger admission transaction, so a delayed POST cannot create a duplicate after release. On reload, a missing saved job releases safely; an explicit Return to editing action also handles lookup outages. No prompt/reference/retake edits are deleted.

Checks: 2 CPU release tests (including a concurrent submit/release), extended HTTP admission/recovery test, 3 browser recovery tests, production build. No GPU generation. Previous live limitation above describes the earlier patch; the follow-up addresses its pending-attempt lock.

| Risk | Follow-up node | File | Anchor | Reason |
| --- | --- | --- | --- | --- |
| 0.60 | release_attempt | backend/story_builder/services/isolated_video_jobs.py:2670 | `    def release_attempt(self, *, workspace_id: str, idempotency_key: str) -> dict[str, Any]:` | Atomic release / recovery; focused CPU and browser tests. |
| 0.40 | returnToEditing | frontend/src/App.tsx:558 | `  const returnToEditing = async (pending: Draft = draft) => {` | Atomic release / recovery; focused CPU and browser tests. |

Live restored Lion_mouse draft now clears the obsolete pending flag without a render POST. Workflow selector verification follows the backend reload; actual GPU generation remains owner acceptance.

Live verification: T2V, FFLF and R2V workflow buttons are all enabled on the restored Lion_mouse draft; pending=false. Generate still waits for reference library loading in this brief probe. No render POST was made.
