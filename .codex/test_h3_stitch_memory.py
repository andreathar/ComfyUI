import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import torch
import comfy.model_management as mm

spec = importlib.util.spec_from_file_location("h3_facerefine", ROOT / "custom_nodes/comfyui-h3-facerefine/nodes.py")
h3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h3)


class StitchMemoryTests(unittest.TestCase):
    def test_small_batches_preserve_composite_and_untracked_frames(self):
        torch.manual_seed(42)
        base = torch.rand(7, 48, 64, 3)
        crops = torch.rand(5, 32, 32, 3)
        transform = {"boxes": [[12, 8, 32, 32]] * 5, "canvas": [32, 32],
                     "src_size": [64, 48], "source": [0, 2, 3, 5, 6],
                     "weights": [1, 0.5, 0, 1, 1]}
        original = base.clone()
        with patch.object(mm, "get_torch_device", return_value=torch.device("cpu")):
            for region in ("full_crop", "face_only", "face_ellipse"):
                for masks in (None, torch.rand(5, 32, 32)):
                    args = dict(base_images=base, refined_crops=crops, transform=transform,
                                paste_region=region, mask_dilation=1, feather=3,
                                colour_match=1, blend=0.8, masks=masks)
                    expected = h3.H3FaceStitch().run(**args, stitch_batch_size=32)[0]
                    for batch in (1, 2, 4):
                        result = h3.H3FaceStitch().run(**args, stitch_batch_size=batch)[0]
                        torch.testing.assert_close(result, expected, rtol=1e-5, atol=1e-6)
                        torch.testing.assert_close(result[[1, 4]], original[[1, 4]], rtol=0, atol=0)
                        self.assertTrue(torch.isfinite(result).all())
        torch.testing.assert_close(base, original, rtol=0, atol=0)

    def test_existing_callers_keep_working(self):
        base = torch.zeros(1, 16, 16, 3)
        transform = {"boxes": [[0, 0, 16, 16]], "canvas": [16, 16], "src_size": [16, 16]}
        with patch.object(mm, "get_torch_device", return_value=torch.device("cpu")):
            result = h3.H3FaceStitch().run(base, base, transform, "full_crop", 0, 1, 0, 1)[0]
        torch.testing.assert_close(result, base)


if __name__ == "__main__":
    unittest.main()
