# Frontend — unfinished work only (2026-11-06)

Read [the current code review](../../fixes/CODE_REVIEW_2026-11-06.md), [active tasks](../../fixes/ACTIVE_FIXES_2026-11-06.md), and [exact one-chat/three-pane spec](../../fixes/UNIFIED_CHAT_AND_PANES.md). Old Q06 discovery/inspector/client work **is implemented**; do not rebuild it.

## UX01: three independent collapse controls
Files: `StudioShell.tsx` (existing `navClosed` and sidebar), `DirectorWorkspace.tsx` (chat width/mobile switch), `DirectorRuntime.tsx` (single stable portal), `DirectorConversation.tsx` (currently private `open`), `director-runtime.css`.
- Preserve sidebar markup and design. Introduce controlled project-scoped `chatOpen` and `workOpen`; keep nav's existing toggle. Add always-visible restore controls and explicit two-pane/one-pane/none grid behavior.
- Keep children and `DirectorSlot` mounted while collapsed, maintain focus/accessibility and resizer only when both visible; mobile should expose tabs.
- Add tests for all eight left/center/right combinations, project switch, unsaved Editor/timeline and Video prompts, keyboard/resize, responsive layout.

## UX02 → UX03: Vibe Editor is most urgent
`VibeEditorPage.tsx` still mounts `editor-messages` and `editor-composer` inside `<EditorWorkspace name="editor">`, so it duplicates central `DirectorConversation`.
- First build typed shared-chat Editor action context (actual `edit-* session`, selected ranges, revision) and send a creative brief via **existing** `vibe_editor.command(action='chat')`; preserve Editor's two clearances, revision checks and render adapter.
- Then remove the old Editor composer and nested Editor-only split. Keep session picker, asset search/attach, exact ranges, Editor brief/plan controls, job status/pause/retry, timeline, style and export in the **right** pane. Move old message history into collapsed **read-only Previous sessions**.
- Do not delete `EditorWorkspace.tsx`: TRELLIS and Media Prep still use it. Do not delete `studioRequest` from `StudioChat.tsx`: other app pages import it.

## UX04: other duplicate chats
The following have separate inputs/logs: `ScreenplayDirector.tsx` (used by ScreenplayPage), `PromptDirector.tsx` (PromptPreparationPage), `CreateWorkspace.tsx` shot chat, `TextToImagePage.tsx` prompt chat, `ImageAssetsPage.tsx` ImageAssetsDirectorChat, `TrellisPage.tsx` StudioChat, `MediaPrepPage.tsx` audio StudioChat. `StoryboardPage.tsx` has a proposal/production instruction form, not a conversation transcript. Migrate one at a time: typed context → server proposal/recovery/apply → read-only existing history → remove old message composer/log. Keep **manual text prompt fields and real tool controls**. Do not refactor Media Prep processing; retain full functionality while removing redundant chat only after parity.

## Other outstanding frontend behavior
- `DirectorRuntime.tsx` currently derives editor surface from `location.hash` only; include actual Editor session/selection/revision through safe typed context.
- `DirectorConversation.tsx` should show clear true task progress and status/recovery, not imply planning equals a completed edit/film.
- Future optional production type/visual style/directing style; story/shot revisions; comic panels; reference manifests and LTX-off must follow backend contracts, not fake UI toggles.

**Code quality:** small view components/hooks and one typed context; no giant App.tsx rewrite, duplicate fetch/client logic or CSS that merely hides a non-migrated feature. Re-run relevant Playwright/build checks, clean synthetic fixture assets, preserve user project history.
