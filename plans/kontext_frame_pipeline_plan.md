# Kontext keyframes and shared interpolation tools

Status: implemented locally, with focused mock/CPU/browser checks. Read-only
ComfyUI probes confirm Kontext and both interpolators are currently discoverable.
Owner-generated-media acceptance remains pending; no GPU generation was run.
See [usage and implementation details](../docs/FRAME_PIPELINE_USAGE.md).

The design below records the approved intent. The implementation uses one additive
`frame_pipeline_takes` table containing revisioned keys/events, and existing image
and media jobs, rather than duplicating histories across three new tables. Routes
follow `/api/frame-pipeline/{workspace_id}`. Shared review UI lives in one small
panel; the existing FFLF workflow receives endpoints through an explicit new-draft
handoff, without changing screenplay selections or frozen requests.

## Objective and authoritative inputs

Add FLUX.1 Kontext Dev to the existing image-generation choices. Recommend it
for iterative first/last-frame (FFLF) editing when an approved reference exists;
keep Z-Image and Qwen available. Add FILM/RIFE interpolation and video export as
shared application tools usable from Director and Editor, with manual controls.
These tools require project ownership and valid media, not an accepted screenplay
or storyboard. Preserve navigation, Media Prep and existing generation workflows.

The supplied handoff is preserved verbatim in
[`docs/VIBE_DIRECTOR_FRAME_PIPELINE.md`](../docs/VIBE_DIRECTOR_FRAME_PIPELINE.md).
It records backend validation elsewhere, not Vibe Director runtime acceptance.
Current application source remains authoritative for integration behavior.

Local inspection confirmed these files under
`/home/riki/web_dev/setup_comfy_and-stuff/workflows/ricky/`:

- `api/flux_kontext_recursive_frame.api.json`: LoadImage 1, instruction 7,
  FluxGuidance 8, KSampler 11, SaveImage 13; actual ReferenceLatent conditioning.
- `api/film_frame_interpolation.api.json` and
  `api/rife_frame_interpolation.api.json`: LoadImage 1/2, loader 4,
  interpolation 5, SaveImage 6.
- `recursive_frames.py`, `interpolate_frames.py`, `finish_shot.py`.

The installer records and model matrix exist under the same checkout at
`env_setup/shared_krita_vibe_20261108/`. Do not copy weights, environments,
historical demo media or Krita-specific graphs into this application.
Do not install another ComfyUI or change its Python/CUDA environment.
No live capability probe, inference or performance measurement was made here.

## Existing seams and impact

| Existing files | Reuse and proposed change |
| --- | --- |
| `backend/story_builder/services/production_image_workflows.py` | Add `flux_kontext_dev` specification, readiness, typed settings validation and graph compilation. Keep existing workflow versions/graphs stable. |
| `services/isolated_image_references.py` | Extend validated reference staging for Kontext without assuming a host absolute path is a ComfyUI filename. |
| `services/production_image_jobs.py`, `production_image_worker.py` | Reuse immutable jobs, prompt-ID reservation, history recovery, asset registration and owned staging cleanup for single-key generation. |
| `services/image_prompt_context.py`, `image_prompt_drafts.py`, `director_skills.py`, `agent_skills.py` | Add model-specific editing guidance and allow valid Kontext references; preserve existing Qwen/Z-Image behavior. |
| `services/production_image_selection.py`, `production_image_admission.py` | Preserve current selected first/last frame identities; explicitly apply an approved chain endpoint to the existing selection mechanism. Do not make chain generation a required production step. |
| `backend/story_builder/isolated_server.py` | Wire project-scoped frame actions and readiness beside current image routes; keep business logic outside this large router. |
| `services/agent_tools.py`, `agent_tasks.py`, `agent_conversation.py` | Register, propose and execute the new tools through the existing shared task lifecycle, including Editor context. |
| `services/video_repertoire.py`, `video_repertoire_worker.py`, `gpu_runtime.py` | Reuse durable jobs, output artifacts and shared GPU admission/watchdog; interpolation is GPU work, FFmpeg export is CPU work. |
| `frontend/src/TextToImagePage.tsx`, `ImageAssetsPage.tsx` | Kontext choice with required reference and correct defaults; first/last frame recommendation and entry to reviewed keyframe editing. |
| `frontend/src/lib/image-api.ts`, `lib/story-api.ts` | Extend workflow contracts; remove assumptions that every image workflow uses the same settings/reference limits. |
| `frontend/src/DirectorRuntime.tsx`, `DirectorConversation.tsx`, `VibeEditorPage.tsx` | Show shared tools/results and open the same review workspace from either surface. Preserve composer state. |

