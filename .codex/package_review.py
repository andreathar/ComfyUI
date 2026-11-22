"""Review the ComfyUI workstation's dependency inventory or one package candidate."""

import argparse
from collections import Counter, defaultdict
from importlib.metadata import distributions, packages_distributions
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tomllib

from packaging.markers import Marker
from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name, InvalidWheelFilename, parse_wheel_filename
from packaging.version import Version

from check_custom_nodes import LOCK_PATH, check_custom_nodes


ROOT = Path(__file__).resolve().parents[1]
CUDA_STACK = {"torch", "torchvision", "torchaudio", "triton", "cuda-toolkit", "comfy-kitchen", "comfy-aimdo"}
BASELINE = "user/default/workflows/Balanced SD15 - RTX 3060.json"


def read_toml(path):
    return tomllib.loads(path.read_text())


def lock_packages(path):
    return {
        canonicalize_name(package["name"]): package
        for package in read_toml(path)["package"]
        if "virtual" not in package.get("source", {})
        and (not package.get("resolution-markers")
             or any(Marker(marker).evaluate() for marker in package["resolution-markers"]))
    }


def read_declarations(root, manifest, nodes, warnings):
    declarations = defaultdict(list)

    def add(values, path, role, consumer):
        for value in values:
            if not isinstance(value, str):
                continue
            try:
                requirement = Requirement(value)
            except InvalidRequirement:
                warnings.add(f"Skipped unsupported requirement syntax in {path}")
                continue
            declarations[canonicalize_name(requirement.name)].append((role, consumer, path, requirement))

    def read_requirements(path, role, consumer, boundary, visited):
        if path.resolve() in visited:
            return
        visited.add(path.resolve())
        display = str(path.relative_to(root) if path.is_relative_to(root) else path)
        for line in path.read_text().splitlines():
            line = line.partition(" #")[0].strip()
            if not line or line.startswith("#"):
                continue
            option, _, argument = line.partition(" ")
            if option in {"-r", "--requirement", "-c", "--constraint"}:
                include = (path.parent / argument.strip()).resolve()
                if include.is_relative_to(boundary) and include.is_file():
                    read_requirements(include, role, consumer, boundary, visited)
                else:
                    warnings.add(f"Skipped unavailable requirement include in {display}")
            else:
                if line.startswith(("./", "../")) and line.endswith(".whl"):
                    try:
                        wheel_name, wheel_version, _, _ = parse_wheel_filename(Path(line).name)
                    except InvalidWheelFilename:
                        warnings.add(f"Skipped invalid wheel filename in {display}")
                        continue
                    line = f"{wheel_name}=={wheel_version}"
                add([line], display, role, consumer)

    add(manifest.get("project", {}).get("dependencies", []), "pyproject.toml", "project", "ComfyUI")
    for group, values in manifest.get("dependency-groups", {}).items():
        add(values, "pyproject.toml", "group", group)
    add(manifest.get("tool", {}).get("uv", {}).get("constraint-dependencies", []),
        "pyproject.toml", "constraint", "ComfyUI")
    for relative in ("requirements.txt", "manager_requirements.txt", "agent_requirements.txt",
                     "tests-unit/requirements.txt", ".codex/requirements.lock.txt"):
        path = root / relative
        if path.is_file():
            role = "historical" if relative.startswith(".codex/") else "compatibility"
            read_requirements(path, role, relative, root, set())
    for node in nodes:
        path = node / "pyproject.toml"
        if path.is_file():
            add(read_toml(path).get("project", {}).get("dependencies", []),
                str(path.relative_to(root)), "node", node.name)
        path = node / "requirements.txt"
        if path.is_file():
            read_requirements(path, "node", node.name, node.resolve(), set())
    return declarations


def active(requirement):
    return requirement.marker is None or requirement.marker.evaluate()


def describe(row):
    role, consumer, source, requirement = row
    return {
        "role": role, "consumer": consumer, "source": source,
        "specifier": str(requirement.specifier), "active_marker": active(requirement),
        "marker": str(requirement.marker) if requirement.marker else None,
        "direct_source": requirement.url is not None,
    }


