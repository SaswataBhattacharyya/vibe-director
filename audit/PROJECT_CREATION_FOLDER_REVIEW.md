# New project folder creation — scoped impact review

Task-specific New-project child-folder change in dirty working tree; unrelated earlier edits excluded.

high (maximum 0.60, upper bound 0.70), prioritization score not defect probability

Risk | Node | File | Anchor | Reason
--- | --- | --- | --- | ---
0.60–0.70 | backend/story_builder/services/projects.py::def handle( | backend/story_builder/services/projects.py:647 | `def handle(root, story, environ, start_response, read_json, respond):` | Creates a fresh child directory, inserts identity, registers internal folder, calls save then activate. ProjectTests new-child tests exercise these branches.
0.60–0.70 | backend/story_builder/services/projects.py::def validate_folder( | backend/story_builder/services/projects.py:312 | `def validate_folder(root, value, workspace=None):` | Called by New for external parent and by save/open for final child. Canonical registered projects retain existing ownership exception.
0.60–0.70 | backend/story_builder/services/projects.py::def existing_project( | backend/story_builder/services/projects.py:155 | `def existing_project(root, folder):` | Recognizes newly registered canonical folder only through live ledger identity; reused by validate_folder and open_project.
0.60–0.70 | backend/story_builder/services/projects.py::def save( | backend/story_builder/services/projects.py:338 | `def save(root, workspace, folder, memory):` | New checkpoints and output defaults use the child folder, not its parent. Legacy exact-folder API callers remain supported.
0.60–0.70 | backend/story_builder/services/projects.py::def open_project( | backend/story_builder/services/projects.py:424 | `def open_project(root, folder):` | Reopens the named child without creating another identity; new backend test saves source and verifies restoration.
0.40–0.50 | backend/story_builder/services/projects.py::def current( | backend/story_builder/services/projects.py:66 | `def current(root):` | Returns projects_folder to ProjectController and the registered child folder after activate.
0.40–0.50 | frontend/src/ProjectController.tsx::const action=async | frontend/src/ProjectController.tsx:81 | `const action=async(operation:string,target?:string)=>{if(!project||actionBusy.current)return;actionBusy.current=true;setBusy(true);setError('');try{` | Sends parent_folder only for New; saves outgoing memory/checkpoint, installs returned child path. Browser creation and project-switch tests pass.
0.40–0.50 | backend/story_builder/services/storage_paths.py::def project_root( | backend/story_builder/services/storage_paths.py:39 | `def project_root(root: Path, workspace_id: str) -> Path:` | Reads project-folders registry; save, output/media ownership and current/open consume the same stable identity. Existing round-trip and named-child tests pass.
0.40–0.50 | backend/story_builder/services/projects.py::def output_defaults( | backend/story_builder/services/projects.py:323 | `def output_defaults(root, workspace, folder):` | Called by save and successful project operations; derives outputs beneath the returned child. Child outputs directory checked by backend test; per-tool provider execution not run.
0.40–0.50 | frontend/src/ProjectController.tsx::function install( | frontend/src/ProjectController.tsx:25 | `function install(project:Project,restore:boolean){` | Applies returned identity/browser memory; existing A-B-A and Editor/ACE restoration browser tests pass.

## Validation and limits

- No measured coverage; test_gap=0 means direct test evidence, not every branch covered.
- Caller count not exhaustively enumerated; unknown adds 0.10 to upper bounds.
- Graphify full refresh: 4576 nodes / 14300 edges; 71 zero-node and 39 unsupported files omitted.
- 22 backend project tests and 7 browser project tests pass; production build passes. New-project browser case additionally checks 390px layout.
- Real user projects were not created or switched as a test. Runtime GET confirms projects_folder and original active project. No provider/GPU generation initiated.
