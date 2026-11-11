# The Message Silent Film Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task in the current session. Do not launch helper agents automatically. Steps use checkbox syntax for tracking.

**Goal:** Prove a reusable six-shot, silent, medium-resolution local movie pipeline, including assets, prompt contracts, generation, recovery and visible delivery.

**Architecture:** Preserve the working two-shot graph and its media. Build the silent production variant through live panel tools using existing Fantastic, Comfy Dynamic and Context Loop nodes. Extend only the small project compiler/run adapter where the current contracts cannot represent the requested behavior.

**Tech Stack:** Local ComfyUI, Fantastic H3 RefMods, Context Loop, Comfy Dynamic, existing Studio Python tools, FFmpeg/ffprobe. No new dependency or paid provider is required by this plan.

**Spec:** [the-message-silent-film-design.md](the-message-silent-film-design.md).

## Global constraints

- Target 832×480, 24 fps, 73 frames per shot, six shots, 438 frames / 18.25 seconds; qualify resource use before the batch.
- Final MP4 has zero audio streams. Prompt silence, zero-amplitude audio and player mute are not substitutes.
- Retain local REF2VA/int8, Qwen NVFP4 and video VAE weights; 20 steps, beta, sa_solver, shifts 12/3, SDPA, no torch.compile initially.
- Never overwrite approved/original references, existing bundles, takes or the successful auto-v001 output. Do not download models or restart services as an incidental step.
- Use live panel reads/edits/runs; no file-based replacement of the visible graph. Save before closing tabs, and verify workflow UUID/path before mutations.
- Run project Python with `.venv/bin/python`; leave host PATH and unrelated dirty changes alone. Operational evidence belongs in `.codex`.
- Preserve user inputs; quality failures are review findings, not reasons to truncate references or hide a bad result. Integrity/path failures do stop submission.
- Scope is a production proof with human creative review, not automatic approval of identity or a production-ready feature-length system.

## Verified starting point and gaps

Live workflow: **The Message - Automated Draft**, UUID `b34de9b0-2a2b-460a-8bbe-b7fd5ae582c8`; 42 nodes, 10 groups. One 608×352 two-shot run completed with checkpointing/assembly. Manifest loading and explicit scene-2 selection passed; actual interruption/resumed sampling did not run.

Source findings that determine the work:

- Node 32 is `Generate fresh audio per scene`; node 18 decodes audio; node 40 uses `audio_source=plan`. Installed Context Loop supports `No final audio` and Assemble `none`.
- `studio/h3_recipe.py:compile_shot` permits only the two registered 608×352 recipes. `silent` currently emits prompt text only.
- `studio/h3_loop.py:PLAN_CODE` exports prompt/length/seed/steps; width/height remain separate node-33 settings. This permits recipe/canvas drift.
- `studio/film.py:reconcile` expects exactly one SaveVideo output, a Prompt Builder and `audio=True`. It cannot be reused unchanged for recursive silent multi-clip output.
- The compiler's asset-role mapping lacks a prop-picture role. The note is currently text-only; wardrobe is a 182×107 crop.
- `assets.json` uses `approved: true` for both earlier approval and input-test authorization. Quality/likeness approval needs its own explicit record.
- `reference-presets.json` lists refinement_steps=500 although Full Reference is encode mode; it must not imply training occurred. The current factory uses zero.
- Current output naming is split between compiled run name and node-40 output folder. The previous user could not find the outputs.

## Review focus

1. Missing/changed JSON or asset bytes must never reuse a stale scene; test in Tasks 2/3/6.
2. Reordered references or an empty cast must not change identity/location labels silently; test in Tasks 3/6.
3. A silent recipe must produce no audio stream and no voice binding; test in Tasks 4/9.
4. Lost completion notices and restart/resume must not duplicate already completed scenes; test in Tasks 6/10.
5. A successful encode must not mask wrong action, environment, likeness, dimensions or output path; test in Tasks 7/8/9/11.

## Files and responsibilities

Existing files to modify only where their task requires it:

