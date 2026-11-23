# The Message — render performance plan (RTX 3060 Laptop, 6 GB)

2026-11-11. Read-only investigation; nothing was changed, restarted or queued.
Scope: the `studio/projects/the-message` Automated Draft and Shot Template graphs
with recipe `h3-ref-four-view-candidate-v1` (608×352, 56 frames, 24 fps, 20 steps,
`sa_solver`/`beta`, four reference pictures).

## Machine

| Resource | Value | Consequence |
|---|---|---|
| GPU | RTX 3060 Laptop, 5.8 GB usable, sm_86, 80 W default (1–105 W allowed), PCIe 4.0 x8 | Holds ~20% of the H3 transformer; the rest streams over PCIe every step |
| Chassis | Acer Predator PH315-54, shared CPU/GPU heat pipes, fans already 6,250 RPM idle | Prior runs throttled to ~530–570 MHz (vs 1,640 MHz cool) within a minute |
| RAM | 31 GB + 16 GB zram + 83 GB swap, swappiness 180 | H3 DiT (19.5 GiB) and TE (14.6 GiB) do not fit together |
| Disks | NVMe 3.3 GB/s (hot copies in `~/ComfyUI-models-hot`), SATA 535 MB/s | Hot copies are in place and first in `extra_model_paths.yaml` |
| Software | ComfyUI 0.44.2, torch 2.14.1+cu130, comfy-kitchen 0.2.40, comfy-aimdo 0.6.0, sageattention 1.0.6 | |

## How ComfyUI runs this workflow

1. **Prompt and cache.** `execution.py` walks the graph; outputs are cached by input
   signature (`comfy_execution/caching.py`, RAM-pressure mode). A loader in the prompt
   keeps its model object alive while the prompt references it.
2. **Model objects are mmap'd.** UNETLoader/CLIPLoader/VAELoader wrap safetensors in a
   `ModelPatcher`. Weights stay file-backed until used.
3. **DynamicVRAM (aimdo).** `comfy/model_management.py` + `comfy_aimdo` keep only what
   fits on the GPU resident and stream the rest per block. The H3 block loop uses
   `comfy.model_prefetch` (`comfy/ldm/minimax/model.py:759-773`) so the next block's
   weights upload while the current block computes.
4. **Pinned memory.** Without `--disable-pinned-memory`, ComfyUI pins up to 27.7 GB of
   host RAM (`cudaHostRegister`). Pinned pages cannot be reclaimed, so on 31 GB the
   rest of the system swaps.
5. **Quantized math.** The DiT's 200 linears are `int8_tensorwise` + `convrot`
   (group 256). comfy-kitchen dispatches them to native int8 IMMA kernels on sm_86
   (`comfy_kitchen/tensor/int8.py`, `MIN_SM_VERSION (7,5)`): no dequantize-to-bf16.
   The Qwen3-VL 32B text encoder is NVFP4 with `full_precision_matrix_mult`, so its
   weights are expanded to bf16 before each matmul (Ampere has no FP4 units).
6. **Attention.** H3 calls `optimized_attention(..., preferred_attention=self.comfy_attention)`.
   The checkpoint carries no per-module attention config, so the global choice applies.
   Today that is PyTorch SDPA (`Using pytorch attention` in every log).

## Where the time goes (one shot)

Model size: 50 blocks, hidden 5376, attention width 7168, gated MLP 14336 ≈ 19 B params.
Tokens: latent /16 spatial, patch 2×2, so 608×352 → 19×11 = 209 tokens per latent frame;
56 frames ≈ 15 latent frames ≈ 3.1k video tokens plus references, audio and text ≈ 5–8k.

