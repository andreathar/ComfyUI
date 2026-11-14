#!/usr/bin/env python3
"""Read-only workflow discovery; writes references, never imports or runs extensions."""

import argparse
import csv
from collections import Counter
from contextlib import contextmanager, ExitStack
from datetime import datetime, timezone
import hashlib
import io
from http.client import HTTPConnection, HTTPException
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import uuid
import sys

try:
    from PIL import Image
except ImportError:
    Image = None

PNG_ERRORS = (Image.DecompressionBombError,) if Image else ()
ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", ".pytest_cache"}
UNSUPPORTED = {".jpg", ".jpeg", ".webp", ".gif", ".zip", ".7z", ".tar", ".gz"}
VIRTUAL = {"Note", "MarkdownNote", "Reroute", "SetNode", "GetNode"}
MODEL_SUFFIXES = {".safetensors", ".ckpt", ".pt", ".pth", ".bin", ".gguf", ".onnx", ".engine", ".pkl", ".sft"}
MODEL_FIELD = re.compile(r"ckpt|checkpoint|unet|diffusion|clip_name|text_encoder|vae|lora|control.?net|upscale_model|adapter|model_name|model_path|weights", re.I)
WRAPPERS = {"workflow", "prompt", "extra_pnginfo", "extra", "workflow_json"}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_hash(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def reference(path, root):
    path = path.absolute()
    return {"absolute": str(path), "relative": os.path.relpath(path, root)}


def graph_kind(value):
    if not isinstance(value, dict):
        return None
    nodes = value.get("nodes")
    if isinstance(nodes, list) and all(isinstance(n, dict) and "id" in n and isinstance(n.get("type"), str) for n in nodes):
        if nodes or "links" in value or "definitions" in value:
            return "ui"
    if value and all(isinstance(n, dict) and isinstance(n.get("class_type"), str) and isinstance(n.get("inputs"), dict) for n in value.values()):
        return "api"
    return None


def payloads(value, pointer="$"):
    """Recognize direct graphs and explicit wrappers, not arbitrary config objects."""
    kind = graph_kind(value)
    if kind:
        yield pointer, kind, value
        return
    keys = sorted(WRAPPERS & value.keys()) if isinstance(value, dict) else []
    if not keys:
        yield pointer, exclusion(value), None
    for key in keys:
        child = value[key]
        location = pointer + "/" + key
        if isinstance(child, str):
            if key == "prompt" and not child.lstrip().startswith(("{", "[")):
                yield location, "metadata_or_config", None
                continue
            try:
                child = json.loads(child)
            except ValueError as exc:
                yield location, "parse_error", str(exc)
                continue
        yield from payloads(child, location)


def exclusion(value):
    if isinstance(value, dict) and isinstance(value.get("nodes"), list):
        if value["nodes"] and all(isinstance(n, dict) and "key" in n and "settings" in n for n in value["nodes"]):
            return "recipe"
        if any(isinstance(n, dict) and "type" in n for n in value["nodes"]) or any(key in value for key in ("links", "definitions", "last_node_id")):
            return "malformed_graph"
    if isinstance(value, dict) and any(isinstance(n, dict) and "class_type" in n for n in value.values()):
        return "malformed_graph"
    return "metadata_or_config"


def graph_nodes(graph, kind, scope="root"):
    if kind == "api":
        for key, node in graph.items():
            yield scope, dict(node, id=key, type=node["class_type"])
    else:
        for node in graph["nodes"]:
            yield scope, node
        definitions = graph.get("definitions", {})
        if isinstance(definitions, dict):
            for index, subgraph in enumerate(definitions.get("subgraphs", [])):
                if graph_kind(subgraph) != "ui":
                    raise ValueError(f"Malformed subgraph definition at {scope}/{index}")
                yield from graph_nodes(subgraph, "ui", scope + "/" + str(subgraph.get("id", index)))


def subgraph_ids(graph):
    ids = set()
    if isinstance(graph, dict):
        definitions = graph.get("definitions", {})
        if isinstance(definitions, dict):
            for subgraph in definitions.get("subgraphs", []):
                if isinstance(subgraph, dict):
                    if "id" in subgraph:
                        ids.add(str(subgraph["id"]))
                    ids.update(subgraph_ids(subgraph))
    return ids


def strings(value, prefix, skip_links=False):
    if isinstance(value, str):
        if value.lstrip().startswith(("{", "[")):
            try:
                decoded = json.loads(value)
            except ValueError:
                pass
            else:
                if isinstance(decoded, (dict, list)):
                    yield from strings(decoded, prefix + "/json", skip_links)
                    return
        yield prefix, value
    elif isinstance(value, dict):
        for key, child in value.items():
            yield from strings(child, prefix + "/" + str(key), skip_links)
    elif isinstance(value, list):
        if skip_links and len(value) == 2 and isinstance(value[0], (str, int)) and isinstance(value[1], int):
            return
        for index, child in enumerate(value):
            yield from strings(child, prefix + "/" + str(index), skip_links)


def describe_graph(graph, kind, schemas):
    nodes, models, unknowns, blockers = [], [], set(), set()
    definitions = subgraph_ids(graph)
    for scope, node in graph_nodes(graph, kind):
        name = node["type"]
        category = "subgraph" if name in definitions else "virtual" if name in VIRTUAL else "backend_or_unknown"
        schema = schemas.get(name) if schemas is not None else None
        muted = node.get("mode", 0) in (2, 4)
        status = "not_applicable" if category != "backend_or_unknown" else "not_checked" if schemas is None else "available" if schema is not None else "unavailable_in_snapshot"
        nodes.append({"scope": scope, "id": str(node["id"]), "type": name, "category": category,
                      "mode": node.get("mode", 0), "schema_status": status,
                      "provider": schema.get("python_module") if schema else None})
        if status == "unavailable_in_snapshot" and not muted:
            blockers.add("Node type unavailable in localhost schema snapshot: " + name)
        if category == "virtual":
            unknowns.add("Frontend virtual-node behavior requires browser validation")
        if category == "subgraph":
            unknowns.add("Subgraph ports and UI/API correspondence are unverified")
        if schema and schema.get("api_node"):
            blockers.add("API node requires separate service/authorization review: " + name)
        values = node.get("inputs", {}) if kind == "api" else {
            "widgets_values": node.get("widgets_values", []),
            "widgets_values_named": node.get("widgets_values_named", {}),
        }
        for field, value in strings(values, "inputs" if kind == "api" else "widgets", skip_links=kind == "api"):
            filename = "\n" not in value and len(value) < 1024 and "://" not in value and Path(value).suffix.lower() in MODEL_SUFFIXES
            named_model = bool(MODEL_FIELD.search(field.rsplit("/", 1)[-1]))
            if filename or (named_model and value):
                models.append({"scope": scope, "node_id": str(node["id"]), "node_type": name,
                               "field": field, "reference": value,
                               "basis": "filename_heuristic" if filename else "named_selection_not_resolved",
                               "availability": "not_checked", "loader_compatibility": "not_checked"})
            if "{{" in value or "${" in value:
                unknowns.add("Template/dynamic values require caller inputs")
    if schemas is None:
        unknowns.add("Node availability/providers not checked (no localhost schema snapshot)")
    if kind == "ui":
        unknowns.add("Positional UI widgets are not schema-decoded; model filename extraction is heuristic")
    unknowns.add("Inputs, services, safety, model availability/compatibility and hardware feasibility are not validated")
    return {"nodes": nodes, "node_types": sorted({n["type"] for n in nodes}), "model_references": models,
            "blockers": sorted(blockers), "unknowns": sorted(unknowns),
            "purpose": "unclassified", "completeness": "unreviewed", "task": "unclassified",
            "variant": "original", "test_status": "mapped / not run"}


def revision(path):
    if not (path / ".git").exists():
        return None
    result = subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"], capture_output=True, text=True, check=False,
                            env=dict(os.environ, GIT_OPTIONAL_LOCKS="0"))
    return result.stdout.strip() if result.returncode == 0 else None


