import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from PIL import Image

from review_utilities import collect_outputs, execute, prompts


class UtilityTests(unittest.TestCase):
    def test_prompts_are_model_free_and_use_only_reviewed_nodes(self):
        graphs = prompts("a.png", "b.png")
        self.assertEqual(len(graphs), 6)
        allowed = {"LoadImage", "PreviewImage", "ImageBatch", "AILab_ImagePreview", "AILab_MaskPreview",
                   "AILab_ImageStitch", "iToolsPromptRecord", "iToolsAddOverlay", "VHS_VideoCombine", "LCImageDesaturate"}
        self.assertEqual({n["class_type"] for graph in graphs.values() for n in graph.values()}, allowed)
        self.assertEqual(graphs["gif"]["4"]["inputs"]["format"], "image/gif")
        self.assertFalse(graphs["gif"]["4"]["inputs"]["save_output"])

    def test_collects_and_decodes_png(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "temp").mkdir()
            folder = root / "evidence"
            folder.mkdir()
            Image.new("RGB", (16, 8), "gray").save(root / "temp/image.png")
            with patch("review_utilities.ROOT", root):
                evidence = collect_outputs({"1": {"images": [{"type": "temp", "filename": "image.png"}]}}, folder)
            self.assertEqual(evidence[0]["size"], [16, 8])
            self.assertTrue(evidence[0]["equal_rgb_channels"])
            self.assertTrue(Path(evidence[0]["copy"]).is_file())

    def test_output_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch("review_utilities.ROOT", Path(temp)):
                with self.assertRaisesRegex(ValueError, "escaped"):
                    collect_outputs({"1": {"images": [{"type": "temp", "filename": "../../escape.png"}]}}, Path(temp))

    def test_unknown_output_type_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "storage type"):
            collect_outputs({"1": {"images": [{"type": "input", "filename": "fixture.png"}]}}, Path("unused"))

    def test_keyboard_interrupt_cancels_owned_prompt_and_persists(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            with patch("review_utilities.request", side_effect=[{"queue_running": [], "queue_pending": []}, {}, KeyboardInterrupt]), \
                 patch("review_utilities.resources", return_value={"ram_available": 3 * 1024**3, "temperature_c": 40}), \
                 patch("review_utilities.cancel") as cancel:
                with self.assertRaises(KeyboardInterrupt):
                    execute("prompt-record", prompts("a", "b")["prompt-record"], folder)
            self.assertEqual(cancel.call_count, 1)
            result = json.loads((folder / "result.json").read_text())
            self.assertEqual(result["status"], "operator_interrupted")

    def test_both_preview_node_outputs_are_required(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            def fake_request(route, data=None):
                if route == "/queue":
                    return {"queue_running": [], "queue_pending": []}
                if route.startswith("/history/"):
                    return {route.rsplit("/", 1)[1]: {"status": {"status_str": "success", "completed": True}, "outputs": {}}}
                return {}
            with patch("review_utilities.request", side_effect=fake_request), \
                 patch("review_utilities.resources", return_value={"ram_available": 3 * 1024**3, "temperature_c": 40}), \
                 patch("review_utilities.collect_outputs", return_value=[{"node_id": "2"}]):
                record = execute("previews", prompts("a", "b")["previews"], folder)
            self.assertFalse(record["contract_passed"])

    def test_gif_frames_are_counted(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "temp").mkdir()
            folder = root / "evidence"
            folder.mkdir()
            a, b = Image.new("RGB", (8, 8), "red"), Image.new("RGB", (8, 8), "blue")
            a.save(root / "temp/test.gif", save_all=True, append_images=[b], duration=500)
            with patch("review_utilities.ROOT", root):
                evidence = collect_outputs({"1": {"gifs": [{"type": "temp", "filename": "test.gif"}]}}, folder)
            self.assertEqual(evidence[0]["frames"], 2)
            self.assertEqual(evidence[0]["format"], "GIF")
            data = (root / "temp/test.gif").read_bytes()
            (root / "temp/truncated.gif").write_bytes(data[:-3])
            with patch("review_utilities.ROOT", root):
                with self.assertRaises(OSError):
                    collect_outputs({"1": {"gifs": [{"type": "temp", "filename": "truncated.gif"}]}}, folder)


if __name__ == "__main__":
    unittest.main()
