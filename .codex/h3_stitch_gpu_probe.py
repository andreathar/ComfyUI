import argparse
import json
from pathlib import Path
import time

from test_h3_stitch_memory import h3, torch

parser = argparse.ArgumentParser()
parser.add_argument("--batch", type=int)
parser.add_argument("--output", required=True)
args = parser.parse_args()
base = torch.full((40, 1080, 1920, 3), 0.25)
crops = torch.full((40, 512, 512, 3), 0.75)
transform = {"boxes": [[640, 284, 512, 512]] * 40, "canvas": [512, 512],
             "src_size": [1920, 1080], "weights": [1.0] * 40}
kwargs = {} if args.batch is None else {"stitch_batch_size": args.batch}
torch.cuda.reset_peak_memory_stats()
started = time.monotonic()
record = {"frames": 40, "source_size": [1920, 1080], "crop_size": [512, 512],
          "stitch_batch_size": args.batch, "passed": False}
try:
    result = h3.H3FaceStitch().run(base, crops, transform, "face_only", 24, 24, 1, 1, **kwargs)[0]
    torch.cuda.synchronize()
    assert result.shape == base.shape
    assert torch.isfinite(result).all()
    torch.testing.assert_close(result[:, :100], base[:, :100], rtol=0, atol=0)
    record["passed"] = True
except torch.OutOfMemoryError as error:
    record["error"] = str(error)
finally:
    record["seconds"] = round(time.monotonic() - started, 3)
    record["peak_allocated_mib"] = round(torch.cuda.max_memory_allocated() / 2**20, 2)
    Path(args.output).write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2))
raise SystemExit(0 if record["passed"] else 1)
