# Isolated execution boundary — initial T2V slice

Implementation direction selected on 2026-10-08 following the user's instruction to start. This is a technical mapping subordinate to the current product plans, not a second story pipeline.

- Retain Story Builder's SQLite ProductionLedger and ProductionJobWorker with their submission locks, reserved Comfy prompt identity, ambiguity handling and GPU safeguards. Source closure matches mooV_E_maker commit `2023bf5bce1a808b2624fb5789b4b2a1e8b7b8db`.
- Expose workspace/clip/job/take identities. Inside the existing ledger, `project_id` stores workspace identity and `shot_id` stores an independent clip slot. No scene, screenplay or story record is manufactured.
- New mapping and asset metadata tables share that ledger database. They provide isolated idempotency, output provenance and candidate retention; execution state stays in the existing production take rows.
- Isolated runs are user-directed and do not require an automation mode. Do not expose a separate Manual mode or inherit legacy Director gates. Story-linked automation follows the two modes in `automation.md`.
- Returning to the input form for a retake never queues a render. Preserve the full request and explicit keep/discard choice; a later Generate click creates a new immutable attempt. Unknown submission outcomes remain attached to the reserved prompt and cannot be implicitly retried.
- Use explicit external runtime/evidence locators. Do not copy models, generated media, source databases, credentials, old pages or OpenMontage code. The new product owns its own data directory.
- The first screen is a reviewable React slice reusing the source theme and UI atoms. FFLF/R2V and Codex annotation are shown as unavailable until integrated. Browser/offline checks and native render acceptance are separate evidence.

Parent review and focused restart/idempotency/recovery checks are required before applying this slice to the canonical repository. Native rendering is tested only after readiness and GPU monitoring are shown in the UI and the user clicks Generate. Existing legacy test evidence is retained; no broad rerun is planned.
