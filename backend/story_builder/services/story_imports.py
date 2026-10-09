"""Persistent, exact-text story imports for the local story API.

Text and Markdown preserve decoded UTF-8 codepoints and line endings. PDF
extraction uses pdftotext layout output as a preview; it never claims OCR or
reading-order correctness.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Any

from story_builder.services.production_ledger import LedgerNotFound, ProductionLedger


class StoryImportError(ValueError):
    def __init__(self, code: str, message: str, status: int = 422):
        super().__init__(message)
        self.code = code
        self.status = status


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _line_spans(text: str, *, start: int = 0, page_number: int = 1,
                first_line_number: int = 1) -> list[dict[str, int]]:
    spans = []
    offset = start
    for number, line in enumerate(text.splitlines(keepends=True), start=first_line_number):
        spans.append({"number": number, "page_number": page_number,
                      "start_codepoint": offset, "end_codepoint": offset + len(line)})
        offset += len(line)
    if text and not spans:
        spans.append({"number": first_line_number, "page_number": page_number,
                      "start_codepoint": start, "end_codepoint": start + len(text)})
    return spans


def _safe_filename(value: str) -> str:
    name = Path(value.replace("\\", "/")).name
    name = re.sub(r"[^A-Za-z0-9._ -]", "_", name).strip(" .")
    if not name or name in {".", ".."}:
        raise StoryImportError("invalid_filename", "Upload filename is empty or invalid.")
    return name[:180]


class StoryImports:
    def __init__(self, ledger: ProductionLedger, data_root: Path):
        self.ledger = ledger
        self.root = (Path(data_root).expanduser().resolve() / "story_imports").resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        with ledger._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS story_imports (
                import_id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_sha256 TEXT NOT NULL,
                text_sha256 TEXT NOT NULL,
                preview_sha256 TEXT NOT NULL DEFAULT '',
                byte_length INTEGER NOT NULL DEFAULT 0,
                extractor_version TEXT NOT NULL DEFAULT '',
                relative_path TEXT NOT NULL,
                preview_path TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""")
            columns = {row["name"] for row in db.execute("PRAGMA table_info(story_imports)")}
            for name, declaration in (("preview_sha256", "TEXT NOT NULL DEFAULT ''"),
                                      ("byte_length", "INTEGER NOT NULL DEFAULT 0"),
                                      ("extractor_version", "TEXT NOT NULL DEFAULT ''")):
                if name not in columns:
                    db.execute(f"ALTER TABLE story_imports ADD COLUMN {name} {declaration}")

    def import_bytes(self, *, filename: str, content: bytes) -> dict[str, Any]:
        if type(content) is not bytes:
            raise StoryImportError("invalid_upload", "Upload content must be raw bytes.")
        if not content:
            raise StoryImportError("empty_upload", "Upload must contain a non-empty file.")
        return self.import_stream(filename=filename, source_stream=io.BytesIO(content), max_bytes=len(content))

    def import_stream(self, *, filename: str, source_stream, max_bytes: int) -> dict[str, Any]:
        if type(max_bytes) is not int or max_bytes < 1:
            raise ValueError("Import byte limit must be a positive integer.")
        safe_name = _safe_filename(filename)
        suffix = Path(safe_name).suffix.lower()
        if suffix not in {".txt", ".md", ".markdown", ".pdf"}:
            raise StoryImportError("unsupported_file_type", "Upload a UTF-8 TXT/Markdown file or a PDF.")
        descriptor, temporary_name = tempfile.mkstemp(prefix=".story-upload-", dir=self.root)
        source_sha_hasher = hashlib.sha256()
        total_bytes = 0
        try:
            with os.fdopen(descriptor, "wb") as temporary:
                while True:
                    chunk = source_stream.read(64 * 1024)
                    if not chunk:
                        break
                    total_bytes += len(chunk)
                    if total_bytes > max_bytes:
                        raise StoryImportError("payload_too_large", f"Upload exceeds the configured {max_bytes}-byte transport limit; no bytes were stored.", 413)
                    source_sha_hasher.update(chunk)
                    temporary.write(chunk)
                if getattr(source_stream, "remaining", 0) != 0:
                    raise StoryImportError("upload_truncated", "Upload ended before its declared Content-Length was received.", 400)
                temporary.flush()
                os.fsync(temporary.fileno())
            if total_bytes == 0:
                raise StoryImportError("empty_upload", "Upload must contain a non-empty file.")
            source_sha = source_sha_hasher.hexdigest()
            source_path = Path(temporary_name)
            if suffix == ".pdf":
                text, pages, lines, warnings, extractor_version = self._extract_pdf_file(source_path)
                source_type = "pdf"
            else:
                try:
                    text = source_path.read_bytes().decode("utf-8", errors="strict")
                except UnicodeDecodeError as exc:
                    raise StoryImportError("invalid_utf8", "TXT and Markdown uploads must be valid UTF-8.") from exc
                source_type = "markdown" if suffix in {".md", ".markdown"} else "text"
                pages = [{"number": 1, "start_codepoint": 0, "end_codepoint": len(text)}]
                lines = _line_spans(text)
                pages[0]["line_start"] = lines[0]["number"] if lines else 1
                pages[0]["line_end"] = lines[-1]["number"] if lines else 0
                warnings = []
                extractor_version = "story-import-adapter/1; strict-python-utf8"
            return self._persist_preview(safe_name=safe_name, suffix=suffix, source_type=source_type,
                source_path=source_path, source_sha=source_sha, text=text, pages=pages,
                lines=lines, warnings=warnings, extractor_version=extractor_version)
        finally:
            try:
                os.unlink(temporary_name)
            except OSError:
                pass

    def _persist_preview(self, *, safe_name: str, suffix: str, source_type: str,
                         source_path: Path, source_sha: str, text: str,
                         pages: list[dict[str, int]], lines: list[dict[str, int]],
                         warnings: list[str], extractor_version: str) -> dict[str, Any]:
        if not text.strip():
            warnings.append("No readable text was extracted. OCR is unavailable; use a text/Markdown source or correct the preview manually before applying.")
        import_id = f"import-{uuid.uuid4().hex}"
        directory = self.root / import_id
        directory.mkdir(mode=0o700)
        original_name = f"original{suffix}"
        original_path = directory / original_name
        preview_path = directory / "preview.json"
        text_sha = _sha_text(text)
        preview = {"import_id": import_id, "filename": safe_name, "source_type": source_type,
            "source_sha256": source_sha, "text_sha256": text_sha, "text": text,
            "warnings": warnings, "pages": pages, "lines": lines, "extraction": {
                "method": "pdftotext -layout" if suffix == ".pdf" else "utf-8-exact",
                "extractor_version": extractor_version,
                "byte_length": source_path.stat().st_size,
                "offset_unit": "python_unicode_codepoints; page spans exclude form-feed separators",
                "ocr_available": False if suffix == ".pdf" else None,
                "utf8_bom_preserved": suffix != ".pdf"}}
        try:
            os.replace(source_path, original_path)
            preview_bytes = json.dumps(preview, ensure_ascii=False, indent=2).encode("utf-8")
            self._write_new(preview_path, preview_bytes)
            rel_original = original_path.relative_to(self.root).as_posix()
            rel_preview = preview_path.relative_to(self.root).as_posix()
            with self.ledger._connect() as db:
                db.execute("INSERT INTO story_imports(import_id,filename,source_type,source_sha256,text_sha256,preview_sha256,byte_length,extractor_version,relative_path,preview_path) VALUES(?,?,?,?,?,?,?,?,?,?)",
                    (import_id, safe_name, source_type, source_sha, text_sha,
                     _sha_bytes(preview_bytes), preview["extraction"]["byte_length"], extractor_version,
                     rel_original, rel_preview))
        except Exception:
            shutil.rmtree(directory, ignore_errors=True)
            raise
        return preview

    @staticmethod
    def _write_new(path: Path, content: bytes) -> None:
        descriptor, temporary = tempfile.mkstemp(prefix=".upload-", dir=path.parent)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            # Exclusive destination creation prevents accidental replacement.
            os.link(temporary, path)
        finally:
            try:
                os.unlink(temporary)
            except OSError:
                pass

    @staticmethod
    def _extract_pdf_file(source_path: Path) -> tuple[str, list[dict[str, int]], list[dict[str, int]], list[str], str]:
        executable = shutil.which("pdftotext")
        if executable is None:
            raise StoryImportError("pdf_extractor_unavailable", "PDF text extraction is unavailable because pdftotext is not installed. TXT and Markdown imports remain available.", 422)
        try:
            try:
                version_result = subprocess.run([executable, "-v"], stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE, check=False, timeout=5)
                version_text = (version_result.stdout or version_result.stderr).decode("utf-8", "replace").strip().splitlines()
                tool_version = version_text[0] if version_text else "pdftotext version unknown"
            except (subprocess.TimeoutExpired, OSError):
                tool_version = "pdftotext version unavailable"
            extractor_version = "story-import-adapter/1; " + tool_version
            with source_path.open("rb") as source_stream:
                result = subprocess.run([executable, "-layout", "-enc", "UTF-8", "-", "-"],
                    stdin=source_stream, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=120)
        except subprocess.TimeoutExpired as exc:
            raise StoryImportError("pdf_extraction_timeout", "PDF extraction exceeded 120 seconds; try a smaller or text-based PDF.") from exc
        except OSError as exc:
            raise StoryImportError("pdf_extraction_failed", "Could not start pdftotext.") from exc
        if result.returncode != 0:
            message = result.stderr.decode("utf-8", "replace").strip()[:500]
            raise StoryImportError("pdf_extraction_failed", "pdftotext could not read this PDF." + (f" {message}" if message else ""))
        try:
            text = result.stdout.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise StoryImportError("pdf_extraction_encoding", "pdftotext returned invalid UTF-8.") from exc
        warnings = ["PDF reading order and layout require preview; pdftotext output is not OCR or a semantic reconstruction."]
        # pdftotext marks page boundaries with form feeds. Preserve the complete
        # stdout string and report exact codepoint spans excluding separators.
        pages = []
        all_lines = []
        offset = 0
        line_number = 1
        segments = text.split("\f")
        if text.endswith("\f"):
            segments.pop()
        for number, segment in enumerate(segments, start=1):
            segment_lines = _line_spans(segment, start=offset, page_number=number,
                                        first_line_number=line_number)
            all_lines.extend(segment_lines)
            pages.append({"number": number, "start_codepoint": offset,
                          "end_codepoint": offset + len(segment),
                          "line_start": segment_lines[0]["number"] if segment_lines else line_number,
                          "line_end": segment_lines[-1]["number"] if segment_lines else line_number - 1})
            line_number += len(segment_lines)
            if not segment.strip():
                warnings.append(f"PDF page {number} produced no text; inspect and correct the preview before applying.")
            offset += len(segment) + 1
        return text, pages, all_lines, warnings, extractor_version

    def get(self, import_id: str) -> dict[str, Any]:
        if type(import_id) is not str or not re.fullmatch(r"import-[a-f0-9]{32}", import_id):
            raise LedgerNotFound("Story import not found.")
        with self.ledger._connect() as db:
            row = db.execute("SELECT * FROM story_imports WHERE import_id=?", (import_id,)).fetchone()
        if row is None:
            raise LedgerNotFound("Story import not found.")
        preview_path = (self.root / row["preview_path"]).resolve()
        original = (self.root / row["relative_path"]).resolve()
        if not preview_path.is_relative_to(self.root) or not original.is_relative_to(self.root):
            raise ValueError("Stored story import paths escape the configured data root.")
        if _sha_file(preview_path) != row["preview_sha256"]:
            raise ValueError("Stored story import preview metadata failed its integrity check.")
        preview = json.loads(preview_path.read_text(encoding="utf-8"))
        if (preview.get("import_id") != import_id or preview.get("source_sha256") != row["source_sha256"]
                or preview.get("text_sha256") != row["text_sha256"]
                or _sha_text(preview.get("text", "")) != row["text_sha256"]
                or preview.get("extraction", {}).get("byte_length") != row["byte_length"]
                or preview.get("extraction", {}).get("extractor_version") != row["extractor_version"]):
            raise ValueError("Stored story import preview failed its integrity check.")
        if not original.is_file() or _sha_file(original) != row["source_sha256"]:
            raise ValueError("Stored original upload failed its integrity check.")
        return preview
