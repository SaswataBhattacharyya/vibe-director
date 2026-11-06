# One Director conversation + three independently collapsible panes

> **STATUS UPDATE — 2026-11-06 at source commit 603b1fcb.** The original three-pane and Vibe Editor-only migration outlined below (UX01–UX03) have been implemented as bounded fixes. This file is retained for behavior requirements and regression parity, **not** a queue to reimplement them. For the owner's expanded every-page request use [fresh review](REFRESH_REVIEW_2026-11-06_603b1fcb.md), [all-page chat/layout migration](PAGE_BY_PAGE_CHAT_AND_LAYOUT.md), [media browser/asset graph](UNIFIED_MEDIA_AND_PROJECT_ASSETS.md), [compact UI](COMPACT_CREATIVE_WORKSPACE_UX.md) and [active tasks](ACTIVE_FIXES_2026-11-06.md). Only UX04 onward remains open.

**Status:** required follow-up to `2d4878db...`; not yet applied. Read [code review](CODE_REVIEW_2026-11-06.md), [active tasks](ACTIVE_FIXES_2026-11-06.md) and `AGENTS.md`. Preserve existing left navigation, Media Prep features and all project history.

## Non-negotiable interaction contract

```
┌── LEFT NAV ──┬──── MIDDLE: DIRECTOR ────┬──────── RIGHT: LIVE WORK SURFACE ────┐
│ Existing    │ ONE persistent project    │ Current route: Story / Screenplay / │
│ sidebar     │ conversation & task cards │ Storyboard / Video / Vibe Editor ...│
│ [collapse]  │ [collapse]                │ [collapse]                         │
└─────────────┴───────────────────────────┴──────────────────────────────────────┘
```

The three panes must each collapse/expand **independently** on desktop. Collapsing a pane must NOT destroy unsaved form state or ongoing chat/task/job. Always-visible toolbar buttons restore hidden panes, including when all three are collapsed; preserve keyboard and mobile layouts. The primary Director conversation **must not be duplicated** in a page. Tool-specific forms, prompt fields, editors, approval cards, preview/timeline tabs and read-only legacy history are **not** redundant chat boxes.

## Change A — one state authority for the center/right pane

Current: `StudioShell.tsx` owns `navClosed` and sidebar; `DirectorWorkspace.tsx` owns saved width + mobile `surface`; `DirectorConversation.tsx` owns its own `open`; `DirectorRuntime.tsx` portals the chat through `DirectorSlot`.

- **Keep** the left sidebar markup and `navClosed` behavior (existing collapse works). Do not copy or replace the navigation.
- Lift center `chatOpen` and right `workOpen` to ONE project-scoped pane controller accessible by both `DirectorWorkspace` and portal-mounted `DirectorConversation` (recommended: a tiny context in `DirectorRuntime`, not another global store). Use `useProjectState('DirectorWorkspace:panes', {chat:true, work:true})` with migration from the previous local `open` default where meaningful.
- `DirectorConversation` receives controlled `open/onToggle` rather than a private `useState(true)`; existing header button becomes a true center-pane toggle. `DirectorWorkspace` provides a **right-workspace** toggle in a small fixed/topbar toolbar, and a **Restore Director** button when hidden. All restore controls must remain clickable when panels are hidden.
- Derive grid columns from both booleans, not a CSS `:has(.director-collapsed)` shortcut that assumes the right side is always visible. Keep left sidebar independent. Remove/mute the drag separator when either center/right is closed; preserve keyboard `ArrowLeft/ArrowRight/Home/End` resizing when both open.
- **Keep both React subtrees mounted** while hidden so editor selections/textarea drafts/timeline and portal/chat remain alive. Use CSS `hidden`/visibility appropriately with inert/focus restrictions; do not change route to collapse. Ensure hidden panes cannot trap Tab or screen-reader navigation. When only one central/right pane is open, it fills the available main width. When both are closed, show a compact restore strip/route title.
- Responsive: existing `surface='chat'|'workspace'` mobile tabs may remain, but implement the same logical open/restore state with visible two-tab navigation and a stable mount. Tablet widths need sensible minmax sizes, not a nested three-column Editor. Respect stored width sanity and project remount keyed in `ProjectController.tsx`.
- Persist center/right collapse per project through current `useProjectState` hook; sidebar can retain its current global preference.

