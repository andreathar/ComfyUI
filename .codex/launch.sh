#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd -- "$project_dir"
if [[ ! -x .venv/bin/python ]]; then
    printf '%s\n' 'Missing .venv/bin/python. Follow .codex/SETUP_PLAN.md.' >&2
    exit 1
fi

export PYTHONNOUSERSITE=1
export HF_HUB_DISABLE_TELEMETRY=1
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export DO_NOT_TRACK=1
export COMFYUI_DISABLE_PRODUCT_TIPS=1
export UV_PYTHON="$project_dir/.venv/bin/python"
export UV_TORCH_BACKEND=cu130
export UV_LINK_MODE=copy

exec .venv/bin/python main.py \
    --listen 127.0.0.1 --port 8188 \
    --disable-auto-launch --enable-manager \
    --reserve-vram 1.0 \
    --preview-method latent2rgb \
    "$@"
