# Frontend — current change guide (2026-11-09)

**First read [test-first entry](../../fixes/change_readme.md), [active queue](../../fixes/ACTIVE_FIXES.md), [acceptance runbook](../../fixes/ACCEPTANCE_TESTS.md) and relevant [architecture contracts](../../fixes/INTEGRATION_ARCHITECTURE.md).** Test baseline precedes feature/refactor changes.

Keep one persistent `DirectorRuntime.tsx` / `DirectorConversation.tsx` chat. Tool tasks must remain explicit propose → approve → run → evidence; do not mount a second composer or hide unavailable runtimes. Preserve project/session state across pane changes, navigation and expansion.

Editor: `VibeEditorPage.tsx`, `EditorVisualTimeline.tsx`, `ClipJoinReview.tsx`, `NativeWorkspace.tsx`, `FramePipelineWorkspace.tsx`. Existing native HyperFrames Studio and limited OpenMontage Backlot are implemented, not future placeholders. Preserve both clearances, source-relative range controls, draft conflicts, revisioned proposals and preview vs final-output distinction.

Media: reuse `MediaSourcePicker.tsx`, `MediaPickerManagement.tsx`, `lib/media-api.ts` with distinct chat/tool/model/Editor destinations and user consent. Never lose imported assets or turn a five-second preview default into an analysis cap. Storyboard `StoryboardPage.tsx` is authoritative; Backlot is an optional project-owned mirror with a bounded typed edit extension, not a second generator.

**T0 tests:** `npm run typecheck`, `npm run build`, and selected mocked Playwright specs named in the runbook. For later changes add a focused regression first, then run neighbors. Do not silently upgrade React, install native apps or run GPU providers. Capture real vs mocked evidence and preserve unsaved user edits. Refactor oversized components only after characterization tests and no-change UI behavior comparisons.
