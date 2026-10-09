# Provisional Story authoring and import UI

## Scope

This frontend-only slice adds `#/story`, preserving the mounted Video workspace and its job recovery state while navigating. Users can create and select story workspaces, edit source text as-is, save revisions against an expected current revision, browse paginated history, and restore old text by creating a new child revision. Source drafts are stored locally with their base revision. Conflicts preserve editor text and require an explicit server reload; reload does not force an overwrite. No input length cap or automatic source rewriting is applied.

TXT, Markdown, and PDF files are submitted to the extraction endpoint for preview. Server errors use `{error:{code,message}}`. Pagination uses numeric offsets and totals. A successful save/restore response supplies the new revision source directly, so a later history refresh failure cannot turn a committed save into a reported failure. Form and import-preview drafts are also stored locally. If browser storage fails, the UI warns that the draft may not survive reload and offers a text download fallback. Editing textareas are disabled while a save/restore request is pending. The preview shows original filename/type, SHA-256, PDF pages when returned, extraction warnings and editable extracted text. Upload alone does not create a workspace; the user must explicitly apply the preview, which creates a new workspace. Editing, switching, saving, and restore are explicit actions. Reloading never issues a write request.

## Deferred production setup

Codex chat integration, story graph, screenplay fields, and deferred style setup are visibly pending and are not represented by fake annotations or default values. This slice does not satisfy production style setup requirements; production work that requires completed style setup remains blocked until that capability is implemented.

## API contract used

- `GET /api/story/workspaces?limit=50&offset=0` returns `{items,limit,offset,total}` summary rows; initializing rows have no current source and remain unavailable until refreshed. `GET /api/story/workspaces/{id}` provides the current revision source when initialized.
- `POST /api/story/workspaces` creates a workspace with `{title, source_text}`.
- `POST /api/story/workspaces/{id}/revisions` saves `{source_text, expected_current_revision_id}`; `409` keeps the local draft intact.
- `GET /api/story/workspaces/{id}/revisions?limit=50&offset=0` returns summary metadata (IDs, hashes, parent, revision number, timestamp), not source previews; `POST /api/story/workspaces/{id}/restore` restores `{revision_id, expected_current_revision_id}` as a new revision.
- `POST /api/story/imports?filename=...` sends raw `application/octet-stream` file bytes and returns extracted text plus source metadata; `POST /api/story/imports/{id}/apply` explicitly creates a workspace.

## Focused checks

Four mocked browser journeys cover editable import preview and explicit apply/save/reload without automatic writes, stale-revision conflict preserving the local draft, recoverable workspace initialization, and storage failure with an export fallback. All story API calls are intercepted; no generation or provider endpoints are used.
