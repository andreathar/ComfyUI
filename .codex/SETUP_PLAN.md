# ComfyUI workstation setup plan

**Goal:** A reproducible local image-generation environment tuned for balanced
quality and speed, with Codex using the correct Python and Linux references.

**Scope:** The user's 2026-10-24 request and balanced quality/speed preference.
Configuration and dependency setup are authorized. Exact model acquisition,
quality benchmarking, and any host/service changes have separate decision gates.

**Architecture:** Keep upstream inference and server code unchanged. Use a local
uv venv, native ComfyUI model directories and execution behavior, and a small
Codex configuration with an explicit foreground launch command. Host PATH stays
owned by pathman; user-level Codex/MCP settings remain inherited.

## Verified starting point — 2026-10-24

| Item | Evidence and implication |
| --- | --- |
| Checkout | Clean `master` at `7cebca52`, ComfyUI 0.42.0; no venv or local config files; `.codex/skills/` was empty. |
| OS | Pop!_OS 24.04 LTS, x86_64. |
| CPU | Intel i7-11800H, 8 cores / 16 threads. |
| RAM | 31 GiB total; about 5.9 GiB available, 18/19 GiB swap used. Snapshot only: recheck before generation. |
| GPU | RTX 3060 Laptop, 6144 MiB VRAM, compute capability 8.6; 838 MiB used and 4969 MiB free at initial probe. |
| Driver | NVIDIA 595.104.02; CUDA 13.x minimum is driver 580. Actual tensor execution still needs validation. |
| Storage | Checkout is on Kingston SATA SSD (`/dev/sda1`), about 546 GiB free; home is on Samsung NVMe with about 142 GiB free. Do not force NVMe-oriented `--fast-disk` for this checkout. |
| Python/tools | Existing uv 0.13.1, Python 3.13.14 and 3.12.15; Codex CLI 0.164.0. No new host runtime needed. |
| PATH | All 15 managed entries ordered consistently in process/systemd/generated mirror; two stale Codex temporary PATH directories flagged separately. Shell and GUI startup contexts were not dynamically tested. |
| Models | No image-generation weights in this checkout. Bounded checks of common external stores found no selected shared image-model store. |
| Runtime | No listener on 8188 at preflight; no established running ComfyUI instance. |

## Decisions and alternatives

- **Selected:** native venv with stable CUDA 13.0 PyTorch; matches this checkout's
  NVIDIA recommendation and uses the already installed driver/interpreter.
- **Not selected:** Conda/Docker/another ComfyUI distribution; these add parallel
  environment/storage ownership without solving a demonstrated requirement.
- **Initially deferred:** third-party acceleration, custom nodes, Manager,
  automatic updates, and quantized large models. Manager was subsequently
  requested and installed; see the follow-up below.
- **Initial tuning:** native dynamic VRAM, native precision/attention and
  RAM-pressure caching, batch 1, 1 GiB desktop VRAM reserve, latent RGB previews.
  Compare `--cache-ram 6 6` or `--cache-none` if runtime memory pressure warrants it.
  Do not force `--lowvram`: its help says it has no effect with dynamic VRAM.

## Task 1 — Isolated runtime and Codex operations

Files: `.codex/config.toml`, `.codex/README.md`,
`.codex/launch.sh`, `.codex/requirements.lock.txt`, and `.codex/.gitignore`.
Generated artifacts go in ignored `.codex/artifacts/`.

- [x] Inventory repository state, installed runtimes, hardware, model folders,
  and static PATH ownership; fetch current ComfyUI/Codex documentation.
- [x] Select Python 3.13 and stable CUDA 13.0 wheels without host PATH changes.
  Use the venv's interpreter explicitly; do not add a `.python-version` pin
  because the host's pyenv installation contains only 3.11.9 and uv owns 3.13.
- [x] Create venv using existing interpreter:
  `uv venv --python 3.13 --no-python-downloads --seed .venv`.
