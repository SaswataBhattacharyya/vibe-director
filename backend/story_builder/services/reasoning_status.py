"""Read-only provider allowance and last-request telemetry; never starts a turn."""
from __future__ import annotations
import json
import math
import os
import queue
import shutil
import subprocess
import threading
import time
from pathlib import Path

_lock = threading.RLock()
_usage = {}
_cached = None


def record_usage(provider, model, input_tokens=None, output_tokens=None):
    def count(value):
        return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None
    with _lock:
        _usage[(provider, model)] = {"input_tokens": count(input_tokens), "output_tokens": count(output_tokens), "recorded_at": time.time()}


def _rpc_limits():
    executable = shutil.which("codex")
    if not executable:
        raise RuntimeError("Codex CLI unavailable")
    process = subprocess.Popen([executable, "app-server", "--listen", "stdio://"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        text=True, cwd="/tmp")
    lines = queue.Queue()
    def read():
        for line in process.stdout:
            lines.put(line)
        lines.put(None)
    reader = threading.Thread(target=read, daemon=True)
    reader.start()
    deadline = time.monotonic() + 10
    def send(value):
        process.stdin.write(json.dumps(value) + "\n")
        process.stdin.flush()
    def reply(identifier):
        while True:
            line = lines.get(timeout=max(.01, deadline-time.monotonic()))
            if line is None:
                raise RuntimeError("Codex status connection closed")
            try:
                value = json.loads(line)
            except ValueError:
                continue
            if value.get("id") == identifier:
                if "error" in value:
                    raise RuntimeError("Codex status unsupported")
                return value.get("result") or {}
    try:
        send({"id": 1, "method": "initialize", "params": {"clientInfo": {"name": "vibe_director_status", "version": "1.0"}, "capabilities": {"experimentalApi": True}}})
        reply(1)
        send({"method": "initialized", "params": {}})
        send({"id": 2, "method": "account/rateLimits/read", "params": {}})
        return reply(2)
    finally:
        if process.poll() is None:
            process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2)
        reader.join(timeout=1)
        process.stdin.close()
        process.stdout.close()


def normalize_limits(result):
    buckets = result.get("rateLimitsByLimitId")
    values = list(buckets.values()) if isinstance(buckets, dict) and buckets else [result.get("rateLimits")]
    windows = []
    for bucket in values:
        if not isinstance(bucket, dict):
            continue
        for name in ("primary", "secondary"):
            window = bucket.get(name)
            used = window.get("usedPercent") if isinstance(window, dict) else None
            if isinstance(used, (int, float)) and not isinstance(used, bool) and math.isfinite(used):
                used = min(100, max(0, used))
                windows.append({"bucket": bucket.get("limitName") or bucket.get("limitId") or "Codex", "window": name,
                    "used_percent": used, "remaining_percent": 100-used,
                    "window_minutes": window.get("windowDurationMins"), "resets_at": window.get("resetsAt")})
    return windows


def provider_status():
    global _cached
    from .reasoning_provider import get_settings
    settings = get_settings()
    provider, model = settings["provider"], settings["model"]
    local = provider == "ollama" or (provider == "opencode" and model.startswith("ollama/"))
    result = {"provider": provider, "model": model, "checked_at": time.time(), "windows": [],
        "quota": "unmetered" if local else "unavailable",
        "quota_note": "100% allowance: local inference has no account quota." if local else "This provider does not expose account allowance through this adapter.",
        "context_note": "Context remaining is not reported. Each Director request is separate; this is not a persistent Codex chat session.",
        "context_remaining_percent": None}
    with _lock:
        result["last_request"] = _usage.get((provider, model))
        if provider == "codex":
            if _cached is None or time.monotonic()-_cached[0] > 30:
                try:
                    _cached = (time.monotonic(), normalize_limits(_rpc_limits()), None)
                except Exception:
                    # Do not expose CLI output, authentication data or provider error bodies.
                    _cached = (time.monotonic(), [], "Account usage unavailable. Check Codex sign-in or retry shortly.")
            result["windows"] = _cached[1]
            result["quota"] = "metered" if _cached[1] else "unavailable"
            result["quota_note"] = _cached[2] or ("Account limits are shared across Codex sessions." if _cached[1] else "Codex did not report an account allowance.")
    return result
