## Completion gate — owner correction, 2026-10-13

[CODING_COMPLETION_GATE.md](CODING_COMPLETION_GATE.md) is the finite copying/coding exit ledger: Luna closes required implementation and configuration, then consolidated Sol 6.1 medium review/fixes, then manual acceptance with Debug ON. This supersedes older review timing for the current completion handoff. Reuse existing evidence and code; do not restart completed work.

## Latest review correction — 2026-10-12

Use [progress_review.md](progress_review.md) and [HANDOFF.md](HANDOFF.md) for current phase state and the compact next task. Before retiring any page, trace its backend prerequisites and preserve every user responsibility at a working destination. Verify a fresh-state path without prefilled derived prompts/plans; source/type checks alone do not prove the journey. Assisted planning, reference persistence and its durable automatic runner are implemented; live workflow compatibility and owner acceptance remain open. Global Prompts is a retired route; dormant source is not a usable recovery page. The owner requested local implementation only; defer Git hosting work until explicitly requested. Review cadence remains unchanged.

# Development workflow — Luna implements, Sol reviews at substantial milestones

## Owner correction — 2026-10-11 (authoritative)

Luna implements, checks and fixes each part directly; no Luna workers. The next planned GPT-6.1 Sol medium review is after P2–P6 are complete, followed by a final review after P7 and remaining integration fixes. Do not invoke Sol per helper, copied tool, issue, slice or individual stage. Earlier Sol help is only when Luna is genuinely stuck on a specific issue after focused investigation; a potentially risky change alone is not a trigger. Pass relevant files, evidence and one concrete question. Sol may make bounded fixes without spawning workers; Luna verifies them itself. Do not request an automatic follow-up Sol review. This replaces all older R1/R2/R3 and three-milestone review triggers.

Reuse Story Builder’s video_audio_analyzer, Video Repertoire/Summariser, audio tools and Image Detailer as the main implementation. Copy/adapt the smallest working file set and existing Vibe adapters; change only necessary imports, paths, API/UI seams, shared asset metadata and job/GPU safeguards. Do not rewrite engines or build speculative frameworks. Implement notes.md’s nested pages, search, carousels, previews and saved selections alongside wiring; current UI shells are not completion evidence.

Implementation is active because the owner resumed the runtime goal. Git coordination remains deferred; live acceptance is owner-clicked. Older runtime-status prose is historical; use the goal tool for actual status.


## Current task packet — 2026-10-11

Luna reads `remaining_app.md` and only the relevant task files; it implements directly, with no Luna workers. Do not invoke Sol for each part, copy or small edit. The first Sol 6.1 medium review is after P2–P6 are complete; the final review is after P7 and remaining integration fixes. Ask earlier only if Luna is genuinely stuck on one specific issue after focused investigation. Use `OWNER_DUMMY_RUNS.md`: prepare real UI inputs and monitoring for the owner to start the operation. Distinguish mock walkthrough from actual generation. Notes corrections override conflicting older stage journeys.


Use Ponytail full: reuse working code and make the smallest complete change, while keeping validation, recovery, security and accessibility. Luna is the implementation lead. This file says how to work; stage plans say what the product does.

## Start here

1. Read `AGENTS.md`, `plans/README.md`, the issue and its stage plan.
2. Inspect the current product files before proposing new files. Product already uses `frontend/` and `backend/`; do not create the old proposed `app/services/adapters` scaffold.
3. Find the matching source feature below. Copy its smallest usable set of files, preserving validation/error handling. Adapt only the imports, paths, records and API/UI seams needed by Vibe Director.
4. List what was copied, what changed and why. If reuse cannot meet the requirement, explain the specific gap before adding new code.
5. Complete one issue-sized behavior, run only checks needed for its changed risks, and update the handoff. Work in the current local checkout; do not do Git/GitHub coordination unless the owner asks. Passing tests alone do not close an issue.

## Sources already available for copying/adaptation

