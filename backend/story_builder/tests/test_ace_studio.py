"""CPU-only contracts. Provider, subprocess inference and training are mocked."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from story_builder.services import ace_studio as studio, video_repertoire as jobs


class AceStudioTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        jobs.configure_roots(self.root)
        self.p = studio.add_project(self.root, {"name": "Music", "workspace_id": "test-media"})
        self.start = patch.object(jobs, "start_job")
        self.start_mock = self.start.start()
        self.addCleanup(self.start.stop)

    def command(self, action, **kw):
        return studio.command(self.root, self.p["id"], {"action": action, "revision": self.p["revision"], **kw})

    def test_settings_and_chat_do_not_submit_generation(self):
        self.p = self.command("settings", settings={**studio.DEFAULTS, "tags": "warm, acoustic"}, intent="generate")
        self.start_mock.assert_not_called()
        self.p = self.command("chat", text="Make this instrumental")
        job = jobs.read_job("ace-studio", self.p["job_id"])
        self.assertEqual(job["request"]["operation"], "chat")
        reply = {"reply": "Ready to review", "summary": "Warm acoustic instrumental",
                 "intent": "generate", "questions": [], "settings": self.p["settings"]}
        with patch("story_builder.services.reasoning_provider.generate_json", return_value=reply) as provider:
            studio.run_job(self.root, job["job_id"], job["request"], lambda *args: None)
        self.assertFalse(provider.call_args.kwargs["include_director_lessons"])
        self.start_mock.assert_called_once()  # The chat job only, never a music job.
        with studio.state(self.root) as data:
            current = studio.project(data, self.p["id"])
            self.assertEqual(current["summary"], reply["summary"])
            self.assertIsNone(current.get("confirmed_revision"))

    def test_confirm_pins_revision_and_blocks_duplicate_or_stale_requests(self):
        self.p = self.command("settings", settings={**studio.DEFAULTS, "tags": "jazz"}, intent="generate")
        with patch.object(studio, "runtime", return_value={"ready": True, "training_ready": True}):
            self.p = self.command("confirm")
        job = jobs.read_job("ace-studio", self.p["job_id"])
        self.assertEqual(job["request"]["operation"], "generate")
        self.assertEqual(job["request"]["revision"], self.p["revision"])
        with patch.object(studio, "current_job", return_value={"status": "completed"}):
            with self.assertRaisesRegex(ValueError, "already submitted"):
                self.command("confirm")
            self.p = self.command("new_take")
            self.assertIsNone(self.p["confirmed_revision"])
            with self.assertRaisesRegex(ValueError, "changed"):
                self.command("settings", revision=0)

    def test_invalid_parameters_and_missing_song_lyrics_are_rejected(self):
        for key, value in (("duration", float("nan")), ("seed", 1.5), ("steps", True), ("rank", 0)):
            with self.subTest(key=key), self.assertRaises(ValueError):
                studio.settings({key: value})
        self.p = self.command("settings", settings={**studio.DEFAULTS, "mode": "song", "tags": "jazz"}, intent="generate")
        with patch.object(studio, "runtime", return_value={"ready": True, "training_ready": True}):
            with self.assertRaisesRegex(ValueError, "lyrics"):
                self.command("confirm")
        self.start_mock.assert_not_called()

    def test_dataset_validates_all_triplets_before_copying(self):
        recording = self.root / "original.mp3"
        recording.write_bytes(b"fixture; probe mocked")
        row = {"stem": "song_001", "asset_id": "pa-test", "prompt": "pop, acoustic", "lyrics": "[verse]\nhello"}
        body = {"revision": 0, "rows": [row]}
        with patch.object(studio.media_library, "asset_path", return_value=(recording, "audio/mpeg", "song.mp3")), \
             patch.object(studio.media_library, "_probe", return_value={"duration_seconds": 20}):
            with self.assertRaisesRegex(ValueError, "characters"):
                studio.dataset(self.root, self.p["id"], {**body, "rows": [row, {**row, "stem": "song_002", "lyrics": ""}]})
            self.assertFalse((self.root / "ace_studio/datasets").exists())
            self.p = studio.dataset(self.root, self.p["id"], body)
        folder = Path(self.p["dataset"]["path"])
        self.assertEqual(sorted(p.name for p in folder.iterdir()), ["song_001.mp3", "song_001_lyrics.txt", "song_001_prompt.txt"])
        self.assertEqual(recording.read_bytes(), (folder / "song_001.mp3").read_bytes())
        self.start_mock.assert_not_called()
        with patch.object(studio.media_library, "asset_path", return_value=(recording, "audio/mpeg", "song.mp3")), \
             patch.object(studio.media_library, "_probe", return_value={"duration_seconds": 241}):
            with self.assertRaisesRegex(ValueError, "240 seconds"):
                studio.dataset(self.root, self.p["id"], {"revision": self.p["revision"], "rows": [row]})

    def test_training_requires_dataset_and_cached_encoders(self):
        self.p = self.command("settings", settings=studio.DEFAULTS, intent="finetune")
        with patch.object(studio, "runtime", return_value={"ready": True, "training_ready": False}):
            with self.assertRaisesRegex(ValueError, "validated dataset"):
                self.command("confirm")
        self.start_mock.assert_not_called()

    def test_generation_adapter_uses_standalone_parameters_and_registers_audio(self):
        import json
        from story_builder.services import ace_studio_runner as runner
        self.p = self.command("settings", settings={**studio.DEFAULTS, "tags": "jazz", "seed": 123}, intent="generate")
        config = {"ready": True, "training_ready": True, "source": str(studio.SOURCE),
                  "python": "/test/python", "checkpoints": "/test/models"}
        with patch.object(studio, "runtime", return_value=config):
            self.p = self.command("confirm")
            job = jobs.read_job("ace-studio", self.p["job_id"])

            def launch(command, **kw):
                payload = json.loads((kw["folder"] / "request.json").read_text())
                self.assertEqual(payload["settings"]["seed"], 123)
                self.assertEqual(payload["adapter"], "none")
                script = (kw["folder"] / "run.py").read_text()
                compile(script, "run.py", "exec")
                self.assertIn("ACEStepPipeline", script)
                self.assertEqual(payload["pipeline"]["lyrics"], "[instrumental]")
                self.assertTrue(kw["gpu"])
                Path(payload["output"]).write_bytes(b"mock-wav")

            with patch.object(runner, "launch", side_effect=launch), \
                 patch.object(runner.media_library, "register_generated_audio", return_value={"asset_id": "pa-song"}) as register:
                result = runner.execute(self.root, job["job_id"], job["request"], lambda *args: None)
        self.assertEqual(result["asset"]["asset_id"], "pa-song")
        self.assertEqual(register.call_args.args[3]["source"], "ace_step_standalone")

    def test_training_adapter_preserves_donor_and_removes_shared_cache_mutation(self):
        import json
        from story_builder.services import ace_studio_runner as runner
        self.p = self.command("settings", settings={**studio.DEFAULTS, "max_steps": 2, "style_name": "Acoustic test", "tags": "acoustic"}, intent="finetune")
        dataset = self.root / "ace_step/datasets" / self.p["id"] / "validated"
        dataset.mkdir(parents=True)
        with studio.state(self.root) as data:
            studio.project(data, self.p["id"])["dataset"] = {"path": str(dataset), "count": 1}
        original = (studio.SOURCE / "trainer.py").read_text()
        config = {"ready": True, "training_ready": True, "source": str(studio.SOURCE),
                  "python": "/test/python", "checkpoints": str(self.root / "models")}
        operations = []

        def launch(command, **kw):
            operations.append(kw["gpu"] if "gpu" in kw else False)
            if not kw.get("gpu"):
                self.assertIn("convert2hf_dataset.py", command[1])
                self.assertEqual(command[command.index("--repeat_count") + 1], "1")
                return
            rewritten = (kw["folder"] / "trainer.py").read_text()
            compile(rewritten, "trainer.py", "exec")
            self.assertNotIn('with open(mert_config_path, mode="w")', rewritten)
            self.assertIn('mert_config.conv_pos_batch_norm = False', rewritten)
            self.assertNotIn('"m-a-p/MERT-v1-330M"', rewritten)
            self.assertIn(str(studio.encoder_paths()["m-a-p/MERT-v1-330M"]), rewritten)
            self.assertIn('strategy="auto"', rewritten)
            # Execute the actual adapted preview method without loading GPU models.
            import ast
            from types import SimpleNamespace
            from unittest.mock import Mock
            tree = ast.parse(rewritten)
            method = next(n for n in ast.walk(tree)
                          if isinstance(n, ast.FunctionDef) and n.name == "plot_step")
            namespace = {"torch": Mock()}
            namespace["torch"].distributed.get_rank.side_effect = AssertionError("No process group")
            exec(compile(ast.Module(body=[method], type_ignores=[]), "preview", "exec"), namespace)
            fake = SimpleNamespace(global_step=0, hparams=SimpleNamespace(every_plot_step=3),
                                   trainer=SimpleNamespace(is_global_zero=True), predict_step=Mock())
            namespace["plot_step"](fake, {}, 0)
            fake.global_step = 1
            namespace["plot_step"](fake, {}, 0)
            fake.global_step = 3
            fake.trainer.is_global_zero = False
            namespace["plot_step"](fake, {}, 0)
            fake.predict_step.assert_not_called()
            fake.trainer.is_global_zero = True
            fake.predict_step.side_effect = RuntimeError("preview reached")
            with self.assertRaisesRegex(RuntimeError, "preview reached"):
                namespace["plot_step"](fake, {}, 0)
            namespace["torch"].distributed.get_rank.assert_not_called()
            self.assertEqual(command[command.index("--every_n_train_steps") + 1], "2")
            saved = kw["folder"] / "training/checkpoints/step=2_lora"
            saved.mkdir(parents=True)
            (saved / "pytorch_lora_weights.safetensors").write_bytes(b"mock-lora")

        with patch.object(studio, "runtime", return_value=config):
            self.p = self.command("confirm")
            job = jobs.read_job("ace-studio", self.p["job_id"])
            with patch.object(runner, "launch", side_effect=launch):
                result = runner.execute(self.root, job["job_id"], job["request"], lambda *args: None)
        self.assertEqual(operations, [False, True])
        self.assertTrue(Path(result["adapter"]["path"]).is_dir())
        self.assertEqual(result["adapter"]["name"], "Acoustic test")
        with patch.object(studio, "runtime", return_value=config):
            self.assertEqual(studio.snapshot(self.root)["adapters"][0]["tags"], "acoustic")
        self.assertEqual((studio.SOURCE / "trainer.py").read_text(), original)

    def test_reference_and_edit_arguments_match_copied_engine(self):
        import ast
        from story_builder.services.ace_studio_runner import pipeline_arguments
        # Inspect the donor signature without loading GPU libraries.
        tree = ast.parse((studio.SOURCE / "acestep/pipeline_ace_step.py").read_text())
        signature = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "__call__")
        supported = {a.arg for a in signature.args.args}
        for task in ("text", "reference", "remix", "lyrics"):
            s = studio.settings({"task": task, "tags": "new, pop", "mode": "song", "lyrics": "new words",
                                 "source_tags": "old, rock", "source_lyrics": "old words"})
            args = pipeline_arguments(s, "/owned/reference.wav")
            self.assertFalse(set(args) - supported)
            if task == "reference":
                self.assertTrue(args["audio2audio_enable"])
                self.assertEqual(args["ref_audio_input"], "/owned/reference.wav")
            elif task in {"remix", "lyrics"}:
                self.assertEqual((args["task"], args["prompt"], args["lyrics"]), ("edit", "old, rock", "old words"))
                self.assertEqual((args["edit_target_prompt"], args["edit_target_lyrics"]), ("new, pop", "new words"))
            else:
                self.assertNotIn("src_audio_path", args)
        with self.assertRaisesRegex(ValueError, "reference audio"):
            pipeline_arguments(studio.settings({"task": "reference"}))

    def test_reference_validation_and_direct_edit_supersedes_chat_questions(self):
        recording = self.root / "reference.wav"
        recording.write_bytes(b"fixture")
        self.p = self.command("settings", settings={"task": "reference", "reference_id": "pa-ref", "tags": "jazz"}, intent="generate")
        with patch.object(studio, "runtime", return_value={"ready": True}), \
             patch.object(studio.media_library, "asset_path", return_value=(recording, "video/mp4", "video.mp4")):
            with self.assertRaisesRegex(ValueError, "audio recording"):
                self.command("confirm")
        self.start_mock.assert_not_called()
        with studio.state(self.root) as data:
            studio.project(data, self.p["id"])["questions"] = ["Which genre?"]
        self.p = self.command("settings", settings={"tags": "jazz"}, intent="generate")
        self.assertEqual(self.p["questions"], [])

    def test_nested_dataset_retains_provenance_without_overwriting_same_names(self):
        recording = self.root / "song.mp3"
        recording.write_bytes(b"fixture")
        row = {"stem": "song", "asset_id": "pa-song", "prompt": "jazz", "lyrics": "[instrumental]"}
        with patch.object(studio.media_library, "asset_path", return_value=(recording, "audio/mpeg", "song.mp3")), \
             patch.object(studio.media_library, "_probe", return_value={"duration_seconds": 10}):
            for invalid in ("../song.mp3", "/song.mp3", "a/../song.mp3"):
                with self.assertRaisesRegex(ValueError, "relative MP3"):
                    studio.dataset(self.root, self.p["id"], {"revision": 0, "rows": [{**row, "relative_path": invalid}]})
            self.p = studio.dataset(self.root, self.p["id"], {"revision": 0, "rows": [
                {**row, "relative_path": "album_a/song.mp3"}, {**row, "relative_path": "album_b/song.mp3"}]})
        self.assertEqual(len(list(Path(self.p["dataset"]["path"]).glob("*.mp3"))), 2)
        self.assertEqual(self.p["dataset"]["entries"][0]["duration_seconds"], 10)
        self.assertEqual(self.p["dataset"]["songs"], ["album_a/song.mp3", "album_b/song.mp3"])

    def test_prompt_preset_is_distinct_from_a_trained_adapter(self):
        self.command("save_preset", name="Warm piano", tags="piano, warm")
        with patch.object(studio, "runtime", return_value={}):
            snapshot = studio.snapshot(self.root)
        self.assertEqual(len(snapshot["presets"]), 10)
        self.assertEqual(snapshot["saved_presets"][0]["tags"], "piano, warm")
        self.assertEqual(snapshot["adapters"], [])
        self.start_mock.assert_not_called()

    def test_http_studio_routes_are_registered_without_submitting_jobs(self):
        import io
        import json
        from story_builder.isolated_server import create_app
        app = create_app(data_root=self.root)
        response = []
        with patch.object(studio, "runtime", return_value={"ready": False, "reason": "Missing standalone models"}):
            body = b"".join(app({"REQUEST_METHOD": "GET", "PATH_INFO": "/api/ace/state", "wsgi.input": io.BytesIO()},
                                lambda status, headers: response.append(status)))
        self.assertEqual(response, ["200 OK"])
        self.assertFalse(json.loads(body)["runtime"]["ready"])
        self.start_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
