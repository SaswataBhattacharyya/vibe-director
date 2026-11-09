# Current integration architecture and preservation contracts (2026-11-09)

This is a **current system map and change guard**, not an implementation queue. **P0 active repair:** [DIRECTOR_HARNESS_P0.md](DIRECTOR_HARNESS_P0.md) for persistent Codex-like tool-loop, MCP, approval and five-clip playback. Use [ACTIVE_FIXES.md](ACTIVE_FIXES.md) for ordering, [ACCEPTANCE_TESTS.md](ACCEPTANCE_TESTS.md) for gates, and actual source for the final truth. Snapshot: `vibe-director-current@6db612357f6c`.

## Authority and execution

```text
Project / registered owned assets / source hashes / saved revisions
                          │
                Shared Director chat
                          │
        Live catalogue + schemas + skills (guidance)
                          │
          Versioned, explicit tool/task approval
                          │
               Durable jobs and recovery
                          │
      ┌───────────────────┼────────────────────────┐
      │                   │                        │
 CPU analyzers       Vibe Editor plan         Generation engines
 transcript /        + two clearances         (image/video/audio/3D)
 overlap / frames           │                        │
                    ┌──────┴────────┐               │
               HyperFrames      Kdenlive MCP          │
               renderer/Studio  narrow joins          │
                    │              │                  │
                    └──────┬───────┴──────────────────┘
                           │
                 Verified registered output
                           │
                Backlot saved-board mirror
```

Vibe owns the project identity, media records, membership/paths/hashes, approval ledger, Editor ranges/revisions, style, checkpoints, jobs and output provenance. Native Studio/Backlot, ComfyUI and Kdenlive MCP are specialist runtimes, not owners of Vibe's source of truth. Skills are instructions, not executable permissions.

## Actual currently implemented boundaries

- **Shared Director:** `agent_tools.py`, `agent_tool_routing.py`, `agent_tasks.py`, `agent_native_tools.py`, `agent_generation_tools.py`, `agent_workspace_tools.py`, `agent_conversation.py`. Catalogue has 37 registered operations, not 37 guaranteed-ready runtimes; model may propose but cannot approve or execute itself. Completed reports/media are evidence, not permission.
- **Media and storage:** `media_library.py`, `media_discovery.py`, `projects.py`, `storage_paths.py` preserve owned references and versioned checkpoints. Save currently copies data; retention/deduplication is not established. No arbitrary client local path as an asset reference.
- **Audio/edit:** `agent_transcription.py`, `editor_speech.py`, `vibe_editor.py`, `vibe_editor_render.py`. CPU timed transcription and reviewed hard-cut plans exist; do not infer human speech correctness or replacement/retimed soundtrack support.
- **Kdenlive:** `video_overlap.py` samples paired ordered sequences, returns evidence and estimated boundaries; `agent_overlap.py` freezes owned inputs; `editor_kdenlive.py` gates preview and final render; `kdenlive_mcp.py` supervises `kdenlive_mcp_client.mjs` against pinned upstream. Adapter is **two videos**, normal speed, linked source audio, contain framing, hard cut, **1920×1080 at 30 fps**. Project XML export is not proof that user's Flatpak Kdenlive opens it.
- **HyperFrames:** `editor_studio.py`, `native_studio.mjs` isolate a pinned Studio 0.8.199 workspace; supported trims, order, captions and contain/cover edits return as JSON proposals through existing clearance. Native arbitrary layers/animations/history/audio round-trip is not supported. React 18 app remains separate from upstream React 19.
- **OpenMontage:** `production_board.py`, `native_backlot.py`, `backlot_editor.html` mirror saved storyboard media into pinned AGPL-3.0 Backlot; application-owned typed prompt/duration/notes proposal flow exists. Upstream arbitrary write-back, general shot reorder, engine generation and native filmmaking pipeline are not exposed. Preserve third-party licenses/source notices.
- **Reviewed frames:** `frame_pipeline.py`, `frame_interpolation.py` and worker/Composer UI support approved takes, branches, RIFE/FILM job staging and exports; live GPU/model creative acceptance is separate.
- **Computer:** `agent_computer.py`, `agent_permissions.py`, `agent_access.py` require a specific user grant and scope. Never broaden to arbitrary HTTP/shell/MCP calls as a shortcut to orchestration.

## Non-negotiable invariants for changes

