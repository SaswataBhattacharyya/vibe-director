# Video generation planning for Story Builder

**Status:** Current product and workflow plan. Use `README.md`, `GLOSSARY.md` and `automation.md` for authoritative decisions, terminology and wrapper behavior.  
**Position in the journey:** Follows the usable screenplay/clip plan. Visual preparation in `char_world.md` is optional and skippable; Full skips image generation. Selected clip frames, character/world references and assets from the shared library feed compatible workflows when chosen.

## 1. Goal

Give the Director one clear video-generation entry point with three explicit modes. The selected mode chooses the compatible ComfyUI workflow in the backend, opens the matching input page, and carries the resulting clip, complete prompt, and reference lineage into review.

The three modes are:

1. **Text to video** — prompt only.
2. **First frame + last frame** — two clip-frame anchors and a prompt.
3. **Reference to video** — a dynamic set of image, video, and audio references with per-reference direction and one collated text prompt.

These are distinct backend workflow contracts. Do not combine their inputs into one generic form or let a mode submit to another mode's workflow.

## 2. Journey and page structure

```text
Choose video mode
  → mode-specific prompt and asset preparation
  → generate in the matching ComfyUI workflow
  → review clip, prompt, references, and generation status
     → Next / accept
     → Retake / revise and regenerate
```

### Page A — Choose a workflow

Show three cards with a short explanation, example use, and required inputs:

- **Text to video:** describe the complete motion/shot in a prompt.
- **First + last frame:** animate between the opening and ending frames for one planned clip.
- **Reference to video:** guide generation with a combination of visual, motion, and audio references.

Selecting a card records the mode and resolves its configured, versioned backend workflow. The next page presents only fields supported by that workflow. Before generation, show the chosen mode and workflow capability status; if unavailable, explain what is missing and do not submit to a fallback workflow silently.

### Page B — Mode-specific preparation

All three mode pages share a prompt editor, duration/output controls, prompt history, save state, generation status and a clear way back to choose another mode. Story-linked work also shows project/scene/shot/clip context; those source selectors are optional for isolated work. Save drafts automatically and preserve them when navigating away.

#### A. Text to video

- Provide one large editable prompt field, informed by the selected scene/shot in the approved screenplay.
- Show the exact prompt that will be sent. Let the user edit it directly.
- Support precise annotation: select a word, phrase, or passage, then enter a requested change in a contextual chat box. The assistant edits the selected section in context; show the proposed before/after prompt and accept it before applying. Keep unrelated prompt material, scene facts, and prior prompt versions intact.
- Provide a **Generate video** button and progress state (queued, preparing, running, saving, complete, failed/cancelled). The progress view should reflect the actual ComfyUI task state and allow the user to leave and return without losing it.
- On completion, open the shared result/review page.

#### B. First frame + last frame

- Provide two distinct image slots: **First frame** and **Last frame**.
- Populate the first-frame picker with available clip first-frame assets only; populate the last-frame picker with clip last-frame assets only. Show scene number/title, shot and clip number, and frame role on each thumbnail. Prefer matching anchors for the current clip and group other frame assets by scene/shot. Exclude character reference images and world/background-only images from these default frame lists.
- Allow either slot to use a local file through file picker, drag-and-drop, or clipboard image paste. Show a preview and role assignment before generation; replacing an image should not silently swap the other slot.
- Provide one editable prompt field for the transition/action. Support the same precise selection-and-chat annotation flow as text-to-video, including a reviewable before/after proposal.
- Validate that each chosen asset is usable by the selected workflow, and make clear if a local upload is replacing a screenplay-linked frame.
- Provide **Generate video** and the same progress states. On completion, open the shared result/review page.

#### C. Reference to video

This mode uses the dynamic MiniMax H3 reference-to-video workflow. The form lets the Director combine reference assets within the model/workflow limits, explains the asset count as items are added, and prevents submission when a limit or compatibility rule is exceeded.

##### Add and find references

Provide an **Add reference** action with three types: image, video, audio. Each type can be added more than once, subject to limits. Support local file picker, drag-and-drop, and clipboard paste for compatible files.

