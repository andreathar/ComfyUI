# Local ComfyUI fork — Claude instructions

Root `AGENTS.md` is upstream's engineering authority; follow it for any code change.
This file covers the local fork only. Machine operations live in `.codex/README.md`
and `.codex/SETUP_PLAN.md` (shared with Codex); read them before setup or launch work.

## Purpose

Generate high-quality cinematic reference stills on this workstation for the
online video platforms, handed off through Argon Studio
(`/mnt/data/Projects_SSD/argon-studio/docs/COMFYUI_REFERENCE_FRAMES.md`).
Argon owns shot approval; importing a PNG never authorizes paid video generation.

## Repository layout

- `origin` = private `andreathar/ComfyUI` (ours). `upstream` = `Comfy-Org/ComfyUI`.
- `master` = upstream + local-only files under `.claude/`, `.codex/` and `studio/`. Never edit
  upstream files on `master`; core patches go on `local/<topic>` branches.
- Prefer custom nodes, `extra_model_paths.yaml`, saved workflows, and launch flags
  over core patches — they never conflict with upstream.
- Known-good points are annotated tags `local/known-good-<YYYY-MM-DD>`.
- Ignored state (`custom_nodes/`, `user/`, `.codex/artifacts/`) is backed up to
  `/mnt/data/backups/comfyui/` before every update.

## Workflows

- Upstream updates: use the `comfyui-upstream-sync` skill in `.claude/skills/`.
- Model weights: `comfyui-models` skill (pinned catalogue `.codex/models.json`).
- Reference stills: `comfyui-shots` skill (`studio/`, outputs in `output/refs/<project>/`).
- Code navigation: `code-review-graph` MCP server (`.mcp.json`, uv tool in `~/.local/bin`) and its
  skills `explore-codebase`, `debug-issue`, `refactor-safely`, `review-changes`. The graph in
  `.code-review-graph/` (ignored via `.git/info/exclude`) covers tracked files only, not `custom_nodes/`;
  hooks keep it updated. Rebuild with `code-review-graph build` after an upstream merge.
- Current plan and open items: `.claude/plans/upstream-and-quality.md`.

## Runtime rules

- Python: `.venv/bin/python` explicitly; deps with
  `uv pip install --python .venv/bin/python --torch-backend cu130 ...`. No `uv sync`.
- Launch with `.codex/launch.sh` (127.0.0.1:8188). Check port, RAM and VRAM first;
  the GPU is an RTX 3060 Laptop with 6 GiB, shared with Argon exports.
- Do not add `--offline`: it also disables partner nodes (Claude, Higgsfield).
- Ask before: model downloads, merging upstream into `master`, pushing, core patches,
  or running paid partner/API workflows.

## Learned preferences and workspace facts

Moved here from an uncommitted AGENTS.md edit on 2026-11-08 (AGENTS.md stays upstream's).

- Keep this install's CUDA 13 / cu130 PyTorch stack. Do not add xformers, sageattention,
  flash_attn, a nightly torch, or forced FP8 / `--fast` unless a benchmark shows a need.
- Run and restart ComfyUI with `.codex/launch.sh` on 127.0.0.1:8188, loopback only.
- Keep LoRA Manager on ComfyUI's flat model folders and bare filenames, not its nested
  `{base_model}/{first_tag}` download layout. Its settings live in
  `~/.config/ComfyUI-LoRA-Manager/settings.json`; recipes go to `models/loras/recipes`.
  A second scanner such as `comfyui-advanced-model-manager` can file weights into its own layout again.
- `models/` → `/home/athar/ComfyUI-models` → `/mnt/data/ComfyUI-models` (SATA disk). The git-ignored
  `extra_model_paths.yaml` adds a hot NVMe copy of the H3 shot-swap weights in
  `/home/athar/ComfyUI-models-hot`, searched first; see
  `.codex/artifacts/h3-resource-review-2026-11-08/README.md`.
- `.codex/models.json` and `.codex/model_download.py verify` expect bare filenames; because
  `models/` resolves onto `/mnt/data`, the catalogue's same-filesystem check can stop before hashing.
- Disabled packs live in `custom_nodes/.disabled/` (old GGUF pack, Reactor, old model manager,
  WAS nightly) and `custom_nodes/ComfyUI-DistorchMemoryManager.disabled` (it overrode
  `--reserve-vram` and patched attention). The live GGUF loader is `comfyui-gguf-loader`.
  `aiia` still fails to import EchoMimic (`retinaface`) and Ditto (`pyximport`).
