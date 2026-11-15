# Brain analytics storage decision

Recommendation: use a separate, rebuildable SQLite analysis index over Brain's existing run files. Keep raw JSON/JSONL authoritative. Do not replace Codebase Memory's graph store or ComfyUI's asset database.

## Measured evaluation

Using the baseline Brain report implementation at `d0cf1c4`, a disposable index imported 38 completed runs, 5,525 events, 9,932 samples and 15 component observations. The raw sources total 25,193,996 bytes; the deliberately verbose prototype database is 38,789,120 bytes. SQLite is for queries and provenance joins, not a storage-saving claim.

A fresh process importing one run at a time took 0.902 seconds including source reading and report construction; `/proc/self/status` measured a 69.1 MiB process high-water mark (17.1 MiB initially). The first two runs reported an anomalous identical 656.7 MiB through `getrusage`; do not use those values to claim memory improvement. The final profile records both process RSS/HWM and getrusage, which agree. No torch import, model load or inference was needed.

Fifteen warm-cache repetitions of the stream evaluation measured median queries: status counts 0.009 ms, evidence-gap counts 0.030 ms, temperature peaks 1.393 ms, component revisions 0.013 ms. Reading the source run JSON for identical status counts took 5.842 ms. Both are already fast for 38 runs; SQLite's main value is a stable relational interface for filters, joins and bounded report input. Derived-query timings exclude report construction/import costs and are not production-load benchmarks.

Status counts and temperature aggregates match direct-source results. Integrity and foreign-key checks passed. A read-only connection rejected DELETE. Every source hash remained unchanged. An unsigned 64-bit seed (`18446744073709551615`) becomes a float through SQLite JSON extraction; storing/reading its JSON text and decoding with Python preserves it exactly. Production identity/seed fields must use decimal TEXT, including browser/model packets.

## Options

| Approach | Benefit | Cost / decision |
|---|---|---|
| Existing files only | Simplest, preserves current behavior | Adequate at current size; each consumer must implement traversal, joins and evidence interpretation |
| Files plus derived SQLite | Stable queries, explicit missing evidence, cross-run joins, rebuild/recovery | Recommended; requires freshness tracking and one importer |
| SQLite as primary recorder | Transactional live event storage | Not justified by this sample; broadens recorder/recovery/export migration and creates avoidable risk |

## Production contract proposed for the next batch

- Brain owns evidence collection and its report `data_quality`; Studio owns the index, experiments, reports and decisions. No new service or duplicated MCP server.
- Stream JSONL line by line in the production importer; the disposable spike only bounded memory by run. Preserve the current per-run caps and avoid retaining entire long-run sample streams in RAM.
- Index only stable terminal-run snapshots. Record file hashes, analyzer schema/code version, source timestamps and skipped/changed runs. A run changed during import is excluded with a diagnostic; never label stale data current.
- Build a new database generation and publish it only after validation. Existing readers finish against their opened generation. Retain the previous valid generation for recovery; do not auto-delete raw runs. Start with on-demand snapshot rebuild, not a background watcher or live dual-write path.
- Store tables for runs, sources, phase/sampler metrics, samples/device observations, component revisions, model/input/output evidence and quality gaps. Preserve NULL for unavailable values, units and evidence basis. Use Brain's quality implementation, not the spike's independent audit helper, as the shared rule owner.
- Expose fixed, parameterized read-only operations for filtering runs, retrieving evidence and comparing selected runs. Bound rows/time/output. A model receives a compact packet and citations, not write access or arbitrary shell/SQL execution.
- Experiment records identify baseline/candidate run IDs, intended differences, controlled workload/cache/thermal conditions, repeated trials, evidence hashes and final human decisions. Existing H3-specific comparison requirements are not universal model-family criteria.
- Deterministic code computes numbers and evidence gaps. A local model may explain patterns and propose tests; its report records model identity, prompt/template version and evidence-packet hash. Validate referenced IDs/fields and report shape. This cannot prove all natural-language claims true; causal conclusions and adoption remain reviewed decisions.
- Reuse the selected local inference runtime only after identifying the actual endpoint/model and checking GPU contention. Do not install/download a model, start a new model server or run inference during generation as part of the index setup.

## Data-quality improvements in this batch

The additive Brain `workflow-monitor.quality.v1` report validates source snapshot digests, lists dirty/unknown owners, distinguishes unresolved scalar parameters from object links, counts runtime-setting attestations without merging scenes, and exposes missing capture/model/output/review/thermal evidence. It does not invent missing measurements or change qualification.

Offline evaluation across all 38 records found 30 runs with unresolved scalar parameters, compared with 35 containing any unresolved graph link. All 38 still lack verified model identity and complete fresh-sampling evidence under the existing sampler coverage rules. These records include smoke tests and failed/interrupted runs; gaps are not failure counts or model rankings. Historical provenance remains absent for 37 runs.

The model-ready demonstration packet is `model-evidence-packet-quality.json` (14.6 KB), including source-record hashes and analyzer-code hashes. It was not submitted to a language model. SQLite files and `spike.py` are evaluation artifacts, not a deployed production integration.

## References and evidence

Official docs were fetched with Context7: [SQLite URI read-only mode](https://www.sqlite.org/uri.html), [transaction isolation](https://www.sqlite.org/isolation.html), [WAL tradeoffs](https://www.sqlite.org/wal.html). WAL is useful when a future requirement actually needs concurrent writers/readers; the initial immutable-generation design does not need a live WAL writer.

Local evidence: `result.json`, `result-stream.json`, `result-profile.json`, `source-hashes.json`, `data-quality-summary.json`, `model-evidence-packet-quality.json`, `spike.py`. No original records, workflow files, launch settings, databases or local-model settings were modified by the evaluation.
