import copy
import hashlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


spec = importlib.util.find_spec("model_download")
downloader = None
if spec is not None:
    downloader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(downloader)


class Response(io.BytesIO):
    def __init__(self, body, status=200, content_range=None):
        super().__init__(body)
        self.status = status
        self.headers = {} if content_range is None else {"Content-Range": content_range}


class DownloadTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(downloader, "The model downloader has not been implemented")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "models"
        self.root.mkdir()
        self.body = b"verified-model-weights"
        self.model = {
            "folder": "checkpoints", "filename": "model.safetensors",
            "url": "https://huggingface.co/example/model/resolve/pinned/model.safetensors",
            "bytes": len(self.body), "sha256": hashlib.sha256(self.body).hexdigest(),
        }
        self.target = self.root / "checkpoints/model.safetensors"
        self.target.parent.mkdir()
        self.partial = self.target.with_name(self.target.name + ".part")

    def test_download_publishes_only_verified_bytes(self):
        with patch.object(downloader.urllib.request, "urlopen", return_value=Response(self.body)):
            self.assertEqual(downloader.download(self.root, self.model), "downloaded")
        self.assertEqual(self.target.read_bytes(), self.body)
        self.assertFalse(self.partial.exists())

    def test_existing_verified_file_needs_no_network(self):
        self.target.write_bytes(self.body)
        with patch.object(downloader.urllib.request, "urlopen", side_effect=AssertionError("Unexpected network")):
            self.assertEqual(downloader.download(self.root, self.model), "verified")
        self.assertEqual(self.target.read_bytes(), self.body)

    def test_existing_corrupt_file_is_preserved(self):
        self.target.write_bytes(b"keep this file")
        with self.assertRaises(ValueError):
            downloader.download(self.root, self.model)
        self.assertEqual(self.target.read_bytes(), b"keep this file")

    def test_resume_validates_range_and_preserves_prefix(self):
        self.partial.write_bytes(self.body[:8])

        def respond(request, **kwargs):
            self.assertEqual(request.get_header("Range"), "bytes=8-")
            return Response(self.body[8:], 206, f"bytes 8-{len(self.body)-1}/{len(self.body)}")

        with patch.object(downloader.urllib.request, "urlopen", side_effect=respond):
            self.assertEqual(downloader.download(self.root, self.model), "resumed")
        self.assertEqual(self.target.read_bytes(), self.body)

    def test_ignored_range_restarts_instead_of_appending(self):
        self.partial.write_bytes(self.body[:8])
        with patch.object(downloader.urllib.request, "urlopen", return_value=Response(self.body)):
            downloader.download(self.root, self.model)
        self.assertEqual(self.target.read_bytes(), self.body)

    def test_wrong_range_preserves_partial(self):
        self.partial.write_bytes(self.body[:8])
        with patch.object(downloader.urllib.request, "urlopen", return_value=Response(self.body[8:], 206, "bytes 0-12/21")):
            with self.assertRaises(ValueError):
                downloader.download(self.root, self.model)
        self.assertEqual(self.partial.read_bytes(), self.body[:8])
        self.assertFalse(self.target.exists())

    def test_bad_hash_is_not_published(self):
        with patch.object(downloader.urllib.request, "urlopen", return_value=Response(b"x" * len(self.body))):
            with self.assertRaises(ValueError):
                downloader.download(self.root, self.model)
        self.assertFalse(self.target.exists())
        self.assertTrue(self.partial.exists())

    def test_short_transfer_is_resumable_and_not_published(self):
        with patch.object(downloader.urllib.request, "urlopen", return_value=Response(self.body[:8])):
            with self.assertRaises(ValueError):
                downloader.download(self.root, self.model)
        self.assertFalse(self.target.exists())
        self.assertEqual(self.partial.read_bytes(), self.body[:8])

    def test_oversized_transfer_is_not_published(self):
        with patch.object(downloader.urllib.request, "urlopen", return_value=Response(self.body + b"extra")):
            with self.assertRaises(ValueError):
                downloader.download(self.root, self.model)
        self.assertFalse(self.target.exists())

    def test_complete_partial_is_published_without_network(self):
        self.partial.write_bytes(self.body)
        with patch.object(downloader.urllib.request, "urlopen", side_effect=AssertionError("Unexpected network")):
            downloader.download(self.root, self.model)
        self.assertEqual(self.target.read_bytes(), self.body)
        self.assertFalse(self.partial.exists())

    def test_low_disk_space_preserves_partial_and_existing_files(self):
        self.partial.write_bytes(self.body[:8])
        usage = type("Usage", (), {"free": 1})()
        with patch.object(downloader.shutil, "disk_usage", return_value=usage):
            with self.assertRaises(OSError):
                downloader.download(self.root, self.model)
        self.assertEqual(self.partial.read_bytes(), self.body[:8])
        self.assertFalse(self.target.exists())

    def test_filename_and_category_cannot_escape_root(self):
        for field, value in (("filename", "../outside.safetensors"), ("filename", "/tmp/outside.safetensors"), ("folder", "../../outside")):
            with self.subTest(field=field, value=value):
                model = copy.deepcopy(self.model)
                model[field] = value
                with self.assertRaises(ValueError):
                    downloader.model_path(self.root, model)

    def test_symlink_category_cannot_escape_root(self):
        outside = Path(self.tmp.name) / "outside"
        outside.mkdir()
        (self.root / "vae").symlink_to(outside, target_is_directory=True)
        self.model["folder"] = "vae"
        with self.assertRaises(ValueError):
            downloader.download(self.root, self.model)
        self.assertEqual(list(outside.iterdir()), [])

    def test_partial_symlink_is_not_followed(self):
        outside = Path(self.tmp.name) / "outside"
        outside.write_bytes(b"do not overwrite")
        self.partial.symlink_to(outside)
        with self.assertRaises(ValueError):
            downloader.download(self.root, self.model)
        self.assertEqual(outside.read_bytes(), b"do not overwrite")

    def test_non_https_source_is_rejected(self):
        self.model["url"] = "http://example.com/model.safetensors"
        with self.assertRaises(ValueError):
            downloader.download(self.root, self.model)
        self.assertFalse(self.target.exists())

    def test_missing_mount_does_not_create_model_directory(self):
        missing = Path(self.tmp.name) / "unmounted"
        with self.assertRaises(ValueError):
            downloader.storage_root({"storage": {"root": str(missing / "models"), "mount": str(missing)}})
        self.assertFalse(missing.exists())


if __name__ == "__main__":
    unittest.main()