- `studio/h3_recipe.py`, `studio/test_h3_recipe.py`: recipe registry, prop binding, prompt compilation and silent delivery contract.
- `studio/h3_loop.py`, `studio/test_h3_loop.py`: immutable bundle and Dynamic node scripts; full recipe and output variables.
- `studio/h3_preflight.py`, `studio/test_h3_preflight.py`: reuse selected-asset/model/resource verification.
- `studio/film.py`, `studio/test_film.py`: retain single-take behavior; use its generic probe/hash helpers rather than weakening its single-take reconciliation rules.
- `studio/projects/the-message/assets.json`, `reference-presets.json`: versioned source records and honest preparation settings.
- `studio/projects/the-message/AUTOMATED_DRAFT.md`, `NODE_AUTOMATION_AUDIT.md`: final operator guide and qualified/deferred features.

New files proposed:

- `studio/projects/the-message/story/silent-proof-v001.md`: the six-shot source story from the design.
- `studio/projects/the-message/production.silent-proof-v1.json`: canonical entities/scenes/shots with script spans and no dialogue.
- `studio/projects/the-message/bindings.silent-proof-v1.json`: exact shot controls and reference aliases.
- `studio/projects/the-message/recipes/h3-ref-silent-medium-v1.json`: explicit registered recipe including delivery audio policy.
- `studio/projects/the-message/reference-review.silent-proof-v1.json`: input-use permission versus visual acceptance and unresolved findings.
- `studio/h3_loop_run.py`, `studio/test_h3_loop_run.py`: narrow loop-run preflight, history reconciliation and delivery receipts; no queue daemon or model code.
- `.codex/artifacts/the-message-production/silent-proof-v001/`: audits, contract receipts, measurements and test results.

## Task 1 — Freeze the baseline and finish the node inventory

Depends on: none. Deliverable: node-audit.json and a saved untouched recovery baseline.

- [ ] Read current graph and modes; bind the intended workflow UUID/path. Save the current workflow in place; record its executable graph receipt through panel tools.
- [ ] Record exact node classes/versions, links, effective input values, dormant widget values, group membership and mode for every row in the node checklist below.
- [ ] Compare classes with live `/object_info` and installed source. Separate absent node, missing weight and disabled API registration; do not install speculative packs.
- [ ] Verify current media/checkpoint hashes and preserve the original auto-v001 bundle/run receipt.
- [ ] Save-As a distinct **The Message - Silent Film Production** working copy through the panel, preserving the current workflow. Create one reusable **The Message - Reference Preparation** only if an equivalent saved workflow does not already exist.
- [ ] Classify unused installed capabilities using the extension matrix below. No per-shot workflow tabs.

Pass: all 42 original nodes have a recorded disposition, source owner and verification method; saved originals still exist; no production output overwritten.

## Task 2 — Qualify and organize every selected asset

Depends on: 1. Deliverables: versioned assets, review record and continuity sheet.

- [ ] Check selected asset paths, bytes, hashes, dimensions, channels, source ownership and RefMod metadata; decode actual stored pictures/video, not only thumbnails.
- [ ] Compare Andre's baseline and video identity at front and modest three-quarter angles. Preserve both; choose one candidate for all character shots. Mark likeness pending until reviewed.
- [ ] Replace or retain provisionally the low-detail wardrobe crop based on an inspected larger source. Record source frame/crop coordinates; generate a candidate only if needed, preserving the original.
- [ ] Establish the café master view, camera A/B/C positions, seat, window side, lighting and three persistent landmarks. Compare all three pictures side-by-side; reject inconsistent geometry from the coverage set or create a reviewed replacement version.
- [ ] Inspect background-v2's three stored views and `concept_type=background`. Exclude the older ambience-labelled bundle from new silent bindings without deleting it.
- [ ] Prepare a clean cream folded-note image on the chosen tabletop; record scale, fold, orientation and fixed table position. Do not require readable writing.
- [ ] Create reviewed crop assets for the insert and reaction using existing image-processing nodes; retain crop geometry/provenance so a crop is not mistaken for a new camera view.
- [ ] For every asset, record `input_use_authorized`, `visual_review` (pending/accepted/rejected), reviewer/evidence, limitations, source hash and derived-file hash in the new review file. Retain existing schema compatibility during migration.
- [ ] Adjust reference presets so encode-only settings are labelled as such; no fake optimization, quality claim or assumed VRAM limit. Voice assets remain preserved but unselected.
- [ ] Save preparation outputs persistently and attach a contact sheet. Source dimensions and derived dimensions remain visible.