| Phase | Estimate | Evidence |
|---|---|---|
| Text encode (TE load + Qwen3-VL) | 20–25 s per shot (NVMe) | Resource review R1–R3 |
| Sampler, 20 steps | ~85% of the shot | ~7 s/step of compute at full clocks; measured 16–22 s/step cool, 30–33 s/step throttled |
| Attention inside sampler | ~20% of FLOPs, ~30–35% of time (bf16 vs int8 linears) | FLOP estimate above |
| VAE decode + composite + save | tens of seconds | Resource review stage 4 |
| Measured total | 632 s (Scene 02, one shot); 936 s for two shots (auto-draft v001) | `.codex/artifacts/the-message-*` receipts |

Conclusion: the sampler is limited first by GPU heat, second by attention in bf16,
third by weight traffic (RAM/NVMe → PCIe). Raw int8 linear compute is already efficient.

## What is wrong right now

1. **Launch flags were lost.** The running server (PID 387810, started by a Copilot
   detached shell) runs `main.py --listen 127.0.0.1 --port 8188 --disable-auto-launch`
   instead of `.codex/launch.sh`. So `--disable-pinned-memory`, `--reserve-vram 1.0`
   and `--preview-method latent2rgb` are off. Every log today shows `Enabled pinned
   memory 27770`. On 2026-11-08 that flag alone moved the pilot from 622 s to 548 s
   and removed all swapping.
2. **The stage split is gone.** `comfyui-andre-shot-swap` (AndreH3StageSave/Load, run R3)
   is in `/mnt/data/.Trash-1000/files/`. The Automated Draft loop runs TE encode and DiT
   sampling alternately inside one recursive prompt, so 14.6 GiB of TE and 19.5 GiB of
   DiT compete for 31 GB every shot.
3. **Optimized attention is installed but unused.** `--use-ck-attention` (Comfy Kitchen
   int8 attention; `int8_attention_is_available` is True on this GPU) and
   `--use-sage-attention` (sageattention 1.0.6) are both available.
4. **Heat is unmanaged.** The GPU runs at the 80 W default and hits the driver's
   thermal target; clocks collapse to ~1/3.

## Plan

Every step is measured against the same shot, seed and recipe with the existing
`.codex/artifacts/h3-resource-review-2026-11-08/tools/{bench,resource_monitor,analyze}.py`.
Run `/free` and cool to ≤ 58 °C before each run. Record s/it, mean SM clock, throttle
reasons, swap traffic and total wall time. Compare outputs with ffmpeg PSNR.

### Phase 0 — Baseline (no changes)

Render one The Message shot (for example `MSG_S003_SH01`, fresh attempt ID) with the
current server and the monitor attached. This fixes the true current number; the
936 s auto-draft figure was taken under unknown flags.

### Phase 1 — Restore the qualified launch (no quality change)

- Immediately before any authorized restart, read the live `/queue` and coordinate an idle window with its users. Wait for running and pending work to finish; never stop active renders. Then stop the bare server and start through `.codex/launch.sh` only. Make whatever launcher
  agents use (Copilot detached shell, comfyui-mcp broker) call that script.
- Remove the duplicated `PYTORCH_CUDA_ALLOC_CONF` value from the launching environment.
- Expected: ~10–12% faster sampler, no swap, ~12 GB free RAM during renders (R1→R2).
- Rollback: start without the flag.

### Phase 2 — Thermal / power (owner decision, needs sudo)

Sweep one variable at a time, each on the Phase 0 shot:

| Run | Setting |
|---|---|
| T0 | 80 W default (Phase 1 result) |
| T1 | `sudo nvidia-smi -pl 65` |
| T2 | `sudo nvidia-smi -pl 55` |
| T3 | `sudo nvidia-smi -lgc 210,1200` (clock cap instead of power cap) |
| T4 | Best of T1–T3 + `system76-power profile battery` or CPU turbo off during renders (shared heat pipes) |

Also: laptop on a cooling stand, rear vents clear, dust check. A sustained ~1,100–1,300 MHz
beats a 1,640 → 530 MHz oscillation. Expected: 20–40% on the sampler if throttling is
removed. Settings reset on reboot (`nvidia-smi -rgc`, `-pl 80` to undo).

