# Tool graph + computer/coding access

## Separate concepts
**Skills**: what good screenplay, cinematography, animation and editing work look like. Text instructions, not execution rights.

**Tool graph**: what operations currently exist and are available; capabilities, typed arguments, safety, lifecycle and outputs. Seed from `source_materials/tool_glossary.zip` (44 groups) but **do not** treat groups as callable functions.

**Computer runtime**: an installed permissioned environment with shell/filesystem/Git/code/tests/browser/desktop automation; independent of LLM model choice. User can enable or decline it. Never claim Codex computer access by changing a system prompt alone.

**Project graph**: what is true of THIS film and its progress, with provenance and snapshots.

## Tool operation descriptor (per operation, not per glossary group)
`tool_id`, `version`, `description`, `scope=project/global`, `category`, `execution_kind=api|sandbox|browser|external`, `input_schema`, `output_schema`, `required_assets`, `capability_check`, `owner_id`, `resource_class`, `permission_tier`, `idempotency/reconcile`, `job_status`, `cancel/retry`, `output_registration`, `UI_route+context`, `source_code_anchor`, `observed_state=wired/navigation_only/unavailable/unverified`.

## Computer/coding tool examples (opt-in)
- `computer.fs.read`, `computer.fs.list` (scoped roots; read-only)
- `computer.fs.patch`, `computer.fs.write` (workspace scratch / approved code worktree)
- `computer.exec.run` (sandboxed allowlisted interpreter/commands, timeout and output budget)
- `computer.git.status`, `.diff`, `.branch`, `.commit` (approval policy)
- `computer.tests.run` (test/build commands from trusted project manifests)
- `computer.browser.navigate`, `.inspect`, `.click`, `.type`, `.screenshot` (authorized web UI, browser isolation)
- `computer.desktop.inspect`, `.click`, `.type` (optional OS-specific computer-use adapter, never assumed)
- `computer.media.ffprobe`, `.ffmpeg`, `.extract_frame` (safe argument arrays, trusted file paths)
- `code.adapter.scaffold`, `.test`, `.register` (create new trusted adapter only after code approval/testing)

## Trust boundaries
Default to app API for generation, media/library, project and export. Computer interaction isn't an escape hatch for ownership checks. Never allow LLM text to become a shell command unvalidated. A trusted runner executes a *structured operation*, and tools expose exact permission/capability scopes. Prevent prompt injection from video transcripts, retrieved websites, source repos or generated captions. Keep credentials out of prompts, logs and artifacts. No unrestricted filesystem crawling or external uploads.

## Tool recovery
Each call records intent and a durable `tool_call_id`. For app jobs use existing idempotency/leases/reconciliation. For local file operations, write temp files + atomic rename with expected hashes. For GUI automation, inspect state after every action and avoid repeating an irreversible click if the outcome is uncertain. Model must not retry failed GPU/paid action with a fresh key unless reconciliation confirms safe release.

## Capability graph navigation example
User: "Extract the sound from video 42 and replace a bad line." Director discovers `audio.extract` via glossary, verifies actual app `/api/audio/.../utilities` schema/capability, executes extract, then inspects supported analysis, speech/scene-surgery and editor composition tools. If transcription unavailable, it says so and obtains real timestamps; does not fabricate them. User remains in Editor chat and right-pane Audio Utilities surface can be opened with correct source selected.

## Integration expansion
First adapters: capability browse, project state, media browse, `audio.extract` end-to-end, editor navigation, clip metadata and last frame. Next: screenplay edits, Z-Image, H3 and take review, audio repair, HyperFrames. Computer/code tools gated behind explicit local runtime setup and user-plan approval. External OpenMontage and Backlot remain optional verified adapters.
