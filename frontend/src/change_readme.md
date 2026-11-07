# Frontend — active change guide (2026-11-07)

**Read:** `fixes/CODEX_START_HERE.md`, `fixes/ACTIVE_FIXES.md`, `fixes/INTEGRATION_ARCHITECTURE.md`. The previous Q/R and UX01–UX03 implementation cards and most UX04/UX05–UX08 layout migrations are **source-implemented**, not a new todo. Confirm current code and route coverage; no sweeping redesign.

- **One persistent chat:** `DirectorRuntime.tsx` / `DirectorConversation.tsx`. Keep only one active AI composer; technical prompts, screenplay editors, property editors and search controls are not duplicate chats.
- **Visual Editor:** `VibeEditorPage.tsx` owns current AI Editor preview/media/timeline/style/export + clearance UI. Add a gated HyperFrames Studio composition view in its right work pane with full-window expansion after HF-01 compatibility proof. Prefer slim child components/typed view models, no new nested nav and no second chat. Unmount/mount must not discard unsaved plan, playback, running job or chat draft.
- **Media:** `MediaSourcePicker.tsx`, `EditorAssetBrowser.tsx`, `LocalImageFolderBrowser.tsx`, `lib/media-api.ts` and `App.tsx` R2V bindings; re-use picker across surfaces but preserve explicit distinct chat attachments, model slots, tool inputs and Editor ranges. Do not remove import/folder consent or delete management by accident.
- **Storyboard:** `StoryboardPage.tsx` remains authoritative for panels, scene/shot planning, revisions and manual routing. OpenMontage Production Board is optional, not replacement.
- **Compact page regressions:** Image Assets, Current Take, Output, Screenplay, Prompt, Text to Image, Media Prep and 3D retain real controls. `EditorWorkspace.tsx` and `StudioChat.tsx` are still used/export helpers; trace imports before deletion.

Use `fixes/ACCEPTANCE_TESTS.md` for focused source, keyboard/mobile, save/reload and regression coverage.