def constraints(name, version, declarations, reverse, replacing=()):
    rows = [row for row in declarations.get(name, []) if row[0] not in {"compatibility", "historical"}]
    rows.extend(row for row in reverse.get(name, []) if row[1] not in replacing)
    return [
        {"dependency": name, "candidate": str(version), **describe(row)} for row in rows
        if active(row[3]) and not row[3].specifier.contains(version, prereleases=True)
    ]


def affected_workflows(root, workflows, schemas, affected_packs, shared_runtime):
    if not workflows:
        return []
    from studio.workflow_catalogue import graph_nodes, payloads

    reports = []
    for path in workflows:
        nodes = {
            node["type"] for _, kind, graph in payloads(json.loads(path.read_text())) if kind in {"api", "ui"}
            for _, node in graph_nodes(graph, kind) if node.get("mode", 0) not in (2, 4)
        }
        matched = []
        if schemas is not None:
            for name in sorted(nodes):
                provider = schemas.get(name, {}).get("python_module") or ""
                if any(provider == pack or provider.startswith(pack + ".") for pack in affected_packs):
                    matched.append(name)
        reports.append({
            "path": str(path.relative_to(root) if path.is_relative_to(root) else path),
            "nodes": matched,
            "unmapped_types": sorted(name for name in nodes if not (schemas or {}).get(name, {}).get("python_module")),
            "shared_runtime": shared_runtime,
            "status": "matched providers" if matched else "candidate smoke test" if shared_runtime else "unverified",
        })
    return reports


