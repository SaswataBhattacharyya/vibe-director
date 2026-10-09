# Shared creation and video UX proposal

Design review for [#3](https://github.com/SaswataBhattacharyya/vibe-director/issues/3) and [#4](https://github.com/SaswataBhattacharyya/vibe-director/issues/4). Start from the `issue-2-isolated-t2v-reuse` branch / draft PR #15. This PR carries a standalone [clickable prototype](prototypes/vibe-director-flow-proposal.html), its Nunito font, and proposed design decisions. It does not alter the production frontend or backend.

Open the HTML locally in a browser. The prototype uses browser storage for its sample draft, simulated takes, and palette choice. No API, model, worker, or payment is connected. A local HTTP server is helpful for the bundled font; for example, serve the repository root and open `/design/prototypes/vibe-director-flow-proposal.html`.

## Proposed route map for #3

| Destination | Entry/context | Saved state and exit |
| --- | --- | --- |
| Home | Named workspace; choose Develop a story or Create directly | Resume link points to unresolved take or video draft. A real app needs a project/task switcher and per-task draft keys. |
| Story → Screenplay | Story identity, source revision, scene/shot/clip | Creative source stays authoritative. The prototype uses a sample; editing and graph links need the later authoring contract. |
| Setup → Prompts → optional Preparation | Story-linked path only | Manual/Semi/Full choices and stage selection are shown. Actual automation and model defaults must come from verified capabilities. |
| Video Create | Shared screen reached from story or directly | Story context is optional. T2V draft/settings persist; FFLF/R2V sample selections persist. Only T2V has a simulated job path. |
| Video Current take | Submitted request/job identity | Full request, status, acceptance, history, retake and lost-reply recovery are demonstrated for T2V. A completed job is not automatically accepted. |
| Media Prep & library; Status | Global auxiliary areas | Status shows capability availability. Media Prep remains a proposed destination. |

The desktop sidebar and horizontal stage rail use the same route names and active state. The mobile menu exposes the same destinations. The story path and direct path converge on the Video screen; there is no second Generate page or required fake story for direct work.

**Production state needed:** workspace/task list and active ID; optional story/source revision/scene/shot/clip IDs; per-task draft and dirty/saved status; next unfinished action; stale dependent work; durable job IDs and recovery lookup. Switching context must not carry one task's draft into another. Linking an isolated asset to a story should preserve its original task and add an explicit source link, rather than silently recasting its provenance. Loading, empty, offline, failure, running and completion states need the same shell and context controls.

## Proposed video workspace for #4

| Mode | Form and review | Current evidence |
| --- | --- | --- |
| T2V | Prompt, actual 5–10 second duration choices, two supported quality presets, readiness by Generate, explicit submission, full frozen request, progress/recovery, accept/retake. | Based on PR #15's provisional UI/API. Prototype simulates jobs. |
| FFLF | First and last clip-frame selectors, prompt, local image input area and request preview. Character/world images are excluded from the endpoint selectors. | Interaction proposal only; workflow adapter, media upload and result path remain unimplemented. |
| R2V | Search/category/sort sample media, multiple selections, numbered reference legend, per-reference direction, combined request and character budget. | Interaction proposal only. Labels in the preview are human-facing placeholders, not verified MiniMax graph tags. Actual limits, collation, clarification and result path need contracts. |

The form puts the required inputs and exact blocker beside the action. A selected reference must retain stable asset ID, order, type, source, role and user intent. The production compiler should generate model-specific labels and return the exact collated prompt plus a label-to-asset manifest. Reordering/removing a reference invalidates prompt validation and updates both legend and compiled request together. A model or human clarification is needed for conflicting directions before submission. The final prompt must be strictly below 7,000 Unicode code points **including labels**; do not truncate silently. Capability data, not guessed UI constants, supplies reference counts, units, duration, quality and workflow version.

The local image input in the prototype acknowledges a chosen, pasted or dropped image but does not upload it or pretend it persists. Production must store it in the managed library and return an eligible asset record before it can enter the request. The sample FFLF/R2V forms deliberately disable Generate. They cannot claim completed jobs or demonstrate real playback/retake until their adapters exist.

For every mode, the result should show native playable output, candidate status, full submitted prompt, workflow/version, parameters, source revision or take-only override, frame roles or all reference labels/intents, and prior takes. Retake asks **Keep this clip?**, returns all inputs to an editable draft, and does not submit another job. Discard affects only the chosen output; request metadata and shared assets remain. Full automation retains every clip, as specified in `plans/automation.md`.

## Existing T2V behavior to preserve

- An offline engine still permits editing and saving; submission requires exact capability, GPU and worker readiness.
- Generate is an explicit action. Reload, recovery, returning to edit, and retake never create a job.
- A submitted request is immutable. An uncertain reply reconciles by the saved request key before another submission is allowed.
- Completion and human acceptance are separate. Failed jobs preserve the draft, request and earlier take history.
- Production duration, quality, workflow, prompt budget and reference rules come from the versioned backend contract. Advanced exposes IDs and provider details without crowding the main form.

## Design review walkthrough

1. Open Home, choose each entry, and follow the route to Video. Check the context and active navigation at desktop and phone widths.
2. In T2V, try an empty or over-budget prompt, offline engine, simulated running/failed/completed job, acceptance, retake, and reload recovery. Confirm attempt count changes only after explicit Generate.
3. In FFLF, inspect the two role-specific selectors and try local image input. In R2V, select multiple media, enter a direction for each, inspect labels and the combined request, filter/search, then reload.
4. Review the three palette choices. **Quiet comic** is the current prototype default; **Concrete & ink** and **Midnight mixtape** are alternatives for discussion. Typography uses bundled Nunito Bold 700.

These are local UI checks. Real rendering, playable media, backend restart durability, assistive technology validation, representative user testing, exact FFLF/R2V graph limits, and finished automation are outside this PR.

## Questions for design review

1. Is the shared route grouping and optional story context right? What task/project switch and isolated-asset linking contract can the backend provide?
2. Which versioned capability response will supply each mode's actual limits, frame eligibility, model tags and readiness blockers?
3. Where should prompt collation/clarification and precise passage annotations live, and what response should the UI persist as the approved final request?
4. Can the existing job/take contract extend to FFLF/R2V with a reference manifest and output-only discard, while keeping the saved-key recovery invariant?
5. Which of the three palette studies should guide the production design system? The current prototype uses a dark, rounded, restrained comic direction with Nunito Bold 700; the other palettes are review options.

## Bounded follow-ups after design acceptance

1. Implement shared route/context shell and per-task draft/resume state on top of PR #15, keeping direct T2V usable.
2. Redesign the production T2V form, readiness and take review; verify mocked offline, reload, failed, accepted and retake journeys.
3. Add verified FFLF media eligibility/upload and R2V manifest/collation in separate contract-backed increments, then integrate their result and retake views.

Issues #3 and #4 should remain open until the design direction is agreed and the production work is verified. This PR is a design proposal, not a claim that every production feature is implemented.
