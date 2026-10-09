# Production style setup foundation

## Scope

This foundation adds a six-type validated base catalog, a schema-validated custom production-type publisher, and immutable selections for a workspace or isolated-generation context. It reuses the existing `ProductionLedger` SQLite database and stores no media bytes. The service records narrative-guidance and Director-profile hashes separately in both published versions and selection snapshots. Published custom versions and selections are append-only in SQLite; changing the selected version creates another snapshot. The local HTTP adapter exposes setup operations and verifies story workspace IDs against the story ledger before binding a selection.

The shared three-theme UI now displays the catalog and frozen selections and supports manual custom-type publication. Style-reference upload/staging, document or media extraction, multimodal analysis, evidence locators, proposal/review flow, original reference asset storage, frame exports, recommendation policy, generation compiler integration, stale-work propagation, and render/provider submission remain unimplemented. The implementation must not be described as a complete production-style feature. In particular, no analyzer or image/audio/video support is claimed.

## Reused source and provenance

The source files were byte-copied from `/home/riki/web_dev/story_builder`, the source path named in the current product README. The parent verified all nine files against the `mooV_E_maker` commit `2023bf5bce1a808b2624fb5789b4b2a1e8b7b8db` through GitHub API blob IDs; IDs are listed alongside local SHA256 values.

| Reused record | Local SHA256 | Pinned source Git blob |
| --- | --- | --- |
| `backend/story_builder/services/prompt_styles.py` | `b36367f97747eb399cc082810b2635d9f63ce52ded6e2d34eca71eb7581968a7` | `ae149e45f74f26af723752bf9deb5188c0b4e08a` |
| `backend/story_builder/services/production_director_profiles.py` | `900b219345d87e20ff1e1a1e60bc9a76f98edd144efc645028702424b6316196` | `f8e2caf56da7d375165ad00ff963ec8eaad0bbc5` |
| `backend/story_builder/prompts/styles/advertisement.json` | `a453ede06685ceb6682beef8caabdb8923936151b6e7c893f64c6a4fa90f340f` | `179ba6fd9262166b5f02dcbb74f5f225448e0ae7` |
| `backend/story_builder/prompts/styles/corporate_pitch.json` | `5d09a6ac59114384264173c040e2d15fc35f55e83f3be70bc2a18c031fe70335` | `4fc18ba0d8ed2326b64c820561f07c2119abc9ba` |
| `backend/story_builder/prompts/styles/informative.json` | `0de12bbc20b0bfd44f7373723bc8011e056d266c2e71204692bafb8116ac550e` | `087dccc0134223f1d2c09c17e897312394755beb` |
| `backend/story_builder/prompts/styles/news_report.json` | `cf5b21f9ab7f774e033c540b8ff5dcb916057f6383b547e476f44a062b932bb9` | `affd42b7697a8ac4016affdd28a1b96e183d0517` |
| `backend/story_builder/prompts/styles/social_profile.json` | `ead428f7aa5130c5de25eb0f7f471c4e7f543391d182a56189d01be450762dd5` | `93af2e4aea4cd8f55f3c33b1c8e9933f981bf667` |
| `backend/story_builder/prompts/styles/story_film.json` | `827043fa7c6330cec4160efb868bb47b252aa932cead2c25dae080c239a4d7ce` | `93a50d3e14d2598febf4a9deede07e134a81a653` |
| `backend/story_builder/prompts/director_profiles/production_types_v1.json` | `0d50674601074e4ff7ee1ed85fed5ca8a3958ba91abb401f5e135bf677f410cc` | `ecd406727e9accbbbaf2fe312672c533f32e4a34` |

The two Python helpers are copied unchanged. The new service uses their six-stage catalog validation and Director profile registry validation. It intentionally does not use the legacy style-catalog exact-equality gate for new types: a custom type is accepted only when it supplies all six non-empty guidance stages and a Director profile with non-empty `display_name`, `purpose`, `behavior`, and `review_priorities` fields.

## Service contract

`ProductionStyleService(ledger)` provides:

