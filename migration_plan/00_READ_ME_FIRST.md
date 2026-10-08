# Vibe Director migration plan

**Date:** 7 October 2026. **Direction:** reuse and reorganize the existing working Story Builder app. This replaces the earlier proposal to start the product from scratch. No product code has been copied or changed during this planning audit.

## Recommended approach

Keep the working React website, FastAPI backend, durable production services, typed ComfyUI adapters, prompts, workflow graphs, and existing tests. Give them a clearer product structure and navigation. Keep the installed ComfyUI engine and model files at their current location. Move code through small, reviewable changes with a compatibility period for existing routes and data.

The two directories play different roles:

| Source | Role | Treatment |
|---|---|---|
| `/home/riki/web_dev/story_builder` | Website, production controller, project data, media tools, workflows, analysis applications and standalone training utilities | Thorough application audit; selectively copy owned application code and preserve its data contracts |
| `/home/riki/web_dev/setup_comfy_and-stuff` | Installed ComfyUI, custom nodes, models and environment setup | Dependency inspection; keep installation in place and reference it through configuration |
| `/home/riki/Documents/ChatGPT/Vibe Director` | Sole new project working directory | Planning now; proposed migration destination later |

## Read these in order

1. [Capability catalog](01_CAPABILITY_CATALOG.md): what can be created, transformed, analyzed and stored; distinguishes integrated features from workflows and standalone tools.
2. [Customer journeys](02_CUSTOMER_JOURNEYS.md): directing modes, making routes, approval loops and specialist workflows.
3. [UI and routes](03_UI_AND_ROUTES.md): navigation, screen structure and reuse of existing pages.
4. [Code and API migration](04_CODE_AND_API_MIGRATION.md): exact destination structure, copy rules and module boundaries.
5. [ComfyUI and data preservation](05_COMFYUI_AND_DATA_PLAN.md): engine dependencies, database/media migration and readiness evidence.
6. [Execution backlog](06_EXECUTION_BACKLOG.md): small PRs, acceptance criteria and collaboration with Ashu.
7. [Domain glossary and decisions](07_DOMAIN_AND_DECISIONS.md): names and invariants that must survive UI changes.
8. [Source evidence index](08_SOURCE_EVIDENCE.md): all indexed services, backend routes and workflow files, including hashes and duplicate groups.
9. [Handoff](HANDOFF.md): continuity and remaining work.

## Evidence legend

- **I — Integrated:** a website/backend path exists. This is a source finding; it does not certify the currently running environment.
- **R — Recorded acceptance:** source release records describe a successful representative live path. Scope and limits remain attached to that record.
- **W — Workflow:** graph exists; a complete typed website adapter or acceptance was not established.
- **S — Standalone:** separate CLI, Streamlit, Docker or training tool exists outside the main website.
- **P — Partial/gated:** important pieces are missing, deliberately disabled, or not executable through the advertised surface.
- **E — Engine component:** node/model/provider building block exists; no dedicated product action was established.
- Combinations such as **I/R** or **S/P** are intentional. File existence, integration and live acceptance are separate facts.

## What changed since the previous audit

Story Builder's current source release records are dated 7 October 2026. They describe a released production workspace and representative Manual/Semi/Full controller paths. The earlier 3 October reuse audit is historical and is too narrow to govern this migration.

The source reports 803 backend tests, 14 frontend unit tests, frontend typecheck/build, lint with 0 errors and 13 warnings, and a browser run with 24 passes and 8 skips. Those are existing release records, **not tests executed in this planning audit**. No provider calls, model inference, rendering, training or service startup was performed here.

Recorded release acceptance covers five native audio/video clips and representative Full Direct and Full Reference continuations. It does not establish that every planned shot was rendered, that every reference-slot combination was tested, or that a complete film was automatically stitched.

## Important distinctions

- Manual/Semi/Full decides **who makes decisions**. Direct/Reference/Hybrid decides **how media is constructed**. Production style decides **what kind of work it is**. Keep these independent.
- Most of the value is already implemented. The first migration is a faithful copy and path/configuration adjustment; UI extraction follows.
- Timed Chatterbox dialogue, production VibeVoice dialogue and native H3 dialogue are different workflows. Do not put one interchangeable model selector over incompatible contracts.
- StyleTTS2 inference and fine-tuning scripts exist. They are standalone, with a checkpoint present; main website integration and completed training are unverified.
- F5 dataset preparation is integrated; training is explicitly disabled. ACE-Step generation is integrated; training source exists but full training is disabled.
- A UI workflow export is not a ready-to-submit API graph. Several filenames are duplicates or presets rather than unique capabilities.
- Legacy scene composition attaches one audio source to one video. Finalize writes a manifest. Neither is a verified full-film editor.

## Scope and limitations

The audit indexed all 71 top-level Python service modules, 224 HTTP routes and two lifecycle handlers, frontend page/navigation structure, and 90 workflow JSON files. It inspected important implementation bodies, contracts, tests and release records, plus standalone tool entry points and runtime dependencies. Workflow subgraph nodes are included in the evidence appendix. It did not read model binaries, inspect every vendored library line, or rerun the application. Optional/vendor facilities are cataloged as such.

The UI, module structure and backlog below are **proposals**. The accepted user direction is migration and reuse. No new GitHub repository, issue, collaborator invitation or external message was created during this audit.
