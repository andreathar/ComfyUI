import json
from importlib.metadata import distributions
from types import SimpleNamespace

import pytest

import package_review
import uv_workspace
from package_review import build_report


def test_outside_lock_consumer_blocks_upgrade_and_identifies_workflow(tmp_path):
    root = tmp_path
    site = root / "site"
    for name, version, dependency in [
        ("numpy", "2.3.2", ""),
        ("local-advisor", "1.0", "Requires-Dist: numpy<=2.3.2\n"),
        ("optional-tool", "1.0", 'Requires-Dist: numpy<2; extra == "legacy"\n'),
    ]:
        metadata = site / f"{name}-{version}.dist-info"
        metadata.mkdir(parents=True)
        (metadata / "METADATA").write_text(f"Name: {name}\nVersion: {version}\n{dependency}")
    (root / "pyproject.toml").write_text('[project]\ndependencies = ["numpy>=1.26"]\n')
    (root / "uv.lock").write_text('[[package]]\nname = "numpy"\nversion = "2.3.2"\n')
    (root / "requirements.txt").write_text("numpy==1.26.4\n")
    settings = root / ".codex"
    settings.mkdir()
    (settings / "custom_nodes.lock.json").write_text(
        '{"schema_version":2,"repositories":[],"install_sources":{}}'
    )
    node = root / "custom_nodes" / "LocalAdvisor"
    node.mkdir(parents=True)
    (node / "requirements.txt").write_text("local-advisor\n")
    workflow = root / "workflow.json"
    workflow.write_text(json.dumps({"nodes": [{"id": 1, "type": "Advisor"}]}))
    schemas = {"Advisor": {"python_module": "custom_nodes.LocalAdvisor"}}

    report = build_report(root, distributions(path=[str(site)]), "numpy", "2.4",
                          workflows=[workflow], schemas=schemas, imports={})
    candidate = report["candidate"]
    assert report["counts"]["outside_lock"] == 2
    assert candidate["decision"] == "blocked"
    assert [block["consumer"] for block in candidate["blockers"]] == ["local-advisor"]
    assert candidate["affected_workflows"][0]["nodes"] == ["Advisor"]
    assert candidate["compatibility_files"][0]["specifier"] == "==1.26.4"


def test_resolver_side_effect_is_checked_against_installed_only_consumer(tmp_path, monkeypatch):
    (tmp_path / "pyproject.toml").write_text('[project]\ndependencies = ["app"]\n')
    lock = tmp_path / "uv.lock"
    lock.write_text('[[package]]\nname = "app"\nversion = "1"\n'
                    '[[package]]\nname = "bridge"\nversion = "1"\n')
    (tmp_path / ".codex").mkdir()
    (tmp_path / ".codex/custom_nodes.lock.json").write_text(
        '{"schema_version":2,"repositories":[],"install_sources":{}}'
    )
    metadata = tmp_path / "site" / "local_tool-1.0.dist-info"
    metadata.mkdir(parents=True)
    (metadata / "METADATA").write_text("Name: local-tool\nVersion: 1.0\nRequires-Dist: bridge<2\n")
    monkeypatch.setattr(package_review, "resolve_candidate", lambda *_: {
        "status": "resolved in isolation",
        "changes": [
            {"package": "app", "before": "1", "after": "2"},
            {"package": "bridge", "before": "1", "after": "2"},
        ],
    })

    before = lock.read_bytes()
    report = build_report(tmp_path, distributions(path=[str(metadata.parent)]), "app", "2", resolve=True)
    candidate = report["candidate"]

    assert candidate["decision"] == "blocked"
    assert [(row["consumer"], row["dependency"]) for row in candidate["blockers"]] == [("local-tool", "bridge")]
    assert lock.read_bytes() == before


def test_migration_checks_missing_dependencies_against_the_projected_environment(tmp_path, monkeypatch):
    monkeypatch.setattr(uv_workspace, "ROOT", tmp_path)
    export = tmp_path / "pylock.toml"
    export.write_text('[[packages]]\nname = "idna"\nversion = "3.19"\n')
    fixture = SimpleNamespace(version="1.0", requires=["idna>=3,<4"])
    installed = {"fixture-node": fixture}

    uv_workspace.check_plan(export, installed, None, {})

    fixture.requires.append("missing-fixture-dependency>=1")
    with pytest.raises(ValueError, match="which the resulting environment would still lack"):
        uv_workspace.check_plan(export, installed, None, {})
