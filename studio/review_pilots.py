#!/usr/bin/env python3
"""Preflight or run the four existing PC pilot workflows on localhost only."""

import argparse
from datetime import datetime, timezone
import hashlib
from http.client import HTTPConnection, HTTPException
import json
from pathlib import Path
import subprocess
import time
import uuid

from workflow_health import check_workflow, ui_matches_prompt, widget_values

ROOT = Path(__file__).resolve().parent.parent
PILOTS = {
    "sd15": "01 - Images/PC Test 01 - SD15 512.json",
    "flux": "01 - Images/PC Test 02 - FLUX2 Klein Q8 512.json",
    "zimage": "90 - Lab and Older Workflows/PC Test 03 - ZImage BF16 512.json",
    "lc123": "04 - Utilities/PC Test 04 - LC123 Prompt and Palette.json",
}
REVIEWED_HASHES = {
    "sd15": "c593547ef6cbbd8ffe8643a6f88e23adab14694579090866b2d2684e12864fdd",
    "flux": "4254a479921aed7e1a26e2fb8e4900727b2795bbc7c701b4aecd363f479dc0f6",
    "zimage": "d86872884abfd5f9e9906d70dc8df5b191ef9a2c4ad3401ebfcc50971e4101cb",
    "lc123": "6749a4c6a21a97a5063e73a9b77e5e8b9344ea8b120c7450cb432494535990f1",
}
ALLOWED = {
    "CheckpointLoaderSimple", "CLIPTextEncode", "EmptyLatentImage", "KSampler",
    "VAEDecode", "SaveImage", "UnetLoaderGGUF", "CLIPLoader", "VAELoader",
    "EmptySD3LatentImage", "UNETLoader", "ModelSamplingAuraFlow", "LCSubject",
    "LCSceneBuilder", "LCColorPalette", "LCPromptAssembler", "PreviewAny",
}


def request(route, data=None):
    body = None if data is None else json.dumps(data).encode()
    connection = HTTPConnection("127.0.0.1", 8188, timeout=20)
    try:
        connection.request("GET" if data is None else "POST", route, body,
                           {"Content-Type": "application/json"})
        response = connection.getresponse()
        raw = response.read()
        if response.status != 200:
            raise RuntimeError(f"Local ComfyUI HTTP {response.status}: {raw.decode()[:2000]}")
        return json.loads(raw) if raw else {}
    finally:
        connection.close()


def convert(workflow, schemas):
    if workflow.get("definitions", {}).get("subgraphs"):
        raise ValueError("Pilot converter does not support subgraphs")
    nodes = {str(n["id"]): n for n in workflow["nodes"]}
    prompt = {}
    for key, node in nodes.items():
        kind = node["type"]
        if kind in ("Note", "MarkdownNote"):
            continue
        if kind not in ALLOWED or node.get("mode", 0) != 0:
            raise ValueError(f"Not an approved pilot node: {kind}")
        prompt[key] = {"class_type": kind, "inputs": widget_values(node, schemas[kind])}
    for link in workflow.get("links", []):
        _, source, slot, target, target_slot, *_ = link
        name = nodes[str(target)]["inputs"][target_slot]["name"]
        prompt[str(target)]["inputs"][name] = [str(source), slot]
    if not ui_matches_prompt(workflow, prompt, schemas):
        raise ValueError("UI/API correspondence could not be established")
    issues, _ = check_workflow(prompt, schemas)
    if issues:
        raise ValueError("; ".join(issues))
    return prompt


def resources():
    memory = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        key, value = line.split(":", 1)
        memory[key] = int(value.strip().split()[0]) * 1024
    raw = subprocess.check_output([
        "nvidia-smi", "--query-gpu=memory.used,temperature.gpu,utilization.gpu",
        "--format=csv,noheader,nounits"], text=True, timeout=10)
    used, temperature, utilization = map(int, raw.splitlines()[0].split(","))
    return {"timestamp": time.time(), "ram_available": memory["MemAvailable"],
            "swap_used": memory["SwapTotal"] - memory["SwapFree"],
            "gpu_used_mib": used, "temperature_c": temperature, "gpu_utilization": utilization}


