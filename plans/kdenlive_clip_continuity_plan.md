# Kdenlive MCP: clip continuity and stitching implementation plan

Planning date: 2026-11-08. Status: implemented after owner approval; focused CPU/MCP and browser acceptance completed. Flatpak desktop opening and owner-content acceptance remain manual. See [usage and verification](kdenlive_clip_continuity_usage.md).

## Outcome and boundaries

From the existing Director chat or Editor, select two ordered clips, compare the end of A with the start of B, inspect evidence and a proposed cut, preview the join, approve it, and obtain a verified final video plus an editable Kdenlive project. Editing and rendering in this workflow must use real Kdenlive MCP calls. An unavailable MCP backend produces a useful blocked state; it must not silently invoke the existing renderer under a Kdenlive label.

Keep the current navigation, Media Prep, shared media identities, Director conversation, Editor sessions and approvals. HyperFrames remains available independently. No screenplay/storyboard prerequisite, second media library, broad dead-code cleanup, general autonomous editing framework, or OpenMontage work belongs in this slice.

The attachment supplies requirements; the user's direct request is to plan first. Existing dirty source is authoritative and must be preserved. The checkout currently contains substantial tracked and untracked work, including native-interface and chat-attachment changes. Re-read affected diffs immediately before implementation.

## Findings and compatibility gate

Locally verified: Ubuntu 24.04.5 ARM64; Node 22.23.1; FFmpeg/FFprobe 6.1.1; host MLT/melt 7.22.0; system Kdenlive 23.08.5; Flatpak Kdenlive 26.08.3 for aarch64. pnpm is missing.

Upstream Kdenlive MCP documents Linux x64 testing, not ARM release testing. Its shell installer chooses an x64 archive, can enable Corepack globally, replaces its installation directory, and ignores a failed doctor result. Do not run that installer here. Use an isolated, pinned source build with a private pnpm installation. Check dependencies, native ARM builds and licenses first. Preserve the installed system and Flatpak applications.

Upstream supplies real project, media, timeline, preview, render, cancellation, verification and editable-export tools. Its analysis worker is a health scaffold; overlap analysis must be implemented in Vibe. The exported Kdenlive format is documented against 26.04.x; opening it successfully in the installed Flatpak 26.08.3 is a separate acceptance check. Host melt readiness does not prove Flatpak GUI compatibility.

## Architecture and contracts

Flow: Director/Editor → existing typed task and approval system → CPU overlap analysis → frozen join proposal → supervised MCP adapter → preview/review → approved final MCP render → verification → existing media registration.

Vibe's saved Editor revision and frozen request remain authoritative for this workflow. The MCP project is a derived execution project, with its own external revision recorded after each mutation. Direct Codex experimentation uses a different workspace so it cannot mutate a Vibe-owned execution project behind an approval.

Use a small Python adapter for Vibe ownership, jobs and results, and a private Node stdio client using the MCP SDK if the dependency review confirms that is the smallest supported option. Inspect `tools/list` and validate the actual pinned schemas before implementing calls. Avoid handwritten JSON-RPC framing and arbitrary shell command exposure. Keep the process local, use argument arrays, bound messages/timeouts, drain stderr, and terminate only owned children.

Proposed application tools:

- `video.compare_clip_overlap`: ordered asset IDs, optional selected ranges, configurable bounded tail/head windows, source fingerprints and rational timing. Returns `match`, `no_match`, or `inconclusive`, evidence frames, aligned timestamps, estimated repeated frames, score explanation and suggested retained ranges.
- `editor.prepare_clip_join`: binds the comparison and chosen ranges to the current Editor revision; prepares an MCP project and join preview under the existing task approval model.
- Final rendering remains an explicit approved Editor action, with backend `kdenlive` frozen into the request. Reuse existing approval controls rather than adding another approval wizard.

These names are proposed application contracts, not claims about upstream MCP tool names. Analysis is allowed to use FFmpeg for decoding; timeline editing and preview/final rendering go through MCP.

