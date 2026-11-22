# The Best Storyboard Creator Assistant — implementation plan

> **Execution:** this is a proposed plan for review, not permission to run every experiment now. Work through reviewed milestones inline; do not launch parallel agents unless separately authorized. Preserve dirty work and complete the smallest working slice before broadening it.

**Goal:** turn a user's story into a persisted, editable production project with consistent reference banks, a comprehensive scene/shot timeline and reviewed start/end storyboard images for every shot, ready for a separate video phase.

**Architecture:** extend the existing Studio production document and Bootstrap with narrow revision, runtime-admission, still-recipe and storyboard services. One guided workspace uses the existing PromptBuilder, Suite and Plan Studio surfaces; native ComfyUI retains model/component memory management and visible execution. Brain observes frozen inputs, results and evidence coverage without deciding creative acceptance.

**Tech stack:** existing Python environment and standard library; existing schema/test tooling; V3 custom nodes and current ComfyUI queue; local llama.cpp/Qwen through a verified Hermes-installed runtime; existing JavaScript UI and native model nodes. No new application server, database or framework is required.

**Spec:** [proposed design](best-storyboard-creator-assistant-design.md). Read it alongside [Bootstrap](production-bootstrap.md), [reference strategy](../docs/REFERENCE_STRATEGY.md), [Master guide](../docs/MASTER_MOVIE_STUDIO_GUIDE.md), [local worker](../docs/LOCAL_ASSET_WORKER.md), [research evidence](../../.codex/artifacts/best-storyboard-assistant-2026-11-21/RESEARCH.md) and the [14-finding UX audit](../../.codex/artifacts/movie-production-ux-2026-11-21/REPORT.md).

## Global constraints

- The original story and dialogue remain verbatim until the user explicitly edits them. Source-backed facts, visual proposals and unresolved questions are distinct.
- `production.json` owns canonical entities, scene/shot order, camera intent, duration and selected `start_frame`/`end_frame`. Do not add a competing timeline or shot database.
- The person owns likeness, reference and creative acceptance. Input-use permission, storyboard pair selection, video take selection and motion continuation are different decisions.
- Each included shot gets a start/end pair, including an explicitly labelled same-image static hold. Two selected images do not guarantee video endpoint control.
- Andre Athar is the authorized pilot stand-in, with separate character/outfit IDs. Preserve source assets, prior approved media and rejected attempts. Do not infer voice authorization.
- Keep native DynamicVRAM/offloading/component release and the current launch/attention stack. Do not patch core inference or add a second tensor-memory manager.
- Serialized local runtimes must prove a supported handoff. Do not remove the current worker's ComfyUI-running guard until its replacement is verified. No killing unrelated processes or editing shared Hermes defaults.
- All long model/media jobs are visible, queued and cancellable. Reconcile uncertain jobs before retrying. Completed stages are reused by complete input keys.
- Resolve real input/output/model roots through native interfaces. Stage generated outputs before loading them as inputs. No guessed paths, workflow-file parsing in place of live graph tools, or overwrite of existing projects.
- No paid/provider fallback, automatic download, dependency upgrade or unrelated service restart. A newly selected model artifact requires authorization. Existing SD15 baseline and manifests remain intact.
- Changes to a custom-node pack belong to that pack's real Git repository. Parent integration updates the existing lock only after reviewed pack changes are committed; a dirty worktree is reported honestly.
- Video generation, voice/music generation, lip sync and final-film delivery are outside this plan's execution phase. Exports are preparation snapshots.

## Review focus

1. A repeated phrase, Unicode character or technical follow-up must not silently change source ownership or point a shot at the wrong text. Pin in P3.
2. Two characters with the same Andre face must not share outfit, prop owner, review or subject-label identity accidentally. Pin in P5/P7/P8.
3. A queued local-model phase must not deadlock waiting for itself, nor allow Hermes to reload during ComfyUI sampling. Pin in P2/P13.
4. A disconnect after native acceptance must not submit a duplicate job, discard a selected image or mistake an old result for a new revision. Pin in P1/P8/P13.
5. Storyboard timing and selections must survive reopen/reorder without overwriting Suite video approvals or run editorial data. Pin in P9/P12/P13.

These are release gates, not claims that the current code already passes them.

## Starting point: reuse before extending

| Existing owner | Reuse | Extension needed |
|---|---|---|
| `production_generate.py`, `production_outline.py`, `production_validate.py` | Local-only calls, validation, compact outline and exact-source checks | Multi-scene decomposition, explicit provenance, bounded context packets and capability-verified runtime integration |
| `production_bootstrap.py` and its tests | Preview/digest/create, no overwrite, staged publication | Browser/V3 entry point, revision-aware reopen, complete reference requirements |
| `asset_intake.py`, `asset_vision.py` | Hash-preserving intake, preview/apply, bounded advisory classification | Project bindings, role translation and shared-runtime admission |
| `worker.py`, `shot.py`, `presets.json` | Existing native still graph construction and model profiles | Shared pure still compiler; verified reference-aware recipes; visible controlled submission |
| `master_studio_package.py`, `master_take.py`, `prompt_review.py` | Package resolution, frozen take checks, prompt review | Remove project-specific selection assumptions through an explicit project argument; extend admission to storyboard endpoints |
| Fantastic PromptBuilder | Model-specific prompt/reference UI and encoder evidence | Six-stage workspace, novice controls, V3 adapter, reliable editor/save behaviour |
| Context Loop Plan Studio | Timeline geometry, frame clocks, editorial controls | Storyboard source adapter with explicit production writes; no synthetic video checkpoints |
| H3 Project Suite | Existing media/clip review and later continuation | Link to preparation context; preserve its separate output manifest and approval semantics |
| Workflow Monitor Brain | Local evidence storage, report/comparison export | Preparation jobs, resource handoff observations, current-project default and creative review joins |

All listed existing files were found during research. Names below marked **new** are proposed files, not existing capabilities. Freeze exact pack revisions/real paths in P0; do not assume the installed directory is the Git root.

## Contracts to settle first

### Application interfaces

These are application-boundary interfaces, not changes to core `execution.py` or model APIs. Keep existing public functions callable and add new entry points where signatures differ.