### Phase 3 — Attention backend A/B (quality check required)

| Run | Flag |
|---|---|
| A0 | PyTorch SDPA (current) |
| A1 | `--use-ck-attention` (Comfy Kitchen int8 attention; first-party path) |
| A2 | `--use-sage-attention` (sageattention 1.0.6, Triton) |

Same seed; compare s/it and frames (PSNR, plus visual review of faces/text/props).
Expected: 10–20% per step if attention drops to int8. Keep the fastest backend whose
output the owner accepts; add it to `.codex/launch.sh`.

### Phase 4 — Model-major batching for multi-shot runs

Goal: encode every shot first (TE only), free, then sample every shot (DiT only),
so the DiT stays in page cache and the TE is loaded once per batch.

- Restore `comfyui-andre-shot-swap` from Trash (its format supports `minimax_refs`,
  which core `SaveConditioning` rejects), or move the same Save/Load pair into
  `ComfyUI-H3-Project-Suite`.
- Extend `studio/h3_loop.py` to emit two bundles/prompts per run: encode-all, then
  sample-all, each reading the `.h3stage.pt` files. Keep the existing loop as the
  qualified fallback.
- Expected: removes one TE and one DiT reload per shot (tens of seconds each, more
  under RAM pressure) and keeps RAM free. Matters most for long runs (114 shots).

### Phase 5 — Draft tier (recipe qualification)

Add a separate pilot recipe (for example 12–14 steps, or 512×288) for blocking and
reference checks; keep `h3-ref-four-view-candidate-v1` for finals. Sampler time scales
linearly with steps and roughly with tokens. Requires the normal recipe
qualification; never silently replace the final recipe.

### Phase 6 — Housekeeping (small)

- `MiniMaxH3MediaLoader` decodes references to fp32 on CPU at full size; pre-scale
  sources to the 608×352 "match" size for less RAM and faster encode.
- ComfyUI-Manager runs a dependency install at every startup; disable for production
  sessions.
- Keep only packs this workflow uses loaded during long renders (49 → ~10).

## Measured results (2026-11-11)

Cold replay (`bench.py --free`) of `MSG_S003_SH01` tk004 (prompt `063db6d1`), same seed,
GPU cooled to 58 °C before each run. Output folder `output/Andre_H3_bench/`; monitor data
in `.codex/artifacts/h3-resource-review-2026-11-08/runs/msg-P*`.

| Run | Attention | Wall | Sampler | s/it | Busy SM clock | PSNR vs P0 | SSIM Y |
|---|---|---|---|---|---|---|---|
| P0 | PyTorch SDPA (launch.sh, pinned off) | 210.8 s | 184 s | 9.06 | 1,212 MHz | — | — |
| P3a | `--use-ck-attention` | 168.1 s | 147 s | 7.28 | 1,013 MHz | 38.6 dB | 0.984 |
| P3b | `--use-sage-attention` | 171.5 s | 147 s | 7.36 | 1,089 MHz | 38.7 dB | 0.984 |

- P0 reproduced the original tk004 video bit for bit (PSNR inf), so replays are deterministic.
- This shot takes ~211 s cold, not the 470–630 s estimated above; the 936 s auto-draft
  figure includes the recursive loop and two shots. The sampler is 87% of the time.
- Comfy Kitchen int8 attention is ~20% faster end to end at a *lower* mean clock;
  composition is unchanged at frames 0/28/55. SageAttention is no better.
- Throttling persists after the attention change: thermal (0x20) in ~56–70% and power
  cap (0x04) in ~28–42% of busy samples, peak 89 °C, minimum 487 MHz. Phase 2 remains
  the next lever.
