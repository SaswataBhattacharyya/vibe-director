# UX04 + UX08 — route-by-route migration without losing a feature

**Baseline: latest source 603b1fcb0a3eedbcb32154f3599e419ffef05a15.** Source inventory based on GitHub file reads; confirm current imports, call sites and tests before changing. The older Editor-specific fix is **done as a bounded implementation**; do not delete Editor functionality. Read fixes/UNIFIED_CHAT_AND_PANES.md, fixes/UNIFIED_MEDIA_AND_PROJECT_ASSETS.md and fixes/COMPACT_CREATIVE_WORKSPACE_UX.md.

## One Composer Rule

The shared DirectorConversation in the middle pane is the **only active agent chat composer**; it follows user and current project across all routes. A page may show a field editor, input prompt, production directive, proposal editor, comment on a scene, rule text area or search form: those are *manual task controls*, not duplicate chat. Do not remove them just because they use textarea.

A "Discuss this with Director" action in a page should focus/open the persistent Director and **pass typed source context only** (project owner ID, surface, object ID, selected media, field name/version/hash, constraints), not mount a new chat instance. The Director proposes actual action through typed existing service validators. Page receives reviewable proposal and can Apply/Discard; stale revision/conflict must be visible. Historical embedded conversations remain read-only and never silently discarded.

A chat composer is redundant when it independently accepts a freeform user request to an AI while the shared Director does the same. Proposed replacement must first preserve what that chat *actually did*, including idempotency, approval, review and local draft restore.

## Route audit: current UI and exact safe adaptation

| Route / page | Existing redundant or crowded part | Preserve | New arrangement / dependency |
|---|---|---|---|
| Home / start | Starter cards/entry points may duplicate stage rail | New/Load projects, quick manual Story/Video | Compact project dashboard; one visible Director CTA; stage links optional shortcuts |
| Production Type & Style (ProductionStylesPage.tsx) | Long catalog, publishing details and multiple independent style selectors | Existing versioned style data, media/document evidence and publish flows | Optional type+visual treatment+directing jacket summary; reference evidence via shared picker; advanced publish details collapsed; cannot gate manual tools |
| Story (StoryPage.tsx) | Story revision/edit/proposal interactions, possible old chat-like areas | Story source, text editor, revision CAS, import/PDF, accept/dismiss, recovery | One Director conversation; retain editing tools and proposal Apply; audit any freeform AI composer before removal |
| Screenplay (ScreenplayPage.tsx + ScreenplayDirector.tsx) | Separate screenplay discussion log and text composer | Whole screenplay proposal/diff/checkbox apply; revision/CAS; old messages | First add typed screenplay discuss/propose action to shared Director against exact latest source; keep proposal card in work surface, old log in History; then remove screenplay chat textarea |
| Frame per shot / Storyboard (StoryboardPage.tsx) | "Production instruction" + proposal block; not a chat transcript | Shot/panel controls, scene keys, story setup, route selection, draft Save, video handoff | Keep as manual instruction/proposal field until equivalent central action exists; central Director can propose stage choices, never force wizard |
| Automation & Parameters (ProductionSetupPage.tsx) | Long expert options shown above the actual task | Duration, workflow, readiness, versions, automated/manual options, FFLF pause | Compact settings summary, advanced options, action-focused status; preserve state/validators |
| Prompt Preparation (PromptPreparationPage.tsx + PromptDirector.tsx) | Independent prompt Director log and textarea | Exact prompt targets and approved/selected diffs, learning rules, save | Central prompt/rule intent with source revision/digest and shot focus; work pane keeps prompt editor, diff review and applied learning, read-only legacy history |
| Video Create (App.tsx VideoWorkspace + CreateWorkspace.tsx) | Shot prompt assistant CreateChat plus a large R2V browser matrix | Model selector, manual prompt, T2V/R2V/FL2VA job versions, frozen refs, idempotency and generation | Central prompt refine typed field-edit (with recover-by-key); remove CreateChat after parity; MED01 unifies *browsing*, R2V retains specialized reference role/intent and 9/3/3 caps; nested reference explorer becomes drawer |
| Current Take (TakeWorkspace.tsx + App.tsx VideoWorkspace take branch) | **Double right-side columns**, status/request and viewer split, duplicate metadata | Progress, player, thumbnails, Accept, Retake, Next, fully automated pause/resume, job recovery, prompt history | UX06 single responsive review surface, main player and actions, details in More. Never unmount active job VideoWorkspace or duplicate players |
| Characters & Voices (ImageAssetsPage.tsx, CharacterVoicesPage.tsx) | Old ImageAssetsDirectorChat; Output folder full card, Workflow details, LocalImageFolderBrowser and nested EditorWorkspace | Actual image creation, character/voice identity, candidate approval, Qwen edits, reference/prompt provenance | UX04 typed image prompt intent then remove chat; UX05 flatten right work area; shared media drawer, compact output badge/info; voice controls remain task-appropriate |
| Scene Backgrounds (ImageAssetsPage.tsx + SceneBackgroundVariant.tsx) | Same image-assets nested panel, repeated refs/search | Base location → shot condition/side view; Qwen edit request, prompt and selected references | Same compact image canvas with scene target/condition, role-specific image tray and one media drawer |
| First & Last Frames (ImageAssetsPage.tsx, video APIs) | Same duplicated selectors; visual frame roles | Exact first_frame/last_frame identity, selected shot/clip, manual FFLF pause | Compact frame role chips and selected frame thumbnails; one picker with role binding, not generic R2V reference substitution |
| Text to Image (TextToImagePage.tsx) | t2i-chat secondary AI textarea and LocalImageFolderBrowser separate import | Image prompt editor, Qwen/Z-Image model settings, lora, chosen output folder, save candidate, field proposal Apply | Central Director image prompt proposals; keep prompt field and reference tray; replace duplicate chat with contextual "Ask Director" and one Media drawer. Special browser directory output permissions preserved |
| TRELLIS.2 / Pixal3D (TrellisPage.tsx) | EditorWorkspace with StudioChat separate settings advice | Image inputs, multi-view modes, output grant, previews, single/batch jobs, settings Apply and recovery | Central chat can suggest settings with reviewed Apply; remove old StudioChat only after parity. Right page collapsible main 3D tools, not conversation + another panel |
| Media Prep (MediaPrepPage.tsx) | audio StudioChat lives in EditorWorkspace; several source pickers/output cards | **All** audio/video extraction, voice, F5, YouTube, analysis, effects, Search, indexed retrieval and export | Preserve page and tools. Replace only redundant audio AI chat after typed settings-action parity, using one central chat. Progressive disclosure of existing controls only when tests prove parity |
| Media Library (MediaLibraryPage.tsx) | Separate browse/filter/library page plus other picker variants | Upload, archive/delete, search/index, semantic and annotation management, project scope | Remains full library management; its browse/filter controls feed MED01, and dangerous destructive controls stay here, not in universal picker |
| Vibe Editor (VibeEditorPage.tsx) | **Old composer and nested EditorWorkspace already removed in latest push** | Session picker, brief and plan clearances, timelines, effects, selected ranges, style rules, playback, output and export | Keep Editor work pane compact. Use same Media picker for clips; Director can plan brief via agent_editor. Do not redo UX02/UX03 |
| Status / logs | Long raw readiness/worker metadata | Actual GPU guards, worker health, job errors, recover options | Summary chips and linked deep details; critical safety errors are never hidden |

