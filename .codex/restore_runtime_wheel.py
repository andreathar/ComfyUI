"""Restore the pinned Spark runtime wheel; run explicitly before recreating the venv."""

import hashlib
import io
from pathlib import Path
import urllib.request
import zipfile


URL = "https://github.com/zechengtang/Spark-H3/releases/download/comfyui-v0.2.0/ComfyUI-Spark-H3-0.2.0-linux-x86_64-sm86-cu130.zip"
ARCHIVE_SHA256 = "8997f751296d1ff6c032125f2ce2fbc45a776bec5ac8cf40d5c30f3a6ac14a02"
WHEEL = "spark_h3_kitchen-0.2.37+spark.h3.sm86.cu130.1-cp312-abi3-linux_x86_64.whl"
WHEEL_SHA256 = "c79c4b84702800bc0381e2f88a94a3ed883e7a8039dc2161cf911979a0d60732"


def restore(directory):
    destination = Path(directory) / WHEEL
    if destination.exists():
        if hashlib.sha256(destination.read_bytes()).hexdigest() != WHEEL_SHA256:
            raise ValueError(f"Existing wheel hash mismatch: {destination}")
        return destination
    with urllib.request.urlopen(URL, timeout=60) as response:
        archive = response.read()
    if hashlib.sha256(archive).hexdigest() != ARCHIVE_SHA256:
        raise ValueError("Spark release archive hash mismatch")
    with zipfile.ZipFile(io.BytesIO(archive)) as release:
        wheel = release.read(f"ComfyUI-Spark-H3/wheelhouse/{WHEEL}")
    if hashlib.sha256(wheel).hexdigest() != WHEEL_SHA256:
        raise ValueError("Spark runtime wheel hash mismatch")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb") as output:
        output.write(wheel)
    return destination


if __name__ == "__main__":
    print(restore(Path(__file__).resolve().parent / "wheels"))
