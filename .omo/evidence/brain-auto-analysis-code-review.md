# Automatic Brain analysis code review

- codeQualityStatus: BLOCK
- recommendation: REQUEST_CHANGES
- Scope: current uncommitted automatic-analysis changes in Studio and the Brain component worktree, including new untracked brain_job.py, workflow_monitor/analysis.py and tests. User's pre-existing llama.cpp adapter additions were preserved and distinguished from this integration.
- Spec: `.codex/artifacts/brain-completion-analysis-20261115/AUTOMATIC_ANALYSIS_EVALUATION.md`.
- Plan/notepad: `.codex/plans/brain-automatic-analysis-20261115.md`.
- Review snapshot: 2026-11-15, before the parent's announced lifecycle fixes. This is not approval of subsequent changes.
- Artifact fallback: `omo-agent-toolkit ulw-loop status --json` failed because its installed runtime target is missing; no installation changes were made.

## CRITICAL

None found.

## HIGH

### H1. Detached report worker survives ComfyUI shutdown and loses queue ownership

`workflow_monitor/analysis.py:119–149` starts a separate session with `subprocess.Popen(..., start_new_session=True)` and only terminates it from a `finally` block in the executing thread. `main.py:630` starts that prompt worker as a daemon thread. There is no parent-death guard in the report child or application cleanup handling for this subprocess. On SIGTERM/crash/process exit the Python thread's finally block need not execute, and the child continues its HTTP request after the native queue no longer exists. Restarting ComfyUI can therefore allow a new render to overlap the previous report inference.

Reproduction: launch the real `supervise` function in an owned temporary Python supervisor with a sleeping child, terminate only that supervisor, and observe the child remains alive. The test then terminates its owned child. Result: supervisor exit -15, detached child survived true.

Evidence: `.omo/evidence/brain-auto-analysis-orphan-repro.json`.

Required: enforce worker lifetime against its owning server (including the startup race), and reconcile unfinished analyzing attempts / prove dedicated runtime idle before a restarted server admits new generation. Test parent death, not merely the normal cancellation flag.

### H2. Recorder eviction silently drops automatic analysis requests in long batches

`workflow_monitor/recorder.py:113–126` evicts the first terminal record at the 32-record limit without preserving its still-pending analysis request. The scheduler is only invoked for records remaining in `self.records` (`recorder.py:381–384`), and `AnalysisScheduler.consider` refuses to enqueue while any rendering job is pending (`analysis.py:70–72`). In a continuously busy batch of more than 32 monitored runs, early completed runs disappear from the only scheduling loop before the queue becomes idle. Their raw files remain marked analysis_requested, but they never receive their promised report.

Reproduction: admit and finalize 33 opt-in runs while pending rendering work remains. The first source is still on disk, but only 32 records remain and the first is no longer eligible for scheduling.

Evidence: `.omo/evidence/brain-auto-analysis-eviction-repro.json`.

Required: preserve finalized pending requests independently of the bounded monitoring-record cache and drain them after pending render work. Do not prevent new monitor admissions merely to retain those requests. Add a >32-run batch regression test.

## MEDIUM

### M1. Deterministic reports depend on an available llama.cpp runtime

`workflow_monitor/analysis.py:169–174` checks `/slots` before starting every worker, and `supervise` always waits for `/slots` in its finally block. However `studio/brain_job.py:25–40` deliberately omits inference for cached/failed/no-sampling runs. Consequently those otherwise-local deterministic summaries fail when the optional model server is stopped, and even a pre-inference worker failure can hold the native queue indefinitely if `/slots` becomes unavailable. The documented hold is safe for a possibly active inference request, but applying it to jobs known not to have submitted inference is unnecessary operational coupling.

Suggested follow-up: let the report worker communicate whether it actually submitted inference, or separate preparation/deterministic publication from the model-request phase; only require runtime cleanup proof when a request may exist. The current documentation explicitly describes requiring a running dedicated runtime, so this is not treated as an undisclosed blocker.

## LOW

No additional findings worth separate changes.

## Verification and test relevance

Independently ran:
- `.venv/bin/python -m pytest -c studio/pytest.ini studio/tests/test_brain_analysis.py studio/tests/test_brain_reports.py studio/tests/test_brain_local_model.py studio/tests/test_brain_job.py -q`: 48 passed, 5 subtests passed. Log: `.omo/evidence/brain-auto-analysis-review-studio-tests.log`.
- `.venv/bin/python -m unittest discover -s .codex/worktrees/workflow-monitor-brain/tests -p 'test_*.py'`: 117 passed. Log: `.omo/evidence/brain-auto-analysis-review-component-tests.log`.

These passing suites did not cover either reproduced HIGH failure. The cancellation unit test exercises an actual subprocess and useful idle-check sequence, but does not establish real llama HTTP cancellation, parent shutdown, or queue exclusivity across restart. The parent is planning live lifecycle checks; this review did not submit generation or inference.

## Skill-perspective check

Searched the installed `.agents/skills`, `.codex/skills` and plugin cache for `remove-ai-slops` and `programming` SKILL.md files; neither was available. Applied the reviewer prompt's supplied criteria instead. The added regression tests assert meaningful persistence, queue-ownership, source-settling and process behavior, not deletion-only or requested-removal facts. No brittle model-prose tests or gratuitous production abstraction were found. Initially observed inherited test classes duplicating existing test suites; the parent independently changed those to fixture reuse during review, so this is not an outstanding finding. Remaining unnecessary coupling is described in M1.

## Blockers before approval

1. H1: report-worker parent-death and restarted-server exclusivity.
2. H2: durable scheduling independent of 32-record eviction.

Parent was notified immediately of both confirmed HIGH findings and owns fixes. Review remains REQUEST_CHANGES until those fixes have artifact-backed regression evidence.
