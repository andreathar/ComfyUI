# ComfyUI workflow review — November 9–10, 2026 snapshot

## Current direction: organize ComfyUI itself

The user chose existing ComfyUI extensions and local model management, not a separate Studio/Argon application. Swap-quality work is paused. Read [the current workspace map](../../reports/COMFYUI_WORKSPACE.md) for the organized workflow folders, dependency keep-list, recovery manifests and model-management distinctions. Earlier test locations below describe historical paths; files were subsequently relocated without content changes. The Z-Image pilot is in Lab because its current file differs from the older reviewed hash.

## November 10 continuation

ComfyUI was freshly started with the canonical launcher at the user's request. All six reduced utility contracts passed again with the source-timestamp guard satisfied. Two new local workflow copies are available under **PC Adapted**: SD1.5 image editing at 512×512 (9.91 s, 2,423 MiB sampled GPU peak) and aspect-preserving, bounded RealESRGAN upscaling (3.25 s, 3,447 MiB sampled GPU peak). These are backend-tested copies; frontend save/reopen and creative acceptance are still pending. Originals remain unchanged. No downloads or dependency changes were made.

Read [the continuation report](results/ADAPTATIONS-2026-11-10.md) for settings, evidence, limitations and the next segmentation/reference-edit candidates. The earlier restart question is superseded by the authorized fresh start; the everyday render-time question remains open. All 195 studio tests passed after switching runner cancellation to the atomic job-specific endpoint.

## November 9 review snapshot

**Inventory, all-graph static preflight and second pilot pass completed; exhaustive execution is not completed.** No originals were moved or renamed. No model downloads, paid/API generation, extension installs, shared-service restarts or cache-clearing requests were made.

The initial catalogue contains 1,187 unique graphs from 1,194 graph payload occurrences across extension examples, saved material, core blueprints and installed templates. Extension-only coverage is 355 payload occurrences / 350 unique graphs. The catalogue has 46 extension/candidate entries, including standalone/example files; these are not 46 successfully loaded extensions. Live filesystem placement can change while other sessions work.

## Folder map

```text
studio/workflow-review/
  START_HERE.md              this handover and next steps
  README.md                  generated discovery methodology and counts
  extensions.csv             extension ownership, paths, revisions and placement
  workflows.json             full source/hash/alias/node reference catalogue
  workflow-matrix.csv        spreadsheet index; not runtime certification
  model-references.csv       unresolved references extracted from graphs
  references/
    extensions.md            original workflow links grouped by extension
    models.csv               54 discovered physical model file paths and sizes
    qualification.json       graph → filename → local candidate paths
    test-queue.csv            heuristic families and blockers for every graph
    static-preflight.json     source/hash checks and static validation for every graph
    static-preflight.csv      readable static-check outcomes
    SOURCE_REVIEW.md          selected safe reductions and unsafe example paths
  tests/
    README.md                test-copy guidance
    pilots/                  reviewed adapted UI/API copies and changes, per run
    utilities/               six constructed, reduced extension API capability tests
  results/
    PILOTS.md                measured pilot outcomes and limitations
    pilots.json              seven machine-readable pilot receipts
    UTILITIES.md             six reduced utility tests and provenance caveats
    utilities.json           utility receipts and preserved output references
    utility-revalidation.json independent checks of GIF frames and both previews
    runtime-coverage.csv      every graph joined to actual/reduced execution evidence
  blockers/
    README.md                interpretation and discovery gaps
    workflows.csv            missing-schema observations and unknowns
```

## Model and path references

Original workflow paths remain authoritative. `workflows.json` stores absolute paths, checkout-relative paths, embedded-payload pointers, source hashes and duplicate aliases. `references/extensions.md` groups those links by owning extension. Node providers come from a localhost schema snapshot, not guesses from display names.

`references/models.csv` scans both the main `models` search tree (resolved to `/mnt/data/ComfyUI-models`) and configured extra paths including `/home/athar/ComfyUI-models-hot`. A matching basename is only a candidate: it does not prove the right loader folder, artifact integrity, full stack, compute compatibility or hardware fit. No multi-GB file hashing was performed for this inventory.

The first qualification pass assigns 1,068 graphs to `blocked_or_review_needed` and 119 to `preflight_and_safety_review_needed`. Neither category is a runtime test result, and **119 does not mean 119 safe/runnable graphs**. Model selectors without filename suffixes and auto-download nodes especially need manual inspection. Family labels are heuristic and may need correction.

## Static preflight

All 1,187 unique graphs and 1,194 source aliases were checked. At this snapshot all aliases matched their recorded hashes. **370 graphs passed the available static checks; 817 had static issues.** These are not runtime verdicts: UI required-input coverage is limited, 1,161 graphs still await frontend validation, and 350 retain subgraph correspondence uncertainty. The first checker pass reported 197/990; inspection found that connected converted widgets still retain serialized slots. Fixing their consumption (including seed control widgets) removed shifted-value false diagnostics in 173 graphs. Source files can change after this snapshot. See `references/static-preflight.json` for exact findings, not an inferred runnable count.

## Actual tests

Four existing PC test graphs were copied, given unique output prefixes and fresh sampler seeds where applicable, and executed sequentially. SD1.5, FLUX and Z-Image each completed a second fresh run: **seven backend successes across the four configurations**. Exact original source hashes are pinned in `studio/review_pilots.py`; changing an original requires a new safety review before that runner will execute it.