def extension_sources(root, issues=None):
    extensions = []
    issues = issues if issues is not None else []
    base = root / "custom_nodes"
    if not base.exists():
        return extensions

    def add(path, disabled=False):
        if path.name in SKIP_DIRS or path.name.startswith("."):
            return
        if not path.is_dir() and not (path.name.endswith((".py", ".py.disabled", ".py.example"))):
            return
        placement = "disabled_location" if disabled or path.name.endswith((".disabled", ".example")) else "enabled_location"
        entry = {"id": os.path.relpath(path, root), **reference(path, root), "placement": placement,
                 "entry_kind": "directory" if path.is_dir() else "standalone_file",
                 "revision": None, "source_sha256": None,
                 "load_status": "not_inferred_from_placement", "frontend_status": "not_inspected"}
        extensions.append(entry)
        try:
            entry["revision"] = revision(path) if path.is_dir() else None
            entry["source_sha256"] = file_hash(path) if path.is_file() else None
        except OSError as exc:
            issues.append({"path": str(path), "status": "extension_inspection_error", "error": str(exc)})

    def children(directory):
        try:
            return sorted(directory.iterdir())
        except OSError as exc:
            issues.append({"path": str(directory), "status": "unreadable_directory", "error": str(exc)})
            return []

    for path in children(base):
        if path.name == ".disabled" and path.is_dir():
            for child in children(path):
                add(child, True)
        else:
            add(path)
    return extensions


