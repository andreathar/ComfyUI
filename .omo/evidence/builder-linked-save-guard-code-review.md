# Builder linked-input Save guard review

codeQualityStatus: CLEAR
recommendation: APPROVE
blockers: []

Scope: newly added assertPromptSaveTarget helper, checkPromptSaveTarget/writeNode/save/requestClose/_doCommit guard changes, and focused linked-input test. Existing source-library and reference-inspection changes visible in the broader dirty diff were not treated as newly implemented scope.

CRITICAL: none.
HIGH: none.
MEDIUM: none.
LOW: none.

No concrete regression found in the narrow guard. It checks either prompt_text or builder_state input with `link != null`, correctly rejecting link ID zero and permitting undefined/null links. Unrelated media links do not block normal editing. The existing explicit loaded source continues through persistSource/saveSource, preserving its selected-library path and version check.

Save checks before persistence and again in writeNode after the await, so an initially unlinked/source-less editor cannot write or claim success if a prompt link appears during that boundary. Save-on-close only closes after successful writeNode for dirty unbacked edits, keeping blocked work in the editor. Commit checks before the await and again afterward, before adopting live state, applying draft-owned media, or clearing draft storage. There is no await between the second check and writeNode/clear, so normal event-loop link changes cannot interleave that synchronous section. A rejected commit keeps its draft and does not toast success. Already-clean close and deliberate Cancel retain existing behavior.

This is an unbacked-linked-input safeguard, not proof that an arbitrary retained prompt_library_source is the actual source of every incoming link. Dynamic source/selector changes during an in-flight source-backed HTTP save and full editor/source ownership remain the separate existing source-round-trip contract; this change does not add a graph-source identity verifier. Do not advertise it as one.

Independent verification: node --test tests/promptsource.test.mjs — 5 passed; node --check web/promptbuilder.js passed. Unit coverage exercises both linked fields, allowed explicit source, unlinked state and link0. Parent reports an isolated real PrimitiveString→Builder scenario where Save remained open/unchanged until disconnection; reviewer inspected implementation and did not independently rerun that browser scenario. Save-on-close and Commit guards were verified by control-flow inspection, not claimed as browser-tested. Additional integration coverage for these two paths would improve future regression protection but no demonstrated failure blocks this narrow change.

Required remove-ai-slops/programming skills unavailable as previously documented; supplied perspectives applied. Focused helper test checks meaningful linked-state behavior rather than removal or implementation constants; no needless extraction/parsing introduced. Required fallback report location used. No implementation, canvas, library or runtime modifications made by reviewer.
