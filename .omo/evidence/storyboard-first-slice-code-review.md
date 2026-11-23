# Storyboard first-slice code review

codeQualityStatus: CLEAR
recommendation: APPROVE

Current disposition follows the final re-review below. Earlier findings are retained as review history.

Scope: production_store.py, storyboard.py, storyboard_workspace.py, validator/schema diff and their tests; PromptBuilder production_api.py, production_workspace.js/mjs, tests, and only the production-route registration insertion in web_api.py. Existing dirty changes and future model/reference/generation features excluded. Plan: studio/plans/best-storyboard-creator-assistant.md and design companion. Ledger/notepad: .codex/artifacts/storyboard-implementation/progress.md.

## CRITICAL
None.

## HIGH

1. Delayed requests can overwrite a different workspace and lose its edits. `custom_nodes/ComfyUI-Fantastic-MiniMaxH3-PromptBuilder/web/production_workspace.mjs:201` (save completion at 204–205), and `:241` (open completion at 244). Save only disables its own button; New story and picker remain usable. Save A after one edit, open B while A is delayed, make one edit in B, then let A complete: the reset/shared editCounter equals A's captured counter, so A replaces B and clears B's unsaved edit without another confirmation. With a different count A's revision is assigned to B instead. Two overlapping opens have the same stale-response problem. Preview/create completions similarly lack a view identity. Bind async operations to captured project/view identity and invalidate obsolete completions or lock conflicting navigation. Add deferred-response interaction coverage for save/open/create, including edits after navigation. Static control-flow reproduction; no live browser manipulation was performed by this reviewer.

2. History publication is not crash-durable before replacing production. `studio/production_store.py:100` hard-links a flushed temporary file into revisions, then removes the temporary name, but never fsyncs the revisions directory. `:112` replaces production.json and `:115` only fsyncs its parent, which is a different directory. A power loss can retain the new canonical document without the previous revision directory entry, breaking the explicit history/durability contract. Flush the revisions directory after publishing its entry and before canonical replacement; ensure creation of revisions itself is durable in the parent before replacement. Validate ordering and fail-before-replace behavior when that directory sync fails. Current failed-file-fsync test cannot detect this missing operation. No destructive crash experiment was run.

## MEDIUM

3. CSV exports requested seconds and omits canonical frame timing/gaps. `custom_nodes/ComfyUI-Fantastic-MiniMaxH3-PromptBuilder/web/production_workspace.mjs:12`. At 24 fps a 1.02-second request becomes 24 frames / 1 second in storyboard.timeline, but CSV says seconds=1.02; a nonzero editorial gap is absent entirely. This does not satisfy the plan's shared timeline/export timing contract. Keep requested seconds explicitly named if useful and export authoritative start/end/duration frames, fps and planned seconds from snapshot.timeline. Test one fractional duration and nonzero gap. This is a limited exporter defect, not a demand to implement the future HTML/video phases.

## LOW
None.

## Skill-perspective check

remove-ai-slops and programming were not present in the available skill catalog or searches of /home/athar/.agents/skills, /home/athar/.codex/skills and installed plugin paths. Applied the explicit developer-provided criteria instead, before judging tests/maintainability. No deletion-only, removal-verification, tautological or brittle prompt-string tests found. Tests mostly exercise persistence, CAS, schema/identity rules and failure behavior; small frontend tests are useful but do not cover asynchronous workspace correctness. No untyped escape hatch or unnecessary production parsing abstraction found. Boundary validation is justified by filesystem and document integrity. No independent violation of either perspective found; concrete correctness gaps above remain blockers.

## Evidence inspected and independently rerun

- Inspected all scoped implementation/test source and tracked validator/schema diff, plus actual guard and Bootstrap integration owner. All new production endpoints use existing guard; API test uses a test guard, so it proves decorator wiring rather than production CSRF integration.
- Root focused command: `.venv/bin/python -m pytest -q studio/tests/test_production_store.py studio/tests/test_storyboard.py studio/tests/test_storyboard_workspace.py studio/tests/test_production_validate.py` — 48 passed in 0.36s.
- `node --test custom_nodes/ComfyUI-Fantastic-MiniMaxH3-PromptBuilder/tests/storyboard-workspace.test.mjs` — 3 passed.
- API command: `.venv/bin/python -m pytest -q custom_nodes/ComfyUI-Fantastic-MiniMaxH3-PromptBuilder/tests/test_production_api.py --rootdir=custom_nodes/ComfyUI-Fantastic-MiniMaxH3-PromptBuilder/tests --confcutdir=custom_nodes/ComfyUI-Fantastic-MiniMaxH3-PromptBuilder/tests --import-mode=importlib` — 1 passed in 0.11s, existing pytest-asyncio configuration warning.
- Inspected ledger `.codex/artifacts/storyboard-implementation/progress.md`: correctly calls manual mode partial, with future automation still open. No misleading overall completion claim found. Full-suite totals supplied by parent were not independently rerun or treated as verified here.
- `omo-agent-toolkit ulw-loop status --json` failed because installed runtime target is missing; no local .omo plan/currentAttemptDir found. Used required fallback report location. No install attempted.
- Graph discovery and architecture completed before source navigation; targeted AKB recall found no relevant records. Local memory search had no task-specific hit and was not used for findings.