| Interface | Proposed narrow contract |
|---|---|
| `production_store.read_project(project_root)` | Returns manifest, canonical document and revision digest after contained-path validation. |
| `production_store.commit(project_root, expected_revision, changes, reason)` | Validates an allowlisted structured change; atomically publishes the next revision and receipt, or reports a revision conflict with no partial active state. No arbitrary path/text patch interface. |
| `production_generate.plan_story(source, context, backend)` | Returns either a validated proposal with source-backed spans and explicit assumptions, or focused questions/problems; never writes assets or chooses paths. |
| `production_runtime.inspect_runtime(profile)` | Reports selected executable/model identity, supported request/lifecycle operations and observed ownership; a configured alias alone is insufficient. |
| `production_runtime.reserve_phase(request_id, phase, owner)` | Bounded reservation for the Studio request, with native queue state and supported external-runtime handshake. The queued phase revalidates ownership at execution. A reservation is not proof of global GPU exclusivity. |
| `still_recipe.compile_endpoint(production, storyboard, bindings, assets, recipe, shot_id, endpoint)` | Pure compilation to native graph + resolved reference manifest + input digest; no queue call. Endpoint is `start` or `end`; native unsupported inputs are reported explicitly. |
| `storyboard_jobs.prepare(project_root, revision, shot_id, endpoint, recipe_id)` | Freezes one immutable endpoint request, expected output branch and all input hashes; returns ready or actionable preflight findings. |
| `storyboard_jobs.submit(request_id)` / `reconcile(request_id)` | Submit at most one native prompt for the frozen request; reconcile native status, actual files and hashes before reporting completion or allowing a retry. |
| `storyboard.accept_pair(project_root, revision, shot_id, candidate_ids, decision)` | Validates exact candidate hashes and current dependencies, writes selected frame locators to production and an immutable human decision receipt as one recoverable transaction. |
| `storyboard_export.build(project_root, revision, export_kind)` | Creates a contained, versioned preparation snapshot with source/selection/review hashes and explicit readiness gaps. Never queues video. |

### Data and state

- New storyboard projects use production schema v2. Keep v1 reading/validation behaviour unchanged. A reviewed migration preserves existing IDs/bindings/spans, decouples IDs from display order, and makes the shot `scene` field authoritative for membership. IDs are never reused or renumbered after reorder/delete/split. Existing v1 projects are not upgraded in place automatically.
- Legacy consumers use explicit adapters. A v1 projection is allowed only when it meets every v1 invariant without renaming IDs or dropping v2 meaning; otherwise report an unsupported legacy view and use a v2 adapter. Every schema revision includes read/upgrade/unsupported-version tests.
- V2 adds `editorial = {version: 1, gap_before_frames: {shot_id: nonnegative_integer}}`, with zero for absent keys. Quantize `duration_s × fps` with decimal half-up rounding. In canonical shot order: `start_i = end_previous + gap_before_frames[shot_id]`; `end_i = start_i + duration_frames_i`. M1 uses zero gaps; P9 explicitly adds gap editing. Serial hard cuts have no overlap or added transition duration. Timed dissolves/fades are deferred until a versioned overlap contract exists. `shot_transitions.json` keeps separate H3 generation cut/continue intent.
- `storyboard.json` indexes endpoint targets and candidates by stable shot ID. A candidate includes request/native prompt ID, endpoint, parent start candidate when relevant, output locator/hash, recipe/model/encoder/VAE identities, seed, reference-role hashes, transform/crop record and dependency digest. Selected frame locators remain only in production.
- Retain existing `start_frame`/`end_frame` string semantics until current consumers are mapped. Store loader-resolvable frame locators there, with asset/candidate IDs and hashes in receipts; do not silently reinterpret path strings as opaque IDs.
- Character, location, prop and wardrobe IDs remain separate from UI labels and display order. Reordering does not renumber IDs. A central alias resolver unifies entity mentions only through a reviewed mapping.
- `assets.json` remains authoritative for input-use permission and selected source roles. Existing fields remain readable. Generated candidates are indexed without granting input-use or likeness approval automatically.
- `bindings.json` adds a versioned still-recipe namespace, leaving current H3 bindings intact. A binding states **consumed**, **metadata only**, **unsupported** or **not selected** for each role; “graph preview” and “encoder verified” are separate evidence states.
- A storyboard job has `prepared → admitted → queued → running → completed/failed/cancelled/unknown`. Crash recovery can enter `unknown` from any active state. `completed` requires readable output files and hashes. Creative state belongs to a review receipt, not this status.
- The submission receipt is durable before network submission. If acknowledgement is lost, the frozen graph includes the request ID as workflow metadata and native history is reconciled. If the native API cannot prove acceptance/non-acceptance, show **Check interrupted job** and prohibit automatic resubmission. Do not claim exactly-once execution from a client lock alone.
- Approval staleness compares semantic dependencies: source span/shot target, source reference hashes/roles, selected recipe and frame hashes. Timeline reorder alone invalidates adjacency checks, not unchanged image pixels. Rejected candidates remain inspectable.

## Milestones and critical path

| Milestone | Demonstration | Prerequisites / exit |
|---|---|---|
| M0 · Safe foundations | Open existing project, draft without losing text, preserve queue and existing work | P0–P2; runtime can be honestly assisted until the unattended handoff gate passes |
| M1 · First complete storyboard | One scene, two shots, four endpoint slots, approved Andre/outfit, save/reopen, timeline and HTML export | Thin paths through P3–P9, P11–P13; one qualified still recipe; no fake green review |
| M2 · Continuity pilot | Two characters cast with Andre, distinct outfits, two locations, recurring prop, six to ten shots | Expanded P3/P5/P7/P8/P9; reviewed prop transfer and reverse shot |
| M3 · Reliable creator workspace | Multi-scene revisions, interruption recovery, full UI/accessibility and reports | All P0–P13 gates, bounded longer-story tests, independent beginner study |
| M4 · Preparation handoff | Frozen storyboard/reference/timeline bundle accepted for later video work | P12 integrity plus human creative acceptance; video submission remains separate |

M1 is not delayed until every advanced task is complete. Build its minimal happy path and recovery first, then expand each existing owner. The critical path is **runtime handoff + canonical persistence → story/bootstrap → reference-aware still qualification → endpoint pair review → timeline/export**. CPU planning and UI work can proceed without loading image models.

