# P0 — Codex-like Vibe Director harness: implementation and acceptance

**Written:** 2026-11-09. **Source baseline for diagnosis:** `vibe-director-current@05508145fe049214f0f83ac45b1164748920dd4d`. This is an executable **plan**, not proof of implementation. Start from current HEAD, existing user dirty state, `AGENTS.md`, `fixes/ACCEPTANCE_TESTS.md`, then the touched production source. Do not reset the user's local checkout.

## 0. Why this is the first priority

Observed owner request: **"Use clips 2 through 6 in proper sequence, stitch them into one video, then open the result here."** Vibe completed `media.list`, exposed a very large raw metadata blob and stopped. The earlier Codex JSON strict-schema failure was patched separately; it did not make the Director an agent.

Source-confirmed failure at 05508145: `reasoning_provider._codex_json` calls `codex exec --ephemeral` for **one-shot JSON reasoning**; `agent_conversation.AgentConversation.send` runs a single reasoning call, proposes at most one task, writes a response and returns. `agent_tool_routing.context` exposes **previous** completed results in a *future* chat message. No durable goal/turn-level tool-observation → next-tool loop runs. `agent_tasks.AgentTasks` already handles typed plans, exact approval, frozen input hashes, dispatch, poll/recovery, and must remain authoritative. The UI may label a media-list task complete even though the **user goal** is incomplete. The existing Kdenlive adapter only does a two-clip join at 1080p30. Current HyperFrames Editor accepts multiple ordered clips but requires approval and a saved plan. These are separate issues: **harness continuation, truthful goal state, five-clip editor backend, and accessible playback**.

**Success criterion:** a user request becomes a persisted objective. The agent discovers real sources, resolves/storyboard-checks 2→3→4→5→6, prepares an exact ordered edit, presents a **human approval** of actual changes, executes only approved operations, survives restart and failures, verifies A/V output, and opens a playable video in the Editor without another user prompt. Raw FFprobe payloads stay behind an expandable diagnostics panel. A pause for human input is not “completed”.

## 1. Harness decision gate — do not rewrite existing services

**Primary candidate: Codex app-server** from the official `openai/codex` distribution. It supports persistent threads/turns, structured streamed events, tool access via MCP, resume and app-controlled approvals. Use the app-server product protocol for a Vibe Director GUI. Use official `@openai/codex-sdk` only for a bounded local spike if the protocol is easier to establish there first; do not mistake `codex exec --ephemeral` for a persistent harness.

**First compatibility checks (on the owner ARM64 host, no production project changes):**
- Installed Codex `codex --version`, `codex app-server --help`, protocol/feature support, authenticated model, account usage and process restart.
- Local disposable-project thread start / turn / streamed events / resume; **real** two-tool continuation without prompting a second user message.
- Locally registered stdio MCP tools with strict JSON schemas, tool results flowing back into the same running turn. Determine actual app-server approval notifications, host response contracts and capability controls from the installed version.
- Restrict work directory to disposable project, deny unrelated filesystem, arbitrary shell, package installation, network and privileged endpoints; validate both allowed and denied operations. The tool-call authorization boundary **must** be Vibe's backend, not only a model prompt.
- If Codex cannot be safely constrained to Vibe-owned tools or resumed with host-enforced approval on this build, **stop and document that specific blocker**. Do not enable full access to get a green demo.

**Fallback 1: OpenAI Agents SDK (Python)**, which natively supports tool loop, sessions, human review, MCP, tracing and guardrails. Wrap existing Vibe task services as function tools or tightly allowlisted MCP tools, and use the current durable job ledger for side-effect state. **Fallback 2:** LangGraph/PydanticAI Harness only if explicit durability/HITL tests favor it; avoid adding multiple orchestration runtimes. OpenHands is a potential research reference, not a default dependency, because it is oriented around broad software tools rather than project-owned media tasks. Record pin/version, ARM64 dependencies, license, source audit, test results and why the selected harness won.

**Do not run all choices in production.** One harness adapter with one owner-owned state machine, interchangeable engine driver, no duplicate Director chats or project stores.

## 2. First phase: tests/reproduction *before implementation*

