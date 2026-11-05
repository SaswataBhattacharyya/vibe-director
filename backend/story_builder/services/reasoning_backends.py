"""Configured OpenCode models and local Ollama; no inference during discovery.

Ollama request/GPU admission adapted from mooV_E_maker/services/ollama_client.py.
OpenCode CLI/config: https://opencode.ai/docs/cli/ and /docs/permissions/.
"""
from __future__ import annotations

import base64
import json
import os
import re
import shutil
import subprocess
import threading
import time
import urllib.request
from pathlib import Path

_cache = None
_cached_at = 0.0
_lock = threading.Lock()


def ollama_host():
    host = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
    return host if "://" in host else "http://" + host


def discover():
    global _cache, _cached_at
    with _lock:
        if _cache is not None and time.monotonic() - _cached_at < 60:
            return _cache
        models, providers = [], []
        local_online = False
        names = []
        try:
            with urllib.request.urlopen(ollama_host() + "/api/tags", timeout=1) as response:
                names = [item["name"] for item in json.load(response).get("models", [])]
            local_online = True
            models.extend({"provider": "ollama", "id": name, "label": name,
                           "efforts": ["default"], "default_effort": "default", "available": True}
                          for name in names if isinstance(name, str))
        except (OSError, ValueError, KeyError, TypeError):
            pass
        providers.append({"id": "ollama", "label": "Ollama · local", "available": local_online,
                          "note": "Local models share the GPU admission guard." if local_online else
                          "Ollama is offline. Start ollama serve, then refresh after a minute."})
        code_models = []
        if shutil.which("opencode"):
            try:
                result = subprocess.run(["opencode", "models", "--pure"], capture_output=True,
                                        text=True, timeout=5, cwd="/tmp", check=False)
                if result.returncode == 0:
                    code_models = [line.strip() for line in result.stdout.splitlines()
                                   if re.fullmatch(r"[\w.-]+/[^\s\x1b]+", line.strip())]
            except (OSError, subprocess.TimeoutExpired):
                pass
        models.extend({"provider": "opencode", "id": name, "label": name,
                       "efforts": ["default"], "default_effort": "default",
                       "available": (local_online and name.removeprefix("ollama/") in names)
                                    if name.startswith("ollama/") else True}
                      for name in code_models)
        providers.append({"id": "opencode", "label": "OpenCode · API", "available": bool(code_models),
                          "note": "Uses OpenCode's configured providers. Paid providers require your API credentials; "
                                  "listing a model does not verify its quota. Configure with opencode auth login."})
        _cache, _cached_at = (models, providers), time.monotonic()
        return _cache


def image_files(paths):
    from .reasoning_provider import ReasoningProviderError
    result = []
    for value in paths or []:
        try:
            path = Path(value).expanduser().resolve(strict=True)
            if not path.is_file() or path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
                raise ValueError()
        except (OSError, ValueError, TypeError, RuntimeError) as exc:
            raise ReasoningProviderError("Image inputs must be existing PNG, JPEG, WebP or GIF files.") from exc
        result.append(path)
    return result


def generate(provider, model, prompt, *, image_paths, output_schema, temperature,
             cpu_only, gpu_admission_timeout_seconds):
    from .reasoning_provider import REASONING_TIMEOUT_SECONDS, ReasoningProviderError, _parse_dict, _run_json_command
    from .media_jobs import gpu_workload_guard
    from contextlib import nullcontext

    images = image_files(image_paths)
    local = provider == "ollama" or (provider == "opencode" and model.startswith("ollama/"))
    guard = gpu_workload_guard(comfy_url=os.environ.get("COMFYUI_URL", "http://127.0.0.1:3008"),
                               timeout_seconds=gpu_admission_timeout_seconds) if local else nullcontext()
    try:
        with guard:
            if provider == "ollama":
                payload = {"model": model, "prompt": prompt, "stream": False,
                           "format": output_schema or "json", "keep_alive": "0m",
                           "options": {"temperature": temperature, **({"num_gpu": 0} if cpu_only else {})}}
                if images:
                    payload["images"] = [base64.b64encode(path.read_bytes()).decode("ascii") for path in images]
                request = urllib.request.Request(ollama_host() + "/api/generate",
                    data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(request, timeout=REASONING_TIMEOUT_SECONDS) as response:
                    value = json.load(response)
                if value.get("error"):
                    raise ReasoningProviderError("Ollama rejected the request; check the model's input capabilities.")
                from .reasoning_status import record_usage
                record_usage(provider, model, value.get("prompt_eval_count"), value.get("eval_count"))
                result = _parse_dict(value.get("response") or value.get("thinking") or "", "Ollama")
            else:
                command = ["opencode", "run", "--pure", "--format", "json", "--model", model]
                for path in images:
                    command.extend(["--file", str(path)])
                if output_schema:
                    prompt += "\nReturn only JSON matching this schema:\n" + json.dumps(output_schema)
                # Preserve providers configured through inline environment JSON, including
                # credentials, while overriding execution permissions for this request.
                config = json.loads(os.environ.get("OPENCODE_CONFIG_CONTENT") or "{}")
                config.update(permission="deny", share="disabled", autoupdate=False, snapshot=False)
                output = _run_json_command(command, prompt, env={**os.environ,
                    "OPENCODE_CONFIG_CONTENT": json.dumps(config)})
                parts = []
                for line in output.splitlines():
                    try:
                        event = json.loads(line)
                    except ValueError:
                        continue
                    if event.get("type") == "error":
                        raise ReasoningProviderError("OpenCode could not complete this request. Check provider credentials and model capabilities.")
                    if event.get("type") == "text":
                        parts.append(event.get("part", {}).get("text", ""))
                result = _parse_dict("\n".join(parts), "OpenCode")
    except ReasoningProviderError:
        raise
    except Exception as exc:
        # Provider bodies/CLI output may contain credentials; never expose them to browser logs.
        raise ReasoningProviderError(f"{provider} request failed ({type(exc).__name__}). Check its connection and model capabilities.") from exc
    if output_schema:
        import jsonschema
        try:
            jsonschema.validate(result, output_schema)
        except jsonschema.ValidationError as exc:
            raise ReasoningProviderError(f"{provider} returned a response outside the required schema.") from exc
    return result