| Work | Dependency to begin | Additional dependency for its live exit gate |
|---|---|---|
| P0 | Current checkout/tool access | None |
| P1 | P0 inventory and fixtures | None; deterministic tests |
| P2 | P0 runtime inventory | Supported runtime handoff and authorized bounded probe |
| P3 | P1 contracts; scripted backend first | P2 for real local Qwen |
| P4 | P1 plus P3 preview contract | P2 for queued inference |
| P5 intake | P1/P3 entity and permission contracts | P6/P8 for generated variants; reviewed source photos can be bound first |
| P6.1 compiler | P0 native loader inventory | No GPU needed for pure compilation |
| P8.1 first job path | P1/P2 and P6.1 compiled graph | P4 queue adapter and authorized source refs from P5 |
| P6.2 qualification | P8.1 controlled submission | Real output inspection; this qualifies a recipe before P8 full pair generation |
| P7 | P3 canonical scenes; P5 requirements | P6 capability results for model-specific promises |
| P8 pair/recovery | P5 selected refs, qualified P6 recipe, P7 targets | P4 browser adapter and real output review |
| P9 | P1/P7; placeholders first | P8 accepted pairs for full storyboard preview |
| P10 | P4/P9 surface exists | Real browser and supervised study |
| P11 | P1 receipt contract; baseline Brain | P8 runs and P2 handoff evidence |
| P12 | P1/P7; incomplete snapshots allowed | P8/P9/P11 for complete reviewed handoff |
| P13 | M1 thin paths above, then expansion | All declared live/creative/usability gates |

P6.2 deliberately uses P8.1's minimal controlled job path. It does not require the full pair workflow before a still recipe can be tested; this avoids a circular qualification dependency.

## P0 — Establish evidence and preserve the baseline

**Owner/files:** parent `studio/` integration; existing `.codex/README.md`, `STACK_OWNERSHIP.md`, runtime/model manifests, live panel graph; new dated `.codex/artifacts/storyboard-m1/` evidence. Product code changes: none.

### P0.1 Confirm the exact working stack

- [ ] Read current root and pack instructions, branch/worktree status and existing task ownership. Preserve uncommitted Bootstrap/outline/recipe work; identify what can be reused without rewriting it.
- [ ] Resolve actual pack Git roots and lock entries, including Brain's installed worktree, Dynamic and import-time memory/cancel hooks. Record relevant executable/model artifacts without copying credentials or private media into reports.
- [ ] Read live canvas outline, effective resolver inputs and node modes; inventory relevant workspace templates through native tools. Do not infer authority from the tab title.
- [ ] Record connected queue/resource state and native model-loader options. Distinguish configured model, discoverable file, compatible recipe and visually qualified recipe.

**Exit:** signed-off inventory artifact and untouched baseline; no unrequested launch, render or model change.

### P0.2 Freeze acceptance fixtures

- [ ] Add **new** `studio/tests/fixtures/storyboard/`: a tiny one-scene story, two-scene prop transfer, dialogue/repeated-name case, Unicode/repeated-phrase case, long-story case and contradictory casting case. Use fictional text; no private images in the Git fixtures.
- [ ] Write expected source spans, entity aliases, exact dialogue and known open questions. Keep creative “gold” choices outside deterministic correctness assertions.
- [ ] Record existing source/revision/selected-output hashes for a real baseline project; verify the SD15 baseline's manifests without replacing its model.

**Validation:** fixtures cover every Review Focus input; the baseline can be reopened unchanged. This is a proposed evidence run, not a benchmark already completed.

## P1 — Canonical records, revision transactions and dependency tracking

**Owner/files:** **new** `studio/production_store.py`, `studio/storyboard.py`, `studio/specs/production/storyboard.schema.json`, `studio/specs/production/production-v2.schema.json`; existing production schema/validator/Bootstrap and current project-reading callers (`film.py`, `master_studio_package.py`); **new** `studio/tests/test_production_store.py`, `test_storyboard.py`.

### P1.1 Define the minimum storyboard sidecar

- [ ] Pin the data/state contracts above with schema fixtures: endpoint targets, candidates, parent-start dependency, observations and receipt links. Do not copy canonical shot order/duration/selected pair into it.
- [ ] Map existing `refs`, assets, bindings and `start_frame`/`end_frame` consumers before adding fields. Specify compatible locator translation through native roots.
- [ ] Define source/proposal provenance and human review receipt shapes, including reviewer, exact hashes, decision, reason and dependency digest. Unknown evidence is explicit.
- [ ] Implement schema-version dispatch: preserve v1 rules, add v2 stable IDs/editorial timing and an explicit reviewed migration. Test reorder/delete/split and cross-scene moves without renumbering; test lossless v1 projections and clear refusal of lossy ones.

### P1.2 Make edits recoverable and conflict-aware

- [ ] Implement one contained project write owner with expected-revision checks, validated changes, immutable snapshots and a staged journal/publish protocol. Avoid pretending that separate file renames form one atomic multi-file transaction.
- [ ] Readers select one committed revision. A crash before publication leaves the previous active revision; after publication it finds a complete next revision. Preserve the existing top-level files as compatibility views, reconciled from the committed revision rather than independent writers.
- [ ] Inventory every current production/assets/bindings reader. Route controlled jobs and new UI through the same pinned revision reader. Legacy raw-file views cannot assemble an executable mixed-revision package; preserve their signatures through caller-side adapters and label any uncontrolled legacy execution accurately.
- [ ] Bootstrap creation remains no-overwrite. Reopen/resume uses the manifest, not replaying creation against a subsequently edited `production.json`. Retry the same creation request by its receipt.
- [ ] Test concurrent tabs, stale revisions, disk-full/incomplete publication, symlink/path escape, duplicate code/slug and non-ASCII project labels. No unrelated file is modified.

### P1.3 Invalidate only affected work

- [ ] Build explicit dependency keys for character/outfit/location/prop references, start/end targets, recipes, candidates and adjacency checks.
- [ ] Test change matrices: title-only; lens; identity source; outfit; prop state; shot reorder; source replacement; edited accepted start. Mark old evidence stale without deleting files or silently deselecting unrelated work.
- [ ] A review of unchanged pixels can remain an image review while preparation readiness becomes stale for changed story intent. Display that distinction.

**Gate:** all transaction and dependency fixtures pass without any model loaded. Commands: `.venv/bin/python -m pytest -q studio/tests/test_production_store.py studio/tests/test_storyboard.py studio/tests/test_production_bootstrap.py studio/tests/test_production_validate.py`.

## P2 — Safe local Qwen/Hermes and ComfyUI handoff

**Owner/files:** **new** `studio/production_runtime.py`; existing `asset_vision.py`, `production_generate.py`, local-worker docs; **new** `studio/tests/test_production_runtime.py`. Queued adapter is owned by the PromptBuilder pack in P4. Dynamic/core settings are observed, not rewritten.

### P2.1 Probe the selected runtime contract