- **Images:** browse generated or imported images in the shared Image Repository, including character, world/background and frame images. No previous image-generation stage is required. Show thumbnails, asset names, scene/character links, and approval status. Also support local image uploads.
- **Videos:** search the Video Repertoire using the existing Media Composer SEO-based clip search pattern shown in the reference screenshot. Search should find clips by their SEO metadata/content. Sort newest-to-oldest or oldest-to-newest with a reversible up/down arrow control. Also support local video uploads.
- **Audio:** use a corresponding SEO-based search and reversible recent/old sorting. Provide type filters for **voice only**, **SFX**, **music**, and **dialogue**, plus search. Also support local audio uploads.
- For every picked or uploaded item, show a thumbnail/player, filename/title, source, type, and the assigned reference number/tag. Allow removal/reordering before collation. Do not add the same asset twice to one request; flag a duplicate and let the user keep one occurrence or choose a different asset.

##### Explain each reference

Each selected reference gets its own context area with:

- A short **How should the model use this reference?** instruction field.
- Optional role/category selector appropriate to the media (for example: character appearance, wardrobe, location/style, motion/action, camera movement, voice identity, dialogue, music, SFX, or soundtrack).
- For character-related references, a character selector using canonical screenplay character names/IDs, plus plain-language context such as “This is Mira's face reference; keep her identity but use the jacket described in the scene.”
- For video/audio, specific guidance about whether to use the visual content, motion, camera, timing/rhythm, dialogue, sound effects, or soundtrack. If a video soundtrack is separately selected as an audio reference, make that relationship visible and explain the resulting separate audio reference label.

These per-reference instructions are drafting context for prompt assembly. They are not additional MiniMax prompt fields: MiniMax receives the final collated prompt and the referenced media inputs.

##### Main prompt, annotation, and collation

- Provide a main prompt field describing the intended new clip and its relation to the selected screenplay scene/shot.
- Allow direct editing and precise selected-text annotation through a contextual chat box, matching the other generation pages.
- **Collate prompt** combines the main prompt, screenplay/shot context, and each reference's instruction into one coherent proposed prompt. The collator must use the exact selected assets, preserve user intent, and not invent or silently change what a reference depicts.
- The collator may ask a clarifying question when the reference directions conflict or do not explain an important role. Keep this as a small chat panel so the user can answer and request further revisions.
- Show an editable final prompt and a numbered reference legend beside it before generation. The Director must be able to see which prompt phrase maps to which image/video/audio asset. Re-collation updates the proposal; it must not erase manual edits without showing the difference.
- Validate tags against the actual final reference list. Every selected item intended for use must have one matching reference tag, and every tag must resolve to one selected asset. Warn about unused selected assets and missing/unknown tags; block generation when mapping is invalid.

##### MiniMax label syntax and limits

The local Story Builder H3 reference compiler and its installed workflow guidance use **`<Picture 1>`, `<Video 1>`, and `<Audio 1>`** prompt labels (not `<Image 1>`). Number each media type independently, in the same order as its selected/connected assets; e.g., the second image can be `<Picture 2>` even if it is the first audio reference. The UI/compiler assigns these labels and displays the asset-to-label mapping; users should not have to number tags by hand. A prompt mentioning an item must use its exact generated label.

This is the syntax of the currently installed Story Builder H3 compiler/workflow contract. MiniMax's public API guide describes reference input roles and limits but does not document those literal textual labels in the guide reviewed. Keep the syntax versioned with the workflow and verify it again if the model or ComfyUI graph changes.

Enforce a final MiniMax prompt length strictly below 7,000 characters as the chosen product rule, across all three modes; count the exact submitted prompt including compiled labels and adapter-added text. Preserve important direction during shortening; no silent truncation. The local compiler currently verifies up to 9 images, 3 videos and 3 standalone audio references, plus per-video excerpt and role constraints. Public MiniMax API documentation also lists a 12-file combined cap and per-type aggregate reference-duration limits; verify those against the installed local graph/model and record them in its capability definition before claiming they are locally established. Apply the selected workflow’s verified file-size, format, duration and capacity rules, including how paired video soundtracks count. Read limits from versioned capability configuration and show remaining counts and actionable explanations.

