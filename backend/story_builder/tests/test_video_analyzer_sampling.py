"""Bound PE-AV input without loading weights, Torch or a GPU.

Modality projection stubs adapted from Story Builder's test_peav_adapter.py.
"""
from contextlib import nullcontext
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest

source = Path(__file__).resolve().parents[3] / "local_data/engines/video-analyzer/src/video_audio_analyzer/peav_adapter.py"
spec = importlib.util.spec_from_file_location("vibe_peav_adapter", source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Tensor:
    def detach(self): return self
    def float(self): return self
    def cpu(self): return self
    def tolist(self): return [[0.25, 0.75]]


class Batch(dict):
    def to(self, device): return self


class SamplingTests(unittest.TestCase):
    def adapter(self):
        adapter = object.__new__(module.PEAVAdapter)
        adapter.device = SimpleNamespace(type="cpu")
        adapter.torch = SimpleNamespace(bfloat16=object(),
            inference_mode=nullcontext, autocast=lambda *args, **kwargs: nullcontext())
        adapter._hf_format = True
        self.calls = []
        def process(**kwargs):
            self.calls.append(kwargs)
            return Batch(input_values="audio", padding_mask="audio-mask",
                pixel_values_videos="video", padding_mask_videos="video-mask", input_ids="text")
        adapter.transform = process
        adapter.model = SimpleNamespace(
            get_audio_embeds=lambda values, mask: Tensor(),
            get_video_embeds=lambda values, mask: Tensor(),
            get_text_audio_video_embeds=lambda values, mask: Tensor())
        return adapter

    def test_video_only_samples_sixteen_full_scene_frames(self):
        output = self.adapter().embed(video="scene.mp4")
        self.assertEqual(self.calls[0]["videos_kwargs"], {"do_sample_frames": True, "num_frames": 16})
        self.assertEqual(output["video_embeds"], [[0.25, 0.75]])

    def test_joint_audio_video_uses_same_frame_bound_and_preserves_audio(self):
        adapter = self.adapter()
        adapter.model = lambda **kwargs: SimpleNamespace(audio_video_embeds=Tensor())
        output = adapter.embed(video="scene.mp4", audio="scene.mp4")
        self.assertEqual(self.calls[0]["videos_kwargs"]["num_frames"], 16)
        self.assertEqual(self.calls[0]["audio"], "scene.mp4")
        self.assertEqual(output["audio_video_embeds"], [[0.25, 0.75]])

    def test_audio_and_text_only_do_not_request_video_sampling(self):
        for modality, path in (("audio", "event.wav"), ("text", "a rainy street")):
            with self.subTest(modality=modality):
                self.adapter().embed(**{modality: path})
                self.assertEqual(self.calls[0]["videos_kwargs"], {})

    def test_legacy_processor_receives_no_hf_specific_parameters(self):
        adapter = self.adapter()
        adapter._hf_format = False
        adapter.model = lambda **kwargs: SimpleNamespace(video_embeds=Tensor())
        adapter.embed(video="scene.mp4")
        self.assertEqual(self.calls[0], {"videos": "scene.mp4", "audio": None, "text": None})


if __name__ == "__main__":
    unittest.main()