- [ ] Verify endpoint ownership, executable/build, model artifact identity, chat template, context and structured-output support. Separate story-text from optional vision-review profiles.
- [ ] Test schema-constrained JSON plus semantic validation, incomplete/length responses, cancellation and wrong-model/wrong-listener rejection on the pinned build. Keep one bounded repair for malformed output; transport failures never reroute or silently regenerate.
- [ ] Establish supported managed unload/pause and reload prevention. If unavailable, retain an owned isolated server only under a proven coordination protocol. Publish the exact unsupported behaviour as an assisted-mode limitation.

### P2.2 Admit phases without replacing native offloading

- [ ] Implement the application reservation and queue-boundary handshake, with request owner, expiry/heartbeat and reconciliation. Record native queue state before admission and recheck at execution.
- [ ] Define external-busy behaviour: wait visibly or report **Another local model is using the GPU**. Do not kill it or assume Studio's lock covers it. A supported provider pause must be authorized and scoped to that provider's own job lifecycle.
- [ ] Verify release of the owned LLM worker before native image loading. Use available RAM and VRAM, not model file size, for admission; preserve configured desktop reserve and native component swapping.
- [ ] Test the queued LLM node recognizing its own prompt, native ComfyUI jobs arriving during handoff, Hermes automatic reload, client disconnect, timeout and expired lease. Never wait forever for the current job's own queue entry.

### P2.3 Recovery and profile qualification

- [ ] Define cancel → free/release owned resources → reconcile → bounded retry for real OOM/recovery. Restart is a last resort and follows normal authorization/queue checks.
- [ ] Measure actual release after success, cancel and failure. A process exit or UI “unloaded” label alone is insufficient; missing observations keep the gate open.
- [ ] Qualify context packets on the existing model before changing precision/offload/CPU policy. Compare useful-output quality and memory, not just tokens/second. Preserve CPU placement if a proposed change has no quality benefit.
- [ ] Keep the existing ComfyUI-running guard until the replacement passes the live contention test. Assisted serial mode cannot be labelled unattended-ready.

**Gate:** mocked scheduling tests pass, then one explicitly bounded live local round trip demonstrates no duplicate server, no other job interruption, actual release and no cloud traffic. `.venv/bin/python -m pytest -q studio/tests/test_production_runtime.py studio/tests/test_asset_vision.py studio/tests/test_production_generate.py`. Live evidence is separate from mocks.

## P3 — Faithful story intake and multi-scene understanding

**Owner/files:** existing `production_generate.py`, `production_outline.py`, `production_validate.py`, `specs/production/generate-prompt.md`; P1 store; existing tests plus **new** `studio/tests/test_story_breakdown.py`.

### P3.1 Preserve text and distinguish facts from choices

- [ ] Save the exact submitted story with a digest before asking Qwen. Make technical follow-ups a separate revision instruction, never a replacement script by default.
- [ ] Extract entities, aliases, places, scene boundaries, observable actions, exact dialogue and source spans. Deterministic code assigns IDs and validates cross-references.
- [ ] Preserve ambiguity: distinguish “not stated” from a proposed lens/outfit/time. Ask only a decision that blocks faithful preparation; the user can accept visibly labelled defaults together.
- [ ] Test repeated phrases, repeated character names, Portuguese/English accents, emoji and line endings. Define source offsets as Python Unicode code points and translate browser UTF-16 selections explicitly.

### P3.2 Expand beyond the compact pilot safely

- [ ] Retain the current compact one-scene path as a bounded mode. Add global entity extraction plus per-scene packets with stable IDs for larger stories.
- [ ] Allocate context budgets from the selected runtime's verified limits; include only relevant facts/adjacent continuity. Save intermediate packets/results and show **scene N of M**.
- [ ] Validate complete source coverage and exact dialogue after merging. Nonvisual exposition may be explicitly unresolved or proposed narration; it is not silently dropped. Overlapping source spans for multiple coverage shots are allowed when intentional and traceable.
- [ ] Preserve wardrobe/time/location changes. Do not flatten multiple locations, remove speech to fit a silent prompt, or invent unrequested story events.

### P3.3 Apply revisions as a previewed change set

- [ ] Show source/story changes separately from coverage/camera proposals. Accept a reviewed change set against the expected revision.
- [ ] Preserve stable entity/shot IDs on small edits; expose merge/split proposals when structure changes. Reordering never renumbers identity.
- [ ] Run P1 dependency invalidation and show what can be reused, what needs re-review and what needs generation. No automatic reroll on a source edit.

**Gate:** fixture expectations pass with a scripted backend first; then a bounded local Qwen fixture run has no unreported source omissions or rewritten dialogue. `.venv/bin/python -m pytest -q studio/tests/test_story_breakdown.py studio/tests/test_production_generate.py studio/tests/test_production_outline.py studio/tests/test_production_validate.py`.

## P4 — One front door, project creation and visible stages

**Owner/files:** PromptBuilder pack **new** `production_nodes.py`, `production_api.py`, `web/production_workspace.mjs`; its registration and `web_api.py`; parent Bootstrap/store/runtime. Add tests in that pack, not core ComfyUI.

### P4.1 Add the guided entry point

- [ ] Add one minimal V3 `StudioStoryboardAssistant` node/workspace entry using the existing extension registration pattern. It owns preparation outputs/status; it does not pass model tensors through for layout convenience.
- [ ] Present six stages, current title/scene/shot, persisted save state and one primary next action. Give **New movie**, **Open movie** and **Resume preparation** explicit meanings.
- [ ] Let advanced users inspect the real canvas/subgraphs and resolved inputs. Keep experiments and recovery variants outside the beginner chooser; do not delete them.
- [ ] Mount the workspace using native UI behaviour. Never require ordinary users to accept unrestricted Python import to open a story.

### P4.2 Connect reviewable Bootstrap and generic Master selection

- [ ] Preview title, source, scene/cast/place summary, proposed folders and defaults; create only the reviewed digest. Expose readable collision/conflict recovery.
- [ ] Replace hard-coded project/shot maps in `master_studio_package.py` with explicit project selection while preserving its current callable entry points/default existing project behaviour.
- [ ] Bind workspace, resolver, package snapshots and Brain to the same immutable project/shot IDs. Recheck live compiled identity before a job; a tab title is insufficient.
- [ ] Reopen the created project after browser refresh and show reference requirements. Do not replay project creation or reset mutable selections.

### P4.3 Queue planning work visibly

