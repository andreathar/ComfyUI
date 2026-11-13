# Camera and reference-role compiler review

codeQualityStatus: CLEAR
recommendation: APPROVE
blockers: []

## CRITICAL
None.
## HIGH
None.
## MEDIUM — resolved in follow-up
1. Wardrobe instructions are silently discarded. studio/h3_recipe.py:205–212 incorporates wardrobe descriptions and picture labels into the character definition, while the revised media loop at lines 234–242 now handles props only. Previously, each wardrobe asset's instruction was emitted in retention_analysis. A valid instruction such as "Preserve the embroidered blue cuff; ignore cropped framing." disappears entirely in current output. This loses user-authored clothing constraints and the explicit crop-is-not-framing instruction, undermining the intended separation of reference roles. Preserve each wardrobe instruction in the owning character definition/retention without reintroducing a standalone picture anchor. Add a behavioral test that the authored instruction survives.
## LOW
None material.

## Independent checks

- Inspected current full diff of studio/h3_recipe.py and studio/test_h3_recipe.py and surrounding role/owner validation, picture numbering, subject numbering, environment, voice and dialogue logic.
- Ran recipe suite with project interpreter: 32 tests pass.
- Compiled a valid empty-cast prop-only fixture with prop picture before the location picture: Subject 1 correctly resolves environment Picture 2, Subject 2 resolves prop Picture 1. No subject-number collision or orphan character reference introduced by these branches.
- Compiled valid wardrobe fixture carrying the custom instruction above: confirmed it is absent from prompt_text. This is a behavior regression rather than a stylistic concern.
- New setting mode removes the compiler's primary-layout and close-up-distance retention boilerplate. Composition remains the default. Neither mode overrides caller-authored style_bible.camera_rules, background instructions, blocking or camera_move.note: moving-shot examples must explicitly avoid inherited static/locked-camera constraints. The new test does explicitly replace camera_rules. No automatic natural-language filtering is recommended.
- Facial identity partial retention, wardrobe picture labels and reordered media handling are internally consistent in inspected output. No claim about model adherence or generated quality.

## Skill perspectives and scope

Applied remove-ai-slops/programming criteria from the reviewer prompt; skill files remain unavailable as recorded earlier. No needless production abstraction or parsing introduced. New tests exercise compiler behavior; their string checks are relevant to this text compiler's contract, though they do not establish semantic model behavior. The specific missing instruction case is not covered.

Read-only review; no implementation changes, GPU calls, live sample execution or creative approval. Report uses requested .omo/evidence path; no separate notepad path supplied. Full 299-test result was supplied by lead, not independently rerun in this focused pass.


## Follow-up disposition

The wardrobe-instruction regression is resolved. The owning character definition now includes each wardrobe reference instruction, associated with its actual picture label; the regression test asserts preservation of the authored cuff/crop instruction in that definition. Independently reran all 32 recipe tests: pass. No remaining material findings.

Recompiled all six current film shots from current source/bindings/assets and compared prompt_text/builder_state with current resolved libraries: all match. This independently confirms saved-file agreement, not a new HTTP Save/Load verification.

Reviewed camera-reference-tests samples.json, manifest.json, both compiled sample artifacts/prompts, preparation script and sample-resolver.py. Both manifest package hashes match. Cases share media_state, empty RefMod picks, seed 918021, transition, recipe, reference hash, 832x480 dimensions, 20 steps and 73 frames. Differences are case identity, prompt/state camera text and derived fingerprint. No portrait or identity RefMod is present. Dolly prompt has slow overhead dolly-in instructions with still paper; static prompt has static camera. Inherited global camera rules are replaced by one continuous shot/no cuts, avoiding a locked-camera contradiction. These are subject-matter-prop-only samples using the tabletop image as a location/environment reference; they do not exercise the separate prop-role Subject branch tested earlier.

Executed the sample resolver locally for both cases without graph submission: package digest checks and actual reference-file hash checks pass; both return seed 918021. Resolver performs read-only input checks in this execution. No GPU models loaded or jobs submitted.

Manifest accurately marks prepared status and pending human acceptance, with a two-run initial maximum. No independent live inspection of separate-tab isolation, muted save node, enabled monitor or unchanged original canvas performed in this review; these remain lead-agent deployment evidence. Samples are not completed camera-response tests or creative approvals.