- Owner accepted P3a; `--use-ck-attention` is now in `.codex/launch.sh`.
- `nvidia-smi -pl` is refused on this laptop ("not supported in current scope"), so
  Phase 2 can only use a clock cap (`sudo nvidia-smi -lgc 210,1200`) or cooling.

Phase 4 stage split, same shot, `--use-ck-attention`, nodes `H3StageSave`/`H3StageLoad`
(ComfyUI-H3-Project-Suite, safetensors under `output/h3_stages/`):

| Run | Wall | Text encoder loaded | Swap out | Min free RAM | PSNR vs P3a |
|---|---|---|---|---|---|
| P3a single prompt | 168.1 s | yes | 4.5 GB | 13.9 GB | — |
| P4 encode + save | 12.0 s | yes | 0 | 17.7 GB | — |
| P4 load + sample | 154.1 s | no | 0 | 17.8 GB | inf (bit-identical) |

For one shot the total is about the same; the gain is that sampling runs never hold the
text encoder, so a batch can encode all shots, then sample all shots without swapping.

Context Loop measurement: first two silent-proof shots (832×480, 73 frames, 20 steps)
in the real Automated Draft graph, run `msg-P4-loop2`, 1,330 s total:

| Shot | Extra tokens per step | Encode | Sampler | s/it | Busy clock | Peak temp |
|---|---|---|---|---|---|---|
| MSG_S001_SH01 (empty café) | 390 media + 650 text | 7 s | 331 s | 16.5 | 914 MHz | 90 °C |
| MSG_S001_SH02 (Andre RefMod) | 409 media + 7,224 RefMod + 1,972 text | 38 s | 903 s | 45.1 | 637 MHz | 93 °C |

Video tokens are ~7.4k per shot, so shot 2 runs ~17k tokens against ~8.5k: twice the
linear work and ~4× the attention, plus deeper throttling. RAM stayed above 14 GB.
The loop's model alternation costs ~30 s per shot (text encoder re-read). Decision:
do not restructure `h3_loop.py` for model-major batching (≈3–5% gain); keep the stage
nodes for manual staged batches.

The largest remaining lever is the reference token budget. The Andre identity RefMod
alone (7,224 tokens) is larger than the video. `max_total_tokens` only refuses bundles
over a limit; it does not shrink them, and RefMods keep the size they were saved at.
Next test: create a smaller Andre identity RefMod once (Compressed Reference, or a
smaller saved size), render the same shot, and judge likeness against the 7,224-token
version — a creative decision, not just a speed one.

Hermes Desktop's llama-server (Qwen3.5-9B, ~5.1 GB VRAM) is respawned by its supervisor
and reloads the model on demand. Close Hermes or unload its model before H3 render sessions.

## Not recommended

- `--highvram` / `--gpu-only`: 6 GB cannot hold either model.
- Re-enabling pinned memory, or more swap: measured slower and swaps.
- `torch.compile`: interacts badly with DynamicVRAM block streaming; small gain at
  this size versus heat limits.
- Changing quantization (e.g. 4-bit DiT) without a quality qualification.

## Expected outcome

| Step | Sampler effect | Cumulative per-shot (rough) |
|---|---|---|
| Phase 0 | — | ~470–630 s |
| Phase 1 | −10–12% | ~420–560 s |
| Phase 2 | −20–40% | ~280–430 s |
| Phase 3 | −10–20% | ~240–380 s |
| Phase 4 | −20–40 s per shot in batches | ~210–350 s |
| Phase 5 (pilots only) | −30–40% | pilots ~150–230 s |

These ranges were pre-measurement estimates; see "Measured results" for actual numbers.

## Decisions for the owner

1. Approve the Phase 1 restart, subject to a fresh queue check and a coordinated idle window.
2. Approve `sudo nvidia-smi` power/clock changes and the cooling setup for Phase 2.
3. Accept or reject the int8 attention output in Phase 3.
4. Restore the stage pack from Trash or reimplement it in Project Suite (Phase 4).
