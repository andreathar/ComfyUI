"""Check installed custom-node Git repositories against the local stack lock."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


SCHEMA_VERSION = 2
LOCK_PATH = Path(".codex/custom_nodes.lock.json")


def _git(path, *args):
    env = os.environ.copy()
    env["GIT_OPTIONAL_LOCKS"] = "0"
    result = subprocess.run(
        ["git", "-c", "core.fsmonitor=false", "-c", "core.untrackedCache=false", "-C", str(path), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        check=False,
    )
    if result.returncode:
        return None
    return result.stdout.rstrip("\n")


def _relative_path(root, path):
    return Path(os.path.relpath(str(path), str(root))).as_posix()


def _repository_metadata(root, path, install_sources):
    remotes = _git(path, "remote") or ""
    origin = _git(path, "remote", "get-url", "origin") if "origin" in remotes.splitlines() else None
    status = _git(path, "status", "--porcelain=v1", "--untracked-files=all") or ""
    return {
        "path": _relative_path(root, path),
        "root": path,
        "origin": origin,
        "head": _git(path, "rev-parse", "HEAD"),
        "tag": _git(path, "describe", "--exact-match", "--tags", "HEAD"),
        "installed_paths": sorted(install_sources),
        "install_sources": dict(sorted(install_sources.items())),
        "dirty": status.splitlines(),
    }


def discover_custom_nodes(root):
    """Return distinct Git roots backing active, direct custom_nodes entries."""
    root = Path(root).resolve()
    install_dir = root / "custom_nodes"
    roots = {}
    if not install_dir.is_dir():
        return {}

    for installed_path in sorted(install_dir.iterdir()):
        if installed_path.name == "__pycache__" or installed_path.name.endswith(".disabled") or not installed_path.is_dir():
            continue
        git_root = _git(installed_path.resolve(), "rev-parse", "--show-toplevel")
        if git_root is None:
            continue
        git_root = Path(git_root).resolve()
        if git_root == root:
            continue
        installed_relative = _relative_path(root, installed_path)
        source_relative = _relative_path(git_root, installed_path.resolve())
        roots.setdefault(git_root, {})[installed_relative] = source_relative

    return {
        path: _repository_metadata(root, path, installed_paths)
        for path, installed_paths in roots.items()
    }


def _valid_entries(manifest, findings):
    if not isinstance(manifest, dict) or manifest.get("schema_version") != SCHEMA_VERSION:
        findings.append(f"INVALID LOCK: expected schema_version {SCHEMA_VERSION}")
        return [], {}
    entries = manifest.get("repositories")
    if not isinstance(entries, list):
        findings.append("INVALID LOCK: repositories must be a list")
        return [], {}

    install_sources = manifest.get("install_sources")
    if not isinstance(install_sources, dict) or not all(
        isinstance(path, str) and path and isinstance(source, str) and source and not Path(source).is_absolute()
        for path, source in install_sources.items()
    ):
        findings.append("INVALID LOCK: install_sources must map install paths to relative source directories")
        install_sources = {}

    valid = []
    seen_paths = set()
    for index, entry in enumerate(entries):
        label = f"repositories[{index}]"
        if not isinstance(entry, dict):
            findings.append(f"INVALID LOCK: {label} must be an object")
            continue
        path = entry.get("path")
        head = entry.get("head")
        installed_paths = entry.get("installed_paths")
        if not isinstance(path, str) or not path or Path(path).is_absolute():
            findings.append(f"INVALID LOCK: {label}.path must be a relative path")
            continue
        if not isinstance(head, str) or not head:
            findings.append(f"INVALID LOCK: {label}.head must be a commit SHA")
            continue
        if not isinstance(installed_paths, list) or not installed_paths or not all(
            isinstance(item, str) and item for item in installed_paths
        ):
            findings.append(f"INVALID LOCK: {label}.installed_paths must be a non-empty list of paths")
            continue
        if path in seen_paths:
            findings.append(f"INVALID LOCK: duplicate repository path {path}")
            continue
        if entry.get("origin") is not None and not isinstance(entry.get("origin"), str):
            findings.append(f"INVALID LOCK: {label}.origin must be a URL or null")
            continue
        if entry.get("tag") is not None and not isinstance(entry.get("tag"), str):
            findings.append(f"INVALID LOCK: {label}.tag must be a tag or null")
            continue
        seen_paths.add(path)
        valid.append(entry)
    expected_installs = {path for entry in valid for path in entry["installed_paths"]}
    for path in sorted(expected_installs - install_sources.keys()):
        findings.append(f"INVALID LOCK: install_sources has no source directory for {path}")
    for path in sorted(install_sources.keys() - expected_installs):
        findings.append(f"INVALID LOCK: install_sources has an unknown install path {path}")
    return valid, install_sources


def check_custom_nodes(root, manifest):
    """Return (active repository count, findings) without changing Git state."""
    root = Path(root).resolve()
    findings = []
    entries, install_sources = _valid_entries(manifest, findings)
    active = discover_custom_nodes(root)
    expected_by_root = {}

    install_dir = root / "custom_nodes"
    for installed_path in sorted(install_dir.iterdir()) if install_dir.is_dir() else []:
        if installed_path.name == "__pycache__" or installed_path.name.endswith(".disabled"):
            continue
        git_root = _git(installed_path.resolve(), "rev-parse", "--show-toplevel")
        if git_root and Path(git_root).resolve() != root:
            continue
        relative = _relative_path(root, installed_path)
        if _git(root, "ls-files", "--error-unmatch", "--", f"{relative}/__init__.py") is None:
            if (installed_path / "__init__.py").is_file():
                findings.append(f"UNVERSIONED NODE PACK: {relative}")
            continue
        status = _git(root, "status", "--porcelain=v1", "--untracked-files=all", "--", relative) or ""
        for line in status.splitlines():
            findings.append(f"DIRTY PARENT NODE PACK: {relative}: {line}")
        if not (installed_path / "__init__.py").is_file():
            findings.append(f"MISSING NODE INITIALIZER: {relative}/__init__.py")

    for entry in entries:
        expected_path = (root / entry["path"]).resolve()
        actual_git_root = _git(expected_path, "rev-parse", "--show-toplevel") if expected_path.exists() else None
        if actual_git_root is None:
            findings.append(f"MISSING CHECKOUT: {entry['path']}")
            continue
        actual_git_root = Path(actual_git_root).resolve()
        if actual_git_root != expected_path:
            findings.append(
                f"PATH MISMATCH: lock path {entry['path']} resolves to Git root "
                f"{_relative_path(root, actual_git_root)}"
            )
        expected_by_root[expected_path] = entry
        repository = active.get(actual_git_root)
        if repository is None:
            findings.append(f"MISSING ACTIVE REPOSITORY: {entry['path']} is not installed under custom_nodes/")
            continue

        if repository["head"] != entry["head"]:
            findings.append(
                f"HEAD DRIFT: {repository['path']} locked={entry['head']} actual={repository['head']}"
            )
        if repository["origin"] is None:
            findings.append(f"NO ORIGIN: {repository['path']} has no origin remote; source cannot be verified")
        if repository["origin"] != entry.get("origin"):
            findings.append(
                f"ORIGIN MISMATCH: {repository['path']} locked={entry.get('origin')!r} "
                f"actual={repository['origin']!r}"
            )
        if entry.get("tag") is not None and repository["tag"] != entry["tag"]:
            findings.append(
                f"TAG DRIFT: {repository['path']} locked={entry['tag']!r} actual={repository['tag']!r}"
            )

        expected_installs = set(entry["installed_paths"])
        actual_installs = set(repository["installed_paths"])
        for missing in sorted(expected_installs - actual_installs):
            findings.append(f"MISSING INSTALLED PATH: {missing}")
        for extra in sorted(actual_installs - expected_installs):
            findings.append(f"UNLOCKED ACTIVE PATH: {extra} uses {repository['path']}")
        for installed_path in sorted(expected_installs & actual_installs):
            expected_source = install_sources.get(installed_path)
            actual_source = repository["install_sources"][installed_path]
            if expected_source != actual_source:
                findings.append(
                    f"SOURCE PATH MISMATCH: {installed_path} locked={expected_source!r} actual={actual_source!r}"
                )

    for path, repository in active.items():
        if path not in expected_by_root:
            findings.append(
                f"EXTRA ACTIVE REPOSITORY: {repository['path']} "
                f"(installed at {', '.join(repository['installed_paths'])})"
            )
            for entry in entries:
                if repository["origin"] and repository["origin"] == entry.get("origin"):
                    findings.append(
                        f"PATH MISMATCH: origin {repository['origin']} is locked at {entry['path']} "
                        f"but active at {repository['path']}"
                    )
                    break
        if repository["origin"] is None and not any(
            finding.startswith(f"NO ORIGIN: {repository['path']} ") for finding in findings
        ):
            findings.append(f"NO ORIGIN: {repository['path']} has no origin remote; source cannot be verified")
        for status in repository["dirty"]:
            findings.append(f"DIRTY: {repository['path']}: {status}")

    return len(active), findings


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--lock", type=Path, help="lock JSON path (defaults to .codex/custom_nodes.lock.json)")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    lock_path = args.lock or root / LOCK_PATH

    try:
        with lock_path.open(encoding="utf-8") as lock_file:
            manifest = json.load(lock_file)
    except (OSError, json.JSONDecodeError) as error:
        print(f"ERROR: cannot read lock {lock_path}: {error}", file=sys.stderr)
        return 2

    repository_count, findings = check_custom_nodes(root, manifest)
    print(f"Checked {repository_count} active custom-node Git repositories against {lock_path}")
    if findings:
        for finding in findings:
            print(f"- {finding}")
        print(f"RESULT: NOT REPRODUCIBLE ({len(findings)} finding(s))")
        return 1
    print("RESULT: reproducible")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
