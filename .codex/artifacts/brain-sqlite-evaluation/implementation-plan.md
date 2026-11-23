# Brain report quality and SQLite evaluation implementation plan

Goal: improve machine-readable evidence quality in existing Brain reports and evaluate SQLite without migrating production storage.
Architecture: Brain owns additive report quality metadata. Raw run/event/sample files remain authoritative. The SQLite spike is disposable and outside runtime imports; Studio remains the future experiment/report owner.
Spec/authorization: user's request to improve Brain data quality and evaluate SQLite for local-model analysis; existing BENCHMARK_READINESS.md and independent-owner decision apply. Sequential native execution is preserved.

Ruling: implement the authorized additive report-quality change now. SQLite adoption, automatic indexing and model invocation are separate from the requested evaluation; no production DB, daemon, model or service restart is introduced by this batch.

- [x] Measure disposable SQLite import, exact query parity, read-only behavior, seed precision and current evidence gaps; preserve all source hashes.
- [x] Add failing report tests for historical missing provenance, digest mismatch, dirty/unknown owners, malformed snapshot, scalar versus object links and multiple runtime settings attestations.
- [x] Add workflow_monitor/quality.py data_quality(report) -> dict; attach to benchmark JSON and comparison rows. Keep benchmark_qualified false, never infer executed values or backfill history. Zero-valued measurements remain values; unavailable evidence remains explicit.
- [x] Verify full Brain suite, JSON/CSV propagation, current records offline and source preservation. Review in Brain's repository with CodeRabbit.
- [x] Commit Brain independently, update parent lock/evidence hashes and refresh only Brain's graph. Document SQLite recommendation and model-ready packet; leave live Python activation explicit.

Review focus: source digest validity differs from loaded-code identity; generic missing fields do not establish a failed generation; object links are not unresolved scalar parameters; multiple scene reports cannot become one fictitious recipe; unsigned 64-bit seeds remain exact text at SQL/model boundaries.
