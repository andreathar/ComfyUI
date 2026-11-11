import unittest
from copy import deepcopy
from unittest.mock import patch

from review_pilots import cancel, convert


class PilotConversionTests(unittest.TestCase):
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
