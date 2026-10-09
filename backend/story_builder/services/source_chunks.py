"""Provenance-preserving source chunk primitives extracted for story revisions.

Source: mooV_E_maker/services/chunked_generation.py at
2023bf5bce1a808b2624fb5789b4b2a1e8b7b8db (SourceChunk and
split_source_text only). Kept provider-free for source indexing and CPU tests.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceChunk:
    chunk_id: str
    index: int
    start: int
    end: int
    text: str



def split_source_text(text: str, *, max_chars: int = 2400) -> list[SourceChunk]:
    """Partition text into contiguous exact slices; no source characters drop."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("A non-empty story source is required.")
    if max_chars < 128:
        raise ValueError("max_chars must be at least 128 characters.")
    chunks: list[SourceChunk] = []
    start, index, length = 0, 1, len(text)
    while start < length:
        target = min(length, start + max_chars)
        end = target
        if target < length:
            minimum = start + max(1, max_chars // 2)
            candidates = [text.rfind("\n\n", minimum, target), text.rfind("\n", minimum, target),
                          text.rfind(". ", minimum, target), text.rfind("! ", minimum, target),
                          text.rfind("? ", minimum, target), text.rfind(" ", minimum, target)]
            boundary = max(candidates)
            if boundary >= minimum:
                end = boundary + (2 if text[boundary:boundary + 2] in {"\n\n", ". ", "! ", "? "} else 1)
        if end <= start:
            end = min(length, start + max_chars)
        chunks.append(SourceChunk(f"story_chunk_{index:04d}", index, start, end, text[start:end]))
        start, index = end, index + 1
    if not chunks or chunks[0].start != 0 or chunks[-1].end != length:
        raise RuntimeError("Internal source chunking error: source coverage is incomplete.")
    if any(left.end != right.start for left, right in zip(chunks, chunks[1:])):
        raise RuntimeError("Internal source chunking error: source chunks contain a gap or overlap.")
    return chunks

