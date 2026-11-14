# Local workflow catalogue

Generated 2026-11-09T17:40:38.680448+00:00. **Mapped / not run**, never a runnable-workflow certification.

- [Extension coverage](extensions.csv) — every extension directory and standalone candidate, including `.disabled` and `.example` placements.
- [Full inventory](workflows.json) — aliases, absolute/checkout-relative paths, source hashes, graph hashes, node references/providers, exclusions and errors.
- [Workflow matrix](workflow-matrix.csv) · [Model references](model-references.csv) · [Blockers/unknowns](blockers/README.md)
- [Test copies](tests/README.md) · [Runtime results](results/README.md) · [Review progress](START_HERE.md). This scanner never executes workflows.

## Reconciliation

2262 candidate files; 1187 unique graphs; 1194 graph payload occurrences = 1187 unique + 7 duplicate aliases. One PNG or JSON wrapper can contain multiple payloads. Source-status counts partition files; payload-status counts partition extracted payloads (not files).

Source statuses: `{"inspected": 1602, "parse_or_read_error": 2, "png_without_workflow_metadata": 130, "uninspected_media_or_archive": 528}`

Payload statuses: `{"graph": 1194, "metadata_or_config": 385, "recipe": 25}`

Traversal gaps: 4. Extensions/candidates: 46.

| Source family | Graph occurrences | Unique graphs within family |
|---|---:|---:|
| core_blueprint | 116 | 116 |
| extension | 355 | 350 |
| installed_template_package | 664 | 664 |
| saved_user | 53 | 51 |
| studio_template | 6 | 6 |

Family unique totals overlap when exact graphs occur in several families; core blueprints and installed templates are not extension coverage. Enabled location is **not proof of loading**. Revisions are local Git HEAD where present, not clean-tree assertions; file hashes capture scanned content.

## Scope and limits

Walk all extension directories (including disabled ones), `user/` (including backups and panel snapshots), optional `workflows/`, `studio/templates/`, `blueprints/`, and installed workflow-template JSON/core packages discovered on the interpreter's site-packages or checkout `.venv`. Exact scan roots are recorded in JSON. No imports of extensions or template packages. No originals moved, rewritten or copied.

Only JSON structure and PNG `workflow`/`prompt` text metadata are inspected. Recipes using `key/settings`, config and metadata sidecars are excluded. Known JSON wrappers are searched; arbitrary document snippets are not. JPEG/WebP/GIF metadata and archives are logged as uninspected, not silently treated as empty. Python/JS/Markdown snippets, binaries, media-package previews, `input/`, `output/`, `.git`, dependency/cache directories and nested symlink directories are outside scope. Standalone Python candidates get coverage rows but their source is not parsed for embedded graphs. The generated output directory is always pruned, even when inside a source root.

Deduplication uses SHA-256 of canonical full graph JSON (sorted object keys, formatting ignored). Layout, settings, node IDs, array order and subgraphs are preserved: meaningful variants cannot silently merge. UI/API pairs remain separate unless exactly identical JSON; shared filenames/metadata are not execution equivalence. Source SHA-256 hashes original bytes independently.

Model references are filename heuristics from node widgets/API inputs plus named model selections; URLs and prose can require manual review. Dynamic/non-file selections remain unresolved. No model-folder inventory, download, loader compatibility, graph completeness, safety or hardware inference. Providers are only the localhost schema's `python_module` when present, not a guessed ownership mapping. Subgraph definitions and muted nodes are included conservatively.

Schema reconciliation: `{"endpoint": "http://127.0.0.1:8188/object_info", "node_types": 1965, "sha256": "753b4c795001fa06ff1a3948562c9347d5567de13adf1975e9b0e9665c13de82", "status": "available"}`. Only optional fixed-loopback `GET /object_info` is supported; no remote URL, redirects, proxies, queue calls or workflow execution. Schema presence does not prove frontend functionality or runtime success.

## Regenerate

```sh
PYTHONPATH=studio .venv/bin/python -m unittest discover -s studio/tests -p 'test_workflow_catalogue.py' -v
.venv/bin/python studio/workflow_catalogue.py
# Optional read-only local schema snapshot (failure leaves availability unknown):
.venv/bin/python studio/workflow_catalogue.py --port 8188
```

Generated index/CSV/JSON files are overwritten on refresh; originals and future test/result evidence are untouched. No copied graph payloads are stored: use the original reference and verify its source hash before review.
