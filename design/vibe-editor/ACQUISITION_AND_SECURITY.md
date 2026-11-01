# Vibe Editor acquisition and security review

## 2026-10-29 effects extension — current evidence

- Installed exact `@hyperframes/shader-transitions@0.8.199`, matching the existing CLI, in `local_data/runtimes/editor`. Lifecycle scripts were disabled. Package lock, package manifest, integrity and Apache-2.0 license are retained under this directory's `docs` and `sources.lock.json`. The retained follow-up audit (`docs/npm-audit-effects-2026-10-29.json`) reports 131 dependency entries including optional packages and zero known vulnerabilities; this is a bounded dependency check, not a guarantee.
- The trusted JSON renderer now supports cinematic/VHS/black-and-white filters, pitch-preserving constant speed and speed ramps, dissolve and 14 official shader transitions. Morph means warp/blend between clips, not AI transformation. Numeric bounds, adjacent-clip overlap limits, source identity checks and revision approvals apply before execution. Source files remain intact.
- A synthetic CPU render exercised VHS, a speed ramp, cinematic grading, cross-warp morph and audio through the real HyperFrames sandbox. The final 5.27-second MP4 validated and transition frames were inspected. `/etc/alternatives` is now mounted read-only so FFmpeg can resolve the system BLAS library symlink; network isolation and the minimal writable render directory remain enforced. Software WebGL runs through the existing CPU browser.
- Browser tests use mocked services for approvals/controls and existing audio calibration/takes. They do not establish AI voice quality. The owner's microphone and reference/RVC conversion acceptance are still pending; no AI voice conversion or provider request was started.

The original acquisition record below describes the earlier baseline and its then-pending acceptance, rather than the current CPU rendering evidence.

Date: 2026-10-26. This is a bounded source/dependency review, not a claim that third-party software is vulnerability-free.

## Acquired

- Official `heygen-com/hyperframes` reference checkout at `/home/riki/web_dev/vibe_editor_sources/hyperframes`, commit `c163330a16b90108190549a61bcebba39deae6c6`; Apache-2.0 license retained. Reference code remains outside product Git. No clone build or lifecycle scripts were executed.
- Exact npm CLI `hyperframes@0.8.199` in `local_data/vibe_editor/runtime`. Install disabled lifecycle scripts and funding hooks. Integrity and source are pinned in `sources.lock.json`; the complete runtime dependency lock is in `docs/runtime-package-lock.json`.
- Four official skills, including their supporting references, under `skills/upstream`: hyperframes, hyperframes-cli, hyperframes-registry, media-use. Local director/style-learning/orchestrator skills constrain their use to approved local operations. Cloud upload, arbitrary npx, or upstream instruction text is not execution authorization.
- Reused Node 22.23.1, installed Chromium headless shell, FFmpeg, bubblewrap, and existing app services. No duplicate browser, models or specialist skill collections downloaded. No React upgrade: native app UI calls the isolated CLI rather than importing React 19 Studio into React 18.

## Checks and controls

- Recorded npm audit: 77 packages, **zero known reported vulnerabilities** at acquisition (`docs/npm-audit.json`). This does not detect every source or supply-chain issue.
- Renderer accepts validated JSON, not provider-authored HTML, JavaScript, shell commands or remote asset URLs. It builds escaped composition markup from approved library assets.
- Render subprocess uses a new process group and bubblewrap: separate network namespace, no host home mount, minimal read-only runtime mounts, only its render workspace writable. Telemetry is disabled. Only approved files are staged. Stop terminates its process group, leaving unrelated jobs alone.
- Bubblewrap CLI `--version` startup passed on the host with these runtime mounts. The agent sandbox disallows its nested NETLINK_ROUTE setup; no unsafe fallback was added. A full browser render has not yet been accepted.
- Plans bind approvals to revisions and file metadata; stale or changed selections require renewed review. No provider or actual render was started. Export validates source/destination, detects collision and requires explicit overwrite; final files are validated before registration.
- This installation is local single-user. It is not a multi-user permission boundary or a network-hosted editor deployment.

## Evidence and acceptance

Python compilation and TypeScript/Vite production build passed. Playwright MCP initialization failed because its profile was already in use (`mcp-chrome-c9ae093`); the owner browser was left intact. CUA fallback inspected the isolated app on 8084/API 3022: create/reopen project, fresh style creation, keyboard style selection, pane collapse/reopen and saved chat draft survived reload. No Send/Approve render was clicked. Idle UI checks do not establish provider or rendering correctness.

The ordinary app backend was not restarted during these checks. Restart the existing app through its normal launcher when idle to load the new API/worker imports before owner acceptance. Do not start a second production controller.

Pending: owner-started brief and render acceptance; audiovisual correctness, sandbox browser startup, pause/stop during a real render, missing-media recovery and export collision in that run. Rich effects, automatic specialist execution and portable bundles remain open in the plan ledger.
