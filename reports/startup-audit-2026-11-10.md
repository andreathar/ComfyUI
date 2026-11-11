# ComfyUI startup audit — 2026-11-10

## Verdict

**The normal launcher is correctly configured for this computer. There is no demonstrated core initialization failure, but not every installed extension is dependency-clean or workflow-tested.**

ComfyUI was **stopped** at inspection: no server process or listener on 8188. This is not evidence of a crash. The latest recorded startup (November 9, 16:08) used the current launch flags, enabled CUDA/DynamicVRAM, loaded custom nodes without an `IMPORT FAILED`, initialized the asset database, and served the UI after about 14 seconds. Later prompts completed successfully.

No server was started/restarted and no packages or configuration were changed. Existing dirty changes were preserved. This report is the only intentional new repository file.

## What is correct

- `.codex/launch.sh:4-9` changes to the checkout and uses its explicit `.venv/bin/python`, independent of the caller's working directory or activated Python.
- `.codex/launch.sh:11-19` disables user-site imports, supplies Hugging Face offline/privacy settings, and points Manager's uv subprocesses at the project Python/CUDA wheel backend.
- `.codex/launch.sh:21-27` binds to **127.0.0.1:8188**, reserves **1 GiB VRAM**, disables pinned memory, enables Manager and the asset library, and uses lightweight latent previews. All flags parsed successfully in the installed core; shell syntax validation passed.
- Hardware: **RTX 3060 Laptop, 6144 MiB**, NVIDIA driver **595.104.02**, approximately **31 GiB RAM**. PyTorch **2.14.1+cu130** detects CUDA and compute capability **8.6**; a real FP16 CUDA matrix multiplication passed. The driver's reported CUDA 13.2 maximum and PyTorch's CUDA 13.0 runtime are not a mismatch requiring repair.
- Every applicable requirement in `requirements.txt` and `manager_requirements.txt` is installed at a satisfying version. The packaged frontend is **1.57.6**. Torchvision, torchaudio, ONNX Runtime and OpenCV imported successfully.
- Native DynamicVRAM, two-stream asynchronous offload and PyTorch attention initialized in the latest log (`user/comfyui_8188.log:26-33`). No forced low-VRAM, FP8, SageAttention or FlashAttention setting is necessary for basic correctness.
- `extra_model_paths.yaml` resolves the H3 hot copies on the **NVMe** before the bulk SATA model tree. All configured category directories exist. `models`, `input`, `output`, `temp` and `user` resolve; working directories are writable.
- Keep `--disable-pinned-memory`: the earlier local H3 benchmark recorded pilot time **622 → 548 seconds**, swap-out **5.2 GB → 0**, and anonymous RAM peak **18.7 → 4.7 GB** after disabling it. This is workload-specific evidence, not a universal optimization (`.codex/artifacts/h3-resource-review-2026-11-08/README.md:79-108`). Distorch is no longer in the active custom-node directory, so its previously observed VRAM-reservation override is not an active startup finding.

## Findings and recommended priorities

### 1. Startup/restart paths are not equivalent

The enabled user service `/home/athar/.config/systemd/user/comfyui-mcp-launcher.service:5-10` starts the **MCP launcher broker**, not the ComfyUI Python server. Login therefore does not automatically start ComfyUI. This matches the documented foreground-launch design in `.codex/README.md:71-74`.

The broker's ensure-running path uses `npx -y comfyui-mcp@latest connect`, not `.codex/launch.sh` (`/home/athar/.comfyui-mcp/launcher/broker.mjs:999-1018`). That command can resolve/download an npm package; its local listener is not a guarantee of offline execution or Python API readiness.

The inspected cached MCP version, **0.52.206**, relaunches the Python executable and captured arguments directly. It may preserve the old process environment, but **changes to `.codex/launch.sh` are not automatically reapplied on an MCP restart**. A cold start without saved process information can instead request manual startup. Evidence: `/home/athar/.npm/_npx/28eae33d00f3f7f1/node_modules/comfyui-mcp/dist/services/process-control.js:1555-1598,3882-3905`; `dist/services/launcher-env.js:412-437,496-508` in that same package.

