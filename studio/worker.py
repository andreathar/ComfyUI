#!/usr/bin/env python3
"""Run openreel ComfyUI job files from a project folder on the local ComfyUI server."""

import argparse
import json
import os
from pathlib import Path
import shutil
import sys
import time
import urllib.error
import urllib.request
import uuid

from PIL import Image

if __package__:
    from . import shot
else:
    import shot

TARGETS = {
    "comfy-zimage": ("keyframe variations entity", "z-image-turbo", "z-image-t2i"),
    "comfy-sd15": ("keyframe variations entity", "sd15", "sd15-t2i"),
    "comfy-refine": ("refine", "z-image-turbo", "z-image-refine"),
    "comfy-klein": ("keyframe variations entity", "flux2-klein-4b", "flux2-t2i"),
}
MODEL_DIRS = {"unet": "unet", "gguf": "diffusion_models", "clip": "clip", "vae": "vae", "checkpoint": "checkpoints"}
MAX_REFS = 3
REFERENCE_TARGETS = {"comfy-klein"}
POLL_SECONDS = 3
RENDER_TIMEOUT = 1800


class JobError(Exception):
    pass


def jobs_dir(project):
    return Path(project) / "jobs" / "comfy"


def inside(path, root):
    return path.resolve().is_relative_to(Path(root).resolve())


def validate_job(job, project, models_root, job_id=None):
    project = Path(project)
    if job_id is not None and job.get("id") != job_id:
        raise JobError(f"job id {job.get('id')!r} does not match file name {job_id!r}")
    if job.get("version") != 1:
        raise JobError(f"unsupported job version: {job.get('version')!r}")
    target = job.get("target")
    if target not in TARGETS:
        raise JobError(f"unknown target: {target!r}")
    kinds, model_key, _ = TARGETS[target]
    if job.get("kind") not in kinds.split():
        raise JobError(f"kind {job.get('kind')!r} does not match target {target}")
    outputs, seeds = job.get("outputs") or [], job.get("seeds") or []
    if not outputs or len(seeds) != len(outputs):
        raise JobError("seeds and outputs must be non-empty and the same length")
    presets = json.loads((shot.STUDIO / "presets.json").read_text())
    if job.get("aspect") not in presets["aspects"]:
        raise JobError(f"unknown aspect: {job.get('aspect')!r}")
    if not job.get("prompt"):
        raise JobError("prompt is required")
    if job["kind"] == "refine":
        denoise = job.get("denoise")
        if not isinstance(denoise, (int, float)) or not 0 <= denoise <= 1:
            raise JobError("refine needs denoise between 0 and 1")
        if not job.get("source"):
            raise JobError("refine needs a source")
    for name in [*(job.get("refs") or []), *([job["source"]] if job.get("source") else []), *outputs]:
        if Path(name).is_absolute() or not inside(project / name, project):
            raise JobError(f"path outside the project: {name}")
    if job.get("source") and not (project / job["source"]).is_file():
        raise JobError(f"source not found: {job['source']}")
    if target in REFERENCE_TARGETS:
        refs = job.get("refs") or []
        if len(refs) > MAX_REFS:
            raise JobError(f"at most {MAX_REFS} refs for {target}")
        for name in refs:
            if not (project / name).is_file():
                raise JobError(f"ref not found: {name}")
    for name in outputs:
        if (project / name).exists():
            raise JobError("output exists")
    model = presets["models"][model_key]
    for key, folder in MODEL_DIRS.items():
        if key in model and not (Path(models_root) / folder / model[key]).is_file():
            raise JobError(f"missing models/{folder}/{model[key]}")


def refine_size(width, height):
    scale = min(1.5, 2048 / max(width, height))
    return tuple(max(16, round(side * scale / 16) * 16) for side in (width, height))