| Source | Local folder | Use |
|---|---|---|
| Story Builder / mooV_E_maker | `/home/riki/web_dev/story_builder` | Copy/adapt first for ComfyUI workflows, jobs/recovery, GPU safeguards, V2 story processing and media tools. Upstream: `https://github.com/SaswataBhattacharyya/mooV_E_maker.git` |
| OpenMontage | `/home/riki/web_dev/OpenMontage` | Inspect for useful retrieval, production status, recovery and assembly code. Upstream: `https://github.com/calesthio/OpenMontage.git`; last reviewed commit `9327439db69021ab4b0e2776729bf3b58fdb5a87`. Copy only if the license decision in `openmontage_licensing.md` allows it. |
| ComfyUI setup | `/home/riki/web_dev/setup_comfy_and-stuff` | Reuse installed models/nodes/runtime through configured paths. Do not duplicate weights already here or whole environments. Required donor-local weights/resources are selectively migrated under `donor_independence.md`. |

References stay outside product Git and are read-only. Record the selected files' source commit/hash and relevant local differences. Reuse existing product copies first. Never import whole repos, source credentials, caches or media. Test assets from Story Builder can be used locally without committing them.

## Luna is the lead implementation agent

Use the user's selected Luna model as the main agent for implementation, copying, file edits and focused checks. Luna reads the issue and inspects the source directly. Do not spawn Luna subagents or routine implementation workers, even for larger tasks; complete manageable slices sequentially. Sol does not prepare a second delegation prompt for every task. This development model choice is independent of the app's reasoning-provider choice.

A task needs only this short card, kept in the handoff during the local phase (or in its issue/PR after Git coordination resumes):

- Outcome: the visible behavior to deliver.
- Source: existing product/source files to reuse, with provenance.
- Change: the minimal adaptation and files expected to change.
- Constraints: relevant stage-plan rules and API/data requirements.
- Check: one or a few checks for the actual risks; reuse retained evidence.
- Done: evidence, pending gaps, and next local action. Add branch/commit/PR details only after Git coordination resumes.

Avoid copying all plans into an agent prompt. Link the relevant files and give a small task. Do not add abstraction layers or dependencies for hypothetical future work.

## GPT-6.1 Sol review cadence

Sol reviews are intentionally infrequent to control token use. Luna implements and checks each part directly. Do not request reviews after individual stages, helpers, copied tools or ordinary edits.

1. One substantial review after P2–P6 are complete.
2. One final review after P7 and remaining integration fixes.

For each review, give Sol the goal, changed files/diff, source provenance, focused checks, known gaps and one concrete question. Sol may make a bounded fix but must not spawn workers; Luna verifies it and continues. Ask earlier only if Luna is genuinely stuck on a specific issue after focused investigation. A risky change by itself does not trigger review. Never repeat the retained 600+ test suite.

## Delivery and UI ownership

Complete the full functional UI and backend wiring locally now; see `GOAL.md`. Keep the approved UI foundation and themes. Ashu's fine design/detail refinement follows after the owner asks to resume Git coordination and share the completed work.

Ashu owns UI design. Keep his PR22 foundation and all three themes; implement and wire the product in that structure. Record exactly what works and what still needs Ashu's design. Do not fetch/pull his changes during the local phase; review and integrate them after the owner resumes Git coordination.

Keep `plans/HANDOFF.md` concise with the current goal, authoritative files, completed checks, pending work, blockers and live process/job handles. Defer remote issue/PR updates, collaborator fetches/pulls, commits and pushes until the owner explicitly requests them.

## Checks and owner acceptance

Reuse the retained legacy test evidence; do not repeat the 600+ suite. Run focused checks only for a changed behavior or unresolved risk. For asset-generation acceptance, prepare the UI with exact prompts/settings/references and GPU monitoring, then ask the owner to click Generate. Normal user-started automated runs follow their saved policy. Open/reload the working UI occasionally at meaningful UI checkpoints and for manual acceptance tests; do not reopen it after every code change.

Codex is the initial app reasoning provider. Other provider/model adapters remain later work. The lead development agent being Luna does not change the app provider or authorize hidden generation.