- [x] Resolve then install upstream runtime into that venv:
  `uv pip install --python .venv/bin/python --torch-backend cu130 --link-mode copy --strict -r requirements.txt`.
  Limit download/install concurrency on this busy workstation. This image
  initial image baseline did not add optional audio, Manager, or agent
  dependencies. The requested Manager follow-up subsequently adds Manager and
  torchaudio for its integrity check; the agent feature remains disabled.
- [x] Verify dependency consistency and a real CUDA tensor operation; confirm
  PyTorch sees the laptop GPU and supports its architecture.
- [x] Freeze installed versions into `.codex/requirements.lock.txt`, with the
  exact checkout/runtime versions and source documented in this plan.
- [x] Verify project TOML through native Codex parsing and effective config
  loading without making a model/inference call or starting duplicate MCPs.
- [x] Verify launcher syntax, flags, and isolated ComfyUI startup.

For a later recreation, create `.venv` as above, then run:

```bash
uv pip install --python .venv/bin/python --torch-backend cu130 --link-mode copy --strict -r .codex/requirements.lock.txt
uv pip check --python .venv/bin/python
```

Keep the old venv until a replacement passes; do not run blind upgrades or
`uv pip sync` against a user's subsequently extended environment.

## Task 2 — Local server and model choice

- [x] Register the operator-started loopback endpoint in the canonical registry
  after checking 8188; preserve unrelated registrations.
- [x] Run a bounded localhost smoke: JSON `/system_stats`, native loader
  registration, packaged frontend, empty checkpoint list; stop the exact
  test process afterward. Record any import warnings or missing dependencies.
- [x] Select a specific checkpoint artifact, source, license, and disk budget
  with the user before downloading. Prefer `.safetensors` in native folders.
- [x] For a fast general baseline, evaluate an SD 1.5 checkpoint at 512×512,
  batch 1, approximately 20–28 steps, using a compatible native workflow.
- [ ] For a quality baseline, evaluate SDXL base at 1024×1024, batch 1,
  approximately 20–30 steps. On 6 GB VRAM this may require offload and more RAM;
  compare 768×768 only if the user accepts the quality/composition tradeoff.
- [x] Keep prompt, checkpoint, VAE, resolution and sampler fixed while comparing
  warm runs. Seeds 42–45 force denoising instead of returning cached samples;
  this is a throughput test, not an image-equivalence comparison. Full VAE
  decode worked; tiling was unnecessary for this baseline.
- [ ] Add only the LoRA/ControlNet/upscaler justified by a chosen workflow;
  record source/hash and model-family compatibility for each artifact.

These are starting points, not measured quality or throughput claims. Large
FLUX/video workflows should follow a successful SD/SDXL baseline and available
RAM evidence, rather than being the default for this 6 GB GPU.

## Task 3 — Acceptance and performance

- [x] Recheck RAM/swap before testing; ask the user to close chosen workloads
  if needed. Do not kill unrelated processes or disable services.
- [x] Complete one cold generation and three warm runs; retain workflow JSON,
  seeds, PNG metadata, timings, peak VRAM/RAM, and error logs.
- [x] Inspect saved images for artifacts, incomplete decode, and prompt fit;
  compare quality before enabling optimizations or lowering precision.
- [ ] Tune one setting at a time: reserve/headroom, cache behavior, resolution,
  VAE tiling. Reject changes that hurt desktop stability or visual quality.
- [x] Mark the SD 1.5 baseline ready after saved images pass decode/visual checks;
  retain separate gates for other model families and the browser catalogue.

## Risks and acceptance boundaries

1. Low available RAM / saturated swap: installation health does not imply a
   large workflow fits; record runtime headroom and avoid forced RAM offload.
2. Driver visibility does not prove CUDA execution: require a tensor operation.
3. New upstream dependency resolution can import successfully yet break a
   workflow: retain the verified snapshot and rerun a known image after updates.
