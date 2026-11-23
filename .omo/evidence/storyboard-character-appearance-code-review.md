# Character appearance editor review

codeQualityStatus: CLEAR
recommendation: APPROVE
blockers: []

Scope: renderProject character appearance controls and insertion in production_workspace.mjs, browser appearance-save scenario, and new appearance/reference invalidation test in studio/tests/test_reference_requirements.py. Other concurrent changes excluded.

CRITICAL: none.
HIGH: none.
MEDIUM: none.
LOW: none.

No concrete regressions found. Each textarea closes over its own character in the active snapshot.production; input updates only appearance, then uses the existing dirty/editCounter tracking. Saved payload already clones that current production document and uses its project/revision, preserving stale-save rejection and response guards. Dirty guards also prevent reference changes and frame generation until saved. Newer edits during save remain on the current document via existing counter handling. Switching projects rerenders controls from the new snapshot rather than sharing character objects between projects.

The editor does not mutate project.source_text, script references, entity IDs, reference bindings or approval receipts. Changes use the existing production-store history path. production_references includes appearance in identity context and wardrobe context, so changing it renders prior bindings needs_rebinding while preserving their records. The explanatory text correctly alerts the user that selection/review may be required again. Reverting to exactly the prior appearance can restore matching context; wording does not falsely imply irreversible loss of approval.

The added Python test exercises kept identity binding -> appearance edit -> needs_rebinding while retaining binding identity. The browser test checks warning visibility and edited appearance in the save payload; it does not independently prove reopen/history or delayed-response behavior, which rely on established paths and earlier tests. No new production special case bypasses those paths.

Independent validation: studio/tests/test_reference_requirements.py — 23 passed in 1.82s; JavaScript syntax check passed. Browser scenario inspected, not executed by reviewer. Named remove-ai-slops/programming skills remain unavailable; supplied criteria applied, no test slop or needless complexity identified. This is a small direct field editor, with semantic invalidation coverage rather than implementation-only assertions.

Report uses required fallback path; ledger/notepad: .codex/artifacts/storyboard-implementation/progress.md. No implementation, runtime or model changes made by reviewer.
