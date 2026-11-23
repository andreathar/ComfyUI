# Storyboard frame jobs code review

codeQualityStatus: CLEAR
recommendation: APPROVE
blockers: []

Scope: read-only review of frame_jobs.py, storyboard_reference_node.py, production_api.py, web_api.py and corresponding tests in custom_nodes/ComfyUI-Fantastic-MiniMaxH3-PromptBuilder; studio/still_recipe.py, studio/storyboard_workspace.py, relevant tests and worker.add_references integration. Approval covers this code slice, not live model execution or creative acceptance. The checkout was concurrently edited; final checks below include the owner's fixes prompted by this review. No production files were changed by the reviewer.

## Findings by severity

- CRITICAL: none remaining.
- HIGH: none remaining.
- MEDIUM: none remaining.
- LOW: none remaining.

## Resolved during review

- FrameJobs._current originally recompiled against the saved whole-project revision, and _draft required matching start/end revisions. This prevented an accepted start from being used after editing only the end description or unrelated project content. The owner changed freshness to recompile against the current revision and compare the frozen relevant digest/graph; start/end ownership now checks project and shot. Independently inspected the final implementation and passed its new unrelated-revision regression.
- FrameJobs.read originally mapped confirmed native interruption after an owned cancel to generic failure. The owner now requires both the durable cancellation marker and matching native execution_interrupted evidence, and persists a request-bound terminal receipt. Independently inspected this implementation and passed cancellation, restart and unowned-interruption regressions.

## Independent verification

- `.venv/bin/python -m pytest custom_nodes/ComfyUI-Fantastic-MiniMaxH3-PromptBuilder/tests/test_frame_jobs.py custom_nodes/ComfyUI-Fantastic-MiniMaxH3-PromptBuilder/tests/test_storyboard_reference_node.py custom_nodes/ComfyUI-Fantastic-MiniMaxH3-PromptBuilder/tests/test_production_api.py --rootdir=custom_nodes/ComfyUI-Fantastic-MiniMaxH3-PromptBuilder/tests --confcutdir=custom_nodes/ComfyUI-Fantastic-MiniMaxH3-PromptBuilder/tests --import-mode=importlib -q --tb=short`: 27 passed in 5.76s.
- `.venv/bin/python -m pytest studio/tests/test_still_recipe.py studio/tests/test_storyboard_workspace.py -q --tb=short`: 33 passed in 0.37s.
- The first combined root-level invocation encountered the pack's relative-import collection failure; using the existing isolated pack test invocation resolved collection. Intermediate runs observed the newly added regression tests fail before their corresponding production fixes. The final commands above passed after those fixes.
- Inspected native PromptQueue.interrupt_if_running and delete_queue_item mutex behavior, source containment/stable-byte reads, output receipt checks, reviewed-start handoff and reference execution hash verification.
- No server launch, GPU generation, media creation or live creative review was performed. Mocked queue tests establish the exercised contracts, not complete live integration proof.

## Skill-perspective check

The remove-ai-slops and programming skills were absent from the provided skill catalog and searches of /home/athar/.agents/skills, /home/athar/.codex/skills and the plugin cache. Applied their documented prompt criteria directly before judging maintainability and test relevance. No deletion-only tests, requested-removal-only tests, tautological tests, unnecessary extraction/normalization, untyped escape hatches or needless abstractions were found in the reviewed slice. Recipe wiring assertions verify actual graph dependencies and effective seed/reference bindings; prompt assertions check propagation of supplied scene/entity information rather than broad exact prose snapshots. The newly added regression tests exercise observable freshness and cancellation behavior. No remaining violation of either perspective identified.

## Evidence and scope limitations

The parent supplied file scope and review concerns, but no standalone success-criteria package or notepad path. No executor success claim was accepted without independent inspection. `omo-agent-toolkit ulw-loop status --json` failed because its configured runtime target was missing, so this report uses the required fallback location. Graph architecture was consulted first; its indexed file coverage did not contain all new files, so raw current source and diffs were inspected for those files.
