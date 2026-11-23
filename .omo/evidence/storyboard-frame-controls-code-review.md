# Storyboard frame controls follow-up review

codeQualityStatus: CLEAR
recommendation: APPROVE
blockers: []

## Final re-review after fixes

All three findings below are resolved in the subsequently inspected implementation; they are retained as historical findings only. The admission record now includes the full request, the UI offers explicit same-ID retry and guarded discard, and FrameJobs.abandon uses the same admission flock plus a durable tombstone checked before request publication. A delayed request cannot pass that tombstone. Refresh responses carry jobsVersion checks and review submission invalidates earlier reads. Per-job browser locks serialize review writes, and cleanup compares the currently stored recovery ID before deletion.

Inspected the new end-frame selector and staged-input controls: the draft and submitted request bind the selected kept start ID, staged start filename and selected reference staging map; changes to those values invalidate the prepared draft. The backend rechecks current kept-start status, same project/shot ownership and matching staged hashes. No concrete remaining blocker found in the reviewed changes.

Independent final checks: focused test_frame_jobs.py, test_frame_integration.py and test_production_api.py using the isolated pack pytest invocation: **27 passed in 7.28s**. `node --test custom_nodes/ComfyUI-Fantastic-MiniMaxH3-PromptBuilder/tests/storyboard-workspace.test.mjs`: **7 passed**. Inspected the browser test source for output-reference staging, kept-start selection, recovery, stale list responses and review-key replacement; did not independently execute that browser suite or generate media. Skill-perspective assessment unchanged: supplied criteria applied, no new violation identified.

Snapshot review of new FrameJobs.list, start/end draft handoff, test_frame_integration.py, and web/production_workspace.mjs. Implementation is being edited concurrently; the owner has acknowledged these findings and started fixes. This report records the inspected frontend snapshot, not an assertion that later edits retain these defects.

## CRITICAL

None.

## HIGH

1. `custom_nodes/ComfyUI-Fantastic-MiniMaxH3-PromptBuilder/web/production_workspace.mjs:540` (through 562): saving only a job locator before submitting loses the request body needed for same-ID recovery. If generation fails before request publication (stale project, another queued frame, or network failure before reaching the server), every subsequent generation attempts GET of the missing ID and fails with 404. The saved global admission marker is never cleared by an available recovery action. All shots/projects remain blocked until manual localStorage deletion. Preserve the request and expose safe same-ID retry or guarded abandonment that excludes delayed admission.

## MEDIUM

2. `custom_nodes/ComfyUI-Fantastic-MiniMaxH3-PromptBuilder/web/production_workspace.mjs:449`: refreshJobs has no response ordering guard. An earlier GET captured before a Reject can arrive after the post-review refresh and replace the UI with the earlier Keep state. Sequence refreshes and invalidate pending reads when review changes begin; do not present superseded approval state.

3. `custom_nodes/ComfyUI-Fantastic-MiniMaxH3-PromptBuilder/web/production_workspace.mjs:484`: a completed review request unconditionally deletes the shared localStorage review key. Another tab can have replaced that key with its newer pending review after observing the first review on the server but before the first tab receives its response. The old response deletes the newer review's recovery ID. Compare the currently stored ID before deletion and serialize updates to this per-job shared key.

## LOW

None.

## Verification and perspectives

Independently inspected the backend list and real-store handoff test; no additional concrete backend blocker found. Ran `.venv/bin/python -m pytest custom_nodes/ComfyUI-Fantastic-MiniMaxH3-PromptBuilder/tests/test_frame_integration.py --rootdir=custom_nodes/ComfyUI-Fantastic-MiniMaxH3-PromptBuilder/tests --confcutdir=custom_nodes/ComfyUI-Fantastic-MiniMaxH3-PromptBuilder/tests --import-mode=importlib -q --tb=short`: 1 passed in 6.16s. The test uses real project/reference persistence and graph compilation with a mocked native queue and validation; it does not prove live generation. No live generation performed.

remove-ai-slops/programming skill files remained unavailable as documented in the earlier frame-jobs report. Applied the supplied skill criteria directly. The new integration test exercises meaningful behavior rather than mirroring implementation constants; no additional slop/overfit violation found. No supplied notepad path. ulw-loop CLI runtime was unavailable during this review session, so the required fallback evidence path is used.

Historical blockers above are resolved by the final re-review recorded at the top of this report.
