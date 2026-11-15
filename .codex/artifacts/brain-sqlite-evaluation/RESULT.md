# Brain data-quality and SQLite evaluation result

Brain commit `40e316bc1d73f92df82e1db6d0ecdfe7cc45ed0a` adds `data_quality` to benchmark and comparison exports. 109 Python tests and 4 browser-event tests pass. The seven new tests were observed failing before implementation. CodeRabbit completed the four-file component review with zero findings. The installed Brain worktree is clean and its graph HEAD/file metadata match. The running server still has the preceding Python modules; report-quality activation requires a guarded restart and can be verified from existing runs without a new prompt.

Offline application of the new report code to all 38 existing records succeeded. It exposes 30 runs with unresolved scalar-name parameters, distinguishes other links, verifies the one captured provenance digest and preserves historical unknowns. Source digest consistency is not loaded-code attestation; missing evidence is not a model ranking. No model-weight hashing, new thermal sensors, executed-parameter hooks, experiment registry or local inference adapter was added by this bounded batch.

SQLite evaluation supports a separate rebuildable analysis index. See [SQLITE_DECISION.md](SQLITE_DECISION.md) for measured costs, exact comparisons, type/precision findings and the proposed production contract. The disposable SQLite files are not deployed or connected to Brain. Existing raw run records, Codebase Memory and the asset database remain authoritative for their own data.

[Demonstration report](BENCHMARK_REPORT_DEMO.md) was generated deterministically from a compact evidence packet with source and analyzer hashes. No language model was invoked. This proves data packaging and report generation mechanics, not local-model reasoning quality.

All existing raw source-file hashes and 78 saved workflow/project file hashes remain unchanged. The parent lock matches all 14 component revisions; unrelated dirty skill edits in Spark H3/Swarm and the parent are preserved and remain a reproducibility caveat. No generation, restart, push, merge, dependency installation or model-setting change occurred.