def source_roots(root, extensions):
    roots = [(Path(e["absolute"]), "extension", e["id"], e["placement"]) for e in extensions if e["entry_kind"] == "directory"]
    for name, kind in (("user", "saved_user"), ("workflows", "saved_user"), ("studio/templates", "studio_template"), ("blueprints", "core_blueprint")):
        if (root / name).is_dir():
            roots.append((root / name, kind, None, None))
    package_roots = {Path(p) for p in sys.path if p and Path(p).is_dir() and "site-packages" in p}
    package_roots.update(root.glob(".venv/lib/python*/site-packages"))
    for packages in sorted(package_roots):
        for name in ("comfyui_workflow_templates_json", "comfyui_workflow_templates_core", "comfyui_workflow_templates"):
            path = packages / name
            if path.is_dir():
                roots.append((path, "installed_template_package", None, None))
    return roots


def candidates(path, output, issues):
    def error(exc):
        issues.append({"path": str(exc.filename), "status": "unreadable_directory", "error": str(exc)})

    for directory, dirs, files in os.walk(path, followlinks=False, onerror=error):
        kept = []
        for name in sorted(dirs):
            child = Path(directory) / name
            if child.resolve().is_relative_to(output.resolve()) or name in SKIP_DIRS:
                continue
            if child.is_symlink():
                issues.append({"path": str(child), "status": "uninspected_symlink_directory"})
            else:
                kept.append(name)
        dirs[:] = kept
        for name in sorted(files):
            child = Path(directory) / name
            if not child.resolve().is_relative_to(output.resolve()) and child.suffix.lower() in {".json", ".png"} | UNSUPPORTED:
                yield child


