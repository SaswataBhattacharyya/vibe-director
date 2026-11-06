# Codex prompt — continue from latest source, not from old cards

You are working in my Vibe Director repository. Use the currently checked-out branch and preserve uncommitted changes. **DO NOT rebuild Q01–Q08** or treat the new chat shell as complete filmmaking automation.

First read:
1. `AGENTS.md`
2. `fixes/CODE_REVIEW_2026-11-06.md`
3. `fixes/ACTIVE_FIXES_2026-11-06.md`
4. `fixes/UNIFIED_CHAT_AND_PANES.md`
5. `fixes/FILE_CHANGE_MATRIX.md` and applicable directory `change_readme.md`
6. Current `fixes/R01_UX03_RESULTS.md`; historical `fixes/Q01_Q06_RESULTS.md`, `fixes/Q07_Q08_RESULTS.md`, blueprint skills and glossary only where needed.

## Updated product/UI requirements
The existing **left sidebar stays intact**. The shared **middle Director chat must be the only active conversational composer**, and the **right pane is the actual editable tool page** (Vibe Editor/Screenplay/Storyboard/Video/Media Prep/Images, etc.). **All three panes independently collapse/restore** without losing page state. The new Director follows the project across pages and can plan, prepare reviewed actions, run approved tools, inspect outputs and delegate editing.

The screenshot shows a duplicate **old Vibe Editor chat** within its own EditorWorkspace. Remove that **only after** connecting the shared Director to actual Editor session/brief/plan operations, otherwise editing becomes unusable. Keep Editor Preview, Asset selection, Timeline, Style, Export, selected ranges, old session history, two approval clearances and trusted HyperFrames renderer. The same rule applies to older page chats listed in UNIFIED_CHAT_AND_PANES.md: preserve proposals/diff/Apply/idempotency while removing redundant composers. Media Prep's existing processing functionality and navigation must not be disturbed.

## Current correctness risks
R01: an abrupt stop between task submitting and job mapping can leave the task stuck.
R02: computer task stdin.write blocks before timeout supervision.
R01/R02 and UX01–UX03 now have local implementations and focused regression evidence in `fixes/R01_UX03_RESULTS.md`. Inspect that record and the current diff; do not repeat completed repairs. Later cards remain open. Follow the current owner instruction for authorization.

## Plan/implementation procedure
1. Show current branch/HEAD/status. Inspect real code and relevant tests before edits. Do not reset/switch/pull without owner approval.
2. State which active task(s) are being implemented, existing vs missing functions, exact patch boundary, upstream/downstream blast radius, rollback and tests.
3. Present the concrete patch plan for review unless an explicit current owner instruction already authorizes that implementation scope. **Do not treat documentation updates as permission to run paid/GPU or grant unrestricted computer access.**
4. When authorized, implement focused small readable changes, not giant rewrites or duplicate engines. Follow code-simplification/ponytail/blast-radius workflows.
5. Run focused backend/Playwright/build checks, mock CPU tests first, verify disposal of any synthetic PNG/TXT/MP4/WAV and test-owned DB/projects even on failure; never remove user media.
6. Report real results and what remains. Respect the dependency UX02 BEFORE UX03, and leave no duplicate main chat by the end of UX03.
7. Continue future creative/film features only as explicitly scoped. Actual outputs—not text plans—determine whether film tasks are completed.

**Start by reconciling this review with your local uncommitted work and producing an updated file-level implementation plan.**