1. **Identity:** Preserve project/workspace, asset ID + SHA-256, source-relative timestamps, provenance, saved sessions, approved plan snapshots, and output lineage. Do not trust model-authored file paths.
2. **Two clearances:** Creative brief and exact media/tool plan require owner approval. Task proposal and run are separate actions; no model self-approval. New edit invalidates stale approval.
3. **Execution:** Durable job must correlate owner, frozen request, submitted invocation, source hashes and output registration. Don't automatically repeat an external action after uncertain acknowledgment; require reconciliation.
4. **Cancellation/recovery:** Maintain job idempotency and cleanup of **owned** temporary processes/files. Never clean whole user directories, remove outputs or silently retry paid jobs.
5. **Backend parity:** A Kdenlive plan must never silently fall back to HyperFrames, nor accept unsupported speed/effects/transitions. Native UI import must sanitize unsupported edits, not execute upstream scripts.
6. **Secrets/process:** Specialist runtimes need loopback binding, limited media roots, minimal environment, bounded subprocess lifetime and explicit filesystem/host guards. Existing Kdenlive MCP full-environment inheritance is a hardening task, not a resolved security finding.
7. **Model scheduling:** Preserve shared GPU admission/thermal/watchdog safety; no model installation, clock changes, real render or provider calls as a consequence of discovery/testing.
8. **Storage:** Checkpoints, media stage copies and render outputs are separate ownership classes; reference counts/recovery checks precede retention or deletion proposals.
9. **Skills:** `agent_skills.py` loads the nested blueprint under `fixes/vibe-director-codex-agent-blueprint-v2/.../skills` and `shared/CONTRACT.md`. This historical-looking folder is **runtime data**; do not delete it. Installed skills cannot grant execution.
10. **Licenses:** Retain Apache-2.0 HyperFrames/Kdenlive notices and AGPL OpenMontage notices; do not silently copy or modify upstream runtime code.

## Change impact map — trace these seams before editing

| Change area | Inspect callers/consumers |
| --- | --- |
| Chat/schema/ready | `DirectorConversation.tsx`, `DirectorRuntime.tsx`, `agent_api.py`, `agent_tool_routing.py`, `agent_tasks.py`, worker mappings, saved plans |
| Media registry | `MediaSourcePicker.tsx`, `media_library.py`, output exporters, asset adoption, project checkpoint/open/membership |
| Editor/Kdenlive | `VibeEditorPage.tsx`, `ClipJoinReview.tsx`, `vibe_editor_api.py`, `editor_kdenlive.py`, `kdenlive_mcp_client.mjs`, FFmpeg/MLT, test fixtures |
| Native GUIs | `NativeWorkspace.tsx`, `editor_studio.py`, `production_board.py`, loopback sessions, HTTP cookies, proposal validation |
| Storage/hygiene | `projects.py`, `storage_paths.py`, `studio_checkpoints.py`, `media_library.py`, Graphify consumers, backup/rollback |
| Orchestration | `agent_tasks.py`, `agent_conversation.py`, job state transitions, approval UI, recovery journals, source/output provenance |

For actual source constraints see [Director tool access](../docs/DIRECTOR_TOOL_ACCESS.md), [Kdenlive usage](../plans/kdenlive_clip_continuity_usage.md), [native interfaces](../design/vibe-editor/native-interfaces.md), and [frame-pipeline usage](../docs/FRAME_PIPELINE_USAGE.md). Never overstate those as global end-to-end acceptance.

## P0 gap: one-shot reasoning is not a harness

As of `05508145fe049214f0f83ac45b1164748920dd4d`, `reasoning_provider._codex_json` uses `codex exec --ephemeral` for JSON reasoning, and `agent_conversation.send` proposes one task and returns. Previous tool results only enter a later **user** message. That is why the Director can list media but not automatically continue to sequence/approval/render. See [Director harness P0](DIRECTOR_HARNESS_P0.md) for official Codex app-server first, SDK spike, Agents SDK fallback, project-owned durable goals and human-only approvals.

Do not replace `agent_tasks`, Vibe Editor clearances, registered assets or worker ledgers with Codex session state. Codex/app-server is the **agent control loop**, MCP is a typed connector to existing Vibe operations, native renderers do the actual media work, and Playwright MCP is an optional **restricted browser/UI observer**, not an approval bypass or Qt desktop automation engine. A user-facing goal completes only when its verified final artifact is registered and playable, not when a read-only discovery tool completes.
