# Farm motion comparison v001

Purpose: choose useful draft and reference-driven motion recipes for the same
two-character shot. This is a screening batch, not a universal model ranking.
No new weights, runtime changes or custom nodes are required.

## Jobs

| Order | Recipe | Production question |
| --- | --- | --- |
| Baseline | Completed `FARM_S001_SH01/tk002`, Ref2VA, 20 steps, sa_solver/beta | Existing reference-driven result |
| 01 | Ref2VA, 12 steps, sa_solver/beta | Can fewer steps preserve the requested action? |
| 02 | Ref2VA, 20 steps, sa_solver/beta, reference cache every 2 steps, no 8-bit cache | Does approximate caching preserve useful quality? |
| 03 | FL2VA, first-frame conditioning, 20 steps, sa_solver/beta | Does animating a composed frame preserve the two characters? |
| 04 | FL2VA + non-768p Turbo 8-step v1.0 LoRA at strength 1, 8 steps, euler/simple | Is the compatible Turbo recipe useful for quick motion drafts? |

All jobs use seed 151103, 832×480, 73 frames at 24 fps, video/audio sigma shifts
12/3, the same video VAE and text encoder, and silent output. Brain monitoring
and its existing automatic analysis remain enabled. Jobs execute sequentially
in the native ComfyUI queue, with normal progress and cancel controls.

Jobs 01–02 retain the farm package's two picture references, Andre RefMod and
REF prompt. Jobs 03–04 share the exact first frame from the baseline video and
an I2VA prompt expressing the same action. This changes both conditioning and
model family; it is a pipeline comparison. Job 04 changes a compatible bundle
of LoRA, sampler, scheduler and steps; it does not isolate the LoRA's effect.

The first frame already has a smile and contains any likeness imperfections in
the baseline. Judge subsequent smile movement against each clip's starting
expression; first-frame preservation alone does not establish original-reference
likeness. The baseline frame is a test input, not an approved production keyframe.

## Evidence and review

Frozen graphs, browser workflows, model inventory, first-frame provenance,
submission receipts and run IDs are stored in
`.codex/artifacts/farm-model-comparison-20261115/`. The mutable execution ledger
is `batch.json`; it must distinguish prepared, submitted, failed and completed.
Saved workflows are named `Farm Benchmark v001 - <job>.json` in the user's
workflow library. Outputs go to
`output/Farm_Reference_Lab/benchmarks/v001/<job>/`; Project Suite also preserves
clips and latents under `output/h3_projects/Farm_Benchmark_v001/`.

Before comparing a result, match native history to the frozen graph, verify
output hashes and decode, and link the Suite files and Brain run. Record:

- Two distinct people, stable left/right and wardrobe binding.
- Andre and Clara likeness relative to their references; separate uncertainty.
- Mutual gaze and chin movement; Clara's smile progression.
- Slow camera tightening, both faces retained, stable buildings. Distinguish
  apparent zoom from verified perspective change.
- Flicker, face deformation, identity mixing, extra people or unwanted objects.
- Wall time, actual sampling time and executed steps, cached nodes, conditioning
  cost, peak RAM/VRAM, temperatures and thermal throttling where available.

The historical baseline and warm-cache jobs are not controlled cold-start
timing trials. Model storage location also differs. Report those conditions;
do not infer model speed from total time alone. Model inventory records header
digests, paths, sizes and modification times, not full weight-content hashes.
The existing local text model's recommendations are advisory; it has not watched
the videos and previously ignored delivered visual review fields.

Choose a candidate only when it completes correctly and its relevant visual
criteria survive review. If a faster candidate looks promising, confirm it on
a second seed and a different motion shot before changing defaults. Keep the
reference recipe when a speed gain loses identity or the requested action.
This batch cannot establish the best uninstalled video model or larger model.

## Recipe sources

- [H3 model families](https://github.com/MiniMax-AI/MiniMax-H3#model-variants-and-input-specifications)
- [Turbo setup and prompt conventions](https://github.com/ModelTC/Minimax-H3-Turbo/blob/main/COMFYUI_SETUP_AND_INFERENCE.md)
- [Turbo I2VA example](https://github.com/ModelTC/Minimax-H3-Turbo/blob/main/example_workflows/video_minimax_h3_i2v_lightx2v_turbo.json)

The installed node schemas and compiled browser graphs are the local execution
authority. No source code from these external examples is executed.
