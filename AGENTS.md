# Vibe Director

Work directly in this checkout. Follow the current user request; do not create handoffs, collaboration ledgers, model-role assignments or recurring review schedules. Do not spawn agents unless explicitly requested.

Read only the source, tests and documentation relevant to the task. `audit/FUNCTIONALITY_AUDIT.md` maps current components, preservation contracts and review findings; consult the relevant section when redesigning. `plans/editor_media_output_ace_plan.md` contains the latest requested Editor/ACE changes. Neither document proves live runtime readiness. Current source and user instructions supersede historical proposals.

Preserve shared asset identities, original media, saved sessions/revisions, frozen requests, durable jobs, cancellation/retry behavior and verified output publication while redesigning. Simplifying output-folder controls does not require removing internal session/asset ownership. Keep existing engines and adapt the smallest necessary seams.

The app reads `skills/vibe-director/SKILL.md`, `skills/video-prompting/` and `design/vibe-editor/skills/vibe-editor-director/SKILL.md`. Preserve their supporting references. Check source licenses before copying third-party code; keep license notices. Models, secrets, user media and runtime environments are not repository content.

Use focused tests for changed behavior. Mocked tests, CPU validation and real generated-media acceptance are different evidence. Do not start paid/provider or GPU generation as an incidental check. Preserve shared GPU admission/watchdog and provider execution guards; the configured cutoff is 90°C and clock ceiling 2100 MHz. Do not change clocks. Prepare new workflow acceptance for the owner's Generate click unless the user explicitly authorizes the run.

For substantial changes, trace callers, persisted data and downstream consumers in source; use the local Graphify graph as a discovery aid and check its coverage. Refresh it after meaningful code changes with `conda run -n react graphify extract . --code-only --no-cluster`. Verify changed UI interactions with available browser tooling and report concrete limitations. Run relevant checks once; broaden them when failures or unresolved risks justify it.

Run/setup commands are in `README.md`. Keep work local unless Git publishing or external communication is explicitly requested.
