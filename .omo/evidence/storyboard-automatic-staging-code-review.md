# Automatic output-reference staging review

codeQualityStatus: CLEAR
recommendation: APPROVE
blockers: []

Scope: current stageOutput and staging integration in custom_nodes/ComfyUI-Fantastic-MiniMaxH3-PromptBuilder/web/production_workspace.mjs, and three related additions in tests/storyboard-workspace.browser.mjs. Read native server.py upload implementation and backend draft/staged-hash checks to verify integration. This disposition covers the narrow staging change, not all intervening storyboard features.

## CRITICAL
None.

## HIGH
None.

## MEDIUM — resolved during review

Valid long output basenames become invalid upload basenames. production_workspace.mjs:63 prefixes the complete original filename with `storyboard-<UUID>-` (48 bytes). An existing valid output filename of 208–255 bytes therefore exceeds the usual Linux component limit when uploaded. Example: 216 ASCII characters plus `.png` (220 bytes) becomes 268 bytes; server.py store_image_upload attempts that filename directly and fails. Generate a short staging basename plus the original extension, or otherwise keep the new component within the filesystem byte limit. Add a meaningful long-name upload-contract case. This is a bounded input compatibility issue, not a blocker for the demonstrated ordinary reference paths.

## LOW
None.

## Native contract and race assessment

- Native `/view` receives filename/subfolder/type=output. Without preview or conversion parameters it supplies original bytes. Upload uses FormData field `image` with a filename and `type=input`; no overwrite flag is sent. Native upload returns name/subfolder/type, matching the client mapping, and registers uploads in the native asset manager.
- Backend storyboard_workspace.draft_endpoint requires reviewed/current/authorized bindings and verifies staged input SHA against source SHA; frame_jobs._draft independently verifies the kept/current start candidate and its staged SHA. Client cache keyed by locator cannot silently authorize different image bytes: mismatches fail at this boundary.
- After staging, usable/view/project/revision/dirty/selection checks prevent obsolete selection from drafting. Generate repeats relevant guards. Staging already underway can finish after navigation, leaving an unused input copy, but cannot itself generate a model job or modify a project selection. No blocking race identified within this change.
- Three browser cases exercise output-reference staging, kept-start staging and checkbox changes while upload is delayed. They stub native HTTP and thus are not evidence of actual image bytes surviving a real native round trip. The first upload assertion checks FormData/type; stronger useful coverage would inspect the image Blob bytes and test failure/retry. No browser execution was claimed by this reviewer.

## Verification and skill perspectives

`node --check .../web/production_workspace.mjs` passed. `node --test .../tests/storyboard-workspace.test.mjs` passed all 7 tests. Inspected source for native upload and both backend integrity checks directly. No installation, GPU work, service changes or implementation edits.

Required remove-ai-slops/programming skills remain absent from catalog and earlier filesystem discovery. Applied supplied criteria: added tests exercise observable requests/user state, not removals or implementation constants; native boundary validation is justified, staging cache has local preparation lifetime, and helper extraction is small and coherent. No independent skill-perspective violation.

ULW runtime previously failed and no usable current attempt was provided; required fallback report path used. Execution ledger/notepad remains .codex/artifacts/storyboard-implementation/progress.md.

## Final verification of fix

Reviewed updated stageOutput:63–64 and browser regression at tests/storyboard-workspace.browser.mjs:127–139. Staging now uses a short UUID basename and bounded extension, so original basename length no longer affects upload filename size. Test inspects actual FormData filename byte length for a 244-byte original name; this is relevant contract coverage. Parent reports RED before fix; reviewer verified code and test rather than executing browser harness. Final disposition CLEAR / APPROVE; blockers []; no remaining CRITICAL/HIGH/MEDIUM/LOW findings within automatic staging scope.