- [ ] Connect story jobs to the native queue with cancel/progress and P2 admission. HTTP handlers validate/enqueue; they do not hide long inference in request handlers or private background pools.
- [ ] Saving a story/plan is a deterministic local action; generating suggestions is a separate visible action. Preserve draft text on cancel, network failure or validation errors.
- [ ] Show resource stage and actionable blocking reason in plain language; put token/cache/runtime details under Details.

**Gate:** browser tests create/open/resume one fixture project without IDs/path editing, no duplicate scaffold and no GPU call from a save. Existing Master still resolves its baseline package. Pack Python route/node tests plus real browser flow are required.

## P5 — Cast, wardrobe, location, prop and RefMod banks

**Owner/files:** existing `asset_intake.py`, Bootstrap reference planning, `h3_recipe.py` role checks; P1 store/storyboard; PromptBuilder workspace/media/RefMod UI. Extend existing asset/intake tests; **new** `studio/tests/test_reference_requirements.py`.

### P5.1 Intake and role binding

- [ ] Discover existing project/library candidates through native assets interfaces and contained intake. Show thumbnails, original path, hash and proposed role before binding.
- [ ] Translate intake `environment` to production `location` explicitly. Separate physical source identity from per-character/per-wardrobe role bindings so shared Andre pixels do not collapse fictional characters.
- [ ] Preserve input-use authorization and human likeness/reference review separately. File presence, model confidence or a previous unrelated project selection does not grant creative acceptance.
- [ ] Reuse files by hash without moving or re-encoding originals. Preserve existing native-library associations and PNG metadata.

### P5.2 Prepare Andre's character/outfit variants

- [ ] Select an authorized clean identity source and inspect it. Establish one pilot character/outfit first; add further angles only for a demonstrated failure.
- [ ] Generate outfit/body variants with a qualified reference-aware still recipe, preserving face identity. Review character A and B side by side with explicit names/outfits.
- [ ] Record outfit IDs per scene and exceptions per shot through a deliberate schema/adapter extension if needed. Test same face/different clothing, reverse angle and both characters in one image.
- [ ] Offer **wrong face**, **wrong outfit**, **characters mixed up** and **keep this** review actions. A failed result stays in history; retries change one specified factor.

### P5.3 Prepare geography and recurring objects

- [ ] Build location anchor descriptions and a simple blocking map: entrances, recurring objects, light source, subject positions and screen-side conventions. Mark proposed geometry as a planning aid.
- [ ] Generate/review the establishing location, then only the working/reverse views needed by planned shots. Keep lighting/time variants distinct.
- [ ] Prepare prop shape/scale and relevant states (e.g. folded/open, held/on table); attach owner/state requirements to shots. Avoid one “everything” reference image as the sole bank.
- [ ] Compile missing/ready requirements from production plus selected assets. Changing one outfit does not regenerate an unrelated location bank.

### P5.4 Respect H3 RefMod derivation

- [ ] Inventory approved compatible RefMods and link each to source assets, role, entity, encoder/model identity and transform. Never infer identity from a RefMod filename alone.
- [ ] Retain original pixels for still-image recipes. If only a RefMod exists, require its source reference or mark that role unavailable to the still model; do not claim reversible extraction.
- [ ] Build a missing RefMod only when the selected later H3 handoff needs it, as a visible encoder job with an explicit budget. Cache by full derivation identity.
- [ ] Show which inputs the still recipe consumes and which are H3-only. Preserve **graph preview** versus **encoder verified** labels.

**Gate:** approved pilot bank survives reopen; every selected source has owner/role/hash/permission; same-face cast cannot leak outfit/prop bindings. No voice or video generation. `.venv/bin/python -m pytest -q studio/tests/test_asset_intake.py studio/tests/test_reference_requirements.py studio/tests/test_h3_recipe.py` plus hash-bound human reference review.

## P6 — Qualify still recipes for actual reference control

**Owner/files:** **new** `studio/still_recipe.py`, `studio/tests/test_still_recipe.py`; existing `worker.py`, `shot.py`, `presets.json`, native nodes and P8 job path. Use shared compilation at the caller boundary; keep H3 compiler model-specific.

### P6.1 Extract only the reusable graph compiler

- [ ] Reuse existing Klein/reference and Z-Image graph builders as pure compilation helpers. Do not copy a template graph per shot or rewrite model math.
- [ ] Declare model/encoder/VAE/precision, supported tasks/roles, reference ordering/limits, geometry, transforms, steps and sampler. Validate native `/object_info` registration and loader values.
- [ ] Keep unsupported/reference-metadata-only paths visibly labelled. If an adapter supports fewer supplied references, propose selection or staged edits; never silently truncate.
- [ ] Include all effective inputs in the cache key and output provenance, including crops and source order. Same seed with a different encoder or asset order is not a cache hit.

### P6.2 Run a bounded qualification matrix

- [ ] Verify the configured Klein GGUF through native loader choices first; do not download to fill an inventory gap automatically. Qualify an installed Qwen Image Turbo recipe only with its correct components and actual license/provenance record.
- [ ] Predeclare four tasks: identity/outfit preservation, two-character composition, location reverse view and prop-state end edit. Start with one seed/candidate per task; inspect before authorizing any extra attempt. A failed adapter check is recorded rather than filled with a text-only fallback.
- [ ] Record cold load, warm end-to-end time, reference encode cost, peak memory, cancellation and visual observations for identical task inputs. Compare one factor at a time; do not attribute speed differences to a model from mismatched jobs.
- [ ] Choose the smallest qualified recipe per task, retaining a higher-fidelity option only when it solves a demonstrated failure. Do not promise one universal best model or upstream benchmark speed on this machine.

**Gate:** at least one recipe actually consumes approved source references and passes the pilot's likeness/outfit/prop/location review. Native output pixels must be inspected; a queued/completed prompt is insufficient. `.venv/bin/python -m pytest -q studio/tests/test_still_recipe.py studio/tests/test_shot.py` verifies compilation, not quality.

## P7 — Shot list, coverage, camera and continuity targets

**Owner/files:** `production_outline.py`, production schema/validator, `storyboard.py`, existing `prompt_review.py`; **new** `studio/tests/test_shot_planning.py`; workspace shot cards.

### P7.1 Turn scenes into editable coverage

- [ ] Preserve source scene order initially; propose establishing/action/reaction/insert coverage with source spans and purpose. Multiple camera views may share the same story beat without duplicating the action in time.
- [ ] Assign visible start/end states and an observable change per shot. Preserve exact dialogue and state whether it spans a cut; record sound intent without generating it.
- [ ] Suggest splitting overloaded actions into smaller shots, showing the effect on duration and reference work. Let users retain executable creative choices; suggestions are not hard model limits.
- [ ] Show placeholders on the timeline immediately, so the user can direct rhythm before spending time generating every reference/frame.