## Migration pattern per duplicate-chat component (MANDATORY)

0. **Baseline:** Identify exact working endpoint, request/reply fields, persistence key, selected inputs and current tests. Snapshot a disposable example for equivalence.
1. **Adapt:** Register one action in the shared project owner-scoped backend agent tools + conversation/action parser. Do not introduce another standalone "AI chat service".
2. **Context:** connect current page object/revision, selection, SHA, expected target and exact model constraints through typed frontend handoff. Selected context must survive route switches only if still owned and valid.
3. **Review:** place proposed revised prompt/scene/shot/parameter settings + before/after diff or preview **in the work pane**, not as another interactive chat transcript. Keep explicit Apply/Discard and exact CAS checks.
4. **History:** preserve existing source chat transcript/project-specific localStorage/recovery ID as read-only archive with "Previous suggestions". Do not blindly delete old localStorage, saved session or DB records.
5. **Retire:** remove second composer/model menu/Send and old conversation styling; retain manual prompt editor and meaningful page actions. Search imports before deleting component files.
6. **Validate:** no duplicate chat on this route, no loss of prompt/ref/approval/Apply, project switch and stale revision guarded, active jobs unaffected, all manual paths still work.

## Code hazards and strategies

- StudioChat.tsx exports studioRequest(), used by TrellisPage, MediaPrepPage, ProjectController, OutputDestination, VibeEditorPage and others. **Do not delete the module** merely because its component is retired. Later extract the request helper with compatibility import in a focused refactor.
- EditorWorkspace.tsx is not only an Editor component: TakeWorkspace, ImageAssetsPage, TRELLIS and Media Prep consume it. Retire only its **unnecessary inner use** for a specific page; do not globally delete it or rewrite its stable shared behavior.
- App.tsx is about 1235 lines and already contains complex video state, model schemas, idempotency and active job recovery. Extract thin presentational MediaBrowser/R2VReferenceTray/TakeReviewView components *without moving* authoritative request formation or state persistence until tests pass. Avoid a huge one-shot App rewrite.
- ImageAssetsPage.tsx is about 804 lines; new presentation may be split into image surface, toolbar/drawers, candidate gallery, but keep existing accepted character/scene/image state, workflows and onPrompt/onGenerate call signatures stable.
- TextToImagePage uses a browser File System Access output handle and temporary image token; do not replace with server OutputDestination component without route-specific review.
- Existing Video R2V prompt slots, audio paired sound semantics and FL2VA first/last semantics must not be generalized into unsafe "one refs array" sent to the model.
- Project IDs, Editor edit IDs, clip IDs, asset IDs and chat request IDs are distinct. Use typed references, not a global string selection to all pages.
- MediaSourcePicker onAdded currently **adds to destination catalogue**; does not bind model ref or chat attachment. New target adapters must do the additional explicit Apply/binding step.
- Do not use styling-only display:none to retire a form that currently owns an API action, as it breaks user workflows.

## Visual acceptance

At 1440×900, 1280×720, ~900×768 and 390×844, with sidebar+Director expanded, primary work action should be visible or one natural scroll below task context; no nested three-column squeeze, no duplicated source search, no second AI message composer, no long metadata cards before preview/player. Error/recovery statuses and required approvals remain prominent, not hidden under ellipses. Buttons/tabs and overlays keyboard/touch accessible. The project-specific output folder is summarized in one short badge with explicit Change path flow and honest "Custom/unavailable" status.

Test each page with connected fixture project plus standalone tool-library mode. GPU/paid provider and live third-party browser automation remain opt-in only.

## Dependency route

First fix small shared picker's browser/intent adapter (MED01), then port high-value screenshot routes: Image Assets/Scene backgrounds and Current Take (UX05/06); implement compact output (UX07). UX04 legacy chat migrations should proceed by tool with exact action parity, including image before old image chat removal. Then the rest of routes, including Editor/library/search, use the same shared primitives. MED02 global indexing and MED03 physical/membership storage changes are separate higher-risk phases.
