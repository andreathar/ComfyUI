# Shot production code review

codeQualityStatus: BLOCK
recommendation: REQUEST_CHANGES

Reviewed 2026-11-15 in `/mnt/data/Projects_SSD/ComfyUI`. Scope: new `studio/master_take.py`, `studio/tests/test_master_take.py`, workflow builder diff, and PromptBuilder component changes to `web/promptbuilder.js`, `web/promptsource.js`, `web_api.py`, and the two new source-save tests. Unrelated requirements.txt and historical branch changes excluded. No implementation edits, live artifact writes, GPU jobs, service actions, or browser mutations performed.

Authority inspected: `.codex/artifacts/production-decision-audit-20261115/SHOT_PRODUCTION_READINESS.md`; execution ledger/notepad: `.codex/artifacts/shot-production-20261115/IMPLEMENTATION.md`. Success requires selected-shot source authority, preserved drafts, immutable preparation reaching the encoder, exact take reconciliation and human review.

## CRITICAL

None found.

## HIGH / Important

1. **A persisted draft can overwrite another shot after reopening the editor.** `custom_nodes/ComfyUI-Fantastic-MiniMaxH3-PromptBuilder/web/promptbuilder.js:3100`, `:3138`, `:4395`, `:7075`. The new source binding belongs to the selected shot at editor open, but draft identity remains solely `node.properties.mmh3_draft_id` (`:2395`). Constructor restoration loads that same draft and automatically enters draft mode. `enterDraft` (`:3864`) restores its state without source identity; the draft payload has no shot/library-source binding. Reproduction: edit a text-only SH05 draft, close while keeping it, select SH06 on the same Master node, reopen, then Commit to Live. The restored state is SH05's draft, whereas `this.source` and its optimistic version are freshly loaded from SH06. `saveSource` accepts that pair because SH06 is still selected, writes SH05's draft into SH06's authoritative library entry, and `_doCommit` clears the shared draft. The generic existing live-overwrite confirmation does not identify this cross-shot mismatch. Preserve/source-bind drafts and require an explicit transfer when their originating shot differs; cover close/switch/reopen/commit, not only changing selection in an already-open editor.

2. **Preparation does not establish that the frozen package reaches the generation path.** `studio/master_take.py:24-29`, `:44-55`. Checking class names and node 22's prompt_text link leaves builder_state, media, RefMods, seed and downstream encoder consumption unchecked. For example, changing the encoder prompt input to a literal old prompt while retaining node 22 and its resolver link passes preparation. Likewise disconnecting the media-state resolver edge leaves mutable/stale media inputs in use. The code still emits authority='Frozen selected shot library revision'. History/sidecar equality later proves only that this same graph ran, not that generation consumed the advertised package. The provided preparation fixture itself contains no encoder or output dependencies and passes. Validate the narrow Master graph's effective package-to-encoder/reference/output connections before allocating/marking a take prepared; add a fixture with actual compilation structure and rejection cases for disconnected or bypassed links. This is a provenance failure in the central goal, not a request for general graph validation infrastructure.

## MEDIUM

1. **A draft with owned media/RefMods has no commit path after following the displayed instruction.** `custom_nodes/ComfyUI-Fantastic-MiniMaxH3-PromptBuilder/web/promptbuilder.js:4391-4393`. The new unconditional truthiness check blocks all drafts with owned arrays (including intentionally empty arrays). Saving those presets does not reset/acknowledge `draftEntry.media` or `draftEntry.refmods`; the guard remains true on every attempt. The message tells users to save presets before committing, but that does not satisfy the condition. Provide an explicit, verified acknowledgment/detach path that preserves the draft, or make the message/action describe a real supported recovery. This does not affect the text-only first render, but is a regression for existing draft editing in newly bound workflows.

## LOW

1. `studio/tests/test_master_take.py:39` names a modified-input binding check, but the test never modifies prompt.json. The hash enforcement itself is direct and appears correct; add the actual mutation assertion or rename the test to avoid overstated coverage.

## Verification and skill perspectives

- MCP graph discovery ran first and returned zero projects. Read-only local CLI fallback (`codebase-memory-mcp cli --json list_projects`, then `get_architecture` for the returned `mnt-data-Projects_SSD-ComfyUI`) found the canonical graph. Raw source/diff inspection establishes the findings above; graph output alone was not treated as proof of runtime behavior.
- `omo-agent-toolkit ulw-loop status --json` failed because its installed runtime target is missing. No attempt directory could be obtained; this report uses the required `.omo/evidence/<goal>-code-review.md` fallback.
- `remove-ai-slops` and `programming` were absent from the available skill catalog and their expected local skill paths. Their documented criteria in the reviewer instructions were applied directly to production code and tests. No deletion-only, tautological, brittle prompt-string, or constant-mirroring tests were found. The narrow source helper and take owner are reasonable; no needless production parsing/normalization or untyped escape hatch was found. The behavioral coverage gaps above violate the intended correctness/false-confidence perspective, rather than indicating generic slop.
- Independently ran `python -m unittest studio/tests/test_master_take.py`: 4 passed, 0 failed.
- Independently ran `node --test custom_nodes/ComfyUI-Fantastic-MiniMaxH3-PromptBuilder/tests/promptsource.test.mjs`: 3 passed, 0 failed.
- Independently ran `python -m unittest discover -s custom_nodes/ComfyUI-Fantastic-MiniMaxH3-PromptBuilder/tests -p test_prompt_source_save.py`: 1 passed, 0 failed.
- All tests use temporary fixtures/mocks; no supplied test establishes live browser draft behavior or the complete Master encoder graph. The report does not claim those runtime checks passed.
- Exact history graph matching, one-time submission transition, optimistic save revision check, review-video hash checking, and resolved review-output directory containment are useful protections. They do not resolve the two HIGH findings.

## Blockers

- Bind persisted drafts to their originating shot/library source and prevent silent cross-shot commit on reopen.
- Establish the actual frozen package-to-generation connections before asserting prepared source authority.

Approval remains withheld until both HIGH findings are fixed and covered with focused behavioral tests.
