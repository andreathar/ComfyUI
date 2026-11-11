import sys
from pathlib import Path

import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "custom_nodes" / "comfyui-videohelpersuite"))
from videohelpersuite import batched_nodes


class FakeVAE:
    def __init__(self):
        self.encoded_batches = []
        self.decoded_batches = []
        self.cropped_batches = []

    def vae_encode_crop_pixels(self, pixels):
        self.cropped_batches.append(pixels.shape[0])
        return pixels

    def encode(self, pixels):
        assert pixels.shape[-1] == 3
        self.encoded_batches.append(pixels.shape[0])
        return pixels[:, :1, :1, :1]

    def decode(self, samples):
        self.decoded_batches.append(samples.shape[0])
        return samples.new_zeros((samples.shape[0], 4, 4, 3))


@pytest.mark.parametrize(
    ("node_type", "input_value", "method_name", "expected_shape"),
    [
        (
            batched_nodes.VAEEncodeBatched,
            torch.zeros((5, 4, 4, 4)),
            "encode",
            (5, 1, 1, 1),
        ),
        (
            batched_nodes.VAEDecodeBatched,
            {"samples": torch.zeros((5, 1, 1, 1))},
            "decode",
            (5, 4, 4, 3),
        ),
    ],
)
def test_batched_vae_nodes_handle_partial_final_batch(
    monkeypatch, node_type, input_value, method_name, expected_shape
):
    progress_updates = []

    class FakeProgressBar:
        def __init__(self, total):
            self.total = total

        def update(self, value):
            progress_updates.append(value)

    monkeypatch.setattr(batched_nodes, "ProgressBar", FakeProgressBar)
    vae = FakeVAE()
    node = node_type()

    if method_name == "encode":
        result = node.encode(vae, input_value, per_batch=2)[0]["samples"]
        assert vae.cropped_batches == [2, 2, 1]
        assert vae.encoded_batches == [2, 2, 1]
    else:
        result = node.decode(vae, input_value, per_batch=2)[0]
        assert vae.decoded_batches == [2, 2, 1]

    assert result.shape == expected_shape
    assert progress_updates == [2, 2, 1]


def test_batched_encode_propagates_vae_crop_errors():
    class BrokenVAE(FakeVAE):
        def vae_encode_crop_pixels(self, pixels):
            raise RuntimeError("crop failed")

    with pytest.raises(RuntimeError, match="crop failed"):
        batched_nodes.VAEEncodeBatched().encode(
            BrokenVAE(), torch.zeros((1, 4, 4, 3)), per_batch=1
        )
