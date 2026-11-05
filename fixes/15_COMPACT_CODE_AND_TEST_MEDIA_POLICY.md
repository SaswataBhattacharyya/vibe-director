# Implementation quality and disposable test-fixture policy

## Code quality (mandatory)

Build the smallest coherent change per phase. Favor typed adapters, small modules, pure logic and clear service boundaries; route UI and agent actions through the same backend contracts. No giant new agents, no massive React page or HTTP dispatcher rewrites, no duplicate generation API, no speculative abstraction, no unused dependencies, no hidden background polling with lost ownership. Extract reusable helpers instead of appending hundreds of lines to large existing files. Name code to reflect actual operations. Prefer explicit errors and typed results over generic catches, `any`, silent fallback and magic strings. Follow current lint/format/test patterns; add targeted comments for non-obvious safety/state edges only.

**Plan the file boundaries before editing**: for each slice list new/changed files, interfaces, migration, rollback, tests and expected size/complexity. Respect existing `StudioShell` navigation, Media Prep operations, editor render validation, project storage, immutable job requests, media hashes and GPU watchdog.

## Test inputs: disposable synthetic media only

All artificial test stories, prompts, images, video and audio must be generated and used as **temporary test fixtures** and removed once tests finish. Tests may use generated plain text/Markdown, small PNG images, short MP4 video and WAV/MP3 audio using available local libraries/FFmpeg; no third-party copyrighted samples or user originals. Prefer mocks/unit tests and CPU integration, then carefully scoped live tests if explicitly approved. Never submit expensive GPU/model/provider work in routine test runs.

Required fixture lifecycle:
1. Create a unique isolated, test-owned root via system `TemporaryDirectory`/equivalent under allowed temp/test locations, with prefix e.g. `vibe-agent-fixture-` and a per-run marker/manifest.
2. For test database/media operations, use an isolated test ledger and library OR a clearly namespaced temporary test project with safe API cleanup. Never write fixtures to the user's live `Lion_mouse` project or any real project.
3. Generate media with tiny duration/resolution where possible. Tag all created assets, tasks/jobs, project IDs and paths in a test-owned manifest.
4. Use `try/finally` or test framework cleanup hooks. If tests fail, still remove test-created media, staging, output and metadata through authorized deletion methods; no shell wildcard cleanup outside the test root.
5. Verify the root no longer exists and no test-only media assets/projects/jobs remain in the chosen test state. If cleanup is blocked by a running job, stop/reconcile it safely, report an exact remaining test-owned resource and do **not** delete unrelated data.
6. Keep permanent regression **test source files**, assertions and small fixtures expressed as deterministic code. The temporary generated media outputs themselves are not bundled or left in project folders.

For interrupted test sessions, provide a safe `cleanup-test-fixtures` routine restricted to explicit test markers, allowlisted root and current test-run manifest. It should refuse ambiguous paths or unmarked resources. Keep user originals and historical production job artifacts untouched. Do not promise zero residue if an OS-level crash prevented cleanup: expose and verify safe recovery.

## Test plan per phase

- Static/schema: registry metadata, skill version hashes, role permissions, exact R2V/T2V/FFLF request shapes, prompt length/timing, project graph scope.
- Unit/integration: metadata-only global/project skill search; Editor/Director parity; tool discovery; context switching; plan approval; fake job/retry/reconcile; portable Save/Load.
- CPU media: synthetic frame extraction, MP3 extraction, probe, trim and Editor composition in a temp project; verify original bytes/hash and deliberate cleanup.
- Agent computer/coding: sandboxed read/list, diff preview, small patch/test within disposable worktree; permission denial and audit log; cleanup.
- GPU/live creative checks: separate owner-approved and resource-bounded; use disposable owned media only where safe, never assume automated deletion of accepted user artifacts.

## Definition of done for each engineering slice

Show the exact source diff and files, tests run and results, functional demonstration, any known blockers, fixture cleanup verification, and no changes to unrelated user data. No test success claim without actual executed evidence. Stop after an approved slice and ask before expanding to unrelated phases.
