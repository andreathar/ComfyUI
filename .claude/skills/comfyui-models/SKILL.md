---
name: comfyui-models
description: Use when adding, downloading, verifying or locating model weights for this ComfyUI fork (checkpoints, diffusion models, text encoders, VAEs, LoRAs, upscalers), or when a workflow reports a missing model file.
---

# ComfyUI models

All weights go through `.codex/model_download.py` and its pinned catalogue
`.codex/models.json`. Never fetch weights with curl, `huggingface-cli`, the
Manager UI or a custom node: those skip the hash, license and disk checks.

## Gate

Downloading is a user decision. Before any `download`, show the user the
`plan` output (files, sizes, license) and get an explicit yes for that profile.
`list`, `plan` and `verify` need no approval.

## Steps

1. Check what exists: `.venv/bin/python .codex/model_download.py list`, then
   `plan <profile>`.
2. New model: find the exact file on Hugging Face (prefer `Comfy-Org` repackages,
   which ship single `.safetensors` files in ComfyUI's layout). Pin it:
   `.venv/bin/python .codex/model_download.py add <profile> --key <key> --folder <folder> --url <hf-file-url>`.
   The folder is the native `models/` category: `checkpoints`, `diffusion_models`,
   `text_encoders`, `vae`, `loras`, `upscale_models`, `controlnet`.
   Review the license it recorded; tell the user if it is non-commercial.
3. Memory check before choosing: GPU is 6 GiB, RAM is often near full. Prefer
   fp8 or GGUF builds when a bf16 model exceeds ~8 GB (`ComfyUI-GGUF` is installed;
   GGUF files go in `unet/`).
4. After approval: `download <profile>`, then `verify <profile>`.
5. If the model is meant for shots, add or update its entry in
   `studio/presets.json` (`family`, file names, sampler settings, `catalogue_profile`)
   and a matching `studio/templates/<family>-{t2i,i2i}.json`. Run
   `.venv/bin/python -m unittest discover -s studio -p test_shot.py`.
6. Tests for the helper: `.venv/bin/python -m unittest discover -s .codex -p test_model_download.py`.

Interrupted downloads resume from `.part`. A file with the wrong hash is kept
and reported; never delete or overwrite it without asking.
