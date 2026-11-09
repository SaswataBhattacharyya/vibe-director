# Acceptance and test baseline — executable runbook

This file specifies **what to run and how to record results**, not a claim that they passed. First milestone: **T0-BASELINE** on current `vibe-director-current`. Execute on the owner's configured Ubuntu/ARM64 checkout, respecting all existing runtime/job guards.

## 0. Safety preflight (no edits)

From repository root:

```bash
git branch --show-current
git rev-parse HEAD
git status --short
git diff --check
uname -m
command -v conda || true
command -v ffmpeg || true
command -v ffprobe || true
command -v melt || command -v melt-7 || true
command -v node || true
command -v pnpm || true
```

Write results to a **new ignored test-only folder** such as `local_data/test-reports/<run-id>/`. Do not commit environment secrets, user paths, generated media, full logs with tokens, or changed application state. Keep a baseline of already-dirty files; do not “fix” by resetting them. Report branch mismatch as a blocker. Record Node, Python, FFmpeg, MLT, Flatpak and runtime versions if present; absence means SKIP/BLOCKED, never PASS.

Before invoking any test, skim its setup/teardown and marker/skip rules. Tests invoking real ComfyUI, expensive generation, external network/providers, training, destructive checkpoint cleanup or user projects **must be excluded** from routine T0. Use disposable fixtures and existing test harness roots only.

## 1. Static/front-end baseline (safe; no media generation)

With dependencies **already installed**:

```bash
cd frontend
npm run typecheck
npm run build
cd ..
git diff --check
```

Do not silently run `npm ci`, upgrade Node/React, rewrite lockfiles, regenerate Graphify or change runtime packages merely to run this step. If dependencies are missing, record the blocker and seek an explicit environment-install step. A Vite bundle-size warning is not automatically a failure; capture it.

## 2. Focused Python CPU/mocked tests

Use the existing `react` Conda environment (or the confirmed project Python, without creating a new environment) and run from `backend/`:

```bash
cd backend
conda run --no-capture-output -n react python -m unittest \
  story_builder.tests.test_video_overlap \
  story_builder.tests.test_editor_kdenlive \
  story_builder.tests.test_kdenlive_bridge \
  story_builder.tests.test_agent_tool_access \
  story_builder.tests.test_agent_tasks \
  story_builder.tests.test_editor_preview \
  story_builder.tests.test_editor_speech \
  story_builder.tests.test_projects
cd ..
```

Some native Kdenlive tests intentionally skip if private pinned runtime/host MLT is absent. Record skips and check that real runtime cases were not silently mistaken for mock coverage. These tests may produce short synthetic CPU video in temporary folders; verify fixture cleanup. A failure caused by a missing dependency belongs in the environment category, not automatically a code defect.

Next, inventory the **full** backend suite from files and test setups. Only after identifying unsafe/external-runtime cases, run a broader bounded selection. Do not blindly start every `test_*.py` on the owner's active production environment.

## 3. Browser contract tests (mocked APIs)

With `frontend/` dependencies and browser installed:

```bash
cd frontend
npx --no-install playwright test \
  tests/clip-join.spec.mjs \
  tests/director-runtime.spec.mjs \
  tests/editor-visual.spec.mjs \
  tests/editor-effects.spec.mjs \
  tests/storyboard.spec.mjs
cd ..
```

These tests may intercept APIs and must be recorded as **MOCKED browser verification** unless the individual test proves otherwise. Inspect failures for test flakiness, race conditions and console errors; capture failing trace/screenshot in ignored test artifacts. Avoid running against a live owner project.

## 4. Native CPU acceptance — opt-in after baseline passes

Kdenlive MCP synthetic diagnostics: `node scripts/check_kdenlive_mcp.mjs` from repo root **only after** verifying its private runtime, sandbox/test root, no production media, and actual script actions. Inspect the existing `test_editor_kdenlive.py` real-runtime cases: preview, exact approval, linked audio, verified output, editable project, recovery and source byte preservation. The Kdenlive/MLT runtime is pinned, not necessarily Flatpak GUI-compatible.

