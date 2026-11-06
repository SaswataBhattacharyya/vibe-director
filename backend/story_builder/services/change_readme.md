# Service guide: reuse engines, connect narrow seams

Implementation scope is defined once in [task cards](../../../fixes/QUICK_FIX_TASKS.md); [assessment](../../../fixes/SOURCE_ASSESSMENT.md) records source traps. Do not copy historical snippets as ready implementations.

| Approved card | Service boundary | Preserve |
| --- | --- | --- |
| Q01 | Precise staging exclusion in discovery | Existing staged paths/retry inputs, originals, legitimate generated media |
| Q02 | Shared audio utility submission | All operations, settings/defaults, errors, destination freezing, configured roots |
| Q03 | Tool metadata and strict API | Actual capability shape, separate execution permission, no worker launch |
| Q04 | Shared bounded skill resolver | Existing context/labels/references, explicit roots, owner/hash/provenance |
| Q05 | Derived non-mutating context | Existing IDs/revisions, no second story source or hidden discovery writes |
| Q07 | Durable one-operation lifecycle | Immutable approvals, crash reconciliation, job identity, checkpoint parity |
| Q08 | Both chat bridges | Existing provider structured JSON, host validation, registered results and Editor approvals |

## Submission failure distinctions

Partial staging with no durable job may be cleaned by its creating call. Once a durable job exists, preserve its inputs on dispatch failure. `start_job` can leave a queued job: returning 503 does not authorize deletion or a duplicate submission. `create_job` uses globally configured roots and new IDs; a root argument or unique agent DB key alone does not solve cross-store crash windows. Q07 requires a correlation/reconciliation design.

## Tool/skill boundaries

Use exact nested schemas at the API boundary, including defaults and finite numeric/type checks. A flat key-set check is not sufficient. Audio availability is selected from `capabilities()['operations']`. Separate support/readiness/permissions; discovery cannot execute commands. Avoid backend self-HTTP and a generic shell/URL tool dispatcher.

One resolver serves both agents. Skills are instructions, not grants. Load metadata first, selected content/references within configured roots and budgets. Keep existing three craft paths and hashes/output compatibility before changing readers. No automatic activation of all 13 blueprint skills.

`video_continuity.last_frame(root, workspace, output, create=True)` consumes generated output metadata with `shared_asset_id`/`sha256`; it is not a generic uploaded-video extractor. `create=False` can still trigger discovery through media listing. Treat frame creation as a write tool, not Phase 1 metadata.

## Later phases: design first

- Creative records: reuse versioned production styles, source/graph/screenplay CAS and storyboard associations. Panels, shots and generated clips are distinct identities. Standalone storyboard drafts need a separately reviewed ownership/schema design.
- Video preparation: T2V, R2V and FL2VA have different exact fields. R2V continuity is a spatial reference; FL2VA owns true first/last frames. Preserve separate image/audio/video slot numbering, hash-bound references and voice-identity vs dialogue distinction. Derive durations/limits from current route validators; R2V requires strictly fewer than 7000 Unicode code points.
- LTX-off: new version/profile/digest plus original collection validation and direct final publication, not an extra field in frozen v2. Preserve old pipeline/recovery; test zero refinement enqueue, audio/video validity and all workflow families.
- QA/retake: actual observations with timestamps, preserve take history, verified media handoff. Missing analyzer means blocked, not invented findings.
- Computer/external: separate authorized runtime, allowlisted roots/actions, audit, real capability/license/auth checks. Not supplied by a coding skill.

No broad simplification of ledger/dispatcher/renderer while adding a gateway. Readability work gets one named function, behavior tests and a separate diff.