Tests: missing file, changed hash, alias selecting another file, duplicate identity, wrong location owner and absent prop all produce explicit preparation findings/errors at the correct boundary. Quality findings do not alter supplied references automatically.

Pass: every selected asset has resolvable provenance and actual visual inspection; no unresolved identity/room contradiction is silently promoted into the full batch.

## Task 3 — Compile story, shot variables and model-native prompts

Depends on: 2. Deliverable: six deterministic compiled shots with reference maps.

- [ ] Write the story and six-shot production document from the design. Preserve source spans; give every shot its own ID, scene, action, composition, duration, seed and prop requirements.
- [ ] Write bindings using the existing framing presets. Add a dedicated insert preset only if needed; keep one observable action per shot and modest head turns.
- [ ] Extend `compile_shot(doc, shot_id, binding, assets, recipe, root)` to accept the named medium/silent recipe and prop pictures owned by declared prop IDs. Keep existing recipes/results compatible.
- [ ] Build definitions, reference retention, composition, action and lighting from the actual ordered assets. Identity describes face; wardrobe describes clothing; background describes environment; primary picture determines angle; prop describes the note.
- [ ] Empty-room and insert shots contain no accidental character/voice reference. Character shots have exactly the intended identity. Do not add contradictory wardrobe or background descriptions from the identity source.
- [ ] Save `prompt.txt`, labels, selected hashes and resolved controls per shot. Use the compiler serializer as the execution source; show an inspector preview rather than maintaining a competing editable Prompt Builder value.
- [ ] Add tests for reordered bindings, empty cast, insert prop, silent/no dialogue, duplicate IDs, prompt/reference agreement and exact frame alignment (73 for this contract).

Run: `.venv/bin/python -m unittest studio.test_h3_recipe studio.test_production_validate -v`.
Pass: all six compile; every prompt label resolves exactly once; source data determines the output without shot-specific graph writes.

## Task 4 — Implement true silent delivery and one recipe authority

Depends on: 3. Deliverable: silent graph contract and registered medium recipe.

- [ ] Add an explicit `delivery_audio: none` contract to the new recipe/bundle while preserving historical audio recipes. Reject speech/voice selections for this named silent production before submission.
- [ ] Set Generation Profile to the installed `No final audio`, retaining Independent scenes. Set Assemble to `none` as the explicit delivery choice.
- [ ] Disconnect unused audio inputs from Trim and Segment Save before muting Decode Audio; muting an upstream dependency alone can suppress downstream nodes. Inspect optional inputs in live schemas first.
- [ ] Disconnect/mute the audio VAE route only where the selected visual references do not require it. Preserve H3's native audiovisual latent contract; no tensor surgery or unverified claim that internal audio sampling disappears.
- [ ] Extend `h3_loop.export` and `PLAN_CODE` so the bundle supplies width, height, timing, steps, audio delivery, run name and output subfolder. Wire these variables to their real consumers; define a new bundle version rather than misreading old bundles.
- [ ] Check effective linked values, not inactive widget defaults. Fail preflight on recipe/graph mismatch; do not downgrade dimensions automatically.
- [ ] Test old recipe behavior, new silent dimensions, stale canvas dimensions, explicit audio selection conflict and a tiny synthetic MP4 with/without an audio stream.

Pass: a CPU assembly fixture yields a decodable video with zero audio streams; native H3 interfaces remain intact. GPU generation is qualified in Task 7.

## Task 5 — Simplify the reusable production canvas

Depends on: 1, 4. Deliverable: two understandable saved workflows.

- [ ] Keep production inputs, reference selection, sampling, persistence and diagnostics in separate labelled areas. Ensure group boxes do not accidentally capture unrelated nodes.
- [ ] Replace misleading stale widget displays with a resolved run-summary preview: run, dimensions, frames, silent policy, asset aliases and destination.
- [ ] Retain one execution path. Remove obsolete manual-only controls from the working copy after their replacement is verified; their original graph remains saved. Keep diagnostic outputs intentionally selectable.
- [ ] Move reference Create/Inspect into the reusable preparation workflow; generation must not rebuild RefMods on each shot.
- [ ] Name outputs by project/run/shot/take; derive the delivery folder from the bundle. Show a persistent output index in the panel after completion.
- [ ] Save, reopen through panel tools, reread effective values/modes and compare the execution contract. Confirm the original workflow remains intact.

