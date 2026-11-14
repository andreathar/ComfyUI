#!/usr/bin/env python3
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from master_studio_compiler import align_h3_frames, format_summary, plan_frames


class MasterStudioCompilerTests(unittest.TestCase):
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
        plan = plan_frames(3.0, 24.0, transition="continue", chain_active=True)
        text = format_summary("P", "MSG_S001_SH05", 832, 480, plan, 20, 12, 3, transition="continue")
        self.assertIn("raw ", text)
        self.assertIn("delivered ", text)
        self.assertIn("Transition: continue", text)


if __name__ == "__main__":
    unittest.main()