def add_references(graph, names, megapixels):
    """Chain each staged reference image into the positive and negative conditioning."""
    guider = graph["60"]["inputs"]
    for i, name in enumerate(names):
        base = 10 + i * 10
        while any(str(base + offset) in graph for offset in range(5)):
            base += 10
        graph[str(base)] = {"class_type": "LoadImage", "inputs": {"image": name}}
        graph[str(base + 1)] = {"class_type": "ImageScaleToTotalPixels", "inputs": {
            "image": [str(base), 0], "upscale_method": "lanczos", "megapixels": megapixels, "resolution_steps": 1}}
        graph[str(base + 2)] = {"class_type": "VAEEncode", "inputs": {"pixels": [str(base + 1), 0], "vae": ["3", 0]}}
        for offset, side in ((3, "positive"), (4, "negative")):
            graph[str(base + offset)] = {"class_type": "ReferenceLatent", "inputs": {
                "conditioning": guider[side], "latent": [str(base + 2), 0]}}
            guider[side] = [str(base + offset), 0]


def build_graph(job, seed, n, source_name, size, presets, ref_names=()):
    _, model_key, template = TARGETS[job["target"]]
    model = presets["models"][model_key]
    values = {**model, "prompt": job["prompt"], "seed": seed,
              "output": f"openreel/{job['project_code']}/{job['id']}/{n}"}
    if job["kind"] == "refine":
        values.update(reference=source_name, denoise=job["denoise"], width=size[0], height=size[1])
    else:
        values["width"], values["height"] = presets["aspects"][job["aspect"]][model["family"]]
    graph = shot.fill(shot.load_template(template), values)
    if ref_names:
        add_references(graph, ref_names, model["ref_megapixels"])
    return graph


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def status_path(project, job_id):
    return jobs_dir(project) / f"{job_id}.status.json"


def write_status(project, status):
    path = status_path(project, status["id"])
    temp = path.with_name(f".{path.name}.tmp")
    temp.write_text(json.dumps({**status, "updatedAt": now()}, indent=2) + "\n")
    os.replace(temp, path)


def read_status(project, job_id):
    try:
        return json.loads(status_path(project, job_id).read_text())
    except FileNotFoundError:
        return None


def pending_jobs(project):
    folder = jobs_dir(project)
    if not folder.is_dir():
        return []
    files = [p for p in folder.glob("*.json")
             if not p.name.endswith(".status.json") and not p.name.startswith(".")
             and not status_path(project, p.stem).exists()]
    return sorted(files, key=lambda p: (p.stat().st_mtime, p.name))


def recover_interrupted(project):
    for path in jobs_dir(project).glob("*.status.json"):
        status = json.loads(path.read_text())
        if status.get("state") == "running":
            write_status(project, {**status, "state": "failed", "error": "interrupted"})


