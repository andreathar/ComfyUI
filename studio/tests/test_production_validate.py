import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import production_validate as pv

EXAMPLE = json.loads((pv.SPEC / "example.production.json").read_text())


class ProductionValidateTests(unittest.TestCase):
    def broken(self, edit):
        doc = copy.deepcopy(EXAMPLE)
        edit(doc)
        return pv.check(doc)

    def assertProblem(self, problems, text):
        self.assertTrue(any(text in p for p in problems), f"{text!r} not in {problems}")

    def test_example_is_valid(self):
        self.assertEqual(pv.check(EXAMPLE), [])

    def test_partial_shot_lighting_is_valid_but_defaults_remain_complete(self):
        for lighting in ({'quality': 'soft'}, {'mood': 'tense'}):
            self.assertEqual(self.broken(lambda d: d['shots'][0].update(lighting=lighting)), [])
        self.assertProblem(self.broken(lambda d: d['style_bible'].update(lighting_default={'mood': 'tense'})), 'lighting_default')

    def test_schema_violation_is_reported_with_path(self):
        self.assertProblem(self.broken(lambda d: d["shots"][0].update(lens="20mm")), "shots/0/lens")

    def test_unknown_character_in_shot(self):
        self.assertProblem(self.broken(lambda d: d["shots"][0].update(characters=["DEMO-CHR-GHOST"])), "not in characters")

    def test_shot_character_must_be_in_scene_cast(self):
        def edit(d):
            d["characters"].append({**d["characters"][0], "id": "DEMO-CHR-OTHER"})
            d["shots"][0]["characters"] = ["DEMO-CHR-OTHER"]
        self.assertProblem(self.broken(edit), "not in the cast")

    def test_script_ref_outside_source_text(self):
        self.assertProblem(self.broken(lambda d: d["shots"][0].update(script_ref={"start": 0, "end": 9999})), "outside source_text")

    def test_speaker_without_voice(self):
        self.assertProblem(self.broken(lambda d: d["shots"][0].update(dialogue=[{"character": "DEMO-CHR-MAIN", "line": "Hi"}])), "no voice")

    def test_complex_motion_needs_motion_entity(self):
        self.assertProblem(self.broken(lambda d: d["shots"][0].update(complexity="complex-motion")), "needs a motion")

    def test_shot_numbers_must_be_consecutive(self):
        def edit(d):
            d["shots"][0]["id"] = "DEMO_S001_SH02"
        self.assertProblem(self.broken(edit), "consecutive")

    def test_scene_without_shots(self):
        def edit(d):
            d["scenes"].append({**d["scenes"][0], "id": "DEMO_S002", "number": 2})
        self.assertProblem(self.broken(edit), "has no shots")

    def test_lighting_must_match_scene_time(self):
        self.assertProblem(self.broken(lambda d: d["scenes"][0].update(
            lighting={"key": "sun", "quality": "hard", "time_of_day": "day"})), "contradicts scene time")

    def test_entity_must_use_project_code(self):
        def edit(d):
            d["characters"][0]["id"] = "OTHER-CHR-MAIN"
        self.assertProblem(self.broken(edit), "project code")


if __name__ == "__main__":
    unittest.main()