Backend paths abbreviated as `services/` above are under
`backend/story_builder/`. New modules below are proposed names, not existing code.
Before each implementation batch, trace its exact callers and persisted consumers
and check current dirty changes. The existing Graphify graph has 5,588 nodes at
inspection; that count does not establish freshness or coverage for new features.
This is a scoped source-based design, not a whole-working-tree code review.

## Shared design and persisted contracts

Prefer one project-owned frame-pipeline module with a small interface: create a
take, request next candidate, review candidate, branch, interpolate and export.
Director, Editor and manual controls call that same interface. Compare two options:
wrapping the external CLI runners would be quick but would add a separate manifest,
process and recovery system; using existing Vibe jobs gives more reuse and one
approval/history model. Choose existing jobs, treating runners as reference
implementations. Check source licensing before copying any graphs or code; retain
notices and provenance. Pin imported API graphs with source hashes/version.

Proposed additive SQLite records, using the current project database/ownership
conventions rather than a second project system:

- `frame_takes`: ID, project ID, optional existing shot/clip link, parent take ID,
  branch point, current revision, explicit canvas size and active head key ID.
- `frame_keys`: ID, take ID, predecessor key ID, ordinal, existing asset ID and
  SHA256, source/reference hashes, job ID, frozen prompt/settings, workflow hash,
  candidate/review state and review revision. Start images also require approval.
- `frame_events`: append-only approve/reject/replacement/branch events with
  expected revision. A manual replacement creates a new asset/key, never mutates
  the approved original.

Use existing job records for engine prompt IDs, frozen graphs, recovery, export
manifests and artifact ownership; add columns/tables only if the current job
contract cannot represent those fields. Do not duplicate asset or job histories.
Schema migration must be additive and idempotent. Unique keys and transactions
must prevent concurrent next-key requests against the same take revision.

Rewind creates a new branch from approved key N; descendants remain in the old
take. Generation consumes only the approved current head. Failed/rejected keys
never become recursive inputs. Review requires the expected revision and exact
asset hash. No automatic approval by chat.

Proposed project-scoped routes under `/api/projects/{project_id}/frame-pipeline`:
`GET /capabilities`, `POST /takes`, `GET /takes/{id}`,
`POST /takes/{id}/next`, `POST /takes/{id}/review`,
`POST /takes/{id}/branch`, `POST /takes/{id}/interpolate`,
`POST /takes/{id}/export`. Mutations carry idempotency and expected-revision
fields. Responses use existing job/asset IDs and actionable structured errors.
Final route naming should follow the actual router conventions during implementation.

Proposed shared tools: `image.generate_next_keyframe`,
`video.interpolate_keyframes`, `video.export_frame_sequence`. Chat may propose
them from Director or Editor. User review approves media; existing explicit Run
controls authorize GPU work. An approved task is distinct from an approved image.
Never invoke GPU work simply to prepare a prompt or inspect readiness.

## Phase 1 — Kontext alongside image tools

1. Audit licenses/provenance, pin the Kontext REST graph in
   `backend/story_builder/workflows/api/flux_kontext_recursive_frame.api.json`.
2. Add its specification and true reference-conditioning compilation. Defaults:
   guidance 2.5, 20 steps, CFG 1, denoise 1, Euler/simple. Make reference count
   explicit; start with one approved source for recursive editing.
3. Probe `/object_info` for required node inputs and actual model choices. Report
   missing nodes/models/backend address precisely. Existing external validation
   is not sufficient to enable a currently unreachable backend.
