import copy
from contextlib import nullcontext
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
    def test_cli_rejects_retired_cloud_backend(self):
        with self.assertRaises(SystemExit) as result:
            pg.main(['script.txt', '--out', 'production.json', '--log', 'unused.log', '--backend', 'claude-cli'])
        self.assertEqual(result.exception.code, 2)

    def test_local_reply_must_be_complete_and_from_the_requested_model(self):
        reply = {'model': 'different', 'choices': [{'finish_reason': 'stop', 'message': {'content': '{}'}}]}
        with (patch.object(pg, 'check_comfyui'), patch.object(pg, 'owns_listener', return_value=True),
              patch.object(pg, 'http', return_value=reply)):
            with self.assertRaisesRegex(pg.GenerateError, 'model'):
                pg.local_completion(12345, 'local-key', 10, 'rules', [], pg.DEFAULT_MODEL)

    def test_local_completion_never_sends_script_to_an_unowned_listener(self):
        with (patch.object(pg, 'check_comfyui'), patch.object(pg, 'owns_listener', return_value=False),
              patch.object(pg, 'http') as request):
            with self.assertRaisesRegex(pg.GenerateError, 'owns its listener'):
                pg.local_completion(12345, 'local-key', 10, 'rules', [], pg.DEFAULT_MODEL)
            request.assert_not_called()

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

    def test_revision_keeps_existing_script_unless_full_replacement_is_supplied(self):
        existing = json.dumps(EXAMPLE)
        backend = scripted(existing)
        self.assertEqual(pg.generate('Change the lens', backend, existing=existing), {'document': EXAMPLE})
        revised = copy.deepcopy(EXAMPLE)
        revised['project']['source_text'] = TEXT + ' Revised.'
        reply = json.dumps(revised)
        result = pg.generate('Replace the source', scripted(reply), existing=existing, revised_script=TEXT + ' Revised.')
        self.assertEqual(result, {'document': revised})
        result = pg.generate('Replace the source', scripted(*[reply] * (pg.MAX_ROUNDS + 1)), existing=existing)
        self.assertIn('source_text', result['problems'][0])

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
            with (patch.object(pg, 'local_server', return_value=nullcontext((12345, 'test-key', 10))) as server,
                  patch.object(pg, 'local_completion', return_value=json.dumps(EXAMPLE))):
                args = [str(source), '--out', str(out), '--log', str(Path(tmp) / 'worker.log')]
                self.assertEqual(pg.main(args), 0)
                self.assertIsNone(server.call_args.args[2])
                self.assertEqual(json.loads(out.read_text()), EXAMPLE)
                self.assertEqual(pg.main(args), 2)

    def test_main_writes_nothing_when_model_asks_questions(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, out = Path(tmp) / "d.txt", Path(tmp) / "p.json"
            source.write_text(TEXT)
            reply = json.dumps({"questions": [{"about": "x", "ask": "y"}]})
            with (patch.object(pg, 'local_server', return_value=nullcontext((12345, 'test-key', 10))),
                  patch.object(pg, 'local_completion', return_value=reply)):
                self.assertEqual(pg.main([str(source), '--out', str(out), '--log', str(Path(tmp) / 'worker.log')]), 1)
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
