# R01/R02 and UX01–UX03 — local implementation results

> **GIT STATUS UPDATE.** This result was authored while the 603b1fcb batch was local/uncommitted, but that batch was subsequently pushed to vibe-director-current. Its tests remain **reported by Codex at the time**, not rerun in the current documentation review. For future work consult [active fixes](ACTIVE_FIXES_2026-11-06.md).

Base: `39680fa382698890542f0751613f33c36fe15241`, branch `vibe-director-current`. Changes are local and uncommitted. This is a bounded implementation result, not completion of the filmmaking blueprint.

## Completed behavior

- **R01:** Poll reconciles a saved submission intent with its existing frozen job after abrupt process death. It verifies owner, tool, invocation and request before mapping. GET never dispatches. Missing jobs become `recovery_required`; mapped/mismatched/duplicate jobs cannot silently allocate replacements.
- **R02:** Computer stdin delivery is nonblocking and supervised from the start by the execution deadline and journal budget. Early exit/BrokenPipe, slow readers and a child that never reads are bounded. Failure/cancellation retains private evidence and terminates/reaps the process group; no uncertain execution is replayed.
- **UX01:** Navigation, shared conversation and work surface independently collapse. Hidden conversation/work children stay mounted, preserving shot prompts, chat drafts and unsaved timeline JSON. Center/right preferences use existing project-scoped storage; all eight desktop combinations, reload, mobile fallback and A → B → A switching are covered.
- **UX02:** Shared chat can propose `editor.prepare_brief` for the actual saved Editor session. Version 1 target includes session ID, expected revision and exact asset ranges. Server loads/validates owner, selected media hashes and confirmed style snapshot. An approved agent task invokes the existing Editor brief command/worker; it cannot approve either Editor clearance or render. Reconciliation uses the existing durable job identity.
- **UX03:** Vibe Editor has one conversational composer, in the shared Director pane. Existing session messages and unsent drafts remain read-only history. Session picker, upload/drop/paste, library attachment, ranges, brief/plan approvals, jobs, pause/stop/retry, timeline, style memory and export remain. The shared `EditorWorkspace` used by other tools is retained. Active preview/timeline is above attachments/history; model/status dialogs stay above sidebar; Send and Access remain visible at 1280×720.

No database schema migration, renderer replacement, dependency installation or global-skill installation was needed. Existing project/asset/session/revision/job ownership remains authoritative.

## Contracts and boundaries

`POST /api/agent/projects/{owner}/conversation` retains the existing five-field request and accepts optional `target` only for `surface: editor`. The target is revalidated after reasoning through task preparation. Old request hashes/retries remain compatible. Task create/approve/run/poll routes retain their contracts; a typed Editor plan is added. The tool manifest now advertises the bounded brief adapter.

The Editor Python command adds internal-only `agent_request`/`on_created` arguments and a `prepare_brief` action. This action always prepares a brief, even if its text is “yes, apply”. Existing explicit brief/plan approvals remain the only path toward rendering. No generic shell or renderer endpoint is introduced.

## Checks actually run