| Configuration | Observed wall time | Sampled whole-GPU peak | Lowest sampled available RAM |
|---|---:|---:|---:|
| SD1.5, 512×512, batch 1, 20 steps | 10.42 / 8.55 s | 2,308 MiB | 11.64 GiB |
| FLUX.2 Klein Q8, 512×512, batch 1, 4 steps | 45.24 / 51.54 s | 4,932 MiB | 11.54 GiB |
| Z-Image BF16, CPU text encoder, 512×512, 8 steps | 176.84 / 183.94 s | 5,060 MiB | 7.22 GiB |
| LC123 prompt/palette utility | 2.05 s | 132 MiB | 16.87 GiB |

There are two image runs per model and one LC123 prompt/palette run. Times include the runner's sampling/polling overhead, are not isolated cold/warm benchmarks, and peaks are sampled system values rather than exact per-process allocator measurements. Fresh sampler seeds avoid recycling the previous generated image; model/conditioning caches may still be reused. See run histories for executed/cached nodes. Two fresh image executions per model are recorded; this is limited repeat evidence, not long-term stability certification. Browser save/reopen verification remains pending.

All PNGs decoded at their expected dimensions and were visually inspected. SD1.5 produced a red cabin at a lake. FLUX matched the vintage motorcycle prompt. Z-Image produced a scooter, so exact subject adherence is weaker in this pilot. LC123 emitted four palette swatches and text, but the source combines a human subject with a scene saying “no main person”; this semantic conflict is recorded, not silently repaired.

Original evidence: `.codex/artifacts/workflow-review-pilots/<UTC timestamp>-<pilot>/` contains UI graph, API prompt, receipt, history and sampled resources. Images: `output/WorkflowReview/`. Organized copies under `tests/pilots/` are **pilot candidates**, not a certified all-extension library.

## Reduced extension capability tests

Six source-reviewed, model-free tests produced expected backend results: iTools text return, RMBG image/mask previews, RMBG stitching (1024×512), iTools text overlay, VHS two-frame GIF assembly, and LC123 full desaturation. They use bounded local image fixtures and are constructed reductions of example graphs—not executions of the complete original examples. Both GIF frames were independently decoded and confirmed distinct; both preview PNGs were separately decoded. The RGB fixture's empty mask is 64×64, so this does not test segmentation accuracy.

**Provenance limitation:** the server PID 677706 started at 2026-11-09 15:38:49 UTC, before four reviewed iTools files were modified at about 16:11:26 UTC. The observed iTools backend contracts are real, but loaded-code/source correspondence is uncertain. `studio/review_utilities.py` now checks expected schema providers and refuses execution when reviewed source mtimes are newer than the explicitly identified server. These are consistency checks, not bytecode attestation. Earlier in this snapshot, a controlled restart was still pending. The November 10 continuation above records the authorized restart and revalidation.

Avoid blindly running apparently model-free examples: RMBG can auto-download segmentation models; its URL loaders can access the network; Canvas explicitly clears device caches; full iTools examples include sampling. Exact reviewed source paths and reduced prompts are retained with receipts.

## Resource and shared-server gates

RAM headroom briefly recovered above 10 GiB, allowing the second image pass. It fluctuates substantially; the second Z-Image run reached 7.22 GiB available RAM. No model unload or process termination was attempted. Recheck actual resource availability and queue ownership before every new run. The runner uses prompt-specific cancellation requests if monitoring encounters a limit/error; cancellation is cooperative, not a hard real-time memory bound.

## Remaining review work

1. Resolve 528 uninspected media/archive candidates and four symlink-directory traversal gaps, or explicitly document exclusions. Two JSON parse errors are comment-containing config files (`.vscode/launch.json` and `jsconfig.json`), not proven broken workflows.
2. Review the 119 no-obvious-blocker candidates for completeness, input media, implicit model downloads, arbitrary-code nodes, local services and loader compatibility before queuing anything.
3. Exercise distinct utilities, image editing/control, upscaling, segmentation, video/audio and 3D workflows with appropriate fixtures. Disabled packs stay disabled unless a separate change is approved.
4. Complete browser verification; image pilot repeats have now been recorded. H3/Qwen/large video tests require complete-stack/backend/resource checks; file presence is insufficient.
5. Convert safe successful candidates into a curated everyday library, with one result or precise reason for every graph. Keep remote-only and missing-model workflows visible rather than declaring them failures on this PC.

The acceptable everyday render-time threshold is still awaiting the person's Inbox choice. Inventory and dependency review do not depend on that answer.

## Verification

All **195 studio unit tests pass**, including regressions for converted widgets, missing preview evidence, truncated GIFs and targeted cancellation on Ctrl+C. No core inference, extension, model, shared-server or user-original workflow code was changed. The existing local audit helper `studio/workflow_health.py` received the narrow widget-decoding fix.

## Commands

Run from `/mnt/data/Projects_SSD/ComfyUI`:

```sh
.venv/bin/python studio/workflow_catalogue.py --port 8188
.venv/bin/python studio/qualify_workflows.py
.venv/bin/python studio/preflight_workflows.py
.venv/bin/python -m pytest -q studio
# Preflight only; does not queue:
.venv/bin/python studio/review_pilots.py sd15
# Explicit execution, only after checking current RAM and queue:
.venv/bin/python studio/review_pilots.py sd15 --run
```

This is a historical qualification snapshot; some original paths have since moved. These commands refresh generated files in place by default. If you need a current inventory, use `workflow_catalogue.py --output <new-directory>` rather than overwriting the snapshot; the qualification and preflight scripts still target the default directory. Model/download and extension-change decisions are separate.
