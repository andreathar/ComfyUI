# Plan: review the André H3 face-swap workflow and its custom nodes for resource use

Written 2026-11-08 by Claude. Status: **proposed. Nothing in it has been executed yet.**

## Goal

Find the node order, stage boundaries and runtime settings that let this workstation run the
"trim every shot, swap the face for André" pipeline across all 114 shots without RAM thrash.
Quality must stay at least as good as the current masked pilot. The work is to review and
measure, then write a proposal. Changes are made only after approval.

## What is already decided (Plannotator history, not reopened here)

Sources: the Inbox threads `andre-comfyui-reference-lab`, `andre-shot-swap` and `comfyui-workflow-health`,
plus `.codex/artifacts/h3-local-workflow-research-2026-11-08.md` and `h3-reference-audit/README.md`.

- Local H3 is the engine. Take 1 was judged better than Kling.
- Pipeline: tracked SAM mask, then masked RefMod encoding, a low-resolution pilot, a source composite,
  exact-length delivery with original audio, and a pending take in H3 Project Suite.
- References: frontal 5332 plus three-quarter 5334a plus profile 5334, all approved. The three-view pilot
  (prompt `4476f2bd…`, 18:08 to 18:19) has finished, and Codex is reviewing it.
- Claude branches stay muted and paid. They are for planning and review only, never on the render path.
- The 114 shots are already cut and analysed. Shot 75 is the test bed.
- Open, unrelated: the Kling 26-video history question in `andre-shot-swap`.

## Facts measured today (18:23, queue idle)

| Item | Value |
|---|---|
| Weights the pipeline touches | H3 int8 19.53 GiB, Qwen3-VL-32B NVFP4 14.61 GiB, video VAE 2.62 GiB, audio VAE 0.58 GiB, SAM 3.1 1.75 GiB. **About 39 GiB in total, against 31 GiB of RAM and 6 GiB of VRAM** |
| ComfyUI while idle | 16.4 GiB RSS, 4.15 GiB VRAM held, 2 GiB of system RAM available |
| Swap in use | 17.7 GiB in `/mnt/data/swapfile`, on a **SATA Kingston SA400**, plus 2.1 GiB of zram. The models themselves are on the NVMe |
| Launch flags | `--reserve-vram 1.0 --preview-method latent2rgb`. Default RAM-pressure cache with no thresholds. No async-offload or pinned-memory tuning |
| Attention | `comfy kitchen attention`. `sageattention` and `flash_attn` are not installed |
| Run times | Encode 117 s. One-view pilot 8m33s, three-view pilot about 11m39s (from history timestamps; not a controlled comparison) |
| Custom nodes | 52 entries. Import time is only about 5 s in total, so startup cost is not the issue. The only runtime `model_management` monkeypatch found is in `ComfyUI-Apt_Preset/NodeBasic/C_flow.py` |

**Main hypothesis.** The Qwen3-VL encoder and the H3 model do not fit in RAM together. When both are
reachable in one graph run or one cache, the excess goes to swap on the slow SATA disk. Ordering the
stages so that only one heavy model is resident at a time is probably the largest win, ahead of any
per-node tweak.

## Observations on the open canvas (`Andre - H3 Three View Comparison Shot 0075`, about 90 nodes)

These are candidate findings for Phase 1 to verify.
1. **Legacy branch.** `MiniMaxH3ReferenceToVideo` (200) has no connected outputs, so it never runs.
   The Reference Splitter (225) is still needed by the input check (380), the review frames (396) and the GUARD (402).
   This adds clutter and makes the graph harder to reason about.
2. **Operation by note.** The note says "run only 399", "never Run All", and that 405 and 406 still point at the
   baseline. Safety currently depends on a human picking the right output node. A mistake reloads
   SAM, Qwen and H3 in one run.
3. **Set/Get indirection** (about 40 Set/Get nodes) hides which loaders each output actually pulls in.
4. **Widget values that look wrong but are not used.** Node 383 shows 1344×768, but links 390/391 override it.
   Node 200 shows length 124.
5. **No preview while sampling.** `ModelPreviewOverrideKJ` has `tiny_vae=none` and suppresses the default
   preview, and `taeh3` is missing. A bad take shows up only after about 10 minutes.
6. **Composite memory.** The composite (384) is capped at `max_size 512`. A full-resolution composite needs
   about 1.7 GiB of float32 for the output alone.
7. **Two video encodes.** The MP4 (386) and the lossless verify output (399) both encode. Check whether
   production needs both on every run.

## Phases

### Phase 0: coordinate and baseline (read-only)
- Ask Codex in the Inbox thread to finish its review of the three-view pilot first. Agree on who owns the
  live canvas, so two agents never edit it at once.
- Reuse the existing monitor (`.codex/artifacts/h3-shot75-monitor-*`). Extend it to log `vmstat` swap-in and
  swap-out, per-process RSS and swap, VRAM, GPU temperature and clocks, and per-node start and end times
  from the websocket `executing` events.