def scan(root, output, schemas=None):
    root, output = root.absolute(), output.absolute()
    issues = []
    extensions = extension_sources(root, issues)
    roots = source_roots(root, extensions)
    validate_output(output, [root, root / "custom_nodes", *(p for p, _, _, _ in roots)])
    workflows, sources = {}, []
    seen = set()
    for directory, family, owner, placement in roots:
        if directory.resolve().is_relative_to(output.resolve()):
            continue
        for path in candidates(directory, output, issues):
            identity = str(path.absolute())
            if identity in seen:
                continue
            seen.add(identity)
            source = {**reference(path, root), "family": family, "extension": owner, "placement": placement, "payloads": []}
            sources.append(source)
            try:
                source["source_sha256"] = file_hash(path)
                if path.suffix.lower() in UNSUPPORTED:
                    source["status"] = "uninspected_media_or_archive"
                    continue
                if path.suffix.lower() == ".png":
                    if Image is None:
                        source["status"] = "uninspected_png_pillow_unavailable"
                        continue
                    with Image.open(path) as image:
                        if image.format != 'PNG':
                            raise ValueError('Expected PNG content for workflow metadata')
                        metadata = dict(image.text)
                    values = []
                    for key in ("workflow", "prompt"):
                        if key in metadata:
                            try:
                                values.append(("png/" + key, json.loads(metadata[key])))
                            except (ValueError, TypeError) as exc:
                                source["payloads"].append({"pointer": "png/" + key, "status": "parse_error", "error": str(exc)})
                    if not values and not source["payloads"]:
                        source["status"] = "png_without_workflow_metadata"
                        continue
                else:
                    values = [("$", json.loads(path.read_text(encoding="utf-8-sig")))]
                for pointer, value in values:
                    for location, kind, graph in payloads(value, pointer):
                        if kind not in ("ui", "api"):
                            record = {"pointer": location, "status": kind}
                            if kind == "parse_error":
                                record["error"] = graph
                            source["payloads"].append(record)
                            continue
                        canonical = json.dumps(graph, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
                        graph_hash = digest(canonical)
                        workflow_id = "wf-" + graph_hash
                        alias = {**reference(path, root), "pointer": location, "family": family, "extension": owner,
                                 "placement": placement, "source_sha256": source["source_sha256"]}
                        if workflow_id not in workflows:
                            workflows[workflow_id] = {"id": workflow_id, "graph_sha256": graph_hash, "format": kind,
                                                      "title": path.stem, "aliases": [], **describe_graph(graph, kind, schemas)}
                        workflows[workflow_id]["aliases"].append(alias)
                        source["payloads"].append({"pointer": location, "status": "graph", "workflow_id": workflow_id, "format": kind})
                source["status"] = "inspected"
            except (OSError, ValueError, TypeError, SyntaxError) + PNG_ERRORS as exc:
                source["status"] = "parse_or_read_error"
                source["error"] = str(exc)
    rows = sorted(workflows.values(), key=lambda w: w["id"])
    for extension in extensions:
        owned = [w for w in rows if any(a["extension"] == extension["id"] for a in w["aliases"])]
        extension["unique_workflows"] = len(owned)
        extension["graph_occurrences"] = sum(a["extension"] == extension["id"] for w in owned for a in w["aliases"])
        extension["coverage"] = "mapped / not run" if owned else "no_graph_discovered; frontend-only status unknown"
    counts = Counter(s["status"] for s in sources)
    payload_counts = Counter(p["status"] for s in sources for p in s["payloads"])
    occurrences = sum(len(w["aliases"]) for w in rows)
    return {"version": 1, "generated_at": datetime.now(timezone.utc).isoformat(), "root": str(root),
            "roots": [{**reference(p, root), "family": f, "extension": e, "placement": loc} for p, f, e, loc in roots],
            "counts": {"extensions": len(extensions), "source_files": len(sources), "unique_workflows": len(rows),
                       "graph_occurrences": occurrences, "duplicate_aliases": occurrences - len(rows),
                       "source_statuses": dict(sorted(counts.items())), "payload_statuses": dict(sorted(payload_counts.items())),
                       "traversal_issues": len(issues)},
            "extensions": extensions, "workflows": rows, "sources": sources, "traversal_issues": issues}


def local_schemas(port):
    """Fixed loopback GET only: no proxy, redirects, URL input, or remote requests."""
    connection = HTTPConnection("127.0.0.1", port, timeout=15)
    try:
        connection.request("GET", "/object_info")
        response = connection.getresponse()
        if response.status != 200:
            raise ValueError(f"localhost /object_info returned HTTP {response.status}")
        raw = response.read()
        schemas = json.loads(raw)
        if not isinstance(schemas, dict) or not all(isinstance(v, dict) for v in schemas.values()):
            raise ValueError("localhost /object_info is not a schema mapping")
        return schemas, {"status": "available", "endpoint": f"http://127.0.0.1:{port}/object_info",
                         "sha256": digest(raw), "node_types": len(schemas)}
    finally:
        connection.close()


REPORT_FILES = ("workflows.json", "extensions.csv", "workflow-matrix.csv", "model-references.csv",
                "blockers/workflows.csv", "tests/README.md", "results/README.md", "blockers/README.md", "README.md")


def validate_output(output, protected):
    output = Path(os.path.abspath(output))
    for path in (*reversed(output.parents), output):
        if path.is_symlink():
            raise ValueError(f"Symlink in catalogue output path: {path}")
    for path in protected:
        if Path(path).resolve().is_relative_to(output):
            raise ValueError(f"Catalogue output overlaps scan root or source: {path}")


@contextmanager
def output_directory(path):
    """Walk from the filesystem root without following any directory symlink."""
    path = Path(os.path.abspath(path))
    fd = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in path.parts[1:]:
            try:
                os.mkdir(part, dir_fd=fd)
            except FileExistsError:
                pass
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        yield fd
    finally:
        os.close(fd)


def csv_value(value):
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, str) and re.match(r"^[\s\x00-\x20\x7f]*[=+\-@]", value):
        return "'" + value
    return value