1. Record branch, HEAD, dirty paths, active jobs, Python/Node/Codex/FFmpeg/MLT/Flatpak versions; no restart until existing jobs finish.
2. Characterize current `agent_conversation.send` with a fake provider selecting `media.list`; assert exactly why no follow-up is scheduled; record the **known failing goal** in a dedicated test, rather than weakening existing unit tests.
3. Regression on strict response schema: optional `generation_settings` and nested arbitrary tool settings; mocked CLI JSONL failure; actual Codex smoke request **only when the owner authorizes model usage**. Verify changed backend version is the one receiving requests; distinguish installed code from stale running process.
4. Record exact baseline for `test_reasoning_provider.py`, `test_agent_conversation.py` if present, `test_agent_tasks.py`, `test_agent_tools.py`, `test_agent_tool_access.py`, `test_editor_kdenlive.py`, `test_editor_preview.py`, `test_video_overlap.py` and corresponding `director-runtime`, `editor-visual`, `clip-join` Playwright. Inventory filenames and fixture effects first; skip missing modules explicitly. Categorize tests as mock / real CPU / native / GPU / owner.
5. Add a **red** goal-level test: `media.list → resolve ordered five assets → editor session → select ranges → prepare sequence → await owner approval → run render → verify → expose player`. Tool lookup alone must not satisfy the goal.

**No feature code change during baseline.** No GPU, paid provider, owner-project renders or broad test sweep by default.

## 3. Target architecture — retain application ownership

```text
One Director composer (current UI)
  ↕ goal / event stream / approval requests
Vibe Host GoalController (SQLite durable goal + step ledger)
  ↕ Codex app-server adapter [fallback Agents SDK]
  ↕ project-scoped, typed MCP gateway / function tools
  ├── media.list / inspect / source-order resolver [read]
  ├── Editor session and selected-range proposals [draft]
  ├── timeline.prepare_ordered_sequence [draft]
  ├── overlap comparison / speech / frames [read, if requested]
  ├── preview / render using existing approved plans [protected write]
  ├── job status / verify / registered artifact [read]
  └── optional Playwright UI observation [restricted, not authority]
Existing Vibe task/approval/jobs/media/services remain authoritative.
```

Implement **one** runtime coordinator service (e.g. `services/director_harness.py`) plus a narrowly scoped Codex driver (e.g. `services/director_codex_bridge.py` or isolated Node helper where necessary). A separate Vibe MCP stdio server is optional but preferred if Codex must discover callable tools dynamically. It must call the **existing validated application services**, not duplicate business logic or expose an unaudited generic HTTP/shell proxy. Codex's global user MCP config is **not** the Vibe runtime tool permission list.

### Durable goal state

Suggested typed structure:

- `goal_id`, owner workspace, source message request ID, conversation/thread ID, engine ID + version.
- `original_goal`, source-selection evidence and unambiguous ordered asset IDs + hashes; selection/storyboard and Editor revision snapshot.
- Steps with input/output schema, dependency IDs, task ID, idempotency key, effect classification (`read` / `draft` / `protected_write` / `external`), provenance and verified result digest.
- `status`: `planning | running | waiting_for_approval | waiting_for_clarification | waiting_for_job | recovering | completed | failed | cancelled`. Partial tool success NEVER means goal complete.
- `next_step`, saved tool receipt, last trustworthy observed event, error/retry budget, no-duplicate external invocation key, final verified artifact locator.

Persist transitions transactionally under the existing project/ledger locking conventions. Store large media metadata/evidence by ID and checksum with bounded summaries in model context; do not store giant JSON in chat or replay entire FFprobe blobs. Restart must rehydrate the same `goal_id` and agent thread; do not submit new GPU or external jobs merely because the process restarted.

### Minimal agent loop (semantics, not arbitrary code execution)

`observe(goal) → plan/choose next tool → validate & authorize → execute or pause → observe result → replan → ... → verify original goal → finish`.

Stop reasons are explicit: `goal_satisfied`, `approval_needed`, `clarification_needed`, `runtime_blocked`, `budget_limit`, `cancelled`, `failed`. Cap step count, wall-clock, context and tool-result bytes; persist a compacted summary with provenance; report blockers rather than claim success. Human approval and tool completion are distinct events.

**Approval ownership:** Never expose `approve`, `grant`, `overwrite`, `delete`, `full_access`, or `run_without_approval` as model-callable MCP functions. Read/draft tools may proceed under a configured plan; protected writes must pause on Vibe's explicit exact-plan review. The human UI supplies an unforgeable authorization not present in the agent/MCP/browser environment; backend revalidates project/revision/hashes right before the effect. One pending approval cannot be reused after source or plan changes. Keep Editor's creative-brief clearance and media/tool-plan clearance; do not substitute a generic Codex approval for them.

## 4. MCP and browser policy

