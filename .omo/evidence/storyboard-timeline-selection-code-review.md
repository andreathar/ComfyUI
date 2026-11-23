# Timeline selection review

codeQualityStatus: CLEAR
recommendation: APPROVE
blockers: []

## Final verdict

All findings below are now resolved and retained only as review history. Independently inspected the final shared renderProject-scoped timelineVersion: review and selection each increment it, review GET results require the captured generation to match, and selection responses cannot render their stale projection after a newer operation. Overlapping selection/review conservatively requests reopening. Candidate-list merging continues to preserve local edits.

Backend cross-browser consistency also checked: production_api.py:37–39 executes project/with_timeline synchronously without await or executor offload, and review_frame at 170–172 calls synchronous review after body parsing. Another browser's review cannot interleave during projection on this server's event loop. An additional frame snapshot lock is not required for that specific path. Multiple processes or future threaded offload would require reconsideration; response age after projection completes is not prevented by a lock.

Inspected the reversed-response browser regression at tests/storyboard-workspace.browser.mjs:301: it delays the Keep-triggered project response, completes a later Reject refresh, then releases the older response and asserts that no selected images return. This is a relevant behavioral regression, not an implementation-constant assertion. Independently reran the frontend unit tests: **7 passed**. Browser regression source inspected; its reported runtime pass was not independently rerun in this final follow-up. Earlier independent backend verification remains **6 passed**. No concrete blocker remains; no live generation performed.

## Follow-up review of UI fixes

The HIGH finding below is resolved: the in-flight edit branch merges server-owned candidate lists while retaining local descriptions and production edits. The basic rejection-refresh finding is also addressed by clearing the timeline when review begins and fetching the current project afterward. Inspected the new browser regressions for both sequences; no browser runtime verification was performed in this follow-up.

One MEDIUM finding remains at `web/production_workspace.mjs:583`–587: timeline project GETs are not sequenced. A slow GET after Keep can return after a later Reject and its newer GET, overwriting the newer empty timeline with the older kept images. Reviews do not increment project revision, so the revision equality guard passes for both responses. jobsVersion protects candidate-list rendering only. Add a renderProject-scoped timeline generation shared across all shot panels, increment it when review or selection invalidates the projection, and apply responses only when their captured generation is still current. Test reversed completion order of the two project GETs. Recommendation remains REQUEST_CHANGES until this remaining stale-approval display race is fixed.

Scope: new explicit frame selection and timeline projection in studio/production_store.py, frame_jobs.py, production_api.py, production_workspace.mjs and test_frame_integration.py. Concurrent checkout; findings describe the inspected snapshot. No implementation files changed by reviewer.

## CRITICAL

None.

## HIGH — resolved in follow-up

- `custom_nodes/ComfyUI-Fantastic-MiniMaxH3-PromptBuilder/web/production_workspace.mjs:583`–589: edits made while select_frame is outstanding preserve the old local storyboard but advance its revision to the newly selected server revision. The local candidates list therefore omits the selected candidate. A subsequent Save posts this stale list; studio/storyboard.py validate_target_edit rejects it as an unauthorized candidate change, even though the user only edited a description. Retrying keeps posting the same stale candidates, and reopening discards the unsaved edits. Merge server-owned candidate lists from the selection response while preserving local editable fields, then test selection followed by an edit before the response and a successful subsequent save.

## MEDIUM — original sequence resolved; out-of-order variant remains above

- `custom_nodes/ComfyUI-Fantastic-MiniMaxH3-PromptBuilder/web/production_workspace.mjs:573`–577: reviewing a selected frame refreshes candidate jobs only. Rejecting a selected start correctly invalidates both selected endpoints in backend projection, but the existing Timeline section retains both images and its earlier Frames kept label. Refresh or invalidate that projection after review without discarding local edits; test that rejection removes the selected timeline images immediately.

## LOW

None.

## Verified evidence

Independently ran `.venv/bin/python -m pytest custom_nodes/ComfyUI-Fantastic-MiniMaxH3-PromptBuilder/tests/test_frame_integration.py custom_nodes/ComfyUI-Fantastic-MiniMaxH3-PromptBuilder/tests/test_production_api.py --rootdir=custom_nodes/ComfyUI-Fantastic-MiniMaxH3-PromptBuilder/tests --confcutdir=custom_nodes/ComfyUI-Fantastic-MiniMaxH3-PromptBuilder/tests --import-mode=importlib -q --tb=short`: **6 passed in 8.19s**. Inspected the current browser tests; the new selection test exercises ordinary selection but does not cover either UI sequence above. No live generation or service launch.

No additional concrete backend blocker found: selection appends prior candidates, checks revision under the project lock and serializes against review via the frame lock. Projection checks current keep, selected review ID and output hash, and suppresses an end whose recorded start_job differs from selected start. Passing backend tests do not establish freshness of the existing browser timeline.

## Skill-perspective check

remove-ai-slops and programming files remain unavailable, as established earlier in this review session. Applied their supplied prompt criteria to the current production code and tests. No useless removal-only tests, tautological tests, needless abstraction or gratuitous production parsing found in this slice. The integration test is behaviorally relevant, but the uncovered frontend races require behavioral browser regressions.

No notepad path supplied. ulw-loop runtime unavailable earlier in this session; using required fallback report location. Blockers: preserve server-owned candidate state when a selection response overlaps local edits; refresh/invalidate selected timeline after review changes.
