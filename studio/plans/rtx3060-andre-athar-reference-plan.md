# RTX 3060 capacity and Andre Athar reference plan

Status: existing-Klein route approved and implemented in OpenJutsu; frontend built and serving at http://127.0.0.1:3000. User will upload approved references through the frontend. Actual identity-render and GPU/RAM measurements remain pending those uploads. Native FLUX3 defaults remain a separate path with missing models; no new model downloads or ComfyUI restart were performed.

## Goal

Create identity-consistent Andre Athar reference stills for later manual use in Kling: face angles, expressions, wardrobe, full-body views, and scene/first-frame compositions. Optimize for recognizable identity and usable stills, not merely a completed render or maximum resolution. No automatic uploads or paid Kling/API calls.

## What we know, and what we do not

| Item | Evidence / limit |
| --- | --- |
| GPU | RTX 3060 Laptop, 6144 MiB total VRAM. At the planning snapshot, 993 MiB used and 4814 MiB free. |
| Host memory | 31866 MiB total RAM; 11156 MiB available at the planning snapshot. Swap already used: 17965 MiB. These figures must be sampled again before testing. |
| Z-Image | 1024×1024 succeeded with Qwen text encoding on CPU and diffusion sampling on GPU. GPU text encoding previously failed with `VRAM grow failed: 777912320 bytes`. |
| FLUX.2 Klein Q8 | A 1024×1024 text-to-image run succeeded. This does not verify reference/identity editing. |
| DA3 Mono Large | Two frames, mono, 504, upper_bound_resize, default dtype succeeded in 10.4 seconds. Sampled whole-device VRAM peaked at 4886 MiB. Not a full-video or isolated-model measurement. |
| Model storage | `models/` resolves to `/home/athar/ComfyUI-models` on `/`, not the large `/mnt/data` filesystem. Download planning must use the destination filesystem's actual free space. |
| Retry target | `/mnt/data/Projects_SSD/openjutsu`, a Next.js application over ComfyUI. Start with `/mnt/data/Projects_SSD/openjutsu/workflows/picture/from_picture_prepare_flux3.api.json`, not the separate H3 video generation stage or the unrelated open ComfyUI template. |
| Current MiniMax template | A native local graph, not assumed to be a remote API: includes a video diffusion model, Qwen3-VL 32B quantized text encoder, video/audio VAEs and a LoRA. It requires a separate compatibility/RAM budget before any run. |
| Andre identity anchors | No approved set located under this checkout's `input/refs/`; user must identify the authoritative files. Do not choose substitute faces. |

A checkpoint larger than 6 GB is **not automatically unusable**. Disk size is not runtime VRAM. Weight storage/compute dtype, supported quantization, offload implementation, activations, resolution, frame count, reference count, and host RAM all matter. Offloading weights cannot remove an activation-memory limit, and swapping heavily can make a technically successful model impractical.

## 1. Classify each workflow before running

Create an evidence-backed entry for the exact graph and model files:

1. **GPU-resident:** weights plus working buffers fit at the tested shape.
2. **Split components:** large text encoder on CPU; GPU diffusion and supported VAE placement. This is the proven Z-Image starting point.
3. **Native partial offload:** supported model patcher streams/evicts weights between RAM and GPU. Test host RAM, transfer cost and activations as well as VRAM.
4. **Blocked or impractical:** missing/incompatible model or node, insufficient host memory, repeated allocation failure, or unacceptable paging/latency. Record the reason instead of calling it optimized.

Keep “supported by the loader,” “completed once,” “stable at this shape,” and “identity approved” as separate results. File names such as “26s” are not benchmark evidence. Quantized checkpoints need a supported loader/device path; smaller file size alone does not establish compatibility.

## 2. Let the existing memory owner manage models