- **Vibe MCP (first):** verified, typed project-scoped `media.list`, `media.inspect`, `editor.prepare_timeline` and `job.status` adapters. Prefer immutable asset references and short JSON results, not raw absolute paths. Wrap application APIs, never bypass them.
- **Kdenlive MCP:** maintain the existing pinned, authorized, two-clip adapter; add multi-clip support only as a separate tested contract. Refuse unsupported transitions/retiming/audio. Do not present a synthetic renderer as Kdenlive.
- **Playwright MCP (later, optional):** official Playwright MCP permits accessibility-snapshot browser navigation and interaction. Use it primarily for **UI acceptance testing** and optional restricted read-only in-app browsing/previews. It is **not** the editing engine, not a desktop automation agent for Kdenlive, and not a way to click approval buttons. A separate test/browser identity must have no approval credentials or ability to make protected writes; allow only app loopback with URL/host allowlisting. Tests should assert the model cannot grant itself approval via browser clicks, JS injection, alternate HTTP endpoints or tool output.
- Native GUIs may be linked/opened through existing safe Vibe workspace adapters. Do not promise Playwright controls a Qt/Flatpak desktop window.
- Test MCP prompt injection, tool-argument tampering, cross-project access, stale hashes, malicious filenames/metadata and parent-env secret inheritance. Browser page text and media metadata are untrusted data, not agent instructions.

## 5. Five-clip assembly vertical slice — first real benchmark

**Request:** "Use clips 2–6 in proper sequence, stitch them into one video and open it here."

1. Discover current project and candidate clips. **Do not equate `media.list` sort order or dates with story order.** Resolve 2/3/4/5/6 via explicit scene/shot/clip metadata, saved plan or existing user selection. If still ambiguous, show 5 thumbnail/name/duration cards for one targeted confirmation; no invented ordering.
2. Inspect registered media and hashes; record exact five asset IDs and source-relative ranges. No implicit 0–5-second truncation. Default **use full clip and source audio**, unless user chooses cuts/transitions/overlap detection. Detect format differences and preview settings.
3. Prepare/edit one versioned five-clip ordered timeline through the existing Editor `editor.prepare_timeline`/HyperFrames pipeline **when accepted as the intended backend**. If user explicitly requires Kdenlive, don't substitute HyperFrames; implement Kdenlive multi-clip adapter separately, retaining approved semantics. Keep original 1344×768/24fps where supported; if conversion is necessary, show proposed profile rather than silently forcing 1080p30.
4. Display a concise review: five ordered thumbnails, filenames, durations, audio policy, cut/transition list, target resolution/fps, estimated duration, selected engine, output path, source hashes, **Approve plan / Reject / Edit**.
5. On true human approval use only the frozen exact Editor plan; enqueue once; stream job stage, progress and controllable cancellation; on crash recover/reconcile rather than re-dispatch uncertain work.
6. Run actual CPU FFmpeg/HyperFrames or verified MCP render with synthetic fixtures. `ffprobe` asserts video and expected audio streams, duration equals planned content within frame/sample tolerance, first/middle/last and each of four boundaries have expected color/timecode patterns, exact order and no skipped/duplicated sections. Verify file decodes, source hashes are unchanged, registered result points at bytes and correct project.
7. Route into Vibe Editor's **immediate playback surface**, set final `<video controls>` source to registered content URL, test play/pause/seek/audio. User can open Visual Editor/HyperFrames Studio without having to complete a creative brief merely to inspect source video/audio; editing still requires normal approvals.
8. Emit result: "Stitched 2→3→4→5→6, preserved audio, [duration/profile], verified [result ID]; open in Editor." Only claim success after verified output. Show link/player, not giant media catalogue JSON.

**Synthetic fixture matrix:** five 2–4s distinct tagged video+audio clips; source-native and mixed FPS; duplicate frames; one audio-less clip; missing/stale asset; reversed list order; out-of-order story labels; ambiguous naming; changed hash after approval; two-tab conflicting revision; cancelled render; delayed background job; backend crash before/after submit; user rejects; different width/fps; runtime missing; destructive tool denial; prompt-injection metadata. No owner data or GPU required.

## 6. UI must look and behave like a working agent

