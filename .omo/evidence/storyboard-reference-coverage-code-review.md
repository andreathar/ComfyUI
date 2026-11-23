# Reference coverage review

codeQualityStatus: CLEAR
recommendation: APPROVE
blockers: []

Scope: reference_coverage additions in storyboard_workspace.py, tests/test_reference_requirements.py, prompt-review coverage display in PromptBuilder production_workspace.mjs and its browser fixture. Other shared changes excluded.

CRITICAL: none.
HIGH: none.

MEDIUM: none remaining. The initial duplicate bank inspection finding is resolved: reviewed_references returns its evaluated rows, and both draft paths reuse them. A caller search confirms both callers unpack the new return shape. Coverage now describes the same bank snapshot used for validation.

LOW: none.

Coverage filters to requirements associated with the selected shot and marks actual requested keys, including ready-but-omitted references and unsupported roles. Existing selected-reference validation remains unchanged. Added metadata is outside compiler graph/digest and FrameJobs compares only graph/input_digest, so omissions/status metadata does not invalidate job identity. The kept start-frame reference is separate from bank requirements and remains described in prompt references; coverage is not a complete enumeration of every encoder input. UI text says not included rather than missing, avoiding a false missing-image claim for deliberately unchecked ready references. Older draft responses without coverage continue rendering.

Independently ran studio/tests/test_reference_requirements.py: 25 passed in 3.94s after the fix. Browser scenario inspected, not run; it tests visible omitted location disclosure. Missing direct cases: ready-but-unchecked requirement, stale unselected binding, unsupported role, and multiple shots proving exact exclusion. Existing code appears to handle these, so these are coverage opportunities rather than additional findings.

Required remove-ai-slops/programming skills unavailable; applied supplied criteria. Tests are behavior-oriented. The repeated extraction is removed and no remaining violations were found; no brittle prompt snapshot or deletion-only tests found. Fallback report path used; notepad .codex/artifacts/storyboard-implementation/progress.md. No implementation edits or runtime operations performed.
