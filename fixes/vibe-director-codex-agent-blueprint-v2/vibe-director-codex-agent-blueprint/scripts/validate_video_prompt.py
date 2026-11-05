#!/usr/bin/env python3
"""Validate a Vibe Director prompt's basic textual constraints.

Usage: python scripts/validate_video_prompt.py examples/minimax-h3-scene5-prompt.txt --max-chars 7000 --duration 15 --manifest examples/scene5-rescue.json

This is a small preflight check, not a model-compatibility or action-physics validator.
"""
import argparse
import json
import re
import sys
from pathlib import Path


def to_s(mm, ss):
    return int(mm) * 60 + int(ss)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("prompt", type=Path)
    parser.add_argument("--max-chars", type=int, default=7000)
    parser.add_argument("--duration", type=int, default=15)
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()
    raw = args.prompt.read_text(encoding="utf-8")
    errors = []
    if len(raw) > args.max_chars:
        errors.append(f"Prompt too long: {len(raw)} > {args.max_chars} characters")
    timeline = []
    for m in re.finditer(r"\[(\d{2}):(\d{2})\s*[–-]\s*(\d{2}):(\d{2})\]", raw):
        a, b = to_s(m[1], m[2]), to_s(m[3], m[4])
        timeline.append((a, b))
        if b <= a:
            errors.append(f"Non-positive beat: {a}–{b}")
    if not timeline:
        errors.append("No [MM:SS–MM:SS] beat ranges found")
    else:
        if timeline[0][0] != 0:
            errors.append(f"First beat starts at {timeline[0][0]} rather than 0")
        if timeline[-1][1] != args.duration:
            errors.append(f"Last beat ends at {timeline[-1][1]} rather than {args.duration}")
        for prev, nxt in zip(timeline, timeline[1:]):
            if prev[1] != nxt[0]:
                errors.append(f"Gap/overlap between beats {prev} and {nxt}")
    tokens = set(re.findall(r"<(?:Picture \d+|audio\d+|Video \d+)>", raw))
    if args.manifest:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        refs = manifest.get("references", [])
        slots = {r["slot"] for r in refs}
        missing = tokens - slots
        if missing:
            errors.append("Prompt uses unmapped reference slot(s): " + ", ".join(sorted(missing)))
        unused = slots - tokens
        if unused:
            errors.append("Manifest reference slot(s) not used in prompt: " + ", ".join(sorted(unused)))
    print(f"chars={len(raw)} max={args.max_chars} duration={args.duration}s beats={len(timeline)} reference_slots={len(tokens)}")
    if errors:
        for e in errors:
            print("ERROR:", e, file=sys.stderr)
        return 1
    print("PASS: basic prompt preflight checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
