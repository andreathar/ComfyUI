import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import production_generate as pg
import production_validate as pv

EXAMPLE = json.loads((pv.SPEC / "example.production.json").read_text())
TEXT = EXAMPLE["project"]["source_text"]


def scripted(*replies):
    calls = []

    def backend(system, messages, model):
        calls.append(copy.deepcopy(messages))
        return replies[len(calls) - 1]
    backend.calls = calls
    return backend


class GenerateTests(unittest.TestCase):
    def test_valid_reply_returns_document_with_fences_stripped(self):
        backend = scripted("```json\n" + json.dumps(EXAMPLE) + "\n```")
        self.assertEqual(pg.generate(TEXT, backend), {"document": EXAMPLE})
        self.assertEqual(len(backend.calls), 1)

    def test_problems_are_fed_back_then_fixed(self):
        bad = copy.deepcopy(EXAMPLE)
        bad["shots"][0]["lens"] = "20mm"
        backend = scripted(json.dumps(bad), json.dumps(EXAMPLE))
        self.assertIn("document", pg.generate(TEXT, backend))
        feedback = backend.calls[1][-1]["content"]
        self.assertIn("shots/0/lens", feedback)
        self.assertIn("Fix only these", feedback)

    def test_gives_up_after_max_rounds_with_problems(self):
        bad = copy.deepcopy(EXAMPLE)
        bad["shots"][0]["lens"] = "20mm"
        backend = scripted(*[json.dumps(bad)] * (pg.MAX_ROUNDS + 1))
        result = pg.generate(TEXT, backend)
        self.assertEqual(len(backend.calls), pg.MAX_ROUNDS + 1)
        self.assertTrue(any("lens" in p for p in result["problems"]))

    def test_questions_are_returned_not_validated(self):
        questions = [{"about": "DEMO-CHR-MAIN", "ask": "Voice?"}]
        self.assertEqual(pg.generate(TEXT, scripted(json.dumps({"questions": questions}))), {"questions": questions})

    def test_changed_source_text_is_rejected(self):
        edited = copy.deepcopy(EXAMPLE)
        edited["project"]["source_text"] = TEXT + " "
        result = pg.generate(TEXT, scripted(*[json.dumps(edited)] * (pg.MAX_ROUNDS + 1)))
        self.assertIn("source_text", result["problems"][0])

    def test_non_json_reply_is_a_problem_not_a_crash(self):
        result = pg.generate(TEXT, scripted(*["no json here"] * (pg.MAX_ROUNDS + 1)))
        self.assertIn("no JSON", result["problems"][0])

    def test_message_carries_rules_schema_and_dictation(self):
        message = pg.user_message("hello", "style", "")
        for tag in ("<rules>", "<schema>", "<style_bible>", "<existing>", "<dictation>\nhello"):
            self.assertIn(tag, message)
        self.assertIn("production document", pg.system_prompt())

    def test_main_writes_valid_file_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, out = Path(tmp) / "d.txt", Path(tmp) / "p.json"
            source.write_text(TEXT)
            with patch.dict(pg.BACKENDS, {"claude-cli": scripted(json.dumps(EXAMPLE))}):
                self.assertEqual(pg.main([str(source), "--out", str(out)]), 0)
                self.assertEqual(json.loads(out.read_text()), EXAMPLE)
                self.assertEqual(pg.main([str(source), "--out", str(out)]), 2)

    def test_main_writes_nothing_when_model_asks_questions(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, out = Path(tmp) / "d.txt", Path(tmp) / "p.json"
            source.write_text(TEXT)
            reply = json.dumps({"questions": [{"about": "x", "ask": "y"}]})
            with patch.dict(pg.BACKENDS, {"claude-cli": scripted(reply)}):
                self.assertEqual(pg.main([str(source), "--out", str(out)]), 1)
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