- `list_catalog()` returns the six validated bundled styles and the newest published version of each custom type, including hashes.
- `publish_custom_type(production_type, narrative_guidance, director_profile)` validates and appends a version; it rejects bundled IDs.
- `select(..., production_type, style_version_id=None)` appends a snapshot tied to exactly one `workspace_id` or `isolated_context_id`. Omitted version selects the current catalog entry; explicit IDs select frozen versions.
- `get_selection(snapshot_id)` and `list_selections(...)` retrieve prior snapshots after later selections.

The database records use the `production_style_versions` and `production_style_selections` tables in the existing ledger. Selection snapshots carry explicit `narrative_hash` and `director_profile_hash` fields. Downstream jobs do not consume these snapshots yet.

The base `director_profile_hash` is the copied registry content hash, matching the source helper; the frozen selected profile payload is included in every selection snapshot. Custom types hash their canonical profile object directly. The base hash therefore identifies the profile registry version, while the custom hash identifies the individual published profile.

## HTTP contract

- `GET /api/styles/catalog` returns `{catalog_version, production_types}`.
- `POST /api/styles/types` accepts `{production_type, narrative_guidance, director_profile}` and returns the published version (`201`). Guidance has `story`, `scene_direction`, `image`, `audio`, `video`, and `review` non-empty strings. The profile has non-empty `display_name`, `purpose`, `behavior[]`, and `review_priorities[]`.
- `POST /api/styles/selections` accepts exactly one context (`workspace_id` or `isolated_context_id`), `production_type`, and optional `style_version_id`; it returns the frozen selection (`201`). Story workspace IDs must exist. Isolated context IDs name setup contexts and do not create story rows.
- `GET /api/styles/selections?workspace_id=...` or `?isolated_context_id=...` returns `{selections:[...]}`. `GET /api/styles/selections/{snapshot_id}` returns one saved snapshot.

Malformed inputs return `422`; unknown workspace IDs and valid-shaped missing snapshot IDs return `404`. Providing a style version ID always resolves that exact ID; missing or mismatched explicit versions never fall back to the latest version.

## Verification

Focused CPU coverage is in `backend/story_builder/tests/test_production_styles.py`: six pinned bundled IDs, rejection of incomplete custom types, increasing immutable custom versions with preserved prior selection, and base selection hash/context pinning. HTTP coverage in `backend/story_builder/tests/test_production_style_api.py` checks catalog reads, custom validation, version publication, selection/reload/history, isolated contexts, unknown workspace/snapshot handling, and confirms setup routes do not probe generation/GPU services. These checks validate the setup foundation only, not media analysis or generation.

## UI integration and parent review — 2026-10-09

Ashu’s StudioShell now mounts ProductionStylesPage before Story. Guidance is readable text with six stage sections and Director purpose/behavior/review priorities. A manual new type is edited in normal labeled fields, explicitly published, then explicitly selected/saved. Publishing never auto-selects. Existing catalog records and versions are copied exactly. Pre-story setup uses a stable browser context ID, not a fabricated story workspace relationship. Existing workspace selection is supported by the API; linking this setup automatically to new Story/video artifacts is still pending under #18/#19.

Parent review corrected invalid API shapes, retained a pinned historical custom version even when catalog latest advances, and stopped uncertain POST errors from claiming no save occurred. After an uncertain selection/publication response, the affected button is disabled until successful read-only Refresh. Reload uses GET only. Publishing/selecting are append-only and do not yet use idempotency keys; after recovering the latest records the user must deliberately decide whether another publication/selection is intended. Browser context/draft persistence errors are shown. Malformed persisted form fields cannot crash trim/split.

Nine focused service/HTTP tests and Python compile checks passed. Frontend typecheck/build passed. Two focused intercepted journeys passed: explicit publish/select, historical v1 retention after v2 and GET-only reload; lost selection response with server commit, disabled retry, read-only recovery and no second POST. A real disposable backend/browser journey loaded six types, saved/reloaded a pinned base selection with one POST, and checked all three palettes. A fresh 390px mobile journey verified hidden sidebar, menu navigation and no horizontal overflow; zero browser errors. Existing Story behavior changed only explanatory copy; Video remains mounted off-route. No provider, GPU generation or broad legacy test rerun.

Remaining complete-feature work is tracked in issue #19: base-style variants, documents/media evidence and proposals, controlled video frame exports, recommended references, real context linking, downstream pins/staleness, and automatic style-video policy/capacity checks. These are not proven by a catalog or mocked picker.