**Recommendation:** use `.codex/launch.sh` as the canonical manual start and after changing launch settings. If automatic login startup or unified MCP restarts are desired, configure that explicitly rather than assuming the existing service does it. No service change is needed merely to run ComfyUI manually.

### 2. The extended environment has six dependency compatibility findings

`uv pip check --python .venv/bin/python` failed with:

| Package | Requirement / problem | Installed |
| --- | --- | --- |
| llama-cpp-python | numpy >=1.21.6, <=2.3.2 | numpy 2.5.4 |
| gradio | huggingface-hub >=0.33.5, <2.0 | huggingface-hub 2.4.0 |
| gradio-client | huggingface-hub >=0.19.3, <2.0 | huggingface-hub 2.4.0 |
| qwen-tts | transformers ==4.57.3 | transformers 5.22.2 |
| sentence-transformers | transformers >=4.41.0, <5.0.0 | transformers 5.22.2 |
| decord | wheel built for a different platform | cp36-cp36m wheel under Python 3.13 |

These are **not proven server-start blockers**: llama_cpp, gradio, sentence_transformers and decord all imported successfully. The startup log also records a Qwen3-TTS compatibility shim restoring legacy defaults (`user/comfyui_8188.log:82-83`). Import success does not establish inference compatibility.

**Recommendation:** qualify the affected audio/LLM/video workflows before changing versions. Do not globally downgrade Transformers or NumPy just to silence the checker; that could break currently working packs. Repair or isolate specific incompatible optional packs only after identifying the workflows that need them.

### 3. SoX is absent; optional audio capability is incomplete

`ffmpeg` and `ffprobe` are available in `/usr/bin`. `sox` is not on the inspected PATH, and the latest startup log reports `SoX could not be found!` (`user/comfyui_8188.log:74-80`). The Python `sox` wrapper invokes the external executable (`.venv/lib/python3.13/site-packages/sox/core.py:59-62,124`).

**Recommendation:** install the system executable only if workflows actually invoke SoX-backed effects/processing. Its absence did not prevent startup; it is not evidence that every audio or Qwen path fails. No package was installed during this audit.

### 4. Offline variables are not a network sandbox

The Hugging Face offline exports are working policy inputs, not a block on arbitrary extension requests. Enabled Manager reports `network_mode: public` and fetches registry data (`user/comfyui_8188.log:47,378`). The local operations README explicitly documents this behavior (`.codex/README.md:98-108`). Manager also supports scheduled startup dependency installs/restarts; none were queued during inspection.

**Recommendation:** retain the current behavior if registry browsing is intended. For a strictly offline mode, separately configure Manager and review enabled extensions; core `--offline` alone is not process-wide network isolation. Do not mistake loopback binding or telemetry flags for that guarantee.

## Not missing requirements

- `comfy-agent` is absent, but `--enable-agent` is false; it is optional, not a missing server dependency (`main.py:132,647`).
- FlashAttention and OpenGL_accelerate are optional. Their startup warnings do not mean the CUDA backend or normal attention is broken.
- Asset database dependencies are present and the last scan succeeded. Keep `--enable-assets` for the library feature; database corruption or locking could still block a future startup, as with any persistent database.
- The historical H3 benchmark recorded thermal throttling at **89–90 °C** during sustained generation. That is a cooling/performance concern, not a missing initialization flag; no sustained thermal test was performed today.

## Validation boundary

Performed: process/listener inspection, hardware/RAM/disk checks, shell and native CLI argument validation, installed requirement comparisons, uv dependency check, selected binary imports, a tiny FP16 CUDA operation, path-resolution/write-permission checks, startup-log review, and read-only inspection of startup/restart implementations.

Not performed: a fresh server startup, HTTP readiness checks against a running API, a new image/audio/video workflow, full model integrity checks, dependency changes, downloads or sustained performance testing. Therefore this audit confirms the core launch configuration and records extension risks; it does not certify every installed node or model.
