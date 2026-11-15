---
name: comfyui-shots
description: Use when generating cinematic reference stills with this ComfyUI fork, writing or editing shot sheets, adding looks or aspect ratios, or finding past renders for an Argon Studio project.
---

# Cinematic shots

The pipeline is `studio/shot.py`; read `studio/README.md` for the sheet
format, folders and naming. Keep everything data-driven: new looks, aspects
and model settings go in `studio/presets.json`, not in code.

## Steps

1. Turn the user's brief into a sheet at `studio/shots/<project>-<scene>.json`.
   Slugs only for `project`, `scene`, `shot`. Write concrete prompt fields
   (subject, action, location, lighting, lens); reuse a named look when one fits.
2. Reference images go under `input/refs/<project>/`. Copy the user's file there;
   never point `reference` outside `input/`. `shot.py` requires an existing
   `studio/templates/<family>-i2i.json` for reference shots. Current reference
   templates are available for SD 1.5 and Z-Image; `flux2-i2i.json` is absent, so
   do not use FLUX.2 references with `shot.py`. For FLUX.2 reference conditioning,
   use the separate `studio/worker.py` `comfy-klein` job workflow (up to three
   refs) and follow its job contract instead.
3. Dry run and show the user the prompts and output names:
   `.venv/bin/python studio/shot.py <sheet> --dry-run`.
4. Before rendering, check the server answers on 127.0.0.1:8188, inspect the
   current queue, and check available memory (`free -m`, `nvidia-smi`). Do not
   duplicate or interrupt queued work; ask before submitting while another job
   is active. If resources are insufficient, explain that and offer a smaller
   supported model such as `"model": "sd15"`. Start the server with
   `.codex/launch.sh` only if it is not running.
5. Render: `.venv/bin/python studio/shot.py <sheet> [--only <shot>]`. Look at
   the saved images before reporting, and give the user their paths.
6. Past renders: read `output/refs/<project>/index.jsonl`, or filter it by tag
   with `jq 'select(.tags | index("night"))'`.

## Rules

- Always submit through `shot.py`, which sets a `client_id`; a bare `/prompt`
  call marks the install as headless for upstream's deploy-to-cloud feature.
- Never strip PNG metadata or delete sidecars; Argon import relies on them.
- Never send renders to an online platform; the user imports into Argon.
- Paid partner nodes (Codex, Higgsfield, Kling) are not part of this pipeline;
  ask before running any.