4. Free port is transient: rerun the check immediately before each launch;
   verify actual listener/process ownership afterward.
5. HTTP/UI success with no weights is runtime readiness only: model discovery,
   actual generation, image quality, and measured performance remain distinct.

## Rollback and change boundaries

New local configuration is additive; no core code, upstream dependencies,
shell startup, pathman data, NVIDIA driver, or boot service needs modification.
Stop only the foreground/test process started for this project. To undo local
settings, remove the files added by this setup after reviewing `git status`;
archive the venv instead of deleting any later user additions. Remove only the
matching ComfyUI registry entry if retiring the endpoint. Preserve models,
outputs, workflows, and unrelated project/service state.

## Sources

- [ComfyUI checkout NVIDIA/Python guidance](https://github.com/Comfy-Org/ComfyUI/blob/7cebca52/README.md), fetched through Context7 and checked against this checkout.
- [ComfyUI manual installation](https://docs.comfy.org/installation/manual_install).
- [NVIDIA CUDA compatibility](https://docs.nvidia.com/deploy/cuda-compatibility/minor-version-compatibility.html).
- [Codex project config](https://learn.chatgpt.com/docs/config-file/config-advanced#project-config-files-codexconfigtoml).
- [Codex configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference).
- This checkout's `comfy/cli_args.py`, `folder_paths.py`, `requirements.txt`,
  and `extra_model_paths.yaml.example`; installed uv/Codex CLI help.

## Validation results — 2026-10-24

- Python **3.13.14**, PyTorch **2.14.1+cu130**, torchvision **0.29.1+cu130**,
  CUDA runtime **13.0**; upstream ComfyUI pins installed as specified.
- `uv pip check --python .venv/bin/python`: **104 distributions compatible**
  (103 runtime packages plus seeded pip). Venv disk usage about **6.7 GiB**.
- Real CUDA matrix multiplication and FP16 scaled-dot-product attention:
  **passed**, architecture `sm_86` present. CUDA exposes about **5806 MiB** of
  allocatable GPU memory versus `nvidia-smi`'s 6144 MiB hardware total.
- Native Codex strict parser and `config/read`: **passed**, project layer
  active, exact instructions/environment loaded, user model and seven MCP
  definitions inherited. No inference, thread, subagent, or MCP call was used.
- `bash -n .codex/launch.sh` and native CLI flag parsing: **passed**.
  The launcher also resolves its project when invoked from `/tmp` and accepts
  the documented `--cache-none` override.
- Loopback smoke: **passed** JSON stats with CUDA, native checkpoint loader,
  frontend HTML and its JavaScript asset, and empty execution queue. Startup
  confirmed dynamic VRAM, async offload and PyTorch attention; no failed node
  imports. HIP/NPU unavailable notices describe unused backends; the optional
  `OpenGL_accelerate` module was absent, which did not block this image baseline.
- Smoke used isolated user/output/temp paths, an in-memory database, and
  disabled custom nodes. Its exact PID and process cwd owned the listener;
  only that test process was stopped afterward. No boot service was installed.
- Normal custom-node initialization was also tested with
  `--quick-test-for-ci`, isolated paths and an in-memory database: **exit 0**,
  no import failures, warning or error lines. Evidence: `default-startup.log`.
- Canonical registry reserves **127.0.0.1:8188** under `reserved_not_live` for
  ComfyUI; structural comparison confirms no unrelated entry changed. Backup
  is in `.codex/artifacts/ports-and-services.before.json`.
- Checkpoint count **0**. Actual generation, visual quality, model-specific
  memory use and throughput are **not tested**; Tasks 2–3 retain those gates.

Evidence: `.codex/artifacts/cuda-check.json`, `codex-config.json`,
`server-smoke.json`, and `server-smoke.log`. These generated artifacts are
ignored by Git. The initial smoke server was stopped after verification.

## Node Manager follow-up — 2026-10-24

The user reported the missing-pack installer message and asked how to respect
the workstation's package managers. Installed the checkout-pinned stable
`comfyui-manager==4.2.2` with uv into `.venv`, constraining the existing version
snapshot so no previous package was changed. A generic `pip -U --pre` upgrade
is unnecessary for this checkout.

Manager's integrity check logs a misleading missing-PyTorch error when
torchaudio alone is absent. Tested the official `torchaudio==2.11.0+cu130`
wheel in an isolated target: import, CPU resampling, and a CUDA operation all
passed with the existing `torch==2.14.1+cu130`. Added that wheel without
changing PyTorch/torchvision. Updated the snapshot to include all additions.

`user/__manager/config.ini` sets `use_uv = true`. The launcher now enables
Manager and explicitly directs its uv subprocesses to the project Python and
CUDA 13.0 backend. Manager's private process PATH selection leaves pathman's
host PATH and shell files unchanged. Its backend can use internet registries
even when the frontend is launched with `--offline`.

The operator's existing ComfyUI process on 8188 remains running with its
original arguments and no Manager routes. Activate the prepared change by
stopping it with Ctrl+C in its terminal, rerunning `bash .codex/launch.sh`,
and refreshing the browser. No unidentified node packs or models were installed.

Evidence: `.codex/artifacts/manager-install.json`, `manager-startup.log`,
and the pre-change package snapshot `requirements.before-manager.txt`.
Startup verification uses isolated user state and offline Manager metadata;
the missing workflow's node installation and actual generation remain untested.
The final check passed native Manager startup with uv and no error lines;
all **118 distributions** are compatible, all **104 original versions** are
unchanged, and pathman/shell-file hashes are unchanged. The optional Matrix
sharing dependency is absent; that unrelated sharing feature remains disabled.

## Active generation setup and browser access — 2026-10-24

The user's existing Chrome tab was accessible by claiming it directly. Creating
an automation tab had returned 403; access was obtained without weakening the
server's origin checks. Opened Nodes Manager and saved the unsaved Z-Image
workflow through the UI as `Z-Image Turbo - original pending models.json`, then
made an independent backup in `.codex/artifacts/Z-Image-original-backup.json`.

The actual workflow issue was missing Z-Image model weights. All its nodes
were native and registered. Official Z-Image documentation also requires
`models/vae/ae.safetensors`; the user's `pixel_space` selection is not the
documented VAE. The Z-Image files remain uninstalled and that workflow is not
marked generation-ready.

Found a separate catalogue issue: `--offline` sends a restrictive browser CSP,
which blocks the new Manager's external search provider. Replaced it with
`--disable-partner-nodes` initially; the missing-node follow-up below removes
that flag because it hides native API nodes used by imported templates.
The server still binds only to `127.0.0.1`, retains
origin protections, uses uv in the project venv, and blocks implicit Hugging
Face model fetching. Manager/package catalogue access is allowed. Queue was
empty and the original workflow was saved before gracefully restarting only
the verified ComfyUI process.

The user explicitly approved downloading the approximately 2 GB SD 1.5 FP16
checkpoint and testing generation. Downloaded exactly:

- Repository: `Comfy-Org/stable-diffusion-1.5`.
- Revision: `9cfd069101959ca3828bf9c04a4419870832b74f`.
- File: `v1-5-pruned-emaonly-fp16.safetensors`.
- Bytes: `2132696762`; SHA-256:
  `e9476a13728cd75d8279f6ec8bad753a66a1957ca375a1464dc63b37db6e3916`.
- License: `creativeml-openrail-m`.

Size and hash matched published repository metadata before the partial file
was promoted to the native checkpoints folder. Source and approval are recorded
in `.codex/artifacts/model-manifest.json`.

Created `user/default/workflows/Balanced SD15 - RTX 3060.json`: seven native
nodes, standard checkpoint/CLIP/VAE loading, 512×512, batch 1, 20 steps,
DPM++ 2M/Karras, CFG 7. No custom node pack was needed. Seed 44 is the saved
starting point after inspecting the four generated images.

| Run | Seed | Wall time | Result |
| --- | --- | --- | --- |
| Cold | 42 | 14.19 s | Complete PNG; cabin geometry imperfect. |
| Warm | 43 | 8.13 s | Complete landscape PNG; cabin omitted. |
| Warm | 44 | 7.65 s | Complete cabin/lake PNG; selected starting seed. |
| Warm | 45 | 6.59 s | Complete landscape PNG; cabin omitted. |

Warm mean: **7.46 s**. Model, sampler, shape and prompts were unchanged;
different seeds deliberately forced denoising rather than cached output.
All PNGs were decoded and checked at 512×512 RGB, with matching seed, prompt
and seven-node UI-workflow metadata. These are correctness and throughput
results, not a claim of optimal quality or modern-model fidelity.

Peak **machine-wide** GPU usage was 5639 MiB, and peak ComfyUI process RSS was
4407.9 MiB. An independently running LM Studio llama-server held **3898 MiB**
of VRAM. It was not stopped. Native ComfyUI unload/free operations were issued
after the tests; `nvidia-smi` then attributed about **204 MiB** to ComfyUI while
the other model still held its allocation. RAM and swap pressure remain host
constraints, so SDXL/Z-Image optimization is a later measured choice.

The live loopback listener and exact PID/cwd were verified. The shared registry
now lists this on-demand instance under `services`; structural comparison
confirmed no unrelated record changed. Host pathman and shell-file hashes
remain unchanged. All **118 distributions** still pass `uv pip check`.

**Browser verification completed:** Initial inspection stalled at
`Emulation.setFocusEmulationEnabled`. Recovered the existing tab through the
documented browser API: obtain the known tab with `Browser.tabs.get`, call
`Tab.reload`, then inspect through `Tab.playwright.domSnapshot`. This avoided
the failing focus step without changing browser or server security settings.
Opened **Balanced SD15 - RTX 3060** through the Workflows sidebar: no setup
issues appeared. Opened **Extensions → All Extensions** and verified that node
cards and Install buttons rendered. No extra packs were installed.

Clicked **Run** in the browser. A fifth generation completed successfully and
appeared in Save Image's preview, producing `baseline_00005_.png`. Server
history recorded success with fresh execution (no cached nodes), about
12.65 seconds of execution after the earlier model unload. The selected
workflow remains open; the original Z-Image tab remains separate.

Visual evidence: `.codex/artifacts/manager-catalogue.png` and
`workflow-browser-verified.png`. Browser generation evidence:
`.codex/artifacts/browser-generation.json`. Native model/cache unloading was
requested after the check to release test allocations; queue remains empty.

Current runtime record/log: `.codex/artifacts/server-process.json` and
`comfyui-current.log`. Generation proof: `generation-benchmark.json`,
`history-42.json` through `history-45.json`, and `setup-validation.json`.
Images: `output/Balanced_SD15/baseline_00001_.png` through `baseline_00004_.png`.
Source model card: https://huggingface.co/Comfy-Org/stable-diffusion-1.5
Z-Image reference: https://docs.comfy.org/tutorials/image/z-image/z-image-turbo

## Model download automation plan — 2026-10-24

The user requested automatic placement on the larger drive, then selected
**Prepare automation; keep SD 1.5 for now**. The existing native model root is
already on `/mnt/data` (`/dev/sda1`, 880 GiB filesystem, about 534 GiB free at
inspection); the system/home filesystem has about 142 GiB free. Keep the native
root rather than relocating weights within the same drive. Pathman owns
executables, not model storage, and requires no changes.

Implement a small standalone downloader under `.codex/`, outside ComfyUI core:

- [x] Catalogue `.codex/models.json` pins exact public artifact URLs, sizes,
  SHA-256 values, native categories and profiles (`sd15`, `z-image-turbo`).
- [x] `.codex/model_download.py` provides `list`, `plan`, `download`, and
  `verify`. Downloads occur only through an explicit selected-profile command.
- [x] Validate storage mount and destination containment; check disk headroom;
  serialize each target; resume `.part` transfers with validated byte ranges;
  publish only complete, hash-verified files without overwriting existing ones.
- [x] `.codex/test_model_download.py` exercises interruption/resume, ignored or
  wrong ranges, bad hashes, existing-file preservation, insufficient space,
  symlink/path escape, and no-network idempotence using temporary files and
  mocked HTTP responses. No test downloads model weights.
- [x] Run the downloader against the existing SD 1.5 model and prove it skips
  network traffic, then verify native loader discovery and update the runbook.

No model transfer, migration, new dependency, service restart or background
download is needed for this change. Z-Image's three-file 20,690,152,836-byte
profile is prepared but must remain undownloaded under the user's choice.

Verification: all **16 tests passed** after the expected failing run before
implementation. Actual SD 1.5 `download` and `verify` commands passed with
network access mocked to fail, preserving the file size and mtime. Every
catalogue destination was checked against native `folder_paths`; the live
checkpoint loader still finds the original filename. Independent code review
approved the change with no material findings, and separately exercised
target-lock contention, non-overwrite publication and unknown-profile exits.
Disk headroom is a preflight, not a reservation against unrelated writers.

Evidence: `.codex/artifacts/model-download-validation.json` and
`model-download-code-review.md`. No Z-Image weight was downloaded, no working
model was moved, and no service or host PATH configuration was changed.

## Missing-node diagnosis and repair — 2026-10-24

The imported Claude Opus 5.5 workflow reproduced a real issue: Workflow
Overview reported `ClaudeNode` as an unknown missing pack, while Manager had
no installable pack to offer. The class already exists in
`comfy_api_nodes/nodes_anthropic.py`. `main.py` skips native API registration
when `--disable-partner-nodes` is set, explaining the mismatch.

Removed that flag from the default launcher. Saved the imported workflow as
`user/default/workflows/Claude Opus 5.5 - API template.json`, backed it up,
confirmed the execution queue was empty, gracefully stopped the verified
ComfyUI PID, checked port 8188 was free, and restarted the same launcher.
No package installation, core edit, model download or host PATH change was
needed. Partner workflows were not executed or authenticated.

Before/after live `/object_info` checks showed 1003 versus 1331 registered
types and confirmed `ClaudeNode` changed from absent to present. All three
saved workflows have zero unregistered top-level node types, accounting for
their declared subgraphs. The browser now renders Claude's real controls,
removes the missing-pack issue and shows the expected account requirement.
Manager's All Extensions catalogue still renders packs and Install buttons.
Startup has no failed node imports; the queue remains empty.

Missing models are separate from missing node packs: the saved Z-Image
workflow still needs its deferred model profile and correct VAE selection.
The optional Matrix dependency warning does not explain either case.

Evidence: `.codex/artifacts/claude-node-before.json`, `claude-node-after.json`,
`claude-node-before.png`, `claude-node-repaired.png`, and
`manager-after-node-repair.png`. The process record identifies the replacement
instance. The previous launcher and log are retained under artifacts.


## Studio stabilization update — 2026-11-13

The older installation snapshots above are historical. Current recovery and
validation are documented in `README.md` and `STABILIZATION.md`. The updated
Python snapshot passes dependency checking (498 distributions); all 15 active
custom-node repositories match the integration lock. The existing CUDA stack
was retained, and the original SD15 model completed a fresh live smoke run.
The unused incompatible optional packages were archived before removal.
Browser interaction remains unverified because the browser access host is
unavailable; two upstream medium advisories have no published fixed version.
