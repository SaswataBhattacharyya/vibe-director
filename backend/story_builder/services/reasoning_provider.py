"""Structured reasoning adapter reused from Story Builder for Vibe Director.

This adapter deliberately exposes model reasoning only. Media executors,
ComfyUI jobs, storage writes, and application authorization stay in their
existing services. Codex runs with no project working directory and no
write-enabled agent sandbox.
"""

from __future__ import annotations

import json
import mimetypes
import os
import signal
import shutil
import subprocess
import sys
import tempfile
import threading
from contextlib import contextmanager
from contextvars import ContextVar, Token
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator



PROJECT_ROOT = Path(__file__).resolve().parents[1]
SETTINGS_PATH = PROJECT_ROOT / "storage" / "reasoning_provider.json"
SUPPORTED_PROVIDERS = {"codex", "ollama", "opencode"}
DEFAULT_CODEX_MODEL = os.environ.get("CODEX_REASONING_MODEL", "gpt-6-luna")
_SETTINGS_LOCK = threading.RLock()
_ACTIVE_PROVIDER: ContextVar[str | None] = ContextVar("story_reasoning_provider", default=None)


class ReasoningProviderError(RuntimeError):
    """Raised when the selected reasoning provider cannot return valid JSON."""


def model_catalog() -> list[dict[str, Any]]:
    """Use the installed CLI's account catalog, never a guessed model roster."""
    cache = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "models_cache.json"
    try:
        models = json.loads(cache.read_text(encoding="utf-8"))["models"]
        result = []
        for item in models:
            if item.get("visibility") != "list" or not str(item.get("slug", "")).startswith("gpt-"):
                continue
            efforts = [entry["effort"] for entry in item.get("supported_reasoning_levels", [])
                       if isinstance(entry, dict) and isinstance(entry.get("effort"), str)]
            if efforts:
                result.append({"id": item["slug"], "label": item.get("display_name") or item["slug"],
                               "efforts": efforts, "default_effort": item.get("default_reasoning_level", "medium")})
        if result:
            return result
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        pass
    # Offline compatibility with the previously installed baseline only.
    return [{"id": DEFAULT_CODEX_MODEL, "label": DEFAULT_CODEX_MODEL,
             "efforts": ["low", "medium", "high"], "default_effort": "medium"}]


def _default_settings() -> dict[str, Any]:
    return {"provider": "codex", "model": DEFAULT_CODEX_MODEL, "reasoning_effort": "medium",
            "lessons": [], "revision": 0, "provider_models": {}}


def get_settings() -> dict[str, Any]:
    with _SETTINGS_LOCK:
        settings = _default_settings()
        try:
            stored = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            if isinstance(stored, dict):
                settings.update({key: stored[key] for key in settings if key in stored})
        except (OSError, ValueError):
            pass
        if settings["provider"] not in SUPPORTED_PROVIDERS:
            settings["provider"] = "codex"
        return settings


def save_settings(payload: dict[str, Any]) -> dict[str, Any]:
    """Save explicit Director preferences/corrections; no credentials or model training."""
    if not isinstance(payload, dict) or set(payload) - {"provider", "model", "reasoning_effort", "lessons", "revision"}:
        raise ValueError("Supply model, reasoning_effort, lessons and current revision.")
    with _SETTINGS_LOCK:
        current = get_settings()
        if payload.get("revision") != current["revision"]:
            raise ValueError("Director settings changed. Reload before saving.")
        provider = payload.get("provider", current["provider"])
        from .reasoning_backends import discover
        choices = model_catalog() if provider == "codex" else discover()[0]
        selected = next((m for m in choices if m["id"] == payload.get("model")
                         and m.get("provider", "codex") == provider and m.get("available", True)), None)
        if not selected or payload.get("reasoning_effort") not in selected["efforts"]:
            raise ValueError("Choose an installed model and one of its supported reasoning levels.")
        lessons = payload.get("lessons", [])
        if not isinstance(lessons, list) or len(lessons) > 30 or any(
                not isinstance(note, str) or not note.strip() or len(note) > 1000 for note in lessons):
            raise ValueError("Save up to 30 Director lessons, each between 1 and 1,000 characters.")
        profiles = dict(current.get("provider_models", {}))
        profiles[current["provider"]] = {key: current[key] for key in ("model", "reasoning_effort")}
        profiles[provider] = {"model": selected["id"], "reasoning_effort": payload["reasoning_effort"]}
        settings = {"provider": provider, "model": selected["id"], "provider_models": profiles,
                    "reasoning_effort": payload["reasoning_effort"],
                    "lessons": [note.strip() for note in lessons], "revision": current["revision"] + 1}
        SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        temporary = SETTINGS_PATH.with_suffix(".tmp")
        temporary.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
        temporary.replace(SETTINGS_PATH)
        return settings