def write_csv(path, fields, rows, write_text):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({key: csv_value(value) for key, value in row.items() if key in fields})
    write_text(path, stream.getvalue())


def write_report(report, output):
    output = Path(os.path.abspath(output))
    sources = [Path(e["absolute"]) for key in ("sources", "extensions") for e in report[key]]
    validate_output(output, [Path(report["root"]), Path(report["root"]) / "custom_nodes",
                             *(Path(r["absolute"]) for r in report["roots"]), *sources])
    source_ids = {(s.st_dev, s.st_ino) for p in sources if p.exists() for s in [p.stat()]}
    with ExitStack() as stack:
        directories = {parent: stack.enter_context(output_directory(output / parent))
                       for parent in (".", "tests", "results", "blockers")}

        def check_target(path):
            fd = directories[str(path.parent.relative_to(output))]
            try:
                info = os.stat(path.name, dir_fd=fd, follow_symlinks=False)
            except FileNotFoundError:
                return fd
            if not stat.S_ISREG(info.st_mode) or (info.st_dev, info.st_ino) in source_ids:
                raise ValueError(f"Unsafe catalogue output target: {path}")
            return fd

        def write_text(path, text):
            fd = check_target(path)
            temporary = f".catalogue-{uuid.uuid4().hex}.tmp"
            handle = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
            try:
                with os.fdopen(handle, "w", encoding="utf-8", newline="") as stream:
                    stream.write(text)
                    stream.flush()
                    os.fsync(stream.fileno())
                check_target(path)
                os.replace(temporary, path.name, src_dir_fd=fd, dst_dir_fd=fd)
            finally:
                try:
                    os.unlink(temporary, dir_fd=fd)
                except FileNotFoundError:
                    pass

        for name in REPORT_FILES:
            check_target(output / name)
        # The output is pruned during discovery, so an existing workflow here
        # would otherwise be hidden from the source-overlap check.
        try:
            handle = os.open("workflows.json", os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directories["."])
        except FileNotFoundError:
            if any(Path(name).name in os.listdir(directories[str(Path(name).parent)]) for name in REPORT_FILES[1:]):
                raise ValueError(f"Existing report targets require a catalogue inventory: {output}")
        else:
            with os.fdopen(handle, encoding="utf-8") as stream:
                existing = json.load(stream)
            if not isinstance(existing, dict) or not {"version", "generated_at", "root", "roots", "sources", "counts", "workflows"} <= existing.keys():
                raise ValueError(f"Not a catalogue inventory: {output / 'workflows.json'}")
        _write_report(report, output, write_text)


