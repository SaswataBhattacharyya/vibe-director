# Story creation request recovery

This backend slice adds durable idempotency to story workspace creation and import application. It prevents a lost HTTP response from leaving the browser unsure whether it created another workspace. It does not add a second execution controller and does not perform provider, GPU, or video work.

## Durable record and transaction boundary

`story_creation_requests` shares the existing `ProductionLedger` SQLite database. A request key is a lowercase canonical UUID. The row freezes its action (`create` or `apply`), exact client payload (title, full source text, and import ID when applying), request hash, resolved import/source metadata, and associated workspace ID. The request row and workspace row are inserted in one `BEGIN IMMEDIATE` transaction. The existing immutable story revision writer creates the initial revision; its DB transaction advances the workspace pointer and marks this request ready with its `initial_revision_id` atomically.

No retry can insert a second workspace for the same key. An identical POST can resume a request left in `initializing` after process interruption. Concurrent identical POSTs may both try to finish initialization, but workspace pointer CAS plus unique revision numbering allows only one initial revision to commit; a losing request reloads the committed winner. Request lookup is read-only. It reports the initial created revision separately from the workspace's current pointer so later edits do not change the creation result.

Same key plus same action and exact payload returns the original request/workspace. Reusing the key for another action, title, source text, or import ID returns 409. Import metadata is resolved only when the request row is first inserted and is then frozen; replay does not reread or reinterpret the import preview.

## HTTP contract

Keyed requests use a JSON `idempotency_key`; browser code should generate and persist one before POSTing. Unkeyed POSTs retain their prior workspace-shaped response for compatibility, but the browser flow should always send a key.

- `POST /api/story/workspaces` with `{idempotency_key,title,source_text}` creates a workspace.
- `POST /api/story/imports/:import_id/apply` with `{idempotency_key,title,source_text}` creates a workspace from the reviewed/corrected import text.
- A first accepted request returns `201 Created`; an identical replay/resume returns `200 OK`. Both return `{status:"ready"|"initializing",idempotency_key,request_hash,workspace}`.
- `workspace` includes the stable workspace ID, initialization/current-pointer state, current revision ID, and `created_revision` when ready. `created_revision` is the immutable initial revision associated with the creation request.
- `GET /api/story/creations/by-idempotency/:key` is read-only: 200 with the stored envelope, including `status:"initializing"` when first-revision initialization has not committed; 404 when no such key exists.
- Same-key payload/action mismatch returns 409. Invalid key/request returns 422. An initializing request is resumed only by an explicit matching POST; GET does not write or retry it.

The request hash includes action, exact client payload, and the source/import lineage frozen on initial insertion. No extracted text is silently truncated. These are local unauthenticated routes; 403 is not used.

## Focused evidence

Run from `backend/`:

```sh
PYTHONPATH=. python -m unittest story_builder.tests.test_story_creation_recovery -v
```

The stdlib tests cover lost-response replay after restart, stable initial-revision identity after later edits, apply metadata frozen across replay, different-payload/action conflict, eight concurrent identical POSTs sharing one workspace and initial revision, a simulated interruption followed by read-only GET and explicit resumption, and the HTTP status/lookup contract. They do not run the broad application suite or any provider/GPU/runtime.

## Browser integration and reviewed evidence — 2026-10-09

The browser persists a UUID plus the exact submitted create/apply payload before POST. Recovery on mount uses GET only. Explicit retry is offered after a missing-key lookup or an initializing result; uncertain status and key conflicts block retry. Editable inputs remain separate from the frozen request. A ready response reads `workspace.created_revision`; if the live pointer has advanced, the editor retrieves the current revision instead. Browser storage failure blocks new creation and offers a text download.

Integrated into Ashu's three-theme StudioShell without replacing its layout or theme files. Five focused intercepted Story browser checks passed, including lost import-apply response and reload recovery; typecheck and build passed. Five recovery CPU checks and the seven existing authoring foundation checks passed during backend review. A real disposable backend/browser journey committed one creation, deliberately lost its response, reloaded, recovered the same workspace and exact Unicode source, and sent no second creation POST; zero browser errors. Earlier harness attempts used separate disposable workspace keys and were corrected; no product data was used. No broad legacy suite, provider, asset generation or GPU test was repeated.