Persistence: reuse existing task plans, approvals, invocations, events, durable job request/result records and versioned Editor JSON. Add optional backend metadata: backend/version, execution project ID/revision, operation ID, source hashes, Editor revision, plan hash, external job ID, output provenance and verification results. No new asset database or production SQL table is planned. Persist a pending operation event before an external mutation and its result afterward; after a crash, reconcile the external project/job before retrying. Never blindly repeat an ambiguous mutation. Legacy requests without a backend retain their existing behavior.

## Phase 1 — prove the real ARM64 backend

1. Pin an upstream commit and record its license/dependency/runtime versions. Build under an isolated application support directory; keep generated installs out of Git.
2. Run doctor with explicit host `MELT_PATH`, `FFMPEG_PATH` and `FFPROBE_PATH`. Probe the actual services/codecs needed for this slice.
3. In a unique temporary root, use actual stdio MCP calls to create a project, import two tiny synthetic clips, add/trim/place them, submit a CPU preview/render, poll, verify and export an editable project. Inspect render streams and duration independently.
4. Test cancellation and a revision conflict. Open the exported project in Flatpak Kdenlive if available browser/desktop controls permit; otherwise provide the exact owner check and mark it unverified.
5. Verify cleanup in `finally`, including owned processes and temporary MCP state. Preserve logs/compact test results without retaining generated media.
6. Only after this passes, prepare the optional Codex MCP entry using the installed Codex CLI's supported configuration. Back up and merge existing configuration, use a dedicated media workspace and stable client ID, and avoid broad filesystem roots. Report any necessary client reload. This registration does not replace the Vibe bridge.

Files: a small runtime setup/check script under `scripts/`, isolated acceptance script, runtime documentation and third-party license notices if anything is vendored. No app readiness claim before actual calls pass.

Exit: real ARM64 MCP edit/render/verification works, or a reproducible compatibility blocker is reported before app integration proceeds.

## Phase 2 — trustworthy overlap analysis

New service `backend/story_builder/services/video_overlap.py`; retain `video_continuity.py` and its one-clip last-frame behavior.

Decode bounded A-tail/B-head windows with source PTS. Use perceptual hashes for candidate discovery, structural similarity for verification, and monotonic multi-frame temporal alignment. Compare motion and match distinctiveness against alternative alignments. Stillness, repeated patterns and common backgrounds must lower confidence or return inconclusive. An isolated matching frame cannot establish duplicated footage.

Use rational frame rates and half-open ranges. Handle different FPS and variable-frame-rate inputs with an explicit analysis sampling grid and a mapping back to source timestamps. Any normalized working media is temporary; originals remain unchanged. Scores describe measured similarity, not calibrated probabilities. Start with conservative thresholds validated on fixtures; do not automatically trim uncertain matches.

Return a versioned evidence object with source hashes, windows, timing, method/settings, sample correspondences, uncertainty and suggested ranges. Bound memory, decode duration and disk usage. Report unsupported/broken media specifically.

Connect through `agent_tools.py`, `agent_conversation.py`, `agent_tasks.py`, `video_repertoire.py` and `video_repertoire_worker.py`. Add the CPU-only job kind without changing GPU admission, watchdog, temperature or clock policies. Supply tool evidence back to chat so it can describe what was actually measured.

Tests: new `test_video_overlap.py`, focused task/conversation regressions. Cases: exact overlap, compressed/graded overlap, no overlap, static scenes, repeated backgrounds, short clips, differing FPS, VFR, invalid ranges, changed/missing sources, cancellation and bounded decoding.

Exit: reproducible timestamp recommendations, useful no-match/inconclusive results, no false claim that video was inspected without a successful analysis.

## Phase 3 — durable MCP execution adapter

New compact services `kdenlive_mcp.py`, `kdenlive_mcp_client.mjs` and `editor_kdenlive.py` (split further only for demonstrated complexity). Extend existing Editor/job seams rather than rewriting the renderer.

