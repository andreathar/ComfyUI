#!/usr/bin/env python3
"""Read-only local workflow audit. Never queues workflows or calls model APIs."""

import argparse
from datetime import datetime, timezone
import hashlib
from http.client import HTTPConnection
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def fingerprint(workflow):
    if not isinstance(workflow, dict):
        raise ValueError("Workflow must be a JSON object")
    if "nodes" in workflow:
        data = {
            "nodes": sorted(({
                "id": str(n["id"]), "type": n["type"], "mode": n.get("mode", 0),
                "widgets": n.get("widgets_values", []),
                "named_widgets": {k: v for k, v in n.get("widgets_values_named", {}).items()
                                  if k not in {i["name"] for i in n.get("inputs", []) if i.get("link") is not None}},
                "inputs": n.get("inputs", []), "properties": n.get("properties", {}),
            } for n in workflow["nodes"]), key=lambda n: n["id"]),
            "links": workflow.get("links", []),
            "subgraphs": [fingerprint(s) for s in workflow.get("definitions", {}).get("subgraphs", [])],
            "inputs": workflow.get("inputs", []), "outputs": workflow.get("outputs", []),
            "inputNode": workflow.get("inputNode"), "outputNode": workflow.get("outputNode"),
        }
    else:
        data = {str(k): {"class_type": v["class_type"], "inputs": v["inputs"]}
                for k, v in workflow.items()}
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def widget_values(node, schema):
    """Decode native widgets, including the frontend's seed control widget."""
    linked = {i["name"] for i in node.get("inputs", []) if i.get("link") is not None}
    if node.get("widgets_values_named"):
        return {k: v for k, v in node["widgets_values_named"].items() if k not in linked}
    widget_inputs = {i["name"] for i in node.get("inputs", []) if i.get("widget")}
    values = iter(node.get("widgets_values", []))
    result = {}
    def consume(inputs, prefix=""):
        for section in ("required", "optional"):
            for key, spec in inputs.get(section, {}).items():
                name = prefix + key
                if name in linked and name not in widget_inputs:
                    continue
                kind = spec[0]
                options = spec[1] if len(spec) > 1 else {}
                if options.get("forceInput") or not (isinstance(kind, list) or kind in ("INT", "FLOAT", "STRING", "BOOLEAN", "COMBO", "COMFY_DYNAMICCOMBO_V3")):
                    continue
                try:
                    value = next(values)
                    if options.get("control_after_generate"):
                        next(values)
                except StopIteration:
                    return
                if name not in linked:
                    result[name] = value
                if kind == "COMFY_DYNAMICCOMBO_V3":
                    for option in options["options"]:
                        if option["key"] == value:
                            consume(option["inputs"], name + ".")
                            break
    consume(schema.get("input", {}))
    return result


def active_inputs(inputs, values, prefix=""):
    for section in ("required", "optional"):
        for key, spec in inputs.get(section, {}).items():
            name = prefix + key
            yield name, spec, section == "required"
            if spec[0] == "COMFY_DYNAMICCOMBO_V3":
                for option in spec[1]["options"]:
                    if option["key"] == values.get(name):
                        yield from active_inputs(option["inputs"], values, name + ".")
                        break


