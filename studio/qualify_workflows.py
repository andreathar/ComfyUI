#!/usr/bin/env python3
"""Join the reference catalogue to local model files and pilot receipts; never queue."""

import csv
import io
import json
import os
import stat
from pathlib import Path
import re
import uuid
from urllib.parse import quote

import yaml

from workflow_catalogue import csv_value, output_directory

ROOT = Path(__file__).resolve().parent.parent
CATALOGUE = ROOT / "studio/workflow-review"
MODEL_SUFFIXES = {".safetensors", ".ckpt", ".gguf", ".pth", ".pt", ".bin", ".onnx", ".engine", ".pkl", ".sft"}


def model_roots(root):
    roots = {root / "models"}
    config = root / "extra_model_paths.yaml"
    if config.exists():
        for entry in (yaml.safe_load(config.read_text()) or {}).values():
            base = Path(os.path.expandvars(str(entry.get("base_path", root)))).expanduser()
            if not base.is_absolute():
                base = root / base
            for key, values in entry.items():
                if key in ("base_path", "is_default") or not isinstance(values, str):
                    continue
                roots.update(base / value.strip() for value in values.splitlines() if value.strip())
    return sorted(roots)


def inventory(roots):
    files, errors = {}, []
    for root in roots:
        if not root.exists():
            errors.append({"path": str(root), "error": "configured model path absent"})
            continue
        # Resolve model categories and follow nested shared weight directories.
        paths = [root.resolve()]
        if root.name == "models":
            paths = [child.resolve() for child in root.iterdir() if child.is_dir()]
        for directory in paths:
            try:
                visited = set()
                for base, directories, names in os.walk(directory, followlinks=True,
                        onerror=lambda exc: errors.append({"path": str(exc.filename), "error": str(exc)})):
                    resolved = Path(base).resolve()
                    if resolved in visited:
                        directories[:] = []
                        continue
                    visited.add(resolved)
                    for name in names:
                        path = Path(base) / name
                        if path.suffix.lower() not in MODEL_SUFFIXES or not path.is_file():
                            continue
                        actual = path.resolve()
                        record = files.setdefault(str(actual), {"path": str(actual), "filename": path.name,
                            "filenames": [], "bytes": actual.stat().st_size, "search_roots": []})
                        if path.name not in record["filenames"]:
                            record["filenames"].append(path.name)
                        if str(root) not in record["search_roots"]:
                            record["search_roots"].append(str(root))
            except OSError as exc:
                errors.append({"path": str(directory), "error": str(exc)})
    return sorted(files.values(), key=lambda value: value["path"]), errors


def family(workflow):
    text = (workflow["title"] + " " + " ".join(workflow["node_types"]) + " " +
            " ".join(alias["relative"] for alias in workflow["aliases"])).lower()
    for label, pattern in (
        ("remote-or-service-review", r"kling|agnes|claude|anthropic|lmstudio"),
        ("h3-video", r"minimax|\bh3\b"), ("3d-and-rigging", r"tripo|trellis|pixal3d|unirig"),
        ("z-image", r"z.image|zimage"), ("flux", r"flux"), ("qwen-image", r"qwen.image"),
        ("segmentation-face-background", r"rmbg|reactor|sam3|segment|face"),
        ("video-audio", r"video|vhs_|audio|tts"), ("sd15", r"sd15|sd1.5|stable.diffusion.1"),
        ("prompt-and-utilities", r"lc123|prompt|palette|itools"),
    ):
        if re.search(pattern, text):
            return label
    return "unclassified-review"


