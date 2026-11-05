# Folder media discovery review

Folder choices now discover supported media recursively, including files copied into a project outside the app. Existing registrations retain their IDs, archive status and role labels. Files are linked in place; Character/World filters remain metadata-based.

## Source contract

- Current project: canonical project content and its saved project folder, when different.
- All projects: project-owned media across known project folders.
- All media: projects, standalone tool media, app YouTube downloads and video repertoire.
- Video repertoire: every supported image/audio/video in the repertoire folder, regardless of analysis registration.
- YouTube downloads: supported media in the application download folder; this does not mean the operating-system Downloads directory.
- Role/category choices such as Characters, Worlds, styles and generated/analysed media retain their metadata semantics.
- Symlinks, hidden internals, saved checkpoint copies and intermediate directories are excluded. Supported suffixes remain PNG/JPEG/WebP; MP4/MOV/MKV/WebM; WAV/MP3/M4A/OGG/FLAC/AAC. Invalid media is not selectable.

## Impact and preservation

Overall heuristic risk: **high (0.60; possible 0.70)** at the source-path boundary. Read the table as change impact, not defect probability. No measured test coverage was collected. Original files, frozen hashes, registered IDs, explicit Add, archive semantics and deletion guards are preserved. Sources modified after registration continue to fail hash validation rather than silently changing saved requests.

| Risk | Node | File | Anchor | Reason |
|---|---|---|---|---|
| 0.60–0.70 | project_locations | backend/story_builder/services/media_discovery.py:10 | `def project_locations(root, workspace):` | Project registry → canonical and saved folder scopes. |
| 0.60–0.70 | discover | backend/story_builder/services/media_discovery.py:26 | `def discover(root, workspace, *, shared=False, kinds=None):` | list_assets/browse_catalogue → serialized discovery. |
| 0.60–0.70 | _discover_locked | backend/story_builder/services/media_discovery.py:35 | `def _discover_locked(root, workspace, *, shared=False, kinds=None):` | Recursive discovery → manifest identities, probe and content hashes; catalogue tests exercise new branches. |
| 0.60–0.70 | shared_file | backend/story_builder/services/storage_paths.py:77 | `def shared_file(root: Path, location: dict) -> Path:` | asset_path → authorized source resolution → previews, reference reuse and tool input validation. |
| 0.60–0.70 | asset_path | backend/story_builder/services/media_library.py:821 | `def asset_path(root: Path, workspace_id: str, asset_id: str) -> tuple[Path, str, str]:` | Unchanged resolver delegates new storage locations to shared_file; frozen identities remain intact. |
| 0.60–0.70 | reuse_catalogue_asset | backend/story_builder/services/media_library.py:1397 | `def reuse_catalogue_asset(root: Path, workspace_id: str, *, source_workspace_id: str, asset_id: str, role: str | None = None, mode: str = "reference") -> dict[str, Any]:` | Explicit Add → hash verification → shared link/copy; tamper and identity tests. |
| 0.60–0.70 | deletion_preview | backend/story_builder/services/media_library.py:1526 | `def deletion_preview(root: Path, workspace_id: str, asset_id: str) -> dict[str, Any]:` | Resolves discovered source path and checks other saved memberships before deleting. |
| 0.60–0.70 | delete_media_file | backend/story_builder/services/media_library.py:1577 | `def delete_media_file(root: Path, workspace_id: str, asset_id: str, sha256: str) -> dict[str, Any]:` | Unchanged explicit deletion resolves same source; discovery does not delete originals. |
| 0.60–0.70 | save | backend/story_builder/services/projects.py:338 | `def save(root, workspace, folder, memory):` | Project checkpoint copies registered source bytes and verifies original hash. |
| 0.40–0.50 | available | backend/story_builder/services/media_discovery.py:93 | `def available(root, record):` | list_assets/browse_catalogue → missing source filtering. |
| 0.40–0.50 | list_assets | backend/story_builder/services/media_library.py:385 | `def list_assets(root: Path, workspace_id: str, *, kind: str | None = None, limit: int = 50,` | API list → generic asset pools → Image Assets, FFLF, Editor, ACE, storyboard. |
| 0.40–0.50 | browse_catalogue | backend/story_builder/services/media_library.py:1302 | `def browse_catalogue(root: Path, workspace_id: str, *, kinds: str = "image,video,audio",` | API catalogue → shared picker and R2V dropdown; current/project/global scopes tested. |
| 0.40–0.50 | catalogue_source | backend/story_builder/services/media_library.py:1232 | `def catalogue_source(record: dict[str, Any]) -> str:` | browse_catalogue → physical repertoire classification without requiring analysis metadata. |
| 0.40–0.50 | _link_shared_asset | backend/story_builder/services/media_library.py:1464 | `def _link_shared_asset(root, workspace_id, source_workspace_id, source, location, role):` | Reference-mode reuse retains location and provenance in target manifest. |
| 0.40–0.50 | owned_files | backend/story_builder/services/projects.py:178 | `def owned_files(root, workspace, memory=None):` | Project save copies source files into checkpoint; excludes nested project-data. |
| 0.40–0.50 | MediaSourcePicker | frontend/src/MediaSourcePicker.tsx:9 | `export default function MediaSourcePicker({workspaceId,kinds,onAdded,disabled=false,role,compact=false}: {` | Shared picker used by Editor, Media Prep, Image Assets, ACE, Jukebox and Styles. Three browser tests cover source/Add interactions. |
| 0.40–0.50 | VideoWorkspace | frontend/src/App.tsx:129 | `function VideoWorkspace({ view='create', visible=true, workspaceId }: { view?: 'create'|'take'; visible?: boolean; workspaceId: string }) {` | R2V current project dropdown → browseMediaCatalogue → explicit Add; FFLF retains role slots. |
| 0.40–0.50 | browseMediaCatalogue | frontend/src/lib/media-api.ts:381 | `export function browseMediaCatalogue(workspaceId:string, options:{kinds:string;source:string;owner:string;query:string;offset:number;order:string;folder?:string}) {` | Shared HTTP client feeds both picker UIs; pagination/filter contracts unchanged. |
| 0.40–0.50 | listMediaAssets | frontend/src/lib/media-api.ts:97 | `export function listMediaAssets(workspaceId: string, kind: string, includeArchived = false, styleContextId = '') {` | Generic tool pools read newly discovered project assets; role categories remain separate. |
| 0.40–0.50 | validate_selection | backend/story_builder/services/vibe_editor.py:169 | `def validate_selection(root, workspace, values):` | Editor asset_path consumer validates selected files before rendering. |
| 0.40–0.50 | reference | backend/story_builder/services/ace_studio.py:196 | `def reference(root, p):` | ACE asset_path consumer probes reference audio; generation was not run. |

