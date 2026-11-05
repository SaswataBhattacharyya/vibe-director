# Vision and user outcomes

## Corrected Agentic Filmmaking definition
The user tells the Director a goal such as "Turn this story into a polished five-minute film. First show me exactly what you will do." The Director reads the project, drafts an end-to-end production plan with deliverables, creative choices, timeline, model capabilities, reference assets, cost/resource risks, review and editing stages, and **waits for authorization**. When the user explicitly says "Implement the plan", it enters implementation mode and acts like an appropriately permissioned Codex agent: it can inspect/edit files, run tests and scripts, use Git, navigate graphical software through computer/browser automation, call app filmmaking APIs, assemble previews, diagnose defects, arrange retakes and delegate finishing to Vibe Editor. It reports progress tied to real task/job events and can resume after interruption.

## Two equal entry modes
**Manual:** jump directly to any page (story, style, screenplay, images, reference manager, storyboard, video, take, editor, Media Prep, export). No prior page approval required to use unrelated manual tools. Manual drafts and jobs are related back to the project graph opportunistically.

**Agentic:** chat-first end-to-end plan. Agent may perform many steps through tools AFTER user authorizes implementation, subject to approvals for costly/destructive/external-sensitive actions. A user can manually take over any task while remaining inside the same project.

## Two distinct meanings of "plan"
1. **Creative plan:** story beats, scene/clip/shot decomposition, art direction, voices, storyboard, generation reference manifests, editing, sound and final runtime.
2. **Executable plan:** DAG of verified tool operations, registered input IDs, budgets, permissions, dependencies, recovery and acceptance checks. An attractive story outline is NOT executable work.

## One project, multiple collaborators
The Director owns orchestration/continuity; the Editor specialist owns cut/retime/audio/composition review and can access the *same* validated tool gateway, knowledge and task timeline. Z-Image, MiniMax, FFmpeg, Blender, Media Prep, OpenMontage and Backlot are tools/delegation endpoints, not isolated narrative authorities. Neither agent may invent assets, pretend tools were called, rewrite historical jobs, or bypass owner consent.

## Define done
For `make entire film`, done means an assembled, playable, verified export plus an accompanying manifest of chosen takes, source assets, used tools, and known quality exceptions. A finished screenplay or disconnected set of clips is **partial work**. When user chooses an earlier stopping point, label that step complete without declaring the entire film finished.

## Examples
- "Make a screenplay and stop" -> plan/write/save screenplay only.
- "I have 2 characters and a video last frame; give the next MiniMax prompt" -> select correct route/refs, 15s/strict <7000 characters; no unrequested generation.
- "Generate the entire fable" -> propose full plan, user approves, run steps, evaluate takes, send edit package, export.
- "Fix the gibberish at the start of the third clip" -> inspect actual audio using existing Media Prep/analysis tools; do not guess timestamps, extract/repair/re-edit and review.
- "Add a new capability" -> plan coding change, ask approval; then Git branch, patch, test, validate and register adapter.
