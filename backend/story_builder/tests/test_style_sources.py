from __future__ import annotations

import hashlib
import json
import subprocess

import pytest

from story_builder.services import style_sources as sources


def test_text_source_has_stable_line_provenance_and_hash():
    result = sources.extract_style_source("guide.txt", b"First rule.\nSecond line.\n\nAnother rule.\n")
    assert result["source_type"] == "text"
    assert result["sha256"]
    assert result["evidence_blocks"] == [
        {"locator": "line:1-2", "text": "First rule.\nSecond line."},
        {"locator": "line:4-4", "text": "Another rule."},
    ]


def test_markdown_utf8_bom_is_supported_but_video_is_rejected():
    result = sources.extract_style_source("rules.md", b"\xef\xbb\xbf# Style\n\nUse quiet dialogue.")
    assert result["source_type"] == "markdown"
    assert result["evidence_blocks"][0]["locator"] == "line:1-1"
    with pytest.raises(sources.StyleSourceError) as error:
        sources.extract_style_source("reference.mp4", b"not a narrative style source")
    assert error.value.code == "unsupported_style_source"


def test_pdf_extraction_records_page_and_line_locators(monkeypatch):
    monkeypatch.setattr(sources.shutil, "which", lambda _name: "/usr/bin/pdftotext")
    monkeypatch.setattr(sources.subprocess, "run", lambda *_args, **_kwargs: subprocess.CompletedProcess(
        args=["pdftotext"], returncode=0, stdout=b"Rule one\n\n\fRule two\n", stderr=b""))
    result = sources.extract_style_source("guide.pdf", b"%PDF mock")
    assert result["source_type"] == "pdf"
    assert result["evidence_blocks"] == [
        {"locator": "page:1:line:1-1", "text": "Rule one"},
        {"locator": "page:2:line:1-1", "text": "Rule two"},
    ]


def test_pdf_extraction_failure_and_unavailable_tool_are_actionable(monkeypatch):
    monkeypatch.setattr(sources.shutil, "which", lambda _name: None)
    with pytest.raises(sources.StyleSourceError, match="pdftotext is not installed"):
        sources.extract_style_source("guide.pdf", b"%PDF mock")
    monkeypatch.setattr(sources.shutil, "which", lambda _name: "/usr/bin/pdftotext")
    monkeypatch.setattr(sources.subprocess, "run", lambda *_args, **_kwargs: subprocess.CompletedProcess(
        args=["pdftotext"], returncode=1, stdout=b"", stderr=b"bad xref"))
    with pytest.raises(sources.StyleSourceError) as error:
        sources.extract_style_source("guide.pdf", b"%PDF mock")
    assert error.value.code == "invalid_pdf"


def test_empty_oversized_and_non_utf8_sources_fail_before_processing():
    with pytest.raises(sources.StyleSourceError) as empty:
        sources.extract_style_source("guide.txt", b"")
    assert empty.value.code == "empty_style_source"
    with pytest.raises(sources.StyleSourceError) as large:
        sources.extract_style_source("guide.txt", b"x" * 20, max_bytes=10)
    assert large.value.code == "style_source_too_large"
    with pytest.raises(sources.StyleSourceError) as encoding:
        sources.extract_style_source("guide.md", b"\xff\xfe")
    assert encoding.value.code == "style_source_encoding_invalid"


def test_source_store_is_hash_addressed_deduplicated_and_integrity_checked(tmp_path):
    content = b"A quiet, restrained narrative style.\n"
    first = sources.store_style_source(tmp_path / "library", "rules.txt", content)
    second = sources.store_style_source(tmp_path / "library", "renamed.txt", content)
    assert first["deduplicated"] is False
    assert second["deduplicated"] is True
    assert first["source_id"] == second["source_id"]
    assert first["sha256"] == hashlib.sha256(content).hexdigest()
    assert len(list((tmp_path / "library" / "sources").glob("*.source"))) == 1
    assert len(sources.list_style_sources(tmp_path / "library")) == 1

    metadata = tmp_path / "library" / "sources" / f"{first['source_id']}.json"
    record = json.loads(metadata.read_text())
    record["sha256"] = "0" * 64
    metadata.write_text(json.dumps(record))
    with pytest.raises(sources.StyleSourceError) as conflict:
        sources.store_style_source(tmp_path / "library", "rules.txt", content)
    assert conflict.value.code == "style_source_hash_conflict"


def test_style_proposal_checks_exact_quote_and_returns_unpublished_citations(tmp_path):
    root = tmp_path / "library"
    source = sources.store_style_source(root, "rules.txt", b"Use quiet dialogue.\n")
    valid = {"display_name": "Quiet Film", "guidance": "Use quiet dialogue.", "evidence": [{
        "source_id": source["source_id"], "locator": "line:1-1",
        "quote": "Use quiet dialogue.", "intent": "Keep dialogue restrained."}]}
    proposal = sources.propose_style_guidance(root, [source["source_id"]], generator=lambda **_kwargs: valid)
    assert proposal["published"] is False and proposal["persisted"] is False
    assert proposal["evidence"][0]["source_sha256"] == source["sha256"]

    invalid = {**valid, "evidence": [{**valid["evidence"][0], "quote": "Invented source claim."}]}
    with pytest.raises(sources.StyleSourceError) as error:
        sources.propose_style_guidance(root, [source["source_id"]], generator=lambda **_kwargs: invalid)
    assert error.value.code == "style_analysis_uncited"


def test_media_style_proposal_cites_analyzer_text_and_only_attaches_images():
    refs = [
        {"asset_id": "image-1", "kind": "image", "sha256": "a" * 64,
         "filename": "frame.png", "path": "/safe/frame.png"},
        {"asset_id": "audio-1", "kind": "audio", "sha256": "b" * 64,
         "filename": "score.wav", "analyzer_run_id": "run-1", "locator": "12-18s",
         "source_text": "Low strings swell under distant dialogue."},
    ]
    received = {}
    result = {"display_name": "Quiet Tension", "guidance": "Use restrained framing and low strings.",
        "evidence": [{"asset_id": "image-1", "intent": "Use narrow framing."},
            {"asset_id": "audio-1", "intent": "Use restrained low strings.",
             "quote": "Low strings swell under distant dialogue."}]}
    proposal = sources.propose_image_style_guidance(refs,
        generator=lambda **kwargs: (received.update(kwargs) or result))
    assert received["image_paths"] == ["/safe/frame.png"]
    assert "do not claim to hear or view" in received["prompt"]
    assert proposal["evidence"][1] == {"kind": "audio", "asset_id": "audio-1",
        "sha256": "b" * 64, "intent": "Use restrained low strings.",
        "quote": "Low strings swell under distant dialogue.", "locator": "12-18s",
        "analyzer_run_id": "run-1"}

    result["evidence"][1]["quote"] = "The clip sounds joyful."
    with pytest.raises(sources.StyleSourceError) as error:
        sources.propose_image_style_guidance(refs, generator=lambda **_kwargs: result)
    assert error.value.code == "style_analysis_uncited"
