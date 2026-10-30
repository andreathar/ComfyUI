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
- Current plan and open items: `.claude/plans/upstream-and-quality.md`.

## Runtime rules

- Python: `.venv/bin/python` explicitly; deps with
  `uv pip install --python .venv/bin/python --torch-backend cu130 ...`. No `uv sync`.
- Launch with `.codex/launch.sh` (127.0.0.1:8188). Check port, RAM and VRAM first;
  the GPU is an RTX 3060 Laptop with 6 GiB, shared with Argon exports.
- Do not add `--offline`: it also disables partner nodes (Claude, Higgsfield).
- Ask before: model downloads, merging upstream into `master`, pushing, core patches,
  or running paid partner/API workflows.