def qualify(workflow, files):
    by_name = {}
    for item in files:
        for name in item.get("filenames", [item["filename"]]):
            by_name.setdefault(name, []).append(item)
    references = []
    for ref in workflow["model_references"]:
        name = Path(ref["reference"].replace("\\", "/")).name
        candidates = by_name.get(name, [])
        references.append({**ref, "local_candidates": [item["path"] for item in candidates],
                           "disk_status": "basename_candidates_found" if candidates else "no_basename_match",
                           "compatibility": "unverified: filename match does not validate loader/search path"})
    blockers = list(workflow["blockers"])
    missing = sorted({r["reference"] for r in references if not r["local_candidates"] and r["basis"] == "filename_heuristic"})
    if missing:
        blockers.append("Referenced filenames not found in scanned model roots: " + "; ".join(missing))
    lane = family(workflow)
    if lane == "remote-or-service-review":
        blockers.append("Remote/API/local-service safety and availability require manual review; not queued")
    return {"workflow_id": workflow["id"], "title": workflow["title"], "family_estimate": lane,
            "family_basis": "heuristic from title, node types and source paths; not certification",
            "aliases": workflow["aliases"], "models": references, "blockers": blockers,
            "disposition": "blocked_or_review_needed" if blockers else "preflight_and_safety_review_needed",
            "runtime": "not_run_by_catalogue", "hardware_fit": "unproven"}


def write_text(path, text):
    with output_directory(path.parent) as fd:
        try:
            info = os.stat(path.name, dir_fd=fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            if not stat.S_ISREG(info.st_mode):
                raise ValueError(f"Unsafe reference output: {path}")
        temporary = ".references-" + uuid.uuid4().hex
        handle = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
        try:
            with os.fdopen(handle, "w") as stream:
                stream.write(text)
            os.replace(temporary, path.name, src_dir_fd=fd, dst_dir_fd=fd)
        finally:
            try:
                os.unlink(temporary, dir_fd=fd)
            except FileNotFoundError:
                pass


def write_csv(path, rows, fields):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fields)
    writer.writeheader()
    writer.writerows({key: csv_value(value) for key, value in row.items()} for row in rows)
    write_text(path, stream.getvalue())


def main():
    catalogue = json.loads((CATALOGUE / "workflows.json").read_text())
    files, errors = inventory(model_roots(ROOT))
    qualified = [qualify(workflow, files) for workflow in catalogue["workflows"]]
    refs = CATALOGUE / "references"
    write_text(refs / "qualification.json", json.dumps({"model_files": files, "model_scan_errors": errors,
        "workflows": qualified}, indent=2) + "\n")
    write_csv(refs / "models.csv", [{**item, "search_roots": " | ".join(item["search_roots"])} for item in files],
              ["path", "filename", "bytes", "search_roots"])
    write_csv(refs / "test-queue.csv", [{"id": item["workflow_id"], "title": item["title"],
        "family_estimate": item["family_estimate"], "disposition": item["disposition"],
        "blockers": " | ".join(item["blockers"]), "hardware_fit": item["hardware_fit"]} for item in qualified],
        ["id", "title", "family_estimate", "disposition", "blockers", "hardware_fit"])
    lines = ["# Extension source references", "", "Originals stay in place. Lists link source artifacts, not runnable certifications.", ""]
    for extension in catalogue["extensions"]:
        lines.extend(["## " + extension["id"], "", "Placement: `" + extension["placement"] + "`", ""])
        aliases = [(w, a) for w in catalogue["workflows"] for a in w["aliases"] if a.get("extension") == extension["id"]]
        if not aliases:
            lines.append("No graph payload found in inspected JSON/PNG sources. See inventory exclusions/gaps.")
        for workflow, alias in aliases:
            source = Path(alias["absolute"])
            link = quote(os.path.relpath(source, refs), safe='/') if source.is_relative_to(ROOT) else source.as_uri()
            lines.append("- `" + workflow["id"] + "` — [" + alias["relative"].replace("]", "\\]") + "](" +
                         link + ") — `" + alias["pointer"] + "`")
        lines.append("")
    write_text(refs / "extensions.md", "\n".join(lines) + "\n")
    print(f"{len(files)} physical model paths, {len(qualified)} workflow dispositions, {len(errors)} model scan gaps")


if __name__ == "__main__":
    main()
