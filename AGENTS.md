# Vibe Director agent entrypoint

Read `plans/README.md` first. It indexes current product requirements. Read `plans/issue_backlog.md` and the stage plan linked by your issue before designing or implementing. Older `migration_plan/`, `My idea/`, `PLAN.md` and `REUSE_AUDIT.md` are historical evidence; their conflicting journeys do not override current plans.

## Collaboration and source reuse

Use issue-linked branches/PRs. Design issues produce accepted layouts, decisions and API needs; implementation issues require demonstrated behavior. Proposed leads are not exclusive ownership. Do not close implementation work on test counts alone.

Story Builder reference repository: `https://github.com/SaswataBhattacharyya/mooV_E_maker.git`. OpenMontage reference repository: `https://github.com/calesthio/OpenMontage.git`, reviewed commit `9327439db69021ab4b0e2776729bf3b58fdb5a87`. Keep reference clones outside product Git. Host-specific paths in source audits identify inspected material; substitute your local clone path. Confirm selected source versions/differences before extraction and record files, provenance, dependencies and required adaptations.

Use one durable execution service and one shared asset identity/library. OpenMontage covered-source imports require a compatible license decision before copying. Preserve source applications, user media, runtime environments and model storage. Models/secrets/media are not repository content.

## Runtime, provider and acceptance boundaries

- Before authorized generation, inspect the actual ComfyUI graph, nodes, models and runtime; reuse Story Builder `gpu_runtime.py`, `gpu_watchdog.py` and `media_jobs.py` safeguards, including independent monitoring through browser work and recovery. Existing code enforces an 83°C cutoff and 2100 MHz ceiling; 85°C is legacy operator guidance, not the code cutoff. Confirm hardware-specific policy. Never alter clocks.
- For uncovered adapter/workflow acceptance, prepare the exact prompt/settings/references, graph readiness, queue and monitor first, then have the user click Generate. Do not automate submission behind the scenes. This test gate does not change an explicitly user-started Manual/Semi/Full run. Keep mocks explicit and show/reload changed usable UI in Codex from the intended branch/backend.
- Reasoning-provider choices are separate from ComfyUI workflow choices. Codex CLI is the initial end-to-end app completion/acceptance baseline. Do not make OpenCode/direct APIs/flexible models or weaker Ollama/Qwen support completion gates; existing Ollama may remain unchanged. Preserve provider_exec_guard and typed JSON parsing. Defer future providers/models until the Codex app works; validate capabilities per adapter/model because one Qwen/API success does not prove others. App model choices do not change Luna coding delegation.

## Verification and scope

Read the current Manual/Semi/Full rules in `plans/automation.md`; avoid parallel controllers or retired-page navigation. Human-readable screenplay precedes derived production prompts. Direct isolated generation uses the same screens without story prerequisites.

Design and source inspection do not authorize paid/provider or GPU generation. Actual generation checks need bounded authorization and existing runtime supervision. Mocked UI, CPU tests and a real usable render are distinct evidence. Prefer focused producer-to-consumer and recovery checks for the changed behavior.

Keep `plans/HANDOFF.md` concise and current at meaningful milestones: objective, authoritative files, completed evidence, pending work, blockers/permissions and live job/process handles. Runtime compaction follows configured settings; do not invent usage percentages or claim a written handoff compacted runtime context.
