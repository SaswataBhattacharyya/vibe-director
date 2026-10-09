# Development workflow — Luna implements, Sol reviews milestones

Current owner instruction. Use Ponytail (full) for development: reuse working code, make the smallest complete change, and keep required validation, recovery, security and accessibility. This file controls how agents work; stage plans control product behavior.

## Start here

1. Read `AGENTS.md`, `plans/README.md`, the issue and its stage plan.
2. Inspect the current product files before proposing new files. Product already uses `frontend/` and `backend/`; do not create the old proposed `app/services/adapters` scaffold.
3. Find the matching source feature below. Copy its smallest usable set of files, preserving validation/error handling. Adapt only the imports, paths, records and API/UI seams needed by Vibe Director.
4. List what was copied, what changed and why. If reuse cannot meet the requirement, explain the specific gap before adding new code.
5. Complete one issue-sized behavior, run only checks needed for its changed risks, update the handoff, and push its issue-linked branch/PR. Passing tests alone do not close an issue.

## Sources already available for copying/adaptation

| Source | Local folder | Use |
|---|---|---|
| Story Builder / mooV_E_maker | `/home/riki/web_dev/story_builder` | First choice for ComfyUI compilers, jobs/recovery, GPU safeguards, providers, V2 source processing and existing media tools. Upstream: `https://github.com/SaswataBhattacharyya/mooV_E_maker.git` |
| OpenMontage | `/home/riki/web_dev/OpenMontage` | Inspect useful retrieval, production visibility, recovery and assembly code. Upstream: `https://github.com/calesthio/OpenMontage.git`; last reviewed commit `9327439db69021ab4b0e2776729bf3b58fdb5a87`. Covered-source copying remains subject to the license decision in `openmontage_licensing.md`. |
| ComfyUI setup | `/home/riki/web_dev/setup_comfy_and-stuff` | Reuse installed models/nodes/runtime through configured paths. Do not duplicate weights or environments. |

References stay outside product Git and are read-only. Record the selected files' source commit/hash and relevant local differences. Reuse existing product copies first. Never import whole repos, source credentials, caches or media. Test assets from Story Builder can be used locally without committing them.

## Luna is the lead implementation agent

Use the user's selected Luna model for routine implementation, copying, file edits and focused checks. Luna reads the issue and inspects the source directly; Sol does not need to prepare a second long delegation prompt for every task. Do not spawn a new agent for a trivial edit. This development model choice is independent of the app's reasoning-provider choice.

A task needs only this short card, written in the issue/PR or handoff:

- Outcome: the visible behavior to deliver.
- Source: existing product/source files to reuse, with provenance.
- Change: the minimal adaptation and files expected to change.
- Constraints: relevant stage-plan rules and API/data requirements.
- Check: one or a few checks for the actual risks; reuse retained evidence.
- Done: evidence, pending gaps, branch/commit/PR and next action.

Avoid copying all plans into an agent prompt. Link the relevant files and give a small task. Do not add abstraction layers or dependencies for hypothetical future work.

## GPT-6.1 Sol review points

Request a bounded review using model `gpt-6.1-sol` after these milestones:

1. **Story → screenplay:** source import/revisions, selected-text editing, graph/source coverage and readable screenplay work together.
2. **Assets → video:** character/world/frame/voice and T2V/FFLF/R2V screens use the exact supported inputs and shared job/recovery service.
3. **Automation → export:** both modes resume safely, preserve full screenplay coverage and clips, and produce the approved ordered export.

For each review, give Sol the milestone goal, changed files/diff, source provenance, checks already done, known gaps and one specific review request. Sol reads relevant contracts, finds concrete defects or omissions, and may make bounded fixes. Luna continues afterward. Do not request an entire-project review every issue or rerun broad tests at each review.

Request Sol earlier only for a concrete blocker, a risky shared contract/data change, an ambiguous submission/recovery defect or a genuine product contradiction. Review cost comes from a bounded diff and relevant files, not model choice alone.

## Delivery and UI ownership

Ashu owns UI design. Keep his PR22 foundation and all three themes; implement provisional controls in that structure. Record exactly what works and what still needs Ashu's design. Review/fetch Ashu's changes at milestones and before editing shared files; merging follows the owner's existing authorization and collaborator review agreement.

Push completed, reviewed issue work periodically. Update issue/PR progress from actual evidence, not planned behavior. Keep `plans/HANDOFF.md` concise with the current goal, authoritative files, completed checks, pending work, blockers and live process/job handles.

## Checks and owner acceptance

Reuse the retained legacy test evidence; do not repeat the 600+ suite. Run focused checks only for a changed behavior or unresolved risk. For asset-generation acceptance, prepare the UI with exact prompts/settings/references and GPU monitoring, then ask the owner to click Generate. Normal user-started automated runs follow their saved policy. Show the working UI in Codex after changes.

Codex is the initial app reasoning provider. Other provider/model adapters remain later work. The lead development agent being Luna does not change the app provider or authorize hidden generation.