def set_provider(provider: str) -> dict[str, Any]:
    if str(provider).lower() not in SUPPORTED_PROVIDERS:
        raise ValueError(f"Unsupported reasoning provider: {provider}")
    return get_settings()


@contextmanager
def use_provider(provider: str | None) -> Iterator[None]:
    """Pin a provider for one background run so UI changes do not affect it."""
    if provider is None:
        yield
        return
    selected = str(provider).lower()
    if selected not in SUPPORTED_PROVIDERS:
        raise ValueError(f"Unsupported reasoning provider: {provider}")
    token: Token[str | None] = _ACTIVE_PROVIDER.set(selected)
    try:
        yield
    finally:
        _ACTIVE_PROVIDER.reset(token)


def activate_provider(provider: str | None) -> Token[str | None] | None:
    """Set a provider in the current worker context and return its reset token."""
    if provider is None:
        return None
    selected = str(provider).lower()
    if selected not in SUPPORTED_PROVIDERS:
        raise ValueError(f"Unsupported reasoning provider: {provider}")
    return _ACTIVE_PROVIDER.set(selected)


def reset_provider(token: Token[str | None] | None) -> None:
    if token is not None:
        _ACTIVE_PROVIDER.reset(token)


def _selected_provider(provider: str | None) -> str:
    selected = provider or _ACTIVE_PROVIDER.get() or get_settings()["provider"]
    selected = str(selected).lower()
    if selected not in SUPPORTED_PROVIDERS:
        raise ReasoningProviderError(f"Unsupported reasoning provider: {selected}")
    return selected


def provider_catalog() -> dict[str, Any]:
    """Return safe UI metadata; this does not call a paid model or reveal secrets."""
    from .reasoning_backends import discover
    extra_models, extra_providers = discover()
    settings = get_settings()
    return {
        "provider": settings["provider"],
        "settings": settings,
        "models": [{**model, "provider": "codex", "available": bool(shutil.which("codex"))}
                   for model in model_catalog()] + extra_models,
        "providers": [{
                "id": "codex",
                "label": "Codex",
                "model": _settings_for("codex", settings)["model"],
                "available": bool(shutil.which("codex")),
                "compatibility": False,
            }, *[{**item, "model": _settings_for(item["id"], settings)["model"]} for item in extra_providers]],
    }


def _settings_for(provider, settings):
    if provider == settings["provider"]:
        return settings
    profile = settings.get("provider_models", {}).get(provider, {})
    default = DEFAULT_CODEX_MODEL if provider == "codex" else ""
    return {**settings, "provider": provider, "model": profile.get("model", default),
            "reasoning_effort": profile.get("reasoning_effort", "medium" if provider == "codex" else "default")}