Reapplied fallback skill perspectives: fix and regression assertion are scoped and meaningful; no new slop/maintainability violation found.


## Follow-up: first-frame layout and corrective static sample

Disposition: CLEAR / APPROVE; no remaining material findings in this narrow update.

- Inspected new first_frame handling and primary_asset.instruction preservation. The authored location instruction now survives setting and first_frame modes, and the composition path avoids duplicating it when environment_override already included it. The first-frame picture label comes from resolved location labels, not a hardcoded Picture 1. Existing composition default and setting behavior remain selectable.
- Independently ran recipe tests with project interpreter: 34 passed, including authored location-instruction retention and first-frame/camera coexistence checks. Full 301 Studio tests were reported by lead but not rerun here.
- Compared CAM_STATIC_ANCHOR.compiled.json to CAM_STATIC.compiled.json: only binding, builder_state, prompt_text and fingerprint differ. Recipe (including model selections, resolution, steps), seed, media_state, stack_state and frames remain identical. Thus the corrective treatment preserves seed 918021, source reference, 832x480, 20 steps and 73 frames.
- Read complete corrective prompt: static camera, still envelope, opening picture anchor, preserved flap/outline/orientation and exact source-relative placement are mutually consistent. The old upper-left-third blocking is replaced by the stated 13%-width/40%-height center and left-quarter framing. The prompt uses an empty cast and no identity RefMod.
- This first_frame option changes prompt semantics and builder summary/retention text. It does not introduce a hard image-to-video initialization or guarantee pixel-identical first-frame reconstruction. Resulting camera/shape fidelity still requires decoded-output review before film SH03 activation.
- No independent verification of previous video bbox measurements, panel repeated-frame storyboard behavior, queued corrective render or its output in this source review. No live submission or implementation edit performed.
- Prompt-provided remove-ai-slops/programming perspective reapplied (skill files unavailable as previously documented): tests assert compiler output contracts, no unnecessary parsing/abstraction introduced. No new violations.

## Final follow-up: deterministic plate evidence and saved Master branch

Disposition remains CLEAR / APPROVE for inspected source and saved artifacts; no code blocker found.

Independently decoded output/The_Message/camera_reference_tests/2026-11-13/CAM_PLATE_HOLD_00001_.mp4 with ffmpeg: 73 RGB frames at the recorded 832x480 dimensions. SHA-256 equals 6a47738a958882769f651b93e20699cc076126dc40e146b066b86393983320dd. Independently computed maximum mean absolute RGB difference from frame zero: 0.005679921207264957, matching probe evidence. This is not lossless pixel identity; encoding differences remain. Probe records 24fps, one video stream, 3.041667 seconds and no audio stream. Saved history records success and SaveVideo output; monitor benchmark has no sampler intervals and benchmark_qualified:false. A fast repeated-plate export cannot establish model speed or generative reference fidelity.

Inspected saved Master JSON (file state, not live browser): SH05 remains selected; H3ProjectSave61 and SaveVideo64 mode0; optional plate SaveVideo104 mode2. ImageScale101 uses lanczos/center, RepeatImageBatch102 feeds CreateVideo103 and SaveVideo104. Verified links from node22 picture1 and node18 actual width/height/delivered-frames/fps/shot outputs to the branch and filename105. Group6 exists with the optional locked-insert title. This branch is persisted in the saved workflow, not reproduced by the inspected build_master_movie_studio_workflow.py source; report it as such.

Freshly recompiled all six film shots: current prompt/state equal source output and final native-save-verification-final.json hashes. This checks stored receipts against current files, not new HTTP roundtrips.

LOW handoff documentation note: camera-reference-tests/NEXT.md still says await the corrective anchor and potentially promote first_frame to film SH03. Lead now reports that anchor rejected for hands, so update this stale continuation note before handoff. No inference of human approval or film promotion follows from the export. Original generated samples/anchor remain separate from the deterministic hold.

Did not independently inspect the forthcoming SH03 integration run or post-run restoration. Prior observations of saved modes/SH05 must not be presented as proof of later restoration. No canvas mutation, generation submission or implementation edit by reviewer.