HyperFrames/OpenMontage: inspect `frontend/tests/native-interfaces.manual.mjs`, sandboxed runtime processes, and cleanup, then run only in an isolated synthetic acceptance window. Native Studio is not the same as a React mock; Backlot extension is not general upstream write-back. Verify revision conflicts and cleanup.

**Owner desktop test (manual):** download a disposable rendered `.kdenlive` project; open in Flatpak Kdenlive; confirm media paths, both linked A/V clips, trim, audio join, playback and no missing-media dialog. Record Flatpak version and any 26.04-format compatibility errors. Do not assert this test passed unless the owner actually performed it.

**GPU/provider tests:** separate explicit permission, safe operating conditions and user-owned acceptance. None are required for T0. Do not start image/video/voice training, paid API calls or AI rendering to diagnose a CPU unit-test failure.

## 5. Gate-specific acceptance matrix

| Gate | Evidence required |
| --- | --- |
| T0 baseline | HEAD + dirty map + environment inventory; each command, exit status, cases passed/failed/skipped, duration, environment-only blockers and test-owned cleanup. No production modifications. |
| T1 triage | Repro case or minimal fixture, failure classification, source owner and affected callers, severity, proposed test and stop/go. |
| T2 fix | One bounded commit; focused regression now passing; neighbor tests; no lost original hashes/owner IDs/revisions; rollback steps. |
| S1 capability truth | Table for all 37 registered tools: registered/ready/actionable; missing model/runtime yields unavailable or actionable blocker **before approval**; no tool execution during discovery. |
| S2 MCP isolation | Minimal-env allowlist; no API token inherited; outside-root paths refused; cancellation, timeout and orphan cleanup verified; uncertain external acknowledgements not replayed. |
| S3 CI | CI runs without expensive models/providers; reliable build, selected backend and UI tests; failures block merges; native ARM64 suite separate. |
| S4 storage | Read-only byte accounting on sample project and checkpoints; identity-aware retention proposal; zero deletions by the reporting step. |
| M1 hygiene | Exact tracked Graphify consumers audited; proposed generated cache untracking excludes source/skills/contracts; Git diff confirms zero product code or data deletion. |
| M2 seams | Characterization tests before extraction, route/output JSON compatibility afterward, no significant user-visible change. |
| O1 orchestration | One synthetic multi-step analyze→propose→approve→preview→render→verify path survives restart and stale revision, cancellation, pending external mutation, and missing backend; no self-approval. |
| E1 Kdenlive | Actual desktop project round-trip plus multi-clip/fps/audio tests before claiming richer control; current two-clip MVP stays supported. |
| E2 native | Real pinned native UI round-trip for each added edit type, safe typed import and revision rejection. |
| F1 film | Opt-in owner scenario with quality notes, recovered jobs, retakes, soundtrack, output checks, and verified final film; no creative-quality claims from codec probe alone. |

## 6. Reporting template — required every test batch

```text
Run ID / date:
Branch + HEAD:
Pre-existing dirty paths (unchanged):
Hardware / Python / Node / FFmpeg / MLT / installed runtimes:
Scope / safety exclusions:
Command:
Result: PASS | FAIL | SKIP | BLOCKED
Counts: passed / failed / skipped; exit code; duration:
Failure classification + reproduction (if applicable):
Real evidence: MOCKED | CPU | NATIVE | GPU/PROVIDER | OWNER:
Media/job ownership and temporary cleanup check:
Source changes: none | exact paths and reason:
Next action / gate:
```

Do not turn a failing test green by weakening assertions or quietly altering test inputs. Any test fixture correction must be justified against production contracts and include before/after output. A **blocked** command must stay visibly blocked until the missing runtime/dependency is supplied. Do not mark a milestone DONE based on a documentation-only update.
