# Ashu studio UI adaptation

## Scope and provenance

This implementation adapts the fresh PR #16-published frontend base in `frontend/` to the owner-approved Ashu structure. Visual and route references are `design/prototypes/vibe-director-flow-proposal.html` and `design/ux-shared-video-review.md`. The three palette token sets (Quiet comic, Concrete & ink, Midnight mixtape) come from the prototype. Nunito 400/700 and its OFL notice are copied unchanged from `design/prototypes/nunito-*-prototype.ttf` and `design/prototypes/nunito-OFL.txt` into `frontend/public/fonts/`.

## Delivered in this UI slice

- Shared sidebar groups for Home, Story Workflow, Video, Library, and System; responsive menu; persistent palette selection.
- Home offers Develop a story and Create directly. Direct Video Create works without a story. The Story page can open an independent T2V draft; it does not claim a workspace/shot association.
- Workflow stage rail includes Production Type & Style before Story, then Screenplay, Automation & Parameters, Prompts, and Video. Unintegrated stages are visible and explicitly unavailable.
- Video Create and Current Take are separate views of the same mounted `VideoWorkspace`. Existing API calls, frozen job/recovery state, draft/history, acceptance, retake, and playback logic remain in `App.tsx`; switching among routes does not unmount the Video component.
- Story source authoring/import/revision and read-only Status remain rendered through the shared shell without replacing their underlying page behavior.
- CSS palette aliases adapt the existing page controls to the selected theme while preserving the established functionality.

## Honest gaps / remaining integration

- The current Video request is independent T2V. Story workspace, revision, scene/shot/clip identifiers and provenance are not carried into its request. A future contract must make this association explicit before any UI says “Story-linked.”
- Production Type & Style, Screenplay, Automation & Parameters, and Prompts are navigation scaffolds, not editors or completed setup. Production setup is still incomplete.
- FFLF and R2V remain unavailable; Assets and Media Prep & Library are unavailable. The UI creates no sample assets, references, or generated content.
- Home does not yet resume a named task/project or route to its unresolved job. Current Take is available from Video navigation, but project switching/task-scoped drafts need a broader task contract.
- Exact FFLF/R2V input roles, source revision/reference manifests, prompt collation limits, annotations, discard semantics, and corresponding generation contracts remain unimplemented.

## Review corrections

Readiness and Status refresh controls were moved out of retired shells into visible page controls; mobile readiness uses its own class so old sidebar media rules cannot hide it. Submitted/recovered jobs open Current Take; retake opens Create. No backend or API client changes are part of this slice.

## Tracked follow-ups

- #3: owner accepted Ashu’s shared navigation design; implementation context follow-up #18 covers real task switching, independent task drafts, resume and linking.
- #4: T2V presentation adapted; exact FFLF/R2V reference/collation/annotation designs remain open with backend #11.
- #6/#10: real Codex story edits, graph and screenplay remain open; #17 keyed create/apply recovery is staged separately.
- #7/#11 assets/voices, #8/#13 wrappers, #9/#12 Media Prep, and #14 assembly retain their existing scopes.

## Verification

`npm run typecheck` and `./node_modules/.bin/vite build --configLoader runner` pass in the staging checkout. The staging `node_modules` points to a read-only source dependency tree; standard Vite config bundling attempted to write a temporary file through that link, so the successful build used Vite's runner config loader. No backend, provider, GPU, live generation, or canonical project files were changed.

Parent review: nine fully intercepted Story/Video/Status journeys pass, including active-job navigation preservation, lost-response recovery, retake without submission, source conflicts/imports and stale Status. Real GET-only review covered all 11 routes at 390px plus three desktop themes, palette reload persistence and preserved prompt; zero POST, page errors or horizontal overflow. Nunito headings and mobile readiness are visible. No media generation, provider calls or legacy broad tests were run. This evidence proves UI preservation, not live rendering.
