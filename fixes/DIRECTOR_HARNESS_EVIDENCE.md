# Director harness evidence — 2026-11-09

## Scope and state

Branch `vibe-director-current`, HEAD `cd6f623` (documentation over source baseline `0550814`). Pre-existing dirty path: `backend/story_builder/tests/test_agent_tool_access.py` (earlier H0 characterization); retained and extended. No production application code or storage migrations changed. No production restart, owner-media modification, paid media generation, GPU generation or owner render. Bounded signed-in Codex reasoning turns were explicitly authorized and used for H1.

Read `DIRECTOR_HARNESS_P0.md` completely. H0 diagnosis is reproduced; baseline is **not green**. H1 persistent-agent compatibility is demonstrated below; its complete security gate remains **open**. H2 onward not started.

## H0 actual commands/results

Run from repository root with `PYTHONPATH=backend` and `/home/riki/miniforge3/envs/react/bin/python`:

- `-m unittest story_builder.tests.test_reasoning_provider story_builder.tests.test_agent_tasks story_builder.tests.test_agent_tools story_builder.tests.test_agent_tool_access story_builder.tests.test_editor_kdenlive story_builder.tests.test_editor_preview story_builder.tests.test_video_overlap`: **48 tests, 46 passed, 2 errors**, 47.405s, exit 1. Errors: `KdenliveTests.test_real_mcp_agent_to_preview_approval_render_and_export` and `test_silent_sources_prepare_without_synthetic_audio`; native MCP returns `McpError -32000: Connection closed`. Do not infer missing ARM64 support from this transport error; underlying runtime cause remains undiagnosed. Other tests use mocks and disposable real CPU media as implemented in their fixtures; native Kdenlive acceptance failed.
- After adding schema regressions, `-m unittest story_builder.tests.test_reasoning_provider`: **9 passed**, 0.095s, exit 0. Mocked CLI only: optional generation settings, arbitrary nested tool settings, invalid response rejection and JSONL provider failure covered. No live model acceptance implied.
- `-m unittest story_builder.tests.test_agent_tool_access.ToolAccessTests.test_current_chat_stops_after_first_task_of_multistep_request story_builder.tests.test_agent_tool_access.ToolAccessTests.test_unfinished_five_clip_goal_reaches_verified_output_without_second_message`: **2 run, 1 pass + 1 expected failure**, 2.295s, exit 0. Real existing media-list adapter/task/ledger execution over disposable WAV; provider and dispatch mocked. Exact five-clip goal produces only one task and one reasoning call after the task completes. Expected failure explicitly records the absent continuation/output; this is not five-video/render/browser acceptance.
- `test_agent_conversation.py` does not exist; excluded explicitly. A prior discovery attempt selected it incorrectly and reported one import error; corrected baseline above does not include it.

Frontend: `cd frontend && npx playwright test tests/director-runtime.spec.mjs tests/editor-visual.spec.mjs tests/clip-join.spec.mjs`: **34 run, 27 passed, 7 failed**, 2.4m, exit 1. Existing API-mocked browser fixtures; proxy pinned to `127.0.0.1:1`, not owner backend. Seven failures in director-runtime: line 44 Apply prompt missing; line 109 old-backend error expectation; line 322 both video/editor extracted-frame image missing; line 411 previous-session-history click intercepted; lines 625 and 660 Browse media sources not found inside expected work surface. Native Studio/owner playback not established. Test diagnostics remain under `/tmp/vibe-director-playwright-results`; no production media created.

AgentTaskFixture and overlap fixture teardown remove disposable media/databases and assert directories absent, including failures. Isolated protocol/schema probes also verified temporary-directory removal. No cleanup assertion failed. `git diff --check` passed.

## Source cause

`AgentConversation.send` performs one reasoning call, proposes at most one task, persists `answered`, and returns history. `agent_tool_routing.context` reads previous task evidence only for a later send. `DirectorRuntime` polls/updates tasks but does not resume the objective after completion. Completing `media.list` therefore cannot satisfy or continue an assembly goal. Existing exact-plan approvals remain authoritative; characterization manually approves only a disposable read task.

## H1 installed runtime

- Host `aarch64`; project Python 3.12.13 (default shell Python 3.13.13); Node v22.23.1; FFmpeg 6.1.1; Flatpak 1.14.6; host melt present. No packages installed.
- Codex CLI 0.167.0; `codex login status` reports ChatGPT login. Credentials were never printed; live probes copied only auth.json into a private disposable CODEX_HOME (0600), removed in finally. No owner configuration, MCP registrations, plugins, hooks or skills were copied. Python MCP and Agents SDK packages absent in project environment; this alone is not an app-server incompatibility.
- `codex app-server --help` succeeds. `generate-json-schema --experimental` generates 470 schemas, including thread start/resume and turn APIs, then temporary schema directory is removed.
- Real stdio app-server `initialize` succeeds with an isolated temporary `CODEX_HOME` and bounded environment. Response identifies version 0.167.0 and Linux/aarch64; process terminated and directory removal verified. No model turn started.
- Official protocol documentation consulted: https://learn.chatgpt.com/docs/app-server . Thread resume and streamed events are documented; `thread/shellCommand` is explicitly outside the thread sandbox. Any future host bridge must never expose that endpoint to model/MCP/browser clients. Documentation is not measured authorization evidence.
- Owner API read-only status: local pending=0/active=0, attention=2; Comfy running=0/pending=0. Existing services left running.

### Real model and MCP acceptance

The owner authorized bounded Codex account reasoning turns. Probe command:

`PYTHONPATH=backend /home/riki/miniforge3/envs/react/bin/python -m story_builder.tests.harness_probe --live-account`

