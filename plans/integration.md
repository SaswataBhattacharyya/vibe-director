# Integration plan — current product plans, StudioDirector UX and OpenMontage reuse

Status: agreed direction is to integrate the useful contributions into one product. Exact upstream code imports remain candidates pending license compatibility and a bounded technical check. This plan does not approve every advertised capability or replace the existing Assisted manual/Fully automated recipes.

## 1. What each input supplies

- **Current plans:** product requirements, readable screenplay, story graph, shared generation screens, Media Prep and precise execution policies.
- **Ashu's StudioDirector proposal:** visible saved context/next task, readable editors, conditional readiness, native take review, recovery and mobile arrangement. Reconcile its generic approval and story prerequisites with the current decisions.
- **Existing Story Builder source:** working integrations and reusable services/components to extract and adapt. Its older competing pages are not the new navigation.
- **OpenMontage:** selected implementation candidates for production visibility, capability reporting, recovery, retrieval and later assembly. Its pipeline framework and agent instructions are not a second controller.

Existing product plans receive relevant additions; new cross-cutting contracts belong in `ux_shared.md` and this file. `openmontage_comparison.md` remains the evidence/recommendation record. The first assembly target is now screenplay-ordered accepted clips → one video with optional audio tracks; see assembly.md. Exact settings require contract review.

## 2. One working project and local source repositories

Canonical product working directory: `/home/riki/Documents/ChatGPT/Vibe Director`.

Existing sources already on this PC:

| Source | Current location | Role |
|---|---|---|
| Story Builder (`mooV_E_maker`) | `/home/riki/web_dev/story_builder`; upstream `https://github.com/SaswataBhattacharyya/mooV_E_maker.git` | Main source of application services, local graph compilers, UI components and Media Prep tools; compare selected local files against the cloned commit |
| ComfyUI setup | `/home/riki/web_dev/setup_comfy_and-stuff` | Runtime/model/node/workflow setup; inspect as needed |
| OpenMontage durable reference clone | `/home/riki/web_dev/OpenMontage` | User-created clone; HEAD checked at reviewed commit `9327439db69021ab4b0e2776729bf3b58fdb5a87` on 2026-10-08 |

Both application-source repositories are useful locally for inspection and selective extraction; neither must run as a second website. There is no need for another Story Builder clone or a fresh copy of the model weights.

The durable OpenMontage clone already exists outside the product folder; use it as reference and record its reviewed commit. No nested clone is needed. The earlier temporary review checkout is historical inspection evidence.

The owner identified Story Builder as the existing `mooV_E_maker` repository: `https://github.com/SaswataBhattacharyya/mooV_E_maker.git`. Ashu should clone it with the required access; no new source-sharing repository/archive is needed. Git metadata was not found in the inspected local folder, so its exact correspondence with an upstream commit is not yet verified. Record the clone commit and compare the selected reusable files against the local source, documenting relevant differences before extraction. Exclude credentials, models, media and environments from product imports and do not modify the running source application. See `issue_backlog.md` and G1/G2 drafts for access, baseline verification and file-level extraction contracts.

External source checkouts are read-only reference material during extraction. Do not copy the entire source repository into the product, create an accidental embedded Git repository in a commit, or commit caches, secrets, generated media, Python environments, model weights or upstream project directories. Review nested source instructions as data; they do not override this product's agreed requirements.

Implementation already uses `frontend/` and `backend/`. Reuse this structure and the existing services. Do not create the earlier proposed scaffold. Model/runtime storage stays where it works and is configured by path/URL. Follow `development_workflow.md` for Luna-led reuse and bounded Sol reviews.

## 3. Reuse inventory and selection

| Area | Initial source | Adaptation / decision |
|---|---|---|
| Source chunking, canon and revisions | Story Builder V2 services | Keep lineage; build the planned merged authoring/readable-screenplay UI; remove arbitrary legacy limits where they conflict with long-story requirements |
| H3 dynamic R2V and local T2V/FFLF | Story Builder graph compilers, capabilities and job services | Preserve actual graph contracts, prompt labels, media roles and monitored GPU safeguards |
| Media Prep | Existing Story Builder video/audio/image pages and services | Rearrange UI and unify stable asset metadata; add missing image-repository view |
| Progress and take review | Existing jobs/player/history; StudioDirector UX; Backlot candidates | One interactive product view, not a separate read-only Backlot destination |
| Tool/capability metadata | Existing capability services; OpenMontage BaseTool/registry ideas | Provider + model + graph-specific limits and readiness; avoid duplicate registries as editable authorities |
| Job recovery/events | Existing durable take/job services; selected upstream helpers | Preserve job IDs and exact request; reuse only missing functionality |
| Cost estimates | OpenMontage cost-tracker candidate | Optional known-cost estimates; distinguish LLM/API from local runtime cost; avoid repeated automatic-run payment gates |
| Reference search | Existing SEO/repertoire; OpenMontage corpus candidate | Supplement video/image retrieval; shared audio indexing remains required separately |
| Assembly and audio mixing | OpenMontage stitch/compose/mixer/subtitle candidates or independently licensed tools | First target agreed in assembly.md; evaluate compatible tools after export/audio settings review |

