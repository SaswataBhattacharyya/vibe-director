# Shared UI and recovery rules

Applies to screenplay, image/world/frame/voice/video stages and Media Prep. These rules integrate Ashu's StudioDirector UI guidance with the current product plans. `automation.md` remains authoritative for advancement and approval behavior; `integration.md` defines code reuse boundaries.

## 1. Entry, context and navigation

Show the current saved workspace/project and, for story-linked work, screenplay revision and scene/shot/clip position. Provide a direct Continue action identifying the next unfinished task. An isolated task needs only its local prompt/assets/settings; it must not be forced through story or project-authoring setup.

Keep story/screenplay, shared generation stages, Media Prep/library and Status discoverable without competing controller pages. Secondary tools retain access to their capabilities through the agreed surfaces. Old links can redirect safely; redirects never submit generation or invent missing scene/source context.

## 2. Readable creative work and useful controls

Use prose, scene/shot cards, image previews, voice playback and clear parameter labels. Keep raw JSON/IDs/provider internals in optional Advanced disclosure. Duration, output quality, reference roles, required assets and prompt-size readiness remain visible when they affect a decision.

The readable screenplay holds integrated creative direction; technical records remain derived. Preserve contextual annotation, selected-text microediting, reviewable edits, undo/history and the Update screenplay/This take only distinction. Do not add a second scene-plan editor with independent creative authority.

## 3. Readiness and state

Every actionable stage distinguishes loading, empty, unavailable, failed, ready, running and completed states. Explain the exact blocker with a direct recovery action: choose a missing frame, pick a compatible workflow, shorten/refine a prompt, retry a connection check, or resume a known job.

Prerequisites apply to the chosen action. T2V does not require images; FFLF requires its actual two frame anchors; R2V needs compatible selected references. Character identity references are not interchangeable with endpoint frames. Silent clips do not acquire a compulsory voice binding.

If ComfyUI is offline, continue editing and saving prompts/story/selection where those actions are otherwise available. If the reasoning provider is offline, direct text edits and saving remain available while AI refinement is marked unavailable. A failed generation does not erase the draft or its reference choices.

## 4. Progress and take review

Provide a single production overview: stage/item, source coverage where present, duration/output settings, workflow, selected refs, exact submitted prompt, job state, generated takes and next action. Show a specific manual stop in Semi. Workflow completion and human acceptance are separate states.

Use native playback and candidate comparison. Manual keeps Generate/Next and review/retake; automatic selected stages advance under their policy without compulsory acceptance. Preserve requests on retake. Manual keep/discard choices follow `video_gen.md`; Full retains every clip. Do not delete assets shared by other tasks when discarding a take.

Reload/reopen restores drafts, selections, policy, progress and known outputs. Reconnect to the existing upstream job instead of resubmitting. Story/screenplay changes mark affected dependent work stale and offer targeted reconciliation while retaining existing outputs/history.

## 5. Mobile and UI acceptance

Use a compact context header, collapsible navigation and one task column. Put the next action near the task and make readiness/reference sections expandable. Complex editing may need more space, but small screens must expose state, recovery and playback clearly.

Before declaring the UX complete, walk through regular Manual, mixed Semi, Full across two scenes, isolated generation, silent/reference-free generation, offline edit/save, prompt-budget recovery, retake, reload/resume and small-screen navigation. Reuse `automation.md`'s concrete routing checks. A static mockup or passing backend tests alone do not prove the implemented UI is usable.