**Illustrative shape, not a drop-in patch:**
```tsx
type WorkPanes = {chat: boolean; work: boolean};
const [panes, setPanes] = useProjectState<WorkPanes>(
  'DirectorWorkspace:panes', {chat: true, work: true}
);
const setPane = (pane: keyof WorkPanes, open: boolean) =>
  setPanes(old => ({...old, [pane]: open}));
// Render a restore toolbar independently of the two optional pane bodies.
// Do not conditionally remove <DirectorSlot/> or {children}.
```

**Tests:** left-only/middle-only/right-only/none/both, independent toggles, keyboard and pointer width, refresh, project A→B→A, screenshot desktop/tablet/mobile, focus when collapsed, unsaved Editor timeline and Video Create prompts survive toggling.

## Change B — Vibe Editor: migrate the useful operations BEFORE removing legacy composer

**Source anchors:**
- `VibeEditorPage.tsx:88–91` `submit` → `POST /api/editor/projects/{id}/command` action `chat` (creative brief preparation).
- `VibeEditorPage.tsx:138–153` `<EditorWorkspace>`, `editor-messages`, `editor-clearance`, `editor-job`, `editor-composer`.
- `vibe_editor.command` owns brief→approve→prepare_plan→approve→render, revision checks and selected media ranges.
- `agent_conversation.RESPONSE_SCHEMA` currently has only discuss, MP3 and last-frame intents; passing `surface:'editor'` does not include `project.id` or Editor ranges.

**Required staged integration:**

1. **Typed surface context:** central Director must learn which real Editor session is active: `workspace_id` (project owner), `editor_session_id` (edit-*), `expected_editor_revision`, `selected_ranges` and selected asset IDs/hashes; treat Editor media selection as source authority. Share via a small typed React context/handoff plus a server-owned session lookup. Recheck owner/session/revision/ranges server-side; never trust browser state alone.
2. **Actual action bridge:** add a narrow allowlisted `editor.prepare_brief` action that invokes the existing Editor command/service *through its validated API*, using text from central chat, correct session and revision. This should prepare an edit brief, **not render** or bypass Editor's two clearances. Expose subsequent `editor.prepare_plan` and approved-render proposal under separate explicit approvals once implemented. Avoid adding a second tool execution engine.
3. **Read-only existing history:** keep `project.messages` visible under `<details><summary>Previous Editor session history</summary>...` or a history tab; do not render a second live conversational log. Never delete `project.messages`, revisions, style rules, drafts or saved session DB.
4. **Retire old composer only after (1)-(3) pass:** remove `<form className="editor-composer">` and its message input/model/picker/send UI. Move Attach/Browse, media selection, style selection, session switch, approval/job controls, timeline/preview/export to right-hand **tool panels**. Do not remove buttons like Approve brief, Prepare media plan, Pause, Retry, Export; retain API contracts. Convert references like `composer.current?.focus()` to focus a surviving control or shared chat; remove orphaned handlers/state in a separate cleanup pass.
5. **Eliminate nested layout:** for Vibe Editor route stop wrapping the old chat + preview in another `<EditorWorkspace name="editor">` two-column grid. The right workspace directly renders Editor session bar, clearances/job cards and Preview/Asset selection/Timeline/Style/Export tabs. **Do not delete the reusable EditorWorkspace.tsx**, still consumed by TRELLIS and Media Prep.
6. **One conversation authority going forward:** the central `agent_messages` remains current dialog; old `edit-* project.messages` remain legacy per-session records. Link replies/plans/outputs by actual task/session IDs; do not copy text with fabricated message identities. Display exact editor session in agent context and have task status reflect real backend job.

**Proof before removal:** from central chat: "Make a punchy 20-second edit from selected clips" → proposal/brief appears for actual active Editor session → clarifications resolved → first clearance available → selected media and tools planned → second clearance available → authorized HyperFrames render via existing trust boundary → result visible in Preview. Also test whole-asset MP3 handoff and selection/range integrity. All without old textarea. A mocked reasoning test proves UI routing, not actual render quality.

## Change C — other legacy conversational interfaces (inventory, per-page migration)

