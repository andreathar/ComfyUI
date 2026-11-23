# Klein prompt presentation review

codeQualityStatus: CLEAR
recommendation: APPROVE
blockers: []

Scope: prompt_review construction in studio/still_recipe.py, related test in studio/tests/test_still_recipe.py, and presentation/role addition in PromptBuilder web/production_workspace.mjs and its browser test. Other uncommitted features excluded.

CRITICAL: none.
HIGH: none.
MEDIUM: none.
LOW: none.

Sections reuse scene_text, people, props, endpoint description and labels already used in prompt construction. Reference numbering enumerates refs in the same order passed into worker.add_references; inspection of that helper confirms it chains reference latents in that order. The appended kept start reference therefore keeps its actual image number rather than being relabeled Image 1. Character and prop wording is preserved; added section separators do not replace the exact full prompt, which remains visible.

prompt_review is computed after the graph/dependencies digest and is not included in its payload. The UI reads it as textContent, adds the conditional identity-conflict reminder for selected identity references, and continues submitting the original input_digest. No approval shortcut, model parameter change, new parser or alternate prompt compilation path introduced by this presentation. Existing selection/revision/dirty guards remain around display and generation. An older response without prompt_review still shows the complete prompt and generation controls. Reminder describes a possible conflict rather than claiming automatic conflict detection or a model identity guarantee.

Validation: independently ran studio/tests/test_still_recipe.py (20 passed) and storyboard-workspace.test.mjs (7 passed). Inspected the browser scenario that asserts character words, reference assignment, reminder, and explicit not-generated state; did not execute browser harness. Tests are relevant semantic presentation checks rather than brittle full prompt snapshots. Required programming/remove-ai-slops skills unavailable as previously documented; supplied perspective criteria applied, no violations found.

Compatibility limitation: still_recipe.py and its tests are untracked, and parent confirms no preserved pre-change source snapshot. KLEIN_IDENTITY_COMPARISON.md records run comparison and the known identity mismatch, but does not contain a complete baseline source/compiled prompt/digest suitable for independent byte-for-byte compatibility verification. Current construction and payload separation support the intended unchanged semantics; exact historical equality is not independently established. This is an evidence limitation, not an identified regression.

Evidence/notepad: .codex/artifacts/storyboard-implementation/KLEIN_IDENTITY_COMPARISON.md and progress.md. Required fallback report path used because no usable ULW attempt is available.