## Validation

- Backend: catalogue, media library, project round trips, storage migration, named project storage and output-destination suites passed. These include real CPU image probing and mocked audio/video discovery fixtures.
- Browser: 33 focused source-picker, selection and Video UI tests passed; the three source-picker tests were rerun after final scope/label changes. API responses in these tests are mocked.
- Production frontend build passed (existing bundle-size warning).
- Running app: Current Project showed 17 images; Video Repertoire showed 122 images, up from the prior registered-only 95. Browser verified both source choices and visible cards. No generation submitted. Screenshot: /tmp/vibe-media-discovery-live.png.
- Graph rebuilt with code-only extraction. 4,589 nodes and 14,366 edges across 476 code files; 73 zero-node files and 39 unsupported files limit coverage. All 21 source citations passed the bundled blast-radius verifier.

## Limits

- Graphify module import candidates are broader than semantic impact; retained only source-confirmed affected seams.
- Two levels traced: UI → API catalogue/list → discovery; reuse → asset_path/shared_file → tool inputs and checkpoint saving. Dynamic tool flows were not exhaustively traversed.
- No measured coverage, no generated-media acceptance. Graph has unsupported/zero-node files.
- Risk is a prioritization heuristic; unknown caller count gives an upper bound.
- Initial discovery reads/probes new files; known file paths are reused on subsequent browsing. A new folder with many large files can take longer on its first browse.