### P7.2 Make camera intent editable and model-aware

- [ ] Expose plain choices with small examples: still, look left/right, move closer/further, follow subject, arc. Details show native shot size, lens and camera motion.
- [ ] Record direction, amplitude, speed, start/end framing and focal subject. Distinguish pan/truck and zoom/dolly in UI copy and recipe compilation.
- [ ] Add a blocking/eyeline sketch linked to location anchors and subject IDs. Declare any unsupported control as advisory; do not present two 2D endpoints as a precise camera trajectory.
- [ ] Compile existing H3 REF and FL prompt structures separately for later handoff. Pin subject/asset labels and retention intent to actual input binding, not UI order alone.

### P7.3 Establish continuity checks without forbidding style

- [ ] Track costume, location/time/light, prop owner/state, handedness, entry/exit, gaze and screen side at each endpoint. Check within-shot reachability and adjacent-shot continuity.
- [ ] Detect contradictory targets before rendering; expose a suggested repair or intentional exception. A jump cut or crossed axis can be an explicit creative choice.
- [ ] Test two Andre-cast characters exchanging a unique prop, a reverse angle and a scene change. A shared face must not unify their state records.

**Gate:** a user can inspect every shot's purpose/action/camera/endpoints before image generation; all source coverage gaps and unresolved continuity assumptions are visible. `.venv/bin/python -m pytest -q studio/tests/test_shot_planning.py studio/tests/test_prompt_review.py studio/tests/test_h3_recipe.py`.

## P8 — Controlled endpoint jobs, review and recovery

**Owner/files:** **new** `studio/storyboard_jobs.py`, `studio/tests/test_storyboard_jobs.py`; reuse `master_take.py` admission/evidence helpers, `still_recipe.py`, `storyboard.py`; queued node adapter and existing native output nodes. No generic `Run` bypass of required preparation checks.

### P8.1 Freeze and submit one endpoint

- [ ] Prepare a request with project/revision/scene/shot/endpoint, selected sources/roles/hashes, full recipe identity, seed, graph digest, target output branch and expected artifact locator.
- [ ] Preflight runtime locality, missing weights versus missing/disabled nodes, node modes, effective prompt authority and changed input files. Do not run a possibly paid/unknown graph as a local smoke test.
- [ ] Make the ordinary workspace generation button use this transaction. A direct advanced canvas Run must display its uncontrolled/uncaptured status or pass the same guarded preparation path; do not imply all manual runs are covered.
- [ ] Submit through the connected browser/native queue so Brain can receive available phase events. Include Brain output in targeted prompts; output targeting must not accidentally omit monitoring.

### P8.2 Build the pair in a controlled order

- [ ] Generate and inspect the start candidate first. Freeze its accepted-for-edit hash before preparing the end request.
- [ ] Stage the start through native asset/upload handling. End generation consumes the accepted start plus explicit state change and the minimum required bank refs; finished upstream jobs are not re-executed.
- [ ] If an end edit drifts, localize whether the failure begins at source binding, composition or edit. Inspect the relevant branch/intermediate output before changing the whole recipe.
- [ ] Provide an intentional static-hold path and preserve independently anchored end generation as a reviewed fallback. Neither silently changes the action or camera intent.

### P8.3 Review the exact pixels and persist selection

- [ ] Show start/end next to source character/outfit/location/prop references, with **Use this pair**, **Change start**, **Change end** and a short problem list. Distinguish provisional draft from accepted pair.
- [ ] Validate actual image decode, dimensions, file hash and dependencies before accepting. Persist selected production locators and review receipt together through P1.
- [ ] Vision checks may propose observations/abstain; they cannot approve likeness or emotion. Attribute every visual review to the reviewer and output hashes.
- [ ] Changing a selected start invalidates dependent end/pair review; unrelated approved shots remain intact.

### P8.4 Reconcile before retry

- [ ] Test double click, lost submission acknowledgement, browser close, queue cancel, ComfyUI restart, OOM and missing result file. Match native history and immutable request metadata to artifacts.
- [ ] Show completed/failed/cancelled/unknown separately. Unknown never triggers an automatic new seed or duplicate prompt. Resume reuses verified completed candidates.
- [ ] Verify no canvas/tab mismatch can write to another project's job, and no output from a prior revision can become the current selection silently.

**Gate:** four endpoint slots can be produced, reviewed, reopened and recovered with no duplicate request and no unreviewed automatic selection. `.venv/bin/python -m pytest -q studio/tests/test_storyboard_jobs.py studio/tests/test_master_take.py studio/tests/test_storyboard.py`; live browser/queue/media checks are additional gates.

## P9 — Reuse the timeline for planning and the storyboard animatic

**Owner/files:** Context Loop `web/h3_chain_plan_studio.js`, `web/h3_chain_plan_studio_core.mjs`; **new** `web/h3_storyboard_source.mjs` and matching JS tests in that pack; parent store/export and workspace adapter.

### P9.1 Add a storyboard source, not fake rendered clips

- [ ] Define a source adapter that projects production scenes/shots, reviewed frame locators and readiness gaps into existing timeline primitives. Map production shot IDs to timeline item IDs explicitly; do not confuse an H3 chain “scene” segment with a screenplay scene.
- [ ] Group shots by screenplay scene. Show start/end thumbnails, direction arrow, camera, duration and incomplete references. Keep placeholders useful before generation.
- [ ] Storyboard reorder/duration changes use P1 and affect canonical production. Existing video `editorial.json` cut/trim state is neither overwritten nor interpreted as story edits.
- [ ] Persist the chosen source/view and active shot on refresh without persisting a second canonical timeline.

### P9.2 Make timing predictable

- [ ] Use the v2 timing formula and decimal half-up rule above; edit explicit nonnegative gap frames through P1. Gaps contribute to total timeline duration and render as empty intervals. Do not overload H3 cut/continue settings.
- [ ] Test many short shots, hard cuts, explicit gaps, scene reorder, missing endpoint and non-default supported FPS. No cumulative floating-point drift or hidden duration reset; no timed overlap/dissolve UI is offered without a future contract.
- [ ] Keep planned duration separate from later H3 raw/delivered/context frames. Display any future conversion as a recipe proposal rather than changing the user's edit.

### P9.3 Preview rhythm without promising generated motion

