# Services — precise proposed code changes

Status: review-ready implementation guidance, NOT applied source code. Inspect current branch and tests before patches. Keep small modules, strict field validation, immutable job inputs and real owner checks.

## A. NEW agent_tools.py — one shared gateway for Director and Editor

The actual backend currently exposes separate Media Prep, Editor, image, video and story endpoints. Add a registry of allowlisted backend actions, not a generic shell dispatcher. Tool metadata: id, description, exact input schema, capability/live blocker, category (read/draft/submit/external/destructive), owner scope, handler and job/result format. No model-generated unknown keys. Resolve the current project server-side, not merely from a prompt.

Illustrative code shape (must add real input schema validation and permission storage before using it for writes):

    from dataclasses import dataclass
    from typing import Any, Callable, Literal

    Effect = Literal["read", "draft", "submit", "external", "destructive"]

    @dataclass(frozen=True)
    class ToolSpec:
        id: str
        effect: Effect
        fields: frozenset[str]
        capability: Callable[[], dict[str, Any]]
        run: Callable[[Any, str, dict[str, Any]], dict[str, Any]]

    def invoke(root, workspace: str, spec: ToolSpec, args, grant):
        if type(args) is not dict or set(args) != spec.fields:
            raise ValueError("Missing or unsupported tool fields")
        ready = spec.capability()
        if ready.get("status") != "available":
            raise ValueError(ready.get("reason") or "Tool unavailable")
        if not grant.permits(workspace, spec.id, spec.effect, args):
            raise PermissionError("This action needs approved scope")
        return spec.run(root, workspace, args)

The snippet is a skeleton, NOT a complete safe grant implementation. Registration and validation must be explicit, and no arbitrary shell or URL invocation is allowed.

Initial typed tools: media browse/search; audio.extract_mp3; video.continuity_last_frame; video capability inspection; Editor selected-media brief/plan; render approved Editor plan. Mark unsupported actions navigation_only or blocked. More actions require adapter-specific acceptance.

## B. Extract MP3 vertical slice: factor out one shared service

Current code around isolated_server.py:890-925 already does capability check, validates settings, stages media with audio_utilities.stage_assets(), creates durable job through video_repertoire.create_job("audio-utilities", request), then calls start_job(). Move that logic into one small service function (NEW agent_media_ops.py or audio_utilities.py), and call it from BOTH existing HTTP route and agent action. Do not have the backend call itself over HTTP.

Example service skeleton, adapted directly from the existing flow:

    from uuid import uuid4
    from . import audio_utilities, video_repertoire

    def start_mp3(root, workspace, asset_ids, quality=2):
        entry = next((x for x in audio_utilities.capabilities()["operations"]
                      if x["id"] == "extract_mp3"), None)
        if not entry or entry["status"] != "available":
            raise ValueError((entry or {}).get("reason") or "ffmpeg unavailable")
        settings = {"quality": quality}
        audio_utilities.validate_settings("extract_mp3", settings)
        staging_id = "stage-" + uuid4().hex
        inputs = audio_utilities.stage_assets(root, workspace, staging_id,
                                               asset_ids, "extract_mp3")
        request = {"workspace_id": workspace, "operation": "extract_mp3",
                   "settings": settings, "inputs": inputs,
                   "staging_id": staging_id}
        job = video_repertoire.create_job("audio-utilities", request)
        return video_repertoire.start_job("audio-utilities", job["job_id"])

Before autonomous use add deduplication/reconciliation keyed to agent task and frozen inputs. The existing HTTP response is 202 Accepted; preserve its behavior, error shape and staging cleanup on failure. Poll the already-available workspace-owned utility job and return registered playable output asset IDs. MP3 extraction is a subtask, not the completed film.

## C. NEW agent_skills.py: global + bundled + project registry

