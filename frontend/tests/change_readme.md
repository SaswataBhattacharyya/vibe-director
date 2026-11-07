# Frontend Playwright — active verification (2026-11-07)

Read `fixes/ACCEPTANCE_TESTS.md`. Earlier “needs new chat removal/image/take flatten” instructions in deleted 2026-11-06 guides were stale; re-audit current rendered UI before filing regressions.

**Next tests:** Director's single composer, tool-unavailable messaging, approval/Run and source-backed MP3 vs actual timed analyzer; a 7+ second clip with target event after 5s. Editor's `AI Editor | Visual Editor` switch and full expansion, once HF-01 feasibility passes: same session/selected asset, visual timeline edit saved as proposal, clearance invalidated, run/reload/preview/return; no duplicate chat or input file upload. Verify React/Studio CSS/focus isolation and blocked missing module path.

Existing references: `director-runtime.spec.mjs`, `editor-assets.spec.mjs`, `editor-effects.spec.mjs`, `media-source-picker.spec.mjs`, `media-selection-scope.spec.mjs`, `storyboard.spec.mjs`, `video-ui.spec.mjs`. Preserve project ownership, media filter integrity and import consent.

Run accessibility + layout screenshots at 1440/1280/900/390 widths with all app panes on; collapse/restore and full-screen can never double mount active video jobs or lose unsaved forms. Mock provider/API in isolated fixtures; no live GPU/paid calls. Document mock-vs-actual boundaries.