Do not mix first/last-frame inputs into the reference-to-video graph; that is the separate first/last-frame mode. If a reference clip includes audio and its soundtrack should be used, represent that as an explicit audio reference only when the workflow supports/extracts it, label it separately, and show the user how the relationship is encoded.

## 3. Generation and progress

- Submit to ComfyUI through the workflow selected on Page A; attach the project, scene/shot IDs, prompt revision, reference manifest, and workflow version to the task.
- Show queued/preparing/running/saving/completed/failed states, task progress where available, and a useful failure reason with retry guidance.
- Keep the page usable while generation runs; returning to the task restores its progress and all input state.
- Prevent duplicate submissions caused by repeated clicks. A retry after failure should retain all inputs and create a traceable attempt.
- Do not mark a clip approved merely because generation succeeded. The clip is a candidate until the Director reviews and accepts it.

## 4. Page C — Result review, next, and retake

After generation, show:

- The playable generated video clip and its candidate status.
- The complete final text prompt.
- The chosen workflow/mode and version.
- For first/last-frame mode, both frame previews and their scene/shot/clip/frame roles.
- For reference-to-video mode, every image/video/audio item with its generated reference label, source, role, and the user's per-reference instruction; include the exact collated prompt.
- Generation parameters and a link back to the originating scene/shot and prompt revision.

Actions:

- **Next / Accept:** approve the candidate and continue to the next production step or selected next shot. Preserve asset and prompt lineage.
- **Retake:** ask **“Keep this clip?”** before returning to the matching preparation page. **Yes** retains the current output in the project's candidate/take history; **No** discards that generated output using this same Keep/Discard choice (no redundant second confirmation); preserve the generation metadata and input draft. In either case, return with the prompt, selected workflow, frame choices/references, per-reference instructions, and other settings restored so the Director can edit and regenerate.
- If the Director leaves without accepting, preserve the candidate and its task record according to project retention rules; do not silently delete it.

Retake is a return-to-edit flow, not a reset. Only the generated output's keep/delete choice changes; user inputs and earlier prompt revisions remain recoverable.

## 5. Shared prompt and asset rules

- The accepted screenplay and scene/shot breakdown provide context; generated prompt text is a production artifact linked to the source revision, not a replacement for screenplay truth.
- Prompt editing and annotation preserve a before/after revision history. The user accepts proposed changes before the revised prompt becomes active.
- Store a reference manifest with stable asset IDs, role, media type, model tag, ordering, source (generated/library/upload), and reference-specific instruction.
- Keep labels deterministic for a given manifest; if adding/removing/reordering media changes numbering, refresh the legend and prompt together, show the change, and revalidate.
- LLM collation may reorganize language for clarity but must retain concrete user instructions, keep media references unambiguous, and ask when materially conflicting directions cannot be reconciled safely.
- The final request sent to MiniMax H3 R2V contains one text prompt and the selected media references. Preserve both the human-entered source context and the exact compiled request for review/debugging.
- Distinguish local files, approved repertoire assets, and generated project assets. Check file format, size, duration, and workflow compatibility before sending to ComfyUI.

## 6. Implementation boundaries

These are planned responsibilities, not claims about current endpoint names:

- **Video mode resolver:** maps the chosen mode to a versioned, capability-checked workflow definition.
- **Prompt editor/annotation service:** target-span instructions, prompt revision diff, and accepted prompt versions shared with image generation.
- **Reference library search:** exposes SEO-based video and audio search, filters, sort order, and approved asset metadata.
- **Reference manifest and validator:** stable asset ordering, MiniMax tag generation, duplicate detection, file/length/capacity checks, and tag-to-asset validation.
- **Prompt collator:** combines screenplay context, main prompt, and reference intents into one reviewable R2V prompt; supports clarifying questions and further chat revisions.
- **ComfyUI job adapter:** submits the correct T2V, FLF, or dynamic R2V workflow and returns task/progress/result state.
- **Candidate/take service:** stores generated clips, prompt/reference lineage, acceptance, and retake keep/delete decisions.

