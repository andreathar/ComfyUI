#!/usr/bin/env python3
"""Render shot specs on the local ComfyUI server into categorized, tagged reference stills."""

import argparse
import json
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.request
import uuid


STUDIO = Path(__file__).resolve().parent
PROJECT = STUDIO.parent
CATALOGUE = PROJECT / ".codex/models.json"
SLUG = re.compile(r"[a-z0-9][a-z0-9.-]*")
VARIABLE = re.compile(r"\{\{(\w+)\}\}")


def expand(sheet):
    shared = {key: value for key, value in sheet.items() if key != "shots"}
    return [{**shared, **item} for item in sheet.get("shots", [{}])]


def resolve(spec, presets, input_dir):
    job = {**presets["defaults"], **spec}
    for key in ("project", "scene", "shot", "model", "aspect"):
        if not SLUG.fullmatch(str(job.get(key, ""))):
            raise ValueError(f"'{key}' must be lowercase letters, digits, '.' or '-': {job.get(key)!r}")
    if not job.get("subject"):
        raise ValueError(f"{job['scene']}-{job['shot']}: 'subject' is required")
    model = presets["models"][job["model"]]
    job = {**model, **job}
    job["width"], job["height"] = presets["aspects"][job["aspect"]][model["family"]]
    look = presets["looks"].get(job["look"], job["look"])
    prompt = presets["prompt_pattern"].format(**{**job, "look": look})
    job["prompt"] = ", ".join(part for part in prompt.split(", ") if part.strip())
    reference = job.get("reference")
    if reference:
        path = (input_dir / reference).resolve()
        if not path.is_relative_to(input_dir.resolve()) or not path.is_file():
            raise ValueError(f"Reference must be an existing file under {input_dir}: {reference}")
    job["template"] = f"{model['family']}-{'i2i' if reference else 't2i'}"
    return job


def output_prefix(job, presets, seed):
    return presets["output_pattern"].format(**{**job, "seed": seed})


def load_template(name):
    return json.loads((STUDIO / "templates" / f"{name}.json").read_text())


def fill(node, values):
    if isinstance(node, dict):
        return {key: fill(value, values) for key, value in node.items()}
    if isinstance(node, list):
        return [fill(value, values) for value in node]
    if isinstance(node, str) and (match := VARIABLE.fullmatch(node)):
        if match[1] not in values:
            raise ValueError(f"Template variable has no value: {match[1]}")
        return values[match[1]]
    return node


def post(server, path, data=None):
    body = None if data is None else json.dumps(data).encode()
    request = urllib.request.Request(server + path, body, {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        raise ValueError(f"ComfyUI rejected the workflow: {error.read().decode()[:2000]}") from error


def render(job, presets, seed, server, output_dir):
    graph = fill(load_template(job["template"]), {**job, "seed": seed, "output": output_prefix(job, presets, seed)})
    started = time.time()
    # A client_id keeps ComfyUI from treating this as a headless deploy-to-cloud install.
    prompt_id = post(server, "/prompt", {"prompt": graph, "client_id": str(uuid.uuid4())})["prompt_id"]
    while (entry := post(server, f"/history/{prompt_id}").get(prompt_id)) is None:
        time.sleep(1)
    if entry["status"]["status_str"] != "success":
        raise ValueError(f"Render failed: {json.dumps(entry['status'].get('messages', []))[:2000]}")
    seconds = round(time.time() - started, 2)
    catalogue = json.loads(CATALOGUE.read_text())
    model_files = {key: {k: catalogue["models"][key][k] for k in ("filename", "sha256", "license")}
                   for key in catalogue["profiles"].get(job.get("catalogue_profile"), [])}
    images = [output_dir / image["subfolder"] / image["filename"]
              for node in entry["outputs"].values() for image in node.get("images", []) if image["type"] == "output"]
    for image in images:
        record = {
            "image": image.relative_to(output_dir).as_posix(),
            **{key: job[key] for key in ("project", "scene", "shot", "model", "aspect", "look", "template", "prompt", "width", "height", "steps", "cfg", "sampler", "scheduler")},
            "seed": seed, "tags": job["tags"], "reference": job.get("reference"),
            "denoise": job["denoise"] if job.get("reference") else 1,
            "model_files": model_files, "prompt_id": prompt_id, "seconds": seconds,
            "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }
        image.with_suffix(".json").write_text(json.dumps(record, indent=2) + "\n")
        with (output_dir / "refs" / job["project"] / "index.jsonl").open("a") as index:
            index.write(json.dumps(record) + "\n")
    return images


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("specs", nargs="+", type=Path, help="Shot or sheet JSON files")
    parser.add_argument("--only", help="Render only this shot id")
    parser.add_argument("--dry-run", action="store_true", help="Print prompts and output names without rendering")
    parser.add_argument("--server", default="http://127.0.0.1:8188")
    args = parser.parse_args(argv)
    presets = json.loads((STUDIO / "presets.json").read_text())
    jobs = [resolve(spec, presets, PROJECT / "input")
            for path in args.specs for spec in expand(json.loads(path.read_text()))
            if args.only in (None, spec.get("shot"))]
    for job in jobs:
        for seed in job["seeds"]:
            print(f"{job['scene']}-{job['shot']} seed {seed} [{job['template']} {job['width']}x{job['height']}]")
            print(f"  prompt: {job['prompt']}")
            if args.dry_run:
                print(f"  output: output/{output_prefix(job, presets, seed)}_00001_.png")
                continue
            for image in render(job, presets, seed, args.server, PROJECT / "output"):
                print(f"  saved: {image}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError) as error:
        print(f"Shot error: {error}", file=sys.stderr)
        raise SystemExit(1)
