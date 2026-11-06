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
   never point `reference` outside `input/`.
3. Dry run and show the user the prompts and output names:
   `.venv/bin/python studio/shot.py <sheet> --dry-run`.
4. Before rendering, check the server answers on 127.0.0.1:8188 and memory is
   free (`free -m`, `nvidia-smi`). Z-Image Turbo needs roughly 12 GB of free
   RAM plus swap headroom; if RAM is short, say so and ask the user to close
   apps, or render with `"model": "sd15"`. Start the server with
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
