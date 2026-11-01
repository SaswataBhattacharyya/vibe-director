> **Historical document — superseded for current migration direction on 7 October 2026.** The user chose to reuse and reorganize the working Story Builder app. Follow [migration_plan/00_READ_ME_FIRST.md](migration_plan/00_READ_ME_FIRST.md) for the current capability, UI, API and data plan. The original text below is retained for traceability.

# Vibe Director — decision map

Updated 2026-10-03. **Planning only; no product implementation is claimed in this repository.**

## Destination

Build a useful, trustworthy way for a creator to turn a short story idea into planned, reviewable video shots and eventually playable clips. The first release should prove one coherent journey before absorbing the many media, analysis, audio, and automation ideas in [My idea](My%20idea/).

Success for the first release is a new user completing a small story-to-shot workflow, understanding what the system generated, changing it without losing work, and producing at least one playable video clip with recorded inputs and output provenance. This is a **proposed success criterion**, subject to user validation.

## Established decisions and boundaries

| Status | Item | Source |
| --- | --- | --- |
| Decided by user | This repository is the single Vibe Director planning/working folder. The product is just starting; older implementation claims are not Vibe Director status. | 2026-10-03 conversation |
| Direction from prior notes, to validate for the first release | A story begins each production; Manual, Semi, and Full describe who decides; Direct H3, Reference-built, and Hybrid describe how visual references are prepared. These are independent concepts. | [Execution handoff](My%20idea/00_READ_ME_FIRST.md), [modes](My%20idea/02_STORY_DIRECTOR_AND_MODES.md) |
| Direction from prior notes, to validate for the first release | Generated project media has one canonical owner; shared Video Repertoire sources are linked rather than copied. The Director proposes prompt changes visibly and records selected reference intent. | [Assets](My%20idea/03_ASSETS_AUDIO_AND_STORAGE.md), [Director](My%20idea/02_STORY_DIRECTOR_AND_MODES.md) |
| Scope boundary in prior notes | Final film stitching, hosted voice cloning, and advanced untested media controls were deferred. | [Execution handoff](My%20idea/00_READ_ME_FIRST.md) |

The notes describe a separate existing Story Builder application and a large upgrade plan. They are valuable design evidence, but none of their phases, tests, or runtime results count as Vibe Director acceptance. See [historical implementation log](My%20idea/IMPLEMENTATION_LOG.md) only to learn from prior experiments and risks.

## Recommended first product slice — proposal

Focus on **one creator, one short story, one planned shot, one reviewed clip**. A creator writes a short story, reviews an editable scene/shot plan, inspects the exact prompt and any references, requests one local render, and accepts or retries the resulting clip. Preserve the story, shot revisions, render settings, output, and failure reason. A first cut can use Manual control and a Direct H3 route; other modes/routes remain design options until this path proves useful and reliable.

This smaller slice tests the essential value and the hardest media boundary without requiring a full asset library, all six style families, a global analysis system, automatic voice casting, or a multi-shot autonomous director on day one. The older phase plan remains a source of technical ideas, not an instruction to build every feature in order.

## Decisions and investigations

| Priority | Question or investigation | Decision it informs | Evidence needed |
| --- | --- | --- | --- |
| 1 | Who is the first intended creator, and what task do they struggle to finish today? | First-release workflow and success criterion | 3–5 concrete examples or short interviews; one representative story and desired output |
| 1 | Is the first deliverable a shot plan, a playable clip, or a complete short film? | MVP boundary and acceptance gate | User choice and one end-to-end walkthrough |
| 1 | Which existing Story Builder code, if any, should be reused rather than studied as reference? | Repository/architecture decision | [Read-only reuse audit](REUSE_AUDIT.md) complete; first-release scope, provenance and local capability still need decisions |
| 2 | Which local video workflow is reliable for the first shot, and what inputs does it truly accept? | Renderer contract and UI controls | Exact local graph/model inventory; one disposable decoded video **with audio**; time/GPU measurements |
| 2 | What must the user review or approve before rendering and after output? | Manual workflow and revision model | Clickable flow tested against representative cases, including a failed render |
| 2 | What minimum provenance and cleanup are needed? | Project data model and safe retry | One canonical output, stable IDs, prompt/input/model versions, restart and deletion behavior |
| Later | Should Semi/Full automation, reference-built assets, voices, styles, and Video Repertoire enter the next release? | Expansion order | Observed demand and a working first slice; separate capability proofs |

These are open questions, not implementation tickets. Terms such as `story`, `scene`, `shot`, `take`, `reference`, and `accepted` should get precise definitions when the first workflow is specified. In particular, a planned shot differs from a rendered take, and a selected reference differs from a file merely present in a library.

## Milestones and prerequisites

1. **Product brief.** Choose the first creator, primary job, first deliverable, and a representative story. Exit evidence: a one-page brief with observable success and exclusions. This unblocks a focused prototype.
2. **Workflow prototype.** Sketch or build a lightweight interaction prototype for story → shot plan → prompt/reference review → render → result review. Test it on the representative story and a failure case. Exit evidence: revised flow and explicit approval points. This informs the first-release specification.
3. **Technical spike.** Inspect candidate code and local media capabilities. Prove one exact graph yields a decoded video and audio result within an acceptable budget; record missing dependencies and failure modes. This unblocks a truthful renderer contract.
4. **First-release specification.** Define the domain records, persistence, UI states, supported input limits, and acceptance tests for the single-shot slice. Exit evidence: a buildable scope with no unresolved material behavior choices.
5. **Build and acceptance.** Implement the specified slice, then verify a fresh story-to-playback run, safe retry/restart, provenance, and user review. Expand only after this gate passes.

The product brief and workflow prototype can progress while the technical spike is investigated. The renderer contract must be proven before the UI claims a workflow is available. The first-release specification depends on both the tested user flow and the verified media capability.

## Risks and evidence gaps

- The original notes cover a broad production suite. Building all of it before testing one creator journey would make the first release hard to validate.
- The historical log reports long local renders, intermittent GPU/ComfyUI telemetry, and cleanup ownership issues. These are prior-system observations, not current Vibe Director measurements. Recheck them if reusing that stack.
- A graph or endpoint existing does not prove useful visual continuity, correct speech, or a playable result. Acceptance needs actual decoded output and human review.
- No first-user validation, Vibe Director implementation test, or current runtime capability test is recorded in this repository. A [read-only reuse audit](REUSE_AUDIT.md) of the separate Story Builder tree is available.

## Next conversation

Resolve the first two priority-one questions: **who is the first creator, and is the first promised result a reviewed shot plan, one playable clip, or a finished film?** Then write the one-page product brief and use it to narrow the prototype and technical spike.
