"""Resolve Visualizer package changes against the ComfyUI runtime lock."""

import argparse
import fcntl
from importlib.metadata import distributions
from pathlib import Path
import subprocess
import tempfile
import tomllib

from packaging.markers import Marker
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import Version

from package_review import active_node_paths, constraints, read_declarations


ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv/bin/python"
MANIFEST = ROOT / "pyproject.toml"
LOCK = ROOT / "uv.lock"
GROUP = "workspace"
MANAGER_REPAIRS = {"comfy", "opencv-python", "opencv-contrib-python", "opencv-python-headless",
                   "opencv-contrib-python-headless"}


def uv(*args):
    subprocess.run(["uv", "--system-certs", *args], cwd=ROOT, check=True)


def requirements(entries):
    return {canonicalize_name(req.name): req for req in map(Requirement, entries)}


def edit_manifest(stage, config, action, name, version, installed):
    groups = config["dependency-groups"]
    editable = requirements(groups[GROUP])
    protected = requirements(config["project"]["dependencies"] + groups["dev"])
    protected.update(requirements(config["tool"]["uv"]["constraint-dependencies"]))
    if name in protected or name in MANAGER_REPAIRS:
        raise ValueError(f"{name} is maintained by the ComfyUI runtime manifest.")
    if action == "remove":
        if name not in editable:
            raise ValueError(f"{name} is outside the editable workspace group.")
        uv("remove", "--project", stage, "--python", PYTHON, "--group", GROUP, "--no-sync", name)
        return

    requirement = editable.get(name, Requirement(name))
    if requirement.url or requirement.marker:
        raise ValueError(f"{name} has a custom source or marker. Edit pyproject.toml directly.")
    current = installed.get(name)
    if current and current.read_text("direct_url.json"):
        raise ValueError(f"{name} uses a custom installed source. Keep its source in pyproject.toml.")
    extras = f"[{','.join(sorted(requirement.extras))}]" if requirement.extras else ""
    spec = f"{name}{extras}=={Version(version)}" if version else f"{name}{extras}"
    uv("add", "--project", stage, "--python", PYTHON, "--group", GROUP,
       "--no-sync", "--bounds", "exact", spec)


def check_plan(export, installed, editable_name, config):
    planned = {}
    for package in tomllib.loads(export.read_text())["packages"]:
        if "marker" not in package or Marker(package["marker"]).evaluate():
            planned[canonicalize_name(package["name"])] = Version(package["version"])
    for name, package in installed.items():
        if name != editable_name and name in planned and Version(package.version) != planned[name]:
            raise ValueError(f"Resolution would change {name} from {package.version} to {planned[name]}.")

    changes = {name: version for name, version in planned.items()
               if name not in installed or Version(installed[name].version) != version}
    if changes:
        # Some custom nodes are loaded directly from Git and have no installed metadata.
        declarations = read_declarations(ROOT, config, active_node_paths(ROOT), set())
        for name, version in changes.items():
            for blocker in constraints(name, version, declarations, {}):
                if blocker["role"] == "node":
                    raise ValueError(f"{blocker['source']} requires {name}{blocker['specifier']}, but uv selected {version}.")

    # Check the resulting environment, including node-pack dependencies outside the lock.
    effective = {name: Version(package.version) for name, package in installed.items()} | planned
    for name, package in installed.items():
        if effective[name] != Version(package.version):
            continue
        for raw in package.requires or []:
            requirement = Requirement(raw)
            if requirement.marker and not requirement.marker.evaluate():
                continue
            dependency = effective.get(canonicalize_name(requirement.name))
            if dependency is None:
                raise ValueError(f"{name} needs {requirement}, which the resulting environment would still lack.")
            if not requirement.specifier.contains(dependency, prereleases=True):
                raise ValueError(f"{name} needs {requirement}, but the resulting environment would have {dependency}.")


def manage(action, name, version):
    manifest_before = MANIFEST.read_bytes()
    lock_before = LOCK.read_bytes() if LOCK.exists() else None
    config = tomllib.loads(manifest_before.decode())
    if config.get("tool", {}).get("uv", {}).get("package") is not False:
        raise ValueError("Restore the ComfyUI uv manifest before running migration.")
    if action != "migrate":
        uv("pip", "check", "--python", PYTHON)
    installed = {canonicalize_name(p.metadata["Name"]): p for p in distributions()}
    with tempfile.TemporaryDirectory(prefix="resolution-", dir=ROOT / ".codex") as directory:
        stage = Path(directory)
        (stage / MANIFEST.name).write_bytes(manifest_before)
        if lock_before is not None:
            (stage / LOCK.name).write_bytes(lock_before)

        if action == "migrate":
            uv("lock", "--project", stage, "--python", PYTHON)
        else:
            edit_manifest(stage, config, action, name, version, installed)

        export = stage / "pylock.toml"
        uv("export", "--project", stage, "--locked", "--format", "pylock.toml",
           "--no-emit-project", "--output-file", export, "--quiet")
        check_plan(export, installed, name, config)
        if (MANIFEST.read_bytes() != manifest_before
                or (LOCK.read_bytes() if LOCK.exists() else None) != lock_before):
            raise ValueError("The package files changed while uv was resolving. Retry the action.")

        uv("pip", "install", "--python", PYTHON, "--no-deps", "--strict",
           "--link-mode", "copy", "--preview-features", "pylock", "-r", export)
        uv("pip", "check", "--python", PYTHON)
        for path, previous in ((MANIFEST, manifest_before), (LOCK, lock_before)):
            candidate = stage / path.name
            if candidate.read_bytes() != previous:
                candidate.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("migrate", "set", "remove"))
    parser.add_argument("name", nargs="?")
    parser.add_argument("version", nargs="?")
    args = parser.parse_args()
    if args.action != "migrate":
        if not args.name:
            parser.error("a package name is required")
        try:
            args.name = canonicalize_name(args.name, validate=True)
        except ValueError as error:
            parser.error(str(error))
    elif args.name:
        parser.error("migrate takes no package name")

    with (ROOT / ".codex/uv-workspace.lock").open("a") as guard:
        try:
            fcntl.flock(guard, fcntl.LOCK_EX | fcntl.LOCK_NB)
            manage(args.action, args.name, args.version)
        except (OSError, ValueError, subprocess.CalledProcessError) as error:
            parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