def check_workflow(workflow, schemas, subgraph_ids=None):
    issues = []
    notes = []
    ui = "nodes" in workflow
    nodes = workflow["nodes"] if ui else [dict(v, id=k, type=v["class_type"]) for k, v in workflow.items()]
    ids = {str(n["id"]) for n in nodes}
    if len(ids) != len(nodes):
        issues.append("Duplicate node ids")
    subgraphs = workflow.get("definitions", {}).get("subgraphs", [])
    subgraph_ids = set(subgraph_ids or ()) | {s["id"] for s in subgraphs}
    for node in nodes:
        if node.get("mode", 0) in (2, 4):
            notes.append(f"Node {node['id']} is muted/bypassed; execution graph not validated")
            continue
        kind = node["type"]
        if kind in ("Note", "MarkdownNote", "Reroute") or kind in subgraph_ids:
            continue
        schema = schemas.get(kind)
        if schema is None:
            issues.append(f"Node {node['id']}: missing node type {kind}")
            continue
        values = widget_values(node, schema) if ui else node["inputs"]
        for name, spec, required in active_inputs(schema.get("input", {}), values):
            empty_autogrow = spec[0] == "COMFY_AUTOGROW_V3" and spec[1]["template"].get("min", 1) == 0
            if not ui and required and name not in values and not empty_autogrow:
                issues.append(f"Node {node['id']} {name}: missing required input")
            value = values.get(name)
            if value is None:
                continue
            if isinstance(value, str) and "{{" in value:
                notes.append(f"Node {node['id']} {name}: template input must be supplied")
            choices = spec[0] if isinstance(spec[0], list) else None
            if spec[0] == "COMBO":
                choices = spec[1]["options"]
            elif spec[0] == "COMFY_DYNAMICCOMBO_V3":
                choices = [option["key"] for option in spec[1]["options"]]
            if choices is not None and not isinstance(value, list) and value not in choices and not (isinstance(value, str) and "{{" in value):
                issues.append(f"Node {node['id']} {name}: unavailable choice {value!r}")
            if name == "device" and value == "default" and kind == "CLIPLoader":
                notes.append(f"Node {node['id']}: GPU text encoding needs a runtime memory test")
        if schema.get("api_node") or "anthropic" in kind.lower() or "claude" in kind.lower():
            notes.append(f"Node {node['id']}: external API/credentials; not executed by this audit")
        if not ui:
            for name, value in values.items():
                if isinstance(value, list) and len(value) == 2 and isinstance(value[1], int) and str(value[0]) not in ids:
                    issues.append(f"Node {node['id']} {name}: missing source node {value[0]}")
    if ui:
        boundary_ids = {str(workflow[key]["id"]) for key in ("inputNode", "outputNode") if key in workflow}
        for link in workflow.get("links", []):
            if isinstance(link, dict):
                link_id, source, target = link["id"], link["origin_id"], link["target_id"]
            elif isinstance(link, list) and len(link) >= 6:
                link_id, source, target = link[0], link[1], link[3]
            else:
                issues.append("Malformed link record")
                continue
            if str(source) not in ids | boundary_ids or str(target) not in ids | boundary_ids:
                issues.append(f"Link {link_id}: missing endpoint")
        for subgraph in subgraphs:
            inner_issues, inner_notes = check_workflow(subgraph, schemas, subgraph_ids)
            issues.extend(f"Subgraph {subgraph['id']}: {issue}" for issue in inner_issues)
            notes.extend(inner_notes)
            notes.append("Subgraph socket types require frontend validation")
    z_image = any(n["type"] == "UNETLoader" and "z_image" in str(n.get("widgets_values", n.get("inputs", {}))) for n in nodes)
    if z_image:
        for node in nodes:
            if node["type"] == "VAELoader" and "pixel_space" in str(node.get("widgets_values", node.get("inputs", {}))):
                issues.append(f"Node {node['id']}: pixel_space is not a Z-Image latent decoder; use ae.safetensors")
    return issues, sorted(set(notes))


def ui_matches_prompt(workflow, prompt, schemas):
    if workflow.get("definitions", {}).get("subgraphs"):
        return False
    expected = {}
    if len({str(n["id"]) for n in workflow["nodes"]}) != len(workflow["nodes"]):
        return False
    for node in workflow["nodes"]:
        if node["type"] in ("Note", "MarkdownNote"):
            continue
        if node.get("mode", 0) != 0 or node["type"] not in schemas:
            return False
        expected[str(node["id"])] = {"class_type": node["type"], "inputs": widget_values(node, schemas[node["type"]])}
    nodes = {str(n["id"]): n for n in workflow["nodes"]}
    for link in workflow.get("links", []):
        if not isinstance(link, list) or len(link) < 6:
            return False
        _, source, slot, target, target_slot, *_ = link
        name = nodes[str(target)]["inputs"][target_slot]["name"]
        expected[str(target)]["inputs"][name] = [str(source), slot]
    observed = {str(k): {"class_type": v["class_type"], "inputs": v["inputs"]} for k, v in prompt.items()}
    return expected == observed