def build_report(root, distributions_, name=None, version=None, *, reason=None, evidence=None,
                 workflows=(), schemas=None, imports=None, resolve=False, offline=False):
    manifest = read_toml(root / "pyproject.toml")
    locked = lock_packages(root / "uv.lock")
    installed = defaultdict(list)
    reverse = defaultdict(list)
    warnings = set()
    for distribution in distributions_:
        consumer = canonicalize_name(distribution.name)
        installed[consumer].append(distribution.version)
        for value in distribution.requires or []:
            try:
                requirement = Requirement(value)
            except InvalidRequirement:
                warnings.add(f"Skipped invalid installed metadata for {consumer}")
                continue
            reverse[canonicalize_name(requirement.name)].append(("installed", consumer, "Requires-Dist", requirement))

    node_dir = root / "custom_nodes"
    nodes = sorted(path for path in node_dir.iterdir()
                   if path.is_dir() and not path.name.endswith(".disabled")
                   and not path.name.startswith(".") and path.name != "__pycache__") if node_dir.is_dir() else []
    declarations = read_declarations(root, manifest, nodes, warnings)
    repositories, findings = check_custom_nodes(root, json.loads((root / LOCK_PATH).read_text()))
    overlaps = {module: providers for module, projects in (imports or {}).items()
                if len(providers := sorted({canonicalize_name(project) for project in projects})) > 1}
    inventory = {}
    for package in sorted(installed.keys() | locked.keys() | declarations.keys()):
        entries = declarations[package]
        owners = sorted({row[1] for row in entries if row[0] in {"project", "group", "node"} and active(row[3])})
        parents = sorted({row[1] for row in reverse[package] if active(row[3])})
        versions = sorted(installed[package])
        locked_version = locked.get(package, {}).get("version")
        inventory[package] = {"installed": versions, "locked": locked_version, "declared_by": owners,
                              "required_by": parents}
    outside = sorted(package for package, versions in installed.items() if versions and package not in locked)
    report = {
        "counts": {"installed": sum(bool(versions) for versions in installed.values()),
                   "locked": len(locked), "outside_lock": len(outside),
                   "outside_lock_without_detected_owner": sum(
                       not (inventory[p]["declared_by"] or inventory[p]["required_by"]) for p in outside)},
        "lock_drift": [p for p, row in inventory.items() if row["locked"] is not None
                       and [Version(v) for v in row["installed"]] != [Version(row["locked"])]],
        "multiple_installed_versions": sorted(p for p, versions in installed.items() if len(versions) > 1),
        "shared_import_names": overlaps,
        "custom_nodes": {"repositories": repositories,
                         "findings_by_kind": dict(sorted(Counter(line.split(":", 1)[0] for line in findings).items()))},
        "inventory": inventory,
        "coverage_notes": [
            "Active node-pack root manifests and installed metadata provide ownership leads. Check dynamic imports and optional features separately.",
            "Shared import names can include legitimate namespaces. No recorded owner does not establish that a distribution is unused.",
        ],
        "warnings": sorted(warnings),
    }
    if name is None:
        return report

    rows = declarations.get(name, [])
    affected = {name}
    pending = [name]
    while pending:
        for row in reverse.get(pending.pop(), []):
            if active(row[3]) and row[1] not in affected:
                affected.add(row[1])
                pending.append(row[1])
    packs = {row[1] for package in affected for row in declarations.get(package, [])
             if row[0] == "node" and active(row[3])}
    runtime = name in CUDA_STACK or name.startswith(("cuda-", "nvidia-")) or any(
        row[0] in {"project", "constraint"} and active(row[3])
        for package in affected for row in declarations.get(package, []))
    blockers = constraints(name, Version(version), declarations, reverse) if version else []
    decision = ("blocked" if blockers else "unmanaged" if name not in locked else
                "keep" if version and Version(version) == Version(locked[name]["version"]) else
                "needs-evidence" if not (version and reason and evidence) else "test")
    candidate = {
        "package": name, "version": version, "reason": reason, "evidence": evidence, "decision": decision,
        "blockers": blockers, "requirements": [describe(row) for row in rows + reverse.get(name, [])],
        "compatibility_files": [describe(row) for row in rows if row[0] in {"compatibility", "historical"}],
        "affected_packs": sorted(packs), "affected_installed_packages": sorted(affected - {name}),
        "affected_workflows": affected_workflows(root, workflows, schemas, {"custom_nodes." + pack for pack in packs}, runtime),
        "proposed_lock": {"status": "not resolved"},
        "tests": [
            "Build a separate candidate environment and verify its full dependency inventory.",
            "Run affected pack tests and verify their node registration and selected workflow behavior.",
        ] + ([f"Smoke-test {BASELINE}; compare the affected production workflow using controlled Brain Monitor runs."]
             if runtime else []),
    }
    if resolve:
        candidate["proposed_lock"] = resolve_candidate(root, candidate, offline)
        changes = {change["package"]: Version(change["after"])
                   for change in candidate["proposed_lock"].get("changes", []) if change["after"]}
        for package, candidate_version in changes.items():
            if package != name:
                candidate["blockers"].extend(constraints(package, candidate_version, declarations, reverse, changes))
        if candidate["blockers"]:
            candidate["decision"] = "blocked"
        elif candidate["proposed_lock"]["status"] == "resolution failed":
            candidate["decision"] = "resolution-failed"
        elif candidate["proposed_lock"]["status"] == "resolver did not select requested version":
            candidate["decision"] = "version-not-selected"
    report["candidate"] = candidate
    return report


def resolve_candidate(root, candidate, offline):
    if candidate["decision"] == "blocked":
        return {"status": "blocked by existing requirements"}
    if candidate["decision"] == "unmanaged":
        return {"status": "package is outside uv.lock"}
    manifest = read_toml(root / "pyproject.toml")
    config = manifest.get("tool", {}).get("uv", {})
    before = lock_packages(root / "uv.lock")
    # This copy intentionally has no workspace or local/editable package sources.
    sources = [source for item in config.get("sources", {}).values()
               for source in (item if isinstance(item, list) else [item])]
    if (config.get("package") is not False or "workspace" in config
            or any({"path", "workspace", "editable"} & source.keys() for source in sources)
            or any(set(package.get("source", {})) - {"registry", "url", "git"} for package in before.values())):
        return {"status": "requires a separate checkout to resolve local or workspace sources"}
    with tempfile.TemporaryDirectory(prefix="comfyui-uv-review-") as directory:
        stage = Path(directory)
        for file in ("pyproject.toml", "uv.lock"):
            shutil.copyfile(root / file, stage / file)
        result = subprocess.run(
            ["uv", "--system-certs", "lock", "--no-build", "--project", str(stage),
             "--python", sys.executable, "--upgrade-package", f"{candidate['package']}=={candidate['version']}",
             *(["--offline"] if offline else [])],
            cwd=stage, capture_output=True, text=True, check=False, timeout=120,
        )
        if result.returncode:
            return {"status": "resolution failed", "detail": result.stderr.strip()}
        after = lock_packages(stage / "uv.lock")
    target = after.get(candidate["package"], {}).get("version")
    if target is None or Version(target) != Version(candidate["version"]):
        return {"status": "resolver did not select requested version", "selected": target}

    def signature(entry):
        return entry.get("version"), entry.get("source", {})

    return {"status": "resolved in isolation",
            "changes": [{"package": name, "before": before.get(name, {}).get("version"),
                         "after": after.get(name, {}).get("version"),
                         "source_changed": before.get(name, {}).get("source") != after.get(name, {}).get("source")}
                        for name in sorted(before.keys() | after.keys())
                        if signature(before.get(name, {})) != signature(after.get(name, {}))]}


