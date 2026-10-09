from __future__ import annotations

import hashlib
import io
import json
import shutil
import tempfile
import unittest
import warnings
from pathlib import Path

from story_builder.isolated_server import create_app
from story_builder.services.production_ledger import ProductionLedger
from story_builder.services.story_imports import StoryImportError, StoryImports


def _minimal_pdf(text: str = "PDF story text") -> bytes:
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    result = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(result))
        result.extend(f"{number} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(result)
    result.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        result.extend(f"{offset:010d} 00000 n \n".encode())
    result.extend(f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return bytes(result)


class StoryImportApiTests(unittest.TestCase):
    def setUp(self):
        warnings.simplefilter("ignore", ResourceWarning)
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "data"
        self.ledger = ProductionLedger(self.root / "storage/production/ledger.sqlite3")
        self.imports = StoryImports(self.ledger, self.root)

    def test_text_markdown_preserves_unicode_blank_lines_and_line_endings(self):
        original = "# Title\r\n\r\nFirst 🌒 line.\n\nLast line.\r\n".encode("utf-8")
        result = self.imports.import_bytes(filename="../input.md", content=original)
        self.assertEqual(result["text"], original.decode("utf-8"))
        self.assertEqual(result["filename"], "input.md")
        self.assertEqual(result["source_sha256"], hashlib.sha256(original).hexdigest())
        self.assertEqual(result["extraction"]["byte_length"], len(original))
        self.assertTrue(result["extraction"]["extractor_version"].startswith("story-import-adapter/1"))
        self.assertEqual("".join(result["text"][span["start_codepoint"]:span["end_codepoint"]]
            for span in result["lines"]), result["text"])
        restarted = StoryImports(ProductionLedger(self.root / "storage/production/ledger.sqlite3"), self.root)
        self.assertEqual(restarted.get(result["import_id"]), result)
        preview_path = self.root / "story_imports" / result["import_id"] / "preview.json"
        preview_path.write_text(preview_path.read_text(encoding="utf-8").replace("line_start", "tampered"), encoding="utf-8")
        with self.assertRaises(ValueError):
            restarted.get(result["import_id"])

    @unittest.skipUnless(shutil.which("pdftotext"), "pdftotext unavailable")
    def test_pdf_extraction_has_page_spans_and_preview_warning(self):
        result = self.imports.import_bytes(filename="story.pdf", content=_minimal_pdf())
        self.assertEqual(result["source_type"], "pdf")
        self.assertIn("PDF story text", result["text"])
        self.assertEqual(result["pages"][0]["number"], 1)
        page = result["pages"][0]
        self.assertEqual(result["text"][page["start_codepoint"]:page["end_codepoint"]].strip(), result["text"].strip())
        self.assertTrue(any("reading order" in warning.lower() for warning in result["warnings"]))

    @unittest.skipUnless(shutil.which("pdftotext"), "pdftotext unavailable")
    def test_scanned_or_empty_pdf_explains_ocr_unavailable(self):
        result = self.imports.import_bytes(filename="scan.pdf", content=_minimal_pdf(""))
        self.assertEqual(result["text"].strip(), "")
        self.assertTrue(any("OCR is unavailable" in warning for warning in result["warnings"]))

    def test_story_routes_apply_import_lineage_and_reject_stale_revision(self):
        app = create_app(data_root=self.root, graph_path=Path(__file__).resolve().parents[1] / "workflows/api/minimax_h3_t2v_api.json",
            capability_provider=lambda: self.fail("story route probed generation capability"),
            gpu_reader=lambda: self.fail("story route read GPU"), story_body_max_bytes=4096)

        def call(method, path, body=b"", content_type="application/json", declared_length=None):
            started = []
            query_path, _, query = path.partition("?")
            environ = {"REQUEST_METHOD": method, "PATH_INFO": query_path, "QUERY_STRING": query,
                "CONTENT_TYPE": content_type, "CONTENT_LENGTH": str(len(body) if declared_length is None else declared_length), "wsgi.input": io.BytesIO(body)}
            response = b"".join(app(environ, lambda status, headers: started.append(status)))
            return started[0], json.loads(response) if response.startswith(b"{") else response

        raw = b"Start\r\n\r\nA moonlit road.\n"
        status, preview = call("POST", "/api/story/imports?filename=story.txt", raw, "application/octet-stream")
        self.assertEqual(status, "201 Created")
        status, recovered = call("GET", f"/api/story/imports/{preview['import_id']}")
        self.assertEqual(status, "200 OK")
        self.assertEqual(recovered["text"], raw.decode())
        payload = json.dumps({"title": "Imported", "source_text": recovered["text"]}).encode()
        status, workspace = call("POST", f"/api/story/imports/{preview['import_id']}/apply", payload)
        self.assertEqual(status, "201 Created")
        revision = workspace["current_revision"]
        self.assertEqual(revision["metadata"]["import_id"], preview["import_id"])
        self.assertEqual(revision["metadata"]["original_sha256"], preview["source_sha256"])
        self.assertEqual(revision["metadata"]["extracted_text_sha256"], preview["text_sha256"])
        status, listing = call("GET", "/api/story/workspaces?limit=10&offset=0")
        self.assertEqual(status, "200 OK")
        self.assertEqual(listing["total"], 1)
        status, loaded = call("GET", f"/api/story/workspaces/{workspace['workspace_id']}")
        self.assertEqual(status, "200 OK")
        self.assertEqual(loaded["current_revision"]["source_text"], recovered["text"])
        status, history = call("GET", f"/api/story/workspaces/{workspace['workspace_id']}/revisions?limit=10")
        self.assertEqual(status, "200 OK")
        self.assertEqual(history["total"], 1)
        status, restored = call("POST", f"/api/story/workspaces/{workspace['workspace_id']}/restore",
            json.dumps({"revision_id": revision["revision_id"],
                        "expected_current_revision_id": revision["revision_id"]}).encode())
        self.assertEqual(status, "201 Created")
        self.assertEqual(restored["parent_revision_id"], revision["revision_id"])
        status, changed = call("POST", f"/api/story/workspaces/{workspace['workspace_id']}/revisions",
            json.dumps({"source_text": "new", "expected_current_revision_id": revision["revision_id"]}).encode())
        self.assertEqual(status, "409 Conflict")
        self.assertEqual(self.ledger.list_runs(project_id="unused"), [])

    def test_stream_reader_stops_at_content_length_and_rejects_truncated_upload(self):
        app = create_app(data_root=self.root, graph_path=Path(__file__).resolve().parents[1] / "workflows/api/minimax_h3_t2v_api.json",
            story_body_max_bytes=64)
        raw_body = b"storyNEXT_REQUEST"
        stream = io.BytesIO(raw_body)
        body = b""
        # Exercise the same bounded reader used by the route, including an
        # underlying stream with additional bytes from a keep-alive request.
        from story_builder.isolated_server import ContentLengthReader
        reader = ContentLengthReader(stream, len(b"story"))
        while chunk := reader.read(64 * 1024):
            body += chunk
        self.assertEqual(body, b"story")
        self.assertEqual(stream.tell(), len(b"story"))

        started = []
        actual = b"short"
        environ = {"REQUEST_METHOD": "POST", "PATH_INFO": "/api/story/imports", "QUERY_STRING": "filename=short.txt",
            "CONTENT_TYPE": "application/octet-stream", "CONTENT_LENGTH": str(len(actual) + 1),
            "wsgi.input": io.BytesIO(actual)}
        response = b"".join(app(environ, lambda status, headers: started.append(status)))
        self.assertEqual(started[0], "400 Bad Request")
        self.assertEqual(json.loads(response)["error"]["code"], "upload_truncated")
        with self.ledger._connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM story_imports").fetchone()[0], 0)

    def test_upload_byte_limit_returns_413_without_truncation(self):
        with self.assertRaises(StoryImportError) as raised:
            self.imports.import_stream(filename="large.txt", source_stream=io.BytesIO(b"12345"), max_bytes=4)
        self.assertEqual(raised.exception.status, 413)


if __name__ == "__main__":
    unittest.main()
