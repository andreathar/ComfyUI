# Local ComfyUI operations

This folder holds Codex configuration and workstation-specific operations. The
root `AGENTS.md` remains the authority for upstream engineering rules. Start
with [SETUP_PLAN.md](SETUP_PLAN.md) for decisions, outstanding work, and evidence.

## Argon Studio reference frames

The local Argon checkout now includes a manual reference-frame handoff:
**OpenReel editor → Vault → Shot reference frames**. Select a server-side
Argon shot, import a saved PNG, review it, and explicitly approve its start
frame. The image is catalogued without re-encoding, preserving ComfyUI's
embedded workflow/prompt metadata when present. Import does not submit video
generation or approve production frames automatically.

Read `/mnt/data/Projects_SSD/argon-studio/docs/COMFYUI_REFERENCE_FRAMES.md`
for usage and limitations, and that repository's `AGENTS.md` before working
there. Argon owns shot association and approval. This is a separate checkout
from `codex_argon_studio`. Keep local ComfyUI model loading separate from
Argon export GPU work. No automatic ComfyUI job submission or GPU scheduler
was added by this handoff.

## Python and tools

- Run commands from the repository root with `.venv/bin/python` explicitly.
- The venv uses the already-installed uv-managed Python 3.13 interpreter; it
  does not use system packages. There is no `.python-version` override: pyenv
  owns bare Python shims and does not have this uv-managed version installed.
- Use `uv pip install --python .venv/bin/python --torch-backend cu130 ...` for
  dependency changes. Review the resolution before applying upgrades.
- `requirements.txt` is upstream's dependency list. `requirements.lock.txt` in
  this folder records the verified local environment; it is a version snapshot,
  not a cross-platform or hash-verified supply-chain lock.
- Do not run `uv sync`: this checkout declares its runtime in `requirements.txt`,
  not a complete dependency list in `pyproject.toml`.
- Keep the project venv out of pathman's host PATH. Activation is optional and
  temporary; explicit interpreter paths work in terminals, IDEs, and agents.
- No Node installation/build is required to run the packaged ComfyUI frontend.

## Local references

These locations were verified on this workstation on 2026-10-24. Check that
they still exist before use; do not copy their contents into shared docs.

| Purpose | Location |
| --- | --- |
| This checkout | `/mnt/data/Projects_SSD/ComfyUI` |
| Host PATH source, owned by pathman | `/home/athar/.config/envman/PATH.env` |
| PATH procedure | `/home/athar/.agents/skills/path-guard/SKILL.md` |
| Static PATH audit | `/home/athar/.agents/skills/path-guard/audit.py` |
| Service/port registry | `/mnt/data/Projects_SSD/docs/ports-and-services.json` |
| Port check | `/home/athar/.agents/skills/port-guard/scan.py` |
| Local OS diagnostics project | `/mnt/data/Projects_SSD/linux-oracle` |
| Shared editor/Python guidance | `/mnt/data/Projects_SSD/docs/editor-health-preflight-python-pilot.json` |

Read each reference's own instructions before executing its tools. A reference
does not authorize changes to another project or to host services. Do not
source shell startup files or run pathman synchronization during diagnostics.

## Launch and stop

Check available RAM/VRAM and the proposed port before launching:

```bash
free -h
nvidia-smi --query-gpu=name,memory.total,memory.used,memory.free --format=csv
/usr/bin/python3 /home/athar/.agents/skills/port-guard/scan.py check 8188 --json
bash .codex/launch.sh
```

The launcher runs a foreground server at `http://127.0.0.1:8188`; stop a
terminal-launched instance with Ctrl+C. No boot service is installed. Arguments after
the script are passed to ComfyUI, for example `bash .codex/launch.sh --cache-none`
when memory pressure makes recomputation preferable to caching.

The setup session left a background instance running. Its PID, cwd and log are
recorded in `.codex/artifacts/server-process.json`; the log is
`.codex/artifacts/comfyui-current.log`. Before stopping that instance, verify
its live PID/cwd/command against the record and confirm the queue is empty,
then send SIGINT only to that process. Do not launch a duplicate on 8188.

