# New-run source and settings provenance

Brain now captures one local source/settings snapshot for a newly observed live-queue run. This change is implemented and tested; activation in the already-running ComfyUI process requires a guarded restart. Historical runs are not backfilled.

## Recorded evidence

- Core and discovered custom-node Git owners, grouped by actual checkout/worktree with symlink install aliases; commit, dirty/unknown state and capture coverage.
- Allowlisted launch options, sampled native VRAM/smart-memory/pinned-memory policy, and LC123 configured settings separately from its last cached values.
- Capture window, observed run state, immutable snapshot and SHA256; status is pending, collecting, collected or unavailable.

Records retain the data under `provenance` in `run.json`; run detail/export, benchmark JSON and comparison JSON expose it. No new frontend control was added. Existing runtime reports remain the evidence for executed dynamic values; this snapshot does not replace them.

The collector reads local Git metadata and selected settings only. It does not collect repository remotes, full command lines, arbitrary settings, source contents or model weights. Git work is serialized outside the event loop, with a 10-second budget, 2 seconds per command, at most 64 custom-node candidates and a 256 KiB snapshot cap. Failures never change generation status. Visual reviews return a conflict while source/settings capture is active, then preserve both updates. Runs no longer live when their capture turn starts remain unavailable. Capture cannot resurrect deleted/evicted records. Shutdown/restart resolves interrupted capture as unavailable, including cancellation before the task's first turn.

## Interpretation

`source_coverage: complete` means metadata was obtained for the discovered candidates, not that every pack imported or every runtime byte matches Git. Ignored files are outside Git coverage. Dirty work requires additional preservation to reproduce. `loaded_code_identity` deliberately remains `unverified`: the process may have imported files before a disk edit. No capture makes the run benchmark-qualified or creatively accepted.

A configured launch flag is not proof of the selected opaque attention backend. Native policy is a point-in-time process observation. A queued run may be captured while another run is executing; its state and capture window remain explicit. LC123's cached value may precede this run's sampling, so it is never labeled executed input. Missing weights/model hashes and unresolved links remain unknown.

The read-only real-filesystem and isolated CPU observer checks found 15 owners (parent plus 14 components) in about 0.09 seconds, with a roughly 4.4 KB snapshot. There are 16 install aliases because a standalone parent-owned Python node is captured in addition to the 15 custom-pack installation paths. Those measurements do not establish under-load overhead or live in-process settings capture.

## Validation and activation

Evidence is in `artifacts/run-provenance/`: failing-first tests, Python/browser-event suite logs, filesystem snapshot, isolated CPU observer persistence/export smoke, review output and preservation hashes. See [RESULT.md](artifacts/run-provenance/RESULT.md) there for final commits and review disposition.

Activation must preserve the visible unsaved movie canvas. Recheck the queue, RAM/VRAM and exact port owner; stop only the verified ComfyUI process with SIGINT, then launch through `.codex/launch.sh` with canonical flags. Verify backend readiness, browser reconnection and the new collector before submitting any media job. A small CPU-only monitored prompt can validate live capture separately from model/generation acceptance if authorized. Reloading the browser alone does not activate changed Python modules.

After changing Brain source, update its own Git commit first, then its parent lock entry and source hashes in `graph-questions.json`. The graph query evaluation is a historical baseline; new source evidence does not rewrite its earlier results. Preserve unrelated edits in `.agents/skills/`.