Resolve assets through `media_library.py`; copy or stage verified inputs inside the dedicated MCP root with deterministic ownership manifests. Revalidate hashes before execution. Enforce workspace containment including realpaths/symlinks. Skills and model output cannot authorize arbitrary roots, tools or commands.

Use actual pinned MCP tools such as `project_create`, `media_import`, `timeline_add_track`, `timeline_add_clips`, `timeline_trim_clip`, `preview_submit`, `render_submit`, `job_get`, `job_cancel`, `job_verify` and `interchange_export`, subject to discovered schemas. Record expected revision on every mutation and checkpoint where supported. Keep linked audio aligned with each retained video range; preserve audio unless the approved plan says otherwise. Handle silent clips explicitly.

Reuse `agent_tasks.py` ownership, frozen-plan approvals and invocation recovery; `vibe_editor.py` session/revision validation; and existing durable job dispatch/cancellation. Reject stale Editor plans and changed media. If submission success is uncertain, reconcile by recorded operation/project/job state; require review when it cannot be established safely.

Verify successful output with upstream job verification and independent stream/duration checks before `media_library.py` registration. Publish to existing output conventions without clobbering files. Store editable project and provenance as associated artifacts. A failed render must never appear as a completed media asset.

Tests: new `test_kdenlive_bridge.py` and `test_editor_kdenlive.py`; mocks for protocol/errors plus Phase 1's actual MCP CPU fixture. Cover malformed responses, root escape, revision conflict, partial mutations, disconnect/restart, timeout, cancellation, duplicate submission, changed source, failed verification and output collision.

Exit: an approved frozen join can survive normal polling/recovery, produce verified media through MCP and preserve original assets and existing HyperFrames behavior.

## Phase 4 — integrate the existing Editor and Director

Touch `VibeEditorPage.tsx`, `EditorVisualTimeline.tsx`, `DirectorRuntime.tsx`, `DirectorConversation.tsx`, `frontend/src/lib/editor-api.ts`, `frontend/src/lib/agent-tasks.ts`, and `vibe_editor_api.py` only where required. Reuse `MediaSourcePicker.tsx` selection/asset IDs and the existing task endpoints. Add a small reusable `ClipJoinReview.tsx` and focused styles if needed.

Show ordered A/B selection, Compare, progress/cancel, evidence near the proposed cut, retained/removed timestamps, confidence explanation, preview and approval/reject controls. No-match/inconclusive offers explicit manual range selection. Invalid inputs explain exactly which asset/range needs attention. Draft chat text and selection survive inspector toggles and failed requests.

For a new Editor session, translate the user's stitch request into the existing brief confirmation; do not require a separate screenplay or a lengthy production wizard. Preserve existing revision clearances and ensure the exact final cut/backend is approved before final rendering. Preview execution must remain within the approved preparation task.

Display capability states accurately: not configured, compatibility check pending, ready, or blocked with a useful reason. Provide final video playback/download and an editable-project action. Kdenlive is a separate desktop application: this slice opens/exports a real project; it does not promise an embeddable native Kdenlive GUI in the browser.

Add `skills/kdenlive-clip-continuity-and-stitching/SKILL.md` and include it in `agent_skills.py` builtin discovery. It teaches tool use, evidence limits, two-clip ordering, approval, audio continuity and recovery. Both Director and Editor use the existing shared skill/tool catalog. Global/project skills may add guidance, but cannot grant execution access. Preserve application/project/full access boundaries.

Tests: extend `director-runtime.spec.mjs`, `editor-visual.spec.mjs` and skill discovery tests; test attachment ordering, review/approval, stale state, preview, readable failures and prompt preservation. Verify actual interactions with available browser tooling.

Exit: one chat and one Editor session drive the same comparison and approved MCP join without duplicating state or disrupting manual tools.

## Phase 5 — demonstrate and document acceptance