The launch script reserves 1 GiB VRAM for the desktop, uses lightweight
previews, and retains native RAM-pressure caching and dynamic
VRAM/attention/precision behavior. These are initial settings to benchmark,
not a claim of the fastest configuration. Do not force FP8 compute on the
Ampere GPU or enable experimental `--fast` options without a measured reason.
For more RAM headroom, compare `bash .codex/launch.sh --cache-ram 6 6` against
the default; use `--cache-none` separately if recomputation is acceptable.

The launcher registers native local and partner API nodes so imported API
templates do not falsely appear to need an unknown node pack. Registration
does not execute an API workflow; partner calls require account access and
credits. Run only the local SD 1.5 baseline when testing local generation.
Pass `--disable-partner-nodes` explicitly to hide API nodes if desired, but
expect their templates to report missing nodes. Do not add `--offline` when
browsing the registry: its CSP blocks the external search provider. For fully
offline generation with existing weights, pass `--offline` explicitly and
accept that the Manager catalogue will be unavailable.
Hugging Face offline variables block implicit Hub fetches. They are not a
network sandbox for Python or arbitrary custom nodes. Missing model/tokenizer
artifacts must be obtained explicitly, never silently downloaded during a run.
Node Manager is installed and enabled by this launcher; the agent feature is
not enabled. Manager uses uv for Python dependencies in this project's venv.
Its backend and catalogue can contact node registries and package sources.
Model downloads still require an explicit choice.

## Install Python packages and missing nodes

Pathman manages host executable paths. Use uv to install Python dependencies
into this project's venv; no pathman change or global Python install is needed.
The project-compatible Manager version comes from `manager_requirements.txt`:

```bash
uv pip install --python .venv/bin/python --torch-backend cu130 --constraint .codex/requirements.lock.txt --link-mode copy -r manager_requirements.txt torchaudio
uv pip check --python .venv/bin/python
```

Manager's integrity check expects torch, torchvision and torchaudio. The CUDA
torchaudio wheel was import/resample tested against this environment before
installation; it does not replace the working PyTorch packages.

Manager's `user/__manager/config.ini` sets `use_uv = true`. The launcher exports
`UV_PYTHON` with the explicit project interpreter, `UV_TORCH_BACKEND=cu130`,
and `UV_LINK_MODE=copy` for its dependency subprocesses. Manager also adds the
venv bin directory to its own process PATH; this is temporary project scope,
not a write to pathman's host configuration.

After package installation, stop the existing ComfyUI process with Ctrl+C in
its terminal and run `bash .codex/launch.sh` again. Refresh the browser, then
use Node Manager's missing-node installation for the workflow's named packs.
Manager installation alone does not install an unidentified workflow's packs.
After custom-node changes, run the dependency check again and refresh the
version snapshot only after the workflow passes.

If Missing Nodes is empty, compare the workflow's issue with its actual node
type before installing anything:

| Report | Check and remedy |
| --- | --- |
| Missing model filename | Obtain the selected weights in the native model category; installing a node pack will not supply them. |
| Unknown pack for a native node such as `ClaudeNode` | Check `/object_info` and launch flags; `--disable-partner-nodes` hides built-in API nodes. Restart without that flag to use their templates. |
| Missing third-party node type | Identify its owning registry pack, then install only that pack with Manager and inspect any import failure after restart. |

An unknown pack is not an install target. Do not install unrelated packs with
similar names to compensate for a disabled or unregistered native node.

### Manager visibility and the Matrix warning

In packaged frontend 1.57.1, the top toolbar's **Extensions** blocks icon opens
the new Custom Nodes Manager. It need not have a text button named Manager.
If the toolbar is hidden, check **View → Focus Mode**. After a server restart,
refresh the browser so frontend availability is checked against the new process.

`GET /v2/manager/version` should return `V4.2.2` for this installed version;
`GET /features` should advertise `extension.manager.supports_v4` and
`supports_csrf_post`. These checks prove backend availability, not visibility
in a particular browser tab.

