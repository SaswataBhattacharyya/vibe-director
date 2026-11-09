# Native interface impact review

working tree vs HEAD 3a5bc11be4b3474db7f54a4f0bc154dbf936a116

Overall heuristic risk: **high** (0.90 idle-expiry test gap; not a defect probability). The native security/flow seams score 0.60. Shared caller counts were not exhaustively counted.

- Traced native UI/route/stage/import/render and saved-board/mirror/native UI flows to depth 2-4. Graphify misses dynamic HTTP registrations, iframe behavior and several JS callbacks; source and execution evidence take precedence.
- No measured coverage collected. Test-gap factor is a source-reference proxy, not proof of complete tests. Idle expiry lacks a targeted timed test. No full security audit or owner-content quality acceptance.
- Only these milestone adapters and directly affected shared consumers are scoped; unrelated broad filmmaking orchestration deferred. CSS/types/licenses/docs have no function call graph.
- Graph refreshed with code-only no-cluster; extraction warnings and dynamic edge limitations remain.

Source anchors: 42 checked, zero rejected by the bundled citation verifier. This verifies locations, not dependency correctness or measured coverage.

| Risk | Scope | Node | File:line | Anchor |
| --- | --- | --- | --- | --- |
| 0.90 | direct | _reap | backend/story_builder/services/interface_sessions.py:94 | <code>def _reap():</code> |
| 0.60 | direct | stage | backend/story_builder/services/editor_studio.py:14 | <code>def stage(root, project_id, body):</code> |
| 0.60 | direct | open_workspace | backend/story_builder/services/editor_studio.py:59 | <code>def open_workspace(root, project_id, body):</code> |
| 0.60 | direct | mapped_plan | backend/story_builder/services/editor_studio.py:107 | <code>def mapped_plan(s):</code> |
| 0.60 | direct | operate | backend/story_builder/services/editor_studio.py:148 | <code>def operate(root, project_id, body):</code> |
| 0.60 | direct | create | backend/story_builder/services/interface_sessions.py:19 | <code>def create(root, kind, owner):</code> |
| 0.60 | direct | get | backend/story_builder/services/interface_sessions.py:29 | <code>def get(root, token, kind, owner, *, allow_stopped=False):</code> |
| 0.60 | direct | launch | backend/story_builder/services/interface_sessions.py:40 | <code>def launch(s, command, *, env=None, health='/'):</code> |
| 0.60 | direct | close | backend/story_builder/services/interface_sessions.py:67 | <code>def close(s):</code> |
| 0.60 | direct | _close | backend/story_builder/services/interface_sessions.py:72 | <code>def _close(s):</code> |
| 0.60 | direct | _shutdown | backend/story_builder/services/interface_sessions.py:104 | <code>def _shutdown():</code> |
| 0.60 | direct | sync | backend/story_builder/services/production_board.py:24 | <code>def sync(board, s, expected_revision=None):</code> |
| 0.60 | direct | _sync | backend/story_builder/services/production_board.py:31 | <code>def _sync(board, s, expected_revision):</code> |
| 0.60 | direct | open_workspace | backend/story_builder/services/production_board.py:64 | <code>def open_workspace(board, owner, screenplay, body):</code> |
| 0.60 | direct | operate | backend/story_builder/services/production_board.py:85 | <code>def operate(board, owner, screenplay, body):</code> |
| 0.60 | direct | authorize | backend/story_builder/services/native_backlot.py:19 | <code>async def authorize(request, call_next):</code> |
| 0.60 | direct | install | scripts/setup_production_interfaces.py:17 | <code>def install():</code> |
| 0.60 | direct | def handle | backend/story_builder/services/vibe_editor_api.py:7 | <code>def handle(root, environ, start_response, read_json, respond, *, tasks=None):</code> |
| 0.60 | direct | def create_app | backend/story_builder/isolated_server.py:273 | <code>def create_app(*, data_root: Path, ledger_path: Path &#124; None = None,</code> |
| 0.60 | direct | export default function NativeWorkspace | frontend/src/NativeWorkspace.tsx:8 | <code>export default function NativeWorkspace({title,open,action,onImported,disabled,identity}:Props){</code> |
| 0.60 | direct | function safeRewrite | backend/story_builder/services/native_studio.mjs:14 | <code>function safeRewrite(text){</code> |
| 0.60 | direct | function allowed | backend/story_builder/services/native_studio.mjs:34 | <code>function allowed(path,method,body){</code> |
| 0.60 | direct | const server=createServer | backend/story_builder/services/native_studio.mjs:61 | <code>const server=createServer(async(req,res)=&gt;{</code> |
| 0.60 | indirect | def selected_plan | backend/story_builder/services/vibe_editor.py:365 | <code>def selected_plan(root, p, raw):</code> |
| 0.60 | indirect | def propose_plan | backend/story_builder/services/vibe_editor.py:373 | <code>def propose_plan(root, project_id, body, *, evidence=None):</code> |
| 0.60 | indirect | def command | backend/story_builder/services/vibe_editor.py:233 | <code>def command(root, project_id, body, *, agent_request=None, on_created=None):</code> |
| 0.60 | indirect | def render | backend/story_builder/services/vibe_editor_render.py:52 | <code>def render(root, job_id, request, progress):</code> |
| 0.60 | indirect | def asset_path | backend/story_builder/services/media_library.py:821 | <code>def asset_path(root: Path, workspace_id: str, asset_id: str) -&gt; tuple[Path, str, str]:</code> |
| 0.60 | indirect | def export | backend/story_builder/services/production_manifest.py:9 | <code>def export(board, owner, screenplay_revision, expected_revision):</code> |
| 0.40 | direct | document | backend/story_builder/services/editor_studio.py:65 | <code>def document(plan, sources):</code> |
| 0.40 | direct | __init__ | backend/story_builder/services/editor_studio.py:83 | <code>    def __init__(self, text):</code> |
| 0.40 | direct | handle_starttag | backend/story_builder/services/editor_studio.py:88 | <code>    def handle_starttag(self, tag, attrs):</code> |
| 0.40 | direct | handle_endtag | backend/story_builder/services/editor_studio.py:98 | <code>    def handle_endtag(self, tag):</code> |
| 0.40 | direct | handle_data | backend/story_builder/services/editor_studio.py:102 | <code>    def handle_data(self, text):</code> |
| 0.40 | direct | _write | backend/story_builder/services/production_board.py:14 | <code>def _write(path, value):</code> |
| 0.40 | direct | export default function VibeEditorPage | frontend/src/VibeEditorPage.tsx:21 | <code>export default function VibeEditorPage() {</code> |
| 0.40 | direct | export default function StoryboardPage | frontend/src/StoryboardPage.tsx:12 | <code>export default function StoryboardPage({view}:{view:'frames'&#124;'storyboard'}){</code> |
| 0.40 | direct | export default function EditorVisualTimeline | frontend/src/EditorVisualTimeline.tsx:6 | <code>export default function EditorVisualTimeline({project, plan, disabled, onChange, onSave, canSave}:{</code> |
| 0.40 | direct | export const openBacklot= | frontend/src/lib/storyboard-api.ts:20 | <code>export const openBacklot=(state:BoardState)=&gt;request&lt;NativeSession&gt;(base(state.workspace_id,state.screenplay_revision_id)+'/backlot',{expected_revision:state.revision});</code> |
| 0.40 | direct | export const operateBacklot= | frontend/src/lib/storyboard-api.ts:21 | <code>export const operateBacklot=(w:string,r:string,token:string,action:NativeAction)=&gt;request&lt;unknown&gt;(base(w,r)+'/backlot-action',{token,action});</code> |
| 0.40 | direct | async function stop | backend/story_builder/services/native_studio.mjs:91 | <code>async function stop(){server.close();await studio.shutdown();process.exit(0);}</code> |
| 0.40 | indirect | def editor_handoff | backend/story_builder/services/storyboard.py:334 | <code>    def editor_handoff(self, workspace, revision):</code> |

## Changed files

Full local change inventory, including refreshed graph artifacts. No application data/database migration or owner-media changes.

- `README.md`
- `backend/story_builder/isolated_server.py`
- `backend/story_builder/services/vibe_editor_api.py`
- `fixes/ACTIVE_FIXES.md`
- `fixes/INTEGRATION_ARCHITECTURE.md`
- `frontend/src/EditorVisualTimeline.tsx`
- `frontend/src/StoryboardPage.tsx`
- `frontend/src/VibeEditorPage.tsx`
- `frontend/src/lib/storyboard-api.ts`
- `frontend/tests/editor-visual.spec.mjs`
- `frontend/tests/storyboard.spec.mjs`
- `graphify-out/cache/stat-index.json`
- `graphify-out/graph.json`
- `graphify-out/manifest.json`
- `.review/native-interfaces-impact.json`
- `.review/native-interfaces-impact.md`
- `backend/story_builder/services/editor_studio.py`
- `backend/story_builder/services/interface_sessions.py`
- `backend/story_builder/services/native_backlot.py`
- `backend/story_builder/services/native_studio.mjs`
- `backend/story_builder/services/production_board.py`
- `backend/story_builder/tests/test_native_interfaces.py`
- `design/vibe-editor/native-interfaces.md`
- `frontend/src/NativeWorkspace.tsx`
- `frontend/src/lib/native-workspace.ts`
- `frontend/src/native-workspace.css`
- `frontend/tests/native-interfaces.manual.mjs`
- `frontend/tests/native-workspace.spec.mjs`
- `graphify-out/cache/ast/v0.9.17/1eb1971716b25033c79a0ceaca27a054299de680e0e5b426fd1d7165b0b84cf4.json`
- `graphify-out/cache/ast/v0.9.17/492edfe04216eec142f3d5f407499bc3c1625b0e9485c815a44935ba135d2c0a.json`
- `graphify-out/cache/ast/v0.9.17/5056d96e53f0ea3433143b9d7cc6c924a8bfa062060b08dc8e7714808cc052d3.json`
- `graphify-out/cache/ast/v0.9.17/50a477e7ecf6efa2352fa6a20917addd1c0c03fe865ab430be80794e7a0751cc.json`
- `graphify-out/cache/ast/v0.9.17/625a19df134ffed013ac9cfb70fdaec85c4b9719134b04564d6a05eaa17273a7.json`
- `graphify-out/cache/ast/v0.9.17/6f1771a1e3c9c073025f636e4fe05e1cbcb63131cb1e252e316a1acbbcad8161.json`
- `graphify-out/cache/ast/v0.9.17/7b2618651dd1f335a75f495fbbd21f24b282277adaecc8994cd53c02ff890048.json`
- `graphify-out/cache/ast/v0.9.17/9f266dbd1c775cc5e1083c201de465bdd471eceb955f604e71bfc7868ec8d81b.json`
- `graphify-out/cache/ast/v0.9.17/d0d08e097ffb79326b4ee302b111536223ffae2d404aee4318f10383540ef096.json`
- `graphify-out/cache/ast/v0.9.17/dbf54868120608e1757c6572d9febebb65238666960d412121b3bb8f70d4d06b.json`
- `graphify-out/cache/ast/v0.9.17/de11ece896261e0a565fec5ebc608f4cd556150af3f5b3ac183ffe71c956a20a.json`
- `scripts/setup_production_interfaces.py`
- `third_party_licenses/OpenMontage/LICENSE`
- `third_party_licenses/OpenMontage/NOTICE.md`
