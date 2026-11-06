# Focused tests and disposable fixtures

Read the approved [card](../../../fixes/QUICK_FIX_TASKS.md). Run matching tests once; expand for failures or a traced dependency. Do not run every generation/assembly suite for a metadata/doc change.

## Source-known baseline

At `f48e99a`, the prior review ran six audio integration tests: five passed and the safety-trip asset-set test failed because browsing discovered staged `001.wav`. Real CPU MP3 extraction passed. Do not turn that failure green by changing its expected set. Q01 fixes discovery. Typecheck and V2 package validator passed in that review; they do not prove live readiness. This guide edit does not rerun those application checks.

## Test selection

| Card | Focused tests / new tests only when implementation lands |
| --- | --- |
| Q01 | Existing `test_audio_utilities_integration.py`, `test_media_catalogue.py`; add precise project/tool-library staging exclusion cases |
| Q02 | Audio integration: all operations/API errors, staging failure, retained retry inputs, configured roots and CPU registration |
| Q03 | New `test_agent_tools.py`, `test_agent_api.py`; selected existing API route smoke regressions |
| Q04 | New `test_agent_skills.py`; old Director/Editor context parity, references, hashes and safe roots |
| Q05 | New `test_agent_project_graph.py`; actual source identity, owner isolation and no state writes |
| Q06 | `npm run typecheck` in frontend; focused browser tests with mocked discovery; direct routes/project switching/no submission |
| Q07 | New `test_agent_tasks.py`; existing `test_projects.py`, `test_named_project_storage.py`; crash/approval/idempotency/roundtrip |
| Q08 | New `test_agent_editor_tool_handoff.py` plus Director bridge tests; CPU synthetic media, ownership/retry/attachment and old Editor approvals |

Discover Editor tests by source references rather than inventing an existing test filename. For later generation-contract work inspect actual `test_isolated_*_contract.py`, continuity, worker collection and assembly tests when their code changes. Mock GPU/provider paths first; paid/GPU acceptance requires explicit authorization.

## Commands and isolation

For the already inspected audio tests, from repo root:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend python3 -B -m unittest story_builder.tests.test_audio_utilities_integration
```

Those tests own temporary data roots and mock GPU/container execution; FFmpeg extraction is real CPU work. Before running any other suite inspect fixture roots, environment variables, worker launch and provider mocks. Test env overrides such as `VIBE_DIRECTOR_IMAGE_JOBS_DB` can defeat intended isolation; do not inherit a live override. Use installed runtime dependencies; report missing dependencies, do not install arbitrarily.

Each test owns a unique TemporaryDirectory and isolated DB/project/global-skill fixture roots. Configure ALL module-global job/ledger roots, not merely the helper's root argument. Restore prior globals/environment after tests. Synthetic WAV/PNG/short MP4/text only; build an audio stream when the target contract requires it. External worker tests require ownership-tracked process shutdown before deleting their root.

Cleanup must run and be verified after success AND failure. In unittest register a root-existence verifier before registering cleanup (cleanups run LIFO), or use an outer finally that checks the directory after the TemporaryDirectory context exits. Plain assertions after a failing test body will never execute; do not call that failure-path cleanup proof. Never mask the original failure with cleanup errors; report both.

Keep source tests; remove generated media/test DBs. A removed isolated DB removes its test records; never issue cleanup DELETEs against production. No broad recursive deletion of user paths. If ownership is uncertain, report a leftover rather than delete it. New tests should include one injected failure proving cleanup still runs.

Report exact commands, pass/fail/skip counts, no-run limitations, temporary root removal and any remaining owned processes. Mock, CPU media and owner-started GPU acceptance are different evidence.