The missing `matrix-nio` warning only disables optional sharing to Matrix.
It does not disable Manager or custom-node installation. Do not add a sharing
dependency to resolve a missing Manager control.

### Claude credentials and extension language

Two installed nodes share the display name Anthropic Claude:

- Native `ClaudeNode` uses the Comfy account/credits path. An Anthropic key
  cannot be entered in that node's `system_prompt` or prompt fields.
- Third-party `AnthropicClaudeNode`, under `LLM/Anthropic`, accepts a personal
  key through its **Anthropic API key → Save & validate** controls. The
  installed extension's instructions are in
  `custom_nodes/anthropic-claude/docs/getting-started.md`. Its credential file
  is private local state under that extension; do not read it into agent
  output or include it in shared archives. No key belongs in workflow JSON.

`Claude - personal Anthropic API key.json` in the Workflows sidebar copies the
extension's bundled basic example without executing it. The browser was left
on its empty key field; authentication and generation remain user actions.

The Chinese prompt controls belong to Prompt Assistant. Its supported setting
is **Settings → Prompt Assistant → System → Interface Language**; English was
selected and verified after its automatic page reload. Portuguese is also
available. This is an interface preference, not translation of prompt content
and not a change to the configured inference/translation providers.

## Verified image-generation baseline

Open **Workflows → Balanced SD15 - RTX 3060**. If the sidebar was already open
when the file was created, refresh its list. This native seven-node workflow
uses `v1-5-pruned-emaonly-fp16.safetensors`, 512×512, batch 1, 20 steps,
CFG 7, DPM++ 2M/Karras and fixed seed 44. It bundles CLIP and VAE through the
standard checkpoint loader and needs no custom node packs.

The user approved this 2,132,696,762-byte checkpoint. Its pinned source revision,
SHA-256 and license are in `.codex/artifacts/model-manifest.json`. The original
Z-Image workflow is saved separately as **Z-Image Turbo - original pending
models**; its missing model files were not downloaded. Its selected
`pixel_space` VAE should also be replaced with the model's documented VAE before
attempting that workflow.

Four native GPU runs completed: cold **14.19 s**, warm **8.13 / 7.65 / 6.59 s**.
These timings apply only to this workflow and the observed busy machine.
Seeds 42–45 forced fresh denoising; model/CLIP caches were reused on warm runs.
All PNGs decoded; prompt adherence varied, so seed 44 is the saved starting
point. Outputs are in `output/Balanced_SD15/`, and the full measurements are in
`.codex/artifacts/generation-benchmark.json`.

The final browser check also passed: Manager's All Extensions catalogue
rendered, this workflow opened without setup issues, and clicking Run produced
`baseline_00005_.png` in the visible Save Image preview. Screenshots and the
browser-run record are in `.codex/artifacts/`.

GPU usage is shared: during this setup, an LM Studio llama-server held about
3898 MiB independently of ComfyUI. Do not stop other projects automatically.
For larger images, unload that model through LM Studio first and recheck RAM
and VRAM. After the benchmark, native ComfyUI unloading left its own allocation
at about 204 MiB; machine-wide usage remained high because of the other model.

SD 1.5 is a fast compatibility baseline, not a claim of modern-model image
quality. SDXL or an appropriately sized Z-Image variant needs its own explicit
artifact choice, resource budget and generation test.

## Models, workflows, and evidence

### Download models to the larger drive

Model storage is already on the larger drive: this checkout and its `models/`
folder live on `/mnt/data` (880 GiB filesystem, about 534 GiB free when checked).
The system/home filesystem had about 142 GiB free. No model relocation or
additional ComfyUI search-path configuration is needed for this layout.

The standalone downloader uses `.codex/models.json` to map each selected model
set to exact native filenames and categories. From the project root:

```bash
# Show the available model sets and sizes; no downloads.
.venv/bin/python .codex/model_download.py list

# Preview destinations and missing files; no downloads.
.venv/bin/python .codex/model_download.py plan sd15

# Download missing SD 1.5 weights, or verify and reuse the existing file.
.venv/bin/python .codex/model_download.py download sd15

# Check the installed model's full size and SHA-256 without network access.
.venv/bin/python .codex/model_download.py verify sd15
```

For the deferred Z-Image set, `plan z-image-turbo` shows all three destinations.
When that model set is explicitly selected for use, the corresponding
`download z-image-turbo` command downloads its 19.27 GiB (20.69 GB) set:

| Artifact | Native destination under `models/` |
| --- | --- |
| SD 1.5 FP16 | `checkpoints/v1-5-pruned-emaonly-fp16.safetensors` |
| Z-Image Turbo BF16 | `diffusion_models/z_image_turbo_bf16.safetensors` |
| Qwen text encoder | `text_encoders/qwen_3_4b.safetensors` |
| Z-Image VAE | `vae/ae.safetensors` |

Only the explicitly named profile is processed. Startup and workflow loading
do not trigger this helper or authorize further model downloads. The user
selected **prepare automation; keep SD 1.5 for now**, so Z-Image remains absent.

The helper checks that `/mnt/data` is mounted and the destination is on that
drive. It keeps 5 GiB disk headroom, resumes interrupted transfers in `.part`
files, verifies the complete size and SHA-256, and publishes complete files
without overwriting existing models. A per-file lock prevents two instances
from downloading the same target. Headroom is a preflight check, not a disk
reservation against other programs. No full-file Hugging Face cache copy is
created on the system drive.

An existing file with the wrong hash is preserved and reported. A failed or
interrupted download remains a `.part` file; rerun the same command to resume.
If a complete partial has the wrong hash, inspect/quarantine that partial
before retrying. ComfyUI ignores the `.part` suffix. Refresh model lists in
the UI after a completed download; the native filenames preserve workflows.

Add future chosen artifacts to `models.json` with their pinned public HTTPS
URL, exact native folder/filename, byte size, SHA-256 and license. This is an
explicitly invoked local script outside core ComfyUI; it installs no packages
and makes no pathman changes.

Downloader tests (temporary files and simulated HTTP, no model downloads):

```bash
.venv/bin/python -m unittest discover -s .codex -p test_model_download.py -v
```

Use existing native folders: `models/checkpoints`, `models/vae`, `models/loras`,
`models/controlnet`, `models/upscale_models`, and `models/text_encoders` as needed.
Keep models, inputs, outputs, user state, and the venv out of Git; upstream
already ignores these. `extra_model_paths.yaml` is needed only after an actual
external model store is selected. Model storage is unrelated to executable PATH.

Keep workflow JSON in `user/default/workflows/` and generation metadata in PNGs.
Before performance comparisons record the checkpoint hash, workflow, seed,
resolution, batch size, steps, sampler/scheduler, package snapshot, available
RAM/VRAM, cold/warm time, and peak resource use. Model downloads require the
specific artifact and license/use choice to be established first.

Codex inherits the existing user MCPs and model selection. Project instructions
load through `.codex/config.toml` in a trusted project; reopen the project or
start a new Codex session to use them in subsequent work. Markdown in this folder
is referenced context, not an automatically discovered skill or custom agent.
Do not treat filesystem presence as proof that a connector is healthy.

## Verification

```bash
uv pip check --python .venv/bin/python
.venv/bin/python main.py --help
bash -n .codex/launch.sh
codex app-server --strict-config --print-startup-config
```

Setup evidence is in ignored `.codex/artifacts/`: `cuda-check.json`,
`codex-config.json`, `server-smoke.json`, and `server-smoke.log`. The port
registry backup is `ports-and-services.before.json`; restore only the matching
entry if other projects have changed the registry since that snapshot.

Check `/system_stats` for actual CUDA/PyTorch information after startup and
`/object_info/CheckpointLoaderSimple` for checkpoint discovery. An HTTP 200
alone does not prove a generation; require a completed queued workflow and a
visually inspected saved image before claiming image-generation readiness.
