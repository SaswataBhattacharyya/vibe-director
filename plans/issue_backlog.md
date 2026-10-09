> Current execution: Luna implements issue-sized changes; Sol reviews the milestones in `development_workflow.md`. Modes follow the latest `automation.md`: Assisted manual with none/some/all checked, plus the distinct image-free Fully automated preset.

# Collaboration and issue backlog — Vibe Director

Updated 2026-10-08. All 14 issue specifications are published on GitHub. G1/D1/B1 etc. remain planning IDs; the publication table maps them to GitHub issue numbers.

## Repository and sources

Use one separate **public Vibe Director product repository**, owned by `SaswataBhattacharyya`, with `ashucodesbio` collaborating on product, design, implementation and review. The owner created `https://github.com/SaswataBhattacharyya/vibe-director` and explicitly authorized public publication, superseding the earlier private choice. This canonical folder has the initial planning commit; the publication record below tracks remote files/issues.

Ashu should obtain:

1. **Vibe Director:** plans, issues, accepted designs and later code. This is the source of product decisions.
2. **Story Builder reference source:** clone `https://github.com/SaswataBhattacharyya/mooV_E_maker.git` with the required repository access. This is the existing `mooV_E_maker` repository, identified by the owner as Story Builder. Local inspected source is `/home/riki/web_dev/story_builder`; missing Git metadata in that folder does not mean the upstream repository is absent. Record the cloned commit and compare the files selected for reuse with the inspected local source before extraction; do not assume local and remote versions match. G1 verifies access and the source baseline. No new Story Builder reference repository/archive is required.
3. **OpenMontage reference source:** clone `https://github.com/calesthio/OpenMontage.git` for candidate components; pin reviewed commit `9327439db69021ab4b0e2776729bf3b58fdb5a87`. Local durable clone is `/home/riki/web_dev/OpenMontage` and matches that commit.

Models/ComfyUI are not required for wireframes, mocked UI or API contract work. Real generation needs an agreed accessible backend or local runtime and its verified graph/node/model setup. Keep existing model storage separate; do not place both full upstream trees or weights in the product Git repository. Read upstream instructions in their source context; the current product plans govern this new product.

## Working rules for Ashu and LLM implementers

- Read [README.md](README.md) and the linked stage plan for the issue. Older migration documents and upstream app flows are reuse evidence, not current requirements.
- Ashu owns UI design for D issues, with Saswata reviewing. The provisional engineering UI does not transfer that ownership; only Saswata’s explicit decision can do so. Backend tasks have a proposed implementer, not a permanently exclusive owner. Either collaborator can contribute to either area.
- **Design issue:** answer its open questions, provide annotated wireframes/prototype, record decisions and API/state requirements in a PR, and propose bounded implementation follow-ups. Close only after the other collaborator accepts the design. Closing a design issue does not imply production functionality exists.
- **Implementation issue:** use the accepted design/contracts, identify reused/adapted/new files and demonstrate the user-visible behavior. Split broad work into bounded PRs rather than claim one huge task is surgical.
- Link each PR to its issue. Either person can merge after the other reviews under the agreed collaboration rule. Keep disagreements and alternatives visible in the issue.
- Do not reopen settled mode recipes, screenplay order, isolated entry or retired pages. Design questions concern presentation or genuinely unspecified architecture.
- Source inspection is read-only. Record exact source files/hashes and dependencies before extraction. Do not copy secrets, source media, models or environments. Check license compatibility before copying covered upstream code; AGPL candidate imports are conditional, not automatically approved by a private repository.
- Do not launch costly generation to design a screen. Verification should demonstrate the changed behavior and relevant recovery path; test count is not UI acceptance.

## Division of work

**Reuse with bounded adaptation:** local workflow compilers, capability checks, durable job/take services, media tools and useful frontend components. Verify their real dependencies and producer/consumer contracts before copying.

