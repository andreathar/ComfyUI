#!/usr/bin/env python3
"""Read-only catalogue preflight against localhost schemas; never queue or load models."""

from collections import Counter
from datetime import datetime, timezone
from http.client import HTTPException
import json
from pathlib import Path

import qualify_workflows
import workflow_catalogue as catalogue
import workflow_health

CATALOGUE = catalogue.ROOT / "studio/workflow-review"
VIRTUAL = {"SetNode", "GetNode"}
CAVEATS = [
    "Static checks only; no runnable or runtime-success claim. Nothing was queued.",
    "Frontend behavior, UI/API correspondence, subgraph socket types and unsupported checker semantics remain unverified.",
    "Model availability/compatibility, services/credentials, safety and hardware feasibility are not validated.",
]


def graph_hash(graph):
    return catalogue.digest(json.dumps(graph, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode())


def extract_graph(path, pointer):
    """Select only an exact catalogue payload pointer, never arbitrary JSON paths."""
    if path.name.lower().endswith(".metadata.json"):
        raise ValueError("Metadata sidecars are not workflow sources")
    if path.suffix.lower() == ".json":
        values = [("$", json.loads(path.read_text(encoding="utf-8-sig")))]
    elif path.suffix.lower() == ".png":
        if catalogue.Image is None:
            raise ValueError("PNG extraction unavailable: Pillow not installed")
        # Read only the requested metadata branch; the other branch may be invalid.
        key = pointer.split("/", 2)[1] if pointer.startswith("png/") else ""
        if key not in ("workflow", "prompt"):
            raise ValueError("Unsupported PNG payload pointer")
        with catalogue.Image.open(path) as image:
            value = image.text.get(key)
        if value is None:
            raise ValueError("Requested PNG metadata is absent")
        values = [("png/" + key, json.loads(value))]
    else:
        raise ValueError("Unsupported workflow source format")
    for base, value in values:
        for location, kind, graph in catalogue.payloads(value, base):
            if location == pointer and kind in ("ui", "api"):
                return kind, graph
    raise ValueError("Exact pointer does not identify a supported graph payload")


def inspect_alias(alias, workflow):
    result = {"absolute": alias.get("absolute"), "pointer": alias.get("pointer"),
              "expected_sha256": alias.get("source_sha256")}
    try:
        path = Path(alias["absolute"])
        # Hash and extract from the source without writing to it.
        result["actual_sha256"] = catalogue.file_hash(path)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return dict(result, outcome="source_unavailable", error=str(exc)), None
    if not result["expected_sha256"] or result["actual_sha256"] != result["expected_sha256"]:
        return dict(result, outcome="stale_source", error="Source SHA256 differs or is absent"), None
    try:
        kind, graph = extract_graph(path, alias["pointer"])
        if catalogue.file_hash(path) != result["actual_sha256"]:
            return dict(result, outcome="stale_source", error="Source changed during extraction"), None
        if kind != workflow["format"] or graph_hash(graph) != workflow["graph_sha256"]:
            raise ValueError("Extracted graph format/SHA256 does not match catalogue")
    except (OSError, ValueError, TypeError, KeyError, SyntaxError) + catalogue.PNG_ERRORS as exc:
        return dict(result, outcome="extraction_error", error=str(exc)), None
    return dict(result, outcome="fresh"), graph


def preflight(workflow, schemas):
    row = {"workflow_id": workflow["id"], "title": workflow.get("title", ""),
           "format": workflow.get("format"), "aliases": [], "issues": [], "notes": [],
           "frontend_validation": "pending" if workflow.get("format") == "ui" else "not_applicable",
           "runtime": "not_run", "uncertainties": list(CAVEATS)}
    selected = None
    for alias in workflow.get("aliases", []):
        result, graph = inspect_alias(alias, workflow)
        row["aliases"].append(result)
        if selected is None and graph is not None:
            selected = graph
            row["checked_alias"] = result
    if selected is None:
        outcomes = {item["outcome"] for item in row["aliases"]}
        row["outcome"] = next(iter(outcomes)) if len(outcomes) == 1 else "source_unavailable" if not outcomes else "no_fresh_graph"
        return row
    if schemas is None:
        row["outcome"] = "schema_unavailable"
        return row
    try:
        nodes = list(catalogue.graph_nodes(selected, workflow["format"]))
        virtual = sorted({node["type"] for _, node in nodes} & VIRTUAL)
        row["virtual_node_types"] = virtual
        if virtual:
            row["frontend_validation"] = "pending"
            row["uncertainties"].append("SetNode/GetNode are frontend virtual nodes; their semantics were not checked")
        if catalogue.subgraph_ids(selected):
            row["uncertainties"].append("Subgraph ports and UI/API correspondence remain unverified")
        # Empty schemas suppress only false missing-type errors, without deleting
        # nodes/links or pretending these are real backend schemas.
        checker_schemas = dict(schemas)
        checker_schemas.update({name: {"input": {}} for name in virtual})
        row["issues"], row["notes"] = workflow_health.check_workflow(selected, checker_schemas)
        row["outcome"] = "static_errors" if row["issues"] else "static_checks_passed"
    except Exception as exc:
        # The shared checker does not support every frontend/schema representation.
        # Keep a per-graph result instead of losing the rest of the catalogue.
        row["outcome"] = "checker_unsupported"
        row["checker_error"] = f"{type(exc).__name__}: {exc}"
    return row


def build_report(data, schemas, snapshot):
    rows = [preflight(workflow, schemas) for workflow in data["workflows"]]
    return {"version": 1, "generated_at": datetime.now(timezone.utc).isoformat(),
            "schema_snapshot": snapshot, "caveats": CAVEATS,
            "counts": {"unique_graphs": len(rows), "outcomes": dict(sorted(Counter(row["outcome"] for row in rows).items())),
                       "alias_outcomes": dict(sorted(Counter(alias["outcome"] for row in rows for alias in row["aliases"]).items()))},
            "workflows": rows}


def main():
    data = json.loads((CATALOGUE / "workflows.json").read_text(encoding="utf-8"))
    try:
        schemas, snapshot = catalogue.local_schemas(8188)
    except (OSError, ValueError, HTTPException) as exc:
        schemas, snapshot = None, {"status": "unavailable", "error": str(exc)}
    report = build_report(data, schemas, snapshot)
    refs = CATALOGUE / "references"
    qualify_workflows.write_text(refs / "static-preflight.json", json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    fields = ["workflow_id", "title", "format", "outcome", "issues", "notes", "aliases", "frontend_validation", "runtime", "uncertainties"]
    qualify_workflows.write_csv(refs / "static-preflight.csv", [{key: row[key] for key in fields} for row in report["workflows"]], fields)
    print(json.dumps(report["counts"], indent=2))
    print("Static only; frontend validation and runtime remain unverified. No workflows queued.")


if __name__ == "__main__":
    main()