4. Reuse image worker recovery/staging/publication. Its current flow reserves a
   prompt ID before submission; preserve that stronger behavior. Confirm backend
   support and reconcile uncertain receipts without blind retries.
5. Add Kontext in Text to Image and First & Last Frames. Recommend it only when a
   usable reference exists. Starting from text alone still uses a text generator
   or an imported image; Kontext must not silently become plain FLUX text-to-image.
6. Add `skills/flux-kontext-prompting/SKILL.md` and discovery wiring: explicit
   requested change, preserved identity/style/background/camera, honest drift
   limits, user-approved learning through existing project knowledge.

Normalize the starting canvas deliberately before the first edit; native buckets
can change dimensions. Show the actual output size and prevent silent resizing
of later approved keys. Do not claim preservation prompts guarantee consistency.

Focused checks: existing image compiler/reference/job regressions; new Kontext
bindings and missing-dependency tests; source tamper, uncertain receipt and
output-node selection tests; browser workflow/reference/defaults and unchanged
prompt on inspector toggle. CPU/mocks first; owner Generate for real acceptance.

## Phase 2 — Reviewed iterative takes and FFLF connection

Add `services/frame_pipeline.py` and `services/frame_pipeline_store.py`, plus
small `FramePipelineWorkspace.tsx` and `FrameKeyReview.tsx` modules and
`frontend/src/lib/frame-pipeline-api.ts`. Implement the records/routes above.

Show source/candidate side by side, changed instruction, actual dimensions,
seed/settings, approve/reject, manual replacement and branch-from-key controls.
Keep timeline/key history visible. Generation pauses after each candidate.
Allow standalone project use with optional shot linkage. Explicitly select a
take's first/last approved keys for the existing FFLF workflow; preserve saved
selection history and frozen video requests. Do not silently replace a saved
video draft's references when a new take is approved.

Focused checks: revision races, project isolation, hash tampering, duplicate
requests, reject/resume, replacement ownership, branch ancestry, project reopen,
selected endpoint mapping and existing FFLF request/retake regressions. Browser
approval/rewind/reload and standalone creation with no screenplay.

## Phase 3 — FILM/RIFE and verified silent video export

Pin the two REST graphs after license/provenance review. Add
`services/frame_interpolation.py` and `services/frame_sequence_export.py` behind
the shared frame-pipeline interface. Reuse durable media-job dispatch rather than
running the standalone scripts directly. Add a small interpolation/export panel.

- Ordered approved keys, equal actual decoded dimensions, unchanged hashes and
  one continuous shot are required. Do not interpolate across cuts.
- Build an ordered ImageBatch chain for N keys. Model choice RIFE by default for
  the described anime use case; FILM remains available. Integer multiplier 2–16.
- Validate `(N-1)*M+1` returned frames, ordering and original keys at multiples
  of M. Inspect installed node implementation for any image round-trip tolerance;
  do not assume byte-identical PNG encoding. No duplicate segment boundaries.
- Download only SaveImage output records; persist sequence manifest and hashes
  before any ComfyUI retention cleanup. Keep engine histories for recovery.
- Expose FPS, endpoint holds and the resulting quantized frame count/duration
  before Run. Four keys at M=16 give 49 frames; 24fps plus 0.5s holds at each end
  gives 73 frames, about 3.04s. FPS alone cannot create additional motion.
- Export preview H.264/yuv420p MP4 and optional FFV1/gbrp lossless MKV using
  existing FFmpeg. Validate finite limits, supported dimensions, disk budget,
  frame count/duration, codec and decode success with FFprobe/FFmpeg before atomic
  publication. Use argument arrays and owned paths, no provider-authored shell.
- Outputs are silent. Preserve any source audio as a separate asset; attaching
  or generating sound remains a separate existing workflow.

The export command templates and runnable references are retained in the handoff
and external `finish_shot.py`. Harden resume: that script skips an existing output
by filename, whereas Vibe must verify its manifest/hash/probe before reuse.
Partial export files must never be registered as completed media.

