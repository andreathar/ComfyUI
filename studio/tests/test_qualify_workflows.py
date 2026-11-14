import json
from pathlib import Path
import tempfile
import unittest

from qualify_workflows import inventory, model_roots, qualify


class QualificationTests(unittest.TestCase):
    def test_inventory_follows_models_and_category_symlinks(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            weights = root / "weights"
            weights.mkdir()
            (weights / "tiny.gguf").write_bytes(b"test")
            models = root / "models"
            models.mkdir()
            (models / "unet").symlink_to(weights, target_is_directory=True)
            files, errors = inventory([models, weights])
            self.assertFalse(errors)
            self.assertEqual(len(files), 1)
            self.assertEqual(files[0]["bytes"], 4)
            self.assertEqual(len(files[0]["search_roots"]), 2)

    def test_missing_root_is_visible(self):
        files, errors = inventory([Path("/nonexistent-workflow-review-test-models")])
        self.assertFalse(files)
        self.assertEqual(len(errors), 1)

    def test_extra_paths_use_config_relative_base(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "extra_model_paths.yaml").write_text("hot:\n  base_path: hot\n  unet: unet/\n")
            self.assertIn(root / "hot/unet", model_roots(root))

    def test_match_is_not_claimed_as_compatibility(self):
        workflow = {"id": "wf-1", "title": "test", "node_types": [], "aliases": [], "blockers": [],
                    "model_references": [{"reference": "model.gguf", "basis": "filename_heuristic"}]}
        result = qualify(workflow, [{"filename": "model.gguf", "path": "/weights/model.gguf"}])
        self.assertEqual(result["models"][0]["disk_status"], "basename_candidates_found")
        self.assertEqual(result["hardware_fit"], "unproven")
        self.assertEqual(result["runtime"], "not_run_by_catalogue")
        self.assertIn("unverified", result["models"][0]["compatibility"])

    def test_absent_filename_is_blocker_not_runtime_failure(self):
        workflow = {"id": "wf-1", "title": "test", "node_types": [], "aliases": [], "blockers": [],
                    "model_references": [{"reference": "absent.gguf", "basis": "filename_heuristic"}]}
        result = qualify(workflow, [])
        self.assertEqual(result["disposition"], "blocked_or_review_needed")
        self.assertEqual(result["runtime"], "not_run_by_catalogue")


if __name__ == "__main__":
    unittest.main()
