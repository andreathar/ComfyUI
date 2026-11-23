import hashlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import restore_runtime_wheel as wheel


class RestoreTests(unittest.TestCase):
    def test_existing_verified_wheel_never_downloads(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / wheel.WHEEL
            target.write_bytes(b"wheel")
            with patch.object(wheel, "WHEEL_SHA256", hashlib.sha256(b"wheel").hexdigest()), patch.object(wheel.urllib.request, "urlopen") as download:
                self.assertEqual(wheel.restore(directory), target)
                download.assert_not_called()

    def test_bad_archive_does_not_publish(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(wheel.urllib.request, "urlopen", return_value=io.BytesIO(b"bad")):
            with self.assertRaisesRegex(ValueError, "archive hash"):
                wheel.restore(directory)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_verified_member_is_published(self):
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w") as release:
            release.writestr(f"ComfyUI-Spark-H3/wheelhouse/{wheel.WHEEL}", b"wheel")
        data = archive.getvalue()
        with tempfile.TemporaryDirectory() as directory, patch.object(wheel.urllib.request, "urlopen", return_value=io.BytesIO(data)), patch.object(wheel, "ARCHIVE_SHA256", hashlib.sha256(data).hexdigest()), patch.object(wheel, "WHEEL_SHA256", hashlib.sha256(b"wheel").hexdigest()):
            self.assertEqual(wheel.restore(directory).read_bytes(), b"wheel")