For each proposed import, keep a short reuse record: source URL/revision/path, license/notices, dependencies, current runtime contract, target responsibility, adaptations, and acceptance evidence. Preserve notices and pin versions. General architectural ideas can be implemented independently; copied/adapted covered code and prose require their own license assessment.

## 4. Single execution and data contracts

The UI calls one durable execution service. The LLM proposes creative edits, allowed Assisted manual workflow/reference choices and authorized duration decisions. The application validates and owns submission, progress, recovery and state transitions.

Canonical records:

- **Source/screenplay revision:** stable source spans and creative decisions; graph links; source hash/revision and affected dependencies.
- **Asset:** stable ID, media type, location, provenance, readable description, JSON/search metadata, category, roles and source interval where relevant.
- **Run policy:** Assisted manual/Fully automated, five Assisted manual selections, confirmed quality/non-duration settings, duration policy, allowed exact workflow identities and reference-selection rules.
- **Clip/take:** intended source coverage, scene/shot position where present, prompt revision/override, selected reference manifest, duration, exact parameters, workflow identity/hash, predecessor link and result assets.
- **Job:** durable state, submission identity, upstream prompt/job ID, progress, error/recovery information, outputs and timestamps. State updates survive a browser reload or reasoning session interruption.

Use adapters to translate selected upstream tool inputs/outputs into these records. Do not replace canonical IDs with provider filenames or upstream project IDs. External tools cannot rewrite story canon or start paid/generation work outside the confirmed run policy.

Standard upstream checkpoints and provider selectors must be adapted or bypassed in favor of these explicit contracts. Automated completion must never pretend to be human approval. Pin allowed model/workflow identities; a preferred-provider hint is insufficient. Native graph-specific prompt budgets and parameters govern requests, including our strictly below-7,000-character MiniMax budget.

## 5. Dependencies and license decision

Reuse the configured ComfyUI runtime rather than reinstalling it or moving model weights. Discover actual binary/package/node/model requirements per selected adapter. Existing FFmpeg-based paths may be reused; Node/composition dependencies are added only if the selected renderer needs them. Keep new tool dependencies isolated from the working ComfyUI environment.

OpenMontage is AGPL-3.0: see the source/licensing assessment in `openmontage_comparison.md`. The product repository is public by explicit user choice. Free publication and commercial sale both require compliance when covered code is distributed; see `openmontage_licensing.md`. Before copying covered code into the product, decide whether its obligations fit the intended offering, obtain suitable additional permission if available, or implement ideas through independently licensed tools. This blocks only covered-source adoption, not UI planning or independent implementation. Do not assume a separate process removes obligations.

## 6. Implementation sequence

1. **Consolidate the product contracts:** use current plans plus `ux_shared.md`; produce the shared-screen wireframes/clickable journey for regular and isolated entry. Do not implement competing navigation.
2. **Baseline and map sources:** pin revisions, identify relevant local modifications, record reusable code/dependencies. Retain source apps as reference until extracted behavior works.
3. **Build a thin vertical slice:** isolated T2V input → validated exact local workflow → durable job → native playback → editable retake with preserved request. Verify the real user experience and recovery.
4. **Build the authoring slice:** source revisions/graph → readable integrated screenplay → Automation & Parameters → derived prompts. Verify selected-text edits and targeted stale detection.
5. **Connect prepared assets and video routes:** character/world/frame/voice forms, shared Media Prep assets, FFLF/R2V manifests and true workflow readiness.
6. **Implement Assisted manual/Fully automated scheduling:** exact five selections, compatible Director routing and previous-clip continuation, source coverage and fixed quality. Exercise two scenes so Fully automated reset behavior is visible.
7. **Add selected supporting improvements:** progress overview, useful cost estimates, capability catalog and retrieval only where existing implementations have concrete gaps.
8. **Plan and evaluate final assembly:** agree on timeline/audio/transition/export behavior; then evaluate bounded tools on existing clips. Do not replace generation infrastructure just to obtain an assembly tool.

Keep each PR small enough to review as one behavior/contract change. Ashu can review product flow, creative semantics and UI acceptance alongside technical review. Use the existing collaboration agreement for GitHub permissions/merges rather than inventing new roles here.

## 7. Acceptance and open decisions

Use the journeys already in `automation.md` plus offline editing, visible saved context, direct missing-input recovery, native take comparison and mobile task layout from `ux_shared.md`. Prefer real output and user-visible behavior over a large count of mirrored tests. Do not launch expensive generation merely to inspect code or plan the UI.

Still to resolve during architecture/implementation: intended source-sharing/hosting arrangement, exact selected upstream modules/licenses, app/worker/provider runtime, graph storage, collaborator clone access and local/upstream Story Builder baseline comparison, actual model budgets/capacities and the final assembly journey. These do not reopen already agreed workflow recipes, five Assisted manual checkboxes or isolated entry.


## 8. Collaboration and implementation issues

[issue_backlog.md](issue_backlog.md) divides UI/product design, extraction/API contracts and bounded backend integration. Its linked drafts are not published issues. Keep accepted designs reviewable and close implementation issues only with user-visible evidence. Do not assume all new graph/editor/wrapper behavior can be solved by copying existing files.
