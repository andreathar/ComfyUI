import hashlib
import importlib.util
import os
from pathlib import Path
import subprocess

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "check_custom_nodes", PROJECT_ROOT / ".codex/check_custom_nodes.py"
)
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)


def git(path, *args):
    env = os.environ.copy()
    env["GIT_OPTIONAL_LOCKS"] = "0"
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["GIT_CONFIG_GLOBAL"] = os.devnull
    return subprocess.run(
        ["git", "-C", str(path), *args],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    ).stdout.strip()


def make_repository(root, relative_path="custom_nodes/plugin", origin="https://example.invalid/plugin.git"):
    repository = root / relative_path
    repository.mkdir(parents=True)
    env = os.environ.copy()
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["GIT_CONFIG_GLOBAL"] = os.devnull
    subprocess.run(["git", "init", "-q", str(repository)], check=True, env=env)
    git(repository, "config", "user.name", "Test User")
    git(repository, "config", "user.email", "test@example.invalid")
    (repository / "tracked.txt").write_text("initial\n", encoding="utf-8")
    git(repository, "add", "tracked.txt")
    git(repository, "commit", "-q", "-m", "initial")
    if origin is not None:
        git(repository, "remote", "add", "origin", origin)
    return repository


def lock_for(root, repository, installed_paths=None, origin="https://example.invalid/plugin.git"):
    relative_path = Path(os.path.relpath(repository, root)).as_posix()
    installed_paths = installed_paths or ["custom_nodes/plugin"]
    return {
        "schema_version": 1,
        "repositories": [
            {
                "path": relative_path,
                "origin": origin,
                "head": git(repository, "rev-parse", "HEAD"),
                "tag": None,
                "installed_paths": installed_paths,
            }
        ],
    }


def check(root, manifest):
    return checker.check_custom_nodes(root, manifest)


def test_clean_checkout_matches_lock(tmp_path):
    root = tmp_path / "comfyui"
    repository = make_repository(root)
    manifest = lock_for(root, repository)

    count, findings = check(root, manifest)

    assert count == 1
    assert findings == []


def test_changed_head_is_reported(tmp_path):
    root = tmp_path / "comfyui"
    repository = make_repository(root)
    manifest = lock_for(root, repository)
    (repository / "tracked.txt").write_text("changed\n", encoding="utf-8")
    git(repository, "add", "tracked.txt")
    git(repository, "commit", "-q", "-m", "change")

    _, findings = check(root, manifest)

    assert any(finding.startswith("HEAD DRIFT:") for finding in findings)


def test_tracked_and_untracked_changes_are_reported(tmp_path):
    root = tmp_path / "comfyui"
    repository = make_repository(root)
    manifest = lock_for(root, repository)
    (repository / "tracked.txt").write_text("dirty\n", encoding="utf-8")
    (repository / "untracked.txt").write_text("untracked\n", encoding="utf-8")
    index = repository / ".git/index"
    index_digest = hashlib.sha256(index.read_bytes()).hexdigest()

    _, findings = check(root, manifest)

    assert any("DIRTY:" in finding and "tracked.txt" in finding for finding in findings)
    assert any("DIRTY:" in finding and "?? untracked.txt" in finding for finding in findings)
    assert hashlib.sha256(index.read_bytes()).hexdigest() == index_digest


def test_missing_checkout_is_reported(tmp_path):
    root = tmp_path / "comfyui"
    root.mkdir()
    manifest = {
        "schema_version": 1,
        "repositories": [
            {
                "path": "custom_nodes/missing",
                "origin": "https://example.invalid/missing.git",
                "head": "1" * 40,
                "tag": None,
                "installed_paths": ["custom_nodes/missing"],
            }
        ],
    }

    _, findings = check(root, manifest)

    assert "MISSING CHECKOUT: custom_nodes/missing" in findings


def test_shared_repository_root_is_counted_once_for_multiple_install_paths(tmp_path):
    root = tmp_path / "comfyui"
    repository = make_repository(root, "vendor/shared")
    install_dir = root / "custom_nodes"
    install_dir.mkdir()
    (install_dir / "plugin-one").symlink_to(repository, target_is_directory=True)
    (install_dir / "plugin-two").symlink_to(repository, target_is_directory=True)
    manifest = lock_for(
        root,
        repository,
        ["custom_nodes/plugin-one", "custom_nodes/plugin-two"],
    )

    count, findings = check(root, manifest)

    assert count == 1
    assert findings == []


def test_origin_and_installed_path_mismatch_are_reported(tmp_path):
    root = tmp_path / "comfyui"
    repository = make_repository(root)
    manifest = lock_for(root, repository, ["custom_nodes/old-name"], "https://example.invalid/old.git")

    _, findings = check(root, manifest)

    assert any(finding.startswith("ORIGIN MISMATCH:") for finding in findings)
    assert "MISSING INSTALLED PATH: custom_nodes/old-name" in findings
    assert "UNLOCKED ACTIVE PATH: custom_nodes/plugin uses custom_nodes/plugin" in findings


def test_repository_without_origin_is_explicitly_reported(tmp_path):
    root = tmp_path / "comfyui"
    repository = make_repository(root, origin=None)
    manifest = lock_for(root, repository, origin=None)

    _, findings = check(root, manifest)

    assert any(finding.startswith("NO ORIGIN:") for finding in findings)


def test_extra_active_repository_is_reported(tmp_path):
    root = tmp_path / "comfyui"
    make_repository(root)
    manifest = {"schema_version": 1, "repositories": []}

    count, findings = check(root, manifest)

    assert count == 1
    assert any(finding.startswith("EXTRA ACTIVE REPOSITORY:") for finding in findings)


def test_disabled_repository_is_not_active(tmp_path):
    root = tmp_path / "comfyui"
    make_repository(root, "custom_nodes/plugin.disabled")
    manifest = {"schema_version": 1, "repositories": []}

    count, findings = check(root, manifest)

    assert count == 0
    assert findings == []