- Start with the existing server and native model-management/patcher behavior. Inspect its effective backend; do not infer that every custom loader supports partial offload.
- Keep one GPU job running at a time. Batch size 1; sequence character views as separate jobs. Group compatible work by model family to avoid needless reloads.
- Run stages in order: reference preprocessing → encode/conditioning → diffusion → decode → optional upscale. Avoid keeping unrelated generators resident just to produce one reference still.
- Keep large encoders on CPU when that is the tested safe path. Do not force `gpu-only`/`highvram` on this 6 GB machine.
- Native eviction may release GPU allocations while retaining CPU weights. Measure both. Clearing allocator cache does not unload live model tensors or solve host-memory pressure.
- Use a global unload/free request only during a coordinated idle window; it affects the shared server, not just one workflow. Never stop another app/agent or restart the server incidentally.
- Do not add tensor caches, manual `.to()` juggling, or memory-policy code inside model implementations or arbitrary nodes.
- In this installed fork, `--lowvram` is documented as ineffective when dynamic VRAM is enabled. Confirm the live backend from the real startup log (`DynamicVRAM support detected and enabled`), not NVIDIA hardware alone. If a later restart is approved, test dynamic `--vram-headroom 0.5` separately from estimate-based `--reserve-vram 0.5`, or the legacy `--disable-dynamic-vram --lowvram` path. These are experiments, not promised fixes; do not stack them initially. `--cpu-vae` is a decode-specific fallback with a host-memory cost. Avoid aggressive CPU offload flags while RAM is already pressured.
- A `/free` request queues flags for the worker; HTTP success alone is not proof that models were unloaded. Confirm the resulting GPU and host-memory state.

The current available RAM is below the roughly 12 GB free-RAM starting guidance for Z-Image in the shots skill. Before another large Z-Image/encoder load, ask to close competing apps and remeasure; extra swap is not a substitute for enough working RAM.

## 3. Measure the real operating envelope

Record a cold/load run and a warm/reuse run separately. An identical graph may be fully cached: label cache-only execution separately, not as a fast sampling benchmark. Use a fresh recorded seed for a genuine warm sampler run while retaining reusable conditioning; use matched seed pairs when comparing configurations. Use a finite benchmark log, not a background monitor. Capture:

- Exact graph fingerprint, loader, model filename/hash verification state, storage dtype and compute settings.
- Width/height, batch/frame count, seed, steps, reference count and all offload overrides.
- Baseline, sampled peak, end and post-unload whole-device VRAM; GPU activity; Python process RSS; minimum MemAvailable; swap-in/out rate and swap delta.
- Load/encode/sample/decode/save timing where observable; otherwise report end-to-end timing without inventing phase timings.
- Output paths, failure node/type, and any behavior changes between runs. Sampled peaks are lower bounds, not exact allocator peaks.

Begin with **512×768, batch 1, one reference** where the identified model supports it. Use a tiny execution-only sample first; judge identity only after a normal-quality render. Keep the same model, reference, seed and sampler while increasing to **768×1024**, then the required delivery shape. These are test points, not universal supported limits. Honor the model's actual input/patch contract.

Change one variable per comparison: shape, dtype/quantization, encoder placement, reference count, or offload policy. On OOM or sustained paging, stop escalation and record the last successful configuration. Do not repeatedly queue the same failed graph. Test image batches, video frames and multiple references independently; image-fit results do not predict video-fit results.

Keep a provisional desktop/OS VRAM margin rather than targeting 6144 MiB exactly. Derive the eventual reserve from measured desktop usage and the identified model; do not advertise an arbitrary 5 GB weight limit as a hardware law. Agree on acceptable render time after observing quality/latency trade-offs.

## 4. Preserve Andre Athar's identity

1. Obtain 2–5 user-approved canonical images; preserve originals. Record their local paths and file hashes in a project manifest, without biometric embeddings or cloud uploads.
2. Make an anchor sheet: front, three-quarter, profile, neutral expression, stable lighting; document face/hair/facial-hair/body traits and wardrobe separately.
3. Select the **identified model's supported identity/reference path**: reference editing/conditioning or an already available compatible identity adapter/LoRA. Do not assume plain image-to-image denoising is an identity mechanism. Do not install/train a new adapter or model without a separate plan/approval.
4. Produce one conservative anchored edit before testing large pose, camera or lighting changes. Fixed seed is useful for comparisons but is not identity locking.
5. Compare side-by-side against the same anchors: facial proportions, hairline, eyes/nose/jaw, age, facial hair and body silhouette. Distinguish pose/lighting variation from identity drift. Human approval is required; a successful render or plausible face is insufficient.
6. Expand to the minimum useful Kling reference pack, with one image per view/composition rather than a collage as the only asset. Store prompts, seeds, graph/model settings, reference hashes and review status in sidecars.

Existing `Character_Consistency_Tests.json` was ordinary text-to-image at the earlier audit. It must not be treated as proof of identity persistence. Existing Z-Image i2i paths may preserve composition at low denoise, but need explicit identity evaluation. Do not silently substitute a generic newly generated person for Andre.