| Page | Existing component/anchor | Preserve on migration | Remove only after working shared chat equivalent |
|---|---|---|---|
| Screenplay | `ScreenplayPage.tsx:144` → `ScreenplayDirector.tsx:68–113` | Saved conversation/proposal history, selected field diffs, apply with revision/CAS | Embedded message log and message composer; keep explicit Review/Apply panel |
| Prompt Preparation | `PromptPreparationPage.tsx:274` → `PromptDirector.tsx:89–121` | Prompt diffs, shot focus, learning rules, source revision, Apply | Old conversational form/log; keep saved rule management and proposal cards |
| Video Create | `CreateWorkspace.tsx:17–76` `CreateChat` | Field-edit proposal key, recovery, source prompt snapshot, Apply suggestion | `Shot prompt assistant` chat UI after typed `video.refine_prompt` action; keep edit/generate controls |
| Image Assets / backgrounds | `ImageAssetsPage.tsx:39–67,699` `ImageAssetsDirectorChat` | Image prompt suggestion, base prompt check, Apply and image refs | Chat log/textarea; keep proposal and preview |
| Text to Image | `TextToImagePage.tsx:265` `t2i-chat` | Reference images, proposed prompt, Use suggested prompt, output folder/generation controls | Embedded secondary prompt chat, not the image prompt editor |
| TRELLIS/Pixal | `TrellisPage.tsx:42` `StudioChat` + `EditorWorkspace` | Tool settings, suggested settings Apply, existing 3D controls | Old chat instance when shared Director can propose/apply safe settings |
| Media Prep audio | `MediaPrepPage.tsx:819` `StudioChat` + `EditorWorkspace` | **Every Media Prep operation and existing selected audio settings**; suggestions/Apply as needed | Only redundant conversation widget once parity demonstrated; otherwise defer removal rather than damaging Media Prep |
| Storyboard | `StoryboardPage.tsx:85` Production instruction/proposal | Source shot context, editable proposal, generated-media and storyboard Save | This is a **proposal form**, not a full chat log; keep until shared typed director action replaces it |
| Story | `StoryPage.tsx` story proposal/revision editor | Source text, edit history/recovery and apply/accept | Treat as manual editing tool until separately proven duplicate |

**Do not delete `StudioChat.tsx` blindly:** it exports `studioRequest()`, used by several unrelated pages. Factor that generic request helper into a stable client only after tracing all imports, and preserve its API behavior. Likewise `EditorWorkspace` remains used outside Vibe Editor.

## Change D — shared backend action context and staged migration

Extend `agent_conversation.py` and `agent_api.py` in small typed/revisioned steps (not broad generic function calling). Current strict payload keys are `request_id,text,asset_ids,skill_refs,surface`. Future context must include optional, server-verified `target` with `surface`, `editor_session_id`, `expected_revision`, `selected_ranges`, `scene/shot` IDs and field snapshot/digest. Version request schema so existing saved idempotency hashes still work. A chat's structured reasoning output is a **proposal**, never executor permission. Register one actual action at a time using existing service validators. An `editor.prepare_brief` request is not a blanket grant to render; Editor's pending clearance must still be explicitly approved.

Allow a page to offer “Ask Director about this selection” which only *sets context in the one composer* and focuses it. Never mount another chat. If no adapter exists for the requested action, reply with exact limitation and optionally open the relevant manual controls—don't claim the operation happened.

## Change E — tests and cleanup

- Add `frontend/tests/single-director-chat.spec.mjs` (or equivalent): for each route, count **one** primary text composer and one active Director conversation; no legacy editor, screenplay, prompt, image or 3D chat textbox; keep legitimate input forms.
- Extend `frontend/tests/director-runtime.spec.mjs` and `create-panes.spec.mjs`: all pane states, restore controls, touch/mobile, keyboard, resizing and project switch.
- Add actual Editor bridge integration with mock LLM + existing Editor service and selected workspace assets. Test session switch, revision 409, conflicting media range, pending clarification, saved historical messages, no auto-render on Send.
- Reuse existing `backend/story_builder/tests/test_agent_editor_tool_handoff.py` and Editor service tests for MP3 and render plan validation. New fixture media: isolated `TemporaryDirectory` PNG/WAV/MP4/text; cleanup on errors; never delete user assets.
- Preserve `MediaPrepPage` processing and sidebar in screenshot regression. No GPU/paid-provider runs without separate approval.

**Acceptance:** one visible agent chat throughout the app; Vibe Editor right panel has no duplicate composer; all three panes independently collapse and recover, with no state loss; manual pages and Renderer controls work; no backend history or source media was deleted.