def _write_report(report, output, write_text):
    write_text(output / "workflows.json", json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    write_csv(output / "extensions.csv", ["id", "absolute", "relative", "placement", "entry_kind", "revision", "source_sha256", "load_status", "frontend_status", "unique_workflows", "graph_occurrences", "coverage"], report["extensions"], write_text)
    matrix, models, blockers = [], [], []
    for workflow in report["workflows"]:
        aliases = workflow["aliases"]
        matrix.append({"id": workflow["id"], "title": workflow["title"], "format": workflow["format"],
                       "families": sorted({a["family"] for a in aliases}), "extensions": sorted({a["extension"] for a in aliases if a["extension"]}),
                       "task": workflow["task"], "models": sorted({m["reference"] for m in workflow["model_references"]}),
                       "blockers": workflow["blockers"], "unknowns": workflow["unknowns"], "variant": workflow["variant"],
                       "test_status": workflow["test_status"], "sources": aliases})
        models.extend(dict(model, workflow_id=workflow["id"]) for model in workflow["model_references"])
        blockers.extend({"workflow_id": workflow["id"], "kind": kind, "detail": detail} for kind in ("blockers", "unknowns") for detail in workflow[kind])
    write_csv(output / "workflow-matrix.csv", ["id", "title", "format", "families", "extensions", "task", "models", "blockers", "unknowns", "variant", "test_status", "sources"], matrix, write_text)
    write_csv(output / "model-references.csv", ["workflow_id", "scope", "node_id", "node_type", "field", "reference", "basis", "availability", "loader_compatibility"], models, write_text)
    write_csv(output / "blockers" / "workflows.csv", ["workflow_id", "kind", "detail"], blockers, write_text)
    write_text(output / "tests" / "README.md", "# Tests\n\nThe scanner creates no test copies and executes no workflows. Separately reviewed PC pilot copies, when present, are in `pilots/`; constructed extension capability API tests are in `utilities/`. See `../START_HERE.md` for current coverage and caveats. Scanner unit tests: `python -m unittest discover -s studio -p 'test_workflow_catalogue.py' -v`.\n")
    write_text(output / "results" / "README.md", "# Results\n\nInventory is not runtime evidence. The scanner performs no queue/history requests or generation tests. Separately executed pilot evidence, when present: [PILOTS.md](PILOTS.md), [pilots.json](pilots.json), [UTILITIES.md](UTILITIES.md) and [utilities.json](utilities.json). See `../START_HERE.md` for overall progress. Cached outputs and historical reports are not certification.\n")
    write_text(output / "blockers" / "README.md", "# Blockers and unknowns\n\n[workflows.csv](workflows.csv) separates observed schema gaps from unverified requirements. A missing localhost schema is not proof that an extension is absent. Muted/bypassed nodes, frontend virtual nodes and native subgraph IDs are not reported as missing backend types. All nodes, including inactive nodes and unused subgraph definitions, remain in the reference map. File-level exclusions, errors, unsupported media and traversal gaps are in `../workflows.json` (`sources`, `traversal_issues`). No model existence, loader compatibility, safety or hardware qualification is implied.\n")
    families = sorted({r["family"] for r in report["roots"]})
    table = ["| Source family | Graph occurrences | Unique graphs within family |", "|---|---:|---:|"]
    for family in families:
        owned = [w for w in report["workflows"] if any(a["family"] == family for a in w["aliases"])]
        table.append(f"| {family} | {sum(a['family'] == family for w in owned for a in w['aliases'])} | {len(owned)} |")
    counts = report["counts"]
    text = f"""# Local workflow catalogue

Generated {report['generated_at']}. **Mapped / not run**, never a runnable-workflow certification.

- [Extension coverage](extensions.csv) — every extension directory and standalone candidate, including `.disabled` and `.example` placements.
- [Full inventory](workflows.json) — aliases, absolute/checkout-relative paths, source hashes, graph hashes, node references/providers, exclusions and errors.
- [Workflow matrix](workflow-matrix.csv) · [Model references](model-references.csv) · [Blockers/unknowns](blockers/README.md)
- [Test copies](tests/README.md) · [Runtime results](results/README.md) · [Review progress](START_HERE.md). This scanner never executes workflows.

## Reconciliation

{counts['source_files']} candidate files; {counts['unique_workflows']} unique graphs; {counts['graph_occurrences']} graph payload occurrences = {counts['unique_workflows']} unique + {counts['duplicate_aliases']} duplicate aliases. One PNG or JSON wrapper can contain multiple payloads. Source-status counts partition files; payload-status counts partition extracted payloads (not files).

Source statuses: `{json.dumps(counts['source_statuses'], sort_keys=True)}`

Payload statuses: `{json.dumps(counts['payload_statuses'], sort_keys=True)}`

Traversal gaps: {counts['traversal_issues']}. Extensions/candidates: {counts['extensions']}.

{chr(10).join(table)}

Family unique totals overlap when exact graphs occur in several families; core blueprints and installed templates are not extension coverage. Enabled location is **not proof of loading**. Revisions are local Git HEAD where present, not clean-tree assertions; file hashes capture scanned content.

## Scope and limits

Walk all extension directories (including disabled ones), `user/` (including backups and panel snapshots), optional `workflows/`, `studio/templates/`, `blueprints/`, and installed workflow-template JSON/core packages discovered on the interpreter's site-packages or checkout `.venv`. Exact scan roots are recorded in JSON. No imports of extensions or template packages. No originals moved, rewritten or copied.

Only JSON structure and PNG `workflow`/`prompt` text metadata are inspected. Recipes using `key/settings`, config and metadata sidecars are excluded. Known JSON wrappers are searched; arbitrary document snippets are not. JPEG/WebP/GIF metadata and archives are logged as uninspected, not silently treated as empty. Python/JS/Markdown snippets, binaries, media-package previews, `input/`, `output/`, `.git`, dependency/cache directories and nested symlink directories are outside scope. Standalone Python candidates get coverage rows but their source is not parsed for embedded graphs. The generated output directory is always pruned, even when inside a source root.

Deduplication uses SHA-256 of canonical full graph JSON (sorted object keys, formatting ignored). Layout, settings, node IDs, array order and subgraphs are preserved: meaningful variants cannot silently merge. UI/API pairs remain separate unless exactly identical JSON; shared filenames/metadata are not execution equivalence. Source SHA-256 hashes original bytes independently.

Model references are filename heuristics from node widgets/API inputs plus named model selections; URLs and prose can require manual review. Dynamic/non-file selections remain unresolved. No model-folder inventory, download, loader compatibility, graph completeness, safety or hardware inference. Providers are only the localhost schema's `python_module` when present, not a guessed ownership mapping. Subgraph definitions and muted nodes are included conservatively.

Schema reconciliation: `{json.dumps(report.get('schema_snapshot', {}), sort_keys=True)}`. Only optional fixed-loopback `GET /object_info` is supported; no remote URL, redirects, proxies, queue calls or workflow execution. Schema presence does not prove frontend functionality or runtime success.

## Regenerate

```sh
.venv/bin/python -m unittest discover -s studio -p 'test_workflow_catalogue.py' -v
.venv/bin/python studio/workflow_catalogue.py
# Optional read-only local schema snapshot (failure leaves availability unknown):
.venv/bin/python studio/workflow_catalogue.py --port 8188
```

Generated index/CSV/JSON files are overwritten on refresh; originals and future test/result evidence are untouched. No copied graph payloads are stored: use the original reference and verify its source hash before review.
"""
    write_text(output / "README.md", text)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, help="Defaults to <root>/studio/workflow-review")
    parser.add_argument("--port", type=int, help="Optional read-only schema GET on 127.0.0.1 only")
    args = parser.parse_args()
    if args.output is None:
        args.output = args.root / "studio/workflow-review"
    schemas, snapshot = None, {"status": "not_requested"}
    if args.port is not None:
        if not 1 <= args.port <= 65535:
            parser.error("--port must be between 1 and 65535")
        try:
            schemas, snapshot = local_schemas(args.port)
        except (OSError, ValueError, HTTPException) as exc:
            snapshot = {"status": "unavailable", "error": str(exc)}
    report = scan(args.root, args.output, schemas)
    report["schema_snapshot"] = snapshot
    write_report(report, args.output)
    print(json.dumps(report["counts"], indent=2))
    print(f"Catalogue: {args.output.absolute() / 'README.md'}")


if __name__ == "__main__":
    main()
