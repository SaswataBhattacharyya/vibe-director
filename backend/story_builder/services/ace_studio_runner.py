"""Owned subprocess execution; no ComfyUI graph is submitted for ACE-Step."""
from __future__ import annotations

import copy
from story_builder.services.storage_paths import generated_root

import json
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path

from . import ace_studio as studio, media_library, video_repertoire as jobs
from .media_jobs import gpu_workload_guard, release_comfyui_models_if_idle


def launch(command, *, folder, env, job_id, progress, gpu=False, timeout=7200):
    """Children share the worker's process group, including cancellation on worker exit."""
    process = None
    stopped = threading.Event()
    lock = threading.Lock()

    def stop(_reason=""):
        nonlocal process
        with lock:
            stopped.set()
            if process is not None and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)

    from contextlib import nullcontext
    comfy = os.environ.get("COMFYUI_URL", "http://127.0.0.1:3008")
    guard = gpu_workload_guard(comfy_url=comfy, on_safety_trip=stop) if gpu else nullcontext()
    log = folder / "runtime.log"
    with guard:
        if gpu:
            release_comfyui_models_if_idle(comfy_url=comfy)
        try:
            with log.open("ab") as stream:
                with lock:
                    if stopped.is_set():
                        raise RuntimeError("GPU safety check stopped ACE-Step before startup.")
                    process = subprocess.Popen(command, cwd=folder, env=env, stdout=stream, stderr=subprocess.STDOUT)
                started = time.monotonic()
                while process.poll() is None:
                    job = jobs.read_job("ace-studio", job_id)
                    if job["status"] in {"cancel_requested", "cancelled"} or stopped.is_set():
                        raise RuntimeError("ACE-Step stopped.")
                    if time.monotonic() - started > timeout:
                        raise RuntimeError("ACE-Step reached this job's execution time limit.")
                    # No invented inference/training percentage; expose the current log instead.
                    progress("training" if gpu and timeout > 7200 else "generating" if gpu else "converting", "ACE-Step is running; progress details are in the runtime log.", 0)
                    time.sleep(2)
                if process.returncode:
                    raise RuntimeError("ACE-Step failed: " + log.read_text(errors="replace")[-3000:])
        finally:
            stop()


def pipeline_arguments(s, reference_path=None):
    args = dict(format="wav", audio_duration=s["duration"], prompt=s["tags"],
                lyrics=s["lyrics"] if s["mode"] == "song" else "[instrumental]",
                infer_step=int(s["steps"]), guidance_scale=s["cfg"], scheduler_type=s["scheduler"],
                manual_seeds=str(int(s["seed"])))
    if s["task"] == "reference":
        args.update(audio2audio_enable=True, ref_audio_input=reference_path, ref_audio_strength=s["reference_strength"])
    elif s["task"] in {"remix", "lyrics"}:
        args.update(task="edit", src_audio_path=reference_path, edit_target_prompt=args["prompt"],
                    edit_target_lyrics=args["lyrics"], prompt=s["source_tags"], lyrics=s["source_lyrics"],
                    edit_n_min=s["edit_min"], edit_n_max=s["edit_max"], edit_n_avg=1)
    if s["task"] != "text" and not reference_path:
        raise ValueError("This ACE-Step task requires a reference audio recording.")
    return args


def inference_arguments(config, settings, output, adapter="none", reference_path=None):
    return {"checkpoint_dir": config["checkpoints"], "settings": settings,
            "output": str(output), "adapter": adapter, "pipeline": pipeline_arguments(settings, reference_path)}


