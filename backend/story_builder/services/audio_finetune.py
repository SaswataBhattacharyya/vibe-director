"""Project-scoped F5-TTS dataset validation and preparation.

Adapted from Story Builder's ``audio_finetune`` service. Dataset preparation
stops before training and writes only inside the selected Vibe workspace.
"""

from __future__ import annotations

import csv
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable



SUPPORTED_MODELS = {
    "F5TTS_v1_Base": "model_1250000.safetensors",
    "F5TTS_Base": "model_1200000.pt",
    "E2TTS_Base": "model_1200000.pt",
}
DATASET_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$")
AUDIO_SUFFIXES = {".wav", ".flac", ".mp3", ".ogg", ".m4a", ".aac"}


class F5DatasetError(ValueError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _suite_root() -> Path:
    configured = os.environ.get("TTS_AUDIO_SUITE_ROOT")
    if configured:
        return Path(configured).expanduser().resolve()
    comfy_root = Path(os.environ.get("COMFYUI_ROOT", "/home/riki/web_dev/setup_comfy_and-stuff/ComfyUI"))
    return comfy_root.expanduser().resolve() / "custom_nodes" / "TTS-Audio-Suite"


def _models_root() -> Path:
    comfy_root = Path(os.environ.get("COMFYUI_ROOT", "/home/riki/web_dev/setup_comfy_and-stuff/ComfyUI"))
    return comfy_root.expanduser().resolve() / "models" / "TTS" / "F5-TTS"


def _checkpoint(model: str) -> Path:
    if model not in SUPPORTED_MODELS:
        raise F5DatasetError(f"Unsupported local F5 fine-tuning base model: {model}")
    return _models_root() / model / SUPPORTED_MODELS[model]


def read_metadata(content: bytes) -> list[dict[str, str]]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise F5DatasetError("metadata.csv must be UTF-8") from exc
    rows = list(csv.reader(text.splitlines(), delimiter="|"))
    if not rows or [value.strip().lower() for value in rows[0][:2]] != ["audio_file", "text"]:
        raise F5DatasetError("metadata.csv must start with the header audio_file|text")
    parsed: list[dict[str, str]] = []
    seen: set[str] = set()
    for line_number, row in enumerate(rows[1:], 2):
        if len(row) < 2:
            raise F5DatasetError(f"metadata.csv line {line_number} must contain audio_file|text")
        filename = Path(row[0].strip()).name
        transcript = row[1].strip()
        if not filename or not transcript:
            raise F5DatasetError(f"metadata.csv line {line_number} has an empty filename or transcript")
        if filename in seen:
            raise F5DatasetError(f"metadata.csv contains duplicate audio file: {filename}")
        if Path(filename).suffix.lower() not in AUDIO_SUFFIXES:
            raise F5DatasetError(f"Unsupported training audio type: {filename}")
        seen.add(filename)
        parsed.append({"filename": filename, "text": transcript})
    if not parsed:
        raise F5DatasetError("metadata.csv must contain at least one training sample")
    return parsed


def build_metadata(samples: list[dict[str, str]]) -> bytes:
    """Serialize transcripts with the donor's pipe-delimited CSV escaping."""
    from io import StringIO

    output = StringIO(newline="")
    writer = csv.writer(output, delimiter="|", lineterminator="\n")
    writer.writerow(["audio_file", "text"])
    for sample in samples:
        writer.writerow([sample["filename"], sample["text"].replace("\r", " ").replace("\n", " ")])
    return output.getvalue().encode("utf-8")


def validate_audio(path: Path) -> dict[str, Any]:
    try:
        import soundfile as sf
        info = sf.info(path)
        if info.frames <= 0 or info.samplerate <= 0:
            raise F5DatasetError(f"Audio is empty: {path.name}")
        peak = 0.0
        with sf.SoundFile(path) as handle:
            while True:
                block = handle.read(65536, dtype="float32", always_2d=True)
                if not len(block):
                    break
                peak = max(peak, float(abs(block).max()))
        if peak < 1e-5:
            raise F5DatasetError(f"Audio appears silent: {path.name}")
        return {"filename": path.name, "duration": round(info.frames / info.samplerate, 4),
                "sample_rate": info.samplerate, "channels": info.channels, "peak": round(peak, 6)}
    except F5DatasetError:
        raise
    except Exception as exc:
        raise F5DatasetError(f"Could not read audio {path.name}: {exc}") from exc


def stage_dataset(*, project_dir: Path, dataset_name: str, model: str, metadata: bytes,
                  uploads: list[tuple[str, bytes]]) -> dict[str, Any]:
    clean_name = dataset_name.strip()
    if not DATASET_NAME_RE.fullmatch(clean_name):
        raise F5DatasetError("Dataset name must be 1-80 letters, numbers, dot, underscore, or hyphen")
    _checkpoint(model)
    entries = read_metadata(metadata)
    upload_map = {Path(name).name: content for name, content in uploads}
    if len(upload_map) != len(uploads):
        raise F5DatasetError("Duplicate uploaded filename")
    expected = {entry["filename"] for entry in entries}
    missing, extras = sorted(expected - set(upload_map)), sorted(set(upload_map) - expected)
    if missing:
        raise F5DatasetError(f"Missing audio listed by metadata: {', '.join(missing)}")
    if extras:
        raise F5DatasetError(f"Audio is not listed by metadata: {', '.join(extras)}")
    root = project_dir / "audio" / "finetune" / clean_name
    if root.exists():
        raise FileExistsError(f"An F5 dataset named '{clean_name}' already exists in this project")
    input_dir, wavs_dir = root / "input", root / "input" / "wavs"
    wavs_dir.mkdir(parents=True, exist_ok=False)
    try:
        samples = []
        for entry in entries:
            target = wavs_dir / entry["filename"]
            target.write_bytes(upload_map[entry["filename"]])
            samples.append({**entry, **validate_audio(target)})
        with (input_dir / "metadata.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, delimiter="|", lineterminator="\n")
            writer.writerow(["audio_file", "text"])
            for entry in entries:
                writer.writerow([f"wavs/{entry['filename']}", entry["text"]])
        manifest = {"version": 1, "dataset_name": clean_name, "base_model": model,
            "created_at": utc_now(), "status": "validated", "sample_count": len(samples),
            "total_duration": round(sum(item["duration"] for item in samples), 4),
            "sample_rates": sorted({item["sample_rate"] for item in samples}), "samples": samples,
            "input_dir": str(input_dir), "prepared_dir": str(root / "prepared")}
        (root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        return manifest
    except Exception:
        shutil.rmtree(root, ignore_errors=True)
        raise


def _convert_texts(texts: list[str]) -> list[str]:
    utils_path = _suite_root() / "engines" / "f5_tts" / "model" / "utils.py"
    spec = importlib.util.spec_from_file_location("vibe_f5_utils", utils_path)
    if spec is None or spec.loader is None:
        raise F5DatasetError(f"Could not load F5 text utilities from {utils_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return list(module.convert_char_to_pinyin(texts, polyphone=True))


def prepare_dataset(*, project_dir: Path, job: dict[str, Any], update: Callable[[dict[str, Any]], None]) -> None:
    root = project_dir / "audio" / "finetune" / job["dataset_name"]
    try:
        update({"status": "running", "stage": "converting", "progress": 20, "started_at": utc_now()})
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        converted = _convert_texts([sample["text"] for sample in manifest["samples"]])
        from datasets.arrow_writer import ArrowWriter
        prepared, durations = root / "prepared", []
        prepared.mkdir(parents=True, exist_ok=False)
        raw_path = prepared / "raw.arrow"
        with ArrowWriter(path=str(raw_path)) as writer:
            for sample, text in zip(manifest["samples"], converted):
                duration = float(sample["duration"])
                durations.append(duration)
                writer.write({"audio_path": str(root / "input" / "wavs" / sample["filename"]), "text": text, "duration": duration})
            writer.finalize()
        (prepared / "duration.json").write_text(json.dumps({"duration": durations}) + "\n", encoding="utf-8")
        vocab = _models_root() / job["base_model"] / "vocab.txt"
        if not vocab.is_file():
            vocab = _suite_root() / "engines" / "f5_tts" / "data" / "Emilia_ZH_EN_pinyin" / "vocab.txt"
        if not vocab.is_file():
            raise F5DatasetError("No compatible F5 vocabulary file is installed")
        vocab_copy = prepared / "vocab.txt"
        shutil.copy2(vocab, vocab_copy)
        command = [sys.executable, "-m", "engines.f5_tts.train.finetune_cli",
            "--exp_name", job["base_model"], "--dataset_name", job["dataset_name"],
            "--finetune", "--pretrain", str(_checkpoint(job["base_model"])), "--logger", "tensorboard"]
        update({"status": "completed", "stage": "completed", "progress": 100, "completed_at": utc_now(),
            "artifacts": {"raw_arrow": str(raw_path), "duration_json": str(prepared / "duration.json"), "vocab": str(vocab_copy)},
            "command_preview": command, "command_blockers": [
                "Training is intentionally disabled; this action only prepares and validates the dataset.",
                "Training needs separate approval and a verified installed F5 loader." ]})
    except Exception as exc:
        update({"status": "failed", "stage": "failed", "completed_at": utc_now(), "error": str(exc)})


def new_prepare_job(dataset_name: str, base_model: str, samples: list[dict[str, str]]) -> dict[str, Any]:
    return {"job_id": f"f5prep-{uuid.uuid4().hex[:12]}", "kind": "f5_prepare", "status": "queued",
        "created_at": utc_now(), "dataset_name": dataset_name, "base_model": base_model,
        "samples": [{"filename": item["filename"], "asset_id": item["asset_id"], "text": item["text"]} for item in samples],
        "artifacts": {}, "command_preview": None, "command_blockers": [], "error": None}