- Measure one baseline replay of the current pilot (same seed) to get per-stage time and memory curves.
  **This uses the GPU for about 12 minutes and needs approval.**

### Phase 1: node-by-node inventory of the open workflow
- Export the graph and the API prompt. Classify every node by role (loader, encode, sample, decode, composite,
  export, review or dead) and by stage (1 SAM, 2 encode, 3 sample, 4 finish).
- For each output node, compute which loaders it pulls in, with Set/Get resolved. This is the "blast radius"
  table.
- Map each class_type to its pack, version and commit. Mark which of the 52 packs this pipeline actually uses.
- Read the code of the heavy nodes (Fantastic RefModTextEncode, EditComposite, ObjectMask, H3Context,
  ProjectSave, ModelPreviewOverrideKJ). Find where tensors are kept (CPU or GPU, float32 or float16),
  what they cache, and whether they release models.

### Phase 2: resource model per stage
- Find the minimum set of resident weights for each stage. Check whether the current cache keeps the
  CLIPLoader and UNETLoader outputs alive across stages.
- Find out whether weights load as mmap'd, file-backed pages (cheap to drop, re-read from NVMe) or as anonymous
  copies (which go to the SATA swapfile). This decides whether `--fast-disk`, `--mmap-torch-files` or
  `--disable-pinned-memory` help.
- Evaluate the ways to free memory between stages: native `/free`, `ComfyUI-DistorchMemoryManager`,
  `comfyui_memory_cleanup` and the KJ purge nodes. Keep one that works correctly on ComfyUI 0.44.2.
  Drop the duplicates.
- Persist intermediates per stage so that a later stage never needs an earlier model. Stage 1 already saves
  the SAM mask. Stage 2 encoded conditioning goes through a Fantastic RefMod store or a project latent.
  Stage 3 already saves the latent.

### Phase 3: compute per run (A/B with the same seed, pilot resolution)
Test one variable at a time:
- cache mode (`--cache-ram` thresholds against `--cache-none`)
- `--reserve-vram`, async offload, pinned memory
- the current attention backend against sage attention (needs an install, so approval)
- `max_total_tokens` and `stack_pictures` for three references
- reference `resize` 512
- the 73-frame padding rule

Also record thermals (90 °C was seen earlier). Report time, peak RSS, swap-in GB and output difference.

### Phase 4: proposed structure for the 114-shot run
- **Model-major batching instead of shot-major:**
  1. SAM masks for all queued shots
  2. Qwen encoding for all of them, then unload
  3. H3 pilots for all of them
  4. review
  5. H3 finals
  6. composite and export

  This way each heavy model loads once per batch.
- Split the canvas into one saved workflow per stage, or use group bypass toggles (rgthree), so that no
  stage can pull in another stage's loaders. Remove the dead branch, replace the "run only X" notes with the
  stage structure, and point the replay and review loaders at parameters instead of hard-coded files.
- Driver options: `comfyui-andre-shot-swap` (already has shot jobs) or the H3 Project Suite hub, queued
  through the API.
- Make the early-failure gate cheap. Use a tiny preview decoder (`taeh3`, a pinned catalogue entry, needs
  download approval) or a short pilot that decodes a few frames.

### Phase 5: custom-node hygiene (proposal only)
- Make a table of the 52 packs: used or unused, overlapping (two GGUF loaders, three model or LoRA managers,
  two memory managers, about nine H3 packs), runtime patches (`Apt_Preset C_flow.py`), and last update.
- Recommend packs to disable, each with its reason. Disabling means moving the pack under `custom_nodes/.disabled/`
  and restarting, which needs approval. Back up first to `/mnt/data/backups/comfyui/`.

### Phase 6: validate and hand off
- Rebuild shot 75 with the proposed structure. Compare it with the baseline on wall time, peak RAM, swap-in,
  pixels outside the mask (must still be zero changed) and audio samples (must still match exactly).
- Then pilot two or three more shots of different types (a wide shot, a small face, an occluded face)
  before scaling up.
- Write the report to `.codex/artifacts/h3-resource-review-2026-11-08/`. Post the summary and decisions
  in a new Inbox thread, `h3-resource-review`. Record verified fixes in akb.

## Approval gates (nothing here is assumed)
- Editing the live canvas: wait for Codex to finish its review, then save as a new workflow and never overwrite.
- GPU benchmark runs (Phases 0, 3 and 6), each about 10–12 minutes.
- Changing launch flags or restarting ComfyUI. Disabling packs.
- Installing `sageattention`. Downloading `taeh3`.
- Any paid Claude or API call.
- Nothing is pushed or merged into `master`. No core patches.

## Outputs
1. Node inventory and blast-radius table (Phase 1)
2. Per-stage resource model with measured curves (Phase 2)
3. A/B results table (Phase 3)
4. Proposed stage workflows and batch driver design (Phase 4)
5. Pack-hygiene table (Phase 5)
6. Shot 75 before-and-after validation (Phase 6)