- [ ] Support play/scrub of held start/end stills and scene/shot labels. Label the result **Storyboard animatic**.
- [ ] Make an optional encoded animatic a visible cancellable ComfyUI media job using seek/stream-based tools. Do not decode long videos into an image batch or run private encoders without progress.
- [ ] Let the user change pacing, shot order and creative notes without regenerating unchanged images. Re-run only affected adjacency checks.

**Gate:** storyboard and exported timing agree frame-for-frame after reopen; existing Plan Studio video timeline tests remain green. Run the pack's existing `_plan_studio_js_test.mjs`/source-timeline suites and new storyboard adapter tests using its documented commands; do not invent a new frontend build.

## P10 — Beginner UX, accessibility and honest recovery

**Owner/files:** PromptBuilder workspace and existing modal JS/CSS, Suite `web/h3_project_panel.js`, Context Loop timeline adapter; relevant UI tests in each owning pack. Changes stay scoped to observed issues.

### P10.1 Make edit authority and next actions clear

- [ ] Distinguish **Save story**, **Save shot**, **Use reference**, **Use pair** and **Prepare for video**. Show which library/project owns the edit and when it last saved.
- [ ] A linked Builder widget becomes a preview with an explicit route to its authoritative source. A saved prompt and unsaved canvas edit cannot appear equally authoritative.
- [ ] Retain selected versus pending candidates visibly. Separate creative selection from motion continuation and from destructive cleanup; keep the latter in advanced maintenance.
- [ ] Explain prerequisites at the point of action with one useful recovery step. Keep IDs, token tables and raw traces in Details.

### P10.2 Repair the reproduced UI defects

- [ ] Modal open moves focus inside; background becomes inert; keyboard traversal stays inside; Escape closes safely and focus returns to the trigger. Use correct accessible name/role/modal semantics and preserve draft edits.
- [ ] Remove narrow-screen horizontal overflow; test the reproduced 390-pixel width, tablet and desktop, zoom and long/localized text. Touch targets and essential actions remain usable.
- [ ] Replace invalid GUID/export metadata in newly generated workflows using native workflow serialization; verify load against the current frontend. Existing unsaved graphs are not silently replaced.
- [ ] Provide empty, loading, conflict, disconnected, partial and cancelled states that retain the user's text and selected media.

### P10.3 Verify with real users

- [ ] First run an expert keyboard/screen-reader/responsive pass on the actual workspace, not just component snapshots.
- [ ] Run a supervised beginner study on a prepared-reference story, then a fresh-story path. With children, use an appropriate supervised session and SFW fixtures; collect only local task evidence needed for the study.
- [ ] Record hands-on time separately from model waiting, coaching, wrong turns, recoveries and help openings. A successful expert demo does not establish child usability.

**Target:** at least four of five supervised beginners complete the prepared-reference storyboard path without procedural coaching; no wrong-project writes, duplicate jobs, lost accepted selections or accidental paid calls. At most two contextual help openings is a proposed target to reassess after the first study. Every essential action is keyboard accessible. These are product goals, not measured outcomes.

## P11 — Brain reports and bounded workflow improvement

**Owner/files:** actual Brain checkout from the lock (installed `ComfyUI-Workflow-Monitor-Brain`); `workflow_monitor/analysis.py`, `benchmark.py`, `evidence.py`, `web/report.js`; existing provenance/comparison/benchmark tests; parent receipts/events adapter.

### P11.1 Tie preparation runs to their actual inputs and project

- [ ] Join project/revision/scene/shot/endpoint/request/native prompt/output IDs without passing product bookkeeping into model code or core execution.
- [ ] Open Brain on the selected workspace project/shot by default; permit a deliberate cross-project comparison with a visible label.
- [ ] Capture available phases and runtime handoff observations. Label event completeness and unknown measurements; headless resource-only evidence cannot masquerade as per-node timing.
- [ ] Keep input authorization and creative review links separate from technical status. A resource report never turns a candidate into an accepted pair.

### P11.2 Make reports useful for tuning

- [ ] Report cold/warm/cache-hit state, end-to-end/active/wait/recovery time, model/component identity, steps/sampler/precision, reference count/size/tokens when measured, peak VRAM/RAM and offload/cancel observations.
- [ ] Add human review columns: identity, outfit, prop, location, action endpoints, adjacency continuity, reviewer/hash and pass/warn/reject/unknown. Do not collapse them into an invented automatic emotion score.
- [ ] Export CSV/JSON with definitions and evidence gaps. Compare matching tasks and frozen inputs; suppress causal speedup claims when control conditions or coverage differ.
- [ ] Predeclare each experiment's question, one changed factor, attempt budget and stopping rule. Start with one controlled candidate per condition; inspect before extending. Keep the previous profile if there is no useful quality benefit.

**Gate:** report links resolve to the exact artifacts/reviews; CSV and UI agree; mismatch/unknown tests suppress unwarranted claims. Existing Brain `test_provenance.py`, `test_evidence.py`, `test_benchmark.py`, `test_comparison.py` plus new preparation fixtures pass in the owning repository.

## P12 — Preparation exports and explicit video handoff

**Owner/files:** **new** `studio/storyboard_export.py`, `studio/tests/test_storyboard_export.py`; existing `film.py` export helpers and native asset staging; workspace export UI.

### P12.1 Build a useful review package

- [ ] Export a scene/shot list CSV, readable storyboard HTML/contact sheet, source/interpretation summary, cast/outfit/location/prop index, continuity report and planned timing.
- [ ] Include both endpoints for each shot and current review state; incomplete exports visibly mark gaps rather than omit shots. Contact sheets are review artifacts, never substituted as reference inputs.
- [ ] Provide a JSON preparation snapshot with schema version, stable IDs, hashes, selected pair locators, source roles, recipes, editorial order/duration and evidence links. Snapshot files are not new canonical owners.
- [ ] Make PDF optional through an already available print/export path. No new dependency is needed for the minimum delivery.

### P12.2 Validate the later model handoff without running it

- [ ] Produce separate capability-qualified payloads for H3 Ref2VA reference preparation versus FL2VA endpoints. Each states which start/end images are actually bound and which remain editorial references.
- [ ] Resolve required sources/RefMods and native loader names; preserve their hashes and model/encoder derivation. Missing input or unsupported role is an explicit readiness gap.
- [ ] Separate **Preparation complete**, **Creatively accepted** and **Ready for selected video recipe**. Confirming one never submits a video job or changes a Suite tail approval.
- [ ] Re-read current revision and output hashes when building the handoff. A changed image or story invalidates its old readiness receipt.