Blockers: fix stale async view/project state and history durability ordering before approval. Address CSV timing mismatch in this slice or explicitly narrow its contract and label requested seconds.

# Re-review after first fixes

Disposition: codeQualityStatus BLOCK; recommendation REQUEST_CHANGES.

Resolved: history durability HIGH is fixed by syncing revisions and root before replace and root after replace. Both new ordering/failure tests are relevant. CSV MEDIUM is fixed by exporting authoritative timeline fields. Original simple stale-save/open/create overwrites are guarded by epoch and snapshot identity.

Remaining HIGH — combined save and canceled-navigation race leaves current edits unsavable. In production_workspace.mjs save completion, `if (context !== epoch || snapshot !== current) return` discards even revision acknowledgement for the same still-active snapshot after a navigation attempt. Reproduction: edit A; start save A and hold response; select B (accept discard), holding its open response; edit still-visible A again; release B response, which correctly aborts navigation because editCounter changed; release successful A save response. The old A revision remains in memory because epoch changed, although A is still current. A's next save returns 409; existing UI recovery requires reopening and discarding those newer edits. Updating revision for the identical retained snapshot, independently of permission to rerender the old view, or otherwise serializing this transition is needed. Add combined deferred-response regression coverage; isolated save/edit and open/edit tests do not cover their interaction. Static control-flow reproduction, not claimed as a reviewer browser run.

Independently reran focused Python tests: 50 passed in 0.54s. Node tests: 4 passed. Inspected browser harness with five meaningful user-state scenarios. Parent reports browser RED/GREEN runs; no saved browser-run output artifact was found in .codex/artifacts/storyboard-implementation during this re-review, so that result is attributed to parent rather than independently verified. No new skill-perspective violation; the required skills remain unavailable and prompt-supplied criteria were applied.

Blockers: preserve the correct revision after a successful save whose navigation attempt is canceled by newer edits.


# Final narrow re-review

codeQualityStatus: CLEAR
recommendation: APPROVE
blockers: []

The remaining HIGH is resolved in production_workspace.mjs:222–223: completion first rejects a different snapshot; if the same snapshot remains after a navigation epoch change, it updates only that snapshot's revision and leaves current edits intact. This addresses the combined canceled-navigation/save case without reviving the wrong-project overwrite. Inspected the sixth browser scenario at tests/storyboard-workspace.browser.mjs:109–119: it reproduces the exact sequence and checks the subsequent save uses the new revision and newest action text. Parent reports all six browser scenarios passing; reviewer inspected code/scenario but did not independently execute browser harness. Prior independently verified 50 Python and 4 Node tests remain applicable; only this narrow completion branch and scenario changed afterward.

Remaining findings by severity: CRITICAL none; HIGH none; MEDIUM none; LOW none. No blocking findings in this first implementation slice. This is code approval, not live route activation, full future-plan completion or creative acceptance. Skill-perspective check remains as documented: named skills unavailable, explicit supplied criteria applied, no violations found.

# Narrow reopen-control follow-up

Disposition unchanged: CLEAR / APPROVE; blockers []. Inspected production_workspace.mjs:238–239 and 264–280 plus seventh browser scenario at tests/storyboard-workspace.browser.mjs:121–129. Reopen saved plan delegates to the same guarded loader as project selection. Explicit discard confirmation occurs before epoch changes; canceled reopen preserves edits, confirmed reload respects newer-navigation and edit-during-load guards. Updating picker on accepted load keeps selection aligned with displayed project. The extraction removes duplicate behavior rather than adding an unnecessary abstraction. No new CRITICAL, HIGH, MEDIUM or LOW findings, and no skill-perspective violations. Parent reports seven browser scenarios and four Node tests passing; reviewer inspected this narrow change and test without rerunning broader tests or activating services.