Reuse shared asset search, prompt revision, job state, and candidate lineage services. Keep workflow-specific validation in versioned capability definitions so the UI can present limits without becoming tied to one graph's internals.

## 7. Delivery order

1. Register and verify the three workflow definitions (text-to-video, first/last-frame, reference-to-video), including versions, required inputs, limits, and health/capability status.
2. Build the mode selector and saveable mode-specific drafts.
3. Implement prompt editing and precise annotation with before/after review.
4. Implement first/last frame selection from the correct clip-frame assets, plus file picker, drag-drop, and clipboard image paste.
5. Implement reference selectors, Video Repertoire SEO search, audio search/filtering, uploads, per-reference instructions, stable labels, and capacity validation.
6. Implement prompt collation/chat, tag-map validation, and exact request preview.
7. Connect generation/progress/result review and retake keep/delete behavior to ComfyUI task and candidate records.
8. Run workflow-specific smoke checks with representative valid/invalid inputs and confirm the deployed graphs match the UI capability data.

## 8. Acceptance criteria

- Choosing each of the three modes opens the correct form and sends only to its matching backend workflow.
- Text-to-video presents an editable/annotatable prompt, generation action, and observable progress.
- First/last-frame selectors default to the correct clip first/last assets, exclude character/world-only references, and support file picker, drag-drop, and image clipboard paste.
- Reference-to-video accepts multiple references of supported types, exposes workflow limits, and provides search/sort/filter as planned.
- Every selected R2V reference has a per-reference direction area and a visible generated tag/asset mapping.
- Prompt collation produces one editable prompt, supports clarification/refinement chat, and validates that tags match the exact selected references before submit.
- The generated result displays the clip, complete prompt, workflow/mode, and all relevant frame/reference inputs.
- Retake asks whether to keep the clip, returns with all user inputs intact, and retains or deletes the prior output according to the user's choice.
- Candidate approval, prompt revisions, asset IDs, and workflow version remain traceable.

## 9. Planning boundary

Story Builder already has separate legacy MiniMax workflow graphs and a local reference compiler. This plan defines the clean user-facing journey and durable product behavior; it does not assert that existing legacy forms provide the complete selection, prompt-collation, annotation, UX, or retake experience described here.

## 10. Duration, scale and workflow-aware prompt adaptation

Each mode exposes **clip duration** and **scale/output settings** using the exact parameters supported by its backend workflow. Include resolution/scale preset and aspect ratio or dimensions where supported, with frame rate and other relevant MiniMax settings in an expandable panel. Distinguish output size from any separate guidance-scale parameter if a workflow exposes both. Never display an unsupported control as though it affects generation.

Persist parameter values with each request/take and show them on result review. Validate duration against the selected graph's supported bounds (the inspected local H3 contracts use 5–15 seconds). A change in duration, workflow/model, reference set or output settings invalidates stale prompt validation and produces a reviewable adapted prompt draft.

Prompts evolve as preparation proceeds: screenplay intent → selected clip → selected workflow/model → actual reference manifest → duration/output parameters → final submitted prompt. Preserve canonical story facts and accepted manual edits; show the delta rather than blindly replacing the prompt. The final collated/refined prompt must fit the MiniMax budget before generation.

If a creative edit changes camera, lighting, mood, action, dialogue, SFX or music, offer **Update screenplay** (new source revision and targeted stale detection) or **This take only** (visible attempt-specific override). Technical rewording that preserves meaning does not require changing the screenplay. Result review shows applicable overrides and the exact submitted prompt.

## 11. Recommended references and auxiliary library boundary

Show bound character images and voice files at the top of compatible reference pickers as **Recommended**, with character identity and intended role. Manual pickers leave them unselected until explicitly chosen. Semi automated video may select them through its confirmed Director reference policy; voice binding alone does not attach media to a request. Respect the compiler's duplicate-asset constraints; represent one shared voice asset and its intended speaker mappings deliberately when multiple characters use it.