Pass: operator edits production inputs rather than individual shot nodes; no inactive manual control appears to control the active run.

## Task 6 — Unify preflight and durable loop-run tracking

Depends on: 3–5. Deliverable: loop adapter with exact run identity and explicit states.

Proposed interfaces in `h3_loop_run.py`:
`preflight(bundle, graph, resources, workspace, registered_nodes) -> dict`,
`reconcile(run_dir, history, output_root) -> dict`,
`publish_delivery(run_dir, destination) -> dict`.
Reuse selected-asset/model checks and media probes. Do not change the single-take
`film.reconcile` contract to accept unrelated loop outputs.

- [ ] Persist bundle/graph/model/asset fingerprints, ordered shot IDs, desired dimensions/audio and observed resource timestamp before submission.
- [ ] Record `prepared → preflight_passed → submitting → queued → rendered → technical_pass → review_pending` and explicit failed/unknown states. Bind the returned prompt ID immediately.
- [ ] Match exact history plus Context Loop manifests/revisions to all expected shots; ignore unrelated runs and temporary previews. Deduplicate repeated completion events.
- [ ] On lost acknowledgement, reconcile authoritative history before retry; unknown submission remains unresolved, not a fresh render request.
- [ ] Verify path containment, source hashes, prompt sidecars, dimensions, fps, decoded frame count, order and no final audio. Track visual review separately.
- [ ] Add tests for changed bundle/file, swallowed DynamicScript exceptions, invalid scene index, duplicate completion, unrelated prompt, partial run, changed media and output-name collision.

Run: `.venv/bin/python -m unittest studio.test_h3_loop studio.test_h3_loop_run studio.test_h3_preflight -v`.
Pass: same completion is idempotent, partial work stays partial, ambiguous work never causes an automatic duplicate.

## Task 7 — Qualify medium resolution and reference cost

Depends on: 2–6. Deliverable: measured medium-recipe report.

- [ ] Verify live RAM/VRAM, model files, port/process ownership, queue and conflicting GPU export before loading. Preserve SDPA/no compile.
- [ ] Run CPU-only compilation and reference-map checks for all six shots; run missing-file/invalid-bundle cases without sampling to prove failure is visible.
- [ ] Measure tokens for identity + primary picture + wardrobe + prop + background using the installed token diagnostic if its inputs match the encoder outputs. Counts are diagnostics, not a memory-fit promise.
- [ ] Run one 56-frame 832×480 stress shot with the largest intended reference set; record wall time, RAM/VRAM pressure, decode success and actual dimensions.
- [ ] If it passes, qualify 73 frames at the same resolution with that reference load. Inspect motion, face and room. If it fails, document whether memory, unsupported shape or quality caused failure; change one variable in a new recipe candidate, never silently shrink references.
- [ ] Record a measured full-run duration estimate from the pilots; report it as an estimate with cold/warm and reference-load limits.

Pass: the heaviest intended shot completes at the declared medium dimensions and duration. Do not queue all six until this gate passes.

## Task 8 — Validate reference control with a bounded comparison

Depends on: 7. Deliverable: environment/identity comparison with explicit selection.

- [ ] Use the same reverse shot, seed, medium recipe, primary picture, identity and wardrobe for two versions: background-v2 absent versus present once at strength 1.
- [ ] Compare the agreed landmarks, camera direction, table/chair arrangement, light and character clothing. Do not assume more references are better.
- [ ] Inspect a reaction shot for recognizable identity, closed-mouth behavior and the requested small gaze change. Distinguish source limitations from prompt/compiler errors.
- [ ] Select a documented reference policy for the six shots. If the background bundle harms fidelity, keep it as a failed candidate; do not force it into every shot to tick a feature box.
- [ ] Where spatial fidelity still fails, use a reviewed composition/keyframe candidate only through a verified supported native route; qualify it as an optional extension to this plan before use.

Pass: the chosen reference policy meets the visual criteria, or the remaining limitation is explicitly unresolved. No unlimited reroll loop; each repair changes one diagnosed cause and receives a new take ID.

## Task 9 — Execute the six-shot silent film

Depends on: 8. Deliverables: six immutable clips and assembled silent draft.

