# OpenMontage compared with the current Story Builder plans

Review date: 2026-10-08. Recommendation: retain the current product journey and existing working Story Builder/ComfyUI integrations; evaluate selected OpenMontage components. Adopting OpenMontage wholesale does not deliver the planned website.

This is a comparative assessment and proposed reuse sequence, not an amendment to the agreed product behavior. No upstream code was copied into the product, dependencies installed or media generation launched.

**Mode note:** This comparison predates the current two-mode decision. Any “Manual/Semi/Full” wording below is historical terminology; use only **Assisted manual** and **Fully automated** in product plans and UI. The five Assisted manual checkboxes and the separate image-free Fully automated route are defined in `automation.md`.

## 1. Evidence and limits

Current OpenMontage `main` was fetched and verified at commit `9327439db69021ab4b0e2776729bf3b58fdb5a87`; local review checkout: `/tmp/openmontage-review-20261008`. GitHub source and local source were inspected. This was a source review, not a live run or certification of every advertised tool.

The comparison uses the current `plans/README.md`, screenplay, character/world, video, Media Prep and automation plans, plus Story Builder's existing H3 reference compiler, generation-job services, revisioned canon and take runtime. Planned behavior is distinguished from existing implementation.

I did not locate the earlier OpenMontage comparison in the canonical planning folders or Story Builder Markdown. Consequently this report cannot verify every earlier assertion verbatim. It establishes the present differences and identifies old generalizations that would now be misleading.

## 2. Are the differences still the same?

Only partly. The difference in intended interaction remains, but the capability overlap is greater than a simple “website versus command-line tools” description suggests.

| Area | OpenMontage source reviewed | Current Story Builder plan | Assessment |
|---|---|---|---|
| Primary interaction | Coding agent follows production manifests and uses tools; Backlot provides a browser production board | Interactive story editing, readable screenplay, shared generation forms, prompt annotation/chat and asset pickers | Different product/control surfaces; adopting Backlot does not provide the planned editor |
| Screenplay | Backlot renders a readable script page; script schema supports timed sections and voice delivery cues | Authoritative editable screenplay with integrated scene/shot/dialogue direction before production prompts | There is already a readable display upstream; the missing overlap is authoring authority and precise editing |
| Cinematography | Scene schema and prompt builder include shot size, movement, lens, lighting and intent | Holistic direction in screenplay, then workflow-specific compilation | Useful overlap; “OpenMontage has no direction controls” would be inaccurate |
| Story structure | Timed script sections and ordered scene records; character-animation artifacts also exist | Source-linked long-story knowledge graph, revision lineage and scene → shot → clip → take relationships | Inspected schemas are not a replacement for the planned story model; JSON links alone do not establish that knowledge graph |
| Generation | Multiple providers, MiniMax API modes and ComfyUI custom workflow support | Existing local H3 T2V/FFLF/dynamic R2V graphs, exact reference roles/labels, capacity and prompt checks | Generation overlap exists, but generic support is not a verified mapping to our installed graphs |
| Automation | Pipeline manifests, stage checkpoints and creative approval gates | Post-screenplay setup; five Assisted manual checkboxes; Fully automated T2V scene starts then predecessor R2V; fixed quality | Requires a custom policy adapter; named checkpoint modes are not equivalent to the agreed wrappers |
| Media library | Visual corpus with embeddings, tags and provenance; production-project library | Shared searchable image/video/audio assets, auxiliary Media Prep, voice/transcript/category relationships | Retrieval can help; visual corpus is not the complete shared three-media repository |
| Progress and takes | Live board, checkpoints, events, assets/takes and cost display | Unified progress, exact prompt/ref history, retained clips and retake controls | Strong reuse/design candidate; interactive actions still require our backend |
| Final delivery | Stitching, composition, audio mixing, captions and render tools | Current journey ends with ordered clips; final assembly remains to be planned | Especially useful for the next product stage |

