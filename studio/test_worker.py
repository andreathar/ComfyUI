import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import shot

PRESETS = json.loads((shot.STUDIO / "presets.json").read_text())


class PresetTests(unittest.TestCase):
    def test_aspect_3x4_present(self):
        self.assertEqual(PRESETS["aspects"]["3x4"], {"z-image": [864, 1152], "sd15": [384, 512]})

    def test_refine_template_fills(self):
        model = PRESETS["models"]["z-image-turbo"]
        values = {**model, "prompt": "p", "width": 64, "height": 64, "reference": "r.png", "seed": 1, "output": "o"}
        graph = shot.fill(shot.load_template("z-image-refine"), values)
        classes = {node["class_type"] for node in graph.values()}
        self.assertLessEqual({"VAEEncodeTiled", "VAEDecodeTiled"}, classes)
        self.assertNotIn("{{", json.dumps(graph))


if __name__ == "__main__":
    unittest.main()
