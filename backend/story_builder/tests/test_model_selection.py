import io
import json
import tempfile
import unittest
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import patch

from story_builder.services import reasoning_backends as backends, reasoning_provider as provider


class ModelSelectionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.settings_patch = patch.object(provider, "SETTINGS_PATH", Path(self.directory.name) / "settings.json")
        self.settings_patch.start()
        self.addCleanup(self.settings_patch.stop)
        self.models = [{"id": "gpt-test", "label": "Test", "efforts": ["medium", "high"], "default_effort": "medium"}]
        self.external = [{"id": "qwen-test", "provider": "ollama", "efforts": ["default"], "available": True},
                         {"id": "vendor/test", "provider": "opencode", "efforts": ["default"], "available": True}]
        for target, value in [("model_catalog", self.models)]:
            p = patch.object(provider, target, return_value=value); p.start(); self.addCleanup(p.stop)
        p = patch.object(backends, "discover", return_value=(self.external, [])); p.start(); self.addCleanup(p.stop)

    def save(self, name, model, effort, revision=0):
        return provider.save_settings({"provider": name, "model": model, "reasoning_effort": effort,
                                       "revision": revision, "lessons": ["Keep continuity."]})

    def test_selection_persists_routes_and_keeps_explicit_provider_profile(self):
        self.save("codex", "gpt-test", "high")
        self.save("ollama", "qwen-test", "default", 1)
        with patch.object(backends, "generate", return_value={"ok": True}) as local:
            value = provider.generate_json(prompt="Hello")
            self.assertEqual(value["provider"], "ollama")
            self.assertEqual(local.call_args.args[:2], ("ollama", "qwen-test"))
            self.assertIn("Keep continuity.", local.call_args.args[2])
        with provider.use_provider("codex"), patch.object(provider, "_codex_json", return_value={"ok": True}) as codex:
            value = provider.generate_json(prompt="Pinned run")
            self.assertEqual(value["model"], "gpt-test")
            self.assertEqual(codex.call_args.kwargs["settings"]["reasoning_effort"], "high")
        self.assertEqual(provider.get_settings()["provider"], "ollama")

    def test_rejects_unknown_unavailable_and_stale_selection(self):
        self.external[0]["available"] = False
        with self.assertRaises(ValueError): self.save("ollama", "qwen-test", "default")
        with self.assertRaises(ValueError): self.save("opencode", "invented/model", "default")
        self.save("codex", "gpt-test", "medium")
        with self.assertRaisesRegex(ValueError, "Reload"): self.save("codex", "gpt-test", "high")

    def test_opencode_uses_json_read_only_permissions_and_required_schema(self):
        self.save("opencode", "vendor/test", "default")
        schema = {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]}
        with patch.object(provider, "_run_json_command", return_value=json.dumps({"type": "text", "part": {"text": '{"ok":true}'}})) as run:
            result = provider.generate_json(prompt="Hello", output_schema=schema)
        self.assertTrue(result["ok"])
        command, prompt = run.call_args.args
        self.assertEqual(command[:2], ["opencode", "run"])
        self.assertIn("--pure", command)
        self.assertEqual(command[command.index("--model") + 1], "vendor/test")
        self.assertIn("schema", prompt)
        self.assertEqual(json.loads(run.call_args.kwargs["env"]["OPENCODE_CONFIG_CONTENT"])["permission"], "deny")
        with patch.object(provider, "_run_json_command", return_value=json.dumps({"type": "text", "part": {"text": '{"ok":"bad"}'}})):
            with self.assertRaisesRegex(provider.ReasoningProviderError, "schema"):
                provider.generate_json(prompt="Hello", output_schema=schema)

    def test_ollama_preserves_gpu_guard_cpu_flag_images_and_schema(self):
        self.save("ollama", "qwen-test", "default")
        image = Path(self.directory.name) / "image.png"; image.write_bytes(b"image")
        with patch("story_builder.services.media_jobs.gpu_workload_guard", return_value=nullcontext()) as guard, \
             patch.object(backends.urllib.request, "urlopen", return_value=io.BytesIO(b'{"response":"{\\"ok\\":true}"}')) as request:
            provider.generate_json(prompt="Inspect", image_paths=[image], cpu_only=True,
                                   output_schema={"type": "object"}, gpu_admission_timeout_seconds=7)
        payload = json.loads(request.call_args.args[0].data)
        self.assertEqual(payload["model"], "qwen-test")
        self.assertEqual(payload["options"]["num_gpu"], 0)
        self.assertEqual(payload["keep_alive"], "0m")
        self.assertTrue(payload["images"])
        self.assertEqual(guard.call_args.kwargs["timeout_seconds"], 7)


class DiscoveryTests(unittest.TestCase):
    def test_catalog_only_reads_metadata_and_disables_uninstalled_local_alias(self):
        with patch.object(backends, "_cache", None), patch.object(backends, "_cached_at", 0), \
             patch.object(backends.urllib.request, "urlopen", return_value=io.BytesIO(b'{"models":[{"name":"installed"}]}')), \
             patch.object(backends.shutil, "which", return_value="opencode"), \
             patch.object(backends.subprocess, "run") as run:
            run.return_value.returncode = 0
            run.return_value.stdout = "vendor/model\nollama/installed\nollama/missing\nnot a model\n"
            models, providers = backends.discover()
            self.assertEqual(len(models), 4)
            self.assertFalse(next(m for m in models if m["id"] == "ollama/missing")["available"])
            self.assertTrue(all(p["available"] for p in providers))
            self.assertEqual(run.call_args.args[0], ["opencode", "models", "--pure"])
