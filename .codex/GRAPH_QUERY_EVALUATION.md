# Production graph query evaluation

Keep the existing SQLite backend. The measured workload exposes missing relationships and provenance, without evidence that database speed is the limiting factor. This is a sample of seven production questions across six owners, not an exhaustive audit of all 15 stack owners.

## Reusable questions and cross-owner evidence

[graph-questions.json](graph-questions.json) contains the questions, expected source answers, exact owner/project identities, 14 read-only probes, source hashes and anchors, and five explicit integration boundaries. These boundaries supplement CBM; they are not synthetic CALLS edges inserted into its databases. Their checks describe required acceptance, not tests that indexing has executed.

| Question | Graph result | Required evidence beyond the graph |
|---|---|---|
| Who requests model unloading? | Native core callers and LC123/Context Loop owner symbols found; Dynamic → native unload edge missing | Dynamic `_cleanup_vram`, native registry, LC123 encoder unload and Context Loop stage retirement source |
| Does LC123 affect graphs without LC nodes? | Local encoder-hook call found; wrapper → native sampler call absent | Import-time `_load` calls and assignments to `CFGGuider.outer_sample`; actual wrapper order still needs runtime inspection |
| How does Brain consume Dynamic samples? | Both local endpoints and normalization call found; runtime-discovered cross-owner call absent | `sys.modules` discovery and `self.module.get_snapshot()`; validate required fields and unknown-value semantics |
| What does scene cleanup do? | Scene-boundary → stage-retirement call found | Branches distinguish off, unload_models and fresh_scene; source semantics are not a VRAM benchmark |
| Can we attribute recorded results to exact inputs/code? | Recorder → prompt-capture call found | Prompt/workflow identity, fingerprints, runtime package/review hashes, unresolved values and historical component revisions |
| Is no incoming CALLS edge proof of dead code? | `interrupt_if_running` exists but has no graph callers | Two real `server.py` calls through `self.prompt_queue` disprove that inference |
| Is the RefMod frontend fully indexed? | Exact-file probe correctly reports partial parsing | Read flagged `web/refmodstack.js` ranges and use browser evidence |

Nine of thirteen symbol/relationship probes found their required row fragments. Four relationships were absent in every repeated query. The fourteenth probe is a coverage diagnostic and correctly reports the known partial parse. These are selected regression cases, not a statistical accuracy score. Missing rows are investigation findings, never permission to delete code.

## Measured workload

The `verified/` run executed 14 probes three times sequentially: **42 successful calls, no tool errors or truncated answers**. Median end-to-end call latency was **0.540 seconds**, maximum **0.800 seconds**, and summed call time **24.94 seconds**. Timings include CLI startup, IPC, query work and serialization on the active workstation; they are not isolated SQL-engine timings or cold-cache benchmarks.

Sampled aggregate RSS of the production CBM processes peaked at **163.8 MiB**, host available RAM stayed above **16,316.8 MiB**, and observed swap usage was **0 MiB**. Sampling is every 100 ms, sums process RSS (which can double-count shared pages), and is neither a unique-page measurement nor an instantaneous peak. No full reindex, GPU job or model load was performed.

All six owners' reported Git HEADs matched their current checkout during verification. Eighteen source evidence entries matched their saved content hashes and anchors. Representative file metadata matched; the known RefMod partial parse remained explicit. HEAD metadata alone is not proof that every file or relationship is current or complete.

Raw responses, timing and resource observations are in `artifacts/graph-query-evaluation/verified/`. The earlier `baseline/` run omitted verbose HEAD metadata; its false HEAD-match flags were a harness omission, not evidence of stale repositories. The verified run corrected that omission. `final-smoke/` exercises the final runner's additional before/after source and HEAD checks.

## Runtime evidence remains qualified

Read-only inspection found 37 historical Brain run records and sampled the two most recently modified records. Both refer to the master movie workflow and each retains **68 unresolved captured inputs**. This count does not mean every input failed: configured links and executed runtime reports are different evidence sources.

One sampled record is `unknown-after-restart`, with partial coverage and unavailable evidence. The other is `succeeded`, with events-only coverage, a collected prompt-review report and model identity still unverified. Their environment records contain Python/platform, attention flags and selected package versions, but no complete component Git revision manifest. Existing package/report hashes provide narrower provenance; today's stack lock cannot establish historical code revisions. See `artifacts/graph-query-evaluation/runtime-metadata.json` for sanitized metadata and source-record hashes.

Brain's actual run directory is `user/workflow_monitor/runs/`, resolved from its configured user root. The current observer reports no error and no active runs; this is an idle health observation, not generation acceptance. We did not rewrite historical records or fill missing provenance with present-day values.

## Run and interpret

From the ComfyUI root, choose a new output directory for every run:

```bash
.venv/bin/python .codex/evaluate_graph_queries.py \
  --output .codex/artifacts/graph-query-evaluation/my-check --repeats 3
```

The runner checks discovered project roots, source hashes, file freshness and reported HEADs, calls only read-only CBM tools, applies a 20-second timeout per call, and records source/HEAD changes during the workload. It does not reindex, change database configuration or restart shared clients. Output directories must not already exist.

Exit 0 means the diagnostic completed without detected operational/freshness errors; it does **not** mean every expected relationship exists. Inspect `missing_row_fragments`, exact-file `coverage` and the question's source-backed answer. Partial parsing remains visible and does not get converted into a clean result. A changed source hash requires reviewing the fact and updating its anchors, not blindly accepting a new hash.

Five focused harness checks covered successful responses, tool-reported errors, malformed JSON, nonzero exit and timeout handling. The live workload and final smoke check exercise the real CLI and freshness checks. CodeRabbit remote review was not run for this local diagnostic tooling.

## Decisions for subsequent work

- Use the five explicit owner boundaries when choosing review scope and required checks. They make runtime discovery and wrappers visible without pretending static analysis resolved them.
- Before a controlled generation benchmark, capture an immutable component-revision manifest alongside the run/package identity and verify that the recorder retains it. Record effective LC123 settings, attention/offload policy and model identities separately from declared settings. Do not retrofit old runs with guessed values.
- Investigate RefMod parser support and the four unresolved relationships in the analyzer only when the specific question needs them. Use source evidence immediately; do not reinstall packs or alter ignore rules to inflate graph counts.
- Revisit database selection only after a concrete workload has a reproducible latency/resource or query-expressiveness failure that cannot be addressed in the current query/index layer. Compare identical data and required answers in a disposable experiment; no migration is justified by this sample.