def runtime_receipts(history, schemas):
    receipts = []
    for prompt_id, item in history.items():
        prompt = item["prompt"]
        status = item.get("status", {})
        messages = status.get("messages", [])
        errors = [data for kind, data in messages if kind in ("execution_error", "execution_interrupted")]
        node_errors = [node_id for node_id, output in item.get("outputs", {}).items() if any(output.get("error", []))]
        success = status.get("completed") and status.get("status_str") == "success" and not errors
        if not success and not errors:
            continue
        workflow = prompt[3].get("extra_pnginfo", {}).get("workflow")
        targets = {str(n) for n in prompt[4]} if len(prompt) > 4 else set()
        outputs = {str(k) for k, node in prompt[2].items() if schemas.get(node["class_type"], {}).get("output_node")}
        complete = bool(outputs) and outputs <= targets
        receipt = {
            "prompt_id": prompt_id, "result": "error" if node_errors or not success else ("success" if complete else "partial_success"),
            "execution_targets": sorted(targets),
            "timestamp_ms": max((data.get("timestamp", 0) for _, data in messages), default=0),
            "fingerprints": [fingerprint(prompt[2])],
            "outputs": [image for output in item.get("outputs", {}).values() for image in output.get("images", [])],
        }
        if workflow and "nodes" in workflow:
            receipt["metadata_fingerprint"] = fingerprint(workflow)
            if ui_matches_prompt(workflow, prompt[2], schemas):
                receipt["fingerprints"].append(receipt["metadata_fingerprint"])
        if errors:
            receipt["error"] = {k: errors[-1].get(k) for k in ("node_id", "node_type", "exception_type")}
        if node_errors:
            receipt["node_errors"] = node_errors
        receipts.append(receipt)
    return receipts


def build_report(paths, schemas, history, previous=None):
    previous = previous if previous and previous.get("version") == 3 else {}
    receipts = {r["prompt_id"]: r for r in previous.get("runtime_receipts", [])}
    evidence_issues = []
    for prompt_id, item in history.items():
        try:
            receipts.update({r["prompt_id"]: r for r in runtime_receipts({prompt_id: item}, schemas)})
        except (ValueError, KeyError, TypeError, IndexError, AttributeError):
            evidence_issues.append(f"Skipped malformed history entry {prompt_id}")
    rows = []
    for path in paths:
        row = {"path": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)}
        try:
            workflow = json.loads(path.read_text())
            digest = fingerprint(workflow)
            issues, notes = check_workflow(workflow, schemas)
        except (ValueError, KeyError, TypeError, IndexError, AttributeError) as error:
            row.update(static="failed", issues=[f"Invalid workflow: {error}"], notes=[], runtime="unverified")
        else:
            matches = sorted((r for r in receipts.values() if digest in r["fingerprints"]), key=lambda r: r["timestamp_ms"])
            static = "failed" if issues else "needs_inputs" if any("template input must be supplied" in n for n in notes) else "preflight_pass"
            row.update(fingerprint=digest, static=static, issues=issues,
                       notes=notes, runtime=matches[-1]["result"] if matches else "unverified")
            if matches:
                row["last_run"] = matches[-1]
            else:
                related = sorted((r for r in receipts.values() if r.get("metadata_fingerprint") == digest), key=lambda r: r["timestamp_ms"])
                if related:
                    row["related_run"] = related[-1]
                    row["notes"].append("Run attached this UI graph, but UI/API correspondence is unverified")
        rows.append(row)
    return {
        "version": 3,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "scope": "Local node/choice/link preflight; no execution. Runtime receipts match exact graph settings, not current environment or output quality.",
        "evidence_issues": evidence_issues,
        "workflows": rows, "runtime_receipts": sorted(receipts.values(), key=lambda r: r["timestamp_ms"]),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8188)
    parser.add_argument("--output", type=Path, default=ROOT / "user/workflow-health.json")
    args = parser.parse_args()
    def get(route):
        connection = HTTPConnection("127.0.0.1", args.port, timeout=30)
        try:
            connection.request("GET", route)
            response = connection.getresponse()
            if response.status != 200:
                raise RuntimeError(f"Local server returned HTTP {response.status} for {route}")
            return json.load(response)
        finally:
            connection.close()
    schemas = get("/object_info")
    history = get("/history")
    paths = sorted((ROOT / "user/default/workflows").rglob("*.json"))
    paths += [ROOT / "default_workflow.json"]
    paths += sorted((ROOT / "studio/templates").glob("*.json"))
    previous = json.loads(args.output.read_text()) if args.output.exists() else None
    report = build_report(paths, schemas, history, previous)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    candidate = args.output.with_suffix(".json.tmp")
    candidate.write_text(json.dumps(report, indent=2) + "\n")
    candidate.replace(args.output)
    for row in report["workflows"]:
        print(f"{row['static']:14} runtime={row['runtime']:10} {row['path']}")
        for issue in row["issues"]:
            print(f"  {issue}")
    print(f"Report: {args.output}")
    return int(any(row["static"] == "failed" or row["runtime"] == "error" for row in report["workflows"]))


if __name__ == "__main__":
    raise SystemExit(main())
