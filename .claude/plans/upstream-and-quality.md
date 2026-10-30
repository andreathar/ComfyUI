# Upstream sync and cinematic-reference plan

**Goal:** Keep this checkout current with Comfy-Org/ComfyUI without losing local
setup, and turn it into a dependable generator of high-quality cinematic
reference frames for the online video platforms (via Argon Studio handoff).

## Conflict check — 2026-10-30

| Item | Finding |
| --- | --- |
| Divergence | `master` is 2 commits ahead (`bb8f5673`, `f34fdd96`) and 29 behind `origin/master` (`b5a43215`, ComfyUI 0.43.0). Merge base `7cebca52`. |
| Text conflicts | None. Local commits touch only `.codex/`; upstream touches 46 files outside it. `git merge-tree` reports a clean merge. |
| Dependency drift | Upstream bumps `comfyui-frontend-package` 1.57.1→1.57.6, `comfyui-workflow-templates` 0.11.96→0.11.100, `comfyui-embedded-docs` 0.5.14→0.5.15. The venv and `.codex/requirements.lock.txt` still pin the old versions, so they must be updated together with the merge. |
| Launch flags | `comfy/cli_args.py` unchanged; every flag in `.codex/launch.sh` stays valid. |
| Custom nodes | `comfyui-easy-use` and `comfyui-gguf-loader` use `comfy.conds.CONDRegular`/`CONDList`, unchanged upstream. Only `_apply_freenoise` (private) gained a `model` argument. No custom node imports it. |
| New behavior | `app/deploy_to_cloud.py`: a prompt queued without `client_id` (Argon/API scripts) writes a permanent marker in `user/` and enables a "deploy to cloud" UI flag. Any upload still needs an explicit user action and credentials. `--offline` would suppress it but also disables partner nodes (Claude/Higgsfield), so leave it unset. |
| Unversioned state | The 8 custom node packs (no `.git`), `user/` workflows/settings, and `.codex/artifacts/` are git-ignored and not backed up anywhere. |
| Model gap | `z_image_turbo_bf16` + `qwen_3_4b` exist, but `models/vae/` is empty, so the Z-Image workflow cannot decode until its VAE (`ae.safetensors`) is present. |

## Phase 0 — Safety net (once, before any update)

- [x] Tag the known-good state: `local/known-good-2026-10-30` (at `f34fdd96`).
- [x] Snapshot ignored state: `custom_nodes/` (without `__pycache__`), `user/` and
  `.codex/artifacts/` into `/mnt/data/backups/comfyui/2026-10-30-ignored-state.tar.zst`.
- [x] Freeze the venv: `/mnt/data/backups/comfyui/2026-10-30-freeze.txt`.

## Phase 1 — Branch model

- [x] Private repo `andreathar/ComfyUI` is `origin`; `Comfy-Org/ComfyUI` is `upstream`.
- `master` tracks upstream plus our `.claude/` and `.codex/` commits only. Never edit upstream
  files on `master`.
- `local/*` topic branches for any core patch we really need. Prefer custom
  nodes, `extra_model_paths.yaml`, and launch flags over core edits, because
  those never conflict.
- Put custom node packs we write ourselves under git (own repo each), so they
  can be versioned and restored.

## Phase 2 — Update routine (repeat every 1–2 weeks or for a wanted feature)

Procedure lives in `.claude/skills/comfyui-upstream-sync/SKILL.md`. Summary:

1. `git fetch upstream`; review `git log --oneline master..upstream/master` and
   `git diff master...upstream/master -- requirements.txt comfy/cli_args.py`.
2. Check `git merge-tree --write-tree master upstream/master` for conflicts.
3. Stop the server, run Phase 0, then `git merge upstream/master`. Use merge rather
   than rebase, because rebase rewrites the local history.
4. `uv pip install --python .venv/bin/python --torch-backend cu130 --strict -r requirements.txt`,
   then regenerate `.codex/requirements.lock.txt`.
5. Validate: start with `.codex/launch.sh`, confirm no import errors for
   custom nodes in the log, check `/object_info`, run the baseline workflow,
   and compare it with `.codex/artifacts/generation-benchmark.json`.
6. On failure: `git reset --hard local/known-good-<date>`, reinstall from the freeze
   file, and restore the tarball.

### Sync log

- 2026-10-30: merged upstream v0.43.0 (`ee3c27d3`), lock `e83ab602`. All 9
  custom nodes imported, 1343 nodes in `/object_info`. Baseline seed 44 was
  pixel-identical to `baseline_00003_.png`: 11.0 s cold, 3.2 s warm (seed 45),
  peak GPU 3074 MiB. Open: `diffusers 0.42.0` (easy-use) wants
  `huggingface-hub>=1.32`, but 0.36.2 is installed.

## Phase 3 — Cinematic quality track (RTX 3060 Laptop, 6 GiB VRAM, ~8 GiB free RAM)

1. **Finish Z-Image Turbo:** add its VAE and confirm a 1024² image with no OOM.
   Measure time and peak VRAM against the SD1.5 baseline.
2. **Shot templates:** saved workflows for 16:9 (1344×768) and 2.39:1
   (1536×640). Each uses a fixed seed and a prompt scaffold covering lens, shot
   size, lighting, film stock, and color grade.
3. **Upscale pass:** 2× model upscale plus a low-denoise refine, so stills meet
   the platforms' 1080p/4K reference sizes.
4. **Consistency:** character/style LoRA or reference conditioning, only after
   steps 1–3 are stable.
5. Larger models (Flux-class, GGUF quantized) only after measuring them. With
   6 GiB VRAM and the current RAM pressure, they depend on offloading and are slow.

## Decision gates (need the user's approval)

- Each model download (size, license, target folder).
- Each upstream merge into `master`.
- Any core-file patch (versus a custom node).
