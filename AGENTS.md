# Vibe Director agent entrypoint

## Owner completion sequence — 2026-10-13

Use `plans/CODING_COMPLETION_GATE.md` as the finite copying/coding exit ledger. Luna closes C1–C12 directly using current source and retained evidence; then one consolidated GPT-6.1 Sol medium review/fixes; then owner manual testing with Debug ON. This sequence supersedes older review timing for this completion handoff. Do not release manual tests while required coding/configuration items remain open. No workers or routine helper reviews.


## Workspace check — 2026-10-12

The product checkout is `/home/riki/Documents/ChatGPT/Vibe Director`. This task currently runs from that exact directory (`pwd` verified), and project edits have succeeded here. Older notes about this task being bound to the nonexistent `Vibe Director 2` path are historical; re-check the current task's `pwd` and write capability before diagnosing or requesting approval. Never create a duplicate project or change mount options to repair a stale path.

## Owner correction — 2026-10-11 (authoritative)

Luna implements, checks and fixes each part directly; no Luna workers. The next planned GPT-6.1 Sol medium review is after P2–P6 are complete, followed by a final review after P7 and remaining integration fixes. Do not invoke Sol per helper, copied tool, issue, slice or individual stage. Earlier Sol help is only when Luna is genuinely stuck on a specific issue after focused investigation; a potentially risky change alone is not a trigger. Pass relevant files, evidence and one concrete question. Sol may make bounded fixes without spawning workers; Luna verifies them itself. Do not request an automatic follow-up Sol review. This replaces all older R1/R2/R3 and three-milestone review triggers.

Reuse Story Builder’s video_audio_analyzer, Video Repertoire/Summariser, audio tools and Image Detailer as the main implementation. Copy/adapt the smallest working file set and existing Vibe adapters; change only necessary imports, paths, API/UI seams, shared asset metadata and job/GPU safeguards. Do not rewrite engines or build speculative frameworks. Implement notes.md’s nested pages, search, carousels, previews and saved selections alongside wiring; current UI shells are not completion evidence.

Implementation is active because the owner has resumed the runtime goal. Git coordination remains deferred; live acceptance is owner-clicked. Older runtime-status prose is historical; use the goal tool for actual status.


Read `plans/README.md` and `plans/development_workflow.md` first. It indexes current product requirements. Read `plans/issue_backlog.md` and the stage plan linked by your issue before designing or implementing. Older `plans/migration/`, `plans/archive/ideas/`, `plans/archive/PLAN.md` and `plans/archive/REUSE_AUDIT.md` are historical evidence; their conflicting journeys do not override current plans.

## Collaboration and source reuse

Use issue-linked branches/PRs. Design issues produce accepted layouts, decisions and API needs; implementation issues require demonstrated behavior. Proposed leads are not exclusive ownership. Do not close implementation work on test counts alone.

Story Builder reference repository: `https://github.com/SaswataBhattacharyya/mooV_E_maker.git`. OpenMontage reference repository: `https://github.com/calesthio/OpenMontage.git`, reviewed commit `9327439db69021ab4b0e2776729bf3b58fdb5a87`. Keep reference clones outside product Git. Host-specific paths in source audits identify inspected material; substitute your local clone path. Confirm selected source versions/differences before extraction and record files, provenance, dependencies and required adaptations.

Use one durable execution service and one shared asset identity/library. OpenMontage covered-source imports require a compatible license decision before copying. Preserve source applications, user media, runtime environments and model storage. Models/secrets/media are not repository content.

## Runtime, provider and acceptance boundaries

- Before authorized generation, inspect the actual ComfyUI graph, nodes, models and runtime; reuse Story Builder `gpu_runtime.py`, `gpu_watchdog.py` and `media_jobs.py` safeguards, including independent monitoring through browser work and recovery. Owner approved a 90°C application cutoff on 2026-10-21, replacing 83°C; the 2100 MHz ceiling remains. 85°C is legacy operator guidance, not the code cutoff. Confirm hardware-specific policy. Never alter clocks.
- For uncovered adapter/workflow acceptance, prepare the exact prompt/settings/references, graph readiness, queue and monitor first, then have the user click Generate. Do not automate submission behind the scenes. This test gate does not change an explicitly user-started Assisted manual/Fully automated run. Keep mocks explicit and show/reload changed usable UI in Codex from the intended branch/backend.
- Reasoning-provider choices are separate from ComfyUI workflow choices. Codex CLI is the initial end-to-end app completion/acceptance baseline. Do not make OpenCode/direct APIs/flexible models or weaker Ollama/Qwen support completion gates; existing Ollama may remain unchanged. Preserve provider_exec_guard and typed JSON parsing. Defer future providers/models until the Codex app works; validate capabilities per adapter/model because one Qwen/API success does not prove others. App model choices are independent of Luna-led implementation and Sol milestone review.

