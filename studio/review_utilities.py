#!/usr/bin/env python3
"""Six source-reviewed, model-free capability tests derived from extension examples."""

import argparse
from datetime import datetime, timezone
import hashlib
from http.client import HTTPException
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import uuid

from PIL import Image

from qualify_workflows import write_text
from review_pilots import ROOT, cancel, request, resources

PROVIDERS = {
    "AILab_ImagePreview": "custom_nodes.comfyui-rmbg", "AILab_MaskPreview": "custom_nodes.comfyui-rmbg",
    "AILab_ImageStitch": "custom_nodes.comfyui-rmbg", "iToolsPromptRecord": "custom_nodes.comfyui-itools",
    "iToolsAddOverlay": "custom_nodes.comfyui-itools", "VHS_VideoCombine": "custom_nodes.comfyui-videohelpersuite",
    "LCImageDesaturate": "custom_nodes.ComfyUI_LC123_nodes", "LoadImage": "nodes",
    "PreviewImage": "nodes", "ImageBatch": "nodes",
}
FIXTURES = (
    "output/WorkflowReview/20261109T175014244334Z-sd15_00001_.png",
    "output/WorkflowReview/20261109T175023220153Z-flux_00001_.png",
)
SOURCES = {
    "custom_nodes/comfyui-rmbg/py/AILab_ImageMaskTools.py": "500ec140c405c68a6fe83408d7dfe1da28d30602b373376490d506323dd9d6ce",
    "custom_nodes/comfyui-itools/nodes/prompt_record.py": "7852c4e151ff4ef26d2da3e7670bc5e84c9f2b57f00a38ec0abe964ee13f995b",
    "custom_nodes/comfyui-itools/nodes/add_overlay.py": "bc6653d26f1489afbd1ea4bac0d256826788fc0342bf341d9dd704634bfa2d18",
    "custom_nodes/comfyui-itools/backend/overlay.py": "0e09d31a8c0c5b7c4cdba0b6d3b394628a51461edb0b902d0e7c799df960f4ce",
    "custom_nodes/comfyui-itools/backend/shared.py": "9367f2ceb50d35b367d89adb601c32d4a8d72e6549e4203a0949dd722acd8173",
    "custom_nodes/comfyui-videohelpersuite/videohelpersuite/nodes.py": "6d975d8fd8906784a4d9233ccc1238150ed33c6311d06c53fd08b5ee96e30442",
    "custom_nodes/ComfyUI_LC123_nodes/lc_image_tools.py": "5cb45955281b646b3458e454977dbd343a8be46d2e76a9f65c99ef75642da090",
}
EXAMPLES = {
    "prompt-record": "custom_nodes/comfyui-itools/example_workflows/PromptRecord.json",
    "previews": "custom_nodes/comfyui-rmbg/example_workflows/image_mask_preview.json",
    "stitch": "custom_nodes/comfyui-rmbg/example_workflows/V2.7.0_ImageStitch.json",
    "overlay": "custom_nodes/comfyui-itools/example_workflows/KSamplerOverlay.json",
    "gif": "custom_nodes/comfyui-videohelpersuite/tests/converted-format-input.json",
    "desaturate": "custom_nodes/ComfyUI_LC123_nodes/workflows/LC123 Examples - Image Tools & Post Processing.json",
}


def node(kind, **inputs):
    return {"class_type": kind, "inputs": inputs}


def prompts(a, b):
    load_a = node("LoadImage", image=a)
    load_b = node("LoadImage", image=b)
    return {
        "prompt-record": {"1": node("iToolsPromptRecord", text="WorkflowReview local utility smoke test", timeline_data="")},
        "previews": {"1": load_a, "2": node("AILab_ImagePreview", image=["1", 0]),
                     "3": node("AILab_MaskPreview", mask=["1", 1])},
        "stitch": {"1": load_a, "2": load_b, "3": node("AILab_ImageStitch", image1=["1", 0], image2=["2", 0],
                    stitch_mode="right", match_image_size=True, megapixels=0, max_width=1024, max_height=512,
                    upscale_method="bilinear", spacing_width=0, background_color="#FFFFFF"),
                   "4": node("PreviewImage", images=["3", 0])},
        "overlay": {"1": load_a, "2": node("iToolsAddOverlay", image=["1", 0], text="LOCAL REVIEW",
                      background_color="#000000AA", font_size=20, overlay_mode=True),
                    "3": node("PreviewImage", images=["2", 0])},
        "gif": {"1": load_a, "2": load_b, "3": node("ImageBatch", image1=["1", 0], image2=["2", 0]),
                "4": node("VHS_VideoCombine", images=["3", 0], frame_rate=2, loop_count=1,
                          filename_prefix="WorkflowReview/local-utilities/vhs", format="image/gif", pingpong=False, save_output=False)},
        "desaturate": {"1": load_a, "2": node("LCImageDesaturate", image=["1", 0], factor=1,
                          method="luminance (Rec.709)"), "3": node("PreviewImage", images=["2", 0])},
    }