There is an existing **Klein reference-conditioning candidate** in `studio/worker.py:95–123`, using `ReferenceLatent`, rather than inventing another loader. Its current preset is **Q4_K_M**, not the previously tested Q8 graph, so it needs its own benchmark. The wrapper currently scales each reference to 0.5 MP and accepts up to three; that wrapper cap is not a proven model limit. Start with one anchor, then add references only if they improve identity and memory remains stable. `studio/shot.py` chooses a family-specific i2i template when a reference is supplied, but `studio/templates/flux2-i2i.json` is currently absent. Do not tell the user that a Klein `reference` field works through that route yet: first reuse/adapt the existing worker conditioning at the appropriate Studio boundary and preserve client identity/provenance.

## Implemented handover

OpenJutsu now defaults to the explicit Klein Q4 still-preview profile under **Object swap → From picture**. On the initial Welcome screen, **Set up later** avoids choosing an unrelated VLM. The profile supports one character picture, optional pose video, CPU text encoding, native GPU/offload sampling, 4 steps, single-frame references, and 512/768/1024 maximum long edges. Q8 is a separate higher-memory selection. PNG metadata retains the executed graph; outputs go under `openjutsu_picture/klein-q4` or `klein-q8`.

Validation: 136 Node tests and TypeScript checks passed; production build passed. Headless Chrome checked desktop/mobile layout, reference-only uploads, sequential size changes retaining original source dimensions, persisted pose/reference captions and absence of implicit describe/video actions. Browser generation requests were intercepted fixtures, not GPU renders. Live model inventories confirm both GGUFs, the Qwen encoder and FLUX VAE are advertised. No memory-fit or identity-quality claim is made before real uploads and generation.

## 5. Retry OpenJutsu's still preparation first

The target is `/mnt/data/Projects_SSD/openjutsu`. Its documentation reports tests on **16 GB VRAM and 64 GB RAM**, with H3 weights streamed from RAM—not on this 6 GB/32 GB laptop. Native partial offload is not enough evidence to promise the full video pipeline fits.

The relevant functional stage is **Object swap → From picture → Generate preview image**, backed by `/mnt/data/Projects_SSD/openjutsu/workflows/picture/from_picture_prepare_flux3.api.json`. It saves a first-frame still at node `21` and explicitly does **not** start H3. Preview FLUX and H3 rendering are separate jobs. The original FLUX3 endpoint path still hardcodes a 768p short-edge canvas: multipart `width`/`height` describe source geometry, not a requested smaller output. The newly implemented Klein profile explicitly replaces that canvas and model path; it is not merely a renamed FLUX3 model or smaller source metadata. Do not press Render video during this still trial.

The current still-stage defaults reference **FLUX 3**, a Qwen3-VL 4B encoder, the FLUX VAE and a **Qwen3.5 9B prompt upsampler**. The earlier successful FLUX.2 Klein Q8 run does not prove these different components fit. Keep relight **off** initially: the relight path raises preparation to **3 MP** and changes how references reach the generator. The ordinary prepare canvas defaults to 768×1376; test a smaller supported canvas before retaining that default.

Inspect `/mnt/data/Projects_SSD/openjutsu/lib/picture.ts` and the selected API graph before pruning or overriding anything. Other agents' client-side edits are not ours to replace. No OpenJutsu listeners were found on the documented ports 3000/8189 and `node_modules` was absent at inspection. Do not install dependencies/start duplicate Next.js/proxy services just to benchmark a graph: first use the running local ComfyUI backend where feasible and preserve client identity/provenance. The From picture stage talks directly to ComfyUI and does not require the proxy.

### Concrete blockers and route decision

All still-prepare node classes are registered, including VideoHelperSuite, `TextGenerate` and `ReferenceMultiLatent`. Its VAE is installed. These native-default files are **missing/unlisted**:

- `diffusion_models/flux3_image_klein_sd_int8_convrot.safetensors`
- `text_encoders/qwen3vl_4b_fp8_scaled.safetensors`
- `text_encoders/qwen3.5_9b_flux3_prompt_upsampler_int8_convrot.safetensors`

No LoRA, SAM, Metric3D, SolarRenderer or face-refinement dependency is needed for still preparation. The exported default source video and character image are absent too; neither should be assumed to be Andre.

Choose between:

- **Native OpenJutsu/FLUX3:** pin exact missing artifacts, show size/license/storage plans, obtain approval, then test the still-only graph with reduced canvas. No download is implicitly authorized by this plan.
- **Recommended first capacity/identity experiment:** use already installed FLUX.2 Klein Q4_K_M or Q8 through its correct GGUF loader and supported reference conditioning, with the existing Qwen encoder on CPU and FLUX VAE. This is a **separate alternative pipeline**, not a drop-in FLUX3 replacement or a verified OpenJutsu success. Compare Q4 and Q8 independently; preserve the original graphs and do not put a `.gguf` filename into the existing `UNETLoader`.

For a non-relight experimental copy, manually authored editing instructions can bypass the 9B upsampler: set node `13.inputs.text` to `["6", 0]` and remove nodes `7,8,9,23,24,25`. Both reference images must still reach conditioning in the original order: character at `images.image0`, pose at `images.image1`. This removes the VLM dependency only; it does **not** make the missing FLUX3 diffusion model/4B encoder installed or prove Klein compatibility. The original FLUX3 path has no standalone bypass setting for this step; the new explicit Klein profile skips the VLM as part of its separate graph transformation.

`ReferenceMultiLatent` derives its initial latent/canvas from the first reference. Reduce the reference preprocessing/canvas together; changing only an empty-latent node will not control the output. Begin without relight, normal-map/video stages, extra identity references or post-upscale.

The prepare graph contains no explicit cleanup node between VLM, encoding, sampling and decode; rely on audited native memory ownership rather than claiming a cleanup feature exists. Motion/Solar variants have `VRAM_Debug(unload_all_models=true)` after FLUX decode and before Metric3D, but no second explicit boundary before H3. That global cleanup neither proves a RAM ceiling nor belongs in the still-only trial by default.

Execution sequence:

1. Snapshot it and map every component to local GPU, CPU/offload, or external API ownership.
2. Check exact model presence, compatible formats, node types, reference inputs and native offload support. Show a pinned size/license/destination plan before any missing-model download.
3. Save an optimized copy, preserving the original. Prefer supported workflow settings over modifying core inference code.
4. Run one local, short, single-output test with the canonical reference. For Studio stills, use `studio/shot.py` and its `client_id`/provenance path where the model is supported; use a model-specific adapter only if that path cannot represent the graph. Preserve client identity and metadata in any dedicated test runner.
5. Inspect the output and record memory/timing evidence. If the workflow is a paid API path, obtain explicit per-test permission; local GPU policy does not optimize remote inference.
6. Repeat the chosen configuration and test the next shape only after stability and identity pass. Do not declare the full workflow healthy from a partial branch or unrelated attached UI metadata.

## Deliverables and acceptance

- A capacity table per **exact model + graph + shape**, with cold/warm evidence and conservative last-known-good settings—not a list of checkpoint-size guesses.
- Original and optimized workflow copies; a verified-download record for any approved new weights.
- A small user-approved Andre reference pack with reusable provenance for manual Kling import.
- Refreshed `user/workflow-health.json`, keeping unsupported UI mappings and untested settings unverified.

Success means: repeated local runs without OOM or sustained paging at the chosen shape, measured resource/timing costs, correct full outputs, and human-confirmed Andre identity. Larger resolutions, longer clips, more references, training and remote generation remain separate tests.

### Local implementation evidence

- Native residency/reclamation: `comfy/model_management.py:893–1039`.
- Partial model load/unload: `comfy/model_patcher.py:1005–1117` and `comfy/model_patcher.py:1194–1300`; dynamic reclamation: `comfy/model_patcher.py:2131–2160`.
- Dynamic initialization evidence: `main.py:282–323`; startup switches: `comfy/cli_args.py:172–185`.
- CPU CLIP placement: `nodes.py:1017–1042`.
- Queued unload/free handling: `server.py:1294–1303`, `main.py:416–433`.
- Studio reference routing: `studio/shot.py:40–54`; existing Klein reference conditioning: `studio/worker.py:95–123`.

### Inputs still needed

- Upload an approved Andre identity image through **Object swap → From picture**. The user explicitly chose frontend uploads rather than supplying file paths in chat.
- A source pose video is optional in the implemented Klein profile; without one the user supplies a direct edit prompt for image 1.
- Route decision is settled: existing FLUX.2 Klein first; do not download FLUX3 models to satisfy the original graph.
- Approval for any newly required model download, dependency installation or server restart, after showing the concrete plan. The project location itself is now resolved.