**New or substantial work:** merged conversational authoring, source-linked knowledge graph, human-readable integrated screenplay, new route/navigation composition, Image Repository, exact new wrapper policies and missing search/contract behavior. These cannot be honestly promised as only copy/paste.

**Conditional OpenMontage adoption:** visibility/events/retrieval/cost or later assembly helpers where a specific gap exists. Its read-only Backlot, selector fallback behavior and human approval gates do not define our product. Retain one execution authority and one asset library.

The old StudioDirector issue is design evidence. This backlog translates useful ideas into the current agreed requirements; it does not automatically close or duplicate that external issue.

## Issue drafts and dependencies

| Draft | Workstream | Depends on |
|---|---|---|
| [G1: Prepare the private repository and reproducible reference sources](issues/G1-groundwork-source-access.md) | Groundwork | None |
| [G2: Map reusable services and define the UI/API boundary](issues/G2-backend-reuse-contract.md) | Groundwork | G1 source access; can begin locally now |
| [D1: Design shared navigation for story-led and isolated creation](issues/D1-shared-navigation-design.md) | UI/product design | Read G2 draft contracts; can design before backend exists |
| [D2: Design merged story authoring and the readable screenplay](issues/D2-story-screenplay-design.md) | UI/product design | D1; G2 revision contract draft |
| [D3: Design optional character/world/frame creation and voice binding](issues/D3-assets-voices-design.md) | UI/product design | D1; G2 asset contracts |
| [D4: Design three video forms, reference collation and take review](issues/D4-video-generation-design.md) | UI/product design | D1; G2 workflow contracts |
| [D5: Design Automation & Parameters and shared run monitoring](issues/D5-automation-design.md) | UI/product design | D1; G2 run-policy draft |
| [D6: Arrange Media Prep libraries/tools and the Status catalog](issues/D6-media-prep-status-design.md) | UI/product design | D1; G2 library/capability contracts |
| [B1: Connect isolated T2V from edited prompt to durable job and retake](issues/B1-isolated-t2v-slice.md) | Backend + UI integration | G2; D1/D4 accepted for this slice |
| [B2: Adapt V2 revisions and build real story edits/graph/screenplay derivation](issues/B2-authoring-screenplay-backend.md) | Backend + UI integration | G2; D2 accepted; deliver in separate bounded PRs |
| [B3: Adapt image/voice assets and exact FFLF/R2V request compilation](issues/B3-asset-workflow-adapters.md) | Backend + UI integration | G2; D3/D4 accepted; B1 durable execution boundary |
| [B4: Reuse Media Prep services behind one searchable asset library](issues/B4-media-library-adaptation.md) | Backend + UI integration | G2; D6 accepted |
| [B5: Implement the two modes using the shared execution service](issues/B5-automation-runtime.md) | Backend + UI integration | B1/B3 contracts; B2 screenplay coverage; D5 accepted |
| [F1: Define final clip assembly, sound and export before selecting tools](issues/F1-assembly-design-later.md) | Later design | Generation/take journey stable; user supplies assembly intent |

## First milestone and publication order

1. Create/configure the public product repository and share this planning set. Complete G1 source access; G2 contract/reuse decisions can begin from the local sources immediately.
2. Start with G1, G2 and D1/D4; these are published as issues #1–#4. Agree navigation and video interaction, then make **isolated T2V → progress → playback → preserved retake** work as B1. Ashu can prototype using G2 fixtures while backend adaptation proceeds.
3. Use D2/D3/D5/D6 as parallelizable design work once shell/context/contracts are clear. Convert accepted designs into small UI implementation issues, by screen/behavior; do not treat the D issue itself as an all-in-one implementation ticket.
4. Schedule B2/B3/B4/B5 after their relevant contracts/designs are accepted. Their drafts state required outcomes; split them into child issues if the source audit reveals wider changes.
5. Keep F1 in Later until the user defines final assembly. All issues are now published at the owner's request; publication does not mean a dependency-blocked or Later issue is ready for implementation.

