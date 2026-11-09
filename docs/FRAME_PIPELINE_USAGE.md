# Reviewed keyframes and silent video

## Where to find it

FLUX Kontext Dev is an image workflow in **Text to Image** and image asset tools,
including **First & Last Frames**. It requires exactly one image reference; it
is not a text-only generator. Existing Z-Image/Qwen choices remain available.

**First & Last Frames** and **Vibe Editor** both contain the same expandable
**Reviewed keyframes → silent video** panel. These controls work with standalone
project media; a screenplay/storyboard is not a prerequisite. Director and Editor
chat can propose the same three registered tools. The built-in Kontext and frame
interpolation skills are discoverable in Context & skills.

## Workflow

1. Choose a starting image in the new-take picker. Canvas preparation is explicit
   and enabled by default: it uses CPU Lanczos resize/center crop to create a
   separate image in the installed Kontext aspect bucket. The original remains
   unchanged. Inspect the actual dimensions and approve the starting key.
2. Describe the next visible change, choose a seed and prepare a Kontext task.
   Review the exact plan, approve it, then Run. This queues one candidate in the
   existing image worker; task completion here means queued, not a finished image.
   The panel refreshes while it is running. Inspect and approve/reject the result.
   Repeat only from an approved head. Rejected keys remain in history.
3. **Branch here** on an approved key creates a new take ending there. The old
   take and descendants remain. Importing a replacement adds a candidate; it does
   not edit an existing image. Later approved keys must match the starting size.
4. With two or more approved keys from one continuous shot, choose RIFE or FILM,
   multiplier, FPS and endpoint holds. The panel shows the quantized frame count
   and duration before Run. Prepare, approve and run interpolation. It downloads
   only saved PNGs, verifies counts/dimensions/original-key placement, and retains
   a hashed sequence manifest. No audio is added.
5. Prepare the separate MP4 + lossless export task, approve and Run. CPU FFmpeg
   creates H.264 preview and FFV1 master, checks count/codec/duration/silence and
   fully decodes both before publication. The preview appears in the shared media
   library; the completed task provides a downloadable FFV1 master. Use existing
   Editor media controls to import the preview. Audio remains a separate workflow.

To use the same take for existing First + Last Frame generation, click **Use
approved endpoints in a new First + Last Frame video draft**, then **Create draft
from approved endpoints**. The backend rechecks revision, approvals and hashes.
The current draft is backed up in browser storage and a separate clip draft gets
the selected endpoints. Add a shot prompt and review settings before Generate.
Unresolved video attempts block this handoff. Existing accepted takes, screenplay
selections and frozen requests are not replaced.

## Recovery and limitations

An uncertain interpolation POST is journaled before submission. **Reconcile saved
interpolation** reads that exact prompt's history; it does not submit another
prompt. Staging is retained while receipt/execution is uncertain, because ComfyUI
may still need it. Owned staging is removed after a terminal result or pre-submit
staging failure. Global queue clearing and unrelated-prompt interruption are not
used. Failed/cancelled image candidates can be rejected before trying another.

Original key checks compare decoded RGB pixels, allowing at most one 8-bit level
for the installed node's optional fp16 intermediate/SaveImage rounding. Larger
changes fail verification. Interpolation does not fix bad poses or bridge cuts.
Kontext preservation prompts cannot guarantee identity or framing consistency.
Canvas buckets reflect the installed FluxKontextImageScale implementation; review
compatibility again after upgrading that backend.

Shared admission/watchdog rules remain in force, including the existing 90°C and
2100 MHz ceilings. No clock changes were made. External ComfyUI clients can race
with application admission; this is not global arbitration across all clients.
Model rights/provenance remain in
`backend/story_builder/workflows/api/FRAME_PIPELINE_PROVENANCE.md`.
ControlNet, MOSAIC and other deferred model families are not enabled.

## Verification

Focused backend tests cover reviews, revision conflicts, branches, project
snapshots/isolation, pinned hashes, idempotent candidate requests, schema/model
choices, ordered graph compilation, uncertain receipts/history-only recovery,
owned staging cleanup, cancellation and process reaping. Synthetic CPU tests
encode/probe/decode MP4 and FFV1 including holds, and reject changed PNG sequences.
Fixtures assert removal of their complete temporary root, records and media even
on failure. No production records or owner media are used for these tests.

Browser specs verify draft preservation, branch controls, exact-plan approval,
explicit FFLF handoff/backup, and no implicit generation. Existing Create and
Kdenlive controls pass focused browser regressions. Production frontend build and
type checking pass. Build still reports a large bundle warning. Existing backend
tests emit SQLite ResourceWarnings; these checks are not a whole-app audit.

Read-only live `/object_info` probes confirmed Kontext and both FILM/RIFE model
choices on 2026-11-08. This is readiness metadata, not inference acceptance.
Actual Kontext drift, motion quality, GPU cancellation and owner-content output
acceptance still need an explicit owner Generate/Run. No GPU or paid requests
were made during implementation. Restart/reload through the usual launcher after
current jobs finish; implementation did not restart the owner's running app.

Graphify was refreshed as a discovery aid. Its incremental graph does not provide
complete repository coverage, and JSON workflow internals are not AST nodes;
source and tests were checked directly.

## Feature files

The checkout already contained unrelated uncommitted work. This feature changes
the following application/docs files; that does not attribute every existing
diff in them to this task.

| Area | Files (repository-relative) |
| --- | --- |
| New backend modules | `backend/story_builder/services/frame_canvas.py`, `frame_pipeline.py`, `frame_pipeline_api.py`, `frame_pipeline_jobs.py`, `frame_interpolation.py` (all in that services directory) |
| Image integration | `backend/story_builder/services/production_image_workflows.py`, `isolated_image_references.py`, `image_prompt_context.py`, `workflow_knowledge_catalog.py` (same services directory) |
| Shared agents/jobs | `backend/story_builder/services/agent_tools.py`, `agent_tasks.py`, `agent_conversation.py`, `agent_skills.py`, `director_skills.py`, `video_repertoire.py`, `video_repertoire_worker.py` (same services directory) |
| Router | `backend/story_builder/isolated_server.py` |
| New frontend modules | `frontend/src/FramePipelineWorkspace.tsx`, `frontend/src/FrameEndpointDraft.tsx`, `frontend/src/frame-pipeline.css` |
| UI integration | `frontend/src/App.tsx`, `frontend/src/TextToImagePage.tsx`, `frontend/src/ImageAssetsPage.tsx`, `frontend/src/VibeEditorPage.tsx` |
| Graphs/provenance | `backend/story_builder/workflows/api/flux_kontext_recursive_frame.api.json`, `film_frame_interpolation.api.json`, `rife_frame_interpolation.api.json`, `FRAME_PIPELINE_PROVENANCE.md` (same API directory) |
| Built-in skills | `skills/flux-kontext-prompting/SKILL.md`, `skills/frame-interpolation/SKILL.md` |
| Tests | `backend/story_builder/tests/test_frame_pipeline.py`, `backend/story_builder/tests/test_production_image_workflows.py`, `backend/story_builder/tests/test_agent_skills.py`, `frontend/tests/frame-pipeline.spec.mjs` |
| Documentation | `README.md`, `plans/kontext_frame_pipeline_plan.md`, `docs/FRAME_PIPELINE_USAGE.md` |

Graphify also regenerates `graphify-out/graph.json`, `manifest.json`,
`cache/stat-index.json` and content-addressed AST caches.

Rollback: disable only these new entries, let jobs settle/reconcile, and revert a
reviewed feature patch without resetting unrelated work. Keep additive take
records, assets, job journals and history; do not automatically drop/delete them.