**Gate:** export opens offline, has every included shot, timing matches the timeline and all asset/review hashes verify. No external fetch, paid request or video generation occurs. `.venv/bin/python -m pytest -q studio/tests/test_storyboard_export.py`.

## P13 — Integration, migration and acceptance

**Owner/files:** parent Studio integration, each changed pack's own tests/docs, existing `.codex/custom_nodes.lock.json` after reviewed commits, dated acceptance artifacts. No broad upstream cleanup/refactor is bundled.

### P13.1 Prove M1 end to end

- [ ] Open the real browser workspace, submit the tiny fixture, review its interpretation and create its project. Check native queue/resources before any generation.
- [ ] Bind one reviewed Andre identity/outfit; generate exactly the planned two-shot endpoint slots with the qualified recipe. Inspect real pixels and reject/record failures rather than claim success from prompt status.
- [ ] Review and select each pair, adjust one duration, reopen, export HTML/CSV/JSON and verify their hashes/timing. Record any operator-only step as an open usability gap.
- [ ] Interrupt one bounded job, reconcile its exact outcome and resume without duplicating completed work. Capture observed release and recovery evidence.

### P13.2 Expand the continuity and revision pilot

- [ ] Use two Andre-cast characters with distinct outfits, two locations and a recurring prop across six to ten shots, including a reverse view and a prop transfer. Keep the actual pilot story human-authored/accepted.
- [ ] Change one outfit and one camera choice in separate comparisons; verify only the declared dependencies become stale. Reorder two shots and inspect adjacency checks without rerendering unchanged pixels.
- [ ] Test longer multi-scene text, exact dialogue and incomplete story inputs. Persist partial work/checkpoints; do not claim an unsupported story is fully covered.
- [ ] Recheck baseline Master, Builder, Suite approval/continuation and Plan Studio video editing. Preparation acceptance must not mutate those owners.

### P13.3 Package and close honestly

- [ ] Complete the beginner study and P10/P11 gates; list any remaining blocker with reproduction evidence. A passed smoke is not an independent usability pass.
- [ ] Review changes per repository, preserve unrelated work, and update the parent lock only to reviewed committed pack SHAs. Run `.venv/bin/python .codex/check_custom_nodes.py`; distinguish known dirty state from a clean reproducible stack.
- [ ] Document supported mode, verified recipes, known limits, cancel/recovery steps and the preparation/video boundary. Keep dated machine measurements under `.codex`, not shared agent rules.
- [ ] Deliver the frozen preparation package for human creative acceptance. Video generation becomes a new bounded phase with its own selected recipe and submission authority.

**Release acceptance:** M1 works; M2 continuity is reviewed; no unresolved data-loss, wrong-project, duplicate-submit or runtime-contention blocker remains; all included shots have exact reviewed endpoint pairs or declared gaps that prevent readiness; save/reopen/export pass; child usability claims are supported only by the actual study. The next video phase stays unqueued.

## Audit coverage

| Finding from the UX report | Tasks that address it | Acceptance evidence |
|---|---|---|
| F01 New movie requires integration | P3, P4, P13 | Story → created/reopened project without IDs/path work |
| F02 Checks are outside ordinary Run | P2, P8 | Actual generation action freezes/admit/reconciles the request; advanced escape is labelled |
| F03 Workflow chooser unclear | P4.1, P10.1 | One beginner entry; existing experiments remain accessible in advanced mode |
| F04 Several edit/save meanings | P1, P4.2, P10.1 | Conflict-aware save, owner labels and reopen tests |
| F05 Reference/camera syntax burden | P5–P7 | Role/camera choices compile to real consumed inputs and native prompts |
| F06 Selection conflated with continuation | P8.3, P12.2 | Pair selection cannot change Suite tail or queue continuation |
| F07 Runtime budget/recovery unclear | P2, P8.4, P11 | Bounded admission, observed release, actionable resume and measured costs |
| F08 Broken modal focus | P10.2 | Keyboard focus/background/return tests in the real browser |
| F09 Narrow editor overflow | P10.2 | Reproduced narrow viewport now retains essential controls |
| F10 GUID/unrestricted-script alarm | P4.1, P10.2 | Native serialized graph loads; ordinary story path requires no Python execution |
| F11 Completion spans disconnected tools | P9, P12, P13 | Complete preparation snapshot; later final-film path explicitly deferred |
| F12 Brain opens wrong project | P11.1 | Contextual report selection test |
| F13 Technical warning density | P4.3, P10.1, P11 | One next action, accurate Details and evidence gaps |
| F14 Dense visual hierarchy | P4.1, P9.1, P10 | Six stages, clear primary action, responsive beginner test |

## Validation strategy and stop rules

Run focused deterministic suites for each task; add only meaningful contract/failure tests. A typical parent integration gate after the files exist is `.venv/bin/python -m pytest -q studio/tests` plus changed packs' documented Python/JS commands. Do not claim the command passed before running it, and do not rerun unrelated GPU benchmarks after a documentation-only change.

Live gates progress in order: runtime handoff → one reference-aware still → one pair → two-shot storyboard → continuity pilot → beginner study. For a wrong completed image, inspect bound inputs and the earliest failing stage before rerolling. For an error/OOM, follow cancel/free/reconcile/retry. A new model, paid route or expanded generation budget is a separate decision; failure never authorizes an automatic cloud fallback.

Stop a qualification when its preparation question is answered. Preserve both passing and rejected artifacts, exact seeds/prompts and measured bottlenecks. Avoid repeated gesture/pixel tuning outside the declared comparison. All visual findings name reviewer and output hashes; all benchmark conclusions name evidence coverage.

## Open verification gates, not unanswered product decisions

- Can the installed Hermes route prevent automatic reload during a Studio lease? If not, keep assisted serial mode and do not advertise unattended completion.
- Which discoverable installed reference-aware still recipe passes identity, costume, geography and prop-state tests within current resources? Qualification decides; no download is assumed.
- Does a chosen end-frame edit preserve the start's identity and geometry sufficiently for the pilot? If not, disclose the recipe gap and use an explicitly reviewed alternative.
- Can the reused Plan Studio source adapter satisfy the keyboard, narrow-screen and save/reopen gates without mixing story and rendered-cut authority? Browser evidence decides.

These questions are assigned experiments in P2/P6/P8/P9. They do not require the user to guess technical answers before implementation can start. Emotional/narrative acceptance remains the user's decision at each actual creative review.