def render(report):
    counts = report["counts"]
    lines = [f"{counts['installed']} installed / {counts['locked']} locked / {counts['outside_lock']} outside uv.lock",
             f"{counts['outside_lock_without_detected_owner']} outside the lock with no detected owner",
             f"Locked version drift  {', '.join(report['lock_drift']) or 'none'}",
             f"Custom-node findings  {json.dumps(report['custom_nodes']['findings_by_kind'], sort_keys=True)}",
             "Shared import names  " + (", ".join(sorted(report["shared_import_names"])) or "none detected")]
    candidate = report.get("candidate")
    if candidate:
        package = candidate["package"]
        installed = ", ".join(report["inventory"].get(package, {}).get("installed", [])) or "not installed"
        lines.extend(["", f"{package}  {installed} → {candidate['version'] or 'unspecified'}  {candidate['decision']}"])
        if candidate["reason"]:
            lines.append(f"Reason  {candidate['reason']}")
        if candidate["evidence"]:
            lines.append(f"Evidence  {candidate['evidence']}")
        for row in candidate["blockers"]:
            lines.append(f"  {row['consumer']} requires {row['dependency']}{row['specifier']} "
                         f"(candidate {row['candidate']}, {row['source']})")
        lines.append("Affected node-pack declarations  " + (", ".join(candidate["affected_packs"]) or "none found"))
        for row in candidate["affected_workflows"]:
            lines.append(f"  {row['path']}  {row['status']}  {', '.join(row['nodes'])}")
        lines.append(f"Candidate lock  {candidate['proposed_lock']['status']}")
        for change in candidate["proposed_lock"].get("changes", []):
            source = " (source changed)" if change["source_changed"] else ""
            lines.append(f"  {change['package']}  {change['before']} → {change['after']}{source}")
        if detail := candidate["proposed_lock"].get("detail"):
            lines.append(detail)
        lines.extend(candidate["tests"])
    lines.extend(report["warnings"])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", nargs="?", type=lambda name: canonicalize_name(name, validate=True))
    parser.add_argument("version", nargs="?", type=Version)
    parser.add_argument("--reason")
    parser.add_argument("--evidence", help="Release, advisory, bug, or benchmark reference")
    parser.add_argument("--workflow", action="append", type=Path, default=[])
    parser.add_argument("--object-info", type=Path, help="Saved ComfyUI /object_info JSON")
    parser.add_argument("--resolve", action="store_true", help="Resolve an exact candidate in a temporary copy")
    parser.add_argument("--offline", action="store_true", help="Resolve using only cached package metadata")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.resolve and args.version is None:
        parser.error("--resolve requires PACKAGE VERSION")
    if any((args.reason, args.evidence, args.workflow, args.object_info)) and not args.package:
        parser.error("candidate options require PACKAGE")
    if args.workflow:
        sys.path.insert(0, str(ROOT))
    try:
        report = build_report(ROOT, distributions(), args.package, str(args.version) if args.version else None,
                              reason=args.reason, evidence=args.evidence, workflows=args.workflow,
                              schemas=json.loads(args.object_info.read_text()) if args.object_info else None,
                              imports=packages_distributions(), resolve=args.resolve, offline=args.offline)
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        parser.exit(1, f"{error}\n")
    sys.stdout.write((json.dumps(report, indent=2) if args.json else render(report)) + "\n")


if __name__ == "__main__":
    main()