- [ ] Freeze the chosen assets, recipe and six-shot bundle under a fresh run name. Save the workflow and record its fingerprint.
- [ ] Run fresh preflight, inspect all active/muted routes, then queue once through the panel. No per-shot edits or provider calls.
- [ ] Reconcile that exact prompt on completion; verify six distinct shot IDs/revisions, 73 frames each, correct prompt/reference sidecars and final ordered 438 frames.
- [ ] Decode each saved shot and final MP4 completely with FFmpeg/ffprobe. Assert 832×480, 24 fps, 18.25 seconds within one frame, zero final audio streams and no broken/truncated files.
- [ ] Inspect first/middle/last frames and playback for each shot plus joins. Record face, wardrobe, note, location landmarks, seating, screen direction, action and flicker findings.
- [ ] Mark technical pass independently of creative acceptance; show every failed criterion. A controlled replacement uses a new revision and replaces only the explicit shot in a new assembly receipt.

Pass: automatic mechanics pass without hidden manual intervention; all six story beats are visible and defects are documented for review.

## Task 10 — Prove repeatability, interruption and reassembly

Depends on: 9. Deliverable: recovery evidence without destroying the good run.

- [ ] In an isolated recovery run, use the installed explicit scene range to finish shot 1, then start at shot 2 with history verification. Hash the completed shot before/after.
- [ ] Separately test an actual interrupted in-flight owned run only when the shared queue is otherwise empty and the available cancellation tool can target this job safely. Never restart the server or cancel another user's run. If targeted interruption is unavailable, report this subtest blocked, not passed.
- [ ] Reconcile partial state, resume from the first incomplete scene and verify that the previously completed clip was not resampled or changed. Do not resume a completed six-shot film merely to demonstrate a button.
- [ ] Load a verified completed manifest and assemble under a fresh filename with sampling disconnected. Compare source hashes and frame order; confirm no new sampler execution.
- [ ] Repeat reconciliation/publication on the same run; require no duplicate media or status regression. Run the small two-shot smoke under a fresh run identity to test repeat execution independently of the main film.

Pass: stop/range resume, reassembly and idempotence have separate evidence. Actual interruption recovery is advertised only if its dedicated test passes.

## Task 11 — Make output discovery and handover unambiguous

Depends on: 9; incorporate Task 10 results. Deliverable: one obvious delivery folder.

- [ ] Publish friendly immutable copies such as `shots/01_cafe_wide.mp4` through `06_closing_wide.mp4` plus `The_Message_silent_proof_v001.mp4`; preserve canonical chain files/checkpoints.
- [ ] Write `index.json` and `README.md` mapping story shot, source revision, hashes, dimensions, duration, audio policy, technical and creative status. Refuse conflicting destinations rather than overwrite.
- [ ] Save contact sheets and show final film + representative shots through `panel_show_media`. Provide the exact absolute folder and file-manager navigation instructions.
- [ ] Update the two workflow notes and operator guide: prepare → preflight → Run → review → resume/reassemble. List which tabs are saved and safe to close.
- [ ] Record final test commands/results, known limitations and all deferred features. Do not label the proof final-approved without the user's visual acceptance.

Pass: a user can locate and play the complete film and each shot without knowing the hashed Context Loop filenames.

## Task 12 — Remove verified unused code and extensions

Depends on: Task 1 for inventory; removal follows the replacement and regression gates in Tasks 4–10. Deliverable: a smaller supported production surface, removal manifest and tested recovery instructions.

- [ ] Inventory custom-node packs, registered classes, frontend-only extensions, project code, shared dependencies and dirty changes; record exact versions/paths before changing anything.
- [ ] Map usage across the live graph, saved user workflows, retained examples and recovery tools using panel/ComfyUI inventory tools. Never infer globally unused from absence in this one film graph.
- [ ] Classify each candidate as required, used elsewhere, duplicate/superseded, unused with evidence, or unknown; keep unknown/shared dependencies until resolved.
- [ ] Identify obsolete production-specific code and duplicate prompt, timing, output and retry logic after the replacement has passed its owning task; preserve core ComfyUI boundaries and public contracts.
- [ ] Prepare exact per-candidate removal manifests with dependent workflows, source revision/hash, dirty-file backup and recovery path. Preserve model weights, reference assets, outputs and checkpoints.
- [ ] Remove proven obsolete project code in scoped changes; run affected tests and import checks. Do not remove historical recipes or take readers still required to reproduce saved work.
- [ ] Remove verified unnecessary third-party packs/frontend extensions through supported management operations after a recoverable backup. Never blanket-uninstall Python dependencies or alter core/native API registration. Any restart remains a separately scheduled, explicitly authorized operation.
- [ ] Verify native and retained custom nodes, saved workflows and the qualified production run after cleanup; restore a removed candidate if regression occurs, then record retained/removed/deferred items with reasons.

