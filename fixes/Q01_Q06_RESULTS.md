# Q01–Q06 implementation results

Implemented locally on `vibe-director-current`, based on `f48e99a`. No commit or publishing performed. Q07–Q08 remain unimplemented and require separate approval.

## Result

| Card | Delivered |
| --- | --- |
| Q01 | Precise private audio staging exclusion for canonical, saved-project and tool-library discovery. Legitimate nested folders remain discoverable. Frozen job inputs stay in place. |
| Q02 | Shared `audio_utilities.submit` preserves all three manual operations, public 202 responses and both 503 codes. Newly owned partial staging is removed on failure; persisted or uncertain jobs retain inputs for recovery. |
| Q03 | GET-only tool metadata for `audio.extract_mp3` and `video.continuity_last_frame`, with concrete nested schemas, passive FFmpeg checks and execution disabled. |
| Q04 | Shared bounded skill reader and metadata registry for configured global providers, the three live bundled packages, and the open project's `skills` directory. Existing Director/Editor prompt text remains equivalent. |
| Q05 | Bounded source-backed workspace, asset, current story revision, Editor session and referenced job projections. No parallel knowledge store, migrations or hidden discovery/recovery writes. |
| Q06 | One collapsed shared capabilities inspector in StudioShell. Director and Editor use the same APIs; abort and owner checks discard late project responses. Sidebar, Media Prep and independent creation remain available. |

## Skill configuration and ownership

The backend process can register installed global skill roots explicitly, for example:

```bash
export VIBE_DIRECTOR_AGENT_SKILL_ROOTS='{"codex":"/home/riki/.codex/skills","agents":"/home/riki/.agents/skills"}'
```

This batch does not edit the running application's environment or global installations. Without that configuration only bundled and project scopes are discovered. Each provider root exposes immediate `<skill>/SKILL.md` packages; no home-directory or fixes-archive scan occurs. A project's owned skills live under its canonical project folder's `skills/<skill>/SKILL.md`. Missing, unsafe or oversized files are unavailable. Scope/provider/id refs preserve collisions; SHA-256 detects file updates. Supporting references can be read only relative to a registered safe root through the bounded reader.

All three discovery routes validate the open server-side workspace, including `tool-library`. This is project ownership validation within the existing local-owner application, not a new authentication system. Skills grant no filesystem, browser, terminal, coding, computer or generation permissions. Automatic binding of new global/project craft guidance into chat and durable execution remain future work.

Implemented endpoints:

- `GET /api/agent/tools?workspace_id=...`
- `GET /api/agent/skills?workspace_id=...`
- `GET /api/agent/projects/{workspace_id}/context`

## Validation

- **59 backend tests passed**: audio utility integration, media catalogue, agent API/skills/tools, project checkpoint/recovery, named storage, Editor clearance and CPU effects. Real CPU FFmpeg MP3 publication and short effect-media checks ran; GPU/container execution was mocked.
- **58 test-owned temporary directories verified removed**, including their media, databases, jobs and injected-failure artifacts. No production data or user media used.
- **TypeScript `npm run typecheck` passed.**
- **5 browser tests passed**: four new inspector/sidebar tests plus existing Editor pasted/dropped attachment regression. Covers Director/Editor, collapsed state, keyboard, mobile width, independent Video Create and retained unsaved prompt, project-switch late responses, Media Prep access and GET-only discovery.
- **3 older browser tests failed identically with the original HEAD shell in an isolated temporary frontend copy**: Create prompt application remains disabled after text restoration; Media Prep Images test expects a heading that does not appear; Media Prep voice test has an ambiguous `Alice` locator. Their source was not modified. These are baseline limitations, not passing acceptance evidence.
- Chromium initially hit a sandbox launch restriction; mocked checks succeeded outside that sandbox. Every browser output directory and the entire temporary baseline copy were removed, including after failed runs. Both test Vite servers were stopped.
- Context byte snapshots confirm no persistent file/manifest/job/database updates. SQLite `mode=ro` still updates volatile WAL shared-memory read-lock bookkeeping; only that `-shm` bookkeeping is excluded from the byte comparison. No mutating catalogue, Editor state or job recovery readers are called by discovery.
- Graphify's incremental extraction produced only changed-file coverage, so a full **local AST-only** refresh ran: **5,001 nodes, 15,025 edges, 418 source files**. No LLM/provider extraction. Unsupported and zero-node sources still limit coverage. Disposable newly generated AST caches were removed; graph, manifest and tracked stat index remain refreshed.
- Source-impact review: [verified citations](../.review/q01-q06-impact.json). The 27 anchors pass the bundled verifier; that verifies locations, not dependency completeness or branch coverage. Maximum heuristic impact risk is 0.60–0.70 (ownership/public flow boundaries), not a defect probability. No measured coverage claim is made.

