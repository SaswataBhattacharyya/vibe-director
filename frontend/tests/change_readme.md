# Frontend tests — current guidance (2026-11-09)

Start with [T0 test baseline runbook](../../fixes/ACCEPTANCE_TESTS.md). Record HEAD, existing dirty files, test commands, exit codes, passed/failed/skipped and mocked vs native evidence. **No application changes while establishing the baseline.**

First run `npm run typecheck` and `npm run build` with existing dependencies. Use `npx --no-install playwright test tests/clip-join.spec.mjs tests/director-runtime.spec.mjs tests/editor-visual.spec.mjs tests/editor-effects.spec.mjs tests/storyboard.spec.mjs` for representative browser contract coverage. Inspect each test's `page.route` interception: browser API mocks do not prove real MCP, GPU, owner-media or native GUI acceptance.

For UI regressions check one persistent chat, full tool settings, two Editor clearances, selected-range behavior beyond five seconds, import/folder consent, storyboard saved revisions, native Studio/Backlot handoffs and source continuity preview. Capture keyboard/focus at 1440/1280/900/390 widths as targeted tests, not assumed global acceptance.

`native-interfaces.manual.mjs`, `editor-preview.manual.mjs` and other real-runtime scripts are separate opt-in isolated acceptance. Verify test-owned server/process/media cleanup; never point them to the owner's working project or invoke paid/GPU generation incidentally.

If any test fails, classify pre-existing/test/environment/product regression before altering source or assertions. Do not weaken tests to make the suite green.
