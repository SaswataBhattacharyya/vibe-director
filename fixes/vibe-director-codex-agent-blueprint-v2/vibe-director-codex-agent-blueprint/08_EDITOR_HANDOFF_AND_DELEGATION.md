# Vibe Editor + external delegation

## Vibe Editor is an actual agent, not only a render planner
It sees same `project_id`, graph query, tool graph, skills and execution log as Director; it has editor-specific instruction layer, timeline/QA capability and default focus on *how to repair/finish*. Chat can call shared Media Prep/image/video/audio operations subject to same permissions. In specialized editing tasks, it can ask Director to arrange missing shots/retakes or itself use registered tools when user scope permits. The difference is skill and task role, not an artificial capability wall.

## Current source limitation
GitHub `vibe_editor.py` has approval workflow and calls a reasoning provider with explicit "Do not run tools or create files". Its trusted renderer only executes a validated JSON composition. **Do not remove trusted validator**. Add an orchestration layer beside it; retain current brief approval/plan approval/render endpoints and migrate approvals deliberately to avoid unnecessary repeated clearance.

## Canonical handoff (`EditorHandoffV1`)
- project ID, Director task/approved revision, selected timeline revision, editor session ID (if exists)
- ordered items: `clip_id`, selected `take_id/asset_id/hash`, in/out, hold duration, intended transition, dialogue/voice, audio policy, screenshot/keyframe pointers
- unresolved findings and suggested actions: trim, retime, replace audio, generate retake, add cutaway, color/effect, mix
- requested output: resolution/fps/aspect, audio policy, project folder/destination
- permissions, approved scope, rejected takes, outstanding tasks, plan history

Editor MUST validate every selection through the owned media library; no guessed file paths. Handoff is a proposed editable composition. Vibe Editor's approved plan is the authoritative input to HyperFrames rendering. Media from Director generated or imported is present through shared library ID/provenance.

## HyperFrames
Keep current trusted HyperFrames + FFmpeg renderer as stable default; it supports selected clip/image ranges, effects/speed ramps/transitions, one replacement soundtrack and verified export in inspected version. Optional **HyperFrames Studio** GUI should be a separate integration spike with a version-pinned supported package, component context, edit roundtrip and verified export. Do not assume embedded Studio can replace the current editor without schema parity and sandbox tests.

## OpenMontage
Optional documentary/montage delegate: discovery, research, shot matching or high-level montage proposal if clearly improves a user request. Work via isolated adapter/project-folder exchange, registry and normalized output; compare with existing semantic search + Editor first. License/legal and dependency/security reviews required before code reuse. User must see external data transfer/compute scope before approval. Delegate tasks, not control over the project's SQLite/ledger internals.

## Backlot
Distinguish (a) user-facing **editable comic storyboard** and (b) **read-only run/production board**. Backlot is aligned with (b) and may observe external pipeline artifacts; it cannot replace editable panel/story/dialogue workflow. Create native production Run Board on current task/job events. Optionally integrate external Backlot via explicit event bridge, not default iframe. User can choose it as monitor.

## Blender and coding tools
For difficult animal jump/camera choreography, Computer/Coding runtime can write/test a Blender bpy script in sandbox and render colored proxy motion ref. It should provide inspected MP4 with explicit asset ID and ask whether to attach to MiniMax; never assume every H3 mode accepts the motion video along with all image/audio references.

## Delegation contracts
A delegate receives a scoped brief, approved inputs, allowed operations, deadline/resource budget (if present), and expected outputs. Returns `job_id`, progress events, verified assets, limitations and evidence. Parent Director remains accountable for final film task, can cancel supported jobs, and cannot mark work completed on a delegate's unverified message.


## Editor global-skill parity and real tool execution

Vibe Editor MUST share the Director's **global + bundled + project-specific skill discovery/inspection/loading** interface. On an editing task it may selectively load globally installed coding, computer-use, audio/video, automation, and other skills, plus project filmmaking/continuity/style skills; the editor-specialist skill is an additive lens, not a whitelist. Project skill bindings and selected creative jackets must round-trip through project Save/Load with scope/version/provenance. Global skill installs are referenced, not copied or rewritten.

Both agents use the same typed tool router, computer/coding runtime, capability probing, permission gates, job tracking and project knowledge graph. Editor chat must be able to invoke authorized Media Prep audio extraction, real analysis, selected-range work, video retake, generation and HyperFrames handoffs; it cannot claim execution when a skill merely described it. Introduce this orchestration beside the existing trusted renderer and approval flow, not by handing raw provider-generated code to HyperFrames. Demonstrate source-preserving audio extraction from Editor and a shared skill search result in both chat contexts as initial parity acceptance tests. Full contract: `14_GLOBAL_AND_PROJECT_SKILL_ACCESS.md`.