def execute(root, job_id, request, progress):
    config = studio.runtime()
    if not config["ready"]:
        raise ValueError(config["reason"])
    settings = studio.settings(request["settings"])
    with studio.state(root) as data:
        p = studio.project(data, request["project_id"])
        if p.get("confirmed_revision") != request["revision"] or p["job_id"] != job_id:
            raise ValueError("This music job has no current owner confirmation.")
        adapter = next((a["path"] for a in studio.available_adapters(data) if a["id"] == settings["adapter_id"]), "none")
        if settings["adapter_id"] and (adapter == "none" or not Path(adapter).is_dir()):
            raise ValueError("Selected trained LoRA is no longer available on disk.")
    folder = root / "ace_step/runs" / job_id
    folder.mkdir(parents=True, exist_ok=True)
    source = Path(config["source"])
    env = {**os.environ, "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "HF_DATASETS_OFFLINE": "1",
           "PYTHONPATH": str(source), "TOKENIZERS_PARALLELISM": "false"}
    if request["operation"] == "generate":
        output = root / "ace_step/output" / request["project_id"] / f"{job_id}.wav"
        output.parent.mkdir(parents=True, exist_ok=True)
        reference_path = None
        if settings["task"] != "text":
            path, _, filename = studio.reference(root, p)
            reference_path = folder / ("reference" + Path(filename).suffix.lower())
            shutil.copy2(path, reference_path)
        write_request = inference_arguments(config, settings, output, adapter, str(reference_path) if reference_path else None)
        script = """import json,sys
from acestep.pipeline_ace_step import ACEStepPipeline
r=json.load(open(sys.argv[1])); s=r['settings']
model=ACEStepPipeline(checkpoint_dir=r['checkpoint_dir'],dtype='bfloat16',torch_compile=False,cpu_offload=True,overlapped_decode=True)
model(**r['pipeline'],lora_name_or_path=r['adapter'],save_path=r['output'])
"""
        studio.write(folder / "request.json", write_request)
        (folder / "run.py").write_text(script)
        launch([config["python"], str(folder / "run.py"), str(folder / "request.json")], folder=folder, env=env, job_id=job_id, progress=progress, gpu=True)
        if not output.is_file():
            raise ValueError("Standalone ACE-Step did not produce the expected WAV.")
        with studio.state(root) as data:
            p = studio.project(data, request["project_id"])
            ensure_current(p, request, job_id)
            relative = output.relative_to(root / "ace_step").as_posix()
            asset = media_library.register_generated_audio(root, request["workspace_id"], relative,
                {"source": "ace_step_standalone", "audio_category": "music", "job_id": job_id, "settings": settings},
                storage_location={"store": "ace", "path": relative})
            p["assets"].append(asset)
            studio.message(p, "assistant", "Music generated and saved to the Audio Clips library.")
        return {"asset": asset}
    if not config["training_ready"]:
        raise ValueError("Standalone training dependencies/encoders are incomplete.")
    from .storage_paths import relocated_path
    dataset = relocated_path(root, Path(request["dataset"]["path"])).resolve()
    if not dataset.is_relative_to((root / "ace_step/datasets" / request["project_id"]).resolve()):
        raise ValueError("Training dataset is outside this music project.")
    hf_data = folder / "hf_dataset"
    progress("converting", "Converting every validated triplet using the copied ACE-Step converter.", 5)
    launch([config["python"], str(source / "convert2hf_dataset.py"), "--data_dir", str(dataset), "--repeat_count", "1", "--output_name", str(hf_data)], folder=folder, env=env, job_id=job_id, progress=progress, timeout=600)
    lora_config = json.loads((source / "config/zh_rap_lora_config.json").read_text())
    lora_config.update(r=int(settings["rank"]), lora_alpha=int(settings["rank"]) * 2)
    studio.write(folder / "lora.json", lora_config)
    # Keep base models read-only by convention; any Hugging Face metadata stays job-local.
    checkpoint_root = folder / "checkpoints"
    checkpoint_root.mkdir(exist_ok=True)
    for name in ("ace_step_transformer", "music_dcae_f8c8", "music_vocoder", "umt5-base"):
        (checkpoint_root / name).symlink_to(Path(config["checkpoints"]) / name, target_is_directory=True)
    # Surgical adapter: drop the donor's fallback which edits a shared HF cache
    # config, and use one process rather than Lightning DDP child workers.
    trainer = (source / "trainer.py").read_text()
    trainer = trainer.replace("from transformers import AutoModel,", "from transformers import AutoConfig, AutoModel,")
    # The upstream fallback corrects this flag by rewriting a shared cache blob.
    # Apply the same compatibility correction only to this in-memory config.
    begin = trainer.index("            try:\n", trainer.index("if self.is_train:"))
    end = trainer.index("            self.mert_model.requires_grad_(False)", begin)
    trainer = trainer[:begin] + """            mert_config = AutoConfig.from_pretrained(
                "m-a-p/MERT-v1-330M", trust_remote_code=True, cache_dir=checkpoint_dir
            )
            mert_config.conv_pos_batch_norm = False
            self.mert_model = AutoModel.from_pretrained(
                "m-a-p/MERT-v1-330M", trust_remote_code=True,
                cache_dir=checkpoint_dir, config=mert_config
            ).eval()
""" + trainer[end:]
    # Use pinned local snapshots rather than a moving hub main revision.
    for repo, path in studio.encoder_paths().items():
        trainer = trainer.replace('"' + repo + '"', repr(str(path)))
    trainer = trainer.replace('strategy="ddp_find_unused_parameters_true"', 'strategy="auto"')
    # Lightning's single-device strategy has no distributed process group.
    # Skip the initial preview too: step zero matches every plotting interval.
    preview_guard = """            global_step % self.hparams.every_plot_step != 0
            or self.local_rank != 0
            or torch.distributed.get_rank() != 0
            or torch.cuda.current_device() != 0"""
    if preview_guard not in trainer:
        raise ValueError("ACE-Step preview guard changed; single-device adapter needs updating.")
    trainer = trainer.replace(preview_guard, """            global_step == 0
            or global_step % self.hparams.every_plot_step != 0
            or not self.trainer.is_global_zero""", 1)
    (folder / "trainer.py").write_text(trainer)
    args = [config["python"], str(folder / "trainer.py"), "--dataset_path", str(hf_data), "--checkpoint_dir", str(checkpoint_root),
            "--lora_config_path", str(folder / "lora.json"), "--logger_dir", str(folder / "training"), "--exp_name", "music_adapter",
            "--max_steps", str(int(settings["max_steps"])), "--every_n_train_steps", str(min(int(settings["save_every"]), int(settings["max_steps"]))),
            "--learning_rate", str(settings["learning_rate"]), "--devices", "1", "--num_workers", "0", "--precision", "bf16-mixed",
            "--every_plot_step", str(int(settings["max_steps"]) + 1)]
    studio.write(folder / "training_request.json", {"settings": settings, "dataset": request["dataset"], "command": args})
    launch(args, folder=folder, env=env, job_id=job_id, progress=progress, gpu=True, timeout=24 * 3600)
    adapters = sorted((folder / "training").rglob("*_lora"), key=lambda path: path.stat().st_mtime)
    if not adapters or not any(adapters[-1].rglob("*.safetensors")):
        raise ValueError("Training ended without a saved music LoRA. Inspect the job log.")
    with studio.state(root) as data:
        p = studio.project(data, request["project_id"])
        ensure_current(p, request, job_id)
        adapter = {"id": job_id, "name": settings["style_name"], "description": settings["style_description"],
                   "tags": settings["tags"], "path": str(adapters[-1]), "created_at": studio.now(),
                   "base_model": "ACE-Step-v1-3.5B", "checkpoint_root": config["checkpoints"], "job_id": job_id,
                   "training_steps": int(settings["max_steps"]), "dataset": request["dataset"]}
        p["adapters"].append(adapter)
        data.setdefault("adapters", []).append(copy.deepcopy(adapter))
        studio.message(p, "assistant", "Training completed. The saved LoRA can now be selected for generation.")
    return {"adapter": adapter}


def ensure_current(p, request, job_id):
    if p["job_id"] != job_id or p["revision"] != request["revision"] or jobs.read_job("ace-studio", job_id)["status"] in {"cancelled", "cancel_requested"}:
        raise ValueError("Music job stopped or draft changed; output was not published.")
