# Small implementation backlog and collaboration

**Status:** proposed issues/PR sequence. No issues, PRs or invitations were posted. Product source remains unchanged. This plan is the concrete basis for the next implementation step.

## Work together through one private repository

Owner: `SaswataBhattacharyya`. Product/intellectual collaborator: `ashucodesbio`.

Both should have repository access sufficient to create issues/branches/PRs, review and merge. Keep repository administration with the owner. Use a branch per small issue and PR review for main; agree that the other person reviews meaningful product/architecture changes. Availability/enforcement of branch rules for a private repository depends on its actual account/repository configuration, so inspect that configuration when setting up rather than claiming a gate is already enforced.

Use issues to agree customer behavior and acceptance, then PRs to review a concrete change. Ashu's reviews can focus on intent, journey, language, defaults and output quality; technical review covers contract/data/recovery preservation. Either person may implement or merge an approved change. Intellectual collaboration should be visible in decisions, not reduced to coding assignments.

Suggested issue fields: customer problem, capability IDs, source files, proposed scope, acceptance, existing behavior to preserve, explicit open decision and evidence links. PR fields: linked issue, copied/extracted files, behavior change, verification, UI screenshots where useful, data/config changes and rollback. Avoid requesting approval for a vague implementation direction when a reviewable artifact can be prepared first.

## Phase 0 — Agree and freeze the migration baseline

| Issue / PR | Scope | Acceptance |
|---|---|---|
| M01: Baseline manifest | Capture current source revision/dirty-file hashes, selected release evidence and source-copy exclusions | Manifest reproduces copied inputs; original source untouched; no huge models/media/secrets in source set |
| M02: Product map review | Review capability catalog, the independent authority/route choices and workspace tabs with Ashu | Written decisions/corrections; capability gaps retain honest labels; no feature silently discarded |
| M03: Repository conventions | Private repo, collaborator access, issue/PR templates, review agreement and CI shape | Both can participate; permissions/rules verified in actual repository; source/data exclusions documented |

M01 and local planning refinement can proceed before remote setup. No external message to Ashu is implied by this plan.

## Phase 1 — Faithful source copy and configuration

| Issue / PR | Scope | Acceptance |
|---|---|---|
| M04: Owned source copy | Apply the exact map in document 04 and preserve relative package layout | Byte comparison for unchanged files; every route/page/required analyzer import has its source dependency; no nested Git/runtime trees |
| M05: Safe fixture mode | Central root configuration and isolated stores; lifecycle consumer disable/control | Fixture startup cannot resume source queued work; source project/engine data untouched; roots validated |
| M06: Paths and launcher | Update allowed roots, ports, graph/evidence lookups and startup ownership | Existing safe env values documented; no implicit model downloads; no competing consumers/shared-GPU locks |
| M07: Parity checks | Run applicable existing CPU backend/frontend checks on the copied package | Results recorded as new evidence; legacy/source failures distinguished; no paid/GPU calls in CPU CI |
| M08: Data snapshot and entry-point cutover | Preserve selected production data and evidence using manifest/WAL-safe sequence | IDs/hashes/accepted ancestry and media resolve; held jobs remain held; old writers stopped; rollback snapshot available |

Do not start M08 until isolated parity and writer ownership are clear.

## Phase 2 — UI structure around the working app

| Issue / PR | Scope | Acceptance |
|---|---|---|
| M09: Navigation and URL scope | Projects/Create/Library/Automations/Jobs plus project/run/shot routes | Existing pages still reachable; project switching/back/refresh cannot use stale run; no provider call on navigation |
| M10: Header and Story desk | Extract saved configuration and story/stage review components | Manual/Semi/Full behavior preserved; revisions/gates visible |
| M11: Bible and shared asset picker | Extract character/world/candidate/voice panels | Required masters follow making route; accepted assets retain identities; shared source not duplicated/deleted |
| M12: Shot desk | Extract scene list, prompt/ref/order/validation/settings | Exact reference tags/order preserved; stale proposals rejected; validation performs no render |
| M13: Take review and Jobs | Native playback, history/evidence and read-only aggregate job views | Completion versus acceptance clear; owner-specific retry/cancel/reconcile; no duplicate submission |
| M14: Audio workbench | Reuse timed TTS/effects/music/Foley/utilities forms as recipes | Contracts/duration/timing/speaker bounds preserved; original/derivative comparison works |
| M15: Research and Library | Reuse repertoire and legacy reference search through a common picker | Existing clips/corpus/voice sources remain usable; evidence/provenance visible |
| M16: Delivery | Accepted-media selection and manifest; retain named legacy composition | Raw output index not confused with accepted delivery; original native audio retained; no full-film promise |

