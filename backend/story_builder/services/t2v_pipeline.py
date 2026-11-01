"""CPU preparation and exact-output remux for the pinned Turbo → LTX route.

Adapted from setup_comfy_and-stuff/env_setup/h3_ltx_20261023/scripts/
prepare_ltx_input.py and remux_original_audio.py (local tested recipe).
Models and custom nodes remain in the shared ComfyUI runtime.
"""
from __future__ import annotations
from story_builder.services.storage_paths import intermediate_root
import hashlib
import json
import math
import os
from fractions import Fraction
from pathlib import Path
import subprocess

from story_builder.services.minimax_h3_t2v import LTX_GRAPH_PATH, final_dimensions, pipeline_digest


def is_pipeline(take):
    request = take.get("input_snapshot") or {}
    return request.get("workflow_id") in {"minimax_h3_t2v_local_v1", "minimax_h3_fl2va_first_last_v1", "minimax_h3_r2v_dynamic_v1"} and request.get("workflow_version") == 2


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def probe(path):
    result = subprocess.run([os.environ.get("FFPROBE", "ffprobe"), "-v", "error", "-count_frames",
        "-show_streams", "-show_format", "-of", "json", str(path)], capture_output=True, text=True,
        timeout=120, check=True)
    return json.loads(result.stdout)


def video_stream(info, *, require_audio=True):
    stream = next((s for s in info["streams"] if s.get("codec_type") == "video"), None)
    if not stream or Fraction(stream["avg_frame_rate"]) != 24 or Fraction(stream["r_frame_rate"]) != 24:
        raise ValueError("Turbo/LTX requires a valid constant 24 fps video.")
    if require_audio and not any(s.get("codec_type") == "audio" for s in info["streams"]):
        raise ValueError("Turbo/LTX output must retain the original H3 audio.")
    return stream


def prepare_refinement(take, *, data_root, input_root, save_plan=None):
    request = take["input_snapshot"]
    from story_builder.services.minimax_h3_t2v import T2V_GRAPH_PATH
    from story_builder.services.isolated_fl2va_contract import FL2VA_GRAPH_PATH
    from story_builder.services.isolated_r2v_contract import GRAPH_PATH as R2V_GRAPH_PATH
    graph_path = {"minimax_h3_t2v_local_v1": T2V_GRAPH_PATH,
                  "minimax_h3_fl2va_first_last_v1": FL2VA_GRAPH_PATH,
                  "minimax_h3_r2v_dynamic_v1": R2V_GRAPH_PATH}[request["workflow_id"]]
    if request["workflow_sha256"] != pipeline_digest(graph_path):
        raise ValueError("Pinned Turbo/LTX graphs changed since submission.")
    root, inputs = Path(data_root).resolve(), Path(input_root).resolve()
    original = take["pipeline"]["original"]
    source = (root / original["relative_path"]).resolve()
    source.relative_to(intermediate_root(root, take["project_id"], "originals"))
    if not source.is_file() or digest(source) != original["sha256"]:
        raise ValueError("Saved Turbo original is missing or changed; refinement cannot resume.")
    v = video_stream(probe(source))
    count = int(v["nb_read_frames"])
    pipeline = take["pipeline"]
    plan = pipeline.get("ltx_chunks")
    # An already submitted legacy whole-clip job must reconcile its original graph.
    if plan is None and not take.get("prompt_id"):
        from story_builder.services.ltx_chunks import plan_chunks
        plan = plan_chunks(source, count)
        if save_plan is None:
            raise ValueError("Chunk planning requires a durable ledger checkpoint.")
        save_plan(take, plan)
        pipeline["ltx_chunks"] = plan
        pipeline["ltx_chunk_outputs"] = []
        pipeline["ltx_chunk_index"] = 0
    index = pipeline.get("ltx_chunk_index", 0)
    window = plan[index] if plan is not None else {
        "start": 0, "end": count, "frames": count,
        "padded_frames": count + (-(count - 1)) % 8}
    folder = inputs / "vibe_t2v" / take["job_id"]
    folder.mkdir(parents=True, exist_ok=True)
    # Distinct loader input paths prevent a cached earlier window being reused.
    target = folder / (f"ltx_chunk_{index:04d}.mkv" if plan is not None else "ltx_input.mkv")
    partial = target.with_suffix(".tmp.mkv")
    from story_builder.services.ltx_chunks import split_input
    split_input(source, window, partial)
    os.replace(partial, target)
    graph = json.loads(LTX_GRAPH_PATH.read_text())
    graph["5022"]["inputs"]["file"] = target.relative_to(inputs).as_posix()
    width, height = final_dimensions(request["resolution_preset"], request["aspect_ratio"])
    graph["5007"]["inputs"].update(width=width, height=height)
    graph["2483"]["inputs"]["text"] = request["prompt"] + "\nPreserve the input video's composition, subjects, action, camera movement and lighting. Refine detail without adding objects or changing the scene."
    graph["5014"]["inputs"]["filename_prefix"] = f"isolated/{take['project_id']}/{take['take_id']}/ltx" + (f"_chunk_{index:04d}" if plan is not None else "")
    return graph, lambda: target.unlink(missing_ok=True)


def remux_final(take, refined, destination, *, data_root):
    root = Path(data_root).resolve()
    original = take["pipeline"]["original"]
    source = (root / original["relative_path"]).resolve()
    source.relative_to(intermediate_root(root, take["project_id"], "originals"))
    if digest(source) != original["sha256"]:
        raise ValueError("Original H3 audio source changed.")
    request = take["input_snapshot"]
    frames = math.ceil(request["duration_seconds"] * 24)
    seconds = frames / 24
    width, height = final_dimensions(request["resolution_preset"], request["aspect_ratio"])
    refined_stream = video_stream(probe(refined), require_audio=False)
    if (refined_stream["width"], refined_stream["height"]) != (width, height) or int(refined_stream["nb_read_frames"]) < frames:
        raise ValueError("LTX output does not match the requested final canvas or duration.")
    subprocess.run([os.environ.get("FFMPEG", "ffmpeg"), "-nostdin", "-v", "error", "-y",
        "-i", str(refined), "-i", str(source), "-map", "0:v:0", "-map", "1:a:0",
        "-c", "copy", "-frames:v", str(frames), "-t", str(seconds), "-movflags", "+faststart", str(destination)],
        capture_output=True, timeout=180, check=True)
    result = probe(destination)
    v = video_stream(result)
    if (v["width"], v["height"]) != (width, height) or int(v["nb_read_frames"]) != frames:
        raise ValueError("Final Turbo/LTX video failed exact dimensions/frame-count validation.")
    return result