## Limits and next phase

Previously indexed private staging assets are not purged; Q01 prevents new discoveries. Existing job inputs, media identities, originals and history are retained. Metadata readiness is not execution authorization, and continuity still requires a registered generated predecessor and verified hash. Project context is derived and bounded; it is not editable persistent agent memory. No GPU/provider generation or full live production acceptance was attempted.

Next is **Q07**, requiring approval of its final SQL, immutable approval/hash bindings, invocation identity and crash recovery design before implementation. Q08 then connects both chats to that durable gateway. No task/chat execution buttons or unrestricted computer capabilities were added here.

## Rollback

Restore the manual audio route before removing the shared submission helper. Revert the private staging discovery exclusion separately if necessary; historical job paths were not relocated. Remove inspector wiring before its client/service modules, restore the legacy craft readers, then remove `/api/agent` dispatch. No database migration or persisted agent data needs rollback. Retain existing jobs, frozen inputs, history, destination grants and published media; never delete them as rollback.

## Changed files

Includes the earlier requested uncommitted guide edits, this batch's application changes/tests, and generated review artifacts. Graphify files are separate from application code.

- [.review/guide-assessment.json](</home/riki/Documents/ChatGPT/Vibe Director/.review/guide-assessment.json>)
- [.review/q01-q06-impact.json](</home/riki/Documents/ChatGPT/Vibe Director/.review/q01-q06-impact.json>)
- [backend/story_builder/change_readme.md](</home/riki/Documents/ChatGPT/Vibe Director/backend/story_builder/change_readme.md>)
- [backend/story_builder/isolated_server.py](</home/riki/Documents/ChatGPT/Vibe Director/backend/story_builder/isolated_server.py>)
- [backend/story_builder/services/agent_api.py](</home/riki/Documents/ChatGPT/Vibe Director/backend/story_builder/services/agent_api.py>)
- [backend/story_builder/services/agent_graph.py](</home/riki/Documents/ChatGPT/Vibe Director/backend/story_builder/services/agent_graph.py>)
- [backend/story_builder/services/agent_skills.py](</home/riki/Documents/ChatGPT/Vibe Director/backend/story_builder/services/agent_skills.py>)
- [backend/story_builder/services/agent_tools.py](</home/riki/Documents/ChatGPT/Vibe Director/backend/story_builder/services/agent_tools.py>)
- [backend/story_builder/services/audio_utilities.py](</home/riki/Documents/ChatGPT/Vibe Director/backend/story_builder/services/audio_utilities.py>)
- [backend/story_builder/services/change_readme.md](</home/riki/Documents/ChatGPT/Vibe Director/backend/story_builder/services/change_readme.md>)
- [backend/story_builder/services/director_skills.py](</home/riki/Documents/ChatGPT/Vibe Director/backend/story_builder/services/director_skills.py>)
- [backend/story_builder/services/media_discovery.py](</home/riki/Documents/ChatGPT/Vibe Director/backend/story_builder/services/media_discovery.py>)
- [backend/story_builder/services/vibe_editor.py](</home/riki/Documents/ChatGPT/Vibe Director/backend/story_builder/services/vibe_editor.py>)
- [backend/story_builder/tests/change_readme.md](</home/riki/Documents/ChatGPT/Vibe Director/backend/story_builder/tests/change_readme.md>)
- [backend/story_builder/tests/test_agent_api.py](</home/riki/Documents/ChatGPT/Vibe Director/backend/story_builder/tests/test_agent_api.py>)
- [backend/story_builder/tests/test_agent_skills.py](</home/riki/Documents/ChatGPT/Vibe Director/backend/story_builder/tests/test_agent_skills.py>)
- [backend/story_builder/tests/test_agent_tools.py](</home/riki/Documents/ChatGPT/Vibe Director/backend/story_builder/tests/test_agent_tools.py>)
- [backend/story_builder/tests/test_audio_utilities_integration.py](</home/riki/Documents/ChatGPT/Vibe Director/backend/story_builder/tests/test_audio_utilities_integration.py>)
- [backend/story_builder/tests/test_media_catalogue.py](</home/riki/Documents/ChatGPT/Vibe Director/backend/story_builder/tests/test_media_catalogue.py>)
- [design/vibe-editor/change_readme.md](</home/riki/Documents/ChatGPT/Vibe Director/design/vibe-editor/change_readme.md>)
- [fixes/CODEX_CHANGE_README_PROMPT.md](</home/riki/Documents/ChatGPT/Vibe Director/fixes/CODEX_CHANGE_README_PROMPT.md>)
- [fixes/FILE_CHANGE_MATRIX.md](</home/riki/Documents/ChatGPT/Vibe Director/fixes/FILE_CHANGE_MATRIX.md>)
- [fixes/Q01_Q06_RESULTS.md](</home/riki/Documents/ChatGPT/Vibe Director/fixes/Q01_Q06_RESULTS.md>)
- [fixes/QUICK_FIX_TASKS.md](</home/riki/Documents/ChatGPT/Vibe Director/fixes/QUICK_FIX_TASKS.md>)
- [fixes/SOURCE_ASSESSMENT.md](</home/riki/Documents/ChatGPT/Vibe Director/fixes/SOURCE_ASSESSMENT.md>)
- [fixes/change_readme.md](</home/riki/Documents/ChatGPT/Vibe Director/fixes/change_readme.md>)
- [frontend/src/AgentInspector.tsx](</home/riki/Documents/ChatGPT/Vibe Director/frontend/src/AgentInspector.tsx>)
- [frontend/src/StudioShell.tsx](</home/riki/Documents/ChatGPT/Vibe Director/frontend/src/StudioShell.tsx>)
- [frontend/src/agent-inspector.css](</home/riki/Documents/ChatGPT/Vibe Director/frontend/src/agent-inspector.css>)
- [frontend/src/change_readme.md](</home/riki/Documents/ChatGPT/Vibe Director/frontend/src/change_readme.md>)
- [frontend/src/lib/agent-api.ts](</home/riki/Documents/ChatGPT/Vibe Director/frontend/src/lib/agent-api.ts>)
- [frontend/src/lib/agent-context.ts](</home/riki/Documents/ChatGPT/Vibe Director/frontend/src/lib/agent-context.ts>)
- [frontend/src/lib/change_readme.md](</home/riki/Documents/ChatGPT/Vibe Director/frontend/src/lib/change_readme.md>)
- [frontend/tests/agent-inspector.spec.mjs](</home/riki/Documents/ChatGPT/Vibe Director/frontend/tests/agent-inspector.spec.mjs>)
- [graphify-out/cache/stat-index.json](</home/riki/Documents/ChatGPT/Vibe Director/graphify-out/cache/stat-index.json>)
- [graphify-out/graph.json](</home/riki/Documents/ChatGPT/Vibe Director/graphify-out/graph.json>)
- [graphify-out/manifest.json](</home/riki/Documents/ChatGPT/Vibe Director/graphify-out/manifest.json>)
- [skills/change_readme.md](</home/riki/Documents/ChatGPT/Vibe Director/skills/change_readme.md>)