## Verification and scope

Read the current Assisted manual/Fully automated rules in `plans/automation.md`; avoid parallel controllers or retired-page navigation. Human-readable screenplay precedes derived production prompts. Direct isolated generation uses the same screens without story prerequisites.

Design and source inspection do not authorize paid/provider or GPU generation. Actual generation checks need bounded authorization and existing runtime supervision. Mocked UI, CPU tests and a real usable render are distinct evidence. Prefer focused producer-to-consumer and recovery checks for the changed behavior.

Keep `plans/HANDOFF.md` concise and current at meaningful milestones: objective, authoritative files, completed evidence, pending work, blockers/permissions and live job/process handles. Runtime compaction follows configured settings; do not invent usage percentages or claim a written handoff compacted runtime context.

## Implementation leadership

Ponytail full is active. Luna is the main agent and implements directly from issues and reference files. Do not spawn Luna subagents or routine implementation workers. GPT-6.1 Sol medium review is deferred until P2–P6 are complete and the final P7/integration checkpoint; ask earlier only if Luna is genuinely stuck on a specific issue after focused investigation. Sol may make a bounded fix, then Luna verifies it and continues. Sol reviewers must not spawn workers. Read the source reuse table before adding new code.

## Notes-integrated task packet

Read `plans/remaining_app.md` for the current sequence and corrections before implementing older stage descriptions. `plans/OWNER_DUMMY_RUNS.md` defines focused owner-clicked acceptance. No standalone Prompts page; automatic graph preparation, combined Characters & Voices, nested Media Prep/Search and corrected Next behavior supersede older conflicting plan text. Keep Luna direct implementation, bounded Sol 6.1 medium milestone review and local-only work.

## Latest prerequisite/state review

Read `plans/implementation/luna_progress_review.md` before continuing P5/P6. Trace UI action → actual backend prerequisites → saved result → next destination before retiring an old entry. Include a focused fresh-state journey without prepopulated derived prompts/plans and relevant workspace/recovery checks. Dormant Prompts source is not a reachable recovery page. Assisted planning is not proof of a working automated runner. Runtime goal status governs pause/resume; this owner-requested review does not introduce routine Sol reviews.

## Graphify and UI verification

- This checkout has a Graphify code graph in `graphify-out/graph.json`. Use it to trace UI-to-service relationships, callers and likely affected modules before substantial implementation changes; confirm conclusions in source and current plans.
- Refresh the local code graph after meaningful code changes with `conda run -n react graphify extract . --code-only --no-cluster`. The code-only graph does not index product plans; consult `plans/README.md`, `plans/remaining_app.md`, `plans/progress_review.md` and the relevant stage plan directly for requirements and status.
- Useful commands: `conda run -n react graphify query "..." --graph graphify-out/graph.json`; `conda run -n react graphify path "A" "B" --graph graphify-out/graph.json`; `conda run -n react graphify affected "Symbol" --graph graphify-out/graph.json`.
- For UI-related changes, use the Playwright MCP to inspect the relevant screen and verify changed interactions when the browser runtime is available. Keep provider, media, GPU and generation actions mocked or idle unless the owner starts the authorized acceptance run. If Playwright MCP cannot initialize, report the concrete runtime error; do not claim browser verification from typechecks or source inspection.

## Project directing skills

Use `skills/vibe-director/SKILL.md` for screenplay/direction and its linked `skills/video-prompting/SKILL.md` for rendering prompts. MiniMax H3 has a cited adapter; do not apply its syntax to other models. The app reads these project files during new screenplay/prompt/clip-plan preparation; already frozen runs are unchanged.
