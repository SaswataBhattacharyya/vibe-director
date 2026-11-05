# Codex instruction — Phase 1 (USE ONLY AFTER OWNER APPROVAL)

Implement only the approved phase of the plan, beginning with **persistent 3-pane shell + read-only shared capability graph + Editor/Director navigation context**, or the user's explicitly approved modified scope. Preserve existing left navigation and Media Prep unchanged. Do not implement the entire film-generation agent in one PR.

- Create safe branch/worktree where possible, examine diff, preserve uncommitted source and users' project data.
- Add domain models/validation in narrow new modules rather than giant edits in `App.tsx` or monolithic `isolated_server.py`.
- Persist project chat/task context safely and isolate project switches; the center chat remains mounted as right tool pane changes.
- Expose actual right-hand tool route selection and selected asset context, not an iframe assumption.
- Register read-only tool catalogue and live capability checks; do not claim execution until wired.
- Tests: frontend routes/resizing/persistence; project isolation; no manual-generation regression; no change to Media Prep services; backend schema/tool introspection and permission defaults.
- Update skills/agent documentation and small upgrade notes. Show tests (pass/fail), exact modified files, no runtime GPU tests without explicit authorization.
- Deliver a self-review and request approval of next phase.