1. `PYTHONPATH=backend python -m unittest discover -s backend/story_builder/tests -p 'test_agent*.py'` — **44 tests, 43 passed, 1 opt-in sandbox test skipped**. Reasoning/provider calls and worker launches are mocked; computer pipe supervision uses real CPU child processes. Covers existing skills, discovery, both chat surfaces, frozen plans, media input changes, crash windows, cancellation, Editor owner/revision/ranges/style and job corruption.
2. `PYTHONPATH=backend python -m unittest backend.test_editor_clearance backend.test_editor_effects` — **6 passed**, including CPU FFmpeg effects checks and existing clearance boundaries.
3. Playwright: `director-runtime`, `editor-assets`, `editor-effects`, `ace-editor-ux`, `model-selection`, `agent-inspector`, `project-pruning-recovery`, `create-panes` — **30 passed**. After final compact control-row and stronger setup cleanup changes, the Editor clearance/layout and nested-folder tests were rerun — **2 passed**. Uses Snap Chromium, isolated port 5193 and mock APIs. Backend proxy intentionally points to port 1 so unmocked keepalive requests cannot write into the owner's backend. Expected ECONNREFUSED messages are this isolation boundary.
4. `npm run build` — TypeScript and Vite passed. Existing bundle-size warning remains; no new dependency.
5. Source citations: bundled blast-radius verifier — **34 anchors matched, zero rejected**. [Impact record](../.review/active-fixes-impact.json) traces the API/service/job and shell/runtime/Editor paths. Maximum lower-bound impact priority is 0.60 (high); this is not a defect probability. Unknown caller counts and worker test gaps are explicit.
6. Final Graphify full code-only extraction: **5,170 nodes / 15,649 edges**, 530 code files scanned; 90 files (JSON) yielded no nodes, 246 non-code files and 45 unsupported files were omitted. An incremental refresh produced a partial 8-node graph; a forced full extraction restored the complete graph, and its counts were read directly from graph.json. Use `--force` for this installation until incremental behavior is resolved. This graph is a discovery aid, not coverage proof.
7. `git diff --check` passed.

During development, outdated browser fixtures, one obsolete tool-availability expectation and the footer clipping defect were corrected and their affected tests rerun. One test invocation named nonexistent `test_agent_conversation`; corrected discovery above passed. An accidental root-directory `npx tsc` lookup failed on DNS; the correct frontend-local build passed and package/lockfiles were not changed.

Existing SQLite ResourceWarnings remain in the ledger connection usage. Tests pass, but this batch does not claim warning-free database lifecycle handling.

## Cleanup and runtime limits

Agent fixtures own temporary projects/databases/jobs and dummy media, register cleanup and assert removal. Folder-import setup is now inside `try/finally`, with explicit absence verification even on test failure. One prior interrupted-run folder was identified by exact relative paths and bytes matching the committed dummy fixture and removed; no user media were present.

Temporary screenshot/output roots `/tmp/vibe-unified-check-lJn4MD`, `/tmp/vibe-unified-layout-final` and `/tmp/vibe-unified-final-checks` were removed after visual inspection and their absence was verified. Verification also confirmed absence of those exact directories, `vibe-agent-task-*`, `vibe-editor-folder-*`, and checkout `.test-editor-folder-*`. No production records, original media or history are deleted. Browser fixtures do not contact the owner's backend. No paid/provider, GPU generation or live Codex computer task was run.

Screenshots were visually inspected at desktop and mobile sizes. Automated interaction evidence is mocked/CPU evidence; it does not establish live provider readiness or finished-film acceptance. The owner's running backend was not restarted by this batch; it must load these Python changes before using the new Editor chat action. Existing frontend dev servers can load source changes automatically.

## Rollback

No migration rollback is required. Review and reverse only this batch's application/test/documentation diff against the stated base; preserve any later owner changes. Do not reset the checkout or delete runtime data. Before running an older backend, let any new Editor brief task finish or cancel it through the supported task controls; older code lacks the new adapter needed to observe those tasks. Keep saved sessions, job journals, source clips and ledger rows. Regenerate Graphify after any code rollback. Historical Editor session data and the standalone/manual rendering paths remain usable.

## Still open

- **UX04:** Route-by-route shared chat adapters before removing screenplay/prompt/Create/image/3D/Media Prep composers; preserve each proposal/diff/Apply path. Next smallest safe slice is screenplay proposal preparation using the accepted draft/revision context.
- **AG01:** Editor brief adapter is implemented; the rest of the shared action registry/context integrations remain incomplete.
- **AG02:** Durable film dependency graph, evidence-backed QA, retakes and finishing remain.
- **CR01:** Optional creative jackets and independent comic storyboard work remain.
- **VID01:** Hash-bound reference manifest and separately versioned LTX OFF workflow remain.

Do not mark these cards done based on the new shared chat shell or this result record. Current source and active cards guide the next implementation slice.

## Changed files

