# Compare and stitch two clips with Kdenlive MCP

Implemented locally on 2026-11-08. No Git publishing, GPU generation or paid provider requests were used for acceptance.

## Use in Vibe Director

Restart Vibe Director through its normal launcher after active jobs finish, so its backend loads these services. Open Vibe Editor and attach two videos in order: A, then B. Use the media range controls to select A through its source end and B from zero, extending the default five-second selection when necessary.

Open **Compare and stitch two clips · Kdenlive**. Choose **Compare clip boundaries**, approve the exact analysis task, and run it. This compares complete-source boundaries, not just the selected editing ranges. The panel searches a three-second window; the shared tool accepts 0.5–10 seconds through its settings. No media is changed by analysis.

Inspect the result and paired source timestamps. Static or ambiguous matches produce no automatic trim. A match estimates repeated moving footage on a common sampling grid; its score is not a probability. Use manual range editing for uncertain footage or unsupported edits.

Choose **Prepare Kdenlive join preview**. Approve the creative brief if this session has none, then inspect the actual MCP-rendered boundary preview and exact retained ranges. Listen at the cut: a matching picture does not prove seamless sound. **Approve this revision** on clearance 2 explicitly starts the final MCP render. **Reject proposal** discards the proposal without deleting original media. Stop, pause/resume and retry use the existing Editor job controls.

The final video appears in Preview and can be saved using Export. **Download editable Kdenlive project** is in the comparison panel after a successful Kdenlive render. The project references managed media inside its retained local execution directory; downloading the XML alone is not a portable media archive. Keep those files together on this machine.

The shared Director can also propose comparison and join preparation from chat. Select the same two media sources; open a saved Editor session before asking it to prepare the join. The built-in `kdenlive-clip-continuity-and-stitching` skill appears in Context & skills for both Director and Editor. Skills do not grant computer access or bypass approvals.

Current Kdenlive adapter scope: two videos, hard cut, normal speed, source audio, contain framing, 1920×1080 at 30 fps. HyperFrames remains the independent renderer for its existing plans. Unsupported Kdenlive edits are rejected explicitly; there is no silent renderer fallback. No screenplay or storyboard is required.

## Installation and Codex

Pinned upstream: `AMMIROSOH/Kdenlive-mcp` revision `b1ff6d5d0263c9074230b9a5d02a6a5d58d2386e`, Apache-2.0. Private pnpm 9.5.0 builds the source; no system package replacement or global Corepack change. License: `third_party_licenses/Kdenlive-mcp/LICENSE`.

The tested runtime is already installed at `local_data/runtimes/kdenlive-mcp`. On another machine, from the repository root run `python3 scripts/setup_kdenlive_mcp.py` with Node 22+, npm, Git, melt, FFmpeg and FFprobe available. The installer refuses to overwrite an existing runtime. Then run `node scripts/check_kdenlive_mcp.mjs`; it uses only synthetic temporary CPU media and verifies cleanup. The full installer script was not independently rerun after the equivalent manual build succeeded.

The existing placeholder Codex MCP entry was replaced with this runtime, explicit host tools and a dedicated `local_data/kdenlive-codex` workspace. Configuration backup: `/home/riki/.codex/config.toml.before-vibe-kdenlive`. Start a fresh Codex session if the tools do not appear. This workspace is separate from Vibe-owned execution projects; direct MCP experiments cannot silently change a reviewed Vibe timeline. It is not a general filesystem grant.

## Verification and remaining owner acceptance

- Actual ARM64 source build and doctor passed with Node 22.23.1, host MLT/melt 7.22.0 and FFmpeg/FFprobe 6.1.1.
- Actual MCP project/import/linked trim/preview/render/verification/editable export passed. Independently audited melt invocation, stream duration, audio presence, cancellation and stale external revision rejection.
- Actual Vibe task → comparison → join preparation → brief approval → MCP preview → final approval → MCP render → media registration passed with moving synthetic video. A=3s, B=3s, repeated opening=1s; result=5s within two project frames, with audio. Silent inputs passed too. Source hashes stayed unchanged.
- Focused tests cover approximate compressed/graded overlap, unequal FPS, VFR sampling, no overlap, still/short/periodic ambiguity, stale approval, source changes, unavailable runtime, selection invalidation, cancellation and uncertain/malformed recovery records. Browser interactions use mocked APIs; actual CPU MCP tests are separate evidence. No paid/model calls were needed.
- Test-owned directories, databases and generated media are removed in finally/cleanup with absence assertions. User media and projects are untouched. The private runtime and user execution artifacts are retained deliberately.

**Owner check:** After rendering your own small join, download its editable project and open it in Flatpak Kdenlive 26.08.3. Confirm no missing-media dialog, both linked source tracks, the trim and playback/audio at the cut. Upstream exports the 26.04.x project format; successful export does not prove compatibility with this newer desktop GUI. Desktop interaction was unavailable for this check. Also review the artistic/audio continuity on your own footage before relying on the cut.

Long/static/looping/sparse-motion footage can remain inconclusive. Timing uses a bounded resampling grid, not exact source-frame PTS registration; VFR and high-rate sources need playback review. No automatic cut is made from an inconclusive result. Uncertain external mutation acknowledgement blocks replay and needs reconciliation; it is not silently retried.

## Changed application seams

- `video_overlap.py`, `agent_overlap.py`: bounded CPU evidence and durable comparison jobs.
- `agent_tools.py`, `agent_tasks.py`, `agent_conversation.py`, `agent_skills.py`: shared catalog, exact approvals, frozen source identity, measured chat context and skill discovery.
- `video_repertoire.py`, `video_repertoire_worker.py`: CPU job routing, preserving existing GPU guards.
- `kdenlive_mcp.py`, `kdenlive_mcp_client.mjs`, `editor_kdenlive.py`: private MCP supervision, operation journals, frozen requests, preview and verified publication.
- `vibe_editor.py`, `vibe_editor_api.py`: existing revision/clearance seams, evidence and editable-project routes.
- `ClipJoinReview.tsx`, `clip-join.css`, `VibeEditorPage.tsx`, `DirectorConversation.tsx`, `lib/editor-api.ts`: shared task controls, source evidence playback, preview and explicit approval/reject controls.
- `test_video_overlap.py`, `test_editor_kdenlive.py`, `test_kdenlive_bridge.py`, `test_agent_skills.py`, `clip-join.spec.mjs`: focused regression/acceptance coverage.
- Runtime setup/acceptance scripts, built-in skill, license notice, this guide, implementation-plan status and README link. Graphify outputs refreshed; unrelated pre-existing dirty work remains preserved.

## Recovery and disabling

If a revision/source changes, prepare a new comparison/proposal. Stop cancels only the owned execution process. A completed MCP job can be reused on final-render retry; changed cached output bytes are rejected. A journal with an uncertain pending operation refuses blind replay. Preserve its execution folder for inspection; prepare a new reviewed execution rather than editing the journal to force it through.

To disable, remove only the new Kdenlive tool routing/runtime capability and Codex MCP entry; keep outputs, sessions and execution/media folders. Existing HyperFrames requests retain their backend. Do not reset this dirty checkout or reinterpret a frozen Kdenlive approval as approval for another renderer.
