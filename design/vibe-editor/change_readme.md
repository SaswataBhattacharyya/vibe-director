# Editor integration guide

Read [assessment](../../fixes/SOURCE_ASSESSMENT.md) and [Q06–Q08](../../fixes/QUICK_FIX_TASKS.md). Preserve `vibe_editor.py`, API contracts, trusted `vibe_editor_render.py`, existing skill/references and manual workflows.

Current Editor has project/session messages, selected media/ranges, brief and plan clearances, style history, trusted JSON→HyperFrames/FFmpeg rendering and protected export. `run_job` explicitly says “Do not run tools or create files.” That is the render planner; do not remove its restriction to create a tool agent.

Q06 exposes shared discovery. Q08 adds specialist orchestration alongside the existing planner: selected owned media → extraction proposal → exact task approval → existing utility job → registered playable output → optional attachment. No silent soundtrack replacement. Keep selections/ranges and render/export approvals. Test both Director and Editor using the same backend gateway.

Handoffs bind workspace owner, separate Editor session ID, asset IDs/hashes/ranges, target brief/sequence, expected revision and task ID. Server revalidates selection. No filename-only handoff or late result applied to another project. General persistent chat changes arrive with Phase 3, not as two unlinked chat/approval systems.

Renderer extensions need demonstrated requirements and focused tests. Current native plan/audio/duration limits must be checked before promising arbitrary multi-track film assembly. QA claims need actual timestamped observations; unavailable analysis stays blocked. Optional HyperFrames Studio/OpenMontage/Backlot adapters need installed version/license/auth and output roundtrip validation, never assumed embedding/replacement.

Update specialist skill wording only after corresponding runtime support exists. A paragraph about tools does not implement them. Existing style learning stays explicit/project-scoped; legacy saved sessions remain usable.