One extraction PR should change one panel/flow. Reuse existing state/client functions and only adjust behavior where the issue explicitly requires it.

## Phase 3 — Backend boundaries and targeted repairs

| Issue / PR | Scope | Acceptance |
|---|---|---|
| M17: API shared dependencies/lifecycle | Extract stores, root resolvers, worker construction and schema ownership | Startup/shutdown/idempotency/recovery preserved; compatibility imports work |
| M18: Domain routers | Move one router group per PR using document 04 | Exact method/path/request/response parity, project ownership and relevant tests pass |
| M19: Pause-tag adapter | Separate engine control tags from speaker tags in website SRT preparation | `[Alice] Hello [pause:1s]` and wait/stop aliases survive; speaker/language validation still rejects unknown identities; CPU parser tests before bounded runtime check |
| M20: Audio pipeline support labels | Mark missing noise/Demucs adapters and input-bearing Foley bindings before run | Unsupported blocks cannot be launched as working; direct utility/Foley features remain reachable |
| M21: Audio pipeline adapters | Add one missing executable block/binding at a time when selected | Typed input/output, per-step manifests and safe retry preserve prior outputs |
| M22: Reconstruction acceptance UI | Wire existing accept endpoint and clarify metadata-only calibration | Exact uploaded take can be reviewed/accepted; no claim of model calibration/automatic ASR |
| M23: Story Canvas passage editing | Replace local request annotation with a real revision-bound edit only when selected | Original source retained, selected span verified, stale selection rejected; no fake generated prose |

M19 and M20 are high-value, small repairs directly evidenced by source. They can precede broad router extraction if prioritized.

## Phase 4 — Optional arsenal adapters

Choose these by actual customer need, not by number of files available:

1. One Wan/LTX recipe with explicit API graph export, ordered inputs, preflight and one representative acceptance.
2. Pose/multi-angle image recipe for a defined character/world need.
3. StyleTTS2 standalone inference adapter with explicit external checkpoint root, job ownership and output acceptance.
4. Unique SRT/alias/report tooling adapted from Art_ist_min.
5. Hunyuan Foley or 3D/VFX expert recipe only with required runtime verified.
6. Custom voice/music training workflow: preparation, bounded smoke, checkpoint/artifact tracking and quality evaluation before exposing full training.
7. Complete-film assembly: timeline, clip order, audio mixing, transitions/titles and export semantics as a separate product feature.

Existing expert graphs remain discoverable throughout. A missing adapter does not justify deleting their source graphs.

## Verification and credit discipline

- Preserve lockfiles and source tests; do not upgrade dependencies during a UI extraction unless a concrete blocker requires it.
- CPU/parser/ownership/contract tests and mocked browser flows are the default development gate.
- Existing recorded render evidence is reusable context but does not certify changed graph/compiler versions.
- Only rerender to resolve an actual changed inference contract or live runtime risk. Retain prompt/model/hash/evidence to avoid repeating the same verification.
- Keep image candidate counts, bounded provider calls and retake limits unchanged during reorganization.
- Do not regenerate accepted stories/assets solely because their UI location changed.
- Stop broad retesting after the relevant acceptance is established; report remaining optional gaps explicitly.

## Decisions for the next implementation kickoff

The migration direction and destination folder are already settled. Remaining choices are the first PR scope, whether Ashu uses fixtures or the shared engine, which optional recipes are customer priorities, and whether remote application hosting is in scope. These do not block the planning files or faithful source manifest preparation.
