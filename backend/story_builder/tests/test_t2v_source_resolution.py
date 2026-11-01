"""CPU-only checks of independent H3 source and LTX final canvases."""
import json
import unittest
from story_builder.services.minimax_h3_graph_compiler import ASPECT_RATIOS, ReferencePlan
from story_builder.services.minimax_h3_t2v import (
    LEGACY_T2V_GRAPH_PATH, T2V_RESOLUTION_PRESETS, compile_t2v_graph,
    final_dimensions, turbo_source_dimensions,
)


class SourceResolutionTests(unittest.TestCase):
    def test_all_qualities_and_ratios(self):
        for quality in T2V_RESOLUTION_PRESETS:
            for ratio in ASPECT_RATIOS:
                with self.subTest(quality=quality, ratio=ratio):
                    plan = ReferencePlan(1, 'p', 'r', 's', 'Exact authored prompt', 18,
                                         quality, ratio, 4, seed=17)
                    compiled = compile_t2v_graph(plan)
                    self.assertEqual((compiled['final_width'], compiled['final_height']),
                                     final_dimensions(quality, ratio))
                    self.assertEqual((compiled['width'], compiled['height']),
                                     turbo_source_dimensions(quality, ratio))
                    source = next(n['inputs'] for n in compiled['graph'].values()
                                  if n.get('class_type') == 'MiniMaxH3ImageToVideo')
                    self.assertEqual(source['prompt'], plan.prompt)
                    self.assertEqual(source['length'], 447)
                    if ratio in {'16:9', '9:16'}:
                        expected = (896, 512) if quality == 2 else (576, 320)
                        if ratio == '9:16':
                            expected = expected[::-1]
                        self.assertEqual((source['width'], source['height']), expected)
                    legacy = compile_t2v_graph(plan, base_graph=json.loads(LEGACY_T2V_GRAPH_PATH.read_text()))
                    self.assertEqual((legacy['width'], legacy['height']), final_dimensions(quality, ratio))