def run(name, execute, destination, max_seconds):
    if max_seconds <= 0:
        raise ValueError("max-seconds must be positive")
    for parent in (destination, *destination.parents):
        if parent.is_symlink():
            raise ValueError(f"Symlink in pilot destination: {parent}")
    source = ROOT / "user/default/workflows" / PILOTS[name]
    original = source.read_bytes()
    if hashlib.sha256(original).hexdigest() != REVIEWED_HASHES[name]:
        raise ValueError("Pilot source changed since safety review; inspect it before updating the pinned hash")
    workflow = json.loads(original)
    schemas = request("/object_info")
    prompt = convert(workflow, schemas)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    folder = destination / f"{stamp}-{name}"
    folder.mkdir(parents=True, exist_ok=False)
    changes = []
    for node in workflow["nodes"]:
        kind = node["type"]
        key = str(node["id"])
        if kind == "KSampler":
            old = prompt[key]["inputs"]["seed"]
            seed = int(time.time_ns() % (2**48))
            prompt[key]["inputs"]["seed"] = seed
            node["widgets_values"][0] = seed
            if node.get("widgets_values_named"):
                node["widgets_values_named"]["seed"] = seed
            changes.append({"node": key, "input": "seed", "old": old, "new": seed})
        if kind == "SaveImage":
            old = prompt[key]["inputs"]["filename_prefix"]
            prefix = f"WorkflowReview/{stamp}-{name}"
            prompt[key]["inputs"]["filename_prefix"] = prefix
            node["widgets_values"][0] = prefix
            if node.get("widgets_values_named"):
                node["widgets_values_named"]["filename_prefix"] = prefix
            changes.append({"node": key, "input": "filename_prefix", "old": old, "new": prefix})
    if not ui_matches_prompt(workflow, prompt, schemas):
        raise ValueError("Adapted UI/API mismatch")
    (folder / "workflow.json").write_text(json.dumps(workflow, indent=2) + "\n")
    (folder / "prompt.json").write_text(json.dumps(prompt, indent=2) + "\n")
    record = {"source": str(source), "source_sha256": hashlib.sha256(original).hexdigest(),
              "adaptations": changes, "status": "preflight_passed", "executed": False,
              "measurement": "sampled whole-GPU use and system RAM, not allocator/process peaks"}
    receipt = folder / "result.json"
    receipt.write_text(json.dumps(record, indent=2) + "\n")
    if not execute:
        return folder
    queue = request("/queue")
    if queue["queue_running"] or queue["queue_pending"]:
        raise RuntimeError("Queue occupied; no work submitted")
    first = resources()
    if first["ram_available"] < 10 * 1024**3 or first["temperature_c"] >= 80 or first["gpu_utilization"] > 20:
        raise RuntimeError("Insufficient quiet resource headroom; no work submitted")
    record["resources_before"] = first
    started = time.monotonic()
    record.update(prompt_id=str(uuid.uuid4()), status="submission_pending")
    receipt.write_text(json.dumps(record, indent=2) + "\n")
    try:
        request("/prompt", {"prompt": prompt, "prompt_id": record["prompt_id"],
                            "client_id": "workflow-review-pilots",
                            "extra_data": {"extra_pnginfo": {"workflow": workflow}}})
    except KeyboardInterrupt:
        record["status"] = "submission_interrupted_acceptance_uncertain"
        cancel(record)
        receipt.write_text(json.dumps(record, indent=2) + "\n")
        raise
    except (OSError, HTTPException, ValueError, RuntimeError) as exc:
        record.update(status="submission_error_acceptance_uncertain", error=str(exc))
        cancel(record)
        receipt.write_text(json.dumps(record, indent=2) + "\n")
        raise
    record.update(status="queued", executed=True)
    receipt.write_text(json.dumps(record, indent=2) + "\n")
    try:
        with (folder / "resources.jsonl").open("w") as samples:
            while True:
                sample = resources()
                samples.write(json.dumps(sample) + "\n")
                samples.flush()
                history = request("/history/" + record["prompt_id"])
                if record["prompt_id"] in history:
                    item = history[record["prompt_id"]]
                    (folder / "history.json").write_text(json.dumps(item, indent=2) + "\n")
                    status = item.get("status", {})
                    record["status"] = "backend_success" if status.get("completed") and status.get("status_str") == "success" else "execution_failed"
                    record["outputs"] = item.get("outputs", {})
                    break
                if time.monotonic() - started > max_seconds or sample["temperature_c"] >= 88 or sample["ram_available"] < 4 * 1024**3:
                    record["status"] = "resource_limit_cancellation_requested"
                    cancel(record)
                    break
                time.sleep(2)
    except KeyboardInterrupt:
        record["status"] = "operator_interrupted"
        cancel(record)
        raise
    except (OSError, HTTPException, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        record["status"] = "monitor_error"
        record["error"] = str(exc)
        cancel(record)
    finally:
        record["elapsed_seconds"] = round(time.monotonic() - started, 2)
        record["visual_acceptance"] = "not_yet_reviewed"
        receipt.write_text(json.dumps(record, indent=2) + "\n")
    return folder


def cancel(record):
    """Use this checkout's targeted endpoints; never submit a global interrupt."""
    try:
        request("/api/jobs/" + record["prompt_id"] + "/cancel", {})
        record["cancellation"] = "targeted cancellation requested; cooperative, completion not confirmed"
    except (OSError, HTTPException, ValueError, RuntimeError) as exc:
        record["cancellation"] = "failed: " + str(exc)
    record["warning"] = "Inspect this prompt and queue before more work; cancellation is not an instantaneous hard memory/time bound."


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pilot", choices=PILOTS)
    parser.add_argument("--run", action="store_true", help="Actually submit the pilot; default is preflight only")
    parser.add_argument("--max-seconds", type=int, default=600)
    parser.add_argument("--destination", type=Path, default=ROOT / ".codex/artifacts/workflow-review-pilots")
    args = parser.parse_args()
    print(run(args.pilot, args.run, args.destination, args.max_seconds), flush=True)


if __name__ == "__main__":
    main()
