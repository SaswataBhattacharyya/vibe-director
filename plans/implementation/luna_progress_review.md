# Luna progress review and next-work guidance — 2026-10-11

## Scope and evidence

Reviewed the latest handoff entries and current producer/consumer code for stage-local prompt migration, Full-mode entry, Assisted clip planning, Media Library annotations and workflow knowledge. This is a targeted review of recent progress, not certification of the entire app. The runtime goal is active. Git remains deferred; no live reasoning-provider calls, media generation, model transfer or visible browser opening occurred in this review.

## Confirmed defects fixed

5. **Invalid custom-style evidence could strand the form.** The publish handler set its busy flag before validating all selected reference notes, then returned outside its `try/finally`. Validation now precedes the busy state. The browser regression covers the invalid-submit-then-correct path; focused mocked Playwright execution now passes 1/1 with host browser access. Sandbox browser launches still fail before assertions; see latest `HANDOFF.md`.

1. **Fresh Assisted planning was blocked.** Video Create called `prepare_assisted_video_clip_plan`, which requires current saved prompt drafts, after the prompt-authoring route was retired. On explicit Plan/Replan only, the panel now reads current drafts, preserves compatible existing prompts, prepares and saves missing shot prompts via the existing APIs, then plans clips. Loading the page never calls the provider or starts a job. This is the approved plan-clips-before-reference-mapping action, not a return to an upfront global prompt page.
2. **Same-page workspace switching could retain another story's plan/run.** Assisted and Full panels now observe query/hash changes; Assisted resets context/reference choices and both guard async replies against an obsolete load. Full polling and capability replies cannot install stale workspace state.
3. **Replanning could silently discard unsaved references.** Confirmation now includes unsaved mappings. Editing is disabled while planning/saving. After planning, reload the saved plan/reference state; idempotent backend plan responses omit references and must not be treated as an empty saved map.
4. **FFLF removal could erase both roles.** When one image was assigned to first and last frames, removing first removed both. Removal now uses asset ID plus frame role.
5. **Full mode briefly rendered duplicate run regions.** Loading and recovered run panels are now mutually exclusive.

Files: `frontend/src/AssistedClipPlanPanel.tsx`, `frontend/src/App.tsx`, `frontend/tests/video-story-route.spec.mjs`.

## Checks actually run

- TypeScript typecheck passed after all code edits.
- Dedicated-port mocked browser run: `video-story-route.spec.mjs` + `full-run-video-entry.spec.mjs`: **10/10 passed**. This includes fresh planning with no saved prompts, explicit-click-only preparation, same-page workspace switching, unsaved-reference confirmation and Full-entry/start gating.
- Additional role-specific FFLF removal browser regression: **1/1 passed**.
- Focused backend: Media Library, workflow knowledge, prompt drafts and the Assisted split-plan/reference-map test: **36/36 passed**.
- Initial browser run exposed the duplicate Full-loading region; it was fixed and the affected case passed in the final run. Tests use mocked provider/job APIs; no live generation acceptance is claimed.

The old broad browser-startup limitation is not a universal blocker: this review successfully used `VIBE_DIRECTOR_TEST_PORT=5296` with the actual Vibe checkout. Use a dedicated free port and verify the intended app before interpreting results. Do not retry unrelated suites or stop another application's server.

## Remaining gaps; do not mark complete

- **Current implementation boundary:** the Assisted durable runner and Full-mode visual identity sampling/crop/retry pipeline are implemented locally. Do not reimplement either from older notes. Fully automated mode intentionally skips character/world/frame image generation and voice selection; those stages are only in Assisted manual. Do not list Full image-stage progression as missing functionality. Remaining P6 evidence is live vision/runtime compatibility, empirical identity-quality review and owner-started continuity acceptance; these are acceptance gates, not permission to add a synchronous provider path.
- Global Prompts is retired from app routing. Dormant `PromptPreparationPage.tsx` and its page-only tests are historical source, not a reachable recovery page. Do not direct users there. Narrowly adapt still-relevant scenarios to actual stage destinations; preserve useful API/recovery coverage. Do not wholesale delete tests to make a suite green.
- Stage-local prompt preparation and edits must remain at the point of use. Verify each screen against the latest notes rather than reopening a global prompt detour. Media Prep has since gained nested tools, carousel/search controls, persistence and lineage slices; remaining parity and semantic indexing are listed in `remaining_app.md`. Do not repeat those implemented controls as new tasks.
- Full-mode image/voice/world/frame progression is intentionally out of scope. The implemented identity review/crop pipeline still needs live runtime and quality acceptance. Donor independence and owner-run acceptance remain open; keep live generation behind the owner's click.
- Donor preservation and runtime independence follow `donor_independence.md`; neither bulk transfer nor deletion occurred during this review.

## Adapted Luna implementation rules

### Follow-up from the production-style audit

Do not treat a selector or a copied module as feature completion. Trace the value through its actual producer, saved record, prompt builder/job, and visible consumer. The built-in directing-style value reaches story, video and image prompt preparation. New source media and selected video frames now link to that direction and story recommendations filter on it; old type-version-only references have ambiguous direction and remain a compatibility fallback. Multimodal analysis that learns reusable style rules is not implemented. Keep those boundaries clear. Before reporting a feature as done, list the paths/contracts that were actually checked and focused evidence; distinguish planned behavior, mocked behavior and owner-accepted live behavior.