- In existing central conversation show human-sized events: **Planning**, **Examining clips**, **Building edit**, **Needs your approval**, **Rendering**, **Verifying**, **Ready to play**. Each event links to one `goal_id` and exact step; no duplicated chat.
- Tool results: compact summary by default. Diagnostics/FFprobe JSON behind an accessible disclosure, with sanitization/redaction. No misleading generic "Review before using" for a completed read-only lookup.
- A persisted "Continue / Retry failed step" button resumes **the same goal** and re-checks side effects. Never require user to repeat original objective after a benign interrupt.
- Preview source media visible on opening Vibe Editor even without saved timeline. Open Visual Editor/Studio from that surface when an actual compatible composition is present; show honest empty-state/limits otherwise. No hidden prerequisite just for audio/video playback.
- Approval card displays exactly what will change and what runs, with human reviewer action and source revision; agent can suggest but not click/auto-approve.

## 7. Gates, tests and no-regression policy

| Gate | Must pass before continuing |
| --- | --- |
| H0 baseline | Current tests/status observed, source bug reproduced. No code changes or owner media. |
| H1 harness spike | Codex app-server (or named fallback) proves **two consecutive real tool calls in one turn**, retained context, event stream, restart/resume, and no unauthorized shell/filesystem. Tests use disposable workspace; record exact CLI/SDK version. |
| H2 Vibe handoff | Goal→agent→MCP→existing task/approval/job state; no duplicate database or permissions; no raw JSON flood; rejects missing runtime. |
| H3 approvals/recovery | Approval cannot be bypassed from model, MCP, Playwright, cross-tab or stale token; pause, cancel, crash-before/after-external-call, idempotence and rejection pass. |
| H4 five-clip edit | Synthetic **five clips**, exact order, linked audio, source byte identity, actual CPU render and FFprobe/decoded boundary checks; preview available with no extra prompt. |
| H5 GUI | Real browser Playwright test without API mock shows media preview on arrival, named clip cards, approval, job progress, playable final and restart reconciliation. Native Studio and Flatpak Kdenlive each have separate owner acceptance; do not infer from mock. |
| H6 owner acceptance | Opt-in one owner-project 2–6 sequence, manually verified order and audio, no surprise media deletion/overwrite/provider spending. Only then call the user-request workflow complete. |

Backend focused paths: `services/reasoning_provider.py`, `agent_conversation.py`, `agent_tasks.py`, `agent_tool_routing.py`, `agent_tools.py`, `agent_api.py`, `vibe_editor.py`, `vibe_editor_render.py`, `editor_kdenlive.py`, `media_library.py`, `projects.py`. Frontend: `DirectorRuntime.tsx`, `DirectorConversation.tsx`, `VibeEditorPage.tsx`, `EditorVisualTimeline.tsx`, `ClipJoinReview.tsx`, `NativeWorkspace.tsx`. Add `test_director_harness.py`, `test_director_harness_approvals.py`, `test_director_five_clip_assembly.py`, and `frontend/tests/director-harness.spec.mjs` (or existing-test extension) **only where aligned with repository conventions**.

Validation must show independent raw results: command, test counts, mocks vs **actual** app-server/MCP/FFmpeg, output hash, A/V decode, failure logs, cleanup, saved state after process restart, remaining limitations. Never mark pass because a test function exists or README claims it. Record frontend build and regressions around Story/Screenplay/Media/production jobs. Do not weaken tests or alter owner files to make baseline green.

## 8. Implementation batches (one bounded commit each)

**H0** baseline/reproduction and red goal-level test → **H1** app-server isolated probe and choice record (no production switch) → **H2** project-bound engine driver + goal/step ledger + allowlisted MCP → **H3** approval/recovery/stream UI → **H4** ordered five-clip timeline and verified render → **H5** accessible Editor playback and real browser evidence → **H6** owner acceptance. First operational demonstration requires H1–H5; document any blocked native tool as a blocker, not a pass.

Do not use a 100-file commit to implement the full loop. Leave legacy one-shot provider available as a **fallback for non-agent chat** until the new harness passes end-to-end, protected by a feature flag. Preserve old transcript/conversation records and existing project/job interfaces; plan migrations/backups before ledger schema work. Avoid new React major versions and changes to ComfyUI, GPU clocks, service ownership or native editor pins.

## 9. Codex task instruction

Read this plan and the current `fixes/ACCEPTANCE_TESTS.md`. **Start H0, not H4.** First show the reproduced one-shot failure and test baseline. Next prove the official Codex app-server + Vibe-local MCP + Vibe-owned approvals inside a disposable workspace. Implement a typed, persisted agent goal loop, not another prompt that says "keep going." Test the exact five-clip 2–6 objective with real CPU media and browser playback. Keep approval control human-owned. Update `fixes/ACTIVE_FIXES.md` with actual evidence and blocked items after each tested batch. No new filmmaking feature work until this P0 flow passes.