Pass: each removal has a concrete dependency audit, recovery path and passing regression evidence; no unresolved candidate is counted as removed.

## Task 13 — Publish the module architecture and board

Depends on: the design and read-only source audit. Deliverable: an editable module diagram and complete Plannotator task coverage.

- [x] Draw ownership and data-flow boundaries for authoring, asset preparation, compilation, preflight/run control, conditioning, sampling, checkpoints/recovery, assembly and review/delivery.
- [x] Map each module to current files/node packs, standard data interfaces and protected core boundaries; distinguish target design from already qualified behavior.
- [x] Publish all tasks/subtasks, individual node-review items and final acceptance criteria to one Plannotator initiative; retain stable IDs, dependencies and source text, and verify readback coverage.

Pass: diagram and task manifest are attached to the production thread; every source checklist item has a Board card, and future implementation updates the existing card IDs.

## Every current node: required review/disposition

This is the audit checklist for implementation, not a claim that each change has
already been tested. IDs refer to the observed baseline; remap deliberately after
Save-As or removal. Each row needs schema/source, effective-value and execution evidence.

| ID | Node | Required disposition/check |
| --- | --- | --- |
| 1 | MarkdownNote | Replace with silent-production controls, output location and honest qualification state |
| 2 | UNETLoader | Keep pinned REF2VA; verify file and dtype/offload |
| 3 | SigmaShift | Keep 12/3; confirm both consumers use patched model |
| 4 | CLIPLoader | Keep correct H3/Qwen type and weight; no assumption it is a standalone prompt-generating LLM |
| 5 | Video VAELoader | Verify reference encoding and output decode use matching VAE |
| 6 | Audio VAELoader | Disconnect/mute when visual route needs none; preserve original graph |
| 7 | RefModStack | Linked state authoritative; identities/background once, no voice, strength 1 initially |
| 8 | PromptBuilder | Retire from active generation; inspector/reference authoring only, no competing prompt source |
| 9 | Fantastic Text Encode | Audit prompt, dimensions, length, reference order/FPS, stack selection and optional audio; record resolved inputs |
| 10 | Stack-label preview | Keep for CPU reference audit; distinguish cached preview from current resolved shot |
| 11 | Reference-map preview | Keep; show shot ID alongside labels to prevent misleading stale view |
| 12 | BasicGuider | Correct patched model and conditioning |
| 13 | KSamplerSelect | sa_solver pinned |
| 14 | BasicScheduler | beta, denoise 1, linked steps and patched model |
| 15 | RandomNoise | Linked per-shot seed, fixed after-generation behavior |
| 16 | SamplerCustomAdvanced | Native AV latent contract; both checkpoint outputs correctly routed |
| 17 | VAEDecode | Medium dimensions, full-frame decode, no hidden resize |
| 18 | VAEDecodeAudio | Disconnect outgoing optional audio routes, then mute/remove in silent copy |
| 19 | CreateVideo | Old manual route; remove from clean copy after replacement proof |
| 20 | SaveVideo | Old take prefix; remove from clean copy so it cannot create misleading outputs |
| 21 | MediaLoader | Linked picture state, exact role/order, embedded audio off; no unused source input |
| 22 | ResolutionSelector | Retire manual driver; recipe/bundle is authority |
| 23 | PrimitiveFloat | Retire manual duration; production shot controls duration |
| 24 | Frame math | Retire duplicate math; compiler owns alignment and records actual duration |
| 25 | EditComposite | Currently a pass-through with editing off; confirm then bypass/remove from production, retain only in a separately qualified editing branch |
| 26 | ReferenceMap | CPU numbering check matches actual encoder order |
| 28 | CreateRefMod | Move to reusable preparation; visual background/identity presets, immutable output, no implied training |
| 29 | InspectRefMod | Preparation QA; video refs decoded temporally, picture stacks inspected as pictures |
| 30 | DynamicLoadTextFile | Missing/changed input must invalidate; absolute resolved bundle path |
| 31 | DynamicScript plan | Fingerprint/version validation; all recipe/output variables; errors cannot become valid fallback values |
| 32 | GenerationProfile | Independent scenes + No final audio |
| 33 | ChainPlanModern | Linked size/run/fingerprint; explicit frames; no stale default overriding bundle |
| 34 | LoopStart | Start/range explicit, verify history on; completed range not blindly rerun |
| 35 | ChainCurrent | One-based index and exact per-shot prompt/seed/frame/dimension mapping |
| 36 | DynamicScript assets | Same bundle/index as prompt; role/order verified; no shared module cache |
| 37 | LoopTrim | fps 24, trim 0 for independent shots; no audio dependency; output count verified |
| 38 | SegmentSave | Correct shot/revision/checkpoint ownership; silent optional-audio behavior |
| 39 | LoopEnd | Direct flow from Start, recursive advance; no duplicated scene or cleanup-induced race |
| 40 | Assemble | Explicit none audio, ordered manifest, bundle-derived folder, preserve checkpoints |
| 41 | ManifestLoad | Recovery/reassembly only; correct run fingerprint and files |
| 42 | Recovery script | Diagnostic only; no sampler path and no stale success wording |
| 43 | Recovery preview | Muted normally; displays exact selected run/scene and verified manifest |