Focused checks: mocked FILM/RIFE graph bindings, output count/order, dimension
rejection, original-key placement, uncertain submission, recovery and cancellation;
CPU synthetic PNG-to-video export including holds, lossless output, corruption
and partial publication. No live interpolation during automated validation.

## Phase 4 — Director and Editor tool integration

Wire the proposed tools through `agent_tools.py`, `agent_tasks.py` and
`agent_conversation.py`; add `skills/frame-interpolation/SKILL.md`. Both chat
surfaces use the same skill discovery, task records, project asset ownership,
frame review controls and result artifacts. Tool descriptions must distinguish
frame creation, interpolation and export and require ordered asset IDs/hashes.
A generated result appears once in the shared project media library; Editor can
select it through the existing picker. Chat should open the review workspace for
missing approvals rather than inventing approvals or demanding a screenplay.

Test both chat surfaces with mocked reasoning: sparse request clarification,
model recommendation, proposed settings, explicit execution, progress/cancel,
reconnect, changed inputs, unavailable backend and Editor import. Browser tests
must verify attachment/inspector actions preserve the current message draft.

## Deferred optional ControlNet work

Do not expand this first delivery to every installed model family. Keep the
handoff's compatibility matrix as guidance, then validate one requested family
at a time against the retained `MODEL_MATRIX.csv` and live nodes. ControlNet
prepares an image in its matching base family, which can then be approved and
fed to Kontext. Do not connect arbitrary SDXL/Noob controls directly to Kontext.
Qwen Edit 2511 is distinct from Qwen Image 2512 ControlNet. MOSAIC and deferred
FLUX.2/Qwen2.1 paths must not appear as available tools.

## Execution safety, tests and rollback

Serialize application GPU work through existing admission/watchdog and check
shared ComfyUI occupancy before submitting. An application lock cannot prevent
an external Krita client racing to submit: document that limitation and avoid
claiming global arbitration unless the shared backend provides it. Never clear
the global queue or interrupt an unrelated prompt. Keep 90°C/2100MHz policy and
existing provider guards unchanged. Use configured backend address; localhost
inside a container may point to the wrong process.

New tests: `test_kontext_workflow.py`, `test_frame_pipeline.py`,
`test_frame_interpolation.py`, `test_frame_sequence_export.py`,
`test_agent_frame_pipeline.py` and `frontend/tests/frame-pipeline.spec.mjs`.
Run focused existing image/FFLF/agent/Editor regressions once per relevant change;
broaden only on failure or unresolved risk. Refresh Graphify after meaningful
code changes using the project command and verify coverage of changed modules.

All synthetic media and test databases belong to isolated temporary directories.
Use fixtures/finally cleanup even on failure, terminate owned test jobs, then
assert those directories and test-owned records are absent. Never remove user
media, installed models, production history or the external workflow repository.
Real owner-content checks remain separate: Kontext drift, interpolation artifacts,
review usability and output acceptance require the owner's Generate click.

Rollback per phase: stop admitting only the new workflow/tool, let owned jobs
settle or reconcile them, restore that phase's code using a reviewed patch
without resetting unrelated dirty work, and leave additive tables/assets/history
intact. Disable the new UI entry if reverting code with retained pipeline data.
Do not automatically drop tables or delete generated media on rollback. Existing
Z-Image, Qwen, FFLF and Editor paths must continue to read their saved records.

The external install report flags Kontext Dev model-use restrictions. Preserve
its license attribution and distinguish model-use terms from output-use terms;
verify applicable terms before deployment. Backend test times in the handoff
are historical samples, not app performance or memory guarantees.

## Completion criteria

One project can generate/edit a key with Kontext, review and branch it, explicitly
use approved endpoints for existing FFLF, interpolate an approved sequence with
RIFE or FILM, and export verified silent video. Director and Editor can propose
and run these same operations through shared tasks. Existing independent tools,
media identities, saved requests, manual workflows and unrelated projects remain
intact. Application readiness is claimed only after focused checks and separately
recorded owner-generated-media acceptance.
