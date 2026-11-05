# Frontend source — proposed precise changes

Status: code-level instructions ONLY; existing application React files remain unchanged. First inspect current branch and uncommitted edits.

## Current relevant source facts
App.tsx (~1200–1233) parses hash routes and renders the chosen page inside StudioShell. StudioShell.tsx (~52–77) supplies the current left sidebar (keep it) and a visual stage rail (currently implies a pipeline). EditorWorkspace.tsx is a small two-pane toggle; VibeEditorPage.tsx holds Editor chat, asset selection/ranges, preview, timeline, styles and export. PromptPreparationPage.tsx uses an accepted-screenplay/setup path, while Video Create also supports independent manual drafts. StoryboardPage.tsx:38–65 uses a browser-controlled autoFrames loop; do not copy that approach for long-running agent orchestration.

## A. Stable Codex-like shell without replacing sidebar or Media Prep
Introduce small AgentWorkspace.tsx, AgentChat.tsx, AgentTaskPanel.tsx, AgentSkillPicker.tsx and scoped agent-workspace.css. Wrap the chosen page in the right-hand real work surface, and mount project-specific chat in a STABLE center component so changing a route does not discard conversation/tasks.

Conceptual JSX (obtain actual projectId from existing managed project controller first):

    <AgentWorkspace projectId={projectId} activeRoute={route}>
      <AgentChat projectId={projectId}
                 specialist={route === 'editor' ? 'editor' : 'director'} />
      <section className="agent-work-surface">{children}</section>
    </AgentWorkspace>

Place this in StudioShell after topbar, preserving the existing aside/sidebar, navigation, palette and Media Prep page intact. Project switch must atomically change chat, asset context and query owner. Ensure old async responses cannot land in another project's chat. Both panes collapsible/resizable; center chat remains visible on most routes, responsive tab treatment on narrow screens. Do not mount a fake browser screenshot in the right pane.

The numbered stage rail should be labeled as optional shortcuts, not compulsory steps; keep every direct route working. Do not force story/screenplay/board completion for standalone Video Create, image or Editor.

## B. AgentChat must show plan/approval/actual execution separately
Use typed client from ../src/lib/change_readme.md. Persist messages, task plans, grants and events server-side; browser localStorage is a draft cache only. Render:
- Chat and actual attached media with selected asset IDs and optional ranges.
- Plan (steps, dependencies, model, estimated duration, resources, permission tier, rollback).
- Approve exact plan revision, then Execute approved. No hidden creation from merely opening a page or viewing a plan.
- Job progress, uncertainty/recovery, actual output assets and raw blocker reason.
- Skill chips Global/App/Project, style jacket choices, tool capability reasons.
Use event/task ID polling tied to project/task, abort stale requests on route and project switch; no infinite spinner without a saved status.

## C. VibeEditorPage.tsx + EditorWorkspace.tsx: specialist and same shared tools
Keep current Editor preview/media/timeline/style/export tools, selected in/out ranges and existing two-clearance render. Move only the general-purpose agent conversation to the stable shared chat (specialist=editor), or bridge the existing Editor chat cleanly; do NOT create two unlinked chat sessions and two sets of approval buttons. The Editor planner behind vibe_editor.run_job currently cannot execute tools; the shared agent gateway should invoke real actions such as audio.extract_mp3 and hand registered results back to the Editor selection surface. Extraction must not silently replace soundtrack.

Agent-to-Editor handoff requires project ID, editor session, selected asset IDs and time ranges, target composition/brief, provenance and task ID. Show clear phases: requested → executing tool → output registered → Editor plan proposed → render approved → finished. Keep existing Editor render scope/range validators and export collision checks.

## D. ProductionStylesPage.tsx — optional layered creative guidance
Retain versioned published production types and directing styles, but redesign visible default into three independent choices:
1) Production TYPE: short film, ad, explainer, etc. — story and screenplay guidance.
2) Visual STYLE: anime, live-action, illustration, etc. — characters, environments, storyboard and video look.
3) Directing STYLE: cinematic, observational, horror, etc. — camera, pacing, lighting, sound.
Each may be None/Inherit. Show project-saved choices with versions and a collapsed advanced publish/edit area. Agent uses approved selection as creative guidance, not strict video admission. Existing published versions must not be silently rewritten by user edits.

## E. ScreenplayPage.tsx — collaboration via proposals, not mandatory gate
Keep source/graph/screenplay revisions and existing whole-screenplay/field-edit mechanisms. Add "Direct this scene" and "Revise dialogue/pacing" actions that send selected scene/shot IDs and requested changes to shared chat, return a proposal/diff and apply through original expected-revision route. Manual video still works with no current screenplay. The AI can create a screenplay from story, but it never turns a suggestion into a lock.

## F. StoryboardPage.tsx — comic book that is quick to review
Current BoardBody contains per-shot route, prompt, images, duration, reference_ids, first/last frame IDs and optional media. Reuse these records: render each panel with illustration, dialogue, action and duration. Offer click-to-edit image/dialogue/duration and per-shot "prepare prompt / generate video" with explicit handoff. Multiple panels can describe a continuous 15-second shot; panels are NOT necessarily individual model render jobs.
Current autoFrames browser loop is not robust across browser close; move future agent automation to server-owned tasks while retaining existing manual per-shot actions and saved batch recovery. Respect current FFLF automatic pause until reviewed.

## G. PromptPreparationPage.tsx / Video Create — exact reference manifest
Above each proposed MiniMax prompt, show assets to upload/select in actual numbered slots: images separate from audio and video, matched by asset ID + SHA; label which audio is a voice identity sample. Enforce selected model duration and prompt length (<7000 Unicode code points). Show exact timestamp action blocks, camera plan, end-frame continuity goal, dialogue time budget and scene-to-scene continuation.
IMPORTANT: R2V last-frame image reference is spatial continuity only. FL2VA owns actual first and last frame fields. Do not invent first_frame inside R2V request. Do not allow LTX toggle until new versioned server route is accepted and tested; showing a switch alone is misleading.

## H. Compact code & blast radius
Prefer four small new components and one typed shared client to expanding 1,200-line App.tsx. Do not redesign MediaPrepPage or sidebar. Keep CSS scoped to agent shell with existing variables. Verify existing routes, editor session restore, project switching, staged references, video form admission, responsive layout, user keyboard focus and unsaved warning. Tests use synthetic temporary images/media only with automatic cleanup.