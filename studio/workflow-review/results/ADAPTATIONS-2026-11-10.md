# Resource-bounded workflow adaptations — 2026-11-10

## Server and fresh-source verification

Started the canonical `.codex/launch.sh` at the user's request. ComfyUI is available at **http://127.0.0.1:8188**, PID **268448**, with DynamicVRAM, 1 GiB VRAM reserve, disabled pinned memory and NVMe hot-model paths. Startup log: `/tmp/comfyui-start-20261110-043140.log`. No startup import failure was found; the API answered and its queue was empty before testing.

Repeated all six reduced utility tests against this fresh server: prompt recording, image/mask previews, stitching, text overlay, two-frame GIF assembly and desaturation. **All six backend contracts passed.** Reviewed hashes, provider schemas and source modification times passed the runner's checks. This resolves the previously observed older-server/source-timestamp inconsistency, without claiming live-bytecode attestation or full original-example coverage.

Receipts: `.codex/artifacts/workflow-review-utilities/20261110T073229917860Z/`.

## Two new usable workflow copies

Find these in ComfyUI's workflow browser under **PC Adapted**:

| Workflow | Tested settings | Wall time | Sampled whole-GPU peak | Lowest available system RAM |
| --- | --- | ---: | ---: | ---: |
| `01 - SD15 Image Edit 512.json` | One 512×512 reference, batch 1, 20 steps, denoise 0.35 | 9.91 s | 2,423 MiB | 16.24 GiB |
| `02 - RealESRGAN Bounded Upscale.json` | Resize reference's longest side to 512, preserve aspect ratio, native tiled 4× upscale; 2048×2048 for square fixture | 3.25 s | 3,447 MiB | 15.29 GiB |

Files:
- `user/default/workflows/PC Adapted/01 - SD15 Image Edit 512.json`
- `user/default/workflows/PC Adapted/02 - RealESRGAN Bounded Upscale.json`

Both use **installed local weights only**. No downloads, installs, paid/API generation, extension changes, core changes or user-original workflow changes occurred. Output files are under `output/WorkflowReview/Adapted/`.

### SD1.5 editing

Constructed from the already reviewed `user/default/workflows/PC Test 01 - SD15 512.json`. Replaced empty latent creation with LoadImage → 512×512 resize → VAEEncode. Retained the native sampler/decode path, changed sunrise wording to sunset and used a fresh seed. The original source hash is recorded.

The 512×512 resize has cropping disabled: **non-square references will be stretched**. Use a square reference for this first preset. Denoise 0.35 made only subtle changes in the tested cabin scene; this is a working low-strength img2img configuration, **not evidence of reliable instruction editing, face identity preservation or a convincingly changed time of day**.

### RealESRGAN upscaling

Constructed native single-image reduction of the learned-upscale capability, using `RealESRGAN_x4plus.safetensors`. The installed template `utility-gan_upscaler.json` is actually video-based; this copy deliberately avoids its video decode/combine chain.

An initial direct 512→2048 run also passed: **3.78 s, 4,343 MiB sampled whole-GPU peak, 16.03 GiB minimum available RAM**. The everyday copy adds an explicit longest-side 512 resize so loading a larger reference does not silently request an enormous upscale. Native code uses 512-pixel tiles and reduces tile size on OOM; these are backend settings, not added widgets. Very large source-image decoding itself is not bounded by the resize, which happens afterward.

The bounded run reused the already loaded image/model nodes but actually executed the resize and upscaler. These times are **not isolated cold-load benchmarks**. Peaks are sampled whole-GPU/system values, not exact allocator or per-process measurements. The three new image tests reached at most **65 °C**; no thermal cancellation was needed.

## Results and limits

Both UI graphs passed static checking and UI/API correspondence against the live schemas. Outputs decoded at the expected dimensions. The contact sheet shows preserved cabin layout, subtle img2img changes and the upscaled reference; a full browser load/save/reopen check is still pending. Human creative acceptance remains separate from backend success.

![Reference, SD1.5 edit and RealESRGAN upscale](../../../.codex/artifacts/workflow-adaptation-20261110/contact-sheet.jpg)

Detailed evidence, API/UI graphs, histories, resource samples, copied outputs, source/fixture hashes and the one-off reproduction script are in `.codex/artifacts/workflow-adaptation-20261110/`. Its output directories are exclusive: rerunning it requires new run directories, not overwriting earlier evidence.

## Runner safety and tests

Changed only the test runner's cancellation path: `studio/review_pilots.py` now calls the fork's atomic **`POST /api/jobs/{prompt_id}/cancel`**, replacing the split queue-delete/`/interrupt` sequence. This prevents a cancellation from interrupting a successor prompt. Updated its exact-call regression test. **All 195 studio unit tests passed.** A live interruption was not intentionally triggered.

## Next distinct capabilities

Read-only source/model review identified two further candidates, **not tested or certified here**:

1. **SAM3.1 text-selected segmentation** with the existing bundled checkpoint, one image and zero refinement iterations. Its native detector internally resizes to **1008×1008**, so a smaller external input is not proof of lower inference VRAM. Resource-fit testing is still needed.
2. **FLUX.2 Klein Q8 single-reference editing**, preserving native ReferenceLatent conditioning, 512×512, four steps, CFG 1. The previous text-to-image pilot does not prove reference-edit memory fit.

ControlNet remains blocked by absent local ControlNet weights. No model acquisition is authorized by this report. The earlier Inbox question about acceptable everyday render time remains open and does not block compatibility investigation.
