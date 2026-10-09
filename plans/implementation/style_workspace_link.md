# Pre-story style selection linked to Story creation

## Contract

Keyed story creation and keyed import application accept an optional `style_selection_snapshot_id`:

- `POST /api/story/workspaces` accepts `{idempotency_key,title,source_text,style_selection_snapshot_id?}`.
- `POST /api/story/imports/:import_id/apply` accepts `{idempotency_key,title,source_text,style_selection_snapshot_id?}`.
- The ID is a 32-character lowercase hexadecimal ID from an existing immutable style selection. Omitted and `null` mean no style pin and preserve the pre-existing no-style request hash.
- Non-null style pins require a keyed request. A non-keyed legacy create/apply without a pin retains its prior behavior; adding a non-null pin without an idempotency key returns 422.
- A style pin must resolve before the story-creation request or workspace row is reserved. Unknown IDs return 404; malformed IDs and invalid shapes return 422.
- The selected immutable snapshot is copied into the original creation request's frozen `source_metadata.style_selection` and into the initial Story revision metadata. Import lineage is retained next to it.
- The style snapshot ID is included in the keyed client payload hash. Reusing a key with another style ID, or removing a previously supplied ID, returns 409. Exact retries use the previously frozen metadata and do not resolve the current/latest selection again.

Read surfaces preserve the original creation pin even after subsequent story revisions:

- `GET /api/story/workspaces/:workspace_id` exposes top-level `style_selection_snapshot_id` and the full `style_selection` snapshot. Both are `null` for older or unstyled workspaces.
- The keyed create/apply response and `GET /api/story/creations/by-idempotency/:key` expose the same two fields inside `workspace`; the creation envelope also includes the original `workspace.created_revision.metadata.style_selection`.
- `GET /api/story/workspaces` summaries expose `style_selection_snapshot_id` or `null`, without duplicating the full snapshot.

Pre-story selections remain attached to their original isolated setup context. Creating a story copies the frozen snapshot reference into Story creation records; it does not mutate, transfer, or delete the selection/context record.

## Implementation boundary

This is durable setup lineage only. `style_selection` in revision metadata is not evidence that downstream prompts/jobs consume its guidance. No generation compiler, provider, media analyzer, style-reference asset, or job submission behavior is added here. The shared Story UI explicitly chooses a saved setup snapshot for creation or import application. The resolver is called only for a new keyed creation request; request replays rely on the frozen original payload. Unknown snapshot resolution occurs before reserving a creation key/workspace.

## Focused verification

Run from `backend/`:

```sh
PYTHONPATH=. python -m unittest story_builder.tests.test_story_style_link -v
```

The three focused CPU tests cover keyed create/reload after a newer selection, keyed import-apply with preserved source lineage and replay, same-key changed-pin conflict, and unknown-snapshot rejection before any workspace/request is created. These do not test downstream prompt conditioning or generation.

## Integrated UI review
Ashu shell and all themes retained; optional explicit selection defaults to none, existing keys preserve omitted style fields, pending creation freezes the snapshot ID. Loaded workspace pins come from backend originals and survive newer setup versions. Unavailable chosen IDs remain visible rather than falsely appearing unstyled. Saved-time labels distinguish repeated snapshots. React StrictMode setup mount reuses the persisted context instead of creating another ID. Three focused backend checks, frontend typecheck/build, one intercepted lost-response/reload/change-setup journey and real local select/create/reload Unicode/mobile journey pass; zero browser errors, reload no POST, no media/provider generation or legacy broad suite. Parent fixed ambiguous test locators and reviewed summary queries to avoid fetching source text for pin display. Downstream guidance conditioning/task scopes still pending (#19/#18).
