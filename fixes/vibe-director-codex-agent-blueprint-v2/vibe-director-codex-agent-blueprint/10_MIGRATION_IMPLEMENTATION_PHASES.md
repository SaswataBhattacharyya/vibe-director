# Staged implementation — protect today's working app

No rewrite-all, no mass deleting historical behavior. Feature flags, small adapters, branch-based changes and tests at every phase. Ordering represents dependency, not mandatory USER navigation.

## Phase 0 — reconcile and baseline (read-only)
- In user's actual checkout: `git status`, current SHA/branch, local uncommitted diff. Start from the currently checked-out branch/HEAD. The `vibe-director-current` branch now includes the Nov 5 review, tool glossary, project and media-discovery changes; initial Nov 1 GitHub findings are historical. Inspect current Editor source and media-discovery fixes directly, then compare any remaining local-only changes.
- Run existing unit/frontend tests safely, produce baseline failure matrix. Inventory true app tools/APIs, tool glossary, actual source schemas, runtime/computer access. No code modifications until plan approved.
- Output detailed change plan, files and risk/permission gates; ask owner "Implement?".

## Phase 1 — persistent Codex shell, read-only graph
- Keep `StudioShell.tsx` sidebar and Media Prep untouched.
- Mount durable project chat + right work pane with real navigation and context bridge. Put current `VibeEditorPage` into right pane.
- Build read-only tool registry and graph projection queries; skill index lazy loading. Show tool capability and *actual* availability. No arbitrary code execution.
- Acceptance: switch pages without losing chat or selection; project switch isolates both.

## Phase 2 — first REAL cross-tool vertical slice
- From Editor chat: select video → use existing Media Prep Extract MP3 capability → submit utility job → display running status → show registered playable output → return to Editor. Preserve original media.
- From Director chat: project lookup, media browse, continuity frame extraction. Add handoff contracts.
- Acceptance: actual utility output, not navigation-only or mock.

## Phase 3 — plan/approve/execute engine + computer runtime
- Durable `TaskPlan` and `Task` DAG with approval, event log, tool calls/reconcile, pause/recovery. Authenticated local computer/code sidecar (scoped fs/shell/git/tests/browser, optional desktop), explicit consent and audit.
- Director and Editor share same agent executor, distinct skill/jacket context.
- Acceptance: propose plan without writes, approve selective stages, execute/test small local coding/media task, restart recovery.

## Phase 4 — craft skills and creative UI
- Integrate 13 skill files (original 6 + production style + operating skills); index version/hash, load relevant only. Optional style jackets, screenplay updates and comic storyboard. Keep all routes accessible.
- Preproduction assets Z-Image prompts and worlds; canonical identity and revision mapping.
- Acceptance: user can start with video and then backfill screenplay, or ask chat for storyboard and edit a single panel.

## Phase 5 — model-aware video preparation and generation
- Model-specific capability resolver; exact R2V/T2V/FFLF fields; `<Picture N>`/`<audioN>` mapping, voice sample vs dialogue; 15 sec and strict <7000 codepoint checks for this H3 route. Real reference manifests and last-frame extraction route.
- Implement LTX toggle as versioned whole-pipeline behavior with source/final stream validation; preserve old jobs.
- Acceptance: real manual T2V/R2V supported modes, no unnecessary screenplay gate; verify LTX OFF submits zero LTX chunks and publishes valid Turbo-only asset.

## Phase 6 — QA, retake, editing and final movie
- Consume actual visual/audio analysis via supported tools; quality findings with timestamps/evidence, user review. Retake only the affected clip, preserve take history; do not auto-overwrite.
- Unified editable timeline with existing images/video, generated clips, source ranges and soundtrack; Editor handoff and verified final export. Keep strict legacy screenplay assembly available separately.
- Acceptance: a short fable from plan approval to reviewed final MP4 with at least one documented defect/retake and editor handoff.

## Phase 7 — optional external agents/GUI
- Evaluate HyperFrames Studio embed and output roundtrip; OpenMontage isolated workflow adapter and license; Backlot monitoring bridge. Feature flag, no forced dependencies.
- Acceptance: optional integration disabled leaves native work fully functional.

## Code seams to inspect or wrap
`frontend/src/StudioShell.tsx`, `App.tsx`, `VibeEditorPage.tsx`, `EditorWorkspace.tsx`, `ProductionStylesPage.tsx`, `ScreenplayPage.tsx`, `StoryboardPage.tsx` (or current pathname), `PromptPreparationPage.tsx`, `MediaPrepPage.tsx` (preserve), plus relevant `frontend/src/lib/*` clients. Backend: `isolated_server.py`, `director_skills.py`, `vibe_editor.py`, `vibe_editor_api.py`, `vibe_editor_render.py`, `production_setup.py`, `story_authoring.py`, `storyboard.py`, `media_library.py`, `media_discovery.py`, `production_ledger.py`, `isolated_video_jobs.py`, `production_job_worker.py`, `t2v_pipeline.py`, `ltx_chunks.py`, exact video contracts, audio utilities. Do not assume line numbers match local tree.
