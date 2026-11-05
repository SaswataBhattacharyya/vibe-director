# Updated GitHub source reconciliation — 2026-11-05

**Purpose:** Make the blueprint accurately describe the now-pushed repository, while preserving its plan-first status. This is a source inspection memo, not a claim that the app has been fixed.

## Checked Git source
- Repository: `SaswataBhattacharyya/vibe-director`.
- Application branch: `vibe-director-current` at inspection SHA `3b9db20304c1073c674271c8f60fc66859a7a044`. The default `main` is primarily planning material, not the current application tree.
- Earlier inspected branch SHA `65e9717932547cad2ef8b55e9beb2c83f7686b05` is **superseded**. The compare endpoint reported one later commit, with a large collection of added/modified files (the changed-file response was capped at 300 entries). Do not infer that unlisted files are unchanged without checking them.
- `full_review.md`, `tool_glossary/`, `audit/`, `backend/`, `frontend/`, `skills/`, and this `fixes/` package are present in the checked application branch. `fixes/` is documentation and example contracts, **not already-installed active skills or operational agent adapters**.

## Source rechecks and conclusions
- `backend/story_builder/services/vibe_editor.py` blob `806019b4c27fd44a78ad534c2fb54c0a543b0c78`: Editor chat still plans brief/selected ranges/HyperFrames composition. Its AI guidance explicitly says not to run tools or create files; this must be addressed by a separate authorized agent executor, **not by dropping the trusted render boundary**.
- `backend/story_builder/services/vibe_editor_render.py` blob `1a07845b8c43a007dbd7ea2a14a06a75c20f729c`: trusted HyperFrames/FFmpeg render path remains available; reuse it.
- `backend/story_builder/services/director_skills.py` blob `51eb979839dce480abca48512ee9d21bb5fae9a9`: hard-coded bundled skill reads; shared global/bundled/project skills discovery is a future implementation task.
- `backend/story_builder/services/media_discovery.py` blob `99efb24b615db98991042b653c202da6e0f8bd97`: updated catalogue/discovery code exists. Preserve its asset-fingerprint and replacement semantics.
- `backend/story_builder/services/projects.py` blob `065085fc63688d2cc91fb491ae0b31fc7fb8545e`: project checkpoint code exists. Preserve project ownership and snapshot semantics; do not create a second competing storage authority.
- `backend/story_builder/services/storyboard.py` blob `6a5a81933493a4220c19eb0883d6d40b6ed84b0c`: revisioned storyboard service exists; `FFLF_AUTOMATION_ENABLED = False` remains explicitly configured. The proposed comic board/agent must adapt this existing service.
- `AGENTS.md` now directs work in the active checkout, preserving media, jobs, and GPU guards. Follow it when implementing.

## What is still not proven
No new live app tests, actual GPU output, desktop automation, global skill-provider access, tool-executing agent, or end-to-end autonomous film production were demonstrated by this documentation reconciliation. The November 5 review's historical test claims must be validated against the currently installed environment before relying on them as fresh acceptance evidence.

## Codex action sequence
1. Read `AGENTS.md`, current `full_review.md`, `tool_glossary/README.md`, `audit/FUNCTIONALITY_AUDIT.md`, the current editor code, and the in-repo blueprint.
2. Record `git branch --show-current`, `git rev-parse HEAD`, `git status --short`. Do **not** assume the above SHA is still current, overwrite local edits, or switch branches without approval.
3. Build a current-state matrix: existing callable tools, navigation-only tools, absent capabilities, actual model limits, project/skill context, Director and Editor invocation paths.
4. Prepare precise file-level phases preserving left sidebar, Media Prep, existing project/media/HyperFrames workers and safety contracts. New global and project skills require a resolver and explicit tool permissions.
5. Stop at the requested **plan-only** gate. Implementation, package installs, paid provider work and GPU media generation require the user's explicit approval. Use disposable synthetic media in isolated test storage and verify cleanup when testing is later approved.

## Package integrity
If you modify any document tracked by `PACKAGE_MANIFEST.json`, update its SHA-256 and UTF-8 byte count, and run `python validate_package.py` from this blueprint directory. Do not silently edit `source_materials/` snapshots or glossary originals to make historical sources appear current.
