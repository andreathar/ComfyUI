# Draft storyboard to Master handoff review

codeQualityStatus: CLEAR
recommendation: APPROVE
blockers: []

Final approval applies to remaining draft API/adapter scope after executable node removal; earlier finding retained below as review history.

Scope: storyboard_workspace.py reviewed reference adapter/draft_master_handoff, master_studio_package.py project compiler, h3_recipe.py configured-input change, PromptBuilder master_package_node.py/production_api.py/__init__.py and related tests. Existing Builder save/source implementation inspected as the integration contract. Other concurrent dirty work excluded.

## CRITICAL
None.

## HIGH

Executable handoff node does not establish the corresponding Builder editing/save source. master_package_node.py:48–55 emits compiled prompt_text and builder_state from canonical project state on each execution; __init__.py:44–49 registers it as a user-connectable node. Connecting these to Builder's matching inputs makes upstream values authoritative at execution. Existing editor Save in web/promptbuilder.js:3693–3697 writes widget values, which connected inputs supersede. Its optional persistSource at :3716 writes the pre-existing prompt_library_source through web/promptsource.js:17–25; this new node does not install, invalidate or replace that source binding.

Reproduction A: connect StudioMasterPackage prompt/state outputs to a Builder; open editor, alter wording, Save, then queue. The project compiler emits original canonical wording again, so saved widget edits are not executed. Reproduction B: make those connections into the existing Master Builder retaining its The Message prompt_library_source. Save targets that old selector/library entry, not the new project/revision, while execution still receives new node outputs. This can produce wrong-library writes plus a rendered prompt different from the editor's saved text. This is a source-ownership mismatch demonstrated by source paths; reviewer did not alter a live canvas or submit a render.

Keep the new node unregistered while the draft API is developed, or establish an explicit editor round-trip/read-only/materialization boundary before registration. The chosen design must prevent legacy library writes from representing a new project's saved prompt and verify actual compiled input after save. Add a test exercising Builder edit/save and its effective inputs, including retained legacy source properties. Existing tests directly call execute and compare outputs, so cannot catch this failure. Experimental/draft labels alone do not change Save behavior.

## MEDIUM
None independently established.

## LOW
None.

## Verified behavior and limits

- API route registration is under media_roots availability and existing guard. Exact project revision is checked before references and again after H3 compilation. Explicit reference keys must identify current reviewed, authorized, hash-matching input images. Configured input roots are used consistently by source inspection and compiler hashing. No preset/library write or queue submission occurs in draft_master_handoff itself.
- Handoff maps approved still references to H3 picture assets and delegates to existing H3 compiler for Builder/Media/seed state. Still-only adapter emits empty RefMod stack; separate project resolver tests now cover real configured RefMod selection. It does not claim automatic conversion of still images into RefMods.
- Project package returns project/revision/root, draft_uncommitted, dimensions/fps/duration; node summary requires review. Legacy The Message resolver remains separate. Previously identified eager import regression is fixed: project-store import is deferred for standalone legacy use, with import tests passing.
- Native registration source is present, but read-only live GET /object_info/StudioMasterPackage returned HTTP200 without that key: node is NOT currently registered in the running backend. No live canvas changes made. Approval of API-only draft behavior would not approve activation of the node.
- Independent focused run: studio/tests/test_master_studio_package.py, test_reference_requirements.py, test_h3_recipe.py, test_e2e_pipeline.py — 78 passed, 4 subtests passed in 10.73s. Isolated pack test_production_api.py — 6 passed in 0.67s; existing pytest-asyncio unset-scope warning. Direct node execution is covered, but full pack import/registration and native editor round-trip are not established by these tests.

## Skill perspectives

remove-ai-slops/programming remain unavailable as previously documented; applied supplied criteria. Functional selected-reference/legacy/configured-root tests are relevant. No deletion-only tests or needless parser abstraction found. Main defect is integration ownership, not test style. Required fallback report path used; notepad .codex/artifacts/storyboard-implementation/progress.md.

## Final narrowed-scope re-review

Verified master_package_node.py is absent and __init__.py has no StudioMasterPackage/master_package_node registration. Related direct-node test was removed. HIGH issue is resolved by removing the unsupported executable handoff surface; it remains a design constraint for future activation. Remaining guarded draft API and reference-bank adapter do not write Builder widgets/libraries or queue a render and therefore do not create the mismatched editor source path.

Re-ran focused suites after removal: 78 passed, 4 subtests passed in 2.57s. Previously independently passed 6 isolated API tests remain applicable to unchanged API behavior. No additional concrete blockers in configured input-root resolution, selected approved reference hashing, exact project/revision binding, legacy resolver behavior or truthful draft status. Final findings: CRITICAL none; HIGH none; MEDIUM none; LOW none. This approves an API-only draft package, not an executable or editable Master canvas handoff, and does not establish live backend activation.