Before a migration, write a small responsibility map: old entry → prerequisite data/API → user action → persisted result → next destination. Trace actual backend prerequisites, not just TypeScript types. Move every reachable responsibility before hiding its old entry. 

For each meaningful change, prefer one focused **fresh-state** path with absent derived data. A fixture that injects finished prompts/plans cannot prove the app prepares them. Also check relevant reload/workspace-change/failed-request cases where state can be lost or stale. Keep provider/job calls mocked for coding checks, and assert no submission occurs merely on page load. Owner performs live acceptance clicks.

For async forms, finish all synchronous validation before setting loading/busy state. If validation must happen afterward, route every exit through a `finally`. Include an invalid-submit-then-correct regression so an early return cannot leave controls disabled.

For versioned creative inputs such as production type/style, trace the exact version/hash through the prompt, frozen job lineage, batch idempotency key, parent run key, retries, and preflight/replay lookup. A lineage field alone does not make a changed input produce a new job; all key derivations and their callers must use the same canonical identity. Add a focused test proving that changing the selected version changes the key while an unchanged retry reuses it.

Use the actual mounted route. A same-path query change does not necessarily remount React components. Guard asynchronous reads and mutations against context changes; use role as part of identity when one asset may fill two slots. Preserve saved prompts/choices and recovery data.

Finish a coherent visible path before jumping to another small label/control improvement. Keep implementation, mocked behavior and owner-accepted live behavior separate in the completion note. No new dependencies/frameworks or engine rewrites.

Luna works directly without Luna subagents. This review was explicitly owner-requested; it does not change the infrequent Sol cadence: consolidated P2–P6, final P7, or a genuine investigated blocker.

## Compact next task prompt for Luna

Continue the end-to-end goal directly, one substantial dependency path at a time. Check `plans/remaining_app.md`, the latest `HANDOFF.md`, and the relevant stage plan before choosing work; later implementation entries supersede historical gaps. For donor migration, trace source → destination → runtime consumer and verify hashes/provenance. Do not rerun the large copy or prune staged data without a reviewed inventory. Reuse existing engines and adapters; don't rebuild completed flows. Run focused tests for changed contracts, typecheck when frontend changes, and avoid the legacy 600+ suite. Use the browser occasionally on a verified Vibe port for meaningful UI milestones, not each edit. Owner performs live analyzer/generation acceptance. No Luna workers, routine Sol review, Git hosting, GPU jobs, or donor deletion.

### P6 visual-continuity task guard

For cross-scene Full-mode continuity, follow the latest P6 handoff. Codex vision is already available through `reasoning_provider.generate_json(..., image_paths=...)`; Image Detailer is Ollama-only and is not a substitute. Do not place a model call inside `advance_fully_automated_run`. First trace the durable video-worker lifecycle and add a recoverable, idempotent analysis checkpoint with bounded frame samples and clip-hash/timestamp evidence; only then connect character matching and next-clip reference resolution. Mock vision calls in software checks. Never claim identity from filenames or metadata, and leave ambiguous matches unassigned. If the durable lifecycle cannot support this safely, record the concrete blocker and continue with another open slice instead of adding a synchronous shortcut. Sol remains reserved for the owner's stated review cadence.


## Review correction — 2026-10-12

Image Detailer's index button repeated a defect already fixed in Media Library: filename and roles are valid saved annotation text, so descriptions/tags must not be prerequisites. Its existing happy-path fixture had both and concealed the mismatch. When copying a control, compare its eligibility to the backend helper and an already-working sibling; include a minimal valid record in the focused check.

Image Detailer's library refresh also lacked a workspace-response guard and retained an old active job when it was absent from new history. Clear context-bound data on workspace changes, discard obsolete read results, and select jobs from the current history. Prevent workspace switches while a mutation is in flight, or explicitly bind its result to its original context. Check a delayed A response arriving after B loads. Do not broaden this into a new state framework.

Historical path diagnosis (2026-10-12; superseded): an earlier task was bound to the nonexistent `Vibe Director 2` path. In the current task, `pwd` is `/home/riki/Documents/ChatGPT/Vibe Director`, and project edits have succeeded. Recheck the live environment before diagnosing permissions; do not repeat host/mount checks or request escalation based only on this old incident. The reviewed temporary patch was applied to the product; do not reapply it.

### Codex project path check — 2026-10-12

Historical project-path check (2026-10-12; superseded in this task): the old task had stale permission metadata despite the saved project pointing to the correct checkout. This task now starts in `/home/riki/Documents/ChatGPT/Vibe Director`; do not assume the previous failure persists. If a later task has a mismatch, inspect its actual `pwd` and test the relevant operation once before diagnosing. Do not recreate folders or repeat broad filesystem diagnostics.

Continue implementing a coherent phase directly. Sol reviews remain consolidated after P2–P6 and final P7, or a specific investigated blocker. This owner-requested review does not create a new routine review cadence.

Applied-check evidence: frontend TypeScript and spec syntax pass; the two new Image Detailer browser regressions pass 2/2 using approved host access on port 5306. Do not repeat the checks without another relevant change.