def _run_json_command(command: list[str], prompt: str, *, timeout_seconds: int = 300, env=None) -> str:
    try:
        with tempfile.TemporaryDirectory(prefix="story-builder-reasoning-") as isolated_cwd:
            guarded_command = command
            if sys.platform.startswith("linux"):
                guard = Path(__file__).with_name("provider_exec_guard.py")
                guarded_command = [sys.executable, str(guard), str(os.getpid()), *command]
            process = subprocess.Popen(
                guarded_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=isolated_cwd,
                env=env,
                start_new_session=(os.name == "posix"),
            )
            try:
                stdout, stderr = process.communicate(input=prompt, timeout=timeout_seconds)
            except subprocess.TimeoutExpired as exc:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except (AttributeError, ProcessLookupError):
                    process.terminate()
                try:
                    stdout, stderr = process.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except (AttributeError, ProcessLookupError):
                        process.kill()
                    stdout, stderr = process.communicate()
                raise ReasoningProviderError(
                    f"{command[0]} timed out after {timeout_seconds} seconds"
                ) from exc
            result = subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
    except FileNotFoundError as exc:
        raise ReasoningProviderError(f"Reasoning command is not installed: {command[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise ReasoningProviderError(f"{command[0]} timed out after {timeout_seconds} seconds") from exc
    if result.returncode:
        if command[0] == "opencode":
            raise ReasoningProviderError("OpenCode failed. Check its provider credentials and model configuration.")
        detail = (result.stderr or result.stdout or "provider command failed").strip()
        raise ReasoningProviderError(f"{command[0]} failed: {detail[-1800:]}")
    return result.stdout.strip()


def _parse_dict(text: str, provider: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if len(lines) >= 3:
            cleaned = "\n".join(lines[1:-1]).strip()
    decoder = json.JSONDecoder()
    for index, char in enumerate(cleaned):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(cleaned[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise ReasoningProviderError(f"{provider} did not return a valid JSON object")


def _codex_json(prompt: str, *, image_paths: list[str | Path] | None = None,
                output_schema: dict[str, Any] | None = None, settings: dict[str, Any] | None = None) -> dict[str, Any]:
    if not shutil.which("codex"):
        raise ReasoningProviderError("Codex CLI is not installed or not on PATH")
    image_args = []
    for value in image_paths or []:
        try:
            path = Path(value).expanduser().resolve(strict=True)
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            raise ReasoningProviderError(
                "Codex image inputs must be existing PNG, JPEG, WebP, or GIF files"
            ) from exc
        if not path.is_file() or mimetypes.guess_type(path.name)[0] not in {
                "image/png", "image/jpeg", "image/webp", "image/gif"}:
            raise ReasoningProviderError("Codex image inputs must be existing PNG, JPEG, WebP, or GIF files")
        image_args.extend(("--image", str(path)))
    selected = settings or get_settings()
    command = [
        "codex", "exec", "--skip-git-repo-check", "--ephemeral",
        "--sandbox", "read-only", "--ignore-user-config", "--model",
        selected["model"], "--config", f'model_reasoning_effort={json.dumps(selected["reasoning_effort"])}',
        *image_args, "--json", "-",
    ]
    with tempfile.TemporaryDirectory(prefix="vibe-director-schema-") as directory:
        if output_schema is not None:
            schema_path = Path(directory) / "response.json"
            schema_path.write_text(json.dumps(output_schema), encoding="utf-8")
            command[2:2] = ["--output-schema", str(schema_path)]
        output = _run_json_command(command, prompt)
    messages: list[str] = []
    failures: list[str] = []
    for line in output.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "item.completed":
            item = event.get("item") or {}
            if item.get("type") == "agent_message" and isinstance(item.get("text"), str):
                messages.append(item["text"])
        elif event.get("type") == "turn.completed":
            from .reasoning_status import record_usage
            usage = event.get("usage") or {}
            record_usage("codex", selected["model"], usage.get("input_tokens"), usage.get("output_tokens"))
        elif event.get("type") in {"turn.failed", "error"}:
            failures.append(str(event.get("error") or event.get("message") or event))
    if not messages:
        if failures:
            raise ReasoningProviderError("Codex failed: " + "; ".join(failures)[-1800:])
        raise ReasoningProviderError("Codex completed without a final assistant message")
    return _parse_dict(messages[-1], "Codex")


def generate_json(
    *,
    prompt: str,
    temperature: float = 0.4,
    provider: str | None = None,
    image_paths: list[str | Path] | None = None,
    cpu_only: bool = False,
    gpu_admission_timeout_seconds: int = 24 * 3600,
    output_schema: dict[str, Any] | None = None,
    include_director_lessons: bool = True,
) -> dict[str, Any]:
    """Generate structured reasoning with the selected, explicit backend."""
    selected = _selected_provider(provider)
    settings = _settings_for(selected, get_settings())
    if not settings["model"]:
        raise ReasoningProviderError(f"Choose a model for {selected} before using this provider.")
    lessons = settings.get("lessons", []) if include_director_lessons else []
    if lessons:
        prompt += ("\nDIRECTOR LESSONS (saved owner preferences, apply only where relevant; "
                       "the current task, source evidence and required JSON schema take precedence):\n"
                       + json.dumps(lessons, ensure_ascii=False))
    if selected == "codex":
        result = _codex_json(prompt, image_paths=image_paths, output_schema=output_schema, settings=settings)
    else:
        from .reasoning_backends import generate
        result = generate(selected, settings["model"], prompt, image_paths=image_paths,
                          output_schema=output_schema, temperature=temperature, cpu_only=cpu_only,
                          gpu_admission_timeout_seconds=gpu_admission_timeout_seconds)
    result["provider"] = selected
    result["model"] = settings["model"]
    result["reasoning_effort"] = settings["reasoning_effort"]
    result["director_settings_revision"] = settings["revision"]
    return result


def test_provider(provider: str) -> dict[str, Any]:
    """Run a tiny no-side-effect structured-output smoke test."""
    selected = _selected_provider(provider)
    started = datetime.now(timezone.utc)
    result = generate_json(
        provider=selected,
        temperature=0,
        cpu_only=True,
        gpu_admission_timeout_seconds=120,
        prompt=(
            'This is a provider connectivity test, not a real project. '
            'Return only this JSON object: {"ok":true,"task":"director_provider_smoke_test"}'
        ),
    )
    if result.get("ok") is not True or result.get("task") != "director_provider_smoke_test":
        raise ReasoningProviderError(f"{selected} returned an unexpected smoke-test payload")
    return {
        "provider": selected,
        "model": next((item["model"] for item in provider_catalog()["providers"] if item["id"] == selected), None),
        "ok": True,
        "result": result,
        "elapsed_ms": int((datetime.now(timezone.utc) - started).total_seconds() * 1000),
    }


def model_for(provider: str | None = None) -> str | None:
    selected = _selected_provider(provider)
    return _settings_for(selected, get_settings())["model"] or None