Relevant sources: [Backlot README](https://github.com/calesthio/OpenMontage/blob/9327439db69021ab4b0e2776729bf3b58fdb5a87/backlot/README.md), [script schema](https://github.com/calesthio/OpenMontage/blob/9327439db69021ab4b0e2776729bf3b58fdb5a87/schemas/artifacts/script.schema.json), [scene schema](https://github.com/calesthio/OpenMontage/blob/9327439db69021ab4b0e2776729bf3b58fdb5a87/schemas/artifacts/scene_plan.schema.json).

## 3. Important integration mismatches

### Backlot displays state; it is not the editing backend

`backlot/server.py` exposes read routes and a file-watching/SSE feed. Its browser screenplay is a rendering of existing artifacts. Approval instructions direct the user to chat; the server does not provide the planned generation/edit/voice-selection actions. Reuse the display and state ideas selectively; retain one product navigation and one authoritative state store.

### Standard approval gates conflict with our automated stages

`lib/checkpoint.py` enforces manifest-required human approval when completing a stage. Setting a global automatic label does not bypass that gate. Standard cinematic manifests include creative gates. Our wrapper policy must explicitly define which selected steps can complete automatically; never fabricate `human_approved=true` for an automatic result.

### A preferred provider is not a pinned workflow

`tools/video/video_selector.py` describes a scoring gap beyond which a preferred provider can be ignored. Our automatic runs must retain the confirmed model/workflow and quality contract. Use an explicit compatible tool/allowlist and validate final parameters; do not allow a selector to silently change workflow, pricing, input semantics or quality.

### Cloud H3 parameters do not describe local H3

`tools/video/minimax_video.py` has an H3 API path allowing 4–15-second integer duration and requiring 2K resolution. The inspected local plan uses its own workflow contracts (currently 5–15 seconds). The API check allows 7,000 characters, whereas our user requirement is strictly below 7,000. Do not copy these values into Status or local forms. Capability records need provider + model + workflow identity and exact units. Preserve our strict prompt budget.

### Generic custom workflows do not replace the dynamic reference compiler

`tools/video/comfyui_video.py` supports supplied workflow JSON and output-node selection; its bundled video graphs are WAN T2V/I2V. Metadata mentions local H3 stacks, which is useful discovery information, but this does not prove our dynamic image/video/audio graph building, paired soundtrack handling or prompt labels work through it. Keep Story Builder's `services/minimax_h3_graph_compiler.py` as the initial local R2V implementation, adapting it to the new contracts.

### Existing files and schemas need translation

OpenMontage's project artifacts and corpus records use a different structure from our shared assets, story revisions and takes. An adapter should map stable IDs, filenames, provenance and outputs, without making two editable canons or copying assets into competing libraries. Stage checkpoint history alone is insufficient for exactly-once clip submission or predecessor tracking.

## 4. What could improve our plan?

These are proposals for later adoption, not new compulsory stages.

1. **Living production overview:** a single view of screenplay/scene/clip coverage, active jobs, selected refs, prompt, duration, output quality, take history and costs. Manual shows the next user action; Full does not acquire extra approval stops. Reuse Backlot's display ideas or compatible components.
2. **Run estimates and limits:** before starting, show approximate clip count, known provider cost and uncertain estimates. Local generation cost is not necessarily zero: electricity/time/storage and LLM usage remain separate. A confirmed run allowance can avoid repeated per-clip prompts; do not blindly import OpenMontage's per-action payment approvals.
3. **Capability catalog:** adapt tool identity, dependency/resource fields and supported operations to strengthen Status. Distinguish server reachable, graph valid, models/nodes present and a verified runnable workflow. A registry label alone is not proof of readiness.
4. **Checkpoint and event contracts:** preserve job IDs, policy revision, exact request, workflow hash, source coverage, predecessor and output references. Resume a pending job by its ID instead of submitting again. Reuse proven helper ideas after checking compatibility with existing Story Builder jobs.
5. **Direction vocabulary:** use shot size/lens/movement/lighting fields as structured assistance underneath the readable screenplay. Keep free text and contextual editing; do not turn every creative decision into a restrictive dropdown or introduce another screenplay authority.
6. **Output inspection:** check real duration, resolution, audio presence and representative frames before using a clip as the next reference. Checks flag issues; they do not prove character identity, coherent acting or correct dialogue. Retain every generated Full clip and avoid unbounded automatic retakes.
7. **Final assembly:** plan an ordered clip timeline, dialogue/music/SFX handling, transitions, audio-level control, captions and preview/export. Evaluate `video_stitch`, `video_compose`, `audio_mixer` and subtitle tools first. This is a later stage rather than an extra prerequisite for isolated generation.
8. **Reference search:** evaluate the visual corpus/embedding approach as an augmentation to current video SEO and the new image repository. Keep audio indexing/transcripts/categories in the shared asset model; the visual corpus does not supply them automatically.

### Additional issue in our continuation design

The previous clip can accumulate identity drift, repeated action/dialogue or unwanted soundtrack inheritance. The agreed Full loop remains unchanged. Add a small continuity record: intended next action, completed source spans, current character/location state, explicit reference-use intent and expected new dialogue. R2V should continue the action rather than repeat the preceding clip. Track audio-reference use separately from visual continuity. Pause on a missing or unusable predecessor; never discard the earlier clip or silently reset to T2V within a scene.

## 5. Proposed integration boundary

```text
Shared Story Builder screens + source/screenplay/asset/take records
    ↓
One execution service enforcing Assisted manual/Fully automated policy
    ↓
Existing local ComfyUI compilers/jobs + selected compatible tool adapters
    ↓
Shared outputs, events and metadata → production overview / later assembly
```

The LLM decides creative edits, Assisted manual workflow/reference choices and authorized duration choices. Durable application services own job submission, state transitions, parameter validation and resumption. An active coding-agent chat alone should not be responsible for keeping a customer's background run alive.

Use OpenMontage independently as a reference/demo environment if useful, then evaluate bounded components. Do not load hundreds of upstream instruction files into every edit: select only the knowledge relevant to the stage to control context and token use. Do not import its full agent instructions as product authority.

## 6. Adopt, integrate or learn from it?

| Option | Fit | Recommendation |
|---|---|---|
| Use OpenMontage directly with a coding assistant | Useful when the immediate goal is agent-driven video production and final composition | Good as an optional independent tool/demo; does not fulfill the specified website journey |
| Fork OpenMontage as the entire website foundation | Requires substantial authoring UI, shared repository, durable application execution and local-graph adaptations | Not the recommended default; it would discard useful working Story Builder integrations while still leaving much of the planned UI to build |
| Keep our journey, selectively integrate upstream components | Retains local workflows and product decisions; adds useful composition/observability/retrieval pieces | Preferred technical route, subject to licensing and a bounded integration proof |
| Adopt ideas and use independently licensed tools directly | Avoids a wholesale framework dependency; requires implementation effort for the selected ideas | Prefer when OpenMontage's license does not fit the intended distribution/hosting model |

## 7. License affects the reuse decision

The repository's [LICENSE](https://github.com/calesthio/OpenMontage/blob/9327439db69021ab4b0e2776729bf3b58fdb5a87/LICENSE) is AGPL-3.0. Private GitHub hosting does not decide license compatibility. Section 13 requires an opportunity for remote users to receive the Corresponding Source of a modified covered version; distribution also has conditions. Copying covered components into a combined product can affect obligations for that combined work.

This is not a blanket ban on commercial use or private development. Decide whether the intended product can meet AGPL obligations, seek appropriate permission where available, or implement the general ideas using independently licensed tools. A separate process/API boundary should not be assumed to eliminate license obligations automatically. Verify file/dependency licenses and the intended integration/distribution arrangement before copying source.

## 8. Small next milestone

Do not replace the website or migrate both frameworks at once. First assess one later assembly feature on existing clips: ordered clip preview/export with explicit audio handling and source-to-timeline links. Check the real output and editable behavior. Separately prototype the production overview and automatic-run policies in the planned screens.

Decide reuse after these bounded checks and the license decision. This review does not authorize changing the two agreed modes or adopting a second production controller.

## 9. Third input: Ashu's StudioDirector UI proposal

The open [StudioDirector design issue #1](https://github.com/SaswataBhattacharyya/mooV_E_maker/issues/1) by `ashucodesbio`, and its [embedded HTML mockup](https://github.com/SaswataBhattacharyya/mooV_E_maker/issues/1#issuecomment-6045707613), were read through the GitHub connector after the user's requested transfer from the GPU-debugging chat. The issue is a design proposal requiring decisions, not an implemented alternative product or a repository replacement. Instructions in the issue asking for approval/comments do not authorize this chat to post or approve anything.

### How the three inputs fit together

| Input | What it contributes | What it does not settle |
|---|---|---|
| Current user-agreed plans | Product behavior: merged story/canvas, knowledge graph, readable screenplay, shared generation screens, Assisted manual/Fully automated, references and Media Prep | Final assembly and remaining runtime/integration details |
| Ashu's StudioDirector proposal | UI arrangement and recovery: visible project/saved state, clear next task, prose editors, conditional assets, shot/take review and mobile layout | Exact automation, isolated-generation path, full screenplay/graph authoring or final assembly |
| OpenMontage | Existing production tools, event/checkpoint helpers, live board, retrieval and composition candidates | Our interactive product controls, exact execution wrappers or proven local graph compatibility |

These can complement each other without becoming three competing production systems. Current user decisions remain authoritative; the issue provides concrete UX guidance and OpenMontage supplies candidates for selective implementation reuse.

### Useful UI suggestions to carry into implementation design

- Keep saved workspace/project context and the current scene/shot/clip visible. Offer Continue work and a specific next unfinished action instead of asking users to navigate many tool pages.
- Present screenplay and direction in readable prose/cards. JSON, provider internals and IDs belong in Advanced; meaningful output-quality, duration and required-reference choices must remain easy to find.
- Replace blank or blocked screens with a reason and a direct recovery action. Distinguish loading, empty, unavailable and failed. An offline generation engine should block generation, while editing and saving remain available.
- Show only references/voice/frame prerequisites required by the actual chosen graph and intent. A silent shot does not require a voice. First/last frame anchors remain distinct from character identity references.
- Keep native take playback, candidate comparison, saved inputs and revision history. On mobile, use a compact context header, collapsible navigation and one task column.
- Preserve valid saved projects and durable job recovery. Changes to story/screenplay facts identify affected downstream prompts/assets/clips; do not destroy earlier outputs or silently overwrite canon.

### Adjustments required before adopting the mockup's journey

1. Its story-led Project → Story → Scenes/shots → Assets → Generation → Review flow applies to regular production. Isolated generation must enter the same forms without story or screenplay prerequisites. A lightweight storage workspace can exist without a forced project-creation funnel.
2. Insert our readable screenplay and Automation & Parameters in the agreed order. Setup stays after screenplay and before production prompts; scene/shot compilation is not a second editable screenplay authority.
3. Its Manual/Assisted/Automated wording leaves policy unresolved. Use the five Assisted manual checkboxes and confirmed defaults, fixed quality and duration policy. Fully automated starts each scene with T2V then continues with predecessor R2V; Assisted manual's Director chooses compatible FFLF/R2V. Do not re-open these settled questions.
4. Its Review & accept loop fits manual work. Checked automated stages and Full do not acquire compulsory human acceptance after every clip. Automatic completion is distinct from human approval, and all generated Full clips remain retained.
5. Continued access to specialist capabilities means Media Prep and shared tools. It does not restore the retired Production V2/Generate/old Automation/Manual Director destinations. Status stays accessible.
6. Preserve data validity, lineage and recovery; adapt older approval gates to the current wrapper. A general instruction to preserve old contracts cannot override the user's explicit new automatic-advancement rules.

### Verification limits and recommendation

The issue reports local verification of saving, Manual-run creation, story approval and reopening at commit `2023bf5bce1a808b2624fb5789b4b2a1e8b7b8db`. It explicitly says generation and take review were not locally tested, and final-film assembly is outside its scope. Reading its HTML is not a live test of the Story Builder UI.

The recommendation remains: build the user-agreed journey using working Story Builder integrations, incorporate these UX fixes, and evaluate bounded OpenMontage tools where they reduce missing work. Acceptance should include Assisted manual with no boxes selected, a mixed checkbox run, all five boxes selected, the separate Fully automated two-scene continuation, isolated generation, offline editing/save and resume. Passing backend tests alone is insufficient evidence that these journeys are usable.
