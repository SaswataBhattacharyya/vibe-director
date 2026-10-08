# [G1] Prepare the product repository and reproducible reference sources

Status: published as [GitHub issue #1](https://github.com/SaswataBhattacharyya/vibe-director/issues/1). Type: Groundwork.

**Proposed lead/reviewer:** Saswata; Ashu reviews. These are proposals, not an assignment already accepted by Ashu.
**Dependencies:** None.
**Read first:** [current plans](../README.md), [issue working rules](../issue_backlog.md), then README.md, integration.md in `plans/`. Paths below are relative to the named reference source, except explicitly absolute paths.

## Outcome and scope

Use the separate public Vibe Director repository under SaswataBhattacharyya, attach this canonical working folder and invite ashucodesbio with the requested collaboration access. Verify the uploaded planning baseline and establish, ignore rules, dependency setup and a simple issue/PR workflow. Do not publish the entire local source tree or runtime storage. Public product visibility was explicitly authorized by the owner; source-repository access and licensing must still be checked.

Story Builder already has an upstream repository: `https://github.com/SaswataBhattacharyya/mooV_E_maker.git` (`mooV_E_maker`), confirmed by the owner. Ashu should clone it with the required access. The inspected local folder `/home/riki/web_dev/story_builder` lacks Git metadata; that local observation does not describe the upstream repository. Record the cloned branch/commit and compare selected reusable files against the inspected local folder, using hashes/diffs to identify any unpushed differences. Preserve the running local source and record its relevant differences without overwriting either source. No separate Story Builder snapshot repository/archive needs to be created. OpenMontage is available at `/home/riki/web_dev/OpenMontage`, reviewed SHA `9327439db69021ab4b0e2776729bf3b58fdb5a87`. Runtime remains separately configured at `/home/riki/web_dev/setup_comfy_and-stuff`.

## Questions to resolve in this issue

- Can Ashu clone `SaswataBhattacharyya/mooV_E_maker`, and which commit supplies the reusable-source baseline? Are there relevant local differences that need a reviewed source update?
- Will Ashu use mocked API responses, a shared development backend or a local backend for integration? Define access/configuration without copying credentials.
- What minimal setup lets either person start UI work without GPU/model installation?

## Acceptance evidence

- A fresh collaborator can read current plans, obtain both reference sources and start the agreed development mode.
- Both reference clones have recorded commits and documented dependency/configuration entrypoints; selected Story Builder files are compared with the local inspected source, with relevant differences recorded.
- Ignore rules exclude credentials, environments, model weights and generated/source media; initial staged contents are reviewed.
- Repository access and first PR review/merge are demonstrated. Record branch-rule availability rather than assume enforcement.

## Handoff

Link the design/implementation PR, decisions, changed-file provenance and demonstrated evidence. Record unresolved dependencies explicitly. Follow the authoritative plans; ask about a real contradiction instead of reintroducing legacy pages or changing agreed mode policies.