def comfy(server, path, data=None):
    body = None if data is None else json.dumps(data).encode()
    request = urllib.request.Request(server + path, body, {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        raise JobError(f"ComfyUI rejected the workflow: {error.read().decode()[:2000]}") from error
    except OSError as error:
        host = server.split("//", 1)[-1]
        raise JobError(f"ComfyUI unreachable at {host}") from error


def render_one(server, graph, comfy_root):
    prompt_id = comfy(server, "/prompt", {"prompt": graph, "client_id": str(uuid.uuid4())})["prompt_id"]
    deadline = time.time() + RENDER_TIMEOUT
    while (entry := comfy(server, f"/history/{prompt_id}").get(prompt_id)) is None:
        if time.time() > deadline:
            raise JobError("render timed out")
        time.sleep(1)
    if entry["status"]["status_str"] != "success":
        raise JobError(f"render failed: {json.dumps(entry['status'].get('messages', []))[:2000]}")
    images = [Path(comfy_root) / "output" / i["subfolder"] / i["filename"]
              for node in entry["outputs"].values() for i in node.get("images", []) if i["type"] == "output"]
    if not images:
        raise JobError("ComfyUI returned no image")
    return prompt_id, images[0]


def model_files(model):
    catalogue = json.loads(shot.CATALOGUE.read_text())
    return {key: {k: catalogue["models"][key][k] for k in ("filename", "sha256", "license")}
            for key in catalogue["profiles"].get(model.get("catalogue_profile"), [])}


def run_job(job_path, project, server, comfy_root=shot.PROJECT, models_root=None):
    project, comfy_root = Path(project), Path(comfy_root)
    models_root = Path(models_root or comfy_root / "models")
    started = time.time()
    job = json.loads(Path(job_path).read_text())
    status = {"id": Path(job_path).stem, "state": "running", "outputs": [],
              "error": None, "seconds": None, "records": []}
    staged = comfy_root / "input" / "openreel" / status["id"]
    try:
        validate_job(job, project, models_root, status["id"])
        write_status(project, status)
        print(f"{status['id']}: running")
        presets = json.loads((shot.STUDIO / "presets.json").read_text())
        job["project_code"] = project.name
        _, model_key, _ = TARGETS[job["target"]]
        model = presets["models"][model_key]
        source_name = size = None
        if job["kind"] == "refine":
            staged.mkdir(parents=True, exist_ok=True)
            source_name = Path(job["source"]).name
            shutil.copyfile(project / job["source"], staged / source_name)
            with Image.open(staged / source_name) as image:
                size = refine_size(*image.size)
            source_name = f"openreel/{status['id']}/{source_name}"
        ref_names = []
        if job["target"] in REFERENCE_TARGETS:
            staged.mkdir(parents=True, exist_ok=True)
            for i, ref in enumerate(job.get("refs") or []):
                staged_ref = f"ref{i}_{Path(ref).name}"
                shutil.copyfile(project / ref, staged / staged_ref)
                ref_names.append(f"openreel/{status['id']}/{staged_ref}")
        for n, (seed, output) in enumerate(zip(job["seeds"], job["outputs"])):
            target = project / output
            if target.exists():
                raise JobError("output exists")
            graph = build_graph(job, seed, n, source_name, size, presets, ref_names)
            prompt_id, image = render_one(server, graph, comfy_root)
            with Image.open(image) as picture:
                width, height = picture.size
            part = target.with_name(f".cf-{status['id']}-{n}.part")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(image, part)
            os.replace(part, target)
            image.with_suffix(".json").write_text(json.dumps({
                "job": status["id"], "target": job["target"], "model": model_key, "seed": seed,
                "width": width, "height": height, "prompt": job["prompt"], "promptId": prompt_id,
                "output": output, "model_files": model_files(model), "created": now()}, indent=2) + "\n")
            status["outputs"].append(output)
            status["records"].append({"path": output, "seed": seed, "model": model_key,
                                      "width": width, "height": height, "promptId": prompt_id})
            write_status(project, status)
        status["state"] = "done"
    except JobError as error:
        status.update(state="failed", error=str(error))
    except Exception as error:  # a bad job must not stop the worker
        status.update(state="failed", error=f"{type(error).__name__}: {error}")
    finally:
        shutil.rmtree(staged, ignore_errors=True)
        for part in project.rglob(f".cf-{status['id']}-*.part"):
            part.unlink(missing_ok=True)
    status["seconds"] = round(time.time() - started, 2)
    write_status(project, status)
    print(f"{status['id']}: {status['state']}" + (f" ({status['error']})" if status["error"] else ""))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--once", action="store_true", help="Process waiting jobs, then exit")
    parser.add_argument("--server", default="http://127.0.0.1:8188")
    args = parser.parse_args(argv)
    if not jobs_dir(args.project).is_dir():
        print(f"Worker error: no jobs/comfy folder in {args.project}", file=sys.stderr)
        return 1
    recover_interrupted(args.project)
    try:
        while True:
            for path in pending_jobs(args.project):
                run_job(path, args.project, args.server)
            if args.once:
                return 0
            time.sleep(POLL_SECONDS)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