Use isolated test-owned media/projects only. Generate moving synthetic patterns with known repeated frames, versions with audio impulses and silent versions. Example: A=6 seconds, B=5 seconds, one second repeated; approved removal should produce a 10-second result within the defined project-frame tolerance. Verify the cut visually and numerically, audio alignment, duration, playable streams, editable export and source hashes.

Run the full chat → comparison → evidence → proposal → MCP preview → approval → MCP render → verification → media registration flow. Exercise rejection, cancellation and restart recovery. Confirm a failed/ambiguous comparison does not automatically remove footage. Run focused existing Editor/task/media/native-interface regressions; broaden only when failures justify it. Refresh Graphify after meaningful source changes and check changed-file coverage.

Every test fixture owns its temporary directory, records and children. Cleanup runs even on failure and asserts that temporary paths, test-owned records and owned processes are gone. Never delete existing media, history or projects. Retained deliverables from an owner-approved real workflow are not test garbage. GPU generation and paid calls are unnecessary for this acceptance.

Evidence report distinguishes mocked tests, actual CPU MCP acceptance, browser interaction and owner-content acceptance. If desktop control is unavailable, owner opening the exported project in Flatpak remains a clearly listed manual gate. Do not declare complete based only on mocks or a registered MCP entry.

## Risks and rollback

| Risk | Mitigation / rollback |
| --- | --- |
| ARM dependencies, old host MLT or export compatibility | Phase 1 gate; report exact failures; leave system packages untouched. |
| False overlap and lost intended action | Multi-frame distinctiveness, conservative/inconclusive result, explicit approved retained ranges, originals preserved. |
| MCP and Vibe revisions diverge | Derived execution project, frozen hash, revision checks, pending/result events and reconciliation. Reject stale approval. |
| Process crash or uncertain submission | Durable external IDs and owned process supervision; reconcile before retry; no blind duplicate mutation. |
| Cross-project access or output overwrite | Dedicated roots, identity/hash validation, containment and existing no-clobber publication. |
| Existing dirty changes conflict | Inspect current diffs before each phase; change the smallest seams; preserve unrelated work. |
| Integration needs disabling | Disable Kdenlive capability/new routing; existing backend remains available for its own requests. Preserve completed user outputs and saved sessions. |

Rollback removes only this integration's configuration entry/processes and identified code changes; it does not reset the dirty checkout, purge projects or delete runtime media. Optional persisted fields are ignored safely by existing paths. Stop owned MCP jobs before disabling. Do not reinterpret a previously approved Kdenlive request as approval for another renderer.

## Implementation sequence and reporting

Proceed in the order above after approval, with Phase 1 as the first bounded milestone. At each phase report changed files, actual checks, cleanup evidence, limitations and remaining work. Pause for a genuine compatibility contradiction or required owner interaction; routine reversible implementation decisions do not require repeated permission.

## Primary references reviewed

- [Kdenlive MCP installation](https://github.com/AMMIROSOH/Kdenlive-mcp/blob/main/INSTALL.md) and [installer source](https://github.com/AMMIROSOH/Kdenlive-mcp/blob/main/scripts/install.sh).
- [Runtime support](https://github.com/AMMIROSOH/Kdenlive-mcp/blob/main/docs/runtime-support.md), [MCP reference](https://github.com/AMMIROSOH/Kdenlive-mcp/blob/main/docs/mcp-reference.md) and [architecture](https://github.com/AMMIROSOH/Kdenlive-mcp/blob/main/docs/architecture.md).
- [Threat model](https://github.com/AMMIROSOH/Kdenlive-mcp/blob/main/docs/threat-model.md), [server package](https://github.com/AMMIROSOH/Kdenlive-mcp/blob/main/apps/mcp-server/package.json) and [CLI source](https://github.com/AMMIROSOH/Kdenlive-mcp/blob/main/apps/mcp-server/src/cli.ts).
- [Kdenlive project format](https://docs.kdenlive.org/en/project_and_asset_management/file_management/project_files.html).

These upstream URLs track a mutable branch. Phase 1 must pin and revalidate the source used for installation; this planning review is not a complete upstream security audit.
