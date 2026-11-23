# P5.1 reference bank code review

codeQualityStatus: CLEAR
recommendation: APPROVE
blockers: []

Scope: REFERENCE_REVIEW_BRIEF.md in .codex/artifacts/storyboard-implementation, P5.1 Ruling in that directory's progress.md, and P5.1 in studio/plans/best-storyboard-creator-assistant.md. Root HEAD 34ec01d6c20a5663b438e2ce3ffbdec67e67761d; PromptBuilder HEAD a4c07bac5173b8d27b463dc2082e9cba98c09fcb. Unrelated dirty work excluded. No implementation changes made.

Reviewed studio/production_references.py, studio/tests/test_reference_requirements.py; scoped store assets-only commit, bootstrap requirement extraction, wardrobe validation and Master guide; pack production_api.py reference routes, web_api.py media roots, web/production_workspace.mjs reference integration, web/storyboard_references.mjs and its Node/browser tests, and tests/test_production_api.py. Consulted asset_intake's directory/read_stable/inspect_image and native asset loader-path contract. Graph architecture consulted for both owners; new frontend module was absent in graph, so raw source was inspected. Several surrounding files are untracked prior work, so Git HEAD is not a complete before-image of this slice.

## Findings

CRITICAL: None.
HIGH (Important): None.
MEDIUM: None.
LOW (Minor): None.

No actionable introduced correctness, scope-control, regression or maintainability defect identified. Hash/source records remain separate from role/entity/outfit binding records; each binding has explicit input authorization and separate exact-binding/hash/context reviews. Stale project revisions and old binding IDs are rejected. Source containment reuses descriptor-based no-follow checks. Assets-only commits preserve other asset keys and use existing revision history and CAS publication. UI guards dirty edits, obsolete project views and late candidate previews.

## Skill-perspective check

remove-ai-slops and programming were not listed and no SKILL.md for either was found under /home/athar/.agents or /home/athar/.codex. Applied the task's documented criteria explicitly to production and test code. No violation found: tests exercise behavioral source changes, distinct owners/outfits, authorization versus review, persistence/reopen, stale revisions, filesystem containment and guarded routes. No deletion-only or brittle prompt tests, untyped escape hatches, or unnecessary extraction/normalization identified. Path checks and role translation occur at the required boundary.

## Verification

Independently ran PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider studio/tests/test_reference_requirements.py together with pack route tests: 18 root cases passed; pack collection initially errored because the combined root invocation imported its __init__ without package context. Reran pack tests with --import-mode=importlib --rootdir=custom_nodes/ComfyUI-Fantastic-MiniMaxH3-PromptBuilder/tests: 3 passed in 4.25s. Node --test tests/storyboard-references.test.mjs: 1 passed. No live project routes, model jobs or service controls invoked.

Inspected existing evidence: .codex/artifacts/storyboard-implementation/reference-root-suite.txt ends with 500 passed, 96 subtests passed; reference-pack-tests.txt ends with 19 passed; reference-tests.txt ends with 34 passed. These are artifact observations, not a fresh full-suite run. Read all four browser test cases; did not independently execute them or claim their reported passes as freshly verified.

## Declined to judge

- Live backend activation: brief explicitly states running process predates new routes; no restart or live mutations authorized.
- Human likeness/outfit/creative acceptance and live browser usability: source/tests are insufficient; no visual acceptance performed.
- GPU generation, RefMod/still compilation, endpoint approval, multi-document acceptance, video handoff and later P5/P8 features: outside slice.
- All unrelated prior dirty work and whole-stack regressions: excluded by review scope.
- Long-bank performance: no representative scale benchmark performed.

Report placement: omo-agent-toolkit ulw-loop status --json failed because installed runtime target /home/athar/.codex/plugins/cache/sisyphuslabs/omo/5.1.21/dist/cli/index.js is missing. No attempt directory could be obtained; used fallback .omo/evidence/reference-bank-code-review.md. Notepad: .codex/artifacts/storyboard-implementation/progress.md (read only). This report is the only intentional workspace write, required by reviewer reporting instructions.