Current director_skills.py loads fixed app skill files. Existing Vibe Editor run_job independently reads design/vibe-editor/skills/vibe-editor-director/SKILL.md. Use one shared metadata/search/context resolver for both, with compatibility wrappers and bounded content.

Global skills come only from explicitly configured installed providers/approved roots; bundled skills include existing three live paths and approved 13 in the fixes blueprint; project skills include user-approved project-owned instruction files and creative jackets. Discover metadata first, then load only relevant SKILL.md and approved local references using canonical safe paths, content hash, version and context limits. Missing global installation must show unavailable, not silently be copied into the project. Skills never confer command execution rights.

## D. NEW agent_tasks.py + agent_graph.py: durable work, derived knowledge

Use the existing project-scoped ProductionLedger (and its Save/Load checkpoint) to persist task_id, project_id, plan revision + SHA, approved scope, step IDs/dependencies, actual tool operation, idempotency/job IDs, events and output hashes. Separate draft/planning from approved execution. Reconcile a possibly submitted job before retrying. Give every project graph node an existing source identifier, provenance and revision; do not make a parallel screenplay/media source of truth. Cache a read-only projection first, then persist only missing relations and reviewed decisions.

## E. NEW agent_video_prep.py + agent_media_review.py

Produce structured timed shot plan BEFORE rendering prompt. Enforce each route using its actual validator:
- R2V: images/videos/audios separately numbered, 5–15s, <7000 Unicode code points. Voice audio is a voice identity reference, not automatically the dialogue track.
- FL2VA: actual first_frame and last_frame, 5–15s; not the R2V arrays.
- T2V: empty references and 5–30s.
- video_continuity.last_frame() uses verified last frame of an owned generated video; R2V continuity image is not guaranteed FIRST FRAME conditioning.
- Inspect actual media with timestamped evidence; a failed probe and a visual continuity defect are different observations. Report unsupported analysis as blocker.
- Retake is prepared from an existing take, not overwrite; Editor receives approved asset IDs and exact media ranges.

## F. LTX OFF — future versioned schema and worker change

DO NOT simply add ltx_enabled to existing v2 request. Exact-field validators isolated_video_contract.py, isolated_r2v_contract.py, isolated_fl2va_contract.py reject unsupported fields. Frozen v2 pipeline_digest binds Turbo+LTX. production_ledger.save_turbo_original() currently sends originals to refinement_pending; promote_turbo_refinements() queues LTX. To implement the toggle:
1. Plan a new versioned workflow/request with postprocess_profile=turbo_only or turbo_plus_ltx and new digest/capability metadata.
2. After Turbo-only collection, validate original video fps/frame count/duration/audio and register a verified final asset, then move directly needs_review without scheduling LTX chunks. Preserve original provenance.
3. Keep historical v1/v2 jobs and resumes on their frozen LTX route; update frontend serializers, graph, collector, ledger and tests together.
4. Prove zero LTX jobs when OFF, correct audio and duration, restart/reconciliation, all three workflow families and failure-state integrity. Do not publish an unvalidated Turbo original under the old contract.

## G. Real computer/coding runtime, optional external delegation

Add a distinct opt-in local sidecar with filesystem/worktree allowlist, command audit, Git/test/browser permissions and per-plan grant. Never expose subprocess.run(user_supplied_string, shell=True) over the app API. Without actual runtime, show blocked. OpenMontage/Backlot/HyperFrames Studio are optional adapters with license/version/auth and output registration tests, not mandatory dependencies.

## Blast-radius tests before any source modification

Check consumers by source search (Graphify index is partial): editor API, Media Prep utility API, project snapshots, all exact MiniMax contracts, worker/ledger, Editor selected-range validator, project UI. Run existing CPU tests test_audio_utilities_integration.py, test_video_continuity.py, test_isolated_*_contract.py, test_isolated_video_jobs.py, test_projects.py, test_storyboard.py, test_video_final_collection.py, and new agent task/skill tests. Only report test results actually run.