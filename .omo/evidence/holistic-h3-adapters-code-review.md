# Reference adapter review

codeQualityStatus: CLEAR
recommendation: APPROVE

## Final re-review
Original HIGH finding below is resolved. Both adapters now initialize all dynamic outputs with native ExecutionBlocker before parsing; their success path replaces them only at completion. The fixture explicitly enables unrestricted imports for both scripts, and native execution.py handles ExecutionBlocker inputs before calling consumers. Missing aliases/variables or invalid selection therefore block dependent encoding instead of sending sentinel text. Global variables followed by scene-variable overrides are direct and scoped; unresolved/malformed tokens block.

Independently ran `PYTHONPATH=. .venv/bin/python .codex/artifacts/holistic-h3-audit/test_adapters.py`: **9 passed**. Independently ran `check_recursion.py`: **passed, 21 cloned nodes, qualified IDs 62:24/62:29, model loaders external**. This is installed-method AST execution with a stubbed node registry, not a full recursive render. Live CPU Shot1/Shot2 results are lead-reported and were not rerun by this reviewer. Initial catalogue remains limited to pictures and one visual RefMod. Supplied programming/remove-ai-slops criteria reapplied; no additional material violations found.

Current severity findings: CRITICAL none; HIGH none; MEDIUM none within initial supported catalogue; LOW none. Current blockers: []. Recommendation APPROVE for this adapter scope. Historical review follows.

Scope: `.codex/artifacts/holistic-h3-audit/select-references.py` and `resolve-prompt.py`, hosted by existing DynamicScriptNode. Initial catalogue explicitly limited to picture media and one visual RefMod. No source/canvas/runtime edits; local pure-Python examples only.

## CRITICAL
None.

## HIGH
**Resolver failures do not stop generation.** `resolve-prompt.py:1,19,23` initializes ordinary STRING outputs to `INVALID_REFERENCE_PROMPT` and raises on unbound/disabled/malformed aliases. `custom_nodes/comfyui_dynamic/nodes/dynamic_script_node.py:486-508` catches Exception and returns the exception plus those ordinary outputs. The encoder can consume the sentinel as a valid prompt and continue an expensive incorrect render. Local reproduction with disabled and missing reference aliases retained both sentinel strings after ValueError, exactly as the host's exception-return branch does. Use an explicit supported execution-blocking value/gate before encoding/sampling; do not equate a Python raise inside DynamicScript with graph failure. Also wire dynamic output slots correctly: fixed exception output is slot 0, `outputs[0]` is actual graph slot 1.

## MEDIUM
No additional blocker for the explicitly bounded initial catalogue. Future generalization needs two explicit contracts: RefMod aliases currently select only the first truthy visual/audio channel, and native captions are basenames rather than globally unique file identifiers. Dual-channel assets and same-caption files from different folders can resolve incompletely or ambiguously. Do not advertise support for these without a defined mapping; initial single visual RefMod avoids this ambiguity.

## LOW
None.

## Confirmed behavior
- Selector skips disabled picture media before assigning picture captions, matching native `reference_lines` numbering.
- Resolver reads actual native map tags rather than predicting RefMod offsets. Two map rows for a copied RefMod correctly yield both tags joined by `and`.
- Disabled/zero-weight RefMods produce no native rows, so referenced aliases are rejected by resolver logic (but currently not by the execution graph, as above). Unused inactive aliases need not reject a shot.
- Missing catalogue shot/asset entries fail selection. Invalid RefMod selection JSON is rejected by the native Stack; MediaLoader alone can turn corrupt JSON into an empty list. Do not rely on every downstream native consumer having the same failure policy.
- Empty `FantasticLoraLoaderMulti` payload `{}` or `{"loras":[]}` is a safe no-LoRA default: `_parse_payload` returns empty entries and `_apply_chain_collect` returns original MODEL/CLIP without loading weights; `_stack_list_from_data` emits an empty stack. This does not introduce a turbo or character LoRA implicitly. Nonempty missing filenames are skipped with warnings, so a named preset is not proof of applied weights.

## Evidence and review perspective
Read source for both adapters, native `refmod_nodes.reference_lines`, `refmods.pick_channels`, DynamicScriptNode execution exception handling, LoRA parsing/application. Ran pure scripts with disabled first picture and copied visual RefMod: output resolved to `Use <Picture 1> and <Video 1> and <Video 2>`; missing/disabled aliases retained sentinel prompt strings on exception. No live render required.

The remove-ai-slops/programming skill files remain unavailable from the prior skill lookup; supplied criteria applied. No unnecessary abstractions or extraction identified: JSON bindings and native map parsing serve this workflow boundary. No implementation-mirroring tests added. Main issue is concrete host-contract correctness, not style.

Historical blocker: resolver failure needed to block downstream encoding/sampling. Resolved as documented above.
