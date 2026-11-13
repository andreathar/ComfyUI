#!/usr/bin/env bash
# Canonical ComfyUI launch for this workstation (RTX 3060 Laptop 6 GB + H3).
# Measured locks: --reserve-vram 1.0, --disable-pinned-memory, --use-ck-attention,
# --preview-method latent2rgb. Extra args are allowed only when they do not
# fight those locks (e.g. --cache-ram 6 6, --cache-none, --offline).
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

locked=(
    --listen 127.0.0.1 --port 8188
    --disable-auto-launch --enable-manager --enable-assets
    --reserve-vram 1.0 --disable-pinned-memory --use-ck-attention
    --preview-method latent2rgb
)

# Drop caller overrides that would conflict with the locked mutually-exclusive
# attention/VRAM groups or quietly replace the measured H3 defaults.
extra=()
skip_next=0
for arg in "$@"; do
    if (( skip_next )); then
        skip_next=0
        printf '%s\n' "launch.sh: ignoring override after blocked flag: $arg" >&2
        continue
    fi
    case "$arg" in
        --use-split-cross-attention|--use-quad-cross-attention|--use-pytorch-cross-attention|--use-sage-attention|--use-flash-attention|--use-ck-attention)
            printf '%s\n' "launch.sh: ignoring attention override $arg (locked: --use-ck-attention)" >&2
            ;;
        --gpu-only|--highvram|--lowvram|--novram|--cpu)
            printf '%s\n' "launch.sh: ignoring VRAM-mode override $arg (DynamicVRAM + --reserve-vram 1.0)" >&2
            ;;
        --reserve-vram|--preview-method)
            printf '%s\n' "launch.sh: ignoring $arg override (locked by this launcher)" >&2
            skip_next=1
            ;;
        --reserve-vram=*|--preview-method=*)
            printf '%s\n' "launch.sh: ignoring $arg (locked by this launcher)" >&2
            ;;
        --disable-pinned-memory|--enable-pinned-memory)
            printf '%s\n' "launch.sh: ignoring $arg (locked: --disable-pinned-memory)" >&2
            ;;
        --listen|--port)
            printf '%s\n' "launch.sh: ignoring $arg override (locked: 127.0.0.1:8188)" >&2
            skip_next=1
            ;;
        --listen=*|--port=*)
            printf '%s\n' "launch.sh: ignoring $arg (locked: 127.0.0.1:8188)" >&2
            ;;
        --disable-assets)
            printf '%s\n' "launch.sh: ignoring $arg (locked: --enable-assets)" >&2
            ;;
        *)
            extra+=("$arg")
            ;;
    esac
done

printf '%s\n' "launch.sh: H3/6GB locks → reserve-vram=1.0 disable-pinned-memory use-ck-attention preview=latent2rgb assets on" >&2
exec .venv/bin/python main.py "${extra[@]}" "${locked[@]}"