## Installed extension coverage

| Capability | Use in proof | Gate |
| --- | --- | --- |
| Fantastic Create/Inspect, Stack, MediaLoader, encoder/map | Preparation and all relevant shots | Tasks 2/3/8 |
| Comfy Dynamic loader/scripts | Typed single-source variables | Tasks 4/6; deterministic JSON only |
| Context Loop Plan/Profile/Current/Save/End/Assemble/ManifestLoad | Whole sequence and recovery | Tasks 4/9/10 |
| KJ token counter, indexed batch/image preview; installed crop/resize nodes | CPU/GPU diagnostics and asset preparation where schema fits | Task 2/7; no automatic quality claim |
| BFS reference description/native prompt helpers | Optional preparation assistance | Audit local VLM compatibility first; no implicit model download/provider call |
| Tagged Ref2VA / ProjectAssetCarousel | Deferred alternate reference system | Not interchangeable with current Fantastic RefMods |
| Plan Studio/RunManager/CheckpointManager | Optional later production UI | Core graph and recovery must pass first |
| Reference Cache | Deferred approximate acceleration | Not persisted conditioning; requires quality A/B |
| Project Suite silent import | Deferred | Known audio-latent contract concern must be reverified before adoption |
| Voice/lip-sync/continuous audio, upscale, motion/video editing | Excluded from silent proof | Separate future specification and qualification |

## Execution order and stopping rules

13 establishes the board/diagram. Production: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11.
Task 12 begins with the Task 1 dependency inventory; removals follow the corresponding replacement and regression gates, with final cleanup verification before handover.
Tasks 1–6 are preparation/contract work; 7–9 consume generation time. No full
batch before medium/reference gates pass. Each failed gate leaves an actionable
finding, its evidence and a bounded next test. Repeated rerolls do not establish
reliability. Commit only scoped implementation files after review of the dirty
tree; never bulk-stage unrelated work.

## Final acceptance checklist

- [ ] Every original node has a recorded review and final disposition.
- [ ] Every selected asset has inspected media, hashes, role/owner and honest review status.
- [ ] Story and bindings alone produce six valid, noncontradictory prompts/reference maps.
- [ ] One run generates all six intended shots without per-shot canvas edits.
- [ ] Native medium output and exact frame order/count pass complete decode.
- [ ] Final film contains no audio stream.
- [ ] Likeness, room/prop continuity and action have explicit review results.
- [ ] Resume, interruption scope, reassembly and idempotence have distinct evidence.
- [ ] Output folder, friendly filenames, index, previews and saved-workflow guide are delivered.
- [ ] Unqualified features and remaining defects remain visible; no automatic creative approval.

Plan self-review: all requested areas map to tasks; all 42 node IDs are listed;
six shots cover three location angles, cast/empty/insert cases and appearance /
action changes. No render, model installation or workflow mutation is part of
writing this plan. The design's medium target and 73-frame duration require the
explicit pilot gates above.
