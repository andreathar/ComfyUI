#!/usr/bin/env python3
from pathlib import Path
import ast
import json
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from master_studio_compiler import align_h3_frames, plan_frames, with_runtime_report


class MasterStudioCompilerTests(unittest.TestCase):
    def test_generated_summary_does_not_claim_unobserved_settings(self):
        source = Path(__file__).resolve().parents[1] / 'build_master_movie_studio_workflow.py'
        tree = ast.parse(source.read_text())
        code = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
                    and isinstance(node.value, ast.Constant) and any(isinstance(t, ast.Name) and t.id == 'VARS_CODE' for t in node.targets))
        for width, height in [(640, 640), (832, 480)]:
            with self.subTest(width=width, height=height):
                env = {'inputs': ['P', 'MSG_A', width, height, 3, 24, 20, 12, 3, 'cut', False], 'outputs': []}
                exec(code, env)
                text = env['outputs'][9]
                self.assertIn(f'Canvas: {width}×{height}', text)
                self.assertIn('raw 73f / delivered 73f', text)
                self.assertIn('20 steps', text)
                self.assertIn('shifts 12/3', text)
                for claim in ('16:9', 'sa_solver', 'beta', 'CK int8'):
                    self.assertNotIn(claim, text)
                self.assertIn('Sampler / scheduler / attention: not observed by controls.', text)

    def test_runtime_report_preserves_every_generation_output(self):
        source = Path(__file__).resolve().parents[1] / 'build_master_movie_studio_workflow.py'
        tree = ast.parse(source.read_text())
        code = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
                    and isinstance(node.value, ast.Constant) and any(isinstance(t, ast.Name) and t.id == 'VARS_CODE' for t in node.targets))
        for width, height, fps, transition, chain, raw, delivered, trim, continuing in [
            (832, 480, 24, 'cut', True, 73, 73, 0, False),
            (832, 480, 24, 'continue', True, 107, 85, 22, True),
            (832, 480, 24, 'continue', False, 73, 73, 0, False),
            (640, 640, 23.976, 'cut', False, 73, 73, 0, False),
        ]:
            before = {'inputs': ['P', 'MSG_A', width, height, 3, fps, 20, 12, 3, transition, chain], 'outputs': []}
            after = {'inputs': before['inputs'][:], 'outputs': []}
            exec(code, before); exec(with_runtime_report(code), after)
            self.assertEqual(before['outputs'][:9] + before['outputs'][10:], after['outputs'][:9] + after['outputs'][10:])
            report = json.loads(after['outputs'][9])
            self.assertEqual(report['summary'], before['outputs'][9])
            self.assertEqual(report['values']['raw_frames'], after['outputs'][4])
            self.assertEqual(report['values']['delivered_frames'], after['outputs'][10])
            self.assertEqual(report['values']['fps'], after['outputs'][5])
            self.assertEqual(after['outputs'][:9] + after['outputs'][10:],
                             ['P', 'MSG_A', width, height, raw, 24, 20, 12.0, 3.0, delivered, trim, continuing])
            if transition == 'continue' and not chain:
                self.assertIn('Transition: continue (cut)', report['summary'])

    def test_generated_controls_use_the_delivered_integer_fps_consistently(self):
        source = Path(__file__).resolve().parents[1] / 'build_master_movie_studio_workflow.py'
        tree = ast.parse(source.read_text())
        code = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
                    and any(isinstance(target, ast.Name) and target.id == 'VARS_CODE' for target in node.targets))
        namespace = {'inputs': ['P', 'MSG_A', 832, 480, 3, 23.976, 20, 12, 3, 'cut', False], 'outputs': []}
        exec(code, namespace)
        self.assertEqual(namespace['outputs'][5], 24)
        self.assertIn('@ 24 fps', namespace['outputs'][9])
        self.assertEqual(plan_frames(3, 23.976)['fps'], 23.976)

    def test_align_matches_silent_medium(self):
        self.assertEqual(align_h3_frames(72), 73)
        self.assertEqual(align_h3_frames(5), 5)

    def test_cut_three_seconds(self):
        plan = plan_frames(3.0, 24.0, transition="cut", chain_active=True)
        self.assertEqual(plan, {
            "raw_frames": 73, "delivered_frames": 73, "trim_frames": 0,
            "continuing": False, "fps": 24.0, "delivered_s": 73 / 24.0, "raw_s": 73 / 24.0,
        })

    def test_continue_inflates_then_trims(self):
        plan = plan_frames(3.0, 24.0, transition="continue", chain_active=True)
        # requested 72 + overlap 22 = 94 → align to 17k+5
        raw = align_h3_frames(72 + 22)
        self.assertEqual(plan["raw_frames"], raw)
        self.assertEqual(plan["trim_frames"], 22)
        self.assertEqual(plan["delivered_frames"], raw - 22)
        self.assertTrue(plan["continuing"])

    def test_continue_without_chain_is_cut(self):
        plan = plan_frames(3.0, 24.0, transition="continue", chain_active=False)
        self.assertEqual(plan["raw_frames"], 73)
        self.assertEqual(plan["trim_frames"], 0)
        self.assertFalse(plan["continuing"])

    def test_summary_names_both_lengths(self):
        source = Path(__file__).resolve().parents[1] / 'build_master_movie_studio_workflow.py'
        tree = ast.parse(source.read_text())
        code = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
                    and isinstance(node.value, ast.Constant) and any(isinstance(t, ast.Name) and t.id == 'VARS_CODE' for t in node.targets))
        env = {'inputs': ['P', 'MSG_S001_SH05', 832, 480, 3, 24, 20, 12, 3, 'continue', True], 'outputs': []}
        exec(code, env)
        text = env['outputs'][9]
        self.assertIn('raw 107f / delivered 85f', text)
        self.assertIn('trim 22', text)
        self.assertIn('Transition: continue (continue)', text)


if __name__ == "__main__":
    unittest.main()
