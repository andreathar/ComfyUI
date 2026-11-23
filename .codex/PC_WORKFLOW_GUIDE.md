# Tested workflows on this PC — 2026-11-09

> Live availability check, 2026-11-16: the Klein GGUF weights remain on disk, but
> `UnetLoaderGGUF` is absent from `/object_info`; the existing worker job is
> rejected before generation. The historical Klein results below are not current
> readiness evidence. Qwen Image 2.1 still lacks the named 8B encoder in the live
> loader choices. See [the kitchen first-frame test](artifacts/kitchen-first-frame-20261116/REPORT.md)
> for the preserved rejection and the existing H3 composition fallback.

**November 10 organization:** the four daily image workflows now live under **01 - Images** and the LC123 utility under **04 - Utilities** in the ComfyUI workflow browser. The changed Z-Image pilot is in **90 - Lab and Older Workflows** pending renewed safety review. See [the current ComfyUI workspace map](../reports/COMFYUI_WORKSPACE.md). Production stays inside ComfyUI; older pilot measurements below remain historical evidence.

Start with **PC Test 02 - FLUX2 Klein Q8 512** for the best subject match observed in these tests. Edit its Prompt node, keep 512×512 / batch 1 / 4 steps, and Run. Change the fixed seed for another variation. Use **PC Test 01 - SD15 512** for faster drafts.

| Saved workflow | Verified settings | Backend execution | Observed result |
|---|---|---:|---|
| PC Test 01 - SD15 512 | 512×512, 20 steps, CFG 7, DPM++ 2M/Karras | 15.23 s | Clean lake/forest image; cabin only partly visible |
| PC Test 02 - FLUX2 Klein Q8 512 | 512×512, 4 steps, CFG 1, Euler/simple | 78.39 s | Clear red vintage motorcycle on wet street |
| PC Test 03 - ZImage BF16 512 | 512×512, 8 steps, CFG 1, res_multistep/simple, CPU text encoder | 222.90 s | Clean red scooter; motorcycle prompt adherence partial |
| PC Test 04 - LC123 Prompt and Palette | Subject + scene + palette → prompt assembler → text preview; palette → SaveImage | 0.55 s (panel 0.9 s) | Text assembled and four-colour palette saved |

All four histories report success and completed=true. Images were visually inspected. These are single-run feasibility tests, not quality rankings across models or throughput benchmarks. Initial free VRAM was about 1.0–1.2 GiB of 5.7 GiB available to CUDA; another workload occupied much of the GPU. Pre-run free RAM ranged from 13.8 to 14.8 GiB for image tests. Peak memory was not measured. Z-Image history lists cached node 7 (its empty latent); no full cache-lineage audit was performed.

## Outputs

All final files are under `/mnt/data/Projects_SSD/ComfyUI/output/PC_Workflow_Tests/`:

- `SD15_512_00001_.png`
- `FLUX2_Klein_Q8_512_00001_.png`
- `ZImage_BF16_512_00001_.png`
- `LC123_Palette_00001_.png`

The original workflows were preserved. No model downloads, paid requests, attention-backend changes, or torch.compile changes were made.

## What is not ready or not covered

- **LC123 Examples - Pipes & Prompt Builders** is an intentionally unwired node catalogue, not a complete image-generation workflow. Use the connected PC Test 04 to see prompt assembly and persistent palette output. Its text preview must still be reviewed before using it to generate: the default scene includes “no main person,” which conflicts with a human subject. This test proves composition and output, not semantic consistency of arbitrary presets.
- **image_qwen_image_2_1_turbo_t2i** lacks `qwen3vl_8b_int8_convrot.safetensors`; its prompt-enhancement branch also references absent `qwen3.5_9b_qwen_image_2.1_pe_t2i.int8_convrot.safetensors`. Not generation-tested; no substitute or download performed.
- Higher resolutions, larger batches, ControlNet, and every installed extension are not certified by these four tests. The separate H3 test below covers one specific clip and preset.
- Existing workflow names containing historical timings such as “26s” or “30s” are not fresh performance measurements.

## Run IDs

- SD1.5: `8c8814e7-00e4-43cd-8b49-901c30dc7207`
- FLUX: `3cbaae4d-10af-44e0-b67f-24b4e305fabd`
- Z-Image: `1bb2bb52-cf01-4018-8cff-2a4621550710`
- LC123: `4091cf1c-3382-4f81-bd53-0812d504dde5`

## H3 FaceRefine — verified 6 GB preset

`H3_Face_Refine_Auto_Select` completed a 241-frame / 10.04-second clip in **13m 59s**, using manual **512x512 face crops** and **stitch_batch_size=2**. Select/upload the source in node 112. Saved output: `video/FaceRefined/RTX3060_512_00001-audio.mp4`. Retrieved file and complete decode verified: 1920x1080, 24 fps, stereo audio. Contact sheet inspected; detailed face quality and lipsync need playback review.

The local FaceRefine stitching patch fixes the previous full-frame GPU allocation failure; extension updates can overwrite it. Longer clips and larger crops are untested. Evidence and recovery backup: `.codex/artifacts/h3-6gb-adaptation-20261109.md`. Run ID: `ccf47590-2c88-49e9-a255-08f1d6eefb8e`.
