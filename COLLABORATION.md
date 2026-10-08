# Collaboration proposal — Vibe Director

Updated 2026-10-08. Owner: `SaswataBhattacharyya`. Public visibility is now explicitly authorized by the owner; it supersedes the earlier private preference. Collaborator account: `ashucodesbio`. Both should contribute product ideas, issues, PRs, reviews and merges. Proposed task leads below are for review, not assignments already accepted by Ashu.

## Shared source of truth

- [plans/README.md](plans/README.md) indexes current product decisions. [plans/issue_backlog.md](plans/issue_backlog.md) and linked drafts describe next work. Historical plans and source applications provide evidence, not a competing product specification.
- Use one separate Vibe Director product repository. Existing local reference sources remain outside it. The canonical local planning repository has an initial commit. The owner created `https://github.com/SaswataBhattacharyya/vibe-director`; all planning files and 14 issues are published. The backlog records issue links; Ashu's write/merge access still requires a collaborator invitation.
- Before the initial commit, review staged contents and ignore rules for credentials, private media, local state, model weights and environments. Share only the reviewed source/planning subset.

## People and decisions

- Ashu is an intellectual/product collaborator and the proposed lead for UI/design drafts. Saswata and the backend implementer propose extraction/adaptation contracts. Both review creative semantics, usability and architecture; either can contribute across these areas.
- Each issue identifies a proposer/lead, reviewer and open decisions. Record accepted material decisions with their rationale and alternatives in the plans or linked decision records.
- Do not reopen already confirmed product requirements as design questions. Flag actual contradictions or unavailable workflow capabilities explicitly.

## Work cycle

1. Use the public product remote, attach this local repository and arrange write access for the specified collaborator. G1 documents source access/setup; the remote and issue publication are complete; no collaborator invitation has been sent by this agent.
2. Publish only ready milestone issues. Use **Backlog → Ready → In progress → Review → Done**, plus Blocked for real dependencies.
3. Design issues produce reviewable layouts/prototypes, answers and API requirements. Accepted designs lead to bounded implementation issues. Implementation issues close with demonstrated behavior, not merely a design or count of passing tests.
4. Use short branches and PRs linked to issues. The other collaborator reviews before merge; either can merge after that approval. Follow this rule by agreement and enforce it in repository settings where available. Add meaningful automated checks as implementation starts.
5. Demo each milestone, record evidence and update authoritative plans/backlog. Keep costly generation supervised and bounded; mocked UI and CPU checks are distinct from real engine/UI acceptance.

## First shared milestone

G1 source access and G2 reuse/API contracts establish the working boundary. Ashu can design D1 navigation and D4 video interaction using agreed fixtures while B1 connects isolated T2V → durable progress → playback → preserved retake. Then accept the remaining screen designs and schedule their bounded UI/backend implementation. Final assembly is a later design issue, not assumed current scope.

## Immediate source-access requirement

Ashu needs the Vibe Director repository, the existing Story Builder repository `https://github.com/SaswataBhattacharyya/mooV_E_maker.git` and the public OpenMontage source. Verify Ashu can clone `mooV_E_maker`; no new reference snapshot repository/archive is required. The inspected local Story Builder folder lacks Git metadata, so record the upstream clone commit and compare selected files against that local source before reuse. Models/ComfyUI are unnecessary for design/mocked UI work; real integration needs agreed backend access or local setup. Exact file extraction, provenance, dependencies and license compatibility are captured in G2 before copying.
