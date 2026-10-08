# Current planning handoff — 2026-10-08

## Objective and authoritative files

Plan the new Story Builder journey using existing code as reusable material. The current `plans/README.md` and linked screenplay, rectification, character/world, video, glossary and execution-wrapper plans govern product behavior. Older migration plans are historical source/reuse evidence and do not set the new journey.

## Completed decisions

Merged story/canvas authoring; source-linked knowledge graph; readable screenplay with integrated direction; derived JSON/prompts; scene/shot/clip terminology; skippable visual preparation; model-specific prompt evolution and budgets; screenplay-versus-take overrides; recommended/unselected character image and bound voice references; duration/output controls; Manual/Semi/Full wrappers; Full T2V scene starts with previous-clip R2V continuation and retention of every clip.

## Pending planning and verification

The user has specified Media Prep; `media_prep.md` now defines reuse/arrangement of Video Repertoire & Summariser, the four audio tools, Audio Repository, Image Detailer and a new Image Repository. Common JSON metadata, readable descriptions and searchable asset registration connect them to story reference pickers. Final video/audio assembly remains to be explained. Exact image model prompt budgets and local graph parameters/capacity need integration verification. Shared-voice multi-character mappings need adaptation to the current compiler rather than duplicated asset slots. Runtime/provider and implementation architecture remain separate work.

## Scope, permissions and live work

Only Markdown planning files were edited; no Story Builder application or ComfyUI workflow was changed and no generation was launched. Canonical project path: `/home/riki/Documents/ChatGPT/Vibe Director`. Current session writable-root configuration points to the earlier `Vibe Director 2` path, so authorized plan writes use reviewed filesystem escalation. There are no live generation jobs or process handles from this update.

## Latest checks

Media Prep source review covered the six named existing frontend pages. The supplied screenshots support the video tab layout and Audio Studio arrangement. Localhost port 8080 was unreachable; no live browser verification was possible. Image Detailer exists but its inspected page lacks the requested image-repository interface. Only plan/index/handoff Markdown changed in this update.

## Latest automation/navigation decisions

`automation.md` is authoritative; `execution_modes.md` is now a superseded pointer. Regular story production inserts Automation & Parameters after screenplay and before model prompts. Semi exposes exactly five checkboxes: character images, character-to-audio selection, world images, frame images, video generation. Checked stages confirm defaults/settings. Automatic video fixes quality/non-duration parameters initially; duration can be fixed or Director-selected per clip. Full automatic video uses T2V scene starts and previous-clip R2V continuation. Semi automatic video lets the Director choose FFLF or R2V using prepared resources, with optional previous-video continuity for R2V. Shared generation screens allow isolated entry without story setup. Production V2, Generate, old Automation Studio and Manual Director are retired as pages; Status remains a connectivity/workflow/limits catalogue.

The user clarified Semi: the Director chooses FFLF or R2V using prepared frames/character images/voices/world images; R2V may also use the preceding video within a scene. Manual pickers remain recommendation-only, but confirmed Semi automation authorizes reference selection. The user explicitly reconfirmed Full: first clip of each scene T2V, later clips R2V with the previous video. Both routing questions are resolved. The inspected current FFLF graph has two frame inputs and no direct voice-reference slot; required direct voice conditioning needs a compatible R2V route or a verified future adapter. No application code, workflow or GPU generation changed during this update.


## OpenMontage assessment — 2026-10-08

`openmontage_comparison.md` records a source-based comparison with current plans, reviewed at upstream commit `9327439db69021ab4b0e2776729bf3b58fdb5a87` (fetched main matches). Recommended technical direction: keep the planned journey and existing local H3 integrations; evaluate selected assembly, progress, capability and retrieval components. Backlot is read-only, standard creative gates and selector routing need adaptation, cloud H3 parameters cannot substitute for local graph contracts, and AGPL licensing must fit intended integration/hosting. These are assessment/proposals, not adopted requirements. Earlier comparison was not found in canonical Markdown, so exact historical assertions could not be verified. No runtime tools were installed/launched or application source changed. Review checkout is `/tmp/openmontage-review-20261008`; no live job handles remain.


