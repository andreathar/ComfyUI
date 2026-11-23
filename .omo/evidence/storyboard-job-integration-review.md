# Story job integration code review

codeQualityStatus: BLOCK
recommendation: REQUEST_CHANGES

Scope: P4.3 creator queue integration only. Parent HEAD 34ec01d6c20a5663b438e2ce3ffbdec67e67761d; PromptBuilder HEAD a4c07bac5173b8d27b463dc2082e9cba98c09fcb. Reviewed untracked production_jobs.py, optional jobs routes in production_api.py, web_api.py registration, analysis and shared preview changes in web/production_workspace.mjs, test_production_jobs.py, job API test, and three new browser scenarios. Existing project persistence/runtime/node contracts were consulted only as dependencies. Unrelated dirty work was excluded and untouched.

Plan: studio/plans/best-storyboard-creator-assistant.md P4.3. Notepad: .codex/artifacts/storyboard-implementation/progress.md, including durable UUID ruling at line 91. Success criteria: visible native admission, no replay after ambiguous reply, targeted cancellation, released source-matching proposals, preservation of newer drafts and recoverability after reload/tabs.

## CRITICAL
None identified.

## HIGH
H1 — A stale second tab can replace the sole recovery record for a running job.

References: custom_nodes/ComfyUI-Fantastic-MiniMaxH3-PromptBuilder/web/production_workspace.mjs:192 (savedAnalysis snapshot), :300–310 (unconditional storage replacement before admission), :268–279 (resume only that record); production_jobs.py:94–97 (reject competing job before its request is saved).

Deterministic source-level scenario: open two creator tabs while no analysis exists. Tab A submits and queues UUID A. Tab B retains its initial null savedAnalysis and enabled Analyze button. B submits UUID B, overwriting comfy.storyboard.analysis.v1 before calling the server. The server rejects B while A is running. Reload both tabs: both load B; its status is 404, and retry resubmits B. A remains on the native queue and its files survive, but the creator has no listing/discovery route or ID entry to recover A's review/cancel flow. After A finishes, retry can instead start B, leaving A's result inaccessible through the intended creator flow. This breaks the expressly requested cross-tab/reload recovery criterion, not merely a stylistic preference.

Required: preserve and reconcile outstanding job identities across tabs before admission, including simultaneous submissions; do not let rejected competing submissions replace the only recoverable active record. Add a two-context browser regression covering B rejection, reload, and recovery of A. A simple read-then-write check alone does not cover simultaneous tabs.

## MEDIUM
None independently identified. The missing cross-tab test belongs to H1 rather than a separate duplicate finding.

## LOW
None identified.

## Verification
- Independently ran .venv/bin/python -m pytest on tests/test_production_jobs.py and tests/test_production_api.py with --rootdir=<pack>/tests --confcutdir=<pack>/tests --import-mode=importlib -q: 14 passed in 4.18 seconds. Only pytest-asyncio fixture-scope deprecation warning.
- Independently ran node --test tests/storyboard-workspace.test.mjs: 4 passed.
- Inspected all three added browser scenarios. They exercise same-window double-click/cancel, ambiguous response/reopen, and late review/create preserving newer draft. They do not exercise two independent contexts sharing storage. Browser suite was not rerun by this reviewer; primary's ten-case pass is a reported result, not independently reproduced here.
- Inspected native execution.py:1380 interrupt_if_running: match and interrupt are under queue mutex. Pending cancellation uses exact owned graph; service tests verify unrelated running job is untouched. No actual GPU cancellation qualification claimed.
- Durable request publication precedes validation/queue insertion; replay of saved IDs returns status instead of enqueuing. Cancellation during awaited validation is checked before admission. Error history is terminal even with completed=false. Successful proposal requires native completion, released state/proposal and matching source/project inputs.
- Epoch/version guards protect late requests within one creator. Storage failure before analysis prevents queue admission. These are meaningful safeguards but do not resolve H1.

## Skill perspectives and review limits
Consulted /home/athar/.codex/skills/code-review/SKILL.md and .codex/AGENT_TOOLING.md. Searched installed .codex/skills, .agents/skills and plugin cache for remove-ai-slops and programming SKILL.md; neither was available. Applied their criteria supplied in reviewer instructions explicitly to production code and tests. No deletion-only, removal-only, tautological, brittle prompt-string, or constant-only test was identified in the scoped additions. Queue doubles establish observable admission/cancellation/result contracts; fixed graph assertions protect actual provenance. Filesystem containment, UUID/request checks and release/source checks serve real boundaries. No unnecessary extraction/normalization, untyped escape hatch or needless abstraction was found in this slice. No skill-perspective violation identified beyond the actual recovery bug above.

Graph list_projects and owner get_architecture ran first. Owner search_graph for StoryJobs/readAnalysis returned no results; these untracked files are a graph coverage gap and were reviewed as raw source. Verified live Git HEADs and dirty status. CodeRabbit was not run: the mixed dirty owner contains unrelated new files, the required new slice is untracked, and available documented selectors cannot safely select this exact partial-file slice without changing index/commits or transmitting unrelated context. No remote transmission, paid continuation, service restart, native job submission or implementation edits occurred.

omo-agent-toolkit ulw-loop status --json failed because its installed runtime target is missing. No attempt directory could be obtained; used fallback .omo/evidence/storyboard-job-integration-code-review.md and provided the parent-requested report alias .omo/evidence/storyboard-job-integration-review.md.

Blocker: H1. Real activated-route and model/GPU qualification remain outside this review and must not be inferred from mocked browser or Python passes.
