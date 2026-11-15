# Brain data quality and analysis storage

Brain's additive `data_quality` report (`workflow-monitor.quality.v1`) is implemented and tested in its owning repository; live activation awaits the guarded restart. It is present in newly generated benchmark JSON and comparison JSON/CSV. Raw historical records are not rewritten.

The report checks provenance snapshot digest integrity, marks dirty/unknown source owners, separates unresolved parameters identified by the existing scalar-name allowlist from other links, and reports absent runtime, sampling, model, output, review and thermal evidence. Other links may also carry scalars outside that allowlist. Multiple settings attestations remain distinct. A digest match establishes internal consistency, not independently attested loaded code. Evidence gaps are not generation failures or a quality score; `benchmark_qualified` remains false.

[SQLite decision and measured evaluation](artifacts/brain-sqlite-evaluation/SQLITE_DECISION.md): use a separate rebuildable analysis index, with raw JSON/JSONL authoritative. This batch created disposable evaluation databases only. No production SQLite writer, watcher, local-model server, inference invocation or automatic configuration-changing loop was added.

The local-model input demonstration is `artifacts/brain-sqlite-evaluation/model-evidence-packet-quality.json`. It contains selected measured facts, source/run identities, quality gaps and analyzer hashes. A future report adapter should compute statistics deterministically and let the selected local model explain them with citations, explicit uncertainty and proposed tests; it must retain human experiment/adoption decisions. Schema validation and citations cannot guarantee every narrative claim is true.

Before production adoption, implement freshness/stable-snapshot import, exact decimal seed storage, fixed read-only queries, bounded model packets and durable experiment/report records in their proper owners. Follow the proposed contract in the decision document; do not connect to the asset DB or Codebase Memory graph as the telemetry store.

## Activation check

After authorization, preserve the open unsaved canvas, verify the empty queue and exact process, restart through `.codex/launch.sh` and observe browser reconnection. Retrieve the existing CPU smoke run `e3ead456-950b-4b5e-840a-e51e3f4e4751`: verify its benchmark/export and comparison contain matching `data_quality`, its valid recorded provenance digest remains valid and `benchmark_qualified` remains false. Its source revisions must remain those captured at execution, not today's checkout. Verify one historical run with absent provenance remains unavailable. No new prompt or model loading is needed. Preserve historical run/workflow hashes.
