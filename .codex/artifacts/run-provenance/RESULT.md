# New-run provenance implementation result

Implemented and committed locally in Brain as `d0cf1c48727a46673e3e1ba23787d509e4b6eafb`. Parent integration pins that exact revision. Activation subsequently passed; see [ACTIVATION.md](ACTIVATION.md). The implementation-stage evidence below predates that authorized restart.

## Behavior

New live-queue records obtain one immutable source/settings snapshot: core and custom-node owner commits, dirty/unknown state, installation aliases, capture window and digest, allowlisted configured launch options, sampled process memory policy and LC123 configured/cached values. Candidate installs are not proof of loaded packs; filesystem commits are not loaded-code attestations. Historical records are never backfilled. Benchmark/comparison JSON retain the snapshot without promoting qualification or resolving dynamic inputs.

Metadata collection is serialized off the event loop with bounded Git time, candidate count and snapshot size. Failure, deletion, eviction and shutdown remain explicit. Visual reviews wait for metadata collection so neither persistence path can overwrite the other.

## Validation and review

- 102 Python tests and 4 browser-event tests pass. Failing-first evidence includes new collector/lifecycle/export behavior, malformed settings, shutdown/recovery and the review-versus-capture race.
- Real-filesystem snapshot: 15 Git owners, 16 installation aliases, about 0.09 seconds and 4.4 KB. Isolated CPU observer smoke verifies persistence, digest and both JSON exports. These are not live-process settings checks or under-load benchmarks.
- CodeRabbit completed two scoped reviews. First: one **minor** non-object settings finding, reproduced and fixed. Second: one **major** visual-review/provenance persistence race, verified and fixed with a two-line existing-route guard and a route regression that fails without it (HTTP 200 instead of required 409), then proves both persisted updates. Final suite passes after this fix. The last guard/test/doc follow-up received native diff/test verification; no third remote review was run. Raw outputs: `coderabbit.ndjson`, `coderabbit-final.ndjson`.
- Brain index refreshed once in the existing production store: 371 nodes / 1731 edges, matching commit, no reported partial/unusable parses. Five changed runtime files have matching metadata; graph query finds both collector functions and the recorder method. This is best-effort coverage, not proof of all relationships.
- Parent question-manifest source hashes and 39 anchors checked. The earlier query-performance evaluation remains historical.

## Preservation and stack status

37 historical run files and 78 saved workflow/project files match their baselines. The seven pre-existing parent skill edits were preserved. All other 13 component HEADs are unchanged. Additional concurrent skill edits in Spark H3 and Swarm were left untouched; the strict checker reports 12 DIRTY findings in those two owners, so the whole stack is not currently reproducible from commits alone. There are no lock revision/remote/install-source mismatches. Brain itself is clean after its commit.

ComfyUI remained PID 37847 with canonical flags and an empty queue; the visible browser session was preserved. No model loading, GPU generation, database migration, host PATH change, shared daemon restart, push or merge occurred.

## Activation follow-up

[activation-plan.md](activation-plan.md) and [activation-cpu-prompt.json](activation-cpu-prompt.json) specify the guarded canonical restart and a five-second CPU-only monitored prompt using existing nodes. Preserve the unsaved movie canvas, verify a real down/up cycle and browser reconnection, then validate a new live record and exports. This integration check does not establish generation performance or creative quality.

The person approved activation in Inbox message `msg_01M7E9NTCCW4EX0YDY387PQQBH`. The guarded restart and single prepared CPU-only prompt completed successfully; the original canvas and historical/saved files remain unchanged.
