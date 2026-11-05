# Change README — Vibe Director agent implementation map

**Source checked:** `vibe-director-current` at `d467dbb269312eabe1ee7afe0697de5187857f61` before adding this guide. This is a **proposed change guide, not an applied application fix**. Read repository `AGENTS.md`, `full_review.md`, `tool_glossary/` and the blueprint at `fixes/vibe-director-codex-agent-blueprint-v2/vibe-director-codex-agent-blueprint/` first. Always inspect current HEAD and uncommitted edits.

## Objective
Build a **Codex-class, project-aware filmmaking Director and Editor** using the already-existing engines and tools. Each page works independently; a user may also request plan → approve → execute for a full film. Both agents have *the same* project/global/app skill resolver and typed tool gateway, with specialized creative/Editor contexts. Computer/terminal/Git/browser capability requires a separately installed authorized runtime, not skill text.

## Codex entry points
Read [CODEX_CHANGE_README_PROMPT.md](CODEX_CHANGE_README_PROMPT.md) and the [file-by-file change matrix](FILE_CHANGE_MATRIX.md) before implementation. Two **project-local proposal skills**, not globally installed or live app skills, are [blast-radius-review](skills/blast-radius-review/SKILL.md) and [compact-code-craft](skills/compact-code-craft/SKILL.md). They help identify downstream risks and keep patches maintainable. The latest proposed guides are in the code directories listed below.

## Placement-specific guides
- `backend/story_builder/change_readme.md`: add one safe API routing seam, task storage/checkpoint and no duplicate dispatcher logic.
- `backend/story_builder/services/change_readme.md`: implement shared tool registry, agent plans, graph/skill service and media operations; model-safe exact APIs, LTX follow-up.
- `backend/story_builder/tests/change_readme.md`: CPU/mock tests, synthetic media fixtures, fail-safe cleanup, blast-radius regressions.
- `frontend/src/change_readme.md`: reuse left sidebar, add project-persistent center chat and real right work area; adapt Editor, Storyboard, styles and prompts.
- `frontend/src/lib/change_readme.md`: typed agent client, routing/selection context, no duplicate HTTP business logic.
- `design/vibe-editor/change_readme.md`: keep HyperFrames trusted renderer, make Editor a tool-using specialist, ensure handoff parity.
- `skills/change_readme.md`: install/link 13 blueprint skills without replacing original 3 installed craft paths; shared global/bundled/project discovery.

## Small ordered slices (DEPENDENCIES, not a mandatory user wizard)
0. **Baseline only**: audit current modules, frozen contracts, local changes, tests and feasibility. No application change.
1. **Read-only services**: typed tool catalogue, skill metadata lookup, project context/graph projection and frontend compact inspector.
2. **One real cross-tool operation**: Editor/Director → Media Prep existing `extract_mp3` → durable job → registered playable asset; same backend path as manual API. Do not change Media Prep UI.
3. **Plan/approval/job runtime**: immutable approved task steps, own durable status, pause/recovery/idempotent calls; project save/load parity.
4. **Creative craft and UI**: optional production type + visual style + directing style; screenplay, comic-book storyboard, reference-aware 15-sec video prompts.
5. **Full film & QA**: new tool-managed mixed-media task graph (not the existing T2V-only full-run), observation-backed defect reports, retake loop, Editor/timeline handoff, verified export.
6. **Later only**: computer/coding sidecar (scoped filesystem/terminal/Git/browser/desktop), OpenMontage/Backlot/HyperFrames Studio adapters, genuine LTX-off pipeline with migrated versioned contracts.

**Approval:** complete and demonstrate one slice, show diff and tests, then ask before moving to the next. Plan approval is not the same as every downstream destructive/GPU/provider permission.

## Verified existing seams
- `isolated_server.py` routes `/api/editor/*` to `vibe_editor_api.handle`; audio utilities are handled in the main dispatcher.
- `audio_utilities.capabilities()`, `stage_assets()`, `video_repertoire.create_job('audio-utilities', request)` and `start_job()` already power Extract MP3.
- `video_continuity.last_frame()` and `POST /api/video/jobs/{id}/continuity-frame` exist; use their registered `asset_id/sha256`.
- `vibe_editor_render.py` is trusted JSON→HyperFrames/FFmpeg; the editor LLM currently plans only and must not be turned into an unvalidated shell.
- `production_setup.py` currently calls `fully_automated` an image-free route; keep historical jobs, add new agent planning separately.
- T2V/R2V/FL2VA have **different exact request fields**, and only FL2VA uses actual first/last frame inputs; R2V continuity images are references, not guaranteed first-frame conditioning.
- `projects.py` save/load snapshots a known ledger and project-owned content; new agent state needs explicit Save/Load tests.
- Existing `skills/vibe-director`, `skills/video-prompting`, `design/vibe-editor/skills/vibe-editor-director` are live paths; the 13 blueprint files under `fixes/` are not automatically live.
- **Preserve** existing navigation, Media Prep, media hashes, immutable requests, output grants, acceptance, recovery and GPU watchdog.

## Blast radius review: source evidence, not invented skill
No installed dedicated “blast radius” or “Ponytail” skill was available in this assistant session. The checked `graphify-out/graph.json` contains **145 nodes and 634 edges**; it is partial and did not index every proposed seam. Use it as a clue only. For EACH change, run repository-wide callsite search, follow imports / HTTP producers / consumers, and inspect output/DB/test contracts. Refresh the local Graphify index per repo `AGENTS.md` **if its required environment exists**; never claim full dependency coverage from its node count.

| Seam | Direct consumers / blast-radius tests |
|---|---|
| `StudioShell.tsx` | App routing, Storyboard and Editor routes, per-page forms, browser memory and responsive layout |
| `isolated_server.py` | every API route, authorization, error responses; test existing `/api/editor`, `/api/audio`, `/api/video` |
| `projects.py` + ledger | project import/export, stale-state protection, global style tables, agent task states |
| `director_skills.py` | screenplay/video prompt callers, Editor's independent skill loader, skill hash budgets |
| `vibe_editor.py` | chat approvals, selected media/ranges, style memory, jobs, export |
| `isolated_*_contract.py` / LTX | frontend serializers, workflow graph digests, collection, resume, old jobs, frame/audio validation |
| `storyboard.py` | screenplay revision, image jobs, manual handoff, storyboard export, editor handoff |

## Compact code rule
Add *one service per responsibility*, keep schemas at boundaries, reuse existing validators/adapters, prefer pure planners and small typed functions. Avoid appending hundreds of lines to `App.tsx`, `isolated_server.py`, `VibeEditorPage.tsx`. Do not implement a generic arbitrary tool executor by exposing shell strings through HTTP.

## Tests and cleanup
Use `tempfile.TemporaryDirectory` / `pytest tmp_path` for dummy PNG/WAV/MP4/text, distinct test DB/project, `try/finally`. Delete only test-owned fixtures and associated test-owned records, including failures; verify cleanup. Do NOT wipe user projects, production media or accepted outputs. No unattended GPU/paid-provider tests. Capture actual test evidence before calling a phase complete.