def collect_outputs(outputs, folder):
    evidence = []
    for node_id, output in outputs.items():
        for key in ("images", "gifs"):
            for item in output.get(key, []):
                if not isinstance(item, dict) or not item.get("filename"):
                    continue
                kind = item.get("type")
                if kind not in ("temp", "output"):
                    raise ValueError("Unexpected output storage type")
                base = (ROOT / kind).resolve()
                path = (base / item.get("subfolder", "") / item["filename"]).resolve()
                if not path.is_relative_to(base):
                    raise ValueError("Output path escaped storage directory")
                name = str(len(evidence)) + "-" + path.name
                target = folder / name
                with path.open("rb") as source, target.open("xb") as destination:
                    shutil.copyfileobj(source, destination)
                with Image.open(target) as image:
                    image.load()
                    details = {"size": list(image.size), "format": image.format,
                               "frames": getattr(image, "n_frames", 1), "mode": image.mode}
                    # Decode every frame, not just the first frame's header/pixels.
                    for index in range(details["frames"]):
                        image.seek(index)
                        image.load()
                    image.seek(0)
                    if image.mode == "RGB":
                        r, g, b = image.split()
                        details["equal_rgb_channels"] = r.tobytes() == g.tobytes() == b.tobytes()
                evidence.append({"node_id": str(node_id),
                                 "source": str(path), "copy": str(target), **details})
    return evidence


def execute(name, prompt, folder, server_identity=None):
    record = {"name": name, "source_example": str(ROOT / EXAMPLES[name]), "variant": "constructed_reduced_capability_test",
              "scope": "No certification of complete source graph or frontend behavior", "status": "preflight_passed",
              "prompt_id": str(uuid.uuid4()), "reviewed_source_hashes": SOURCES,
              "runtime_consistency": server_identity,
              "provenance_limit": "Disk-source hashes and schema providers are checked; live bytecode is not attested"}
    receipt = folder / "result.json"
    write_text(folder / "prompt.json", json.dumps(prompt, indent=2) + "\n")
    queue = request("/queue")
    if queue["queue_running"] or queue["queue_pending"]:
        raise RuntimeError("Queue occupied; no utility test submitted")
    record["before"] = resources()
    if record["before"]["ram_available"] < 2 * 1024**3 or record["before"]["temperature_c"] >= 80:
        raise RuntimeError("Insufficient utility test resource headroom")
    record["status"] = "submission_pending"
    write_text(receipt, json.dumps(record, indent=2) + "\n")
    started = time.monotonic()
    try:
        request("/prompt", {"prompt": prompt, "prompt_id": record["prompt_id"], "client_id": "workflow-review-utilities"})
        while True:
            history = request("/history/" + record["prompt_id"])
            if record["prompt_id"] in history:
                item = history[record["prompt_id"]]
                write_text(folder / "history.json", json.dumps(item, indent=2) + "\n")
                record["status"] = "backend_success" if item.get("status", {}).get("status_str") == "success" and item["status"].get("completed") else "execution_failed"
                record["outputs"] = item.get("outputs", {})
                record["evidence"] = collect_outputs(record["outputs"], folder)
                if record["status"] == "backend_success":
                    if name == "prompt-record":
                        record["contract_passed"] = record["outputs"].get("1", {}).get("text") == ["WorkflowReview local utility smoke test"]
                    elif name == "stitch":
                        record["contract_passed"] = any(e["size"] == [1024, 512] for e in record["evidence"])
                    elif name == "gif":
                        record["contract_passed"] = any(e["format"] == "GIF" and e["frames"] == 2 for e in record["evidence"])
                    elif name == "desaturate":
                        record["contract_passed"] = any(e.get("equal_rgb_channels") for e in record["evidence"])
                    elif name == "previews":
                        record["contract_passed"] = {"2", "3"} <= {e["node_id"] for e in record["evidence"]}
                    else:
                        record["contract_passed"] = bool(record["evidence"])
                break
            sample = resources()
            if time.monotonic() - started > 30 or sample["ram_available"] < 1024**3 or sample["temperature_c"] >= 88:
                record["status"] = "limit_cancellation_requested"
                cancel(record)
                break
            time.sleep(0.3)
    except KeyboardInterrupt:
        record["status"] = "operator_interrupted"
        cancel(record)
        raise
    except (OSError, HTTPException, ValueError, KeyError, RuntimeError, subprocess.SubprocessError) as exc:
        # Persist monitoring/output-validation failures as evidence, not silent success.
        record.update(status="monitor_or_validation_error", error=str(exc))
        cancel(record)
    finally:
        record["elapsed_seconds"] = round(time.monotonic() - started, 2)
        write_text(receipt, json.dumps(record, indent=2) + "\n")
    return record