Official app-server 0.167.0 / gpt-6-luna, isolated persistent thread `01a1bfcb-3b65-7fe3-af10-338558b21e9b`:

- Initial turn: **three actual sequential MCP calls**, `media_list → media_inspect → editor_propose_session`, completed in 34.160s. Read calls used existing AgentTasks, ledger, workspace adapters and real subprocess CPU Media Prep jobs. No mocked tool result. The model used the returned asset ID and reported measured 0.3s audio duration and exact source SHA-256 `1abc382caecf8e3c86c758feb1a74af366d82827ec5ffbadc96c4141e80abdf4`. Stream contained 259 agent-message delta events. Session proposal remained a draft; it did not create an Editor session or render.
- A second inspection turn was interrupted after its actual MCP call started (host-controlled delay before dispatch), status **interrupted**, 4.093s. Only probe-owned app-server/MCP processes were stopped.
- A new app-server process resumed the **same thread** and history. An internal recovery turn used `input=[]` plus application context; saved user-message count was unchanged. It inspected the same asset through MCP, consumed its measured result, and finished in 16.353s. No second user message was required for recovery.
- The existing task database still contained exactly one Editor proposal, revision 1, **draft/unapproved, invocation absent**, across restart. This demonstrates pause/persistence, not human-UI approval or recovery of a protected external effect.

Read execution used an explicitly configured **test-host read policy** invoking existing exact-plan approvals. MCP exposed no approval endpoint. The app-server's transport approval for the three allowlisted tools does not approve Vibe plans. Draft/write proposals never use that read branch.

### Negative checks and cleanup

`... -m story_builder.tests.harness_probe --offline-boundary` passed twice with a real initialized app-server and real MCP transport, without a model/account turn. **Seven requests rejected**: unknown shell, approve and fetch tools; foreign asset; owner override; filesystem-path injection; proposal argument `approve=true`. Latest thread `01a1bfcf-610c-7ed3-b4fb-82085d0fa50f`. Output: `DENIALS 7 real MCP requests rejected`, `SOURCE unchanged`, `CLEANUP verified`.

Three offline unit tests additionally cover unknown/destructive tools, extra shell/path/network/owner arguments, foreign IDs, changed source hash before dispatch, unapproved execution, tampered approval hash and durable unapproved proposal with zero approval records.

The probe sanitizes child environment, isolates configuration and authentication, disables shell/browser/computer/web-search/image tools and plugins, restricts MCP to three schemas and fixed test owner, rejects incoming host escalation requests, and configures root-deny/read-only-workspace/network-disabled permissions. gpt-6-luna requires its `code_mode_host` tool-routing runtime; disabling it made MCP unavailable. That router is retained; it is not a generic terminal endpoint.

**Security limitation / H1 blocker:** model statements about unavailable filesystem/network are not enforcement evidence. Gateway rejections above are actual evidence, but direct native OS filesystem/network sandbox escape attempts were not independently exercised. A separate sanitized `codex sandbox linux --help` diagnostic failed before execution with `error building bubblewrap command: app-server socket directory must be a user-owned directory with mode 0700`. This does not prove app-server incompatibility or a vulnerability. Resolve/verify that boundary before treating H1 as fully passed or switching production. Prompt-injection metadata, inherited-secret sentinels, browser approval bypass and protected crash-after-submit recovery remain unverified; later H3/H4 gates must cover their applicable cases.

Every probe uses finally cleanup: close owned process group, reconcile/stop only workers matching disposable job IDs, verify synthetic source hash, remove temporary credentials/history/database/media, assert directory absent. All completed probe cleanup assertions passed. No owner service was stopped or restarted. Playwright failure diagnostics (not generated media) remain at the H0 path above.

### Bounded attempt diagnostics

- Restricted-network attempt failed routing discovery with retries, zero calls; cleanup passed.
- Enabling network for the authenticated app-server transport (not agent tools) allowed account reasoning. `code_mode_host` disabled: model completed but zero tool calls; **not a pass**.
- With code-mode routing enabled but MCP transport approval unset, `media_list` was denied because approval policy was never; **not a pass**. Corrected only the three explicit tool transport grants, preserving Vibe task approval.
- A first three-tool sequence then passed in 21.404s; the separate full restart run above passed afterward. No fallback SDK was installed or tested: no primary compatibility blocker has been established. Native security verification remains a gate, not grounds for enabling full access.

### Latest focused regression

`PYTHONPATH=backend /home/riki/miniforge3/envs/react/bin/python -m unittest story_builder.tests.test_director_harness_probe story_builder.tests.test_reasoning_provider story_builder.tests.test_agent_tasks story_builder.tests.test_agent_tools story_builder.tests.test_agent_tool_access`

**39 run: 38 passed, 1 expected failure**, 32.885s, exit 0. The expected failure is the original unfinished goal; it has not been fixed. H0 Kdenlive and seven mocked-browser failures remain open; focused passing tests do not establish whole-app health.

### Impact and next gate

Changes are opt-in test probes, regressions and documentation only. Existing production APIs, task/job storage and approval contracts are reused without modification. No frontend interactions changed. Graphify was refreshed with the mandated command; its incremental graph has partial coverage and ambiguous generic method edges, so manual source tracing remains authoritative. Review evidence is in `.review/director-harness-h1-impact.json`: 27 source anchors verified, zero rejected. Maximum probe-node prioritization risk is 0.60 (high: credential/authorization helper); this is not a production vulnerability finding. Final filesystem/process check found zero `/tmp/vibe-h1-*` directories and zero probe process matches. `git diff --check` passed.

Next: independently verify the native security boundary and remaining H1 safety cases, then H2's bounded production coordinator/driver slice. H2–H6 are **not implemented**. No real five-video assembly, human UI approval, protected render recovery or browser playback acceptance is claimed.