The main Story Builder consumes searchable assets from one shared media library. `media_prep.md` defines the separate auxiliary video/audio/image preparation, annotation and SEO workspaces. Their output contract supplies stable asset ID, media type, playable file, timestamps/duration, JSON metadata, readable description, category/tags and searchable annotation. Store asset links with each take rather than copying shared files. This plan covers selection and compatible request preparation, not auxiliary analysis/training/repertoire workflows.

Uploads selected directly on the video page enter that same managed library/storage contract. If a long reference needs an excerpt, expose the selected interval and let the user choose or accept it; runtime staging may prepare it for the model while retaining the original asset and provenance. Do not silently trim a reference to an arbitrary interval.

## 12. Execution wrappers and fully automatic continuation

`automation.md` controls which steps run automatically. The wrappers use the same scene/shot/clip records, prompt compiler, reference validator, job state and output store.

Full skips image generation and required manual asset-binding/review gates. Its confirmed recipe starts each scene's first clip with T2V, then uses the immediately preceding generated video as an R2V reference for subsequent clips within that scene. Reset to T2V at every new scene. Initial quality remains fixed; duration is fixed or Director-selected under the confirmed policy. Retain all outputs for the complete story.

Keep every generated clip, including a replaced/failed-quality candidate that exists as playable media. Completion does not claim human approval. Record the ordered scene/clip outputs and predecessor links so the complete story has traceable video coverage. Full produces the complete collection of story clips; final-film stitching/mixing is a separate subsequent plan.

Manual/Semi **Next** advances to the next planned clip, then the next scene, and finally the scene/clip completion overview; it does not imply a finished-film export. Mode pages support skipping unused image/frame stages, but first/last-frame generation still requires its two images when selected.

## 13. Isolated entry and confirmed automation settings

Directly open any video mode and generate without story, screenplay or previous production stages. Use a user-authored prompt and library/uploaded media; source scene/shot/clip links remain optional. FLF still needs its two images, and R2V still needs its compatible selected references. The backend may use a lightweight workspace identity for storage without imposing story setup. Do not create a separate Generate or Manual Director product page to handle isolated work.

Regular story work passes through `automation.md` after screenplay generation and before final prompts. Manual steps show editable prompts with annotation/Codex microediting and wait for Generate/Next. Semi's Video Generation checkbox authorizes the Director to choose FFLF or R2V and compatible prepared frames/character/voice/world references. R2V can also use the preceding clip within the scene when useful. The existing FFLF graph has no direct voice-reference slot; required voice conditioning favors compatible R2V rather than claiming an unsupported FFLF input.

Automatic video confirms quality and all non-duration settings initially, across both workflows. The Director may vary only clip duration under an expressly selected dynamic-duration policy and supported bounds. Otherwise use the confirmed fixed-duration policy. No automatic per-clip quality change or silent downgrade is allowed. Manual generation settings remain editable per request. Status and generation/setup forms share the same verified prompt and parameter limits.


## 14. Integrated review, recovery and continuity

Apply `ux_shared.md`: native playback/candidate comparison, preserved prompts/references on retake, saved context and direct recovery actions. An offline engine blocks submission while editing and saving remain available. Reopen reconnects to known job IDs; it must not repeat a submission. Optional provider details belong in Advanced, while useful duration/quality/ref controls stay visible.

For previous-video continuation, record completed source spans, intended next action/dialogue, character/location state and what the reference should contribute. Distinguish visual continuity from use of its soundtrack so previous dialogue/action is not unintentionally repeated. Inspect available duration/resolution/audio metadata before using a predecessor; these checks do not guarantee creative continuity. Missing/unusable predecessor pauses with a clear remedy; never silently reset to T2V inside the Full scene chain.

Follow `integration.md` for selected tool reuse. Final assembly/composition is a later stage with its own future plan; it does not add prerequisites to the present isolated or story-linked generation forms.