def verify_server_sources(pid):
    proc = Path("/proc") / str(pid)
    if (proc / "cwd").resolve() != ROOT.resolve():
        raise ValueError("Server process is not running from this checkout")
    command = (proc / "cmdline").read_bytes().split(b"\0")
    if b"main.py" not in command or b"8188" not in command:
        raise ValueError("Expected explicit local ComfyUI main.py --port 8188 process")
    boot = next(int(line.split()[1]) for line in Path("/proc/stat").read_text().splitlines() if line.startswith("btime "))
    ticks = int((proc / "stat").read_text().rsplit(")", 1)[1].split()[19])
    started = boot + ticks / os.sysconf("SC_CLK_TCK")
    for source in SOURCES:
        if (ROOT / source).stat().st_mtime > started:
            raise ValueError("Reviewed source modified after server start; loaded code is uncertain: " + source)
    # Consistency evidence, not cryptographic attestation of live Python bytecode.
    return {"pid": pid, "started_epoch": started, "cwd": str(ROOT)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", help="Submit six bounded tests; otherwise print preflight only")
    parser.add_argument("--server-pid", type=int, help="Explicit live local ComfyUI PID; required for execution")
    args = parser.parse_args()
    identity = None
    if args.run:
        if not args.server_pid:
            parser.error("--run requires --server-pid from the live local instance")
        identity = verify_server_sources(args.server_pid)
    for path, expected in SOURCES.items():
        if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != expected:
            raise ValueError(f"Reviewed extension source changed: {path}")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    relative = Path("WorkflowReview") / ("utilities-" + stamp)
    fixture_dir = ROOT / "input" / relative
    for parent in (fixture_dir, *fixture_dir.parents):
        if parent.is_symlink():
            raise ValueError(f"Symlink in fixture destination: {parent}")
    graphs = prompts(str(relative / "a.png"), str(relative / "b.png"))
    schemas = request("/object_info")
    for graph in graphs.values():
        for entry in graph.values():
            kind = entry["class_type"]
            if schemas.get(kind, {}).get("python_module") != PROVIDERS[kind]:
                raise ValueError("Unavailable or unexpected node provider: " + kind)
    if not args.run:
        print("Source hashes and node availability checked; no execution or fixture copies")
        return
    fixture_dir.mkdir(parents=True, exist_ok=False)
    for path, name in zip(FIXTURES, ("a.png", "b.png")):
        with Image.open(ROOT / path) as image:
            if image.size != (512, 512) or image.mode != "RGB":
                raise ValueError("Fixture must be one 512x512 RGB image")
        with (ROOT / path).open("rb") as source, (fixture_dir / name).open("xb") as destination:
            shutil.copyfileobj(source, destination)
    base = ROOT / ".codex/artifacts/workflow-review-utilities" / stamp
    for name, prompt in graphs.items():
        folder = base / name
        # write_text uses no-follow directory traversal and atomic replacement.
        record = execute(name, prompt, folder, identity)
        print(name, record["status"], record.get("contract_passed"), record["elapsed_seconds"], folder, flush=True)
        if record["status"] != "backend_success" or not record.get("contract_passed"):
            raise SystemExit("Stopping batch after unsuccessful utility test")


if __name__ == "__main__":
    main()
