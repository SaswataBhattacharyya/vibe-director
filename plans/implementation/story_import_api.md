# Story source import and revision API slice

Status: implemented as a bounded local API slice in the current draft. This is source ingestion and revision access only; there is no Codex editing, graph extraction, screenplay generation, LLM, GPU, or render-job dispatch here. Product behavior remains governed by `plans/production_styles.md`, `plans/screenplay.md`, and the indexed current plans.

## Provenance and extraction boundary

Story Builder `services/narrative_style_sources.py` at `/home/riki/web_dev/story_builder` documents the safe `pdftotext -layout -enc UTF-8 - -` stdin/stdout technique (function `extract_style_source`, lines 46–100). Its existing evidence-block conversion drops blank-line structure and enforces a 10 MiB upload and 1.5M-character extracted-text cap. This implementation does not import that function or its output model. It adapts only the subprocess invocation pattern, streams the uploaded bytes to a product-owned temporary file, then uses `pdftotext` with that file as stdin and retains the full decoded stdout plus page and line codepoint spans. The source remains read-only.

TXT and Markdown decode strict UTF-8 and retain all decoded codepoints exactly, including CRLF/LF endings, blank lines, and a UTF-8 BOM as U+FEFF. Invalid UTF-8 is a 422 error. PDF extraction stores the original upload bytes and SHA256, full `pdftotext -layout` text and SHA256, page/line codepoint spans, extraction method/tool version, and warnings. Span offsets count Python Unicode codepoints; PDF page spans exclude form-feed separators, while the full returned text retains them. The immutable preview's serialized JSON hash is indexed in SQLite, so page/warning metadata is integrity-checked on reload along with the original file and extracted text. Reading order needs human preview; blank pages are flagged. A PDF with no text is retained as a preview with an explicit “OCR unavailable” warning. No OCR is performed.

Uploads are incrementally spooled in 64 KiB chunks using a reader bounded by WSGI `Content-Length`. A shorter-than-declared body is rejected before an import record is committed. The explicit transport limit defaults to 64 MiB and can be configured through `VIBE_DIRECTOR_STORY_BODY_MAX_BYTES`; a request exceeding it receives 413 and is never silently truncated. This is an operational request limit, not a story-length rule. PDF extraction has a 120-second process timeout. Managed originals and preview JSON live beneath `<VIBE_DIRECTOR_DATA_DIR>/story_imports/<import_id>/`; filenames are sanitized display metadata and are never treated as paths.

## Routes

All routes are local to the existing server on `127.0.0.1:3020`. There is no permissive CORS. Mutations require the listed content type.

| Method and route | Request | Result |
|---|---|---|
| `GET /api/story/workspaces?limit=50&offset=0` | — | Paginated `{items,limit,offset,total}`. An interrupted empty workspace is returned as `status: "initializing"`. |
| `POST /api/story/workspaces` | JSON `{title,source_text}` | Creates a workspace and initial immutable source revision. |
| `GET /api/story/workspaces/:id` | — | Workspace with current full revision/source. |
| `POST /api/story/workspaces/:id/revisions` | JSON `{source_text,expected_current_revision_id,metadata?}` | Creates a child revision if the expected pointer is current. |
| `GET /api/story/workspaces/:id/revisions?limit=50&offset=0` | — | Paginated immutable revision history, newest sequence first. |
| `POST /api/story/workspaces/:id/restore` | JSON `{revision_id,expected_current_revision_id}` | Creates a new child containing the selected old text; never rewinds the pointer. |
| `POST /api/story/imports?filename=...` | Raw `application/octet-stream` bytes | Creates a persistent immutable upload and preview; returns `{import_id,filename,source_type,source_sha256,text_sha256,text,warnings,pages,lines,extraction}`. |
| `GET /api/story/imports/:id` | — | Reloads the persisted preview after restart and checks original and preview hashes. |
| `POST /api/story/imports/:id/apply` | JSON `{title,source_text}` | Creates a workspace/revision from the reviewed or corrected text, recording import ID, original hash, extracted hash, source type, extractor version, and corrected-source hash in revision metadata. |

Workspace/revision identity and existing ledger optimistic concurrency are reused from the B2 authoring foundation. A stale expected revision returns 409. Malformed/unsupported input returns an explanatory 422; missing IDs return 404; truncated bodies return 400; over-limit uploads return 413. This local unauthenticated server does not emit 403. No route starts or probes a provider, GPU, video capability, or worker.

## Focused verification

Run from `backend/`:

```sh
PYTHONPATH=. python -m unittest story_builder.tests.test_story_import_api -v
```

The focused stdlib suite checks exact Unicode/blank-line/line-ending preservation, actual local `pdftotext` extraction/page spans, empty/scanned-PDF OCR messaging, persistent preview/hash lineage through restart, import application and stale-revision conflict, bounded keep-alive stream reads, truncated-body rejection, transport 413 without truncation, and absence of GPU/capability probing on story routes. These tests do not establish PDF reading-order correctness; the product preview/correction step remains required.

Next: connect the story workspace UI and reviewed import preview, then implement the Codex collaborator and source-linked graph/screenplay stages under their accepted product plans. This API slice does not make an upload a screenplay or create any story canon beyond the exact user-reviewed source revision.

Parent verification: six focused API tests passed, including actual local pdftotext. Actual HTTP browser upload/apply/save/restore/reload passed on disposable storage with zero page errors and no mobile overflow. No provider or render dispatched. Extraction-pattern source SHA256: `e67ace433c58b5e4d7a84d84ec698fad6a749b2f62e82d5b44fef52417d45019`. Creation/apply has no idempotency key yet; inspect the workspace list after an uncertain response before retrying.
