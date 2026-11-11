import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import h3_loop
import h3_recipe
import h3_loop_run


class LoopContractTests(unittest.TestCase):
    def setUp(self):
        recipe = copy.deepcopy(h3_recipe.SILENT_MEDIUM)
        shot = dict(shot_id='MSG_S001_SH01', recipe=recipe, frames=73, seed=1,
                    prompt_text='Empty cafe', assets={}, media_state=[], stack_state={'picks': []})
        self.bundle = h3_loop.export([shot], 'silent_test')
        self.graph = {
            '2': {'class_type': 'UNETLoader', 'inputs': {'unet_name': recipe['models']['diffusion_models']}},
            '3': {'class_type': 'MiniMaxH3SigmaShift', 'inputs': {'model': ['2', 0], 'shift_video': 12, 'shift_audio': 3}},
            '4': {'class_type': 'CLIPLoader', 'inputs': {'clip_name': recipe['models']['text_encoders'], 'type': 'minimax'}},
            '5': {'class_type': 'VAELoader', 'inputs': {'vae_name': recipe['models']['video_vae']}},
            '7': {'class_type': 'MiniMaxH3RefModStack', 'inputs': {'stack_state': ['36', 1]}},
            '9': {'class_type': 'MiniMaxH3FantasticRefModTextEncode', 'inputs': {
                'clip': ['4', 0], 'vae': ['5', 0], 'mods': ['7', 0], 'references': ['21', 0],
                'prompt': ['35', 4], 'length': ['35', 6], 'width': ['35', 8], 'height': ['35', 9],
                **{k: recipe[k] for k in ('ref_image_size', 'reference_fps', 'max_total_tokens',
                   'voice_description_at_label', 'stack_pictures', 'stack_pictures_n')}}},
            '13': {'class_type': 'KSamplerSelect', 'inputs': {'sampler_name': recipe['sampler']}},
            '14': {'class_type': 'BasicScheduler', 'inputs': {'model': ['3', 0], 'scheduler': recipe['scheduler'], 'denoise': 1, 'steps': ['35', 7]}},
            '15': {'class_type': 'RandomNoise', 'inputs': {'noise_seed': ['35', 5]}},
            '21': {'class_type': 'MiniMaxH3MediaLoader', 'inputs': {'media_state': ['36', 2]}},
            '31': {'class_type': 'DynamicScriptNode', 'inputs': {'code': h3_loop.PLAN_CODE, 'input_0': ['30', 0], 'output_ports_count': 8, 'use_module_cache': False}},
            '32': {'class_type': 'MiniMaxH3GenerationProfile', 'inputs': {'scene_continuity': 'Independent scenes', 'audio_profile': 'No final audio'}},
            '33': {'class_type': 'MiniMaxH3ChainPlanModern', 'inputs': {'chain_policy': ['32', 0], 'plan_json_input': ['31', 1], 'generation_fingerprint': ['31', 2], 'run_name': ['31', 3], 'width': ['31', 4], 'height': ['31', 5], 'encode_mode': 'video', 'video_blend_frames': 0}},
            '36': {'class_type': 'DynamicScriptNode', 'inputs': {'code': h3_loop.SELECT_CODE, 'input_0': ['30', 0], 'input_1': ['35', 1], 'use_module_cache': False}},
            '37': {'class_type': 'MiniMaxH3LoopTrim', 'inputs': {'fps': ['31', 8], 'trim_frames': 0}},
            '38': {'class_type': 'MiniMaxH3ChainSegmentSave', 'inputs': {}},
            '40': {'class_type': 'MiniMaxH3ChainAssemble', 'inputs': {'audio_source': ['31', 6], 'output_subfolder': ['31', 7], 'filename': 'draft', 'copy_to_output': True, 'delete_checkpoints_after_assembly': False}},
        }

    def test_bundle_driven_silent_contract(self):
        self.assertEqual(h3_loop_run.check_graph(self.bundle, self.graph), [])

    def test_stale_dimensions_and_wrong_script_fail(self):
        self.graph['33']['inputs']['width'] = 608
        self.graph['31']['inputs']['code'] = 'old script'
        errors = h3_loop_run.check_graph(self.bundle, self.graph)
        self.assertTrue(any('33.width' in e for e in errors))
        self.assertTrue(any('31.code' in e for e in errors))

    def test_audio_routes_cannot_survive_silent_contract(self):
        self.graph['38']['inputs']['audio'] = ['18', 0]
        self.graph['32']['inputs']['audio_profile'] = 'Generate audio'
        errors = h3_loop_run.check_graph(self.bundle, self.graph)
        self.assertTrue(any('38.audio' in e for e in errors))
        self.assertTrue(any('32.audio_profile' in e for e in errors))

    def test_changed_bundle_is_rejected_before_graph_check(self):
        self.bundle['shots'][0]['seed'] = 9
        with self.assertRaisesRegex(ValueError, 'fingerprint'):
            h3_loop_run.check_graph(self.bundle, self.graph)

    def test_missing_required_node_is_an_actionable_failure(self):
        del self.graph['9']
        errors = h3_loop_run.check_graph(self.bundle, self.graph)
        self.assertTrue(any('node 9' in e for e in errors))