The OpenMontage comparison now includes section 9 on Ashu's open StudioDirector design issue #1 and its embedded HTML mockup, both independently fetched via GitHub. Useful UX fixes include visible context/next task, conditional requirements, readable editors, clear offline/recovery states and mobile layouts. Reconcile story-led entry, manual acceptance and legacy access with the current isolated-entry, automation and retired-page decisions. No issue comment/approval or implementation was performed.


## Integration-plan update

User requested integrating the three contributions and updating/adding plans. Added authoritative cross-cutting `ux_shared.md` and `integration.md`; stage plans now reference shared UI/recovery and source reuse. Existing story/editing/Manual/Semi/Full policies remain intact. Integration records existing Story Builder/ComfyUI paths and the temporary pinned OpenMontage review checkout; durable ignored source checkout is proposed, not created. Covered-source adoption/license compatibility, exact modules/dependencies, runtime architecture and final assembly remain implementation decisions. No source apps, model storage or GitHub issues were modified and no jobs launched.


## Collaboration/backlog update — 2026-10-08

User cloned OpenMontage and requested an issue plan separating Ashu's UI/product design from selective source reuse/backend adaptations, before creating/publishing product issues. Verified durable clone `/home/riki/web_dev/OpenMontage` at reviewed SHA `9327439db69021ab4b0e2776729bf3b58fdb5a87`. Correction from the owner: Story Builder upstream is `https://github.com/SaswataBhattacharyya/mooV_E_maker.git`. Only the inspected local folder lacks Git metadata; Ashu can clone the existing repository with access. Record the clone commit and compare selected local/upstream files before reuse; the previously proposed new snapshot repository/archive is unnecessary. Canonical product has empty `main`, no commits and no remote as checked this turn.

Added `plans/issue_backlog.md` and 14 local issue drafts under `plans/issues/`: two groundwork, six design, five backend/integration and one later assembly design. Design outputs require human acceptance and later bounded UI implementation issues; proposed leads are not assignments already accepted by Ashu. First milestone is isolated T2V/progress/playback/retake, alongside API/reuse contracts. Updated source placement, plan entrypoints and collaboration guidance.

No source application edits, initial Git commit, remote creation, collaborator invitation, issue publication, dependency installation or GPU job was performed. Pending: user creates the private Vibe Director repository; verify access to existing Story Builder upstream and local/upstream baseline; reuse/license/runtime decisions; accepted UI designs and later implementation. No live process/job handles. Current authoritative files remain `plans/README.md` and linked stage plans.


## Story Builder repository correction

The owner supplied the existing `SaswataBhattacharyya/mooV_E_maker` clone URL. Corrected README, collaboration guidance, source access issue G1, backlog and integration plan to use it. Remote contents and correspondence to the inspected local folder have not been checked in this correction; G1/G2 record that bounded verification. No GitHub issue, source repository, invitation or application code was changed.


## Repository publication preparation

User authorized creation of a private Vibe Director repository and upload of all plans plus publication of all 14 issue drafts. GitHub connector authenticated as SaswataBhattacharyya, but exposes no repository-creation capability; local GitHub CLI, token environment and Git credential helper are absent. Requested the user create an empty private `vibe-director` remote while local preparation continues. Target lookup returned 404 via connector; this does not by itself distinguish absence from missing installation access.

Reviewed all 64 existing planning Markdown files (approximately 760 KB); credential-pattern scan found no matching private-key/GitHub-token/OpenAI-key strings. Added ignore rules and a portable agent entrypoint. Source trees/models/media remain external. Issue publication is pending remote availability/access; no remote upload or issue creation occurred at this milestone.


## Public publication authorization and access blocker

The owner explicitly authorized public publication to https://github.com/SaswataBhattacharyya/vibe-director, superseding private visibility. The first README upload was rejected with HTTP 403 Resource not accessible by integration; no file, commit or issue was created remotely by this attempt. Connector repository listing contains only H2H; user was asked to add vibe-director to the GitHub app installation. Local GitHub CLI/tokens/credential helper are absent, and host SSH agent has no identities. No alternate authenticated push route is available.

All 66 files and 14 GitHub-safe issue bodies are staged in /tmp/vibe-publication and functions store publication_files/publication_issues. On access restoration: verify target, initialize README if repository remains empty, upload full tree, publish issues with idempotent checks, update backlog with real links, and synchronize local Git with remote. No live jobs/process handles.