- `.review/active-fixes-impact.json`
- `backend/story_builder/services/agent_computer.py`
- `backend/story_builder/services/agent_conversation.py`
- `backend/story_builder/services/agent_editor.py`
- `backend/story_builder/services/agent_tasks.py`
- `backend/story_builder/services/agent_tools.py`
- `backend/story_builder/services/vibe_editor.py`
- `backend/story_builder/tests/test_agent_api.py`
- `backend/story_builder/tests/test_agent_computer.py`
- `backend/story_builder/tests/test_agent_editor.py`
- `backend/story_builder/tests/test_agent_tasks.py`
- `backend/story_builder/tests/test_agent_tools.py`
- `fixes/ACTIVE_FIXES_2026-11-06.md`
- `fixes/CODEX_CHANGE_README_PROMPT.md`
- `fixes/FILE_CHANGE_MATRIX.md`
- `fixes/R01_UX03_RESULTS.md`
- `frontend/src/DirectorConversation.tsx`
- `frontend/src/DirectorEditor.tsx`
- `frontend/src/DirectorRuntime.tsx`
- `frontend/src/DirectorWorkspace.tsx`
- `frontend/src/VibeEditorPage.tsx`
- `frontend/src/director-runtime.css`
- `frontend/src/lib/agent-tasks.ts`
- `frontend/tests/ace-editor-ux.spec.mjs`
- `frontend/tests/director-runtime.spec.mjs`
- `frontend/tests/editor-assets.spec.mjs`
- `frontend/tests/editor-effects.spec.mjs`
- `frontend/tests/model-selection.spec.mjs`
- `frontend/tests/project-pruning-recovery.spec.mjs`
- `graphify-out/cache/ast/v0.9.17/18939af4016e6521e5c1f175e6d4f138dd930ff8af1b2c8bb09b3bb1cc4e7bc7.json`
- `graphify-out/cache/ast/v0.9.17/1983eefddaed8b0b0c6f2681311c1bcb5aaacb2e4f75f5ae512b7a224bd48204.json`
- `graphify-out/cache/ast/v0.9.17/292efe4b65cb67a64d7b3466f2de7a6c94b9a746695d40d4c4fe14d2fd52d791.json`
- `graphify-out/cache/ast/v0.9.17/3f1ae6e86d681b7761e812db60178ce80155ad8a35664864efd0b9382d22114e.json`
- `graphify-out/cache/ast/v0.9.17/41e7c68e19cb9209e795f19502e7b6bd5e971fc443fb02550c521f5aab841b4b.json`
- `graphify-out/cache/ast/v0.9.17/4633daa470ff9f4716ab02b00f54702298202a73527efc7e4bda4f934472fe03.json`
- `graphify-out/cache/ast/v0.9.17/7c2f3be1e6f7a8a24239128d4bb277ab01da90c69e2bf9ab22d56507efcf9b96.json`
- `graphify-out/cache/ast/v0.9.17/856816331b01b8da5a1d10571d1090253e4201e2c2e3dce8f732587c1ee12d46.json`
- `graphify-out/cache/ast/v0.9.17/8ce4f85f6a2f8f80588d84808dda9aeed31b131f9113cabed46ec93cece7cff5.json`
- `graphify-out/cache/ast/v0.9.17/9e1e2cc9c21582d455a95a0672f0b275a5172015bb9910ed9098d5d9c1aab6bf.json`
- `graphify-out/cache/ast/v0.9.17/a3df85cfa96c570f5eb2504db634ec9f15049e07ac3907bd9d4de3103abc7ca0.json`
- `graphify-out/cache/ast/v0.9.17/b93b5bdd9a4580dfb5202508719b60d078b158228c15236186517b1257780137.json`
- `graphify-out/cache/ast/v0.9.17/bd509fa5b87a50b760eb03f30795885118bcd3beaec3c452c6341253dbefb86a.json`
- `graphify-out/cache/ast/v0.9.17/e5a9d0ad19e5f3b9fd0b3257ac2db547288e814b21046a347732204ebd974c4b.json`
- `graphify-out/cache/stat-index.json`
- `graphify-out/graph.json`
- `graphify-out/manifest.json`