## Reviewed impact nodes

Bounded production-flow nodes; test functions and import-only candidates are excluded from this table and documented in the JSON limitations. Risk factors and relationship evidence are in the verified artifact.

| Risk | Node | File and line | Source anchor |
| --- | --- | --- | --- |
| 0.60–0.70 | isolated_server.py::app | [backend/story_builder/isolated_server.py:480](</home/riki/Documents/ChatGPT/Vibe Director/backend/story_builder/isolated_server.py:480>) | `def app(environ, start_response):` |
| 0.60–0.70 | audio_utilities.py::stage_assets | [backend/story_builder/services/audio_utilities.py:136](</home/riki/Documents/ChatGPT/Vibe Director/backend/story_builder/services/audio_utilities.py:136>) | `def stage_assets(data_root: Path, workspace_id: str, job_id: str, asset_ids: list[str], operation: str) -> list[dict[str, str]]:` |
| 0.60–0.70 | audio_utilities.py::submit | [backend/story_builder/services/audio_utilities.py:173](</home/riki/Documents/ChatGPT/Vibe Director/backend/story_builder/services/audio_utilities.py:173>) | `def submit(root: Path, workspace_id: str, payload: dict) -> dict:` |
| 0.60–0.70 | media_discovery.py::_discover_locked | [backend/story_builder/services/media_discovery.py:48](</home/riki/Documents/ChatGPT/Vibe Director/backend/story_builder/services/media_discovery.py:48>) | `def _discover_locked(root, workspace, *, shared=False, kinds=None):` |
| 0.60–0.70 | agent_api.py::handle | [backend/story_builder/services/agent_api.py:7](</home/riki/Documents/ChatGPT/Vibe Director/backend/story_builder/services/agent_api.py:7>) | `def handle(root, environ, start_response, respond):` |
| 0.60–0.70 | agent_graph.py::resolve_workspace | [backend/story_builder/services/agent_graph.py:42](</home/riki/Documents/ChatGPT/Vibe Director/backend/story_builder/services/agent_graph.py:42>) | `def resolve_workspace(root: Path, workspace: str) -> dict:` |
| 0.60–0.70 | agent_graph.py::read_json | [backend/story_builder/services/agent_graph.py:14](</home/riki/Documents/ChatGPT/Vibe Director/backend/story_builder/services/agent_graph.py:14>) | `def read_json(root, path, default=None):` |
| 0.60–0.70 | agent_graph.py::database | [backend/story_builder/services/agent_graph.py:30](</home/riki/Documents/ChatGPT/Vibe Director/backend/story_builder/services/agent_graph.py:30>) | `def database(root):` |
| 0.60–0.70 | agent_graph.py::context | [backend/story_builder/services/agent_graph.py:58](</home/riki/Documents/ChatGPT/Vibe Director/backend/story_builder/services/agent_graph.py:58>) | `def context(root: Path, owner: dict) -> dict:` |
| 0.60–0.70 | agent_skills.py::read_content | [backend/story_builder/services/agent_skills.py:14](</home/riki/Documents/ChatGPT/Vibe Director/backend/story_builder/services/agent_skills.py:14>) | `def read_content(root: Path, relative: str, *, limit: int = 24000) -> str:` |
| 0.60–0.70 | agent_skills.py::_metadata | [backend/story_builder/services/agent_skills.py:31](</home/riki/Documents/ChatGPT/Vibe Director/backend/story_builder/services/agent_skills.py:31>) | `def _metadata(scope, provider, root, skill_id):` |
| 0.60–0.70 | agent_skills.py::discover | [backend/story_builder/services/agent_skills.py:51](</home/riki/Documents/ChatGPT/Vibe Director/backend/story_builder/services/agent_skills.py:51>) | `def discover(root: Path, workspace: str) -> dict:` |
| 0.60–0.70 | audio_utilities.py::run_job | [backend/story_builder/services/audio_utilities.py:210](</home/riki/Documents/ChatGPT/Vibe Director/backend/story_builder/services/audio_utilities.py:210>) | `def run_job(job: dict[str, Any], *, data_root: Path, progress: Callable[[dict[str, Any]], None]) -> list[dict[str, Any]]:` |
| 0.60–0.70 | video_repertoire.py::create_job | [backend/story_builder/services/video_repertoire.py:806](</home/riki/Documents/ChatGPT/Vibe Director/backend/story_builder/services/video_repertoire.py:806>) | `def create_job(kind: str, request: dict[str, Any]) -> dict[str, Any]:` |
| 0.60–0.70 | AgentInspector.tsx::AgentInspector | [frontend/src/AgentInspector.tsx:6](</home/riki/Documents/ChatGPT/Vibe Director/frontend/src/AgentInspector.tsx:6>) | `export default function AgentInspector() {` |
| 0.60–0.70 | agent-api.ts::discoverAgent | [frontend/src/lib/agent-api.ts:18](</home/riki/Documents/ChatGPT/Vibe Director/frontend/src/lib/agent-api.ts:18>) | `export async function discoverAgent(workspace: string, signal: AbortSignal): Promise<AgentDiscovery> {` |
| 0.40–0.50 | agent_tools.py::tools | [backend/story_builder/services/agent_tools.py:5](</home/riki/Documents/ChatGPT/Vibe Director/backend/story_builder/services/agent_tools.py:5>) | `def tools() -> dict:` |
| 0.40–0.50 | director_skills.py::director_skill_context | [backend/story_builder/services/director_skills.py:11](</home/riki/Documents/ChatGPT/Vibe Director/backend/story_builder/services/director_skills.py:11>) | `def director_skill_context(*, video: bool = False) -> str:` |
| 0.40–0.50 | vibe_editor.py::run_job | [backend/story_builder/services/vibe_editor.py:380](</home/riki/Documents/ChatGPT/Vibe Director/backend/story_builder/services/vibe_editor.py:380>) | `def run_job(root, job_id, request, progress):` |
| 0.40–0.50 | video_repertoire.py::start_job | [backend/story_builder/services/video_repertoire.py:975](</home/riki/Documents/ChatGPT/Vibe Director/backend/story_builder/services/video_repertoire.py:975>) | `def start_job(kind: str, job_id: str) -> dict[str, Any]:` |
| 0.40–0.50 | media_library.py::list_assets | [backend/story_builder/services/media_library.py:385](</home/riki/Documents/ChatGPT/Vibe Director/backend/story_builder/services/media_library.py:385>) | `def list_assets(root: Path, workspace_id: str, *, kind: str \| None = None, limit: int = 50,` |
| 0.40–0.50 | media_library.py::browse_catalogue | [backend/story_builder/services/media_library.py:1302](</home/riki/Documents/ChatGPT/Vibe Director/backend/story_builder/services/media_library.py:1302>) | `def browse_catalogue(root: Path, workspace_id: str, *, kinds: str = "image,video,audio",` |
| 0.40–0.50 | story_authoring.py::draft_screenplay | [backend/story_builder/services/story_authoring.py:1612](</home/riki/Documents/ChatGPT/Vibe Director/backend/story_builder/services/story_authoring.py:1612>) | `def draft_screenplay(self, *, workspace_id: str, source_revision_id: str,` |
| 0.40–0.50 | prompt_drafts.py::prepare | [backend/story_builder/services/prompt_drafts.py:105](</home/riki/Documents/ChatGPT/Vibe Director/backend/story_builder/services/prompt_drafts.py:105>) | `def prepare(self, workspace_id, revision_id, shot_key, workflow_id, *, setup_snapshot=None,` |
| 0.40–0.50 | fully_automated_clip_plan.py::generate_clip_plan | [backend/story_builder/services/fully_automated_clip_plan.py:33](</home/riki/Documents/ChatGPT/Vibe Director/backend/story_builder/services/fully_automated_clip_plan.py:33>) | `def generate_clip_plan(*, workspace_id: str, screenplay_revision_id: str,` |
| 0.40–0.50 | StudioShell.tsx::StudioShell | [frontend/src/StudioShell.tsx:53](</home/riki/Documents/ChatGPT/Vibe Director/frontend/src/StudioShell.tsx:53>) | `export default function StudioShell({ route, children, context='Direct creation' }: { route:StudioRoute;children:ReactNode;context?:string }) {` |
| 0.40–0.50 | video_repertoire_worker.py::main | [backend/story_builder/services/video_repertoire_worker.py:1135](</home/riki/Documents/ChatGPT/Vibe Director/backend/story_builder/services/video_repertoire_worker.py:1135>) | `def main() -> int:` |
