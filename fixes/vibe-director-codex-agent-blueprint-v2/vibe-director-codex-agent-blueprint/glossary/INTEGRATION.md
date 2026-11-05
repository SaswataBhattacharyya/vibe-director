# Turning the glossary into usable Director tools

The owner wants the chatbot to decide which application capability to use, like an agent choosing a skill. Descriptions are the knowledge layer; typed tool execution is the action layer. Both are needed for a Director that can complete tasks across pages.

## What this folder delivers now

- A compact selection index and detailed usage guides for 44 capability groups.
- A JSON catalogue for lookup and future registry construction.
- Source-linked API helper, HTTP route and backend component inventories.
- Input/output and workflow guidance, known boundaries and a concrete audio-extraction chain.

**It does not change the app, install executable tools, load this knowledge into current chats or prove runtime readiness.** Documentation-only creation preserves the current app behavior. The next implementation must wire the catalogue and adapters into the Director loop deliberately.

## Why current chats miss app capabilities

The runtime receives explicit prompts and schemas, not automatically all repository Markdown. `backend/story_builder/services/director_skills.py` reads a selected list of skill files. The Editor separately reads `design/vibe-editor/skills/vibe-editor-director/SKILL.md` in `vibe_editor.py`.

The current Editor skill describes its renderer and instructs specialist assets to be created/imported through another tool. That is a genuine scope restriction in today's implementation. `studio_tools_api.py` also tells its studio assistant to discuss settings and **never run tools or start generation**. `music_jukebox_api.py` chat similarly proposes supported changes rather than running tools. These prompts and the corresponding handlers need a coordinated redesign; appending a glossary alone will not grant cross-tool actions.

Keep prompt-specific artistic guidance separate from the new execution catalogue. Existing source/craft rules must not be silently replaced by this document.

## Proposed runtime contract

Each exposed operation needs its own validated schema. The 44 glossary groups are routing domains; they must be split into concrete read/create/update/approve/export operations where necessary. Do not expose a single generic “call any URL” tool.

| Field | Purpose |
|---|---|
| `tool_id`, `version`, description | Stable executable identity and when to choose it. Glossary IDs can seed this naming; they are not registered yet. |
| `input_schema`, `output_schema` | Exact fields/types and supported operation choices, derived from existing application validators. |
| Context requirements | Project/session ownership, revision, selected asset IDs and time ranges; resolve server-side where possible. |
| Capability resolver | Current dependency/model/worker/readiness reasons. |
| Execution adapter | Supported existing service/API; validate user input and model-generated arguments. |
| Authorization/resource policy | Read-only, local processing, inference/training, destructive publication or explicit user choice. Reuse current guards. |
| UI target/context mapping | Open the matching right-pane surface with selected media, settings and result handles. Nested Media Prep pages currently use local state; add a real navigation contract instead of inventing query parameters. |
| Job lifecycle | Start/status/result plus supported cancel/retry/reconcile. Respect operations that lack one of these actions. |
| Output binding | Registered asset IDs, verified paths, consumer role and originating project/conversation. |

The orchestrator should receive a small index, retrieve only relevant details, choose a concrete operation, validate arguments, execute, observe its real result, and continue the task. This supports provider-native function calls or a validated structured-action protocol; choose based on the existing reasoning-provider interfaces. Never execute arbitrary generated code.

## Implementation order

1. Build a read-only catalogue lookup and per-operation capability lookup. Reconcile the source schemas with the inventory; mark navigation-only and runtime-unverified entries explicitly.
2. Add a shared context/navigation bridge for the Codex-style right pane while central chat persists. Carry asset IDs/ranges and output choices between pages without duplicating their state.
3. Add the first execution adapter around **Extract MP3**, with input resolution, readiness, job polling and result attachment. This directly addresses the reported failure.
4. Add supported audio analysis/range splitting, then search/indexing and image/video/speech/music/editor/assembly adapters. Keep generation authorization and recovery behavior identical to their UI paths.
5. Integrate tool selection into the actual Director prompts and orchestration loop. Update the Editor specialist-operation guidance together with the executor so it no longer falsely claims unavailable functionality.
6. Persist task steps, jobs and artifacts with project/session state. Add resource-aware orchestration for longer chains, without making an optional storyboard a manual-generation prerequisite.

This order is an implementation recommendation, not a request to create a new parallel production engine. Keep service ownership and existing jobs; bridge their seams.

## Completion checks for the eventual implementation

- A chat request extracts a supplied video's audio through the existing utility and returns a playable registered asset.
- The Director chooses a tool from the catalogue rather than inventing an API or declaring an app capability absent because its own renderer lacks it.
- Tool navigation actually opens the populated surface and retains the conversation.
- Capability failure names the missing dependency; unsupported analysis does not produce imaginary transcripts or timestamps.
- Existing project loading, source files, manual workflows, frozen jobs and output publication remain intact.
- Interrupted tool calls reconcile without duplicate submissions. Only supported operations offer cancel/retry.
- Cross-project results cannot appear in the wrong conversation; original assets are preserved.
- Verify with focused backend/browser checks. Separate mocks and CPU extraction from explicitly authorized GPU/provider acceptance.