First milestone acceptance: one usable isolated video journey with real input validation, saved state, engine-unavailable behavior, durable progress/playback and retake. UI evidence and an authorized monitored integration render are distinct from mocked demonstrations. The app remains planning-only until implementation evidence exists.

## What the design PR should contain

For each screen: purpose, entry/exit/context, annotated layout, editable fields and actions, optional/required inputs, saved-state behavior, loading/empty/offline/error/running/done states, mobile behavior, API requests/responses needed, and unresolved questions. A linked prototype plus written decisions is sufficient; choose the design tool together. No requirement to use Figma or install a second app stack.


## Published GitHub issues

Repository: [SaswataBhattacharyya/vibe-director](https://github.com/SaswataBhattacharyya/vibe-director), public by the owner's explicit instruction. All 66 planning/guidance files have been uploaded; no application implementation is claimed.

| Plan ID | GitHub issue | Stage |
|---|---|---|
| G1 | [#1: [G1] Prepare the product repository and reproducible reference sources](https://github.com/SaswataBhattacharyya/vibe-director/issues/1) | Planning/design |
| G2 | [#2: [G2] Map reusable services and define the UI/API boundary](https://github.com/SaswataBhattacharyya/vibe-director/issues/2) | Planning/design |
| D1 | [#3: [D1] Design shared navigation for story-led and isolated creation](https://github.com/SaswataBhattacharyya/vibe-director/issues/3) | Planning/design |
| D4 | [#4: [D4] Design three video forms, reference collation and take review](https://github.com/SaswataBhattacharyya/vibe-director/issues/4) | Planning/design |
| B1 | [#5: [B1] Connect isolated T2V from edited prompt to durable job and retake](https://github.com/SaswataBhattacharyya/vibe-director/issues/5) | Pending design/contracts |
| D2 | [#6: [D2] Design merged story authoring and the readable screenplay](https://github.com/SaswataBhattacharyya/vibe-director/issues/6) | Planning/design |
| D3 | [#7: [D3] Design optional character/world/frame creation and voice binding](https://github.com/SaswataBhattacharyya/vibe-director/issues/7) | Planning/design |
| D5 | [#8: [D5] Design Automation & Parameters and shared run monitoring](https://github.com/SaswataBhattacharyya/vibe-director/issues/8) | Planning/design |
| D6 | [#9: [D6] Arrange Media Prep libraries/tools and the Status catalog](https://github.com/SaswataBhattacharyya/vibe-director/issues/9) | Planning/design |
| B2 | [#10: [B2] Adapt V2 revisions and build real story edits/graph/screenplay derivation](https://github.com/SaswataBhattacharyya/vibe-director/issues/10) | Pending design/contracts |
| B3 | [#11: [B3] Adapt image/voice assets and exact FFLF/R2V request compilation](https://github.com/SaswataBhattacharyya/vibe-director/issues/11) | Pending design/contracts |
| B4 | [#12: [B4] Reuse Media Prep services behind one searchable asset library](https://github.com/SaswataBhattacharyya/vibe-director/issues/12) | Pending design/contracts |
| B5 | [#13: [B5] Implement the two modes using the shared execution service](https://github.com/SaswataBhattacharyya/vibe-director/issues/13) | Pending design/contracts |
| F1 | [#14: [F1] Define final clip assembly, sound and export before selecting tools](https://github.com/SaswataBhattacharyya/vibe-director/issues/14) | Later design |

Ashu currently has read access as checked during publication. The owner should invite `ashucodesbio` as a collaborator for the requested write/merge participation; public cloning does not require that invitation. Start with #1–#4, then #5 once its designs/contracts are accepted. Do not treat all open issues as simultaneously ready.

## Current implementation and UI ownership

The initial isolated T2V implementation is published in draft PR #15 on `issue-2-isolated-t2v-reuse`; main remains the planning baseline. Read [Ashu UI handoff](ASHU_UI_HANDOFF.md) for actual files, behavior, evidence and unfinished features. All D issues remain open. Historical planning-only publication statements above describe the initial publication, not the current draft branch.
