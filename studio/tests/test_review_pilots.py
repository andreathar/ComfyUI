import unittest
import hashlib
import json
from pathlib import Path
import tempfile
from copy import deepcopy
from unittest.mock import patch

from review_pilots import cancel, convert, run


class PilotConversionTests(unittest.TestCase):
    def test_receipt_failure_after_submission_cancels_owned_prompt(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'user/default/workflows/test.json'
            source.parent.mkdir(parents=True)
            source.write_text(json.dumps(self.graph))
            calls = []
            def request(path, body=None):
                calls.append((path, body))
                if path == '/object_info':
                    return self.schemas
                if path == '/queue':
                    return {'queue_running': [], 'queue_pending': []}
                return {}
            original = Path.write_text
            def write(path, text, *args, **kwargs):
                if path.name == 'result.json' and json.loads(text)['status'] == 'queued':
                    raise OSError('disk full')
                return original(path, text, *args, **kwargs)
            with patch('review_pilots.ROOT', root), patch('review_pilots.PILOTS', {'test': 'test.json'}), \
                    patch('review_pilots.REVIEWED_HASHES', {'test': hashlib.sha256(source.read_bytes()).hexdigest()}), \
                    patch('review_pilots.request', side_effect=request), \
                    patch('review_pilots.resources', return_value={'ram_available': 20 * 1024**3, 'temperature_c': 50, 'gpu_utilization': 0}), \
                    patch.object(Path, 'write_text', write):
                folder = run('test', True, root / 'results', 60)
            receipt = json.loads((folder / 'result.json').read_text())
            self.assertEqual(receipt['status'], 'monitor_error')
            self.assertIn(('/api/jobs/' + receipt['prompt_id'] + '/cancel', {}), calls)

    def setUp(self):
        self.schemas = {
            "CLIPTextEncode": {"input": {"required": {"text": ["STRING", {}]}}},
            "SaveImage": {"input": {"required": {"images": ["IMAGE", {}], "filename_prefix": ["STRING", {}]}}},
        }
        self.graph = {"nodes": [
            {"id": 1, "type": "CLIPTextEncode", "widgets_values": ["test"], "inputs": []},
            {"id": 2, "type": "SaveImage", "widgets_values": ["audit"],
             "inputs": [{"name": "images", "link": 1}]},
        ], "links": [[1, 1, 0, 2, 0, "IMAGE"]]}

    def test_widget_and_link_mapping(self):
        result = convert(self.graph, self.schemas)
        self.assertEqual(result["1"]["inputs"], {"text": "test"})
        self.assertEqual(result["2"]["inputs"], {"images": ["1", 0], "filename_prefix": "audit"})

    def test_named_widgets_take_precedence(self):
        self.graph["nodes"][1]["widgets_values_named"] = {"filename_prefix": "named"}
        self.assertEqual(convert(self.graph, self.schemas)["2"]["inputs"]["filename_prefix"], "named")

    def test_does_not_modify_original(self):
        before = deepcopy(self.graph)
        convert(self.graph, self.schemas)
        self.assertEqual(self.graph, before)

    def test_rejects_unknown_code_node(self):
        self.graph["nodes"][0]["type"] = "CustomCode"
        with self.assertRaisesRegex(ValueError, "approved pilot"):
            convert(self.graph, self.schemas)

    def test_rejects_muted_graph(self):
        self.graph["nodes"][0]["mode"] = 2
        with self.assertRaisesRegex(ValueError, "approved pilot"):
            convert(self.graph, self.schemas)

    def test_cancellation_is_always_prompt_specific(self):
        record = {"prompt_id": "owned-prompt"}
        with patch("review_pilots.request") as request:
            cancel(record)
        request.assert_called_once_with("/api/jobs/owned-prompt/cancel", {})
        self.assertIn("completion not confirmed", record["cancellation"])

    def test_cancellation_failure_is_recorded(self):
        record = {"prompt_id": "owned-prompt"}
        with patch("review_pilots.request", side_effect=OSError("offline")):
            cancel(record)
        self.assertIn("failed: offline", record["cancellation"])

    def test_rejects_subgraph(self):
        self.graph["definitions"] = {"subgraphs": [{"id": "example"}]}
        with self.assertRaisesRegex(ValueError, "subgraphs"):
            convert(self.graph, self.schemas)


if __name__ == "__main__":
    unittest.main()
