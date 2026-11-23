# Project-aware Master resolver review

codeQualityStatus: BLOCK
recommendation: REQUEST_CHANGES
blockers: [legacy standalone import regression]

Scope: studio/master_studio_package.py, its tests, and dual-import change in studio/h3_recipe.py. Existing shared dirty work excluded. No live canvas or model work performed.

## CRITICAL
None.

## HIGH
Legacy standalone imports now require repository root on sys.path. master_studio_package.py:16 eagerly imports `from studio import production_store` in the top-level/script branch. Previously its imports were satisfied by the studio directory alone. Independent reproduction from /tmp: `/mnt/data/Projects_SSD/ComfyUI/.venv/bin/python -I -c "import sys; sys.path.insert(0, '/mnt/data/Projects_SSD/ComfyUI/studio'); import master_studio_package"` fails ModuleNotFoundError: No module named studio. This breaks existing direct/script-style callers before the legacy resolver can execute. Root-only new subprocess coverage does not catch it. Preserve legacy standalone import/use without forcing an unused project-store dependency, and test both isolated import forms.

## MEDIUM
None confirmed.

## LOW
None.

New project-aware path explicitly requires workspace/registered recipe, selected shot binding, explicit bounded integer seed and transition presence. It checks selected asset locations against native/configured roots before delegating to existing compiler and rechecks project revision after compilation. Returned metadata marks draft_uncommitted and includes project revision. Existing legacy live_resolver_code executed successfully under original test harness (9 tests passed before import follow-up), but this does not prove standalone module import compatibility. The h3_recipe conditional relative import itself is coherent.

Coverage observations sent to parent: initial new fixtures only exercised picture references, leaving nonempty RefMod stack/configured roots untested; transition presence accepted arbitrary values, with downstream behavior still to be confirmed. These observations are not independently classified as correctness failures. Do not describe this disk resolver as an activated project-aware Master canvas: live_resolver_code still calls legacy resolver without project arguments.

Required remove-ai-slops/programming skills unavailable as previously documented; applied explicit supplied criteria. Cross-project isolation and selected compiler contract comparisons are useful behavior tests; no tautological/removal-only tests or needless production abstraction found. Required fallback report location used; notepad .codex/artifacts/storyboard-implementation/progress.md.
